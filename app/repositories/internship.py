from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, select

from app.models.vacancy import InternshipVacancy, VacancyDocument
from app.utilities.pagination import Pagination


class InternshipRepository:
    def __init__(self, db: Session):
        self.db = db

    def browse_published(
        self,
        query: str | None = None,
        page: int = 1,
        limit: int = 12,
    ) -> tuple[list[InternshipVacancy], Pagination]:
        statement = select(InternshipVacancy).where(
            InternshipVacancy.status == "Published"
        )
        if query:
            search = f"%{query.strip()}%"
            statement = statement.where(
                InternshipVacancy.title.ilike(search)
                | InternshipVacancy.description.ilike(search)
                | InternshipVacancy.location.ilike(search)
            )

        count_statement = select(func.count()).select_from(statement.subquery())
        total_count = self.db.exec(count_statement).one()
        offset = (page - 1) * limit
        vacancies = self.db.exec(
            statement.order_by(InternshipVacancy.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return vacancies, Pagination(
            total_count=total_count,
            current_page=page,
            limit=limit,
        )

    def get_published_by_id(self, vacancy_id: int) -> InternshipVacancy | None:
        statement = select(InternshipVacancy).where(
            InternshipVacancy.id == vacancy_id,
            InternshipVacancy.status == "Published",
        )
        return self.db.exec(statement).one_or_none()

    def get_published_detail(self, vacancy_id: int) -> InternshipVacancy | None:
        statement = (
            select(InternshipVacancy)
            .where(
                InternshipVacancy.id == vacancy_id,
                InternshipVacancy.status == "Published",
            )
            .options(
                selectinload(InternshipVacancy.company),
                selectinload(InternshipVacancy.documents).selectinload(
                    VacancyDocument.document
                ),
            )
        )
        return self.db.exec(statement).one_or_none()

    def get_published_document(
        self,
        vacancy_id: int,
        document_id: int,
    ):
        statement = (
            select(VacancyDocument)
            .join(InternshipVacancy)
            .where(
                InternshipVacancy.id == vacancy_id,
                InternshipVacancy.status == "Published",
                VacancyDocument.document_id == document_id,
            )
            .options(selectinload(VacancyDocument.document))
        )
        return self.db.exec(statement).one_or_none()
