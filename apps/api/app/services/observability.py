from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextvars import ContextVar, Token
import json
import logging
import re
from typing import Any, Protocol
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.config import ErrorReporterBackend, settings


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
EVENT_FIELD_LIMITS = {
    "request_id": 64,
    "route": 128,
    "method": 16,
    "status": 32,
    "duration_ms": None,
    "error_code": 100,
    "exception_type": 128,
    "reason": 64,
    "category": 100,
    "stripe_event_id": 255,
    "attempt_id": 64,
    "previous_status": 32,
    "next_status": 32,
    "source": 64,
    "examined": None,
    "recovered": None,
    "failed": None,
    "still_stale": None,
    "failed_webhooks": None,
    "failed_attempts": None,
    "stale_attempts": None,
    "overdue_reservations": None,
}
logger = logging.getLogger("stockx.events")
_report_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stockx-error-reporter")
_request_id_context: ContextVar[str] = ContextVar("stockx_request_id", default="system")


def accepted_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def bind_request_id(request_id: str) -> Token[str]:
    return _request_id_context.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    _request_id_context.reset(token)


def current_request_id() -> str:
    return _request_id_context.get()


def route_template(scope: dict[str, Any]) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    if not isinstance(path, str):
        return "unmatched"
    # Included FastAPI routers can retain their child template in the scope.
    # Recover only the known static API prefix; never copy the raw path or its
    # personal/product parameter values into telemetry.
    raw_path = scope.get("path")
    if isinstance(raw_path, str) and raw_path.startswith("/api/v1/") and not path.startswith("/api/v1/"):
        return f"/api/v1{path}"
    return path


def emit_event(event: str, **fields: Any) -> None:
    if not EVENT_NAME_PATTERN.fullmatch(event):
        raise ValueError("event name must use bounded lowercase snake case")
    safe = {"event": event}
    for key, value in fields.items():
        if key not in EVENT_FIELD_LIMITS or value is None:
            continue
        if isinstance(value, str):
            safe[key] = value[: EVENT_FIELD_LIMITS[key]]
        elif isinstance(value, (int, float, bool)):
            safe[key] = value
    logger.info(json.dumps(safe, separators=(",", ":"), sort_keys=True))


class ErrorReporter(Protocol):
    def report(self, event: dict[str, str]) -> None: ...


class DisabledErrorReporter:
    def report(self, event: dict[str, str]) -> None:
        del event


class WebhookErrorReporter:
    def __init__(self, url: str) -> None:
        self.url = url

    def report(self, event: dict[str, str]) -> None:
        request = Request(
            self.url,
            data=json.dumps(event).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=settings.error_reporter_timeout_seconds) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError("error reporter rejected the event")


def _configured_reporter() -> ErrorReporter:
    if settings.error_reporter_backend == ErrorReporterBackend.WEBHOOK:
        return WebhookErrorReporter(settings.error_reporter_webhook_url.get_secret_value())
    return DisabledErrorReporter()


error_reporter: ErrorReporter = _configured_reporter()


def report_unexpected_error(*, request_id: str, route: str, method: str, exception_type: str) -> None:
    event = {
        "request_id": request_id,
        "route": route[:128],
        "method": method[:16],
        "exception_type": exception_type[:128],
    }
    future = _report_executor.submit(error_reporter.report, event)
    try:
        future.result(timeout=settings.error_reporter_timeout_seconds)
    except FutureTimeoutError:
        future.cancel()
        emit_event("error_reporter_failed", request_id=request_id, reason="timeout")
    except Exception:
        emit_event("error_reporter_failed", request_id=request_id, reason="unavailable")
