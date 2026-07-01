"""Persist and load eBay browser session state (Playwright storage_state).

Local development only — the saved session file is gitignored and is not
intended for CI until a secret/artifact upload flow exists.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext

_AUTH_DIR: Path = Path(__file__).parents[1] / "secured_env_files"
AUTH_STATE_PATH: Path = _AUTH_DIR / "ebay-auth.json"


def auth_state_exists() -> bool:
    """Return True when a saved session file is present."""
    return AUTH_STATE_PATH.is_file()


def resolve_auth_state_path() -> Path | None:
    """Return the session file path when it exists, else None."""
    if auth_state_exists():
        return AUTH_STATE_PATH
    return None


def save_auth_state(context: BrowserContext) -> Path:
    """Write cookies/localStorage from *context* to the session file."""
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(AUTH_STATE_PATH))
    return AUTH_STATE_PATH
