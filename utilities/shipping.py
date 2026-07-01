"""Shipping destination helpers for eBay test runs."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

DEFAULT_US_ZIP: str = "95621"

# Elk Grove, CA — matches ZIP 95621 for geolocation hints
US_SHIPPING_GEOLOCATION: dict[str, float] = {
    "latitude": 38.4088,
    "longitude": -121.3716,
}


def us_shipping_query_params(*, zip_code: str = DEFAULT_US_ZIP) -> dict[str, list[str]]:
    """Return URL query params for US domestic shipping at *zip_code*."""
    return {
        "_stpos": [zip_code],
        "_fcid": ["1"],
        "LH_PrefLoc": ["1"],
    }


def listing_url_with_shipping(url: str, *, zip_code: str = DEFAULT_US_ZIP) -> str:
    """Append Ship-to ZIP params so listing pages render USD prices."""
    parsed = urlparse(url)
    params: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in us_shipping_query_params(zip_code=zip_code).items():
        params[key] = value
    query: str = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=query))
