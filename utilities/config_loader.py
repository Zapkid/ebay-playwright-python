"""Environment configuration loader.

Reads TEST_ENV from the shell/CI environment and merges the matching
resources/<env>/config.json with any runtime overrides (HEADLESS, SLOW_MO, etc.).

Auth session file (ebay-auth.json) is local-only — see utilities/auth_storage.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from utilities.timeouts import MAX_TIMEOUT_MS


class ConfigLoader:
    """Loads and merges environment-specific configuration."""

    _RESOURCES_DIR = Path(__file__).parents[1] / "resources"
    _VALID_ENVS: frozenset[str] = frozenset({"staging", "preprod", "prod"})

    @classmethod
    def load(cls, env: str | None = None) -> dict:
        """Return merged config for the requested (or $TEST_ENV) environment."""
        env = (env or os.getenv("TEST_ENV", "preprod")).lower()
        if env not in cls._VALID_ENVS:
            raise ValueError(f"Unknown TEST_ENV '{env}'. Must be one of {cls._VALID_ENVS}")

        config_path = cls._RESOURCES_DIR / env / "config.json"
        with config_path.open() as fh:
            config: dict = json.load(fh)

        # Allow env-var overrides for CI/CD pipelines
        if (headless := os.getenv("HEADLESS")) is not None:
            config["headless"] = headless.lower() in ("1", "true", "yes")
        if (slow_mo := os.getenv("SLOW_MO")) is not None:
            config["slow_mo"] = int(slow_mo)
        if (timeout := os.getenv("DEFAULT_TIMEOUT")) is not None:
            config["timeout"] = int(timeout)

        config["timeout"] = min(int(config.get("timeout", MAX_TIMEOUT_MS)), MAX_TIMEOUT_MS)
        config.setdefault("headless", True)

        return config
