"""
validate_confluence_weights.py

Reads trade_signal_log.csv and prints recommended weight updates.
Run after accumulating >= 60 outcomes per regime type per pair.

Usage: python3 validate_confluence_weights.py
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List

_LOG_FILE = "trade_signal_log.csv"

# Current weights — kept in sync with decision_engine.py _REGIME_WEIGHTS
_CURRENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "TRENDING_UP": {
        "htf": 0.22, "strength": 0.18, "liquidity": 0.12, "cross": 0.08,
        "news": 0.07, "rates": 0.04, "cot": 0.03, "legs": 0.10,
        "value": 0.04, "regime": 0.12, "structure": 0.10,
    },
    "TRENDING_DOWN": {
        "htf": 0.22, "strength": 0.18, "liquidity": 0.12, "cross": 0.08,
        "news": 0.07, "rates": 0.04, "cot": 0.03, "legs": 0.10,
        "value": 0.04, "regime": 0.12, "structure": 0.10,
    },
    "RANGING": {
        "liquidity": 0.25, "strength": 0.16, "htf": 0.12, "cross": 0.10,
        "news": 0.09, "rates": 0.04, "cot": 0.03, "legs": 0.09,
        "value": 0.06, "regime": 0.15, "structure": 0.05,
    },
    "VOLATILE": {
        "news": 0.30, "regime": 0.20, "cross": 0.08, "liquidity": 0.08,
        "strength": 0.08, "legs": 0.08, "htf": 0.05,
        "value": 0.03, "rates": 0.02, "cot": 0.01, "structure": 0.00,
    },
}


def _load_outcomes(instrument: str = None) -> List[Dict]:
    """Return all rows with outcome_filled=True, optionally filtered by instrument."""
    if not os.path.exists(_LOG_FILE):
        return []
    rows = []
    with open(_LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("outcome_filled") != "True":
                continue
            if instrument and row.get("instrument") != instrument:
                continue
            rows.append(row)
    return rows


def _accuracy(rows: List[Dict]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("signal_correct") == "True") / len(rows)


def _recommend(current: float, signal_acc: float, baseline_acc: float) -> float:
    """Scale current weight by how much the signal outperforms the baseline."""
    if baseline_acc <= 0:
        return current
    scale = signal_acc / baseline_acc
    return round(current * scale, 3)


def analyze_weights(min_samples: int = 30) -> None:
    """
    Read trade_signal_log.csv.
    For each regime type with >= min_samples outcomes:
      - Compute accuracy by signal combination
      - Compare to current weights
      - Print recommended weight adjustments
    """
    rows = _load_outcomes()
    if not rows:
        if not os.path.exists(_LOG_FILE):
            print(f"No log file found at {_LOG_FILE}.")
            print("Run the framework to accumulate signals, then record outcomes.")
        else:
            print("No completed outcomes found in log.")
            print("Call record_outcome() on logged signal_ids to fill outcomes.")
        return

    print(f"\nAnalyzing {len(rows)} completed outcomes...")

    # Group by regime_d1
    by_regime: Dict[str, List[Dict]] = {}
    for row in rows:
        by_regime.setdefault(row["regime_d1"], []).append(row)

    for regime in sorted(by_regime):
        regime_rows = by_regime[regime]
        if len(regime_rows) < min_samples:
            print(f"\n{regime}: {len(regime_rows)} samples (need {min_samples} — skipping)")
            continue

        baseline = _accuracy(regime_rows)
        cur_w    = _CURRENT_WEIGHTS.get(regime, {})

        print(f"\n{'='*70}")
        print(f"REGIME: {regime}  |  {len(regime_rows)} samples  |  baseline accuracy: {baseline:.1%}")
        print(f"{'='*70}")
        print(f"  {'Signal type':<38} {'Current':>9} {'Recommended':>13} {'Accuracy':>10} {'N':>6}  Evidence")
        print(f"  {'-'*88}")

        # Structure breakdown
        by_struct: Dict[str, List[Dict]] = {}
        for row in regime_rows:
            by_struct.setdefault(row.get("structure_d1", ""), []).append(row)
        for struct, s_rows in sorted(by_struct.items(), key=lambda x: -len(x[1])):
            if len(s_rows) < 5:
                continue
            acc    = _accuracy(s_rows)
            diff   = acc - baseline
            cur    = cur_w.get("structure", "—")
            rec    = _recommend(cur, acc, baseline) if isinstance(cur, float) else "—"
            evid   = "↑ increase" if diff > 0.05 else "↓ reduce" if diff < -0.05 else "  keep"
            print(f"  structure={struct:<28} {str(cur):>9} {str(rec):>13} {acc:>9.1%} {len(s_rows):>6}  {evid}")

        # Weekly context breakdown
        by_weekly: Dict[str, List[Dict]] = {}
        for row in regime_rows:
            by_weekly.setdefault(row.get("weekly_context", ""), []).append(row)
        for wc, w_rows in sorted(by_weekly.items(), key=lambda x: -len(x[1])):
            if len(w_rows) < 5:
                continue
            acc  = _accuracy(w_rows)
            diff = acc - baseline
            evid = "↑ increase" if diff > 0.05 else "↓ reduce" if diff < -0.05 else "  keep"
            print(f"  weekly_context={wc:<23} {'—':>9} {'—':>13} {acc:>9.1%} {len(w_rows):>6}  {evid}")

        # ADX exhaustion impact
        ex_rows = [r for r in regime_rows if r.get("adx_exhaustion") == "True"]
        if len(ex_rows) >= 5:
            acc  = _accuracy(ex_rows)
            diff = acc - baseline
            evid = "↑ increase" if diff > 0.05 else "↓ reduce" if diff < -0.05 else "  keep"
            print(f"  adx_exhaustion=True              {'—':>9} {'—':>13} {acc:>9.1%} {len(ex_rows):>6}  {evid}")

        # Timeframe conflict impact
        conf_rows = [r for r in regime_rows if r.get("timeframe_conflict") == "True"]
        if len(conf_rows) >= 5:
            acc  = _accuracy(conf_rows)
            diff = acc - baseline
            evid = "↑ increase" if diff > 0.05 else "↓ reduce" if diff < -0.05 else "  keep"
            print(f"  timeframe_conflict=True          {'—':>9} {'—':>13} {acc:>9.1%} {len(conf_rows):>6}  {evid}")

    print(f"\n{'─'*70}")
    print("Re-run after 60 outcomes per regime per pair for stable estimates.")
    print(f"{'─'*70}")


if __name__ == "__main__":
    analyze_weights()
