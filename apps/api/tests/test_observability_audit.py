from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from threading import Event
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import create_access_token
from app.models import AdministrativeAudit, User
from app.services import administrative_audit, observability


ROOT = Path(__file__).resolve().parents[1]


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _event_messages(caplog) -> list[dict]:
    return [json.loads(record.getMessage()) for record in caplog.records if record.name == "stockx.events"]


def test_readiness_succeeds_with_database_and_request_ids_cover_every_response_class(
    client: TestClient,
    monkeypatch,
) -> None:
    assert client.get("/ready").json() == {"status": "ready"}

    success = client.get("/health")
    validation = client.post("/api/v1/auth/register", json={"name": "x"})
    not_found = client.get("/not-a-real-route")

    from app.api.v1 import catalog

    def explode(_db):
        raise RuntimeError("private exception message")

    monkeypatch.setattr(catalog.catalog_service, "list_categories", explode)
    unexpected = client.get("/api/v1/categories")

    assert success.status_code == 200
    assert validation.status_code == 422
    assert not_found.status_code == 404
    assert unexpected.status_code == 500
    for response in (success, validation, not_found, unexpected):
        assert len(response.headers[observability.REQUEST_ID_HEADER]) == 32


def test_structured_event_helper_allows_only_bounded_operational_scalars(caplog) -> None:
    caplog.set_level("INFO", logger="stockx.events")
    observability.emit_event(
        "request_completed",
        request_id="r" * 100,
        route="/api/v1/products/{slug}",
        method="GET",
        status=200,
        duration_ms=1.25,
        raw_path="/api/v1/products/private-customer-slug",
        authorization="Bearer secret",
        email="person@example.test",
        payload={"card": "secret"},
        exception_message="database password secret",
    )
    event = _event_messages(caplog)[-1]
    assert event == {
        "duration_ms": 1.25,
        "event": "request_completed",
        "method": "GET",
        "request_id": "r" * 64,
        "route": "/api/v1/products/{slug}",
        "status": 200,
    }
    serialized = json.dumps(event)
    for forbidden in ("private-customer-slug", "Bearer secret", "person@example.test", "card", "password"):
        assert forbidden not in serialized


def test_error_reporter_success_disabled_rejection_and_timeout_are_failure_isolated(monkeypatch, caplog) -> None:
    caplog.set_level("INFO", logger="stockx.events")
    captured: list[dict[str, str]] = []

    class SuccessfulReporter:
        def report(self, event):
            captured.append(event)

    monkeypatch.setattr(observability, "error_reporter", SuccessfulReporter())
    observability.report_unexpected_error(
        request_id="report-ok",
        route="/api/v1/products/{slug}",
        method="GET",
        exception_type="RuntimeError",
    )
    assert captured == [
        {
            "request_id": "report-ok",
            "route": "/api/v1/products/{slug}",
            "method": "GET",
            "exception_type": "RuntimeError",
        }
    ]

    monkeypatch.setattr(observability, "error_reporter", observability.DisabledErrorReporter())
    observability.report_unexpected_error(
        request_id="report-disabled",
        route="/health",
        method="GET",
        exception_type="RuntimeError",
    )

    class RejectedReporter:
        def report(self, _event):
            raise RuntimeError("secret rejection detail")

    monkeypatch.setattr(observability, "error_reporter", RejectedReporter())
    observability.report_unexpected_error(
        request_id="report-rejected",
        route="/health",
        method="GET",
        exception_type="RuntimeError",
    )

    release = Event()

    class SlowReporter:
        def report(self, _event):
            release.wait(0.1)

    monkeypatch.setattr(observability, "error_reporter", SlowReporter())
    monkeypatch.setattr(settings, "error_reporter_timeout_seconds", 0.01)
    started = perf_counter()
    observability.report_unexpected_error(
        request_id="report-timeout",
        route="/health",
        method="GET",
        exception_type="RuntimeError",
    )
    elapsed = perf_counter() - started
    release.set()

    events = _event_messages(caplog)
    assert elapsed < 0.08
    assert {event.get("reason") for event in events if event["event"] == "error_reporter_failed"} == {
        "timeout",
        "unavailable",
    }
    assert "secret rejection detail" not in "\n".join(record.getMessage() for record in caplog.records)


