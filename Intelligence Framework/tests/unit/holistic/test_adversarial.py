"""
tests/unit/holistic/test_adversarial.py

Adversarial holistic tests — real-world stress scenarios designed to break
the framework and expose hidden gaps across all modules.

Every test here represents a condition that could lead to a wrong trading
decision or system failure if the code doesn't handle it correctly.

Severity labels in class docstrings:
  P0 — Critical: dangerous outcome (trade fires when it absolutely should not,
                 or system crashes before a trade decision is made)
  P1 — Logic gap: incorrect calculation that would mislead the trader
  P2 — Defensive: silent data corruption or unexpected edge-case behavior

Run this suite independently:
    pytest tests/unit/holistic/ -v

Or as part of the full suite:
    pytest --tb=short -q
"""

import json
import pytest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from risk_config import get_grade, calculate_lot_size, HARD_LIMITS
from entry_watcher import check_trigger_conditions, _context_age_hours
from auto_label import compute_label, label_journal
from session_guard import get_session_status, STATUS_ACTIVE, STATUS_HALTED, STATUS_SESSION_CLOSED
from tests.fixtures.journal_samples import _base_row, write_journal_csv, TODAY


YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW  = (date.today() + timedelta(days=1)).isoformat()


def _fresh_ctx(**overrides) -> dict:
    """Return a context dict with a timestamp from right now — passes freshness gate."""
    now = datetime.now(timezone.utc)
    ctx = {
        "date":          now.strftime("%Y-%m-%d"),
        "time_utc":      now.strftime("%H:%M"),
        "grade":         "A",
        "intraday":      {},
        "upcoming_news": [],
    }
    ctx.update(overrides)
    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# P0 CRITICAL — System crashes or dangerous trade fires without authorization
# ═══════════════════════════════════════════════════════════════════════════════

class TestP0_SwingGradeCrash:
    """
    P0: get_grade() raises UnboundLocalError when trade_type='swing' with
    structural_score < 60 and alignment > 55.

    Root cause: the swing-cap block references `reasons` (line ~139) before
    `reasons = []` is initialized (line ~157). Python detects the later
    assignment and treats the entire function as having `reasons` as a local
    — so the early reference raises UnboundLocalError.

    Impact: any caller that passes trade_type='swing' on a strong-looking
    setup (alignment > 55) crashes before returning a grade.
    """

    def test_swing_grade_cap_does_not_crash(self):
        """Swing cap path must not raise — returns a valid grade."""
        grade, risk, label, reason = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session",
            trade_type="swing", structural_score=50,
        )
        assert grade in ("A+", "A", "B+", "B", "C")

    def test_swing_grade_cap_downgrades_to_B_plus(self):
        """
        alignment=75 with swing cap → capped at 55 → B+.
        London bonus adds 5 → adjusted=60, still below A threshold of 70.
        """
        grade, risk, label, reason = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session",
            trade_type="swing", structural_score=50,
        )
        assert grade == "B+"

    def test_swing_cap_not_triggered_when_structural_score_meets_threshold(self):
        """structural_score=65 (≥60) — swing cap block is skipped entirely."""
        grade, risk, label, reason = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session",
            trade_type="swing", structural_score=65,
        )
        assert grade in ("A", "A+")

    def test_swing_cap_not_triggered_when_alignment_at_or_below_55(self):
        """alignment=55 — condition is alignment > 55, so no cap fires."""
        grade, risk, label, reason = get_grade(
            alignment=55, quality="MEDIUM",
            is_counter_trend=False, event_risk=False,
            session="London Session",
            trade_type="swing", structural_score=40,
        )
        assert grade in ("B+", "B", "C")

    def test_standard_trade_type_unaffected_by_structural_score(self):
        """trade_type='auto' (default) never enters the swing cap code path."""
        grade, risk, label, reason = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session",
            trade_type="auto", structural_score=50,
        )
        assert grade in ("A", "A+")


