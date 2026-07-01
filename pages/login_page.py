"""LoginPage — eBay sign-in flow."""

from __future__ import annotations

import allure
from playwright.sync_api import TimeoutError as PWTimeoutError

from pages.base_page import BasePage
from pages.locators.login_locators import LoginLocators
from utilities.logger import log
from utilities.timeouts import QUICK_TIMEOUT_MS, SHORT_TIMEOUT_MS


class LoginPage(BasePage):
    """eBay sign-in page."""

    def open(self) -> "LoginPage":
        with allure.step("Open eBay sign-in page"):
            self.goto(LoginLocators.SIGN_IN_URL)
            self.accept_cookies_if_present()
        return self

    def enter_username(self, username: str) -> None:
        with allure.step("Enter username"):
            self.fill(LoginLocators.EMAIL_INPUT, username)

    def click_continue(self) -> None:
        with allure.step("Click Continue"):
            self.click(LoginLocators.CONTINUE_BTN)
            self.wait_for_load()

    def enter_password(self, password: str) -> None:
        with allure.step("Enter password"):
            self.fill(LoginLocators.PASSWORD_INPUT, password)

    def click_sign_in(self) -> None:
        with allure.step("Click Sign in"):
            self.click(LoginLocators.SIGN_IN_BTN)
            self.wait_for_load()

    def login(self, username: str, password: str) -> bool:
        """Full sign-in flow. Returns True if account nav is visible after login."""
        with allure.step(f"Login as {username}"):
            self.open()
            self.enter_username(username)
            self.click_continue()

            try:
                self.loc(LoginLocators.PASSWORD_INPUT).wait_for(
                    state="visible", timeout=SHORT_TIMEOUT_MS
                )
            except PWTimeoutError:
                allure.attach(
                    "Password field not visible after Continue", name="login-warning"
                )
                return False

            self.enter_password(password)
            self.click_sign_in()

            try:
                self.loc(LoginLocators.LOGGED_IN_SIGNAL).wait_for(
                    state="visible", timeout=SHORT_TIMEOUT_MS
                )
                return True
            except PWTimeoutError:
                error: str = ""
                try:
                    error = self.get_text(LoginLocators.ERROR_MSG)
                except PWTimeoutError:
                    log.debug("[login] No error message displayed")
                allure.attach(error or "Unknown login error", name="login-error")
                return False

    def is_logged_in(self) -> bool:
        return self.is_visible(LoginLocators.LOGGED_IN_SIGNAL, timeout=QUICK_TIMEOUT_MS)
