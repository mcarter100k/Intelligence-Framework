"""
test_health_state.py — pins the Spec-A alerting contract
(docs/specs/heartbeat_spec.md item 1):

  failure #1 silent · #2 alerts · #3 same-day silent · next day repeats ·
  success resets and says RECOVERED exactly once · corrupt state = zero state.

Run: pytest test_health_state.py
"""
import importlib.util
import json
import os
from datetime import datetime, timezone

import pytest

_spec = importlib.util.spec_from_file_location(
    "health_state",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
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
    assert hs.record_failure("OANDA not configured") == ""

def test_second_failure_alerts_with_exact_message(state):
    hs.record_failure("OANDA not configured")
    out = hs.record_failure("OANDA not configured")
    assert out == ("ALERT:FRAMEWORK UNHEALTHY — OANDA not configured — "
                   "2nd consecutive failed run")

def test_third_same_day_failure_does_not_realert(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    hs.record_failure("x"); assert hs.record_failure("x") != ""
    assert hs.record_failure("x") == ""            # daily repeat, not per-run

def test_next_day_failure_realerts_with_running_count(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    hs.record_failure("x"); hs.record_failure("x"); hs.record_failure("x")
    _freeze(monkeypatch, "2026-09-10T10:00:00")
    out = hs.record_failure("x")
    assert out.endswith("4th consecutive failed run")

def test_success_resets_and_reports_recovery_once(state):
    hs.record_failure("x"); hs.record_failure("x")
    assert hs.record_success() == "RECOVERED after 2 failed runs"
    assert hs.record_success() == ""               # exactly once
    assert hs.record_failure("y") == ""            # streak restarted at 1

def test_recovery_after_reset_allows_fresh_alert_same_day(state, monkeypatch):
    _freeze(monkeypatch, "2026-09-09T10:00:00")
    hs.record_failure("x"); hs.record_failure("x")   # alert fired today
    hs.record_success()
    hs.record_failure("y")
    assert hs.record_failure("y") != ""            # new outage may re-alert

def test_reason_text_carried_through(state):
    hs.record_failure("no data from OANDA")
    out = hs.record_failure("no data from OANDA")
    assert "no data from OANDA" in out

def test_corrupt_state_file_is_zero_state(state):
    state.write_text("{not json")
    assert hs.record_failure("x") == ""            # counts as failure #1
    d = json.loads(state.read_text())
    assert d["consecutive_failures"] == 1

def test_status_lines(state):
    assert "healthy" in hs.status()
    hs.record_failure("OANDA not configured")
    s = hs.status()
    assert "UNHEALTHY" in s and "1 consecutive" in s
    hs.record_success()
    assert "healthy" in hs.status()


def test_grader_early_exit_is_loud(monkeypatch, capsys):
    """run_outcome_check must never exit quietly when unconfigured (item 2)."""
    import oanda_feed
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: False)
    import run_outcome_check
    run_outcome_check.main()
    out = capsys.readouterr().out
    assert "GRADER EARLY EXIT" in out
    assert "nothing graded this run" in out
