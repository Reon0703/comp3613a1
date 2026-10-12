from fastapi import File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.vacancy import VacancyRepository
from app.services.vacancy_service import VacancyService
from app.utilities.flash import flash
from . import router, templates


@router.get("/company/vacancies", response_class=HTMLResponse, name="company_vacancies_view")
async def company_vacancies_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    repo = VacancyRepository(db)
    vacancies = repo.list_by_company(user.id)
    applicant_counts = repo.application_counts_by_company(user.id)
    return templates.TemplateResponse(
        request=request,
        name="company_vacancies.html",
        context={
            "user": user,
            "vacancies": vacancies,
            "applicant_counts": applicant_counts,
        },
    )


@router.post("/company/vacancies", response_class=HTMLResponse, name="company_vacancies_create")
async def company_vacancies_create(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    title: str = Form(...),
    description: str = Form(...),
    location: str = Form(""),
    status_value: str = Form("Draft", alias="status"),
    vacancy_image: UploadFile | None = File(None),
):
    service = VacancyService(VacancyRepository(db))
    try:
        image_url = None
        if vacancy_image and vacancy_image.filename:
            image_url = service.save_image(
                await vacancy_image.read(),
                vacancy_image.content_type,
            )
        service.create_vacancy(
            company_id=user.id,
            title=title,
            description=description,
            location=location,
            image_url=image_url,
            status=status_value,
        )
        flash(request, "Internship vacancy created successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to create the vacancy right now.", "danger")

    return RedirectResponse(
        url=request.url_for("company_vacancies_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/company/vacancies/{vacancy_id}",
    response_class=HTMLResponse,
    name="company_vacancies_update",
)
async def company_vacancies_update(
    request: Request,
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    title: str = Form(...),
    description: str = Form(...),
    location: str = Form(""),
    status_value: str = Form("Draft", alias="status"),
    vacancy_image: UploadFile | None = File(None),
):
    service = VacancyService(VacancyRepository(db))
    try:
        image_url = None
        if vacancy_image and vacancy_image.filename:
            image_url = service.save_image(
                await vacancy_image.read(),
                vacancy_image.content_type,
            )
        service.update_vacancy(
            vacancy_id=vacancy_id,
            company_id=user.id,
            title=title,
            description=description,
            location=location,
            status=status_value,
            image_url=image_url,
        )
        flash(request, "Internship vacancy updated successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to update the vacancy right now.", "danger")

    return RedirectResponse(
        url=request.url_for("company_vacancies_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
