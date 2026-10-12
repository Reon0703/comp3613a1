from typing import Annotated

from fastapi import Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.services.application_service import ApplicationService
from app.utilities.flash import flash
from . import router, templates


def _application_service(db: SessionDep) -> ApplicationService:
    return ApplicationService(ApplicationRepository(db))


@router.get(
    "/company/vacancies/{vacancy_id}/applications",
    response_class=HTMLResponse,
    name="company_vacancy_applications_view",
)
def company_vacancy_applications_view(
    request: Request,
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    education_level: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    # === STUDENT SNIPPET: thin review list handler ===
    service = _application_service(db)
    try:
        result = service.browse(
            user,
            vacancy_id=vacancy_id,
            query=q,
            education_level=education_level,
            page=page,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("company_vacancies_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="company_vacancy_applications.html",
        context={
            "user": user,
            "result": result,
        },
    )
    # === END STUDENT SNIPPET ===


@router.get(
    "/company/vacancies/{vacancy_id}/applications/{application_id}",
    response_class=HTMLResponse,
    name="company_application_review_view",
)
def company_application_review_view(
    request: Request,
    vacancy_id: int,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = _application_service(db)
    try:
        result = service.get_review(user, vacancy_id, application_id)
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("company_vacancies_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="company_application_review.html",
        context={
            "user": user,
            "result": result,
        },
    )


@router.post(
    "/company/vacancies/{vacancy_id}/applications/{application_id}/shortlist",
    response_class=HTMLResponse,
    name="company_application_shortlist",
)
def company_application_shortlist(
    request: Request,
    vacancy_id: int,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = _application_service(db)
    try:
        service.shortlist(user, vacancy_id, application_id)
        flash(request, "Applicant added to the shortlist.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for(
            "company_application_review_view",
            vacancy_id=vacancy_id,
            application_id=application_id,
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/company/vacancies/{vacancy_id}/applications/{application_id}/reject",
    response_class=HTMLResponse,
    name="company_application_reject",
)
def company_application_reject(
    request: Request,
    vacancy_id: int,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = _application_service(db)
    try:
        service.reject(user, vacancy_id, application_id)
        flash(request, "Applicant rejected.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for(
            "company_application_review_view",
            vacancy_id=vacancy_id,
            application_id=application_id,
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )
