"""
test_trade_outcome_loop.py

Locks Phase 5.1: the trade-signal feedback loop actually closes, and grades each
signal at the price EXACTLY `window` bars after it was logged — not the latest
bar (which may be far past the window if the checker ran late).

Run: pytest test_trade_outcome_loop.py
"""
import csv

import pandas as pd
import pytest

import trade_outcome_logger as tol


def _seed_log(path, timestamp, entry=1.9000, direction="LONG"):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tol._FIELDS)
        w.writeheader()
        row = {k: "" for k in tol._FIELDS}
        row.update({
            "signal_id":       f"{timestamp}_GBP_AUD",
            "timestamp":       timestamp,
            "instrument":      "GBP_AUD",
            "direction":       direction,
            "grade":           "A",
            "conviction":      75,
            "price_at_signal": entry,
            "outcome_filled":  False,
        })
        w.writerow(row)


def test_loop_grades_at_window_bar_not_latest(tmp_path, monkeypatch):
    log = tmp_path / "trade_signal_log.csv"
    monkeypatch.setattr(tol, "_LOG_FILE", str(log))

    # 30 daily bars; the signal was logged 1 day before bar 0, so all 30 bars
    # are "after" it → bars_elapsed = 30, window = 20 → outcome bar = index 19.
    index = pd.date_range(start="2026-01-01", periods=30, freq="B", tz="UTC")
    log_time = (index[0] - pd.Timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_log(log, log_time, entry=1.9000, direction="LONG")

    closes = [1.9000] * 30
    closes[19] = 1.9100   # window bar (20 bars after log): LONG is CORRECT here
    closes[29] = 1.8800   # latest bar: LONG would look WRONG here

    filled = tol.check_pending_trade_outcomes("GBP_AUD", closes, recent_index=index)
    assert filled == 1

    with open(log, newline="") as f:
        row = next(csv.DictReader(f))
    assert row["outcome_filled"] == "True"
    # Graded at the window bar (1.9100), NOT the latest bar (1.8800).
    assert float(row["price_20_bars_later"]) == pytest.approx(1.9100)
    assert row["signal_correct"] == "True"
    assert float(row["move_pips"]) == pytest.approx(100.0)


def test_loop_leaves_unelapsed_signals_pending(tmp_path, monkeypatch):
    log = tmp_path / "trade_signal_log.csv"
    monkeypatch.setattr(tol, "_LOG_FILE", str(log))

    index = pd.date_range(start="2026-01-01", periods=30, freq="B", tz="UTC")
    # Logged only 5 bars ago → window (20) not elapsed → must stay pending.
    log_time = index[25].strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_log(log, log_time)

    filled = tol.check_pending_trade_outcomes("GBP_AUD", [1.9] * 30, recent_index=index)
    assert filled == 0
    with open(log, newline="") as f:
        row = next(csv.DictReader(f))
    assert row["outcome_filled"] == "False"
