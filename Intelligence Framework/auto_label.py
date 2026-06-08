"""
auto_label.py
─────────────
Automatically scores past framework runs as WIN / LOSS / NEUTRAL.

Plain English: every time the framework runs, it records its directional
               bias (BULLISH or BEARISH). After 24 hours we can look at
               where price actually closed and grade the call. This module
               does that grading automatically so the calibration engine
               has real outcome data to learn from.

Labeling rules:
  WIN     — price moved ≥ 20 pips WITH the bias direction
  NEUTRAL — price moved < 20 pips in either direction (no clean move)
  LOSS    — price moved ≥ 20 pips AGAINST the bias direction

Only BULLISH and BEARISH biases are graded. Rows with NEUTRAL or
NO TRADE bias are skipped — there is no directional call to score.

Only rows older than today are processed — the 24h window must have
closed before grading makes sense.

Usage:
    from auto_label import label_journal

    stats = label_journal("run_journal.csv")
    print(f"Labeled {stats['labeled']} rows")

For testing without OANDA:
    stats = label_journal("run_journal.csv", fetch_fn=lambda date: 2.0078)
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional


# ── Constants ─────────────────────────────────────────────────────────────────
WIN_THRESHOLD_PIPS: int = 20    # minimum pips with bias to call WIN
PIPS_MULTIPLIER: float = 10_000 # GBP/AUD: 1 pip = 0.0001 price movement

LABELABLE_BIASES = {"BULLISH", "BEARISH"}


# ── Pure labeling logic ───────────────────────────────────────────────────────

def compute_label(
    run_price: float,
    bias: str,
    close_price: float,
    win_threshold_pips: int = WIN_THRESHOLD_PIPS,
) -> dict:
    """
    Score a single framework run against its 24h outcome.

    Plain English: the framework made a directional call (up or down).
                   After 24 hours we check which way price actually moved.
                   If it moved ≥ 20 pips with the call → WIN.
                   If it moved ≥ 20 pips against the call → LOSS.
                   If it barely moved either way → NEUTRAL.

    Args:
        run_price           : price when the framework ran (from journal)
        bias                : "BULLISH" or "BEARISH" (case insensitive)
        close_price         : price 24h after the run
        win_threshold_pips  : pips needed to call WIN or LOSS (default 20)

    Returns dict:
        outcome_label       : "WIN" | "LOSS" | "NEUTRAL" | "" (unlabelable)
        framework_was_right : "YES" | "NO" | ""
        pips_with_bias      : signed pips — positive = price moved with bias
    """
    bias_upper = bias.strip().upper()

    if bias_upper not in LABELABLE_BIASES:
        return {"outcome_label": "", "framework_was_right": "", "pips_with_bias": 0}

    if bias_upper == "BEARISH":
        # For BEARISH: price falling is good → run_price - close_price
        pips_with_bias = round((run_price - close_price) * PIPS_MULTIPLIER, 1)
    else:
        # For BULLISH: price rising is good → close_price - run_price
        pips_with_bias = round((close_price - run_price) * PIPS_MULTIPLIER, 1)

    if pips_with_bias >= win_threshold_pips:
        return {"outcome_label": "WIN",     "framework_was_right": "YES", "pips_with_bias": pips_with_bias}
    elif pips_with_bias <= -win_threshold_pips:
        return {"outcome_label": "LOSS",    "framework_was_right": "NO",  "pips_with_bias": pips_with_bias}
    else:
        return {"outcome_label": "NEUTRAL", "framework_was_right": "NO",  "pips_with_bias": pips_with_bias}


# ── OANDA price fetch ─────────────────────────────────────────────────────────

def fetch_next_close(run_date: str, pair: str = "GBPAUD") -> Optional[float]:
    """
    Fetch the daily close of the bar immediately after run_date from OANDA.

    Plain English: get the price at which GBP/AUD closed on the day after
                   the framework ran. That is the reference price we score
                   the bias call against.

    Returns float or None if OANDA is unavailable.
    """
    try:
        from oanda_feed import get_daily_bars

        bars = get_daily_bars(pair=pair, count=5)
        if bars is None or bars.empty:
            return None

        target_date = date.fromisoformat(run_date) + timedelta(days=1)

        # Walk forward through bars to find the first one on or after target_date
        for idx in bars.index:
            bar_date = idx.date() if hasattr(idx, "date") else idx
            if bar_date >= target_date:
                return float(bars.loc[idx, "Close"])

        # Fallback: use the most recent available close
        return float(bars["Close"].iloc[-1])

    except Exception:
        return None


# ── Orchestrator ──────────────────────────────────────────────────────────────

def label_journal(
    journal_path,
    fetch_fn: Optional[Callable[[str], Optional[float]]] = None,
) -> dict:
    """
    Read the journal, label every unlabeled row older than today, write back.

    Plain English: scan the journal for runs that haven't been scored yet
                   (outcome_label is blank) and whose 24h window has closed
                   (date is before today). For each one, fetch the next-day
                   close price and assign WIN / LOSS / NEUTRAL.

    Args:
        journal_path : path to the journal CSV
        fetch_fn     : callable(run_date: str) -> Optional[float]
                       defaults to fetch_next_close (calls OANDA)
                       inject a lambda in tests to avoid network calls

    Returns dict:
        labeled  : rows successfully labeled
        skipped  : rows skipped (already labeled, today's date, no bias)
        errors   : rows that could not be labeled (bad price, OANDA fail)
    """
    if fetch_fn is None:
        fetch_fn = fetch_next_close

    path = Path(journal_path)
    if not path.exists():
        return {"labeled": 0, "skipped": 0, "errors": 0}

    today_str = date.today().isoformat()
    labeled = skipped = errors = 0

    # Read all rows + preserve field order
    rows: list[dict] = []
    fields: list[str] = []
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return {"labeled": 0, "skipped": 0, "errors": 1}

    for row in rows:
        # Already labeled — leave it alone
        if row.get("outcome_label", "").strip():
            skipped += 1
            continue

        # Skip rows whose 24h window has not closed: today, future dates, or empty date.
        # Empty date is treated as untrustworthy — skip to avoid labeling corrupt rows.
        row_date = row.get("date", "").strip()
        if not row_date or row_date >= today_str:
            skipped += 1
            continue

        # No directional bias — nothing to score
        bias = row.get("bias", "").strip().upper()
        if bias not in LABELABLE_BIASES:
            skipped += 1
            continue

        # Parse run price
        try:
            run_price = float(row.get("price", ""))
        except (ValueError, TypeError):
            errors += 1
            continue

        # Fetch the next-day close
        run_date = row.get("date", "")
        close_price = fetch_fn(run_date)
        if close_price is None:
            errors += 1
            continue

        # Score and write back into the row
        result = compute_label(run_price, bias, close_price)
        row["outcome_label"]     = result["outcome_label"]
        row["framework_was_right"] = result["framework_was_right"]
        row["next_day_close"]    = str(round(close_price, 5))
        labeled += 1

    # Write all rows back (overwrite the file)
    if fields:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    return {"labeled": labeled, "skipped": skipped, "errors": errors}
