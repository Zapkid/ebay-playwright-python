"""Workflow: walk search result pages and collect product URLs."""

from __future__ import annotations

from collections.abc import Callable

import allure
from playwright.sync_api import TimeoutError as PWTimeoutError

from pages.locators.search_locators import SearchLocators
from pages.search_page import SearchPage, is_valid_listing_url
from utilities.logger import log
from utilities.timeouts import SHORT_TIMEOUT_MS


def collect_product_urls(
    search: SearchPage,
    *,
    limit: int,
    filter_fn: Callable[[dict], bool] | None = None,
    max_pages: int = 5,
) -> list[dict]:
    """Walk search result pages and collect up to *limit* product URLs."""
    collected: list[dict] = []
    page_num: int = 1

    with allure.step(f"Collect up to {limit} product URLs"):
        while len(collected) < limit and page_num <= max_pages:
            search._prime_results_page()

            allure.attach(
                search.current_url,
                name=f"Search results page {page_num}",
                attachment_type=allure.attachment_type.TEXT,
            )

            if search.count_cards() == 0:
                try:
                    search.wait_for_selector(
                        SearchLocators.PRODUCT_CARDS,
                        state="attached",
                        timeout=SHORT_TIMEOUT_MS,
                    )
                except PWTimeoutError:
                    log.warning(f"[search] No cards on page {page_num} — stopping collection")
                    break

            cards = search.get_card_locators()
            count: int = cards.count()
            scan_limit: int = min(count, max(limit * 4, 16))
            before: int = len(collected)

            for i in range(scan_limit):
                if len(collected) >= limit:
                    break
                try:
                    data: dict = search.extract_card_data(cards.nth(i))
                    if not is_valid_listing_url(data["url"]):
                        continue
                    if filter_fn is None or filter_fn(data):
                        collected.append(data)
                except PWTimeoutError as exc:
                    log.warning(f"[search] Card {i + 1} on page {page_num} timed out: {exc!s}")
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        f"[search] Could not parse card {i + 1} on page {page_num}: {exc!s}"
                    )

            matched: int = len(collected) - before
            log.info(
                f"[search] Page {page_num} — {count} cards, "
                f"{matched} matched ({len(collected)}/{limit} total)"
            )

            if len(collected) >= limit:
                break

            if page_num >= max_pages:
                log.warning(f"[search] Reached max pages ({max_pages}) — stopping collection")
                break

            if not search.has_next_page():
                break

            log.info("[search] → next page")
            search.go_to_next_page()
            page_num += 1

    return collected[:limit]
