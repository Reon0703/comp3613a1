from sqlmodel import select

from app.models.application import Application
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy
from app.utilities.security import encrypt_password

PASSWORD = "company-vacancy-api-password"


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
    title: str = "API Internship",
    status: str = "Published",
    image_url: str | None = None,
) -> InternshipVacancy:
    vacancy = InternshipVacancy(
        company_id=company.id,
        title=title,
        description="A role created for API tests.",
        location="Port of Spain",
        field_of_study="Technology",
        status=status,
        is_published=status == "Published",
        image_url=image_url,
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


def test_company_list_returns_only_owned_vacancies_with_counts(
    client,
    db_session,
):
    company = create_user(db_session, "vacancy_list_owner", ROLE_COMPANY)
    other_company = create_user(db_session, "vacancy_list_other", ROLE_COMPANY)
    student = create_user(db_session, "vacancy_list_student", ROLE_STUDENT)
    populated = create_vacancy(db_session, company, title="Has applicants")
    create_vacancy(db_session, company, title="No applicants", status="Draft")
    create_vacancy(db_session, other_company, title="Private vacancy")
    db_session.add(
        Application(
            student_id=student.id,
            vacancy_id=populated.id,
            status=Application.STATUS_SUBMITTED,
        )
    )
    db_session.commit()
    login(client, company.username)

    response = client.get("/api/company/vacancies")

    assert response.status_code == 200
    vacancies = response.json()
    assert [vacancy["title"] for vacancy in vacancies] == [
        "No applicants",
        "Has applicants",
    ]
    assert [vacancy["applicant_count"] for vacancy in vacancies] == [0, 1]
    assert all(vacancy["company_id"] == company.id for vacancy in vacancies)
    assert all("image_url" not in vacancy for vacancy in vacancies)


def test_company_list_derives_publication_flag_from_status(client, db_session):
    company = create_user(db_session, "vacancy_list_status_company", ROLE_COMPANY)
    vacancy = create_vacancy(db_session, company, status="Published")
    vacancy.is_published = False
    db_session.add(vacancy)
    db_session.commit()
    login(client, company.username)

    response = client.get("/api/company/vacancies")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "Published"
    assert response.json()[0]["is_published"] is True


def test_company_vacancy_api_rejects_student_account(client, db_session):
    student = create_user(db_session, "vacancy_api_student", ROLE_STUDENT)
    login(client, student.username)

    response = client.get("/api/company/vacancies")

    assert response.status_code == 403
    assert response.json() == {"detail": "Only company accounts can view vacancies."}


def test_student_cannot_create_or_update_company_vacancies(
    client,
    db_session,
):
    student = create_user(db_session, "vacancy_api_write_student", ROLE_STUDENT)
    company = create_user(db_session, "vacancy_api_write_company", ROLE_COMPANY)
    vacancy = create_vacancy(db_session, company)
    login(client, student.username)

    create_response = client.post(
        "/api/company/vacancies",
        data={
            "title": "Unauthorized vacancy",
            "description": "A student cannot create this.",
            "field_of_study": "Technology",
        },
    )
    update_response = client.put(
        f"/api/company/vacancies/{vacancy.id}",
        data={"title": "Unauthorized edit"},
    )

    assert create_response.status_code == 403
    assert update_response.status_code == 403


def test_company_can_create_vacancy_through_api(client, db_session):
    company = create_user(db_session, "vacancy_create_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.post(
        "/api/company/vacancies",
        data={
            "title": "  API Created Internship  ",
            "description": "  Build an API feature.  ",
            "location": "Port of Spain",
            "field_of_study": "Technology",
            "status": "Published",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company_id"] == company.id
    assert body["title"] == "API Created Internship"
    assert body["description"] == "Build an API feature."
    assert body["status"] == "Published"
    assert body["is_published"] is True
    assert body["image_url"] is None
    created = db_session.exec(
        select(InternshipVacancy).where(InternshipVacancy.id == body["id"])
    ).one()
    assert created.company_id == company.id


def test_company_vacancy_create_rejects_invalid_fields(client, db_session):
    company = create_user(db_session, "vacancy_invalid_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.post(
        "/api/company/vacancies",
        data={
            "title": "Invalid Field",
            "description": "Unsupported field of study.",
            "field_of_study": "Underwater Basketry",
            "status": "Published",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Choose a valid field of study."}


def test_company_can_create_vacancy_with_optional_image(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    from app.services import vacancy_service

    monkeypatch.setattr(vacancy_service, "UPLOAD_DIRECTORY", tmp_path)
    company = create_user(db_session, "vacancy_image_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.post(
        "/api/company/vacancies",
        data={
            "title": "Image Internship",
            "description": "A vacancy with an image.",
            "field_of_study": "Technology",
        },
        files={"vacancy_image": ("vacancy.png", b"image", "image/png")},
    )

    assert response.status_code == 201
    image_url = response.json()["image_url"]
    assert image_url.startswith("/static/uploads/")
    assert (tmp_path / image_url.rsplit("/", 1)[-1]).read_bytes() == b"image"


def test_company_vacancy_create_rejects_invalid_image(client, db_session):
    company = create_user(db_session, "vacancy_bad_image_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.post(
        "/api/company/vacancies",
        data={
            "title": "Invalid Image",
            "description": "An invalid image should be rejected.",
            "field_of_study": "Technology",
        },
        files={"vacancy_image": ("vacancy.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Upload a JPG, PNG, or WEBP image."}


def test_company_update_preserves_omitted_fields_and_image(client, db_session):
    company = create_user(db_session, "vacancy_update_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        image_url="/static/uploads/existing.png",
    )
    login(client, company.username)

    response = client.put(
        f"/api/company/vacancies/{vacancy.id}",
        data={"title": "Updated API Internship"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated API Internship"
    assert body["description"] == vacancy.description
    assert body["location"] == vacancy.location
    assert body["field_of_study"] == vacancy.field_of_study
    assert body["status"] == "Published"
    assert body["image_url"] == "/static/uploads/existing.png"


def test_company_cannot_update_another_company_vacancy(client, db_session):
    owner = create_user(db_session, "vacancy_update_owner", ROLE_COMPANY)
    other_company = create_user(db_session, "vacancy_update_other", ROLE_COMPANY)
    vacancy = create_vacancy(db_session, owner)
    login(client, other_company.username)

    response = client.put(
        f"/api/company/vacancies/{vacancy.id}",
        data={"title": "Unauthorized edit"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Vacancy not found."}


def test_company_vacancy_update_preserves_published_status_with_applicants(
    client,
    db_session,
):
    company = create_user(db_session, "vacancy_status_company", ROLE_COMPANY)
    student = create_user(db_session, "vacancy_status_student", ROLE_STUDENT)
    vacancy = create_vacancy(db_session, company)
    db_session.add(
        Application(
            student_id=student.id,
            vacancy_id=vacancy.id,
            status=Application.STATUS_SUBMITTED,
        )
    )
    db_session.commit()
    login(client, company.username)

    response = client.put(
        f"/api/company/vacancies/{vacancy.id}",
        data={"status": "Draft"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Published"
    assert response.json()["is_published"] is True


def test_company_vacancy_routes_require_authentication(client):
    response = client.get("/api/company/vacancies")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
