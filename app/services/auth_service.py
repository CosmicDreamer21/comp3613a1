from app.repositories.user import UserRepository
from app.utilities.security import encrypt_password, verify_password, create_access_token
from app.schemas.user import RegularUserCreate
from typing import Optional
from datetime import timedelta

REMEMBER_ME_DURATION = timedelta(days=30)

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(
        self,
        identifier: str,
        password: str,
        remember_me: bool = False,
    ) -> Optional[str]:
        user = self.user_repo.get_by_identifier(identifier)
        if not user or not verify_password(plaintext_password=password, encrypted_password=user.password):
            return None
        token_data = {"sub": f"{user.id}", "role": user.role}
        if remember_me:
            access_token = create_access_token(
                data=token_data,
                expires_delta=REMEMBER_ME_DURATION,
            )
        else:
            access_token = create_access_token(data=token_data)
        return access_token

    def register_user(self, username: str, email: str, password: str):
        new_user = RegularUserCreate(
            username=username, 
            email=email, 
            password=encrypt_password(password)
        )
        return self.user_repo.create(new_user)
