from fastapi import HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ApiLoginRequest,
    ApiLoginResponse,
    ApiRegisterRequest,
    ApiRegisterResponse,
    ApiUserResponse,
    CurrentUserResponse,
)
from app.services.auth_service import AuthService
from app.utilities.security import access_token_cookie_kwargs

from . import api_router


@api_router.post(
    "/auth/register",
    response_model=ApiRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_api_user(payload: ApiRegisterRequest, db: SessionDep):
    service = AuthService(UserRepository(db))
    try:
        user = service.register_user(
            role=payload.role,
            username=payload.username,
            email=str(payload.email),
            password=payload.password,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        ) from exc

    return {
        "message": "account created",
        "user": ApiUserResponse.model_validate(user),
    }


@api_router.post("/auth/login", response_model=ApiLoginResponse)
def login_api_user(
    payload: ApiLoginRequest,
    db: SessionDep,
    response: Response,
):
    repository = UserRepository(db)
    token = AuthService(repository).authenticate_user(
        payload.username,
        payload.password,
    )
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user = repository.get_by_username(payload.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    response.set_cookie(
        key="access_token",
        value=token,
        **access_token_cookie_kwargs(),
    )
    return {"user": ApiUserResponse.model_validate(user)}


@api_router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def logout_api_user(user: AuthDep):
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="access_token",
        **access_token_cookie_kwargs(),
    )
    return response


@api_router.get("/me", response_model=CurrentUserResponse)
def get_api_current_user(user: AuthDep):
    return user