def test_documented_environment_settings_are_known_and_reporter_configuration_is_validated() -> None:
    for filename in (".env.example", ".env.production.example"):
        keys = {
            line.partition("=")[0].strip().lower()
            for line in (ROOT / filename).read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        application_keys = {key for key in keys if not key.startswith("postgres_")}
        assert application_keys <= set(Settings.model_fields)

    configured = Settings(
        _env_file=None,
        error_reporter_backend="webhook",
        error_reporter_webhook_url="https://errors.example.test/report",
        error_reporter_timeout_seconds=0.5,
    )
    assert configured.error_reporter_timeout_seconds == 0.5


def test_operator_alert_mapping_uses_the_emitted_payment_event_names_and_categories() -> None:
    readme = (ROOT / "README.md").read_text()
    for name in ("payment_attempt_failed", "payment_webhook_failed", "payment_attempt_transition"):
        assert f"`{name}`" in readme
    for category in (
        "provider_creation_failed",
        "async_payment_failed",
        "session_expired",
        "customer_cancelled",
        "verification_failed",
        "unknown_checkout_session",
        "metadata_mismatch",
        "processing_failed",
    ):
        assert f"`{category}`" in readme


def test_audit_writer_drops_unknown_sensitive_and_non_scalar_facts_and_bounds_strings(db_session: Session) -> None:
    actor = User(name="Audit Actor", email="audit-writer@example.test", password_hash="hash", is_admin=True)
    target = User(name="Audit Target", email="audit-writer-target@example.test", password_hash="hash")
    db_session.add_all([actor, target])
    db_session.commit()

    record = administrative_audit.write_audit(
        db_session,
        actor=actor,
        action="product.updated",
        target_type="product",
        target_id=target.id,
        request_id="audit-safe",
        before={
            "name": "n" * 1000,
            "password": "forbidden",
            "token": "forbidden",
            "payload": {"secret": "forbidden"},
        },
        after={"name": "safe", "unknown": "forbidden"},
    )
    assert record.facts == {
        "before": {"name": "n" * 256},
        "after": {"name": "safe"},
    }
    db_session.rollback()
    assert db_session.scalar(select(AdministrativeAudit).where(AdministrativeAudit.request_id == "audit-safe")) is None


def test_audit_model_has_append_only_facts_constraints_and_supported_query_indexes() -> None:
    table = AdministrativeAudit.__table__
    assert {
        "actor_user_id",
        "action",
        "target_type",
        "target_id",
        "request_id",
        "facts",
        "created_at",
    } <= set(table.c.keys())
    assert table.c.actor_user_id.nullable is False
    assert table.c.facts.nullable is False
    assert table.c.created_at.server_default is not None
    constraint_names = {constraint.name for constraint in table.constraints}
    assert {
        "ck_administrative_audits_action_not_blank",
        "ck_administrative_audits_target_type_not_blank",
        "ck_administrative_audits_request_id_not_blank",
        "ck_administrative_audits_facts_bounded",
    } <= constraint_names
    assert {
        "ix_administrative_audits_created_id",
        "ix_administrative_audits_actor_created",
        "ix_administrative_audits_action_created",
        "ix_administrative_audits_target_created",
    } == {index.name for index in table.indexes}


def test_audit_history_is_admin_only_filterable_bounded_and_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = User(name="Audit Admin", email="audit-history-admin@example.test", password_hash="hash", is_admin=True)
    customer = User(name="Audit Customer", email="audit-history-customer@example.test", password_hash="hash")
    db_session.add_all([admin, customer])
    db_session.commit()
    now = datetime.now(UTC)

    first = administrative_audit.write_audit(
        db_session,
        actor=admin,
        action="product.created",
        target_type="product",
        target_id=uuid4(),
        request_id="audit-first",
    )
    second_target = uuid4()
    second = administrative_audit.write_audit(
        db_session,
        actor=admin,
        action="listing.inventory.updated",
        target_type="listing",
        target_id=second_target,
        request_id="audit-second",
    )
    first.created_at = now - timedelta(minutes=2)
    second.created_at = now - timedelta(minutes=1)
    db_session.commit()

    assert client.get("/api/v1/admin/audits").status_code == 401
    assert client.get("/api/v1/admin/audits", headers=_headers(customer)).status_code == 403
    page = client.get("/api/v1/admin/audits?limit=1&offset=0", headers=_headers(admin))
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["items"][0]["request_id"] == "audit-second"

    filtered = client.get(
        "/api/v1/admin/audits",
        params={
            "actor_user_id": str(admin.id),
            "action": "listing.inventory.updated",
            "target_type": "listing",
            "target_id": str(second_target),
            "created_from": (now - timedelta(minutes=1, seconds=1)).isoformat(),
            "created_to": now.isoformat(),
        },
        headers=_headers(admin),
    )
    assert filtered.status_code == 200
    assert [item["request_id"] for item in filtered.json()["items"]] == ["audit-second"]
    assert client.get("/api/v1/admin/audits?limit=101", headers=_headers(admin)).status_code == 422


def test_production_like_failure_workflow_is_correlated_sanitized_alertable_and_audited(
    client: TestClient,
    db_session: Session,
    monkeypatch,
    caplog,
) -> None:
    from app.api.v1 import catalog
    from app.core.config import CheckoutMode
    from app.models import PaymentAttempt, StripeWebhookEvent
    from app.services import stripe_webhooks
    from tests.test_stripe_webhooks import checkout_event, start_local_payment

    caplog.set_level("INFO", logger="stockx.events")
    monkeypatch.setattr(settings, "checkout_mode", CheckoutMode.STRIPE)
    monkeypatch.setattr(settings, "frontend_base_url", "https://shop.example.com")
    monkeypatch.setattr(settings, "stripe_expected_livemode", False)

    class FailedReporter:
        def report(self, _event):
            raise RuntimeError("reporter credential must stay private")

    def explode(_db):
        raise RuntimeError("database credential must stay private")

    monkeypatch.setattr(observability, "error_reporter", FailedReporter())
    monkeypatch.setattr(catalog.catalog_service, "list_categories", explode)

    readiness = client.get("/ready", headers={"X-Request-ID": "prod-ready"})
    failure = client.get("/api/v1/categories", headers={"X-Request-ID": "prod-failure"})
    assert readiness.status_code == 200
    assert readiness.headers["X-Request-ID"] == "prod-ready"
    assert failure.status_code == 500
    assert failure.headers["X-Request-ID"] == "prod-failure"
    assert failure.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected server error occurred.",
        }
    }

    buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="production-like-failure@example.test",
        quantity=1,
        available_quantity=2,
    )
    event, payload = checkout_event(
        event_id="evt_production_like_failed",
        event_type="checkout.session.async_payment_failed",
        started=started,
        provider=provider,
        payment_status="unpaid",
        session_status="complete",
    )
    stripe_webhooks.handle_verified_event(db_session, event=event, payload=payload)
    stripe_webhooks.handle_verified_event(db_session, event=event, payload=payload)

    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    db_session.refresh(listing)
    assert attempt is not None and attempt.status == "failed"
    assert listing.available_quantity == 2
    webhook = db_session.scalar(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == "evt_production_like_failed")
    )
    assert webhook is not None and webhook.processing_status == "processed"
    audits = list(
        db_session.scalars(
            select(AdministrativeAudit)
            .where(AdministrativeAudit.actor_user_id == buyer.id)
            .order_by(AdministrativeAudit.created_at, AdministrativeAudit.id)
        ).all()
    )
    assert {audit.action for audit in audits} == {
        "listing.inventory.checkout_reserved",
        "listing.inventory.checkout_released",
    }

    events = _event_messages(caplog)
    assert any(event["event"] == "application_error" and event["request_id"] == "prod-failure" for event in events)
    assert any(event["event"] == "error_reporter_failed" and event["reason"] == "unavailable" for event in events)
    payment_failures = [
        event
        for event in events
        if event["event"] == "payment_attempt_failed" and event["attempt_id"] == str(attempt.id)
    ]
    assert len(payment_failures) == 1
    assert payment_failures[0]["category"] == "async_payment_failed"
    serialized = "\n".join(record.getMessage() for record in caplog.records)
    assert "reporter credential" not in serialized
    assert "database credential" not in serialized
