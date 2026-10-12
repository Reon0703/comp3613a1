from typing import Annotated

from fastapi import File, Form, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.repositories.internship import InternshipRepository
from app.services.application_service import ApplicationService
from app.services.internship_service import InternshipService
from app.utilities.flash import flash
from . import router, templates


def _internship_service(db: SessionDep) -> InternshipService:
    return InternshipService(
        internship_repo=InternshipRepository(db),
        application_repo=ApplicationRepository(db),
    )


@router.get(
    "/student/applications",
    response_class=HTMLResponse,
    name="student_applications_view",
)
def student_applications_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        result = service.list_for_student(user, page=page)
    except ValueError as exc:
        flash(request, str(exc), "warning")
        return RedirectResponse(
            url=request.url_for("user_home_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="student_applications.html",
        context={
            "user": user,
            "result": result,
        },
    )


@router.post(
    "/student/applications/{application_id}/edit",
    response_class=HTMLResponse,
    name="student_application_edit",
)
async def student_application_edit(
    request: Request,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
    application_document: UploadFile = File(...),
    page: int = Form(1),
):
    service = _internship_service(db)
    try:
        service.replace_application_document(
            user=user,
            application_id=application_id,
            filename=application_document.filename or "application.pdf",
            content=await application_document.read(),
        )
        flash(request, "Application document updated successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to update your application right now.", "danger")

    return RedirectResponse(
        url=str(request.url_for("student_applications_view").include_query_params(page=page)),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/student/applications/{application_id}/delete",
    response_class=HTMLResponse,
    name="student_application_delete",
)
def student_application_delete(
    request: Request,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
    page: int = Form(1),
):
    service = _internship_service(db)
    try:
        service.delete_application(user, application_id)
        flash(request, "Application deleted successfully.", "success")
        remaining = ApplicationService(ApplicationRepository(db)).list_for_student(
            user,
            page=page,
        )
        page = min(page, max(remaining.pagination.total_pages, 1))
    except ValueError as exc:
        flash(request, str(exc), "warning")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to delete your application right now.", "danger")
        page = 1

    return RedirectResponse(
        url=str(request.url_for("student_applications_view").include_query_params(page=page)),
        status_code=status.HTTP_303_SEE_OTHER,
    )
