from alembic import context
from sqlalchemy import create_engine
from app.core.config import settings
from app.db.session import Base
from app.models import *  # noqa: F401, F403

target_metadata = Base.metadata
config = context.config

def run_migrations_online():
    url = config.get_main_option("sqlalchemy.url") or settings.database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
