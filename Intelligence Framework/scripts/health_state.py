"""
health_state.py — consecutive-failure tracker for the scheduled wrappers,
PER JOB. Per docs/specs/heartbeat_spec.md (Spec A), made per-job by
docs/specs/visible_failures_spec.md (D4). Stdlib only; never raises;
always exits 0 (exit-0 discipline: a broken health tracker must not break
the runs it watches).

Usage (from the wrappers):
    python3 scripts/health_state.py record-failure <job> "<reason>"
    python3 scripts/health_state.py record-success <job>
    python3 scripts/health_state.py status          # for the weekly heartbeat
Jobs: brief, outcomes. (A legacy call with no job counts toward `brief`.)

Why per job: the jobs used to share one counter. The brief failed three
times a day (a stale human-written file), and the 15:15 grader's success
reset the shared streak and sent "RECOVERED after N failed runs" for a
brief that had not recovered. That was a false alarm pair every day, and a
grader failing between brief successes never reached an alert at all.

Stdout protocol (one line, or nothing):
    ALERT:<JOB> UNHEALTHY — <reason> — Nth consecutive failed run
        printed when that job's failures >= ALERT_AFTER and no alert fired
        for that job yet today (repeats DAILY while unhealthy).
    RECOVERED: <job> healthy again after N failed runs
        printed exactly once, when that job's success ends its streak.

State file: logs/health_state.json = {"jobs": {<job>: {...}}}. A missing or
corrupt file is zero state, never an error. The pre-2026-09-29 flat format
is migrated into the `brief` job, which is where its streak came from.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "logs", "health_state.json")
ALERT_AFTER = 2          # consecutive failed runs before the first alert
JOBS = ("brief", "outcomes")
_FLAT_KEYS = ("consecutive_failures", "last_failure_reason",
              "last_failure_utc", "last_alert_date", "last_success_utc")


def _load() -> dict:
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {"jobs": {}}
    except Exception:
        return {"jobs": {}}             # missing/corrupt = zero state
    if "jobs" not in d or not isinstance(d.get("jobs"), dict):
        legacy = {k: d[k] for k in _FLAT_KEYS if k in d}
        d = {"jobs": {"brief": legacy} if legacy else {}}
    return d


def _save(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass                            # tracker failure never breaks a run


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_failure(job: str, reason: str) -> str:
    """Count a failed run of `job`; return the alert line to emit, or ''."""
    d = _load()
    j = d["jobs"].setdefault(job, {})
    n = int(j.get("consecutive_failures", 0) or 0) + 1
    today = _now().strftime("%Y-%m-%d")
    j.update({
        "consecutive_failures": n,
        "last_failure_reason": reason,
        "last_failure_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    out = ""
    if n >= ALERT_AFTER and j.get("last_alert_date") != today:
        j["last_alert_date"] = today    # daily repeat, not per-run
        nth = {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")
        out = (f"ALERT:{job.upper()} UNHEALTHY — {reason} — "
               f"{nth} consecutive failed run")
    _save(d)
    return out


def record_success(job: str) -> str:
    """Reset `job`'s streak; return its one-shot recovery line, or ''."""
    d = _load()
    j = d["jobs"].setdefault(job, {})
    n = int(j.get("consecutive_failures", 0) or 0)
    out = f"RECOVERED: {job} healthy again after {n} failed runs" if n > 0 else ""
    j.update({
        "consecutive_failures": 0,
        "last_alert_date": "",
        "last_success_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    _save(d)
    return out


def _disp(iso: str) -> str:
    """Render a stored UTC stamp in the display zone (storage stays UTC).
    Falls back to the raw stamp if the helper is unavailable."""
    try:
        import sys as _s
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in _s.path:
            _s.path.insert(0, _root)
        from display_time import to_display
        return to_display(iso) or iso
    except Exception:
        return iso


def _job_status(job: str, j: dict) -> str:
    n = int(j.get("consecutive_failures", 0) or 0)
    last_ok = _disp(j.get("last_success_utc")) or "not yet recorded"
    if n == 0:
        return f"{job}: healthy — last success {last_ok}"
    return (f"{job}: UNHEALTHY — {n} consecutive failed run(s); last reason: "
            f"{j.get('last_failure_reason', '?')}; last success: {last_ok}")


def status() -> str:
    """One line covering every job, so a single UNHEALTHY job is visible."""
    d = _load()
    jobs = sorted(set(JOBS) | set(d["jobs"]))
    return " | ".join(_job_status(job, d["jobs"].get(job, {})) for job in jobs)


def main(argv) -> int:
    try:
        cmd = argv[1] if len(argv) > 1 else ""
        rest = argv[2:]
        # Legacy form (no job): count toward `brief`, whose streak it was.
        job = rest[0] if rest and rest[0] in JOBS else "brief"
        if rest and rest[0] in JOBS:
            rest = rest[1:]
        if cmd == "record-failure":
            line = record_failure(job, rest[0] if rest else "unknown failure")
        elif cmd == "record-success":
            line = record_success(job)
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
