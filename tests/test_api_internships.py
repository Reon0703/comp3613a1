from pathlib import Path
from types import SimpleNamespace

from sqlmodel import select

from app.models.application import Application
from app.models.document import Document
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy, VacancyDocument
from app.routers import api_internships as api_internships_router
from app.services import internship_service
from app.services.internship_service import (
    MAX_APPLICATION_DOCUMENT_SIZE,
    InternshipService,
)
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


def test_student_view_published_internship_details(
    client,
    db_session,
    generic_pdf,
):
    student = create_user(db_session, "internship_detail_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_detail_company", ROLE_COMPANY)
    company.company_name = "Detail API Company"
    company.location = "San Fernando"
    company.profile_image_url = "/static/img/company.svg"
    db_session.add(company)
    db_session.commit()
    vacancy = create_vacancy(
        db_session,
        company,
        title="Detail API Internship",
    )
    application = Application(
        student_id=student.id,
        vacancy_id=vacancy.id,
        status=Application.STATUS_SUBMITTED,
    )
    document = Document(
        name="Role brief.pdf",
        file_path="https://example.com/role-brief.pdf",
        type="application/pdf",
        size_bytes=len(generic_pdf),
    )
    db_session.add(application)
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    db_session.add(
        VacancyDocument(
            vacancy_id=vacancy.id,
            document_id=document.id,
        )
    )
    db_session.commit()
    login(client, student.username)

    response = client.get(f"/api/internships/{vacancy.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Detail API Internship"
    assert body["is_published"] is True
    assert body["already_applied"] is True
    assert body["company"] == {
        "company_name": "Detail API Company",
        "location": "San Fernando",
        "profile_image_url": "/static/img/company.svg",
    }
    assert body["documents"] == [
        {
            "id": document.id,
            "name": "Role brief.pdf",
            "type": "application/pdf",
            "size_bytes": len(generic_pdf),
        }
    ]


def test_student_detail_rejects_company_account(client, db_session):
    company = create_user(db_session, "internship_detail_role_company", ROLE_COMPANY)
    login(client, company.username)

    response = client.get("/api/internships/1")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only student accounts can view internship details."
    }


def test_student_detail_hides_unpublished_vacancy(client, db_session):
    student = create_user(db_session, "internship_detail_hidden_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_detail_hidden_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Unpublished API Internship",
        status="Draft",
    )
    login(client, student.username)

    response = client.get(f"/api/internships/{vacancy.id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Published internship not found."}


