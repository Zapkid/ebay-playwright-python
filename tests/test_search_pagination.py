"""E2E test: search result pagination."""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from pages.search_page import SearchPage
from tests.models import PaginationCase
from utilities.logger import log
from utilities.verifications import (
    verify_greater_than_or_equal,
    verify_not_empty,
    verify_positive,
    verify_true,
)
from workflows.paginate_search import collect_listing_ids_by_page


@allure.suite("eBay E2E")
@allure.feature("Search")
@pytest.mark.search
@pytest.mark.pagination
class TestSearchPagination:
    """Verify eBay search pagination returns new listings on subsequent pages."""

    @allure.story("Next page shows new search results")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_pagination_next_page(
        self,
        page: Page,
        base_url: str,
        pagination_case: PaginationCase,
    ) -> None:
        """Subsequent pages should load with higher page numbers and mostly new listings."""
        case: PaginationCase = pagination_case

        listing_ids_by_page: list[set[str]] = collect_listing_ids_by_page(
            page,
            base_url=base_url,
            query=case.query,
            min_price=case.min_price,
            max_price=case.max_price,
            pages=case.pages,
        )

        verify_greater_than_or_equal(
            len(listing_ids_by_page),
            case.pages,
            f"Expected at least {case.pages} result pages for query='{case.query}'",
        )

        page1_ids: set[str] = listing_ids_by_page[0]
        page2_ids: set[str] = listing_ids_by_page[1]

        verify_not_empty(
            page1_ids,
            f"Page 1 returned no listings for query='{case.query}'",
        )
        verify_not_empty(
            page2_ids,
            f"Page 2 returned no listings for query='{case.query}'",
        )

        new_on_page2: set[str] = page2_ids - page1_ids
        verify_positive(
            len(new_on_page2),
            "Page 2 should contain listings not present on page 1",
        )

        overlap: set[str] = page1_ids & page2_ids
        overlap_ratio: float = len(overlap) / len(page2_ids)
        verify_true(
            overlap_ratio <= case.max_overlap_ratio,
            f"Page 2 overlaps too much with page 1 ({len(overlap)}/{len(page2_ids)} "
            f"duplicates, {overlap_ratio:.0%})",
        )

        search: SearchPage = SearchPage(page, base_url=base_url)
        verify_greater_than_or_equal(
            search.current_page_number(),
            2,
            "URL should reflect page 2 after clicking Next",
        )

        log.info(
            f"[test]   ✓ PASS | page1={len(page1_ids)} | page2={len(page2_ids)} | "
            f"new={len(new_on_page2)} | overlap={len(overlap)}"
        )

        allure.attach(
            f"Test ID       : {case.test_id}\n"
            f"Query         : {case.query}\n"
            f"Price range   : ${case.min_price}–${case.max_price}\n"
            f"Pages visited : {case.pages}\n"
            f"Page 1 IDs    : {len(page1_ids)}\n"
            f"Page 2 IDs    : {len(page2_ids)}\n"
            f"New on page 2 : {len(new_on_page2)}\n"
            f"Overlap       : {len(overlap)}",
            name="Pagination summary",
            attachment_type=allure.attachment_type.TEXT,
        )
