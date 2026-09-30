"""
test_weekly_alignment_wording.py

Pins docs/specs/weekly_alignment_wording_spec.md (Phase 5 review 2, R2b and
its review): the 20-week alignment gate blocks every trade against the
20-week trend; its former exceptions were unreachable and are removed; the
reason says what the gate does, in plain English.

Run: pytest test_weekly_alignment_wording.py
"""
import re

import pytest

import decision_brief as db
import regime_detection as rd
from no_trade_filter import apply_filter
from regime_detection import get_composite_regime

# Any raw label the brief should have translated (review F6).
_RAW = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b"
                  r"|\b(?:UPTREND|DOWNTREND|RANGING|VOLATILE|UNAVAILABLE|UNKNOWN|D1|H4)\b")

_LEVEL = {"UPTREND": 0.9, "DOWNTREND": 1.1, "RANGING": 1.0}


def _weekly(lt, st):
    """Real _compute_weekly_context output for a given (lt, st) — so fixtures
    carry only combinations the classifier can emit (review F8)."""
    c = [1.0] * 40
    for i in range(3):
        c[-(rd._WEEKLY_LT_LOOKBACK + 3) + i] = _LEVEL[lt]
        c[-(rd._WEEKLY_ST_LOOKBACK + 3) + i] = _LEVEL[st]
    out = rd._compute_weekly_context(c, c, c)
    assert (out["lt_trend"], out["st_trend"]) == (lt, st)
    return out


def test_the_former_exceptions_are_unreachable():
    """Every (lt, st): COUNTER_TREND_BOUNCE never pairs with lt=UPTREND and
    PULLBACK_IN_UPTREND never with lt=DOWNTREND — the removed exceptions
    could not fire, so removing them changes no decision."""
    pairs = {(lt, _weekly(lt, st)["weekly_context"])
             for lt in _LEVEL for st in _LEVEL}
    assert ("UPTREND", "COUNTER_TREND_BOUNCE") not in pairs
    assert ("DOWNTREND", "PULLBACK_IN_UPTREND") not in pairs
    assert len(pairs) == 5          # non-vacuous: the classifier really ran


def _shown(d, weekly):
    comp = get_composite_regime(d, d)
    r = {"regime_d1": d, "regime_h4": d, "adx": 28.0, "adx_h4": 28.0,
         "atr_vs_avg": 1.0, "structure": "DOWNTREND" if "DOWN" in d else "UPTREND",
         "execution_mode": comp["execution_mode"], "size_mult": comp["size_mult"],
         "confidence": comp["confidence"], "resolution_note": comp["note"],
         "news_gate": {}, "instrument": "GBP_AUD", "range_position": 0.5,
         "regime_d1_subtype": "", "regime_h4_subtype": "", **weekly}
    fr = apply_filter(r)
    r.update(filter_allowed=fr.allowed, filter_reason=fr.reason,
             filter_block=fr.block, stand_down=True, stand_down_reason=fr.reason)
    return fr, db._render_reason(r, {}, "STAND DOWN", False)


# Every weekly context the classifier emits with a 20-week trend (review F5).
@pytest.mark.parametrize("d,lt,st,side", [
    ("TRENDING_DOWN", "UPTREND", "UPTREND", "Short"),
    ("TRENDING_DOWN", "UPTREND", "DOWNTREND", "Short"),
    ("TRENDING_DOWN", "UPTREND", "RANGING", "Short"),
    ("TRENDING_UP", "DOWNTREND", "DOWNTREND", "Long"),
    ("TRENDING_UP", "DOWNTREND", "UPTREND", "Long"),
    ("TRENDING_UP", "DOWNTREND", "RANGING", "Long"),
])
def test_against_the_20_week_trend_is_blocked_and_says_so(d, lt, st, side):
    fr, shown = _shown(d, _weekly(lt, st))
    assert fr.allowed is False and fr.block == "weekly_alignment"
    word = "up" if lt == "UPTREND" else "down"
    assert shown == (f"{side} blocked: dominant 20-week trend is {word} — "
                     f"the framework does not trade against it."), shown
    assert _RAW.search(shown) is None, shown


@pytest.mark.parametrize("d,ctx", [("TRENDING_DOWN", "COUNTER_TREND_BOUNCE"),
                                   ("TRENDING_UP", "PULLBACK_IN_UPTREND")])
def test_apply_filter_has_no_counter_trend_exception(d, ctx):
    """Review F6/F8: the removed exceptions, pinned at apply_filter itself.
    Restoring either 'UNLESS' branch makes this fail — even though the
    classifier cannot currently produce these pairings."""
    lt = "UPTREND" if d == "TRENDING_DOWN" else "DOWNTREND"
    fr, _ = _shown(d, {"lt_trend": lt, "st_trend": "RANGING", "weekly_context": ctx})
    assert fr.allowed is False and fr.block == "weekly_alignment"


@pytest.mark.parametrize("d,lt,st", [("TRENDING_DOWN", "DOWNTREND", "DOWNTREND"),
                                     ("TRENDING_UP", "UPTREND", "UPTREND"),
                                     ("TRENDING_DOWN", "RANGING", "RANGING"),
                                     ("TRENDING_UP", "RANGING", "RANGING")])
def test_control_the_gate_is_silent_with_the_trend_or_without_one(d, lt, st):
    """With the 20-week trend, or when it is RANGING, the gate does not fire
    (review F5): whatever decides the cell, it is not this rule."""
    fr, _ = _shown(d, _weekly(lt, st))
    assert fr.block != "weekly_alignment"
    assert "20-week" not in fr.reason
