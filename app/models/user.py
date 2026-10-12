from typing import TYPE_CHECKING, Optional

from pwdlib import PasswordHash         
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.vacancy import InternshipVacancy

ROLE_STUDENT = "regular_user"
ROLE_COMPANY = "company"
ROLE_ADMIN = "admin"

_hasher = PasswordHash.recommended()


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str                          
    role: str = ROLE_STUDENT
    profile_image_url: Optional[str] = None

    # student-only (NULL for other roles)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    education_level: Optional[str] = None

    # company-only (NULL for other roles)
    company_name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # same table, two roles: a student has applications, a company has vacancies
    applications: list["Application"] = Relationship(back_populates="student")
    vacancies: list["InternshipVacancy"] = Relationship(back_populates="company")

    # --- shared behavior ---
    def check_password(self, plaintext_password: str) -> bool:
        return _hasher.verify(plaintext_password, self.password)

    # --- role behavior ---
    @property
    def is_student(self) -> bool:
        return self.role == ROLE_STUDENT

    @property
    def is_company(self) -> bool:
        return self.role == ROLE_COMPANY

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def display_name(self) -> str:
        if self.is_company and self.company_name:
            return self.company_name
        full = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full or self.username