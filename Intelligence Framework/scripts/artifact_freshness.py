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
    "fresh: <name> — <age>h old (<basis>; cadence <N>h)"  or
    "STALE: <name> — last write <age>h ago (<basis>), expected within <N>h"
    ("STALE: <name> — MISSING" when the file does not exist)
    "DUE: <name> — ..." for a HUMAN-written file past its cadence: a
    reminder only, never a run failure (visible_failures_spec D5).
    <basis> is "newest row" for the live ledgers (D6), else "file time".
Exit 0 always (exit-0 discipline: the watcher never breaks the runs).

Cadence basis (informed priors, revisit with operating data):
  regime_classification_log.csv  72h  — 3 scheduled briefs/weekday; covers weekend
  session_context_log.csv        72h  — written by the same runs
  calendar.csv                  192h  — weekly fetch + midweek retry
  storylines.md                 216h  — weekly Sunday session
  shadow_signal_log.csv         504h  — candidates fire irregularly; generous

READ-SIDE INVENTORY (added 2026-09-16,
docs/specs/level_source_repair_spec.md guard A). The table above is
write-side only, which is exactly why a 98-day-stale `last_run.json` —
read by entry_confirmation, written by nobody live — was invisible to it.
Every artifact the live path READS must now be accounted for here, either
by carrying a cadence above or by appearing in READ_SIDE_NO_CADENCE with
a stated reason. A cadence is only meaningful where one is genuinely
expected; inventing one for an event-driven file would manufacture false
alarms, so those are listed and explicitly excused instead. The point is
that the boundary is documented rather than assumed — a new live-path
read cannot be introduced silently (pinned by
test_live_path_connections.py).

NOTE: `last_run.json` is deliberately absent. R1 removed the read
entirely rather than monitoring it — deleting a staleness class beats
watching one.
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
    # Added 2026-09-16 (evidence_loop_repair_spec.md Part 1). Neither was
    # watched, which is why trade_signal_log.csv could sit at 2 lines since
    # 2026-06-28 while run_outcome_check graded it nightly. Cadences are
    # generous on purpose: a directional decision is NOT a daily event, and
    # an honest run of STAND ASIDE days must not raise a health failure.
    # 720h/1440h are informed priors — revisit once the ledger has operating
    # data, which by definition it does not yet have.
    ("trade_signal_log.csv",         720),
]

# Read-side artifacts with NO expected cadence. (relative path, reason)
# These are reported for visibility and can never render a STALE line —
# a cadence here would alarm on normal operation.
READ_SIDE_NO_CADENCE = [
    ("trades.csv", "event-driven — weeks without a trade is normal; the "
                   "circuit breaker fails closed on a malformed file, which "
                   "is the real control here"),
    (".env",       "credentials, not an evidence artifact — its failure mode "
                   "is a failed run, already caught by health_state"),
    ("excluded_rows.csv",
                   "exclusion registry — changes only when a contaminated or "
                   "withdrawn row is authorized out of the tallies, which may "
                   "be never. Per STANDING RULE 8 a cadence requires a live "
                   "writer; this one's writer is a human authorization event, "
                   "so it is inventoried and never alarmed on. Its integrity "
                   "control is test_exclusions.py, not freshness."),
    ("trade_log.csv",
                   "FROZEN historical evidence, deliberately writer-less. The "
                   "April-era framework-snapshot file (bias/value_zone "
                   "schema), superseded by trades.csv; trade_logger.py:22 and "
                   "trade_logger_repair_spec.md:23-28 already ruled it stays "
                   "untouched. The 2026-09-16 ruling asked for a cadence here; "
                   "premise inspection (standing rule 5) says a cadence would "
                   "render STALE forever — measured at 3987h on the first live "
                   "check — making every scheduled run a health FAILURE and "
                   "training the operator to ignore the channel. Inventoried "
                   "without a cadence instead. Team to confirm."),
]


def read_side_lines(proj: str | None = None) -> list[str]:
    """Visibility lines for read-side artifacts that carry no cadence.
    Never STALE by construction — prefix is 'watched:' so the wrapper's
    '^STALE:' grep cannot turn these into a health failure."""
    proj = PROJ if proj is None else proj
    lines = []
    for rel, reason in READ_SIDE_NO_CADENCE:
        present = os.path.exists(os.path.join(proj, rel))
        lines.append(f"watched: {rel} — no cadence "
                     f"({'present' if present else 'absent'}; {reason})")
    return lines


# Written by a HUMAN, not by a live job (docs/specs/visible_failures_spec.md
# D5). Rule 8: a cadence requires a live writer. Past-due renders as a DUE:
# reminder, never a STALE: failure. Before this, a stale storylines.md failed
# every healthy brief run and made the health channel alarm daily.
HUMAN_WRITTEN = {"storylines.md"}

# Ledgers whose age is the NEWEST ROW's timestamp, not the file's mtime
# (D6). The nightly graders rewrite whole files, which refreshes mtime even
# when no live writer has appended anything, so mtime hid a dead writer.
ROW_TIMESTAMPED = {"regime_classification_log.csv", "session_context_log.csv",
                   "shadow_signal_log.csv", "trade_signal_log.csv"}


def _newest_row_epoch(path: str) -> float | None:
    """Epoch seconds of the newest `timestamp` in a CSV ledger, or None."""
    import csv
    from datetime import datetime
    newest = None
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                ts = (row.get("timestamp") or "").strip()
                if not ts:
                    continue
                try:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
                newest = t if newest is None or t > newest else newest
    except Exception:
        return None
    return newest


def _age_hours(path: str, rel: str, now: float) -> tuple[float, str]:
    """(age in hours, basis). Raises OSError when the file is missing."""
    mtime = os.path.getmtime(path)
    if rel in ROW_TIMESTAMPED:
        t = _newest_row_epoch(path)
        if t is not None:
            return (now - t) / 3600.0, "newest row"
    return (now - mtime) / 3600.0, "file time"


def check(now: float | None = None, proj: str | None = None) -> list[str]:
    """Return the per-artifact report lines."""
    now = time.time() if now is None else now
    proj = PROJ if proj is None else proj
    lines = []
    for rel, cadence_h in CADENCES:
        path = os.path.join(proj, rel)
        human = rel in HUMAN_WRITTEN
        try:
            age_h, basis = _age_hours(path, rel, now)
        except OSError:
            lines.append(f"DUE: {rel} — MISSING (written by you; a reminder, "
                         f"never a run failure)" if human
                         else f"STALE: {rel} — MISSING")
            continue
        if age_h > cadence_h and human:
            lines.append(f"DUE: {rel} — last written {age_h:.0f}h ago, your "
                         f"cadence is {cadence_h}h (a reminder, never a run "
                         f"failure)")
        elif age_h > cadence_h:
            lines.append(f"STALE: {rel} — last write {age_h:.0f}h ago "
                         f"({basis}), expected within {cadence_h}h")
        else:
            lines.append(f"fresh: {rel} — {age_h:.0f}h old ({basis}; "
                         f"cadence {cadence_h}h)")
    return lines


def main(argv) -> int:
    try:
        if len(argv) > 1 and argv[1] == "check":
            for line in check():
                print(line)
            for line in read_side_lines():
                print(line)
    except Exception:
        pass
    return 0                            # always


if __name__ == "__main__":
    sys.exit(main(sys.argv))
