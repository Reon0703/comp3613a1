from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, select

from app.models.application import Application, ApplicationDocument
from app.models.document import Document
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy
from app.routers import api_student_applications as api_student_applications_router
from app.services import internship_service
from app.utilities.security import encrypt_password

PASSWORD = "student-applications-api-password"


def create_user(db_session: Session, username: str, role: str, **profile) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password(PASSWORD),
        role=role,
        **profile,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_vacancy(db_session: Session, company: User, title: str) -> InternshipVacancy:
    vacancy = InternshipVacancy(
        company_id=company.id,
        title=title,
        description="A role for testing student application lists.",
        location="Port of Spain",
        field_of_study="Technology",
        status="Published",
        is_published=True,
    )
    db_session.add(vacancy)
    db_session.commit()
    db_session.refresh(vacancy)
    return vacancy


def create_application(
    db_session: Session,
    student: User,
    vacancy: InternshipVacancy,
    *,
    document_name: str,
    generic_pdf: bytes,
) -> Application:
    application = Application(
        student_id=student.id,
        vacancy_id=vacancy.id,
        status=Application.STATUS_SUBMITTED,
    )
    document = Document(
        name=document_name,
        file_path=f"app/uploads/applications/{document_name}",
        type="application/pdf",
        size_bytes=len(generic_pdf),
    )
    db_session.add(application)
    db_session.add(document)
    db_session.commit()
    db_session.refresh(application)
    db_session.refresh(document)
    db_session.add(
        ApplicationDocument(
            application_id=application.id,
            document_id=document.id,
        )
    )
    db_session.commit()
    return application


def login(client, username: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200


def test_student_lists_only_owned_applications_with_details(
    client,
    db_session,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_api_owner",
        ROLE_STUDENT,
    )
    other_student = create_user(
        db_session,
        "student_applications_api_other",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_api_company",
        ROLE_COMPANY,
        company_name="Applications API Company",
    )
    own_vacancy = create_vacancy(db_session, company, "Owned Internship")
    other_vacancy = create_vacancy(db_session, company, "Other Internship")
    own_application = create_application(
        db_session,
        student,
        own_vacancy,
        document_name="own-resume.pdf",
        generic_pdf=generic_pdf,
    )
    create_application(
        db_session,
        other_student,
        other_vacancy,
        document_name="other-resume.pdf",
        generic_pdf=generic_pdf,
    )
    login(client, student.username)

    response = client.get("/api/student/applications")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [own_application.id]
    assert body["items"][0]["vacancy"] == {
        "title": "Owned Internship",
        "company_name": "Applications API Company",
    }
    assert body["items"][0]["documents"] == [
        {
            "id": body["items"][0]["documents"][0]["id"],
            "name": "own-resume.pdf",
            "type": "application/pdf",
            "size_bytes": len(generic_pdf),
        }
    ]
    assert body["pagination"] == {
        "total_count": 1,
        "current_page": 1,
        "limit": 12,
        "total_pages": 1,
    }


def test_company_cannot_list_student_applications(client, db_session):
    company = create_user(
        db_session,
        "student_applications_api_role_company",
        ROLE_COMPANY,
    )
    login(client, company.username)

    response = client.get("/api/student/applications")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only student accounts can view their applications."
    }


def test_student_applications_requires_authentication(client):
    response = client.get("/api/student/applications")

    assert response.status_code == 401


def test_student_applications_rejects_invalid_page(client, db_session):
    student = create_user(
        db_session,
        "student_applications_api_page",
        ROLE_STUDENT,
    )
    login(client, student.username)

    response = client.get("/api/student/applications", params={"page": 0})

    assert response.status_code == 422


