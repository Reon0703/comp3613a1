from unittest.mock import Mock

from pwdlib import PasswordHash

from app.models.user import ROLE_STUDENT, User
from app.services import auth_service
from app.services.auth_service import AuthService


def test_check_password():
    plaintext = "my-password"
    user = User(
        username="bob",
        email="bob@example.com",
        password=PasswordHash.recommended().hash(plaintext),
    )

    assert user.check_password(plaintext) is True
    assert user.password != plaintext


def test_check_password_wrong_value():
    user = User(
        username="bob",
        email="bob@example.com",
        password=PasswordHash.recommended().hash("my-password"),
    )

    assert user.check_password("wrong-password") is False


def test_authenticate_user_success(monkeypatch):
    user = User(
        id=41,
        username="bob",
        email="bob@example.com",
        password=PasswordHash.recommended().hash("my-password"),
        role=ROLE_STUDENT,
    )
    repository = Mock()
    repository.get_by_username.return_value = user
    token_factory = Mock(return_value="signed-token")
    monkeypatch.setattr(auth_service, "create_access_token", token_factory)

    token = AuthService(repository).authenticate_user("bob", "my-password")

    assert token == "signed-token"
    token_factory.assert_called_once_with(data={"sub": "41", "role": ROLE_STUDENT})


def test_authenticate_user_invalid_password():
    user = User(
        id=41,
        username="bob",
        email="bob@example.com",
        password=PasswordHash.recommended().hash("my-password"),
        role=ROLE_STUDENT,
    )
    repository = Mock()
    repository.get_by_username.return_value = user

    assert AuthService(repository).authenticate_user("bob", "wrong") is None


def test_authenticate_user_unknown_username():
    repository = Mock()
    repository.get_by_username.return_value = None

    assert AuthService(repository).authenticate_user("missing", "password") is None
