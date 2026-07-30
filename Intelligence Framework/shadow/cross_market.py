"""
cross_market.py

Cross-market context for GBP/AUD.
Data: OANDA (forex/gold) + Yahoo Finance JSON (VIX/SP500)
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple
from datetime import datetime

import requests
from oanda_feed import get_daily_bars as _oanda_bars, is_configured as _oanda_ok

_YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0"}

_OANDA_INSTRUMENTS = {
    "Gold":   "XAU_USD",  # Gold in USD
    "DXY":    "USD_CHF",  # USD proxy — invert for DXY direction
    "AUD":    "AUD_USD",  # Iron ore / commodity proxy + AUD leg
    "GBPUSD": "GBP_USD",  # GBP leg — needed for decomposition
}


def get_cross_market(instrument: str = "GBP_AUD") -> Dict:
    # This model is GBP/AUD-specific: it reads AUD as a commodity currency
    # (gold / iron-ore proxies) and maps risk-off → AUD-falls → BULLISH GBP/AUD.
    # That polarity is WRONG for other pairs (e.g. JPY is a safe-haven, so
    # risk-off strengthens JPY → GBP/JPY falls). Rather than contaminate a
    # non-AUD decision with GBP/AUD macro reasoning, contribute nothing and say
    # so. A pair-specific macro model is required before enabling such a pair.
    if instrument != "GBP_AUD":
        return _not_modelled(instrument)

    if not _oanda_ok():
        return _fallback("OANDA not configured")

    # ── Fetch OANDA returns ───────────────────────────────────────────────────
    instrument_returns: Dict[str, Optional[float]] = {}
    for name, instrument in _OANDA_INSTRUMENTS.items():
        try:
            df = _oanda_bars(pair=instrument, count=3)
            if df is not None and len(df) >= 2:
                prev = float(df["Close"].iloc[-2])
                last = float(df["Close"].iloc[-1])
                if prev != 0:
                    ret = (last - prev) / prev * 100
                    instrument_returns[name] = -ret if name == "DXY" else ret
        except Exception:
            instrument_returns[name] = None

    dxy_chg    = instrument_returns.get("DXY")
    gold_chg   = instrument_returns.get("Gold")
    bhp_chg    = instrument_returns.get("AUD")
    gbpusd_chg = instrument_returns.get("GBPUSD")
    audusd_chg = instrument_returns.get("AUD")   # same feed as bhp_chg

    # ── Fetch VIX and S&P500 from Yahoo JSON ─────────────────────────────────
    vix_level: Optional[float] = None
    vix_chg:   Optional[float] = None
    sp500_chg: Optional[float] = None

    for ticker, target in (("%5EVIX", "vix"), ("%5EGSPC", "sp")):
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d",
                timeout=5, headers=_YAHOO_HEADERS,
            )
            if r.status_code == 200:
                closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [v for v in closes if v is not None]
                if len(closes) >= 2:
                    if target == "vix":
                        vix_level = closes[-1]
                        vix_chg   = closes[-1] - closes[-2]
                    else:
                        sp500_chg = (closes[-1] - closes[-2]) / closes[-2] * 100
        except Exception:
            pass

    # ── Analyse each signal ───────────────────────────────────────────────────
    dxy_bias,  dxy_note  = _analyse_dxy(dxy_chg)
    gold_bias, gold_note = _analyse_gold(gold_chg)
    bhp_bias,  bhp_note  = _analyse_bhp(bhp_chg)

    risk_mode, risk_bias, risk_note, vix_regime, vix_regime_note = \
        _analyse_risk(vix_level, vix_chg, sp500_chg)

    overall_bias, overall_note = _aggregate(
        dxy_bias, gold_bias, bhp_bias, risk_bias,
        dxy_chg, gold_chg, bhp_chg, vix_level, sp500_chg
    )

    narrative = _build_narrative_label(
        risk_mode, dxy_chg, gold_chg, bhp_chg,
        sp500_chg, vix_level, vix_chg, overall_bias
    )

    legs = _leg_decomposition(gbpusd_chg, audusd_chg)

    return {
        "dxy_change":       round(dxy_chg,   3) if dxy_chg   is not None else None,
        "dxy_bias":         dxy_bias,
        "dxy_note":         dxy_note,
        "gold_change":      round(gold_chg,  3) if gold_chg  is not None else None,
        "gold_bias":        gold_bias,
        "gold_note":        gold_note,
        "bhp_change":       round(bhp_chg,   3) if bhp_chg   is not None else None,
        "bhp_bias":         bhp_bias,
        "bhp_note":         bhp_note,
        "vix_level":        round(vix_level, 1) if vix_level is not None else None,
        "vix_change":       round(vix_chg,   2) if vix_chg   is not None else None,
        "vix_regime":       vix_regime,
        "vix_regime_note":  vix_regime_note,
        "sp500_change":     round(sp500_chg, 3) if sp500_chg is not None else None,
        "risk_mode":        risk_mode,
        "risk_bias":        risk_bias,
        "risk_note":        risk_note,
        "overall_bias":     overall_bias,
        "overall_note":     overall_note,
        "narrative":        narrative,
        "legs":             legs,
        "error":            None,
    }


# ── Signal analysers ──────────────────────────────────────────────────────────

def _analyse_dxy(chg: Optional[float]) -> Tuple[str, str]:
    # Relationship (consistent with the risk-off → BULLISH logic below): a
    # strong USD hits AUD (commodity/risk) harder than GBP, so AUD/USD falls
    # MORE than GBP/USD → GBP/AUD (= GBPUSD ÷ AUDUSD) RISES → BULLISH. A weak
    # USD benefits AUD more → GBP/AUD falls → BEARISH. (The prior version had the
    # label and its own note contradicting each other.)
    if chg is None:
        return "NEUTRAL", "DXY data unavailable."
    if chg > 0.3:
        return "BULLISH", (
            f"USD strengthened sharply today (+{chg:.2f}%). "
            f"A strong dollar hits AUD harder than GBP — AUD weakens more, "
            f"so GBP/AUD tends higher (bullish)."
        )
    elif chg > 0.1:
        return "BULLISH", (
            f"USD is modestly stronger (+{chg:.2f}%). "
            f"Slight tailwind for GBP/AUD — AUD tends to weaken more than GBP vs USD."
        )
    elif chg < -0.3:
        return "BEARISH", (
            f"USD weakened sharply today ({chg:.2f}%). "
            f"Dollar weakness benefits AUD more — GBP/AUD tends lower (bearish)."
        )
    elif chg < -0.1:
        return "BEARISH", (
            f"USD is modestly weaker ({chg:.2f}%). "
            f"Slight headwind for GBP/AUD — commodity currencies firm up."
        )
    else:
        return "NEUTRAL", (
            f"USD is roughly flat today ({chg:+.2f}%). "
            f"No meaningful dollar driver for GBP/AUD."
        )


def _analyse_gold(chg: Optional[float]) -> Tuple[str, str]:
    if chg is None:
        return "NEUTRAL", "Gold data unavailable."
    if chg > 0.5:
        return "BEARISH", (
            f"Gold is up {chg:.2f}% today. "
            f"Gold rising supports AUD — AUD strengthening = bearish for GBP/AUD."
        )
    elif chg > 0.2:
        return "BEARISH", f"Gold up {chg:.2f}% — mild tailwind for AUD. Slight bearish pressure on GBP/AUD."
    elif chg < -0.5:
        return "BULLISH", (
            f"Gold is down {chg:.2f}% today. "
            f"Gold falling typically weighs on AUD — bullish for GBP/AUD."
        )
    elif chg < -0.2:
        return "BULLISH", f"Gold down {chg:.2f}% — mild headwind for AUD. Slight bullish pressure on GBP/AUD."
    else:
        return "NEUTRAL", f"Gold is roughly flat ({chg:+.2f}%). No meaningful impact on GBP/AUD."


def _analyse_bhp(chg: Optional[float]) -> Tuple[str, str]:
    # NOTE: there is no independent commodity/iron-ore feed here — the "BHP
    # proxy" was just AUD/USD reused, which double-counts AUD strength that is
    # already captured by currency_strength and the GBP/USD÷AUD/USD leg
    # decomposition. Reporting a bias from it triple-counts the same AUD move,
    # so this signal contributes NEUTRAL until a real commodity feed exists.
    return "NEUTRAL", (
        "No independent commodity feed available — AUD strength is already "
        "captured by currency strength and leg decomposition, so no separate "
        "commodity bias is added (avoids double-counting AUD)."
    )


def _analyse_risk(
    vix: Optional[float],
    vix_chg: Optional[float],
    sp500_chg: Optional[float],
) -> Tuple[str, str, str, str, str]:
    """Returns: risk_mode, risk_bias, risk_note, vix_regime, vix_regime_note"""

    if vix is None:
        return "NEUTRAL", "NEUTRAL", "Risk sentiment data unavailable.", "NORMAL", ""

    vix_dropping_sharply = vix_chg is not None and vix_chg < -5
    vix_rising_sharply   = vix_chg is not None and vix_chg > 5
    sp_surging = sp500_chg is not None and sp500_chg > 1.0
    sp_falling = sp500_chg is not None and sp500_chg < -1.0
    sp_up      = sp500_chg is not None and sp500_chg > 0.5
    sp_down    = sp500_chg is not None and sp500_chg < -0.5

    if vix_dropping_sharply and sp_surging:
        risk_mode = "RISK_ON"
    elif vix_rising_sharply or sp_falling or vix > 30:
        risk_mode = "RISK_OFF"
    elif vix > 20:
        if vix_dropping_sharply or sp_surging:
            risk_mode = "RISK_ON"
        elif sp_down:
            risk_mode = "RISK_OFF"
        else:
            risk_mode = "NEUTRAL"
    else:
        risk_mode = "RISK_ON" if (sp_up or vix_dropping_sharply) else "NEUTRAL"

    sp_str   = f"S&P500 {sp500_chg:+.2f}%" if sp500_chg is not None else "S&P500 N/A"
    vix_str  = f"VIX {vix:.1f}"
    vchg_str = f"({vix_chg:+.1f})" if vix_chg is not None else ""

    if risk_mode == "RISK_OFF":
        risk_bias = "BULLISH"
        risk_note = (
            f"RISK-OFF environment — {vix_str} {vchg_str}, {sp_str}. "
            f"AUD falls harder than GBP in risk-off — BULLISH for GBP/AUD."
        )
    elif risk_mode == "RISK_ON":
        risk_bias = "BEARISH"
        risk_note = (
            f"RISK-ON environment — {vix_str} {vchg_str}, {sp_str}. "
            f"AUD typically outperforms GBP in risk-on — BEARISH for GBP/AUD."
        )
    else:
        risk_bias = "NEUTRAL"
        risk_note = (
            f"NEUTRAL risk sentiment — {vix_str} {vchg_str}, {sp_str}. "
            f"No strong risk-on or risk-off signal."
        )

    # VIX regime
    vix_regime = "NORMAL"
    vix_regime_note = ""
    if vix_chg is not None:
        if vix > 25 and vix_chg < -3:
            vix_regime = "PANIC_FADING"
            vix_regime_note = (
                f"VIX spiked to {vix:.1f} but falling ({vix_chg:+.1f} today). "
                f"Panic selling likely exhausted — short-term relief bounce probable."
            )
        elif vix > 25 and vix_chg > 5:
            vix_regime = "PANIC_BUILDING"
            vix_regime_note = (
                f"VIX spiking ({vix:.1f}, {vix_chg:+.1f} today). "
                f"Panic accelerating — AUD likely to underperform further."
            )
        elif vix < 20 and vix_chg < -3:
            vix_regime = "FEAR_CLEARING"
            vix_regime_note = (
                f"VIX dropping from elevated levels ({vix:.1f}, {vix_chg:+.1f}). "
                f"Fear clearing — risk appetite recovering."
            )

    return risk_mode, risk_bias, risk_note, vix_regime, vix_regime_note


def _aggregate(
    dxy_bias, gold_bias, bhp_bias, risk_bias,
    dxy_chg, gold_chg, bhp_chg, vix_level, sp500_chg
) -> Tuple[str, str]:
    scores = {"BULLISH": 1, "BEARISH": -1, "NEUTRAL": 0}
    weighted = (
        scores.get(risk_bias, 0) * 3 +
        scores.get(dxy_bias,  0) * 2 +
        scores.get(gold_bias, 0) * 1 +
        scores.get(bhp_bias,  0) * 1
    )
    bias = "BULLISH" if weighted > 0 else "BEARISH" if weighted < 0 else "NEUTRAL"

    drivers = []
    if risk_bias != "NEUTRAL": drivers.append(f"risk sentiment ({risk_bias.lower()})")
    if dxy_bias  != "NEUTRAL": drivers.append(f"USD move ({dxy_bias.lower()})")
    if gold_bias != "NEUTRAL": drivers.append(f"gold ({gold_bias.lower()})")
    if bhp_bias  != "NEUTRAL": drivers.append(f"iron ore proxy ({bhp_bias.lower()})")

    note = (
        f"Cross-market picture is {bias} for GBP/AUD. Key drivers: {', '.join(drivers)}."
        if drivers else
        "Cross-market environment is neutral — no strong macro driver for GBP/AUD today."
    )
    return bias, note


def _build_narrative_label(
    risk_mode, dxy_chg, gold_chg, bhp_chg,
    sp500_chg, vix_level, vix_chg, overall_bias
) -> str:
    parts = []
    if risk_mode == "RISK_ON":
        parts.append("Fear unwinding sharply" if (vix_chg and vix_chg < -5) else "Risk-on environment")
    elif risk_mode == "RISK_OFF":
        parts.append("Risk-off fear spike" if (vix_chg and vix_chg > 5) else "Risk-off caution")
    else:
        parts.append("Neutral risk tone")

    if gold_chg and bhp_chg:
        if gold_chg > 1.0 and bhp_chg > 1.0:
            parts.append("broad commodity surge — AUD positive")
        elif gold_chg > 1.0:
            parts.append("gold leading — defensive bid")
        elif bhp_chg > 1.0:
            parts.append("iron ore / materials strong — AUD positive")
        elif gold_chg < -1.0 and bhp_chg < -1.0:
            parts.append("commodities selling — AUD negative")

    if dxy_chg:
        if dxy_chg < -0.3:   parts.append("USD selling broadly")
        elif dxy_chg > 0.3:  parts.append("USD strength")

    if sp500_chg:
        if sp500_chg > 1.5:  parts.append("equities surging")
        elif sp500_chg < -1.5: parts.append("equities selling off")

    if not parts:
        return "No dominant macro theme — markets quiet"

    label = parts[0]
    if len(parts) > 1:
        label += " with " + ", ".join(parts[1:])

    suffix = {
        "BEARISH": " — net BEARISH for GBP/AUD",
        "BULLISH": " — net BULLISH for GBP/AUD",
    }.get(overall_bias, " — mixed for GBP/AUD")
    return label + suffix


def _leg_decomposition(gbpusd_chg: Optional[float], audusd_chg: Optional[float]) -> Dict:
    """
    GBP/AUD = GBP/USD ÷ AUD/USD.
    Determines which leg is driving the GBP/AUD move today.

    BOTH_CONFIRMING = strongest signal (both legs aligned).
    ONE_LED         = moderate signal (one leg doing the work, other flat).
    OUTPACING       = weak signal (both vs USD in same direction, one faster).
    NEUTRAL         = no meaningful driver.
    """
    THRESHOLD = 0.10  # % below which a move is "roughly flat"

    if gbpusd_chg is None or audusd_chg is None:
        return {
            "driver": "UNKNOWN", "bias": "NEUTRAL", "strong": False,
            "note": "GBP/USD or AUD/USD data unavailable — leg decomposition skipped.",
            "gbpusd_change": gbpusd_chg, "audusd_change": audusd_chg,
        }

    g = 1 if gbpusd_chg > THRESHOLD else -1 if gbpusd_chg < -THRESHOLD else 0
    a = 1 if audusd_chg > THRESHOLD else -1 if audusd_chg < -THRESHOLD else 0

    if g == 1 and a == -1:
        driver = "BOTH_CONFIRMING_BULLISH"
        note   = (f"GBP rising ({gbpusd_chg:+.2f}%) AND AUD falling ({audusd_chg:+.2f}%) vs USD. "
                  f"Both legs pushing GBP/AUD higher — highest-conviction signal.")
        bias, strong = "BULLISH", True
    elif g == -1 and a == 1:
        driver = "BOTH_CONFIRMING_BEARISH"
        note   = (f"GBP falling ({gbpusd_chg:+.2f}%) AND AUD rising ({audusd_chg:+.2f}%) vs USD. "
                  f"Both legs pushing GBP/AUD lower — highest-conviction signal.")
        bias, strong = "BEARISH", True
    elif g == 1 and a == 0:
        driver = "GBP_STRENGTH_LED"
        note   = (f"GBP rising ({gbpusd_chg:+.2f}%) while AUD flat ({audusd_chg:+.2f}%). "
                  f"GBP strength driving GBP/AUD — AUD not confirming. If AUD turns down, move accelerates.")
        bias, strong = "BULLISH", False
    elif g == -1 and a == 0:
        driver = "GBP_WEAKNESS_LED"
        note   = (f"GBP falling ({gbpusd_chg:+.2f}%) while AUD flat ({audusd_chg:+.2f}%). "
                  f"GBP weakness driving GBP/AUD — AUD not confirming. Susceptible to reversal if AUD turns down.")
        bias, strong = "BEARISH", False
    elif g == 0 and a == -1:
        driver = "AUD_WEAKNESS_LED"
        note   = (f"AUD falling ({audusd_chg:+.2f}%) while GBP flat ({gbpusd_chg:+.2f}%). "
                  f"AUD weakness pushing GBP/AUD higher — but if AUD bounces, GBP/AUD snaps back fast.")
        bias, strong = "BULLISH", False
    elif g == 0 and a == 1:
        driver = "AUD_STRENGTH_LED"
        note   = (f"AUD rising ({audusd_chg:+.2f}%) while GBP flat ({gbpusd_chg:+.2f}%). "
                  f"AUD strength pushing GBP/AUD lower — if AUD stalls, GBP/AUD could bounce.")
        bias, strong = "BEARISH", False
    elif g == 1 and a == 1:
        if gbpusd_chg > audusd_chg:
            driver = "GBP_OUTPACING"
            note   = (f"Both rising vs USD (GBP {gbpusd_chg:+.2f}%, AUD {audusd_chg:+.2f}%) "
                      f"but GBP outpacing — GBP/AUD has a mild bullish tilt. Weak signal.")
            bias   = "BULLISH"
        else:
            driver = "AUD_OUTPACING"
            note   = (f"Both rising vs USD (GBP {gbpusd_chg:+.2f}%, AUD {audusd_chg:+.2f}%) "
                      f"but AUD outpacing — GBP/AUD has a mild bearish tilt. Weak signal.")
            bias   = "BEARISH"
        strong = False
    elif g == -1 and a == -1:
        if abs(gbpusd_chg) > abs(audusd_chg):
            driver = "GBP_LEADING_DOWN"
            note   = (f"Both falling vs USD (GBP {gbpusd_chg:+.2f}%, AUD {audusd_chg:+.2f}%) "
                      f"but GBP falling faster — GBP/AUD biased lower. USD-strength story, weak signal.")
            bias   = "BEARISH"
        else:
            driver = "AUD_LEADING_DOWN"
            note   = (f"Both falling vs USD (GBP {gbpusd_chg:+.2f}%, AUD {audusd_chg:+.2f}%) "
                      f"but AUD falling faster — GBP/AUD biased higher. USD-strength story, weak signal.")
            bias   = "BULLISH"
        strong = False
    else:
        driver = "NEUTRAL"
        note   = (f"GBP/USD ({gbpusd_chg:+.2f}%) and AUD/USD ({audusd_chg:+.2f}%) both roughly flat. "
                  f"No meaningful leg driver for GBP/AUD today.")
        bias, strong = "NEUTRAL", False

    return {
        "driver":        driver,
        "bias":          bias,
        "strong":        strong,
        "note":          note,
        "gbpusd_change": round(gbpusd_chg, 3),
        "audusd_change": round(audusd_chg, 3),
    }


def _not_modelled(instrument: str) -> Dict:
    """Honest neutral result for pairs this GBP/AUD-specific model doesn't cover.
    Not an error — intentionally contributes no bias (error=None, NEUTRAL)."""
    pair = instrument.replace("_", "/")
    note = (f"Cross-market model is GBP/AUD-specific (commodity / AUD drivers); "
            f"not applied to {pair}. No cross-market bias contributed.")
    d = _fallback(note)
    d["error"]        = None      # intentional — not a failure
    d["overall_bias"] = "NEUTRAL"
    d["not_modelled"] = True
    return d


def _fallback(reason: str) -> Dict:
    return {
        "dxy_change": None,  "dxy_bias": "NEUTRAL",  "dxy_note": reason,
        "gold_change": None, "gold_bias": "NEUTRAL",  "gold_note": reason,
        "bhp_change": None,  "bhp_bias": "NEUTRAL",   "bhp_note": reason,
        "vix_level": None,   "vix_change": None,
        "vix_regime": "NORMAL", "vix_regime_note": "",
        "sp500_change": None,
        "risk_mode": "NEUTRAL", "risk_bias": "NEUTRAL", "risk_note": reason,
        "overall_bias": "NEUTRAL",
        "overall_note": f"Cross-market data unavailable: {reason}",
        "narrative": "Cross-market data unavailable",
        "legs": {"driver": "UNKNOWN", "bias": "NEUTRAL", "strong": False,
                 "note": reason, "gbpusd_change": None, "audusd_change": None},
        "error": reason,
    }


if __name__ == "__main__":
    data = get_cross_market()
    if data["error"]:
        print(f"Error: {data['error']}")
    else:
        print(f"DXY    : {data['dxy_change']}%  -> {data['dxy_bias']}")
        print(f"Gold   : {data['gold_change']}%  -> {data['gold_bias']}")
        print(f"AUD/BHP: {data['bhp_change']}%  -> {data['bhp_bias']}")
        print(f"VIX    : {data['vix_level']}  ({data['vix_change']})  -> {data['risk_mode']}")
        print(f"S&P500 : {data['sp500_change']}%")
        print(f"Overall: {data['overall_bias']}")
        print(f"Story  : {data['narrative']}")
