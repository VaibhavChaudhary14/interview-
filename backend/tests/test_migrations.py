"""
Migration safety test — runs against a real (ephemeral) Postgres database.

Why this test must NOT be skipped:
  The boolean-default Postgres bug we hit earlier could only have been caught
  against real Postgres, not SQLite. This test was added specifically to replace
  the "someone remembers to manually check migrations" pattern that caused that
  bug. A migration test that skips is equivalent to not having it.

Connection strategy:
  Reads the Postgres host from the DATABASE_URL env var (same URL the app uses)
  so the test works whether run from:
  - Inside the backend container (db=db:5432, default)
  - On the host machine (db=localhost:5432 if port is forwarded)
  - In a CI environment with a Postgres service

  The admin connection uses the same host/port/creds but connects to the
  default "postgres" database to create/drop the throwaway test database.
"""
import pytest
import os
import re
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command


def _parse_postgres_admin_url() -> str:
    """
    Derive a Postgres admin URL (database=postgres) from DATABASE_URL.
    Falls back to localhost:5432 if DATABASE_URL isn't set or isn't Postgres.
    """
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db:5432/screening_db",
    )
    # Replace the database name with 'postgres' for the admin connection
    # Works for both postgresql+psycopg:// and postgresql:// schemes
    admin_url = re.sub(r"/[^/]+$", "/postgres", db_url)
    return admin_url


def _test_db_url(admin_url: str, test_db_name: str) -> str:
    """Swap the database name in admin_url to the test database name."""
    return re.sub(r"/[^/]+$", f"/{test_db_name}", admin_url)


def test_migrations_on_postgres():
    """
    Runs upgrade-head → downgrade-base → upgrade-head against a fresh,
    throwaway Postgres database derived from the app's DATABASE_URL.

    Validates:
    1. Every migration applies cleanly from scratch
    2. Every migration rolls back cleanly (downgrade path isn't broken)
    3. Re-applying after downgrade succeeds (idempotency / no leftover state)

    This catches Postgres-specific migration bugs (boolean server_default,
    Enum DDL, generated columns) that SQLite silently ignores.
    """
    test_db_name = "screening_db_migration_test"
    admin_url = _parse_postgres_admin_url()

    # Try to connect to Postgres using the app's host/port/creds
    try:
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))
    except Exception as e:
        pytest.fail(
            f"Could not connect to Postgres admin DB ({admin_url}) — "
            f"migration test cannot be skipped. Fix the connection first.\n"
            f"Error: {e}"
        )

    run_url = _test_db_url(admin_url, test_db_name)
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")

    try:
        cfg = Config(ini_path)
        cfg.set_main_option("script_location", os.path.join(backend_dir, "app/db/migrations"))
        cfg.set_main_option("sqlalchemy.url", run_url)

        # 1. Fresh upgrade to head — all migrations must apply cleanly
        command.upgrade(cfg, "head")

        # 2. Downgrade to base — all downgrade() methods must work
        command.downgrade(cfg, "base")

        # 3. Re-upgrade — no leftover state should block a fresh apply
        command.upgrade(cfg, "head")

        # 4. Spot-check: verify key tables exist after final upgrade
        check_engine = create_engine(run_url)
        with check_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = {row[0] for row in result}

        expected_tables = {
            "sessions", "questions", "answers", "recordings",
            "consent_policy_versions", "consents", "provider_usage",
            "answer_metrics", "transcription_jobs", "audit_logs",
            "role_families", "reports", "resumes", "feedbacks",
        }
        missing = expected_tables - tables
        assert not missing, (
            f"Migration ran to head but expected tables are missing: {missing}\n"
            f"Present tables: {sorted(tables)}"
        )

    finally:
        # Always clean up the throwaway database
        try:
            cleanup_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with cleanup_engine.connect() as conn:
                # Terminate connections before dropping
                conn.execute(text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
                ))
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        except Exception:
            pass
