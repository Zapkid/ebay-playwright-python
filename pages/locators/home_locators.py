"""Locators for the eBay home page."""

from __future__ import annotations


class HomeLocators:
    SEARCH_INPUT: str = "#gh-ac, input[type='text'][aria-label*='Search']"
    SIGN_IN_LINK: str = "#signin-btn, a[href*='signin.ebay.com'], a:has-text('Sign in')"
    SHIP_TO_MENU: str = "[class*='gh-ship-to']"
    SHIP_TO_COUNTRY_BUTTON: str = ".shipto__country-list button.menu-button__button"
    SHIP_TO_ZIP_INPUT: str = (
        "input[name='postalCode'], "
        "input[name='zipCode'], "
        "input[aria-label*='ZIP'], "
        "input[aria-label*='Zip'], "
        "input[placeholder*='ZIP'], "
        "input[placeholder*='Zip']"
    )
    SHIP_TO_DONE: str = "button:has-text('Done')"
