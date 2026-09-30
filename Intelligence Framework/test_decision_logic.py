"""
test_decision_logic.py

Locks docs/specs/decision_logic_spec.md (Phase 5). Each defect is pinned at
the edge of its property, next to a control that must keep passing:

  D1  exhaustion (RANGING/EXHAUSTION) stands aside       — control: same cell, no subtype, trades
  D2  ADX >= 32 needs agreeing structure                  — (test_regime_detection_p1 T10-T15, T10c-T15c, T45)
  D3  the opposite-trend conflict block fires on emitted types
  D4  the filter is the single authority: allowed <=> the official decision trades
  D5  news gate: coverage through the feed's Saturday; 30-min post-release buffer
  D6  missing levels are NOT READY                        — (test_level_source_repair)
  D7  grade C is never a trade                            — boundary: conviction 45 trades, 40 does not
  logic_version on every ledger row; no session alert across a rule change

Run: pytest test_decision_logic.py
"""
import csv
import itertools
import unittest.mock as mock
from datetime import datetime, timezone

import pandas as pd
import pytest

import no_trade_filter
import regime_detection as rd
import regime_classifier_logger as rcl
import session_memory as sm
import trade_outcome_logger as tol
from news_gate import check_news_gate, covered_through, when_phrase
from no_trade_filter import apply_filter
from official_decision import LOGIC_VERSION, decide, get_official_decision
from regime_detection import _detect_conflict, get_composite_regime

_TRADES = ("LONG", "SHORT")


def _chain(r):
    """The live order: apply_filter, its outputs onto the dict, official."""
    fr = apply_filter(r)
    r = dict(r, filter_allowed=fr.allowed, filter_mode=fr.execution_mode,
             filter_size_mult=fr.size_mult, filter_reason=fr.reason,
             override_fired=fr.override_fired)
    return fr, get_official_decision(r)


def _regime(d1, h4, **over):
    comp = get_composite_regime(d1, h4)
    c, ct = _detect_conflict(d1, h4)
    r = {"regime_d1": d1, "regime_h4": h4, "adx": 28.0, "adx_h4": 28.0,
         "atr_vs_avg": 1.0, "atr_compression": False,
         "timeframe_conflict": c, "conflict_type": ct,
         "structure": "UPTREND", "weekly_context": "ESTABLISHED_UPTREND",
         "lt_trend": "UPTREND", "st_trend": "UPTREND",
         "execution_mode": comp["execution_mode"], "size_mult": comp["size_mult"],
         "confidence": comp["confidence"], "resolution_note": comp["note"],
         "news_gate": {}, "instrument": "GBP_AUD", "adx_exhaustion": False,
         "range_position": 0.5, "regime_d1_subtype": "", "regime_h4_subtype": ""}
    r.update(over)
    return r


# ── D4: the invariant, over the whole grid ─────────────────────────────────────

_REGIMES = ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE")


def _grid():
    for (d1, h4, structure, lt, wctx, adx_h4, atr, inst, exh, h4sub, rpos) in \
            itertools.product(
                _REGIMES, _REGIMES, ("UPTREND", "DOWNTREND", "TRANSITIONAL"),
                ("UPTREND", "DOWNTREND", "RANGING"),
                ("ESTABLISHED_UPTREND", "ESTABLISHED_DOWNTREND",
                 "COUNTER_TREND_BOUNCE", "RANGING"),
                (20.0, 28.0), (1.0, 1.1), ("GBP_AUD", "GBP_JPY"),
                (False, True), ("", "EXHAUSTION"), (0.1, 0.5)):
        yield _regime(d1, h4, structure=structure, lt_trend=lt,
                      weekly_context=wctx, adx_h4=adx_h4, atr_vs_avg=atr,
                      instrument=inst, adx_exhaustion=exh,
                      regime_h4_subtype=h4sub, range_position=rpos)


def test_filter_allows_iff_official_trades_over_the_grid():
    allowed = blocked = 0
    for r in _grid():
        fr, od = _chain(r)
        trades = od["direction"] in _TRADES
        assert fr.allowed is trades, (r, fr, od)
        if trades:
            allowed += 1
            assert od["grade"] != "C" and od["size_mult"] > 0, (r, od)
        else:
            blocked += 1
            assert od["conviction"] == 0 and od["size_mult"] == 0.0
            # the ledgers and alerts read the same answer the brief shows
            assert od["reason"] == fr.reason, (r, fr, od)
    # non-vacuous: both sides of the invariant are exercised heavily
    assert allowed > 1000 and blocked > 1000, (allowed, blocked)


