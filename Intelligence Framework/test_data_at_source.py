"""
test_data_at_source.py — the inputs are right before anything is computed
from them (docs/specs/data_at_source_spec.md). Each defect was reproduced
on main before the fix (validation_log, Phase 4).
"""
import csv
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd
import pytest

import regime_detection as rd
from no_trade_filter import apply_filter

UTC = timezone.utc


def _trend(n, step, start, slope):
    end = pd.Timestamp.now(tz="UTC").floor("h") - step
    idx = pd.DatetimeIndex([end - (n - 1 - i) * step for i in range(n)])
    closes = [start + slope * i for i in range(n)]
    return pd.DataFrame({"High": [c + abs(slope) * 2 for c in closes],
                         "Low": [c - abs(slope) * 2 for c in closes],
                         "Close": closes}, index=idx)


DOWN_D1 = _trend(100, timedelta(days=1), 1.95, -0.001)
DOWN_H4 = _trend(120, timedelta(hours=4), 1.90, -0.0005)
UP_W = _trend(110, timedelta(weeks=1), 1.60, +0.004)


def _regime(weekly=UP_W, live=1.8512):
    with mock.patch("regime_detection._oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", return_value=DOWN_D1), \
         mock.patch("regime_detection._oanda_h4_bars", return_value=DOWN_H4), \
         mock.patch("regime_detection._oanda_weekly_bars", return_value=weekly), \
         mock.patch("regime_detection._oanda_live_price", return_value=live):
        return rd.get_regime("GBP_AUD")


# ── P1: the live price, labelled ──────────────────────────────────────────────

def test_p1_current_price_is_the_live_mid_not_the_last_close():
    r = _regime(live=1.8512)
    assert r["current_price"] == 1.8512
    assert r["price_basis"] == "live"
    assert r["current_price"] != round(float(DOWN_D1["Close"].iloc[-1]), 4)


def test_p1_no_live_price_falls_back_to_the_close_labelled_and_reported(capsys):
    r = _regime(live=None)
    assert r["current_price"] == round(float(DOWN_D1["Close"].iloc[-1]), 4)
    assert r["price_basis"] == "prior_close"
    assert "live price unavailable for GBP/AUD" in capsys.readouterr().err


def test_p1_the_brief_says_when_the_price_is_not_live():
    import decision_brief as db
    b = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.85, atr_pips=80.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=20.0,
        adx_h4=20.0, weekly_context="RANGING", error=None,
        price_basis="prior_close")
    assert "Price is the previous daily close — the live price could not be fetched" in b.format()
    b.price_basis = "live"
    assert "previous daily close" not in b.format()


def test_p1_both_ledgers_record_the_price_basis(tmp_path, monkeypatch):
    import regime_classifier_logger as rcl
    import trade_outcome_logger as tol
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    monkeypatch.setattr(tol, "_LOG_FILE", str(tmp_path / "trade.csv"))
    regime = dict(_regime(live=1.8512), market_open=True)
    rcl.log_regime(regime, "GBP_AUD")
    tol.log_signal(regime, {"direction": "SHORT", "grade": "B", "conviction": 50,
                            "size_mult": 0.5}, "GBP_AUD")
    for path, price_col in ((tmp_path / "regime.csv", "price_at_log"),
                            (tmp_path / "trade.csv", "price_at_signal")):
        row = list(csv.DictReader(open(path)))[-1]
        assert row["price_basis"] == "live" and float(row[price_col]) == 1.8512


def test_p1_trade_ledger_migration_is_additive(tmp_path, monkeypatch):
    import trade_outcome_logger as tol
    p = tmp_path / "trade.csv"
    old = [f for f in tol._FIELDS if f != "price_basis"]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old)
        w.writeheader()
        w.writerow({k: ("KEEP" if k == "price_at_signal" else "x") for k in old})
    tol._migrate_header(str(p))
    rows = list(csv.DictReader(open(p)))
    assert list(rows[0].keys()) == tol._FIELDS
    assert rows[0]["price_at_signal"] == "KEEP" and rows[0]["price_basis"] == ""


# ── P2: market hours from New York time ───────────────────────────────────────

@pytest.mark.parametrize("when,is_open", [
    (datetime(2026, 9, 27, 21, 30, tzinfo=UTC), True),    # summer Sun, NY 17:30
    (datetime(2026, 9, 27, 20, 59, tzinfo=UTC), False),   # summer Sun, NY 16:59
    (datetime(2026, 10, 2, 20, 59, tzinfo=UTC), True),    # summer Fri, NY 16:59
    (datetime(2026, 10, 2, 21, 0, tzinfo=UTC), False),    # summer Fri, NY 17:00
    (datetime(2026, 11, 1, 21, 30, tzinfo=UTC), False),   # winter Sun, NY 16:30
    (datetime(2026, 11, 1, 22, 0, tzinfo=UTC), True),     # winter Sun, NY 17:00
    (datetime(2026, 11, 6, 21, 30, tzinfo=UTC), True),    # winter Fri, NY 16:30
    (datetime(2026, 11, 6, 22, 0, tzinfo=UTC), False),    # winter Fri, NY 17:00
    (datetime(2026, 12, 25, 12, 0, tzinfo=UTC), False),   # Christmas
    (datetime(2026, 12, 24, 21, 59, tzinfo=UTC), True),   # Christmas Eve, NY 16:59
    (datetime(2027, 1, 1, 12, 0, tzinfo=UTC), False),     # New Year's Day
    (datetime(2026, 9, 30, 8, 0, tzinfo=UTC), True),      # ordinary Wednesday
])
def test_p2_market_open_follows_new_york_17_00(when, is_open):
    assert rd._market_status(_now=when)["open"] is is_open


@pytest.mark.parametrize("when,next_open", [
    (datetime(2026, 10, 3, 12, 0, tzinfo=UTC), "2026-10-04T21:00:00Z"),  # summer weekend
    (datetime(2026, 11, 7, 12, 0, tzinfo=UTC), "2026-11-08T22:00:00Z"),  # winter weekend
    (datetime(2026, 12, 25, 12, 0, tzinfo=UTC), "2026-12-27T22:00:00Z"), # Christmas Friday
    (datetime(2027, 1, 1, 12, 0, tzinfo=UTC), "2027-01-03T22:00:00Z"),   # New Year Friday
])
def test_p2_next_open_is_correct_across_dst_and_holidays(when, next_open):
    assert rd._market_status(_now=when)["next_open_utc"] == next_open


# ── P3: a weekly outage stands down ───────────────────────────────────────────

@pytest.mark.parametrize("weekly", [None, UP_W.iloc[0:0], UP_W.iloc[:5]],
                         ids=["fetch failed", "empty", "too short"])
def test_p3_weekly_outage_is_unavailable_and_stands_down(weekly):
    r = _regime(weekly=weekly)
    assert r["weekly_context"] == r["lt_trend"] == "UNAVAILABLE"
    assert r["weekly_available"] is False
    f = apply_filter(r)
    assert f.allowed is False
    assert f.reason.startswith("Weekly trend data unavailable")


def test_p3_control_with_weekly_data_the_gate_runs():
    r = _regime(weekly=UP_W)
    assert r["weekly_available"] is True and r["lt_trend"] == "UPTREND"
    f = apply_filter(r)
    assert f.allowed is False and f.reason.startswith("Short blocked: dominant 20-week trend")


def test_p3_unavailable_reads_in_plain_english():
    import decision_brief as db
    assert "UNAVAILABLE" not in db._plain("Weekly: UNAVAILABLE")
    assert "could not be fetched" in db._plain("Weekly: UNAVAILABLE")
