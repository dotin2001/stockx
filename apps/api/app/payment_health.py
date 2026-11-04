from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import json
import sys

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Order, PaymentAttempt, StripeWebhookEvent
from app.services.observability import emit_event


def payment_health_snapshot(
    db: Session,
    *,
    stale_minutes: int = 5,
    now: datetime | None = None,
) -> dict[str, int | str]:
    current = now or datetime.now(UTC)
    stale_before = current - timedelta(minutes=stale_minutes)
    failed_webhooks = db.scalar(
        select(func.count()).select_from(StripeWebhookEvent).where(StripeWebhookEvent.processing_status == "failed")
    ) or 0
    failed_attempts = db.scalar(
        select(func.count()).select_from(PaymentAttempt).where(PaymentAttempt.status == "failed")
    ) or 0
    stale_attempts = db.scalar(
        select(func.count())
        .select_from(PaymentAttempt)
        .join(Order, Order.id == PaymentAttempt.order_id)
        .where(
            or_(
                and_(PaymentAttempt.status == "initializing", PaymentAttempt.updated_at <= stale_before),
                and_(PaymentAttempt.status.in_(("open", "processing")), PaymentAttempt.expires_at <= current),
            )
        )
    ) or 0
    overdue_reservations = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status == "pending_payment",
            Order.inventory_released_at.is_(None),
            Order.reservation_expires_at <= current,
        )
    ) or 0
    health = "degraded" if any((failed_webhooks, failed_attempts, stale_attempts, overdue_reservations)) else "healthy"
    return {
        "status": health,
        "failed_webhooks": failed_webhooks,
        "failed_attempts": failed_attempts,
        "stale_attempts": stale_attempts,
        "overdue_reservations": overdue_reservations,
    }


def main(
    argv: list[str] | None = None,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> int:
    parser = argparse.ArgumentParser(description="Report bounded payment-processing health counts.")
    parser.add_argument("--stale-minutes", type=int, default=5)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.stale_minutes < 0:
        print(json.dumps({"status": "error", "code": "invalid_arguments"}))
        return 2
    try:
        with session_factory() as db:
            snapshot = payment_health_snapshot(db, stale_minutes=args.stale_minutes)
    except Exception:
        print(json.dumps({"status": "error", "code": "database_unavailable"}))
        return 1
    emit_event(
        "payment_health_checked",
        status=snapshot["status"],
        failed_webhooks=snapshot["failed_webhooks"],
        failed_attempts=snapshot["failed_attempts"],
        stale_attempts=snapshot["stale_attempts"],
        overdue_reservations=snapshot["overdue_reservations"],
    )
    print(json.dumps(snapshot, separators=(",", ":"), sort_keys=True))
    return 0 if snapshot["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
