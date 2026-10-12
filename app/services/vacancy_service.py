from pathlib import Path
from uuid import uuid4

from app.models.vacancy import InternshipVacancy


UPLOAD_DIRECTORY = Path("app/static/uploads")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
VACANCY_STATUSES = {"Published", "Closed", "Draft"}


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
        image_url: str | None = None,
        status: str = "Draft",
    ) -> InternshipVacancy:
        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        cleaned_location = (location or "").strip()
        cleaned_status = (status or "Draft").strip().title()

        if not cleaned_title:
            raise ValueError("Vacancy title is required.")
        if not cleaned_description:
            raise ValueError("Vacancy description is required.")
        if cleaned_status not in VACANCY_STATUSES:
            raise ValueError("Choose Published, Closed, or Draft as the vacancy status.")

        vacancy = InternshipVacancy(
            company_id=company_id,
            title=cleaned_title,
            description=cleaned_description,
            location=cleaned_location,
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
        image_url: str | None = None,
    ) -> InternshipVacancy:
        vacancy = self.vacancy_repo.get_by_id(vacancy_id)
        if not vacancy or vacancy.company_id != company_id:
            raise ValueError("Vacancy not found.")

        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        cleaned_status = (status or "Draft").strip().title()
        if not cleaned_title:
            raise ValueError("Vacancy title is required.")
        if not cleaned_description:
            raise ValueError("Vacancy description is required.")
        if cleaned_status not in VACANCY_STATUSES:
            raise ValueError("Choose Published, Closed, or Draft as the vacancy status.")

        vacancy.title = cleaned_title
        vacancy.description = cleaned_description
        vacancy.location = (location or "").strip()
        vacancy.status = cleaned_status
        vacancy.is_published = cleaned_status == "Published"
        if image_url:
            vacancy.image_url = image_url
        return self.vacancy_repo.update(vacancy)
