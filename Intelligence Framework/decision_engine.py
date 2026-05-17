"""
decision_engine.py

Capstone decision layer for the GBP/AUD intelligence framework.

Transforms the aggregated market report into a single explicit decision:
  DIRECTION  : LONG | SHORT | NO TRADE
  GRADE      : A+ / A / B+ / B / C
  CONVICTION : 0-100, regime-weighted (not static)
  ENTRY      : exact condition required before executing
  INVALIDATION: concrete conditions that flip this view

Three things this adds that the existing report layer does not have:
  1. Direction is first-class — the grade means nothing without it
  2. Weights shift with the market regime — trending markets weight
     structure higher; ranging markets weight levels higher;
     volatile sessions de-weight technicals entirely
  3. Signal conflicts are explicitly named and separated from supporters
"""

from __future__ import annotations
from typing import Dict, List, Tuple

from risk_config import get_grade
from utils import pacific_offset, hours_until

# Load calibrated weights at startup if available — falls back to defaults silently
try:
    from calibrate_weights import load_calibrated_weights as _load_cal
    _calibrated = _load_cal()
except Exception:
    _calibrated = None


# ── Regime-aware weight tables ────────────────────────────────────────────────
# Logic: in a trend, structure dominates.
#        in a range, price levels dominate.
#        in volatility, news and macro dominate — technicals lie.

_LAYER_MAP: Dict[str, str] = {
    "Currency Strength":      "strength",
    "Big Picture Trend":      "htf",
    "Interest Rate Signal":   "rates",   # legacy fallback
    "Carry Signal":           "rates",
    "Rate Path Signal":       "rates",
    "Price Level Signal":     "liquidity",
    "Global Market Signal":   "cross",
    "Hedge Fund Positioning": "cot",
    "Economic News":          "news",
    "Leg Decomposition":      "legs",
}

# Which tier each signal category belongs to.
# Structural = the multi-week directional case
# Tactical   = is now a good time to act on it
# Execution  = is this the right moment to enter
_TIER_MAP: Dict[str, str] = {
    "htf":      "structural",
    "rates":    "structural",
    "cot":      "structural",
    "macro":    "structural",
    "strength": "tactical",
    "cross":    "tactical",
    "legs":     "tactical",
    "value":    "tactical",
    "regime":   "tactical",
    "liquidity":"execution",
    "news":     "execution",
    "session":  "execution",
    "intraday": "execution",
}

_REGIME_WEIGHTS: Dict[str, Dict[str, float]] = {
    "TRENDING_UP": {
        "htf": 0.30, "strength": 0.18, "liquidity": 0.12,
        "cross": 0.08, "news": 0.07, "rates": 0.04, "cot": 0.03,
        "legs": 0.10, "value": 0.04, "regime": 0.04,
    },
    "TRENDING_DOWN": {
        "htf": 0.30, "strength": 0.18, "liquidity": 0.12,
        "cross": 0.08, "news": 0.07, "rates": 0.04, "cot": 0.03,
        "legs": 0.10, "value": 0.04, "regime": 0.04,
    },
    "RANGING": {
        "liquidity": 0.28, "strength": 0.16, "htf": 0.12,
        "cross": 0.10, "news": 0.09, "rates": 0.04, "cot": 0.03,
        "legs": 0.09, "value": 0.06, "regime": 0.03,
    },
    "VOLATILE": {
        "news": 0.30, "cross": 0.20, "liquidity": 0.16,
        "strength": 0.10, "htf": 0.05, "rates": 0.02, "cot": 0.01,
        "legs": 0.10, "value": 0.03, "regime": 0.03,
    },
}
_DEFAULT_WEIGHTS: Dict[str, float] = {
    "htf": 0.26, "strength": 0.18, "liquidity": 0.16,
    "cross": 0.09, "news": 0.08, "rates": 0.04, "cot": 0.03,
    "legs": 0.09, "value": 0.04, "regime": 0.03,
}

# ── Trade-type weight multipliers ─────────────────────────────────────────────
# Applied on top of regime weights.  Values are per-signal-key multipliers.
# Intraday: boost execution signals, suppress structural slow signals.
# Swing: boost structural signals, suppress execution noise.
_TRADE_TYPE_MULTS: Dict[str, Dict[str, float]] = {
    "intraday": {
        "htf":      0.40, "rates":    0.40, "cot":      0.40, "macro":    0.40,
        "strength": 1.00, "cross":    0.80, "legs":     0.80, "value":    0.80,
        "regime":   1.00,
        "liquidity":1.80, "news":     1.50, "session":  1.80, "intraday": 1.80,
    },
    "swing": {
        "htf":      1.60, "rates":    1.60, "cot":      1.60, "macro":    1.60,
        "strength": 1.20, "cross":    1.20, "legs":     1.20, "value":    1.00,
        "regime":   0.80,
        "liquidity":0.60, "news":     0.60, "session":  0.50, "intraday": 0.50,
    },
    "auto": {},   # empty = no multiplier applied, regime weights used as-is
}

# Apply calibrated weights where available (overrides the defaults above)
if _calibrated:
    for _r, _w in _calibrated.items():
        if _r in _REGIME_WEIGHTS:
            _REGIME_WEIGHTS[_r] = _w


# ── Regime-aware scoring ──────────────────────────────────────────────────────

def _regime_score(
    signals: List[Dict], regime: str, trade_type: str = "auto"
) -> Tuple[int, str]:
    """
    Re-score the signal list with regime-appropriate weights, optionally
    multiplied by trade-type biases (intraday / swing / auto).

    Returns (conviction_0_to_100, direction_BULLISH_BEARISH_NEUTRAL).
    """
    weights      = _REGIME_WEIGHTS.get(regime, _DEFAULT_WEIGHTS)
    type_mults   = _TRADE_TYPE_MULTS.get(trade_type, {})
    weighted_sum = 0.0
    weight_used  = 0.0

    for s in signals:
        if not s.get("available"):
            continue
        key = _LAYER_MAP.get(s["layer"])
        if not key:
            continue
        w   = weights.get(key, 0.0) * type_mults.get(key, 1.0)
        raw = 0.0 if s.get("stale") else s.get("raw_score", 0.0)
        weighted_sum += raw * w
        weight_used  += w

    if weight_used == 0:
        return 10, "NEUTRAL"

    norm       = weighted_sum / weight_used
    conviction = int(min(95, max(10, abs(norm))))
    direction  = "BULLISH" if weighted_sum > 8 else "BEARISH" if weighted_sum < -8 else "NEUTRAL"
    return conviction, direction


# ── Three-tier conviction scoring ────────────────────────────────────────────

