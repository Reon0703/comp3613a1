from typing import Optional

from sqlmodel import SQLModel


class VacancyCreate(SQLModel):
    company_id: int
    title: str
    description: str
    location: Optional[str] = ""
    image_url: Optional[str] = None
    status: str = "Draft"
    is_published: bool = True


class VacancyPayload(SQLModel):
    title: str
    description: str
    location: Optional[str] = ""
    image_url: Optional[str] = None
    status: str = "Draft"
    is_published: bool = True
