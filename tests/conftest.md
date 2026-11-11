import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models.application import Application
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy


@pytest.fixture
def student_user():
    return User(
        id=101,
        username="student",
        email="student@example.com",
        password="not-used",
        role=ROLE_STUDENT,
    )


@pytest.fixture
def company_user():
    return User(
        id=201,
        username="company",
        email="company@example.com",
        password="not-used",
        role=ROLE_COMPANY,
        company_name="Example Company",
    )


@pytest.fixture
def vacancy(company_user):
    return InternshipVacancy(
        id=12,
        company_id=company_user.id,
        title="Summer Intern",
        description="Assist the team",
        location="Port of Spain",
        field_of_study="Technology",
        status="Published",
        is_published=True,
    )


@pytest.fixture
def application(student_user, vacancy):
    return Application(
        id=35,
        student_id=student_user.id,
        vacancy_id=vacancy.id,
        status=Application.STATUS_SUBMITTED,
    )


@pytest.fixture
def test_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'integration-tests.db'}")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine):
    def override_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    test_client = TestClient(app, follow_redirects=False)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        test_client.close()
