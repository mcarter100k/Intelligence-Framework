"""
regime_classifier_logger.py
────────────────────────────
Logs every regime classification call with its testable prediction.
Outcomes are filled in automatically when enough bars have elapsed.

VALIDATION CONTRACT (from Problem 1):
  TRENDING → momentum signal win rate > 50% over next 20 bars
  RANGING  → mean reversion win rate > 50% over next 20 bars
  VOLATILE → realized vol > 1.3x ATR baseline over next 8 bars

LOG FILE: regime_classification_log.csv
OUTCOME WINDOW: 20 bars for TRENDING/RANGING, 8 bars for VOLATILE
MINIMUM ACCURACY: 55% — below this, thresholds need review

USAGE:
  from regime_classifier_logger import log_regime, check_pending_outcomes

  # Log a regime classification (call after every get_regime())
  log_regime(regime_data, instrument)

  # Check and fill outcomes for classifications old enough to measure
  # Call this at the start of each framework run
  check_pending_outcomes(instrument, current_bars_data)
"""

import csv
import os
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

LOG_FILE = "regime_classification_log.csv"

# Outcome windows per regime type (in bars)
OUTCOME_WINDOWS = {
    "TRENDING_UP":   20,
    "TRENDING_DOWN": 20,
    "RANGING":       20,
    "VOLATILE":      8,
}

# Minimum accuracy before flagging threshold for review
MIN_ACCURACY_THRESHOLD = 0.55
MIN_SAMPLES_FOR_REVIEW = 60

FIELDNAMES = [
    # Identity
    "log_id",           # timestamp_instrument
    "timestamp",        # ISO UTC
    "instrument",       # GBP_AUD or GBP_JPY

    # Regime state logged
    "regime_d1",
    "regime_h4",
    "composite_regime",
    "execution_mode",
    "confidence",
    "size_mult",
    "adx_d1",
    "adx_h4",
    "atr_ratio",
    "structure_d1",
    "weekly_context",
    "timeframe_conflict",
    "stand_down",

    # Price context at classification time
    "price_at_log",
    "atr_pips_at_log",

    # Testable prediction
    "prediction_type",   # MOMENTUM_WIN / MR_WIN / VOL_EXPANSION
    "prediction_window", # bars until outcome measured

    # Outcome fields (filled later)
    "outcome_filled",    # False until measured
    "bars_elapsed",
    "price_at_outcome",
    "outcome_correct",   # True/False
    "outcome_detail",    # plain-English explanation of what happened
]


