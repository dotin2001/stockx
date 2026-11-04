from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings
from app.core.security import create_access_token, hash_refresh_token
from app.main import app
from app.models import AccountChallenge, AdministrativeAudit, RefreshToken, User
from app.services import auth as auth_service
from app.services.action_delivery import CaptureActionDelivery, action_delivery
from app.services.auth_rate_limit import AuthRateLimiter, InMemoryRateLimitStore, client_address
from app.services.auth_rate_limit import RateLimitStoreError
from app.services.action_delivery import ActionDeliveryError
from app.payment_health import payment_health_snapshot


PRODUCTION_BASE = {
    "app_environment": "production",
    "database_url": "postgresql+psycopg://api:strong-password@db.example.com/stockx",
    "secret_key": "a-production-signing-secret-that-is-long-enough",
    "refresh_cookie_secure": True,
    "refresh_cookie_httponly": True,
    "cors_origins": ["https://shop.example.com"],
    "auth_rate_limit_backend": "redis",
    "auth_rate_limit_redis_url": "redis://rate-limit.example.com/0",
    "action_delivery_backend": "webhook",
    "action_delivery_webhook_url": "https://delivery.example.com/actions",
    "_env_file": None,
}


def test_auth_hardening_models_expose_required_columns_relationships_and_constraints() -> None:
    assert RefreshToken.__table__.c.family_id.nullable is False
    assert User.__table__.c.verified_at.nullable is True
    assert User.account_challenges.property.mapper.class_ is AccountChallenge
    assert AccountChallenge.user.property.mapper.class_ is User
    constraint_names = {constraint.name for constraint in AccountChallenge.__table__.constraints}
    index_names = {index.name for index in AccountChallenge.__table__.indexes}
    assert {
        "ck_account_challenges_purpose_known",
        "ck_account_challenges_expires_after_creation",
    }.issubset(constraint_names)
    assert "ix_account_challenges_user_purpose_created" in index_names
    assert AccountChallenge.__table__.c.token_hash.unique is True


def test_local_settings_are_usable_and_production_rejects_unsafe_values_without_echoing_them() -> None:
    assert Settings(_env_file=None).app_environment == "development"
    assert Settings(**PRODUCTION_BASE).cors_origins == ["https://shop.example.com"]
    unsafe = (
        {"secret_key": "super-sensitive-but-short"},
        {"refresh_cookie_secure": False},
        {"refresh_cookie_httponly": False},
        {"cors_origins": ["*"]},
        {"cors_origins": ["http://localhost:3000"]},
        {"cors_origins": ["https://shop.example.com/path"]},
        {"database_url": "sqlite:///production.db"},
        {"auth_rate_limit_backend": "memory"},
        {"auth_rate_limit_fail_closed": False},
        {"action_delivery_backend": "capture"},
    )
    for override in unsafe:
        secret_value = next(iter(override.values()))
        with pytest.raises(ValidationError) as captured:
            Settings(**{**PRODUCTION_BASE, **override})
        if isinstance(secret_value, str) and "sensitive" in secret_value:
            assert secret_value not in str(captured.value)


def test_stripe_production_configuration_matrix() -> None:
    disabled = Settings(**PRODUCTION_BASE)
    assert disabled.checkout_mode == "disabled"
    live = Settings(
        **PRODUCTION_BASE,
        checkout_mode="stripe",
        stripe_secret_key="sk_live_example",
        stripe_webhook_secret="whsec_example",
        frontend_base_url="https://shop.example.com",
        stripe_expected_livemode=True,
    )
    assert live.stripe_expected_livemode is True
    with pytest.raises(ValidationError):
        Settings(
            **PRODUCTION_BASE,
            checkout_mode="stripe",
            stripe_secret_key="sk_test_example",
            stripe_webhook_secret="whsec_example",
            frontend_base_url="https://shop.example.com",
        )


