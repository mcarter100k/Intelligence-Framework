"""
trade_outcome_logger.py

Logs every signal output with enough context to validate accuracy later.
CSV-based. One row per signal. Outcome fields filled in separately via
record_outcome().

Schema mirrors TradeSignal — see field comments for data source.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Dict, Optional

_LOG_FILE = "trade_signal_log.csv"

_FIELDS = [
    # Identity
    "signal_id",
    "timestamp",
    "instrument",
    # Regime state at signal time (from get_regime())
    "regime_d1",
    "regime_h4",
    "adx_d1",
    "adx_h4",
    "atr_ratio",
    "atr_compression",
    "adx_exhaustion",
    "timeframe_conflict",
    "conflict_type",
    "stand_down",
    "structure_d1",
    "weekly_context",
    "lt_trend",
    "st_trend",
    # Signal output (from decision_engine)
    "direction",
    "grade",
    "conviction",
    # Price context at signal time
    "price_at_signal",
    "atr_pips",
    # Outcome fields (filled later via record_outcome())
    "outcome_filled",
    "outcome_direction",
    "price_20_bars_later",
    "move_pips",
    "signal_correct",
]


def _ensure_file() -> None:
    """Create CSV with header row if it does not exist."""
    if not os.path.exists(_LOG_FILE):
        with open(_LOG_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=_FIELDS).writeheader()


def log_signal(
    regime_data:   Dict,
    decision_data: Dict,
    instrument:    str,
) -> str:
    """
    Log a signal to trade_signal_log.csv.
    Returns the signal_id (ISO timestamp + instrument).
    outcome_filled defaults to False — call record_outcome() later.
    """
    _ensure_file()
    ts        = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    signal_id = f"{ts}_{instrument}"

    row = {
        "signal_id":           signal_id,
        "timestamp":           ts,
        "instrument":          instrument,
        "regime_d1":           regime_data.get("regime_d1", ""),
        "regime_h4":           regime_data.get("regime_h4", ""),
        "adx_d1":              regime_data.get("adx", 0.0),
        "adx_h4":              regime_data.get("adx_h4", 0.0),
        "atr_ratio":           regime_data.get("atr_vs_avg", 1.0),
        "atr_compression":     regime_data.get("atr_compression", False),
        "adx_exhaustion":      regime_data.get("adx_exhaustion", False),
        "timeframe_conflict":  regime_data.get("timeframe_conflict", False),
        "conflict_type":       regime_data.get("conflict_type", ""),
        "stand_down":          regime_data.get("stand_down", False),
        "structure_d1":        regime_data.get("structure", ""),
        "weekly_context":      regime_data.get("weekly_context", ""),
        "lt_trend":            regime_data.get("lt_trend", ""),
        "st_trend":            regime_data.get("st_trend", ""),
        "direction":           decision_data.get("direction", ""),
        "grade":               decision_data.get("grade", ""),
        "conviction":          decision_data.get("conviction", 0),
        "price_at_signal":     regime_data.get("current_price", 0.0),
        "atr_pips":            regime_data.get("atr_pips", 0.0),
        # Outcome defaults — populated by record_outcome()
        "outcome_filled":      False,
        "outcome_direction":   "",
        "price_20_bars_later": "",
        "move_pips":           "",
        "signal_correct":      "",
    }

    with open(_LOG_FILE, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=_FIELDS).writerow(row)

    return signal_id


def record_outcome(
    signal_id:     str,
    price_outcome: float,
    bars_elapsed:  int = 20,
) -> bool:
    """
    Fill in outcome fields for a logged signal.
    Computes move_pips and signal_correct from price_at_signal
    and price_outcome.
    Returns True if record found and updated.
    """
    if not os.path.exists(_LOG_FILE):
        return False

    rows = []
    found = False
    with open(_LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row["signal_id"] == signal_id:
                found = True
                price_entry = float(row["price_at_signal"]) if row["price_at_signal"] else 0.0
                move        = price_outcome - price_entry
                direction   = row["direction"]

                # JPY pairs quote in 2dp; everything else 4dp
                pip_size  = 0.01 if "JPY" in row["instrument"] else 0.0001
                move_pips = round(move / pip_size, 1)

                if move > 0:
                    outcome_direction = "UP"
                elif move < 0:
                    outcome_direction = "DOWN"
                else:
                    outcome_direction = "FLAT"

                signal_correct = (
                    (direction == "LONG"  and move > 0) or
                    (direction == "SHORT" and move < 0)
                )

                row["outcome_filled"]      = True
                row["outcome_direction"]   = outcome_direction
                row["price_20_bars_later"] = price_outcome
                row["move_pips"]           = move_pips
                row["signal_correct"]      = signal_correct
            rows.append(row)

    if not found:
        return False

    with open(_LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return True


def get_accuracy_by_regime(
    instrument:  Optional[str] = None,
    min_samples: int = 30,
) -> Dict:
    """
    Compute signal accuracy grouped by regime_d1.
    Returns dict: {regime: {accuracy, n, avg_conviction}}
    Only returns groups with >= min_samples filled outcomes.
    Used by validate_confluence_weights.py to derive weights.
    """
    if not os.path.exists(_LOG_FILE):
        return {}

    groups: Dict[str, list] = {}
    with open(_LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("outcome_filled") != "True":
                continue
            if instrument and row["instrument"] != instrument:
                continue
            regime = row["regime_d1"]
            groups.setdefault(regime, []).append(row)

    result = {}
    for regime, regime_rows in groups.items():
        if len(regime_rows) < min_samples:
            continue
        correct     = sum(1 for r in regime_rows if r["signal_correct"] == "True")
        convictions = [int(r["conviction"]) for r in regime_rows if r.get("conviction")]
        result[regime] = {
            "accuracy":       round(correct / len(regime_rows), 4),
            "n":              len(regime_rows),
            "avg_conviction": round(sum(convictions) / len(convictions), 1) if convictions else 0.0,
        }
    return result


def get_accuracy_by_signal_type(instrument: Optional[str] = None) -> Dict:
    """
    Compute accuracy for each signal combination:
    regime_d1 + structure_d1 + weekly_context.
    Returns dict sorted by accuracy descending.
    """
    if not os.path.exists(_LOG_FILE):
        return {}

    groups: Dict[str, list] = {}
    with open(_LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("outcome_filled") != "True":
                continue
            if instrument and row["instrument"] != instrument:
                continue
            key = (
                f"{row.get('regime_d1', '')}|"
                f"{row.get('structure_d1', '')}|"
                f"{row.get('weekly_context', '')}"
            )
            groups.setdefault(key, []).append(row)

    result = {}
    for key, key_rows in groups.items():
        correct = sum(1 for r in key_rows if r["signal_correct"] == "True")
        result[key] = {
            "accuracy": round(correct / len(key_rows), 4),
            "n":        len(key_rows),
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["accuracy"], reverse=True))
