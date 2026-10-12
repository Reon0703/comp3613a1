from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, select

from app.models.application import Application, ApplicationDocument
from app.models.document import Document
from app.models.user import User
from app.models.vacancy import InternshipVacancy, VacancyDocument
from app.utilities.pagination import Pagination


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_student_and_vacancy(
        self,
        student_id: int,
        vacancy_id: int,
    ) -> Application | None:
        statement = select(Application).where(
            Application.student_id == student_id,
            Application.vacancy_id == vacancy_id,
        )
        return self.db.exec(statement).one_or_none()

    def list_vacancy_ids_for_student(self, student_id: int) -> set[int]:
        statement = select(Application.vacancy_id).where(
            Application.student_id == student_id
        )
        return set(self.db.exec(statement).all())

    def remove_seeded_applications_not_in_targets(
        self,
        student_id: int,
        target_vacancy_ids: set[int],
        demo_document_path: str,
    ) -> int:
        statement = (
            select(Application)
            .where(Application.student_id == student_id)
            .options(
                selectinload(Application.documents).selectinload(
                    ApplicationDocument.document
                )
            )
        )
        applications = self.db.exec(statement).all()
        removed = 0
        for application in applications:
            if application.vacancy_id in target_vacancy_ids:
                continue
            links = application.documents
            if not links or not all(
                link.document and link.document.file_path == demo_document_path
                for link in links
            ):
                continue
            for link in links:
                if link.document:
                    self.db.delete(link.document)
                self.db.delete(link)
            self.db.delete(application)
            removed += 1

        if removed:
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
        return removed

    def list_for_student(
        self,
        student_id: int,
        page: int = 1,
        limit: int = 12,
    ) -> tuple[list[Application], Pagination]:
        count_statement = select(func.count()).where(
            Application.student_id == student_id
        )
        total_count = self.db.exec(count_statement).one()
        applications = self.db.exec(
            select(Application)
            .where(Application.student_id == student_id)
            .options(
                selectinload(Application.vacancy).selectinload(
                    InternshipVacancy.company
                ),
                selectinload(Application.documents).selectinload(
                    ApplicationDocument.document
                ),
            )
            .order_by(Application.submission_date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        return applications, Pagination(
            total_count=total_count,
            current_page=page,
            limit=limit,
        )

    def _get_for_student(
        self,
        application_id: int,
        student_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(
                Application.id == application_id,
                Application.student_id == student_id,
            )
            .options(
                selectinload(Application.documents).selectinload(
                    ApplicationDocument.document
                )
            )
        )
        return self.db.exec(statement).one_or_none()

    def replace_student_application_document(
        self,
        application_id: int,
        student_id: int,
        document_name: str,
        file_path: str,
        document_type: str,
        size_bytes: int,
    ) -> tuple[Application, list[str]] | None:
        application = self._get_for_student(application_id, student_id)
        if application is None:
            return None

        old_documents = [
            link.document for link in application.documents if link.document
        ]
        try:
            for link in application.documents:
                self.db.delete(link)
            self.db.flush()
            removed_file_paths = self._delete_unlinked_documents(old_documents)

            document = Document(
                name=document_name,
                file_path=file_path,
                type=document_type,
                size_bytes=size_bytes,
            )
            self.db.add(document)
            self.db.flush()
            self.db.add(
                ApplicationDocument(
                    application_id=application.id,
                    document_id=document.id,
                )
            )
            self.db.commit()
            self.db.refresh(application)
            return application, removed_file_paths
        except Exception:
            self.db.rollback()
            raise

    def delete_student_application(
        self,
        application_id: int,
        student_id: int,
    ) -> list[str] | None:
        application = self._get_for_student(application_id, student_id)
        if application is None:
            return None

        old_documents = [
            link.document for link in application.documents if link.document
        ]
        try:
            for link in application.documents:
                self.db.delete(link)
            self.db.delete(application)
            self.db.flush()
            removed_file_paths = self._delete_unlinked_documents(old_documents)
            self.db.commit()
            return removed_file_paths
        except Exception:
            self.db.rollback()
            raise

    def _delete_unlinked_documents(self, documents: list[Document]) -> list[str]:
        removed_file_paths = []
        for document in {document.id: document for document in documents}.values():
            application_links = self.db.exec(
                select(func.count())
                .select_from(ApplicationDocument)
                .where(ApplicationDocument.document_id == document.id)
            ).one()
            vacancy_links = self.db.exec(
                select(func.count())
                .select_from(VacancyDocument)
                .where(VacancyDocument.document_id == document.id)
            ).one()
            if application_links == 0 and vacancy_links == 0:
                removed_file_paths.append(document.file_path)
                self.db.delete(document)
        return removed_file_paths

    def create_application(
        self,
        student_id: int,
        vacancy_id: int,
        status: str = "Submitted",
    ) -> Application:
        application = Application(
            student_id=student_id,
            vacancy_id=vacancy_id,
            status=status,
        )
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def create_document(
        self,
        name: str,
        file_path: str,
        document_type: str = "application/pdf",
        size_bytes: int = 0,
    ) -> Document:
        document = Document(
            name=name,
            file_path=file_path,
            type=document_type,
            size_bytes=size_bytes,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def create_with_document(
        self,
        student_id: int,
        vacancy_id: int,
        document_name: str,
        file_path: str,
        document_type: str,
        size_bytes: int,
    ) -> Application:
        application = Application(
            student_id=student_id,
            vacancy_id=vacancy_id,
            status=Application.STATUS_SUBMITTED,
        )
        document = Document(
            name=document_name,
            file_path=file_path,
            type=document_type,
            size_bytes=size_bytes,
        )
        self.db.add(application)
        self.db.add(document)
        try:
            self.db.flush()
            self.db.add(
                ApplicationDocument(
                    application_id=application.id,
                    document_id=document.id,
                )
            )
            self.db.commit()
            self.db.refresh(application)
            return application
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("You have already applied to this internship.") from exc
        except Exception:
            self.db.rollback()
            raise

    def get_owned_vacancy(
        self,
        vacancy_id: int,
        company_id: int,
    ) -> InternshipVacancy | None:
        statement = select(InternshipVacancy).where(
            InternshipVacancy.id == vacancy_id,
            InternshipVacancy.company_id == company_id,
        )
        return self.db.exec(statement).one_or_none()

    def list_for_vacancy(
        self,
        vacancy_id: int,
        query: str | None = None,
        education_level: str | None = None,
        page: int = 1,
        limit: int = 12,
    ) -> tuple[list[Application], Pagination]:
        filters = [
            Application.vacancy_id == vacancy_id,
        ]
        if query:
            search = f"%{query.strip()}%"
            filters.append(
                User.first_name.ilike(search)
                | User.last_name.ilike(search)
                | User.username.ilike(search)
                | User.email.ilike(search)
            )
        if education_level:
            filters.append(User.education_level.ilike(f"%{education_level}%"))

        count_statement = (
            select(func.count())
            .select_from(Application)
            .join(User, Application.student_id == User.id)
            .where(*filters)
        )
        total_count = self.db.exec(count_statement).one()
        offset = (page - 1) * limit
        statement = (
            select(Application)
            .join(User, Application.student_id == User.id)
            .where(*filters)
            .options(
                selectinload(Application.student),
                selectinload(Application.documents).selectinload(
                    ApplicationDocument.document
                ),
            )
            .order_by(Application.submission_date.desc())
            .offset(offset)
            .limit(limit)
        )
        applications = self.db.exec(statement).all()
        return applications, Pagination(
            total_count=total_count,
            current_page=page,
            limit=limit,
        )

    def get_for_vacancy(
        self,
        application_id: int,
        vacancy_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(
                Application.id == application_id,
                Application.vacancy_id == vacancy_id,
            )
            .options(
                selectinload(Application.student),
                selectinload(Application.documents).selectinload(
                    ApplicationDocument.document
                ),
            )
        )
        return self.db.exec(statement).one_or_none()

    def save(self, application: Application) -> Application:
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def attach_document(self, application_id: int, document_id: int) -> ApplicationDocument:
        link = ApplicationDocument(
            application_id=application_id,
            document_id=document_id,
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link
