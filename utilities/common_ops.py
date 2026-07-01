"""Shared helpers — filters, predicates, and small utilities."""

from __future__ import annotations

import re
from collections.abc import Callable

_NON_USD_CURRENCY_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:ILS|EUR|GBP|CAD|AUD|JPY|CNY|INR|CHF|MXN|BRL|HKD|SGD|NZD|SEK|NOK|DKK|PLN|"
    r"RUB|ZAR|KRW|TWD|THB|MYR|PHP|IDR|VND|AED|SAR|TRY|CZK|HUF|RON|BGN|HRK|UAH|"
    r"₪|€|£|¥|₹|₩|₽)\b",
    re.IGNORECASE,
)

_USD_PRICE_PATTERNS: tuple[str, ...] = (
    r"US\s*\$\s*([\d,]+\.?\d*)",
    r"USD\s*([\d,]+\.?\d*)",
    r"\$\s*([\d,]+\.?\d*)",
)

_SALE_PRICE_PATTERNS: tuple[str, ...] = (
    r"now\s*(?:price\s*)?\$\s*([\d,]+\.?\d*)",
    r"current\s*(?:price\s*)?\$\s*([\d,]+\.?\d*)",
    r"you pay\s*\$\s*([\d,]+\.?\d*)",
    r"sale\s*(?:price\s*)?\$\s*([\d,]+\.?\d*)",
)


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _contains_non_usd_currency(value_text: str) -> bool:
    return _NON_USD_CURRENCY_PATTERN.search(value_text) is not None


def _contains_usd_marker(value_text: str) -> bool:
    return re.search(r"US\s*\$|\$|USD", value_text, re.IGNORECASE) is not None


def parse_usd_price(value_text: str | None) -> float | None:
    """
    Extract a USD price from item value text.

    Returns ``None`` for foreign-currency-only strings (e.g. ``ILS 47.73``)
    or when no ``$`` / ``US $`` / ``USD`` amount is present.
    """
    if not value_text or not value_text.strip():
        return None

    text: str = value_text.strip()
    if _contains_non_usd_currency(text) and not _contains_usd_marker(text):
        return None

    lower: str = text.lower()
    for pattern in _SALE_PRICE_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            parsed: float | None = _to_float(match.group(1))
            if parsed is not None:
                return parsed

    for pattern in _USD_PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = _to_float(match.group(1))
            if parsed is not None:
                return parsed

    if _contains_non_usd_currency(text):
        return None

    return None


def parse_item_value(value_text: str | None) -> float | None:
    """
    Extract a numeric price from item value text (legacy helper).

    Prefer :func:`parse_usd_price` anywhere test assertions compare prices.
    """
    usd_price: float | None = parse_usd_price(value_text)
    if usd_price is not None:
        return usd_price

    if not value_text or not value_text.strip():
        return None

    if _contains_non_usd_currency(value_text):
        return None

    normalized: str = value_text.replace(",", "")
    match = re.search(r"[\d,]+\.?\d*", normalized)
    if not match:
        return None

    return _to_float(match.group())


def price_in_range(
    card: dict,
    *,
    min_price: float,
    max_price: float,
    allow_missing_price: bool = False,
) -> bool:
    """Return True when a search-result card price is within *min_price*–*max_price*."""
    p: float | None = card.get("price")
    if p is None:
        return allow_missing_price
    return min_price <= p <= max_price


def make_price_in_range_filter(
    min_price: float,
    max_price: float,
    *,
    allow_missing_price: bool = False,
) -> Callable[[dict], bool]:
    """Build a ``filter_fn`` for product URL collection workflows."""
    def _filter(card: dict) -> bool:
        return price_in_range(
            card,
            min_price=min_price,
            max_price=max_price,
            allow_missing_price=allow_missing_price,
        )

    return _filter


def is_price_in_range(
    price: float | None,
    *,
    min_price: float | None = None,
    max_price: float | None = None,
) -> bool:
    """Return True when *price* is inside the optional min/max bounds."""
    if price is None:
        return False
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def search_collect_limit(limit: int) -> int:
    """Return how many URLs to collect before add-to-cart filtering."""
    return limit + min(limit, 3)