@pytest.mark.parametrize("d1,h4", [("RANGING", "RANGING"),
                                   ("RANGING", "TRENDING_UP"),
                                   ("RANGING", "TRENDING_DOWN")])
def test_former_allow_then_veto_cells_are_blocked_by_the_filter(d1, h4):
    """The three cells measured on main as filter-allowed then official-vetoed."""
    r = _regime(d1, h4, structure="TRANSITIONAL", adx=15.0,
                lt_trend="RANGING", weekly_context="RANGING")
    fr, od = _chain(r)
    assert fr.allowed is False
    assert od["direction"] == "NO TRADE"
    assert fr.reason == od["reason"]


def test_ranging_under_trending_h4_reason_is_honest():
    """Not the range-fade wording: the mode wanted a trend direction."""
    fr, _ = _chain(_regime("RANGING", "TRENDING_UP", structure="TRANSITIONAL",
                           lt_trend="RANGING", weekly_context="RANGING"))
    assert "Range mid-zone" not in fr.reason
    assert "no trend direction" in fr.reason


# ── D7: grade C ────────────────────────────────────────────────────────────────

def test_the_2026_09_25_row_is_no_trade():
    """The real GBP/JPY row main showed as SHORT, conviction 30, grade C, 75%."""
    r = _regime("TRENDING_DOWN", "RANGING", adx=34.9, adx_h4=14.4,
                structure="DOWNTREND", lt_trend="DOWNTREND",
                weekly_context="ESTABLISHED_DOWNTREND", atr_vs_avg=1.02,
                instrument="GBP_JPY", adx_exhaustion=True)
    fr, od = _chain(r)
    assert fr.allowed is False
    assert od["direction"] == "NO TRADE" and od["size_mult"] == 0.0
    assert "grades C" in fr.reason and "never trade a C" in fr.reason


@pytest.mark.parametrize("adx_h4,expect_trade", [(25.0, True), (24.9, False)])
def test_grade_boundary_45_trades_40_does_not(adx_h4, expect_trade):
    """LOW confidence (40) + the H4 bonus (+5 at adx_h4 >= 25) = 45 = B, the
    lowest traded grade; without the bonus it is 40 = C. The only input that
    differs is adx_h4, straddling its threshold."""
    r = {"regime_d1": "TRENDING_UP", "confidence": "LOW",
         "structure": "TRANSITIONAL", "adx_h4": adx_h4,
         "instrument": "GBP_AUD", "atr_vs_avg": 1.0, "resolution_note": "n"}
    d = decide(r, exec_mode="CONTINUATION", size_mult=0.5)
    assert (d["direction"] in _TRADES) is expect_trade
    assert d["grade"] == ("B" if expect_trade else "C")
    assert d["conviction"] == (45 if expect_trade else 0)


# ── D1: exhaustion ─────────────────────────────────────────────────────────────

def _jpy_exhaustion(sub_key="regime_h4_subtype", sub="EXHAUSTION"):
    return _regime("TRENDING_UP", "RANGING", adx=28.0, adx_h4=42.0,
                   structure="UPTREND", lt_trend="UPTREND",
                   weekly_context="ESTABLISHED_UPTREND", atr_vs_avg=1.3,
                   instrument="GBP_JPY", **{sub_key: sub})


def test_h4_exhaustion_stands_aside():
    fr, od = _chain(_jpy_exhaustion())
    assert fr.allowed is False and od["direction"] == "NO TRADE"
    assert fr.reason.startswith("The market is in an exhaustion move")


def test_d1_exhaustion_stands_aside():
    fr, _ = _chain(_jpy_exhaustion("regime_d1_subtype"))
    assert fr.allowed is False
    assert fr.reason.startswith("The market is in an exhaustion move")


