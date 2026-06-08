"""
tests/unit/phase1/test_auto_label.py

Unit + behavioral tests for auto_label.py.

Plain English: these tests verify that the framework correctly grades its
               own past calls as WIN / LOSS / NEUTRAL by comparing the
               direction it predicted to where price actually closed.
               No OANDA calls are made — we inject the close price directly.
"""

import pytest
from auto_label import compute_label, label_journal, WIN_THRESHOLD_PIPS
from tests.fixtures.journal_samples import (
    write_journal_csv,
    read_journal_csv,
    rows_unlabeled_bearish,
    rows_unlabeled_bullish,
    rows_already_labeled,
    rows_yesterday_loss_only,
    _base_row,
    YESTERDAY,
    TODAY,
    TWO_DAYS_AGO,
)
from tests.fixtures.market_scenarios import SCENARIO_J, SCENARIO_K


# ── compute_label() return structure ─────────────────────────────────────────

class TestComputeLabelStructure:

    def test_returns_dict(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        for key in ["outcome_label", "framework_was_right", "pips_with_bias"]:
            assert key in result, f"Missing key: {key}"

    def test_outcome_label_is_valid_string(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert result["outcome_label"] in ("WIN", "LOSS", "NEUTRAL", "")

    def test_framework_was_right_is_yes_or_no_or_empty(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert result["framework_was_right"] in ("YES", "NO", "")

    def test_pips_with_bias_is_numeric(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert isinstance(result["pips_with_bias"], (int, float))


# ── WIN / LOSS / NEUTRAL logic ────────────────────────────────────────────────

class TestComputeLabelOutcomes:

    def test_bearish_big_drop_is_win(self):
        """
        BEARISH bias, price dropped 222 pips → WIN.
        Plain English: the framework called DOWN and price went DOWN a lot.
        """
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert result["outcome_label"] == "WIN"

    def test_bullish_big_rise_is_win(self):
        """BULLISH bias, price rose 222 pips → WIN."""
        result = compute_label(2.0300, "BULLISH", 2.0522)
        assert result["outcome_label"] == "WIN"

    def test_bullish_small_rise_is_neutral(self):
        """
        BULLISH bias, price rose only 15 pips (< 20 threshold) → NEUTRAL.
        Plain English: technically moved the right way but not enough to count.
        """
        result = compute_label(2.0300, "BULLISH", 2.0315)
        assert result["outcome_label"] == "NEUTRAL"

    def test_bearish_price_rises_is_loss(self):
        """
        BEARISH bias, price rose 100 pips → LOSS.
        Plain English: the framework called DOWN but price went UP hard.
        """
        result = compute_label(2.0300, "BEARISH", 2.0400)
        assert result["outcome_label"] == "LOSS"

    def test_exactly_at_threshold_is_win(self):
        """
        At exactly 20 pips with bias → WIN (threshold is inclusive).
        BULLISH at 2.0300, close at 2.0320 → 20 pips up → WIN.
        """
        result = compute_label(2.0300, "BULLISH", 2.0320)
        assert result["outcome_label"] == "WIN"

    def test_one_pip_below_threshold_is_neutral(self):
        """19 pips with bias → NEUTRAL (just below the 20-pip floor)."""
        result = compute_label(2.0300, "BULLISH", 2.0319)
        assert result["outcome_label"] == "NEUTRAL"

    def test_exactly_at_loss_threshold_is_loss(self):
        """BEARISH bias, price rises exactly 20 pips → LOSS."""
        result = compute_label(2.0300, "BEARISH", 2.0320)
        assert result["outcome_label"] == "LOSS"

    def test_neutral_bias_returns_empty(self):
        """
        NEUTRAL or NO TRADE bias → cannot be graded — empty result.
        Plain English: there was no directional call, so there is nothing to score.
        """
        for bias in ["NEUTRAL", "NO TRADE", "", "WAIT"]:
            result = compute_label(2.0300, bias, 2.0500)
            assert result["outcome_label"] == "", f"Expected empty for bias='{bias}'"
            assert result["framework_was_right"] == ""


# ── framework_was_right logic ─────────────────────────────────────────────────

class TestFrameworkWasRight:

    def test_win_sets_was_right_yes(self):
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert result["framework_was_right"] == "YES"

    def test_loss_sets_was_right_no(self):
        result = compute_label(2.0300, "BEARISH", 2.0500)
        assert result["framework_was_right"] == "NO"

    def test_neutral_sets_was_right_no(self):
        """
        NEUTRAL means the framework's call was inconclusive — marked as NO.
        Plain English: if the market didn't move, the call wasn't validated.
        """
        result = compute_label(2.0300, "BULLISH", 2.0315)
        assert result["framework_was_right"] == "NO"


# ── pips_with_bias calculation ────────────────────────────────────────────────

class TestPipsWithBias:

    def test_bearish_pips_calculated_correctly(self):
        """BEARISH at 2.0300, close at 2.0078 → (2.0300-2.0078)*10000 = 222 pips."""
        result = compute_label(2.0300, "BEARISH", 2.0078)
        assert result["pips_with_bias"] == pytest.approx(222.0, abs=0.5)

    def test_bullish_pips_calculated_correctly(self):
        """BULLISH at 2.0300, close at 2.0315 → (2.0315-2.0300)*10000 = 15 pips."""
        result = compute_label(2.0300, "BULLISH", 2.0315)
        assert result["pips_with_bias"] == pytest.approx(15.0, abs=0.5)

    def test_loss_pips_are_negative(self):
        """Price moved against bias → pips_with_bias is negative."""
        result = compute_label(2.0300, "BEARISH", 2.0500)
        assert result["pips_with_bias"] < 0

    def test_case_insensitive_bias(self):
        """Bias matching must not care about case."""
        lower = compute_label(2.0300, "bearish", 2.0078)
        upper = compute_label(2.0300, "BEARISH", 2.0078)
        assert lower["outcome_label"] == upper["outcome_label"]


# ── label_journal() return structure ─────────────────────────────────────────

class TestLabelJournalStructure:

    def test_returns_dict(self, tmp_path):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        result = label_journal(p, fetch_fn=lambda d: 2.0078)
        assert isinstance(result, dict)

    def test_has_required_keys(self, tmp_path):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        result = label_journal(p, fetch_fn=lambda d: 2.0078)
        for key in ["labeled", "skipped", "errors"]:
            assert key in result, f"Missing key: {key}"

    def test_missing_journal_returns_zeros(self, tmp_path):
        missing = tmp_path / "no_file.csv"
        result = label_journal(missing, fetch_fn=lambda d: 2.0078)
        assert result == {"labeled": 0, "skipped": 0, "errors": 0}

    def test_empty_journal_returns_zeros(self, tmp_path):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        result = label_journal(p, fetch_fn=lambda d: 2.0078)
        assert result["labeled"] == 0


# ── label_journal() labeling behavior ────────────────────────────────────────

class TestLabelJournalBehavior:

    def test_unlabeled_yesterday_row_gets_labeled(self, tmp_path):
        """
        An unlabeled BEARISH row from yesterday gets WIN with close 2.0078.
        Plain English: yesterday's call is now scoreable — label it.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bearish())

        label_journal(p, fetch_fn=lambda d: 2.0078)

        rows = read_journal_csv(p)
        assert rows[0]["outcome_label"] == "WIN"

    def test_labeled_row_is_not_modified(self, tmp_path):
        """
        A row that already has an outcome_label must not be overwritten.
        Plain English: don't re-grade what's already been graded.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_already_labeled())

        label_journal(p, fetch_fn=lambda d: 9.9999)  # wild price — should not touch labeled rows

        rows = read_journal_csv(p)
        labeled_rows = [r for r in rows if r["outcome_label"] in ("WIN", "LOSS", "NEUTRAL")]
        assert labeled_rows[0]["outcome_label"] == "WIN"
        assert labeled_rows[1]["outcome_label"] == "LOSS"

    def test_todays_row_is_skipped(self, tmp_path):
        """
        Today's run is too fresh — 24h window hasn't closed. Must be skipped.
        Plain English: we can't grade a call that's still playing out.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, bias="BEARISH", price="2.0300", outcome_label="",
        )])

        result = label_journal(p, fetch_fn=lambda d: 2.0078)

        assert result["labeled"] == 0
        assert result["skipped"] >= 1
        rows = read_journal_csv(p)
        assert rows[0]["outcome_label"] == ""

    def test_only_unlabeled_old_rows_are_counted(self, tmp_path):
        """
        Mix: 2 already-labeled + 1 unlabeled yesterday → labeled=1, skipped=2.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_already_labeled())

        result = label_journal(p, fetch_fn=lambda d: 2.0078)

        assert result["labeled"] == 1
        assert result["skipped"] == 2

    def test_next_day_close_written_to_row(self, tmp_path):
        """The close price used for labeling must be written to next_day_close."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bearish())

        label_journal(p, fetch_fn=lambda d: 2.0078)

        rows = read_journal_csv(p)
        assert rows[0]["next_day_close"] == "2.0078"

    def test_fetch_fn_none_records_error(self, tmp_path):
        """If fetch_fn returns None (OANDA down), row is an error — not labeled."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bearish())

        result = label_journal(p, fetch_fn=lambda d: None)

        assert result["labeled"] == 0
        assert result["errors"] == 1
        rows = read_journal_csv(p)
        assert rows[0]["outcome_label"] == ""

    def test_framework_was_right_written_to_row(self, tmp_path):
        """framework_was_right must be written alongside outcome_label."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bearish())  # BEARISH, price=2.0300

        label_journal(p, fetch_fn=lambda d: 2.0078)  # big drop → WIN

        rows = read_journal_csv(p)
        assert rows[0]["framework_was_right"] == "YES"

    def test_neutral_bias_row_is_skipped(self, tmp_path):
        """A row with bias=NEUTRAL has no directional call — skip it."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=YESTERDAY, bias="NEUTRAL", price="2.0300", outcome_label="",
        )])

        result = label_journal(p, fetch_fn=lambda d: 2.0500)

        assert result["labeled"] == 0
        assert result["skipped"] >= 1