class TestP0_BothSweptMasksGradeGate:
    """
    P0: When BOTH_SWEPT (pattern_clean=False) and Grade C (grade_tradeable=False)
    fail simultaneously, the watch() loop does NOT block the trade.

    Root cause: watch() blocks only when:
        not can_trigger AND first_failure not in ("pattern_clean", "")

    When both gates fail, first_failure is 'pattern_clean' (insertion order).
    The exclusion check passes → loop continues → Grade C alert fires.

    This means a chaotic Asian range (BOTH_SWEPT) combined with terrible
    conditions (Grade C) is the one scenario where the gate is bypassed.

    Fix: check_trigger_conditions must expose a 'first_blocking_failure' key
    (the first non-pattern-clean failure) so watch() can block correctly.
    """

    def _ctx(self, **overrides) -> dict:
        ctx = _fresh_ctx(grade="C", intraday={"fakeout_type": "BOTH_SWEPT"})
        ctx.update(overrides)
        return ctx

    def test_can_trigger_is_false(self):
        """Both gates fail → can_trigger must be False."""
        gate = check_trigger_conditions(self._ctx())
        assert gate["can_trigger"] is False

    def test_grade_tradeable_gate_fails(self):
        """Grade C explicitly fails the grade_tradeable gate."""
        gate = check_trigger_conditions(self._ctx())
        assert gate["conditions"]["grade_tradeable"]["passed"] is False

    def test_pattern_clean_gate_fails(self):
        """BOTH_SWEPT explicitly fails the pattern_clean gate."""
        gate = check_trigger_conditions(self._ctx())
        assert gate["conditions"]["pattern_clean"]["passed"] is False

    def test_pattern_clean_is_first_failure_revealing_the_masking_bug(self):
        """
        pattern_clean is listed before grade_tradeable in conditions dict.
        With insertion-order iteration, first_failure='pattern_clean'.
        The watch() exclusion check then lets the Grade C trade through.
        This test documents the exact mechanism of the bug.
        """
        gate = check_trigger_conditions(self._ctx())
        assert gate["first_failure"] == "pattern_clean"

    def test_first_blocking_failure_key_exists(self):
        """
        check_trigger_conditions must return 'first_blocking_failure' —
        the first gate that fails EXCLUDING pattern_clean.
        watch() uses this for the block decision.
        """
        gate = check_trigger_conditions(self._ctx())
        assert "first_blocking_failure" in gate, (
            "Missing 'first_blocking_failure'. Without it, watch() cannot correctly "
            "block when BOTH_SWEPT coexists with other gate failures (e.g. Grade C)."
        )

    def test_first_blocking_failure_is_grade_tradeable(self):
        """With fresh context, clear news, and no session issues, grade is the blocking gate."""
        gate = check_trigger_conditions(self._ctx())
        assert gate["first_blocking_failure"] == "grade_tradeable"

    def test_both_swept_alone_does_not_produce_blocking_failure(self):
        """
        BOTH_SWEPT only (Grade A, everything else passes) →
        first_blocking_failure is empty — pattern_clean is excluded by design.
        """
        gate = check_trigger_conditions(_fresh_ctx(grade="A", intraday={"fakeout_type": "BOTH_SWEPT"}))
        assert gate["first_blocking_failure"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# P1 LOGIC GAPS — Wrong calculations that mislead the trader
# ═══════════════════════════════════════════════════════════════════════════════

class TestP1_FutureTimestampPassesFreshnessGate:
    """
    P1: A context dict with a future date/time produces negative age.
    Negative age satisfies age <= expiry (e.g., -24 <= 4 → True).
    A context from "tomorrow" is treated as the freshest possible context.

    Cause: _context_age_hours() computes delta without guarding for negative.
    Fix: if delta.total_seconds() < 0, return 999.0 (treat as unknown/stale).

    Real scenario: user manually edits last_run.json, DST confusion,
    or NTP clock sync that jumps forward temporarily.
    """

    def _future_ctx(self) -> dict:
        return {
            "date":          TOMORROW,
            "time_utc":      "07:30",
            "grade":         "A+",
            "intraday":      {},
            "upcoming_news": [],
        }

    def test_future_timestamp_age_is_not_negative(self):
        """_context_age_hours must return a non-negative value — negative is meaningless."""
        age = _context_age_hours(self._future_ctx())
        assert age >= 0, (
            f"_context_age_hours returned {age:.2f}h for a future timestamp. "
            f"A negative age passes the freshness gate, treating future state as current."
        )

    def test_future_timestamp_treated_as_stale(self):
        """A context from the future must be treated as stale (age=999.0)."""
        age = _context_age_hours(self._future_ctx())
        assert age == pytest.approx(999.0), (
            f"Expected 999.0 (stale sentinel) for future timestamp, got {age:.2f}h."
        )

    def test_future_context_freshness_gate_fails(self):
        """The context_not_stale gate must FAIL for a future timestamp."""
        gate = check_trigger_conditions(self._future_ctx())
        assert gate["conditions"]["context_not_stale"]["passed"] is False, (
            "A future timestamp incorrectly passed the freshness gate. "
            "last_run.json from 'tomorrow' is not a valid framework context."
        )

    def test_yesterday_context_correctly_expires(self):
        """A context 24h old exceeds the 4h limit — must fail freshness."""
        old_ctx = {"date": YESTERDAY, "time_utc": "07:30", "grade": "A",
                   "intraday": {}, "upcoming_news": []}
        gate = check_trigger_conditions(old_ctx)
        assert gate["conditions"]["context_not_stale"]["passed"] is False


class TestP1_AutoLabelDateGuardGap:
    """
    P1: label_journal() labels rows with empty or future dates because the
    today-guard uses strict equality (== today) instead of (>= today).

    Empty date: "" != today → skips today check → gets labeled with date=""
    Future date: "2026-06-08" != "2026-06-07" → skips today check → labeled

    Fix: change guard to `if row.get("date","") >= today_str or not date_val.strip()`

    Impact: Journal rows with bad dates get labeled and permanently alter
    the journal file. The calibration engine then trains on bad data.
    """

    def test_empty_date_row_is_not_labeled(self, tmp_path):
        """Row with date='' must be skipped — no valid date means no valid window."""
        row = _base_row(date="", bias="BEARISH", price="2.0300", outcome_label="")
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [row])
        result = label_journal(p, fetch_fn=lambda d: 2.0100)
        assert result["labeled"] == 0, (
            f"Empty-date row was labeled (got labeled={result['labeled']}). "
            f"A row with no date should be skipped — its 24h window is unknown."
        )

    def test_future_date_row_is_not_labeled(self, tmp_path):
        """Row dated tomorrow must be skipped — its 24h window has not closed."""
        row = _base_row(date=TOMORROW, bias="BEARISH", price="2.0300", outcome_label="")
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [row])
        result = label_journal(p, fetch_fn=lambda d: 2.0100)
        assert result["labeled"] == 0, (
            f"Future-dated row was labeled (got labeled={result['labeled']}). "
            f"A row from tomorrow cannot have a closed 24h window today."
        )

    def test_today_date_row_is_still_skipped(self, tmp_path):
        """Existing guard: today's row must remain skipped after the fix."""
        row = _base_row(date=TODAY, bias="BEARISH", price="2.0300", outcome_label="")
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [row])
        result = label_journal(p, fetch_fn=lambda d: 2.0100)
        assert result["labeled"] == 0

    def test_yesterday_date_row_is_still_labeled(self, tmp_path):
        """Regression: yesterday's unlabeled row must still be labeled after the fix."""
        row = _base_row(date=YESTERDAY, bias="BEARISH", price="2.0300", outcome_label="")
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [row])
        result = label_journal(p, fetch_fn=lambda d: 2.0100)
        assert result["labeled"] == 1


