"""
tests/unit/phase0/test_session_guard.py

Unit + behavioral tests for session_guard.py.

Plain English: we are testing the circuit breaker that protects the account.
               Every scenario here represents a real situation a trader will face.
               If these tests pass, the kill switch is trustworthy.
"""

import pytest
from session_guard import (
    get_session_status,
    can_trade,
    STATUS_ACTIVE,
    STATUS_HALTED,
    STATUS_SESSION_CLOSED,
    MAX_DAILY_LOSS_PCT,
    MAX_TRADES_PER_SESSION,
)
from tests.fixtures.journal_samples import write_journal_csv, _base_row
from datetime import date, timedelta


BALANCE = 10_000.0
TODAY   = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


# ── Return structure ───────────────────────────────────────────────────────────

class TestReturnStructure:

    def test_returns_dict_with_required_keys(self, empty_journal):
        result = get_session_status(empty_journal, BALANCE)
        for key in ["status", "reason", "trades_today", "realized_loss_pct", "remaining_capacity"]:
            assert key in result, f"Missing key: {key}"

    def test_reason_is_non_empty_string(self, empty_journal):
        result = get_session_status(empty_journal, BALANCE)
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_status_is_one_of_three_valid_values(self, empty_journal):
        result = get_session_status(empty_journal, BALANCE)
        assert result["status"] in (STATUS_ACTIVE, STATUS_HALTED, STATUS_SESSION_CLOSED)


# ── ACTIVE — no trades or small losses ───────────────────────────────────────

class TestActiveStatus:

    def test_active_when_journal_is_empty(self, empty_journal):
        """No trades today — green light."""
        result = get_session_status(empty_journal, BALANCE)
        assert result["status"]       == STATUS_ACTIVE
        assert result["trades_today"] == 0
        assert result["realized_loss_pct"] == 0.0

    def test_active_when_journal_does_not_exist(self, tmp_path):
        """Missing journal file → treat as no trades → ACTIVE."""
        missing = tmp_path / "nonexistent.csv"
        result  = get_session_status(missing, BALANCE)
        assert result["status"] == STATUS_ACTIVE

    def test_active_with_one_small_loss(self, tmp_path):
        """One trade today at -0.5% — well below the 2.0% limit."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="-0.5", outcome_label="LOSS"
        )])
        result = get_session_status(p, BALANCE)
        assert result["status"]            == STATUS_ACTIVE
        assert result["trades_today"]      == 1
        assert result["realized_loss_pct"] == pytest.approx(0.5)

    def test_active_with_one_win(self, tmp_path):
        """One winning trade today — definitely not halted."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="2.1", outcome_label="WIN"
        )])
        result = get_session_status(p, BALANCE)
        assert result["status"]            == STATUS_ACTIVE
        assert result["realized_loss_pct"] == 0.0   # net gain → 0 loss

    def test_remaining_capacity_decreases_with_loss(self, tmp_path):
        """After a -0.8% loss, remaining capacity should be 1.2%."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="-0.8", outcome_label="LOSS"
        )])
        result = get_session_status(p, BALANCE)
        assert result["remaining_capacity"] == pytest.approx(1.2)

    def test_win_does_not_reduce_remaining_capacity(self, tmp_path):
        """A win should not reduce how much loss room we have."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="1.5", outcome_label="WIN"
        )])
        result = get_session_status(p, BALANCE)
        # Win reduces net loss to 0 — full daily capacity remains
        assert result["remaining_capacity"] == pytest.approx(MAX_DAILY_LOSS_PCT)


# ── HALTED — daily loss limit ─────────────────────────────────────────────────

