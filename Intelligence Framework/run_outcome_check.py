"""
run_outcome_check.py
─────────────────────
Daily/weekly script to fill pending regime classification outcomes
and report accuracy against the Problem 1 validation contract.

Run this after the market closes each day (or weekly) to see if
the framework's regime calls are statistically correct.

Usage: python3 run_outcome_check.py
"""

from __future__ import annotations


def main() -> None:
    from regime_detection import PAIRS
    from oanda_feed import get_daily_bars, is_configured
    from regime_classifier_logger import (
        check_pending_outcomes, get_accuracy_report, get_regime_accuracy,
        MIN_SAMPLES_FOR_REVIEW,
    )

    if not is_configured():
        print("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")
        return

    review_needed = []

    for instrument, pair_cfg in PAIRS.items():
        oanda_pair = pair_cfg.instrument.replace("_", "")
        raw = get_daily_bars(pair=oanda_pair, count=60)
        if raw is None or raw.empty:
            print(f"{instrument}: no data from OANDA")
            continue
        if hasattr(raw.columns, "levels"):
            raw.columns = raw.columns.get_level_values(0)

        closes = [float(v) for v in raw["Close"].dropna().values]
        highs  = [float(v) for v in raw["High"].dropna().values]
        lows   = [float(v) for v in raw["Low"].dropna().values]

        filled = check_pending_outcomes(instrument, closes, highs, lows)
        print(f"\n{instrument}: {filled} outcomes filled")
        print(get_accuracy_report(instrument))

        acc = get_regime_accuracy(instrument=instrument,
                                  min_samples=MIN_SAMPLES_FOR_REVIEW)
        for regime, data in acc.items():
            if data["needs_review"]:
                review_needed.append(
                    f"  {instrument} {regime}: {data['accuracy']:.0%} "
                    f"({data['n']} samples)"
                )

    if review_needed:
        print("\n" + "=" * 55)
        print("REGIMES REQUIRING THRESHOLD REVIEW:")
        for line in review_needed:
            print(line)
        print("Run validate_adx_threshold.py for each flagged regime.")
        print("=" * 55)


if __name__ == "__main__":
    main()