def _tier_scores(
    signals:       List[Dict],
    regime:        str,
    direction:     str,
    overall_bias:  str,
    macro_opposes: bool,
    macro_aligns:  bool,
    macro_mag:     int,
    session_label: str,
    is_wrong_session: bool,
    adx:           float,
    fakeout_aligns:   bool,
    fakeout_opposes:  bool,
    sweep_conf:    bool,
    news_blocked:  bool,
    range_pct:     float,
    trade_type:    str = "auto",
) -> Dict:
    """
    Compute per-tier conviction scores (0–100) and per-signal verdicts.

    Returns:
      structural_score  — HTF trend, rates, COT, macro
      tactical_score    — strength, cross-market, legs, value, regime
      execution_score   — levels/sweep, session, intraday, news
      tier_signals      — dict of tier → list of {name, verdict, note}
    """
    weights    = _REGIME_WEIGHTS.get(regime, _DEFAULT_WEIGHTS)
    type_mults = _TRADE_TYPE_MULTS.get(trade_type, {})
    dir_bias = (
        "BULLISH" if direction == "LONG"
        else "BEARISH" if direction == "SHORT"
        else overall_bias if overall_bias in ("BULLISH", "BEARISH")
        else None
    )

    # Per-tier accumulators: (weighted_score, weight_used)
    tier_acc: Dict[str, List[float]] = {
        "structural": [0.0, 0.0],
        "tactical":   [0.0, 0.0],
        "execution":  [0.0, 0.0],
    }
    tier_signals: Dict[str, List[Dict]] = {
        "structural": [], "tactical": [], "execution": []
    }

    def _verdict(bias: str) -> str:
        if not dir_bias:
            return "neutral"
        if bias == dir_bias:
            return "confirm"
        if bias in ("NEUTRAL", "UNKNOWN", ""):
            return "neutral"
        return "conflict"

    # Score signals from signal_summary list
    for s in signals:
        key  = _LAYER_MAP.get(s["layer"])
        tier = _TIER_MAP.get(key, "tactical") if key else "tactical"
        w    = (weights.get(key, 0.0) * type_mults.get(key, 1.0)) if key else 0.0
        raw  = 0.0 if s.get("stale") else s.get("raw_score", 0.0)

        if not s.get("available"):
            tier_signals[tier].append({"name": s["layer"], "verdict": "no_data", "note": "No data"})
            continue

        tier_acc[tier][0] += raw * w
        tier_acc[tier][1] += w
        v = _verdict(s.get("bias", "NEUTRAL"))
        note = s.get("summary", "")
        if s.get("stale"):
            note = f"[STALE — score zeroed]  {note}"
        tier_signals[tier].append({"name": s["layer"], "verdict": v, "note": note})

    # Add macro as structural signal
    if macro_aligns and macro_mag >= 4:
        tier_acc["structural"][0] += macro_mag * weights.get("htf", 0.05)
        tier_acc["structural"][1] += weights.get("htf", 0.05)
        tier_signals["structural"].append({"name": "Macro", "verdict": "confirm",
                                           "note": f"Macro quadrant aligned (+{macro_mag})"})
    elif macro_opposes and macro_mag >= 4:
        tier_acc["structural"][0] -= macro_mag * weights.get("htf", 0.05)
        tier_acc["structural"][1] += weights.get("htf", 0.05)
        tier_signals["structural"].append({"name": "Macro", "verdict": "conflict",
                                           "note": f"Macro quadrant opposes (-{macro_mag})"})

    # Add execution signals not in the signal list
    # These use the session/intraday multipliers from trade_type
    _sm  = type_mults.get("session",   1.0)
    _im  = type_mults.get("intraday",  1.0)

    # Session
    if is_wrong_session:
        tier_acc["execution"][0] -= 40 * 0.12 * _sm
        tier_acc["execution"][1] += 0.12 * _sm
        tier_signals["execution"].append({"name": "Session", "verdict": "conflict",
                                          "note": f"{session_label} — wrong session for GBP/AUD"})
    else:
        tier_acc["execution"][0] += 40 * 0.12 * _sm
        tier_acc["execution"][1] += 0.12 * _sm
        tier_signals["execution"].append({"name": "Session", "verdict": "confirm",
                                          "note": f"{session_label} — active GBP/AUD window"})

    # Intraday fakeout
    if fakeout_aligns:
        tier_acc["execution"][0] += 50 * 0.10 * _im
        tier_acc["execution"][1] += 0.10 * _im
        tier_signals["execution"].append({"name": "Intraday", "verdict": "confirm",
                                          "note": "Fakeout confirmed — institutional signal"})
    elif fakeout_opposes:
        tier_acc["execution"][0] -= 50 * 0.10 * _im
        tier_acc["execution"][1] += 0.10 * _im
        tier_signals["execution"].append({"name": "Intraday", "verdict": "conflict",
                                          "note": "Fakeout opposes direction"})

    # Sweep
    if sweep_conf:
        tier_acc["execution"][0] += 40 * 0.08
        tier_acc["execution"][1] += 0.08
        tier_signals["execution"].append({"name": "Sweep", "verdict": "confirm",
                                          "note": "Liquidity sweep confirmed"})

    # News blocker
    if news_blocked:
        tier_acc["execution"][0] -= 60 * 0.10
        tier_acc["execution"][1] += 0.10
        tier_signals["execution"].append({"name": "News", "verdict": "conflict",
                                          "note": "High-impact event nearby — blocked"})

    # Range exhaustion (only meaningful for intraday)
    if range_pct > 80:
        tier_acc["execution"][0] -= 20 * 0.06 * _im
        tier_acc["execution"][1] += 0.06 * _im
        tier_signals["execution"].append({"name": "Range", "verdict": "conflict",
                                          "note": f"Range {range_pct:.0f}% used — little room left"})
    elif range_pct > 0:
        tier_signals["execution"].append({"name": "Range", "verdict": "neutral",
                                          "note": f"Range {range_pct:.0f}% used"})

    def _to_score(acc: List[float]) -> int:
        if acc[1] == 0:
            return 50  # no data = neutral
        norm = acc[0] / acc[1]  # roughly -100 to +100
        return int(min(95, max(5, (norm + 100) / 2)))

    return {
        "structural_score": _to_score(tier_acc["structural"]),
        "tactical_score":   _to_score(tier_acc["tactical"]),
        "execution_score":  _to_score(tier_acc["execution"]),
        "tier_signals":     tier_signals,
    }


# ── Direction resolution ──────────────────────────────────────────────────────

_HTF_STRUCTURAL_DIR: Dict[str, str] = {
    "ESTABLISHED_DOWNTREND": "SHORT",
    "ESTABLISHED_UPTREND":   "LONG",
    "PULLBACK_IN_UPTREND":   "LONG",
}


