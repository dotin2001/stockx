from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Mapping
from typing import Any


def generate_order_number() -> str:
    """Return a non-secret, URL-safe public identifier suitable for display."""
    return f"STX-{secrets.token_hex(8).upper()}"


def normalized_request_hash(payload: Mapping[str, Any]) -> str:
    """Hash a normalized request so semantically equivalent retries compare equal."""

    def normalize(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): normalize(value[key]) for key in sorted(value, key=str)}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return value

    encoded = json.dumps(normalize(payload), ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