def test_readiness_failure_is_sanitized_while_liveness_stays_up(client: TestClient) -> None:
    class UnavailableSession:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("postgresql://user:password@secret-host/db"))

    def unavailable_db():
        yield UnavailableSession()

    original = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = unavailable_db
    try:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/ready")
    finally:
        app.dependency_overrides[get_db] = original
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_not_ready"
    assert "password" not in response.text


def test_request_id_is_accepted_or_replaced_on_success_and_error(client: TestClient) -> None:
    accepted = client.get("/health", headers={"X-Request-ID": "req-123.test"})
    invalid = client.get("/missing", headers={"X-Request-ID": "unsafe request/id"})
    oversized = client.get("/health", headers={"X-Request-ID": "x" * 65})
    assert accepted.headers["X-Request-ID"] == "req-123.test"
    assert invalid.headers["X-Request-ID"] != "unsafe request/id"
    assert len(invalid.headers["X-Request-ID"]) == 32
    assert len(oversized.headers["X-Request-ID"]) == 32


def test_rate_limiter_counts_successes_and_failures_with_retry_after(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.auth_rate_limit_login", 2)
    monkeypatch.setattr("app.core.config.settings.auth_rate_limit_window_seconds", 60)
    limiter = AuthRateLimiter(InMemoryRateLimitStore())
    scope = {"type": "http", "client": ("203.0.113.10", 1234), "headers": []}
    request = Request(scope)
    limiter.check(request, "login", email="person@example.com")
    limiter.check(request, "login", email="person@example.com")
    with pytest.raises(Exception) as captured:
        limiter.check(request, "login", email="person@example.com")
    assert captured.value.code == "rate_limit_exceeded"
    assert int(captured.value.headers["Retry-After"]) > 0


def test_rate_limit_store_failure_policy_is_explicit(monkeypatch) -> None:
    class FailedStore:
        def consume(self, *args, **kwargs):
            raise RateLimitStoreError("offline")

    request = Request({"type": "http", "client": ("203.0.113.11", 1234), "headers": []})
    limiter = AuthRateLimiter(FailedStore())
    monkeypatch.setattr("app.core.config.settings.auth_rate_limit_fail_closed", True)
    with pytest.raises(Exception) as captured:
        limiter.check(request, "password_reset", email="person@example.com")
    assert captured.value.code == "rate_limit_unavailable"
    monkeypatch.setattr("app.core.config.settings.auth_rate_limit_fail_closed", False)
    limiter.check(request, "password_reset", email="person@example.com")


def test_rate_limit_policies_use_independent_limits_private_keys_and_trusted_proxy(monkeypatch) -> None:
    class RecordingStore:
        def __init__(self) -> None:
            self.calls = []

        def consume(self, key, *, limit, window_seconds, now):
            self.calls.append((key, limit, window_seconds, now))
            return None

    configured_limits = {
        "register": 11,
        "login": 12,
        "refresh": 13,
        "verification": 14,
        "password_reset": 15,
    }
    for policy, limit in configured_limits.items():
        monkeypatch.setattr(f"app.core.config.settings.auth_rate_limit_{policy}", limit)
    monkeypatch.setattr("app.core.config.settings.trusted_proxy_addresses", ["10.0.0.8"])
    store = RecordingStore()
    limiter = AuthRateLimiter(store)
    request = Request(
        {
            "type": "http",
            "client": ("10.0.0.8", 1234),
            "headers": [(b"x-forwarded-for", b"203.0.113.20, 10.0.0.8")],
        }
    )

    assert client_address(request) == "203.0.113.20"
    for policy in configured_limits:
        limiter.check(request, policy, email="Private.Person@Example.com")

    assert [call[1] for call in store.calls] == list(configured_limits.values())
    keys = [call[0] for call in store.calls]
    assert all("203.0.113.20" not in key for key in keys)
    assert all("private.person@example.com" not in key for key in keys)
    assert len(set(keys)) == len(configured_limits)

    untrusted = Request(
        {
            "type": "http",
            "client": ("198.51.100.9", 1234),
            "headers": [(b"x-forwarded-for", b"203.0.113.21")],
        }
    )
    assert client_address(untrusted) == "198.51.100.9"


def test_registration_rejects_invalid_email_without_creating_a_user(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Invalid", "email": "not-an-address", "password": "password123"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert db_session.scalar(select(User).where(User.name == "Invalid")) is None


def _challenge(
    db_session: Session,
    user: User,
    *,
    raw_token: str,
    purpose: str,
    expired: bool = False,
) -> AccountChallenge:
    now = datetime.now(UTC)
    challenge = AccountChallenge(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_refresh_token(raw_token),
        created_at=now - timedelta(hours=2) if expired else now,
        expires_at=now - timedelta(hours=1) if expired else now + timedelta(hours=1),
    )
    db_session.add(challenge)
    db_session.commit()
    return challenge


def test_verification_requests_are_non_enumerating_and_tokens_enforce_expiry_and_purpose(
    client: TestClient,
    db_session: Session,
    caplog,
) -> None:
    assert isinstance(action_delivery, CaptureActionDelivery)
    action_delivery.clear()
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "Verify", "email": "verify@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    action_delivery.clear()
    caplog.set_level(logging.INFO)

    known = client.post("/api/v1/auth/verification/request", json={"email": "verify@example.com"})
    unknown = client.post("/api/v1/auth/verification/request", json={"email": "missing@example.com"})
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert known.status_code == 202
    raw_token = action_delivery.messages[-1].token
    persisted = db_session.scalar(
        select(AccountChallenge).where(AccountChallenge.token_hash == hash_refresh_token(raw_token))
    )
    assert persisted is not None and persisted.purpose == "email_verification"
    assert raw_token not in known.text + unknown.text
    assert raw_token not in "\n".join(record.getMessage() for record in caplog.records)

    user = db_session.scalar(select(User).where(User.email == "verify@example.com"))
    _challenge(
        db_session,
        user,
        raw_token="expired-verification-token-value-000000000000",
        purpose="email_verification",
        expired=True,
    )
    _challenge(
        db_session,
        user,
        raw_token="wrong-purpose-token-value-0000000000000000",
        purpose="password_reset",
    )
    for token in (
        "expired-verification-token-value-000000000000",
        "wrong-purpose-token-value-0000000000000000",
    ):
        response = client.post("/api/v1/auth/verification/confirm", json={"token": token})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_action_token"


def test_password_reset_is_non_enumerating_policy_checked_and_isolates_other_users(
    client: TestClient,
    db_session: Session,
) -> None:
    assert isinstance(action_delivery, CaptureActionDelivery)
    action_delivery.clear()
    first = client.post(
        "/api/v1/auth/register",
        json={"name": "Reset One", "email": "reset-one@example.com", "password": "password123"},
    )
    assert first.status_code == 201
    first_refresh = client.cookies.get("stockx_refresh")
    second_user = auth_service.register_user(
        db_session,
        name="Reset Two",
        email="reset-two@example.com",
        password="password123",
    )
    _second_record, second_refresh = auth_service.create_refresh_token_record(db_session, second_user)
    db_session.commit()
    action_delivery.clear()

    known = client.post("/api/v1/auth/password-reset/request", json={"email": "reset-one@example.com"})
    unknown = client.post("/api/v1/auth/password-reset/request", json={"email": "missing@example.com"})
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    reset_token = action_delivery.messages[-1].token
    invalid_password = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "short"},
    )
    assert invalid_password.status_code == 422
    reset = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "new-password-123"},
    )
    assert reset.status_code == 200
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={first_refresh}"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={second_refresh}"},
    ).status_code == 200
    reused = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "another-password-123"},
    )
    assert reused.status_code == 400
    first_user = db_session.scalar(select(User).where(User.email == "reset-one@example.com"))
    expired_reset = "expired-reset-token-value-000000000000000000"
    _challenge(
        db_session,
        first_user,
        raw_token=expired_reset,
        purpose="password_reset",
        expired=True,
    )
    expired = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": expired_reset, "new_password": "another-password-123"},
    )
    assert expired.status_code == 400
    assert expired.json()["error"]["code"] == "invalid_action_token"


