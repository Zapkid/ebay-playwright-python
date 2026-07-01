"""Workflow: ensure an authenticated eBay session from saved storage state."""

from __future__ import annotations

import allure
from playwright.sync_api import Page

from pages.login_page import LoginPage


def ensure_logged_in(page: Page, *, base_url: str) -> bool:
    """Return True when the loaded session is valid on eBay."""
    login_page: LoginPage = LoginPage(page)

    with allure.step("[auth] Verify saved session"):
        page.goto(base_url, wait_until="domcontentloaded")
        login_page.accept_cookies_if_present()
        if login_page.is_logged_in():
            return True

        allure.attach(
            "Saved session is missing or expired.\n"
            "Run: uv run python -m scripts.bootstrap_ebay_auth",
            name="auth-error",
        )
        return False
