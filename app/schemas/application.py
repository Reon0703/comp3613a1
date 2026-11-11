from datetime import datetime
from typing import Literal

from sqlmodel import SQLModel


class ApplicationDocumentResponse(SQLModel):
    id: int
    name: str
    type: str
    size_bytes: int


class StudentApplicationResponse(SQLModel):
    id: int
    student_id: int
    vacancy_id: int
    status: str
    submission_date: datetime
    documents: list[ApplicationDocumentResponse]


class ApplicationVacancySummary(SQLModel):
    title: str
    company_name: str | None


class StudentApplicationListItem(SQLModel):
    id: int
    vacancy_id: int
    status: str
    submission_date: datetime
    vacancy: ApplicationVacancySummary
    documents: list[ApplicationDocumentResponse]


class StudentApplicationsPagination(SQLModel):
    total_count: int
    current_page: int
    limit: int
    total_pages: int


class StudentApplicationsResponse(SQLModel):
    items: list[StudentApplicationListItem]
    pagination: StudentApplicationsPagination


class ApplicationDocumentUpdateResponse(SQLModel):
    message: str


class CompanyApplicationStudentSummary(SQLModel):
    first_name: str | None
    last_name: str | None
    email: str
    education_level: str | None


class CompanyApplicationListItem(SQLModel):
    id: int
    student_id: int
    vacancy_id: int
    status: str
    submission_date: datetime
    student: CompanyApplicationStudentSummary
    documents: list[ApplicationDocumentResponse]


class CompanyApplicationsResponse(SQLModel):
    items: list[CompanyApplicationListItem]
    pagination: StudentApplicationsPagination


ApplicationReviewStatus = Literal["Shortlisted", "Rejected"]


class CompanyApplicationReviewStudent(SQLModel):
    first_name: str | None
    last_name: str | None
    email: str
    education_level: str | None


class CompanyApplicationReview(SQLModel):
    id: int
    student_id: int
    vacancy_id: int
    status: str
    submission_date: datetime
    student: CompanyApplicationReviewStudent
    documents: list[ApplicationDocumentResponse]


class CompanyApplicationVacancySummary(SQLModel):
    id: int
    title: str


class CompanyApplicationReviewResponse(SQLModel):
    vacancy: CompanyApplicationVacancySummary
    application: CompanyApplicationReview


class CompanyApplicationStatusUpdate(SQLModel):
    status: ApplicationReviewStatus


class CompanyApplicationStatusResponse(SQLModel):
    id: int
    vacancy_id: int
    status: ApplicationReviewStatus


class FinishApplicationReviewResponse(SQLModel):
    updated_count: int
