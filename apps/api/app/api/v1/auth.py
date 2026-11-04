from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.schemas.auth import (
    AcceptedResponse,
    ActionTokenRequest,
    AuthResponse,
    EmailActionRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    RegisterRequest,
)
from app.schemas.user import UserPublic
from app.services import auth as auth_service
from app.services.auth_rate_limit import auth_rate_limiter


router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    auth_rate_limiter.check(request, "register", email=str(payload.email))
    user = auth_service.register_user(db, name=payload.name, email=str(payload.email), password=payload.password)
    access_token = auth_service.issue_session(db, response, user)
    db.commit()
    db.refresh(user)
    auth_service.request_email_verification(db, email=user.email)
    return AuthResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    auth_rate_limiter.check(request, "login", email=str(payload.email))
    user = auth_service.authenticate_user(db, email=str(payload.email), password=payload.password)
    access_token = auth_service.issue_session(db, response, user)
    db.commit()
    return AuthResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: DbSession) -> AuthResponse:
    auth_rate_limiter.check(request, "refresh")
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


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(response: Response, db: DbSession, current_user: CurrentUser) -> Response:
    auth_service.revoke_all_refresh_tokens(db, response, current_user)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/verification/request", response_model=AcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def request_verification(payload: EmailActionRequest, request: Request, db: DbSession) -> AcceptedResponse:
    auth_rate_limiter.check(request, "verification", email=str(payload.email))
    auth_service.request_email_verification(db, email=str(payload.email))
    return AcceptedResponse()


@router.post("/verification/confirm", response_model=UserPublic)
def confirm_verification(payload: ActionTokenRequest, db: DbSession) -> UserPublic:
    user = auth_service.verify_email(db, raw_token=payload.token)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/password-reset/request", response_model=AcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: EmailActionRequest, request: Request, db: DbSession) -> AcceptedResponse:
    auth_rate_limiter.check(request, "password_reset", email=str(payload.email))
    auth_service.request_password_reset(db, email=str(payload.email))
    return AcceptedResponse()


@router.post("/password-reset/confirm", response_model=UserPublic)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    response: Response,
    db: DbSession,
) -> UserPublic:
    user = auth_service.reset_password(db, response, raw_token=payload.token, new_password=payload.new_password)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)
