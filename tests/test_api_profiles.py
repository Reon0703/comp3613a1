import pytest
from sqlmodel import select

from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User
from app.utilities.security import encrypt_password

PASSWORD = "profile-test-password"


def create_user(db_session, username: str, email: str, role: str) -> User:
    user = User(
        username=username,
        email=email,
        password=encrypt_password(PASSWORD),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client, username: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200


def test_student_can_update_profile_through_json_api(client, db_session):
    student = create_user(
        db_session,
        "api_profile_student",
        "api-profile-student@example.com",
        ROLE_STUDENT,
    )
    login(client, student.username)

    response = client.put(
        "/api/students/me",
        json={
            "first_name": "Avery",
            "last_name": "Student",
            "email": "avery-api@example.com",
            "education_level": "Undergraduate",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "student profile updated"}
    db_session.expire_all()
    updated = db_session.exec(select(User).where(User.id == student.id)).one()
    assert updated.first_name == "Avery"
    assert updated.last_name == "Student"
    assert updated.email == "avery-api@example.com"
    assert updated.education_level == "Undergraduate"


def test_company_can_update_profile_through_json_api(client, db_session):
    company = create_user(
        db_session,
        "api_profile_company",
        "api-profile-company@example.com",
        ROLE_COMPANY,
    )
    login(client, company.username)

    response = client.put(
        "/api/companies/me",
        json={
            "company_name": "Updated API Company",
            "email": "postman-company@example.com",
            "phone": "555-0123",
            "location": "Port of Spain",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "company profile updated"}
    db_session.expire_all()
    updated = db_session.exec(select(User).where(User.id == company.id)).one()
    assert updated.company_name == "Updated API Company"
    assert updated.email == "postman-company@example.com"
    assert updated.phone == "555-0123"
    assert updated.location == "Port of Spain"


def test_profile_apis_reject_wrong_account_roles(client, db_session):
    student = create_user(
        db_session,
        "api_wrong_role_student",
        "api-wrong-role-student@example.com",
        ROLE_STUDENT,
    )
    company = create_user(
        db_session,
        "api_wrong_role_company",
        "api-wrong-role-company@example.com",
        ROLE_COMPANY,
    )

    login(client, company.username)
    student_profile_response = client.put(
        "/api/students/me",
        json={
            "first_name": "Wrong",
            "last_name": "Role",
            "email": student.email,
        },
    )
    assert student_profile_response.status_code == 403
    assert student_profile_response.json() == {"detail": "Student profile not found."}

    login(client, student.username)
    company_profile_response = client.put(
        "/api/companies/me",
        json={
            "company_name": "Wrong Role",
            "email": company.email,
        },
    )
    assert company_profile_response.status_code == 403
    assert company_profile_response.json() == {"detail": "Company profile not found."}


@pytest.mark.parametrize(
    ("role", "path", "payload", "detail"),
    [
        (
            ROLE_STUDENT,
            "/api/students/me",
            {
                "first_name": " ",
                "last_name": "Student",
                "email": "invalid-profile-name@example.com",
            },
            "First and last name are required.",
        ),
        (
            ROLE_COMPANY,
            "/api/companies/me",
            {
                "company_name": " ",
                "email": "invalid-company-name@example.com",
            },
            "Company name is required.",
        ),
    ],
)
def test_profile_apis_reject_invalid_profile_fields(
    client,
    db_session,
    role,
    path,
    payload,
    detail,
):
    user = create_user(
        db_session,
        f"api_invalid_profile_{role}",
        f"api-invalid-profile-{role}@example.com",
        role,
    )
    login(client, user.username)

    response = client.put(path, json=payload)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_profile_apis_reject_duplicate_email(client, db_session):
    student = create_user(
        db_session,
        "api_duplicate_email_student",
        "api-duplicate-email-student@example.com",
        ROLE_STUDENT,
    )
    create_user(
        db_session,
        "api_duplicate_email_owner",
        "email-already-used@example.com",
        ROLE_STUDENT,
    )
    login(client, student.username)

    response = client.put(
        "/api/students/me",
        json={
            "first_name": "Duplicate",
            "last_name": "Email",
            "email": "email-already-used@example.com",
            "education_level": "Undergraduate",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already exists"}


@pytest.mark.parametrize("path", ["/api/students/me", "/api/companies/me"])
def test_profile_apis_require_authentication_and_return_json(client, path):
    response = client.put(path, json={})

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