def test_exhaustion_control_same_cell_without_subtype_trades():
    """Positive control: the subtype is the ONLY difference, and main traded
    this cell (grade A LONG). If this stops trading, the D1 test proves
    nothing."""
    fr, od = _chain(_jpy_exhaustion(sub=""))
    assert fr.allowed is True and od["direction"] == "LONG"


# ── D3: opposite-trend conflict ────────────────────────────────────────────────

@pytest.mark.parametrize("d1,h4", [("TRENDING_UP", "TRENDING_DOWN"),
                                   ("TRENDING_DOWN", "TRENDING_UP")])
def test_conflict_block_fires_on_emitted_types(d1, h4):
    conflict, ctype = _detect_conflict(d1, h4)
    assert conflict and ctype in ("D1_BULLISH_H4_BEARISH", "D1_BEARISH_H4_BULLISH")
    # a mode that would otherwise trade, so only the named block can stop it
    r = _regime(d1, h4, execution_mode="CONTINUATION", size_mult=1.0,
                confidence="HIGH")
    fr = apply_filter(r)
    assert fr.allowed is False
    assert fr.reason.startswith("Opposite trend conflict")


# ── D5: news gate ──────────────────────────────────────────────────────────────

_HDR = "time,currency,event,actual,forecast,previous,impact\n"


def _cal(tmp_path, *rows):
    p = tmp_path / "calendar.csv"
    p.write_text(_HDR + "".join(f"{t},{c},{e},,,,High\n" for t, c, e in rows))
    return str(p)


def test_coverage_runs_to_saturday_2359_eastern():
    # newest event Wed 2026-09-30 (EDT, UTC-4): covered through Sat 10-03
    # 23:59:59 EDT = Sun 10-04 03:59:59 UTC.
    assert covered_through(datetime(2026, 9, 30, 12, 0)) == \
        datetime(2026, 10, 4, 3, 59, 59)


@pytest.mark.parametrize("now,active", [
    (datetime(2026, 10, 4, 3, 59, tzinfo=timezone.utc), True),    # last covered minute
    (datetime(2026, 10, 4, 4, 1, tzinfo=timezone.utc), False),    # the next week
    (datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc), False),    # Monday, < 7 days old
])
def test_calendar_that_does_not_cover_now_is_inactive(tmp_path, now, active):
    path = _cal(tmp_path, ("2026-09-30 12:00", "GBP", "Mid-week event"))
    g = check_news_gate("GBP_AUD", now=now, calendar_path=path)
    assert g["active"] is active
    assert g["gating"] is False
    assert (g["note"] == "") is active       # never a silent all-clear


@pytest.mark.parametrize("mins_after,gating", [(-120, True), (0, True), (30, True), (31, False)])
def test_gate_window_is_2h_before_to_30min_after(tmp_path, mins_after, gating):
    path = _cal(tmp_path, ("2026-09-30 12:00", "GBP", "BoE rate decision"))
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc) + \
        pd.Timedelta(minutes=mins_after).to_pytimedelta()
    g = check_news_gate("GBP_AUD", now=now, calendar_path=path)
    assert g["gating"] is gating
    if gating:
        assert g["minutes_until"] == -mins_after


def test_post_release_reason_reads_released_ago():
    fr = apply_filter(_regime("TRENDING_UP", "TRENDING_UP", news_gate={
        "active": True, "gating": True, "event": "BoE rate decision",
        "currency": "GBP", "minutes_until": -5, "event_time_utc": "", "note": ""}))
    assert fr.allowed is False
    assert "released 5 minutes ago" in fr.reason
    assert "-5" not in fr.reason and "ahead" not in fr.reason


def test_when_phrase():
    assert when_phrase(90) == "90 minutes"
    assert when_phrase(-12) == "released 12 minutes ago"
    assert when_phrase(None) == "under 2 hours"


# ── the live wiring: get_regime gives the filter what decide() reads ───────────

def _bars(n, freq, step, start):
    closes = [1.85 + i * step for i in range(n)]
    return pd.DataFrame(
        {"High": [c + 0.0025 for c in closes], "Low": [c - 0.0025 for c in closes],
         "Close": closes, "Open": closes, "Volume": [1000] * n},
        index=pd.date_range(start, periods=n, freq=freq, tz="UTC"))


