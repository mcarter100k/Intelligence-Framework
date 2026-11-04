"""
test_range_volatile_wording.py — the REASON for range + volatile 4-hour
stand-asides (docs/specs/range_volatile_wording_v3_spec.md, amended by v4).
The old sentence, "Range breaking down — 4-hour chart volatile inside daily
chart range", read as bearish while GBP/AUD rallied ~370 pips (2026-11-01 → 03).

  W1  only the REASON text changes: the renderer never mutates its inputs
  W2  every new sentence passes the banned-token floor
  W3  no false direction; the only direction words are _unconfirmed_fact's
  W4  no notification trigger text (the real-wrapper run is in
      test_wrapper_behavior.py)
  W5  exactly the cells where main said "Range breaking down" changed; every
      other cell of the 1,382,400-cell grid is identical (golden from main)
  W6  an EXHAUSTION timeframe is never called sideways or unsettled
  W7  the internal notes never reach this REASON
  +   the two 4-hour states marked unreachable are pinned so, through the
      real get_regime (v4 §3)
"""
import copy
import importlib.util
import json
import os
import random
import re
from unittest import mock

import pandas as pd
import pytest

import decision_brief as db
import regime_detection as rd
from _paths import ROOT
from test_brief_display import _assert_clean

_spec = importlib.util.spec_from_file_location(
    "reason_grid", os.path.join(ROOT, "tests", "golden", "reason_grid.py"))
grid = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grid)

_ENDINGS = ("Standing aside until it confirms.", "Standing aside until a direction emerges.",
            "Standing aside until the 4-hour picture settles.",
            "Standing aside until the 4-hour picture changes.")
_OPENINGS = ("The 4-hour chart", "On the 4-hour chart")


def _is_new_sentence(reason: str) -> bool:
    return reason.startswith(_OPENINGS) and reason.endswith(_ENDINGS)


def _rv(**kw):
    """A RANGING D1 + VOLATILE H4 regime on the conflict path."""
    r = dict(grid.FIXED, regime_d1="RANGING", regime_h4="VOLATILE", regime_d1_subtype="",
             regime_h4_subtype="", adx=14.8, timeframe_conflict=True,
             conflict_type="RANGING_D1_VOLATILE_H4", news_gate={}, filter_block="",
             atr_vs_avg=1.0, h4_change_pips_10=None, stand_down_reason="",
             atr_spike_multiplier=1.2, atr_compression=False)
    r.update(kw)
    return r


def _reason(r, decision="STAND DOWN"):
    return db._render_reason(r, {"reason": ""}, decision, False)


# Every reachable state, on both paths (conflict: with strength; STAND DOWN: without)
_STATES = [dict(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=190),
           dict(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=-190),
           dict(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=4),
           dict(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=None),
           dict(regime_h4_subtype="TRANSITION_ZONE"),
           dict(regime_h4_subtype="")]
_PATHS = [dict(), dict(timeframe_conflict=False, conflict_type="")]


def _all_rendered():
    return [(s, p, _reason(_rv(**s, **p))) for s in _STATES for p in _PATHS]


# ── the approved sentences, exactly (spec v3 §3 + v4 §1) ─────────────────────

def test_the_rally_case_says_what_the_chart_did():
    assert _reason(_rv(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=190)) == (
        "The 4-hour chart has been rising — up 190 pips over the last 40 hours — but its "
        "swing pattern hasn't confirmed a trend yet, inside a sideways daily chart (daily "
        "trend strength 14.8/100). Standing aside until it confirms.")


@pytest.mark.parametrize("state,expected", [
    (dict(regime_h4_subtype="UNCONFIRMED_TREND", h4_change_pips_10=4),
     "The 4-hour chart is moving strongly but its swing pattern hasn't confirmed a "
     "direction yet, inside a sideways daily chart. Standing aside until it confirms."),
    (dict(regime_h4_subtype="TRANSITION_ZONE"),
     "The 4-hour chart has no clear direction yet, inside a sideways daily chart. "
     "Standing aside until a direction emerges."),
    (dict(regime_h4_subtype=""),
     "The 4-hour chart's volatility is outside its normal range, inside a sideways "
     "daily chart. Standing aside until the 4-hour picture settles."),
], ids=["unconfirmed_small_move", "transition_zone", "volatility"])
def test_stand_down_path_sentences(state, expected):
    assert _reason(_rv(timeframe_conflict=False, conflict_type="", **state)) == expected