def log_regime(regime_data: Dict, instrument: str) -> str:
    """
    Log a regime classification with its testable prediction.

    Args:
        regime_data: full dict returned by get_regime()
        instrument:  "GBP_AUD" or "GBP_JPY"

    Returns:
        log_id (timestamp_instrument) for future outcome lookup
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_id    = f"{timestamp}_{instrument}"

    composite = regime_data.get("regime", "UNKNOWN")
    prediction_type, prediction_window = _get_prediction(composite)

    row = {
        "log_id":             log_id,
        "timestamp":          timestamp,
        "instrument":         instrument,
        "regime_d1":          regime_data.get("regime_d1", ""),
        "regime_h4":          regime_data.get("regime_h4", ""),
        "composite_regime":   composite,
        "execution_mode":     regime_data.get("execution_mode", ""),
        "confidence":         regime_data.get("confidence", ""),
        "size_mult":          regime_data.get("size_mult", 0.0),
        "adx_d1":             regime_data.get("adx", 0.0),
        "adx_h4":             regime_data.get("adx_h4", 0.0),
        "atr_ratio":          regime_data.get("atr_vs_avg", 0.0),
        "structure_d1":       regime_data.get("structure", ""),
        "weekly_context":     regime_data.get("weekly_context", ""),
        "timeframe_conflict": regime_data.get("timeframe_conflict", False),
        "stand_down":         regime_data.get("stand_down", False),
        "price_at_log":       regime_data.get("current_price", 0.0),
        "atr_pips_at_log":    regime_data.get("atr_pips", 0.0),
        "prediction_type":    prediction_type,
        "prediction_window":  prediction_window,
        "outcome_filled":     False,
        "bars_elapsed":       0,
        "price_at_outcome":   "",
        "outcome_correct":    "",
        "outcome_detail":     "",
    }

    _write_row(row)
    return log_id


def check_pending_outcomes(
    instrument:    str,
    recent_closes: List[float],
    recent_highs:  List[float],
    recent_lows:   List[float],
) -> int:
    """
    Check all pending (outcome_filled=False) classifications for
    this instrument and fill outcomes where enough bars have elapsed.

    Args:
        instrument:     "GBP_AUD" or "GBP_JPY"
        recent_closes:  list of recent D1 closes (newest last)
        recent_highs:   list of recent D1 highs (newest last)
        recent_lows:    list of recent D1 lows (newest last)

    Returns:
        number of outcomes filled in this call
    """
    if not os.path.exists(LOG_FILE):
        return 0

    rows = _read_all()
    filled_count = 0
    now_price = recent_closes[-1] if recent_closes else None

    updated = []
    for row in rows:
        if (row["instrument"] != instrument or
                row["outcome_filled"] == "True"):
            updated.append(row)
            continue

        # Count bars elapsed since log timestamp
        log_time = datetime.fromisoformat(
            row["timestamp"].replace("Z", "+00:00")
        )
        bars_elapsed = _estimate_bars_elapsed(log_time)
        window       = int(row.get("prediction_window", 20))

        if bars_elapsed < window:
            updated.append(row)
            continue

        # Enough bars elapsed — measure outcome
        price_at_log = float(row["price_at_log"])
        atr_at_log   = float(row["atr_pips_at_log"])
        regime       = row["composite_regime"]
        pred_type    = row["prediction_type"]

        correct, detail = _measure_outcome(
            pred_type, price_at_log, atr_at_log,
            regime, recent_closes, recent_highs, recent_lows,
            row.get("structure_d1", ""),
        )

        row["outcome_filled"]   = True
        row["bars_elapsed"]     = bars_elapsed
        row["price_at_outcome"] = now_price or ""
        row["outcome_correct"]  = correct
        row["outcome_detail"]   = detail
        filled_count += 1
        updated.append(row)

    if filled_count > 0:
        _write_all(updated)

    return filled_count


def get_regime_accuracy(
    instrument:  str = None,
    min_samples: int = MIN_SAMPLES_FOR_REVIEW,
) -> Dict:
    """
    Compute regime classification accuracy from filled outcomes.

    Returns dict keyed by composite_regime:
      {regime: {accuracy, n, needs_review, adx_range, detail}}

    needs_review=True when accuracy < MIN_ACCURACY_THRESHOLD
    and n >= min_samples — this is the signal to revise thresholds.
    """
    rows = _read_all()
    filled = [r for r in rows
              if r.get("outcome_filled") == "True"
              and (instrument is None or r["instrument"] == instrument)]

    from collections import defaultdict
    groups = defaultdict(list)
    for r in filled:
        groups[r["composite_regime"]].append(r)

    result = {}
    for regime, regime_rows in groups.items():
        n       = len(regime_rows)
        correct = sum(1 for r in regime_rows
                      if str(r.get("outcome_correct")) == "True")
        accuracy = correct / n if n > 0 else 0.0
        adx_vals = [float(r["adx_d1"]) for r in regime_rows
                    if r.get("adx_d1")]

        result[regime] = {
            "accuracy":     round(accuracy, 3),
            "n":            n,
            "correct":      correct,
            "needs_review": (n >= min_samples and
                             accuracy < MIN_ACCURACY_THRESHOLD),
            "adx_min":      round(min(adx_vals), 1) if adx_vals else None,
            "adx_max":      round(max(adx_vals), 1) if adx_vals else None,
            "adx_avg":      round(sum(adx_vals)/len(adx_vals), 1)
                            if adx_vals else None,
        }

    return result


def get_accuracy_report(instrument: str = None) -> str:
    """
    Return a plain-English accuracy report for all regimes.
    Flags any regime where accuracy < 55% with >= 60 samples.
    """
    acc = get_regime_accuracy(instrument=instrument, min_samples=1)
    if not acc:
        return "No completed outcomes yet. Keep running the framework."

    lines = ["Regime Classification Accuracy Report",
             "─" * 45]
    for regime, data in sorted(acc.items()):
        flag = " ← REVIEW THRESHOLDS" if data["needs_review"] else ""
        lines.append(
            f"  {regime:<16}: {data['accuracy']:.0%} "
            f"({data['correct']}/{data['n']} correct){flag}"
        )
    lines.append("─" * 45)
    lines.append(
        f"Run validate_adx_threshold.py if any regime "
        f"shows needs_review=True with >= {MIN_SAMPLES_FOR_REVIEW} samples."
    )
    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_prediction(composite: str) -> Tuple[str, int]:
    """Map regime to its testable prediction type and window."""
    if composite in ("TRENDING_UP", "TRENDING_DOWN"):
        return "MOMENTUM_WIN", 20
    elif composite == "RANGING":
        return "MR_WIN", 20
    elif composite == "VOLATILE":
        return "VOL_EXPANSION", 8
    return "MOMENTUM_WIN", 20


def _measure_outcome(
    pred_type:    str,
    price_at_log: float,
    atr_at_log:   float,
    regime:       str,
    closes:       List[float],
    highs:        List[float],
    lows:         List[float],
    structure:    str,
) -> Tuple[bool, str]:
    """
    Measure whether the prediction was correct.

    MOMENTUM_WIN: price moved further in trend direction
    MR_WIN:       price reverted toward the mean
    VOL_EXPANSION: realized vol > 1.3x ATR at log time
    """
    if not closes:
        return False, "No price data available"

    current_price = closes[-1]

    if pred_type == "MOMENTUM_WIN":
        direction = 1 if regime == "TRENDING_UP" else -1
        move = (current_price - price_at_log) * direction
        correct = move > 0
        detail  = (f"Price moved {'+' if move > 0 else ''}"
                   f"{move:.4f} in trend direction "
                   f"({'correct' if correct else 'wrong direction'})")
        return correct, detail

    elif pred_type == "MR_WIN":
        if len(closes) >= 20:
            mean = sum(closes[-20:]) / 20
        else:
            mean = sum(closes) / len(closes)
        gap     = mean - price_at_log
        move    = current_price - price_at_log
        correct = (gap * move) > 0  # both same sign = moved toward mean
        detail  = (f"Mean reversion: price moved "
                   f"{'toward' if correct else 'away from'} mean "
                   f"(mean={mean:.4f}, entry={price_at_log:.4f}, "
                   f"now={current_price:.4f})")
        return correct, detail

    elif pred_type == "VOL_EXPANSION":
        if len(highs) >= 8 and len(lows) >= 8:
            recent_ranges = [highs[i] - lows[i] for i in range(-8, 0)]
            realized_vol  = sum(recent_ranges) / 8
            ratio = realized_vol / (atr_at_log * 0.0001) \
                    if atr_at_log > 0 else 1.0
            correct = ratio >= 1.3
            detail  = (f"Vol expansion: realized={realized_vol:.5f}, "
                       f"ratio vs ATR baseline={ratio:.2f}x "
                       f"(threshold 1.3x, "
                       f"{'correct' if correct else 'no expansion'})")
        else:
            correct = False
            detail  = "Insufficient bar data for vol measurement"
        return correct, detail

    return False, f"Unknown prediction type: {pred_type}"


def _estimate_bars_elapsed(log_time: datetime) -> int:
    """
    Estimate D1 bars elapsed since log_time.
    Approximates trading days (excludes weekends).
    """
    now   = datetime.now(timezone.utc)
    delta = now - log_time
    total_days = delta.days
    return max(0, int(total_days * 5 / 7))


def _write_row(row: Dict) -> None:
    """Append a single row to the log file."""
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _read_all() -> List[Dict]:
    """Read all rows from the log file."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", newline="") as f:
        return list(csv.DictReader(f))


def _write_all(rows: List[Dict]) -> None:
    """Overwrite the log file with updated rows."""
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
