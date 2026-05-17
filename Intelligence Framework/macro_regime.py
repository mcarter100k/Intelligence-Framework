"""
macro_regime.py

Dalio growth-inflation quadrant filter for GBP/AUD.

Before any technical signal is evaluated, this module positions both
currencies within the global macro cycle. Growth and inflation direction
determine which currency has the structural macro tailwind.

Quadrants (Dalio All-Weather framework):
  REFLATION   — Growth up,   Inflation up   → AUD commodity bid  → BEARISH GBP/AUD
  GOLDILOCKS  — Growth up,   Inflation down → Risk appetite high → BEARISH GBP/AUD
  STAGFLATION — Growth down, Inflation up   → AUD demand falls   → BULLISH GBP/AUD
  DEFLATION   — Growth down, Inflation flat/down → Risk-off       → BULLISH GBP/AUD
  TRANSITIONAL — Mixed signals              → NEUTRAL

Data: re-uses already-fetched cross_market and news layers. No new API calls.
"""

from __future__ import annotations
from typing import Dict, List, Tuple


def get_macro_regime(cross: Dict, news: Dict) -> Dict:
    """
    Classify current macro regime from cross_market and news data.
    Returns quadrant, GBP/AUD bias, and a direction-agnostic magnitude (0–12)
    used by decision_engine to boost or reduce conviction.
    """
    growth_score, growth_factors       = _growth_score(cross, news)
    inflation_score, inflation_factors = _inflation_score(cross, news)
    quadrant                           = _classify_quadrant(growth_score, inflation_score)
    gbpaud_bias, magnitude, narrative  = _quadrant_gbpaud(quadrant, growth_score, inflation_score)

    return {
        "quadrant":            quadrant,
        "growth_direction":    "UP" if growth_score > 0 else "DOWN" if growth_score < 0 else "FLAT",
        "inflation_direction": "UP" if inflation_score > 0 else "DOWN" if inflation_score < 0 else "FLAT",
        "growth_score":        round(growth_score, 2),
        "inflation_score":     round(inflation_score, 2),
        "growth_factors":      growth_factors,
        "inflation_factors":   inflation_factors,
        "gbpaud_bias":         gbpaud_bias,
        "magnitude":           magnitude,
        "narrative":           narrative,
    }


# ── Growth impulse ────────────────────────────────────────────────────────────

def _growth_score(cross: Dict, news: Dict) -> Tuple[float, List[str]]:
    """
    Score global growth momentum from cross-market proxies + calendar releases.
    > 0 = growth accelerating. < 0 = growth decelerating.
    """
    score, factors = 0.0, []

    bhp = cross.get("bhp_change")
    if bhp is not None:
        if   bhp >  1.0: score += 2.0; factors.append(f"Iron ore/AUD +{bhp:.2f}% — strong growth demand")
        elif bhp >  0.3: score += 1.0; factors.append(f"Iron ore/AUD +{bhp:.2f}% — mild growth signal")
        elif bhp < -1.0: score -= 2.0; factors.append(f"Iron ore/AUD {bhp:.2f}% — growth demand falling")
        elif bhp < -0.3: score -= 1.0; factors.append(f"Iron ore/AUD {bhp:.2f}% — mild growth drag")

    sp = cross.get("sp500_change")
    if sp is not None:
        if   sp >  1.0: score += 2.0; factors.append(f"S&P500 +{sp:.2f}% — equity markets pricing growth")
        elif sp >  0.5: score += 1.0; factors.append(f"S&P500 +{sp:.2f}% — mild equity strength")
        elif sp < -1.0: score -= 2.0; factors.append(f"S&P500 {sp:.2f}% — equity sell-off, growth fears")
        elif sp < -0.5: score -= 1.0; factors.append(f"S&P500 {sp:.2f}% — mild equity weakness")

    for ev in _released_events(news, ["PMI", "Manufacturing", "Services", "GDP", "Retail Sales"]):
        tb  = (ev.get("trade_bias") or "").upper()
        ccy = ev.get("currency", "")
        if ccy in ("GBP", "AUD"):
            if "BULLISH" in tb:
                score += 1.5; factors.append(f"{ccy} {ev['event']}: beat — growth positive")
            elif "BEARISH" in tb:
                score -= 1.5; factors.append(f"{ccy} {ev['event']}: miss — growth negative")

    return score, factors


