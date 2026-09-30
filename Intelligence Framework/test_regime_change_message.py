"""
test_regime_change_message.py

Pins docs/specs/regime_change_message_spec.md (issue 4, 2026-09-30): the
session "Regime changed" message names each timeframe that changed. The
defect, seen live in the 02:30 PDT brief: an H4-only change rendered as
"Regime changed (no clear direction → no clear direction)" because the
message always printed the daily pair.

Run: pytest test_regime_change_message.py
"""
import csv
import re
from datetime import datetime, timezone

import pytest

import decision_brief as db
import session_memory as sm

# The two real GBP_AUD rows behind the 2026-09-30 02:30 PDT brief (only the
# 4-hour chart changed), re-dated to today so _get_today_rows sees them.
_PRIOR = {"instrument": "GBP_AUD", "adx_d1": "19.4", "adx_h4": "42.9",
          "atr_ratio": "1.0", "regime_d1": "VOLATILE", "regime_h4": "TRENDING_UP",
          "structure_d1": "TRANSITIONAL", "filter_allowed": "False",
          "logic_version": ""}
_NOW = dict(_PRIOR, adx_h4="45.3", regime_h4="VOLATILE")


def _summary(tmp_path, monkeypatch, prior, now):
    monkeypatch.setattr(sm, "LOG_FILE", str(tmp_path / "s.csv"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(sm.LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sm.FIELDNAMES)
        w.writeheader()
        w.writerow(dict(prior, timestamp=f"{today}T01:15:59Z"))
        w.writerow(dict(now, timestamp=f"{today}T09:30:07Z"))
    return sm.get_session_delta("GBP_AUD")


def test_h4_only_change_names_the_4_hour_chart(tmp_path, monkeypatch):
    d = _summary(tmp_path, monkeypatch, _PRIOR, _NOW)
    assert d["regime_changed"] is True
    assert "Regime changed (4-hour chart: TRENDING_UP → VOLATILE)" in d["summary"]
    assert "daily chart" not in d["summary"]


def test_d1_only_change_names_the_daily_chart(tmp_path, monkeypatch):
    d = _summary(tmp_path, monkeypatch, _PRIOR,
                 dict(_PRIOR, regime_d1="TRENDING_DOWN"))
    assert "Regime changed (daily chart: VOLATILE → TRENDING_DOWN)" in d["summary"]
    assert "4-hour" not in d["summary"]


def test_both_changed_names_both_daily_first(tmp_path, monkeypatch):
    d = _summary(tmp_path, monkeypatch, _PRIOR,
                 dict(_NOW, regime_d1="TRENDING_DOWN"))
    assert ("Regime changed (daily chart: VOLATILE → TRENDING_DOWN; "
            "4-hour chart: TRENDING_UP → VOLATILE)") in d["summary"]


def test_control_no_regime_change_has_no_regime_message(tmp_path, monkeypatch):
    d = _summary(tmp_path, monkeypatch, _PRIOR, dict(_PRIOR, adx_h4="43.0"))
    assert d["regime_changed"] is False
    assert "Regime changed" not in d["summary"]


def test_rendered_brief_line_is_plain_and_keeps_the_marker(tmp_path, monkeypatch):
    """The real 02:30 case, end to end through DecisionBrief.format()."""
    d = _summary(tmp_path, monkeypatch, _PRIOR, _NOW)
    brief = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9, atr_pips=90.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="l", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=19.4,
        adx_h4=45.3, weekly_context="RANGING", error=None, session_delta=d)
    out = brief.format()
    session = out[out.index("⚡ SESSION"):out.index("WATCH FOR")]
    flat = re.sub(r"\s+", " ", session)
    assert "4-hour chart: trending up → no clear direction" in flat
    assert "no clear direction → no clear direction" not in flat
    assert re.search(r"\b[A-Za-z]+_[A-Za-z0-9]+\b", flat) is None    # no raw tokens
