import pytest
from sqlmodel import select

from app.models.user import ROLE_COMPANY, ROLE_STUDENT, User


def test_register_page_offers_student_and_company_options(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert 'value="regular_user">Student</option>' in response.text
    assert 'value="company">Company</option>' in response.text


@pytest.mark.parametrize(
    ("username", "role"),
    [
        ("web_student", ROLE_STUDENT),
        ("web_company", ROLE_COMPANY),
    ],
)
def test_web_registration_creates_selected_account_type(
    client,
    db_session,
    username,
    role,
):
    response = client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@example.com",
            "password": "company-password",
            "role": role,
        },
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")
    created = db_session.exec(
        select(User).where(User.username == username)
    ).one()
    assert created.role == role
    assert created.check_password("company-password")


def test_web_registration_rejects_unknown_role(client):
    response = client.post(
        "/register",
        data={
            "username": "invalid_role",
            "email": "invalid_role@example.com",
            "password": "test-password",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_api_registration_creates_company_account(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "api_company",
            "email": "api_company@example.com",
            "password": "company-password",
            "role": ROLE_COMPANY,
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["role"] == ROLE_COMPANY
    created = db_session.exec(
        select(User).where(User.username == "api_company")
    ).one()
    assert created.role == ROLE_COMPANY


def test_api_registration_rejects_admin_role(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "api_admin",
            "email": "api_admin@example.com",
            "password": "admin-password",
            "role": "admin",
        },
    )

    assert response.status_code == 422
