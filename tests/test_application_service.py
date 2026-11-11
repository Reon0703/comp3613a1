from unittest.mock import Mock

import pytest

from app.models.application import Application
from app.services.application_service import ApplicationService


def test_list_student_applications_rejects_company_user(company_user):
    repository = Mock()

    with pytest.raises(
        ValueError, match="Only student accounts can view their applications"
    ):
        ApplicationService(repository).list_for_student(company_user)

    repository.list_for_student.assert_not_called()


def test_browse_applications_rejects_non_owner(company_user):
    repository = Mock()
    repository.get_owned_vacancy.return_value = None

    with pytest.raises(ValueError, match="Vacancy not found"):
        ApplicationService(repository).browse(company_user, vacancy_id=12)

    repository.list_for_vacancy.assert_not_called()


def test_browse_applications_ignores_unsupported_filters(company_user, vacancy):
    repository = Mock()
    repository.get_owned_vacancy.return_value = vacancy
    repository.list_for_vacancy.return_value = ([], Mock())

    result = ApplicationService(repository).browse(
        company_user,
        vacancy_id=vacancy.id,
        education_level="Unrecognized level",
        status_sort="Unrecognized status",
    )

    assert result.education_level is None
    assert result.status_sort is None
    repository.list_for_vacancy.assert_called_once_with(
        vacancy_id=vacancy.id,
        query=None,
        education_level=None,
        status_sort=None,
        page=1,
    )


@pytest.mark.parametrize(
    ("method_name", "expected_status"),
    [
        ("shortlist", Application.STATUS_SHORTLISTED),
        ("reject", Application.STATUS_REJECTED),
    ],
)
def test_application_review_status_change(
    method_name,
    expected_status,
    company_user,
    vacancy,
    application,
):
    repository = Mock()
    repository.get_owned_vacancy.return_value = vacancy
    repository.get_for_vacancy.return_value = application
    repository.save.side_effect = lambda item: item

    result = getattr(ApplicationService(repository), method_name)(
        company_user,
        vacancy_id=vacancy.id,
        application_id=application.id,
    )

    assert result.status == expected_status
    repository.save.assert_called_once_with(application)


def test_finish_review_rejects_only_under_review_applications(company_user, vacancy):
    repository = Mock()
    repository.get_owned_vacancy.return_value = vacancy
    repository.finish_review_for_vacancy.return_value = 1

    updated_count = ApplicationService(repository).finish_review(
        company_user,
        vacancy_id=vacancy.id,
    )

    assert updated_count == 1
    repository.finish_review_for_vacancy.assert_called_once_with(vacancy.id)
