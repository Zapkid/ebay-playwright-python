"""ProductPage — individual eBay listing with variant selection and add-to-cart."""

from __future__ import annotations

import re

import allure
from playwright.sync_api import Locator, TimeoutError as PWTimeoutError

from pages.base_page import BasePage
from pages.locators.product_locators import ProductLocators
from utilities.common_ops import parse_usd_price
from utilities.logger import log
from utilities.random_data import short_name, short_phrase
from utilities.shipping import listing_url_with_shipping
from utilities.timeouts import QUICK_TIMEOUT_MS, SHORT_TIMEOUT_MS

_PLACEHOLDER_VARIANT_LABELS: frozenset[str] = frozenset({"", "-", "select", "choose"})


class ProductPage(BasePage):
    """eBay product / listing detail page."""

    def get_price(self) -> float | None:
        """Return the displayed listing price in USD (or None if not shown in USD)."""
        try:
            raw: str = self.inner_text(self.loc(ProductLocators.PRICE), timeout=QUICK_TIMEOUT_MS)
            price: float | None = parse_usd_price(raw)
            if price is None and raw.strip():
                log.warning(f"[product] Non-USD or unparseable price: {raw!r}")
            return price
        except PWTimeoutError:
            log.debug("[product] Price element not found")
            return None

    def _is_valid_variant_label(self, label: str) -> bool:
        normalized: str = label.strip().lower()
        if not normalized:
            return False
        if normalized in _PLACEHOLDER_VARIANT_LABELS:
            return False
        if any(token in normalized for token in ("select", "choose", "filter", "rating", "sort")):
            return False
        return True

    def _fill_variation_selects(self) -> None:
        """For each variation <select>, pick the first non-default option."""
        buy_box: Locator = self.loc(ProductLocators.BUY_BOX)
        selects: Locator = buy_box.locator(ProductLocators.VARIATION_SELECT)
        count: int = selects.count()
        if count:
            log.info(f"[product] {count} variant dropdown(s) found")
        for i in range(count):
            sel: Locator = selects.nth(i)
            try:
                options: list[str] = sel.locator("option").all_inner_texts()
                valid: list[str] = [o for o in options if self._is_valid_variant_label(o)]
                if valid:
                    log.info(f"[product] Variant dropdown {i + 1}: '{valid[0]}'")
                    with allure.step(f"Select variant '{valid[0]}' for dropdown {i + 1}"):
                        self.select_option_label(sel, valid[0])
            except PWTimeoutError as exc:
                log.warning(f"[product] Variant dropdown {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[product] Could not select variant dropdown {i + 1}: {exc!s}")

    def _select_variation_radios(self) -> None:
        """Click the first available radio in each MSKU radio group."""
        buy_box: Locator = self.loc(ProductLocators.BUY_BOX)
        radios: Locator = buy_box.locator(ProductLocators.VARIATION_RADIO)
        count: int = radios.count()
        if count == 0:
            return

        log.info(f"[product] {count} variant radio(s) found")
        seen_groups: set[str] = set()
        for i in range(count):
            radio: Locator = radios.nth(i)
            try:
                if not radio.is_enabled():
                    continue
                group: str = radio.get_attribute("name") or f"radio-{i}"
                if group in seen_groups:
                    continue
                label: str = (
                    radio.get_attribute("aria-label")
                    or radio.get_attribute("value")
                    or f"option {i + 1}"
                )
                if not self._is_valid_variant_label(label):
                    continue
                log.info(f"[product] Variant radio group '{group}': '{label}'")
                with allure.step(f"Select variant radio '{label}'"):
                    self.click_locator(radio, step=f"Select variant radio '{label}'")
                seen_groups.add(group)
            except PWTimeoutError as exc:
                log.warning(f"[product] Variant radio {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[product] Could not select variant radio {i + 1}: {exc!s}")

    def _select_variation_buttons(self) -> None:
        """Open listbox-style variant pickers and choose the first valid option."""
        buy_box: Locator = self.loc(ProductLocators.BUY_BOX)
        buttons: Locator = buy_box.locator(ProductLocators.VARIATION_BUTTON)
        count: int = buttons.count()
        if count == 0:
            return

        log.info(f"[product] {count} variant button/listbox control(s) found")
        for i in range(count):
            button: Locator = buttons.nth(i)
            try:
                if not button.is_enabled() or not button.is_visible():
                    continue
                label: str = (button.inner_text(timeout=QUICK_TIMEOUT_MS) or "").strip()
                if label and self._is_valid_variant_label(label):
                    log.info(f"[product] Variant button {i + 1} already set: '{label}'")
                    continue

                with allure.step(f"Open variant picker {i + 1}"):
                    self.click_locator(button, step=f"Open variant picker {i + 1}")

                options: Locator = self.loc_all(ProductLocators.VARIATION_LISTBOX_OPTION)
                option_count: int = options.count()
                for j in range(option_count):
                    option: Locator = options.nth(j)
                    option_label: str = (option.inner_text(timeout=QUICK_TIMEOUT_MS) or "").strip()
                    if not self._is_valid_variant_label(option_label):
                        continue
                    log.info(f"[product] Variant picker {i + 1}: '{option_label}'")
                    with allure.step(f"Select variant '{option_label}'"):
                        self.click_locator(option, step=f"Select variant '{option_label}'")
                    break
            except PWTimeoutError as exc:
                log.warning(f"[product] Variant button {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[product] Could not select variant button {i + 1}: {exc!s}")

    def _select_variations(self) -> None:
        """Pick variants across dropdown, radio, and button/listbox controls."""
        self._fill_variation_selects()
        self._select_variation_radios()
        self._select_variation_buttons()

    def _fill_required_inputs(self) -> None:
        """Fill any required text inputs with random short text."""
        required: Locator = self.loc_all(ProductLocators.REQUIRED_INPUT)
        for i in range(required.count()):
            inp: Locator = required.nth(i)
            try:
                placeholder: str = (inp.get_attribute("placeholder") or "").lower()
                if "name" in placeholder or "initial" in placeholder:
                    value: str = short_name()
                elif "message" in placeholder or "text" in placeholder:
                    value = short_phrase()
                else:
                    value = short_name()
                with allure.step(f"Fill required input {i + 1} with '{value}'"):
                    self.fill_locator(inp, value, step=f"Fill required input {i + 1}")
            except PWTimeoutError as exc:
                log.warning(f"[product] Required input {i + 1} timed out: {exc!s}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"[product] Could not fill required input {i + 1}: {exc!s}")

    def _wait_for_buy_box(self) -> None:
        """Wait until the listing buy box is interactive."""
        try:
            self.loc(ProductLocators.BUY_BOX).wait_for(state="visible", timeout=QUICK_TIMEOUT_MS)
        except PWTimeoutError:
            log.debug("[product] Buy box not visible within timeout")

        add_to_cart: Locator = self.role("button", name=re.compile(r"add to cart", re.I))
        try:
            add_to_cart.wait_for(state="visible", timeout=QUICK_TIMEOUT_MS)
        except PWTimeoutError:
            log.warning("[product] Buy box loaded without an Add to cart button")

    def _click_add_to_cart(self) -> bool:
        """Click the Add to cart CTA if present."""
        add_to_cart: Locator = self.roles("button", name=re.compile(r"add to cart", re.I))
        if add_to_cart.count() == 0:
            return False

        log.info("[product] Clicking 'Add to cart'")
        self.click_locator(add_to_cart.first, step="Click Add to cart")
        return True

    def _confirm_add_to_cart(self) -> bool:
        """Detect post-click confirmation in the DOM."""
        try:
            self.text(re.compile(r"added to (?:your )?cart", re.I)).wait_for(
                state="visible", timeout=QUICK_TIMEOUT_MS
            )
            return True
        except PWTimeoutError:
            log.debug("[product] Add-to-cart confirmation text not visible")

        if self.role("link", name=re.compile(r"view in cart", re.I)).is_visible(
            timeout=QUICK_TIMEOUT_MS
        ):
            return True

        content: str = self._page.content().lower()
        return "added to your cart" in content or "view in cart" in content

    def _set_quantity(self, quantity: int) -> bool:
        """Set buy-box quantity before add-to-cart."""
        if quantity < 1:
            return False
        if quantity == 1:
            return True

        qty_value: str = str(quantity)
        scopes: list[Locator] = [
            self._page.locator(ProductLocators.QUANTITY_SCOPE),
            self.loc(ProductLocators.BUY_BOX),
            self._page.locator("body"),
        ]
        seen: set[str] = set()
        unique_scopes: list[Locator] = []
        for scope in scopes:
            key: str = scope.__str__()
            if key not in seen:
                seen.add(key)
                unique_scopes.append(scope)

        for scope in unique_scopes:
            qty_select: Locator = scope.locator(ProductLocators.QUANTITY_SELECT)
            if qty_select.count() > 0:
                select: Locator = qty_select.first
                try:
                    with allure.step(f"Set quantity to {quantity}"):
                        select.select_option(value=qty_value)
                    log.info(f"[product] Quantity set to {quantity} (select)")
                    return True
                except PWTimeoutError:
                    pass
                except Exception:  # noqa: BLE001
                    try:
                        with allure.step(f"Set quantity to {quantity}"):
                            select.select_option(label=qty_value)
                        log.info(f"[product] Quantity set to {quantity} (select label)")
                        return True
                    except Exception as exc:  # noqa: BLE001
                        log.warning(f"[product] Could not select quantity {quantity}: {exc!s}")

            qty_input: Locator = scope.locator(ProductLocators.QUANTITY_INPUT)
            if qty_input.count() > 0:
                input_el: Locator = qty_input.first
                if not input_el.is_enabled():
                    log.debug("[product] Quantity input present but disabled")
                    continue
                try:
                    with allure.step(f"Set quantity to {quantity}"):
                        self.fill_locator(
                            input_el,
                            qty_value,
                            step=f"Set quantity to {quantity}",
                        )
                    log.info(f"[product] Quantity set to {quantity} (input)")
                    return True
                except PWTimeoutError as exc:
                    log.debug(f"[product] Quantity input timed out: {exc!s}")
                except Exception as exc:  # noqa: BLE001
                    log.debug(f"[product] Could not fill quantity {quantity}: {exc!s}")

        log.warning(f"[product] ✗ No quantity control found for qty={quantity}")
        return False

    def _click_and_confirm_add(self) -> bool:
        """Click Add to cart once and wait for confirmation."""
        if not self._click_add_to_cart():
            log.warning("[product] ✗ 'Add to cart' button not found")
            return False

        confirmed: bool = self._confirm_add_to_cart()
        if not confirmed:
            log.warning("[product] ✗ Cart confirmation not detected")

        modal_btn: Locator = self.loc(ProductLocators.MODAL_CONTINUE)
        if self.is_locator_visible(modal_btn, timeout=QUICK_TIMEOUT_MS):
            try:
                log.info("[product] Dismissing post-add modal")
                self.click_locator(modal_btn, step="Dismiss post-add modal")
                modal_btn.wait_for(state="hidden", timeout=QUICK_TIMEOUT_MS)
            except PWTimeoutError:
                log.debug("[product] Post-add modal did not hide after dismiss")

        return confirmed

    def add_to_cart(self, *, quantity: int = 1) -> int:
        """
        Select variants, set quantity, fill required fields, then add to cart.

        Returns the number of units confirmed added (0 when nothing was added).
        """
        with allure.step(f"Add product to cart (qty={quantity})"):
            self._wait_for_buy_box()
            self._select_variations()
            self._fill_required_inputs()

            if quantity == 1:
                return 1 if self._click_and_confirm_add() else 0

            if self._set_quantity(quantity):
                return quantity if self._click_and_confirm_add() else 0

            log.info(
                f"[product] Quantity UI unavailable — adding {quantity} unit(s) via repeated clicks"
            )
            successful: int = 0
            for unit in range(1, quantity + 1):
                if not self._click_and_confirm_add():
                    log.warning(f"[product] Add-to-cart failed on unit {unit}/{quantity}")
                    break
                successful = unit

            if successful == quantity:
                log.info(f"[product] ✓ Added {quantity} unit(s) via repeated clicks")
            elif successful > 0:
                log.warning(f"[product] ✗ Only {successful}/{quantity} unit(s) confirmed added")

            return successful

    def open(self, url: str) -> "ProductPage":
        """Navigate to a listing URL and wait for the page to settle."""
        shipping_url: str = listing_url_with_shipping(url)
        with allure.step(f"Open product page: {shipping_url.split('?')[0]}"):
            self.goto(shipping_url, wait_until="commit")
            self.accept_cookies_if_present()
        return self
