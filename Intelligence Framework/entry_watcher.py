"""
entry_watcher.py
────────────────
Monitors GBP/AUD 5-min and 15-min candles from OANDA.
Fires an entry alert when BOTH timeframes confirm an engulfing
at a key level identified by the framework.

Logic:
  1. Read current bias + key levels from last framework run
  2. Every 60 seconds: fetch latest 5-min and 15-min candles
  3. When a 15-min engulfing forms at a key level → PARTIAL SIGNAL
  4. When a 5-min engulfing confirms same direction within 30 min → FIRE ALERT

Run via:
    python3 main.py watch
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from oanda_feed import get_m5_bars, get_m15_bars
from levels_context import levels_as_list, nearest_resistance, nearest_support

_DIR          = Path(__file__).parent
_LAST_RUN     = _DIR / "last_run.json"
_PIP          = 0.0001   # GBP/AUD 4-decimal pair
_PROXIMITY    = 20       # pips — how close to a key level the candle must be
_STOP_BUFFER  = 5        # pips added beyond the candle wick for the stop
_POLL_SECONDS = 60       # how often to check for new candles
_PENDING_TTL  = 30 * 60  # 15-min signal expires after 30 minutes if no 5-min confirms


# ── Context ───────────────────────────────────────────────────────────────────

def _load_context() -> dict:
    """Read the most recent framework run from last_run.json."""
    if not _LAST_RUN.exists():
        return {}
    try:
        return json.loads(_LAST_RUN.read_text())
    except Exception:
        return {}


def _context_age_hours(ctx: dict) -> float:
    """Return how many hours ago the last framework run was."""
    date_str = ctx.get("date", "")
    time_str = ctx.get("time_utc", "")
    if not date_str or not time_str:
        return 999.0
    try:
        run_dt = datetime.strptime(f"{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
        run_dt = run_dt.replace(tzinfo=timezone.utc)
        delta  = datetime.now(timezone.utc) - run_dt
        return delta.total_seconds() / 3600
    except ValueError:
        return 999.0


def _get_key_levels(ctx: dict) -> list[float]:
    """
    Extract all key price levels from the framework context.
    Combines last_run.json levels dict with legacy single-level fields.
    """
    levels = []

    # Rich levels dict (PDH/PDL, weekly, session, Asian)
    stored = ctx.get("levels", {})
    if stored:
        levels.extend(levels_as_list(stored))

    # Legacy single-level fields as fallback
    for key in ("nearest_level", "trigger_price", "invalidation"):
        val = ctx.get(key)
        if val:
            try:
                levels.append(round(float(val), 5))
            except (TypeError, ValueError):
                pass

    return sorted(set(levels))


def _get_levels_dict(ctx: dict) -> dict:
    """Return the raw levels dict for target calculation."""
    return ctx.get("levels", {})


# ── News filter ───────────────────────────────────────────────────────────────

def _check_news_block(ctx: dict) -> tuple[bool, str]:
    """
    Returns (is_blocked, reason_string).
    Blocked if a high-impact GBP or AUD event is within 60 minutes
    or within 15 minutes after release (spreads still wide).
    """
    upcoming = ctx.get("upcoming_news", [])
    if not upcoming:
        return False, ""

    for ev in upcoming:
        mins = ev.get("minutes", 999)
        name = ev.get("event", "Unknown event")
        curr = ev.get("currency", "")
        time = ev.get("time", "")

        if -15 <= mins <= 0:
            return True, (
                f"⛔ NEWS BLOCK: {curr} {name} released {abs(mins)}min ago "
                f"— spreads still elevated, skip this entry"
            )
        if 0 < mins <= 60:
            return True, (
                f"⛔ NEWS BLOCK: {curr} {name} in {mins}min ({time} UTC) "
                f"— do not enter before high-impact news"
            )

    return False, ""


# ── Candle pattern detection ──────────────────────────────────────────────────

def _body_high(c: dict) -> float:
    return max(c["Open"], c["Close"])

def _body_low(c: dict) -> float:
    return min(c["Open"], c["Close"])

def _body_size(c: dict) -> float:
    return abs(c["Close"] - c["Open"])

def _total_range(c: dict) -> float:
    return c["High"] - c["Low"]

def _upper_wick(c: dict) -> float:
    return c["High"] - _body_high(c)

def _lower_wick(c: dict) -> float:
    return _body_low(c) - c["Low"]


def _detect_bullish_pattern(prev: dict, curr: dict) -> Optional[str]:
    """
    Check for any bullish confirmation pattern.
    Returns the pattern name or None.
    Checked in order of strength — returns the first match.
    """
    body  = _body_size(curr)
    rng   = _total_range(curr)
    lo_wk = _lower_wick(curr)
    up_wk = _upper_wick(curr)

    if rng == 0:
        return None

    # 1. Bullish engulfing — current bullish body covers previous body entirely
    if (curr["Close"] > curr["Open"]
            and curr["Close"] >= _body_high(prev)
            and curr["Open"] <= _body_low(prev)):
        return "Bullish engulfing"

    # 2. Pin bar / Hammer — long lower wick, small body at top of range
    #    Lower wick >= 2x body, closes in upper 40% of candle range
    if (lo_wk >= 2 * max(body, _PIP)
            and (curr["Close"] - curr["Low"]) >= 0.6 * rng):
        return "Bullish pin bar"

    # 3. Rejection candle — lower wick dominates, closes above midpoint
    #    Lower wick >= 1.5x body, no excessive upper wick
    midpoint = curr["Low"] + rng / 2
    if (lo_wk >= 1.5 * max(body, _PIP)
            and curr["Close"] >= midpoint
            and up_wk <= lo_wk * 0.5):
        return "Bullish rejection"

    # 4. Strong momentum close — large bullish body, closes near high
    #    Body >= 70% of range, close in upper 20%
    if (curr["Close"] > curr["Open"]
            and body >= 0.70 * rng
            and (curr["High"] - curr["Close"]) <= 0.20 * rng):
        return "Strong bullish close"

    return None


def _detect_bearish_pattern(prev: dict, curr: dict) -> Optional[str]:
    """
    Check for any bearish confirmation pattern.
    Returns the pattern name or None.
    """
    body  = _body_size(curr)
    rng   = _total_range(curr)
    lo_wk = _lower_wick(curr)
    up_wk = _upper_wick(curr)

    if rng == 0:
        return None

    # 1. Bearish engulfing
    if (curr["Close"] < curr["Open"]
            and curr["Open"] >= _body_high(prev)
            and curr["Close"] <= _body_low(prev)):
        return "Bearish engulfing"

    # 2. Pin bar / Shooting star — long upper wick, small body at bottom
    if (up_wk >= 2 * max(body, _PIP)
            and (curr["High"] - curr["Close"]) >= 0.6 * rng):
        return "Bearish pin bar"

    # 3. Rejection candle — upper wick dominates, closes below midpoint
    midpoint = curr["Low"] + rng / 2
    if (up_wk >= 1.5 * max(body, _PIP)
            and curr["Close"] <= midpoint
            and lo_wk <= up_wk * 0.5):
        return "Bearish rejection"

    # 4. Strong momentum close — large bearish body, closes near low
    if (curr["Close"] < curr["Open"]
            and body >= 0.70 * rng
            and (curr["Close"] - curr["Low"]) <= 0.20 * rng):
        return "Strong bearish close"

    return None


def _near_level(candle: dict, level: float, direction: str) -> bool:
    """
    Check if the candle is forming at/near a key level.
    LONG: candle low should be within proximity of the level (support)
    SHORT: candle high should be within proximity of the level (resistance)
    """
    threshold = _PROXIMITY * _PIP
    if direction == "LONG":
        return abs(candle["Low"] - level) <= threshold
    else:
        return abs(candle["High"] - level) <= threshold


def _at_any_level(candle: dict, levels: list[float], direction: str) -> Optional[float]:
    """Return the first key level the candle is near, or None."""
    for level in levels:
        if _near_level(candle, level, direction):
            return level
    return None


# ── Stop and target ───────────────────────────────────────────────────────────

def _calc_stop(candle: dict, direction: str) -> float:
    """Place stop just beyond the engulfing candle's wick."""
    buffer = _STOP_BUFFER * _PIP
    if direction == "LONG":
        return round(candle["Low"] - buffer, 5)
    else:
        return round(candle["High"] + buffer, 5)


