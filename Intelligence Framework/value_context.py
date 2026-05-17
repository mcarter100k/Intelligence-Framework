"""
value_context.py

Answers the question every professional trader asks before entering:
Is price cheap or expensive RIGHT NOW?

Three measures of value:
  1. Fair value (20-day average price)
     Price tends to gravitate back to its recent average.
     Above it = PREMIUM (expensive). Below it = DISCOUNT (cheap).

  2. Weekly range midpoint
     The exact middle of this week's high/low range.
     Upper half of the week = expensive. Lower half = cheap.

  3. Daily range midpoint
     The middle of today's intraday range so far.
     At the top of today's range = premium. Bottom = discount.

Overall verdict combines all three into one label:
  STRONG PREMIUM  - all three say expensive - best location to short
  PREMIUM         - 2 of 3 say expensive
  FAIR VALUE      - mixed, near equilibrium
  DISCOUNT        - 2 of 3 say cheap - best location to buy
  STRONG DISCOUNT - all three say cheap

No new dependencies - all inputs come from existing modules.
"""

from __future__ import annotations
from typing import Dict, Optional


def get_value_context(
    current_price: float,
    daily_closes: list,
    pwh: float,           # this week's high (from liquidity_context)
    pwl: float,           # this week's low  (from liquidity_context)
    today_high: float,    # today's intraday high (from regime_detection)
    today_low: float,     # today's intraday low  (from regime_detection)
    lookback: int = 10,   # 10-day average — recent enough to be relevant
) -> Dict:
    """
    Calculate value context from existing data.
    All inputs come from modules already running — no extra API calls.
    """
    try:
        if not daily_closes or len(daily_closes) < lookback:
            return _error_result("Not enough daily data for value context")

        # ── Measure 1: Fair value (10-day average) ────────────────────────────
        # Use 10-day average — close enough to reflect current market level
        # If price has trended strongly, even 10 days can lag; cap distortion at 150 pips
        avg_10    = round(sum(daily_closes[-lookback:]) / lookback, 4)
        diff_fv   = round((current_price - avg_10) * 10000)  # in pips

        # If the average is more than 150 pips away, use 5-day (very recent)
        if abs(diff_fv) > 150 and len(daily_closes) >= 5:
            avg_5   = round(sum(daily_closes[-5:]) / 5, 4)
            diff_fv = round((current_price - avg_5) * 10000)
            avg_10  = avg_5  # replace for display
            lookback_label = "5-day"
        else:
            lookback_label = "10-day"

        if diff_fv > 20:
            fv_zone  = "PREMIUM"
            fv_label = f"Price is {abs(diff_fv)} pips ABOVE {lookback_label} average ({avg_10}) — trading at a premium"
        elif diff_fv < -20:
            fv_zone  = "DISCOUNT"
            fv_label = f"Price is {abs(diff_fv)} pips BELOW {lookback_label} average ({avg_10}) — trading at a discount"
        else:
            fv_zone  = "FAIR VALUE"
            fv_label = f"Price is within 20 pips of {lookback_label} average ({avg_10}) — near fair value"

        # ── Measure 2: Weekly range midpoint ─────────────────────────────────
        weekly_mid = round((pwh + pwl) / 2, 4)
        weekly_rng = round((pwh - pwl) * 10000)
        diff_wk    = round((current_price - weekly_mid) * 10000)  # pips from mid
        pct_wk     = round(min(100, max(0,
                     (current_price - pwl) / (pwh - pwl) * 100)), 1) if pwh != pwl else 50.0

        if current_price > pwh:
            wk_zone  = "PREMIUM"
            wk_label = f"Price is ABOVE this week's high — extended premium"
        elif current_price < pwl:
            wk_zone  = "DISCOUNT"
            wk_label = f"Price is BELOW this week's low — deep discount zone"
        elif diff_wk > 0:
            wk_zone  = "PREMIUM"
            wk_label = (
                f"Price is in the UPPER half of this week's range "
                f"({pct_wk:.0f}% from the bottom) — premium zone this week"
            )
        else:
            wk_zone  = "DISCOUNT"
            wk_label = (
                f"Price is in the LOWER half of this week's range "
                f"({pct_wk:.0f}% from the bottom) — discount zone this week"
            )

        # ── Measure 3: Daily range midpoint ───────────────────────────────────
        daily_rng  = round((today_high - today_low) * 10000)
        daily_mid  = round((today_high + today_low) / 2, 4)

        # Guard: if today's range is less than 30 pips, the bar may be incomplete
        # (e.g. first hour of new day) — skip this measure
        if daily_rng < 30 or today_high <= today_low:
            dy_zone  = "FAIR VALUE"
            dy_label = "Today's range too small to assess — session may just be starting"
            pct_dy   = 50.0
            diff_dy  = 0
        else:
            diff_dy  = round((current_price - daily_mid) * 10000)
            pct_dy   = round(min(100, max(0,
                       (current_price - today_low) / (today_high - today_low) * 100)), 1)

            if diff_dy > 0:
                dy_zone  = "PREMIUM"
                dy_label = (
                    f"Price is in the UPPER half of today's range "
                    f"({pct_dy:.0f}% from today's low) — expensive vs today's action"
                )
            else:
                dy_zone  = "DISCOUNT"
                dy_label = (
                    f"Price is in the LOWER half of today's range "
                    f"({pct_dy:.0f}% from today's low) — cheap vs today's action"
                )

        # ── Overall verdict ───────────────────────────────────────────────────
        zones      = [fv_zone, wk_zone, dy_zone]
        premium_ct = zones.count("PREMIUM")
        discount_ct = zones.count("DISCOUNT")

        if premium_ct == 3:
            verdict      = "STRONG PREMIUM"
            verdict_note = (
                "All three measures agree — price is EXPENSIVE right now. "
                "Best location to look for shorts. Avoid buying here."
            )
            verdict_bias = "BEARISH"
        elif premium_ct == 2:
            verdict      = "PREMIUM"
            verdict_note = (
                "Price is trading in a premium zone — slightly expensive. "
                "Better location for shorts than longs."
            )
            verdict_bias = "BEARISH"
        elif discount_ct == 3:
            verdict      = "STRONG DISCOUNT"
            verdict_note = (
                "All three measures agree — price is CHEAP right now. "
                "Best location to look for longs. Avoid selling here."
            )
            verdict_bias = "BULLISH"
        elif discount_ct == 2:
            verdict      = "DISCOUNT"
            verdict_note = (
                "Price is trading in a discount zone — slightly cheap. "
                "Better location for longs than shorts."
            )
            verdict_bias = "BULLISH"
        else:
            verdict      = "FAIR VALUE"
            verdict_note = (
                "Mixed signals — price is near equilibrium. "
                "No clear premium or discount. Location is neutral."
            )
            verdict_bias = "NEUTRAL"

        # ── Trade alignment note ──────────────────────────────────────────────
        # Tell the trader whether their current bias aligns with location
        return {
            # Overall
            "verdict":       verdict,
            "verdict_note":  verdict_note,
            "verdict_bias":  verdict_bias,

            # Measure 1 — fair value
            "fair_value":    avg_10,
            "lookback_label": lookback_label,
            "fv_zone":       fv_zone,
            "fv_diff_pips":  diff_fv,
            "fv_label":      fv_label,

            # Measure 2 — weekly midpoint
            "weekly_mid":    weekly_mid,
            "weekly_range":  weekly_rng,
            "wk_zone":       wk_zone,
            "wk_pct":        pct_wk,
            "wk_label":      wk_label,

            # Measure 3 — daily midpoint
            "daily_mid":     daily_mid,
            "daily_range":   daily_rng,
            "dy_zone":       dy_zone,
            "dy_pct":        pct_dy,
            "dy_label":      dy_label,

            "error": None,
        }

    except Exception as e:
        return _error_result(f"Value context error: {e}")


