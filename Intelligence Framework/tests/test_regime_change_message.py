"""
test_regime_change_message.py

Pins docs/specs/regime_change_message_spec.md (issue 4, 2026-09-30): the
session "Regime changed" message names each timeframe that changed. The
defect, seen live in the 02:30 PDT brief: an H4-only change rendered as
"Regime changed (no clear direction → no clear direction)" because the
message always printed the daily pair.

Run: pytest tests/test_regime_change_message.py
"""
import csv
import re
from datetime import datetime, timezone

import pytest

import decision_brief as db
import session_memory as sm

# The two real GBP_AUD rows behind the 2026-09-30 02:30 PDT brief (only the
# 4-hour chart changed). Time is frozen so a run crossing UTC midnight cannot
# split the writer's and the reader's "today" (review F8).
_PRIOR = {"instrument": "GBP_AUD", "adx_d1": "19.4", "adx_h4": "42.9",
          "atr_ratio": "1.0", "regime_d1": "VOLATILE", "regime_h4": "TRENDING_UP",
          "structure_d1": "TRANSITIONAL", "filter_allowed": "False",
          "logic_version": ""}
_NOW = dict(_PRIOR, adx_h4="45.3", regime_h4="VOLATILE")

# Rendered text must carry no raw regime token — single words included
# (review F5: the underscore-only regex missed VOLATILE itself).
_RAW = re.compile(r"\b(?:VOLATILE|RANGING|TRENDING|UNKNOWN|UNAVAILABLE|D1|H4)\b"
                  r"|\b[A-Za-z]+_[A-Za-z0-9]+\b")


class _Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def _delta(tmp_path, monkeypatch, prior, now):
    monkeypatch.setattr(sm, "datetime", _Frozen)
    monkeypatch.setattr(sm, "LOG_FILE", str(tmp_path / "s.csv"))
    with open(sm.LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sm.FIELDNAMES)
        w.writeheader()
        w.writerow(dict(prior, timestamp="2026-09-30T01:15:59Z"))
        w.writerow(dict(now, timestamp="2026-09-30T09:30:07Z"))
    return sm.get_session_delta("GBP_AUD")


def _brief_session_line(d):
    brief = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9, atr_pips=90.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="l", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=19.4,
        adx_h4=45.3, weekly_context="RANGING", error=None, session_delta=d)
    out = brief.format()
    return re.sub(r"\s+", " ", out[out.index("SESSION") - 2:out.index("WATCH FOR")])


def test_h4_only_change_names_the_4_hour_chart(tmp_path, monkeypatch):
    d = _delta(tmp_path, monkeypatch, _PRIOR, _NOW)
    assert d["regime_changed"] is True
    assert "Regime changed — H4: TRENDING_UP → VOLATILE." in d["summary"]
    assert "D1:" not in d["summary"]


def test_d1_only_change_names_the_daily_chart(tmp_path, monkeypatch):
    d = _delta(tmp_path, monkeypatch, _PRIOR, dict(_PRIOR, regime_d1="TRENDING_DOWN"))
    assert "Regime changed — D1: VOLATILE → TRENDING_DOWN." in d["summary"]
    assert "H4:" not in d["summary"]


def test_both_changed_names_both_daily_first(tmp_path, monkeypatch):
    d = _delta(tmp_path, monkeypatch, _PRIOR, dict(_NOW, regime_d1="TRENDING_DOWN"))
    assert ("Regime changed — D1: VOLATILE → TRENDING_DOWN; "
            "H4: TRENDING_UP → VOLATILE.") in d["summary"]


def test_control_no_regime_change_has_no_regime_message(tmp_path, monkeypatch):
    d = _delta(tmp_path, monkeypatch, _PRIOR, dict(_PRIOR, adx_h4="43.0"))
    assert d["regime_changed"] is False
    assert "Regime changed" not in d["summary"]


def test_rendered_brief_line_is_plain_and_keeps_the_marker(tmp_path, monkeypatch):
    """The real 02:30 case, end to end through DecisionBrief.format()."""
    line = _brief_session_line(_delta(tmp_path, monkeypatch, _PRIOR, _NOW))
    assert line.startswith("⚡ SESSION")                        # marker kept
    assert "Regime changed — 4-hour chart: trending up → no clear direction" in line
    assert "no clear direction → no clear direction" not in line
    assert _RAW.search(line) is None, line


def test_setup_check_path_renders_the_new_format_plainly(tmp_path, monkeypatch):
    """The summary's second consumer (review F4)."""
    import setup_check
    d = _delta(tmp_path, monkeypatch, _PRIOR, dict(_NOW, regime_d1="TRENDING_DOWN"))
    txt = setup_check._delta_sentence(d)
    assert "the market's character changed — daily chart: no clear direction → " \
           "trending down; 4-hour chart: trending up → no clear direction" in txt
    assert _RAW.search(txt) is None, txt


@pytest.mark.parametrize("gap", ["UNAVAILABLE", "UNKNOWN", ""])
def test_an_h4_data_gap_is_not_told_as_a_regime(tmp_path, monkeypatch, gap):
    """Review F2/F3: an outage or a blank read reads 'no data this run' — no
    '(…))' nesting and no ' → ' with an empty side."""
    line = _brief_session_line(_delta(tmp_path, monkeypatch, _PRIOR,
                                      dict(_PRIOR, regime_h4=gap)))
    assert "4-hour chart: trending up → no data this run" in line
    assert "))" not in line and ":  →" not in line
    assert _RAW.search(line) is None, line


def test_a_filter_flip_also_names_the_regime_change(tmp_path, monkeypatch):
    """Review F6: the flip message surfaces first but no longer hides the
    regime change the alert reports."""
    d = _delta(tmp_path, monkeypatch, dict(_PRIOR, filter_allowed="True"), _NOW)
    assert "CONDITIONS DETERIORATED" in d["summary"]
    assert "Regime changed — H4: TRENDING_UP → VOLATILE." in d["summary"]


def test_a_filter_flip_without_a_regime_change_is_unchanged(tmp_path, monkeypatch):
    d = _delta(tmp_path, monkeypatch, dict(_PRIOR, filter_allowed="True"),
               dict(_PRIOR, adx_h4="43.0"))
    assert d["summary"].endswith("CONDITIONS DETERIORATED — framework moved to stand aside.")
