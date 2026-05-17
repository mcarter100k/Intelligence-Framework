"""
trade_logic.py
──────────────
Derives a directional bias for GBP/AUD from a single released economic print.

Rules
─────
•  GBP event beats forecast  →  GBP strengthens  →  GBPAUD BULLISH
•  GBP event misses forecast →  GBP weakens      →  GBPAUD BEARISH
•  AUD event beats forecast  →  AUD strengthens  →  GBPAUD BEARISH
•  AUD event misses forecast →  AUD weakens      →  GBPAUD BULLISH

"Beats" depends on the indicator:
  - For Unemployment / Jobless Claims: lower is better (inverted)
  - For everything else: higher is better
"""

from typing import Optional


# Indicators where a *lower* actual is the positive surprise
_INVERTED_INDICATORS = {
    "unemployment",
    "jobless",
    "claimant",
    "layoff",
}


def _to_float(raw: str) -> Optional[float]:
    """
    Parse a formatted economic string to float.
    Handles: %, K, M, B suffixes, negative values, missing data.
    """
    if not raw:
        return None
    cleaned = (
        raw.strip()
        .replace("%", "")
        .replace(",", "")
        .upper()
    )
    # Expand shorthand suffixes BEFORE calling float()
    multiplier = 1
    if cleaned.endswith("B"):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _is_inverted(event_name: str) -> bool:
    name_lower = event_name.lower()
    return any(kw in name_lower for kw in _INVERTED_INDICATORS)


def analyze_impact(event: str, actual: str, forecast: str, currency: str = "GBP") -> str:
    """
    Return a plain-English directional bias string for GBP/AUD.

    Parameters
    ----------
    event    : event name (e.g. "CPI YoY", "Unemployment Rate")
    actual   : released actual value as string
    forecast : consensus forecast as string
    currency : which currency the event belongs to ("GBP" or "AUD")
    """
    actual_val = _to_float(actual)
    forecast_val = _to_float(forecast)

    if actual_val is None or forecast_val is None:
        return "⚠️  Missing data — no bias."

    inverted = _is_inverted(event)
    # "Beat" means actual > forecast for normal indicators,
    # actual < forecast for inverted ones (lower unemployment = good).
    if inverted:
        beat = actual_val < forecast_val
    else:
        beat = actual_val > forecast_val

    # Exact match — no surprise, should be neutral not a miss
    if actual_val == forecast_val:
        return f"Result matched forecast exactly ({actual_val}) — no surprise, neutral for GBP/AUD"

    diff = actual_val - forecast_val
    # Smart formatting: avoid scientific notation for large numbers
    abs_diff = abs(diff)
    if abs_diff >= 1_000_000_000:
        diff_str = f"{'+' if diff > 0 else ''}{diff/1_000_000_000:.2f}B"
    elif abs_diff >= 1_000_000:
        diff_str = f"{'+' if diff > 0 else ''}{diff/1_000_000:.2f}M"
    elif abs_diff >= 1_000:
        diff_str = f"{'+' if diff > 0 else ''}{diff/1_000:.1f}K"
    elif abs_diff >= 1:
        diff_str = f"{diff:+.2f}"
    else:
        diff_str = f"{diff:+.2f}"

    # Map currency × beat/miss → GBP/AUD direction
    if currency.upper() == "GBP":
        if beat:
            return (
                f"✅ GBP beat forecast ({diff_str}) → "
                "GBP strengthens → GBPAUD BULLISH bias"
            )
        else:
            return (
                f"❌ GBP missed forecast ({diff_str}) → "
                "GBP weakens → GBPAUD BEARISH bias"
            )
    elif currency.upper() == "AUD":
        if beat:
            return (
                f"✅ AUD beat forecast ({diff_str}) → "
                "AUD strengthens → GBPAUD BEARISH bias"
            )
        else:
            return (
                f"❌ AUD missed forecast ({diff_str}) → "
                "AUD weakens → GBPAUD BULLISH bias"
            )
    else:
        return f"⚠️  Unknown currency '{currency}' — no bias mapped."