def _error_result(msg: str) -> Dict:
    return {
        "verdict":      "UNKNOWN",
        "verdict_note": msg,
        "verdict_bias": "NEUTRAL",
        "fair_value":   None,
        "fv_zone":      "UNKNOWN",
        "fv_diff_pips": None,
        "lookback_label": "recent",
        "fv_label":     msg,
        "weekly_mid":   None,
        "weekly_range": None,
        "wk_zone":      "UNKNOWN",
        "wk_pct":       None,
        "wk_label":     msg,
        "daily_mid":    None,
        "daily_range":  None,
        "dy_zone":      "UNKNOWN",
        "dy_pct":       None,
        "dy_label":     msg,
        "error":        msg,
    }


if __name__ == "__main__":
    # Quick test with sample data
    test_closes = [1.91, 1.912, 1.915, 1.918, 1.916, 1.913, 1.920, 1.922,
                   1.919, 1.921, 1.918, 1.915, 1.912, 1.916, 1.919, 1.921,
                   1.923, 1.920, 1.918, 1.921]
    result = get_value_context(
        current_price=1.9223,
        daily_closes=test_closes,
        pwh=1.9399,
        pwl=1.9107,
        today_high=1.9265,
        today_low=1.9107,
    )
    print(f"Verdict      : {result['verdict']}")
    print(f"Fair value   : {result['fair_value']}  ({result['fv_zone']})")
    print(f"Weekly zone  : {result['wk_zone']}  ({result['wk_pct']}% from low)")
    print(f"Daily zone   : {result['dy_zone']}  ({result['dy_pct']}% from low)")
    print(f"\n{result['verdict_note']}")
