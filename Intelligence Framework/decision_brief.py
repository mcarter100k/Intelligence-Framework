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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict

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
    error:                Optional[str]
    session_delta:        Optional[Dict]  = None
    live_bar_age:         Optional[float] = None
    live_bar_in_progress: Optional[bool]  = None
    market_open:          bool            = True
    market_note:          str             = ""
    narrative:            str             = ""   # THE FULL PICTURE section

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
        ]
        # Market status / bar freshness — inserted between Price/ATR line and border
        if not self.market_open and self.market_note:
            lines.insert(3, f"  {self.market_note}")
        elif self.market_open and self.live_bar_age is not None:
            if self.live_bar_in_progress:
                lines.insert(3, f"  Daily bar in progress — analysis "
                                f"uses last closed bar")
            else:
                # Staleness measured from bar CLOSE (open + 24h for D1), not
                # open. A completed daily bar's OPEN is always >24h old once the
                # next session begins, so the old "age > 30h" test false-alarmed
                # every weekday morning. We warn only when the newest complete
                # bar is genuinely behind the most recent expected close (a real
                # feed problem), accounting for weekends.
                from datetime import datetime, timezone, timedelta
                _now       = datetime.now(timezone.utc)
                _last_open = _now - timedelta(hours=self.live_bar_age)
                _last_close = _last_open + timedelta(hours=24)
                _expected  = _last_expected_d1_close(_now, _last_open.hour)
                if _last_close < _expected - timedelta(hours=6):
                    _lag = (_expected - _last_close).total_seconds() / 3600.0
                    lines.insert(3, f"  ⚠ D1 feed looks stale — newest complete "
                                    f"bar is ~{_lag:.0f}h behind the expected "
                                    f"close. Check the data feed.")

        # Session delta line — inserted between MARKET STATE and EXIT IF
        if self.session_delta:
            summary = _plain(self.session_delta.get("summary", ""))
            if summary:
                if ("CONDITIONS IMPROVED" in summary or
                        "CONDITIONS DETERIORATED" in summary or
                        "Regime changed" in summary):
                    lines.append(f"  ⚡ SESSION  {self._wrap(summary, 37, 13)}")
                else:
                    lines.append(f"  SESSION    {self._wrap(summary, 37, 13)}")
                lines.append(f"")
        lines += [
            f"  EXIT IF      {self._wrap(self.invalidation, 37, 15)}",
            f"",
            f"  DATA BASIS   {self._wrap(self.regime_log, 37, 15)}",
            f"",
        ]
        # THE FULL PICTURE — plain-English narrative (the 10-second layer above
        # is unchanged; this is the read-it-if-you-want layer).
        if self.narrative:
            lines += [
                border,
                f"  THE FULL PICTURE",
                f"",
                f"  {self._wrap(self.narrative, 49, 2)}",
                f"",
            ]
        lines.append(border)
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
        # ── Jargon sweep (display layer only) — banned tokens → plain English ──
        ("pivot structure",        "price structure"),
        ("HH/HL",                  "stair-step pattern of higher highs and higher lows"),
        ("LH/LL",                  "stair-step pattern of lower highs and lower lows"),
    ]

    result = text
    for technical, plain in multi_word:
        result = result.replace(technical, plain)

    # Numbered jargon: "ADX 26.8" → "trend strength 26.8/100";
    # "ATR ratio 1.2x" → "volatility at 1.2 times its normal level".
    result = re.sub(r'\bADX\s+(\d+(?:\.\d+)?)', r'trend strength \1/100', result)
    result = re.sub(r'\bATR ratio\s+(\d+(?:\.\d+)?)\s*x?',
                    r'volatility at \1 times its normal level', result)

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
        # residual jargon-sweep tokens (standalone forms)
        (r'\bADX\b',       "trend strength"),
        (r'\bATR ratio\b', "volatility level"),
        (r'\bpivot\b',     "price structure"),
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

        # ── 1b. Log session snapshot and get intraday delta ───────────────────
        from session_memory import log_session_snapshot, get_session_delta
        log_session_snapshot(regime, instrument,
                             market_open=regime.get("market_open", True))
        session_delta = get_session_delta(instrument)

        # ── 2. Derive direction, conviction, grade from official decision path ──
        from official_decision import get_official_decision
        _official  = get_official_decision(regime)
        direction  = _official["direction"]
        conviction = _official["conviction"]
        grade      = _official["grade"]

        # decision dict used only for _build_reason() fallback
        decision   = {}
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
            size_pct = int(round(_official["size_mult"] * 100))

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

        # ── 10. Build THE FULL PICTURE narrative ──────────────────────────────
        try:
            from shadow_signals import latest_pending_signal
            from regime_detection import PAIRS as _PAIRS
            _pip = _PAIRS[instrument].pip_size if instrument in _PAIRS else 0.0001
            narrative = _build_narrative(
                regime, decision_str, session_delta, invalidation,
                latest_pending_signal(instrument), _pip)
        except Exception:
            narrative = ""

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
            session_delta=session_delta,
            live_bar_age=regime.get("last_closed_bar_age_hours"),
            live_bar_in_progress=regime.get("live_bar_in_progress"),
            market_open=regime.get("market_open", True),
            market_note=regime.get("market_note", ""),
            narrative=narrative,
        )

    except Exception as e:
        return _error_brief(instrument, timestamp, str(e))


