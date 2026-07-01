"""Locators shared across pages (cookie banners, etc.)."""

from __future__ import annotations


class BaseLocators:
    COOKIE_ACCEPT_SELECTORS: tuple[str, ...] = (
        "button[data-gdpr-single-choice-accept]",
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
        "#onetrust-accept-btn-handler",
    )
