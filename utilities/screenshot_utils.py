"""Screenshot helpers with Allure attachment support."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import allure
from playwright.sync_api import Page

_SCREENSHOTS_DIR = Path(__file__).parents[1] / "screenshots"


def take_screenshot(
    page: Page,
    *,
    name: str = "screenshot",
    attach_to_allure: bool = True,
) -> Path:
    """Capture a full-page screenshot, save to disk, and optionally attach to Allure."""
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts: str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    safe_name: str = name.replace(" ", "_").replace("/", "-")
    path: Path = _SCREENSHOTS_DIR / f"{ts}_{safe_name}.png"

    png: bytes = page.screenshot(full_page=True, path=str(path))

    if attach_to_allure:
        allure.attach(
            png,
            name=name,
            attachment_type=allure.attachment_type.PNG,
            extension="png",
        )

    return path


def attach_failure_screenshot(page: Page, test_name: str) -> None:
    """Capture a failure screenshot and attach it to the current Allure test result."""
    safe_name: str = f"FAILURE_{test_name}".replace(" ", "_").replace("/", "-")
    try:
        take_screenshot(page, name=safe_name, attach_to_allure=True)
    except Exception as exc:  # noqa: BLE001
        allure.attach(
            f"Could not capture failure screenshot: {exc}",
            name="screenshot-error",
            attachment_type=allure.attachment_type.TEXT,
        )
