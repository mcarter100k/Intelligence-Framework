"""
fixtures/journal_samples.py

Reusable journal rows for testing session_guard, auto_label, review_runs.
Every row mirrors the exact columns in run_journal.csv so tests stay
in sync with the real schema.
"""

import csv
import io
from datetime import date, timedelta

# Matches _JOURNAL_FIELDS in market_brain.py exactly
JOURNAL_FIELDS = [
    "run_id", "date", "time_utc", "session", "framework_version",
    "primary_state", "setup_type", "quality", "action",
    "bias", "conviction_score", "live_structural_conflict",
    "best_setup", "wait_for", "flip_if", "breaks_if",
    "intraday_view", "swing_view",
    "price", "htf_context", "regime", "macro_quadrant", "fib_pct", "higher_low_formed",
    "value_zone", "value_verdict", "value_aligned", "nearest_level",
    "sweep_up", "sweep_down", "sweep_confirmed",
    "cot_extreme", "cot_aud_pct", "strength_diff",
    "vix_level", "vix_change", "vix_regime",
    "atr_pips", "fuel_pct",
    "size_note", "invalidation_level", "high_impact_event_soon",
    "degraded", "degraded_components", "rate_stale_warning", "cot_data_date",
    "next_day_close", "next_london_open", "outcome_label",
    "trigger_fired", "framework_was_right",
    "trade_taken", "trade_direction",
    "entry", "stop", "target", "exit", "pnl_r", "notes",
    "grade",
]

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TWO_DAYS_AGO = (date.today() - timedelta(days=2)).isoformat()


def _base_row(**overrides) -> dict:
    """Return a minimal valid journal row with sensible defaults."""
    row = {f: "" for f in JOURNAL_FIELDS}
    row.update({
        "run_id":            "test0001",
        "date":              TODAY,
        "time_utc":          "07:30",
        "session":           "London",
        "framework_version": "1.0",
        "bias":              "BEARISH",
        "conviction_score":  "72",
        "quality":           "HIGH",
        "grade":             "A",
        "price":             "2.0300",
        "regime":            "TRENDING_DOWN",
        "htf_context":       "ESTABLISHED_DOWNTREND",
        "trade_taken":       "NO",
        "outcome_label":     "",
        "pnl_r":             "",
    })
    row.update(overrides)
    return row


# ── Pre-built scenario rows ────────────────────────────────────────────────────

def row_no_trades_today() -> list:
    """Empty journal — no trades today at all."""
    return []


def rows_two_losses_today() -> list:
    """
    Scenario C: two closed losing trades today exceed the 2% daily loss limit.
    Trade 1: -1.1%  Trade 2: -1.2%  Total: -2.3%
    """
    return [
        _base_row(
            run_id="loss001", date=TODAY, time_utc="08:00",
            trade_taken="YES", trade_direction="SHORT",
            pnl_r="-1.1", outcome_label="LOSS",
        ),
        _base_row(
            run_id="loss002", date=TODAY, time_utc="10:00",
            trade_taken="YES", trade_direction="SHORT",
            pnl_r="-1.2", outcome_label="LOSS",
        ),
    ]


def rows_two_trades_today_one_win() -> list:
    """Two trades today (at trade count limit), first is WIN, second is LOSS — net positive."""
    return [
        _base_row(
            run_id="cnt001", date=TODAY, time_utc="07:45",
            trade_taken="YES", pnl_r="2.1", outcome_label="WIN",
        ),
        _base_row(
            run_id="cnt002", date=TODAY, time_utc="10:30",
            trade_taken="YES", pnl_r="-0.5", outcome_label="LOSS",
        ),
    ]


def rows_open_trade_today() -> list:
    """One trade open today — pnl_r empty because trade not yet closed."""
    return [
        _base_row(
            run_id="open001", date=TODAY, time_utc="08:00",
            trade_taken="YES", pnl_r="", outcome_label="",
        ),
    ]


def rows_yesterday_loss_only() -> list:
    """Loss was yesterday — today's slate is clean."""
    return [
        _base_row(
            run_id="yest001", date=YESTERDAY, time_utc="09:00",
            trade_taken="YES", pnl_r="-2.5", outcome_label="LOSS",
        ),
    ]


def rows_unlabeled_bearish() -> list:
    """One unlabeled BEARISH run from yesterday — ready for auto-labeling."""
    return [
        _base_row(
            run_id="label001", date=YESTERDAY, time_utc="08:00",
            bias="BEARISH", price="2.0300",
            outcome_label="", next_day_close="", framework_was_right="",
        ),
    ]


def rows_unlabeled_bullish() -> list:
    """One unlabeled BULLISH run from yesterday."""
    return [
        _base_row(
            run_id="label002", date=YESTERDAY, time_utc="08:00",
            bias="BULLISH", price="2.0300",
            outcome_label="", next_day_close="", framework_was_right="",
        ),
    ]


def rows_already_labeled() -> list:
    """Two labeled rows + one unlabeled — only the unlabeled one should be processed."""
    return [
        _base_row(run_id="done001", date=TWO_DAYS_AGO, outcome_label="WIN",
                  next_day_close="2.0078", framework_was_right="YES"),
        _base_row(run_id="done002", date=TWO_DAYS_AGO, outcome_label="LOSS",
                  next_day_close="2.0350", framework_was_right="NO"),
        _base_row(run_id="todo001", date=YESTERDAY, bias="BEARISH",
                  price="2.0300", outcome_label=""),
    ]


def rows_c_grade_trade_taken() -> list:
    """Psychological flag: trade taken on a C grade (should never happen)."""
    return [
        _base_row(
            run_id="psych001", date=TODAY,
            grade="C", quality="DO NOT TRADE",
            trade_taken="YES", pnl_r="-0.5", outcome_label="LOSS",
        ),
    ]


# ── CSV helpers ────────────────────────────────────────────────────────────────

def write_journal_csv(path, rows: list) -> None:
    """Write rows to a CSV file at path. Creates file even if rows is empty."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def read_journal_csv(path) -> list:
    """Read all rows from a journal CSV. Returns list of dicts."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
