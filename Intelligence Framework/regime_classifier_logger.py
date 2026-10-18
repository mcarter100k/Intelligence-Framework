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
  log_regime(regime_data, instrument)
      called by decision_brief on every open-market run
  check_pending_outcomes(instrument, closes, highs, lows, recent_index)
      called nightly by run_outcome_check.py to grade old-enough rows
"""

import csv
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from exclusions import excluder, filter_rows
from ledger_io import append_row, atomic_write_rows, locked, migrate_header

LOG_FILE = "regime_classification_log.csv"

# Minimum accuracy threshold — below this a regime is underperforming
MIN_ACCURACY_THRESHOLD = 0.55
# Two-checkpoint sample gates
MIN_SAMPLES_FLAG   = 60   # enough to notice a pattern — flag, watch closely
MIN_SAMPLES_REVISE = 150  # enough to act on — triggers threshold re-validation

# Legacy alias kept so run_outcome_check.py import doesn't break
MIN_SAMPLES_FOR_REVIEW = MIN_SAMPLES_FLAG

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
    "outcome_detail",    # plain-English explanation of what happened,
    # additive 2026-09-09 (unresolved_direction_polish_spec):
    # d1/h4 display subtypes at classification time, so the
    # unresolved bucket can be split in future accuracy analysis.
    # Old rows blank; loss_species-style migration on append.
    "subtype",
    # data_at_source_spec.md P1: "live" (OANDA mid at log time) or
    # "prior_close" (fallback, labelled). BLANK on rows logged before
    # 2026-09-30: those all used the previous D1 close.
    "price_basis",
    # decision_logic_spec.md: the decision rules in force when the row was
    # written (official_decision.LOGIC_VERSION). BLANK on rows logged before
    # Phase 5 (2026-09-30) — never pool evidence across rule changes.
    "logic_version",
]


def _price_plausible(instrument: str, price) -> bool:
    """Reject impossible price scales (cross-contamination): a JPY cross below
    10, or a non-JPY pair above 50, cannot be a real price for that instrument.
    Prevents the kind of synthetic pollution (GBP_JPY logged at 1.91) that once
    corrupted the outcome log."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return True   # non-numeric handled elsewhere — don't block here
    if p <= 0:
        return False
    is_jpy = "JPY" in (instrument or "")
    if is_jpy and p < 10:
        return False
    if not is_jpy and p > 50:
        return False
    return True


def _subtype_tag(regime_data: Dict) -> str:
    """Compact d1/h4 subtype record for the ledger — blank when both empty,
    else 'd1=<sub>;h4=<sub>' with empty parts omitted."""
    parts = []
    for tf, key in (("d1", "regime_d1_subtype"), ("h4", "regime_h4_subtype")):
        v = (regime_data.get(key) or "").strip()
        if v:
            parts.append(f"{tf}={v}")
    return ";".join(parts)


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

    # Refuse to pollute the log with an impossible price for this instrument.
    if not _price_plausible(instrument, regime_data.get("current_price", 0.0)):
        return log_id

    # get_regime's "regime" is the DAILY label, not the daily+4-hour composite.
    # The ledger column is still named composite_regime: it cannot be renamed
    # in an append-only ledger. Grading and accuracy buckets key on it.
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
        "subtype":            _subtype_tag(regime_data),
        "weekly_context":     regime_data.get("weekly_context", ""),
        "timeframe_conflict": regime_data.get("timeframe_conflict", False),
        "stand_down":         regime_data.get("stand_down", False),
        # The closed D1 bar the classification was computed from: the right
        # baseline for D1-bar outcomes, and stable across runs on the same
        # bar, so repeat logs of one state still merge (review V2).
        "price_at_log":       regime_data.get("last_close",
                                              regime_data.get("current_price", 0.0)),
        "price_basis":        "d1_close" if "last_close" in regime_data
                              else regime_data.get("price_basis", ""),
        "atr_pips_at_log":    regime_data.get("atr_pips", 0.0),
        "prediction_type":    prediction_type,
        "prediction_window":  prediction_window,
        "outcome_filled":     False,
        "bars_elapsed":       0,
        "price_at_outcome":   "",
        "outcome_correct":    "",
        "outcome_detail":     "",
        "logic_version":      regime_data.get("logic_version", ""),
    }

    _write_row(row)
    return log_id


