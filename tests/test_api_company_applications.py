from sqlmodel import Session

from app.models.application import Application, ApplicationDocument
from app.models.document import Document
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy
from app.utilities.security import encrypt_password

PASSWORD = "company-applications-api-password"


def create_user(
    db_session: Session,
    username: str,
    role: str,
    **profile,
) -> User:
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


def create_vacancy(
    db_session: Session,
    company: User,
    title: str,
) -> InternshipVacancy:
    vacancy = InternshipVacancy(
        company_id=company.id,
        title=title,
        description="A role for testing company application browsing.",
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
    status: str = Application.STATUS_SUBMITTED,
) -> Application:
    application = Application(
        student_id=student.id,
        vacancy_id=vacancy.id,
        status=status,
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


def login_company(client, username: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200


def test_company_browses_owned_vacancy_applications(client, db_session, generic_pdf):
    company = create_user(
        db_session,
        "company_applications_api_owner",
        ROLE_COMPANY,
    )
    other_company = create_user(
        db_session,
        "company_applications_api_other",
        ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "company_applications_api_student",
        ROLE_STUDENT,
        first_name="Ada",
        last_name="Lovelace",
        education_level="Undergraduate",
    )
    vacancy = create_vacancy(db_session, company, "Owned API Vacancy")
    other_vacancy = create_vacancy(db_session, other_company, "Other API Vacancy")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="ada-resume.pdf",
        generic_pdf=generic_pdf,
        status=Application.STATUS_SHORTLISTED,
    )
    create_application(
        db_session,
        student,
        other_vacancy,
        document_name="other-resume.pdf",
        generic_pdf=generic_pdf,
    )
    login_company(client, company.username)

    response = client.get(
        f"/api/company/vacancies/{vacancy.id}/applications",
        params={
            "q": "Ada",
            "education_level": "Undergraduate",
            "status_sort": "Shortlisted",
            "page": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [application.id]
    assert body["items"][0]["vacancy_id"] == vacancy.id
    assert body["items"][0]["student"] == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": student.email,
        "education_level": "Undergraduate",
    }
    assert body["items"][0]["documents"][0]["name"] == "ada-resume.pdf"
    assert body["pagination"] == {
        "total_count": 1,
        "current_page": 1,
        "limit": 12,
        "total_pages": 1,
    }


def test_company_application_browse_rejects_non_owner(client, db_session):
    company = create_user(
        db_session,
        "company_applications_api_nonowner",
        ROLE_COMPANY,
    )
    owner = create_user(
        db_session,
        "company_applications_api_actual_owner",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, owner, "Private API Vacancy")
    login_company(client, company.username)

    response = client.get(f"/api/company/vacancies/{vacancy.id}/applications")

    assert response.status_code == 404
    assert response.json() == {"detail": "Vacancy not found."}


def test_student_cannot_browse_company_applications(client, db_session):
    student = create_user(
        db_session,
        "company_applications_api_wrong_role",
        ROLE_STUDENT,
    )
    login_company(client, student.username)

    response = client.get("/api/company/vacancies/1/applications")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only company accounts can review applications."
    }


def test_company_reviews_owned_application_details(client, db_session, generic_pdf):
    company = create_user(
        db_session,
        "company_applications_api_review_owner",
        ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "company_applications_api_review_student",
        ROLE_STUDENT,
        first_name="Grace",
        last_name="Hopper",
        education_level="Postgraduate",
    )
    vacancy = create_vacancy(db_session, company, "Review API Vacancy")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="grace-resume.pdf",
        generic_pdf=generic_pdf,
    )
    login_company(client, company.username)

    response = client.get(
        f"/api/company/vacancies/{vacancy.id}/applications/{application.id}"
    )
    db_session.refresh(application)

    assert response.status_code == 200
    assert response.json() == {
        "vacancy": {"id": vacancy.id, "title": vacancy.title},
        "application": {
            "id": application.id,
            "student_id": student.id,
            "vacancy_id": vacancy.id,
            "status": Application.STATUS_SUBMITTED,
            "submission_date": application.submission_date.isoformat(),
            "student": {
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": student.email,
                "education_level": "Postgraduate",
            },
            "documents": [
                {
                    "id": application.documents[0].document_id,
                    "name": "grace-resume.pdf",
                    "type": "application/pdf",
                    "size_bytes": len(generic_pdf),
                }
            ],
        },
    }


