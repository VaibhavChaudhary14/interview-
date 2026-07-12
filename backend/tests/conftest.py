import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.session import Base, get_db
from app.models import Resume, Session, Question, Answer, Report, Consent, Recording, AuditLog
from app.main import app

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # Create all tables in the SQLite database before running the test
    Base.metadata.create_all(bind=engine)

    # Seed role families
    import uuid
    from app.models.role_family import RoleFamily
    
    session = TestingSessionLocal()
    try:
        seeds = [
            RoleFamily(
                id=uuid.uuid4(),
                slug="software_engineering",
                name="Software Engineering",
                description="Software development, programming, backend, frontend, systems engineering, design patterns, testing, databases, and deployment.",
                keywords=["swe", "software engineer", "backend", "frontend", "full stack", "developer", "programmer", "coder"],
                kb_collection_name="kb_backend_engineer",
            ),
            RoleFamily(
                id=uuid.uuid4(),
                slug="ai_ml",
                name="AI / ML Engineering",
                description="Machine learning, artificial intelligence, neural networks, computer vision, natural language processing, data science, and model training.",
                keywords=["ml engineer", "ai engineer", "machine learning", "data scientist", "deep learning", "nlp scientist"],
                kb_collection_name="kb_ai_ml_engineer",
            ),
            RoleFamily(
                id=uuid.uuid4(),
                slug="product_management",
                name="Product Management",
                description="Product strategy, roadmap planning, user research, backlog grooming, cross-functional leadership, and feature specifications.",
                keywords=["product manager", "pm", "product owner", "product lead"],
                kb_collection_name=None,
            ),
            RoleFamily(
                id=uuid.uuid4(),
                slug="design",
                name="Design",
                description="User experience, user interface, graphic design, design systems, visual design, wireframing, and user research.",
                keywords=["designer", "ux", "ui", "product design", "visual designer"],
                kb_collection_name=None,
            ),
            RoleFamily(
                id=uuid.uuid4(),
                slug="sales",
                name="Sales",
                description="Account management, outbound sales, customer relationship management, deal closing, SDR, business development, and lead qualification.",
                keywords=["sales", "account executive", "sdr", "bdr", "sales representative", "sales lead"],
                kb_collection_name=None,
            ),
        ]
        session.add_all(seeds)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    yield
    # Drop all tables after the test runs
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
