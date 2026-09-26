from __future__ import annotations

import argparse
from collections.abc import Callable
import sys

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.admin_bootstrap import AdminPromotionError, grant_supreme_admin, promote_existing_user


def promote_admin(email: str, *, session_factory: Callable[[], Session] = SessionLocal) -> str:
    with session_factory() as session:
        user = promote_existing_user(session, email=email)
        session.commit()
        return user.email


def promote_supreme_admin(email: str, *, session_factory: Callable[[], Session] = SessionLocal) -> str:
    with session_factory() as session:
        user = grant_supreme_admin(session, email=email)
        session.commit()
        return user.email


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StockX backend administration commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    promote = subparsers.add_parser("promote", help="Promote an existing user to admin.")
    promote.add_argument("email", help="Email address for an existing user.")

    promote_supreme = subparsers.add_parser("promote-supreme", help="Grant supreme-admin access to an existing user.")
    promote_supreme.add_argument("email", help="Email address for an existing user.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, session_factory: Callable[[], Session] = SessionLocal) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "promote":
        try:
            email = promote_admin(args.email, session_factory=session_factory)
        except AdminPromotionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Promoted admin: {email}")
        return 0
    if args.command == "promote-supreme":
        try:
            email = promote_supreme_admin(args.email, session_factory=session_factory)
        except AdminPromotionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Promoted supreme admin: {email}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
