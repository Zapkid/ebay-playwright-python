"""Login workflow — E2E tests for eBay session replay.

Requires secured_env_files/ebay-auth.json from manual bootstrap (local only):
    uv run python -m scripts.bootstrap_ebay_auth
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from utilities.auth_storage import auth_state_exists
from utilities.screenshot_utils import take_screenshot
from utilities.verifications import verify_contains, verify_true
from workflows.ensure_logged_in import ensure_logged_in


@pytest.fixture(autouse=True)
def _before_login_test(request: pytest.FixtureRequest) -> None:
    """Before hook: skip login tests when no saved session file."""
    if request.node.get_closest_marker("login") is None:
        return

    if not auth_state_exists():
        pytest.skip(
            "No saved session (secured_env_files/ebay-auth.json). "
            "Run: uv run python -m scripts.bootstrap_ebay_auth"
        )


@allure.suite("eBay E2E")
@allure.feature("Authentication")
@pytest.mark.login
class TestLogin:
    """eBay sign-in via saved session replay."""

    @allure.story("Authenticated session replay")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_success(self, page: Page, base_url: str) -> None:
        """Verify a valid session from ebay-auth.json and post-login URL on eBay."""
        success: bool = ensure_logged_in(page, base_url=base_url)

        verify_true(
            success,
            "Not logged in — run uv run python -m scripts.bootstrap_ebay_auth",
        )

        current_url: str = page.url
        verify_contains(
            current_url,
            "ebay.com",
            f"Unexpected URL after login: {current_url}",
        )

        take_screenshot(page, name="logged_in_home")
