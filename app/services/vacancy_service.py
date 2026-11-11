from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.models.application import Application
from app.models.user import User
from app.models.vacancy import FIELD_OF_STUDY_OPTIONS, InternshipVacancy

UPLOAD_DIRECTORY = Path("app/static/uploads")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
VACANCY_STATUSES = {"Published", "Closed", "Draft"}


@dataclass
class VacancyUpdateResult:
    vacancy: InternshipVacancy
    draft_status_blocked: bool


class VacancyAccessError(ValueError):
    """The authenticated user cannot manage company vacancies."""


class VacancyNotFoundError(ValueError):
    """The vacancy is unavailable to the requested company."""


class VacancyService:
    def __init__(self, vacancy_repo):
        self.vacancy_repo = vacancy_repo

    def save_image(self, content: bytes, content_type: str | None) -> str:
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Upload a JPG, PNG, or WEBP image.")
        if len(content) > MAX_IMAGE_SIZE:
            raise ValueError("Images must be 5 MB or smaller.")

        UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}{ALLOWED_IMAGE_TYPES[content_type]}"
        (UPLOAD_DIRECTORY / filename).write_bytes(content)
        return f"/static/uploads/{filename}"

    def create_vacancy(
        self,
        company_id: int,
        title: str,
        description: str,
        location: str,
        field_of_study: str,
        image_url: str | None = None,
        status: str = "Draft",
    ) -> InternshipVacancy:
        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        cleaned_location = (location or "").strip()
        cleaned_field_of_study = (field_of_study or "").strip()
        cleaned_status = (status or "Draft").strip().title()

        if not cleaned_title:
            raise ValueError("Vacancy title is required.")
        if not cleaned_description:
            raise ValueError("Vacancy description is required.")
        if cleaned_field_of_study not in FIELD_OF_STUDY_OPTIONS:
            raise ValueError("Choose a valid field of study.")
        if cleaned_status not in VACANCY_STATUSES:
            raise ValueError(
                "Choose Published, Closed, or Draft as the vacancy status."
            )

        vacancy = InternshipVacancy(
            company_id=company_id,
            title=cleaned_title,
            description=cleaned_description,
            location=cleaned_location,
            field_of_study=cleaned_field_of_study,
            status=cleaned_status,
            is_published=cleaned_status == "Published",
            image_url=image_url,
        )
        return self.vacancy_repo.create(vacancy)

    def list_company_vacancies(self, company_id: int):
        return self.vacancy_repo.list_by_company(company_id)

    def list_company_vacancies_with_counts(
        self,
        user: User,
    ) -> list[tuple[InternshipVacancy, int]]:
        if not user.is_company:
            raise VacancyAccessError("Only company accounts can view vacancies.")
        return self.vacancy_repo.list_company_vacancies_with_counts(user.id)

    def create_company_vacancy(
        self,
        user: User,
        title: str,
        description: str,
        location: str,
        field_of_study: str,
        status: str,
        image_content: bytes | None = None,
        image_content_type: str | None = None,
    ) -> InternshipVacancy:
        if not user.is_company:
            raise VacancyAccessError("Only company accounts can create vacancies.")
        image_url = (
            self.save_image(image_content, image_content_type)
            if image_content is not None
            else None
        )
        return self.create_vacancy(
            company_id=user.id,
            title=title,
            description=description,
            location=location,
            field_of_study=field_of_study,
            image_url=image_url,
            status=status,
        )

    def update_company_vacancy(
        self,
        user: User,
        vacancy_id: int,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
        status: str | None = None,
        field_of_study: str | None = None,
        image_content: bytes | None = None,
        image_content_type: str | None = None,
    ) -> VacancyUpdateResult:
        if not user.is_company:
            raise VacancyAccessError("Only company accounts can update vacancies.")

        vacancy = self.vacancy_repo.get_by_id(vacancy_id)
        if not vacancy or vacancy.company_id != user.id:
            raise VacancyNotFoundError("Vacancy not found.")

        image_url = (
            self.save_image(image_content, image_content_type)
            if image_content is not None
            else None
        )
        return self.update_vacancy(
            vacancy_id=vacancy_id,
            company_id=user.id,
            title=vacancy.title if title is None else title,
            description=vacancy.description if description is None else description,
            location=vacancy.location if location is None else location,
            status=vacancy.status if status is None else status,
            field_of_study=field_of_study,
            image_url=image_url,
        )

    def update_vacancy(
        self,
        vacancy_id: int,
        company_id: int,
        title: str,
        description: str,
        location: str,
        status: str,
        field_of_study: str | None = None,
        image_url: str | None = None,
    ) -> VacancyUpdateResult:
        vacancy = self.vacancy_repo.get_by_id(vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise VacancyNotFoundError("Vacancy not found.")

        was_closed = vacancy.status == "Closed"
        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        cleaned_field_of_study = (field_of_study or "").strip()
        cleaned_status = (status or "Draft").strip().title()
        if not cleaned_title:
            raise ValueError("Vacancy title is required.")
        if not cleaned_description:
            raise ValueError("Vacancy description is required.")
        if (
            cleaned_field_of_study
            and cleaned_field_of_study not in FIELD_OF_STUDY_OPTIONS
        ):
            raise ValueError("Choose a valid field of study.")
        if cleaned_status not in VACANCY_STATUSES:
            raise ValueError(
                "Choose Published, Closed, or Draft as the vacancy status."
            )

        draft_status_blocked = (
            vacancy.status == "Published"
            and cleaned_status == "Draft"
            and self.vacancy_repo.has_applications(vacancy_id)
        )
        if draft_status_blocked:
            cleaned_status = vacancy.status

        vacancy.title = cleaned_title
        vacancy.description = cleaned_description
        vacancy.location = (location or "").strip()
        if cleaned_field_of_study:
            vacancy.field_of_study = cleaned_field_of_study
        vacancy.status = cleaned_status
        vacancy.is_published = cleaned_status == "Published"
        if image_url:
            vacancy.image_url = image_url
        application_status = (
            Application.STATUS_UNDER_REVIEW
            if cleaned_status == "Closed" and not was_closed
            else None
        )
        updated_vacancy = self.vacancy_repo.update(
            vacancy,
            application_status=application_status,
        )
        return VacancyUpdateResult(
            vacancy=updated_vacancy,
            draft_status_blocked=draft_status_blocked,
        )
