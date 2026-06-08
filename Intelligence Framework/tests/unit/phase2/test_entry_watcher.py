"""
tests/unit/phase2/test_entry_watcher.py

Unit + behavioral tests for entry_watcher.check_trigger_conditions().

Plain English: these tests prove that the entry gate checklist correctly
               blocks entries under every condition where trading is unsafe
               or not ready — and allows entries when all conditions are met.
               No OANDA calls are made. No candles are fetched.
"""

import pytest
from datetime import datetime, timezone, timedelta
from entry_watcher import check_trigger_conditions
from risk_config import HARD_LIMITS, RISK_RULES
from tests.fixtures.journal_samples import (
    write_journal_csv,
    rows_two_losses_today,
    rows_unlabeled_bearish,
    YESTERDAY,
    TODAY,
)
from tests.fixtures.market_scenarios import SCENARIO_B, SCENARIO_D, SCENARIO_E, SCENARIO_G

BALANCE = 10_000.0


# ── Context builder helpers ───────────────────────────────────────────────────

def _ctx(age_hours: float = 0.5, grade: str = "A", **extra) -> dict:
    """
    Build a minimal valid context dict with a timestamp `age_hours` old.
    All conditions pass by default — override as needed.
    """
    run_dt = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    ctx = {
        "date":          run_dt.strftime("%Y-%m-%d"),
        "time_utc":      run_dt.strftime("%H:%M"),
        "bias":          "BEARISH",
        "grade":         grade,
        "upcoming_news": [],
        "intraday":      {"fakeout_type": "BEARISH_FAKEOUT"},
    }
    ctx.update(extra)
    return ctx


def _ctx_with_news(age_hours: float = 0.5, minutes_to_event: int = 90) -> dict:
    """Context with a high-impact news event `minutes_to_event` minutes away."""
    return _ctx(age_hours=age_hours, upcoming_news=[{
        "event":    "BoE Rate Decision",
        "currency": "GBP",
        "impact":   "High",
        "minutes":  minutes_to_event,
        "time":     "12:00",
    }])


def _ctx_both_swept(age_hours: float = 0.5) -> dict:
    """Context where Asian range was swept in both directions."""
    return _ctx(age_hours=age_hours, intraday={
        "fakeout_type":  "BOTH_SWEPT",
        "intraday_bias": "WAIT",
    })


# ── Return structure ──────────────────────────────────────────────────────────

class TestReturnStructure:

    def test_returns_dict(self):
        result = check_trigger_conditions(_ctx())
        assert isinstance(result, dict)

    def test_has_required_top_level_keys(self):
        result = check_trigger_conditions(_ctx())
        for key in ["can_trigger", "conditions", "first_failure"]:
            assert key in result, f"Missing top-level key: {key}"

    def test_can_trigger_is_bool(self):
        result = check_trigger_conditions(_ctx())
        assert isinstance(result["can_trigger"], bool)

    def test_conditions_has_all_gates(self):
        result = check_trigger_conditions(_ctx())
        expected = [
            "context_not_stale",
            "session_valid",
            "news_clear",
            "pattern_clean",
            "grade_tradeable",
        ]
        for gate in expected:
            assert gate in result["conditions"], f"Missing gate: {gate}"

    def test_each_condition_has_passed_and_reason(self):
        result = check_trigger_conditions(_ctx())
        for name, cond in result["conditions"].items():
            assert "passed" in cond,  f"Condition '{name}' missing 'passed'"
            assert "reason" in cond,  f"Condition '{name}' missing 'reason'"
            assert isinstance(cond["passed"], bool)
            assert isinstance(cond["reason"], str) and len(cond["reason"]) > 0

    def test_first_failure_is_string(self):
        result = check_trigger_conditions(_ctx())
        assert isinstance(result["first_failure"], str)


# ── All-pass baseline ─────────────────────────────────────────────────────────

class TestAllPass:

    def test_clean_context_can_trigger(self):
        """Fresh context, no news, clean pattern, good grade → can_trigger=True."""
        result = check_trigger_conditions(_ctx())
        assert result["can_trigger"] is True

    def test_first_failure_empty_when_all_pass(self):
        result = check_trigger_conditions(_ctx())
        assert result["first_failure"] == ""

    def test_all_conditions_passed(self):
        result = check_trigger_conditions(_ctx())
        for name, cond in result["conditions"].items():
            assert cond["passed"] is True, f"Expected {name} to pass but it failed: {cond['reason']}"


# ── Context age gate ──────────────────────────────────────────────────────────

