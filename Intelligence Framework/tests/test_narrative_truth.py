"""
test_narrative_truth.py — regime_log_restore spec items 2, 3, 4b (pinned).

Narrative-truth matrix: for a matrix of regime states, the rendered REASON
and FULL PICTURE claims must match the regime FIELDS — alignment is derived,
never asserted from the existence of a decision. Regression anchor: the
2026-09-10 18:04 PDT GBP/AUD brief rendered "4-hour chart trending inside
daily chart trending_down" (opposite of the raw state, plus a raw-token
leak) and "All three timeframes line up" over an H4 in the transition zone.
"""
import re

import decision_brief as db

RAW_TOKEN = re.compile(r'\b[A-Za-z]+_[A-Za-z0-9]+\b')


def _reason(regime, decision_str="SHORT"):
    return db._render_reason(regime, {}, decision_str, False)


def _narrative(regime, decision_str):
    return db._build_narrative(regime, decision_str, None, "", None, 0.0001)


def _mk(d1, h4, weekly, **over):
    r = {
        "regime_d1": d1, "regime_h4": h4, "weekly_context": weekly,
        "lt_trend": over.pop("lt_trend", "RANGING"),
        "execution_mode": "REDUCED_MOMENTUM", "filter_mode": "REDUCED_MOMENTUM",
        "filter_allowed": True, "filter_size_mult": 0.5, "size_mult": 0.5,
        "stand_down": False, "confidence": "LOW",
        "adx": 26.0, "adx_h4": 22.0, "atr_vs_avg": 0.96,
        "structure": "DOWNTREND", "current_price": 1.8879, "atr_pips": 84.0,
    }
    r.update(over)
    return r


# ── REASON renders per the actual (d1, h4) cell ───────────────────────────────

def test_reason_d1_trending_h4_volatile_names_the_true_state():
    """The 2026-09-10 incident cell: D1 trends, H4 is the unresolved one."""
    r = _mk("TRENDING_DOWN", "VOLATILE", "ESTABLISHED_DOWNTREND")
    text = _reason(r)
    assert "Daily downtrend intact" in text
    assert "4-hour chart has not resolved" in text
    assert "Wait for the 4-hour chart to resolve" in text
    assert "inside" not in text          # the old inverted claim
    assert RAW_TOKEN.search(text) is None, text


def test_reason_d1_ranging_h4_trending_names_the_suspect_h4():
    r = _mk("RANGING", "TRENDING_DOWN", "RANGING",
            adx=15.0, adx_h4=28.0, structure="TRANSITIONAL")
    text = _reason(r)
    assert "4-hour downtrend inside a sideways daily market" in text
    assert "range trade with momentum bias" in text
    assert RAW_TOKEN.search(text) is None, text


def test_reason_d1_exhaustion_never_called_sideways():
    r = _mk("RANGING", "TRENDING_UP", "RANGING",
            adx=40.0, adx_h4=28.0, structure="TRANSITIONAL",
            regime_d1_subtype="EXHAUSTION")
    text = _reason(r)
    assert "overextended daily one-way move" in text
    assert "sideways" not in text
    assert RAW_TOKEN.search(text) is None, text


# ── FULL PICTURE: alignment derived from fields, never from the decision ──────

def test_narrative_full_alignment_still_says_line_up():
    r = _mk("TRENDING_DOWN", "TRENDING_DOWN", "ESTABLISHED_DOWNTREND",
            execution_mode="CONTINUATION", filter_mode="CONTINUATION",
            filter_size_mult=1.0, size_mult=1.0, confidence="HIGH",
            adx_h4=30.0)
    text = _narrative(r, "SHORT")
    assert "All three timeframes line up" in text
    assert RAW_TOKEN.search(text) is None, text


def test_narrative_h4_unresolved_under_short_is_honest():
    """The incident state: SHORT with H4 in the transition zone."""
    r = _mk("TRENDING_DOWN", "VOLATILE", "ESTABLISHED_DOWNTREND",
            regime_h4_subtype="TRANSITION_ZONE")
    text = _narrative(r, "SHORT")
    assert "All three timeframes line up" not in text
    assert "not full alignment" in text
    assert "4-hour chart has not resolved in that direction yet" in text
    assert "position size is reduced" in text     # size_mult 0.5
    assert RAW_TOKEN.search(text) is None, text


def test_narrative_opposed_timeframe_under_decision_says_so():
    """A timeframe actively pointing the other way is named, not papered over."""
    r = _mk("TRENDING_DOWN", "TRENDING_UP", "ESTABLISHED_DOWNTREND")
    text = _narrative(r, "SHORT")
    assert "All three timeframes line up" not in text
    assert "the other way" in text
    assert "not aligned" in text
    assert RAW_TOKEN.search(text) is None, text


def test_narrative_full_size_partial_alignment_makes_no_reduced_size_claim():
    """CONTINUATION at 1.0x with a directionless weekly must not claim the
    size was reduced — the honest sentence stops at the unresolved chart."""
    r = _mk("TRENDING_DOWN", "TRENDING_DOWN", "RANGING",
            execution_mode="CONTINUATION", filter_mode="CONTINUATION",
            filter_size_mult=1.0, size_mult=1.0, confidence="HIGH",
            adx_h4=30.0)
    text = _narrative(r, "SHORT")
    assert "All three timeframes line up" not in text
    assert "weekly chart has not resolved" in text
    assert "size is reduced" not in text
    assert RAW_TOKEN.search(text) is None, text
