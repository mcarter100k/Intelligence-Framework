"""
test_session_guard.py

Locks Phase 2.2 correctness fixes for the circuit breaker:
  * peak-to-trough DRAWDOWN accounting (not net) trips the daily limit
  * a CORRUPT journal fails CLOSED (HALTED), an ABSENT one is ACTIVE
  * the daily-loss and max-trades limits both halt

Run: pytest test_session_guard.py
"""
import csv
from datetime import date

import pytest

import session_guard as sg
from session_guard import (
    get_session_status, can_trade,
    STATUS_ACTIVE, STATUS_HALTED, STATUS_SESSION_CLOSED,
)

_TODAY = date.today().isoformat()


def _write_journal(path, rows):
    """rows: list of (trade_taken, pnl_r) for today."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "trade_taken", "pnl_r"])
        w.writeheader()
        for taken, pnl in rows:
            w.writerow({"date": _TODAY, "trade_taken": taken, "pnl_r": pnl})


def test_absent_journal_is_active(tmp_path):
    missing = tmp_path / "nope.csv"
    assert can_trade(missing, account_balance=10_000) is True
    assert get_session_status(missing, 10_000)["status"] == STATUS_ACTIVE


def test_corrupt_journal_fails_closed(tmp_path):
    # File exists but its header lacks the columns we rely on (schema drift /
    # truncation) — we cannot verify limits, so we must halt.
    bad = tmp_path / "corrupt.csv"
    bad.write_text("foo,bar,baz\n1,2,3\n")
    status = get_session_status(bad, 10_000)
    assert status["status"] == STATUS_HALTED
    assert can_trade(bad, 10_000) is False


def test_empty_file_is_active(tmp_path):
    # A zero-byte file is 'no trades yet', not corruption.
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert get_session_status(empty, 10_000)["status"] == STATUS_ACTIVE


def test_small_loss_stays_active(tmp_path):
    j = tmp_path / "j.csv"
    _write_journal(j, [("YES", "-0.5")])
    assert get_session_status(j, 10_000)["status"] == STATUS_ACTIVE


def test_drawdown_trips_limit_even_when_net_is_small(tmp_path, monkeypatch):
    # Isolate the loss path from the trade-count path.
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_PCT", 2.0)
    j = tmp_path / "j.csv"
    # +2, +1, -4 → net = -1 (would NOT halt on net) but peak-to-trough = 4
    _write_journal(j, [("YES", "2.0"), ("YES", "1.0"), ("YES", "-4.0")])
    status = get_session_status(j, 10_000)
    assert status["status"] == STATUS_HALTED
    assert status["realized_loss_pct"] == pytest.approx(4.0)


def test_max_trades_closes_session(tmp_path, monkeypatch):
    # Isolate the count path from the loss path.
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_PCT", 99.0)
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 2)
    j = tmp_path / "j.csv"
    _write_journal(j, [("YES", "0.3"), ("YES", "0.2")])
    status = get_session_status(j, 10_000)
    assert status["status"] == STATUS_SESSION_CLOSED
    assert status["trades_today"] == 2


def test_wins_only_never_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    j = tmp_path / "j.csv"
    _write_journal(j, [("YES", "1.0"), ("YES", "1.5")])
    status = get_session_status(j, 10_000)
    assert status["status"] == STATUS_ACTIVE
    assert status["realized_loss_pct"] == pytest.approx(0.0)


def test_only_todays_taken_trades_count(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    j = tmp_path / "j.csv"
    with open(j, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "trade_taken", "pnl_r"])
        w.writeheader()
        w.writerow({"date": "2000-01-01", "trade_taken": "YES", "pnl_r": "-5.0"})  # old
        w.writerow({"date": _TODAY, "trade_taken": "NO", "pnl_r": ""})             # not taken
        w.writerow({"date": _TODAY, "trade_taken": "YES", "pnl_r": "-0.4"})        # counts
    status = get_session_status(j, 10_000)
    assert status["trades_today"] == 1
    assert status["realized_loss_pct"] == pytest.approx(0.4)
