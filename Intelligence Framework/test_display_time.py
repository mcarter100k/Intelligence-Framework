"""
test_display_time.py
────────────────────
Pins docs/specs/display_timezone_spec.md: PST/PDT by date, env override,
identical UTC gating across display zones, byte-identical decisions, and
no bare "UTC" in rendered prose.

Run: pytest test_display_time.py
"""
from datetime import datetime, timedelta, timezone

import pytest

import display_time as dtm
from display_time import to_display


@pytest.fixture(autouse=True)
def _default_zone(monkeypatch):
    monkeypatch.delenv("DISPLAY_TZ", raising=False)


# ── the helper: abbreviation by date, never hardcoded ──────────────────────────

def test_winter_date_renders_pst():
    assert to_display(datetime(2026, 1, 15, 17, 7, tzinfo=timezone.utc)) == \
        "Thu 15 Jan 2026 9:07 AM PST"

def test_summer_date_renders_pdt():
    assert to_display(datetime(2026, 7, 15, 4, 7, tzinfo=timezone.utc)) == \
        "Tue 14 Jul 2026 9:07 PM PDT"

def test_styles_pinned():
    dt = datetime(2026, 9, 11, 6, 0, tzinfo=timezone.utc)   # UK GDP instant
    assert to_display(dt, style="time") == "11:00 PM PDT"
    assert to_display(datetime(2026, 9, 13, 21, 0), style="day_time") == \
        "Sun 2:00 PM PDT"                                    # naive = UTC

def test_env_override(monkeypatch):
    monkeypatch.setenv("DISPLAY_TZ", "America/New_York")
    assert to_display(datetime(2026, 1, 15, 17, 7,
                               tzinfo=timezone.utc)).endswith("12:07 PM EST")

def test_iso_string_and_garbage():
    assert to_display("2026-09-11T06:00:00Z", style="time") == "11:00 PM PDT"
    assert to_display("not a time") == ""
    assert to_display(None) == ""


# ── news gate: identical UTC instant across display zones ──────────────────────

def _calendar(tmp_path):
    p = tmp_path / "calendar.csv"
    p.write_text("time,currency,event,actual,forecast,previous,impact\n"
                 "2026-09-11 06:00,GBP,GDP m/m,,0.0%,0.3%,High\n")
    return str(p)

def test_gate_fires_identically_in_any_display_zone(tmp_path, monkeypatch):
    from news_gate import check_news_gate
    path = _calendar(tmp_path)
    now = datetime(2026, 9, 11, 4, 30, tzinfo=timezone.utc)   # 90 min out
    results = []
    for tz in ("America/Los_Angeles", "America/New_York", "UTC"):
        monkeypatch.setenv("DISPLAY_TZ", tz)
        r = check_news_gate("GBP_AUD", now=now, calendar_path=path)
        results.append((r["gating"], r["minutes_until"], r["event_time_utc"]))
    assert results[0] == results[1] == results[2] == \
        (True, 90, "2026-09-11T06:00:00Z")

def test_gate_quiet_outside_window_regardless_of_zone(tmp_path, monkeypatch):
    from news_gate import check_news_gate
    path = _calendar(tmp_path)
    now = datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc)    # 4 h out
    for tz in ("America/Los_Angeles", "UTC"):
        monkeypatch.setenv("DISPLAY_TZ", tz)
        assert check_news_gate("GBP_AUD", now=now,
                               calendar_path=path)["gating"] is False


# ── decisions byte-identical ───────────────────────────────────────────────────

def test_official_decision_identical_across_zones(monkeypatch):
    from official_decision import get_official_decision
    regime = {"execution_mode": "CONTINUATION",
              "composite_regime": "TRENDING_UP", "confidence": "HIGH",
              "size_mult": 1.0, "stand_down": False, "filter_allowed": True,
              "filter_reason": "", "regime_d1": "TRENDING_UP",
              "regime_h4": "TRENDING_UP", "structure": "UPTREND",
              "instrument": "GBP_AUD"}
    outs = []
    for tz in ("America/Los_Angeles", "America/New_York", "UTC"):
        monkeypatch.setenv("DISPLAY_TZ", tz)
        outs.append(get_official_decision(dict(regime)))
    assert outs[0] == outs[1] == outs[2]


# ── rendered prose carries no bare UTC ─────────────────────────────────────────

def test_market_closed_note_in_display_zone():
    from regime_detection import _market_status
    st = _market_status(_now=datetime(2026, 9, 12, 23, 0,
                                      tzinfo=timezone.utc))   # Saturday
    assert st["open"] is False
    assert st["note"] == ("Market closed — analysis based on last close. "
                          "Next open Sun 2:00 PM PDT.")
    assert st["next_open_utc"] == "2026-09-13T21:00:00Z"      # machine field

def test_filter_reason_carries_local_time(monkeypatch):
    from no_trade_filter import apply_filter
    regime = {"regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP",
              "adx_h4": 28.0, "atr_vs_avg": 1.0, "atr_compression": False,
              "timeframe_conflict": False, "conflict_type": "",
              "structure": "UPTREND",
              "weekly_context": "ESTABLISHED_UPTREND",
              "lt_trend": "UPTREND", "st_trend": "UPTREND",
              "execution_mode": "CONTINUATION", "size_mult": 1.0,
              "confidence": "HIGH",
              "news_gate": {"active": True, "gating": True,
                            "event": "UK GDP", "currency": "GBP",
                            "minutes_until": 90,
                            "event_time_utc": "2026-09-11T06:00:00Z",
                            "note": ""}}
    fr = apply_filter(regime)
    assert fr.allowed is False
    assert "UK GDP in 90 minutes (at 11:00 PM PDT)." in fr.reason

def test_setup_clock_carries_local_time():
    from test_setup_check import _stack, _regime
    s = _stack(regime=_regime(news_gate={
        "active": True, "gating": True, "event": "UK GDP",
        "minutes_until": 100, "event_time_utc": "2026-09-11T06:00:00Z"}))
    assert s["clock"] == ("UK GDP in 1h 40m (at 11:00 PM PDT) — "
                          "stand aside until after.")

def test_no_bare_utc_in_rendered_prose():
    import re
    from regime_detection import _market_status
    texts = [
        to_display(datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)),
        _market_status(_now=datetime(2026, 9, 12, 23, 0,
                                     tzinfo=timezone.utc))["note"],
    ]
    for t in texts:
        assert not re.search(r"\bUTC\b", t), t
