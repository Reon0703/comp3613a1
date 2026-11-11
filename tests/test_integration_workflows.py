from pathlib import Path

import pytest
from sqlmodel import select

from app.models.application import Application, ApplicationDocument
from app.models.document import Document
from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.models.vacancy import InternshipVacancy
from app.services import internship_service, vacancy_service
from app.utilities.security import encrypt_password


def create_user(
    session,
    username,
    email,
    *,
    role=ROLE_STUDENT,
    password="test-password",
    **profile,
):
    user = User(
        username=username,
        email=email,
        password=encrypt_password(password),
        role=role,
        **profile,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_vacancy(
    session,
    company,
    *,
    title="Summer Intern",
    description="Assist the technology team",
    location="Port of Spain",
    field_of_study="Technology",
    status="Published",
):
    vacancy = InternshipVacancy(
        company_id=company.id,
        title=title,
        description=description,
        location=location,
        field_of_study=field_of_study,
        status=status,
        is_published=status == "Published",
    )
    session.add(vacancy)
    session.commit()
    session.refresh(vacancy)
    return vacancy


def create_application(
    session, student, vacancy, *, status="Submitted", file_path=None
):
    application = Application(
        student_id=student.id,
        vacancy_id=vacancy.id,
        status=status,
    )
    session.add(application)
    session.commit()
    session.refresh(application)

    if file_path is not None:
        document = Document(
            name=Path(file_path).name,
            file_path=str(file_path),
            type="application/pdf",
            size_bytes=9,
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        session.add(
            ApplicationDocument(
                application_id=application.id,
                document_id=document.id,
            )
        )
        session.commit()
    return application


def login(client, username, password="test-password"):
    response = client.post(
        "/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 303
    return response


def test_register_student(client, db_session):
    response = client.post(
        "/register",
        data={
            "username": "newstudent",
            "email": "newstudent@example.com",
            "password": "student-password",
        },
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")
    user = db_session.exec(select(User).where(User.username == "newstudent")).one()
    assert user.email == "newstudent@example.com"
    assert user.role == ROLE_STUDENT
    assert user.password != "student-password"
    assert user.check_password("student-password")


def test_login(client, db_session):
    user = create_user(
        db_session,
        "loginstudent",
        "loginstudent@example.com",
    )

    response = login(client, user.username)

    assert response.headers["location"].endswith("/app")
    assert "access_token" in response.cookies
    home = client.get("/app")
    assert home.status_code == 200
    assert "Welcome" in home.text


def test_login_invalid_credentials(client, db_session):
    create_user(db_session, "wrongpassword", "wrongpassword@example.com")

    response = client.post(
        "/login",
        data={"username": "wrongpassword", "password": "incorrect"},
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")
    assert "access_token" not in response.cookies
    login_page = client.get("/login")
    assert "Incorrect username or password" in login_page.text


def test_get_all_users_json(client, db_session):
    first = create_user(db_session, "jsonone", "jsonone@example.com")
    second = create_user(db_session, "jsontwo", "jsontwo@example.com")

    response = client.get("/api/users")

    assert response.status_code == 200
    returned_users = response.json()
    assert {
        (user["id"], user["username"], user["email"]) for user in returned_users
    } == {
        (first.id, first.username, first.email),
        (second.id, second.username, second.email),
    }


def test_create_published_vacancy(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    company = create_user(
        db_session,
        "vacancycompany",
        "vacancycompany@example.com",
        role=ROLE_COMPANY,
        company_name="Vacancy Company",
    )
    monkeypatch.setattr(vacancy_service, "UPLOAD_DIRECTORY", tmp_path / "images")
    login(client, company.username)

    response = client.post(
        "/company/vacancies",
        data={
            "title": "  New Engineer  ",
            "description": "  Build useful software  ",
            "location": "  Port of Spain  ",
            "field_of_study": "Technology",
            "status": "Published",
        },
    )

    assert response.status_code == 303
    created = db_session.exec(
        select(InternshipVacancy).where(InternshipVacancy.company_id == company.id)
    ).one()
    assert created.title == "New Engineer"
    assert created.description == "Build useful software"
    assert created.location == "Port of Spain"
    assert created.status == "Published"
    assert created.is_published is True
    page = client.get("/company/vacancies")
    assert "New Engineer" in page.text


def test_create_draft_vacancy_with_image(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    company = create_user(
        db_session,
        "imagecompany",
        "imagecompany@example.com",
        role=ROLE_COMPANY,
        company_name="Image Company",
    )
    image_directory = tmp_path / "images"
    monkeypatch.setattr(vacancy_service, "UPLOAD_DIRECTORY", image_directory)
    login(client, company.username)

    response = client.post(
        "/company/vacancies",
        data={
            "title": "Draft Engineer",
            "description": "A draft role",
            "location": "Remote",
            "field_of_study": "Technology",
            "status": "Draft",
        },
        files={"vacancy_image": ("vacancy.png", b"test-image", "image/png")},
    )

    assert response.status_code == 303
    created = db_session.exec(
        select(InternshipVacancy).where(InternshipVacancy.company_id == company.id)
    ).one()
    assert created.status == "Draft"
    assert created.is_published is False
    assert created.image_url.startswith("/static/uploads/")
    assert len(list(image_directory.iterdir())) == 1


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("vacancy.txt", "text/plain", b"not an image"),
        ("vacancy.png", "image/png", b"x" * (5 * 1024 * 1024 + 1)),
    ],
)
def test_reject_invalid_vacancy_image(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    filename,
    content_type,
    content,
):
    company = create_user(
        db_session,
        "badimagecompany",
        "badimagecompany@example.com",
        role=ROLE_COMPANY,
    )
    image_directory = tmp_path / "images"
    monkeypatch.setattr(vacancy_service, "UPLOAD_DIRECTORY", image_directory)
    login(client, company.username)

    response = client.post(
        "/company/vacancies",
        data={
            "title": "Invalid Image Role",
            "description": "The vacancy should not be created",
            "field_of_study": "Technology",
            "status": "Published",
        },
        files={"vacancy_image": (filename, content, content_type)},
    )

    assert response.status_code == 303
    assert (
        db_session.exec(
            select(InternshipVacancy).where(InternshipVacancy.company_id == company.id)
        ).first()
        is None
    )
    assert not image_directory.exists() or list(image_directory.iterdir()) == []


def test_browse_published_vacancies(client, db_session):
    student = create_user(db_session, "browser", "browser@example.com")
    company = create_user(
        db_session,
        "browsecompany",
        "browsecompany@example.com",
        role=ROLE_COMPANY,
    )
    matching = create_vacancy(
        db_session,
        company,
        title="Technology Analyst",
        description="Build platforms",
    )
    create_vacancy(
        db_session,
        company,
        title="Business Analyst",
        description="Analyze markets",
        field_of_study="Business",
    )
    create_vacancy(
        db_session,
        company,
        title="Hidden Technology Role",
        status="Draft",
    )
    login(client, student.username)

    response = client.get(
        "/internships",
        params=[
            ("q", "Technology"),
            ("field_of_study", "Technology"),
            ("page", "1"),
        ],
    )

    assert response.status_code == 200
    assert matching.title in response.text
    assert "Business Analyst" not in response.text
    assert "Hidden Technology Role" not in response.text


def test_view_published_vacancy_details(
    client,
    db_session,
    student_user,
):
    student = create_user(
        db_session,
        "detailstudent",
        "detailstudent@example.com",
    )
    company = create_user(
        db_session,
        "detailcompany",
        "detailcompany@example.com",
        role=ROLE_COMPANY,
        company_name="Detail Company",
    )
    vacancy = create_vacancy(db_session, company, title="Detail Vacancy")
    create_application(db_session, student, vacancy)
    login(client, student.username)

    response = client.get(f"/internships/{vacancy.id}")

    assert response.status_code == 200
    assert "Detail Vacancy" in response.text
    assert "Detail Company" in response.text
    assert "Application submitted" in response.text


@pytest.mark.parametrize("status", ["Draft", "Closed"])
def test_student_cannot_view_unpublished_vacancy(
    client,
    db_session,
    status,
):
    student = create_user(
        db_session,
        f"hiddenstudent{status.lower()}",
        f"hiddenstudent{status.lower()}@example.com",
    )
    company = create_user(
        db_session,
        f"hiddencompany{status.lower()}",
        f"hiddencompany{status.lower()}@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, status=status)
    login(client, student.username)

    response = client.get(f"/internships/{vacancy.id}")

    assert response.status_code == 303
    assert response.headers["location"].endswith("/internships")
    assert "Hidden Technology Role" not in client.get("/internships").text


def test_apply_with_valid_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "applystudent",
        "applystudent@example.com",
    )
    company = create_user(
        db_session,
        "applycompany",
        "applycompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    upload_directory = tmp_path / "applications"
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)
    content = b"%PDF-1.7\napplication test"

    response = client.post(
        f"/internships/{vacancy.id}/apply",
        data={"page": "1"},
        files={
            "application_document": (
                "resume.pdf",
                content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 303
    application = db_session.exec(
        select(Application).where(
            Application.student_id == student.id,
            Application.vacancy_id == vacancy.id,
        )
    ).one()
    assert application.status == Application.STATUS_SUBMITTED
    link = db_session.exec(
        select(ApplicationDocument).where(
            ApplicationDocument.application_id == application.id
        )
    ).one()
    document = db_session.get(Document, link.document_id)
    assert document.name == "resume.pdf"
    assert document.type == "application/pdf"
    assert document.size_bytes == len(content)
    assert Path(document.file_path).read_bytes() == content


def test_reject_duplicate_application(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "duplicatestudent",
        "duplicatestudent@example.com",
    )
    company = create_user(
        db_session,
        "duplicatecompany",
        "duplicatecompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    create_application(db_session, student, vacancy)
    upload_directory = tmp_path / "applications"
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.post(
        f"/internships/{vacancy.id}/apply",
        files={
            "application_document": (
                "duplicate.pdf",
                b"%PDF-1.7 duplicate",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 303
    assert (
        db_session.exec(
            select(Application).where(
                Application.student_id == student.id,
                Application.vacancy_id == vacancy.id,
            )
        )
        .all()
        .__len__()
        == 1
    )
    assert db_session.exec(select(Document)).all() == []
    assert not upload_directory.exists()


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("resume.docx", b"document"),
        ("resume.pdf", b""),
        ("resume.pdf", b"not a PDF"),
        ("resume.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024 + 1)),
    ],
)
def test_reject_invalid_application_pdf(
    client,
    db_session,
    monkeypatch,
    tmp_path,
    filename,
    content,
):
    student = create_user(
        db_session,
        f"invalidpdf{len(content)}",
        f"invalidpdf{len(content)}@example.com",
    )
    company = create_user(
        db_session,
        f"invalidpdfcompany{len(content)}",
        f"invalidpdfcompany{len(content)}@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    upload_directory = tmp_path / "applications"
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.post(
        f"/internships/{vacancy.id}/apply",
        files={
            "application_document": (
                filename,
                content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 303
    assert (
        db_session.exec(
            select(Application).where(
                Application.student_id == student.id,
                Application.vacancy_id == vacancy.id,
            )
        ).first()
        is None
    )
    assert db_session.exec(select(Document)).first() is None
    assert not upload_directory.exists() or list(upload_directory.iterdir()) == []


def test_list_student_applications(client, db_session):
    student = create_user(
        db_session,
        "ownapplications",
        "ownapplications@example.com",
    )
    other_student = create_user(
        db_session,
        "otherapplications",
        "otherapplications@example.com",
    )
    company = create_user(
        db_session,
        "applicationscompany",
        "applicationscompany@example.com",
        role=ROLE_COMPANY,
    )
    own_vacancy = create_vacancy(
        db_session,
        company,
        title="My Application Vacancy",
    )
    other_vacancy = create_vacancy(
        db_session,
        company,
        title="Other Student Vacancy",
    )
    create_application(db_session, student, own_vacancy)
    create_application(db_session, other_student, other_vacancy)
    login(client, student.username)

    response = client.get("/student/applications")

    assert response.status_code == 200
    assert "My Application Vacancy" in response.text
    assert "Other Student Vacancy" not in response.text


def test_replace_submitted_application_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "replaceowner",
        "replaceowner@example.com",
    )
    company = create_user(
        db_session,
        "replacecompany",
        "replacecompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    upload_directory = tmp_path / "applications"
    upload_directory.mkdir()
    old_file = upload_directory / "old.pdf"
    old_file.write_bytes(b"%PDF-1.4 old")
    application = create_application(
        db_session,
        student,
        vacancy,
        file_path=old_file,
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.post(
        f"/student/applications/{application.id}/edit",
        files={
            "application_document": (
                "replacement.pdf",
                b"%PDF-1.7 replacement",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 303
    assert not old_file.exists()
    refreshed = db_session.get(Application, application.id)
    link = db_session.exec(
        select(ApplicationDocument).where(
            ApplicationDocument.application_id == application.id
        )
    ).one()
    document = db_session.get(Document, link.document_id)
    assert refreshed.status == Application.STATUS_SUBMITTED
    assert document.name == "replacement.pdf"
    assert Path(document.file_path).read_bytes() == b"%PDF-1.7 replacement"


def test_cannot_replace_reviewed_application_document(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "reviewedowner",
        "reviewedowner@example.com",
    )
    company = create_user(
        db_session,
        "reviewedcompany",
        "reviewedcompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    upload_directory = tmp_path / "applications"
    upload_directory.mkdir()
    old_file = upload_directory / "submitted.pdf"
    old_file.write_bytes(b"%PDF-1.4 old")
    application = create_application(
        db_session,
        student,
        vacancy,
        status=Application.STATUS_UNDER_REVIEW,
        file_path=old_file,
    )
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.post(
        f"/student/applications/{application.id}/edit",
        files={
            "application_document": (
                "replacement.pdf",
                b"%PDF-1.7 replacement",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 303
    assert (
        db_session.get(Application, application.id).status
        == Application.STATUS_UNDER_REVIEW
    )
    assert old_file.read_bytes() == b"%PDF-1.4 old"
    assert len(list(upload_directory.iterdir())) == 1


def test_delete_owned_application(
    client,
    db_session,
    monkeypatch,
    tmp_path,
):
    student = create_user(
        db_session,
        "deleteowner",
        "deleteowner@example.com",
    )
    company = create_user(
        db_session,
        "deletecompany",
        "deletecompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    upload_directory = tmp_path / "applications"
    upload_directory.mkdir()
    file_path = upload_directory / "delete.pdf"
    file_path.write_bytes(b"%PDF-1.7")
    application = create_application(
        db_session,
        student,
        vacancy,
        file_path=file_path,
    )
    application_id = application.id
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    login(client, student.username)

    response = client.post(
        f"/student/applications/{application.id}/delete",
        data={"page": "1"},
    )

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.get(Application, application_id) is None
    assert not file_path.exists()
    assert db_session.exec(select(ApplicationDocument)).all() == []
    assert db_session.exec(select(Document)).all() == []


def test_cannot_delete_another_students_application(client, db_session):
    student = create_user(
        db_session,
        "deleteintruder",
        "deleteintruder@example.com",
    )
    owner = create_user(
        db_session,
        "deleteactualowner",
        "deleteactualowner@example.com",
    )
    company = create_user(
        db_session,
        "deleteothercompany",
        "deleteothercompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    application = create_application(db_session, owner, vacancy)
    login(client, student.username)

    response = client.post(
        f"/student/applications/{application.id}/delete",
        data={"page": "1"},
    )

    assert response.status_code == 303
    assert db_session.get(Application, application.id) is not None


def test_company_lists_owned_vacancies(client, db_session):
    company = create_user(
        db_session,
        "listowner",
        "listowner@example.com",
        role=ROLE_COMPANY,
    )
    another_company = create_user(
        db_session,
        "listother",
        "listother@example.com",
        role=ROLE_COMPANY,
    )
    own_vacancy = create_vacancy(db_session, company, title="Owned Vacancy")
    create_vacancy(db_session, another_company, title="Not Owned Vacancy")
    student = create_user(
        db_session,
        "listapplicant",
        "listapplicant@example.com",
    )
    create_application(db_session, student, own_vacancy)
    login(client, company.username)

    response = client.get("/company/vacancies")

    assert response.status_code == 200
    assert "Owned Vacancy" in response.text
    assert "Not Owned Vacancy" not in response.text
    assert "1" in response.text


def test_company_browses_vacancy_applications(client, db_session):
    company = create_user(
        db_session,
        "reviewowner",
        "reviewowner@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company, title="Searchable Role")
    matching_student = create_user(
        db_session,
        "matchingstudent",
        "matchingstudent@example.com",
        first_name="Taylor",
        last_name="Candidate",
        education_level="Undergraduate",
    )
    other_student = create_user(
        db_session,
        "unmatchingstudent",
        "unmatchingstudent@example.com",
        first_name="Morgan",
        last_name="Candidate",
        education_level="Diploma",
    )
    create_application(db_session, matching_student, vacancy)
    create_application(db_session, other_student, vacancy)
    login(client, company.username)

    response = client.get(
        f"/company/vacancies/{vacancy.id}/applications",
        params={
            "q": "Taylor",
            "education_level": "Undergraduate",
            "status_sort": "Shortlisted",
            "page": "1",
        },
    )

    assert response.status_code == 200
    assert "Taylor Candidate" in response.text
    assert "Morgan Candidate" not in response.text


def test_company_cannot_review_another_company_vacancy(client, db_session):
    requester = create_user(
        db_session,
        "requestercompany",
        "requestercompany@example.com",
        role=ROLE_COMPANY,
    )
    owner = create_user(
        db_session,
        "actualcompany",
        "actualcompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, owner)
    student = create_user(
        db_session,
        "privateapplicant",
        "privateapplicant@example.com",
    )
    create_application(db_session, student, vacancy)
    login(client, requester.username)

    response = client.get(
        f"/company/vacancies/{vacancy.id}/applications",
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/company/vacancies")
    assert "privateapplicant" not in response.text


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("shortlist", Application.STATUS_SHORTLISTED),
        ("reject", Application.STATUS_REJECTED),
    ],
)
def test_company_updates_application_review_status(
    client,
    db_session,
    action,
    expected_status,
):
    company = create_user(
        db_session,
        f"statuscompany{action}",
        f"statuscompany{action}@example.com",
        role=ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        f"statusstudent{action}",
        f"statusstudent{action}@example.com",
    )
    vacancy = create_vacancy(db_session, company)
    application = create_application(db_session, student, vacancy)
    login(client, company.username)

    response = client.post(
        f"/company/vacancies/{vacancy.id}/applications/{application.id}/{action}",
    )

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.get(Application, application.id).status == expected_status


def test_company_finishes_review(client, db_session):
    company = create_user(
        db_session,
        "finishcompany",
        "finishcompany@example.com",
        role=ROLE_COMPANY,
    )
    vacancy = create_vacancy(db_session, company)
    under_review = create_user(
        db_session,
        "underreviewstudent",
        "underreviewstudent@example.com",
    )
    shortlisted = create_user(
        db_session,
        "shortlistedstudent",
        "shortlistedstudent@example.com",
    )
    rejected = create_user(
        db_session,
        "rejectedstudent",
        "rejectedstudent@example.com",
    )
    pending = create_application(
        db_session,
        under_review,
        vacancy,
        status=Application.STATUS_UNDER_REVIEW,
    )
    selected = create_application(
        db_session,
        shortlisted,
        vacancy,
        status=Application.STATUS_SHORTLISTED,
    )
    declined = create_application(
        db_session,
        rejected,
        vacancy,
        status=Application.STATUS_REJECTED,
    )
    login(client, company.username)

    response = client.post(
        f"/company/vacancies/{vacancy.id}/applications/finish-review",
    )

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.get(Application, pending.id).status == Application.STATUS_REJECTED
    assert (
        db_session.get(Application, selected.id).status
        == Application.STATUS_SHORTLISTED
    )
    assert (
        db_session.get(Application, declined.id).status == Application.STATUS_REJECTED
    )


def test_closing_vacancy_updates_application_statuses(client, db_session):
    company = create_user(
        db_session,
        "closingcompany",
        "closingcompany@example.com",
        role=ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "closingstudent",
        "closingstudent@example.com",
    )
    vacancy = create_vacancy(db_session, company)
    application = create_application(db_session, student, vacancy)
    login(client, company.username)

    response = client.post(
        f"/company/vacancies/{vacancy.id}",
        data={
            "title": vacancy.title,
            "description": vacancy.description,
            "location": vacancy.location,
            "field_of_study": vacancy.field_of_study,
            "status": "Closed",
        },
    )

    assert response.status_code == 303
    db_session.expire_all()
    assert db_session.get(InternshipVacancy, vacancy.id).status == "Closed"
    assert db_session.get(InternshipVacancy, vacancy.id).is_published is False
    assert (
        db_session.get(Application, application.id).status
        == Application.STATUS_UNDER_REVIEW
    )


def test_published_vacancy_with_applicants_cannot_become_draft(
    client,
    db_session,
):
    company = create_user(
        db_session,
        "draftblockedcompany",
        "draftblockedcompany@example.com",
        role=ROLE_COMPANY,
    )
    student = create_user(
        db_session,
        "draftblockedstudent",
        "draftblockedstudent@example.com",
    )
    vacancy = create_vacancy(db_session, company)
    create_application(db_session, student, vacancy)
    login(client, company.username)

    response = client.post(
        f"/company/vacancies/{vacancy.id}",
        data={
            "title": "Updated title",
            "description": vacancy.description,
            "location": vacancy.location,
            "field_of_study": vacancy.field_of_study,
            "status": "Draft",
        },
    )

    assert response.status_code == 303
    db_session.expire_all()
    updated = db_session.get(InternshipVacancy, vacancy.id)
    assert updated.title == "Updated title"
    assert updated.status == "Published"
    assert updated.is_published is True


def test_update_student_profile(client, db_session):
    student = create_user(
        db_session,
        "profile_student",
        "before-student@example.com",
    )
    login(client, student.username)

    response = client.post(
        "/student/profile",
        data={
            "first_name": "Avery",
            "last_name": "Student",
            "email": "avery@example.com",
            "education_level": "Undergraduate",
        },
    )

    assert response.status_code == 303
    db_session.expire_all()
    updated = db_session.get(User, student.id)
    assert updated.first_name == "Avery"
    assert updated.last_name == "Student"
    assert updated.email == "avery@example.com"
    assert updated.education_level == "Undergraduate"


def test_update_company_profile(client, db_session):
    company = create_user(
        db_session,
        "profile_company",
        "before-company@example.com",
        role=ROLE_COMPANY,
        company_name="Old Company",
    )
    login(client, company.username)

    response = client.post(
        "/company/profile",
        data={
            "company_name": "Updated Company",
            "email": "updated-company@example.com",
            "phone": "555-0123",
            "location": "Port of Spain",
        },
    )

    assert response.status_code == 303
    db_session.expire_all()
    updated = db_session.get(User, company.id)
    assert updated.company_name == "Updated Company"
    assert updated.email == "updated-company@example.com"
    assert updated.phone == "555-0123"
    assert updated.location == "Port of Spain"


def test_student_cannot_use_company_review_action(
    client,
    db_session,
):
    student = create_user(
        db_session,
        "reviewactionstudent",
        "reviewactionstudent@example.com",
    )
    company = create_user(
        db_session,
        "reviewactioncompany",
        "reviewactioncompany@example.com",
        role=ROLE_COMPANY,
    )
    applicant = create_user(
        db_session,
        "reviewactionapplicant",
        "reviewactionapplicant@example.com",
    )
    vacancy = create_vacancy(db_session, company)
    application = create_application(db_session, applicant, vacancy)
    login(client, student.username)

    response = client.post(
        f"/company/vacancies/{vacancy.id}/applications/{application.id}/shortlist",
    )

    assert response.status_code == 303
    assert (
        db_session.get(Application, application.id).status
        == Application.STATUS_SUBMITTED
    )


def test_logout_clears_session(client, db_session):
    user = create_user(
        db_session,
        "logoutstudent",
        "logoutstudent@example.com",
    )
    login(client, user.username)
    assert "access_token" in client.cookies

    response = client.get("/logout")

    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")
    assert "access_token" not in client.cookies
    protected = client.get("/student/applications")
    assert "401" in protected.text
    assert "Unauthorized" in protected.text