def check_pending_outcomes(instrument, recent_closes, recent_highs, recent_lows, recent_index=None):
    """Grade pending classifications. Holds the ledger lock from the read to
    the write, so a row appended meanwhile cannot be lost (ledger_io)."""
    with locked(LOG_FILE):
        return _check_pending_outcomes_unlocked(instrument, recent_closes, recent_highs, recent_lows, recent_index)


def _check_pending_outcomes_unlocked(
    instrument:    str,
    recent_closes: List[float],
    recent_highs:  List[float],
    recent_lows:   List[float],
    recent_index=None,
) -> int:
    """
    Check all pending (outcome_filled=False) classifications for
    this instrument and fill outcomes where enough bars have elapsed.

    Args:
        instrument:     "GBP_AUD" or "GBP_JPY"
        recent_closes:  list of recent D1 closes (newest last)
        recent_highs:   list of recent D1 highs (newest last)
        recent_lows:    list of recent D1 lows (newest last)
        recent_index:   DatetimeIndex from the OANDA D1 frame (optional).
                        When provided, bars_elapsed = number of timestamps
                        strictly after the row's log time — exact, not
                        calendar-approximated. Falls back to
                        _estimate_bars_elapsed_calendar() when absent.

    Returns:
        number of outcomes filled in this call
    """
    if not os.path.exists(LOG_FILE):
        return 0

    rows = _read_all()
    filled_count = 0
    now_price = recent_closes[-1] if recent_closes else None

    # Excluded rows are never graded (exclusions.py). They are passed through
    # to `updated` untouched — the ledger is append-only, so an excluded row
    # stays in the record; it simply never earns an outcome or a tally.
    is_excluded = excluder("regime_classification_log.csv")

    updated = []
    for row in rows:
        if (row["instrument"] != instrument or
                row["outcome_filled"] == "True"):
            updated.append(row)
            continue

        if is_excluded(row):
            updated.append(row)
            continue

        # Count bars elapsed since log timestamp
        log_time = datetime.fromisoformat(
            row["timestamp"].replace("Z", "+00:00")
        )
        bars_elapsed = _count_bars_after(log_time, recent_index)
        window       = int(row.get("prediction_window", 20))

        if bars_elapsed < window:
            updated.append(row)
            continue

        # Enough bars elapsed — measure the outcome at the bar EXACTLY `window`
        # bars after the log time, NOT the latest bar. If the checker ran late
        # (bars_elapsed >> window), grading on closes[-1] would score a fixed
        # 20-bar prediction on price 30-60 bars out. Truncate the series to end
        # at the window bar so _measure_outcome's tail-relative reads are correct.
        price_at_log = float(row["price_at_log"])
        atr_at_log   = float(row["atr_pips_at_log"])
        regime       = row["composite_regime"]
        pred_type    = row["prediction_type"]

        c_meas, h_meas, l_meas = recent_closes, recent_highs, recent_lows
        price_at_outcome = now_price
        if (recent_index is not None and
                len(recent_index) == len(recent_closes) ==
                len(recent_highs) == len(recent_lows)):
            slice_end = len(recent_index) - bars_elapsed + window
            if window <= slice_end <= len(recent_closes):
                c_meas = recent_closes[:slice_end]
                h_meas = recent_highs[:slice_end]
                l_meas = recent_lows[:slice_end]
                price_at_outcome = c_meas[-1]

        correct, detail = _measure_outcome(
            pred_type, price_at_log, atr_at_log,
            regime, c_meas, h_meas, l_meas,
            row.get("structure_d1", ""),
            row["instrument"],
        )

        row["outcome_filled"]   = True
        row["bars_elapsed"]     = bars_elapsed
        row["price_at_outcome"] = price_at_outcome if price_at_outcome is not None else ""
        row["outcome_correct"]  = correct
        row["outcome_detail"]   = detail
        filled_count += 1
        updated.append(row)

    if filled_count > 0:
        _write_all(updated)

    return filled_count


