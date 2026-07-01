"""One-time manual auth bootstrap — thin pytest wrapper around the bootstrap script.

Not part of the normal test suite. Run explicitly:
    HEADLESS=false pytest -m bootstrap -s
"""

from __future__ import annotations

import pytest

from scripts.bootstrap_ebay_auth import run_bootstrap


@pytest.mark.bootstrap
def test_bootstrap_ebay_auth() -> None:
    """Open headed browser; complete sign-in manually; save session file."""
    run_bootstrap(force=False)
