"""
run_outcome_check.py
─────────────────────
The nightly grader (launchd 15:15 via scheduled_outcome_check.sh, after a
verified ledger backup). For each pair it grades the regime calls, trade
signals and shadow candidates that are now old enough, then prints accuracy
and any regime due for review.

Usage: python3 run_outcome_check.py
"""

from __future__ import annotations


def main() -> None:
    from regime_detection import PAIRS
    from oanda_feed import get_daily_bars, is_configured
    from regime_classifier_logger import (
        check_pending_outcomes, get_accuracy_report, get_regime_accuracy,
    )

    if not is_configured():
        # Loud, machine-detectable early exit (docs/specs/heartbeat_spec.md
        # item 2). The 39-day outage hid behind the old quiet one-liner: the
        # wrapper detects this marker, counts consecutive failures, and
        # alerts — this function must NEVER exit silently having graded
        # nothing. The wrapper owns the "Nth consecutive" counter.
        print("GRADER EARLY EXIT — OANDA not configured "
              "(set OANDA_API_KEY and OANDA_ACCOUNT_ID) — "
              "nothing graded this run")
        return

    review_needed = []

    for instrument, pair_cfg in PAIRS.items():
        oanda_pair = pair_cfg.instrument.replace("_", "")
        raw = get_daily_bars(pair=oanda_pair, count=60)
        if raw is None or raw.empty:
            print(f"{instrument}: no data from OANDA")
            continue

        closes = [float(v) for v in raw["Close"].dropna().values]
        highs  = [float(v) for v in raw["High"].dropna().values]
        lows   = [float(v) for v in raw["Low"].dropna().values]

        filled = check_pending_outcomes(instrument, closes, highs, lows,
                                        recent_index=raw.index)
        print(f"\n{instrument}: {filled} regime outcomes filled")
        print(get_accuracy_report(instrument))

        # Grade trade signals (20 daily bars after each signal).
        from trade_outcome_logger import (
            check_pending_trade_outcomes, get_accuracy_by_regime,
        )
        t_filled = check_pending_trade_outcomes(instrument, closes,
                                                recent_index=raw.index)
        print(f"{instrument}: {t_filled} trade-signal outcomes filled")

        # Shadow-signal harness — grade pending shadow candidates (H4 horizon).
        from shadow_signals import grade_pending_shadow
        sh_filled = grade_pending_shadow(instrument)
        if sh_filled:
            print(f"{instrument}: {sh_filled} shadow-signal outcomes filled")
        _t_acc = get_accuracy_by_regime(instrument=instrument, min_samples=1)
        for _reg, _d in _t_acc.items():
            print(f"    {_reg}: {_d['accuracy']:.0%} correct "
                  f"({_d['n']} graded, avg conviction {_d['avg_conviction']})")

        acc = get_regime_accuracy(instrument=instrument)
        for regime, data in acc.items():
            if data["actionable"]:
                review_needed.append(
                    f"  {instrument} {regime}: {data['accuracy']:.0%} "
                    f"({data['n']} samples) — REVISE"
                )
            elif data["flagged"]:
                review_needed.append(
                    f"  {instrument} {regime}: {data['accuracy']:.0%} "
                    f"({data['n']} samples) — FLAG"
                )

    if review_needed:
        print("\n" + "=" * 55)
        print("REGIMES REQUIRING THRESHOLD REVIEW:")
        for line in review_needed:
            print(line)
        print("Run validate_thresholds_v2.py for each flagged regime "
              "(non-overlapping windows). Do NOT use the v1 validators in "
              "legacy_validators/ — their output is INVALIDATED.")
        print("=" * 55)


if __name__ == "__main__":
    main()
