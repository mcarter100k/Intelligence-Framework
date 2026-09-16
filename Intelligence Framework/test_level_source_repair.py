"""
test_level_source_repair.py — per-defect pins for
docs/specs/level_source_repair_spec.md (team ruling 2026-09-16).

One test class per defect. These are Gate-1 controlled-input tests: they
pin the defects with fixed bars and never touch the network. Gate 2
(REALITY, both pairs against live OANDA) is recorded in validation_log.md
and is what actually clears the merge.
"""
import os
import sys

import pandas as pd
import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)

import entry_confirmation
import intraday_context
import levels_context
import oanda_feed


def _bars(rows, tz="UTC"):
    """rows = [(iso_ts, open, high, low, close)] -> OHLC frame."""
    idx = pd.to_datetime([r[0] for r in rows], utc=(tz == "UTC"))
    return pd.DataFrame(
        {"Open":  [r[1] for r in rows],
         "High":  [r[2] for r in rows],
         "Low":   [r[3] for r in rows],
         "Close": [r[4] for r in rows],
         "Volume": [1] * len(rows)},
        index=idx)


# ── DEFECT 3 — weekly semantics (ruling R5) ───────────────────────────────────

class TestDefect3WeeklySemantics:
    """prev_week_* is the last CLOSED week; current_week_* is this week to
    date from completed daily bars. The old weekly_* keys are gone."""

    WEEKLY = _bars([("2026-09-04 21:00", 1.87751, 1.88838, 1.87323, 1.88646)])
    # cur_open = 2026-09-04 21:00 + 7d = 2026-09-11 21:00
    DAILY = _bars([
        ("2026-09-10 21:00", 1.88722, 1.88838, 1.88183, 1.88646),  # prev week
        ("2026-09-13 21:00", 1.88823, 1.89512, 1.88617, 1.89078),  # this week
        ("2026-09-14 21:00", 1.89218, 1.89456, 1.88938, 1.88976),  # this week
    ])

    @pytest.fixture(autouse=True)
    def _stub(self, monkeypatch):
        monkeypatch.setattr(levels_context, "get_weekly_bars",
                            lambda *a, **k: self.WEEKLY)
        monkeypatch.setattr(levels_context, "get_daily_bars",
                            lambda *a, **k: self.DAILY)
        monkeypatch.setattr(levels_context, "get_hourly_bars",
                            lambda *a, **k: None)
        monkeypatch.setattr(intraday_context, "get_intraday_context",
                            lambda pair="GBPAUD": {})

    def test_prev_week_is_the_last_closed_week(self):
        lv = levels_context.get_key_levels("GBPAUD")
        assert lv["prev_week_high"] == 1.88838
        assert lv["prev_week_low"] == 1.87323

    def test_current_week_is_this_week_to_date(self):
        lv = levels_context.get_key_levels("GBPAUD")
        # max/min across the two bars at or after the weekly open only —
        # the 2026-09-10 bar belongs to the previous week and must not leak
        assert lv["current_week_high"] == 1.89512
        assert lv["current_week_low"] == 1.88617

    def test_old_weekly_keys_are_gone(self):
        lv = levels_context.get_key_levels("GBPAUD")
        assert "weekly_high" not in lv
        assert "weekly_low" not in lv

    def test_empty_week_yields_none_not_a_wrong_level(self, monkeypatch):
        """Between the weekly open and the first completed daily bar there
        is no week-to-date range. None is the honest answer; session_* and
        prev_week_* still carry."""
        monkeypatch.setattr(
            levels_context, "get_daily_bars",
            lambda *a, **k: _bars([("2026-09-10 21:00", 1.887, 1.888,
                                    1.881, 1.886)]))
        lv = levels_context.get_key_levels("GBPAUD")
        assert lv["current_week_high"] is None
        assert lv["current_week_low"] is None
        assert lv["prev_week_high"] == 1.88838


# ── DEFECT 4 — Asian range was never pair-keyed ───────────────────────────────

