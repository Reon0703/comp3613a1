from typing import Literal

from pydantic import EmailStr
from sqlmodel import SQLModel

RegistrationRole = Literal["regular_user", "company"]


class SigninRequest(SQLModel):
    username: str
    password: str


class SignupRequest(SQLModel):
    username: str
    email: str
    password: str
    role: RegistrationRole


class ApiLoginRequest(SQLModel):
    username: str
    password: str


class ApiRegisterRequest(SQLModel):
    username: str
    email: EmailStr
    password: str
    role: RegistrationRole = "regular_user"


class ApiUserResponse(SQLModel):
    id: int
    username: str
    email: EmailStr
    role: str


class ApiLoginResponse(SQLModel):
    user: ApiUserResponse


class ApiRegisterResponse(SQLModel):
    message: str
    user: ApiUserResponse


class CurrentUserResponse(ApiUserResponse):
    first_name: str | None = None
    last_name: str | None = None
    education_level: str | None = None
    company_name: str | None = None
    location: str | None = None
    phone: str | None = None
    profile_image_url: str | None = None
