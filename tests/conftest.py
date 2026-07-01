"""Tests-level conftest — DDT data loading, env config helpers, and before hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import allure
import pytest
from playwright.sync_api import Page

from tests.models import PaginationCase, SearchCartCase
from workflows.ensure_logged_in import ensure_logged_in

_DATA_FILE = Path(__file__).parent / "data" / "test_data.json"
_PAGINATION_DATA_FILE = Path(__file__).parent / "data" / "pagination_data.json"


def load_test_cases() -> list[dict]:
    """Read test_data.json and return list of test-case dicts."""
    with _DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_pagination_cases() -> list[dict]:
    """Read pagination_data.json and return list of pagination-case dicts."""
    with _PAGINATION_DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize DDT fixtures from JSON data files."""
    if "test_case" in metafunc.fixturenames:
        cases: list[dict] = load_test_cases()
        metafunc.parametrize(
            "test_case",
            cases,
            ids=[c["test_id"] for c in cases],
        )

    if "pagination_test_case" in metafunc.fixturenames:
        cases = load_pagination_cases()
        metafunc.parametrize(
            "pagination_test_case",
            cases,
            ids=[c["test_id"] for c in cases],
        )


@pytest.fixture
def search_cart_case(test_case: dict) -> SearchCartCase:
    """Normalize the raw DDT dict into a typed case object."""
    search_cfg: dict = test_case["search"]
    cart_cfg: dict = test_case.get("cart_validation", {})
    return SearchCartCase(
        test_id=test_case["test_id"],
        description=test_case.get("description", ""),
        query=search_cfg["query"],
        min_price=search_cfg["min_price"],
        max_price=search_cfg["max_price"],
        limit=search_cfg["limit"],
        quantity=int(search_cfg.get("quantity", 1)),
        min_total=cart_cfg.get("min_total"),
        max_total=cart_cfg.get("max_total"),
        budget_per_item=cart_cfg.get("budget_per_item", search_cfg["max_price"]),
    )


@pytest.fixture
def pagination_case(pagination_test_case: dict) -> PaginationCase:
    """Normalize the raw pagination DDT dict into a typed case object."""
    search_cfg: dict = pagination_test_case["search"]
    validation_cfg: dict = pagination_test_case.get("pagination_validation", {})
    return PaginationCase(
        test_id=pagination_test_case["test_id"],
        description=pagination_test_case.get("description", ""),
        query=search_cfg["query"],
        min_price=search_cfg["min_price"],
        max_price=search_cfg["max_price"],
        pages=search_cfg["pages"],
        max_overlap_ratio=validation_cfg.get("max_overlap_ratio", 0.25),
    )


@pytest.fixture(autouse=True)
def _before_search_cart_test(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Before hook: configure Allure metadata for each search-and-cart DDT case."""
    if "search_cart_case" not in request.fixturenames:
        yield
        return

    from utilities.logger import log

    case: SearchCartCase = request.getfixturevalue("search_cart_case")
    allure.dynamic.title(f"[{case.test_id}] {case.description}")
    allure.dynamic.parameter("query", case.query)
    allure.dynamic.parameter("min_price", case.min_price)
    allure.dynamic.parameter("max_price", case.max_price)
    allure.dynamic.parameter("limit", case.limit)
    allure.dynamic.parameter("quantity", case.quantity)

    log.info(f"{'─' * 55}")
    log.info(f"[test]   {case.test_id} — {case.description}")
    log.info(f"{'─' * 55}")

    yield


@pytest.fixture(autouse=True)
def _before_pagination_test(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Before hook: configure Allure metadata for each pagination DDT case."""
    if "pagination_case" not in request.fixturenames:
        yield
        return

    from utilities.logger import log

    case: PaginationCase = request.getfixturevalue("pagination_case")
    allure.dynamic.title(f"[{case.test_id}] {case.description}")
    allure.dynamic.parameter("query", case.query)
    allure.dynamic.parameter("pages", case.pages)

    log.info(f"{'─' * 55}")
    log.info(f"[test]   {case.test_id} — {case.description}")
    log.info(f"{'─' * 55}")

    yield


@pytest.fixture(autouse=True)
def _ensure_login_for_e2e(
    page: Page,
    with_login: bool,
    base_url: str,
    request: pytest.FixtureRequest,
) -> None:
    """When --with-login is set, authenticate before search/cart E2E tests."""
    if not with_login:
        return
    if "search_cart_case" not in request.fixturenames:
        return

    success: bool = ensure_logged_in(page, base_url=base_url)
    if not success:
        pytest.fail(
            "Authentication required (--with-login) but no valid session. "
            "Run: uv run python -m scripts.bootstrap_ebay_auth"
        )
