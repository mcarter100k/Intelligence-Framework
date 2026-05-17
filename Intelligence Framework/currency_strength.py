"""
currency_strength.py

Scores GBP and AUD relative strength by measuring all 8 major currencies
against each other. Using only 2 currencies in the basket was the bug —
the normalisation always pushed them to opposite extremes (+50/-50)
regardless of actual market movement.

Fix: score all 8 majors (USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD),
then report where GBP and AUD rank within that full picture.

Score range: -100 (weakest of the 8) to +100 (strongest of the 8)
A score of 0 means the currency is performing exactly average today.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional

# yfinance removed — OANDA used for currency pair data

# All 8 major currencies
_ALL_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

# We measure each currency against USD as the common denominator.
# For USD itself we invert the other pairs.
# Format: ticker -> (base, quote)
# Returns for base are positive if base strengthened vs quote.
_BASKET_VS_USD = {
    "EUR_USD": ("EUR", "USD"),
    "GBP_USD": ("GBP", "USD"),
    "USD_JPY": ("USD", "JPY"),   # inverted — USD is base here
    "USD_CHF": ("USD", "CHF"),   # inverted
    "USD_CAD": ("USD", "CAD"),   # inverted
    "AUD_USD": ("AUD", "USD"),
    "NZD_USD": ("NZD", "USD"),
}

# USD is derived by inverting EUR, GBP, AUD, NZD returns and averaging with direct pairs


def get_currency_strength(currencies: List[str] = None) -> Dict:
    """
    Return strength scores for the requested currencies.
    Always calculates all 8 majors internally for correct normalisation.

    Returns dict with:
        GBP: float (-100 to +100)
        AUD: float (-100 to +100)
        all_scores: dict of all 8 currencies
        differential: GBP - AUD
        bias: BULLISH / BEARISH / NEUTRAL
        confidence: 0-100
        error: None or error string
    """
    if currencies is None:
        currencies = ["GBP", "AUD"]

    from oanda_feed import get_daily_bars, is_configured
    if not is_configured():
        return _fallback(currencies, "OANDA not configured")

    # Fetch last 3 days for each pair to compute 1-day return
    try:
        ticker_returns: Dict[str, float] = {}
        for instrument in _BASKET_VS_USD.keys():
            try:
                df = get_daily_bars(pair=instrument, count=3)
                if df is None or len(df) < 2:
                    continue
                prev = float(df["Close"].iloc[-2])
                last = float(df["Close"].iloc[-1])
                if prev != 0:
                    ticker_returns[instrument] = (last - prev) / prev * 100
            except Exception:
                continue
    except Exception as exc:
        return _fallback(currencies, f"OANDA fetch error: {exc}")

    if not ticker_returns:
        return _fallback(currencies, "No valid return data from OANDA")

    # Build per-currency raw scores
    # For pairs where USD is base (USDJPY, USDCHF, USDCAD), a positive return
    # means USD strengthened, so we invert for the quote currency
    raw_scores: Dict[str, List[float]] = {c: [] for c in _ALL_CURRENCIES}

    for ticker, ret in ticker_returns.items():
        if ticker not in _BASKET_VS_USD:
            continue
        base, quote = _BASKET_VS_USD[ticker]
        raw_scores[base].append(ret)       # base gained ret%
        raw_scores[quote].append(-ret)     # quote lost ret% (inverse)

    # Average across all legs for each currency
    avg_scores: Dict[str, float] = {}
    for ccy, scores in raw_scores.items():
        if scores:
            avg_scores[ccy] = sum(scores) / len(scores)
        else:
            avg_scores[ccy] = 0.0

    if not avg_scores:
        return _fallback(currencies, "Could not compute any currency scores")

    # Normalise: rank within the 8 currencies, scale to -100 to +100
    # Method: z-score style — subtract mean, divide by std, scale
    vals = list(avg_scores.values())
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = variance ** 0.5

    if std > 0:
        normalised = {
            ccy: round(((score - mean) / std) * 33, 1)  # *33 puts typical range in -100/+100
            for ccy, score in avg_scores.items()
        }
        # Clamp to -100/+100
        normalised = {ccy: max(-100, min(100, s)) for ccy, s in normalised.items()}
    else:
        # All currencies moved identically — flat market
        normalised = {ccy: 0.0 for ccy in avg_scores}

    # Build result
    gbp_score = normalised.get("GBP", 0.0)
    aud_score = normalised.get("AUD", 0.0)
    diff      = round(gbp_score - aud_score, 1)

    if diff > 10:
        bias = "BULLISH"
    elif diff < -10:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    confidence = min(100, int(abs(diff)))

    # Sort all currencies for display (strongest to weakest)
    ranked = sorted(normalised.items(), key=lambda x: x[1], reverse=True)

    result = {
        "GBP":          gbp_score,
        "AUD":          aud_score,
        "all_scores":   dict(ranked),
        "ranking":      [c for c, _ in ranked],
        "differential": diff,
        "bias":         bias,
        "confidence":   confidence,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source":       "OANDA (1-day vs USD basket, 7 majors)",
        "error":        None,
    }

    return result


def _fallback(currencies: List[str], reason: str = "") -> Dict:
    return {
        "GBP":          0.0,
        "AUD":          0.0,
        "all_scores":   {},
        "ranking":      [],
        "differential": 0.0,
        "bias":         "NEUTRAL",
        "confidence":   0,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source":       "fallback",
        "error":        reason or "Unavailable",
    }


if __name__ == "__main__":
    data = get_currency_strength(["GBP", "AUD"])
    if data["error"]:
        print(f"Error: {data['error']}")
    else:
        print("\nAll 8 majors ranked (strongest to weakest today):")
        for i, (ccy, score) in enumerate(data["all_scores"].items(), 1):
            marker = " <-- GBP" if ccy == "GBP" else " <-- AUD" if ccy == "AUD" else ""
            print(f"  {i}. {ccy}: {score:+.1f}{marker}")
        print(f"\nGBP vs AUD differential : {data['differential']:+.1f}")
        print(f"Bias for GBP/AUD        : {data['bias']}")
        print(f"Confidence              : {data['confidence']}/100")
