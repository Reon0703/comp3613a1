from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository
from app.schemas.user import (
    ProfileUpdateResponse,
    StudentProfileUpdate,
    UserProfileUpdate,
)
from app.services.user_service import (
    ProfileRoleError,
    ProfileValidationError,
    UserService,
)

from . import api_router


def _update_profile_response(
    update_profile,
    payload: StudentProfileUpdate | UserProfileUpdate,
    user_id: int,
):
    try:
        update_profile(user_id, payload)
    except ProfileRoleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ProfileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from exc


@api_router.put(
    "/students/me",
    response_model=ProfileUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_student_profile_api(
    payload: StudentProfileUpdate,
    user: AuthDep,
    db: SessionDep,
):
    service = UserService(UserRepository(db))
    _update_profile_response(service.update_student_profile, payload, user.id)
    return ProfileUpdateResponse(message="student profile updated")


@api_router.put(
    "/companies/me",
    response_model=ProfileUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_company_profile_api(
    payload: UserProfileUpdate,
    user: AuthDep,
    db: SessionDep,
):
    service = UserService(UserRepository(db))
    _update_profile_response(service.update_profile, payload, user.id)
    return ProfileUpdateResponse(message="company profile updated")
