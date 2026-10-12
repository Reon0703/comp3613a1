from dataclasses import dataclass

from app.models.application import Application
from app.models.user import User
from app.models.vacancy import InternshipVacancy
from app.repositories.application import ApplicationRepository
from app.utilities.pagination import Pagination

EDUCATION_LEVEL_FILTERS = (
    "Undergraduate",
    "Postgraduate",
    "Associate's",
    "Diploma",
)
APPLICATION_STATUS_SORT_OPTIONS = (
    Application.STATUS_REJECTED,
    Application.STATUS_SHORTLISTED,
    Application.STATUS_UNDER_REVIEW,
)


@dataclass
class ApplicationBrowseResult:
    vacancy: InternshipVacancy
    applications: list[Application]
    pagination: Pagination
    education_level_options: tuple[str, ...]
    status_sort_options: tuple[str, ...]
    query: str | None = None
    education_level: str | None = None
    status_sort: str | None = None


@dataclass
class ApplicationReviewResult:
    vacancy: InternshipVacancy
    application: Application


@dataclass
class StudentApplicationsResult:
    applications: list[Application]
    pagination: Pagination


class ApplicationService:
    def __init__(self, application_repo: ApplicationRepository):
        self.application_repo = application_repo

    def list_for_student(
        self,
        user: User,
        page: int = 1,
    ) -> StudentApplicationsResult:
        if not user.is_student:
            raise ValueError("Only student accounts can view their applications.")
        applications, pagination = self.application_repo.list_for_student(
            student_id=user.id,
            page=page,
        )
        return StudentApplicationsResult(
            applications=applications,
            pagination=pagination,
        )

    def browse(
        self,
        user: User,
        vacancy_id: int,
        query: str | None = None,
        education_level: str | None = None,
        status_sort: str | None = None,
        page: int = 1,
    ) -> ApplicationBrowseResult:
        vacancy = self._owned_vacancy(user, vacancy_id)
        if education_level not in EDUCATION_LEVEL_FILTERS:
            education_level = None
        if status_sort not in APPLICATION_STATUS_SORT_OPTIONS:
            status_sort = None
        applications, pagination = self.application_repo.list_for_vacancy(
            vacancy_id=vacancy.id,
            query=query,
            education_level=education_level,
            status_sort=status_sort,
            page=page,
        )
        return ApplicationBrowseResult(
            vacancy=vacancy,
            applications=applications,
            pagination=pagination,
            education_level_options=EDUCATION_LEVEL_FILTERS,
            status_sort_options=APPLICATION_STATUS_SORT_OPTIONS,
            query=query,
            education_level=education_level,
            status_sort=status_sort,
        )

    def get_review(
        self,
        user: User,
        vacancy_id: int,
        application_id: int,
    ) -> ApplicationReviewResult:
        vacancy = self._owned_vacancy(user, vacancy_id)
        application = self.application_repo.get_for_vacancy(
            application_id,
            vacancy.id,
        )
        if application is None:
            raise ValueError("Application not found.")
        return ApplicationReviewResult(vacancy=vacancy, application=application)

    def shortlist(
        self,
        user: User,
        vacancy_id: int,
        application_id: int,
    ) -> Application:
        return self._set_status(
            user,
            vacancy_id,
            application_id,
            Application.STATUS_SHORTLISTED,
        )

    def reject(
        self,
        user: User,
        vacancy_id: int,
        application_id: int,
    ) -> Application:
        return self._set_status(
            user,
            vacancy_id,
            application_id,
            Application.STATUS_REJECTED,
        )

    def finish_review(self, user: User, vacancy_id: int) -> int:
        vacancy = self._owned_vacancy(user, vacancy_id)
        return self.application_repo.finish_review_for_vacancy(vacancy.id)

    def _set_status(
        self,
        user: User,
        vacancy_id: int,
        application_id: int,
        status: str,
    ) -> Application:
        result = self.get_review(user, vacancy_id, application_id)
        result.application.status = status
        return self.application_repo.save(result.application)

    def _owned_vacancy(self, user: User, vacancy_id: int) -> InternshipVacancy:
        if not user.is_company:
            raise ValueError("Only company accounts can review applications.")
        vacancy = self.application_repo.get_owned_vacancy(vacancy_id, user.id)
        if vacancy is None:
            raise ValueError("Vacancy not found.")
        return vacancy
