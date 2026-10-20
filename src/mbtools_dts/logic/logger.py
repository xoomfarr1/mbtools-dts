"""Lightweight timestamped bus logger.

The engine keeps a :class:`BusMonitor` that records the frames it sees.  This
module provides a small writer that serialises those frames to a JSON log so a
human can replay or compare a session.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def write_log(path: Path, entries: list[dict]) -> None:
    """Write *entries* to *path* as a JSON list.

    Each *entry* is a dict with keys: ``timestamp``, ``direction``,
    ``frame`` (hex string), ``id`` (hex string), ``dlc`` (int), ``data``
    (hex string).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)


def parse_log(path: Path) -> list[dict]:
    """Read a bus log written by :func:`write_log` back into a list of dicts."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
