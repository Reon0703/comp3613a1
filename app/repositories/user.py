from sqlmodel import Session, select, func
from app.models.user import UserBase, User
from typing import Optional, Tuple
from app.utilities.pagination import Pagination
from app.schemas.user import StudentProfileUpdate, UserProfileUpdate, UserUpdate
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: UserBase) -> Optional[User]:
        try:
            user_db = User.model_validate(user_data)
            self.db.add(user_db)
            self.db.commit()
            self.db.refresh(user_db)
            return user_db
        except Exception as e:
            logger.error(f"An error occurred while saving user: {e}")
            self.db.rollback()
            raise

    def search_users(self, query: str, page:int=1, limit:int=10) -> Tuple[list[User], Pagination]:
        offset = (page - 1) * limit
        db_qry = select(User)
        if query:
            db_qry = db_qry.where(
                User.username.ilike(f"%{query}%") | User.email.ilike(f"%{query}%")
            )
        count_qry = select(func.count()).select_from(db_qry.subquery())
        count_todos = self.db.exec(count_qry).one()

        users = self.db.exec(db_qry.offset(offset).limit(limit)).all()
        pagination = Pagination(total_count=count_todos, current_page=page, limit=limit)

        return users, pagination

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.exec(select(User).where(User.username == username)).one_or_none()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def set_profile_image(self, user: User, profile_image_url: str) -> User:
        user.profile_image_url = profile_image_url
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_profile(
        self,
        user_id: int,
        profile_data: UserProfileUpdate,
        profile_image_url: str | None = None,
    ) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise Exception("Invalid user id given")

        user.company_name = profile_data.company_name.strip()
        user.email = profile_data.email
        user.phone = profile_data.phone.strip()
        user.location = profile_data.location.strip()
        if profile_image_url:
            user.profile_image_url = profile_image_url

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as exc:
            logger.error("An error occurred while updating profile: %s", exc)
            self.db.rollback()
            raise

    def update_student_profile(
        self,
        user_id: int,
        profile_data: StudentProfileUpdate,
        profile_image_url: str | None = None,
    ) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise Exception("Invalid user id given")

        user.first_name = profile_data.first_name.strip()
        user.last_name = profile_data.last_name.strip()
        user.email = profile_data.email
        user.education_level = profile_data.education_level.strip()
        if profile_image_url:
            user.profile_image_url = profile_image_url

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as exc:
            logger.error("An error occurred while updating student profile: %s", exc)
            self.db.rollback()
            raise

    def get_all_users(self) -> list[User]:
        return self.db.exec(select(User)).all()

    def update_user(self, user_id:int, user_data: UserUpdate)->User:
        user = self.db.get(User, user_id)
        if not user:
            raise Exception("Invalid user id given")
        if user_data.username:
            user.username = user_data.username
        if user_data.email:
            user.email = user_data.email
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            logger.error(f"An error occurred while updating user: {e}")
            self.db.rollback()
            raise

    def delete_user(self, user_id: int):
        user = self.db.get(User, user_id)
        if not user:
            raise Exception("User doesn't exist")
        try:
            self.db.delete(user)
            self.db.commit()
        except Exception as e:
            logger.error(f"An error occurred while deleting user: {e}")
            self.db.rollback()
            raise
