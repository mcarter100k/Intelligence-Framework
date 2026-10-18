"""
test_health_state.py — pins the Spec-A alerting contract
(docs/specs/heartbeat_spec.md item 1):

  failure #1 silent · #2 alerts · #3 same-day silent · next day repeats ·
  success resets and says RECOVERED exactly once · corrupt state = zero state.

Run: pytest tests/test_health_state.py
"""
import importlib.util
from _paths import ROOT
import json
import os
from datetime import datetime, timezone

import pytest

_spec = importlib.util.spec_from_file_location(
    "health_state",
    os.path.join(ROOT,
                 "scripts", "health_state.py"))
hs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hs)


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(hs, "STATE_FILE", str(tmp_path / "health_state.json"))
    return tmp_path / "health_state.json"


def _freeze(monkeypatch, iso):
    monkeypatch.setattr(hs, "_now",
                        lambda: datetime.fromisoformat(iso).replace(
                            tzinfo=timezone.utc))


def test_first_failure_is_silent(state):
    assert hs.record_failure("brief", "OANDA not configured") == ""

def test_second_failure_alerts_with_exact_message(state):
    hs.record_failure("brief", "OANDA not configured")
    out = hs.record_failure("brief", "OANDA not configured")
    assert out == ("ALERT:BRIEF UNHEALTHY — OANDA not configured — "
                   "2nd consecutive failed run")

def test_third_same_day_failure_does_not_realert(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    hs.record_failure("brief", "x"); assert hs.record_failure("brief", "x") != ""
    assert hs.record_failure("brief", "x") == ""   # daily repeat, not per-run

def test_next_day_failure_realerts_with_running_count(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    for _ in range(3):
        hs.record_failure("brief", "x")
    _freeze(monkeypatch, "2026-09-10T10:00:00")
    out = hs.record_failure("brief", "x")
    assert out.endswith("4th consecutive failed run")

def test_success_resets_and_reports_recovery_once(state):
    hs.record_failure("brief", "x"); hs.record_failure("brief", "x")
    assert hs.record_success("brief") == \
        "RECOVERED: brief healthy again after 2 failed runs"
    assert hs.record_success("brief") == ""        # exactly once
    assert hs.record_failure("brief", "y") == ""   # streak restarted at 1

def test_recovery_after_reset_allows_fresh_alert_same_day(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    hs.record_failure("brief", "x"); hs.record_failure("brief", "x")
    hs.record_success("brief")
    hs.record_failure("brief", "y")
    assert hs.record_failure("brief", "y") != ""   # new outage may re-alert

def test_reason_text_carried_through(state):
    hs.record_failure("outcomes", "no data from OANDA")
    out = hs.record_failure("outcomes", "no data from OANDA")
    assert out.startswith("ALERT:OUTCOMES UNHEALTHY") and "no data from OANDA" in out

def test_corrupt_state_file_is_zero_state(state):
    state.write_text("{not json")
    assert hs.record_failure("brief", "x") == ""   # counts as failure #1
    d = json.loads(state.read_text())
    assert d["jobs"]["brief"]["consecutive_failures"] == 1

def test_status_lines(state):
    s = hs.status()
    assert "brief: healthy" in s and "outcomes: healthy" in s
    hs.record_failure("outcomes", "OANDA not configured")
    s = hs.status()
    assert "outcomes: UNHEALTHY" in s and "1 consecutive" in s
    assert "brief: healthy" in s
    hs.record_success("outcomes")
    assert "UNHEALTHY" not in hs.status()


# ── per-job isolation (docs/specs/visible_failures_spec.md D4) ────────────────

def test_one_jobs_success_never_recovers_another(state):
    """The daily false pair: a brief ALERT, then 'RECOVERED' from the grader."""
    hs.record_failure("brief", "stale file")
    assert hs.record_failure("brief", "stale file").startswith("ALERT:BRIEF")
    assert hs.record_success("outcomes") == ""     # no RECOVERED for the brief
    d = json.loads(state.read_text())
    assert d["jobs"]["brief"]["consecutive_failures"] == 2   # streak intact

def test_a_job_failing_between_the_others_successes_still_alerts(state):
    """Before: a grader failing nightly between brief successes never
    reached 2 in a row on the shared counter, so it never alerted."""
    hs.record_failure("outcomes", "Traceback")
    hs.record_success("brief"); hs.record_success("brief")
    assert hs.record_failure("outcomes", "Traceback").startswith(
        "ALERT:OUTCOMES UNHEALTHY")

def test_legacy_flat_state_migrates_into_brief(state):
    state.write_text(json.dumps({"consecutive_failures": 3,
                                 "last_failure_reason": "STALE: storylines.md",
                                 "last_alert_date": "2026-09-29"}))
    assert "brief: UNHEALTHY — 3 consecutive" in hs.status()
    assert hs.record_success("brief") == \
        "RECOVERED: brief healthy again after 3 failed runs"

def test_legacy_cli_without_a_job_counts_toward_brief(state, capsys):
    hs.main(["health_state.py", "record-failure", "old-style reason"])
    d = json.loads(state.read_text())
    assert d["jobs"]["brief"]["last_failure_reason"] == "old-style reason"

def test_cli_with_a_job(state, capsys):
    hs.main(["health_state.py", "record-failure", "outcomes", "Traceback"])
    hs.main(["health_state.py", "record-failure", "outcomes", "Traceback"])
    assert capsys.readouterr().out.startswith("ALERT:OUTCOMES UNHEALTHY — Traceback")


def test_f5_an_unknown_job_is_its_own_job_never_the_brief(state):
    hs.main(["health_state.py", "record-failure", "outcome", "Traceback"])   # typo
    hs.main(["health_state.py", "record-failure", "outcome", "Traceback"])
    d = json.loads(state.read_text())
    assert "brief" not in d["jobs"] or d["jobs"]["brief"].get("consecutive_failures", 0) == 0
    assert d["jobs"]["outcome"]["consecutive_failures"] == 2
    assert "outcome: UNHEALTHY" in hs.status()     # the typo is visible, not hidden


def test_f8_a_malformed_job_entry_is_zero_state_not_silence(state, capsys):
    state.write_text('{"jobs": {"brief": null, "outcomes": 7}}')
    hs.main(["health_state.py", "record-failure", "brief", "a"])
    hs.main(["health_state.py", "record-failure", "brief", "a"])
    assert capsys.readouterr().out.startswith("ALERT:BRIEF UNHEALTHY — a")
    assert "outcomes: healthy" in hs.status()


def test_grader_early_exit_is_loud(monkeypatch, capsys):
    """run_outcome_check must never exit quietly when unconfigured (item 2)."""
    import oanda_feed
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: False)
    import run_outcome_check
    run_outcome_check.main()
    out = capsys.readouterr().out
    assert "GRADER EARLY EXIT" in out
    assert "nothing graded this run" in out
