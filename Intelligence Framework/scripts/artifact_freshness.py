"""
artifact_freshness.py — evidence-artifact staleness check (regime_log_restore
spec item 4a). Silence must never again mean "fine": the six-week
regime_classification_log.csv outage was invisible because nothing watched
last-write ages.

Each evidence artifact has an EXPECTED CADENCE (hours). The check reports
every artifact's age; anything past its cadence is a STALE line. The
scheduled wrapper treats any STALE line as a health FAILURE (health_state.py),
so the existing 2-consecutive / daily-repeat alerting fires the UNHEALTHY
path; the Sunday heartbeat prints the full report and treats STALE as
NEEDS ATTENTION.

Usage:
    python3 scripts/artifact_freshness.py check
Stdout: one line per artifact —
    "fresh: <name> — <age>h old (cadence <N>h)"  or
    "STALE: <name> — last write <age>h ago, expected within <N>h"
    ("STALE: <name> — MISSING" when the file does not exist)
Exit 0 always (exit-0 discipline: the watcher never breaks the runs).

Cadence basis (informed priors, revisit with operating data):
  regime_classification_log.csv  72h  — 3 scheduled briefs/weekday; covers weekend
  session_context_log.csv        72h  — written by the same runs
  calendar.csv                  192h  — weekly fetch + midweek retry
  storylines.md                 216h  — weekly Sunday session
  shadow_signal_log.csv         504h  — candidates fire irregularly; generous
"""
from __future__ import annotations

import os
import sys
import time

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (relative path, expected cadence in hours)
CADENCES = [
    ("regime_classification_log.csv", 72),
    ("session_context_log.csv",       72),
    ("calendar.csv",                 192),
    ("storylines.md",                216),
    ("shadow_signal_log.csv",        504),
]


def check(now: float | None = None, proj: str | None = None) -> list[str]:
    """Return the per-artifact report lines. Pure function of file mtimes."""
    now = time.time() if now is None else now
    proj = PROJ if proj is None else proj
    lines = []
    for rel, cadence_h in CADENCES:
        path = os.path.join(proj, rel)
        try:
            age_h = (now - os.path.getmtime(path)) / 3600.0
        except OSError:
            lines.append(f"STALE: {rel} — MISSING")
            continue
        if age_h > cadence_h:
            lines.append(f"STALE: {rel} — last write {age_h:.0f}h ago, "
                         f"expected within {cadence_h}h")
        else:
            lines.append(f"fresh: {rel} — {age_h:.0f}h old "
                         f"(cadence {cadence_h}h)")
    return lines


def main(argv) -> int:
    try:
        if len(argv) > 1 and argv[1] == "check":
            for line in check():
                print(line)
    except Exception:
        pass
    return 0                            # always


if __name__ == "__main__":
    sys.exit(main(sys.argv))
