from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import json
import logging
import re
from typing import Any, Protocol
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.config import ErrorReporterBackend, settings


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
logger = logging.getLogger("stockx.events")
_report_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stockx-error-reporter")


def accepted_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


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
    safe = {"event": event}
    for key, value in fields.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            safe[key] = value[:256] if isinstance(value, str) else value
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
