from pathlib import Path
from dataclasses import dataclass
from uuid import uuid4

from app.models.application import Application
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
            raise ValueError("Choose Published, Closed, or Draft as the vacancy status.")

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
            raise ValueError("Vacancy not found.")

        was_closed = vacancy.status == "Closed"
        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        cleaned_field_of_study = (field_of_study or "").strip()
        cleaned_status = (status or "Draft").strip().title()
        if not cleaned_title:
            raise ValueError("Vacancy title is required.")
        if not cleaned_description:
            raise ValueError("Vacancy description is required.")
        if cleaned_field_of_study and cleaned_field_of_study not in FIELD_OF_STUDY_OPTIONS:
            raise ValueError("Choose a valid field of study.")
        if cleaned_status not in VACANCY_STATUSES:
            raise ValueError("Choose Published, Closed, or Draft as the vacancy status.")

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
