from importlib.metadata import version

import stripe

from app.payments import STRIPE_API_VERSION


def test_supported_stripe_sdk_and_api_version_are_pinned() -> None:
    assert version("stripe") == "16.0.0"
    assert stripe._api_version._ApiVersion.CURRENT == STRIPE_API_VERSION
