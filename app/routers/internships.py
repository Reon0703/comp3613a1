from typing import Annotated
from urllib.parse import urlencode

from fastapi import File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.repositories.internship import InternshipRepository
from app.services.internship_service import InternshipService
from app.utilities.flash import flash
from . import router, templates


def _internship_service(db: SessionDep) -> InternshipService:
    return InternshipService(
        InternshipRepository(db),
        ApplicationRepository(db),
    )


@router.get("/internships", response_class=HTMLResponse, name="browse_internships")
def browse_internships(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    field_of_study: Annotated[list[str] | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    service = _internship_service(db)
    result = service.browse(
        user,
        query=q,
        field_of_study=field_of_study,
        page=page,
    )
    return templates.TemplateResponse(
        request=request,
        name="student_internships.html",
        context={
            "user": user,
            "result": result,
        },
    )


@router.get(
    "/internships/{vacancy_id}",
    response_class=HTMLResponse,
    name="internship_detail_view",
)
def internship_detail_view(
    request: Request,
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = _internship_service(db)
    try:
        vacancy = service.get_vacancy_detail(user, vacancy_id)
        already_applied = service.has_applied(user, vacancy_id)
    except ValueError as exc:
        flash(request, str(exc), "warning")
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="student_internship_detail.html",
        context={
            "user": user,
            "vacancy": vacancy,
            "already_applied": already_applied,
        },
    )


@router.get(
    "/internships/{vacancy_id}/documents/{document_id}/download",
    name="download_vacancy_document",
)
def download_vacancy_document(
    request: Request,
    vacancy_id: int,
    document_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = _internship_service(db)
    try:
        document = service.get_supplementary_document(
            user,
            vacancy_id,
            document_id,
        )
    except ValueError:
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    remote_url = service.external_document_url(document.file_path)
    if remote_url:
        return RedirectResponse(url=remote_url, status_code=status.HTTP_302_FOUND)

    local_path = service.local_document_path(document.file_path)
    if local_path is None:
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return FileResponse(
        path=local_path,
        filename=document.name,
        media_type=document.type or "application/octet-stream",
    )


@router.post(
    "/internships/{vacancy_id}/apply",
    response_class=HTMLResponse,
    name="apply_to_internship",
)
async def apply_to_internship(
    request: Request,
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    application_document: UploadFile = File(...),
    q: str = Form(""),
    field_of_study: list[str] = Form(default=[]),
    page: int = Form(1),
):
    service = _internship_service(db)
    try:
        content = await application_document.read()
        service.apply(
            user=user,
            vacancy_id=vacancy_id,
            filename=application_document.filename or "application.pdf",
            content=content,
        )
        flash(request, "Your application was submitted successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to submit your application right now.", "danger")

    redirect_params = [("page", str(page))]
    if q:
        redirect_params.append(("q", q))
    redirect_params.extend(
        ("field_of_study", field) for field in field_of_study
    )
    redirect_url = f"{request.url_for('browse_internships')}?{urlencode(redirect_params)}"
    return RedirectResponse(
        url=str(redirect_url),
        status_code=status.HTTP_303_SEE_OTHER,
    )