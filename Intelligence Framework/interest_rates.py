"""
interest_rates.py

Tracks the Bank of England (BoE) and Reserve Bank of Australia (RBA)
interest rates, their policy stances, and the differential between them.

Why this matters for GBP/AUD:
  - Higher interest rates attract foreign capital → currency strengthens
  - If BoE rate > RBA rate, GBP has a yield advantage over AUD
  - If the gap is widening (BoE hiking, RBA cutting) → bullish GBP/AUD
  - If the gap is narrowing (RBA hiking, BoE cutting) → bearish GBP/AUD
  - Central bank STANCE matters as much as the rate itself —
    a hawkish BoE (planning hikes) is bullish even before the hike happens

Data: hardcoded current rates + stance (updated manually each meeting).
      Central banks meet roughly every 6 weeks — update this file after each.

Last updated: March 2026
"""

from __future__ import annotations
from datetime import datetime, date
from typing import Dict


# ── Current rates and stance ───────────────────────────────────────────────────
# Update these after each central bank meeting.

CENTRAL_BANKS = {
    "BoE": {
        "full_name":        "Bank of England",
        "currency":         "GBP",
        "current_rate":     4.50,       # % — VERIFY: last confirmed cut Feb 2026; May meeting outcome unclear
        "previous_rate":    4.75,       # rate before the last change
        "last_change":      "cut",      # "cut", "hike", or "hold"
        "last_meeting":     "2026-05-08",
        "next_meeting":     "2026-06-18",
        "stance":           "dovish",   # "hawkish", "dovish", or "neutral"
        "stance_note": (
            "BoE cut rates in February 2026 from 4.75% to 4.50%. "
            "The MPC is cautious about further cuts given sticky services inflation. "
            "Market pricing suggests 1-2 more cuts in 2026."
        ),
        "rate_trend":       "cutting",  # "hiking", "cutting", or "holding"
    },
    "RBA": {
        "full_name":        "Reserve Bank of Australia",
        "currency":         "AUD",
        "current_rate":     4.35,       # % — hiked 25bp at May 6 meeting (third consecutive hike)
        "previous_rate":    4.10,       # rate before the last change
        "last_change":      "hike",     # "cut", "hike", or "hold"
        "last_meeting":     "2026-05-06",
        "next_meeting":     "2026-07-07",
        "stance":           "hawkish",  # "hawkish", "dovish", or "neutral"
        "stance_note": (
            "RBA hiked 25bp to 4.35% at its May 2026 meeting — third consecutive hike in 2026. "
            "Board cited material pickup in inflation in H2 2025 and higher fuel/commodity prices. "
            "Governor Bullock left door open to further hikes; vote was 8-1."
        ),
        "rate_trend":       "hiking",   # "hiking", "cutting", or "holding"
    },
}


