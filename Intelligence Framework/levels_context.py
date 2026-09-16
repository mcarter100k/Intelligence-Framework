"""
levels_context.py
─────────────────
Computes all key GBP/AUD price levels from OANDA data.
Used by market_brain to store levels in last_run.json,
and by entry_watcher to find valid entry zones and targets.

Levels returned:
  prev_day_high / prev_day_low   — yesterday's high and low (strongest daily levels)
  prev_week_high / prev_week_low — PREVIOUS completed week's extremes
  current_week_high / current_week_low
                                 — this week to date, from completed daily
                                   bars; today is covered by session_*
  session_high / session_low     — current session's high and low so far
  asian_high   / asian_low       — Asian range for THIS pair

Weekly naming corrected 2026-09-16 (docs/specs/level_source_repair_spec.md
D3): these keys were called weekly_high/weekly_low and documented as the
current week, but the feed filters incomplete bars so the value has always
been the previous completed week. Prior-week extremes are legitimate
levels and are kept under an honest name; the current week is now supplied
alongside rather than confused with them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from oanda_feed import get_daily_bars, get_weekly_bars, get_hourly_bars


# ── Session windows (UTC) ─────────────────────────────────────────────────────
# These are the hours each session is active — used to isolate session OHLC

_SESSIONS = {
    "Asian":  (0,  9),   # 00:00 – 09:00 UTC  (Tokyo/Sydney)
    "London": (7,  16),  # 07:00 – 16:00 UTC
    "NY":     (13, 22),  # 13:00 – 22:00 UTC
}


def _current_session(hour_utc: int) -> str:
    if 7 <= hour_utc < 16:
        return "London"
    if 13 <= hour_utc < 22:
        return "NY"
    return "Asian"


def get_key_levels(pair: str = "GBPAUD") -> dict:
    """
    Return all key price levels. Any level that cannot be fetched is None.
    Always returns the dict — never raises.
    """
    result = {
        "prev_day_high":  None,
        "prev_day_low":   None,
        "prev_week_high": None,
        "prev_week_low":  None,
        "current_week_high": None,
        "current_week_low":  None,
        "session_high":   None,
        "session_low":    None,
        "session_name":   None,
        "asian_high":     None,
        "asian_low":      None,
    }

    now_utc   = datetime.now(timezone.utc)
    hour_utc  = now_utc.hour

    # ── Previous day high / low ───────────────────────────────────────────────
    try:
        daily = get_daily_bars(pair, count=3)
        if daily is not None and len(daily) >= 2:
            # Last completed day (index -2 because -1 may be today's incomplete bar,
            # but _get_bars already filters incomplete — so -1 is yesterday's full day)
            prev = daily.iloc[-1]
            result["prev_day_high"] = round(float(prev["High"]), 5)
            result["prev_day_low"]  = round(float(prev["Low"]),  5)
    except Exception:
        pass

    # ── Previous week + current week to date ──────────────────────────────────
    # The feed filters incomplete bars, so weekly.iloc[-1] is the last CLOSED
    # week — named prev_week_* accordingly. The current week cannot come from
    # the weekly series at all (its bar is still forming and is filtered out),
    # so it is aggregated from this week's completed DAILY bars; today's
    # forming session is covered by session_high/session_low. A high or low is
    # a recorded fact, not a revisable computation, so using week-to-date data
    # carries none of the risk that justifies dropping a forming bar for an
    # indicator. oanda_feed is deliberately left unchanged.
    try:
        weekly = get_weekly_bars(pair, count=2)
        if weekly is not None and len(weekly) >= 1:
            wk = weekly.iloc[-1]
            result["prev_week_high"] = round(float(wk["High"]), 5)
            result["prev_week_low"]  = round(float(wk["Low"]),  5)

            cur_open = wk.name + timedelta(days=7)
            daily_wk = get_daily_bars(pair, count=10)
            if daily_wk is not None and not daily_wk.empty:
                idx = daily_wk.index
                if getattr(idx, "tz", None) is None:
                    idx = idx.tz_localize("UTC")
                    daily_wk = daily_wk.copy()
                    daily_wk.index = idx
                this_week = daily_wk[daily_wk.index >= cur_open]
                # Empty between the weekly open and the first completed daily
                # bar — both keys stay None, per the module's None contract.
                if not this_week.empty:
                    result["current_week_high"] = round(
                        float(this_week["High"].max()), 5)
                    result["current_week_low"] = round(
                        float(this_week["Low"].min()), 5)
    except Exception:
        pass

    # ── Session high / low ────────────────────────────────────────────────────
    try:
        session_name = _current_session(hour_utc)
        start_h, end_h = _SESSIONS[session_name]
        hourly = get_hourly_bars(pair, count=24)

        if hourly is not None:
            # Filter to candles within the current session window today
            today = now_utc.date()
            mask  = hourly.index.map(
                lambda dt: dt.date() == today and start_h <= dt.hour < end_h
            )
            session_bars = hourly[mask]

            if not session_bars.empty:
                result["session_high"] = round(float(session_bars["High"].max()), 5)
                result["session_low"]  = round(float(session_bars["Low"].min()),  5)
                result["session_name"] = session_name
    except Exception:
        pass

    # ── Asian high / low (from intraday_context, keyed to THIS pair) ──────────
    # `pair` threaded 2026-09-16 (spec D4): this call took no pair and always
    # returned GBPAUD, so a GBP_JPY level set carried two AUD-scale values.
    try:
        from intraday_context import get_intraday_context
        intra = get_intraday_context(pair)
        ah = intra.get("asian_high")
        al = intra.get("asian_low")
        if ah:
            result["asian_high"] = round(float(ah), 5)
        if al:
            result["asian_low"]  = round(float(al), 5)
    except Exception:
        pass

    return result


def levels_as_list(levels: dict) -> list[float]:
    """
    Flatten the levels dict into a sorted list of unique floats.
    Used by entry_watcher to check proximity to any key level.
    """
    vals = []
    for v in levels.values():
        if isinstance(v, (int, float)) and v > 0:
            vals.append(float(v))
    return sorted(set(round(v, 5) for v in vals))


def nearest_resistance(levels: dict, entry: float) -> Optional[float]:
    """Return the nearest key level ABOVE entry (target for LONG trades)."""
    candidates = [
        v for k, v in levels.items()
        if isinstance(v, float) and v > entry
        and k not in ("session_name",)
    ]
    return min(candidates) if candidates else None


def nearest_support(levels: dict, entry: float) -> Optional[float]:
    """Return the nearest key level BELOW entry (target for SHORT trades)."""
    candidates = [
        v for k, v in levels.items()
        if isinstance(v, float) and v < entry
        and k not in ("session_name",)
    ]
    return max(candidates) if candidates else None


def get_round_number_levels(price: float, range_pips: int = 400) -> list[float]:
    """
    Return psychological / round-number price levels within range_pips of price.

    GBP/AUD traders watch three tiers of round numbers:
      Full handle   : X.XX00  (e.g. 2.0000) — strongest magnet
      Half handle   : X.XX50  (e.g. 2.0500) — significant
      Quarter handle: X.XX25 / X.XX75        — weaker but respected

    These levels are magnets — price gravitates toward them and often
    reverses or stalls there even with no prior S/R context.
    """
    step   = 0.0025   # quarter-handle spacing (25 pips)
    margin = range_pips * 0.0001

    # Snap the centre to the nearest 25-pip level
    centre = round(round(price / step) * step, 4)

    levels = []
    n = int(margin / step) + 2
    for i in range(-n, n + 1):
        lvl = round(centre + i * step, 4)
        if abs(lvl - price) <= margin:
            levels.append(lvl)

    return sorted(set(levels))


def find_confluence_zones(
    levels: dict,
    price: float,
    threshold_pips: int = 10,
) -> list[dict]:
    """
    Identify price zones where multiple key levels cluster together.

    Plain English: when PDH, a weekly high, and a Fibonacci level all sit
                   within 10 pips of each other, that is not three separate
                   levels — it is one high-conviction zone. This function
                   finds those clusters and ranks them by strength.

    Args:
        levels         : levels dict from get_key_levels() or last_run.json
        price          : current price (used to label zone as support/resistance)
        threshold_pips : levels within this many pips are grouped together

    Returns list of dicts, sorted by confluence count descending:
        zone_price   : centre price of the cluster
        count        : number of levels in the cluster
        names        : list of level names in the cluster
        distance_pips: pips from current price to zone centre
        side         : "RESISTANCE" | "SUPPORT" | "AT"
    """
    threshold = threshold_pips * 0.0001

    # Flatten to (name, price) pairs — skip non-numeric and session_name
    flat: list[tuple[str, float]] = []
    for k, v in levels.items():
        if isinstance(v, (int, float)) and v > 0 and k != "session_name":
            flat.append((k, round(float(v), 5)))

    if not flat:
        return []

    # Add round numbers to the pool so they can form confluences too
    round_levels = get_round_number_levels(price)
    for rl in round_levels:
        flat.append((f"round_{rl:.4f}", rl))

    # Greedy clustering: walk sorted list, group within threshold
    flat.sort(key=lambda x: x[1])
    clusters: list[list[tuple[str, float]]] = []
    current_cluster: list[tuple[str, float]] = [flat[0]]

    for name, lvl in flat[1:]:
        if lvl - current_cluster[-1][1] <= threshold:
            current_cluster.append((name, lvl))
        else:
            clusters.append(current_cluster)
            current_cluster = [(name, lvl)]
    clusters.append(current_cluster)

    # Build output — only return clusters with 2+ levels
    zones = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        zone_price = round(sum(v for _, v in cluster) / len(cluster), 5)
        dist_pips  = round((zone_price - price) * 10000, 1)
        if dist_pips > 5:
            side = "RESISTANCE"
        elif dist_pips < -5:
            side = "SUPPORT"
        else:
            side = "AT"
        zones.append({
            "zone_price":    zone_price,
            "count":         len(cluster),
            "names":         [n for n, _ in cluster],
            "distance_pips": dist_pips,
            "side":          side,
        })

    return sorted(zones, key=lambda z: z["count"], reverse=True)
