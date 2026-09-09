"""
health_state.py — consecutive-failure tracker for the scheduled wrappers.
Per docs/specs/heartbeat_spec.md (Spec A). Stdlib only; never raises;
always exits 0 (exit-0 discipline: a broken health tracker must not break
the runs it watches).

Usage (from the wrappers):
    python3 scripts/health_state.py record-failure "<reason>"
    python3 scripts/health_state.py record-success
    python3 scripts/health_state.py status          # for the weekly heartbeat

Stdout protocol (one line, or nothing):
    ALERT:FRAMEWORK UNHEALTHY — <reason> — Nth consecutive failed run
        printed when failures >= ALERT_AFTER and no alert fired yet today
        (repeats DAILY while unhealthy, not per-run).
    RECOVERED after N failed runs
        printed exactly once, when a success ends a failure streak.

State file: logs/health_state.json — written by the automation layer, like
everything under logs/. A corrupt or missing file is zero state, never an
error (fail-open for tracking; the runs themselves are what matter).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "logs", "health_state.json")
ALERT_AFTER = 2          # consecutive failed runs before the first alert


def _load() -> dict:
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {}
        return d
    except Exception:
        return {}                       # missing/corrupt = zero state


def _save(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass                            # tracker failure never breaks a run


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_failure(reason: str) -> str:
    """Count a failed run; return the alert line to emit, or ''."""
    d = _load()
    n = int(d.get("consecutive_failures", 0) or 0) + 1
    today = _now().strftime("%Y-%m-%d")
    d.update({
        "consecutive_failures": n,
        "last_failure_reason": reason,
        "last_failure_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    out = ""
    if n >= ALERT_AFTER and d.get("last_alert_date") != today:
        d["last_alert_date"] = today    # daily repeat, not per-run
        nth = {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")
        out = f"ALERT:FRAMEWORK UNHEALTHY — {reason} — {nth} consecutive failed run"
    _save(d)
    return out


def record_success() -> str:
    """Reset the streak; return the one-shot recovery line, or ''."""
    d = _load()
    n = int(d.get("consecutive_failures", 0) or 0)
    out = f"RECOVERED after {n} failed runs" if n > 0 else ""
    d.update({
        "consecutive_failures": 0,
        "last_alert_date": "",
        "last_success_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    _save(d)
    return out


def status() -> str:
    d = _load()
    n = int(d.get("consecutive_failures", 0) or 0)
    if n == 0:
        return (f"healthy — last success "
                f"{d.get('last_success_utc') or 'not yet recorded'}")
    return (f"UNHEALTHY — {n} consecutive failed run(s); last reason: "
            f"{d.get('last_failure_reason', '?')}; last success: "
            f"{d.get('last_success_utc') or 'not yet recorded'}")


def main(argv) -> int:
    try:
        cmd = argv[1] if len(argv) > 1 else ""
        if cmd == "record-failure":
            line = record_failure(argv[2] if len(argv) > 2 else "unknown failure")
        elif cmd == "record-success":
            line = record_success()
        elif cmd == "status":
            line = status()
        else:
            line = ""
        if line:
            print(line)
    except Exception:
        pass
    return 0                            # always


if __name__ == "__main__":
    sys.exit(main(sys.argv))
