from sqlmodel import SQLModel


class VacancyCreate(SQLModel):
    company_id: int
    title: str
    description: str
    location: str | None = ""
    image_url: str | None = None
    status: str = "Draft"
    is_published: bool = True


class VacancyPayload(SQLModel):
    title: str
    description: str
    location: str | None = ""
    image_url: str | None = None
    status: str = "Draft"
    is_published: bool = True


class CompanyVacancyListItem(SQLModel):
    id: int
    company_id: int
    title: str
    description: str
    location: str
    field_of_study: str | None
    status: str
    is_published: bool
    applicant_count: int


class CompanyVacancyResponse(SQLModel):
    id: int
    company_id: int
    title: str
    description: str
    location: str
    field_of_study: str | None
    status: str
    is_published: bool
    image_url: str | None = None