def _calc_rr(entry: float, stop: float, target: float, direction: str) -> float:
    """Calculate R:R ratio."""
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 1)


def _pips(a: float, b: float) -> float:
    return round(abs(a - b) / _PIP, 1)


# ── Alert formatting ──────────────────────────────────────────────────────────

def _print_partial(timeframe: str, direction: str, level: float, pattern: str):
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    print(f"\n🟡 PARTIAL SIGNAL — GBP/AUD  [{now}]")
    print(f"  {'─'*52}")
    print(f"  {timeframe} : {pattern} at key level {level:.5f}  ✅")
    print(f"  5-min  : Waiting for confirmation...")
    print(f"  (Signal valid for 30 minutes — watch your chart)")
    print(f"  {'─'*52}\n")


def _print_alert(direction: str, level: float,
                 entry: float, stop: float, target: float,
                 rr: float, ctx: dict,
                 pattern_15: str, pattern_5: str):
    now   = datetime.now(timezone.utc).strftime("%H:%M UTC")
    grade = ctx.get("grade", "?")
    conv  = ctx.get("conviction_score", "?")
    icon  = "🟢" if direction == "LONG" else "🔴"
    stop_pips = _pips(entry, stop)
    tgt_pips  = _pips(entry, target)
    rr_ok     = rr >= 1.5

    print(f"\n{'═'*56}")
    print(f"  {icon} ENTRY TRIGGER — GBP/AUD  [{now}]")
    print(f"{'═'*56}")
    print(f"  Direction : {'LONG  (buy GBP/AUD — profit when price rises)' if direction == 'LONG' else 'SHORT (sell GBP/AUD — profit when price falls)'}")
    print(f"  {'─'*52}")
    print(f"  15-min : {pattern_15} at {level:.5f}  ✅")
    print(f"  5-min  : {pattern_5} confirmed                ✅")
    print(f"  {'─'*52}")
    print(f"  Entry  : {entry:.5f}")
    print(f"  Stop   : {stop:.5f}  ({stop_pips:.1f} pips risk)")
    print(f"     (Stop is placed {_STOP_BUFFER} pips beyond the candle wick — ")
    print(f"      if price goes here your trade idea is wrong)")
    print(f"  Target : {target:.5f}  ({tgt_pips:.1f} pips potential)")
    print(f"     (Next key level {'above' if direction == 'LONG' else 'below'} your entry)")
    print(f"  R:R    : {rr}:1  {'✅ Good' if rr_ok else '⚠️  Below minimum 1.5 — consider skipping'}")
    print(f"  {'─'*52}")
    print(f"  Grade at signal : {grade}  (conviction {conv})")
    if grade in ("A+", "A"):
        print(f"  → Strong setup. Standard position size.")
    elif grade in ("B+", "B"):
        print(f"  → Valid but not perfect. Reduce size slightly, manage actively.")
    elif grade == "C":
        print(f"  ⚠️  Grade C — framework says conditions are not ideal.")
        print(f"      Consider skipping or waiting for a better setup.")
    print(f"  {'─'*52}")
    print(f"  Execute on Liquid Charts Pro")
    print(f"  Invalidated if: price {'falls' if direction == 'LONG' else 'rises'} back through {level:.5f}")
    print(f"{'═'*56}\n")


