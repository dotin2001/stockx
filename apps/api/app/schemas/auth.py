from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.core.identity import normalize_email
from app.schemas.user import UserPublic


def validate_auth_email(value: str) -> str:
    try:
        result = validate_email(
            value,
            check_deliverability=False,
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise PydanticCustomError("value_error", "Email must be valid.") from exc
    return normalize_email(result.normalized)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return validate_auth_email(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return validate_auth_email(value)


class EmailActionRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return validate_auth_email(value)


class ActionTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class PasswordResetConfirmRequest(ActionTokenRequest):
    new_password: str = Field(min_length=8, max_length=128)


class AcceptedResponse(BaseModel):
    message: str = "If the account is eligible, instructions will be sent."


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
