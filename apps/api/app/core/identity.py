from __future__ import annotations


def normalize_email(value: str) -> str:
    normalized = str(value).strip().lower()
    if not normalized:
        raise ValueError("Email must not be blank.")
    return normalized


def normalize_sku(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
