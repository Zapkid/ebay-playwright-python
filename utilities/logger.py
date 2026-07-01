"""Thin logging wrapper — concise terminal output during test runs.

Usage:
    from utilities.logger import log

    log.info("[search] Searching 'handmade jewelry' | $10–$50 | limit=3")
    log.info("[cart]   → Item 1/3: Silver Ring ($24.99)")
    log.warning("[cart]   ✗ Add-to-cart not confirmed for item 2")
    log.error("[verify] Subtotal mismatch: displayed $60 vs calculated $55")

Live output is enabled via log_cli = true in pyproject.toml.
"""

from __future__ import annotations

import logging

# Single named logger for the entire suite
log: logging.Logger = logging.getLogger("ebay")
