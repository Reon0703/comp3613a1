from unittest.mock import Mock

import pytest

from app.models.user import ROLE_COMPANY
from app.schemas.user import StudentProfileUpdate, UserProfileUpdate
from app.services.user_service import UserService


def test_update_company_profile_requires_company_name():
    repository = Mock()
    profile = UserProfileUpdate(
        company_name="   ",
        email="company@example.com",
    )

    with pytest.raises(ValueError, match="Company name is required"):
        UserService(repository).update_profile(201, profile)

    repository.update_profile.assert_not_called()


@pytest.mark.parametrize(
    "account",
    [
        None,
        "company",
    ],
)
def test_update_student_profile_requires_student_account(
    account, student_user, company_user
):
    repository = Mock()
    repository.get_by_id.return_value = None if account is None else company_user
    profile = StudentProfileUpdate(
        first_name="Sam",
        last_name="Student",
        email="student@example.com",
    )

    with pytest.raises(ValueError, match="Student profile not found"):
        UserService(repository).update_student_profile(101, profile)

    repository.update_student_profile.assert_not_called()
    assert company_user.role == ROLE_COMPANY


@pytest.mark.parametrize(
    ("first_name", "last_name"),
    [
        (" ", "Student"),
        ("Sam", " "),
    ],
)
def test_update_student_profile_requires_first_and_last_name(
    first_name,
    last_name,
    student_user,
):
    repository = Mock()
    repository.get_by_id.return_value = student_user
    profile = StudentProfileUpdate(
        first_name=first_name,
        last_name=last_name,
        email="student@example.com",
    )

    with pytest.raises(ValueError, match="First and last name are required"):
        UserService(repository).update_student_profile(student_user.id, profile)

    repository.update_student_profile.assert_not_called()
