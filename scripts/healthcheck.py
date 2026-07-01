"""Preflight checks before bootstrap or other local Playwright workflows.

Usage:
    uv run python -m scripts.healthcheck
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from utilities.auth_storage import AUTH_STATE_PATH
from utilities.config_loader import ConfigLoader


class HealthCheckError(RuntimeError):
    """One or more preflight checks failed."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _check_config() -> CheckResult:
    try:
        config: dict = ConfigLoader.load()
    except (ValueError, OSError, KeyError) as exc:
        return CheckResult("config", False, str(exc))

    base_url: str = config.get("base_url", "").rstrip("/")
    if not base_url:
        return CheckResult("config", False, "base_url is missing from config.json")

    return CheckResult("config", True, f"TEST_ENV ok, base_url={base_url}")


def _check_chromium() -> CheckResult:
    try:
        with sync_playwright() as playwright:
            executable: str = playwright.chromium.executable_path
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "chromium",
            False,
            f"{exc}. Run: uv run playwright install chromium",
        )

    if not Path(executable).is_file():
        return CheckResult(
            "chromium",
            False,
            f"Chromium binary not found at {executable}. "
            "Run: uv run playwright install chromium",
        )

    return CheckResult("chromium", True, "Chromium browser installed")


def _check_base_url_reachable(base_url: str, *, timeout_s: float = 15.0) -> CheckResult:
    request = urllib.request.Request(
        base_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            status: int = response.status
    except urllib.error.HTTPError as exc:
        if exc.code < 500:
            return CheckResult(
                "connectivity", True, f"{base_url} reachable (HTTP {exc.code})"
            )
        return CheckResult(
            "connectivity", False, f"{base_url} returned HTTP {exc.code}"
        )
    except urllib.error.URLError as exc:
        return CheckResult(
            "connectivity", False, f"Cannot reach {base_url}: {exc.reason}"
        )
    except TimeoutError:
        return CheckResult(
            "connectivity",
            False,
            f"Timed out reaching {base_url} after {timeout_s:.0f}s",
        )

    if status >= 500:
        return CheckResult("connectivity", False, f"{base_url} returned HTTP {status}")

    return CheckResult("connectivity", True, f"{base_url} reachable (HTTP {status})")


def _check_auth_dir_writable() -> CheckResult:
    auth_dir: Path = AUTH_STATE_PATH.parent
    try:
        auth_dir.mkdir(parents=True, exist_ok=True)
        probe: Path = auth_dir / ".healthcheck_write_probe"
        probe.write_text("")
        probe.unlink()
    except OSError as exc:
        return CheckResult(
            "auth_dir",
            False,
            f"Cannot write to {auth_dir}: {exc}",
        )

    return CheckResult("auth_dir", True, f"{auth_dir} is writable")


def run_healthcheck(*, verbose: bool = True) -> list[CheckResult]:
    """Run all preflight checks. Raises HealthCheckError when any check fails."""
    results: list[CheckResult] = [_check_config(), _check_chromium()]

    config_result: CheckResult = results[0]
    if config_result.ok:
        config: dict = ConfigLoader.load()
        base_url: str = config.get("base_url", "https://www.ebay.com").rstrip("/")
        results.append(_check_base_url_reachable(base_url))
    else:
        results.append(
            CheckResult("connectivity", False, "skipped — config check failed"),
        )

    results.append(_check_auth_dir_writable())

    failures: list[CheckResult] = [result for result in results if not result.ok]

    if verbose:
        for result in results:
            status: str = "OK" if result.ok else "FAIL"
            print(f"[healthcheck] {status:4}  {result.name}: {result.detail}")

    if failures:
        messages: list[str] = [f"{result.name}: {result.detail}" for result in failures]
        raise HealthCheckError(
            "Preflight checks failed:\n  - " + "\n  - ".join(messages)
        )

    return results


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
    try:
        run_healthcheck(verbose=True)
    except HealthCheckError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("[healthcheck] All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
