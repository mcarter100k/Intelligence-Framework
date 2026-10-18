"""
test_risk_config.py
───────────────────
First dedicated coverage for risk_config (the module had none — promotion
spec, 2026-09-09). Pins the grade ladder, the lot-size arithmetic, the
hard-limit wiring to session_guard, and the shared-leg standing rule.

Run: pytest tests/test_risk_config.py
"""
import pytest

import risk_config as rc
import session_guard as sg


def _grade(**over):
    base = dict(alignment=60, quality="MEDIUM", is_counter_trend=False,
                event_risk=False, session="London")
    base.update(over)
    return rc.get_grade(**base)


# ── grade ladder ───────────────────────────────────────────────────────────────

def test_event_risk_is_a_hard_block():
    g, risk, label, reason = _grade(event_risk=True, alignment=100, quality="HIGH")
    assert g == "C" and risk == 0.0
    assert "EVENT RISK" in label

def test_do_not_trade_quality_is_a_hard_block():
    g, risk, *_ = _grade(quality="DO NOT TRADE", alignment=100)
    assert g == "C" and risk == 0.0

def test_a_plus_needs_score_and_high_quality():
    # 85 base + 5 London bonus = 90 adjusted, HIGH quality → A+ at 1.5%
    g, risk, *_ = _grade(alignment=85, quality="HIGH")
    assert (g, risk) == ("A+", 1.5)
    # same score, MEDIUM quality → capped below A tier → B+
    g2, risk2, *_ = _grade(alignment=85, quality="MEDIUM")
    assert (g2, risk2) == ("B+", 0.5)

def test_grade_risk_mapping_matches_config():
    for g, cfg in rc.GRADE_CONFIG.items():
        assert cfg["risk_pct"] == {"A+": 1.5, "A": 1.0, "B+": 0.5,
                                   "B": 0.25, "C": 0.0}[g]

def test_counter_trend_penalty_costs_a_grade():
    # 70 + 5 (London) = 75 → A; counter-trend −10 → 65 → B+
    g, *_ = _grade(alignment=70, quality="HIGH")
    assert g == "A"
    g2, *_ = _grade(alignment=70, quality="HIGH", is_counter_trend=True)
    assert g2 == "B+"

def test_tokyo_caps_below_a_tier():
    g, *_ = _grade(alignment=95, quality="HIGH", session="Tokyo")
    assert g in ("B+", "B", "C")        # never A/A+ in Tokyo

def test_baseline_reason_is_plain():
    *_, reason = _grade(session="")
    assert reason == "baseline signals"


# ── lot sizing ─────────────────────────────────────────────────────────────────

def test_lot_size_arithmetic_pinned():
    # $10k, 1% risk = $100; stop 30p + spread 4p = 34p adjusted;
    # 100 / (34 × $10) = 0.29 lots
    r = rc.calculate_lot_size(10_000, 1.0, 30.0, spread_pips=4.0)
    assert r["lot_size"] == 0.29
    assert r["dollar_risk"] == 100.0
    assert r["adjusted_stop"] == 34.0

def test_effective_rr_after_spread_and_floor():
    # target 60p − 4 spread = 56 net; 56/34 = 1.6471 ≥ 1.5 floor
    r = rc.calculate_lot_size(10_000, 1.0, 30.0, spread_pips=4.0,
                              target_pips=60.0)
    assert r["effective_rr"] == 1.6471
    assert r["rr_below_minimum"] is False
    # target 45p → 41/34 = 1.2059 < 1.5 floor
    r2 = rc.calculate_lot_size(10_000, 1.0, 30.0, spread_pips=4.0,
                               target_pips=45.0)
    assert r2["rr_below_minimum"] is True

def test_min_lot_warning_below_broker_minimum():
    r = rc.calculate_lot_size(100, 0.25, 50.0, spread_pips=4.0)
    assert r["min_lot_warning"] is True

def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        rc.calculate_lot_size(0, 1.0, 30.0)
    with pytest.raises(ValueError):
        rc.calculate_lot_size(10_000, 1.0, 0)


# ── hard-limit wiring + the standing rule ──────────────────────────────────────

def test_hard_limits_wired_to_session_guard():
    assert rc.HARD_LIMITS["max_daily_loss_pct"] == sg.MAX_DAILY_LOSS_PCT
    assert rc.HARD_LIMITS["max_daily_loss_r"] == sg.MAX_DAILY_LOSS_R
    assert rc.HARD_LIMITS["max_trades_per_session"] == sg.MAX_TRADES_PER_SESSION

def test_standing_rule_documented_and_reexported():
    assert rc.RISK_RULES["shared_leg_counts_as_one"] is True
    assert rc.count_leg_grouped_positions is sg.count_leg_grouped_positions
    assert rc.count_leg_grouped_positions(["GBP_AUD", "GBP_JPY"]) == 1
