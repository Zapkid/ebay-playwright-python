"""Shared test data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchCartCase:
    """Parsed DDT case for search-and-cart tests."""

    test_id: str
    description: str
    query: str
    min_price: float
    max_price: float
    limit: int
    quantity: int
    min_total: float | None
    max_total: float | None
    budget_per_item: float | None


@dataclass
class PaginationCase:
    """Parsed DDT case for search pagination tests."""

    test_id: str
    description: str
    query: str
    min_price: float
    max_price: float
    pages: int
    max_overlap_ratio: float
