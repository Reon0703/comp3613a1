from app.repositories.user import UserRepository
from app.utilities.security import encrypt_password, verify_password, create_access_token
from app.schemas.user import RegularUserCreate, StudentProfileUpdate, UserProfileUpdate
from typing import Optional

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_all_users(self):
        return self.user_repo.get_all_users()

    def update_profile(
        self,
        user_id: int,
        profile_data: UserProfileUpdate,
        profile_image_url: str | None = None,
    ):
        if not profile_data.company_name.strip():
            raise ValueError("Company name is required.")
        return self.user_repo.update_profile(
            user_id,
            profile_data,
            profile_image_url,
        )

    def update_student_profile(
        self,
        user_id: int,
        profile_data: StudentProfileUpdate,
        profile_image_url: str | None = None,
    ):
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_student:
            raise ValueError("Student profile not found.")
        if not profile_data.first_name.strip() or not profile_data.last_name.strip():
            raise ValueError("First and last name are required.")
        return self.user_repo.update_student_profile(
            user_id,
            profile_data,
            profile_image_url,
        )
    