from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, SQLModel,Relationship, UniqueConstraint

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application
    from app.models.document import Document


class InternshipVacancyBase(SQLModel):
    company_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(index=True)
    description: str
    location: str = ""
    image_url: Optional[str] = None
    status: str = "Draft"
    is_published: bool = False



class InternshipVacancy(InternshipVacancyBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    company: Optional["User"] = Relationship(back_populates="vacancies")
    applications: List["Application"] = Relationship(back_populates="vacancy")
    documents: List["VacancyDocument"] = Relationship(back_populates="vacancy")


class VacancyDocument(SQLModel, table=True):

    
    vacancy_id: int = Field(primary_key=True, foreign_key="internshipvacancy.id", index=True)
    document_id: int = Field(primary_key=True, foreign_key="document.id", index=True)

    vacancy: Optional["InternshipVacancy"] = Relationship(back_populates="documents")
    document: Optional["Document"] = Relationship(back_populates="vacancies")