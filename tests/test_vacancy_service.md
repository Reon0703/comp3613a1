from unittest.mock import Mock

import pytest

from app.models.application import Application
from app.services.vacancy_service import VacancyService


def test_create_vacancy_trims_fields():
    repository = Mock()
    repository.create.side_effect = lambda vacancy: vacancy

    created = VacancyService(repository).create_vacancy(
        company_id=7,
        title="  Summer Intern  ",
        description="  Assist the team  ",
        location="  Port of Spain  ",
        field_of_study="Technology",
        status="Published",
    )

    saved = repository.create.call_args.args[0]
    assert created is saved
    assert saved.title == "Summer Intern"
    assert saved.description == "Assist the team"
    assert saved.location == "Port of Spain"
    assert saved.status == "Published"
    assert saved.is_published is True


def test_create_vacancy_defaults_to_draft():
    repository = Mock()
    repository.create.side_effect = lambda vacancy: vacancy

    created = VacancyService(repository).create_vacancy(
        company_id=7,
        title="Summer Intern",
        description="Assist the team",
        location="Port of Spain",
        field_of_study="Technology",
    )

    assert created.status == "Draft"
    assert created.is_published is False


def test_create_vacancy_rejects_empty_title():
    repository = Mock()

    with pytest.raises(ValueError, match="Vacancy title is required"):
        VacancyService(repository).create_vacancy(
            company_id=7,
            title="   ",
            description="Assist the team",
            location="Port of Spain",
            field_of_study="Technology",
        )

    repository.create.assert_not_called()


def test_create_vacancy_rejects_empty_description():
    repository = Mock()

    with pytest.raises(ValueError, match="Vacancy description is required"):
        VacancyService(repository).create_vacancy(
            company_id=7,
            title="Summer Intern",
            description="",
            location="Port of Spain",
            field_of_study="Technology",
        )

    repository.create.assert_not_called()


def test_create_vacancy_rejects_unsupported_field():
    repository = Mock()

    with pytest.raises(ValueError, match="Choose a valid field of study"):
        VacancyService(repository).create_vacancy(
            company_id=7,
            title="Summer Intern",
            description="Assist the team",
            location="Port of Spain",
            field_of_study="Underwater Basketry",
        )

    repository.create.assert_not_called()


def test_create_vacancy_rejects_invalid_status():
    repository = Mock()

    with pytest.raises(ValueError, match="Choose Published, Closed, or Draft"):
        VacancyService(repository).create_vacancy(
            company_id=7,
            title="Summer Intern",
            description="Assist the team",
            location="Port of Spain",
            field_of_study="Technology",
            status="Archived",
        )

    repository.create.assert_not_called()


def test_update_vacancy_rejects_non_owner(vacancy):
    repository = Mock()
    repository.get_by_id.return_value = vacancy

    with pytest.raises(ValueError, match="Vacancy not found"):
        VacancyService(repository).update_vacancy(
            vacancy_id=vacancy.id,
            company_id=999,
            title=vacancy.title,
            description=vacancy.description,
            location=vacancy.location,
            status="Closed",
        )

    repository.update.assert_not_called()


def test_update_published_vacancy_with_applicants_cannot_become_draft(vacancy):
    repository = Mock()
    repository.get_by_id.return_value = vacancy
    repository.has_applications.return_value = True
    repository.update.side_effect = lambda item, **kwargs: item

    result = VacancyService(repository).update_vacancy(
        vacancy_id=vacancy.id,
        company_id=vacancy.company_id,
        title=vacancy.title,
        description=vacancy.description,
        location=vacancy.location,
        status="Draft",
        field_of_study=vacancy.field_of_study,
    )

    assert result.draft_status_blocked is True
    assert result.vacancy.status == "Published"
    assert result.vacancy.is_published is True


def test_closing_vacancy_moves_applications_under_review(vacancy):
    repository = Mock()
    repository.get_by_id.return_value = vacancy
    repository.update.side_effect = lambda item, **kwargs: item

    result = VacancyService(repository).update_vacancy(
        vacancy_id=vacancy.id,
        company_id=vacancy.company_id,
        title=vacancy.title,
        description=vacancy.description,
        location=vacancy.location,
        status="Closed",
        field_of_study=vacancy.field_of_study,
    )

    assert result.vacancy.status == "Closed"
    assert result.vacancy.is_published is False
    repository.update.assert_called_once_with(
        vacancy,
        application_status=Application.STATUS_UNDER_REVIEW,
    )
