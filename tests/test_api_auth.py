import pytest
from sqlmodel import select

from app.models.user import ROLE_STUDENT, User
from app.utilities.security import encrypt_password


def test_api_register_student(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "api_student",
            "email": "api_student@example.com",
            "password": "student-password",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "account created"
    assert body["user"]["username"] == "api_student"
    assert body["user"]["email"] == "api_student@example.com"
    assert body["user"]["role"] == ROLE_STUDENT
    assert "password" not in body["user"]

    created = db_session.exec(select(User).where(User.username == "api_student")).one()
    assert created.check_password("student-password")
    assert created.password != "student-password"


@pytest.mark.parametrize(
    ("username", "email"),
    [
        ("existing_api_user", "new_api_email@example.com"),
        ("new_api_user", "existing_api_email@example.com"),
    ],
)
def test_api_register_rejects_duplicate_username_or_email(
    client,
    db_session,
    username,
    email,
):
    db_session.add(
        User(
            username="existing_api_user",
            email="existing_api_email@example.com",
            password="already-hashed",
            role=ROLE_STUDENT,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "student-password",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Username or email already exists"}


def test_api_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "invalid_email_user",
            "email": "not-an-email",
            "password": "student-password",
        },
    )

    assert response.status_code == 422


def test_api_login_sets_cookie_and_returns_public_user_fields(
    client,
    db_session,
):
    user = User(
        username="api_login_user",
        email="api_login@example.com",
        password=encrypt_password("student-password"),
        role=ROLE_STUDENT,
        first_name="Api",
        last_name="User",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": user.username,
            "password": "student-password",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == user.username
    assert response.json()["user"]["role"] == ROLE_STUDENT
    assert "password" not in response.json()["user"]
    assert "access_token" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_api_login_rejects_invalid_credentials_as_json(
    client,
    db_session,
):
    db_session.add(
        User(
            username="api_wrong_password",
            email="api_wrong_password@example.com",
            password=encrypt_password("different-valid-password"),
            role=ROLE_STUDENT,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "api_wrong_password",
            "password": "wrong",
        },
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Incorrect username or password"}


def test_api_get_current_user_returns_authenticated_profile(
    client,
    db_session,
):
    user = User(
        username="api_me_user",
        email="api_me@example.com",
        password=encrypt_password("student-password"),
        role=ROLE_STUDENT,
        first_name="Api",
        last_name="Me",
        education_level="Undergraduate",
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "student-password"},
    )
    assert login_response.status_code == 200

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["username"] == user.username
    assert response.json()["role"] == ROLE_STUDENT
    assert response.json()["first_name"] == "Api"
    assert response.json()["last_name"] == "Me"
    assert response.json()["education_level"] == "Undergraduate"
    assert "password" not in response.json()


def test_api_get_current_user_returns_json_401_without_cookie(client):
    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Could not validate credentials"}


def test_api_logout_clears_cookie_and_web_login_route_still_works(
    client,
    db_session,
):
    user = User(
        username="api_logout_user",
        email="api_logout@example.com",
        password=encrypt_password("student-password"),
        role=ROLE_STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "student-password"},
    )
    assert login_response.status_code == 200
    assert "access_token" in client.cookies

    logout_response = client.post("/api/auth/logout")

    assert logout_response.status_code == 204
    assert logout_response.text == ""
    assert "access_token" not in client.cookies
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()

    web_login_response = client.post(
        "/login",
        data={"username": user.username, "password": "student-password"},
    )
    assert web_login_response.status_code == 303
    assert web_login_response.headers["location"].endswith("/app")