def _print_expired():
    print(f"\n  ⏱  15-min signal expired — no 5-min confirmation within 30 min.")
    print(f"  Returning to WAITING state.\n")


# ── Main watcher loop ─────────────────────────────────────────────────────────

def watch(pair: str = "GBPAUD"):
    """
    Main polling loop. Runs continuously until Ctrl+C.
    State machine: WAITING → PENDING (15-min fired) → TRIGGERED (both fired)
    """
    print(f"\n  {'═'*52}")
    print(f"  ENTRY WATCHER — GBP/AUD")
    print(f"  {'═'*52}")
    print(f"  Monitoring 5-min + 15-min candles from OANDA")
    print(f"  Polling every {_POLL_SECONDS}s  |  Ctrl+C to stop\n")

    # State
    last_m5_ts  : Optional[datetime] = None
    last_m15_ts : Optional[datetime] = None
    pending_15  : Optional[dict]     = None   # set when 15-min fires
    pending_at  : Optional[datetime] = None   # when the 15-min fired

    while True:
        try:
            ctx    = _load_context()
            age    = _context_age_hours(ctx)
            bias   = ctx.get("bias", "").upper()
            grade  = ctx.get("grade", "C")
            levels = _get_key_levels(ctx)

            # Map bias to direction
            if "BULL" in bias or bias == "LONG":
                direction = "LONG"
            elif "BEAR" in bias or bias == "SHORT":
                direction = "SHORT"
            else:
                direction = None

            now_utc = datetime.now(timezone.utc)

            # Warn if brain run is stale
            if age > 8:
                ts = now_utc.strftime("%H:%M")
                print(f"  [{ts}] ⚠️  Last framework run was {age:.0f}h ago — run 'python3 main.py' to refresh")

            # Expire pending 15-min signal after TTL
            if pending_15 and pending_at:
                if (now_utc - pending_at).total_seconds() > _PENDING_TTL:
                    _print_expired()
                    pending_15 = None
                    pending_at = None

            if direction and levels:
                # ── News filter — check before looking at candles ─────────────
                news_blocked, news_reason = _check_news_block(ctx)
                if news_blocked:
                    ts = now_utc.strftime("%H:%M")
                    print(f"\n  [{ts}] {news_reason}\n")
                    time.sleep(_POLL_SECONDS)
                    continue

                # ── Fetch candles ─────────────────────────────────────────────
                df15 = get_m15_bars(pair, count=4)
                df5  = get_m5_bars(pair, count=4)
                levels_dict = _get_levels_dict(ctx)

                if df15 is not None and len(df15) >= 2:
                    m15_rows    = df15.iloc[-2:].reset_index()
                    m15_prev    = m15_rows.iloc[0].to_dict()
                    m15_curr    = m15_rows.iloc[1].to_dict()
                    m15_curr_ts = m15_rows.iloc[1]["Datetime"]

                    if m15_curr_ts != last_m15_ts:
                        last_m15_ts = m15_curr_ts

                        pattern_15 = (
                            _detect_bullish_pattern(m15_prev, m15_curr) if direction == "LONG"
                            else _detect_bearish_pattern(m15_prev, m15_curr)
                        )
                        hit_level = _at_any_level(m15_curr, levels, direction)

                        if pattern_15 and hit_level:
                            pending_15 = {
                                "candle":  m15_curr,
                                "level":   hit_level,
                                "pattern": pattern_15,
                            }
                            pending_at = now_utc
                            _print_partial("15-min", direction, hit_level, pattern_15)

                if df5 is not None and len(df5) >= 2 and pending_15:
                    m5_rows    = df5.iloc[-2:].reset_index()
                    m5_prev    = m5_rows.iloc[0].to_dict()
                    m5_curr    = m5_rows.iloc[1].to_dict()
                    m5_curr_ts = m5_rows.iloc[1]["Datetime"]

                    if m5_curr_ts != last_m5_ts:
                        last_m5_ts = m5_curr_ts

                        pattern_5 = (
                            _detect_bullish_pattern(m5_prev, m5_curr) if direction == "LONG"
                            else _detect_bearish_pattern(m5_prev, m5_curr)
                        )

                        if pattern_5:
                            m15_candle = pending_15["candle"]
                            level      = pending_15["level"]
                            pattern_15 = pending_15["pattern"]
                            entry      = m5_curr["Close"]
                            stop       = _calc_stop(m15_candle, direction)

                            # Target: nearest key level on the opposing side
                            if direction == "LONG":
                                target = nearest_resistance(levels_dict, entry)
                                if not target:
                                    target = round(entry + 2 * abs(entry - stop), 5)
                            else:
                                target = nearest_support(levels_dict, entry)
                                if not target:
                                    target = round(entry - 2 * abs(entry - stop), 5)

                            rr = _calc_rr(entry, stop, target, direction)

                            _print_alert(direction, level, entry, stop, target,
                                         rr, ctx, pattern_15, pattern_5)

                            pending_15 = None
                            pending_at = None

            elif not direction:
                ts = now_utc.strftime("%H:%M")
                print(f"  [{ts}] Bias is NEUTRAL — no entry direction to watch. Run framework to update.")

            elif not levels:
                ts = now_utc.strftime("%H:%M")
                print(f"  [{ts}] No key levels in last run — run framework first.")

        except KeyboardInterrupt:
            print("\n  Entry watcher stopped.\n")
            break
        except Exception as exc:
            ts = datetime.now(timezone.utc).strftime("%H:%M")
            print(f"  [{ts}] Watcher error: {exc}")

        time.sleep(_POLL_SECONDS)
