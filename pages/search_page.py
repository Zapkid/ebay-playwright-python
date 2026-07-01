"""SearchPage — eBay search results with price filter."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import allure
from playwright.sync_api import Locator, Page, TimeoutError as PWTimeoutError

from pages.base_page import BasePage
from pages.locators.search_locators import SearchLocators
from utilities.common_ops import parse_usd_price
from utilities.logger import log
from utilities.shipping import DEFAULT_US_ZIP, us_shipping_query_params
from utilities.timeouts import QUICK_TIMEOUT_MS, SHORT_TIMEOUT_MS

_PLACEHOLDER_LISTING_IDS: frozenset[str] = frozenset({"123456"})


def _listing_id(url: str) -> str | None:
    match = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
    return match.group(1) if match else None


def is_valid_listing_url(url: str) -> bool:
    """Return True for real eBay listing URLs (skip template/placeholder cards)."""
    listing_id: str | None = _listing_id(url)
    if not listing_id or listing_id in _PLACEHOLDER_LISTING_IDS:
        return False
    return len(listing_id) >= 10


class SearchPage(BasePage):
    """eBay search-results page."""

    def __init__(self, page: Page, base_url: str = "https://www.ebay.com") -> None:
        super().__init__(page)
        self._base_url: str = base_url.rstrip("/")

    def go_to_filtered_search(
        self,
        query: str,
        min_price: float,
        max_price: float,
        *,
        ship_zip: str = DEFAULT_US_ZIP,
    ) -> None:
        """Navigate directly to a price-filtered search results page."""
        with allure.step(
            f"Search '{query}' with price ${min_price}–${max_price} (Ship to USA {ship_zip})"
        ):
            params: dict[str, list[str]] = {
                "_nkw": [query],
                "_udlo": [str(int(min_price))],
                "_udhi": [str(int(max_price))],
                "LH_BIN": ["1"],
            }
            params.update(us_shipping_query_params(zip_code=ship_zip))
            query_string: str = urlencode(params, doseq=True)
            url: str = f"{self._base_url}/sch/i.html?{query_string}"
            self.goto(url, wait_until="commit")
            self._wait_for_results()

    def apply_price_filter_via_url(
        self,
        min_price: float,
        max_price: float,
        *,
        ship_zip: str = DEFAULT_US_ZIP,
    ) -> None:
        """Append eBay price, shipping, and Buy-It-Now params to the current search URL."""
        with allure.step(
            f"Set URL price filter ${min_price}–${max_price} (Ship to USA {ship_zip})"
        ):
            parsed = urlparse(self.current_url)
            params: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)
            params["_udlo"] = [str(int(min_price))]
            params["_udhi"] = [str(int(max_price))]
            params["LH_BIN"] = ["1"]
            for key, value in us_shipping_query_params(zip_code=ship_zip).items():
                params[key] = value
            query: str = urlencode(params, doseq=True)
            url: str = urlunparse(parsed._replace(query=query))
            self.goto(url, wait_until="commit")
            self._wait_for_results()

    def _prime_results_page(self) -> None:
        """Scroll results so lazy-loaded card prices render."""
        try:
            self._page.evaluate(
                "() => window.scrollTo(0, Math.max(document.body.scrollHeight / 2, 600))",
            )
            self.loc(SearchLocators.CARD_PRICE).wait_for(
                state="visible",
                timeout=SHORT_TIMEOUT_MS,
            )
        except PWTimeoutError:
            log.debug("[search] Prices not visible after scroll")

    def _wait_for_results(self) -> None:
        """Wait until search result cards appear (no-op when the page is empty)."""
        try:
            self.loc(SearchLocators.PRODUCT_CARDS).wait_for(
                state="attached", timeout=SHORT_TIMEOUT_MS
            )
        except PWTimeoutError:
            log.debug("[search] Result cards not attached within timeout")
            return

        self._prime_results_page()

    def get_card_locators(self) -> Locator:
        """Return all visible product-card locators on the current page."""
        cards: Locator = self.loc_all(SearchLocators.PRODUCT_CARDS)
        if cards.count() == 0:
            cards = self.loc_all(SearchLocators.PRODUCT_CARD_FALLBACK)
        return cards

    def extract_card_data(self, card_locator: Locator) -> dict:
        """Pull URL, price, and title out of a single card locator."""
        link: Locator = card_locator.locator(SearchLocators.CARD_LINK).first
        href: str = link.get_attribute("href") or ""
        if href and not href.startswith("http"):
            href = self._base_url + href

        href = re.split(r"\?", href)[0]

        raw_price: str = self._read_card_price(card_locator)
        if not raw_price:
            try:
                card_locator.scroll_into_view_if_needed(timeout=QUICK_TIMEOUT_MS)
            except PWTimeoutError:
                log.debug("[search] Could not scroll card into view")
            raw_price = self._read_card_price(card_locator)

        price: float | None = parse_usd_price(raw_price)

        title: str = ""
        try:
            title = self.inner_text(
                card_locator.locator(SearchLocators.CARD_TITLE).first,
                timeout=QUICK_TIMEOUT_MS,
            )
            title = re.sub(r"^New Listing\s*", "", title).strip()
        except PWTimeoutError:
            log.debug("[search] Card title not readable")

        return {"url": href, "price": price, "title": title}

    def _read_card_price(self, card_locator: Locator) -> str:
        try:
            return self.inner_text(
                card_locator.locator(SearchLocators.CARD_PRICE).first,
                timeout=QUICK_TIMEOUT_MS,
            )
        except PWTimeoutError:
            log.debug("[search] Card price not readable")
            return ""

    def current_page_number(self) -> int:
        """Return the ``_pgn`` query param from the current search URL (default 1)."""
        parsed = urlparse(self.current_url)
        params: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)
        raw: list[str] = params.get("_pgn", ["1"])
        try:
            return int(raw[0])
        except ValueError:
            return 1

    def collect_listing_ids_on_page(self) -> set[str]:
        """Return valid listing IDs visible on the current results page."""
        ids: set[str] = set()
        cards: Locator = self.get_card_locators()
        count: int = cards.count()

        for i in range(count):
            try:
                href: str = (
                    cards.nth(i).locator(SearchLocators.CARD_LINK).first.get_attribute("href")
                    or ""
                )
                if href and not href.startswith("http"):
                    href = self._base_url + href
                href = re.split(r"\?", href)[0]
                if not is_valid_listing_url(href):
                    continue
                listing_id: str | None = _listing_id(href)
                if listing_id is not None:
                    ids.add(listing_id)
            except PWTimeoutError as exc:
                log.warning(f"[search] Listing ID read timed out for card {i + 1}: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[search] Could not read listing ID for card {i + 1}: {exc!s}")

        return ids

    def has_next_page(self) -> bool:
        """Return True when the Next pagination control is visible."""
        return self.is_visible(SearchLocators.NEXT_PAGE, timeout=QUICK_TIMEOUT_MS)

    def go_to_next_page(self) -> None:
        """Click Next and wait for the next results page to load."""
        with allure.step("Go to next search results page"):
            current_url: str = self.current_url
            next_link: Locator = self.loc(SearchLocators.NEXT_PAGE)
            self.click_locator(next_link, step="Click Next page")
            self.wait_for_load()
            self.wait_for_url_change(current_url, timeout=SHORT_TIMEOUT_MS)
            self._wait_for_results()

    def count_cards(self) -> int:
        """Return the number of product cards on the current results page."""
        return self.get_card_locators().count()

    def has_results(self) -> bool:
        try:
            self.wait_for_selector(
                SearchLocators.PRODUCT_CARDS,
                state="attached",
                timeout=SHORT_TIMEOUT_MS,
            )
        except PWTimeoutError:
            log.debug("[search] No result cards attached")
        return self.count_cards() > 0
