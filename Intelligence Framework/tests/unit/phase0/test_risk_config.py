"""
tests/unit/phase0/test_risk_config.py

Unit + behavioral tests for risk_config.py grade system and HARD_LIMITS.

Plain English: these tests confirm that the framework assigns the correct
               trade size grade given the market inputs, and that the hard
               limits (daily loss cap, spread, R:R floor) are locked in.
"""

import pytest
from risk_config import (
    get_grade,
    get_size_note,
    HARD_LIMITS,
    RISK_RULES,
    GRADE_CONFIG,
)
from tests.fixtures.market_scenarios import SCENARIO_F, SCENARIO_H


# ── HARD_LIMITS structure ─────────────────────────────────────────────────────

class TestHardLimits:

    def test_hard_limits_dict_exists(self):
        """HARD_LIMITS must be importable from risk_config."""
        assert isinstance(HARD_LIMITS, dict)

    def test_hard_limits_has_all_required_keys(self):
        required = [
            "max_daily_loss_pct",
            "max_trades_per_session",
            "min_rr_after_spread",
            "spread_pips",
            "context_expiry_hours",
        ]
        for key in required:
            assert key in HARD_LIMITS, f"HARD_LIMITS missing key: {key}"

    def test_max_daily_loss_matches_session_guard(self):
        """Single source of truth — must equal session_guard.MAX_DAILY_LOSS_PCT."""
        from session_guard import MAX_DAILY_LOSS_PCT
        assert HARD_LIMITS["max_daily_loss_pct"] == MAX_DAILY_LOSS_PCT

    def test_max_trades_matches_session_guard(self):
        """Single source of truth — must equal session_guard.MAX_TRADES_PER_SESSION."""
        from session_guard import MAX_TRADES_PER_SESSION
        assert HARD_LIMITS["max_trades_per_session"] == MAX_TRADES_PER_SESSION

    def test_min_rr_is_at_least_1_point_5(self):
        """R:R floor must be 1.5 — below this the reward does not justify the risk."""
        assert HARD_LIMITS["min_rr_after_spread"] >= 1.5

    def test_spread_pips_is_positive(self):
        assert HARD_LIMITS["spread_pips"] > 0

    def test_context_expiry_hours_is_positive(self):
        assert HARD_LIMITS["context_expiry_hours"] > 0


# ── get_grade() — basic grade assignments ─────────────────────────────────────

class TestGetGradeBasic:

    def test_event_risk_always_returns_C(self):
        """High-impact news → C grade, no matter how good the setup looks."""
        grade, risk_pct, label, reason = get_grade(
            alignment=95, quality="HIGH", is_counter_trend=False,
            event_risk=True, session="London Session",
        )
        assert grade == "C"
        assert risk_pct == 0.0

    def test_do_not_trade_quality_returns_C(self):
        grade, risk_pct, label, reason = get_grade(
            alignment=90, quality="DO NOT TRADE", is_counter_trend=False,
            event_risk=False, session="London Session",
        )
        assert grade == "C"

    def test_strong_alignment_high_quality_returns_Aplus(self):
        """Clean A+ conditions — all signals aligned, London session."""
        grade, risk_pct, label, reason = get_grade(
            alignment=90, quality="HIGH", is_counter_trend=False,
            event_risk=False, session="London Session",
            sweep_confirmed=True, is_value_aligned=True,
        )
        assert grade == "A+"
        assert risk_pct == 1.5

    def test_low_alignment_returns_C(self):
        """Below minimum — must refuse to grade above C."""
        grade, risk_pct, label, reason = get_grade(
            alignment=20, quality="LOW", is_counter_trend=False,
            event_risk=False, session="London Session",
        )
        assert grade == "C"

    def test_grade_config_has_all_grades(self):
        """GRADE_CONFIG must define all five grades."""
        for g in ("A+", "A", "B+", "B", "C"):
            assert g in GRADE_CONFIG, f"Grade '{g}' missing from GRADE_CONFIG"

    def test_grade_risk_pcts_are_ordered(self):
        """A+ > A > B+ > B > C in risk_pct — larger grade = larger size."""
        pcts = [GRADE_CONFIG[g]["risk_pct"] for g in ("A+", "A", "B+", "B", "C")]
        assert pcts == sorted(pcts, reverse=True)

    def test_returns_four_tuple(self):
        result = get_grade(
            alignment=70, quality="HIGH", is_counter_trend=False,
            event_risk=False, session="London Session",
        )
        assert len(result) == 4
        grade, risk_pct, label, reason = result
        assert isinstance(grade, str)
        assert isinstance(risk_pct, float)
        assert isinstance(label, str)
        assert isinstance(reason, str)


# ── Behavioral: Scenario F — Counter-trend penalty ───────────────────────────

