from datetime import datetime

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
