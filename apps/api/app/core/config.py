from __future__ import annotations

from enum import StrEnum
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class CheckoutMode(StrEnum):
    DISABLED = "disabled"
    MANUAL = "manual"
    STRIPE = "stripe"


class RateLimitBackend(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"


class ActionDeliveryBackend(StrEnum):
    CAPTURE = "capture"
    WEBHOOK = "webhook"
    DISABLED = "disabled"


class ErrorReporterBackend(StrEnum):
    DISABLED = "disabled"
    WEBHOOK = "webhook"


DEVELOPMENT_SECRETS = {"dev-secret-change-me", "change-me-in-local-env", "changeme", "secret"}


def _is_local_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    normalized = hostname.rstrip(".").lower()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _normalize_origin(value: str, *, setting_name: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if (
        candidate == "*"
        or parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError(
            f"{setting_name} must contain absolute HTTP(S) origins without credentials, path, query, or fragment"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{setting_name} contains an invalid port") from exc
    host = parsed.hostname.lower().rstrip(".")
    if ":" in host:
        host = f"[{host}]"
    default_port = (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)
    netloc = host if port is None or default_port else f"{host}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, "", "", ""))


class Settings(BaseSettings):
    app_environment: ApplicationEnvironment = ApplicationEnvironment.DEVELOPMENT
    database_url: SecretStr = SecretStr("postgresql+psycopg://stockx:stockx@localhost:5432/stockx")
    database_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    secret_key: SecretStr = SecretStr("dev-secret-change-me")
    secret_key_min_length: int = Field(default=32, ge=32, le=128)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)
    refresh_cookie_name: str = "stockx_refresh"
    refresh_cookie_secure: bool = False
    refresh_cookie_httponly: bool = True
    refresh_cookie_samesite: str = "lax"
    cors_origins: list[str] = []
    checkout_mode: CheckoutMode = CheckoutMode.DISABLED
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    frontend_base_url: str | None = None
    stripe_expected_livemode: bool = False
    stripe_reservation_minutes: int = 30
    stripe_use_fake_provider: bool = False
    auth_rate_limit_backend: RateLimitBackend = RateLimitBackend.MEMORY
    auth_rate_limit_redis_url: SecretStr | None = None
    auth_rate_limit_window_seconds: int = Field(default=300, ge=1, le=3600)
    auth_rate_limit_register: int = Field(default=1000, ge=1, le=10000)
    auth_rate_limit_login: int = Field(default=1000, ge=1, le=10000)
    auth_rate_limit_refresh: int = Field(default=1000, ge=1, le=10000)
    auth_rate_limit_verification: int = Field(default=1000, ge=1, le=10000)
    auth_rate_limit_password_reset: int = Field(default=1000, ge=1, le=10000)
    auth_rate_limit_fail_closed: bool = True
    trusted_proxy_addresses: list[str] = []
    action_delivery_backend: ActionDeliveryBackend = ActionDeliveryBackend.CAPTURE
    action_delivery_webhook_url: SecretStr | None = None
    verification_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    password_reset_token_expire_minutes: int = Field(default=30, ge=5, le=240)
    error_reporter_backend: ErrorReporterBackend = ErrorReporterBackend.DISABLED
    error_reporter_webhook_url: SecretStr | None = None
    error_reporter_timeout_seconds: float = Field(default=1.0, gt=0, le=2)

    @field_validator("database_url", "secret_key", mode="before")
    @classmethod
    def validate_required_secrets(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("setting must not be blank")
            return value.strip()
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        values = [origin.strip() for origin in value.split(",")] if isinstance(value, str) else list(value)
        normalized = [_normalize_origin(str(origin), setting_name="CORS_ORIGINS") for origin in values if str(origin).strip()]
        if len(set(normalized)) != len(normalized):
            raise ValueError("CORS_ORIGINS contains duplicate normalized origins")
        return normalized

    @field_validator("stripe_secret_key", "stripe_webhook_secret", mode="before")
    @classmethod
    def reject_blank_optional_secrets(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "auth_rate_limit_redis_url",
        "action_delivery_webhook_url",
        "error_reporter_webhook_url",
        mode="before",
    )
    @classmethod
    def reject_blank_redis_url(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("trusted_proxy_addresses", mode="before")
    @classmethod
    def parse_trusted_proxy_addresses(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        values = [item.strip() for item in value.split(",")] if isinstance(value, str) else list(value)
        normalized: list[str] = []
        for item in values:
            try:
                normalized.append(str(ip_address(str(item).strip())))
            except ValueError as exc:
                raise ValueError("TRUSTED_PROXY_ADDRESSES contains an invalid IP address") from exc
        return normalized

    @field_validator("frontend_base_url", mode="before")
    @classmethod
    def validate_frontend_base_url(cls, value: Any) -> str | None:
        if value is None or value == "":
            return None
        return _normalize_origin(str(value), setting_name="FRONTEND_BASE_URL")

    @field_validator("refresh_cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("REFRESH_COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @field_validator("stripe_reservation_minutes")
    @classmethod
    def require_fixed_reservation_duration(cls, value: int) -> int:
        if value != 30:
            raise ValueError("STRIPE_RESERVATION_MINUTES must be 30")
        return value

    @model_validator(mode="after")
    def validate_deployment(self) -> "Settings":
        production = self.app_environment == ApplicationEnvironment.PRODUCTION
        database_url = self.database_url.get_secret_value()
        secret_key = self.secret_key.get_secret_value()

        if production:
            if secret_key.lower() in DEVELOPMENT_SECRETS or len(secret_key) < self.secret_key_min_length:
                raise ValueError("SECRET_KEY does not meet production strength requirements")
            if not self.refresh_cookie_secure:
                raise ValueError("REFRESH_COOKIE_SECURE must be enabled in production")
            if not self.refresh_cookie_httponly:
                raise ValueError("REFRESH_COOKIE_HTTPONLY must be enabled in production")
            if self.refresh_cookie_samesite == "none" and not self.refresh_cookie_secure:
                raise ValueError("REFRESH_COOKIE_SAMESITE=none requires REFRESH_COOKIE_SECURE")
            parsed_database = urlsplit(database_url)
            if parsed_database.scheme not in {"postgresql", "postgresql+psycopg"} or not parsed_database.hostname:
                raise ValueError("DATABASE_URL must select a PostgreSQL database in production")
            if database_url == "postgresql+psycopg://stockx:stockx@localhost:5432/stockx":
                raise ValueError("DATABASE_URL must not use the development default in production")
            for origin in self.cors_origins:
                parsed = urlsplit(origin)
                if parsed.scheme != "https" or _is_local_host(parsed.hostname):
                    raise ValueError("CORS_ORIGINS must contain only non-local HTTPS origins in production")
            if self.auth_rate_limit_backend != RateLimitBackend.REDIS or self.auth_rate_limit_redis_url is None:
                raise ValueError("AUTH_RATE_LIMIT_REDIS_URL and the redis backend are required in production")
            if not self.auth_rate_limit_fail_closed:
                raise ValueError("AUTH_RATE_LIMIT_FAIL_CLOSED must be enabled in production")
            if self.action_delivery_backend != ActionDeliveryBackend.WEBHOOK:
                raise ValueError("ACTION_DELIVERY_BACKEND must select a production adapter")

        if self.auth_rate_limit_backend == RateLimitBackend.REDIS and self.auth_rate_limit_redis_url is None:
            raise ValueError("AUTH_RATE_LIMIT_REDIS_URL is required for the redis backend")
        if self.action_delivery_backend == ActionDeliveryBackend.WEBHOOK:
            if self.action_delivery_webhook_url is None:
                raise ValueError("ACTION_DELIVERY_WEBHOOK_URL is required for the webhook adapter")
            parsed_delivery = urlsplit(self.action_delivery_webhook_url.get_secret_value())
            if parsed_delivery.scheme != "https" or not parsed_delivery.hostname:
                raise ValueError("ACTION_DELIVERY_WEBHOOK_URL must be an absolute HTTPS URL")
        if self.error_reporter_backend == ErrorReporterBackend.WEBHOOK:
            if self.error_reporter_webhook_url is None:
                raise ValueError("ERROR_REPORTER_WEBHOOK_URL is required for the webhook reporter")
            parsed_reporter = urlsplit(self.error_reporter_webhook_url.get_secret_value())
            if parsed_reporter.scheme != "https" or not parsed_reporter.hostname:
                raise ValueError("ERROR_REPORTER_WEBHOOK_URL must be an absolute HTTPS URL")

        if self.frontend_base_url:
            parsed_frontend = urlsplit(self.frontend_base_url)
            is_local = _is_local_host(parsed_frontend.hostname)
            if parsed_frontend.scheme != "https" and not (not self.stripe_expected_livemode and is_local):
                raise ValueError("FRONTEND_BASE_URL must use HTTPS except for local Stripe test mode")
            if self.stripe_expected_livemode and is_local:
                raise ValueError("Stripe live mode cannot use a local FRONTEND_BASE_URL")

        has_stripe_key = self.stripe_secret_key is not None
        has_webhook_secret = self.stripe_webhook_secret is not None
        if self.checkout_mode != CheckoutMode.STRIPE:
            if has_stripe_key or has_webhook_secret or self.stripe_expected_livemode or self.stripe_use_fake_provider:
                raise ValueError("Stripe credentials and switches require CHECKOUT_MODE=stripe")
            return self

        missing = [
            name
            for name, present in (
                ("STRIPE_SECRET_KEY", has_stripe_key),
                ("STRIPE_WEBHOOK_SECRET", has_webhook_secret),
                ("FRONTEND_BASE_URL", self.frontend_base_url is not None),
            )
            if not present
        ]
        if missing:
            raise ValueError(f"Stripe checkout requires: {', '.join(missing)}")

        stripe_key = self.stripe_secret_key.get_secret_value()
        expected_prefix = "sk_live_" if self.stripe_expected_livemode else "sk_test_"
        if not stripe_key.startswith(expected_prefix):
            raise ValueError(f"STRIPE_SECRET_KEY must use the {expected_prefix} environment")
        if not self.stripe_webhook_secret.get_secret_value().startswith("whsec_"):
            raise ValueError("STRIPE_WEBHOOK_SECRET must use the configured endpoint-secret format")
        if production and not self.stripe_expected_livemode:
            raise ValueError("Stripe checkout in production requires STRIPE_EXPECTED_LIVEMODE")
        if production and self.stripe_use_fake_provider:
            raise ValueError("STRIPE_USE_FAKE_PROVIDER is unavailable in production")
        if self.stripe_use_fake_provider:
            parsed_frontend = urlsplit(self.frontend_base_url)
            if self.stripe_expected_livemode or not _is_local_host(parsed_frontend.hostname):
                raise ValueError("STRIPE_USE_FAKE_PROVIDER is limited to local Stripe test-mode smoke runs")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )


settings = Settings()
