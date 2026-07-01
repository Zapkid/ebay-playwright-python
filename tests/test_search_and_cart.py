"""E2E test: Search → filter by price → add items to cart → verify total.

DDT cases are loaded from tests/data/test_data.json (see tests/conftest.py).
Workflows live in workflows/.
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from pages.cart_page import CartState
from tests.models import SearchCartCase
from utilities.logger import log
from utilities.verifications import verify_not_empty, verify_positive
from workflows import add_items_to_cart, assert_cart_total, search_items


@allure.suite("eBay E2E")
@allure.feature("Search & Cart")
@pytest.mark.cart
@pytest.mark.search
@pytest.mark.regression
class TestSearchAndCart:
    """Data-driven end-to-end test: search → filter → add to cart → verify total."""

    @allure.story("Search, add items to cart, and verify subtotal")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_add_cart(
        self,
        page: Page,
        base_url: str,
        search_cart_case: SearchCartCase,
    ) -> None:
        case: SearchCartCase = search_cart_case

        products: list[dict] = search_items(
            page,
            base_url=base_url,
            query=case.query,
            min_price=case.min_price,
            max_price=case.max_price,
            limit=case.limit,
            test_id=case.test_id,
        )

        verify_not_empty(
            products,
            f"[{case.test_id}] searchItems returned no products for "
            f"query='{case.query}' "
            f"price=${case.min_price}–${case.max_price}",
        )

        augmented: list[dict] = add_items_to_cart(
            page,
            products,
            min_price=case.min_price,
            max_price=case.max_price,
            target_count=case.limit,
            quantity=case.quantity,
        )

        added_count: int = sum(1 for a in augmented if a["added"])
        unit_count: int = sum(a["quantity"] for a in augmented if a["added"])
        verify_positive(
            added_count,
            f"[{case.test_id}] No items were successfully added to cart",
        )

        cart_state: CartState = assert_cart_total(
            page,
            added_items=augmented,
            expected_count=added_count,
            min_total=case.min_total,
            max_total=case.max_total,
            budget_per_item=case.budget_per_item,
            items_count=unit_count,
        )

        log.info(
            f"[test]   ✓ PASS | lines={len(cart_state.items)} | "
            f"units={unit_count} | subtotal=${cart_state.subtotal:.2f}"
        )

        allure.attach(
            f"Test ID      : {case.test_id}\n"
            f"Query        : {case.query}\n"
            f"Price range  : ${case.min_price}–${case.max_price}\n"
            f"Quantity     : {case.quantity} per listing\n"
            f"URLs found   : {len(products)}\n"
            f"Lines added  : {added_count}\n"
            f"Units added  : {unit_count}\n"
            f"Cart lines   : {len(cart_state.items)}\n"
            f"Subtotal     : ${cart_state.subtotal:.2f}\n"
            f"Budget cap   : ${case.budget_per_item:.2f} × {unit_count} "
            f"= ${case.budget_per_item * unit_count:.2f}\n"
            f"Checkout btn : {'✓' if cart_state.checkout_enabled else '✗'}",
            name="Test summary",
            attachment_type=allure.attachment_type.TEXT,
        )