def test_company_cannot_review_application_for_another_vacancy(
    client, db_session, generic_pdf
):
    company = create_user(
        db_session,
        "company_applications_api_review_wrong_owner",
        ROLE_COMPANY,
    )
    owner = create_user(
        db_session,
        "company_applications_api_review_actual_owner",
        ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "company_applications_api_review_other_student",
        ROLE_STUDENT,
    )
    vacancy = create_vacancy(db_session, owner, "Private Review Vacancy")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="private-review.pdf",
        generic_pdf=generic_pdf,
    )
    login_company(client, company.username)

    response = client.get(
        f"/api/company/vacancies/{vacancy.id}/applications/{application.id}"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Vacancy not found."}


def test_company_updates_application_review_status(client, db_session, generic_pdf):
    company = create_user(
        db_session,
        "company_applications_api_status_owner",
        ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "company_applications_api_status_student",
        ROLE_STUDENT,
    )
    vacancy = create_vacancy(db_session, company, "Status API Vacancy")
    application = create_application(
        db_session,
        student,
        vacancy,
        document_name="status-resume.pdf",
        generic_pdf=generic_pdf,
    )
    login_company(client, company.username)

    shortlist_response = client.put(
        f"/api/company/vacancies/{vacancy.id}/applications/{application.id}",
        json={"status": "Shortlisted"},
    )
    reject_response = client.put(
        f"/api/company/vacancies/{vacancy.id}/applications/{application.id}",
        json={"status": "Rejected"},
    )

    assert shortlist_response.status_code == 200
    assert shortlist_response.json() == {
        "id": application.id,
        "vacancy_id": vacancy.id,
        "status": "Shortlisted",
    }
    assert reject_response.status_code == 200
    assert reject_response.json() == {
        "id": application.id,
        "vacancy_id": vacancy.id,
        "status": "Rejected",
    }


def test_company_application_status_rejects_invalid_status(client, db_session):
    company = create_user(
        db_session,
        "company_applications_api_invalid_status",
        ROLE_COMPANY,
    )
    login_company(client, company.username)

    response = client.put(
        "/api/company/vacancies/1/applications/1",
        json={"status": "Under Review"},
    )

    assert response.status_code == 422


def test_finish_application_review_rejects_only_under_review_applications(
    client, db_session, generic_pdf
):
    company = create_user(
        db_session,
        "company_applications_api_finish_owner",
        ROLE_COMPANY,
    )
    submitted_student = create_user(
        db_session,
        "company_applications_api_finish_submitted",
        ROLE_STUDENT,
    )
    review_student = create_user(
        db_session,
        "company_applications_api_finish_review",
        ROLE_STUDENT,
    )
    shortlisted_student = create_user(
        db_session,
        "company_applications_api_finish_shortlisted",
        ROLE_STUDENT,
    )
    vacancy = create_vacancy(db_session, company, "Finish Review Vacancy")
    submitted = create_application(
        db_session,
        submitted_student,
        vacancy,
        document_name="submitted.pdf",
        generic_pdf=generic_pdf,
    )
    under_review = create_application(
        db_session,
        review_student,
        vacancy,
        document_name="under-review.pdf",
        generic_pdf=generic_pdf,
        status=Application.STATUS_UNDER_REVIEW,
    )
    shortlisted = create_application(
        db_session,
        shortlisted_student,
        vacancy,
        document_name="shortlisted.pdf",
        generic_pdf=generic_pdf,
        status=Application.STATUS_SHORTLISTED,
    )
    login_company(client, company.username)

    response = client.post(
        f"/api/company/vacancies/{vacancy.id}/applications/finish-review"
    )
    db_session.refresh(submitted)
    db_session.refresh(under_review)
    db_session.refresh(shortlisted)

    assert response.status_code == 200
    assert response.json() == {"updated_count": 1}
    assert submitted.status == Application.STATUS_SUBMITTED
    assert under_review.status == Application.STATUS_REJECTED
    assert shortlisted.status == Application.STATUS_SHORTLISTED


def test_finish_application_review_rejects_non_owner(client, db_session):
    company = create_user(
        db_session,
        "company_applications_api_finish_nonowner",
        ROLE_COMPANY,
    )
    owner = create_user(
        db_session,
        "company_applications_api_finish_actual_owner",
        ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, owner, "Private Finish Vacancy")
    login_company(client, company.username)

    response = client.post(
        f"/api/company/vacancies/{vacancy.id}/applications/finish-review"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Vacancy not found."}
