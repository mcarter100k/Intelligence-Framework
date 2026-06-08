#!/usr/bin/env python3
"""
explain.py
──────────
Look up any framework term in plain English. Run from the terminal anytime.

Usage:
    python explain.py                        → print full glossary (all terms)
    python explain.py conviction             → explain one term
    python explain.py "COUNTER_TREND_BOUNCE" → explain a specific context
    python explain.py sweep                  → partial match (shows sweep_up + sweep_down)
    python explain.py --list                 → list all term names without definitions
"""

import sys
from glossary import explain, all_terms, TERMS

W = 60

def print_full_glossary() -> None:
    print("\n" + "═" * W)
    print("  GBP/AUD INTELLIGENCE FRAMEWORK — FULL GLOSSARY")
    print(f"  {len(TERMS)} terms defined in plain English")
    print("═" * W)

    sections = {
        "Direction & Grades":   ["LONG", "SHORT", "NO TRADE", "A+", "A", "B+", "B", "C"],
        "Conviction & Tiers":   ["conviction", "structural_score", "tactical_score", "execution_score"],
        "Market Structure":     ["ESTABLISHED_UPTREND", "ESTABLISHED_DOWNTREND",
                                 "PULLBACK_IN_UPTREND", "COUNTER_TREND_BOUNCE",
                                 "HH_HL", "LH_LL", "RANGING", "TRANSITIONAL"],
        "Regime":               ["TRENDING_UP", "TRENDING_DOWN", "VOLATILE", "DEFAULT",
                                 "ADX", "ATR", "fuel_pct"],
        "Macro Environment":    ["GOLDILOCKS", "REFLATION", "STAGFLATION", "DEFLATION"],
        "Value":                ["PREMIUM", "STRONG PREMIUM", "DISCOUNT", "STRONG DISCOUNT",
                                 "FAIR VALUE", "fair_value", "weekly_mid"],
        "Liquidity & Sweeps":   ["sweep_down", "sweep_up", "Sweep",
                                 "PDH", "PDL", "PWH", "PWL", "nearest_pool"],
        "Currency Strength":    ["Currency Strength", "differential"],
        "COT / Big Money":      ["COT", "Hedge Fund Positioning", "CONTRARIAN"],
        "Cross-Market":         ["VIX", "PANIC_BUILDING", "PANIC_FADING", "risk_on", "risk_off", "DXY"],
        "Interest Rates":       ["Carry Signal", "Rate Path Signal", "hawkish", "dovish", "BoE", "RBA"],
        "Intraday / Fakeouts":  ["Asian range", "BULLISH_FAKEOUT", "BEARISH_FAKEOUT",
                                 "CLEAN_BREAK_UP", "CLEAN_BREAK_DOWN", "BOTH_SWEPT"],
        "Sessions":             ["London Session", "New York Session", "Tokyo Session",
                                 "London/New York Overlap", "Sydney Session", "Off-hours"],
        "Leg Decomposition":    ["Leg Decomposition", "BOTH_CONFIRMING_BULLISH",
                                 "BOTH_CONFIRMING_BEARISH", "GBP_STRENGTH_LED", "AUD_WEAKNESS_LED"],
        "Trade Math":           ["pips", "Stop Loss", "R:R", "spread", "lot_size",
                                 "entry_zone", "invalidation"],
        "Outcomes & Guards":    ["WIN", "LOSS", "HALTED", "SESSION_CLOSED", "ACTIVE"],
    }

    for section, keys in sections.items():
        print(f"\n  ── {section} " + "─" * max(0, W - len(section) - 6))
        for k in keys:
            if k in TERMS:
                short = TERMS[k][:72] + "…" if len(TERMS[k]) > 72 else TERMS[k]
                print(f"  {k:<28}  {short}")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print_full_glossary()
        return

    if args[0] == "--list":
        print("\n  All defined terms:\n")
        for t in all_terms():
            print(f"    {t}")
        print(f"\n  Total: {len(TERMS)} terms")
        return

    term = " ".join(args)
    print(explain(term))


if __name__ == "__main__":
    main()