class TestP1_SpreadWiderThanTarget:
    """
    P1: When broker spread exceeds the target distance (news spike),
    effective_rr is negative — meaning the spread alone exceeds the reward.
    The current code correctly sets rr_below_minimum=True but the negative
    effective_rr is indistinguishable in severity from effective_rr=1.4.

    Scenario: BoE announcement widens spread to 15 pips.
    Normal stop: 10 pips → adjusted_stop: 25 pips.
    Target: 30 pips → net_target: 30-15 = 15 pips → R:R = 15/25 = 0.6
    With target=3: net_target: 3-15 = -12 → R:R = -0.48 (guaranteed loss)

    This is a real intraday condition. The framework should explicitly flag
    when the trade is guaranteed to lose even if price reaches the target.
    """

    def test_negative_rr_when_spread_exceeds_target(self):
        """Target 3 pips, spread 4 pips → net_target = -1 → effective_rr < 0."""
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=1.0,
            stop_pips=10, spread_pips=4, target_pips=3,
        )
        assert result["effective_rr"] < 0

    def test_rr_below_minimum_flagged_when_spread_exceeds_target(self):
        """rr_below_minimum must be True — negative R:R is always below 1.5."""
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=1.0,
            stop_pips=10, spread_pips=4, target_pips=3,
        )
        assert result["rr_below_minimum"] is True

    def test_news_spike_spread_destroys_rr_on_reasonable_target(self):
        """
        Spread=15 (news spike), stop=10, target=30 pips.
        Net target = 30-15=15, adjusted_stop=25 → R:R = 0.6 (below 1.5).
        """
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=1.0,
            stop_pips=10, spread_pips=15, target_pips=30,
        )
        assert result["adjusted_stop"] == 25
        assert round(result["effective_rr"], 2) == 0.60
        assert result["rr_below_minimum"] is True

    def test_normal_spread_with_good_target_passes_rr(self):
        """Regression: normal conditions (4 pip spread, 40 pip target) pass R:R."""
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=1.0,
            stop_pips=15, spread_pips=4, target_pips=40,
        )
        assert result["rr_below_minimum"] is False
        assert result["effective_rr"] > 1.5