# ── Behavioral: Scenario J — BEARISH WIN ─────────────────────────────────────

class TestScenarioJ:
    """
    Scenario J — BEARISH bias at 2.0300, 24h close at 2.0078.
    Price fell 222 pips in the direction of the bias → WIN.

    Plain English: the framework called DOWN, and price dropped hard.
                   222 pips is way above the 20-pip threshold → clear WIN.
                   framework_was_right = YES.
    """

    def _run(self):
        return compute_label(
            run_price=SCENARIO_J["run_price"],
            bias=SCENARIO_J["run_bias"],
            close_price=SCENARIO_J["close_24h"],
            win_threshold_pips=SCENARIO_J["win_threshold_pips"],
        )

    def test_outcome_is_win(self):
        result = self._run()
        assert result["outcome_label"] == SCENARIO_J["expected_label"]

    def test_framework_was_right_is_yes(self):
        result = self._run()
        assert result["framework_was_right"] == SCENARIO_J["expected_framework_was_right"]

    def test_pips_with_bias_is_222(self):
        result = self._run()
        assert result["pips_with_bias"] == pytest.approx(SCENARIO_J["pips_moved"], abs=1.0)

    def test_pips_well_above_threshold(self):
        """222 pips >> 20-pip threshold — not a borderline call."""
        result = self._run()
        assert result["pips_with_bias"] > WIN_THRESHOLD_PIPS * 5

    def test_journal_write_through(self, tmp_path):
        """End-to-end: write BEARISH row, inject Scenario J close, verify WIN in CSV."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bearish())

        label_journal(p, fetch_fn=lambda d: SCENARIO_J["close_24h"])

        rows = read_journal_csv(p)
        assert rows[0]["outcome_label"]       == "WIN"
        assert rows[0]["framework_was_right"] == "YES"


# ── Behavioral: Scenario K — BULLISH NEUTRAL ─────────────────────────────────

class TestScenarioK:
    """
    Scenario K — BULLISH bias at 2.0300, 24h close at 2.0315.
    Price rose only 15 pips — below the 20-pip WIN threshold → NEUTRAL.

    Plain English: the framework called UP and price did go up a little.
                   But 15 pips is not enough to count as a confirmed move.
                   The framework's call is graded as inconclusive → NEUTRAL.
                   framework_was_right = NO.
    """

    def _run(self):
        return compute_label(
            run_price=SCENARIO_K["run_price"],
            bias=SCENARIO_K["run_bias"],
            close_price=SCENARIO_K["close_24h"],
            win_threshold_pips=SCENARIO_K["win_threshold_pips"],
        )

    def test_outcome_is_neutral(self):
        result = self._run()
        assert result["outcome_label"] == SCENARIO_K["expected_label"]

    def test_framework_was_right_is_no(self):
        result = self._run()
        assert result["framework_was_right"] == SCENARIO_K["expected_framework_was_right"]

    def test_pips_with_bias_is_15(self):
        result = self._run()
        assert result["pips_with_bias"] == pytest.approx(SCENARIO_K["pips_moved"], abs=1.0)

    def test_pips_below_threshold(self):
        """15 pips < 20-pip WIN threshold — correctly NEUTRAL."""
        result = self._run()
        assert result["pips_with_bias"] < WIN_THRESHOLD_PIPS

    def test_pips_still_positive(self):
        """Price did move the right way — just not enough. Pips should be positive."""
        result = self._run()
        assert result["pips_with_bias"] > 0

    def test_journal_write_through(self, tmp_path):
        """End-to-end: write BULLISH row, inject Scenario K close, verify NEUTRAL in CSV."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_unlabeled_bullish())

        label_journal(p, fetch_fn=lambda d: SCENARIO_K["close_24h"])

        rows = read_journal_csv(p)
        assert rows[0]["outcome_label"]       == "NEUTRAL"
        assert rows[0]["framework_was_right"] == "NO"
