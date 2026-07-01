"""HomePage — eBay landing page with global search bar."""

from __future__ import annotations

import re

import allure
from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.locators.home_locators import HomeLocators
from utilities.logger import log
from utilities.shipping import DEFAULT_US_ZIP
from utilities.timeouts import QUICK_TIMEOUT_MS, SHORT_TIMEOUT_MS


class HomePage(BasePage):
    """eBay home page."""

    def __init__(self, page: Page, base_url: str = "https://www.ebay.com") -> None:
        super().__init__(page)
        self._base_url: str = base_url.rstrip("/")

    def open(self) -> "HomePage":
        with allure.step("Open eBay home page"):
            self.goto(self._base_url)
            self.accept_cookies_if_present()
        return self

    def set_shipping_to_usa(self, zip_code: str = DEFAULT_US_ZIP) -> None:
        """Set Ship-to country to United States so listing pages show USD prices."""
        with allure.step(f"Set shipping to USA (ZIP {zip_code})"):
            self.goto(f"{self._base_url}?_stpos={zip_code}")
            self.accept_cookies_if_present()

            ship_to: str = HomeLocators.SHIP_TO_MENU
            if not self.is_visible(ship_to, timeout=SHORT_TIMEOUT_MS):
                log.warning("[home] Ship-to menu not visible — relying on _stpos URL param")
                return

            self.click(ship_to, timeout=SHORT_TIMEOUT_MS)

            country_button: str = HomeLocators.SHIP_TO_COUNTRY_BUTTON
            if self.is_visible(country_button, timeout=QUICK_TIMEOUT_MS):
                self.click(country_button, timeout=QUICK_TIMEOUT_MS)
                united_states = self._page.get_by_role("menuitemradio", name="United States")
                if united_states.count() > 0:
                    united_states.first.click()
                else:
                    log.warning("[home] United States option not found in Ship-to menu")

            zip_input = self.loc(HomeLocators.SHIP_TO_ZIP_INPUT)
            if self.is_locator_visible(zip_input, timeout=QUICK_TIMEOUT_MS):
                self.fill_locator(zip_input, zip_code, step=f"Enter ZIP {zip_code}")

            done_button = self._page.get_by_role("button", name=re.compile(r"^Done$", re.I))
            if done_button.count() > 0:
                self.click_locator(done_button.first, step="Confirm Ship-to location")

            log.info(f"[home] Ship-to set to United States (ZIP {zip_code})")

    def search(self, query: str) -> None:
        """Type *query* into the global search bar and submit."""
        with allure.step(f"Search for '{query}'"):
            search_input = self.loc(HomeLocators.SEARCH_INPUT)
            search_input.fill("")
            self.type_locator(search_input, query, delay=60, step=f"Type '{query}'")
            self.press_locator(search_input, "Enter", step="Submit search")
            self.wait_for_load()

    def click_sign_in(self) -> None:
        with allure.step("Click Sign in"):
            self.click(HomeLocators.SIGN_IN_LINK)
            self.wait_for_load()
