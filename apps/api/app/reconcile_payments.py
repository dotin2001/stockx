from __future__ import annotations

import argparse
from collections.abc import Callable
import sys

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.payments import CheckoutSessionProvider, StripeCheckoutSessionProvider
from app.services.payment_checkout import reconcile_stale_attempts
from app.services.stripe_webhooks import reprocess_stripe_event


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile stale Stripe payment attempts safely.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--stale-minutes", type=int, default=5)
    parser.add_argument("--event-id", help="Reprocess one stored Stripe event from current provider state.")
    return parser.parse_args(argv)


def configured_provider() -> CheckoutSessionProvider:
    if settings.stripe_secret_key is None:
        raise RuntimeError("STRIPE_SECRET_KEY is required for payment reconciliation")
    return StripeCheckoutSessionProvider(settings.stripe_secret_key.get_secret_value())


def main(
    argv: list[str] | None = None,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    provider_factory: Callable[[], CheckoutSessionProvider] = configured_provider,
) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.limit < 1 or args.stale_minutes < 0:
        print("ERROR: --limit must be positive and --stale-minutes cannot be negative", file=sys.stderr)
        return 2
    try:
        provider = provider_factory()
        with session_factory() as db:
            if args.event_id:
                outcomes = [
                    reprocess_stripe_event(
                        db,
                        stripe_event_id=args.event_id,
                        provider=provider,
                    )
                ]
            else:
                outcomes = reconcile_stale_attempts(
                    db,
                    provider=provider,
                    stale_minutes=args.stale_minutes,
                    limit=args.limit,
                )
    except Exception as exc:
        print(f"ERROR: payment reconciliation failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    for outcome in outcomes:
        detail = f" ({outcome.detail})" if outcome.detail else ""
        print(f"{outcome.attempt_id}: {outcome.outcome}{detail}")
    print(f"Reconciled {len(outcomes)} payment attempt(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
