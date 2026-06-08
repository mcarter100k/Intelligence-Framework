"""
tests/unit/phase0/test_lot_size.py

Unit + behavioral tests for risk_config.calculate_lot_size().

Plain English: these tests verify that the framework sizes every trade
               correctly so the account can never lose more than the
               stated risk percentage — even after spread is added.
"""

import pytest
from risk_config import calculate_lot_size, HARD_LIMITS
from tests.fixtures.market_scenarios import SCENARIO_I, SCENARIO_A


# ── Return structure ──────────────────────────────────────────────────────────

class TestReturnStructure:

    def test_returns_dict(self):
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert isinstance(result, dict)

    def test_has_all_required_keys(self):
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        for key in ["lot_size", "dollar_risk", "adjusted_stop", "effective_rr", "rr_below_minimum"]:
            assert key in result, f"Missing key: {key}"

    def test_lot_size_is_float(self):
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert isinstance(result["lot_size"], float)

    def test_rr_below_minimum_is_bool(self):
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert isinstance(result["rr_below_minimum"], bool)


# ── Core lot size math ────────────────────────────────────────────────────────

class TestLotSizeMath:

    def test_basic_sizing_no_spread(self):
        """
        $10k account, 1% risk, 30-pip stop, no spread.
        dollar_risk = $100, lot_size = 100 / (30 * 10) = 0.33
        """
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert result["dollar_risk"]   == pytest.approx(100.0)
        assert result["lot_size"]      == pytest.approx(0.33)
        assert result["adjusted_stop"] == 30

    def test_sizing_with_spread(self):
        """
        $10k account, 1% risk, 30-pip stop, 4-pip spread.
        adjusted_stop = 34, lot_size = 100 / (34 * 10) = 0.29
        """
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=4)
        assert result["adjusted_stop"] == 34
        assert result["lot_size"]      == pytest.approx(0.29)

    def test_dollar_risk_scales_with_balance(self):
        """Doubling the balance doubles the dollar risk."""
        r1 = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        r2 = calculate_lot_size(20_000, 1.0, 30, spread_pips=0)
        assert r2["dollar_risk"] == pytest.approx(r1["dollar_risk"] * 2)

    def test_larger_stop_produces_smaller_lot(self):
        """Wider stop = fewer lots for the same dollar risk."""
        r_narrow = calculate_lot_size(10_000, 1.0, 20, spread_pips=0)
        r_wide   = calculate_lot_size(10_000, 1.0, 40, spread_pips=0)
        assert r_wide["lot_size"] < r_narrow["lot_size"]

    def test_higher_risk_pct_produces_larger_lot(self):
        """More risk % = bigger position."""
        r_low  = calculate_lot_size(10_000, 0.5, 30, spread_pips=0)
        r_high = calculate_lot_size(10_000, 1.5, 30, spread_pips=0)
        assert r_high["lot_size"] > r_low["lot_size"]

    def test_adjusted_stop_is_stop_plus_spread(self):
        result = calculate_lot_size(10_000, 1.0, 25, spread_pips=5)
        assert result["adjusted_stop"] == 30

    def test_default_spread_comes_from_hard_limits(self):
        """Omitting spread_pips should use HARD_LIMITS default (4.0 pips)."""
        result_default  = calculate_lot_size(10_000, 1.0, 30)
        result_explicit = calculate_lot_size(10_000, 1.0, 30, spread_pips=4.0)
        assert result_default["adjusted_stop"] == result_explicit["adjusted_stop"]
        assert result_default["lot_size"]      == result_explicit["lot_size"]

    def test_scenario_a_lot_size(self):
        """
        Scenario A: A+ SHORT — $10k, 1.5% risk, 40-pip structure stop, 4-pip spread.
        adjusted_stop = 44, dollar_risk = $150, lot_size = 150 / (44 * 10) = 0.34
        """
        result = calculate_lot_size(
            account_balance=SCENARIO_A["account_balance"],
            risk_pct=SCENARIO_A["expected_risk_pct"],
            stop_pips=40,
            spread_pips=4,
        )
        assert result["dollar_risk"]   == pytest.approx(SCENARIO_A["expected_dollar_risk"])
        assert result["adjusted_stop"] == SCENARIO_A["expected_stop_pips"]
        assert result["lot_size"]      == pytest.approx(SCENARIO_A["expected_lot_size"])


# ── Input validation ──────────────────────────────────────────────────────────