def test_get_regime_passes_the_decision_inputs_to_the_filter():
    seen = []
    real = no_trade_filter.apply_filter

    def spy(r):
        seen.append(dict(r))
        return real(r)

    d1 = _bars(220, "B", 0.0015, "2025-01-01")
    h4 = _bars(200, "4h", 0.0004, "2025-09-01")
    wk = _bars(110, "W", 0.005, "2023-01-01")
    with mock.patch.object(no_trade_filter, "apply_filter", spy), \
         mock.patch.object(rd, "_oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: d1.tail(count).copy()), \
         mock.patch("regime_detection._oanda_h4_bars", lambda *a, count=200, **k: h4.tail(count).copy()), \
         mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: wk.tail(count).copy()):
        regime = rd.get_regime("GBP_AUD")

    assert len(seen) == 1
    for k in ("instrument", "adx", "confidence", "adx_exhaustion",
              "range_position", "regime_d1_subtype", "regime_h4_subtype"):
        assert k in seen[0], k
        assert seen[0][k] == regime[k], k
    # and the regime's own answer obeys the invariant
    od = get_official_decision(regime)
    assert regime["filter_allowed"] is (od["direction"] in _TRADES)
    assert regime["logic_version"] == LOGIC_VERSION


# ── logic_version on every ledger ──────────────────────────────────────────────

def test_official_decision_carries_logic_version():
    assert get_official_decision({})["logic_version"] == LOGIC_VERSION
    _, od = _chain(_regime("TRENDING_UP", "TRENDING_UP"))
    assert od["direction"] == "LONG" and od["logic_version"] == LOGIC_VERSION


def test_trade_and_regime_rows_carry_logic_version(tmp_path, monkeypatch):
    monkeypatch.setattr(tol, "_LOG_FILE", str(tmp_path / "t.csv"))
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "r.csv"))
    regime = dict(_regime("TRENDING_UP", "TRENDING_UP"), regime="TRENDING_UP",
                  current_price=1.88, last_close=1.88, logic_version=LOGIC_VERSION)
    tol.log_signal(regime, {"direction": "LONG", "logic_version": LOGIC_VERSION},
                   "GBP_AUD")
    rcl.log_regime(regime, "GBP_AUD")
    for p in (tol._LOG_FILE, rcl.LOG_FILE):
        rows = list(csv.DictReader(open(p)))
        assert rows[-1]["logic_version"] == LOGIC_VERSION, p


def _session_row(ts, allowed, lv):
    return {"timestamp": ts, "instrument": "GBP_AUD", "adx_d1": 25.0,
            "adx_h4": 20.0, "atr_ratio": 1.0, "regime_d1": "VOLATILE",
            "regime_h4": "RANGING", "structure_d1": "TRANSITIONAL",
            "filter_allowed": allowed, "logic_version": lv}


@pytest.mark.parametrize("prior_lv,expect_flag", [(LOGIC_VERSION, True), ("", False)])
def test_session_flip_only_alerts_under_the_same_rules(tmp_path, monkeypatch,
                                                       prior_lv, expect_flag):
    """Control (same rules) flags the flip; across the rule change it does not."""
    monkeypatch.setattr(sm, "LOG_FILE", str(tmp_path / "s.csv"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sm._append_row(_session_row(f"{today}T01:00:00Z", True, prior_lv))
    sm._append_row(_session_row(f"{today}T02:00:00Z", False, LOGIC_VERSION))
    delta = sm.get_session_delta("GBP_AUD")
    assert delta["filter_changed"] is expect_flag


def test_session_append_migrates_an_old_header_first(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "LOG_FILE", str(tmp_path / "s.csv"))
    old = sm.FIELDNAMES[:-1]
    with open(sm.LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old)
        w.writeheader()
        w.writerow({k: ("KEEP" if k == "structure_d1" else "1") for k in old})
    sm._append_row(_session_row("2026-09-30T01:00:00Z", True, LOGIC_VERSION))
    with open(sm.LOG_FILE) as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == sm.FIELDNAMES
        rows = list(reader)
    assert rows[0]["structure_d1"] == "KEEP" and rows[0]["logic_version"] == ""
    assert rows[1]["logic_version"] == LOGIC_VERSION
    assert rows[1]["instrument"] == "GBP_AUD"          # not shifted a column
