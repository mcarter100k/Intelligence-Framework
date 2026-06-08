"""
tests/unit/phase3/test_review_runs.py

Unit + behavioral tests for review_runs.py weekly performance report.

Plain English: confirm the weekly review correctly computes win rates,
               reports trade discipline, and handles sparse/complete journals
               without crashing — including journals with COT-extreme rows.
"""

import pytest

import review_runs
from review_runs import _pct, load_journal, review
from tests.fixtures.journal_samples import (
    _base_row, write_journal_csv, YESTERDAY, TWO_DAYS_AGO,
)
from tests.fixtures.market_scenarios import SCENARIO_L


# ── _pct() ────────────────────────────────────────────────────────────────────

class TestPct:

    def test_zero_denominator_returns_na(self):
        assert _pct(0, 0) == "n/a"

    def test_nonzero_numerator_zero_denominator_returns_na(self):
        assert _pct(5, 0) == "n/a"

    def test_100_percent(self):
        assert _pct(10, 10) == "100%"

    def test_0_percent(self):
        assert _pct(0, 10) == "0%"

    def test_50_percent(self):
        assert _pct(5, 10) == "50%"

    def test_rounds_correctly(self):
        assert _pct(1, 3) == "33%"

    def test_always_returns_string(self):
        assert isinstance(_pct(3, 7), str)


# ── load_journal() ────────────────────────────────────────────────────────────

class TestLoadJournal:

    def test_exits_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", tmp_path / "missing.csv")
        with pytest.raises(SystemExit):
            load_journal()

    def test_returns_list_of_dicts(self, tmp_path, monkeypatch):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(outcome_label="WIN")])
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        rows = load_journal()
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert isinstance(rows[0], dict)

    def test_returns_empty_list_for_header_only_file(self, tmp_path, monkeypatch):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        rows = load_journal()
        assert rows == []

    def test_all_fields_present_in_each_row(self, tmp_path, monkeypatch):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(outcome_label="WIN", quality="HIGH")])
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        rows = load_journal()
        assert "outcome_label" in rows[0]
        assert "quality" in rows[0]
        assert "grade" in rows[0]


# ── review() output sections ──────────────────────────────────────────────────

class TestReviewSections:

    def _run_review(self, tmp_path, monkeypatch, rows):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()

    def test_review_runs_without_crash(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY)])
        out = capsys.readouterr().out
        assert len(out) > 0

    def test_journal_health_section_appears(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY)])
        out = capsys.readouterr().out
        assert "JOURNAL HEALTH" in out

    def test_what_framework_said_section_appears(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY)])
        out = capsys.readouterr().out
        assert "WHAT THE FRAMEWORK SAID" in out

    def test_recent_runs_section_appears(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY)])
        out = capsys.readouterr().out
        assert "RECENT RUNS" in out

    def test_empty_journal_prints_no_runs_message(self, tmp_path, monkeypatch, capsys):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()
        out = capsys.readouterr().out
        assert "No runs" in out

    def test_total_run_count_in_header(self, tmp_path, monkeypatch, capsys):
        rows = [_base_row(date=YESTERDAY) for _ in range(3)]
        self._run_review(tmp_path, monkeypatch, rows)
        out = capsys.readouterr().out
        assert "3" in out

    def test_warning_when_fewer_than_10_outcomes(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY, outcome_label="WIN")])
        out = capsys.readouterr().out
        assert "Less than 10 outcomes" in out

    def test_next_steps_section_appears(self, tmp_path, monkeypatch, capsys):
        self._run_review(tmp_path, monkeypatch, [_base_row(date=YESTERDAY)])
        out = capsys.readouterr().out
        assert "NEXT STEPS" in out


# ── win rate by quality ───────────────────────────────────────────────────────

