"""Root conftest.py — session-level browser setup/teardown with Allure hooks.

Lifecycle:
    session  → Playwright instance, Browser
    function → BrowserContext (isolated), Page

Auth:
    Login tests and ``--with-login`` load secured_env_files/ebay-auth.json when present.
    Bootstrap locally: uv run python -m scripts.bootstrap_ebay_auth
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from utilities.auth_storage import resolve_auth_state_path
from utilities.config_loader import ConfigLoader
from utilities.shipping_storage import ensure_shipping_storage_state
from utilities.screenshot_utils import attach_failure_screenshot
from utilities.trace_utils import (
    attach_failure_trace,
    save_failure_trace,
    start_tracing,
    stop_tracing_without_save,
)
from utilities.timeouts import MAX_TIMEOUT_MS


def _format_duration(seconds: float) -> str:
    """Format a pytest duration for terminal output."""
    if seconds >= 60:
        minutes: int = int(seconds // 60)
        remainder: float = seconds % 60
        return f"{minutes}m {remainder:.1f}s"
    return f"{seconds:.1f}s"


def _test_outcome_label(outcome: str) -> str:
    labels: dict[str, str] = {
        "passed": "✓ PASS",
        "failed": "✗ FAIL",
        "skipped": "⊘ SKIP",
    }
    return labels.get(outcome, outcome.upper())


def _maximize_browser_window(page: Page) -> None:
    """Maximize the browser window in headed mode (CDP; works on macOS/Windows/Linux)."""
    try:
        cdp = page.context.new_cdp_session(page)
        target_info: dict = cdp.send("Target.getTargetInfo")
        window_info: dict = cdp.send(
            "Browser.getWindowForTarget",
            {"targetId": target_info["targetInfo"]["targetId"]},
        )
        cdp.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_info["windowId"],
                "bounds": {"windowState": "maximized"},
            },
        )
    except Exception as exc:  # noqa: BLE001
        from utilities.logger import log

        log.debug(f"[browser] Could not maximize window via CDP: {exc!s}")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--with-login",
        action="store_true",
        default=False,
        help="Run E2E tests with a saved eBay session (requires ebay-auth.json).",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Apply retry_count from environment config when --reruns is not set on CLI.

    retry_count is the number of reruns after the initial failure (1 = one retry).
    """
    reruns: int = int(getattr(config.option, "reruns", 0) or 0)
    if reruns > 0:
        return

    try:
        cfg: dict = ConfigLoader.load()
    except (ValueError, OSError):
        return

    retry_count: int = int(cfg.get("retry_count", 0))
    if retry_count > 0:
        config.option.reruns = retry_count
        config.option.reruns_delay = 1


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Exclude bootstrap tests unless explicitly selected with -m bootstrap."""
    markexpr: str = config.option.markexpr or ""
    if "bootstrap" in markexpr:
        return
    items[:] = [item for item in items if item.get_closest_marker("bootstrap") is None]


def _load_auth_for_test(request: pytest.FixtureRequest, with_login: bool) -> bool:
    if with_login:
        return True
    if request.node.get_closest_marker("login") is not None:
        return True
    return False


def _context_options(
    base_url: str,
    config: dict,
    *,
    load_auth: bool,
    shipping_state: Path | None = None,
) -> dict:
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
        "accept_downloads": True,
        "geolocation": {
            "latitude": 38.4088,
            "longitude": -121.3716,
        },
        "permissions": ["geolocation"],
        "record_video_dir": "reports/videos" if config.get("record_video") else None,
    }
    if headless:
        options["viewport"] = {"width": 1920, "height": 1080}
    else:
        options["no_viewport"] = True

    if load_auth:
        auth_path = resolve_auth_state_path()
        if auth_path is not None:
            options["storage_state"] = str(auth_path)
    elif shipping_state is not None:
        options["storage_state"] = str(shipping_state)

    return options


@pytest.fixture(scope="session")
def shipping_storage_state(
    browser: Browser,
    base_url: str,
    config: dict,
) -> Path:
    """Session-scoped Ship-to-US cookies — reused to skip per-test Ship-to UI."""
    return ensure_shipping_storage_state(browser, base_url=base_url, config=config)


# ── session fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def config() -> dict:
    """Load environment config once for the whole session."""
    return ConfigLoader.load()


@pytest.fixture(scope="session")
def base_url(config: dict) -> str:
    """Application base URL for the active TEST_ENV (default: preprod)."""
    url: str = config.get("base_url", "https://www.ebay.com")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def with_login(request: pytest.FixtureRequest) -> bool:
    """True when --with-login or WITH_LOGIN=1 (opt-in authenticated E2E)."""
    cli_flag: bool = bool(request.config.getoption("--with-login"))
    env_flag: bool = os.getenv("WITH_LOGIN", "").lower() in ("1", "true", "yes")
    return cli_flag or env_flag


@pytest.fixture(scope="session")
def pw(config: dict) -> Generator[Playwright, None, None]:  # noqa: ARG001
    """Session-scoped Playwright instance."""
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(pw: Playwright, config: dict) -> Generator[Browser, None, None]:
    """Session-scoped Chromium browser — launched once, closed after all tests."""
    headless: bool = config.get("headless", True)
    launch_args: list[str] = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    if not headless:
        launch_args.append("--start-maximized")

    b = pw.chromium.launch(
        headless=headless,
        slow_mo=config.get("slow_mo", 50),
        args=launch_args,
    )
    yield b
    b.close()


# ── function fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def context(
    browser: Browser,
    base_url: str,
    config: dict,
    request: pytest.FixtureRequest,
    with_login: bool,
    shipping_storage_state: Path,
) -> Generator[BrowserContext, None, None]:
    """Function-scoped browser context — each test gets a clean session."""
    load_auth: bool = _load_auth_for_test(request, with_login)
    guest_shipping: Path | None = None if load_auth else shipping_storage_state
    context_options: dict = _context_options(
        base_url,
        config,
        load_auth=load_auth,
        shipping_state=guest_shipping,
    )

    ctx: BrowserContext = browser.new_context(**context_options)
    ctx.set_default_timeout(config.get("timeout", MAX_TIMEOUT_MS))
    ctx.set_default_navigation_timeout(config.get("timeout", MAX_TIMEOUT_MS))

    trace_on_failure: bool = config.get("trace_on_failure", True)
    if trace_on_failure:
        start_tracing(ctx)
        request.node._trace_started = True  # noqa: SLF001

    headless: bool = config.get("headless", True)
    if not headless:
        bootstrap: Page = ctx.new_page()
        _maximize_browser_window(bootstrap)
        bootstrap.close()

    yield ctx

    if trace_on_failure and getattr(request.node, "_trace_started", False):
        if not getattr(request.node, "_trace_saved", False):
            stop_tracing_without_save(ctx)

    ctx.close()


@pytest.fixture(scope="function")
def page(
    context: BrowserContext, request: pytest.FixtureRequest
) -> Generator[Page, None, None]:
    """Function-scoped page; failure screenshots attach via pytest_runtest_makereport."""
    pg: Page = context.new_page()
    yield pg
    pg.close()


# ── Allure hooks ─────────────────────────────────────────────────────────────


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Attach test phase result to the item; capture failure screenshots for Allure."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    if rep.when == "call":
        from utilities.logger import log

        duration: str = _format_duration(rep.duration)
        label: str = _test_outcome_label(rep.outcome)
        log.info(f"[test]   {label} in {duration} — {item.nodeid}")

    if rep.when != "call" or not rep.failed:
        return

    config: dict | None = item.funcargs.get("config")
    page: Page | None = item.funcargs.get("page")
    context: BrowserContext | None = item.funcargs.get("context")

    if config is not None and config.get("trace_on_failure", True) and context is not None:
        if getattr(item, "_trace_started", False) and not getattr(item, "_trace_saved", False):
            trace_path: Path | None = save_failure_trace(context, test_name=item.name)
            item._trace_saved = True  # noqa: SLF001
            if trace_path is not None:
                attach_failure_trace(trace_path)

    if config is not None and not config.get("screenshot_on_failure", True):
        return

    if page is None or page.is_closed():
        return

    attach_failure_screenshot(page, item.name)


def pytest_sessionstart(session: pytest.Session) -> None:  # noqa: ARG001
    """Executed before collection — useful for CI banners."""
    pass


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int
) -> None:  # noqa: ARG001
    """Executed after the last test — generate environment.properties for Allure."""
    import os
    from pathlib import Path

    props_path = Path("reports/allure-results/environment.properties")
    props_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.getenv("TEST_ENV", "preprod")
    props_path.write_text(
        f"Environment={env}\n" f"Browser=Chromium\n" f"Framework=Playwright+pytest\n"
    )