class TestHaltedStatus:

    def test_halted_when_two_losses_exceed_limit(self, journal_two_losses):
        """Scenario C: -1.1% + -1.2% = -2.3% > 2.0% limit → HALTED."""
        result = get_session_status(journal_two_losses, BALANCE)
        assert result["status"]            == STATUS_HALTED
        assert result["realized_loss_pct"] == pytest.approx(2.3)
        assert result["remaining_capacity"] == 0.0

    def test_halted_reason_mentions_loss_limit(self, journal_two_losses):
        """The reason must explain WHY in plain English."""
        result = get_session_status(journal_two_losses, BALANCE)
        assert "loss" in result["reason"].lower()
        assert "limit" in result["reason"].lower() or "2.0" in result["reason"]

    def test_halted_at_exactly_the_limit(self, tmp_path):
        """At exactly 2.0% loss, trading must stop (inclusive threshold)."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="-2.0", outcome_label="LOSS"
        )])
        result = get_session_status(p, BALANCE)
        assert result["status"] == STATUS_HALTED

    def test_not_halted_just_below_limit(self, tmp_path):
        """At -1.99%, trading is still permitted."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="-1.99", outcome_label="LOSS"
        )])
        result = get_session_status(p, BALANCE)
        assert result["status"] == STATUS_ACTIVE

    def test_win_after_loss_reduces_net_loss(self, tmp_path):
        """
        Loss of -1.5% followed by win of +0.8% → net -0.7% → no loss halt.
        But 2 trades taken hits the trade count limit → SESSION_CLOSED.
        Plain English: the loss limit is safe, but you've used both your
                       daily trades. Session is closed for a different reason.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [
            _base_row(run_id="t1", date=TODAY, trade_taken="YES",
                      pnl_r="-1.5", outcome_label="LOSS"),
            _base_row(run_id="t2", date=TODAY, trade_taken="YES",
                      pnl_r="0.8", outcome_label="WIN"),
        ])
        result = get_session_status(p, BALANCE)
        # 2 trades taken → SESSION_CLOSED (trade count limit hit)
        assert result["status"]            == STATUS_SESSION_CLOSED
        assert result["realized_loss_pct"] == pytest.approx(0.7)   # net loss is correct

    def test_zero_balance_halts_immediately(self, empty_journal):
        """Zero account balance is an instant halt — cannot size a trade."""
        result = get_session_status(empty_journal, 0)
        assert result["status"] == STATUS_HALTED

    def test_negative_balance_halts_immediately(self, empty_journal):
        result = get_session_status(empty_journal, -500)
        assert result["status"] == STATUS_HALTED


# ── SESSION_CLOSED — trade count limit ───────────────────────────────────────

class TestSessionClosedStatus:

    def test_session_closed_after_two_trades(self, journal_two_trades):
        """Two completed trades today → SESSION_CLOSED."""
        result = get_session_status(journal_two_trades, BALANCE)
        assert result["status"]       == STATUS_SESSION_CLOSED
        assert result["trades_today"] == MAX_TRADES_PER_SESSION

    def test_session_closed_reason_mentions_trade_count(self, journal_two_trades):
        result = get_session_status(journal_two_trades, BALANCE)
        assert "trade" in result["reason"].lower()

    def test_not_closed_with_one_trade(self, tmp_path):
        """One trade taken — still one more allowed."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [_base_row(
            date=TODAY, trade_taken="YES", pnl_r="1.0", outcome_label="WIN"
        )])
        result = get_session_status(p, BALANCE)
        assert result["status"] == STATUS_ACTIVE


# ── Priority: HALTED beats SESSION_CLOSED ─────────────────────────────────────

class TestPriority:

    def test_halted_takes_priority_over_session_closed(self, tmp_path):
        """
        If both limits are hit (2 trades + 2.3% loss), HALTED is returned.
        Plain English: the loss limit is more serious than the trade count.
        """
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [
            _base_row(run_id="t1", date=TODAY, trade_taken="YES",
                      pnl_r="-1.2", outcome_label="LOSS"),
            _base_row(run_id="t2", date=TODAY, trade_taken="YES",
                      pnl_r="-1.1", outcome_label="LOSS"),
        ])
        result = get_session_status(p, BALANCE)
        # Two trades (SESSION_CLOSED) AND 2.3% loss (HALTED) — HALTED wins
        assert result["status"] == STATUS_HALTED


# ── Date scoping — yesterday does not count ────────────────────────────────────

