"""Workflow: search eBay and walk paginated result pages."""

from __future__ import annotations

import allure
from playwright.sync_api import Page

from pages.search_page import SearchPage
from utilities.logger import log


def collect_listing_ids_by_page(
    page: Page,
    *,
    base_url: str,
    query: str,
    min_price: float,
    max_price: float,
    pages: int,
) -> list[set[str]]:
    """
    Search *query*, apply price filters, and collect listing IDs from the first
    *pages* result pages.

    Returns one set of listing IDs per page visited.
    """
    if pages < 1:
        raise ValueError("pages must be >= 1")

    log.info(
        f"[pagination] '{query}' | ${min_price}–${max_price} | pages={pages}"
    )

    with allure.step(
        f"[pagination] query='{query}' price=${min_price}–${max_price} pages={pages}"
    ):
        search: SearchPage = SearchPage(page, base_url=base_url)
        search.go_to_filtered_search(query, min_price, max_price)

        listing_ids_by_page: list[set[str]] = []

        for page_num in range(1, pages + 1):
            ids: set[str] = search.collect_listing_ids_on_page()
            listing_ids_by_page.append(ids)
            allure.attach(
                f"page={page_num}\nurl={page.url}\nlistings={len(ids)}",
                name=f"Pagination page {page_num}",
                attachment_type=allure.attachment_type.TEXT,
            )
            log.info(
                f"[pagination] Page {page_num} — {len(ids)} listings "
                f"(url page={search.current_page_number()})"
            )

            if page_num >= pages:
                break

            if not search.has_next_page():
                log.warning(f"[pagination] No next page after page {page_num}")
                break

            search.go_to_next_page()

        return listing_ids_by_page
