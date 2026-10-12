from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar, Optional, List

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vacancy import InternshipVacancy
    from app.models.document import Document

class ApplicationBase(SQLModel):
    student_id: int = Field(foreign_key="user.id", index=True)
    vacancy_id: int = Field(foreign_key="internshipvacancy.id", index=True)
    status: str
    submission_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    

class Application(ApplicationBase, table=True):
    __table_args__ = (
        UniqueConstraint("student_id", "vacancy_id", name="uq_one_application_per_vacancy"),
    )

    # === STUDENT SNIPPET: screening statuses ===
    # Set the three string values used when a company reviews an application.
    STATUS_SUBMITTED: ClassVar[str] = "Submitted"
    STATUS_SHORTLISTED: ClassVar[str] = "Shortlisted"
    STATUS_UNDER_REVIEW: ClassVar[str] = "Under Review"
    STATUS_REJECTED: ClassVar[str] = "Rejected"
    # === END STUDENT SNIPPET ===

    id: Optional[int] = Field(default=None, primary_key=True)

    student: Optional["User"] = Relationship(back_populates="applications")
    vacancy: Optional["InternshipVacancy"] = Relationship(back_populates="applications") 
    documents: List["ApplicationDocument"] = Relationship(back_populates="application")
    

class ApplicationDocument(SQLModel, table=True):
    application_id: int = Field(primary_key=True, foreign_key="application.id", index=True)
    document_id: int = Field(primary_key=True, foreign_key="document.id", index=True)

    application: Optional["Application"] = Relationship(back_populates="documents")
    document: Optional["Document"] = Relationship( back_populates="applications")  