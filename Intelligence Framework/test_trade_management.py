"""
test_trade_management.py

Locks Phase 3.1: instrument-aware pip maths (no 100x JPY error) and geometry /
reward-risk validation so an incoherent trade never yields a clean-looking plan.

Run: pytest test_trade_management.py
"""
import pytest

from trade_management import get_management_plan


def test_jpy_pip_factor_is_not_100x_off():
    # GBP_JPY: 0.50 price = 50 pips (pip size 0.01), NOT 5000.
    plan = get_management_plan(
        entry=217.00, stop=216.50, target=218.50, direction="LONG",
        instrument="GBP_JPY",
    )
    assert plan["valid"] is True
    assert plan["r_pips"] == pytest.approx(50.0)


def test_aud_pip_factor_unchanged():
    # GBP_AUD: 0.0050 price = 50 pips (pip size 0.0001).
    plan = get_management_plan(
        entry=1.9000, stop=1.8950, target=1.9150, direction="LONG",
        instrument="GBP_AUD",
    )
    assert plan["valid"] is True
    assert plan["r_pips"] == pytest.approx(50.0)
    assert plan["rr"] == pytest.approx(3.0)  # reward 150 / risk 50


def test_long_stop_on_wrong_side_is_invalid():
    plan = get_management_plan(
        entry=1.9000, stop=1.9050, target=1.9150, direction="LONG",
    )
    assert plan["valid"] is False
    assert any("stop" in e.lower() for e in plan["errors"])


def test_long_target_on_wrong_side_is_invalid():
    plan = get_management_plan(
        entry=1.9000, stop=1.8950, target=1.8990, direction="LONG",
    )
    assert plan["valid"] is False
    assert any("target" in e.lower() for e in plan["errors"])


def test_reward_less_than_risk_is_invalid():
    # risk 0.010, reward 0.005 → rr 0.5 < 1.0
    plan = get_management_plan(
        entry=1.9000, stop=1.8900, target=1.9050, direction="LONG",
    )
    assert plan["valid"] is False
    assert plan["rr"] == pytest.approx(0.5)


def test_below_effective_rr_floor_is_invalid():
    # Raw R:R ~1.3 but after 4-pip spread it drops below the 1.5 floor.
    # entry 1.9000, stop 1.8900 (risk 100p), target 1.9130 (reward 130p)
    # effective = (130-4)/(100+4) = 126/104 ≈ 1.21 < 1.5
    plan = get_management_plan(
        entry=1.9000, stop=1.8900, target=1.9130, direction="LONG",
    )
    assert plan["valid"] is False
    assert plan["effective_rr"] < 1.5
    assert any("spread" in e.lower() for e in plan["errors"])


def test_valid_short_plan():
    plan = get_management_plan(
        entry=1.9000, stop=1.9050, target=1.8850, direction="SHORT",
    )
    assert plan["valid"] is True
    assert plan["rr"] == pytest.approx(3.0)  # reward 150 / risk 50
    assert "TRADE MANAGEMENT PLAN" in plan["plan_text"]
