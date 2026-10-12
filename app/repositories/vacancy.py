import logging
from typing import List

from sqlmodel import Session, func, select, update

from app.models.application import Application
from app.models.vacancy import InternshipVacancy

logger = logging.getLogger(__name__)


class VacancyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, vacancy: InternshipVacancy) -> InternshipVacancy:
        try:
            self.db.add(vacancy)
            self.db.commit()
            self.db.refresh(vacancy)
            return vacancy
        except Exception as exc:  # noqa: BLE001
            logger.error("An error occurred while saving vacancy: %s", exc)
            self.db.rollback()
            raise

    def list_by_company(self, company_id: int) -> List[InternshipVacancy]:
        statement = (
            select(InternshipVacancy)
            .where(InternshipVacancy.company_id == company_id)
            .order_by(InternshipVacancy.id.desc())
        )
        return self.db.exec(statement).all()

    def application_counts_by_company(self, company_id: int) -> dict[int, int]:
        statement = (
            select(
                InternshipVacancy.id,
                func.count(Application.id).label("applicant_count"),
            )
            .outerjoin(Application, Application.vacancy_id == InternshipVacancy.id)
            .where(InternshipVacancy.company_id == company_id)
            .group_by(InternshipVacancy.id)
        )
        return {
            vacancy_id: applicant_count
            for vacancy_id, applicant_count in self.db.exec(statement).all()
        }

    def get_by_company_and_title(
        self,
        company_id: int,
        title: str,
    ) -> InternshipVacancy | None:
        statement = select(InternshipVacancy).where(
            InternshipVacancy.company_id == company_id,
            InternshipVacancy.title == title,
        )
        return self.db.exec(statement).one_or_none()

    def get_by_id(self, vacancy_id: int) -> InternshipVacancy | None:
        return self.db.get(InternshipVacancy, vacancy_id)

    def has_applications(self, vacancy_id: int) -> bool:
        statement = (
            select(func.count())
            .select_from(Application)
            .where(Application.vacancy_id == vacancy_id)
        )
        return self.db.exec(statement).one() > 0

    def update(
        self,
        vacancy: InternshipVacancy,
        application_status: str | None = None,
    ) -> InternshipVacancy:
        try:
            self.db.add(vacancy)
            if application_status:
                self.db.exec(
                    update(Application)
                    .where(Application.vacancy_id == vacancy.id)
                    .values(status=application_status)
                )
            self.db.commit()
            self.db.refresh(vacancy)
            return vacancy
        except Exception as exc:  # noqa: BLE001
            logger.error("An error occurred while updating vacancy: %s", exc)
            self.db.rollback()
            raise

    def list_published(self) -> List[InternshipVacancy]:
        statement = (
            select(InternshipVacancy)
            .where(InternshipVacancy.status == "Published")
            .order_by(InternshipVacancy.id.desc())
        )
        return self.db.exec(statement).all()