def test_student_replaces_submitted_application_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_replace_owner",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_replace_company",
        ROLE_COMPANY,
        company_name="Replace API Company",
    )
    vacancy = create_vacancy(db_session, company, "Replace API Internship")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="old-resume.pdf",
        generic_pdf=generic_pdf,
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.put(
        f"/api/student/applications/{application.id}/document",
        files={
            "application_document": (
                "new-resume.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "application document updated"}
    db_session.expire_all()
    documents = db_session.exec(select(Document)).all()
    assert [document.name for document in documents] == ["new-resume.pdf"]
    assert documents[0].size_bytes == len(generic_pdf)


def test_student_replaces_document_without_upload_in_development(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_replace_fallback_owner",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_replace_fallback_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(
        db_session,
        company,
        "Replace Fallback API Internship",
    )
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="old-fallback-resume.pdf",
        generic_pdf=generic_pdf,
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    monkeypatch.setattr(
        api_student_applications_router,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    login(client, student.username)

    response = client.put(
        f"/api/student/applications/{application.id}/document",
    )

    assert response.status_code == 200
    assert response.json() == {"message": "application document updated"}
    db_session.expire_all()
    documents = db_session.exec(select(Document)).all()
    assert [document.name for document in documents] == ["generic-test-application.pdf"]
    assert Path(documents[0].file_path).read_bytes().startswith(b"%PDF-1.4")


def test_student_cannot_replace_reviewed_application_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_replace_reviewed",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_replace_reviewed_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, "Reviewed API Internship")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="reviewed-resume.pdf",
        generic_pdf=generic_pdf,
    )
    application.status = Application.STATUS_UNDER_REVIEW
    db_session.add(application)
    db_session.commit()
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.put(
        f"/api/student/applications/{application.id}/document",
        files={
            "application_document": (
                "replacement.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Only applications with Submitted status can be edited."
    }


def test_student_cannot_replace_another_students_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_replace_other",
        ROLE_STUDENT,
    )
    owner = create_user(
        db_session,
        "student_applications_replace_actual_owner",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_replace_other_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, "Other Owner API Internship")
    application = create_application(
        db_session,
        owner,
        vacancy,
        document_name="owner-resume.pdf",
        generic_pdf=generic_pdf,
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    login(client, student.username)

    response = client.put(
        f"/api/student/applications/{application.id}/document",
        files={
            "application_document": (
                "replacement.pdf",
                generic_pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found."}


def test_student_withdraws_owned_application_with_no_content(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_withdraw_owner",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_withdraw_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, "Withdraw API Internship")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="withdraw-resume.pdf",
        generic_pdf=generic_pdf,
    )
    application_id = application.id
    application.status = Application.STATUS_UNDER_REVIEW
    db_session.add(application)
    db_session.commit()
    document = db_session.exec(select(Document)).one()
    upload_directory = tmp_path / "applications"
    upload_directory.mkdir()
    file_path = upload_directory / "withdraw-resume.pdf"
    file_path.write_bytes(generic_pdf)
    document.file_path = str(file_path)
    db_session.add(document)
    db_session.commit()
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.delete(f"/api/student/applications/{application_id}")

    assert response.status_code == 204
    assert response.content == b""
    db_session.expire_all()
    assert db_session.get(Application, application_id) is None
    assert db_session.exec(select(ApplicationDocument)).all() == []
    assert db_session.exec(select(Document)).all() == []
    assert not file_path.exists()


def test_student_cannot_withdraw_another_students_application(
    client,
    db_session,
    generic_pdf,
):
    student = create_user(
        db_session,
        "student_applications_withdraw_other",
        ROLE_STUDENT,
    )
    owner = create_user(
        db_session,
        "student_applications_withdraw_actual_owner",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "student_applications_withdraw_other_company",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, "Private Withdraw Internship")
    application = create_application(
        db_session,
        owner,
        vacancy,
        document_name="private-withdraw-resume.pdf",
        generic_pdf=generic_pdf,
    )
    login(client, student.username)

    response = client.delete(f"/api/student/applications/{application.id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found."}
    assert db_session.get(Application, application.id) is not None


def test_company_cannot_withdraw_student_application(client, db_session):
    company = create_user(
        db_session,
        "student_applications_withdraw_wrong_role",
        ROLE_COMPANY,
    )
    login(client, company.username)

    response = client.delete("/api/student/applications/1")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only student accounts can delete their applications."
    }