def _resolve_direction(
    htf_context:  str,
    lt_trend:     str,
    overall_bias: str,
    live_dom:     str,
    struct_dom:   str,
    conflict:     bool,
    sweep_down:   bool,
    sweep_up:     bool,
    conviction:   int,
) -> Tuple[str, str, bool]:
    """
    Derives the primary trade direction from all available context.

    Priority order:
      1. Hard structural direction (established trend, pullback, bounce)
      2. Confirmed liquidity sweep (overrides weak/absent structural signal)
      3. Strong live signal alignment in a ranging market

    Returns (direction, plain_reason, is_counter_trend).
    """
    bias_to_dir  = {"BULLISH": "LONG", "BEARISH": "SHORT"}
    is_counter   = htf_context == "COUNTER_TREND_BOUNCE"

    # COUNTER_TREND_BOUNCE direction depends on which trend the bounce is inside
    if htf_context == "COUNTER_TREND_BOUNCE":
        structural_dir: str | None = "SHORT" if lt_trend == "DOWNTREND" else "LONG"
    else:
        structural_dir = _HTF_STRUCTURAL_DIR.get(htf_context)

    # Sweep overrides when structural direction is absent or the same side
    if sweep_down and not sweep_up:
        if structural_dir in (None, "LONG"):
            return "LONG", "Liquidity sweep below confirmed — bullish reversal signal", False
    if sweep_up and not sweep_down:
        if structural_dir in (None, "SHORT"):
            return "SHORT", "Liquidity sweep above confirmed — bearish reversal signal", False

    if structural_dir:
        bias_aligned = (
            (structural_dir == "LONG"  and overall_bias == "BULLISH") or
            (structural_dir == "SHORT" and overall_bias == "BEARISH")
        )
        if bias_aligned and not conflict:
            return structural_dir, f"HTF {htf_context} + signals aligned", is_counter
        if conviction >= 45:
            note = f"HTF {htf_context} — intraday conflict noted" if conflict else f"HTF {htf_context}"
            return structural_dir, note, is_counter

    # Ranging with clear live agreement
    if overall_bias in ("BULLISH", "BEARISH") and conviction >= 55:
        return bias_to_dir[overall_bias], "Ranging — following live signal alignment", False

    return "NO TRADE", "Insufficient signal alignment for a directional call", False


# ── Setup quality ─────────────────────────────────────────────────────────────

def _setup_quality(conviction: int, conflict: bool, sweep: bool, adx: float,
                   fakeout_confirmed: bool = False) -> str:
    score = 0
    if not conflict:       score += 2
    if sweep:              score += 2
    if fakeout_confirmed:  score += 2  # confirmed institutional stop hunt
    if conviction >= 60:   score += 2
    if adx > 25:           score += 1
    score += 1  # event_risk already handled before this is called
    if score >= 7: return "HIGH"
    if score >= 4: return "MEDIUM"
    if score >= 2: return "LOW"
    return "DO NOT TRADE"


# ── Invalidation conditions ───────────────────────────────────────────────────

def _build_invalidation_conditions(
    direction:  str,
    htf:        Dict,
    liquidity:  Dict,
    value:      Dict,
    sweep_down: bool,
    sweep_up:   bool,
) -> List[str]:
    """
    Returns a list of concrete, price-specific conditions that would prove
    the current directional view wrong. Deliberately price-anchored — not vague.
    """
    out           = []
    ma50          = htf.get("ma50", "")
    ctx           = htf.get("context", "")
    wk_high       = liquidity.get("wk_high") or liquidity.get("pwh", "")
    wk_low        = liquidity.get("wk_low")  or liquidity.get("pwl", "")
    near_lvl      = liquidity.get("nearest_pool", "")
    fib_382       = str(htf.get("fib_levels", {}).get("38.2", "")) if htf.get("fib_levels") else ""
    swing_high    = htf.get("nearest_daily_swing_high")
    swing_low     = htf.get("nearest_daily_swing_low")
    struct_type   = htf.get("daily_structure_type", "")

    if direction == "LONG":
        if sweep_down and near_lvl:
            out.append(f"Daily close BELOW swept low ({near_lvl}) — sweep failed, bias flips short")
        if swing_low:
            out.append(
                f"Daily close below last daily swing low ({swing_low}) — "
                f"bullish market structure (HH/HL) broken"
            )
        elif wk_low:
            out.append(f"Daily close below this week's low ({wk_low}) — lower low destroys bullish structure")
        if ma50:
            out.append(f"Price holds below MA50 ({ma50}) — structural support broken")
        out.append("AUD outperforms GBP for 2+ consecutive sessions — strength thesis fails")

    elif direction == "SHORT":
        if sweep_up and near_lvl:
            out.append(f"Daily close ABOVE swept high ({near_lvl}) — sweep failed, bias flips long")
        if ctx == "COUNTER_TREND_BOUNCE" and fib_382:
            out.append(f"Daily close above 38.2% Fibonacci ({fib_382}) — bounce extending, not exhausting")
        if swing_high:
            out.append(
                f"Daily close above last daily swing high ({swing_high}) — "
                f"bearish market structure (LH/LL) broken"
            )
        elif wk_high:
            out.append(f"Daily close above this week's high ({wk_high}) — structure broken to upside")
        if ma50:
            out.append(f"Daily close above MA50 ({ma50}) — downtrend structure failing")
        out.append("GBP outperforms AUD for 2+ consecutive sessions — strength thesis fails")

    return out or ["Key weekly level breaks on a daily close — re-run full framework"]


# ── Entry condition ───────────────────────────────────────────────────────────

def _build_entry_condition(
    direction:   str,
    htf_context: str,
    lt_trend:    str,
    sweep_down:  bool,
    sweep_up:    bool,
    value:       Dict,
    liquidity:   Dict,
    htf:         Dict,
) -> str:
    if direction == "NO TRADE":
        return "No entry — wait for direction to resolve before looking for triggers"

    near       = liquidity.get("nearest_pool", "")
    fv         = value.get("fair_value", "")
    wk_mid     = value.get("weekly_mid", "")
    fib382     = str(htf.get("fib_levels", {}).get("38.2", "")) if htf.get("fib_levels") else ""
    swing_low  = htf.get("nearest_daily_swing_low")
    swing_high = htf.get("nearest_daily_swing_high")

    # Use daily swing level as the primary reference; fall back to sweep/fib/fair value
    if direction == "LONG":
        lvl  = near or (str(swing_low) if swing_low else "") or "key level"
        zone = fib382 or (str(swing_low) if swing_low else fv) or wk_mid or "fair value zone"
    else:
        lvl  = near or (str(swing_high) if swing_high else "") or "key level"
        zone = fib382 or (str(swing_high) if swing_high else fv) or wk_mid or "fair value zone"

    if sweep_down and direction == "LONG":
        return f"Swept low ({lvl}) holds on retest + bullish close above it + higher low on 15m/1H"
    if sweep_up and direction == "SHORT":
        return f"Swept high ({lvl}) fails on retest + bearish close below it + lower high on 15m/1H"
    if htf_context == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND" and direction == "SHORT":
        return (
            f"Price rallies into {zone} (last daily swing high) + "
            f"bearish rejection (wick or engulf) + bearish close — enter short"
        )
    if htf_context == "PULLBACK_IN_UPTREND" and direction == "LONG":
        return (
            f"Pullback holds above {lvl} (last daily swing low) + "
            f"bullish rejection candle + higher low on 1H — enter long"
        )
    if htf_context == "ESTABLISHED_DOWNTREND" and direction == "SHORT":
        return f"Rally into {lvl} + bearish rejection + lower high confirmed on 1H"
    if htf_context == "ESTABLISHED_UPTREND" and direction == "LONG":
        return f"Pullback to {lvl} holds + bullish rejection + GBP maintaining strength"

    return "Price reaches key level + rejection candle on execution timeframe + no high-impact event within 2h"


