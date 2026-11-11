from typing import Annotated

from fastapi import File, Form, HTTPException, UploadFile, status

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.vacancy import VacancyRepository
from app.schemas.vacancy import CompanyVacancyListItem, CompanyVacancyResponse
from app.services.vacancy_service import (
    VacancyAccessError,
    VacancyNotFoundError,
    VacancyService,
)

from . import api_router


def _raise_vacancy_http_error(exc: ValueError) -> None:
    if isinstance(exc, VacancyAccessError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, VacancyNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    ) from exc


@api_router.get(
    "/company/vacancies",
    response_model=list[CompanyVacancyListItem],
)
def list_company_vacancies_api(user: AuthDep, db: SessionDep):
    service = VacancyService(VacancyRepository(db))
    try:
        rows = service.list_company_vacancies_with_counts(user)
    except ValueError as exc:
        _raise_vacancy_http_error(exc)
    return [
        CompanyVacancyListItem.model_validate(
            {
                **vacancy.model_dump(),
                "is_published": vacancy.status == "Published",
                "applicant_count": count,
            }
        )
        for vacancy, count in rows
    ]


@api_router.post(
    "/company/vacancies",
    response_model=CompanyVacancyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_vacancy_api(
    user: AuthDep,
    db: SessionDep,
    title: str = Form(...),
    description: str = Form(...),
    location: str = Form(""),
    field_of_study: str = Form(...),
    status_value: str = Form("Draft", alias="status"),
    vacancy_image: Annotated[UploadFile | None, File()] = None,
):
    image_content = (
        await vacancy_image.read() if vacancy_image and vacancy_image.filename else None
    )
    service = VacancyService(VacancyRepository(db))
    try:
        vacancy = service.create_company_vacancy(
            user=user,
            title=title,
            description=description,
            location=location,
            field_of_study=field_of_study,
            status=status_value,
            image_content=image_content,
            image_content_type=vacancy_image.content_type
            if image_content is not None and vacancy_image
            else None,
        )
    except ValueError as exc:
        _raise_vacancy_http_error(exc)
    return CompanyVacancyResponse.model_validate(vacancy)


@api_router.put(
    "/company/vacancies/{vacancy_id}",
    response_model=CompanyVacancyResponse,
)
async def update_company_vacancy_api(
    vacancy_id: int,
    user: AuthDep,
    db: SessionDep,
    title: str | None = Form(None),
    description: str | None = Form(None),
    location: str | None = Form(None),
    field_of_study: str | None = Form(None),
    status_value: str | None = Form(None, alias="status"),
    vacancy_image: Annotated[UploadFile | None, File()] = None,
):
    image_content = (
        await vacancy_image.read() if vacancy_image and vacancy_image.filename else None
    )
    service = VacancyService(VacancyRepository(db))
    try:
        result = service.update_company_vacancy(
            user=user,
            vacancy_id=vacancy_id,
            title=title,
            description=description,
            location=location,
            status=status_value,
            field_of_study=field_of_study,
            image_content=image_content,
            image_content_type=vacancy_image.content_type
            if image_content is not None and vacancy_image
            else None,
        )
    except ValueError as exc:
        _raise_vacancy_http_error(exc)
    return CompanyVacancyResponse.model_validate(result.vacancy)
