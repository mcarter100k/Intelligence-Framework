"""
test_exhaustion_display.py
──────────────────────────
Pins docs/specs/exhaustion_subtype_display_spec.md: the GBP/JPY exhaustion
RANGING renders as overextension (never "moving sideways"), quiet RANGING
keeps its words, GBP/AUD is unaffected, and routing/decisions are
byte-identical — the subtype changes words only.

Run: pytest test_exhaustion_display.py
"""
import decision_brief as db
import regime_detection as rd
from official_decision import get_official_decision


# ── classifier: subtype source of truth, routing unchanged ─────────────────────

_JPY = rd.PAIRS["GBP_JPY"]
_AUD = rd.PAIRS["GBP_AUD"]

def test_jpy_exhaustion_branch_sets_subtype():
    regime, sub = rd._classify_ex(64.1, 1.05, -1.0, "GBP_JPY", _JPY, "DOWNTREND")
    assert (regime, sub) == ("RANGING", "EXHAUSTION")

def test_quiet_ranging_has_no_subtype():
    regime, sub = rd._classify_ex(15.0, 1.0, 0.0, "GBP_JPY", _JPY, "TRANSITIONAL")
    assert (regime, sub) == ("RANGING", "")

def test_gbpaud_high_adx_is_not_subtyped():
    regime, sub = rd._classify_ex(64.1, 1.05, -1.0, "GBP_AUD", _AUD, "DOWNTREND")
    assert regime == "TRENDING_DOWN" and sub == ""

def test_wrapper_routing_pinned_unchanged():
    # _classify must return exactly what it returned before the refactor,
    # across every branch of the matrix.
    cases = [
        ((64.1, 1.05, -1.0, "GBP_JPY", _JPY, "DOWNTREND"), "RANGING"),
        ((64.1, 1.05, -1.0, "GBP_AUD", _AUD, "DOWNTREND"), "TRENDING_DOWN"),
        ((15.0, 1.00,  0.0, "GBP_JPY", _JPY, "TRANSITIONAL"), "RANGING"),
        ((20.0, 1.00,  0.0, "GBP_AUD", _AUD, "TRANSITIONAL"), "VOLATILE"),
        ((28.0, 1.00,  1.0, "GBP_AUD", _AUD, "UPTREND"), "TRENDING_UP"),
        ((28.0, 1.00,  1.0, "GBP_AUD", _AUD, "TRANSITIONAL"), "VOLATILE"),
        ((28.0, 1.60,  1.0, "GBP_AUD", _AUD, "UPTREND"), "VOLATILE"),   # spike
        ((28.0, 0.70,  1.0, "GBP_JPY", _JPY, "UPTREND"), "VOLATILE"),   # coil
    ]
    for args, want in cases:
        assert rd._classify(*args) == want, args


# ── display: MARKET STATE ──────────────────────────────────────────────────────

def _regime(adx_h4=64.1, h4_sub="EXHAUSTION", h4_struct="DOWNTREND",
            regime_h4="RANGING", **over):
    r = {"weekly_context": "ESTABLISHED_UPTREND",
         "regime_d1": "VOLATILE", "regime_d1_subtype": "",
         "regime_h4": regime_h4, "regime_h4_subtype": h4_sub,
         "structure": "TRANSITIONAL", "structure_h4": h4_struct,
         "adx": 27.5, "adx_h4": adx_h4}
    r.update(over)
    return r

def test_market_state_exhaustion_words_pinned():
    ms = db._build_market_state(_regime())
    assert ("4-hour chart: in a strong downtrend, flagged as overextended — "
            "the framework does not chase this (trend strength 64/100)") in ms
    assert "moving sideways" not in ms

def test_market_state_quiet_ranging_keeps_sideways():
    ms = db._build_market_state(_regime(adx_h4=15.0, h4_sub=""))
    assert "4-hour chart: moving sideways (trend strength 15/100)" in ms
    assert "overextended" not in ms

def test_market_state_d1_exhaustion_equivalent():
    ms = db._build_market_state(_regime(
        regime_d1="RANGING", regime_d1_subtype="EXHAUSTION",
        structure="DOWNTREND", adx=40.0, h4_sub="", regime_h4="VOLATILE"))
    assert "Daily chart: in a strong downtrend, flagged as overextended" in ms

def test_market_state_unconfirmed_structure_falls_back():
    ms = db._build_market_state(_regime(h4_struct="TRANSITIONAL"))
    assert "in a strong extended move, flagged as overextended" in ms


# ── display: THE FULL PICTURE ──────────────────────────────────────────────────

