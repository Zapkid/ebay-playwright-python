"""Playwright trace helpers — capture and attach traces on test failure."""

from __future__ import annotations

import re
from pathlib import Path

import allure
from playwright.sync_api import BrowserContext

_TRACES_DIR = Path(__file__).parents[1] / "reports" / "traces"


def start_tracing(context: BrowserContext) -> None:
    """Begin Playwright tracing for the browser context."""
    context.tracing.start(screenshots=True, snapshots=True, sources=True)


def _safe_trace_name(test_name: str) -> str:
    cleaned: str = re.sub(r"[^\w.-]+", "_", test_name).strip("_")
    return cleaned or "test"


def save_failure_trace(context: BrowserContext, *, test_name: str) -> Path | None:
    """Stop tracing and write a zip trace file. Returns the path, or None on error."""
    _TRACES_DIR.mkdir(parents=True, exist_ok=True)
    path: Path = _TRACES_DIR / f"FAILURE_{_safe_trace_name(test_name)}.zip"

    try:
        context.tracing.stop(path=str(path))
    except Exception as exc:  # noqa: BLE001
        allure.attach(
            f"Could not save Playwright trace: {exc}",
            name="trace-error",
            attachment_type=allure.attachment_type.TEXT,
        )
        return None

    return path


def attach_failure_trace(trace_path: Path) -> None:
    """Attach a Playwright trace zip to the current Allure result."""
    if not trace_path.is_file():
        return

    allure.attach.file(
        str(trace_path),
        name="Playwright trace",
        attachment_type=allure.attachment_type.ZIP,
        extension="zip",
    )
    allure.attach(
        "View at https://trace.playwright.dev — upload the zip or drag-and-drop.",
        name="Playwright trace viewer",
        attachment_type=allure.attachment_type.TEXT,
    )


def stop_tracing_without_save(context: BrowserContext) -> None:
    """Discard an in-progress trace (successful test run)."""
    try:
        context.tracing.stop()
    except Exception:  # noqa: BLE001
        pass
