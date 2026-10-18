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

# The P1/V6 tests exercise the open-market live-price path. get_regime reads
# the real clock through _market_status(), so on a weekend they took the
# closed-market branch and failed (4 tests, every Fri 17:00 NY to Sun). The
# clock is injected through _market_status's _now, as test_v8 already does.
OPEN_NOW = datetime(2026, 10, 14, 15, 0, tzinfo=UTC)          # Wednesday, open


def _open_market():
    return mock.patch("regime_detection._market_status",
                      return_value=rd._market_status(_now=OPEN_NOW))


def _regime(weekly=UP_W, live=1.8512):
    with _open_market(), \
         mock.patch("regime_detection._oanda_ok", return_value=True), \
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


def test_p1_each_ledger_records_the_right_price_and_basis(tmp_path, monkeypatch):
    """The trade entry is the LIVE price. The regime row records the closed D1
    bar it was classified from (basis d1_close): the right baseline for D1-bar
    outcomes, and stable across runs so repeat logs of one state still merge
    (review V2/V3)."""
    import regime_classifier_logger as rcl
    import trade_outcome_logger as tol
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    monkeypatch.setattr(tol, "_LOG_FILE", str(tmp_path / "trade.csv"))
    regime = dict(_regime(live=1.8512), market_open=True)
    rcl.log_regime(regime, "GBP_AUD")
    tol.log_signal(regime, {"direction": "SHORT", "grade": "B", "conviction": 50,
                            "size_mult": 0.5}, "GBP_AUD")
    trade = list(csv.DictReader(open(tmp_path / "trade.csv")))[-1]
    assert trade["price_basis"] == "live" and float(trade["price_at_signal"]) == 1.8512
    reg = list(csv.DictReader(open(tmp_path / "regime.csv")))[-1]
    assert reg["price_basis"] == "d1_close"
    assert float(reg["price_at_log"]) == round(float(DOWN_D1["Close"].iloc[-1]), 5)


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


# ── /code-review findings (spec addendum) ─────────────────────────────────────

@pytest.mark.parametrize("n_bars,available", [(20, False), (22, False), (23, True)])
def test_v1_weekly_history_must_cover_the_20_week_read(n_bars, available):
    """20-22 bars used to pass as 'available' while the 20-week trend came
    back RANGING, so the gate was skipped silently again."""
    r = _regime(weekly=UP_W.iloc[-n_bars:])
    assert r["weekly_available"] is available
    assert apply_filter(r).allowed is False       # stands down OR is blocked by the gate


def test_v2_v3_classification_does_not_move_with_the_live_price(tmp_path, monkeypatch):
    import regime_classifier_logger as rcl
    a, b = _regime(live=1.80), _regime(live=1.99)
    for k in ("atr_pct", "range_position", "price_vs_ma50", "price_vs_ma200",
              "last_close", "execution_mode"):
        assert a.get(k) == b.get(k), k
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    rcl.log_regime(dict(a, market_open=True), "GBP_AUD")
    rcl.log_regime(dict(b, market_open=True), "GBP_AUD")
    rows = list(csv.DictReader(open(tmp_path / "regime.csv")))
    assert rows[0]["price_at_log"] == rows[1]["price_at_log"]
    assert len(rcl._independent_states(rows)) == 1    # one state, counted once


def test_v5_a_missing_basis_is_never_shown_as_live():
    import decision_brief as db
    b = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.85, atr_pips=80.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=20.0,
        adx_h4=20.0, weekly_context="RANGING", error=None)
    assert b.price_basis == "unknown"
    assert "Price source unknown" in b.format()


def test_v6_a_failed_live_price_says_why(monkeypatch, capsys):
    import oanda_feed
    import requests

    class _R:
        status_code = 401
        def raise_for_status(self):
            e = requests.HTTPError("401"); e.response = self; raise e
    monkeypatch.setenv("OANDA_API_KEY", "k")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "a")
    monkeypatch.setattr(oanda_feed.requests, "get", lambda *a, **k: _R())
    assert oanda_feed.get_live_price("GBPAUD") is None
    assert oanda_feed.last_error().startswith("live price: credentials rejected (HTTP 401)")
    with _open_market(), \
         mock.patch("regime_detection._oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", return_value=DOWN_D1), \
         mock.patch("regime_detection._oanda_h4_bars", return_value=DOWN_H4), \
         mock.patch("regime_detection._oanda_weekly_bars", return_value=UP_W):
        rd.get_regime("GBP_AUD")
    assert "credentials rejected (HTTP 401)" in capsys.readouterr().err


@pytest.mark.parametrize("now,expected", [
    (datetime(2026, 12, 28, 10, 0, tzinfo=UTC), datetime(2026, 12, 24, 22, 0, tzinfo=UTC)),
    (datetime(2027, 1, 4, 10, 0, tzinfo=UTC), datetime(2026, 12, 31, 22, 0, tzinfo=UTC)),
    (datetime(2026, 10, 5, 10, 0, tzinfo=UTC), datetime(2026, 10, 2, 22, 0, tzinfo=UTC)),
])
def test_v7_the_stale_feed_check_uses_the_same_trading_calendar(now, expected):
    import decision_brief as db
    assert db._last_expected_d1_close(now, 22) == expected


def test_v8_a_closed_market_is_labelled_and_makes_no_pricing_request():
    sat = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    live = mock.Mock(return_value=1.87)
    with mock.patch("regime_detection._market_status",
                    return_value=rd._market_status(_now=sat)), \
         mock.patch("regime_detection._oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", return_value=DOWN_D1), \
         mock.patch("regime_detection._oanda_h4_bars", return_value=DOWN_H4), \
         mock.patch("regime_detection._oanda_weekly_bars", return_value=UP_W), \
         mock.patch("regime_detection._oanda_live_price", live):
        r = rd.get_regime("GBP_AUD")
    assert r["price_basis"] == "market_closed" and live.call_count == 0


def test_v9_the_error_path_uses_the_unavailable_sentinel_too():
    e = rd._error_result("x")
    assert e["weekly_context"] == e["lt_trend"] == e["st_trend"] == "UNAVAILABLE"
    assert e["weekly_available"] is False