def get_regime_accuracy(
    instrument:  str = None,
    min_samples: int = 1,
) -> Dict:
    """
    Compute regime classification accuracy from filled outcomes.

    Returns dict keyed by composite_regime:
      {regime: {accuracy, n, correct, flagged, actionable, adx_*}}

    flagged    = n >= MIN_SAMPLES_FLAG   and accuracy < MIN_ACCURACY_THRESHOLD
    actionable = n >= MIN_SAMPLES_REVISE and accuracy < MIN_ACCURACY_THRESHOLD

    flagged-only  → watch closely, pattern emerging but not yet conclusive
    actionable    → rerun threshold validation now
    """
    rows = _read_all()
    # Contaminated/withdrawn rows never reach a tally (exclusions.py). The
    # ledger keeps them; the accuracy N does not count them.
    rows = filter_rows(rows, "regime_classification_log.csv")
    filled = [r for r in rows
              if r.get("outcome_filled") == "True"
              and (instrument is None or r["instrument"] == instrument)]

    from collections import defaultdict
    raw_counts = defaultdict(int)
    for r in filled:
        raw_counts[r["composite_regime"]] += 1

    # Anti-inflation: back-to-back reruns of an unchanged market state count
    # as ONE observation (same rule as shadow episode counting). The ledger
    # keeps every row; only the accuracy N dedupes. See _independent_states.
    filled = _independent_states(filled)

    groups = defaultdict(list)
    for r in filled:
        groups[r["composite_regime"]].append(r)

    result = {}
    for regime, regime_rows in groups.items():
        n        = len(regime_rows)
        correct  = sum(1 for r in regime_rows
                       if str(r.get("outcome_correct")) == "True")
        accuracy = correct / n if n > 0 else 0.0
        adx_vals = [float(r["adx_d1"]) for r in regime_rows
                    if r.get("adx_d1")]
        below    = accuracy < MIN_ACCURACY_THRESHOLD

        result[regime] = {
            "accuracy":   round(accuracy, 3),
            "n":          n,
            "n_raw":      raw_counts[regime],
            "correct":    correct,
            "flagged":    n >= MIN_SAMPLES_FLAG   and below,
            "actionable": n >= MIN_SAMPLES_REVISE and below,
            "adx_min":    round(min(adx_vals), 1) if adx_vals else None,
            "adx_max":    round(max(adx_vals), 1) if adx_vals else None,
            "adx_avg":    round(sum(adx_vals)/len(adx_vals), 1)
                          if adx_vals else None,
        }

    return result