# ── Setup levels: entry zone, stop, target ───────────────────────────────────

_PIP              = 0.0001  # GBP/AUD 4-decimal pip value
_STOP_BEYOND_PIPS = 40      # pips beyond the tested level where the stop sits
_STOP_MAX_PIPS    = 45      # hard ceiling — never risk more than this
_LEVEL_SEARCH_PIPS = 80     # how far from price we'll accept a key level


def _calc_setup_levels(
    direction:    str,
    liq:          Dict,
    htf:          Dict,
    value:        Dict,
    trade_type:   str,
    current_price: float,
) -> Dict:
    """
    Level-anchored stop placement.

    Logic
    ─────
    1. Find the key level being *tested* (the one that was swept or is the
       nearest structure level in the trade direction).
    2. Stop goes BEYOND that level by _STOP_BEYOND_PIPS, capped at _STOP_MAX_PIPS
       from the entry anchor.
    3. Entry zone is a tight ±8-pip band around the tested level.
    4. Target is the nearest opposing key level beyond entry.

    Priority (SHORT — stop above a HIGH level):
        sweep_pool (if sweep_up) → pdh → pwh → nearest_daily_swing_high

    Priority (LONG — stop below a LOW level):
        sweep_pool (if sweep_down) → pdl → pwl → nearest_daily_swing_low

    If no level found within _LEVEL_SEARCH_PIPS → returns wait note.
    """
    if direction not in ("LONG", "SHORT") or current_price <= 0:
        return {}

    _pip = _PIP

    # ── 1. Find the tested key level ─────────────────────────────────────────
    tested_level: float | None = None
    level_name: str = ""

    def _valid(v, must_be_above: bool | None = None) -> bool:
        if not v or not isinstance(v, (int, float)):
            return False
        dist = abs(float(v) - current_price) / _pip
        if dist > _LEVEL_SEARCH_PIPS:
            return False
        if must_be_above is True and float(v) <= current_price:
            return False
        if must_be_above is False and float(v) >= current_price:
            return False
        return True

    if direction == "SHORT":
        # For a short we want a HIGH level above (or near) current price
        sweep_pool = liq.get("nearest_pool")
        if liq.get("sweep_up") and _valid(sweep_pool, must_be_above=None):
            tested_level = float(sweep_pool)
            level_name   = "swept high"
        if tested_level is None:
            for k, n in [("pdh", "PDH"), ("pwh", "PWH")]:
                v = liq.get(k)
                if _valid(v, must_be_above=None):
                    tested_level = float(v)
                    level_name   = n
                    break
        if tested_level is None:
            v = htf.get("nearest_daily_swing_high")
            if _valid(v, must_be_above=None):
                tested_level = float(v)
                level_name   = "daily swing high"
    else:
        # For a long we want a LOW level below (or near) current price
        sweep_pool = liq.get("nearest_pool")
        if liq.get("sweep_down") and _valid(sweep_pool, must_be_above=None):
            tested_level = float(sweep_pool)
            level_name   = "swept low"
        if tested_level is None:
            for k, n in [("pdl", "PDL"), ("pwl", "PWL")]:
                v = liq.get(k)
                if _valid(v, must_be_above=None):
                    tested_level = float(v)
                    level_name   = n
                    break
        if tested_level is None:
            v = htf.get("nearest_daily_swing_low")
            if _valid(v, must_be_above=None):
                tested_level = float(v)
                level_name   = "daily swing low"

    if tested_level is None:
        return {
            "wait_note": (
                f"No key level within {_LEVEL_SEARCH_PIPS} pips — "
                "wait for price to reach a defined structure level before entering."
            )
        }

    # ── 2. Entry zone — tight band around the tested level ───────────────────
    entry_anchor = round(tested_level, 4)
    entry_low    = round(entry_anchor - 8 * _pip, 4)
    entry_high   = round(entry_anchor + 8 * _pip, 4)

    # ── 3. Stop — beyond the tested level, hard ceiling from entry ───────────
    if direction == "SHORT":
        raw_stop = round(tested_level + _STOP_BEYOND_PIPS * _pip, 4)
        stop_pips_from_entry = round((raw_stop - entry_anchor) / _pip)
    else:
        raw_stop = round(tested_level - _STOP_BEYOND_PIPS * _pip, 4)
        stop_pips_from_entry = round((entry_anchor - raw_stop) / _pip)

    # Hard ceiling
    if stop_pips_from_entry > _STOP_MAX_PIPS:
        stop_pips_from_entry = _STOP_MAX_PIPS
        if direction == "SHORT":
            raw_stop = round(entry_anchor + _STOP_MAX_PIPS * _pip, 4)
        else:
            raw_stop = round(entry_anchor - _STOP_MAX_PIPS * _pip, 4)

    stop_price = raw_stop
    stop_pips  = stop_pips_from_entry

    # ── 4. Target — nearest opposing key level beyond entry ──────────────────
    if direction == "LONG":
        target_candidates = []
        for k in ("pdh", "pwh"):
            v = liq.get(k)
            if v and isinstance(v, (int, float)) and float(v) > current_price:
                target_candidates.append(float(v))
        lt_high = htf.get("lt_high")
        if lt_high and isinstance(lt_high, (int, float)) and lt_high > current_price:
            target_candidates.append(float(lt_high))
        for sh in htf.get("daily_swing_highs", []):
            if sh > current_price:
                target_candidates.append(sh)
        target = round(min(target_candidates), 4) if target_candidates else None
    else:
        target_candidates = []
        for k in ("pdl", "pwl"):
            v = liq.get(k)
            if v and isinstance(v, (int, float)) and float(v) < current_price:
                target_candidates.append(float(v))
        lt_low = htf.get("lt_low")
        if lt_low and isinstance(lt_low, (int, float)) and lt_low < current_price:
            target_candidates.append(float(lt_low))
        for sl in htf.get("daily_swing_lows", []):
            if sl < current_price:
                target_candidates.append(sl)
        target = round(max(target_candidates), 4) if target_candidates else None

    # ── 5. R:R ───────────────────────────────────────────────────────────────
    risk_reward  = None
    target_pips  = None
    if target:
        if direction == "LONG":
            target_pips = round((target - entry_anchor) / _pip)
        else:
            target_pips = round((entry_anchor - target) / _pip)

        if stop_pips > 0 and target_pips and target_pips > 0:
            risk_reward = round(target_pips / stop_pips, 1)

    rr_flag = ""
    if risk_reward is not None and risk_reward < 1.5:
        rr_flag = f"Low R:R ({risk_reward}) — target too close, consider skipping"

    return {
        "entry_zone":    f"{entry_low} – {entry_high}",
        "entry_anchor":  entry_anchor,
        "stop_loss":     stop_price,
        "stop_pips":     stop_pips,
        "target":        target,
        "target_pips":   target_pips,
        "risk_reward":   risk_reward,
        "rr_flag":       rr_flag,
        "level_name":    level_name,
        "tested_level":  round(tested_level, 4),
    }


