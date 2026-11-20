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
    # trade_signal_log.csv had a 720h cadence here from 2026-09-16
    # (evidence_loop_repair_spec.md Part 1) until 2026-11-15. With operating
    # data it failed every run from 2026-11-12: the framework stood aside in
    # every open-market run since 2026-10-13, the honest quiet month the
    # comment warned about. It is now watched by agreement_lines() instead
    # (docs/specs/alert_importance_spec.md N7).
]

# The live job whose runs write each cadence ledger (scripts/run_count.py
# wrapper kinds). While launchd has every job of that kind disabled, the
# ledger has no live writer and so no cadence (AGENTS rule 8): it renders
# "stopped:", never STALE. Re-enabling the job restores the cadence with no
# code change. Added 2026-11-17 when owner ruling M1 stopped the GBP brief
# and grader jobs.
WRITERS = {"regime_classification_log.csv": "brief",
           "session_context_log.csv":       "brief",
           "shadow_signal_log.csv":         "brief"}


def _shown(epoch: float) -> str:
    """An epoch as the owner reads it: display_time's 12-hour PT clock
    (display_timezone_spec addendum 2026-11-18). ISO-UTC only if the helper
    cannot load."""
    try:
        if PROJ not in sys.path:
            sys.path.insert(0, PROJ)
        from datetime import datetime, timezone
        from display_time import to_display
        s = to_display(datetime.fromtimestamp(epoch, timezone.utc))
    except Exception:
        s = ""
    return s or time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(epoch))


def _stopped_kinds() -> dict:
    """launchd's stopped wrapper kinds. A failed lookup returns {} so every
    cadence applies: a loud STALE, never a silent pass."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import run_count
        return run_count.stopped_kinds(disabled=run_count.disabled_labels())
    except Exception:
        return {}


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
    ("trade_signal_log.csv",
                   "event-driven — a row only for an open-market LONG/SHORT, "
                   "and a stand-aside month is normal. Its writer is checked "
                   "by agreement_lines(): every regime_classification_log row "
                   "with stand_down False must have its trade row "
                   "(docs/specs/alert_importance_spec.md N7)."),
    ("notification_log.csv",
                   "event-driven — one row per notification actually sent, "
                   "written by notify() (scripts/notification_ledger.py), and "
                   "none while ALERTS_MUTED holds back a category, so quiet "
                   "days are normal. gold_briefing.py reads it for ARRIVAL and "
                   "LEVEL BREAK rows; with none it says those alerts are not "
                   "live yet, never that none were sent "
                   "(configuration_detector_spec.md §14.1, §14.2)."),
]

# N7: a trade call recorded in the regime log must have its trade-signal row.
AGREE_WINDOW_S = 600
AGREE_LOOKBACK_H = 720


def agreement_lines(now: float | None = None, proj: str | None = None) -> list[str]:
    """One line: STALE when the regime log shows an open-market trade call
    in the last AGREE_LOOKBACK_H with no trade_signal_log row for the same
    instrument within AGREE_WINDOW_S; otherwise 'agree:'."""
    import csv
    from datetime import datetime
    now = time.time() if now is None else now
    proj = PROJ if proj is None else proj

    def rows(rel):
        path = os.path.join(proj, rel)
        if not os.path.exists(path):
            return []
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            got = list(csv.DictReader(f))
        try:
            from exclusions import filter_rows
        except ImportError:                     # behavioral-test sandboxes only
            return got
        return filter_rows(got, rel)

    def epoch(r):
        try:
            return datetime.fromisoformat((r.get("timestamp") or "").strip()
                                          .replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    if not os.path.exists(os.path.join(proj, "regime_classification_log.csv")):
        # Never an all-clear from a file that was not read (rule 9); the
        # regime log's own cadence line already reports it MISSING.
        return ["unchecked: trade_signal_log.csv — regime_classification_log.csv "
                "is missing, so trade calls cannot be checked"]
    # Only rows with a logic_version: under those rules apply_filter allows
    # iff the official decision trades (decision_logic_spec; the 36,864-cell
    # sweep in test_decision_logic.py). Blank-version rows (before
    # 2026-09-30) could allow a trade while the decision stood aside: 10
    # such rows in late September have no trade row, correctly.
    calls = [(epoch(r), r.get("instrument", "")) for r in rows("regime_classification_log.csv")
             if (r.get("stand_down") or "").strip().lower() == "false"
             and (r.get("logic_version") or "").strip()]
    calls = [(t, i) for t, i in calls if t is not None and 0 <= now - t <= AGREE_LOOKBACK_H * 3600]
    if not calls:
        return [f"agree: trade_signal_log.csv — no open-market trade call in the last "
                f"{AGREE_LOOKBACK_H}h, so no row is expected"]
    logged = [(epoch(r), r.get("instrument", "")) for r in rows("trade_signal_log.csv")]
    missing = [(t, i) for t, i in calls
               if not any(u is not None and j == i and abs(u - t) <= AGREE_WINDOW_S
                          for u, j in logged)]
    if missing:
        t, i = min(missing)
        first = _shown(t)
        return [f"STALE: trade_signal_log.csv — {len(missing)} of {len(calls)} trade calls "
                f"in the regime log have no trade row (first: {i} {first}); the "
                f"trade-signal writer may be dead"]
    return [f"agree: trade_signal_log.csv — all {len(calls)} trade calls in the last "
            f"{AGREE_LOOKBACK_H}h have their row"]


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
        if t is None:
            # Review F6: no parseable row means no live writer has proven
            # anything. Falling back to mtime would let a grader rewrite of a
            # header-only file read as fresh, the hole D6 closed.
            return float("inf"), "no timestamped rows"
        return (now - t) / 3600.0, "newest row"
    return (now - mtime) / 3600.0, "file time"


def check(now: float | None = None, proj: str | None = None,
          stopped: dict | None = None) -> list[str]:
    """Return the per-artifact report lines. `stopped` ({wrapper kind:
    [labels]}) defaults to launchd's own state for the live project and to
    none for an explicit project (a test fixture)."""
    now = time.time() if now is None else now
    if stopped is None:
        stopped = _stopped_kinds() if proj is None else {}
    proj = PROJ if proj is None else proj
    lines = []
    for rel, cadence_h in CADENCES:
        path = os.path.join(proj, rel)
        kind = WRITERS.get(rel)
        if kind in stopped:
            lines.append(f"stopped: {rel} — its writer ({kind}: "
                         f"{', '.join(stopped[kind])}) is disabled in launchd; "
                         f"no cadence while stopped (AGENTS rule 8)")
            continue
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
        elif basis == "no timestamped rows":
            lines.append(f"STALE: {rel} — no timestamped rows (a rewrite "
                         f"cannot prove a live writer), expected within "
                         f"{cadence_h}h")
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
            for line in check() + agreement_lines() + read_side_lines():
                print(line)
    except Exception as e:
        # A crashing check used to print nothing, which the wrapper read as
        # healthy: a broken health check looked like good health. Now it
        # fails the run (alert_importance_spec N7).
        print(f"STALE: artifact_freshness — the check itself failed "
              f"({type(e).__name__}: {e})")
    return 0                            # always


if __name__ == "__main__":
    sys.exit(main(sys.argv))
