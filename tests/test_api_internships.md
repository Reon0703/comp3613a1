from app.models.application import Application
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy
from app.utilities.security import encrypt_password

PASSWORD = "student-internship-api-password"


def create_user(db_session, username: str, role: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password(PASSWORD),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_vacancy(
    db_session,
    company: User,
    *,
    title: str,
    field_of_study: str = "Technology",
    status: str = "Published",
    is_published: bool | None = None,
) -> InternshipVacancy:
    vacancy = InternshipVacancy(
        company_id=company.id,
        title=title,
        description="A role for testing published internship browsing.",
        location="Port of Spain",
        field_of_study=field_of_study,
        status=status,
        is_published=status == "Published" if is_published is None else is_published,
    )
    db_session.add(vacancy)
    db_session.commit()
    db_session.refresh(vacancy)
    return vacancy


def login(client, username: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200


def test_student_browse_filters_published_search_and_fields(client, db_session):
    student = create_user(db_session, "internship_api_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_api_company", ROLE_COMPANY)
    other_company = create_user(
        db_session,
        "internship_api_other_company",
        ROLE_COMPANY,
    )
    legacy_published = create_vacancy(
        db_session,
        company,
        title="Design Technology Internship",
        is_published=False,
    )
    create_vacancy(
        db_session,
        other_company,
        title="Design Business Internship",
        field_of_study="Business",
    )
    applied = create_vacancy(
        db_session,
        company,
        title="Design Applied Internship",
    )
    create_vacancy(
        db_session,
        company,
        title="Design Draft Internship",
        status="Draft",
    )
    create_vacancy(
        db_session,
        company,
        title="Engineering Internship",
    )
    db_session.add(
        Application(
            student_id=student.id,
            vacancy_id=applied.id,
            status=Application.STATUS_SUBMITTED,
        )
    )
    db_session.commit()
    login(client, student.username)

    response = client.get(
        "/api/internships",
        params=[
            ("q", "Design"),
            ("field_of_study", "Technology"),
            ("field_of_study", "Business"),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["title"] for item in body["items"]} == {
        "Design Technology Internship",
        "Design Business Internship",
    }
    assert all(item["status"] == "Published" for item in body["items"])
    assert all(item["is_published"] is True for item in body["items"])
    assert (
        next(item for item in body["items"] if item["id"] == legacy_published.id)[
            "is_published"
        ]
        is True
    )
    assert body["pagination"] == {
        "total_count": 2,
        "current_page": 1,
        "limit": 12,
        "total_pages": 1,
    }


def test_student_browse_pagination(client, db_session):
    student = create_user(db_session, "internship_api_page_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_api_page_company", ROLE_COMPANY)
    for index in range(13):
        create_vacancy(db_session, company, title=f"Paged Internship {index}")
    login(client, student.username)

    response = client.get("/api/internships", params={"page": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["pagination"] == {
        "total_count": 13,
        "current_page": 2,
        "limit": 12,
        "total_pages": 2,
    }


def test_student_browse_requires_student_account(client, db_session):
    company = create_user(db_session, "internship_api_role_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.get("/api/internships")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only student accounts can browse internships."
    }


def test_student_browse_requires_authentication(client):
    response = client.get("/api/internships")

    assert response.status_code == 401


def test_student_browse_rejects_long_search_query(client, db_session):
    student = create_user(db_session, "internship_api_query_student", ROLE_STUDENT)
    login(client, student.username)

    response = client.get("/api/internships", params={"q": "x" * 101})

    assert response.status_code == 422