class TestDateScoping:

    def test_yesterday_loss_does_not_affect_today(self, journal_yesterday_loss):
        """A large loss yesterday must NOT trigger today's halt."""
        result = get_session_status(journal_yesterday_loss, BALANCE)
        assert result["status"]            == STATUS_ACTIVE
        assert result["trades_today"]      == 0
        assert result["realized_loss_pct"] == 0.0

    def test_only_todays_rows_are_counted(self, tmp_path):
        """Mix of today and yesterday rows — only today counts."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [
            _base_row(run_id="old", date=YESTERDAY, trade_taken="YES",
                      pnl_r="-2.5", outcome_label="LOSS"),
            _base_row(run_id="new", date=TODAY,     trade_taken="YES",
                      pnl_r="-0.3", outcome_label="LOSS"),
        ])
        result = get_session_status(p, BALANCE)
        assert result["status"]            == STATUS_ACTIVE
        assert result["trades_today"]      == 1
        assert result["realized_loss_pct"] == pytest.approx(0.3)


# ── Open trades (no pnl_r yet) ────────────────────────────────────────────────

class TestOpenTrades:

    def test_open_trade_counts_toward_trade_count(self, journal_open_trade):
        """An open trade (pnl_r empty) counts as one trade taken."""
        result = get_session_status(journal_open_trade, BALANCE)
        assert result["trades_today"] == 1

    def test_open_trade_does_not_count_toward_loss(self, journal_open_trade):
        """An open trade has no P&L yet — must not count as a loss."""
        result = get_session_status(journal_open_trade, BALANCE)
        assert result["realized_loss_pct"] == 0.0

    def test_open_trade_does_not_halt_session(self, journal_open_trade):
        """One open trade — session should still be ACTIVE."""
        result = get_session_status(journal_open_trade, BALANCE)
        assert result["status"] == STATUS_ACTIVE


# ── can_trade() boolean API ───────────────────────────────────────────────────

class TestCanTrade:

    def test_can_trade_true_when_active(self, empty_journal):
        assert can_trade(empty_journal, BALANCE) is True

    def test_can_trade_false_when_halted(self, journal_two_losses):
        """Scenario C: session halted → can_trade must return False."""
        assert can_trade(journal_two_losses, BALANCE) is False

    def test_can_trade_false_when_session_closed(self, journal_two_trades):
        assert can_trade(journal_two_trades, BALANCE) is False

    def test_can_trade_returns_bool_not_truthy(self, empty_journal):
        """must be exactly True/False, not just truthy."""
        result = can_trade(empty_journal, BALANCE)
        assert result is True

    def test_can_trade_false_when_journal_missing_but_balance_zero(self, tmp_path):
        missing = tmp_path / "no_journal.csv"
        assert can_trade(missing, 0) is False


# ── Behavioral: Scenario C ────────────────────────────────────────────────────

class TestScenarioC:
    """
    Scenario C — Two losses today totaling -2.3% exceed the 2% daily limit.
    A new A+ setup appears. The kill switch must block it.

    Plain English: you had a bad morning. Two trades, both losses.
                   You're down 2.3% on the day. Even though the next setup
                   looks perfect, the machine says NO. Come back tomorrow.
    """

    def test_scenario_c_session_is_halted(self, journal_two_losses):
        result = get_session_status(journal_two_losses, BALANCE)
        assert result["status"] == STATUS_HALTED, (
            f"Expected HALTED but got {result['status']}. Reason: {result['reason']}"
        )

    def test_scenario_c_loss_is_above_limit(self, journal_two_losses):
        result = get_session_status(journal_two_losses, BALANCE)
        assert result["realized_loss_pct"] > MAX_DAILY_LOSS_PCT

    def test_scenario_c_can_trade_returns_false(self, journal_two_losses):
        assert can_trade(journal_two_losses, BALANCE) is False

    def test_scenario_c_remaining_capacity_is_zero(self, journal_two_losses):
        result = get_session_status(journal_two_losses, BALANCE)
        assert result["remaining_capacity"] == 0.0

    def test_scenario_c_reason_is_human_readable(self, journal_two_losses):
        """The reason must be something a trader can understand at a glance."""
        result = get_session_status(journal_two_losses, BALANCE)
        reason = result["reason"]
        # Must mention the actual loss percentage
        assert "2." in reason, "Reason should include the loss percentage"
        # Must not be cryptic
        assert len(reason) > 20, "Reason is too short to be meaningful"