# ── W1: words only ──────────────────────────────────────────────────────────

def test_w1_rendering_never_mutates_its_inputs():
    for s in _STATES:
        for p in _PATHS:
            r = _rv(**s, **p)
            before = copy.deepcopy(r)
            _reason(r)
            assert r == before


# ── W2: plain English ───────────────────────────────────────────────────────

def test_w2_every_new_sentence_is_plain_english():
    for _s, _p, why in _all_rendered():
        assert _is_new_sentence(why), why
        _assert_clean(why)


# ── W3: no false direction ──────────────────────────────────────────────────

_DIRECTION = re.compile(r"\b(down|up|rising|falling|higher|lower|breaking|breakout|"
                        r"breakdown|collapse|rally|drop|climb|surge|slide|sell|buy|"
                        r"bull\w*|bear\w*)\b", re.I)


def test_w3_only_the_closed_bar_fact_carries_a_direction():
    for s, _p, why in _all_rendered():
        found = {w.lower() for w in _DIRECTION.findall(why)}
        chg = s.get("h4_change_pips_10")
        if s["regime_h4_subtype"] == "UNCONFIRMED_TREND" and chg is not None and abs(chg) >= 10:
            assert found == ({"rising", "up"} if chg > 0 else {"falling", "down"}), (why, found)
        else:
            assert not found, (why, found)


# ── W4: no trigger text ─────────────────────────────────────────────────────

def test_w4_no_notification_trigger_text():
    for _s, _p, why in _all_rendered():
        for trig in ("DECISION", "SHADOW SIGNALS", "Framework error", "EXIT IF",
                     "WATCH FOR", "STAND ASIDE", "##ALERT##"):
            assert trig not in why, (trig, why)


# ── W6: EXHAUSTION is never sideways ────────────────────────────────────────

def test_w6_an_exhausted_daily_chart_is_not_called_sideways():
    why = _reason(_rv(regime_d1_subtype="EXHAUSTION", regime_h4_subtype="TRANSITION_ZONE"))
    assert "sideways" not in why and "overextended in a violent one-way move" in why


def test_w6_an_exhausted_4_hour_chart_is_not_called_unsettled():
    why = _reason(_rv(regime_h4_subtype="EXHAUSTION"))
    assert why.startswith("The 4-hour chart is overextended in a violent one-way move")
    assert "unsettled" not in why


# ── W7: the internal notes never reach this REASON ──────────────────────────

def test_w7_internal_notes_never_reach_the_reason():
    note = rd.get_composite_regime("RANGING", "VOLATILE")["note"]
    filt = "RANGING D1 + VOLATILE H4 — range breaking down, wait"
    for s in _STATES:
        for p in _PATHS:
            # as live: the filter's reason arrives with no block (no_trade_filter.py:245-252)
            why = _reason(_rv(stand_down_reason=filt, **s, **p))
            assert "breaking down" not in why.lower() and note not in why, why


# ── unreachable fallbacks: labelled, never counted as coverage (v3 §0.2) ────

def test_defensive_fallback_unreachable_on_h4_structure_disagrees():
    """Defensive fallback: unreachable on H4 per v3 §0.2 (pinned below)."""
    assert _reason(_rv(regime_h4_subtype="STRUCTURE_DISAGREES")).startswith(
        "On the 4-hour chart the swing pattern and the momentum point opposite ways")