def _last_expected_d1_close(now, close_hour: int):
    """Most recent UTC time a complete D1 bar should have closed.

    OANDA D1 bars close at `close_hour` UTC (21:00 in summer / 22:00 in winter,
    derived from the last bar's own open hour) on weekday sessions. After
    Friday's close the next is Monday's, so Sat/Sun have no D1 close — we step
    back over the weekend so a fresh Monday-morning brief is not flagged stale.
    """
    from datetime import timedelta
    c = now.replace(hour=close_hour, minute=0, second=0, microsecond=0)
    if c > now:
        c -= timedelta(days=1)
    while c.weekday() >= 5:      # 5 = Saturday, 6 = Sunday
        c -= timedelta(days=1)
    return c


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

        # Cause 3a: ADX 25-32 — in the trending band, but pivot structure has
        # not confirmed a direction (Problem 2 gate). This is NOT the 18-25
        # transition zone; say so precisely or the brief lies about the cause.
        from regime_detection import _ADX_TRANSITION_HIGH  # 25
        if (float(adx_d1 or 0) >= _ADX_TRANSITION_HIGH
                and structure not in ("UPTREND", "DOWNTREND")):
            return (
                f"Daily chart trend strength is {float(adx_d1):.0f}/100 — in the "
                f"trending band — but price structure has not confirmed a "
                f"direction yet (no clean stair-step pattern of higher highs and "
                f"higher lows, or lower highs and lower lows). 4-hour chart {h4}. "
                f"Standing aside until structure confirms."
            )

        # Cause 3b: ADX 18-25 — genuine no-edge transition zone
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
            # When trend strength is ALREADY above the trending threshold, the
            # watch condition is price STRUCTURE confirming — not an ADX cross
            # that is already behind us (the sibling of the REASON-label bug).
            if float(adx_d1 or 0) >= _ADX_TRANSITION_HIGH:
                return ("Daily price structure confirms a direction — a clean "
                        "stair-step pattern of higher highs and higher lows, or "
                        "lower highs and lower lows — with the 4-hour chart "
                        "aligned. Revisit then.")
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

    n < 20 : count only — no percentage (not yet meaningful)
    n 20-59 : percentage shown, labelled 'developing'
    n 60-149: 'flag threshold' — percentage shown, may have flag marker
    n 150+  : 'validated sample' — percentage shown, may have revise marker
    """
    try:
        acc = get_regime_accuracy(instrument=instrument)
        if d1_regime in acc:
            data = acc[d1_regime]
            n    = data["n"]
            if n < 20:
                return (f"D1 {d1_regime}: {n} outcomes logged "
                        f"(early data — accuracy not yet meaningful)")
            pct = f"{data['accuracy']:.0%}"
            if n < 60:
                note = "developing"
            elif n < 150:
                note = "flag threshold"
            else:
                note = "validated sample"
            if data.get("actionable"):
                note += " — REVISE thresholds"
            elif data.get("flagged"):
                note += " — FLAG, watch closely"
            return (f"D1 {d1_regime}: {n} outcomes logged, "
                    f"{pct} accuracy ({note})")
        return f"D1 {d1_regime}: no outcomes logged yet (new regime)"
    except Exception:
        return "Regime log unavailable"


_DIR_WORDS = {
    "TRENDING_UP":   "trending up",
    "TRENDING_DOWN": "trending down",
    "RANGING":       "moving sideways",
    "VOLATILE":      "choppy with no clear direction",
}
_STRUCT_WORDS = {
    "UPTREND":   "a confirmed stair-step pattern of higher highs and higher lows",
    "DOWNTREND": "a confirmed stair-step pattern of lower highs and lower lows",
}


def _dir_sign(regime_label: str) -> int:
    if "UP" in regime_label:   return 1
    if "DOWN" in regime_label: return -1
    return 0


def _build_narrative(regime: dict, decision_str: str, session_delta: dict = None,
                     invalidation: str = "", shadow_pending: dict = None,
                     pip: float = 0.0001) -> str:
    """THE FULL PICTURE — a plain-English paragraph built entirely from framework
    data (template + live values, never hardcoded scenario prose)."""
    d1     = regime.get("regime_d1", "UNKNOWN")
    h4     = regime.get("regime_h4", "UNKNOWN")
    adx_d1 = float(regime.get("adx", 0) or 0)
    adx_h4 = float(regime.get("adx_h4", 0) or 0)
    struct = regime.get("structure", "TRANSITIONAL")
    weekly = regime.get("weekly_context", "UNKNOWN")
    lt     = regime.get("lt_trend", "RANGING")
    price  = float(regime.get("current_price", 0) or 0)
    atr_r  = float(regime.get("atr_vs_avg", 1.0) or 1.0)
    comp   = regime.get("atr_compression", False)

    d1_word = _DIR_WORDS.get(d1, "unclear")
    h4_word = _DIR_WORDS.get(h4, "unclear")
    struct_word = _STRUCT_WORDS.get(struct, "no confirmed pattern yet")

    # rising / falling from the session delta, when available
    d1_rf = ""
    if session_delta and session_delta.get("adx_d1_delta") is not None:
        dlt = session_delta["adx_d1_delta"]
        d1_rf = " and rising" if dlt > 1 else " and falling" if dlt < -1 else " and steady"

    parts = []
    # 1. weekly  2. daily  3. 4-hour
    parts.append(f"The weekly chart shows {_plain(weekly)}.")
    parts.append(f"The daily chart is {d1_word}, trend strength "
                 f"{adx_d1:.0f}/100{d1_rf}, with {struct_word}.")
    parts.append(f"The 4-hour chart is {h4_word} (trend strength {adx_h4:.0f}/100).")

    # 4/5/7. why the decision follows + what to watch (trade case handled here)
    if decision_str in ("LONG", "SHORT"):
        side = "buying" if decision_str == "LONG" else "selling"
        parts.append(f"All three timeframes line up, which is what produced this "
                     f"{decision_str} signal — {side} in the direction the weekly, "
                     f"daily and 4-hour agree on.")
        parts.append(f"The stop marks where that idea would be proven wrong; a "
                     f"close through it means the setup has failed and the trade "
                     f"is over.")
    else:
        w_sign = (1 if ("UPTREND" in weekly or lt == "UPTREND") else
                  -1 if ("DOWNTREND" in weekly or "BOUNCE" in weekly or lt == "DOWNTREND")
                  else 0)
        signs = {s for s in (w_sign, _dir_sign(d1), _dir_sign(h4)) if s != 0}
        if comp:
            parts.append("Volatility is compressed below its normal level, which "
                         "historically precedes a fake move, so the framework waits.")
        elif atr_r >= 2.0:
            parts.append("Volatility has spiked far above its normal level — too "
                         "high for a reliable read, so the framework stands aside.")
        elif len(signs) > 1:
            parts.append("These timeframes disagree, so any direction you pick "
                         "fights one of them — the framework stands aside rather "
                         "than force a trade the whole picture doesn't support.")
        else:
            parts.append("The pieces don't line up clearly enough to justify risk, "
                         "so the framework stands aside.")
        if invalidation:
            parts.append("This changes when " + invalidation[0].lower() + invalidation[1:])

    # 6. a live/pending shadow signal, if any (logged, not traded). Honest about
    #    a stopped-out idea: past the stop = "stopped in live terms", NOT pips
    #    "underwater" (which would narrate a dead loss as an open position). The
    #    grader still computes the real outcome from bar data at the horizon.
    if shadow_pending:
        d, entry = shadow_pending["direction"], shadow_pending["entry"]
        stop = shadow_pending.get("stop")
        base = (f"Separately, the framework is watching the "
                f"{shadow_pending['candidate_id']} candidate: {d} entered at {entry}")
        stopped = (price and stop is not None and
                   ((price <= stop) if d == "LONG" else (price >= stop)))
        if stopped:
            stop_pips = abs(entry - stop) / pip
            parts.append(f"{base}, stopped in live terms at {stop} "
                         f"(-{stop_pips:.0f} pips, -1.0R) — final grading at the "
                         f"30-bar horizon. Logged for evidence, NOT traded.")
        elif price:
            diff = ((price - entry) / pip) if d == "LONG" else ((entry - price) / pip)
            standing = (f"currently about {diff:.0f} pips onside" if diff >= 0
                        else f"currently about {abs(diff):.0f} pips underwater")
            parts.append(f"{base}, {standing} — logged for evidence, NOT traded.")
        else:
            parts.append(f"{base}, being tracked — logged for evidence, NOT traded.")

    return " ".join(p for p in parts if p)


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

        # Shadow signals — logged, never traded. Prints a clearly-marked section
        # ONLY if a candidate fired on the last complete H4 bar (zero noise
        # otherwise). Evidence accumulates for the eventual honest validation.
        try:
            from shadow_signals import run_and_report
            run_and_report(inst)
        except Exception:
            pass

        print()
