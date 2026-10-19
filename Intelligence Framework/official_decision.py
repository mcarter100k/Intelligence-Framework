"""
official_decision.py
────────────────────
The one official LONG / SHORT / NO TRADE call, with its conviction and
grade, computed deterministically from get_regime's output. Every input,
including the conviction points below, is an INFORMED PRIOR, not a
validated result (validation_log 2026-06-29).
"""

from typing import Dict

# Range trading: only the outer `_RANGE_EDGE` fraction of the range is tradeable
# (0.25 = fade in the bottom/top 25%). Mid-range has no edge.
_RANGE_EDGE = 0.25

# INFORMED PRIOR — UNREVIEWED, gated off 2026-07-29.
# Range trading (below) is an unreviewed, unvalidated heuristic that can issue
# live grade-B trades at 0.75x size. Precedent: the counter-trend override
# (team-reviewed, 5 conditions, 0.35x size) still fired 2026-05-15 and lost on a
# 280-pip rally. An UNREVIEWED heuristic at HIGHER size does not trade until it
# survives team review + non-overlapping validation. The logic is retained but
# gated off — flip to True only after that review passes.
RANGE_TRADING_ENABLED = False


# The decision rules in force (docs/specs/decision_logic_spec.md). Logged on
# every regime, trade and session row so evidence recorded under different
# rules is never pooled: rows written before Phase 5 carry it blank.
LOGIC_VERSION = "p5-2026-09-30"


def _no_trade(reason: str) -> Dict:
    return {
        "direction": "NO TRADE", "conviction": 0, "grade": "C",
        "size_mult": 0.0, "reason": reason,
        "source": "official_filter_path", "logic_version": LOGIC_VERSION,
    }


def get_official_decision(regime: Dict) -> Dict:
    """
    The single official decision. Input: full get_regime() dict.
    Output dict:
      direction     : "LONG" | "SHORT" | "NO TRADE"
      conviction    : 0-100
      grade         : "A+" | "A" | "B+" | "B" | "C"
      size_mult     : float (from filter)
      reason        : str
      source        : "official_filter_path"
      logic_version : LOGIC_VERSION

    NO TRADE when the filter blocked; otherwise decide(). Since apply_filter
    itself runs decide() and blocks whenever it would not trade, a filter
    allow always yields LONG/SHORT here (decision_logic_spec: the filter is
    the single stand-down authority). The checks in decide() still run on
    this path — defence in depth, never a second, disagreeing authority.
    """
    if not regime.get("filter_allowed", False):
        return _no_trade(regime.get("filter_reason", "Filter stand-down"))
    return decide(
        regime,
        exec_mode=regime.get("filter_mode",
                             regime.get("execution_mode", "STAND_DOWN")),
        size_mult=float(regime.get("filter_size_mult", 0.0) or 0.0),
        override=regime.get("override_fired", False),
    )