def get_rate_differential() -> Dict:
    """
    Returns a structured dict with the rate differential analysis.

    Keys
    ----
    boe_rate          : current BoE rate (%)
    rba_rate          : current RBA rate (%)
    differential      : BoE rate - RBA rate (positive = GBP has yield advantage)
    differential_bias : BULLISH / BEARISH / NEUTRAL for GBP/AUD
    stance_bias       : bias from central bank stances (independent of current rate)
    overall_bias      : combined rate + stance bias
    boe               : full BoE data dict
    rba               : full RBA data dict
    summary           : plain-English one-paragraph summary
    error             : None
    """
    boe = CENTRAL_BANKS["BoE"]
    rba = CENTRAL_BANKS["RBA"]

    diff = round(boe["current_rate"] - rba["current_rate"], 2)

    # Rate differential bias
    # Positive diff = GBP has higher yield = attracts more capital = bullish GBP/AUD
    if diff > 0.5:
        diff_bias = "BULLISH"
        diff_note = (
            f"GBP has a {abs(diff):.2f}% yield advantage over AUD. "
            f"Higher UK rates attract capital to GBP — supports GBP/AUD going UP."
        )
    elif diff < -0.5:
        diff_bias = "BEARISH"
        diff_note = (
            f"AUD has a {abs(diff):.2f}% yield advantage over GBP. "
            f"Higher Australian rates attract capital to AUD — supports GBP/AUD going DOWN."
        )
    else:
        diff_bias = "NEUTRAL"
        diff_note = (
            f"BoE and RBA rates are close ({abs(diff):.2f}% gap). "
            f"Neither currency has a significant yield advantage right now."
        )

    # Stance bias — forward-looking (more important than current rate)
    # Hawkish BoE + dovish RBA = widening differential = very bullish
    # Dovish BoE + hawkish RBA = narrowing differential = very bearish
    boe_stance = boe["stance"]
    rba_stance = rba["stance"]

    stance_score = _stance_score(boe_stance) - _stance_score(rba_stance)

    if stance_score >= 2:
        stance_bias = "BULLISH"
        stance_note = (
            f"BoE is {boe_stance} while RBA is {rba_stance}. "
            f"The rate gap is likely to WIDEN — strongly bullish for GBP/AUD."
        )
    elif stance_score == 1:
        stance_bias = "BULLISH"
        stance_note = (
            f"BoE is {boe_stance}, RBA is {rba_stance}. "
            f"Rate gap may widen slightly — mildly bullish for GBP/AUD."
        )
    elif stance_score == -1:
        stance_bias = "BEARISH"
        stance_note = (
            f"RBA is {rba_stance}, BoE is {boe_stance}. "
            f"Rate gap may narrow — mildly bearish for GBP/AUD."
        )
    elif stance_score <= -2:
        stance_bias = "BEARISH"
        stance_note = (
            f"RBA is {rba_stance} while BoE is {boe_stance}. "
            f"The rate gap is likely to NARROW — strongly bearish for GBP/AUD."
        )
    else:
        stance_bias = "NEUTRAL"
        stance_note = (
            f"Both BoE ({boe_stance}) and RBA ({rba_stance}) have similar stances. "
            f"No clear directional pressure from central bank policy right now."
        )

    # Overall: combine rate differential + stance
    # Stance is more forward-looking so weight it slightly higher
    overall_votes = []
    if diff_bias == "BULLISH":   overall_votes.append(1)
    elif diff_bias == "BEARISH": overall_votes.append(-1)
    if stance_bias == "BULLISH":   overall_votes.append(1.5)
    elif stance_bias == "BEARISH": overall_votes.append(-1.5)

    overall_sum = sum(overall_votes)
    if overall_sum > 0.5:
        overall_bias = "BULLISH"
    elif overall_sum < -0.5:
        overall_bias = "BEARISH"
    else:
        overall_bias = "NEUTRAL"

    # Plain-English summary
    summary = _build_summary(boe, rba, diff, diff_bias, stance_bias, overall_bias)

    return {
        "boe_rate":         boe["current_rate"],
        "rba_rate":         rba["current_rate"],
        "differential":     diff,
        "differential_bias": diff_bias,
        "differential_note": diff_note,
        "stance_score":     stance_score,
        "stance_bias":      stance_bias,
        "stance_note":      stance_note,
        "overall_bias":     overall_bias,
        "boe":              boe,
        "rba":              rba,
        "summary":          summary,
        "error":            None,
        "stale_warning":    _check_rate_staleness(boe, rba),
    }


def _check_rate_staleness(boe: dict, rba: dict) -> str:
    """Check if rate data is likely stale based on next_meeting dates."""
    today = date.today()
    warnings = []
    for bank, data in [("BoE", boe), ("RBA", rba)]:
        nm = data.get("next_meeting", "")
        if nm:
            try:
                meeting_date = date.fromisoformat(nm)
                if meeting_date < today:
                    days_past = (today - meeting_date).days
                    warnings.append(
                        f"{bank}: scheduled meeting {nm} passed {days_past}d ago — "
                        f"rates may be outdated. Update interest_rates.py."
                    )
            except ValueError:
                pass
    return " | ".join(warnings) if warnings else ""


def _stance_score(stance: str) -> int:
    """Convert stance label to numeric score for comparison."""
    return {"hawkish": 2, "neutral": 0, "dovish": -1}.get(stance.lower(), 0)


def _build_summary(boe, rba, diff, diff_bias, stance_bias, overall_bias) -> str:
    direction = (
        "BULLISH for GBP/AUD" if overall_bias == "BULLISH"
        else "BEARISH for GBP/AUD" if overall_bias == "BEARISH"
        else "NEUTRAL for GBP/AUD"
    )
    return (
        f"The Bank of England rate is {boe['current_rate']}% and the RBA rate is "
        f"{rba['current_rate']}%, giving GBP a {abs(diff):.2f}% "
        f"{'advantage' if diff > 0 else 'disadvantage'} over AUD on yield. "
        f"The BoE is currently {boe['stance']} and the RBA is {rba['stance']}. "
        f"Overall the interest rate picture is {direction}."
    )


def format_rate_report(data: Dict) -> str:
    """Plain-English formatted string for display in the market brain."""
    if data.get("error"):
        return f"  Rate data unavailable: {data['error']}"

    boe = data["boe"]
    rba = data["rba"]

    lines = [
        f"  Bank of England (BoE) rate : {boe['current_rate']}%  [{boe['stance'].upper()}]",
        f"  {boe['stance_note']}",
        f"",
        f"  Reserve Bank of Australia  : {rba['current_rate']}%  [{rba['stance'].upper()}]",
        f"  {rba['stance_note']}",
        f"",
        f"  Rate differential (BoE - RBA) : {data['differential']:+.2f}%",
        f"  {data['differential_note']}",
        f"",
        f"  Forward-looking stance bias : {data['stance_bias']}",
        f"  {data['stance_note']}",
        f"",
        f"  Overall rate verdict : {data['overall_bias']} for GBP/AUD",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    data = get_rate_differential()
    print(format_rate_report(data))
    print(f"\nSummary: {data['summary']}")
