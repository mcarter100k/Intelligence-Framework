"""
test_news_gate.py

Pins the pre-news stand-down gate (docs/specs/news_gate_spec.md): fires at
90 min, silent at 3 h, gates only on the pair's OWN currencies (USD out of
scope), stale calendar → note not gate, missing file → safe inactive, filter
reason pinned, brief honesty line pinned, shadow signals NOT gated.

Run: pytest tests/test_news_gate.py
"""
from datetime import datetime, timedelta, timezone

import pytest

import news_gate
from news_gate import check_news_gate
from no_trade_filter import apply_filter

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def _calendar(tmp_path, rows):
    p = tmp_path / "calendar.csv"
    lines = ["time,currency,event,actual,forecast,previous,impact"]
    for dt, ccy, event, impact in rows:
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M')},{ccy},{event},,1.0%,0.9%,{impact}")
    p.write_text("\n".join(lines) + "\n")
    return str(p)


# ── Gate behavior (mocked calendar, fixed clock) ───────────────────────────────

def test_fires_at_90_minutes(tmp_path):
    path = _calendar(tmp_path, [(NOW + timedelta(minutes=90), "GBP", "UK CPI", "High")])
    r = check_news_gate("GBP_AUD", now=NOW, calendar_path=path)
    assert r["active"] is True
    assert r["gating"] is True
    assert r["event"] == "UK CPI"
    assert r["minutes_until"] == 90


def test_silent_at_3_hours(tmp_path):
    path = _calendar(tmp_path, [(NOW + timedelta(hours=3), "GBP", "UK CPI", "High")])
    r = check_news_gate("GBP_AUD", now=NOW, calendar_path=path)
    assert r["active"] is True
    assert r["gating"] is False


def test_own_currencies_only(tmp_path):
    # AUD event gates GBP_AUD but not GBP_JPY; JPY event the reverse.
    path = _calendar(tmp_path, [(NOW + timedelta(minutes=60), "AUD", "RBA Rate Statement", "High")])
    assert check_news_gate("GBP_AUD", now=NOW, calendar_path=path)["gating"] is True
    assert check_news_gate("GBP_JPY", now=NOW, calendar_path=path)["gating"] is False


def test_usd_event_gates_neither_pair(tmp_path):
    # USD deliberately out of scope — known v1 boundary.
    path = _calendar(tmp_path, [(NOW + timedelta(minutes=45), "USD", "FOMC Statement", "High")])
    assert check_news_gate("GBP_AUD", now=NOW, calendar_path=path)["gating"] is False
    assert check_news_gate("GBP_JPY", now=NOW, calendar_path=path)["gating"] is False


def test_low_impact_does_not_gate(tmp_path):
    path = _calendar(tmp_path, [(NOW + timedelta(minutes=30), "GBP", "M4 Money Supply", "Low")])
    assert check_news_gate("GBP_AUD", now=NOW, calendar_path=path)["gating"] is False


def test_stale_calendar_notes_but_never_gates(tmp_path):
    # A HIGH own-currency event "ahead" in a calendar whose newest row is 8 days
    # old: impossible data — gate INACTIVE with the pinned note, no gating.
    path = _calendar(tmp_path, [(NOW - timedelta(days=8), "GBP", "Old CPI", "High")])
    r = check_news_gate("GBP_AUD", now=NOW, calendar_path=path)
    assert r["active"] is False
    assert r["gating"] is False
    assert r["note"] == "news calendar stale — event risk unchecked"


def test_missing_file_is_safe_inactive(tmp_path):
    r = check_news_gate("GBP_AUD", now=NOW, calendar_path=str(tmp_path / "nope.csv"))
    assert r["active"] is False
    assert r["gating"] is False
    assert "unchecked" in r["note"]


# ── Filter wiring (pinned reason; floors untouched elsewhere in the suite) ─────

_CLEAN_LONG = {
    "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "adx_h4": 28.0,
    "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
    "conflict_type": "", "structure": "UPTREND",
    "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
    "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
    "size_mult": 1.0, "confidence": "HIGH",
}


def test_filter_stands_down_on_gate_with_pinned_reason():
    regime = dict(_CLEAN_LONG)
    regime["news_gate"] = {"active": True, "gating": True, "event": "UK CPI",
                           "currency": "GBP", "minutes_until": 90, "note": ""}
    fr = apply_filter(regime)
    assert fr.allowed is False
    assert fr.reason == ("Major economic event ahead — UK CPI in 90 minutes. "
                         "Markets reprice violently around releases; standing "
                         "aside until after.")


def test_filter_ignores_inactive_gate():
    regime = dict(_CLEAN_LONG)
    regime["news_gate"] = {"active": False, "gating": False, "event": "",
                           "minutes_until": None,
                           "note": "news calendar stale — event risk unchecked"}
    assert apply_filter(regime).allowed is True    # stale = note, never gate


# ── Brief honesty line (pinned) ────────────────────────────────────────────────

def test_brief_renders_stale_calendar_line():
    import decision_brief as db
    brief = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="test", price=1.9, atr_pips=90.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="l", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=20.0,
        adx_h4=20.0, weekly_context="RANGING", error=None,
        news_note="news calendar stale — event risk unchecked")
    assert "news calendar stale — event risk unchecked" in brief.format()


# ── Shadow signals are NOT gated (spec item 4) ────────────────────────────────

def test_shadow_signals_fire_through_news_window(monkeypatch):
    import shadow_signals as ss
    # pre_release: the gate's flag for "an event 0-120 min ahead" (added with
    # the post-release buffer, decision_logic_spec review V6); this mock is an
    # event 30 min ahead, so the real gate sets it.
    monkeypatch.setattr(news_gate, "check_news_gate",
                        lambda *a, **k: {"active": True, "gating": True,
                                         "event": "UK CPI", "minutes_until": 30,
                                         "pre_release": True})
    ctx = {
        "O": [217.0] * 40, "H": [217.5] * 40, "L": [216.5] * 40, "C": [217.0] * 40,
        "T": [datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)] * 40,
        "atr": [0.5] * 40, "pip": 0.01,
        "adx": 20.0, "adx_slope": 0.0, "struct": "UPTREND",
        "sd": {"latest_sl": 216.0, "latest_sh": 218.0},
    }
    signals = ss.check_shadow_signals("GBP_JPY", ctx)
    assert len(signals) == 1                      # NOT suppressed by the gate
    assert signals[0]["candidate_id"] == "EARLY_MOMENTUM_v2"   # v1 retired 2026-09-09
    assert "news_window=true" in signals[0]["extra"]   # context stamp only
