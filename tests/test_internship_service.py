from pathlib import Path
from unittest.mock import Mock

import pytest

from app.models.application import Application
from app.services import internship_service
from app.services.internship_service import (
    MAX_APPLICATION_DOCUMENT_SIZE,
    InternshipService,
)


def make_service():
    return InternshipService(Mock(), Mock())


def test_browse_internships_rejects_company_user(company_user):
    service = make_service()

    with pytest.raises(
        ValueError, match="Only student accounts can browse internships"
    ):
        service.browse(company_user)

    service.internship_repo.browse_published.assert_not_called()


def test_browse_internships_filters_supported_fields(student_user):
    service = make_service()
    service.internship_repo.browse_published.return_value = ([], Mock())

    result = service.browse(
        student_user,
        query="design",
        field_of_study=["Technology", "not-a-field"],
        page=2,
    )

    service.internship_repo.browse_published.assert_called_once_with(
        student_id=student_user.id,
        query="design",
        field_of_study=["Technology"],
        page=2,
    )
    assert result.selected_fields_of_study == ("Technology",)


def test_apply_creates_submitted_application_with_pdf(
    monkeypatch,
    tmp_path,
    student_user,
    vacancy,
    generic_pdf,
):
    upload_directory = tmp_path / "applications"
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    service = make_service()
    service.internship_repo.get_published_by_id.return_value = vacancy
    service.application_repo.get_by_student_and_vacancy.return_value = None
    created_application = object()
    service.application_repo.create_with_document.return_value = created_application
    content = generic_pdf

    result = service.apply(
        student_user,
        vacancy.id,
        "resume.pdf",
        content,
    )

    assert result is created_application
    call = service.application_repo.create_with_document.call_args.kwargs
    assert call["student_id"] == student_user.id
    assert call["vacancy_id"] == vacancy.id
    assert call["document_name"] == "resume.pdf"
    assert call["document_type"] == "application/pdf"
    assert call["size_bytes"] == len(content)
    assert Path(call["file_path"]).read_bytes() == content


def test_apply_rejects_non_student(
    monkeypatch,
    tmp_path,
    company_user,
    vacancy,
    generic_pdf,
):
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    service = make_service()

    with pytest.raises(ValueError, match="Only student accounts can apply"):
        service.apply(company_user, vacancy.id, "resume.pdf", generic_pdf)

    service.internship_repo.get_published_by_id.assert_not_called()
    service.application_repo.create_with_document.assert_not_called()


def test_apply_rejects_unpublished_vacancy(student_user, generic_pdf):
    service = make_service()
    service.internship_repo.get_published_by_id.return_value = None

    with pytest.raises(ValueError, match="no longer accepting applications"):
        service.apply(student_user, 12, "resume.pdf", generic_pdf)

    service.application_repo.create_with_document.assert_not_called()


def test_apply_rejects_duplicate_application(
    monkeypatch,
    tmp_path,
    student_user,
    vacancy,
    generic_pdf,
):
    upload_directory = tmp_path / "applications"
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    service = make_service()
    service.internship_repo.get_published_by_id.return_value = vacancy
    service.application_repo.get_by_student_and_vacancy.return_value = object()

    with pytest.raises(ValueError, match="already applied"):
        service.apply(student_user, vacancy.id, "resume.pdf", generic_pdf)

    service.application_repo.create_with_document.assert_not_called()
    assert not upload_directory.exists()


def test_application_document_rejects_non_pdf():
    with pytest.raises(ValueError, match="as a PDF"):
        InternshipService._store_application_document("resume.docx", b"document")


def test_application_document_rejects_invalid_pdf_content():
    with pytest.raises(ValueError, match="not a valid PDF"):
        InternshipService._store_application_document("resume.pdf", b"not a pdf")


def test_application_document_rejects_empty_content():
    with pytest.raises(ValueError, match="selected PDF is empty"):
        InternshipService._store_application_document("resume.pdf", b"")


def test_application_document_rejects_file_over_10_mb(generic_pdf):
    content = generic_pdf + b"x" * (
        MAX_APPLICATION_DOCUMENT_SIZE + 1 - len(generic_pdf)
    )

    with pytest.raises(ValueError, match="10 MB or smaller"):
        InternshipService._store_application_document("resume.pdf", content)


def test_replace_document_only_for_submitted_application(
    monkeypatch,
    tmp_path,
    student_user,
    application,
    generic_pdf,
):
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        tmp_path / "applications",
    )
    application.status = Application.STATUS_UNDER_REVIEW
    service = make_service()
    service.application_repo.get_for_student.return_value = application

    with pytest.raises(ValueError, match="Only applications with Submitted status"):
        service.replace_application_document(
            student_user,
            application.id,
            "replacement.pdf",
            generic_pdf,
        )

    service.application_repo.replace_student_application_document.assert_not_called()


def test_replace_document_for_submitted_application(
    monkeypatch,
    tmp_path,
    student_user,
    application,
    generic_pdf,
):
    upload_directory = tmp_path / "applications"
    upload_directory.mkdir()
    old_file = upload_directory / "old.pdf"
    old_file.write_bytes(generic_pdf)
    monkeypatch.setattr(
        internship_service,
        "APPLICATION_UPLOAD_DIRECTORY",
        upload_directory,
    )
    service = make_service()
    service.application_repo.get_for_student.return_value = application
    service.application_repo.replace_student_application_document.return_value = (
        application,
        [str(old_file)],
    )
    content = generic_pdf

    result = service.replace_application_document(
        student_user,
        application.id,
        "replacement.pdf",
        content,
    )

    assert result is application
    call = (
        service.application_repo.replace_student_application_document.call_args.kwargs
    )
    assert call["application_id"] == application.id
    assert call["student_id"] == student_user.id
    assert call["document_name"] == "replacement.pdf"
    assert call["document_type"] == "application/pdf"
    assert call["size_bytes"] == len(content)
    assert Path(call["file_path"]).read_bytes() == content
    assert not old_file.exists()


def test_delete_application_rejects_non_student(company_user):
    service = make_service()

    with pytest.raises(ValueError, match="Only student accounts can delete"):
        service.delete_application(company_user, 35)

    service.application_repo.delete_student_application.assert_not_called()


def test_delete_application_rejects_application_not_owned_by_student(student_user):
    service = make_service()
    service.application_repo.delete_student_application.return_value = None

    with pytest.raises(ValueError, match="Application not found"):
        service.delete_application(student_user, 35)


def test_local_document_path_rejects_path_outside_upload_directories(
    tmp_path,
    generic_pdf,
):
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_bytes(generic_pdf)

    assert InternshipService.local_document_path(str(outside_file)) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://files.example.test/guide.pdf",
        "http://files.example.test/guide.pdf",
    ],
)
def test_external_document_url_accepts_http_and_https(url):
    assert InternshipService.external_document_url(url) == url


@pytest.mark.parametrize(
    "file_path",
    [
        "javascript:alert(1)",
        "app/uploads/applications/resume.pdf",
    ],
)
def test_external_document_url_rejects_non_http_scheme(file_path):
    assert InternshipService.external_document_url(file_path) is None