def decide(regime: Dict, exec_mode: str, size_mult: float,
           override: bool = False) -> Dict:
    """
    The whole call for a setup the market-condition checks have passed:
    direction, the (disabled) range trade, conviction and grade. Pure — the
    same inputs always give the same answer. apply_filter calls this on its
    provisional allow and blocks with the returned reason whenever the
    direction is NO TRADE, so the filter and the official decision cannot
    disagree.
    """
    confidence = regime.get("confidence", "NONE")
    d1         = regime.get("regime_d1", "UNKNOWN")
    structure  = regime.get("structure", "TRANSITIONAL")

    from no_trade_filter import _derive_direction

    if exec_mode == "COUNTER_TREND_OVERRIDE":
        # Override: D1 is VOLATILE, direction comes from H4
        h4 = regime.get("regime_h4", "UNKNOWN")
        if h4 == "TRENDING_UP":
            direction = "LONG"
        elif h4 == "TRENDING_DOWN":
            direction = "SHORT"
        else:
            direction = "NONE"
    else:
        direction = _derive_direction(d1, exec_mode)

    # Range / fade-from-edges: a RANGING regime (FADE_EXTREMES) issues no trend
    # direction, so derive one from position in the range. Only the OUTER edges
    # are tradeable — mid-range has no edge. Never fade directly against a
    # strongly established weekly trend (support/resistance is likely to break).
    range_trade = False
    if direction == "NONE" and exec_mode == "FADE_EXTREMES":
        rng_pos  = regime.get("range_position")
        lt_trend = regime.get("lt_trend", "RANGING")
        if rng_pos is not None:
            if rng_pos <= _RANGE_EDGE and lt_trend != "DOWNTREND":
                direction, range_trade = "LONG", True      # fade at support
            elif rng_pos >= (1.0 - _RANGE_EDGE) and lt_trend != "UPTREND":
                direction, range_trade = "SHORT", True     # fade at resistance

        # Gate: an unreviewed heuristic does not trade. A detected range
        # candidate stands aside until range trading is reviewed + validated.
        if range_trade and not RANGE_TRADING_ENABLED:
            return _no_trade("Range trading candidate detected — disabled "
                             "pending team review and validation.")

    if direction == "NONE":
        if exec_mode == "FADE_EXTREMES":
            return _no_trade("Range mid-zone or edge blocked by the dominant "
                             "weekly trend — wait for price to reach a "
                             "tradeable range extreme before fading.")
        # A mode that wants a trend direction the daily chart does not give
        # (e.g. daily ranging under a trending 4-hour) — nothing to follow.
        return _no_trade("The daily chart gives no trend direction to follow "
                         "— no trade. Standing aside.")

    # Conviction: start from the resolution table's confidence tier, then add
    # or subtract fixed points (all informed priors).
    base     = {"HIGH": 70, "MEDIUM": 55, "LOW": 40}.get(confidence, 30)
    jpy_note = ""

    if range_trade:
        # Mean-reversion fade at a range edge — a valid setup but lower grade
        # than a trend continuation. No trend-structure bonus; a fade penalty;
        # capped below the momentum tiers. Needs rejection confirmation at the
        # level (entry_confirmation) before entry.
        base = min(base, 55) - 10
        range_note = (" | Range fade at support/resistance — reduced size, "
                      "needs a rejection candle at the level before entry.")
    else:
        range_note = ""

        # Structure agreement bonus (P2)
        struct_aligned = (
            (direction == "LONG" and structure == "UPTREND") or
            (direction == "SHORT" and structure == "DOWNTREND")
        )
        if struct_aligned:
            base += 10

        # H4 momentum bonus: adx_h4 >= 25 (conservative +5)
        if float(regime.get("adx_h4", 0) or 0) >= 25:
            base += 5

        # Exhaustion penalty
        if regime.get("adx_exhaustion", False):
            base -= 15

        # GBP/JPY at 1.0-1.2x normal volatility snapped back 75% of the time
        # (2026-06-29; N=16, below the N<20 INSUFFICIENT line): cut conviction.
        instrument = regime.get("instrument", "")
        atr_ratio  = float(regime.get("atr_vs_avg", 1.0) or 1.0)
        if ("JPY" in instrument
                and direction in ("LONG", "SHORT")
                and exec_mode in ("CONTINUATION", "PULLBACK_ENTRY",
                                  "REDUCED_MOMENTUM")
                and 1.0 <= atr_ratio < 1.2):
            base -= 20
            jpy_note = (" | GBP/JPY caution: at this volatility level this pair "
                        "historically snaps back rather than follows through "
                        "(75% mean reversion, N=16)")

        # Override caps conviction (P8 — unvalidated condition)
        if override:
            base = min(base, 45)

    conviction = max(0, min(100, base))

    # Grade from conviction
    if conviction >= 80:   grade = "A+"
    elif conviction >= 70: grade = "A"
    elif conviction >= 60: grade = "B+"
    elif conviction >= 45: grade = "B"
    else:                  grade = "C"

    # Grade C never trades (owner decision 2026-09-30; validation_log has the
    # 2026-09-25 GBP/JPY row that showed a C as a direction).
    if grade == "C":
        return _no_trade(f"Setup grades C (conviction {conviction} of 100) — "
                         f"the risk rules never trade a C. Standing aside.")

    return {
        "direction": direction, "conviction": conviction,
        "grade": grade, "size_mult": size_mult,
        "reason": regime.get("resolution_note", exec_mode) + jpy_note + range_note,
        "source": "official_filter_path", "logic_version": LOGIC_VERSION,
    }