class TestScenarioF:
    """
    Scenario F — Counter-trend bounce with alignment 75.
    Expected: grade A (not A+).

    Plain English: the trade direction fights the main trend (-10 penalty).
                   Even though a sweep and value zone are confirmed (+13 bonus),
                   the counter-trend penalty keeps the final score below 85 → A.

    Math:
        alignment = 75
        - 10 (counter-trend)
        + 8  (sweep confirmed)
        + 5  (value aligned)
        + 5  (London session)
        ─────────────────────
        adjusted = 83  →  < 85  →  A (not A+)
    """

    def _call(self):
        return get_grade(
            alignment=SCENARIO_F["alignment"],
            quality=SCENARIO_F["quality"],
            is_counter_trend=SCENARIO_F["is_counter_trend"],
            event_risk=SCENARIO_F["event_risk"],
            session=SCENARIO_F["session"],
            sweep_confirmed=SCENARIO_F["sweep_confirmed"],
            is_value_aligned=SCENARIO_F["is_value_aligned"],
            htf_conflict=SCENARIO_F["htf_conflict"],
        )

    def test_grade_is_A_not_Aplus(self):
        grade, _, _, _ = self._call()
        assert grade == SCENARIO_F["expected_grade"], (
            f"Expected A but got {grade} — counter-trend penalty not applied correctly"
        )

    def test_risk_pct_is_1_0(self):
        _, risk_pct, _, _ = self._call()
        assert risk_pct == SCENARIO_F["expected_risk_pct"]

    def test_reason_mentions_counter_trend(self):
        """The reason string must flag this as a counter-trend trade."""
        _, _, _, reason = self._call()
        assert SCENARIO_F["expected_reason_contains"] in reason.lower(), (
            f"Expected 'counter' in reason but got: '{reason}'"
        )

    def test_not_Aplus_even_with_high_quality(self):
        """HIGH quality is not enough to override the counter-trend penalty."""
        grade, _, _, _ = self._call()
        assert grade != "A+", "Counter-trend trades must never reach A+"


# ── Behavioral: Scenario H — Tokyo session caps grade ────────────────────────

class TestScenarioH:
    """
    Scenario H — Tokyo session with raw alignment 90.
    Expected: grade A (not A+).

    Plain English: Tokyo is a low-volume session. The framework clamps the
                   alignment to 69 before calculating. Even with a sweep
                   bonus (+8), the final adjusted score is 77 → A, not A+.
                   If this same setup fired in London, it would be A+.

    Math (Tokyo):
        alignment capped at 69
        + 8  (sweep confirmed)
        ─────────────────────
        adjusted = 77  →  ≥ 70 but < 85  →  A

    Math (London — contrast):
        alignment = 90 (no cap)
        + 8  (sweep confirmed)
        + 5  (London session)
        ─────────────────────
        adjusted = 103  →  ≥ 85  →  A+
    """

    def _call_tokyo(self):
        return get_grade(
            alignment=SCENARIO_H["raw_alignment"],
            quality=SCENARIO_H["quality"],
            is_counter_trend=SCENARIO_H["is_counter_trend"],
            event_risk=SCENARIO_H["event_risk"],
            session="Tokyo Session",
            sweep_confirmed=True,
        )

    def _call_london(self):
        return get_grade(
            alignment=SCENARIO_H["raw_alignment"],
            quality=SCENARIO_H["quality"],
            is_counter_trend=SCENARIO_H["is_counter_trend"],
            event_risk=SCENARIO_H["event_risk"],
            session="London Session",
            sweep_confirmed=True,
        )

    def test_tokyo_grade_is_A(self):
        grade, _, _, _ = self._call_tokyo()
        assert grade == SCENARIO_H["expected_grade"], (
            f"Expected A in Tokyo but got {grade}"
        )

    def test_tokyo_never_reaches_Aplus(self):
        grade, _, _, _ = self._call_tokyo()
        assert grade != "A+", "Tokyo session must never produce an A+ grade"

    def test_tokyo_risk_pct_capped_at_1_0(self):
        _, risk_pct, _, _ = self._call_tokyo()
        assert risk_pct == SCENARIO_H["expected_risk_pct"]

    def test_same_inputs_london_gives_Aplus(self):
        """
        Proof that the cap is specifically Tokyo — London produces A+.
        Plain English: it is NOT the alignment that prevents A+; it is the session.
        """
        grade, _, _, _ = self._call_london()
        assert grade == "A+", (
            "Same inputs in London should produce A+ — Tokyo cap is doing the work"
        )


# ── get_size_note() backward compatibility ───────────────────────────────────

class TestGetSizeNote:

    def test_returns_dict_with_required_keys(self):
        result = get_size_note(
            quality="HIGH", alignment=80, is_counter_trend=False,
            event_risk=False, session="London Session",
        )
        for key in ["allowed", "grade", "risk_pct", "size_note", "label", "reason"]:
            assert key in result, f"get_size_note missing key: {key}"

    def test_C_grade_sets_allowed_false(self):
        result = get_size_note(
            quality="HIGH", alignment=90, is_counter_trend=False,
            event_risk=True, session="London Session",
        )
        assert result["allowed"] is False
        assert result["grade"] == "C"

    def test_A_grade_sets_allowed_true(self):
        result = get_size_note(
            quality="HIGH", alignment=80, is_counter_trend=False,
            event_risk=False, session="London Session",
        )
        assert result["allowed"] is True