class TestValidation:

    def test_raises_on_zero_stop(self):
        """Stop of 0 pips is undefined — cannot size a trade."""
        with pytest.raises(ValueError, match="stop_pips"):
            calculate_lot_size(10_000, 1.0, 0)

    def test_raises_on_negative_stop(self):
        with pytest.raises(ValueError, match="stop_pips"):
            calculate_lot_size(10_000, 1.0, -10)

    def test_raises_on_zero_balance(self):
        """Zero balance — nothing to risk."""
        with pytest.raises(ValueError, match="account_balance"):
            calculate_lot_size(0, 1.0, 30)

    def test_raises_on_negative_balance(self):
        with pytest.raises(ValueError, match="account_balance"):
            calculate_lot_size(-5_000, 1.0, 30)


# ── R:R calculation ───────────────────────────────────────────────────────────

class TestRiskReward:

    def test_no_target_gives_none_rr(self):
        """If no target provided, effective_rr should be None."""
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert result["effective_rr"] is None

    def test_no_target_rr_below_minimum_is_false(self):
        """Without a target, rr_below_minimum defaults to False."""
        result = calculate_lot_size(10_000, 1.0, 30, spread_pips=0)
        assert result["rr_below_minimum"] is False

    def test_good_rr_is_not_below_minimum(self):
        """
        stop=20, target=60, spread=0 → R:R = 60/20 = 3.0 → above 1.5 floor.
        """
        result = calculate_lot_size(10_000, 1.0, 20, spread_pips=0, target_pips=60)
        assert result["rr_below_minimum"] is False
        assert result["effective_rr"] == pytest.approx(3.0)

    def test_spread_reduces_effective_rr(self):
        """Adding spread makes R:R worse on both sides."""
        no_spread   = calculate_lot_size(10_000, 1.0, 30, spread_pips=0, target_pips=45)
        with_spread = calculate_lot_size(10_000, 1.0, 30, spread_pips=4, target_pips=45)
        assert with_spread["effective_rr"] < no_spread["effective_rr"]

    def test_at_exactly_minimum_rr_not_flagged(self):
        """
        R:R that equals the minimum exactly is acceptable (not strictly below).
        stop=20, spread=0, target=30 → 30/20 = 1.5 exactly → rr_below_minimum=False
        """
        result = calculate_lot_size(10_000, 1.0, 20, spread_pips=0, target_pips=30)
        assert result["effective_rr"] == pytest.approx(1.5)
        assert result["rr_below_minimum"] is False


# ── Behavioral: Scenario I — Spread wipes R:R below minimum ──────────────────

class TestScenarioI:
    """
    Scenario I — Stop 30 pips, target 45 pips.
    Before spread: R:R looks acceptable at 1.5.
    After 4-pip spread: effective R:R drops to 1.21 — below the 1.5 floor.
    This trade must be blocked.

    Plain English: the broker takes 4 pips immediately when you enter.
                   That 4-pip cost is added to your stop (makes it harder to
                   hit breakeven) and subtracted from your target (reduces
                   your reward). The raw 1:1.5 R:R shrinks to 1:1.21 — not
                   worth the risk.
    """

    def _call(self):
        return calculate_lot_size(
            account_balance=10_000,
            risk_pct=1.0,
            stop_pips=SCENARIO_I["stop_pips"],
            spread_pips=SCENARIO_I["spread_pips"],
            target_pips=SCENARIO_I["target_pips"],
        )

    def test_adjusted_stop_is_34(self):
        result = self._call()
        assert result["adjusted_stop"] == SCENARIO_I["effective_stop"]

    def test_effective_rr_is_approx_1_21(self):
        result = self._call()
        assert result["effective_rr"] == pytest.approx(
            SCENARIO_I["effective_target"] / SCENARIO_I["effective_stop"],
            rel=1e-3,
        )

    def test_rr_below_minimum_is_true(self):
        result = self._call()
        assert result["rr_below_minimum"] is SCENARIO_I["expected_rr_below_minimum"]

    def test_rr_below_minimum_is_true_not_just_truthy(self):
        result = self._call()
        assert result["rr_below_minimum"] is True

    def test_dollar_risk_still_calculated_correctly(self):
        """The sizing math is still correct — it's the R:R that fails, not the size."""
        result = self._call()
        assert result["dollar_risk"] == pytest.approx(100.0)

    def test_lot_size_accounts_for_spread_in_stop(self):
        """Lot size uses adjusted_stop (34), not raw stop (30)."""
        result = self._call()
        # $100 risk / (34 pips * $10/pip) = 0.29 lots
        assert result["lot_size"] == pytest.approx(100.0 / (34 * 10.0), abs=0.01)

    def test_raw_rr_would_have_passed(self):
        """Without spread, the same trade would pass — spread is the decisive factor."""
        no_spread = calculate_lot_size(
            account_balance=10_000,
            risk_pct=1.0,
            stop_pips=SCENARIO_I["stop_pips"],
            spread_pips=0,
            target_pips=SCENARIO_I["target_pips"],
        )
        # raw R:R = 45/30 = 1.5 — exactly at the minimum, not flagged
        assert no_spread["rr_below_minimum"] is False