# ── Core decision function ────────────────────────────────────────────────────

def make_decision(report: Dict, trade_type: str = "auto") -> Dict:
    """
    Takes the full market report dict (output of build_market_report()).
    Returns a clean decision dict.

    trade_type: "intraday" | "swing" | "auto"
      intraday — boosts execution signals, suppresses slow structural signals
      swing    — boosts structural signals, suppresses execution noise
      auto     — framework picks based on which tier score is strongest
    """
    layers    = report.get("layers", {})
    htf       = layers.get("htf", {})
    liq       = layers.get("liquidity", {})
    regime    = layers.get("regime", {})
    news      = layers.get("news", {})
    value     = layers.get("value", {})
    ses       = layers.get("session", {})
    signals   = report.get("signal_summary", [])

    overall_bias = report.get("overall_bias", "NEUTRAL")
    conflict     = report.get("live_vs_structural_conflict", False)
    live_dom     = report.get("live_dominant",  "NEUTRAL")
    struct_dom   = report.get("struct_dominant", "NEUTRAL")

    htf_context = htf.get("context", "UNKNOWN")
    lt_trend    = htf.get("lt_trend", "UNKNOWN")
    sweep_down  = liq.get("sweep_down", False)
    sweep_up    = liq.get("sweep_up",   False)
    adx         = float(regime.get("adx", 0) or 0)
    regime_lbl  = regime.get("regime", "DEFAULT")
    session     = ses.get("session_label") or ses.get("session", "")

    # ── Hard block: high-impact event within 2h ───────────────────────────────
    hard_blocks = []
    event_risk  = False
    event_name  = ""
    for ev in news.get("events", []):
        if ev.get("impact", "") in ("High", "Orange", "Red"):
            hrs = hours_until(str(ev.get("time", "")))
            if -0.5 < hrs < 2.0:
                event_risk = True
                event_name = ev.get("event", "high-impact event")
                hard_blocks.append(f"{event_name} in {hrs:.1f}h")
                break

    if event_risk:
        return {
            "direction":            "NO TRADE",
            "grade":                "C",
            "risk_pct":             0.0,
            "conviction":           0,
            "regime":               regime_lbl,
            "regime_weights":       _REGIME_WEIGHTS.get(regime_lbl, _DEFAULT_WEIGHTS),
            "primary_reason":       f"Hard block: {event_name} within 2h — no new positions",
            "supporting":           [],
            "conflicts":            [],
            "entry_condition":      f"Wait for {event_name} to pass, then re-run framework",
            "invalidation":         [],
            "hard_blocks":          hard_blocks,
            "grade_label":          "C — NO TRADE",
            "grade_reason":         "Event risk",
            "grade_cap_reason":     f"High-impact event within 2h: {event_name}",
            "come_back_at":         f"After {event_name} clears",
            "is_counter":           False,
            "intraday_fakeout_type": "",
            "intraday_note":        "",
            "asian_range_pips":     None,
            "fakeout_aligns":       False,
            "fakeout_opposes":      False,
            "macro_quadrant":       "",
            "macro_bias":           "NEUTRAL",
            "macro_narrative":      "",
            "macro_modifier":       0,
            "macro_direction":      "neutral",
        }

    # ── Intraday fakeout layer ────────────────────────────────────────────────
    intraday         = layers.get("intraday", {})
    fakeout_detected = intraday.get("fakeout_detected", False)
    fakeout_type     = intraday.get("fakeout_type", "NONE")
    fakeout_note     = intraday.get("fakeout_note", "")
    intraday_bias    = intraday.get("intraday_bias", "WAIT")
    intraday_entry   = intraday.get("entry_note", "")
    asian_range_pips = intraday.get("asian_range_pips")
    intraday_warn    = intraday.get("warning", "")

    # BOTH_SWEPT is highly chaotic — flag it now (doesn't force early return)
    if fakeout_type == "BOTH_SWEPT":
        hard_blocks.append("Asian range: both extremes swept — highly chaotic, no clean signal")

    # ── Macro regime quadrant ─────────────────────────────────────────────────
    macro        = layers.get("macro", {})
    macro_bias   = macro.get("gbpaud_bias", "NEUTRAL")
    macro_mag    = int(macro.get("magnitude", 0))
    macro_quad   = macro.get("quadrant", "TRANSITIONAL")
    macro_narr   = macro.get("narrative", "")

    # ── Leg decomposition — inject as synthetic signal ────────────────────────
    cross       = layers.get("cross_market", {})
    legs        = cross.get("legs", {})
    leg_bias    = legs.get("bias", "NEUTRAL")
    leg_strong  = legs.get("strong", False)
    leg_note    = legs.get("note", "")
    # Compute a raw_score for the leg signal: strong both-confirming = ±60, one-led = ±30
    _leg_raw_scores = {
        "BOTH_CONFIRMING_BULLISH":  60, "BOTH_CONFIRMING_BEARISH": -60,
        "GBP_STRENGTH_LED":          30, "GBP_WEAKNESS_LED":        -30,
        "AUD_WEAKNESS_LED":          25, "AUD_STRENGTH_LED":        -25,
        "GBP_OUTPACING":             15, "AUD_OUTPACING":           -15,
        "AUD_LEADING_DOWN":          15, "GBP_LEADING_DOWN":        -15,
        "NEUTRAL":                    0, "UNKNOWN":                   0,
    }
    _leg_raw = _leg_raw_scores.get(legs.get("driver", "NEUTRAL"), 0)
    # Only inject if we have actual data
    if leg_bias != "NEUTRAL" or legs.get("driver", "UNKNOWN") != "UNKNOWN":
        signals = list(signals) + [{
            "layer":     "Leg Decomposition",
            "bias":      leg_bias,
            "available": legs.get("driver", "UNKNOWN") != "UNKNOWN",
            "raw_score": _leg_raw,
            "summary":   leg_note[:120] if leg_note else "GBP/USD vs AUD/USD decomposition",
            "timeframe": "LIVE",
        }]

    # ── Regime-aware conviction ───────────────────────────────────────────────
    conviction, _ = _regime_score(signals, regime_lbl, trade_type)

    # ── Resolve direction ─────────────────────────────────────────────────────
    direction, reason, is_counter = _resolve_direction(
        htf_context, lt_trend, overall_bias,
        live_dom, struct_dom, conflict,
        sweep_down, sweep_up, conviction,
    )

    # ── Apply macro modifier (after direction is known) ───────────────────────
    macro_aligns = (
        (direction == "LONG"  and macro_bias == "BULLISH") or
        (direction == "SHORT" and macro_bias == "BEARISH")
    )
    macro_opposes = (
        (direction == "LONG"  and macro_bias == "BEARISH") or
        (direction == "SHORT" and macro_bias == "BULLISH")
    )
    if direction not in ("NO TRADE", "") and macro_mag > 0:
        if macro_aligns:
            conviction = min(95, conviction + macro_mag)
        elif macro_opposes:
            conviction = max(10, conviction - macro_mag)

    # ── Apply intraday modifier (after direction is known) ────────────────────
    # intraday_bias: LONG / SHORT / WAIT / NEUTRAL (from fakeout OR clean break)
    intraday_dir    = intraday_bias
    intraday_aligns = intraday_dir in ("LONG", "SHORT") and intraday_dir == direction
    intraday_opps   = (
        intraday_dir in ("LONG", "SHORT") and
        intraday_dir != direction and
        direction not in ("NO TRADE", "")
    )
    fakeout_aligns  = fakeout_detected and intraday_aligns
    fakeout_opposes = fakeout_detected and intraday_opps

    if intraday_aligns:
        boost = 10 if fakeout_detected else 5   # confirmed fakeout > clean break
        conviction = min(95, conviction + boost)
    elif intraday_opps:
        cut = 10 if fakeout_detected else 5
        conviction = max(10, conviction - cut)

    # ── Asian range quality penalty ───────────────────────────────────────────
    thin_range = asian_range_pips is not None and asian_range_pips < 20
    if thin_range and direction not in ("NO TRADE", ""):
        conviction = max(10, conviction - 5)

    # Conviction floor — no trade when signals are too weak
    if direction != "NO TRADE" and conviction < 28:
        direction = "NO TRADE"
        reason    = f"Conviction too low ({conviction}/100) — insufficient signal alignment"

    # ── Pre-compute tier inputs + resolve trade type (needed before grade) ────
    _wrong_session = session in ("Tokyo", "Sydney", "Off-hours", "Market closed")
    _sweep_conf    = (sweep_down and direction == "LONG") or (sweep_up and direction == "SHORT")
    _range_pct     = float(layers.get("regime", {}).get("fuel_pct", 0) or 0)

    _tiers_raw = _tier_scores(
        signals=signals, regime=regime_lbl, direction=direction,
        overall_bias=overall_bias, macro_opposes=macro_opposes,
        macro_aligns=macro_aligns, macro_mag=macro_mag,
        session_label=session, is_wrong_session=_wrong_session, adx=adx,
        fakeout_aligns=fakeout_aligns, fakeout_opposes=fakeout_opposes,
        sweep_conf=_sweep_conf, news_blocked=bool(hard_blocks),
        range_pct=_range_pct, trade_type="auto",
    )
    _resolved_type = trade_type
    if trade_type == "auto":
        _exec_raw   = _tiers_raw["execution_score"]
        _struct_raw = _tiers_raw["structural_score"]
        _resolved_type = "intraday" if (_exec_raw - _struct_raw) >= 15 else "swing"

    # ── Grade ─────────────────────────────────────────────────────────────────
    if direction == "NO TRADE":
        grade, risk_pct, grade_label, grade_reason = "C", 0.0, "NO TRADE", reason
    else:
        sweep_conf  = (sweep_down and direction == "LONG") or (sweep_up and direction == "SHORT")
        val_aligned = (
            (value.get("verdict_bias") == "BULLISH" and direction == "LONG") or
            (value.get("verdict_bias") == "BEARISH" and direction == "SHORT")
        )
        htf_conflict = conflict and (
            (direction == "LONG"  and struct_dom == "BEARISH") or
            (direction == "SHORT" and struct_dom == "BULLISH")
        )
        qual = _setup_quality(conviction, conflict, sweep_down or sweep_up, adx,
                              fakeout_aligns)
        # Use raw tier scores (pre-trade-type) for grade assignment so the
        # structural floor check compares apples-to-apples
        grade, risk_pct, grade_label, grade_reason = get_grade(
            alignment         = conviction,
            quality           = qual,
            is_counter_trend  = is_counter,
            event_risk        = False,
            session           = session,
            sweep_confirmed   = sweep_conf,
            is_value_aligned  = val_aligned,
            htf_conflict      = htf_conflict,
            fakeout_confirmed = fakeout_aligns,
            trade_type        = _resolved_type,
            structural_score  = _tiers_raw["structural_score"],
        )

    # ── Grade cap reason and come-back hint ───────────────────────────────────
    grade_cap_reason = ""
    come_back_at     = ""
    if grade == "C":
        if session in ("Tokyo", "Sydney", "Off-hours", "Market closed"):
            grade_cap_reason = f"Session is {session} — minimal GBP/AUD activity"
            come_back_at     = "London open (07:00 UTC)"
        elif thin_range:
            grade_cap_reason = (
                f"Asian range only {asian_range_pips} pips — "
                "setup signals unreliable below 20 pips"
            )
            come_back_at = "Next Asian session for a fresh, wider range"
        elif fakeout_opposes:
            grade_cap_reason = (
                f"Intraday {fakeout_type} fakeout opposes the "
                f"{'long' if direction == 'LONG' else 'short'} call — wait for alignment"
            )
        elif direction == "NO TRADE":
            grade_cap_reason = "Direction unresolved — signals not aligned enough"
        else:
            grade_cap_reason = "Signal quality or alignment below tradeable threshold"
    elif grade in ("B", "B+") and thin_range:
        grade_cap_reason = f"Note: Asian range thin ({asian_range_pips} pips)"

    # ── Split signals into supporters and conflicts ───────────────────────────
    supporting:     List[str] = []
    conflicts_list: List[str] = []
    dir_bias = "BULLISH" if direction == "LONG" else "BEARISH" if direction == "SHORT" else None

    for s in signals:
        if not s.get("available") or s["bias"] in ("NEUTRAL", "UNKNOWN") or not dir_bias:
            continue
        target = supporting if s["bias"] == dir_bias else conflicts_list
        target.append(f"{s['layer']}: {s['summary']}")

    # Surface macro as conflict or support
    if macro_opposes and macro_mag >= 6:
        conflicts_list.insert(0, f"Macro: {macro_quad} quadrant opposes this direction")
    elif macro_aligns and macro_mag >= 6:
        supporting.insert(0, f"Macro: {macro_quad} quadrant supports this direction")

    # Surface intraday fakeout / clean break as conflict or support
    if intraday_aligns and intraday_dir in ("LONG", "SHORT"):
        tag = "confirmed fakeout" if fakeout_detected else "clean break"
        label_ = "long" if intraday_dir == "LONG" else "short"
        supporting.insert(0, f"Intraday: {fakeout_type} {tag} — confirms {label_}")
    elif intraday_opps and intraday_dir in ("LONG", "SHORT"):
        tag = "fakeout" if fakeout_detected else "break"
        supporting_dir = "long" if intraday_dir == "LONG" else "short"
        conflicts_list.insert(0,
            f"Intraday: {fakeout_type} {tag} signals {supporting_dir} — conflicts with this call"
        )

    # ── Three-tier conviction matrix ──────────────────────────────────────────
    # (_wrong_session, _sweep_conf, _range_pct, _tiers_raw, _resolved_type
    #  are already computed above before the grade block)
    tiers = _tier_scores(
        signals         = signals,
        regime          = regime_lbl,
        direction       = direction,
        overall_bias    = overall_bias,
        macro_opposes   = macro_opposes,
        macro_aligns    = macro_aligns,
        macro_mag       = macro_mag,
        session_label   = session,
        is_wrong_session= _wrong_session,
        adx             = adx,
        fakeout_aligns  = fakeout_aligns,
        fakeout_opposes = fakeout_opposes,
        sweep_conf      = _sweep_conf,
        news_blocked    = bool(hard_blocks),
        range_pct       = _range_pct,
        trade_type      = _resolved_type,
    )

    # ── "What would make this an A" — find weakest blocking tier ─────────────
    _s_score = tiers["structural_score"]
    _t_score = tiers["tactical_score"]
    _e_score = tiers["execution_score"]
    _weakest = min(
        [("structural", _s_score), ("tactical", _t_score), ("execution", _e_score)],
        key=lambda x: x[1]
    )
    _upgrade_hints: List[str] = []
    if grade == "C" or _weakest[1] < 50:
        _wname, _wscore = _weakest
        if _wname == "execution":
            if _wrong_session:
                _upgrade_hints.append(f"Wait for London open — {session} session blocks execution")
            if not _sweep_conf:
                _upgrade_hints.append("Wait for price to reach a key level (PDH, PDL, weekly high/low)")
            if _range_pct > 80:
                _upgrade_hints.append("Daily range nearly exhausted — wait for tomorrow's fresh range")
        elif _wname == "tactical":
            _upgrade_hints.append("Wait for currency strength to confirm direction (GBP vs AUD gap ≥ 10 pts)")
            if legs.get("driver", "NEUTRAL") in ("NEUTRAL", "UNKNOWN"):
                _upgrade_hints.append("Wait for GBP/USD and AUD/USD to diverge — confirms which leg is leading")
        elif _wname == "structural":
            if macro_opposes:
                _upgrade_hints.append("Macro conflict must resolve — watch for macro quadrant shift away from current reading")
            _upgrade_hints.append("HTF trend must show further distance from MA50 — structure needs more room")

    # ── Entry and invalidation ────────────────────────────────────────────────
    entry = _build_entry_condition(
        direction, htf_context, lt_trend,
        sweep_down, sweep_up, value, liq, htf,
    )
    # Fakeout-specific entry is more precise — use it when confirmed and aligned
    if fakeout_aligns and intraday_entry:
        entry = intraday_entry

    inv_conditions = _build_invalidation_conditions(
        direction, htf, liq, value, sweep_down, sweep_up,
    )

    # ── Setup levels: entry zone, stop, target (grade B and above only) ───────
    _current_price = float(liq.get("current_price") or 0)
    setup_levels: Dict = {}
    if grade in ("A+", "A", "B+", "B") and _current_price > 0:
        setup_levels = _calc_setup_levels(
            direction     = direction,
            liq           = liq,
            htf           = htf,
            value         = value,
            trade_type    = _resolved_type,
            current_price = _current_price,
        )

    return {
        "direction":             direction,
        "grade":                 grade,
        "risk_pct":              risk_pct,
        "conviction":            conviction,
        "regime":                regime_lbl,
        "regime_weights":        _REGIME_WEIGHTS.get(regime_lbl, _DEFAULT_WEIGHTS),
        "primary_reason":        reason,
        "supporting":            supporting,
        "conflicts":             conflicts_list,
        "entry_condition":       entry,
        "invalidation":          inv_conditions,
        "hard_blocks":           hard_blocks,
        "grade_label":           grade_label,
        "grade_reason":          grade_reason,
        "grade_cap_reason":      grade_cap_reason,
        "come_back_at":          come_back_at,
        "is_counter":            is_counter,
        "intraday_fakeout_type": fakeout_type,
        "intraday_note":         fakeout_note,
        "asian_range_pips":      asian_range_pips,
        "fakeout_aligns":        fakeout_aligns,
        "fakeout_opposes":       fakeout_opposes,
        "macro_quadrant":        macro_quad,
        "macro_bias":            macro_bias,
        "macro_narrative":       macro_narr,
        "macro_modifier":        macro_mag if (macro_aligns or macro_opposes) else 0,
        "macro_direction":       "boost" if macro_aligns else "reduce" if macro_opposes else "neutral",
        "structural_score":      tiers["structural_score"],
        "tactical_score":        tiers["tactical_score"],
        "execution_score":       tiers["execution_score"],
        "tier_signals":          tiers["tier_signals"],
        "upgrade_hints":         _upgrade_hints,
        "legs":                  legs,
        "trade_type":            _resolved_type,
        "setup_levels":          setup_levels,
    }


