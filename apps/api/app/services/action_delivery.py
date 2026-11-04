from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
from urllib.request import Request, urlopen

from app.core.config import ActionDeliveryBackend, settings


class ActionDeliveryError(RuntimeError):
    pass


class ActionDelivery(Protocol):
    def send(self, *, purpose: str, email: str, token: str) -> None: ...


@dataclass(frozen=True)
class CapturedAction:
    purpose: str
    email: str
    token: str


class CaptureActionDelivery:
    """Local/test adapter. Tokens are available to tests but are never logged."""

    def __init__(self) -> None:
        self.messages: list[CapturedAction] = []

    def send(self, *, purpose: str, email: str, token: str) -> None:
        self.messages.append(CapturedAction(purpose=purpose, email=email, token=token))

    def clear(self) -> None:
        self.messages.clear()


class WebhookActionDelivery:
    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, *, purpose: str, email: str, token: str) -> None:
        body = json.dumps({"purpose": purpose, "email": email, "token": token}).encode("utf-8")
        request = Request(self.url, data=body, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=2) as response:
                if not 200 <= response.status < 300:
                    raise ActionDeliveryError("action delivery adapter rejected the message")
        except ActionDeliveryError:
            raise
        except Exception as exc:
            raise ActionDeliveryError("action delivery adapter is unavailable") from exc


class DisabledActionDelivery:
    def send(self, *, purpose: str, email: str, token: str) -> None:
        del purpose, email, token
        raise ActionDeliveryError("action delivery is disabled")


def _configured_delivery() -> ActionDelivery:
    if settings.action_delivery_backend == ActionDeliveryBackend.WEBHOOK:
        return WebhookActionDelivery(settings.action_delivery_webhook_url.get_secret_value())
    if settings.action_delivery_backend == ActionDeliveryBackend.DISABLED:
        return DisabledActionDelivery()
    return CaptureActionDelivery()


action_delivery: ActionDelivery = _configured_delivery()
