from pydantic import BaseModel, Field, field_validator

from app.core.identity import normalize_email
from app.schemas.user import UserPublic


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        value = normalize_email(value)
        if "@" not in value:
            raise ValueError("Email must be valid.")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return normalize_email(value)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
