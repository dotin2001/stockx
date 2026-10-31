from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
import sys

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.refresh_token_retention import (
    DEFAULT_BATCH_SIZE,
    delete_refresh_token_batch,
    preview_refresh_token_cleanup,
    retention_cutoff,
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete one bounded batch of refresh tokens past the fixed retention window."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the bounded batch without deleting records.",
    )
    parser.add_argument("--batch-size", type=positive_int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        cutoff = retention_cutoff(now=clock())
        with session_factory() as db:
            with db.begin():
                if args.dry_run:
                    result = preview_refresh_token_cleanup(
                        db,
                        cutoff=cutoff,
                        batch_size=args.batch_size,
                    )
                else:
                    result = delete_refresh_token_batch(
                        db,
                        cutoff=cutoff,
                        batch_size=args.batch_size,
                    )
    except Exception as exc:
        print(
            f"ERROR: refresh-token cleanup failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    count_label = "would_delete" if result.mode == "dry-run" else "deleted"
    count = result.selected_count if result.mode == "dry-run" else result.deleted_count
    print(
        f"mode={result.mode} cutoff={result.cutoff.isoformat()} "
        f"batch_size={result.batch_size} {count_label}={count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
