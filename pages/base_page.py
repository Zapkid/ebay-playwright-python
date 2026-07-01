"""BasePage — shared behaviour for all page objects."""

from __future__ import annotations

import re
from typing import Pattern

import allure
from playwright.sync_api import Locator, Page, TimeoutError as PWTimeoutError

from pages.locators.base_locators import BaseLocators
from utilities.logger import log
from utilities.timeouts import MAX_TIMEOUT_MS, QUICK_TIMEOUT_MS


class BasePage:
    """Abstract base providing common Playwright helpers and Allure steps."""

    def __init__(self, page: Page) -> None:
        self._page = page

    def loc(self, selector: str) -> Locator:
        """Return the first element matching *selector*."""
        return self._page.locator(selector).first

    def loc_all(self, selector: str) -> Locator:
        """Return all elements matching *selector*."""
        return self._page.locator(selector)

    def role(
        self,
        role: str,
        *,
        name: str | Pattern[str] | None = None,
    ) -> Locator:
        """Return the first element located by ARIA role (and optional name)."""
        if name is not None:
            return self._page.get_by_role(role, name=name).first
        return self._page.get_by_role(role).first

    def roles(
        self,
        role: str,
        *,
        name: str | Pattern[str] | None = None,
    ) -> Locator:
        """Return all elements located by ARIA role (and optional name)."""
        if name is not None:
            return self._page.get_by_role(role, name=name)
        return self._page.get_by_role(role)

    def text(self, pattern: str | Pattern[str]) -> Locator:
        """Return the first element whose text matches *pattern*."""
        return self._page.get_by_text(pattern).first

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        with allure.step(f"Navigate to {url}"):
            self._page.goto(url, wait_until=wait_until)

    def reload(self) -> None:
        with allure.step("Reload page"):
            self._page.reload(wait_until="domcontentloaded")

    def wait_for_load(self, state: str = "domcontentloaded") -> None:
        self._page.wait_for_load_state(state)

    def click(self, selector: str, *, timeout: int | None = None) -> None:
        with allure.step(f"Click '{selector}'"):
            self.loc(selector).click(timeout=timeout)

    def click_locator(self, locator: Locator, *, step: str | None = None) -> None:
        label: str = step or "Click element"
        with allure.step(label):
            locator.click()

    def fill(self, selector: str, value: str) -> None:
        with allure.step(f"Fill '{selector}' with '{value}'"):
            self.loc(selector).fill(value)

    def fill_locator(self, locator: Locator, value: str, *, step: str | None = None) -> None:
        label: str = step or f"Fill with '{value}'"
        with allure.step(label):
            locator.fill(value)

    def type_locator(
        self,
        locator: Locator,
        text: str,
        *,
        delay: int = 0,
        step: str | None = None,
    ) -> None:
        label: str = step or f"Type '{text}'"
        with allure.step(label):
            locator.type(text, delay=delay)

    def press_locator(self, locator: Locator, key: str, *, step: str | None = None) -> None:
        label: str = step or f"Press {key}"
        with allure.step(label):
            locator.press(key)

    def select_option(self, selector: str, value: str) -> None:
        with allure.step(f"Select option '{value}' in '{selector}'"):
            self.loc(selector).select_option(value)

    def select_option_label(self, locator: Locator, label: str) -> None:
        with allure.step(f"Select option '{label}'"):
            locator.select_option(label=label)

    def get_text(self, selector: str) -> str:
        return (self.loc(selector).inner_text() or "").strip()

    def inner_text(
        self,
        locator: Locator,
        *,
        timeout: int = QUICK_TIMEOUT_MS,
    ) -> str:
        return (locator.inner_text(timeout=timeout) or "").strip()

    def count(self, selector: str) -> int:
        return self.loc_all(selector).count()

    def is_visible(self, selector: str, *, timeout: int = QUICK_TIMEOUT_MS) -> bool:
        try:
            self.loc(selector).wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeoutError:
            return False

    def is_locator_visible(self, locator: Locator, *, timeout: int = QUICK_TIMEOUT_MS) -> bool:
        try:
            locator.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeoutError:
            return False

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: int | None = None,
    ) -> Locator:
        loc: Locator = self.loc(selector)
        loc.wait_for(state=state, timeout=timeout)
        return loc

    def wait_for_url(self, pattern: str, *, timeout: int = MAX_TIMEOUT_MS) -> None:
        self._page.wait_for_url(f"**{pattern}**", timeout=timeout)

    def wait_for_url_change(self, previous_url: str, *, timeout: int = MAX_TIMEOUT_MS) -> None:
        try:
            self._page.wait_for_url(lambda url: url != previous_url, timeout=timeout)
        except PWTimeoutError:
            log.warning(f"[page] URL did not change from {previous_url!r}")

    @property
    def current_url(self) -> str:
        return self._page.url

    @property
    def title(self) -> str:
        return self._page.title()

    def accept_cookies_if_present(self) -> None:
        """Dismiss cookie / GDPR banners if they appear."""
        for sel in BaseLocators.COOKIE_ACCEPT_SELECTORS:
            if not self.is_visible(sel, timeout=QUICK_TIMEOUT_MS):
                continue
            banner: Locator = self.loc(sel)
            try:
                banner.click()
                banner.wait_for(state="hidden", timeout=QUICK_TIMEOUT_MS)
                break
            except PWTimeoutError:
                log.debug(f"[page] Cookie banner '{sel}' did not dismiss")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[page] Could not dismiss cookie banner '{sel}': {exc!s}")
