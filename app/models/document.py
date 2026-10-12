from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.application import ApplicationDocument
    from app.models.vacancy import VacancyDocument

class DocumentBase(SQLModel):
    name: str
    file_path: str
    type: str
    size_bytes: int

class Document(DocumentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    applications: List["ApplicationDocument"] = Relationship(back_populates="document")
    vacancies: List["VacancyDocument"] = Relationship(back_populates="document")