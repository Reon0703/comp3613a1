from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from app.models.user import User
from app.repositories.application import ApplicationRepository
from app.repositories.internship import InternshipRepository
from app.utilities.pagination import Pagination

APPLICATION_UPLOAD_DIRECTORY = Path("app/uploads/applications")
MAX_APPLICATION_DOCUMENT_SIZE = 10 * 1024 * 1024


@dataclass
class InternshipBrowseResult:
    vacancies: list
    pagination: Pagination
    query: str | None = None
    applied_vacancy_ids: set[int] | None = None


class InternshipService:
    def __init__(
        self,
        internship_repo: InternshipRepository,
        application_repo: ApplicationRepository,
    ):
        self.internship_repo = internship_repo
        self.application_repo = application_repo

    def browse(
        self,
        user: User,
        query: str | None = None,
        page: int = 1,
    ) -> InternshipBrowseResult:
        if not user.is_student:
            raise ValueError("Only student accounts can browse internships.")

        vacancies, pagination = self.internship_repo.browse_published(
            query=query,
            page=page,
        )
        applied_vacancy_ids = self.application_repo.list_vacancy_ids_for_student(
            user.id
        )
        return InternshipBrowseResult(
            vacancies=vacancies,
            pagination=pagination,
            query=query,
            applied_vacancy_ids=applied_vacancy_ids,
        )

    def apply(
        self,
        user: User,
        vacancy_id: int,
        filename: str,
        content: bytes,
    ):
        if not user.is_student:
            raise ValueError("Only student accounts can apply to internships.")

        vacancy = self.internship_repo.get_published_by_id(vacancy_id)
        if vacancy is None:
            raise ValueError("This internship is no longer accepting applications.")

        existing_application = self.application_repo.get_by_student_and_vacancy(
            user.id,
            vacancy_id,
        )
        if existing_application:
            raise ValueError("You have already applied to this internship.")

        safe_name, stored_path = self._store_application_document(filename, content)
        try:
            return self.application_repo.create_with_document(
                student_id=user.id,
                vacancy_id=vacancy_id,
                document_name=safe_name,
                file_path=str(stored_path),
                document_type="application/pdf",
                size_bytes=len(content),
            )
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

    def replace_application_document(
        self,
        user: User,
        application_id: int,
        filename: str,
        content: bytes,
    ):
        if not user.is_student:
            raise ValueError("Only student accounts can edit their applications.")

        safe_name, stored_path = self._store_application_document(filename, content)
        try:
            result = self.application_repo.replace_student_application_document(
                application_id=application_id,
                student_id=user.id,
                document_name=safe_name,
                file_path=str(stored_path),
                document_type="application/pdf",
                size_bytes=len(content),
            )
            if result is None:
                raise ValueError("Application not found.")
            application, old_file_paths = result
            self._remove_application_files(old_file_paths)
            return application
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

    def delete_application(self, user: User, application_id: int) -> None:
        if not user.is_student:
            raise ValueError("Only student accounts can delete their applications.")
        removed_file_paths = self.application_repo.delete_student_application(
            application_id=application_id,
            student_id=user.id,
        )
        if removed_file_paths is None:
            raise ValueError("Application not found.")
        self._remove_application_files(removed_file_paths)

    @staticmethod
    def _store_application_document(filename: str, content: bytes) -> tuple[str, Path]:
        safe_name = Path(filename).name
        if Path(safe_name).suffix.lower() != ".pdf":
            raise ValueError("Attach your application document as a PDF.")
        if not content:
            raise ValueError("The selected PDF is empty.")
        if not content.startswith(b"%PDF-"):
            raise ValueError("The uploaded file is not a valid PDF document.")
        if len(content) > MAX_APPLICATION_DOCUMENT_SIZE:
            raise ValueError("Application documents must be 10 MB or smaller.")

        APPLICATION_UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
        stored_path = APPLICATION_UPLOAD_DIRECTORY / f"{uuid4().hex}.pdf"
        stored_path.write_bytes(content)
        return safe_name, stored_path

    @staticmethod
    def _remove_application_files(file_paths: list[str]) -> None:
        upload_directory = APPLICATION_UPLOAD_DIRECTORY.resolve()
        for file_path in file_paths:
            candidate = Path(file_path).resolve()
            if candidate.is_relative_to(upload_directory):
                candidate.unlink(missing_ok=True)

    def get_vacancy_detail(self, user: User, vacancy_id: int):
        if not user.is_student:
            raise ValueError("Only student accounts can view internship details.")
        vacancy = self.internship_repo.get_published_detail(vacancy_id)
        if vacancy is None:
            raise ValueError("Published internship not found.")
        return vacancy

    def has_applied(self, user: User, vacancy_id: int) -> bool:
        if not user.is_student:
            raise ValueError("Only student accounts can view internship details.")
        return (
            self.application_repo.get_by_student_and_vacancy(user.id, vacancy_id)
            is not None
        )

    def get_supplementary_document(
        self,
        user: User,
        vacancy_id: int,
        document_id: int,
    ):
        if not user.is_student:
            raise ValueError("Only student accounts can download vacancy documents.")
        link = self.internship_repo.get_published_document(vacancy_id, document_id)
        if link is None or link.document is None:
            raise ValueError("Supplementary document not found.")
        return link.document

    @staticmethod
    def external_document_url(file_path: str) -> str | None:
        parsed = urlparse(file_path)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return file_path
        return None

    @staticmethod
    def local_document_path(file_path: str) -> Path | None:
        candidate = Path(file_path).resolve()
        allowed_directories = (
            Path("app/uploads").resolve(),
            Path("app/static/uploads").resolve(),
        )
        if any(candidate.is_relative_to(directory) for directory in allowed_directories):
            return candidate if candidate.is_file() else None
        return None
