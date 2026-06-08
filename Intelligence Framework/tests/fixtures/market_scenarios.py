"""
fixtures/market_scenarios.py

The 12 real-world market scenarios used across behavioral tests.
Each scenario is a dict that can be injected into mocks or passed
directly to the functions under test.

Plain English label on every scenario so tests read like documentation.
"""

# ── Scenario A — The Perfect Storm (A+ SHORT, London open) ───────────────────
SCENARIO_A = {
    "label": "A+ SHORT during London open — all signals aligned",
    "time_utc": "07:15",
    "session": "London",
    "direction": "SHORT",
    "expected_grade": "A+",
    "expected_risk_pct": 1.5,
    "expected_conviction_min": 85,
    "htf": {
        "context": "ESTABLISHED_DOWNTREND",
        "lt_trend": "DOWNTREND",
        "st_trend": "DOWNTREND",
        "adx": 32,
        "ma50": "2.0250",
        "nearest_daily_swing_high": 2.0380,
        "nearest_daily_swing_low": 2.0100,
    },
    "liquidity": {
        "current_price": 2.0300,
        "sweep_up": True,
        "sweep_down": False,
        "nearest_pool": 2.0380,
        "pool_direction": "resistance",
        "pdh": 2.0380,
        "pdl": 2.0150,
        "pwh": 2.0420,
        "pwl": 2.0050,
    },
    "currency_strength": {
        "GBP": -8,
        "AUD": 7,
        "differential": -15,
        "error": None,
    },
    "regime": {
        "regime": "TRENDING_DOWN",
        "adx": 32,
        "fuel_pct": 45,
        "atr_pips": 155,
        "current_price": 2.0300,
    },
    "value": {
        "verdict": "PREMIUM",
        "verdict_bias": "BEARISH",
        "fair_value": 2.0180,
        "fv_diff_pips": 120,
    },
    "session_data": {
        "session": "London",
        "session_label": "London Session",
        "market_closed": False,
    },
    "news": {"events": [], "data_available": True, "net_score": 0, "bias": "NEUTRAL"},
    "intraday": {
        "fakeout_detected": True,
        "fakeout_type": "BEARISH_FAKEOUT",
        "intraday_bias": "SHORT",
        "asian_range_pips": 40,
        "fakeout_note": "London swept Asian high at 2.0380, rejected hard — bearish fakeout",
        "entry_note": "Sell retest of 2.0376-2.0384, stop 2.0424",
    },
    "account_balance": 10_000,
    # Expected trade math
    "expected_stop_pips": 44,       # 40 pip structure + 4 pip spread
    "expected_lot_size": 0.34,      # $150 risk / (44 pips * $10)
    "expected_dollar_risk": 150.0,
    "expected_rr_min": 4.0,
}

# ── Scenario B — News Block kills a valid setup ───────────────────────────────
SCENARIO_B = {
    "label": "BoE Rate Decision in 90 min — hard block, no trade regardless of grade",
    "time_utc": "10:30",
    "session": "London",
    "direction": "NO TRADE",
    "expected_grade": "C",
    "expected_conviction": 0,
    "news_event": {
        "event": "BoE Rate Decision",
        "currency": "GBP",
        "impact": "High",
        "time": "12:00",   # 90 min away from 10:30
    },
    "blocker": "BoE Rate Decision",
}

# ── Scenario C — Daily kill switch fires ─────────────────────────────────────
SCENARIO_C = {
    "label": "Two losses today totaling -2.3% — session halted, A+ setup blocked",
    "account_balance": 10_000,
    "trades_today": [
        {"time_utc": "08:00", "pnl_r": -1.1, "outcome": "LOSS"},
        {"time_utc": "10:00", "pnl_r": -1.2, "outcome": "LOSS"},
    ],
    "total_loss_pct": 2.3,
    "max_daily_loss_pct": 2.0,
    "expected_status": "HALTED",
    "expected_can_trade": False,
}

# ── Scenario D — Stale context, watcher refuses ───────────────────────────────
SCENARIO_D = {
    "label": "Framework ran 5.75h ago — context expired, watcher blocked",
    "last_run_time_utc": "11:00",
    "current_time_utc": "16:45",
    "context_age_hours": 5.75,
    "context_expiry_hours": 4.0,
    "expected_blocked": True,
    "expected_failing_condition": "context_not_stale",
}