def test_refresh_replay_and_logout_all_revoke_only_the_target_family_or_user(
    client: TestClient,
    db_session: Session,
) -> None:
    first_user = auth_service.register_user(
        db_session,
        name="Family One",
        email="family-one@example.com",
        password="password123",
    )
    first_family_record, first_family_raw = auth_service.create_refresh_token_record(db_session, first_user)
    _other_family_record, other_family_raw = auth_service.create_refresh_token_record(db_session, first_user)
    second_user = auth_service.register_user(
        db_session,
        name="Family Two",
        email="family-two@example.com",
        password="password123",
    )
    _second_user_record, second_user_raw = auth_service.create_refresh_token_record(db_session, second_user)
    db_session.commit()

    client.cookies.clear()
    rotated = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={first_family_raw}"},
    )
    assert rotated.status_code == 200
    rotated_raw = client.cookies.get("stockx_refresh")
    client.cookies.clear()
    second_rotation = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={rotated_raw}"},
    )
    assert second_rotation.status_code == 200
    descendant_raw = client.cookies.get("stockx_refresh")
    client.cookies.clear()
    replay = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={first_family_raw}"},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_refresh_token"
    assert "stockx_refresh=" in replay.headers["set-cookie"]
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={descendant_raw}"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={other_family_raw}"},
    ).status_code == 200

    client.cookies.clear()
    logout_all = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {create_access_token(first_user.id)}"},
    )
    assert logout_all.status_code == 204
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={second_user_raw}"},
    ).status_code == 200
    db_session.expire_all()
    assert all(
        token.revoked_at is not None
        for token in db_session.scalars(select(RefreshToken).where(RefreshToken.user_id == first_user.id))
    )
    assert first_family_record.family_id is not None