class TestDefect4AsianRangeIsPairKeyed:

    def test_pair_is_threaded_into_intraday_context(self, monkeypatch):
        seen = {}

        def _fake(pair="GBPAUD"):
            seen["pair"] = pair
            return {"asian_high": 209.479, "asian_low": 208.901}

        monkeypatch.setattr(intraday_context, "get_intraday_context", _fake)
        monkeypatch.setattr(levels_context, "get_weekly_bars",
                            lambda *a, **k: None)
        monkeypatch.setattr(levels_context, "get_daily_bars",
                            lambda *a, **k: None)
        monkeypatch.setattr(levels_context, "get_hourly_bars",
                            lambda *a, **k: None)

        lv = levels_context.get_key_levels("GBPJPY")
        assert seen["pair"] == "GBPJPY", (
            "get_intraday_context must receive the requested pair — it "
            "silently returned GBPAUD for every pair before 2026-09-16")
        assert lv["asian_high"] == 209.479

    def test_intraday_context_signature_accepts_a_pair(self):
        """The root cause was a pair-specific function whose signature said
        otherwise. Defaulted for the existing callers."""
        import inspect
        sig = inspect.signature(intraday_context.get_intraday_context)
        assert "pair" in sig.parameters
        assert sig.parameters["pair"].default == "GBPAUD"

    def test_no_mixed_scale_in_a_jpy_level_set(self, monkeypatch):
        """The published symptom: six JPY levels beside two GBP/AUD ones."""
        monkeypatch.setattr(
            intraday_context, "get_intraday_context",
            lambda pair="GBPAUD": {"asian_high": 209.479,
                                   "asian_low": 208.901})
        monkeypatch.setattr(
            levels_context, "get_weekly_bars",
            lambda *a, **k: _bars([("2026-09-04 21:00", 208.0, 211.224,
                                    207.1, 208.5)]))
        monkeypatch.setattr(
            levels_context, "get_daily_bars",
            lambda *a, **k: _bars([("2026-09-14 21:00", 208.3, 209.231,
                                    208.252, 208.9)]))
        monkeypatch.setattr(levels_context, "get_hourly_bars",
                            lambda *a, **k: None)

        vals = levels_context.levels_as_list(
            levels_context.get_key_levels("GBPJPY"))
        assert vals, "expected a non-empty level set"
        assert all(v > 100 for v in vals), f"mixed-scale level set: {vals}"


# ── DEFECT 2 — GBP_JPY could never reach m15_trigger ──────────────────────────

class TestDefect2JpyEntryPathIsAlive:
    """The regression that matters: with the orphaned, single-pair file in
    place, m15_trigger could never be True on GBP_JPY. It must now be
    reachable when the pattern and the level actually agree."""

    # Bearish engulfing on the last two M15 candles, at a JPY-scale price.
    M15 = _bars([
        ("2026-09-16 07:00", 208.80, 208.92, 208.78, 208.90),  # bullish body
        ("2026-09-16 07:15", 208.95, 208.97, 208.70, 208.75),  # engulfs it
    ])
    H1 = None   # H1 unconfirmed — isolates the M15 trigger under test

    @pytest.fixture(autouse=True)
    def _stub_feed(self, monkeypatch):
        monkeypatch.setattr(oanda_feed, "get_m15_bars",
                            lambda *a, **k: self.M15)
        monkeypatch.setattr(oanda_feed, "get_hourly_bars",
                            lambda *a, **k: self.H1)

    def test_level_lookup_is_keyed_to_the_requested_pair(self, monkeypatch):
        seen = {}

        def _fake(pair):
            seen["pair"] = pair
            return {"session_high": 208.80}

        monkeypatch.setattr(levels_context, "get_key_levels", _fake)
        entry_confirmation.get_entry_brief("GBP_JPY", "SHORT")
        assert seen["pair"] == "GBPJPY"

    def test_jpy_trigger_fires_when_pattern_meets_level(self, monkeypatch):
        """JPY-scale level within the 25-pip (0.25) tolerance of the M15
        close — the case that was unreachable for 98 days."""
        monkeypatch.setattr(levels_context, "get_key_levels",
                            lambda pair: {"session_low": 208.74})
        brief = entry_confirmation.get_entry_brief("GBP_JPY", "SHORT")
        assert brief.m15_trigger is True
        assert "key level" in brief.trigger_basis

    def test_jpy_trigger_blocked_by_an_aud_scale_level_set(self, monkeypatch):
        """The defect itself, pinned: AUD levels against a JPY price are
        ~207 away, so near_key_level stays False while _level_available
        stays True — the gating branch, never the degraded one."""
        monkeypatch.setattr(levels_context, "get_key_levels",
                            lambda pair: {"session_low": 1.88924,
                                          "session_high": 1.89232})
        brief = entry_confirmation.get_entry_brief("GBP_JPY", "SHORT")
        assert brief.m15_trigger is False
        assert "not near a key level" in brief.trigger_basis

    def test_degraded_pass_when_no_levels_at_all(self, monkeypatch):
        """Absent levels degrade to a pass — the branch Step 0 restored."""
        monkeypatch.setattr(levels_context, "get_key_levels",
                            lambda pair: {})
        brief = entry_confirmation.get_entry_brief("GBP_JPY", "SHORT")
        assert brief.m15_trigger is True
        assert "unavailable" in brief.trigger_basis


# ── DEFECT 1 — the orphaned read is gone ──────────────────────────────────────

def test_last_run_json_is_never_read_again(tmp_path, monkeypatch):
    """Planting the artifact back at the repo root must change nothing."""
    planted = os.path.join(_ROOT, "last_run.json")
    assert not os.path.exists(planted), (
        "last_run.json is back on disk — Step 0 renamed it aside and "
        "nothing should recreate it")