# ── Scenario E — Asian range both extremes swept (chaos) ─────────────────────
SCENARIO_E = {
    "label": "Asian high AND low both swept — chaotic, hard block, NO TRADE",
    "intraday": {
        "fakeout_detected": True,
        "fakeout_type": "BOTH_SWEPT",
        "intraday_bias": "WAIT",
        "asian_range_pips": 28,
        "asian_high": 2.0340,
        "asian_low": 2.0312,
        "warning": "Both Asian range extremes swept — no clean signal",
    },
    "expected_direction": "NO TRADE",
    "expected_block_contains": "BOTH_SWEPT",
}

# ── Scenario F — Counter-trend penalty applied ───────────────────────────────
SCENARIO_F = {
    "label": "Counter-trend bounce — -10 conviction penalty, grade capped at A",
    "alignment": 75,
    "quality": "HIGH",
    "is_counter_trend": True,
    "session": "London",
    "event_risk": False,
    "sweep_confirmed": True,
    "is_value_aligned": True,
    "htf_conflict": False,
    # alignment 75 - 10 counter penalty + 8 sweep + 5 value + 5 London = 83 → A (not A+, needs 85)
    "expected_grade": "A",
    "expected_risk_pct": 1.0,
    "expected_reason_contains": "counter",
}

# ── Scenario G — Ranging regime, liquidity weights dominate ──────────────────
SCENARIO_G = {
    "label": "Ranging market (ADX=14) — liquidity weight 0.28, HTF weight 0.12",
    "regime": "RANGING",
    "adx": 14,
    "expected_liquidity_weight": 0.28,
    "expected_htf_weight": 0.12,
    "expected_trade_type": "intraday",
}

# ── Scenario H — Tokyo session caps grade ─────────────────────────────────────
SCENARIO_H = {
    "label": "Tokyo session — alignment capped at 69, grade max A (never A+)",
    "session": "Tokyo",
    "raw_alignment": 90,
    "quality": "HIGH",
    "event_risk": False,
    "is_counter_trend": False,
    "expected_grade": "A",          # capped — not A+
    "expected_risk_pct": 1.0,
    "expected_max_alignment": 69,
    "expected_trigger_blocked": True,
    "expected_failing_condition": "session_valid",
}

# ── Scenario I — Spread wipes R:R below minimum ───────────────────────────────
SCENARIO_I = {
    "label": "Stop 30 pips, target 45 pips — after 4-pip spread R:R is 1.21, below 1.5 min",
    "stop_pips": 30,
    "target_pips": 45,
    "spread_pips": 4,
    "raw_rr": 1.5,            # 45/30 — looks fine before spread
    "effective_stop": 34,     # 30 + 4
    "effective_target": 41,   # 45 - 4
    "effective_rr": 1.21,     # 41/34
    "min_rr": 1.5,
    "expected_rr_below_minimum": True,
    "expected_trigger_blocked": True,
    "expected_failing_condition": "rr_clears_minimum",
}

# ── Scenario J — Auto-label WIN ───────────────────────────────────────────────
SCENARIO_J = {
    "label": "BEARISH bias at 2.0300, 24h close 2.0078 (222 pips down) → WIN",
    "run_price": 2.0300,
    "run_bias": "BEARISH",
    "close_24h": 2.0078,
    "pips_moved": 222,
    "direction": "with_bias",
    "win_threshold_pips": 20,
    "expected_label": "WIN",
    "expected_framework_was_right": "YES",
}

# ── Scenario K — Auto-label NEUTRAL ──────────────────────────────────────────
SCENARIO_K = {
    "label": "BULLISH bias at 2.0300, 24h close 2.0315 (15 pips up) → NEUTRAL",
    "run_price": 2.0300,
    "run_bias": "BULLISH",
    "close_24h": 2.0315,
    "pips_moved": 15,
    "direction": "with_bias",
    "win_threshold_pips": 20,
    "expected_label": "NEUTRAL",   # 15 pips < 20 pip threshold
    "expected_framework_was_right": "NO",
}

# ── Scenario L — COT extreme positioning flips bias ──────────────────────────
SCENARIO_L = {
    "label": "GBP 85th percentile long (extreme) — COT flips from BULLISH to BEARISH contrarian",
    "cot_data": {
        "pair_bias": "BULLISH",    # normal read before extreme check
        "gbp_extreme": True,
        "aud_extreme": False,
        "gbp_net": 45_000,
        "aud_net": -30_000,
        "error": None,
        "report_date": "2026-06-06",
    },
    "expected_bias": "BEARISH",    # flipped
    "expected_raw_score": -50,     # flipped from +50
    "expected_summary_contains": "CONTRARIAN",
}