class TestP1_ZeroLotSizeNotFlagged:
    """
    P1: calculate_lot_size() can return 0.00 lots when account is tiny or
    risk_pct is extremely small. A 0-lot order fails at the broker level.
    The framework should add a 'min_lot_warning' flag when lot_size < 0.01
    (the standard minimum lot size on OANDA and most retail brokers).

    Scenario: $100 account, 0.1% risk = $0.10 risk.
              Stop 100 pips + 4 spread = 104 pip adjusted stop.
              Lot size = $0.10 / (104 × $10) = 0.000096 → rounds to 0.00.
    """

    def test_tiny_account_produces_zero_lots(self):
        """Confirm the condition that triggers the gap."""
        result = calculate_lot_size(
            account_balance=100, risk_pct=0.1, stop_pips=100,
        )
        assert result["lot_size"] == 0.00

    def test_zero_lots_triggers_min_lot_warning(self):
        """When lot_size rounds to 0.00, min_lot_warning must be True."""
        result = calculate_lot_size(
            account_balance=100, risk_pct=0.1, stop_pips=100,
        )
        assert "min_lot_warning" in result, (
            "calculate_lot_size does not return 'min_lot_warning'. "
            "A 0-lot calculation will silently fail at the broker."
        )
        assert result["min_lot_warning"] is True

    def test_standard_trade_no_min_lot_warning(self):
        """Regression: $10k account, 1% risk, 15-pip stop → normal lot size, no warning."""
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=1.0, stop_pips=15,
        )
        assert result["lot_size"] >= 0.01
        assert result.get("min_lot_warning") is False

    def test_grade_c_zero_risk_pct_also_warns(self):
        """Grade C = 0% risk → lot_size=0 → min_lot_warning=True."""
        result = calculate_lot_size(
            account_balance=10_000, risk_pct=0.0, stop_pips=15,
        )
        assert result["lot_size"] == 0.0
        assert result.get("min_lot_warning") is True


# ═══════════════════════════════════════════════════════════════════════════════
# P2 DEFENSIVE — Silent data issues or unexpected edge-case behavior
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2_ContextAgeEdgeCases:
    """
    P2: _context_age_hours() edge cases — malformed timestamps, empty fields.
    All of these must return 999.0 (stale) rather than crashing or allowing
    a bad context through.
    """

    def test_empty_context_returns_stale(self):
        assert _context_age_hours({}) == 999.0

    def test_missing_time_utc_returns_stale(self):
        assert _context_age_hours({"date": YESTERDAY}) == 999.0

    def test_missing_date_returns_stale(self):
        assert _context_age_hours({"time_utc": "07:30"}) == 999.0

    def test_invalid_date_format_returns_stale(self):
        assert _context_age_hours({"date": "June 7 2026", "time_utc": "07:30"}) == 999.0

    def test_single_digit_hour_is_handled(self):
        """
        time_utc='7:30' — Python's strptime %H accepts single-digit hours,
        so this parses successfully. The resulting age is valid (not 999.0).
        This confirms _context_age_hours is flexible with time formatting.
        """
        age = _context_age_hours({"date": YESTERDAY, "time_utc": "7:30"})
        assert age != 999.0   # parsed fine — age is real (roughly 24+ hours)
        assert age > 0        # yesterday is in the past


