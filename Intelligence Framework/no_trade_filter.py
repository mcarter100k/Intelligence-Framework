"""
no_trade_filter.py
──────────────────
Single source of truth for all no-trade and stand-down decisions.

This module sits upstream of signal scoring. It reads the full
regime output and returns a FilterResult that either:
  - Allows trading (with execution parameters)
  - Blocks trading (with reason)
  - Overrides a stand-down in specific high-conviction conditions

STAND-DOWN CONDITIONS (any one triggers NO TRADE):
  1. D1 VOLATILE (ADX 18-25 transition zone) with no override eligible
  2. Opposite-trend conflict (D1 up + H4 down or vice versa)
  3. ATR compression (GBP/JPY pre-BoJ coil)
  4. Extreme ATR spike (ratio >= 2.0x)
  5. RANGING D1 + VOLATILE H4 (range breaking down)
  6. Both timeframes VOLATILE
  7. Exhaustion move on either timeframe (GBP/JPY RANGING/EXHAUSTION) —
     fade, don't follow; stands aside until EXHAUSTION is validated
  8. The official decision would not trade (no direction, disabled range
     trade, grade C) — official_decision.decide() runs on every provisional
     allow, so allowed == "the official decision trades"
     (docs/specs/decision_logic_spec.md)

COUNTER-TREND OVERRIDE (lifts D1 VOLATILE stand-down only):
  ALL of the following must be true:
  1. Stand-down reason is D1 VOLATILE only (not conflict, not ATR)
  2. H4 regime is TRENDING with ADX >= 25
  3. Weekly context is defined (not RANGING)
  4. H4 direction aligns with weekly structure bias
  5. D1 structure is confirmed (UPTREND or DOWNTREND, not TRANSITIONAL)

  When override fires:
    execution_mode = COUNTER_TREND_OVERRIDE
    size_mult      = 0.35  (reduced — unvalidated condition)
    confidence     = LOW
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterResult:
    allowed:             bool
    execution_mode:      str
    size_mult:           float
    confidence:          str
    reason:              str
    override_fired:      bool = False
    override_conditions: str  = ""
    # Which rule blocked, for renderers that must not re-narrate the cause
    # (decision_logic_spec review V1/V5): "exhaustion", "conflict" or
    # "decision" (the official decision would not trade). "" otherwise.
    block:               str  = ""


# Weekly contexts that have defined directional bias
_DIRECTIONAL_CONTEXTS = {
    "ESTABLISHED_UPTREND",
    "ESTABLISHED_DOWNTREND",
    "PULLBACK_IN_UPTREND",
    "COUNTER_TREND_BOUNCE",
}

# Minimum H4 ADX for override to fire
_OVERRIDE_MIN_H4_ADX = 25.0

# Size multiplier when override fires (unvalidated — conservative)
_OVERRIDE_SIZE_MULT = 0.35


def _derive_direction(d1: str, exec_mode: str) -> str:
    """
    Derive the intended trade direction from regime and execution mode.
    Returns "LONG", "SHORT", or "NONE" (no directional trade).

    Direction is always derivable from D1 regime — no external
    parameter needed.
    """
    if exec_mode in ("STAND_DOWN", "FADE_EXTREMES"):
        return "NONE"
    if d1 in ("TRENDING_UP",) or (
        exec_mode == "PULLBACK_ENTRY" and "UP" in d1
    ):
        return "LONG"
    if d1 in ("TRENDING_DOWN",) or (
        exec_mode == "PULLBACK_ENTRY" and "DOWN" in d1
    ):
        return "SHORT"
    if exec_mode == "CONTINUATION":
        if "UP" in d1:   return "LONG"
        if "DOWN" in d1: return "SHORT"
    if exec_mode == "REDUCED_MOMENTUM":
        if "UP" in d1:   return "LONG"
        if "DOWN" in d1: return "SHORT"
    return "NONE"


def apply_filter(regime: dict) -> FilterResult:
    """
    Apply the no-trade filter to a regime output dict.

    Args:
        regime: full dict returned by get_regime(), or a partial dict
                built inside get_regime() with the required keys.

    Returns:
        FilterResult with allowed, execution_mode, size_mult,
        confidence, reason, and override details.
    """
    d1         = regime.get("regime_d1",       "UNKNOWN") or "UNKNOWN"
    h4         = regime.get("regime_h4",       "UNKNOWN") or "UNKNOWN"
    adx_h4     = float(regime.get("adx_h4",   0.0) or 0.0)

    # ATR ratio — parse defensively. A MISSING value (None / key absent) is
    # treated as neutral 1.0; a value that is PRESENT but corrupt (non-numeric,
    # non-finite, or <= 0) is caught by the ATR-sanity hard block below. We must
    # not use `... or 1.0` here, as that silently rewrites a real 0.0 to 1.0.
    _atr_raw = regime.get("atr_vs_avg", 1.0)
    if _atr_raw is None:
        atr_ratio = 1.0
    else:
        try:
            atr_ratio = float(_atr_raw)
        except (TypeError, ValueError):
            atr_ratio = float("nan")
    atr_comp   = regime.get("atr_compression", False)
    structure  = regime.get("structure",       "TRANSITIONAL") or "TRANSITIONAL"
    weekly_ctx = regime.get("weekly_context",  "RANGING") or "RANGING"
    lt_trend   = regime.get("lt_trend",        "RANGING") or "RANGING"
    st_trend   = regime.get("st_trend",        "RANGING") or "RANGING"
    exec_mode  = regime.get("execution_mode",  "STAND_DOWN") or "STAND_DOWN"
    size_mult  = float(regime.get("size_mult", 0.0) or 0.0)
    confidence = regime.get("confidence",      "NONE") or "NONE"

    # ── Hard blocks — no override possible ───────────────────────────────────

    # ATR sanity — a present-but-corrupt volatility read (non-finite, or <= 0)
    # invalidates every downstream size and edge decision. Stand aside; never
    # trade on impossible volatility. (inf/nan/negative/zero all land here.)
    if not math.isfinite(atr_ratio) or atr_ratio <= 0.0:
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=(f"Invalid ATR ratio ({_atr_raw!r}) — corrupt volatility "
                    f"read, stand aside"),
        )

    # Pre-news stand-down gate (docs/specs/news_gate_spec.md) — a HIGH-impact
    # event for the pair's own currencies inside the 2-hour window. Safety
    # infrastructure, same class as the market-closed gate: the framework
    # declines to present its reading as valid when its inputs are guaranteed
    # to be repriced. Gate state is computed upstream (news_gate.check_news_gate
    # via get_regime) so this decision is deterministic from the input dict.
    _ng = regime.get("news_gate") or {}
    if _ng.get("gating"):
        # local-time parenthetical (display_timezone_spec) — display only
        from display_time import to_display
        from news_gate import gate_reason
        _evt = to_display(_ng.get('event_time_utc'), style='time')
        _at_local = f" (at {_evt})" if _evt else ""
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=gate_reason(_ng, _at_local),
        )

    # Weekly trend data unavailable (docs/specs/data_at_source_spec.md P3).
    # The 20-week trend gate below needs lt_trend; without it the gate used to
    # be skipped silently (UNAVAILABLE used to arrive as RANGING). Same class
    # as the H4 outage: the framework will not present a read it cannot check.
    if weekly_ctx == "UNAVAILABLE" or lt_trend == "UNAVAILABLE":
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=("Weekly trend data unavailable — the 20-week trend "
                    "check cannot run, so standing aside."),
        )

    # ATR compression (GBP/JPY pre-BoJ coil)
    if atr_comp:
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=regime.get("atr_compression_note",
                              "ATR compression — pre-intervention coil"),
        )

    # Exhaustion (decision_logic_spec D1, owner decision 2026-09-30). The
    # GBP/JPY RANGING/EXHAUSTION label means a violent extended move, not a
    # quiet market; read as a pullback it produced a grade-A trade WITH the
    # exhausted move. Stand aside until EXHAUSTION is a validated regime. The
    # subtype is regime_detection's single source — no threshold re-derived.
    if "EXHAUSTION" in (regime.get("regime_h4_subtype"),
                        regime.get("regime_d1_subtype")):
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=("The market is in an exhaustion move — fade, don't "
                    "follow. Standing aside."),
            block="exhaustion",
        )

    # Opposite-trend conflict — structural disagreement. Compared on the
    # regimes themselves: the former string match looked for tokens
    # _detect_conflict never emits, so this block could not fire (D3).
    if {d1, h4} == {"TRENDING_UP", "TRENDING_DOWN"}:
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=("Opposite trend conflict — the daily and 4-hour trends "
                    "point in opposite directions. No edge; standing aside."),
            block="conflict",
        )

    # Extreme ATR spike
    if atr_ratio >= 2.0:
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=f"ATR ratio {atr_ratio:.1f}x — extreme spike, stand aside",
        )

    # RANGING + VOLATILE — range breaking down
    if d1 == "RANGING" and h4 == "VOLATILE":
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason="RANGING D1 + VOLATILE H4 — range breaking down, wait",
        )

    # Both VOLATILE
    if d1 == "VOLATILE" and h4 == "VOLATILE":
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason="Both timeframes VOLATILE — no edge on either TF",
        )

    # ── D1 VOLATILE — check for counter-trend override ────────────────────────

    if d1 == "VOLATILE":
        override_result = _check_override(
            h4, adx_h4, weekly_ctx, lt_trend, st_trend, structure
        )
        if override_result:
            return _confirm_with_decision(regime, override_result)
        # Override not eligible — stand-down holds. Distinguish WHY D1 is
        # VOLATILE so the reason does not lie: ADX 25+ with unconfirmed pivot
        # structure is the "trending band, structure not confirmed" gate
        # (Problem 2; 32+ joined it with decision_logic_spec D2); ADX 25+ with
        # confirmed structure against the recent direction is a disagreement;
        # ADX 18-25 is the genuine no-edge transition zone. (Zone boundaries
        # mirror regime_detection; kept local to avoid a circular import,
        # since regime_detection imports this module.)
        d1_adx = float(regime.get("adx", 0.0) or 0.0)
        if d1_adx >= 25.0 and structure not in ("UPTREND", "DOWNTREND"):
            _reason = (f"D1 ADX {d1_adx:.1f} is in the trending band but pivot "
                       f"structure has not confirmed (no clean HH/HL or LH/LL) "
                       f"— trend unconfirmed, standing aside.")
        elif d1_adx >= 25.0:
            _reason = (f"D1 ADX {d1_adx:.1f} is in the trending band but the "
                       f"recent direction disagrees with the {structure.lower()} "
                       f"structure — trend unconfirmed, standing aside.")
        elif 18.0 <= d1_adx < 25.0:
            _reason = (f"D1 in transition zone (ADX {d1_adx:.1f}) — "
                       f"no statistical edge.")
        else:
            _reason = "D1 VOLATILE — no confirmed edge, standing aside."
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=_reason,
        )

    # ── Weekly alignment gate ─────────────────────────────────────────────────
    # Checks that the intended trade direction does not contradict
    # the dominant 20-week trend (lt_trend).
    #
    # ALIGNMENT RULE:
    #   SHORT against lt_trend=UPTREND is blocked
    #     UNLESS weekly_context=COUNTER_TREND_BOUNCE
    #     (dominant macro trend is actually DOWN)
    #   LONG against lt_trend=DOWNTREND is blocked
    #     UNLESS weekly_context=PULLBACK_IN_UPTREND
    #     (dominant macro trend is actually UP)
    #
    # Uses lt_trend (20-week) not weekly_context label —
    # lt_trend is the clean directional read.
    # If lt_trend is RANGING — no weekly bias, no gate.

    intended = _derive_direction(d1, exec_mode)

    if intended == "SHORT" and lt_trend == "UPTREND":
        if weekly_ctx != "COUNTER_TREND_BOUNCE":
            return FilterResult(
                allowed=False,
                execution_mode="STAND_DOWN",
                size_mult=0.0,
                confidence="NONE",
                reason=(
                    f"Short blocked: dominant 20-week trend is UPTREND. "
                    f"Counter-trend short requires COUNTER_TREND_BOUNCE "
                    f"weekly context (current: {weekly_ctx})."
                ),
            )

    if intended == "LONG" and lt_trend == "DOWNTREND":
        if weekly_ctx != "PULLBACK_IN_UPTREND":
            return FilterResult(
                allowed=False,
                execution_mode="STAND_DOWN",
                size_mult=0.0,
                confidence="NONE",
                reason=(
                    f"Long blocked: dominant 20-week trend is DOWNTREND. "
                    f"Counter-trend long requires PULLBACK_IN_UPTREND "
                    f"weekly context (current: {weekly_ctx})."
                ),
            )

    # ── Resolution table allows trading ───────────────────────────────────────
    if exec_mode == "STAND_DOWN":
        return FilterResult(
            allowed=False,
            execution_mode="STAND_DOWN",
            size_mult=0.0,
            confidence="NONE",
            reason=regime.get("resolution_note", "Resolution table: STAND_DOWN"),
        )

    # Market conditions pass — the official decision has the last word.
    return _confirm_with_decision(regime, FilterResult(
        allowed=True,
        execution_mode=exec_mode,
        size_mult=size_mult,
        confidence=confidence,
        reason="All filter conditions passed",
    ))


def _confirm_with_decision(regime: dict, provisional: FilterResult) -> FilterResult:
    """The filter is the single stand-down authority (decision_logic_spec D4):
    a provisional allow stands only if the official decision, run on it,
    trades. Otherwise block with the decision's own reason — no direction,
    a disabled range trade, or grade C. Before this, the filter allowed
    RANGING cells the official path then vetoed, and every consumer of
    filter_allowed (ledgers, session flips, alerts) saw an allow that was
    never a trade."""
    from official_decision import decide     # lazy: official imports this module
    d = decide(regime, exec_mode=provisional.execution_mode,
               size_mult=provisional.size_mult,
               override=provisional.override_fired)
    if d["direction"] in ("LONG", "SHORT"):
        return provisional
    return FilterResult(
        allowed=False,
        execution_mode="STAND_DOWN",
        size_mult=0.0,
        confidence="NONE",
        reason=d["reason"],
        block="decision",
    )


def _check_override(
    h4:         str,
    adx_h4:     float,
    weekly_ctx: str,
    lt_trend:   str,
    st_trend:   str,
    structure:  str,
) -> Optional[FilterResult]:
    """
    Check whether the counter-trend override conditions are met.
    Returns FilterResult if override fires, None if stand-down holds.

    ALL conditions must be true for override to fire:
    1. H4 is TRENDING (up or down) with ADX >= 25
    2. Weekly context is directional (not pure RANGING)
    3. H4 direction aligns with weekly bias
    4. D1 structure is confirmed (not TRANSITIONAL)
    """
    # Condition 1: H4 must be trending with real momentum
    if h4 not in ("TRENDING_UP", "TRENDING_DOWN"):
        return None
    if adx_h4 < _OVERRIDE_MIN_H4_ADX:
        return None

    # Condition 2: Weekly context must be directional
    if weekly_ctx not in _DIRECTIONAL_CONTEXTS:
        return None

    # Condition 3: H4 direction must align with weekly bias
    weekly_bullish = lt_trend == "UPTREND" or weekly_ctx in (
        "ESTABLISHED_UPTREND", "PULLBACK_IN_UPTREND"
    )
    weekly_bearish = lt_trend == "DOWNTREND" or weekly_ctx in (
        "ESTABLISHED_DOWNTREND", "COUNTER_TREND_BOUNCE"
    )

    h4_bullish = (h4 == "TRENDING_UP")
    h4_bearish = (h4 == "TRENDING_DOWN")

    aligned = (h4_bullish and weekly_bullish) or \
              (h4_bearish and weekly_bearish)

    if not aligned:
        return None

    # Condition 4: D1 structure must be confirmed
    if structure not in ("UPTREND", "DOWNTREND"):
        return None

    # All conditions met — override fires
    direction  = "long" if h4_bullish else "short"
    conditions = (
        f"H4 {h4} (ADX {adx_h4:.1f} >= {_OVERRIDE_MIN_H4_ADX}), "
        f"weekly={weekly_ctx}, "
        f"D1 structure={structure}, "
        f"direction aligned={direction}"
    )

    return FilterResult(
        allowed=True,
        execution_mode="COUNTER_TREND_OVERRIDE",
        size_mult=_OVERRIDE_SIZE_MULT,
        confidence="LOW",
        reason=(f"Counter-trend override: D1 VOLATILE but H4 + weekly "
                f"aligned {direction}. Reduced size={_OVERRIDE_SIZE_MULT}x. "
                f"Unvalidated — requires HTF level confirmation before entry."),
        override_fired=True,
        override_conditions=conditions,
    )


def get_filter_summary(result: FilterResult) -> str:
    """Plain-English summary of filter decision."""
    if not result.allowed:
        return f"NO TRADE — {result.reason}"
    if result.override_fired:
        return (f"OVERRIDE ACTIVE — {result.execution_mode} "
                f"at {result.size_mult}x size. "
                f"Conditions: {result.override_conditions}")
    return (f"TRADE ALLOWED — {result.execution_mode} "
            f"at {result.size_mult}x size, "
            f"confidence={result.confidence}")