# ── Terminal formatter ────────────────────────────────────────────────────────

def _wrap(text: str, width: int, indent: str = "    ") -> List[str]:
    """Word-wrap a long string, preserving the indent on continuation lines."""
    import textwrap
    return textwrap.wrap(text, width=width - len(indent),
                         initial_indent=indent, subsequent_indent=indent)


def format_decision_block(dec: Dict, width: int = 66) -> str:
    """
    Renders the decision dict as a clean terminal block.
    Designed to print at the very top of the market report.
    """
    W     = width
    dir_  = dec.get("direction", "NO TRADE")
    grade = dec.get("grade", "C")
    conv  = dec.get("conviction", 0)
    risk  = dec.get("risk_pct", 0.0)
    reg   = dec.get("regime", "")

    dir_display  = {"LONG": "▲  LONG", "SHORT": "▼  SHORT", "NO TRADE": "—  NO TRADE"}.get(dir_, dir_)
    dir_explain  = {
        "LONG":     "(buy GBP/AUD — you profit when price rises)",
        "SHORT":    "(sell GBP/AUD — you profit when price falls)",
        "NO TRADE": "(stand aside — conditions are not good enough right now)",
    }.get(dir_, "")

    grade_icon   = {"A+": "🔥", "A": "✅", "B+": "⚡", "B": "⚠️ ", "C": "🚫"}.get(grade, "")
    grade_action = {
        "A+": "→ everything aligned. Take your full planned position size.",
        "A":  "→ strong setup. Standard position size. Let it run.",
        "B+": "→ valid trade, 1–2 things not perfect. Standard size, manage actively.",
        "B":  "→ direction there but conflicts exist. Half size, tight stop.",
        "C":  "→ do not trade. Stand aside until conditions improve.",
    }.get(grade, "")

    conv_label   = (
        "very weak — signals cancel out"   if conv < 25 else
        "weak — limited agreement"         if conv < 45 else
        "moderate — directional edge"      if conv < 65 else
        "solid — most signals agree"       if conv < 80 else
        "strong — all layers stacked"
    )
    conv_explain = (
        "Conviction is how strongly all the signals agree on one direction.\n"
        "  0 = total disagreement. 100 = every signal pointing the same way."
    )

    macro_quad = dec.get("macro_quadrant", "")
    macro_dir  = dec.get("macro_direction", "neutral")
    macro_mod  = dec.get("macro_modifier", 0)
    macro_icon = {"boost": "+", "reduce": "−", "neutral": "~"}.get(macro_dir, "~")
    macro_plain = {
        "REFLATION":   "growth up, inflation up — AUD commodity demand rising",
        "GOLDILOCKS":  "growth up, inflation low — risk-on, equities and AUD favoured",
        "STAGFLATION": "growth down, inflation up — GBP safe-haven demand rising",
        "DEFLATION":   "growth down, inflation down — risk-off, GBP may gain vs AUD",
        "TRANSITIONAL":"signals mixed, no clear macro regime",
    }.get(macro_quad, "")
    macro_line = (
        f"  Macro: {macro_quad}  ({macro_icon}{macro_mod} conviction)"
        if macro_quad and macro_quad != "TRANSITIONAL"
        else f"  Macro: {macro_quad}" if macro_quad else ""
    )

    regime_plain = {
        "TRENDING_UP":   "price is in an uptrend — structure signals carry more weight",
        "TRENDING_DOWN": "price is in a downtrend — structure signals carry more weight",
        "RANGING":       "market is bouncing between levels — price zones matter most",
        "VOLATILE":      "news-driven volatility — reduce size, watch economic events",
        "DEFAULT":       "mixed or unclear — default signal weights applied",
    }.get(reg, "")

    lines = [
        "═" * W,
        "  DECISION ENGINE  —  what to do right now",
        "─" * W,
        f"  {dir_display}",
        f"  {dir_explain}",
        "",
        f"  {grade_icon} Grade: {grade}   Risk: {risk}%/trade   "
        f"Conviction: {conv}/100 ({conv_label})",
        f"     {grade_action}",
        f"  Regime: {reg}" + (f"   {macro_line.strip()}" if macro_line else ""),
    ]
    if regime_plain:
        lines.append(f"     ({regime_plain})")
    lines += [
        "─" * W,
        f"  {dec.get('primary_reason', '')}",
    ]

    if dec.get("macro_narrative") and macro_quad not in ("", "TRANSITIONAL"):
        direction = dec.get("direction", "")
        macro_aligns = dec.get("macro_modifier", 0) > 0
        if grade == "C" or not macro_aligns:
            # Macro conflicts with direction — say so plainly, skip the bullish/bearish narrative
            lines += ["", f"  MACRO ({macro_quad}): {macro_plain}."]
            lines.append(f"  This macro signal conflicts with the structural direction — one reason for Grade C.")
        else:
            lines += ["", f"  MACRO ENVIRONMENT ({macro_quad}):"]
            if macro_plain:
                lines.append(f"  {macro_plain}.")
            lines += _wrap(dec["macro_narrative"], W)

    if dec.get("is_counter"):
        lines += [
            "",
            "  ⚠  COUNTER-TREND TRADE — you are trading against the dominant trend.",
            "     This is higher risk. The dominant trend can resume and stop you out.",
            "     Position size is automatically reduced.",
        ]

    grade = dec.get("grade", "C")
    if grade == "C":
        # Grade C = no trade. Don't show supporting/opposing — just show what's blocking.
        all_blocks = list(dec.get("conflicts", []))[:3]
        if all_blocks:
            lines += ["", "  WHAT'S BLOCKING THIS TRADE:"]
            for c in all_blocks:
                lines += _wrap(f"✗ {c}", W)
    else:
        if dec.get("supporting"):
            lines += ["", "  SIGNALS SUPPORTING THIS CALL:"]
            for s in dec["supporting"][:3]:
                lines += _wrap(f"+ {s}", W)

        if dec.get("conflicts"):
            lines += ["", "  SIGNALS WORKING AGAINST THIS CALL:"]
            for c in dec["conflicts"][:2]:
                lines += _wrap(f"✗ {c}", W)

    lines += ["", "  WHAT NEEDS TO HAPPEN BEFORE YOU ENTER:"]
    lines += _wrap(dec.get("entry_condition", ""), W)

    if dec.get("invalidation"):
        lines += ["", "  THIS TRADE IDEA IS WRONG IF:"]
        for iv in dec["invalidation"][:3]:
            lines += _wrap(f"✗ {iv}", W)

    if dec.get("hard_blocks"):
        lines += ["", "  HARD BLOCKS — trade is blocked regardless of grade:"]
        for b in dec["hard_blocks"]:
            lines.append(f"    🚫 {b}")

    cap = dec.get("grade_cap_reason", "")
    ret = dec.get("come_back_at", "")
    if cap:
        lines += ["", f"  WHY THIS GRADE: {cap}"]
    if ret:
        lines.append(f"  WHEN TO COME BACK: {ret}")

    tmpl = dec.get("template_match", {})
    if tmpl.get("win_rate") is not None:
        lines += ["", "  HISTORICAL BASE RATE (similar past setups):"]
        lines.append(f"    {tmpl['message']}")
    elif tmpl.get("message") and tmpl.get("total_matches", 0) > 0:
        lines += ["", "  HISTORICAL CONTEXT:"]
        lines.append(f"    {tmpl['message']}")

    lines.append("═" * W)
    return "\n".join(lines)