class TestContextAge:

    def test_fresh_30min_context_passes(self):
        result = check_trigger_conditions(_ctx(age_hours=0.5))
        assert result["conditions"]["context_not_stale"]["passed"] is True

    def test_stale_context_fails(self):
        """Context older than HARD_LIMITS expiry must fail the gate."""
        expiry = HARD_LIMITS["context_expiry_hours"]
        result = check_trigger_conditions(_ctx(age_hours=expiry + 1))
        assert result["conditions"]["context_not_stale"]["passed"] is False

    def test_stale_context_blocks_trigger(self):
        expiry = HARD_LIMITS["context_expiry_hours"]
        result = check_trigger_conditions(_ctx(age_hours=expiry + 1))
        assert result["can_trigger"] is False

    def test_stale_reason_mentions_hours(self):
        expiry = HARD_LIMITS["context_expiry_hours"]
        result = check_trigger_conditions(_ctx(age_hours=expiry + 1))
        reason = result["conditions"]["context_not_stale"]["reason"]
        assert "h" in reason.lower() or "hour" in reason.lower()

    def test_just_under_expiry_passes(self):
        """
        A context 6 minutes under the expiry limit must pass.
        Plain English: if the limit is 4 hours, a 3h54m-old context is still valid.
        Note: we do not test exactly-at-the-limit because wall-clock timing
              makes that test flaky — microseconds pass between creation and check.
        """
        expiry = HARD_LIMITS["context_expiry_hours"]
        result = check_trigger_conditions(_ctx(age_hours=expiry - 0.1))  # 6 min under
        assert result["conditions"]["context_not_stale"]["passed"] is True

    def test_missing_timestamps_treated_as_stale(self):
        """Context with no date/time fields → treated as ancient → fails."""
        result = check_trigger_conditions({"grade": "A", "upcoming_news": []})
        assert result["conditions"]["context_not_stale"]["passed"] is False


# ── Session guard gate ────────────────────────────────────────────────────────

class TestSessionGuard:

    def test_active_session_passes(self, tmp_path):
        """Empty journal → ACTIVE session → session_valid passes."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        result = check_trigger_conditions(_ctx(), journal_path=p, account_balance=BALANCE)
        assert result["conditions"]["session_valid"]["passed"] is True

    def test_halted_session_fails(self, tmp_path):
        """Two losses today → HALTED → session_valid fails."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_two_losses_today())
        result = check_trigger_conditions(_ctx(), journal_path=p, account_balance=BALANCE)
        assert result["conditions"]["session_valid"]["passed"] is False

    def test_halted_session_blocks_trigger(self, tmp_path):
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows_two_losses_today())
        result = check_trigger_conditions(_ctx(), journal_path=p, account_balance=BALANCE)
        assert result["can_trigger"] is False

    def test_no_journal_skips_session_guard(self):
        """Without a journal path, session guard is skipped — gate passes."""
        result = check_trigger_conditions(_ctx(), journal_path=None)
        assert result["conditions"]["session_valid"]["passed"] is True


# ── Behavioral: Scenario B — News block ───────────────────────────────────────

class TestScenarioB:
    """
    Scenario B — BoE Rate Decision 90 minutes away.
    Risk config lockout is 2 hours (120 minutes).
    90 minutes is inside the lockout window → hard block.

    Plain English: the framework runs at 10:30 UTC. The BoE rate decision
                   fires at 12:00 UTC (90 minutes away). GBP/AUD will move
                   violently at the news — entering 90 minutes before is
                   gambling, not trading. The gate blocks it.
    """

    def _result(self):
        ctx = _ctx_with_news(minutes_to_event=90)
        return check_trigger_conditions(ctx)

    def test_news_clear_fails(self):
        result = self._result()
        assert result["conditions"]["news_clear"]["passed"] is False

    def test_can_trigger_is_false(self):
        result = self._result()
        assert result["can_trigger"] is False

    def test_first_failure_is_news_clear(self):
        result = self._result()
        assert result["first_failure"] == "news_clear"

    def test_reason_mentions_event_name(self):
        result = self._result()
        reason = result["conditions"]["news_clear"]["reason"]
        assert "BoE" in reason or "Rate" in reason or "GBP" in reason

    def test_event_outside_lockout_does_not_block(self):
        """
        Event 150 minutes away is outside the 120-minute lockout → no block.
        Plain English: enough time has passed — the setup can still be taken.
        """
        ctx    = _ctx_with_news(minutes_to_event=150)
        result = check_trigger_conditions(ctx)
        assert result["conditions"]["news_clear"]["passed"] is True

    def test_lockout_window_matches_risk_config(self):
        """The news lockout window must use RISK_RULES event_lockout_hours_before."""
        lockout_mins = int(RISK_RULES["event_lockout_hours_before"] * 60)
        # Event just inside the window → blocked
        ctx_in  = _ctx_with_news(minutes_to_event=lockout_mins - 1)
        ctx_out = _ctx_with_news(minutes_to_event=lockout_mins + 1)
        assert check_trigger_conditions(ctx_in)["conditions"]["news_clear"]["passed"] is False
        assert check_trigger_conditions(ctx_out)["conditions"]["news_clear"]["passed"] is True


# ── Behavioral: Scenario D — Stale context ────────────────────────────────────

