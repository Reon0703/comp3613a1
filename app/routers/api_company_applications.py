from typing import Annotated

from fastapi import HTTPException, Query, status

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.schemas.application import (
    ApplicationDocumentResponse,
    CompanyApplicationListItem,
    CompanyApplicationReviewResponse,
    CompanyApplicationsResponse,
    CompanyApplicationStatusResponse,
    CompanyApplicationStatusUpdate,
    FinishApplicationReviewResponse,
)
from app.services.application_service import ApplicationService

from . import api_router


@api_router.get(
    "/company/vacancies/{vacancy_id}/applications",
    response_model=CompanyApplicationsResponse,
)
def browse_company_vacancy_applications_api(
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    education_level: Annotated[str | None, Query(max_length=100)] = None,
    status_sort: Annotated[str | None, Query(max_length=30)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        result = service.browse(
            user,
            vacancy_id=vacancy_id,
            query=q,
            education_level=education_level,
            status_sort=status_sort,
            page=page,
        )
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_company
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(
            status_code=error_status,
            detail=str(exc),
        ) from exc

    items = []
    for application in result.applications:
        if application.student is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Application student details are unavailable.",
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
            CompanyApplicationListItem(
                id=application.id,
                student_id=application.student_id,
                vacancy_id=application.vacancy_id,
                status=application.status,
                submission_date=application.submission_date,
                student={
                    "first_name": application.student.first_name,
                    "last_name": application.student.last_name,
                    "email": application.student.email,
                    "education_level": application.student.education_level,
                },
                documents=documents,
            )
        )

    return CompanyApplicationsResponse(
        items=items,
        pagination={
            "total_count": result.pagination.total_count,
            "current_page": result.pagination.page,
            "limit": result.pagination.limit,
            "total_pages": result.pagination.total_pages,
        },
    )


@api_router.get(
    "/company/vacancies/{vacancy_id}/applications/{application_id}",
    response_model=CompanyApplicationReviewResponse,
    name="review_company_application_api",
)
def review_company_application_api(
    vacancy_id: int,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        result = service.get_review(
            user,
            vacancy_id=vacancy_id,
            application_id=application_id,
        )
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_company
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=error_status, detail=str(exc)) from exc

    application = result.application
    if application.student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Application student details are unavailable.",
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

    vacancy = result.vacancy
    return {
        "vacancy": {
            "id": vacancy.id,
            "title": vacancy.title,
        },
        "application": {
            "id": application.id,
            "student_id": application.student_id,
            "vacancy_id": application.vacancy_id,
            "status": application.status,
            "submission_date": application.submission_date,
            "student": {
                "first_name": application.student.first_name,
                "last_name": application.student.last_name,
                "email": application.student.email,
                "education_level": application.student.education_level,
            },
            "documents": documents,
        },
    }


@api_router.put(
    "/company/vacancies/{vacancy_id}/applications/{application_id}",
    response_model=CompanyApplicationStatusResponse,
    name="update_company_application_status_api",
)
def update_company_application_status_api(
    vacancy_id: int,
    application_id: int,
    payload: CompanyApplicationStatusUpdate,
    user: AuthDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        if payload.status == "Shortlisted":
            application = service.shortlist(user, vacancy_id, application_id)
        else:
            application = service.reject(user, vacancy_id, application_id)
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_company
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=error_status, detail=str(exc)) from exc

    return CompanyApplicationStatusResponse(
        id=application.id,
        vacancy_id=application.vacancy_id,
        status=application.status,
    )


@api_router.post(
    "/company/vacancies/{vacancy_id}/applications/finish-review",
    response_model=FinishApplicationReviewResponse,
    name="finish_company_application_review_api",
)
def finish_company_application_review_api(
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        updated_count = service.finish_review(user, vacancy_id)
    except ValueError as exc:
        error_status = (
            status.HTTP_403_FORBIDDEN
            if not user.is_company
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=error_status, detail=str(exc)) from exc

    return FinishApplicationReviewResponse(updated_count=updated_count)
