"""CartPage — eBay shopping cart verification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import allure
from playwright.sync_api import Locator, Page, TimeoutError as PWTimeoutError

from pages.base_page import BasePage
from pages.locators.cart_locators import CartLocators
from utilities.common_ops import parse_usd_price
from utilities.logger import log
from utilities.timeouts import MAX_TIMEOUT_MS, QUICK_TIMEOUT_MS, SHORT_TIMEOUT_MS

_PLACEHOLDER_LISTING_IDS: frozenset[str] = frozenset({"123456"})


@dataclass
class CartItem:
    title: str
    price: float
    quantity: int


@dataclass
class CartState:
    items: list[CartItem] = field(default_factory=list)
    subtotal: float = 0.0
    checkout_enabled: bool = False

    @property
    def calculated_total(self) -> float:
        return sum(i.price * i.quantity for i in self.items)


def _listing_id(url: str) -> str | None:
    match = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
    return match.group(1) if match else None


class CartPage(BasePage):
    """eBay cart page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def open(self, *, timeout_ms: int = SHORT_TIMEOUT_MS) -> "CartPage":
        with allure.step("Open cart page"):
            view_in_cart: Locator = self.roles("link", name=re.compile(r"view in cart", re.I))
            if view_in_cart.count() > 0:
                self.click_locator(view_in_cart.first, step="Open cart via View in cart")
                self.wait_for_load()
            else:
                self._page.goto(
                    CartLocators.CART_URL,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )

            self.accept_cookies_if_present()
            self._wait_for_cart_content(timeout_ms=timeout_ms)
        return self

    def _wait_for_cart_content(self, *, timeout_ms: int = SHORT_TIMEOUT_MS) -> None:
        """Wait until the cart page shows items or an explicit empty state."""
        try:
            cart_ready: str = (
                f"{CartLocators.CHECKOUT_BTN}, "
                f"{CartLocators.EMPTY_CART}, "
                f"{CartLocators.LISTING_LINK}"
            )
            self._page.locator(cart_ready).first.wait_for(
                state="visible", timeout=timeout_ms
            )
        except PWTimeoutError:
            log.debug("[cart] Cart content not visible within timeout")

    def wait_for_items(self, *, min_items: int = 1, timeout_ms: int = SHORT_TIMEOUT_MS) -> bool:
        """Wait until at least *min_items* line items appear on the cart page."""
        deadline_ms: int = timeout_ms
        poll_ms: int = 500
        elapsed_ms: int = 0

        while elapsed_ms <= deadline_ms:
            if self._read_items_count() >= min_items or self._read_subtotal() > 0:
                return True

            if self.is_empty() and not self._has_checkout():
                self._page.wait_for_timeout(poll_ms)
                elapsed_ms += poll_ms
                continue

            self._page.wait_for_timeout(poll_ms)
            elapsed_ms += poll_ms

        return self._read_items_count() >= min_items or self._read_subtotal() > 0

    def _has_checkout(self) -> bool:
        return self.is_visible(CartLocators.CHECKOUT_BTN, timeout=QUICK_TIMEOUT_MS)

    def _read_items_count(self) -> int:
        link_count: int = len(self._read_items_from_listing_links())
        if link_count > 0:
            return link_count
        return min(self.loc_all(CartLocators.ITEM_ROW).count(), 20)

    def _read_subtotal(self) -> float:
        """Read the displayed subtotal."""
        subtotal_from_label: float | None = self._read_subtotal_from_label()
        if subtotal_from_label is not None and subtotal_from_label > 0:
            return subtotal_from_label

        locators: list[str] = CartLocators.SUBTOTAL.split(", ")
        for sel in locators:
            try:
                loc: Locator = self.loc(sel.strip())
                if self.is_locator_visible(loc, timeout=QUICK_TIMEOUT_MS):
                    raw: str = self.inner_text(loc, timeout=QUICK_TIMEOUT_MS)
                    price: float | None = parse_usd_price(raw)
                    if price is not None and price > 0:
                        return price
            except PWTimeoutError:
                log.debug(f"[cart] Subtotal selector '{sel}' not readable")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[cart] Could not read subtotal from '{sel}': {exc!s}")

        return 0.0

    def _read_subtotal_from_label(self) -> float | None:
        """Parse subtotal from the Order summary panel (label + adjacent amount)."""
        labels: Locator = self._page.get_by_text(re.compile(r"^Subtotal$", re.I))
        for i in range(min(labels.count(), 3)):
            label: Locator = labels.nth(i)
            try:
                parent_text: str = label.locator("xpath=..").inner_text(timeout=QUICK_TIMEOUT_MS)
                price: float | None = parse_usd_price(parent_text)
                if price is not None and price > 0:
                    return price

                section_text: str = label.locator(
                    "xpath=ancestor::*[contains(@class,'summary') "
                    "or contains(@class,'Summary')][1]",
                ).inner_text(timeout=QUICK_TIMEOUT_MS)
                for line in section_text.splitlines():
                    if "subtotal" in line.lower():
                        line_price: float | None = parse_usd_price(line)
                        if line_price is not None and line_price > 0:
                            return line_price
            except PWTimeoutError:
                log.debug(f"[cart] Subtotal label {i + 1} not readable")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[cart] Could not parse subtotal label {i + 1}: {exc!s}")

        return None

    def _read_items(self) -> list[CartItem]:
        """Parse cart line items (listing links first — faster and more reliable)."""
        items: list[CartItem] = self._read_items_from_listing_links()
        if items:
            return items
        return self._read_items_from_rows()

    def _read_items_from_rows(self) -> list[CartItem]:
        items: list[CartItem] = []
        rows: Locator = self.loc_all(CartLocators.ITEM_ROW)
        row_count: int = min(rows.count(), 20)

        for i in range(row_count):
            row: Locator = rows.nth(i)
            try:
                title: str = ""
                try:
                    title = self.inner_text(
                        row.locator(CartLocators.ITEM_TITLE).first,
                        timeout=QUICK_TIMEOUT_MS,
                    )
                except PWTimeoutError:
                    log.debug(f"[cart] Line item {i + 1} title not readable")

                raw_price: str = ""
                try:
                    raw_price = self.inner_text(
                        row.locator(CartLocators.ITEM_PRICE).first,
                        timeout=QUICK_TIMEOUT_MS,
                    )
                except PWTimeoutError:
                    log.debug(f"[cart] Line item {i + 1} price not readable")

                if not raw_price:
                    raw_price = row.inner_text(timeout=QUICK_TIMEOUT_MS)

                price: float = parse_usd_price(raw_price) or 0.0

                quantity: int = 1
                try:
                    qty_el: Locator = row.locator(CartLocators.ITEM_QUANTITY).first
                    raw_qty: str = qty_el.input_value()
                    qty_match = re.search(r"\d+", raw_qty)
                    quantity = int(qty_match.group()) if qty_match else 1
                except PWTimeoutError:
                    log.debug(f"[cart] Line item {i + 1} quantity not readable")
                except Exception as exc:  # noqa: BLE001
                    log.warning(f"[cart] Could not parse quantity for line item {i + 1}: {exc!s}")

                if price > 0 or title:
                    items.append(CartItem(title=title.strip(), price=price, quantity=quantity))
            except PWTimeoutError as exc:
                log.warning(f"[cart] Line item {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[cart] Could not parse line item {i + 1}: {exc!s}")

        return items

    def _read_items_from_listing_links(self) -> list[CartItem]:
        """Fallback: derive line items from listing links on the cart page."""
        items: list[CartItem] = []
        links: Locator = self.loc_all(CartLocators.LISTING_LINK)
        seen_ids: set[str] = set()

        for i in range(min(links.count(), 20)):
            link: Locator = links.nth(i)
            try:
                href: str = link.get_attribute("href") or ""
                listing_id: str | None = _listing_id(href)
                if listing_id is None or listing_id in _PLACEHOLDER_LISTING_IDS:
                    continue
                if listing_id in seen_ids or len(listing_id) < 10:
                    continue
                seen_ids.add(listing_id)

                title: str = link.inner_text(timeout=QUICK_TIMEOUT_MS).strip()
                if len(title) < 5:
                    continue

                container_text: str = link.evaluate(
                    """(el) => {
                        const container = el.closest(
                            '[class*="line-item"], [class*="cart-item"], '
                            + '[class*="bucket"], section, article, li'
                        ) || el.parentElement?.parentElement?.parentElement;
                        return container ? container.innerText : el.innerText;
                    }""",
                )
                price: float = parse_usd_price(container_text) or 0.0
                items.append(CartItem(title=title, price=price, quantity=1))
            except PWTimeoutError as exc:
                log.warning(f"[cart] Listing link {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[cart] Could not parse listing link {i + 1}: {exc!s}")

        return items

    def get_state(self) -> CartState:
        """Snapshot the full cart state."""
        with allure.step("Read cart state"):
            checkout: bool = self._has_checkout()

            if self.is_empty() and not checkout:
                return CartState()

            items: list[CartItem] = self._read_items()
            subtotal: float = self._read_subtotal()
            if subtotal <= 0 and items:
                subtotal = sum(item.price * item.quantity for item in items)

            state = CartState(items=items, subtotal=subtotal, checkout_enabled=checkout)

            summary: str = (
                f"Items: {len(items)}  |  "
                f"Subtotal: ${subtotal:.2f}  |  "
                f"Calculated: ${state.calculated_total:.2f}  |  "
                f"Checkout visible: {checkout}"
            )
            allure.attach(summary, name="Cart state", attachment_type=allure.attachment_type.TEXT)
            return state

    def is_empty(self) -> bool:
        return self.is_visible(CartLocators.EMPTY_CART, timeout=QUICK_TIMEOUT_MS)

    def proceed_to_checkout(self) -> None:
        with allure.step("Click checkout"):
            self.click(CartLocators.CHECKOUT_BTN)
            self._page.wait_for_load_state("domcontentloaded", timeout=MAX_TIMEOUT_MS)
