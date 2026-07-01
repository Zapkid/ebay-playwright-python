"""Persist eBay Ship-to-US session state for reuse across test contexts."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page

from pages.home_page import HomePage
from utilities.config_loader import ConfigLoader

_SHIPPING_DIR: Path = Path(__file__).parents[1] / "secured_env_files"
SHIPPING_STATE_PATH: Path = _SHIPPING_DIR / "shipping-us.json"


def shipping_state_exists() -> bool:
    """Return True when a saved Ship-to-US session file is present."""
    return SHIPPING_STATE_PATH.is_file()


def resolve_shipping_state_path() -> Path | None:
    """Return the Ship-to session path when it exists, else None."""
    if shipping_state_exists():
        return SHIPPING_STATE_PATH
    return None


def _guest_context_options(base_url: str, config: dict) -> dict:
    headless: bool = config.get("headless", True)
    options: dict = {
        "base_url": base_url,
        "locale": "en-US",
        "timezone_id": "America/Los_Angeles",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "geolocation": {"latitude": 38.4088, "longitude": -121.3716},
        "permissions": ["geolocation"],
    }
    if headless:
        options["viewport"] = {"width": 1920, "height": 1080}
    else:
        options["no_viewport"] = True
    return options


def ensure_shipping_storage_state(
    browser: Browser,
    *,
    base_url: str,
    config: dict | None = None,
) -> Path:
    """Create Ship-to-US storage state once; return path to the session file."""
    if shipping_state_exists():
        return SHIPPING_STATE_PATH

    cfg: dict = config or ConfigLoader.load()
    _SHIPPING_DIR.mkdir(parents=True, exist_ok=True)

    ctx: BrowserContext = browser.new_context(**_guest_context_options(base_url, cfg))
    page: Page = ctx.new_page()
    HomePage(page, base_url=base_url).set_shipping_to_usa()
    ctx.storage_state(path=str(SHIPPING_STATE_PATH))
    ctx.close()
    return SHIPPING_STATE_PATH