class TestWinRateByQuality:

    def _make_journal(self, tmp_path, monkeypatch, rows):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)

    def test_win_rate_section_shows_with_enough_outcomes(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(date=YESTERDAY, quality="HIGH",   outcome_label="WIN"),
            _base_row(date=YESTERDAY, quality="HIGH",   outcome_label="WIN"),
            _base_row(date=YESTERDAY, quality="HIGH",   outcome_label="LOSS"),
            _base_row(date=YESTERDAY, quality="MEDIUM", outcome_label="WIN"),
            _base_row(date=YESTERDAY, quality="MEDIUM", outcome_label="LOSS"),
        ]
        self._make_journal(tmp_path, monkeypatch, rows)
        review()
        out = capsys.readouterr().out
        assert "WIN RATE BY QUALITY" in out
        assert "HIGH" in out

    def test_below_5_outcomes_prints_insufficient_data_warning(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(date=YESTERDAY, quality="HIGH", outcome_label="WIN"),
            _base_row(date=YESTERDAY, quality="HIGH", outcome_label="LOSS"),
        ]
        self._make_journal(tmp_path, monkeypatch, rows)
        review()
        out = capsys.readouterr().out
        assert "need at least 5" in out.lower() or "Only" in out


# ── trade discipline ──────────────────────────────────────────────────────────

class TestTradeDiscipline:

    def test_discipline_section_appears(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(date=YESTERDAY, trade_taken="YES", pnl_r="1.5", outcome_label="WIN"),
            _base_row(date=YESTERDAY, trade_taken="NO"),
        ]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()
        out = capsys.readouterr().out
        assert "TRADE DISCIPLINE" in out
        assert "Trades taken" in out

    def test_unfilled_trade_taken_shows_guidance(self, tmp_path, monkeypatch, capsys):
        rows = [_base_row(date=YESTERDAY, trade_taken="", outcome_label="")]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()
        out = capsys.readouterr().out
        assert "trade_taken" in out.lower()

    def test_pnl_r_shown_when_trade_closed(self, tmp_path, monkeypatch, capsys):
        rows = [_base_row(date=YESTERDAY, trade_taken="YES", pnl_r="2.0", outcome_label="WIN")]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()
        out = capsys.readouterr().out
        assert "P&L" in out or "+2.00R" in out


# ── Behavioral: Scenario L — COT extreme rows handled in review ───────────────

class TestScenarioL_ReviewRuns:
    """
    Scenario L — GBP 85th percentile long (extreme).
    COT extreme flag flips the framework bias from BULLISH to BEARISH (contrarian).
    The review must display these rows without crashing and count them correctly.

    Plain English: a journal containing COT-extreme flagged runs is still a
                   valid journal. The weekly review doesn't break on them.
    """

    def _cot_extreme_row(self, outcome: str) -> dict:
        return _base_row(
            date=YESTERDAY,
            bias="BEARISH",
            cot_extreme="YES",
            outcome_label=outcome,
            quality="HIGH",
            grade="A",
        )

    def test_review_handles_cot_extreme_rows_without_crash(self, tmp_path, monkeypatch, capsys):
        rows = [self._cot_extreme_row("WIN"), self._cot_extreme_row("LOSS")]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()   # must not raise

    def test_cot_extreme_rows_counted_in_total(self, tmp_path, monkeypatch, capsys):
        rows = [self._cot_extreme_row("WIN")] * 3
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        monkeypatch.setattr(review_runs, "JOURNAL_PATH", p)
        review()
        out = capsys.readouterr().out
        assert "3 runs recorded" in out

    def test_scenario_l_label_references_cot(self):
        assert "COT" in SCENARIO_L["label"] or "extreme" in SCENARIO_L["label"]

    def test_scenario_l_flips_to_bearish_contrarian(self):
        """When GBP is at 85th percentile long, the framework goes contrarian SHORT."""
        assert SCENARIO_L["expected_bias"] == "BEARISH"

    def test_scenario_l_raw_score_is_negative(self):
        """COT extreme inverts the score from +50 to -50."""
        assert SCENARIO_L["expected_raw_score"] < 0

    def test_scenario_l_summary_says_contrarian(self):
        assert "CONTRARIAN" in SCENARIO_L["expected_summary_contains"]
