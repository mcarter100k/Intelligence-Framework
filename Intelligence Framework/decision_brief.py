"""
decision_brief.py
─────────────────
Trader-facing output layer. Compresses full framework output
into a 7-field brief readable in under 10 seconds.

This is the final output layer. Everything the framework computes
passes through here before a human sees it.

FIELDS:
  1. decision     : LONG / SHORT / STAND DOWN
  2. reason       : one sentence — why this decision
  3. conviction   : 0-100 score + letter grade
  4. size_pct     : position size modifier as percentage (0-100)
  5. market_state : three-timeframe snapshot string
  6. invalidation : one sentence — what makes this view wrong
  7. regime_log   : sample count behind current regime

DESIGN RULES:
  - One function call: get_decision_brief(instrument)
  - Returns a DecisionBrief dataclass + formatted string
  - Never raises — returns a safe STAND DOWN brief on any error
  - Invalidation is always derived from framework data,
    never hardcoded text
  - Regime log pulled from regime_classifier_logger.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from regime_detection import get_regime, PAIRS
from regime_classifier_logger import get_regime_accuracy


@dataclass
class DecisionBrief:
    # Identity
    instrument:   str
    timestamp:    str
    price:        float
    atr_pips:     float

    # The 7 fields
    decision:     str    # LONG / SHORT / STAND DOWN
    reason:       str    # one sentence
    conviction:   int    # 0-100
    grade:        str    # A+ / A / B+ / B / C
    size_pct:     int    # 0 / 35 / 50 / 75 / 100
    market_state: str    # "Weekly: X | D1: Y | H4: Z"
    invalidation: str    # one sentence
    regime_log:   str    # "D1 VOLATILE: 4 outcomes (early data)"

    # Supporting context (available but not in brief)
    stand_down:       bool
    override_fired:   bool
    execution_mode:   str
    adx_d1:           float
    adx_h4:           float
    weekly_context:   str
    error:            Optional[str]

    def format(self) -> str:
        """Render the brief as a formatted string."""
        width = 51
        border = "═" * width

        if self.decision == "STAND DOWN":
            decision_line = "STAND ASIDE — conditions not right to trade"
        elif self.decision == "LONG":
            decision_line = "LONG  ▲ — look for buy entries"
        elif self.decision == "SHORT":
            decision_line = "SHORT ▼ — look for sell entries"
        else:
            decision_line = self.decision

        ms = self.market_state

        position_note = (
            "  — do not trade"             if self.size_pct == 0  else
            "  — trade smaller than normal" if self.size_pct < 75 else
            "  — normal position size"
        )

        lines = [
            border,
            f"  {self.instrument.replace('_','/')}  |  "
            f"{self.timestamp}",
            f"  Price: {self.price}  |  "
            f"ATR: {self.atr_pips} pips",
            border,
            f"",
            f"  DECISION     {decision_line}",
            f"",
            f"  REASON       {self._wrap(self.reason, 37, 15)}",
            f"",
            f"  CONFIDENCE   {self.conviction}/100  |  Rating: {self.grade}",
            f"",
            f"  POSITION     {self.size_pct}% of standard size{position_note}",
            f"",
            f"  MARKET STATE {self._wrap(ms, 37, 15)}",
            f"",
            f"  EXIT IF      {self._wrap(self.invalidation, 37, 15)}",
            f"",
            f"  DATA BASIS   {self._wrap(self.regime_log, 37, 15)}",
            f"",
            border,
        ]
        return "\n".join(lines)

    def _wrap(self, text: str, width: int, indent: int) -> str:
        """Wrap text at word boundary with indent for continuation."""
        if len(text) <= width:
            return text
        words = text.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= width:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        pad = " " * indent
        return f"\n{pad}".join(lines)


def _plain(text: str) -> str:
    """
    Translate technical framework terms to plain English.
    Uses word-boundary matching to avoid partial word replacements.
    Applied to reason, market_state, invalidation, and regime_log fields.
    """
    import re

    # Multi-word and longer replacements first (order matters).
    # Safe to use str.replace() — these are specific compound tokens
    # that cannot appear as substrings inside other words.
    multi_word = [
        ("COUNTER_TREND_BOUNCE",   "bouncing against the main trend"),
        ("PULLBACK_IN_UPTREND",    "pulling back inside an uptrend"),
        ("PULLBACK_IN_DOWNTREND",  "pulling back inside a downtrend"),
        ("ESTABLISHED_UPTREND",    "strong uptrend on all timeframes"),
        ("ESTABLISHED_DOWNTREND",  "strong downtrend on all timeframes"),
        ("COUNTER_TREND_OVERRIDE", "reduced-size entry against daily trend"),
        ("PULLBACK_ENTRY",         "pullback entry"),
        ("FADE_EXTREMES",          "trade from range edges"),
        ("REDUCED_MOMENTUM",       "reduced-size momentum trade"),
        ("TRENDING_UP",            "trending up"),
        ("TRENDING_DOWN",          "trending down"),
        ("STAND_DOWN",             "stand aside"),
        ("STAND DOWN",             "stand aside"),
        ("HH_HL",                  "higher highs and higher lows"),
        ("LH_LL",                  "lower highs and lower lows"),
        ("TRANSITIONAL",           "mixed structure"),
        ("CONTINUATION",           "trend continuation"),
    ]

    result = text
    for technical, plain in multi_word:
        result = result.replace(technical, plain)

    # Single-word replacements — word-boundary matching only.
    # \b ensures we match whole tokens, not substrings inside words.
    # "W" removed entirely: too short to replace safely, and the
    # MARKET STATE label "Weekly:" is already plain English.
    word_replacements = [
        (r'\bVOLATILE\b',  "no clear direction"),
        (r'\bRANGING\b',   "moving sideways"),
        (r'\bUPTREND\b',   "uptrend"),
        (r'\bDOWNTREND\b', "downtrend"),
        (r'\bUNKNOWN\b',   "unavailable"),
        (r'\bD1\b',        "daily chart"),
        (r'\bH4\b',        "4-hour chart"),
        (r'\bH1\b',        "1-hour chart"),
        (r'\bM15\b',       "15-minute chart"),
    ]

    for pattern, replacement in word_replacements:
        result = re.sub(pattern, replacement, result)

    return result


def get_decision_brief(instrument: str = "GBP_AUD") -> DecisionBrief:
    """
    Generate a trader-facing decision brief for the given instrument.

    Args:
        instrument: "GBP_AUD" or "GBP_JPY"

    Returns:
        DecisionBrief dataclass with .format() method for display.
        Never raises — returns safe STAND DOWN brief on any error.
    """
    timestamp = datetime.now(timezone.utc).strftime("%a %d %b %Y  %H:%M UTC")

    try:
        # ── 1. Get full regime data ───────────────────────────────────────────
        regime = get_regime(instrument)

        if regime.get("error"):
            return _error_brief(instrument, timestamp,
                                regime.get("error", "Unknown error"))

        # ── 2. Derive direction from regime filter output ─────────────────────
        # make_decision() needs a full multi-layer report (htf, signal stack)
        # to resolve direction and conviction. The brief uses regime-only data,
        # so we derive direction from the filter's execution_mode directly.
        from no_trade_filter import _derive_direction as _regime_dir

        filter_allowed = regime.get("filter_allowed", False)
        exec_mode_raw  = regime.get("execution_mode", "STAND_DOWN")
        d1_raw         = regime.get("regime_d1", "UNKNOWN")
        h4_raw         = regime.get("regime_h4", "UNKNOWN")

        if not filter_allowed:
            direction = "NO TRADE"
        elif exec_mode_raw == "COUNTER_TREND_OVERRIDE":
            direction = "LONG" if "UP" in h4_raw else "SHORT" if "DOWN" in h4_raw else "NO TRADE"
        else:
            _d = _regime_dir(d1_raw, exec_mode_raw)
            direction = _d if _d != "NONE" else "NO TRADE"

        # Conviction maps regime confidence to a 0-100 score.
        # Grade reflects filter conviction: HIGH→A (75), MEDIUM→B+ (55),
        # LOW→B (35), NONE→C (0).
        _conf_map   = {"HIGH": 75, "MEDIUM": 55, "LOW": 35, "NONE": 0}
        filter_conf = regime.get("confidence", "NONE")
        conviction  = _conf_map.get(filter_conf, 0)
        grade       = (
            "A"  if conviction >= 75 else
            "B+" if conviction >= 55 else
            "B"  if conviction >= 35 else
            "C"
        )

        # decision dict used only for _build_reason() fallback
        decision = {}
        stand_down = regime.get("stand_down", True)
        exec_mode  = regime.get("execution_mode", "STAND_DOWN")
        override   = regime.get("override_fired", False)

        # ── 4. Build DECISION field ───────────────────────────────────────────
        if direction in ("NO TRADE", "") or stand_down:
            decision_str = "STAND DOWN"
        elif direction == "LONG":
            decision_str = "LONG"
        elif direction == "SHORT":
            decision_str = "SHORT"
        else:
            decision_str = "STAND DOWN"

        # ── 5. Build REASON ───────────────────────────────────────────────────
        reason = _plain(_build_reason(regime, decision, decision_str, override))

        # ── 6. Build SIZE ─────────────────────────────────────────────────────
        # Size is meaningful only when trading is allowed.
        # Force to 0 on STAND DOWN regardless of filter output.
        if decision_str == "STAND DOWN":
            size_pct = 0
        else:
            size_mult = float(regime.get("filter_size_mult",
                              regime.get("size_mult", 0.0)))
            size_pct  = int(round(size_mult * 100))

        # ── 7. Build MARKET STATE ─────────────────────────────────────────────
        weekly_ctx = regime.get("weekly_context", "UNKNOWN")
        d1_regime  = regime.get("regime_d1", "UNKNOWN")
        h4_regime  = regime.get("regime_h4", "UNKNOWN")
        adx_d1     = float(regime.get("adx", 0.0))
        adx_h4     = float(regime.get("adx_h4", 0.0))

        # _plain() applied only to the technical values — not to the label
        # string itself. "Weekly:" contains uppercase W which _plain() would
        # wrongly expand to "weekly chartly:" if applied to the whole string.
        market_state = (
            f"Weekly: {_plain(weekly_ctx)} | "
            f"Daily chart: {_plain(d1_regime)} "
            f"(trend strength {adx_d1:.0f}/100) | "
            f"4-hour chart: {_plain(h4_regime)} "
            f"(trend strength {adx_h4:.0f}/100)"
        )

        # ── 8. Build INVALIDATION ─────────────────────────────────────────────
        invalidation = _plain(_build_invalidation(regime, decision_str))

        # ── 9. Build REGIME LOG ───────────────────────────────────────────────
        regime_log = _plain(_build_regime_log(d1_regime, instrument))

        return DecisionBrief(
            instrument=instrument,
            timestamp=timestamp,
            price=float(regime.get("current_price", 0.0)),
            atr_pips=float(regime.get("atr_pips", 0.0)),
            decision=decision_str,
            reason=reason,
            conviction=conviction,
            grade=grade,
            size_pct=size_pct,
            market_state=market_state,
            invalidation=invalidation,
            regime_log=regime_log,
            stand_down=stand_down,
            override_fired=override,
            execution_mode=exec_mode,
            adx_d1=adx_d1,
            adx_h4=adx_h4,
            weekly_context=weekly_ctx,
            error=None,
        )

    except Exception as e:
        return _error_brief(instrument, timestamp, str(e))


def _build_reason(regime: dict, decision: dict,
                  decision_str: str, override: bool) -> str:
    """
    Build a one-sentence reason for the decision.
    Always derived from framework data — never hardcoded.
    """
    d1        = regime.get("regime_d1", "UNKNOWN")
    h4        = regime.get("regime_h4", "UNKNOWN")
    adx_d1    = regime.get("adx", 0.0)
    adx_h4    = regime.get("adx_h4", 0.0)
    conflict  = regime.get("timeframe_conflict", False)
    atr_comp  = regime.get("atr_compression", False)
    atr_ratio = regime.get("atr_vs_avg", 1.0)
    structure = regime.get("structure", "TRANSITIONAL")
    weekly    = regime.get("weekly_context", "")
    exec_mode = regime.get("execution_mode", "STAND_DOWN")
    stand_rsn = regime.get("stand_down_reason", "")

    if atr_comp:
        return (f"GBP/JPY ATR compression ({regime.get('atr_vs_avg', 0):.2f}x) "
                f"— pre-intervention coil, both signals historically fail here.")

    if atr_ratio >= 2.0:
        return (f"Extreme ATR spike ({atr_ratio:.1f}x the 20-day average) "
                f"— volatility too high for reliable signals.")

    if conflict:
        conflict_t = regime.get("conflict_type", "")
        if any(x in conflict_t for x in (
            "TRENDING_UP__TRENDING_DOWN",
            "TRENDING_DOWN__TRENDING_UP"
        )):
            return (f"D1 and H4 trending in opposite directions "
                    f"({d1} vs {h4}) — structural disagreement, no edge.")
        elif "RANGING" in conflict_t and "VOLATILE" in conflict_t:
            return (f"Range breaking down — H4 volatile inside D1 "
                    f"range (ADX {adx_d1:.1f}). "
                    f"Wait for resolution before engaging.")
        else:
            return (f"Timeframe conflict ({d1} D1, {h4} H4) — "
                    f"no clean directional edge.")

    if decision_str == "STAND DOWN" and d1 == "VOLATILE":
        atr_comp  = regime.get("atr_compression", False)
        atr_ratio = float(regime.get("atr_vs_avg", 1.0) or 1.0)

        # Cause 1: ATR spike triggered VOLATILE
        spike_mult = float(regime.get("atr_spike_multiplier", 1.2) or 1.2)
        if atr_ratio >= spike_mult:
            return (
                f"ATR spike ({atr_ratio:.1f}x the 20-day average, "
                f"threshold {spike_mult}x) — volatility too high "
                f"for reliable signals regardless of trend strength."
            )

        # Cause 2: ADX exhaustion triggered VOLATILE
        from regime_detection import (
            _ADX_EXHAUSTION_THRESHOLD,
            _ADX_JPY_EXHAUSTION,
        )
        jpy = "JPY" in regime.get("instrument", "")
        exhaustion_thresh = (
            _ADX_JPY_EXHAUSTION if jpy
            else _ADX_EXHAUSTION_THRESHOLD
        )
        if adx_d1 >= exhaustion_thresh:
            return (
                f"ADX {adx_d1} in exhaustion zone (>={exhaustion_thresh}) "
                f"— trend is late-stage, mean reversion probability "
                f"elevated. Do not chase."
            )

        # Cause 3: ADX transition zone (18-25) — no directional edge
        return (
            f"D1 in transition zone (ADX {adx_d1}) — "
            f"no statistical edge. "
            f"H4 {h4} but daily structure has no conviction."
        )

    if decision_str == "STAND DOWN":
        if d1 == "RANGING" and h4 == "VOLATILE":
            return (f"Range breaking down — H4 volatile inside D1 range. "
                    f"Wait for resolution before engaging.")
        if stand_rsn:
            return stand_rsn
        # Filter allowed but decision engine found no tradeable signal
        if exec_mode not in ("STAND_DOWN", "VOLATILE"):
            exec_label = exec_mode.replace("_", " ").title()
            return (
                f"{exec_label} structure identified "
                f"({d1} D1, {h4} H4) but no signal met "
                f"conviction threshold — stand aside until "
                f"setup strengthens."
            )
        return f"{exec_mode.replace('_', ' ').title()} — {d1} D1, {h4} H4."

    if override:
        return (f"Counter-trend override: D1 transition but H4 {h4} "
                f"(ADX {adx_h4:.0f}) aligns with {weekly}. "
                f"Reduced size — unvalidated condition.")

    if exec_mode == "CONTINUATION":
        return (f"Both timeframes aligned {d1.replace('_', ' ').lower()} "
                f"— D1 ADX {adx_d1}, H4 ADX {adx_h4:.0f}. "
                f"Structure: {structure}.")

    if exec_mode == "PULLBACK_ENTRY":
        direction = "long" if "UP" in d1 else "short"
        return (f"D1 trend intact ({d1}), H4 ranging — "
                f"pullback structure. Wait for H4 support/resistance "
                f"to hold before entering {direction}.")

    if exec_mode == "REDUCED_MOMENTUM":
        return (f"H4 trending inside D1 {d1.lower()} — "
                f"suspect move, size reduced. "
                f"Treat as range trade with momentum bias.")

    filter_reason = regime.get("filter_reason", "")
    if filter_reason and "20-week trend" in filter_reason:
        return filter_reason

    # Filter allowed but decision engine found no tradeable signal
    if decision_str == "STAND DOWN" and exec_mode not in (
        "STAND_DOWN", "VOLATILE"
    ):
        exec_label = exec_mode.replace("_", " ").title()
        return (
            f"{exec_label} structure identified "
            f"({d1} D1, {h4} H4) but no signal met "
            f"conviction threshold — stand aside until "
            f"setup strengthens."
        )

    reason = decision.get("reason", "")
    return reason if reason else (
        f"{exec_mode.replace('_',' ').title()} — "
        f"{d1} D1, {h4} H4."
    )


def _build_invalidation(regime: dict, decision_str: str) -> str:
    """
    Build a one-sentence invalidation condition.
    Always derived from actual threshold values — never generic text.
    """
    from regime_detection import (
        _ADX_RANGING_THRESHOLD,
        _ADX_TRANSITION_HIGH,
        _ADX_EXHAUSTION_THRESHOLD,
    )

    d1        = regime.get("regime_d1", "UNKNOWN")
    h4        = regime.get("regime_h4", "UNKNOWN")
    adx_d1    = regime.get("adx", 0.0)
    adx_h4    = regime.get("adx_h4", 0.0)
    exec_mode = regime.get("execution_mode", "STAND_DOWN")
    structure = regime.get("structure", "TRANSITIONAL")
    pair      = regime.get("pair", "GBP/AUD")

    if decision_str == "STAND DOWN":
        if d1 == "VOLATILE":
            return (f"D1 ADX crosses {_ADX_TRANSITION_HIGH} with confirmed "
                    f"H4 structure holding — revisit then.")
        if d1 == "RANGING":
            return (f"D1 ADX drops below {_ADX_RANGING_THRESHOLD} "
                    f"or H4 resolves to clean trend — revisit then.")
        if d1 == "TRENDING_UP":
            return (f"D1 structure breaks — price closes below most "
                    f"recent confirmed swing low.")
        if d1 == "TRENDING_DOWN":
            return (f"D1 structure breaks — price closes above most "
                    f"recent confirmed swing high.")
        return "Regime resolves to clean trending or ranging state."

    if exec_mode == "CONTINUATION":
        if "UP" in d1:
            sl = regime.get("latest_sl")
            if sl:
                return (f"Price closes below confirmed swing low at "
                        f"{sl:.4f} — trend structure broken.")
            return "Price closes below most recent confirmed swing low."
        else:
            sh = regime.get("latest_sh")
            if sh:
                return (f"Price closes above confirmed swing high at "
                        f"{sh:.4f} — trend structure broken.")
            return "Price closes above most recent confirmed swing high."

    if exec_mode == "PULLBACK_ENTRY":
        if "UP" in d1:
            return (f"H4 breaks below range support before entry — "
                    f"pullback extends into trend reversal territory.")
        return (f"H4 breaks above range resistance before entry — "
                f"pullback extends into trend reversal territory.")

    if exec_mode == "COUNTER_TREND_OVERRIDE":
        return (f"H4 ADX drops below {_ADX_TRANSITION_HIGH} or "
                f"weekly context shifts — override conditions no longer met.")

    return "Regime classification changes — re-run framework before re-entry."


def _build_regime_log(d1_regime: str, instrument: str) -> str:
    """
    Pull outcome count for current D1 regime from the logger.
    Returns a plain-English sample count with calibration note.
    """
    try:
        acc = get_regime_accuracy(instrument=instrument, min_samples=1)
        if d1_regime in acc:
            data = acc[d1_regime]
            n    = data["n"]
            pct  = f"{data['accuracy']:.0%}"
            if n < 30:
                note = "early data — treat with caution"
            elif n < 60:
                note = "developing — more data needed"
            elif data.get("needs_review"):
                note = "REVIEW FLAG — accuracy below threshold"
            else:
                note = "validated"
            return (f"D1 {d1_regime}: {n} outcomes logged, "
                    f"{pct} accuracy ({note})")
        return f"D1 {d1_regime}: no outcomes logged yet (new regime)"
    except Exception:
        return "Regime log unavailable"


def _error_brief(instrument: str, timestamp: str,
                 error: str) -> DecisionBrief:
    """Return a safe STAND DOWN brief when any error occurs."""
    return DecisionBrief(
        instrument=instrument,
        timestamp=timestamp,
        price=0.0,
        atr_pips=0.0,
        decision="STAND DOWN",
        reason=f"Framework error — do not trade: {error[:60]}",
        conviction=0,
        grade="C",
        size_pct=0,
        market_state="Unavailable",
        invalidation="Resolve framework error before re-running.",
        regime_log="Unavailable",
        stand_down=True,
        override_fired=False,
        execution_mode="STAND_DOWN",
        adx_d1=0.0,
        adx_h4=0.0,
        weekly_context="UNKNOWN",
        error=error,
    )


if __name__ == "__main__":
    import sys
    from entry_confirmation import get_entry_brief

    instruments = sys.argv[1:] if len(sys.argv) > 1 \
                  else ["GBP_AUD", "GBP_JPY"]

    for inst in instruments:
        brief = get_decision_brief(inst)
        print(brief.format())

        if brief.decision in ("LONG", "SHORT"):
            entry = get_entry_brief(inst, brief.decision)
            print(entry.precision_brief)

        print()