# ── Inflation impulse ─────────────────────────────────────────────────────────

def _inflation_score(cross: Dict, news: Dict) -> Tuple[float, List[str]]:
    """
    Score inflation momentum from gold and calendar releases.
    > 0 = inflation rising. < 0 = inflation falling.
    """
    score, factors = 0.0, []

    gold = cross.get("gold_change")
    if gold is not None:
        if   gold >  1.0: score += 2.0; factors.append(f"Gold +{gold:.2f}% — inflation expectations rising")
        elif gold >  0.3: score += 1.0; factors.append(f"Gold +{gold:.2f}% — mild inflation signal")
        elif gold < -1.0: score -= 2.0; factors.append(f"Gold {gold:.2f}% — inflation expectations falling")
        elif gold < -0.3: score -= 1.0; factors.append(f"Gold {gold:.2f}% — mild deflation signal")

    dxy = cross.get("dxy_change")
    if dxy is not None:
        if   dxy >  0.3: score -= 0.5; factors.append(f"Strong USD ({dxy:+.2f}%) — global inflation compressed")
        elif dxy < -0.3: score += 0.5; factors.append(f"Weak USD ({dxy:+.2f}%) — global inflation elevated")

    for ev in _released_events(news, ["CPI", "Inflation", "PPI", "PCE", "RPI"]):
        tb  = (ev.get("trade_bias") or "").upper()
        ccy = ev.get("currency", "")
        if ccy in ("GBP", "AUD"):
            if "BULLISH" in tb:
                score += 1.5; factors.append(f"{ccy} {ev['event']}: hot — inflation rising")
            elif "BEARISH" in tb:
                score -= 1.5; factors.append(f"{ccy} {ev['event']}: miss — inflation cooling")

    return score, factors


def _released_events(news: Dict, keywords: List[str]) -> List[Dict]:
    return [
        ev for ev in news.get("events", [])
        if ev.get("status") == "released"
        and any(kw.upper() in ev.get("event", "").upper() for kw in keywords)
    ]


# ── Quadrant classification ───────────────────────────────────────────────────

def _classify_quadrant(growth: float, inflation: float) -> str:
    g_up = growth    >= 1.0
    g_dn = growth    <= -1.0
    i_up = inflation >= 0.5
    i_dn = inflation <= -0.5

    if g_up and i_up: return "REFLATION"
    if g_up and i_dn: return "GOLDILOCKS"
    if g_dn and i_up: return "STAGFLATION"
    if g_dn:          return "DEFLATION"
    return "TRANSITIONAL"


# ── GBP/AUD implication ───────────────────────────────────────────────────────

def _quadrant_gbpaud(
    quadrant: str, growth: float, inflation: float
) -> Tuple[str, int, str]:
    """
    Returns (gbpaud_bias, magnitude, narrative).
    magnitude is 0–12 and direction-agnostic — decision_engine applies the sign
    based on whether the macro bias aligns with or opposes the trade direction.
    """
    strength = min(abs(growth) + abs(inflation), 6.0) / 6.0  # 0–1

    if quadrant == "REFLATION":
        return (
            "BEARISH",
            int(12 * strength),
            "REFLATION — growth and inflation both rising. AUD benefits as a commodity "
            "currency; iron ore demand supports AUD. Macro favours SHORT GBP/AUD.",
        )
    if quadrant == "GOLDILOCKS":
        return (
            "BEARISH",
            int(10 * strength),
            "GOLDILOCKS — growth rising, inflation contained. Risk appetite high; AUD "
            "outperforms in risk-on environments. Macro favours SHORT GBP/AUD.",
        )
    if quadrant == "STAGFLATION":
        return (
            "BULLISH",
            int(8 * strength),
            "STAGFLATION — growth falling while inflation rises. AUD loses its commodity "
            "demand bid while inflation erodes real yields. Macro favours LONG GBP/AUD.",
        )
    if quadrant == "DEFLATION":
        return (
            "BULLISH",
            int(12 * strength),
            "DEFLATION — growth and inflation both falling. Risk-off: AUD falls harder "
            "than GBP in deflationary environments. Macro strongly favours LONG GBP/AUD.",
        )
    return (
        "NEUTRAL",
        0,
        "TRANSITIONAL — growth and inflation signals are mixed or insufficient. "
        "No strong macro quadrant override on the technical view.",
    )
