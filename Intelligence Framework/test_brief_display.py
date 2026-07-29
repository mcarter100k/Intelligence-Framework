"""
test_brief_display.py

Display-layer enforcement:
  * EXIT IF (_build_invalidation) names STRUCTURE confirmation when trend
    strength is already >= the trending threshold, and the ADX-cross text only
    when it is below it — pinned exact.
  * Rendered briefs (live stand-aside, mock LONG, mock active-shadow) all carry
    THE FULL PICTURE, contain the pinned narrative sentences, and NEVER contain
    a banned jargon token.

Run: pytest test_brief_display.py            (offline)
     pytest test_brief_display.py -m integration   (adds the live case)
"""
import re

import pytest

import decision_brief as db
from official_decision import get_official_decision

BANNED = re.compile(r'\bADX\b|HH/HL|LH/LL|\bpivot\b|ATR ratio')


def _assert_clean(text):
    m = BANNED.search(text)
    assert m is None, f"banned jargon token rendered: {m.group()!r}\n{text}"


def _brief_from_regime(regime, shadow_pending=None, pip=0.0001):
    """Mimic get_decision_brief's field construction from a mock regime (no
    network), exercising the real builders + _plain + narrative + format()."""
    off = get_official_decision(regime)
    direction = off["direction"]
    decision_str = ("STAND DOWN" if direction in ("NO TRADE", "") or regime.get("stand_down")
                    else direction)
    reason = db._plain(db._build_reason(regime, {}, decision_str, regime.get("override_fired", False)))
    invalidation = db._plain(db._build_invalidation(regime, decision_str))
    d1, h4 = regime.get("regime_d1"), regime.get("regime_h4")
    adx_d1, adx_h4 = float(regime.get("adx", 0)), float(regime.get("adx_h4", 0))
    market_state = (f"Weekly: {db._plain(regime.get('weekly_context','UNKNOWN'))} | "
                    f"Daily chart: {db._plain(d1)} (trend strength {adx_d1:.0f}/100) | "
                    f"4-hour chart: {db._plain(h4)} (trend strength {adx_h4:.0f}/100)")
    narrative = db._build_narrative(regime, decision_str, None, invalidation, shadow_pending, pip)
    return db.DecisionBrief(
        instrument=regime.get("instrument", "GBP_AUD"), timestamp="test",
        price=regime.get("current_price", 0.0), atr_pips=regime.get("atr_pips", 0.0),
        decision=decision_str, reason=reason, conviction=off["conviction"], grade=off["grade"],
        size_pct=int(off["size_mult"] * 100) if decision_str != "STAND DOWN" else 0,
        market_state=market_state, invalidation=invalidation,
        regime_log="daily chart: 2 outcomes logged (early data)",
        stand_down=(decision_str == "STAND DOWN"), override_fired=False,
        execution_mode=regime.get("execution_mode", ""), adx_d1=adx_d1, adx_h4=adx_h4,
        weekly_context=regime.get("weekly_context", ""), error=None, narrative=narrative)


# ── EXIT IF: the structure-confirm vs ADX-cross branches ───────────────────────

def test_exit_if_structure_confirm_when_strength_already_above_threshold():
    inv = db._build_invalidation(
        {"regime_d1": "VOLATILE", "adx": 26.8, "structure": "TRANSITIONAL"}, "STAND DOWN")
    assert inv == ("Daily price structure confirms a direction — a clean "
                   "stair-step pattern of higher highs and higher lows, or "
                   "lower highs and lower lows — with the 4-hour chart aligned. "
                   "Revisit then.")


def test_exit_if_adx_cross_when_strength_below_threshold():
    inv = db._build_invalidation(
        {"regime_d1": "VOLATILE", "adx": 23.1, "structure": "TRANSITIONAL"}, "STAND DOWN")
    # below 25 → the cross-25 watch condition is still ahead of us (valid)
    assert "crosses 25" in inv


# ── Mock regimes ───────────────────────────────────────────────────────────────

_LONG = {
    "instrument": "GBP_AUD", "filter_allowed": True, "filter_mode": "CONTINUATION",
    "execution_mode": "CONTINUATION", "filter_size_mult": 1.0, "confidence": "HIGH",
    "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "structure": "UPTREND",
    "adx": 30.0, "adx_h4": 30.0, "atr_vs_avg": 1.0, "weekly_context": "ESTABLISHED_UPTREND",
    "lt_trend": "UPTREND", "st_trend": "UPTREND", "current_price": 1.9100, "atr_pips": 90.0,
    "resolution_note": "clean continuation", "override_fired": False, "latest_sl": 1.9000,
}

_STANDASIDE_JPY = {
    "instrument": "GBP_JPY", "filter_allowed": False, "regime_d1": "VOLATILE",
    "regime_h4": "VOLATILE", "structure": "UPTREND", "adx": 23.1, "adx_h4": 20.0,
    "atr_vs_avg": 1.0, "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
    "current_price": 217.767, "atr_pips": 100.0, "stand_down": True,
    "filter_reason": "Both timeframes VOLATILE — no edge on either TF",
}


def test_mock_long_full_brief_pinned_and_clean():
    brief = _brief_from_regime(_LONG)
    out = brief.format()
    assert "THE FULL PICTURE" in out
    assert ("which is what produced this LONG signal — buying in the direction "
            "the weekly, daily and 4-hour agree on.") in brief.narrative
    assert ("The stop marks where that idea would be proven wrong; a close "
            "through it means the setup has failed and the trade is over.") in brief.narrative
    _assert_clean(out)


def test_mock_active_shadow_full_brief_pinned_and_clean():
    pending = {"candidate_id": "EARLY_MOMENTUM", "direction": "SHORT", "entry": 217.667}
    brief = _brief_from_regime(_STANDASIDE_JPY, shadow_pending=pending, pip=0.01)
    out = brief.format()
    assert "THE FULL PICTURE" in out
    # price 217.767 vs SHORT entry 217.667 → 10 pips underwater
    assert ("Separately, the framework is watching a EARLY_MOMENTUM SHORT idea "
            "entered at 217.667 — currently about 10 pips underwater — logged "
            "for evidence, NOT traded.") in brief.narrative
    _assert_clean(out)


@pytest.mark.integration
def test_live_stand_aside_full_brief_present_and_clean():
    for inst in ("GBP_AUD", "GBP_JPY"):
        brief = db.get_decision_brief(inst)
        out = brief.format()
        if brief.error:
            continue
        assert "THE FULL PICTURE" in out
        _assert_clean(out)
