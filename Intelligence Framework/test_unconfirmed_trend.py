"""
test_unconfirmed_trend.py
─────────────────────────
Pins docs/specs/unconfirmed_trend_display_spec.md: the UNCONFIRMED_TREND
subtype's single source, the factual pip-change wording, the concrete
EXIT IF with the engine's TRUE confirmation rule, the vocabulary ban for
this subtype, and the behavior freeze (routing + decisions byte-identical;
transition-zone and quiet-RANGING wording untouched).

Run: pytest test_unconfirmed_trend.py
"""
import decision_brief as db
import regime_detection as rd
from official_decision import get_official_decision

_AUD = rd.PAIRS["GBP_AUD"]
_JPY = rd.PAIRS["GBP_JPY"]


# ── classifier: single source, routing unchanged ───────────────────────────────

def test_trending_band_transitional_is_tagged():
    assert rd._classify_ex(25.5, 1.0, 0.1, "GBP_AUD", _AUD, "TRANSITIONAL") \
        == ("VOLATILE", "UNCONFIRMED_TREND")

def test_transition_zone_18_25_has_own_subtype():
    # follow-up ruling 2026-09-09: transition zone is named, not blank
    assert rd._classify_ex(20.0, 1.0, 0.1, "GBP_AUD", _AUD, "TRANSITIONAL") \
        == ("VOLATILE", "TRANSITION_ZONE")

def test_confirmed_structure_is_untagged():
    assert rd._classify_ex(28.0, 1.0, 1.0, "GBP_AUD", _AUD, "UPTREND") \
        == ("TRENDING_UP", "")
    assert rd._classify_ex(28.0, 1.0, -1.0, "GBP_AUD", _AUD, "DOWNTREND") \
        == ("TRENDING_DOWN", "")

def test_routing_matrix_unchanged():
    cases = [
        ((25.5, 1.0, 0.1, "GBP_AUD", _AUD, "TRANSITIONAL"), "VOLATILE"),
        ((20.0, 1.0, 0.1, "GBP_AUD", _AUD, "TRANSITIONAL"), "VOLATILE"),
        ((15.0, 1.0, 0.0, "GBP_AUD", _AUD, "TRANSITIONAL"), "RANGING"),
        ((64.1, 1.05, -1.0, "GBP_JPY", _JPY, "DOWNTREND"), "RANGING"),
        ((35.0, 1.0, -1.0, "GBP_AUD", _AUD, "TRANSITIONAL"), "TRENDING_DOWN"),
    ]
    for args, want in cases:
        assert rd._classify(*args) == want, args


# ── display fixtures: today's GBP_AUD D1 shape ─────────────────────────────────

def _regime(**over):
    r = {"weekly_context": "STRONG_DOWNTREND_ALL_TIMEFRAMES",
         "regime_d1": "VOLATILE", "regime_d1_subtype": "UNCONFIRMED_TREND",
         "regime_h4": "RANGING", "regime_h4_subtype": "",
         "structure": "TRANSITIONAL", "structure_h4": "TRANSITIONAL",
         "adx": 25.0, "adx_h4": 17.0,
         "d1_change_pips_10": -290.0,
         "d1_pending_low": 1.87323, "d1_pending_low_age": 1,
         "d1_pending_high": 1.92600, "d1_pending_high_age": 45,
         "d1_lower_highs": True, "d1_higher_lows": True,
         "latest_sl": 1.90733, "latest_sh": 1.89716,
         "pair": "GBP/AUD"}
    r.update(over)
    return r


def test_market_state_falling_unconfirmed_pinned():
    ms = db._build_market_state(_regime())
    assert ("Daily chart: falling — down 290 pips over the last 10 "
            "sessions — but the confirmation rule isn't met yet "
            "(trend strength 25/100)") in ms

def test_market_state_vocabulary_ban_for_subtype():
    ms = db._build_market_state(_regime())
    d1_clause = ms.split("|")[1]
    assert "choppy" not in d1_clause
    assert "no clear direction" not in d1_clause

def test_narrative_engine_waiting_sentence():
    n = db._build_narrative(_regime(), "STAND DOWN")
    assert ("The daily chart has been falling — down 290 pips over the "
            "last 10 sessions. The engine is waiting for the latest low "
            "to confirm before calling it a trend.") in n
    assert "choppy with no clear direction" not in n.split("4-hour")[0]

def test_rising_mirror():
    ms = db._build_market_state(_regime(d1_change_pips_10=180.0))
    assert "rising — up 180 pips over the last 10 sessions" in ms


# ── EXIT IF: concrete, true rule, honesty-gated ────────────────────────────────

def test_exit_if_names_pending_low_young_candidate():
    out = db._build_invalidation(_regime(), "STAND DOWN")
    assert out == ("The low near 1.8732 confirms as a swing low — it stays "
                   "the lowest point for 2 more sessions and a session then "
                   "closes above it — with the 4-hour chart aligned, the "
                   "downtrend is confirmed then. Revisit then.")

def test_exit_if_shape_complete_candidate():
    out = db._build_invalidation(_regime(d1_pending_low_age=4), "STAND DOWN")
    assert "a session closes back above it" in out
    assert "more session" not in out

def test_exit_if_falls_back_when_highs_do_not_agree():
    # lower highs NOT in place: a confirmed low alone would not make a
    # downtrend — the concrete promise would be dishonest, generic stays
    out = db._build_invalidation(_regime(d1_lower_highs=False), "STAND DOWN")
    assert "stair-step" in out

def test_exit_if_falls_back_when_candidate_not_lower():
    out = db._build_invalidation(_regime(d1_pending_low=1.95), "STAND DOWN")
    assert "stair-step" in out

def test_exit_if_falls_back_without_the_fact():
    out = db._build_invalidation(_regime(d1_change_pips_10=None), "STAND DOWN")
    assert "stair-step" in out


# ── behavior freeze: neighbors keep their wording ──────────────────────────────

def test_transition_zone_wording_per_followup_ruling():
    # superseded by the 2026-09-09 follow-up ruling: transition-zone VOLATILE
    # names itself
    r = _regime(adx=20.0, regime_d1_subtype="TRANSITION_ZONE",
                d1_change_pips_10=-290.0)
    ms = db._build_market_state(r)
    assert ("Daily chart: no clear direction yet (trend strength 20/100, "
            "transition zone)") in ms

def test_h4_quiet_ranging_unchanged():
    ms = db._build_market_state(_regime())
    assert "4-hour chart: moving sideways (trend strength 17/100)" in ms

def test_official_decision_ignores_new_fields():
    base = {"execution_mode": "STAND_DOWN", "composite_regime": "VOLATILE",
            "confidence": "NONE", "size_mult": 0.0, "stand_down": True,
            "filter_allowed": False, "filter_reason": "x",
            "regime_d1": "VOLATILE", "regime_h4": "RANGING",
            "structure": "TRANSITIONAL"}
    extra = dict(base, regime_d1_subtype="UNCONFIRMED_TREND",
                 d1_change_pips_10=-290.0, d1_pending_low=1.87323,
                 d1_pending_low_age=1, d1_lower_highs=True,
                 d1_higher_lows=True)
    for inst in ("GBP_AUD", "GBP_JPY"):
        assert get_official_decision(dict(base, instrument=inst)) == \
               get_official_decision(dict(extra, instrument=inst))
