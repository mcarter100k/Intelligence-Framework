"""
liquidity_context.py
─────────────────────
Identifies key price levels for GBP/AUD and detects liquidity sweeps.
Uses yfinance for free OHLC data — no API key needed.

Key levels explained:
  Yesterday's high/low  : Where price stopped yesterday (most-watched short-term levels)
  This week's high/low  : The outer boundaries of this week's range
  Equal highs/lows      : Price touched the same level 2+ times = pool of orders waiting there
  Sweep                 : Price wicked past a key level then closed back — smart money move
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from oanda_feed import get_daily_bars, get_live_price, is_configured


PAIR_TICKER  = "GBP_AUD"
_EQ_TOLERANCE = 0.0009   # 9 pips — two touches within this are treated as "equal"


def get_liquidity_context(ticker: str = PAIR_TICKER) -> Dict:
    if not is_configured():
        return _error_result("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")

    try:
        raw = get_daily_bars(pair=ticker, count=30)
    except Exception as exc:
        return _error_result(f"Download failed: {exc}")

    if raw is None or raw.empty or len(raw) < 5:
        return _error_result("Not enough price history returned")

    if hasattr(raw.columns, "levels"):
        raw.columns = raw.columns.get_level_values(0)

    closes = raw["Close"]
    highs  = raw["High"]
    lows   = raw["Low"]

    # Pip scale for this instrument — JPY crosses use 0.01, others 0.0001.
    # Equal-level clustering and sweep dedup must scale with the pip size, or
    # a JPY pair (price ~217) would treat every level as "equal".
    _pip    = 0.01 if ticker.replace("_", "").endswith("JPY") else 0.0001
    _eq_tol = 9 * _pip   # ~9 pips — two touches within this count as "equal"
    _dedup  = 1 * _pip   # ~1 pip — levels closer than this are the same level

    # Live price: fetch for THIS instrument, fall back to last close
    try:
        _oanda_price = get_live_price(pair=ticker) if is_configured() else None
    except Exception:
        _oanda_price = None
    current_price = _oanda_price if _oanda_price else float(closes.iloc[-1])
    _price_source = "OANDA live" if _oanda_price else "OANDA (last close)"
    pdh = float(highs.iloc[-2])
    pdl = float(lows.iloc[-2])
    pwh = float(highs.iloc[-7:-1].max())
    pwl = float(lows.iloc[-7:-1].min())

    today_high  = float(highs.iloc[-1])
    today_low   = float(lows.iloc[-1])
    today_close = float(closes.iloc[-1])

    recent_highs = [float(h) for h in highs.iloc[-20:]]
    recent_lows  = [float(l) for l in lows.iloc[-20:]]
    equal_highs  = _find_equal_levels(recent_highs, _eq_tol)
    equal_lows   = _find_equal_levels(recent_lows, _eq_tol)

    # ── Sweep detection — deduplicate levels first ────────────────────────────
    # If PDH and PWH are the same price (within 1 pip), only report it once
    sweep_events: List[str] = []
    swept_up    = False
    swept_down  = False

    checked_highs: List[float] = []
    for level, name in [(pdh, "Yesterday's High"), (pwh, "This Week's High")]:
        # Skip if we already reported a sweep at virtually the same level
        if any(abs(level - seen) < _dedup for seen in checked_highs):
            continue
        checked_highs.append(level)
        if today_high > level and today_close < level:
            swept_up = True
            sweep_events.append(
                f"🔴 {name} ({level:.4f}) was swept — price pushed above it then fell back below.\n"
                f"     This suggests the move up was a fake-out to grab stop orders above that level."
            )

    checked_lows: List[float] = []
    for level, name in [(pdl, "Yesterday's Low"), (pwl, "This Week's Low")]:
        if any(abs(level - seen) < _dedup for seen in checked_lows):
            continue
        checked_lows.append(level)
        if today_low < level and today_close > level:
            swept_down = True
            sweep_events.append(
                f"🟢 {name} ({level:.4f}) was swept — price pushed below it then recovered above.\n"
                f"     This suggests the move down was a fake-out to grab stop orders below that level."
            )

    if not sweep_events:
        sweep_note = "No sweeps detected today — price has not broken and reversed any key level yet."
    else:
        sweep_note = "\n  ".join(sweep_events)

    # ── What does this mean overall? ──────────────────────────────────────────
    if swept_down and not swept_up:
        bias_note = (
            "A low was swept and price recovered — this is a BULLISH signal.\n"
            "  Banks may have collected sell orders below that level before pushing price up.\n"
            "  Watch for confirmation on your charts before going long."
        )
    elif swept_up and not swept_down:
        bias_note = (
            "A high was swept and price rejected — this is a BEARISH signal.\n"
            "  Banks may have collected buy orders above that level before pushing price down.\n"
            "  Watch for confirmation on your charts before going short."
        )
    elif swept_up and swept_down:
        bias_note = (
            "Both a high AND a low were swept today — this is a mixed/indecision signal.\n"
            "  The market is hunting stops in both directions. Wait for a clear close\n"
            "  above or below a key level before committing to a direction."
        )
    else:
        all_pools = sorted(set([pdh, pdl, pwh, pwl] + equal_highs + equal_lows))
        nearest, pool_dir = _nearest(current_price, all_pools)
        if nearest:
            bias_note = (
                f"No sweep yet today. The nearest key level is {nearest:.4f} ({pool_dir} current price).\n"
                f"  Watch to see if price sweeps that level and reverses — that would be your signal."
            )
        else:
            bias_note = "No sweep yet. Watch the levels above and below for a potential move."

    all_pools   = sorted(set([pdh, pdl, pwh, pwl] + equal_highs + equal_lows))
    nearest, pool_dir = _nearest(current_price, all_pools)

    return {
        "current_price": round(current_price, 4),
        "price_source":  _price_source,
        "pdh":  round(pdh, 4),
        "pdl":  round(pdl, 4),
        "pwh":  round(pwh, 4),
        "pwl":  round(pwl, 4),
        "equal_highs":  [round(v, 4) for v in equal_highs],
        "equal_lows":   [round(v, 4) for v in equal_lows],
        "sweep_up":     swept_up,
        "sweep_down":   swept_down,
        "sweep_note":   sweep_note,
        "nearest_pool": round(nearest, 4) if nearest else None,
        "pool_direction": pool_dir,
        "bias_note":    bias_note,
        "error":        None,
    }


def _find_equal_levels(prices: List[float], tol: float = _EQ_TOLERANCE) -> List[float]:
    clusters: List[float] = []
    visited = [False] * len(prices)
    for i, p in enumerate(prices):
        if visited[i]:
            continue
        group = [p]
        for j in range(i + 1, len(prices)):
            if not visited[j] and abs(prices[j] - p) <= tol:
                group.append(prices[j])
                visited[j] = True
        if len(group) >= 2:
            clusters.append(round(sum(group) / len(group), 4))
        visited[i] = True
    return clusters


def _nearest(price: float, levels: List[float]) -> Tuple[Optional[float], str]:
    if not levels:
        return None, ""
    above = [l for l in levels if l > price]
    below = [l for l in levels if l < price]
    candidates = []
    if above: candidates.append((above[0],  "above"))
    if below: candidates.append((below[-1], "below"))
    if not candidates:
        return None, ""
    return min(candidates, key=lambda x: abs(x[0] - price))


def _error_result(msg: str) -> Dict:
    return {
        "current_price": None,
        "pdh": None, "pdl": None, "pwh": None, "pwl": None,
        "equal_highs": [], "equal_lows": [],
        "sweep_up": False, "sweep_down": False,
        "sweep_note": msg,
        "nearest_pool": None, "pool_direction": "",
        "bias_note": "Price level data unavailable.",
        "error": msg,
    }


if __name__ == "__main__":
    data = get_liquidity_context()
    for k, v in data.items():
        print(f"{k}: {v}")