class TestP2_NewsLockoutBoundaries:
    """
    P2: The news_clear gate uses a 120-minute lockout from RISK_RULES.
    Test the exact boundaries and confirm the lockout works correctly.
    """

    def _ctx_with_news(self, minutes: int) -> dict:
        return _fresh_ctx(upcoming_news=[{
            "event": "BoE Rate Decision", "currency": "GBP",
            "minutes": minutes, "time": "12:00",
        }])

    def test_event_90min_away_is_blocked(self):
        """90 min < 120 min lockout → blocked."""
        gate = check_trigger_conditions(self._ctx_with_news(90))
        assert gate["conditions"]["news_clear"]["passed"] is False

    def test_event_120min_away_is_blocked(self):
        """Exactly at the lockout boundary (120 min) → blocked."""
        gate = check_trigger_conditions(self._ctx_with_news(120))
        assert gate["conditions"]["news_clear"]["passed"] is False

    def test_event_121min_away_passes(self):
        """1 minute past the lockout window → clear."""
        gate = check_trigger_conditions(self._ctx_with_news(121))
        assert gate["conditions"]["news_clear"]["passed"] is True

    def test_event_just_released_15min_ago_is_blocked(self):
        """Event released 15 min ago (minutes=-15) — spreads still wide → blocked."""
        gate = check_trigger_conditions(self._ctx_with_news(-15))
        assert gate["conditions"]["news_clear"]["passed"] is False

    def test_event_16min_ago_passes(self):
        """Event released 16 min ago (minutes=-16) → outside the post-release window."""
        gate = check_trigger_conditions(self._ctx_with_news(-16))
        assert gate["conditions"]["news_clear"]["passed"] is True

    def test_no_news_always_passes(self):
        gate = check_trigger_conditions(_fresh_ctx(upcoming_news=[]))
        assert gate["conditions"]["news_clear"]["passed"] is True


class TestP2_SessionGuardWithOpenTrades:
    """
    P2: An open trade (trade_taken=YES, pnl_r empty) counts toward the
    2-trade limit but NOT toward the P&L loss calculation.

    This is intentional design: we don't know the outcome of an open trade yet.
    But it means the session closes after 2 trades even if neither is closed.
    """

    def test_one_open_trade_session_remains_active(self, tmp_path):
        """One open trade → 1 of 2 → ACTIVE — can still take another trade."""
        rows = [_base_row(date=TODAY, trade_taken="YES", pnl_r="", outcome_label="")]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        result = get_session_status(p, 10_000)
        assert result["status"] == STATUS_ACTIVE
        assert result["trades_today"] == 1
        assert result["realized_loss_pct"] == 0.0  # open trades don't count to P&L

    def test_two_open_trades_closes_session(self, tmp_path):
        """Two open trades → 2 of 2 → SESSION_CLOSED regardless of P&L."""
        rows = [
            _base_row(date=TODAY, trade_taken="YES", pnl_r="", outcome_label=""),
            _base_row(date=TODAY, trade_taken="YES", pnl_r="", outcome_label=""),
        ]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        result = get_session_status(p, 10_000)
        assert result["status"] == STATUS_SESSION_CLOSED

    def test_one_open_one_loss_session_closed_not_halted(self, tmp_path):
        """Open trade + 1% loss → SESSION_CLOSED (trade count), not HALTED (loss limit)."""
        rows = [
            _base_row(date=TODAY, trade_taken="YES", pnl_r="",     outcome_label=""),
            _base_row(date=TODAY, trade_taken="YES", pnl_r="-1.0", outcome_label="LOSS"),
        ]
        p = tmp_path / "journal.csv"
        write_journal_csv(p, rows)
        result = get_session_status(p, 10_000)
        assert result["status"] == STATUS_SESSION_CLOSED   # count limit, not loss limit
        assert result["realized_loss_pct"] == 1.0

    def test_zero_account_balance_halts_immediately(self, tmp_path):
        """account_balance <= 0 → HALTED before reading journal."""
        p = tmp_path / "journal.csv"
        write_journal_csv(p, [])
        result = get_session_status(p, 0)
        assert result["status"] == STATUS_HALTED


