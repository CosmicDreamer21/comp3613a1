from fastapi import HTTPException, status

from app.dependencies import AuthDep, SessionDep
from app.repositories.user import UserRepository
from app.schemas.api import LoginRequest, MeResponse, TokenResponse
from app.services.auth_service import REMEMBER_ME_DURATION, AuthService
from app.utilities.security import create_access_token
from . import api_router


@api_router.post("/auth/login", response_model=TokenResponse, tags=["API Auth"])
def api_login(body: LoginRequest, db: SessionDep):
    """Exchange username/email + password for a bearer token."""
    repo = UserRepository(db)
    token = AuthService(repo).authenticate_user(
        body.identifier, body.password, body.remember_me
    )
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = repo.get_by_identifier(body.identifier)
    return TokenResponse(access_token=token, role=user.role)


@api_router.get("/auth/me", response_model=MeResponse, tags=["API Auth"])
def api_me(user: AuthDep):
    return user
