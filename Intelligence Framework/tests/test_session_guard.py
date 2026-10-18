"""
test_session_guard.py
─────────────────────
Circuit-breaker pins, rewritten for the trades.csv two-row ledger at
promotion (2026-09-09, docs/specs/circuit_breaker_promotion_spec.md).
The 8 original behavioral pins from shadow/ are preserved one-for-one on
the new schema; new pins cover the R arithmetic, leg grouping, the
return_pct path, and open-position counting.

Run: pytest tests/test_session_guard.py
"""
import csv
from datetime import datetime, timezone

import pytest

import session_guard as sg
from session_guard import (
    STATUS_ACTIVE, STATUS_HALTED, STATUS_SESSION_CLOSED,
    can_trade, count_leg_grouped_positions, get_session_status,
)

from trade_logger import FIELDS as _FIELDS      # the writer's schema, not a copy


def test_the_breakers_required_columns_are_written_by_trade_logger():
    """session_guard reads trades.csv that trade_logger writes; a column the
    breaker needs but the writer dropped would fail closed on every read."""
    import session_guard as sg
    assert sg._REQUIRED_COLUMNS <= set(_FIELDS)


def _today(hhmmss="10:00:00"):
    return datetime.now(timezone.utc).strftime("%Y-%m-%d") + " " + hhmmss


def _open(pid, inst="GBP_JPY", direction="SHORT", o=210.0, s=211.0,
          ts=None, **over):
    r = dict.fromkeys(_FIELDS, "")
    r.update({"row_type": "OPEN", "position_id": pid,
              "timestamp_utc": ts or _today(), "instrument": inst,
              "direction": direction, "open_price": o, "stop": s})
    r.update(over)
    return r


def _close(pid, inst="GBP_JPY", direction="SHORT", o=210.0, s=211.0,
           c=210.0, ts=None, **over):
    r = _open(pid, inst, direction, o, s, ts, **over)
    r.update({"row_type": "CLOSE", "close_price": c})
    r.update(over)
    return r


def _ledger(tmp_path, rows):
    p = tmp_path / "trades.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return str(p)


# ── the 8 original behavioral pins, on the two-row schema ──────────────────────

def test_absent_journal_is_active(tmp_path):
    s = get_session_status(str(tmp_path / "nope.csv"), 10_000)
    assert s["status"] == STATUS_ACTIVE
    assert s["trades_today"] == 0

def test_corrupt_journal_fails_closed(tmp_path):
    p = tmp_path / "trades.csv"
    p.write_text("date,trade_taken,pnl_r\n2026-09-09,YES,-1.0\n")  # old schema
    s = get_session_status(str(p), 10_000)
    assert s["status"] == STATUS_HALTED
    assert "cannot verify" in s["reason"]
    assert not can_trade(str(p), 10_000)

def test_empty_file_is_active(tmp_path):
    p = tmp_path / "trades.csv"
    p.write_text("")
    assert get_session_status(str(p), 10_000)["status"] == STATUS_ACTIVE

def test_small_loss_stays_active(tmp_path):
    # SHORT 210 → 210.5, stop 211: R = (210 − 210.5)/1.0 = −0.5R
    p = _ledger(tmp_path, [_open("P1"), _close("P1", c=210.5)])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_ACTIVE
    assert s["realized_loss_r"] == 0.5

