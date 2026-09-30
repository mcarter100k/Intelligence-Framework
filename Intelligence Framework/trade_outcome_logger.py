"""
trade_outcome_logger.py

Logs every signal output with enough context to validate accuracy later.
CSV-based. One row per signal. Outcome fields filled in by the nightly
grader, check_pending_trade_outcomes().

Schema mirrors TradeSignal — see field comments for data source.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from exclusions import excluder
from ledger_io import append_row, atomic_write_rows, locked, migrate_header

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
    # Signal output (from official decision path)
    "direction",
    "grade",
    "conviction",
    # Shadow path (signal-stack, logged for comparison only — never traded)
    "shadow_direction",
    "shadow_conviction",
    # Price context at signal time
    "price_at_signal",
    "atr_pips",
    # Outcome fields (filled later by check_pending_trade_outcomes())
    "outcome_filled",
    "outcome_direction",
    "price_20_bars_later",
    "move_pips",
    "signal_correct",
    # Appended 2026-09-16 (docs/specs/evidence_loop_repair_spec.md Part 1) —
    # the ruling's payload needs size and entry context, which the original
    # schema had no column for.
    "size_pct",
    "entry_context",
    # data_at_source_spec.md P1: "live" (OANDA mid at log time) or
    # "prior_close" (fallback, labelled). BLANK on rows logged before
    # 2026-09-30: those all used the previous D1 close.
    "price_basis",
]


def _migrate_header(path: str = None) -> None:
    """One-time additive migration (size_pct + entry_context, 2026-09-16).

    Same pattern as setup_check._migrate_journal_header, reviewed
    2026-09-09: when the ledger's header predates a column appended to
    _FIELDS, rewrite with the current header — every existing row preserved
    VERBATIM in its old columns and blank in the new ones. This is the
    logger maintaining its own schema, never an edit of recorded values.
    Must run before any append.
    """
    migrate_header(_LOG_FILE if path is None else path, _FIELDS)   # ledger_io


def _ensure_file() -> None:
    """Create CSV with header row if it does not exist; migrate if its
    header predates an appended column."""
    with locked(_LOG_FILE):
        if not os.path.exists(_LOG_FILE):
            atomic_write_rows(_LOG_FILE, _FIELDS, [])
        else:
            _migrate_header()


def log_signal(
    regime_data:    Dict,
    decision_data:  Dict,
    instrument:     str,
    shadow_decision: Optional[Dict] = None,
    size_pct:        Optional[int] = None,
    entry_context:   str = "",
) -> str:
    """
    Log a signal to trade_signal_log.csv.
    Returns the signal_id (ISO timestamp + instrument).
    outcome_filled defaults to False — the nightly grader fills it.
    shadow_decision: the signal-stack result (logged for comparison, never traded).
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
        "shadow_direction":    shadow_decision.get("direction", "") if shadow_decision else "",
        "shadow_conviction":   shadow_decision.get("conviction", "") if shadow_decision else "",
        "price_at_signal":     regime_data.get("current_price", 0.0),
        "price_basis":         regime_data.get("price_basis", ""),
        "atr_pips":            regime_data.get("atr_pips", 0.0),
        # Outcome defaults — populated by check_pending_trade_outcomes()
        "outcome_filled":      False,
        "outcome_direction":   "",
        "price_20_bars_later": "",
        "move_pips":           "",
        "signal_correct":      "",
        "size_pct":            "" if size_pct is None else int(size_pct),
        "entry_context":       entry_context or "",
    }

    append_row(_LOG_FILE, _FIELDS, row)          # locked + fsynced (ledger_io)

    return signal_id


def _fill_outcome(row: Dict, price_outcome: float) -> None:
    """Populate a row's outcome fields from the outcome price (mutates row)."""
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


def _bars_after(log_time, index=None) -> int:
    """Number of D1 bar timestamps in `index` strictly after log_time.
    Returns 0 when no index is supplied (cannot locate the window bar)."""
    if index is None:
        return 0
    try:
        import pandas as pd
        ts = pd.Timestamp(log_time)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        idx = index
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")
        return int((idx > ts).sum())
    except Exception:
        return 0


def check_pending_trade_outcomes(instrument, recent_closes, recent_index=None,
                                 window=20):
    """Grade pending trade signals. Holds the ledger lock from the read to
    the write, so a row appended meanwhile cannot be lost (ledger_io)."""
    with locked(_LOG_FILE):
        return _check_pending_trade_outcomes_unlocked(
            instrument, recent_closes, recent_index, window)


def _check_pending_trade_outcomes_unlocked(
    instrument:    str,
    recent_closes: list,
    recent_index=None,
    window:        int = 20,
) -> int:
    """
    Close the trade-signal feedback loop: for every pending signal whose window
    has elapsed, grade it against the price EXACTLY `window` bars after it was
    logged (not the latest bar). Mirrors the regime-classifier checker.

    Returns the number of outcomes filled in this call.
    """
    if not os.path.exists(_LOG_FILE):
        return 0

    with open(_LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0

    # Excluded rows are never graded (exclusions.py). `rows` is written back
    # below, so they are skipped here rather than filtered out of the list —
    # filtering would delete them from an append-only ledger.
    is_excluded = excluder("trade_signal_log.csv")

    filled = 0
    for row in rows:
        if row.get("instrument") != instrument or row.get("outcome_filled") == "True":
            continue
        if row.get("direction") not in ("LONG", "SHORT"):
            continue  # nothing directional to grade
        if is_excluded(row):
            continue

        try:
            log_time = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        except Exception:
            continue

        bars_elapsed = _bars_after(log_time, recent_index)
        if bars_elapsed < window:
            continue

        # Grade at the window bar, not the latest bar.
        price_outcome = None
        if recent_index is not None and len(recent_index) == len(recent_closes):
            slice_end = len(recent_index) - bars_elapsed + window
            if window <= slice_end <= len(recent_closes):
                price_outcome = recent_closes[slice_end - 1]
        if price_outcome is None:
            price_outcome = recent_closes[-1] if recent_closes else None
        if price_outcome is None:
            continue

        _fill_outcome(row, price_outcome)
        filled += 1

    if filled:
        atomic_write_rows(_LOG_FILE, _FIELDS, rows)

    return filled


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

    is_excluded = excluder("trade_signal_log.csv")

    groups: Dict[str, list] = {}
    with open(_LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("outcome_filled") != "True":
                continue
            if instrument and row["instrument"] != instrument:
                continue
            if is_excluded(row):
                continue    # never reaches a tally (exclusions.py)
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
