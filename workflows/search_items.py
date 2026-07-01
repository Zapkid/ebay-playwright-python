"""Workflow: search eBay, apply price filters, collect product URLs."""

from __future__ import annotations

from pathlib import Path

import allure
from playwright.sync_api import Page

from pages.search_page import SearchPage
from utilities.csv_writer import DEFAULT_CSV_PATH, append_product, init_csv
from utilities.logger import log
from utilities.common_ops import make_price_in_range_filter, search_collect_limit
from workflows.collect_product_urls import collect_product_urls


def search_items(
    page: Page,
    *,
    base_url: str,
    query: str,
    min_price: float,
    max_price: float,
    limit: int,
    test_id: str = "",
    csv_path: Path = DEFAULT_CSV_PATH,
) -> list[dict]:
    """
    Type *query* into the eBay search box, apply price filters via URL params,
    then walk product cards page by page.

    Returns a list of dicts: {url, price, title}.
    """
    log.info(f"[search] '{query}' | ${min_price}–${max_price} | limit={limit}")

    with allure.step(
        f"[searchItems] query='{query}' price=${min_price}–${max_price} limit={limit}"
    ):
        search = SearchPage(page, base_url=base_url)
        search.go_to_filtered_search(query, min_price, max_price)

        if search.count_cards() == 0:
            log.warning(f"[search] No results for '{query}' — check filters")
            allure.attach(
                "No results returned for this query/filter combo.", name="warning"
            )
            return []

        collect_limit: int = search_collect_limit(limit)
        results: list[dict] = collect_product_urls(
            search,
            limit=collect_limit,
            filter_fn=make_price_in_range_filter(
                min_price,
                max_price,
                allow_missing_price=True,
            ),
        )

        init_csv(csv_path)
        for item in results:
            append_product(
                url=item["url"],
                price=item.get("price"),
                title=item.get("title", ""),
                query=query,
                test_id=test_id,
                path=csv_path,
            )

        log.info(f"[search] ✓ Collected {len(results)}/{limit} URLs → CSV saved")
        allure.attach(
            "\n".join(f"{r['url']}  (${r.get('price', 'N/A')})" for r in results),
            name="Collected product URLs",
            attachment_type=allure.attachment_type.TEXT,
        )
        return results
