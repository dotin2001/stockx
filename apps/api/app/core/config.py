from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CheckoutMode(StrEnum):
    DISABLED = "disabled"
    MANUAL = "manual"
    STRIPE = "stripe"


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://stockx:stockx@localhost:5432/stockx"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    refresh_cookie_name: str = "stockx_refresh"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    cors_origins: list[str] = []
    checkout_mode: CheckoutMode = CheckoutMode.DISABLED
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    frontend_base_url: str | None = None
    stripe_expected_livemode: bool = False
    stripe_reservation_minutes: int = 30
    stripe_use_fake_provider: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("stripe_secret_key", "stripe_webhook_secret", mode="before")
    @classmethod
    def reject_blank_secrets(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("frontend_base_url", mode="before")
    @classmethod
    def validate_frontend_base_url(cls, value: Any) -> str | None:
        if value is None or value == "":
            return None
        candidate = str(value).strip()
        parsed = urlsplit(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("FRONTEND_BASE_URL must be an absolute HTTP(S) origin without credentials, path, query, or fragment")
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))

    @field_validator("stripe_reservation_minutes")
    @classmethod
    def require_fixed_reservation_duration(cls, value: int) -> int:
        if value != 30:
            raise ValueError("STRIPE_RESERVATION_MINUTES must be 30")
        return value

    @model_validator(mode="after")
    def validate_stripe_mode(self) -> "Settings":
        if self.frontend_base_url:
            parsed = urlsplit(self.frontend_base_url)
            is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            if parsed.scheme != "https" and not (not self.stripe_expected_livemode and is_local):
                raise ValueError("FRONTEND_BASE_URL must use HTTPS except for local Stripe test mode")
            if self.stripe_expected_livemode and is_local:
                raise ValueError("Stripe live mode cannot use a local FRONTEND_BASE_URL")

        if self.checkout_mode != CheckoutMode.STRIPE:
            if self.stripe_use_fake_provider:
                raise ValueError("STRIPE_USE_FAKE_PROVIDER requires CHECKOUT_MODE=stripe")
            return self

        missing = [
            name
            for name, value in (
                ("STRIPE_SECRET_KEY", self.stripe_secret_key),
                ("STRIPE_WEBHOOK_SECRET", self.stripe_webhook_secret),
                ("FRONTEND_BASE_URL", self.frontend_base_url),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"Stripe checkout requires: {', '.join(missing)}")

        secret_key = self.stripe_secret_key.get_secret_value()
        expected_prefix = "sk_live_" if self.stripe_expected_livemode else "sk_test_"
        if not secret_key.startswith(expected_prefix):
            raise ValueError(f"STRIPE_SECRET_KEY must use the {expected_prefix} environment")
        if not self.stripe_webhook_secret.get_secret_value().startswith("whsec_"):
            raise ValueError("STRIPE_WEBHOOK_SECRET must start with whsec_")
        if self.stripe_use_fake_provider:
            parsed = urlsplit(self.frontend_base_url)
            if self.stripe_expected_livemode or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("STRIPE_USE_FAKE_PROVIDER is limited to local Stripe test-mode smoke runs")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )


settings = Settings()
