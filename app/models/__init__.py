"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.user import User
from app.models.vacancy import InternshipVacancy, VacancyDocument
from app.models.application import Application, ApplicationDocument
from app.models.document import Document
__all__ = ["User", "InternshipVacancy", "VacancyDocument", "Application", "ApplicationDocument", "Document"]
