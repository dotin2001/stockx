from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import threading
import time
from typing import Protocol

from fastapi import Request, status

from app.api.errors import APIError
from app.core.config import RateLimitBackend, settings
from app.core.identity import normalize_email


class RateLimitStoreError(RuntimeError):
    pass


class RateLimitStore(Protocol):
    def consume(self, key: str, *, limit: int, window_seconds: int, now: float) -> int | None:
        """Return retry-after seconds when denied, otherwise None."""


@dataclass
class _Bucket:
    count: int
    reset_at: float


class InMemoryRateLimitStore:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def consume(self, key: str, *, limit: int, window_seconds: int, now: float) -> int | None:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or bucket.reset_at <= now:
                self._buckets[key] = _Bucket(count=1, reset_at=now + window_seconds)
                return None
            if bucket.count >= limit:
                return max(1, int(bucket.reset_at - now + 0.999))
            bucket.count += 1
            return None

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()


class RedisRateLimitStore:
    """Atomic, multi-worker fixed-window limiter backed by Redis."""

    _SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    local ttl = redis.call('TTL', KEYS[1])
    return {count, ttl}
    """

    def __init__(self, url: str) -> None:
        from redis import Redis

        self._client = Redis.from_url(url, decode_responses=True, socket_timeout=1, socket_connect_timeout=1)

    def consume(self, key: str, *, limit: int, window_seconds: int, now: float) -> int | None:
        del now
        try:
            count, ttl = self._client.eval(self._SCRIPT, 1, key, window_seconds)
        except Exception as exc:  # Redis exposes several backend-specific exception classes.
            raise RateLimitStoreError("shared rate-limit store is unavailable") from exc
        return max(1, int(ttl)) if int(count) > limit else None


POLICY_LIMITS = {
    "register": lambda: settings.auth_rate_limit_register,
    "login": lambda: settings.auth_rate_limit_login,
    "refresh": lambda: settings.auth_rate_limit_refresh,
    "verification": lambda: settings.auth_rate_limit_verification,
    "password_reset": lambda: settings.auth_rate_limit_password_reset,
}


def _privacy_digest(value: str) -> str:
    return hmac.new(
        settings.secret_key.get_secret_value().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if peer in settings.trusted_proxy_addresses:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            try:
                from ipaddress import ip_address

                return str(ip_address(forwarded))
            except ValueError:
                pass
    return peer


class AuthRateLimiter:
    def __init__(self, store: RateLimitStore) -> None:
        self.store = store

    def check(self, request: Request, policy: str, *, email: str | None = None) -> None:
        limit_factory = POLICY_LIMITS[policy]
        components = [policy, f"client:{_privacy_digest(client_address(request))}"]
        if email:
            components.append(f"account:{_privacy_digest(normalize_email(email))}")
        key = "stockx:auth-rate:" + ":".join(components)
        try:
            retry_after = self.store.consume(
                key,
                limit=limit_factory(),
                window_seconds=settings.auth_rate_limit_window_seconds,
                now=time.time(),
            )
        except RateLimitStoreError:
            if settings.auth_rate_limit_fail_closed:
                raise APIError(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "rate_limit_unavailable",
                    "Authentication is temporarily unavailable.",
                )
            return
        if retry_after is not None:
            raise APIError(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "rate_limit_exceeded",
                "Too many authentication attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def _configured_store() -> RateLimitStore:
    if settings.auth_rate_limit_backend == RateLimitBackend.REDIS:
        return RedisRateLimitStore(settings.auth_rate_limit_redis_url.get_secret_value())
    return InMemoryRateLimitStore()


auth_rate_limiter = AuthRateLimiter(_configured_store())