def test_drawdown_trips_limit_even_when_net_is_small(tmp_path, monkeypatch):
    # +2.5R then −2.0R: net +0.5R but peak-to-trough is 2.0R → HALTED.
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    p = _ledger(tmp_path, [
        _open("P1"), _close("P1", c=207.5),           # SHORT +2.5R
        _open("P2", inst="EUR_USD", direction="LONG", o=1.10, s=1.09),
        _close("P2", inst="EUR_USD", direction="LONG", o=1.10, s=1.09,
               c=1.08),                                # LONG −2.0R
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_HALTED
    assert s["realized_loss_r"] == 2.0
    assert "drawdown limit" in s["reason"].lower()

def test_max_trades_closes_session(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_R", 99.0)
    # two DISJOINT-leg positions → count 2 → SESSION_CLOSED
    p = _ledger(tmp_path, [
        _open("P1", inst="GBP_JPY"),
        _open("P2", inst="EUR_USD", direction="LONG", o=1.10, s=1.09),
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_SESSION_CLOSED
    assert s["trades_today"] == 2

def test_wins_only_never_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    p = _ledger(tmp_path, [
        _open("P1"), _close("P1", c=208.0),            # +2R
        _open("P2"), _close("P2", c=207.0),            # +3R
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_ACTIVE
    assert s["realized_loss_r"] == 0.0

def test_only_todays_rows_count(tmp_path):
    p = _ledger(tmp_path, [
        _open("P0", ts="2026-08-01 05:39:21"),
        _close("P0", ts="2026-08-01 05:39:21", c=213.0),   # old day: −3R ignored
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_ACTIVE
    assert s["trades_today"] == 0
    assert s["realized_loss_r"] == 0.0


# ── new pins: R arithmetic, legs, %, open positions ────────────────────────────

def test_r_from_prices_pinned_both_directions(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    # SHORT o=212.264 s=213.88 c=213.88 → −1R exactly (the PAPER geometry)
    p = _ledger(tmp_path, [
        _open("P1", o=212.264, s=213.88),
        _close("P1", o=212.264, s=213.88, c=213.88),
    ])
    assert get_session_status(p, 10_000)["realized_loss_r"] == 1.0

def test_shared_leg_positions_count_as_one(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_R", 99.0)
    p = _ledger(tmp_path, [
        _open("P1", inst="GBP_JPY"),
        _open("P2", inst="GBP_AUD", direction="SHORT", o=1.90, s=1.91),
    ])
    s = get_session_status(p, 10_000)
    assert s["trades_today"] == 1                      # one pound bet
    assert s["status"] == STATUS_ACTIVE

def test_leg_grouping_component_arithmetic():
    assert count_leg_grouped_positions(["GBP_JPY", "GBP_AUD"]) == 1
    assert count_leg_grouped_positions(["GBP_JPY", "EUR_USD"]) == 2
    assert count_leg_grouped_positions(["GBP_JPY", "AUD_JPY", "GBP_AUD"]) == 1
    assert count_leg_grouped_positions([]) == 0

def test_open_without_close_counts_toward_session(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_R", 99.0)
    p = _ledger(tmp_path, [_open("P1"), _open("P2", inst="EUR_USD")])
    assert get_session_status(p, 10_000)["trades_today"] == 2

def test_return_pct_path_trips_percent_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    monkeypatch.setattr(sg, "MAX_DAILY_LOSS_R", 99.0)  # isolate the % check
    p = _ledger(tmp_path, [
        _open("P1"), _close("P1", c=210.5, return_pct="-2.5"),
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_HALTED
    assert s["realized_loss_pct"] == 2.5

def test_close_with_no_stop_counts_trade_but_no_r(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "MAX_TRADES_PER_SESSION", 99)
    p = _ledger(tmp_path, [
        _open("P1", s=""), _close("P1", s="", c=205.0),  # would be +5R if scored
    ])
    s = get_session_status(p, 10_000)
    assert s["status"] == STATUS_ACTIVE
    assert s["realized_loss_r"] == 0.0

def test_zero_balance_halts(tmp_path):
    p = _ledger(tmp_path, [])
    assert get_session_status(p, 0)["status"] == STATUS_HALTED

def test_reason_lines_are_plain_english(tmp_path):
    # anything a trader reads stays plain (AGENTS.md rule 4): spot-check the
    # three reason paths for internal jargon
    for rows, bal in ([[], 10_000],
                      [[_open("P1"), _open("P2", inst="EUR_USD")], 10_000]):
        s = get_session_status(_ledger(tmp_path, rows), bal)
        for tok in ("ADX", "ATR", "HH-HL", "pivot"):
            assert tok not in s["reason"]