def test_verification_reset_and_logout_all_are_single_use_and_revoke_sessions(
    client: TestClient,
    db_session: Session,
) -> None:
    assert isinstance(action_delivery, CaptureActionDelivery)
    action_delivery.clear()
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "Lifecycle", "email": "lifecycle@example.com", "password": "password123"},
    )
    assert registered.status_code == 201
    first_refresh = client.cookies.get("stockx_refresh")
    verification = action_delivery.messages[-1]
    challenge = db_session.scalar(
        select(AccountChallenge).where(AccountChallenge.purpose == "email_verification")
    )
    assert challenge.token_hash == hash_refresh_token(verification.token)
    assert verification.token not in challenge.token_hash

    verified = client.post("/api/v1/auth/verification/confirm", json={"token": verification.token})
    assert verified.status_code == 200
    assert verified.json()["is_verified"] is True
    assert client.post("/api/v1/auth/verification/confirm", json={"token": verification.token}).status_code == 400

    reset_requested = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "lifecycle@example.com"},
    )
    assert reset_requested.status_code == 202
    reset_token = action_delivery.messages[-1].token
    reset = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "new-password-123"},
    )
    assert reset.status_code == 200
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"stockx_refresh={first_refresh}"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "lifecycle@example.com", "password": "password123"},
    ).status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "lifecycle@example.com", "password": "new-password-123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post("/api/v1/auth/logout-all", headers=headers).status_code == 204
    user = db_session.scalar(select(User).where(User.email == "lifecycle@example.com"))
    assert db_session.scalar(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ) is None


