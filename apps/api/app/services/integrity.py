from __future__ import annotations

from sqlalchemy.exc import IntegrityError


def matches_integrity_target(error: IntegrityError, targets: tuple[str, ...]) -> bool:
    """Return true only for expected constraint/table-column fragments."""
    text = str(error.orig).lower()
    return any(target.lower() in text for target in targets)
