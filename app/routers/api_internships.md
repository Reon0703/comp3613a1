from typing import Annotated

from fastapi import File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import (
    ApplicationAlreadyExistsError,
    ApplicationRepository,
)
from app.repositories.internship import InternshipRepository
from app.schemas.application import StudentApplicationResponse
from app.schemas.internship import (
    InternshipBrowseResponse,
    InternshipDetailResponse,
    InternshipDocumentSummary,
)
from app.services.internship_service import (
    MAX_APPLICATION_DOCUMENT_SIZE,
    InternshipAccessError,
    InternshipService,
    InternshipUnavailableError,
)

from . import api_router


@api_router.get(
    "/internships",
    response_model=InternshipBrowseResponse,
)
def browse_internships_api(
    user: AuthDep,
    db: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    field_of_study: Annotated[list[str] | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    try:
        result = service.browse(
            user,
            query=q,
            field_of_study=field_of_study,
            page=page,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return InternshipBrowseResponse(
        items=[
            {
                **vacancy.model_dump(),
                "is_published": vacancy.status == "Published",
            }
            for vacancy in result.vacancies
        ],
        pagination={
            "total_count": result.pagination.total_count,
            "current_page": result.pagination.page,
            "limit": result.pagination.limit,
            "total_pages": result.pagination.total_pages,
        },
    )


@api_router.get(
    "/internships/{vacancy_id}",
    response_model=InternshipDetailResponse,
)
def internship_detail_api(
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    try:
        vacancy = service.get_vacancy_detail(user, vacancy_id)
        already_applied = service.has_applied(user, vacancy_id)
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_student
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=error_status, detail=str(exc)) from exc

    if vacancy.company is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internship company details are unavailable.",
        )

    documents = []
    for link in vacancy.documents:
        if link.document is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internship document details are unavailable.",
            )
        documents.append(
            InternshipDocumentSummary(
                id=link.document.id,
                name=link.document.name,
                type=link.document.type,
                size_bytes=link.document.size_bytes,
            )
        )

    return InternshipDetailResponse(
        **{
            **vacancy.model_dump(),
            "is_published": vacancy.status == "Published",
        },
        company={
            "company_name": vacancy.company.company_name,
            "location": vacancy.company.location,
            "profile_image_url": vacancy.company.profile_image_url,
        },
        already_applied=already_applied,
        documents=documents,
    )


@api_router.get("/internships/{vacancy_id}/documents/{document_id}")
def download_internship_document_api(
    vacancy_id: int,
    document_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    try:
        document = service.get_supplementary_document(
            user,
            vacancy_id,
            document_id,
        )
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_student
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=error_status, detail=str(exc)) from exc

    remote_url = service.external_document_url(document.file_path)
    if remote_url:
        return RedirectResponse(
            url=remote_url,
            status_code=status.HTTP_302_FOUND,
        )

    local_path = service.local_document_path(document.file_path)
    if local_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplementary document not found.",
        )
    return FileResponse(
        path=local_path,
        filename=document.name,
        media_type=document.type or "application/octet-stream",
    )


@api_router.post(
    "/internships/{vacancy_id}/applications",
    response_model=StudentApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_internship_api(
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    application_document: UploadFile = File(...),
):
    service = InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )
    content = await application_document.read(MAX_APPLICATION_DOCUMENT_SIZE + 1)
    # === STUDENT SNIPPET: thin application API handler ===
    raise NotImplementedError("Complete the internship application API handler.")
    # === END STUDENT SNIPPET ===
