from sqlmodel import SQLModel


class InternshipBrowseItem(SQLModel):
    id: int
    company_id: int
    title: str
    description: str
    location: str
    field_of_study: str | None
    image_url: str | None
    status: str
    is_published: bool


class InternshipBrowsePagination(SQLModel):
    total_count: int
    current_page: int
    limit: int
    total_pages: int


class InternshipBrowseResponse(SQLModel):
    items: list[InternshipBrowseItem]
    pagination: InternshipBrowsePagination


class InternshipCompanySummary(SQLModel):
    company_name: str | None
    location: str | None
    profile_image_url: str | None


class InternshipDocumentSummary(SQLModel):
    id: int
    name: str
    type: str
    size_bytes: int


class InternshipDetailResponse(InternshipBrowseItem):
    company: InternshipCompanySummary
    already_applied: bool
    documents: list[InternshipDocumentSummary]
