from app.repositories.user import UserRepository
from app.utilities.security import encrypt_password, verify_password, create_access_token
from app.models.user import ROLE_COMPANY, ROLE_STUDENT
from app.schemas.user import CompanyCreate, RegularUserCreate
from typing import Optional

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(plaintext_password=password, encrypted_password=user.password):
            return None
        access_token = create_access_token(data={"sub": f"{user.id}", "role": user.role})
        return access_token

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = ROLE_STUDENT,
    ):
        create_schema = {
            ROLE_STUDENT: RegularUserCreate,
            ROLE_COMPANY: CompanyCreate,
        }.get(role)
        if create_schema is None:
            raise ValueError("Registration role must be student or company")

        new_user = create_schema(
            username=username, 
            email=email, 
            password=encrypt_password(password)
        )
        return self.user_repo.create(new_user)
