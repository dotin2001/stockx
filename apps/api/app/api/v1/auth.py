from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.services import auth as auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: DbSession) -> AuthResponse:
    user = auth_service.register_user(db, name=payload.name, email=payload.email, password=payload.password)
    access_token = auth_service.issue_session(db, response, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: DbSession) -> AuthResponse:
    user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    access_token = auth_service.issue_session(db, response, user)
    db.commit()
    return AuthResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: DbSession) -> AuthResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    user, access_token = auth_service.rotate_refresh_token(db, response, refresh_token)
    db.commit()
    return AuthResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> Response:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    auth_service.revoke_refresh_token(db, response, refresh_token)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
