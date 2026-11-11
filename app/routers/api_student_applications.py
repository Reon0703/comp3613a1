from typing import Annotated

from fastapi import File, HTTPException, Query, Response, UploadFile, status

from app.config import get_settings
from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.repositories.internship import InternshipRepository
from app.schemas.application import (
    ApplicationDocumentResponse,
    ApplicationDocumentUpdateResponse,
    StudentApplicationListItem,
    StudentApplicationsResponse,
)
from app.services.application_service import ApplicationService
from app.services.internship_service import (
    MAX_APPLICATION_DOCUMENT_SIZE,
    InternshipAccessError,
    InternshipApplicationNotEditableError,
    InternshipApplicationNotFoundError,
    InternshipService,
)
from app.utilities.pdf import create_generic_pdf

from . import api_router


@api_router.get(
    "/student/applications",
    response_model=StudentApplicationsResponse,
)
def list_student_applications_api(
    user: AuthDep,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        result = service.list_for_student(user, page=page)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    items = []
    for application in result.applications:
        if application.vacancy is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Application vacancy details are unavailable.",
            )
        if application.vacancy.company is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Application company details are unavailable.",
            )
        documents = []
        for link in application.documents:
            if link.document is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Application document details are unavailable.",
                )
            documents.append(
                ApplicationDocumentResponse(
                    id=link.document.id,
                    name=link.document.name,
                    type=link.document.type,
                    size_bytes=link.document.size_bytes,
                )
            )
        items.append(
            StudentApplicationListItem(
                id=application.id,
                vacancy_id=application.vacancy_id,
                status=application.status,
                submission_date=application.submission_date,
                vacancy={
                    "title": application.vacancy.title,
                    "company_name": application.vacancy.company.company_name,
                },
                documents=documents,
            )
        )

    return StudentApplicationsResponse(
        items=items,
        pagination={
            "total_count": result.pagination.total_count,
            "current_page": result.pagination.page,
            "limit": result.pagination.limit,
            "total_pages": result.pagination.total_pages,
        },
    )


@api_router.put(
    "/student/applications/{application_id}/document",
    response_model=ApplicationDocumentUpdateResponse,
)
async def replace_student_application_document_api(
    application_id: int,
    user: AuthDep,
    db: SessionDep,
    application_document: Annotated[UploadFile | None, File()] = None,
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    content = (
        await application_document.read(MAX_APPLICATION_DOCUMENT_SIZE + 1)
        if application_document is not None
        else b""
    )
    filename = (
        application_document.filename or "application.pdf"
        if application_document is not None
        else ""
    )
    if not filename and not content:
        if get_settings().env.lower() not in {"dev", "development", "test"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="An application PDF is required.",
            )
        filename = "generic-test-application.pdf"
        content = create_generic_pdf()
    try:
        service.replace_application_document(
            user=user,
            application_id=application_id,
            filename=filename,
            content=content,
        )
    except InternshipAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except InternshipApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InternshipApplicationNotEditableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ApplicationDocumentUpdateResponse(
        message="application document updated",
    )


@api_router.delete(
    "/student/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="delete_student_application_api",
)
def delete_student_application_api(
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    try:
        service.delete_application(user, application_id)
    except InternshipAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except InternshipApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
