"""CSV recording utilities for product URLs and prices."""

from __future__ import annotations

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


_LOCK = threading.Lock()

DEFAULT_CSV_PATH = Path(__file__).parents[1] / "downloads" / "search_results.csv"
_FIELDNAMES: Sequence[str] = ["timestamp", "test_id", "query", "url", "price", "title"]


def init_csv(path: Path = DEFAULT_CSV_PATH) -> None:
    """Create (or overwrite) the CSV with headers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
        writer.writeheader()


def append_product(
    *,
    url: str,
    price: float | None = None,
    title: str = "",
    query: str = "",
    test_id: str = "",
    path: Path = DEFAULT_CSV_PATH,
) -> None:
    """Append a single product row to the CSV (thread-safe)."""
    row = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "test_id": test_id,
        "query": query,
        "url": url,
        "price": f"{price:.2f}" if price is not None else "",
        "title": title,
    }
    with _LOCK, path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
        writer.writerow(row)
