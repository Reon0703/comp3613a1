from app.models.user import UserBase
from sqlmodel import SQLModel
from pydantic import EmailStr
from typing import Optional


class UserUpdate(SQLModel):
    username: Optional[str]
    email: Optional[EmailStr]

class UserProfileUpdate(SQLModel):
    company_name: str
    email: EmailStr
    phone: str = ""
    location: str = ""

class StudentProfileUpdate(SQLModel):
    first_name: str
    last_name: str
    email: EmailStr
    education_level: str = ""
 
class AdminCreate(UserBase):
    role:str = "admin"

class RegularUserCreate(UserBase):
    role:str = "regular_user"

class StudentCreate(UserBase):
    role: str = "regular_user"

class CompanyCreate(UserBase):
    role: str = "company"

class UserResponse(SQLModel):
    id: int
    username:str
    email: EmailStr

class SignupRequest(SQLModel):
    username: str
    email: EmailStr
    password: str