class TestP2_ComputeLabelBoundaries:
    """
    P2: compute_label() boundary conditions — exact thresholds, edge prices,
    case sensitivity, and whitespace handling.
    """

    def test_exactly_20_pips_bearish_is_win(self):
        """The ≥ 20 threshold is inclusive — exactly 20 pips is a WIN.
        1 pip = 0.0001, so 20 pips = 0.0020 price fall for BEARISH."""
        result = compute_label(run_price=2.0300, bias="BEARISH", close_price=2.0280)
        assert result["pips_with_bias"] == pytest.approx(20.0)
        assert result["outcome_label"] == "WIN"

    def test_exactly_negative_20_pips_is_loss(self):
        """Exactly -20 pips is a LOSS (≤ -20 is inclusive).
        Price rose 0.0020 against a BEARISH call."""
        result = compute_label(run_price=2.0300, bias="BEARISH", close_price=2.0320)
        assert result["pips_with_bias"] == pytest.approx(-20.0)
        assert result["outcome_label"] == "LOSS"

    def test_19_pips_is_neutral_just_under_threshold(self):
        """19 pips — just below 20-pip win threshold → NEUTRAL.
        0.0019 price fall = 19 pips for BEARISH."""
        result = compute_label(run_price=2.0300, bias="BEARISH", close_price=2.0281)
        assert result["outcome_label"] == "NEUTRAL"

    def test_zero_movement_is_neutral(self):
        """Price at exactly the same level → 0 pips → NEUTRAL."""
        result = compute_label(run_price=2.0300, bias="BEARISH", close_price=2.0300)
        assert result["outcome_label"] == "NEUTRAL"
        assert result["pips_with_bias"] == 0.0

    def test_bias_trailing_whitespace_handled(self):
        """'BEARISH ' with trailing space must be treated as BEARISH."""
        result = compute_label(run_price=2.0300, bias="BEARISH ", close_price=2.0280)
        assert result["outcome_label"] == "WIN"

    def test_bias_lowercase_handled(self):
        """'bearish' lowercase must work same as 'BEARISH'."""
        result = compute_label(run_price=2.0300, bias="bearish", close_price=2.0280)
        assert result["outcome_label"] == "WIN"

    def test_neutral_bias_returns_empty_label(self):
        """'NEUTRAL' bias has no directional call → outcome_label=''."""
        result = compute_label(run_price=2.0300, bias="NEUTRAL", close_price=2.0280)
        assert result["outcome_label"] == ""

    def test_bullish_direction_correct_pip_sign(self):
        """BULLISH: price rising 20 pips = positive pips → WIN.
        0.0020 price rise = 20 pips."""
        result = compute_label(run_price=2.0300, bias="BULLISH", close_price=2.0320)
        assert result["pips_with_bias"] == pytest.approx(20.0)
        assert result["outcome_label"] == "WIN"


class TestP2_GradeSystemConsistency:
    """
    P2: Grade assignment system-level consistency — hard blocks, penalties,
    and bonuses must interact correctly across all combinations.
    """

    def test_event_risk_always_forces_grade_c(self):
        """event_risk=True must ALWAYS produce Grade C — even with perfect alignment."""
        for alignment in (90, 75, 55, 40, 0):
            grade, risk, _, _ = get_grade(
                alignment=alignment, quality="HIGH",
                is_counter_trend=False, event_risk=True,
                session="London Session",
            )
            assert grade == "C", f"event_risk=True with alignment={alignment} gave {grade}"
            assert risk == 0.0

    def test_do_not_trade_quality_forces_grade_c(self):
        """quality='DO NOT TRADE' must always produce Grade C."""
        grade, risk, _, _ = get_grade(
            alignment=90, quality="DO NOT TRADE",
            is_counter_trend=False, event_risk=False,
            session="London Session",
        )
        assert grade == "C"
        assert risk == 0.0

    def test_htf_conflict_reduces_grade_vs_clean_context(self):
        """htf_conflict=True must produce equal or lower grade than clean context."""
        grades_order = ["A+", "A", "B+", "B", "C"]
        grade_clean, _, _, _ = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session", htf_conflict=False,
        )
        grade_conflict, _, _, _ = get_grade(
            alignment=75, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session", htf_conflict=True,
        )
        assert grades_order.index(grade_conflict) >= grades_order.index(grade_clean), (
            f"htf_conflict should reduce grade: {grade_clean} → {grade_conflict}"
        )

    def test_tokyo_session_caps_at_B_plus(self):
        """Tokyo session: alignment capped at 69 → can never reach A or A+."""
        grade, _, _, _ = get_grade(
            alignment=90, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="Tokyo Session",
        )
        assert grade not in ("A+", "A"), f"Tokyo session should cap at B+, got {grade}"

    def test_london_ny_overlap_is_highest_energy_session(self):
        """London+NY overlap adds the most bonus — same alignment should give better grade."""
        grade_london, _, _, _ = get_grade(
            alignment=72, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London Session",
        )
        grade_overlap, _, _, _ = get_grade(
            alignment=72, quality="HIGH",
            is_counter_trend=False, event_risk=False,
            session="London New York Session",
        )
        grades_order = ["A+", "A", "B+", "B", "C"]
        assert grades_order.index(grade_overlap) <= grades_order.index(grade_london), (
            f"Overlap should give >= grade: London={grade_london}, Overlap={grade_overlap}"
        )
