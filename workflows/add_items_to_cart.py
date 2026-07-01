"""Workflow: open product URLs, pick variants, and add items to cart."""

from __future__ import annotations

import allure
from playwright.sync_api import Page

from pages.product_page import ProductPage
from pages.search_page import is_valid_listing_url
from utilities.config_loader import ConfigLoader
from utilities.logger import log
from utilities.screenshot_utils import take_screenshot
from utilities.common_ops import is_price_in_range


def add_items_to_cart(
    page: Page,
    product_list: list[dict],
    *,
    min_price: float | None = None,
    max_price: float | None = None,
    target_count: int | None = None,
    quantity: int = 1,
) -> list[dict]:
    """
    Open each product URL from *product_list*, pick variants, fill required
    fields, set *quantity*, and click Add to Cart.

    Skips listings whose on-page price falls outside the expected range.
    Stops once *target_count* distinct listings are confirmed added.

    Returns list of dicts augmented with ``page_price``, ``quantity``, and ``added``.
    """
    product_page = ProductPage(page)
    augmented: list[dict] = []
    goal: int = target_count or len(product_list)
    total: int = len(product_list)
    item_qty: int = max(1, quantity)
    screenshot_on_add: bool = bool(ConfigLoader.load().get("screenshot_on_add", True))

    log.info(
        f"[cart]   Adding up to {goal} listing(s) × qty {item_qty} "
        f"from {total} candidate(s)"
    )

    with allure.step(f"[addItemsToCart] adding up to {goal} items (qty={item_qty})"):
        for idx, item in enumerate(product_list, start=1):
            if sum(1 for a in augmented if a["added"]) >= goal:
                break

            url: str = item["url"]
            if not is_valid_listing_url(url):
                log.warning(f"[cart]   ✗ Skipping invalid listing URL: {url}")
                augmented.append({**item, "page_price": None, "quantity": item_qty, "added": False})
                continue

            title: str = item.get("title", f"Item {idx}") or f"Item {idx}"
            short_title: str = title[:40].strip()

            log.info(f"[cart]   → {idx}/{total}: {short_title!r} × {item_qty}")

            with allure.step(f"Item {idx}: {short_title}"):
                product_page.open(url)
                page_price: float | None = product_page.get_price()

                if page_price is None:
                    log.warning(
                        f"[cart]   ✗ Skipping {short_title!r}: "
                        "no USD price on product page (expected US $…)"
                    )
                    augmented.append({**item, "page_price": None, "quantity": item_qty, "added": False})
                    continue

                if not is_price_in_range(
                    page_price, min_price=min_price, max_price=max_price
                ):
                    if min_price is not None and page_price < min_price:
                        bound: str = f"below min ${min_price:.2f}"
                    elif max_price is not None and page_price > max_price:
                        bound = f"above max ${max_price:.2f}"
                    else:
                        bound = "out of range"
                    log.warning(
                        f"[cart]   ✗ Skipping {short_title!r}: "
                        f"${page_price:.2f} {bound}"
                    )
                    augmented.append({**item, "page_price": page_price, "quantity": item_qty, "added": False})
                    continue

                added_qty: int = product_page.add_to_cart(quantity=item_qty)
                added: bool = added_qty == item_qty
                if screenshot_on_add:
                    take_screenshot(page, name=f"add_to_cart_{idx}")

                if added:
                    line_total: float = page_price * added_qty
                    log.info(
                        f"[cart]   ✓ Added  ${page_price:.2f} × {added_qty} = ${line_total:.2f}"
                        if page_price
                        else f"[cart]   ✓ Added × {added_qty}"
                    )
                elif added_qty > 0:
                    log.warning(
                        f"[cart]   ✗ Partial add for {short_title!r}: "
                        f"{added_qty}/{item_qty} unit(s) confirmed"
                    )
                else:
                    log.warning(
                        f"[cart]   ✗ Could not confirm add-to-cart for {short_title!r} "
                        f"(qty={item_qty})"
                    )

                augmented.append(
                    {
                        **item,
                        "page_price": page_price,
                        "quantity": added_qty if added else item_qty,
                        "added": added,
                    }
                )

    added_count: int = sum(1 for a in augmented if a["added"])
    unit_count: int = sum(a["quantity"] for a in augmented if a["added"])
    log.info(f"[cart]   {added_count}/{goal} listings confirmed ({unit_count} unit(s) in cart)")
    return augmented
