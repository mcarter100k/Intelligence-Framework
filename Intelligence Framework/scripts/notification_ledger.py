"""
notification_ledger.py — one row per notification actually sent
(docs/specs/notification_ledger_spec.md). Called by notify() in
scripts/notify.sh after the send command exits 0. Writes through
ledger_io.append_row. On failure it exits nonzero with the reason on
stderr, and notify() writes that reason into the day log.

Usage: python3 scripts/notification_ledger.py <project> <category> <pairs> <decision_state> <summary>
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

FILE = "notification_log.csv"
FIELDS = ["timestamp_utc", "category", "pairs", "decision_state", "summary"]


def append(project: str, category: str, pairs: str, decision_state: str,
           summary: str, now: datetime | None = None) -> None:
    if project not in sys.path:
        sys.path.insert(0, project)
    from ledger_io import append_row
    t = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    append_row(os.path.join(project, FILE), FIELDS,
               {"timestamp_utc": t, "category": category, "pairs": pairs,
                "decision_state": decision_state, "summary": summary})


if __name__ == "__main__":
    if len(sys.argv) != 6:
        sys.exit("usage: notification_ledger.py <project> <category> <pairs> "
                 "<decision_state> <summary>")
    try:
        append(*sys.argv[1:6])
    except Exception as e:
        sys.exit(f"{type(e).__name__}: {e}")
