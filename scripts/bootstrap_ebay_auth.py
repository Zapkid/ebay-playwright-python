"""Bootstrap eBay auth — manual sign-in once, save session for later runs.

Local development only. Opens a headed browser; complete sign-in with eBay
username/password or Google. Session is written to secured_env_files/ebay-auth.json.

Usage:
    uv run python -m scripts.bootstrap_ebay_auth
    uv run python -m scripts.bootstrap_ebay_auth --force
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, TimeoutError as PWTimeoutError, sync_playwright

from pages.login_page import LoginPage
from scripts.healthcheck import HealthCheckError, run_healthcheck
from utilities.auth_storage import AUTH_STATE_PATH, auth_state_exists, save_auth_state
from utilities.config_loader import ConfigLoader

_BOOTSTRAP_TIMEOUT_S: int = 300
_POLL_INTERVAL_MS: int = 2_000


def _build_context(browser: Browser, base_url: str) -> BrowserContext:
    context: BrowserContext = browser.new_context(
        base_url=base_url,
        locale="en-US",
        timezone_id="America/New_York",
        no_viewport=True,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    return context


def _wait_for_manual_login(page: Page, base_url: str) -> None:
    login_page: LoginPage = LoginPage(page)
    deadline: float = time.monotonic() + _BOOTSTRAP_TIMEOUT_S

    print(
        "\nComplete sign-in in the browser window (eBay username/password or Google).\n"
        f"Waiting up to {_BOOTSTRAP_TIMEOUT_S // 60} minutes…\n"
    )

    while time.monotonic() < deadline:
        current_url: str = page.url.lower()
        if "signin.ebay" not in current_url:
            page.goto(base_url, wait_until="domcontentloaded")
            login_page.accept_cookies_if_present()
            if login_page.is_logged_in():
                return

        remaining_ms: float = max(
            0.0,
            (deadline - time.monotonic()) * 1000,
        )
        if remaining_ms <= 0:
            break
        try:
            page.wait_for_url(
                lambda url: "signin.ebay" not in url.lower(),
                timeout=min(_POLL_INTERVAL_MS, int(remaining_ms)),
            )
        except PWTimeoutError:
            continue

    raise TimeoutError(
        f"Manual login not detected within {_BOOTSTRAP_TIMEOUT_S} seconds. "
        "Try again or check that sign-in completed successfully."
    )


def run_bootstrap(*, force: bool = False) -> Path:
    """Open headed browser, wait for manual login, persist session state."""
    if auth_state_exists() and not force:
        print(f"Session already exists at {AUTH_STATE_PATH}. Use --force to overwrite.")
        return AUTH_STATE_PATH

    print("Running preflight healthcheck…")
    run_healthcheck(verbose=True)

    config: dict = ConfigLoader.load()
    base_url: str = config.get("base_url", "https://www.ebay.com").rstrip("/")

    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(
            headless=False,
            slow_mo=config.get("slow_mo", 50),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context: BrowserContext = _build_context(browser, base_url)
        page: Page = context.new_page()

        LoginPage(page).open()
        _wait_for_manual_login(page, base_url)

        saved_path: Path = save_auth_state(context)
        print(f"\nSession saved to {saved_path}\n")

        context.close()
        browser.close()

    return saved_path


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Manual eBay login bootstrap — saves session for automated test runs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing saved session file.",
    )
    args: argparse.Namespace = parser.parse_args(argv)

    try:
        run_bootstrap(force=args.force)
    except HealthCheckError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except TimeoutError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
