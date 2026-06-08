"""
tests/unit/phase2/test_cron_health.py

Unit tests for verify_cron.py health checks.

Plain English: these tests confirm that the health check correctly identifies
               when the system is ready vs when something needs fixing.
               No real OANDA calls, no cron jobs — isolated file-based checks.
"""

import json
import os
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from verify_cron import (
    check_env_vars,
    check_last_run,
    check_journal,
    check_cron_log,
    run_health_check,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_last_run(path: Path, age_hours: float) -> None:
    """Write a last_run.json with a timestamp `age_hours` old."""
    run_dt = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    data = {
        "date":     run_dt.strftime("%Y-%m-%d"),
        "time_utc": run_dt.strftime("%H:%M"),
        "bias":     "BEARISH",
        "grade":    "A",
    }
    path.write_text(json.dumps(data))


def _write_cron_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


# ── check_env_vars() ──────────────────────────────────────────────────────────

class TestEnvVars:

    def test_returns_dict_with_passed_and_reason(self, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY", "test-key")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "test-acct")
        result = check_env_vars()
        assert "passed" in result
        assert "reason" in result

    def test_passes_when_both_vars_set(self, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY", "live-key-abc")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-123456")
        result = check_env_vars()
        assert result["passed"] is True

    def test_fails_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("OANDA_API_KEY", raising=False)
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-123456")
        result = check_env_vars()
        assert result["passed"] is False
        assert "OANDA_API_KEY" in result["reason"]

    def test_fails_when_account_id_missing(self, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY", "live-key-abc")
        monkeypatch.delenv("OANDA_ACCOUNT_ID", raising=False)
        result = check_env_vars()
        assert result["passed"] is False
        assert "OANDA_ACCOUNT_ID" in result["reason"]

    def test_fails_when_both_missing(self, monkeypatch):
        monkeypatch.delenv("OANDA_API_KEY",    raising=False)
        monkeypatch.delenv("OANDA_ACCOUNT_ID", raising=False)
        result = check_env_vars()
        assert result["passed"] is False

    def test_reason_is_non_empty_string(self, monkeypatch):
        monkeypatch.delenv("OANDA_API_KEY", raising=False)
        result = check_env_vars()
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 10


# ── check_last_run() ──────────────────────────────────────────────────────────

class TestLastRun:

    def test_fails_when_file_missing(self, tmp_path):
        result = check_last_run(tmp_path / "nonexistent.json")
        assert result["passed"] is False
        assert "not found" in result["reason"].lower()

    def test_passes_with_fresh_context(self, tmp_path):
        """30-minute-old last_run.json → passes (well within 4h limit)."""
        p = tmp_path / "last_run.json"
        _write_last_run(p, age_hours=0.5)
        result = check_last_run(p)
        assert result["passed"] is True

    def test_fails_with_stale_context(self, tmp_path):
        """6-hour-old last_run.json → fails (beyond 4h limit)."""
        p = tmp_path / "last_run.json"
        _write_last_run(p, age_hours=6.0)
        result = check_last_run(p)
        assert result["passed"] is False

    def test_stale_reason_mentions_expiry(self, tmp_path):
        p = tmp_path / "last_run.json"
        _write_last_run(p, age_hours=6.0)
        result = check_last_run(p)
        assert "expired" in result["reason"].lower() or "limit" in result["reason"].lower()

    def test_fails_with_corrupted_json(self, tmp_path):
        p = tmp_path / "last_run.json"
        p.write_text("{this is not valid json}")
        result = check_last_run(p)
        assert result["passed"] is False


# ── check_journal() ───────────────────────────────────────────────────────────

class TestJournal:

    def test_passes_when_journal_exists(self, tmp_path):
        p = tmp_path / "run_journal.csv"
        p.write_text("run_id,date\n")
        result = check_journal(p)
        assert result["passed"] is True

    def test_fails_when_journal_missing(self, tmp_path):
        result = check_journal(tmp_path / "nonexistent.csv")
        assert result["passed"] is False

    def test_reason_non_empty(self, tmp_path):
        result = check_journal(tmp_path / "nonexistent.csv")
        assert isinstance(result["reason"], str) and len(result["reason"]) > 0


# ── check_cron_log() ─────────────────────────────────────────────────────────

class TestCronLog:

    def test_fails_when_log_missing(self, tmp_path):
        result = check_cron_log(tmp_path / "logs" / "cron.log")
        assert result["passed"] is False
        assert "not found" in result["reason"].lower() or "setup_cron" in result["reason"]

    def test_fails_when_log_empty(self, tmp_path):
        p = tmp_path / "logs" / "cron.log"
        _write_cron_log(p, [])
        result = check_cron_log(p)
        assert result["passed"] is False

    def test_passes_with_log_entries(self, tmp_path):
        p = tmp_path / "logs" / "cron.log"
        _write_cron_log(p, [
            "2026-06-06 23:30  === Framework run — Pre-London ===",
            "2026-06-06 23:30  Grade: A | Alignment: 82 | Price: 2.03201",
        ])
        result = check_cron_log(p)
        assert result["passed"] is True

    def test_reason_mentions_entry_count(self, tmp_path):
        p = tmp_path / "logs" / "cron.log"
        _write_cron_log(p, ["line1", "line2", "line3"])
        result = check_cron_log(p)
        assert "3" in result["reason"]


# ── run_health_check() ───────────────────────────────────────────────────────

class TestRunHealthCheck:

    def test_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY",    "key")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "acct")
        result = run_health_check(
            last_run_path=tmp_path / "no.json",
            journal_path=tmp_path / "no.csv",
            cron_log_path=tmp_path / "no.log",
        )
        assert "all_passed" in result
        assert "checks"     in result

    def test_all_passed_true_when_all_pass(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY",    "live-key")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-99999")

        lr = tmp_path / "last_run.json"
        _write_last_run(lr, age_hours=0.5)

        jn = tmp_path / "run_journal.csv"
        jn.write_text("run_id,date\n")

        cl = tmp_path / "logs" / "cron.log"
        _write_cron_log(cl, ["2026-06-07 23:30  === Framework run ==="])

        result = run_health_check(lr, jn, cl)
        assert result["all_passed"] is True

    def test_all_passed_false_when_any_fails(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OANDA_API_KEY", raising=False)   # env check fails
        result = run_health_check(
            last_run_path=tmp_path / "no.json",
            journal_path=tmp_path / "no.csv",
            cron_log_path=tmp_path / "no.log",
        )
        assert result["all_passed"] is False

    def test_checks_dict_has_four_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OANDA_API_KEY",    "k")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "a")
        result = run_health_check(
            last_run_path=tmp_path / "x.json",
            journal_path=tmp_path / "x.csv",
            cron_log_path=tmp_path / "x.log",
        )
        assert set(result["checks"].keys()) == {
            "env_vars", "last_run", "journal", "cron_log"
        }

    def test_partial_failure_correctly_reported(self, tmp_path, monkeypatch):
        """One check fails, others pass — all_passed must be False."""
        monkeypatch.setenv("OANDA_API_KEY",    "live-key")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-99999")

        lr = tmp_path / "last_run.json"
        _write_last_run(lr, age_hours=0.5)

        # Journal missing → that check fails
        cl = tmp_path / "logs" / "cron.log"
        _write_cron_log(cl, ["2026-06-07 23:30  === Framework run ==="])

        result = run_health_check(lr, tmp_path / "missing.csv", cl)
        assert result["all_passed"] is False
        assert result["checks"]["journal"]["passed"] is False
        assert result["checks"]["env_vars"]["passed"] is True