def test_narrative_exhaustion_words_pinned():
    n = db._build_narrative(_regime(), "STAND DOWN")
    assert ("The 4-hour chart is in a strong downtrend, flagged as "
            "overextended — the framework does not chase this "
            "(trend strength 64/100).") in n
    assert "moving sideways" not in n

def test_narrative_quiet_ranging_keeps_sideways():
    n = db._build_narrative(_regime(adx_h4=15.0, h4_sub=""), "STAND DOWN")
    assert "The 4-hour chart is moving sideways (trend strength 15/100)." in n

def test_narrative_banned_tokens_absent():
    n = db._build_narrative(_regime(), "STAND DOWN")
    for tok in ("ADX", "pivot", "HH-HL", "LH-LL", "ATR ratio"):
        assert tok not in n


# ── display: REASON pre-pass ───────────────────────────────────────────────────

def test_reason_prepass_replaces_exhaustion_ranging_token():
    out = db._exhaustion_reason_pass(
        "RANGING D1 + VOLATILE H4 — range breaking down, wait",
        {"regime_d1_subtype": "EXHAUSTION", "regime_h4_subtype": ""})
    assert "RANGING D1" not in out
    assert "overextended one-way move D1 (not chased)" in out

def test_reason_prepass_leaves_quiet_ranging_alone():
    text = "RANGING D1 + VOLATILE H4 — range breaking down, wait"
    assert db._exhaustion_reason_pass(
        text, {"regime_d1_subtype": "", "regime_h4_subtype": ""}) == text

def test_build_reason_live_shape_never_says_sideways_on_exhaustion():
    # the exact live GBP/JPY shape that exposed the bug: D1 ADX 28 with
    # unconfirmed structure (cause 3a) while H4 is exhaustion-RANGING
    regime = {"regime_d1": "VOLATILE", "regime_h4": "RANGING",
              "regime_d1_subtype": "", "regime_h4_subtype": "EXHAUSTION",
              "adx": 27.5, "adx_h4": 64.1, "structure": "TRANSITIONAL",
              "structure_h4": "DOWNTREND", "timeframe_conflict": False,
              "atr_compression": False, "atr_vs_avg": 1.05,
              "weekly_context": "PULLBACK_IN_UPTREND",
              "execution_mode": "STAND_DOWN", "stand_down_reason": "",
              "filter_allowed": False, "filter_reason": ""}
    reason = db._plain(db._exhaustion_reason_pass(
        db._build_reason(regime, {}, "STAND DOWN", False), regime))
    assert "moving sideways" not in reason
    assert "overextended" in reason

def test_build_reason_quiet_h4_ranging_still_says_sideways():
    regime = {"regime_d1": "VOLATILE", "regime_h4": "RANGING",
              "regime_d1_subtype": "", "regime_h4_subtype": "",
              "adx": 27.5, "adx_h4": 15.0, "structure": "TRANSITIONAL",
              "structure_h4": "TRANSITIONAL", "timeframe_conflict": False,
              "atr_compression": False, "atr_vs_avg": 1.0,
              "weekly_context": "PULLBACK_IN_UPTREND",
              "execution_mode": "STAND_DOWN", "stand_down_reason": "",
              "filter_allowed": False, "filter_reason": ""}
    reason = db._plain(db._exhaustion_reason_pass(
        db._build_reason(regime, {}, "STAND DOWN", False), regime))
    assert "moving sideways" in reason


# ── behavior freeze: decisions byte-identical ──────────────────────────────────

def test_official_decision_ignores_subtype_fields():
    base = {"execution_mode": "STAND_DOWN", "composite_regime": "VOLATILE",
            "confidence": "NONE", "size_mult": 0.0, "stand_down": True,
            "filter_allowed": False, "filter_reason": "x",
            "regime_d1": "RANGING", "regime_h4": "RANGING",
            "structure": "DOWNTREND", "instrument": "GBP_JPY"}
    with_sub = dict(base, regime_d1_subtype="EXHAUSTION",
                    regime_h4_subtype="EXHAUSTION", structure_h4="DOWNTREND")
    assert get_official_decision(base) == get_official_decision(with_sub)

def test_official_decision_unaffected_both_pairs_tradeable_case():
    base = {"execution_mode": "CONTINUATION", "composite_regime": "TRENDING_UP",
            "confidence": "HIGH", "size_mult": 1.0, "stand_down": False,
            "filter_allowed": True, "filter_reason": "",
            "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP",
            "structure": "UPTREND"}
    for inst in ("GBP_AUD", "GBP_JPY"):
        a = get_official_decision(dict(base, instrument=inst))
        b = get_official_decision(dict(base, instrument=inst,
                                       regime_d1_subtype="", regime_h4_subtype="",
                                       structure_h4="UPTREND"))
        assert a == b
