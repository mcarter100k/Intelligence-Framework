"""
tests/conftest.py

Shared fixtures available to every test in the suite.
Import nothing from here directly — pytest injects fixtures by name.

Plain English: This file is the "setup room" before every test.
               It creates fake versions of external things (OANDA prices,
               journal files on disk) so tests run fast and never hit
               the real market or real files.
"""

import csv
import json
import pytest
from pathlib import Path
from datetime import date, timedelta

from tests.fixtures.journal_samples import (
    JOURNAL_FIELDS,
    write_journal_csv,
    rows_two_losses_today,
    rows_two_trades_today_one_win,
    rows_open_trade_today,
    rows_yesterday_loss_only,
    rows_unlabeled_bearish,
    rows_already_labeled,
)


# ── Temporary journal files ────────────────────────────────────────────────────

@pytest.fixture
def empty_journal(tmp_path) -> Path:
    """A journal CSV with headers but no rows — brand-new install."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, [])
    return p


@pytest.fixture
def journal_two_losses(tmp_path) -> Path:
    """Journal with two losing trades today totaling -2.3% (Scenario C)."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_two_losses_today())
    return p


@pytest.fixture
def journal_two_trades(tmp_path) -> Path:
    """Journal with two completed trades today (at the per-session trade limit)."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_two_trades_today_one_win())
    return p


@pytest.fixture
def journal_open_trade(tmp_path) -> Path:
    """Journal with one open trade — pnl_r is empty (trade not closed yet)."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_open_trade_today())
    return p


@pytest.fixture
def journal_yesterday_loss(tmp_path) -> Path:
    """Big loss yesterday — today's slate should be clean."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_yesterday_loss_only())
    return p


@pytest.fixture
def journal_unlabeled_bearish(tmp_path) -> Path:
    """One unlabeled BEARISH run ready for auto-labeling."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_unlabeled_bearish())
    return p


@pytest.fixture
def journal_mixed_labeled(tmp_path) -> Path:
    """Two labeled rows + one unlabeled — only unlabeled should be processed."""
    p = tmp_path / "run_journal.csv"
    write_journal_csv(p, rows_already_labeled())
    return p


# ── Temporary last_run.json ────────────────────────────────────────────────────

@pytest.fixture
def last_run_fresh(tmp_path) -> Path:
    """
    A last_run.json written 30 minutes ago — context is fresh.
    Plain English: the framework ran half an hour ago, still valid.
    """
    from datetime import datetime, timezone, timedelta
    run_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    data = {
        "date":           run_time.strftime("%Y-%m-%d"),
        "time_utc":       run_time.strftime("%H:%M"),
        "bias":           "BEARISH",
        "conviction_score": 72,
        "price":          2.0300,
        "decision": {
            "direction":  "SHORT",
            "grade":      "A",
            "risk_pct":   1.0,
        },
    }
    p = tmp_path / "last_run.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def last_run_stale(tmp_path) -> Path:
    """
    A last_run.json written 5 hours 45 minutes ago — context is expired.
    Plain English: the framework ran too long ago to trust its levels.
    """
    from datetime import datetime, timezone, timedelta
    run_time = datetime.now(timezone.utc) - timedelta(hours=5, minutes=45)
    data = {
        "date":           run_time.strftime("%Y-%m-%d"),
        "time_utc":       run_time.strftime("%H:%M"),
        "bias":           "BEARISH",
        "conviction_score": 72,
        "price":          2.0300,
        "decision": {"direction": "SHORT", "grade": "A", "risk_pct": 1.0},
    }
    p = tmp_path / "last_run.json"
    p.write_text(json.dumps(data))
    return p


# ── OANDA mock helpers ────────────────────────────────────────────────────────

@pytest.fixture
def mock_oanda_price():
    """
    Returns a function that mimics oanda_feed.get_live_price().
    Plain English: pretends OANDA is giving us a live price without
                   actually calling the real API.
    """
    def _price():
        return 2.0300
    return _price


@pytest.fixture
def mock_oanda_win_close():
    """
    Returns a function that mimics fetching a 24h close that is a WIN.
    For a BEARISH run at 2.0300: close at 2.0078 = 222 pips down = WIN.
    """
    def _close(pair, target_date):
        return 2.0078
    return _close


@pytest.fixture
def mock_oanda_loss_close():
    """24h close that moved AGAINST a BEARISH bias — price went UP."""
    def _close(pair, target_date):
        return 2.0325   # 25 pips up from 2.0300 = LOSS for a BEARISH call
    return _close


@pytest.fixture
def mock_oanda_neutral_close():
    """24h close within the neutral threshold — barely moved."""
    def _close(pair, target_date):
        return 2.0315   # only 15 pips up = NEUTRAL (below 20-pip threshold)
    return _close


@pytest.fixture
def mock_oanda_unavailable():
    """Simulates OANDA being offline — returns None."""
    def _close(pair, target_date):
        return None
    return _close