def get_accuracy_report(instrument: str = None) -> str:
    """
    Return a plain-English accuracy report for all regimes.
    Two-tier flag system:
      flagged only  (n >= 60)  → watch closely, not yet actionable
      actionable    (n >= 150) → rerun threshold validation now
    """
    acc = get_regime_accuracy(instrument=instrument)
    if not acc:
        return "No completed outcomes yet. Keep running the framework."

    lines = ["Regime Classification Accuracy Report",
             "─" * 45]
    for regime, data in sorted(acc.items()):
        if data["actionable"]:
            flag = " ← REVISE — rerun threshold validation"
        elif data["flagged"]:
            flag = " ← FLAG — watch closely, not yet actionable"
        else:
            flag = ""
        dedupe = (f" [{data['n_raw']} rows -> {data['n']} independent]"
                  if data.get("n_raw", data["n"]) != data["n"] else "")
        lines.append(
            f"  {regime:<16}: {data['accuracy']:.0%} "
            f"({data['correct']}/{data['n']} correct){dedupe}{flag}"
        )
    lines.append("─" * 45)
    lines.append(
        f"Flags at {MIN_SAMPLES_FLAG} samples. "
        f"Actionable at {MIN_SAMPLES_REVISE} samples."
    )
    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _independent_states(rows: List[Dict]) -> List[Dict]:
    """Collapse identical back-to-back classifications into one observation.

    WHY: repeated manual/scheduled runs against an unchanged market write
    near-duplicate rows minutes apart (2026-07-29: 22 rows = 5 states).
    Counting each row inflates N — the same anti-inflation rule shadow
    episode counting applies (episodes, not raw fires, are evidence).

    A row joins an open state when it shares
      (instrument, prediction_type, price_at_log, adx_d1, adx_h4)
    with it AND lands within that state's outcome window
    (prediction_window daily bars) of the state's FIRST row. The first row
    of each state is the observation kept — later identical rows are echoes
    of it, so the state's outcome is the first row's outcome. Distinct
    snapshots (any field differs, or outside the window) stay separate.
    The ledger itself is never touched; this collapses counting only.
    """
    def _key(r):
        return (r.get("instrument"), r.get("prediction_type"),
                r.get("price_at_log"), r.get("adx_d1"), r.get("adx_h4"))

    def _ts(r):
        try:
            return datetime.fromisoformat(
                r["timestamp"].replace("Z", "+00:00"))
        except Exception:
            return None

    reps, open_states = [], {}             # key -> first-row timestamp
    for r in sorted(rows, key=lambda r: r.get("timestamp", "")):
        t = _ts(r)
        if t is None:                      # unparseable time: count it, once
            reps.append(r)
            continue
        try:
            window = timedelta(days=int(float(r.get("prediction_window") or 0)))
        except (TypeError, ValueError):
            window = timedelta(0)
        k = _key(r)
        first = open_states.get(k)
        if first is not None and window > timedelta(0) and (t - first) < window:
            continue                       # echo of an open state — not counted
        open_states[k] = t
        reps.append(r)
    return reps


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
    instrument:   str = "GBP_AUD",
) -> Tuple[bool, str]:
    """
    Was the logged prediction right? (no costs, any amount counts)

    MOMENTUM_WIN:  price at the outcome bar is beyond the logged price in the
                   trend direction.
    MR_WIN:        KNOWN DEFECT (audit 2026-09-29 item 2): "the mean" is the
                   average of the 20 bars AFTER the log, so a steady trend
                   also scores as correct.
    VOL_EXPANSION: the average daily range over the last 8 bars of the
                   window is at least 1.3x the logged ATR.
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
            from regime_detection import PAIRS
            pair         = PAIRS.get(instrument)
            pip_size     = pair.pip_size if pair else 0.0001
            atr_in_price = atr_at_log * pip_size
            ratio = realized_vol / atr_in_price \
                    if atr_in_price > 0 else 1.0
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


def _count_bars_after(log_time: datetime, index=None) -> int:
    """
    Count D1 bar timestamps in index that are strictly after log_time.

    When index is available (DatetimeIndex from the OANDA D1 frame)
    this gives the exact number of completed bars since the
    classification was logged — no calendar approximation needed.

    Falls back to _estimate_bars_elapsed_calendar() when index is None.
    """
    if index is None:
        return _estimate_bars_elapsed_calendar(log_time)
    try:
        import pandas as pd
        ts = pd.Timestamp(log_time)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        idx = index
        if hasattr(idx, "tz") and idx.tz is None:
            idx = idx.tz_localize("UTC")
        elif hasattr(idx, "tz") and idx.tz is not None:
            idx = idx.tz_convert("UTC")
        return int((idx > ts).sum())
    except Exception:
        return _estimate_bars_elapsed_calendar(log_time)


def _estimate_bars_elapsed_calendar(log_time: datetime) -> int:
    """
    Fallback: estimate D1 bars elapsed using 5/7 calendar approximation.
    Used when no DatetimeIndex is available.
    """
    now        = datetime.now(timezone.utc)
    delta      = now - log_time
    total_days = delta.days
    return max(0, int(total_days * 5 / 7))


def _migrate_header() -> None:
    """Additive header migration (subtype column, 2026-09-09): when the
    ledger's header predates FIELDNAMES, rewrite with the current header —
    every existing row verbatim in its old columns, blank in the new one.
    The logger maintaining its own schema; values never edited. Must run
    before any append."""
    migrate_header(LOG_FILE, FIELDNAMES)       # shared, locked (ledger_io)


def _write_row(row: Dict) -> None:
    """Append a single row to the log file (locked; ledger_io)."""
    with locked(LOG_FILE):
        if os.path.exists(LOG_FILE):
            _migrate_header()
        append_row(LOG_FILE, FIELDNAMES, row)


def _read_all() -> List[Dict]:
    """Read all rows from the log file."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", newline="") as f:
        return list(csv.DictReader(f))


def _write_all(rows: List[Dict]) -> None:
    """Overwrite the log file with updated rows, atomically (ledger_io).
    Callers doing read-modify-write must hold locked(LOG_FILE) from the read."""
    atomic_write_rows(LOG_FILE, FIELDNAMES, rows)