class TestScenarioD:
    """
    Scenario D — Framework ran 5.75 hours ago. Expiry is 4 hours.
    Context is stale → watcher must refuse.

    Plain English: the market context from 5 hours ago is no longer valid.
                   Price levels, news, regime — all could have changed.
                   Running the framework first is mandatory before the
                   watcher can fire any alert.
    """

    def _result(self):
        age    = SCENARIO_D["context_age_hours"]   # 5.75
        return check_trigger_conditions(_ctx(age_hours=age))

    def test_context_not_stale_fails(self):
        result = self._result()
        assert result["conditions"]["context_not_stale"]["passed"] is False

    def test_can_trigger_is_false(self):
        result = self._result()
        assert result["can_trigger"] is False

    def test_first_failure_is_context_not_stale(self):
        result = self._result()
        assert result["first_failure"] == "context_not_stale"

    def test_expiry_matches_hard_limits(self):
        """The context expiry must use HARD_LIMITS['context_expiry_hours'] = 4.0."""
        assert HARD_LIMITS["context_expiry_hours"] == SCENARIO_D["context_expiry_hours"]

    def test_fresh_context_passes_same_gate(self):
        """30-minute-old context → passes the same gate that Scenario D fails."""
        result = check_trigger_conditions(_ctx(age_hours=0.5))
        assert result["conditions"]["context_not_stale"]["passed"] is True


# ── Behavioral: Scenario E — BOTH_SWEPT chaos ────────────────────────────────

class TestScenarioE:
    """
    Scenario E — Asian high AND low both swept before London open.
    When both extremes are taken, there is no clean directional signal.
    Hard block — no trade.

    Plain English: the Asian session usually establishes a range. London
                   opens and sweeps one side → that's a fakeout signal.
                   But if BOTH sides get swept, price is just hunting
                   liquidity in all directions. No edge. Stand aside.
    """

    def _result(self):
        return check_trigger_conditions(_ctx_both_swept())

    def test_pattern_clean_fails(self):
        result = self._result()
        assert result["conditions"]["pattern_clean"]["passed"] is False

    def test_can_trigger_is_false(self):
        result = self._result()
        assert result["can_trigger"] is False

    def test_first_failure_is_pattern_clean(self):
        result = self._result()
        assert result["first_failure"] == "pattern_clean"

    def test_reason_mentions_both_swept(self):
        result = self._result()
        reason = result["conditions"]["pattern_clean"]["reason"]
        assert "BOTH" in reason.upper() or "both" in reason.lower()

    def test_clean_fakeout_passes(self):
        """
        A BEARISH_FAKEOUT (only one side swept) must pass the pattern gate.
        Plain English: London swept the Asian high and reversed → clean SHORT signal.
        """
        ctx    = _ctx(intraday={"fakeout_type": "BEARISH_FAKEOUT"})
        result = check_trigger_conditions(ctx)
        assert result["conditions"]["pattern_clean"]["passed"] is True

    def test_no_intraday_key_passes(self):
        """Missing intraday key → no BOTH_SWEPT → gate passes."""
        ctx    = _ctx()
        del ctx["intraday"]
        result = check_trigger_conditions(ctx)
        assert result["conditions"]["pattern_clean"]["passed"] is True


# ── Grade gate ────────────────────────────────────────────────────────────────

class TestGradeGate:

    def test_grade_A_plus_passes(self):
        result = check_trigger_conditions(_ctx(grade="A+"))
        assert result["conditions"]["grade_tradeable"]["passed"] is True

    def test_grade_A_passes(self):
        result = check_trigger_conditions(_ctx(grade="A"))
        assert result["conditions"]["grade_tradeable"]["passed"] is True

    def test_grade_B_passes(self):
        result = check_trigger_conditions(_ctx(grade="B"))
        assert result["conditions"]["grade_tradeable"]["passed"] is True

    def test_grade_C_fails(self):
        """C grade is NO TRADE — gate must fail."""
        result = check_trigger_conditions(_ctx(grade="C"))
        assert result["conditions"]["grade_tradeable"]["passed"] is False

    def test_grade_C_blocks_trigger(self):
        result = check_trigger_conditions(_ctx(grade="C"))
        assert result["can_trigger"] is False

    def test_missing_grade_fails(self):
        """No grade in context → defaults to C → gate fails."""
        ctx = _ctx()
        del ctx["grade"]
        result = check_trigger_conditions(ctx)
        assert result["conditions"]["grade_tradeable"]["passed"] is False


# ── Multiple failures — first_failure ordering ────────────────────────────────

class TestFirstFailureOrdering:

    def test_context_stale_is_checked_first(self):
        """
        Stale context + news block: context_not_stale should be first_failure.
        Plain English: if the context is expired, we don't even need to check
                       news — the data is too old to act on.
        """
        ctx = _ctx_with_news(age_hours=10.0, minutes_to_event=30)
        result = check_trigger_conditions(ctx)
        assert result["first_failure"] == "context_not_stale"

    def test_all_failing_still_returns_first_only(self):
        """Multiple failures → first_failure is the first one hit."""
        ctx = _ctx_both_swept(age_hours=10.0)
        ctx["grade"] = "C"
        result = check_trigger_conditions(ctx)
        # context_not_stale fails first (checked first in the function)
        assert result["first_failure"] == "context_not_stale"
        assert result["can_trigger"] is False