def test_audit_model_is_bounded_and_contains_only_allowlisted_facts(db_session: Session) -> None:
    actor = User(
        name="Audit Admin",
        email="audit-admin@example.com",
        password_hash="hash",
        is_admin=True,
        is_supreme_admin=True,
    )
    target = User(name="Target", email="audit-target@example.com", password_hash="hash")
    db_session.add_all([actor, target])
    db_session.commit()
    from app.services.admin_users import promote_user_by_id

    promote_user_by_id(db_session, user_id=target.id, actor=actor, request_id="audit-request")
    db_session.commit()
    record = db_session.scalar(select(AdministrativeAudit))
    assert record.request_id == "audit-request"
    assert record.facts == {"before": {"is_admin": False}, "after": {"is_admin": True}}


def test_audit_write_rolls_back_with_privileged_mutation(db_session: Session) -> None:
    actor = User(
        name="Rollback Admin",
        email="rollback-admin@example.com",
        password_hash="hash",
        is_admin=True,
        is_supreme_admin=True,
    )
    target = User(name="Rollback Target", email="rollback-target@example.com", password_hash="hash")
    db_session.add_all([actor, target])
    db_session.commit()
    from app.services.admin_users import promote_user_by_id

    promote_user_by_id(db_session, user_id=target.id, actor=actor, request_id="rollback-request")
    db_session.rollback()
    db_session.refresh(target)
    assert target.is_admin is False
    assert db_session.scalar(select(AdministrativeAudit)) is None


def test_logs_use_route_templates_and_reporter_failures_do_not_replace_response(
    client: TestClient,
    monkeypatch,
    caplog,
) -> None:
    from app.api.v1 import catalog
    from app.services import observability

    class FailedReporter:
        def report(self, event):
            raise RuntimeError("reporter secret must not escape")

    def explode(_db):
        raise RuntimeError("password=forbidden token=forbidden")

    caplog.set_level("INFO", logger="stockx.events")
    monkeypatch.setattr(observability, "error_reporter", FailedReporter())
    monkeypatch.setattr(catalog.catalog_service, "list_categories", explode)
    response = client.get(
        "/api/v1/categories",
        headers={"Authorization": "Bearer forbidden-secret", "X-Request-ID": "correlated-500"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "correlated-500" in logs
    assert "/api/v1/categories" in logs
    assert "error_reporter_failed" in logs
    for forbidden in ("forbidden-secret", "password=forbidden", "token=forbidden"):
        assert forbidden not in logs


def test_delivery_failure_is_reported_without_leaking_action_token(db_session: Session, monkeypatch, caplog) -> None:
    class FailedDelivery:
        def send(self, *, purpose, email, token):
            raise ActionDeliveryError("offline")

    user = User(name="Delivery", email="delivery@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    caplog.set_level("ERROR", logger="stockx.auth")
    monkeypatch.setattr("app.services.auth.action_delivery", FailedDelivery())
    auth_service.request_email_verification(db_session, email=user.email)
    challenge = db_session.scalar(select(AccountChallenge).where(AccountChallenge.user_id == user.id))
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert challenge is not None
    assert "action_delivery_failed" in logs
    assert challenge.token_hash not in logs


def test_payment_health_snapshot_is_bounded_and_categorical() -> None:
    class Counts:
        def __init__(self):
            self.values = iter((2, 3, 4, 5))

        def scalar(self, _statement):
            return next(self.values)

    snapshot = payment_health_snapshot(Counts(), now=datetime.now(UTC))
    assert snapshot == {
        "status": "degraded",
        "failed_webhooks": 2,
        "failed_attempts": 3,
        "stale_attempts": 4,
        "overdue_reservations": 5,
    }


def test_new_auth_and_audit_routes_are_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/v1/auth/logout-all",
        "/api/v1/auth/verification/request",
        "/api/v1/auth/verification/confirm",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
        "/api/v1/admin/audits",
    }.issubset(paths)
    assert "202" in paths["/api/v1/auth/verification/request"]["post"]["responses"]
    assert "202" in paths["/api/v1/auth/password-reset/request"]["post"]["responses"]
    unauthenticated = client.post("/api/v1/auth/logout-all")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "not_authenticated"