def test_student_download_redirects_to_external_vacancy_document(
    client,
    db_session,
    generic_pdf,
):
    student = create_user(db_session, "internship_download_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_download_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Download API Internship",
    )
    document = Document(
        name="Role brief.pdf",
        file_path="https://example.com/role-brief.pdf",
        type="application/pdf",
        size_bytes=len(generic_pdf),
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    db_session.add(
        VacancyDocument(
            vacancy_id=vacancy.id,
            document_id=document.id,
        )
    )
    db_session.commit()
    login(client, student.username)

    response = client.get(
        f"/api/internships/{vacancy.id}/documents/{document.id}",
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/role-brief.pdf"


def test_student_download_serves_local_vacancy_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(db_session, "internship_download_local_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_download_local_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Local Download API Internship",
    )
    document = Document(
        name="Local role brief.pdf",
        file_path="app/uploads/local-role-brief.pdf",
        type="application/pdf",
        size_bytes=len(generic_pdf),
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    db_session.add(
        VacancyDocument(
            vacancy_id=vacancy.id,
            document_id=document.id,
        )
    )
    db_session.commit()
    local_file = tmp_path / "local-role-brief.pdf"
    local_file.write_bytes(generic_pdf)
    monkeypatch.setattr(
        InternshipService,
        "local_document_path",
        staticmethod(lambda _file_path: local_file),
    )
    login(client, student.username)

    response = client.get(
        f"/api/internships/{vacancy.id}/documents/{document.id}",
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Local%20role%20brief.pdf" in response.headers["content-disposition"]
    assert response.content == generic_pdf


def test_student_cannot_download_document_from_another_vacancy(
    client,
    db_session,
    generic_pdf,
):
    student = create_user(
        db_session, "internship_download_missing_student", ROLE_STUDENT
    )
    company = create_user(
        db_session, "internship_download_missing_company", ROLE_COMPANY
    )
    vacancy = create_vacancy(
        db_session,
        company,
        title="No Linked Document Internship",
    )
    document = Document(
        name="Unlinked.pdf",
        file_path="https://example.com/unlinked.pdf",
        type="application/pdf",
        size_bytes=len(generic_pdf),
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    login(client, student.username)

    response = client.get(
        f"/api/internships/{vacancy.id}/documents/{document.id}",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Supplementary document not found."}


def test_student_applies_to_published_internship_with_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(db_session, "internship_apply_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_apply_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Application API Internship",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == student.id
    assert body["vacancy_id"] == vacancy.id
    assert body["status"] == Application.STATUS_SUBMITTED
    assert body["documents"] == [
        {
            "id": body["documents"][0]["id"],
            "name": "resume.pdf",
            "type": "application/pdf",
            "size_bytes": len(generic_pdf),
        }
    ]
    assert db_session.exec(select(Application)).one().id == body["id"]


def test_student_apply_without_pdf_uses_development_generic_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "internship_apply_fallback_student",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "internship_apply_fallback_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(
        db_session,
        company,
        title="Fallback PDF API Internship",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    monkeypatch.setattr(
        api_internships_router,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    login(client, student.username)

    response = client.post(f"/api/internships/{vacancy.id}/applications")

    assert response.status_code == 201
    application = db_session.get(Application, response.json()["id"])
    assert application is not None
    assert application.documents[0].document.name == "generic-test-application.pdf"
    stored_pdf = Path(application.documents[0].document.file_path).read_bytes()
    assert stored_pdf.startswith(b"%PDF-1.4")
    assert stored_pdf.endswith(b"%%EOF\n")


def test_student_apply_without_pdf_is_rejected_in_production(
    client,
    db_session,
    monkeypatch,
):
    student = create_user(
        db_session,
        "internship_apply_production_student",
        ROLE_STUDENT,
    )
    login(client, student.username)
    monkeypatch.setattr(
        api_internships_router,
        "get_settings",
        lambda: SimpleNamespace(env="production"),
    )

    response = client.post("/api/internships/1/applications")

    assert response.status_code == 422
    assert response.json() == {"detail": "An application PDF is required."}


def test_student_duplicate_application_returns_conflict(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(db_session, "internship_duplicate_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_duplicate_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Duplicate API Internship",
    )
    db_session.add(
        Application(
            student_id=student.id,
            vacancy_id=vacancy.id,
            status=Application.STATUS_SUBMITTED,
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "You have already applied to this internship."}


def test_student_apply_rejects_unpublished_vacancy(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(db_session, "internship_unavailable_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_unavailable_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Closed API Internship",
        status="Closed",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "This internship is no longer accepting applications."
    }


def test_student_apply_rejects_invalid_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(db_session, "internship_invalid_pdf_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_invalid_pdf_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Invalid PDF API Internship",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                b"not a PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The uploaded file is not a valid PDF document."
    }


def test_student_apply_rejects_oversized_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(db_session, "internship_large_pdf_student", ROLE_STUDENT)
    company = create_user(db_session, "internship_large_pdf_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Large PDF API Internship",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                generic_pdf
                + b"x" * (MAX_APPLICATION_DOCUMENT_SIZE + 1 - len(generic_pdf)),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Application documents must be 10 MB or smaller."
    }


def test_company_cannot_apply_to_internship(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    company = create_user(db_session, "internship_apply_role_company", ROLE_COMPANY)
    vacancy = create_vacancy(
        db_session,
        company,
        title="Role-Restricted API Internship",
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, company.username)

    response = client.post(
        f"/api/internships/{vacancy.id}/applications",
        files={
            "application_document": (
                "resume.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only student accounts can apply to internships."
    }