def _walk(seed, n, freq, start, drift, vol):
    rnd = random.Random(seed)
    c, closes = 1.90, []
    for _ in range(n):
        c += drift + rnd.gauss(0, vol)
        closes.append(c)
    return pd.DataFrame(
        {"Open": closes, "Close": closes, "High": [x + vol for x in closes],
         "Low": [x - vol for x in closes], "Volume": [1000] * n},
        index=pd.date_range(start, periods=n, freq=freq, tz="UTC"))


def test_the_two_fallback_states_cannot_come_out_of_get_regime():
    """v4 §3: through the real get_regime. The 4-hour slope is forced from
    structure (regime_detection.py, the h4_slope block), so a confirmed
    structure at strength 25+ always trends and TRANSITIONAL is always
    UNCONFIRMED_TREND."""
    calls, real = [], rd._classify_ex

    def rec(adx, atr_ratio, slope, instrument=None, pair=None, structure=None):
        out = real(adx, atr_ratio, slope, instrument=instrument, pair=pair, structure=structure)
        calls.append((adx, atr_ratio, slope, structure, out))
        return out

    d1 = _walk(1, 220, "B", "2025-01-01", 0.0, 0.002)
    wk = _walk(2, 110, "W", "2023-01-01", 0.0, 0.004)
    h4_calls = []
    for seed in range(60):
        drift = (0.0009, -0.0009, 0.0)[seed % 3]
        h4 = _walk(100 + seed, 200, "4h", "2025-09-01", drift, 0.0012)
        if seed % 4 == 0:                 # a late pullback against the structure
            h4.iloc[-10:, h4.columns.get_loc("Close")] -= [0.0008 * k for k in range(10)]
        calls.clear()
        with mock.patch.object(rd, "_classify_ex", rec), \
             mock.patch.object(rd, "_oanda_ok", return_value=True), \
             mock.patch.object(rd, "_oanda_live_price", return_value=None), \
             mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: d1.tail(count).copy()), \
             mock.patch("regime_detection._oanda_h4_bars", lambda *a, count=120, h4=h4, **k: h4.tail(count).copy()), \
             mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: wk.tail(count).copy()):
            rd.get_regime("GBP_AUD")
        closes = list(h4.tail(120)["Close"])
        raw = closes[-1] - closes[-10]    # what the slope would be if it were not forced
        h4_calls += [c + (raw,) for c in calls[1:]]   # the first call is the daily chart
    confirmed = [c for c in h4_calls if c[3] in ("UPTREND", "DOWNTREND") and c[0] >= 25]
    opposed = [c for c in confirmed
               if (c[3] == "UPTREND" and c[5] < 0) or (c[3] == "DOWNTREND" and c[5] > 0)]
    assert len(confirmed) >= 5, "the sweep must reach confirmed 4-hour structure at 25+"
    assert opposed, "no raw move against its structure: the slope-forcing mutant could not bite"
    for adx, ratio, slope, struct, (regime, sub), _raw in h4_calls:
        if struct == "UPTREND":
            assert slope > 0, (adx, slope, struct)
        if struct == "DOWNTREND":
            assert slope < 0, (adx, slope, struct)
        assert sub != "STRUCTURE_DISAGREES", (adx, slope, struct, regime, sub)
        if adx >= 25 and 0.8 <= ratio < 1.2:
            assert not (regime == "VOLATILE" and sub == ""), (adx, ratio, struct)


# ── W5: exactly the target cells changed (golden from main, 47903d7) ─────────

def test_w5_only_the_old_range_breaking_down_cells_changed():
    golden = json.load(open(os.path.join(ROOT, "tests", "golden", "reason_grid_main.json")))
    assert golden["targets"] > 0 and golden["has_conflict_path"] and golden["has_stand_down_path"]
    summary, targets, _rows = grid.summarize(_is_new_sentence)
    assert summary["cells"] == golden["cells"]
    assert {k.split("|")[5] for k in targets} == {"0", "1"}       # both paths changed
    assert summary["targets"] == golden["targets"], (summary, golden)
    assert summary["target_keys_sha256"] == golden["target_keys_sha256"]
    assert summary["non_target_sha256"] == golden["non_target_sha256"]
