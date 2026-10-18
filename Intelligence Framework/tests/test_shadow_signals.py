"""
test_shadow_signals.py

Pins each frozen candidate's trigger with synthetic data — fires on exact
conditions, silent otherwise. Exact values, not bounds.

Run: pytest tests/test_shadow_signals.py
"""
from datetime import datetime, timezone

import pytest

import shadow_signals as ss


def _ctx(**over):
    n = 40
    base = {
        "O": [1.9000] * n, "H": [1.9010] * n, "L": [1.8990] * n, "C": [1.9000] * n,
        "T": [datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)] * n,
        "atr": [0.0010] * n, "pip": 0.0001,
        "adx": 20.0, "adx_slope": 0.0, "struct": "TRANSITIONAL",
        "sd": {"latest_sl": 1.8950, "latest_sh": 1.9050},
    }
    base.update(over)
    return base


# ── EARLY_MOMENTUM (GBP/JPY only) ──────────────────────────────────────────────

def test_early_momentum_fires_long():
    ctx = _ctx(adx=20.0, struct="UPTREND",
               C=[217.0] * 40, atr=[0.5] * 40,
               sd={"latest_sl": 216.0, "latest_sh": 218.0})
    s = ss.check_early_momentum_v2("GBP_JPY", ctx)
    assert s is not None
    assert s["direction"] == "LONG"
    assert s["entry"] == 217.0
    assert s["stop"] == 216.0            # opposite side = last swing low


def test_early_momentum_silent_adx_too_high():
    assert ss.check_early_momentum_v2("GBP_JPY", _ctx(adx=25.0, struct="UPTREND")) is None


def test_early_momentum_silent_adx_too_low():
    assert ss.check_early_momentum_v2("GBP_JPY", _ctx(adx=17.9, struct="UPTREND")) is None


def test_early_momentum_silent_no_structure():
    assert ss.check_early_momentum_v2("GBP_JPY", _ctx(adx=20.0, struct="TRANSITIONAL")) is None


def test_early_momentum_silent_wrong_instrument():
    assert ss.check_early_momentum_v2("GBP_AUD", _ctx(adx=20.0, struct="UPTREND")) is None


# ── EARLY_MOMENTUM_v2 stop-validity guard (the ONE change from v1) ─────────────
# v1's defect geometry, pinned from the graded 2026-07-29/30 rows: SHORT with
# the stale swing high BELOW entry. v2 must be silent there — no ATR fallback.

def test_em_v2_fires_under_new_id():
    ctx = _ctx(adx=20.0, struct="UPTREND",
               C=[217.0] * 40, atr=[0.5] * 40,
               sd={"latest_sl": 216.0, "latest_sh": 218.0})
    s = ss.check_early_momentum_v2("GBP_JPY", ctx)
    assert s is not None
    assert s["candidate_id"] == "EARLY_MOMENTUM_v2"

def test_em_v2_guard_short_stale_swing_below_entry_no_fire():
    # entry 218.572 above stale swing high 217.996 — the July row-3 geometry
    ctx = _ctx(adx=20.8, struct="DOWNTREND",
               C=[218.572] * 40, atr=[0.37] * 40,
               sd={"latest_sl": 215.0, "latest_sh": 217.996})
    assert ss.check_early_momentum_v2("GBP_JPY", ctx) is None

def test_em_v2_guard_short_swing_at_entry_no_fire():
    ctx = _ctx(adx=20.0, struct="DOWNTREND",
               C=[218.0] * 40, atr=[0.37] * 40,
               sd={"latest_sl": 215.0, "latest_sh": 218.0})
    assert ss.check_early_momentum_v2("GBP_JPY", ctx) is None

def test_em_v2_guard_long_stale_swing_above_entry_no_fire():
    ctx = _ctx(adx=20.0, struct="UPTREND",
               C=[216.0] * 40, atr=[0.37] * 40,
               sd={"latest_sl": 216.5, "latest_sh": 219.0})
    assert ss.check_early_momentum_v2("GBP_JPY", ctx) is None

def test_em_v2_valid_short_still_fires():
    # the July row-1 geometry: swing high ABOVE entry — real adverse room
    ctx = _ctx(adx=20.0, struct="DOWNTREND",
               C=[217.667] * 40, atr=[0.34] * 40,
               sd={"latest_sl": 214.0, "latest_sh": 217.996})
    s = ss.check_early_momentum_v2("GBP_JPY", ctx)
    assert s is not None
    assert s["direction"] == "SHORT"
    assert s["stop"] == 217.996

def test_em_v2_no_swing_keeps_atr_fallback():
    # v1 behavior preserved: missing swing = entry +/- 1.5*ATR (adverse side)
    ctx = _ctx(adx=20.0, struct="DOWNTREND",
               C=[217.0] * 40, atr=[0.5] * 40,
               sd={"latest_sl": None, "latest_sh": None})
    s = ss.check_early_momentum_v2("GBP_JPY", ctx)
    assert s is not None
    assert s["stop"] == 217.75            # 217.0 + 1.5 * 0.5

def test_em_v2_guarded_no_fire_writes_no_ledger_row(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ctx = _ctx(adx=20.8, struct="DOWNTREND",
               C=[218.572] * 40, atr=[0.37] * 40,
               sd={"latest_sl": 215.0, "latest_sh": 217.996})
    ss.log_shadow_signals(ss.check_shadow_signals("GBP_JPY", ctx))
    import os
    assert not os.path.exists(ss.LOG_FILE)   # nothing fired, nothing written


# ── MOMENTUM_JOIN (both) ───────────────────────────────────────────────────────

def _mj_ctx(**over):
    H = [1.9000 + i * 0.0001 for i in range(40)]   # rising → H[-1] is the 12-bar high
    ctx = _ctx(adx=35.0, adx_slope=10.0, struct="UPTREND",
               H=H, C=[1.9000] * 40, atr=[0.0010] * 40)
    ctx.update(over)
    return ctx


def test_momentum_join_fires_long():
    s = ss.check_momentum_join("GBP_AUD", _mj_ctx())
    assert s is not None and s["direction"] == "LONG"
    assert s["entry"] == 1.9000
    assert s["stop"] == pytest.approx(1.9000 - 1.5 * 0.0010)   # 1.5*ATR stop


def test_momentum_join_silent_adx_below_30():
    assert ss.check_momentum_join("GBP_AUD", _mj_ctx(adx=29.9)) is None


def test_momentum_join_silent_slope_below_8():
    assert ss.check_momentum_join("GBP_AUD", _mj_ctx(adx_slope=7.9)) is None


def test_momentum_join_silent_not_new_extreme():
    # flat highs → H[-1] is not a strict new 12-bar high beyond the rest
    assert ss.check_momentum_join("GBP_AUD",
                                  _mj_ctx(H=[1.9010] * 39 + [1.9005])) is None


# ── THRUST_PULLBACK (both) ─────────────────────────────────────────────────────

def _thrust_series():
    n = 32
    O = [1.9000] * n; H = [1.9010] * n; L = [1.8990] * n; C = [1.9000] * n
    # break at b=21 (box = bars 3..20, tight [1.8990,1.9010]); body 1.5*ATR
    O[21], C[21], H[21], L[21] = 1.9015, 1.9030, 1.9032, 1.9014
    # pullback near the broken edge (1.9010) at bar 25
    L[25], C[25] = 1.9012, 1.9015
    # bar n-2 closes at/below edge, bar n-1 closes back above (fresh cross)
    C[30], H[30], L[30] = 1.9008, 1.9012, 1.9006
    O[31], C[31], H[31], L[31] = 1.9010, 1.9020, 1.9022, 1.9008
    return _ctx(O=O, H=H, L=L, C=C, atr=[0.0010] * n,
                T=[datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)] * n)


def test_thrust_pullback_fires_long():
    s = ss.check_thrust_pullback("GBP_AUD", _thrust_series())
    assert s is not None and s["direction"] == "LONG"
    assert s["entry"] == 1.9020            # the close-back bar
    assert s["stop"] == 1.8990             # opposite box edge (box_lo)


def test_thrust_pullback_silent_no_break():
    # a flat box that never breaks → no signal
    ctx = _ctx(O=[1.9000] * 32, H=[1.9010] * 32, L=[1.8990] * 32,
               C=[1.9000] * 32, atr=[0.0010] * 32)
    assert ss.check_thrust_pullback("GBP_AUD", ctx) is None


# ── Idempotency + episode counting (automation guardrails) ─────────────────────

def test_idempotent_double_eval_no_duplicate_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ctx = _ctx(adx=20.0, struct="UPTREND", C=[217.0] * 40, atr=[0.5] * 40,
               sd={"latest_sl": 216.0, "latest_sh": 218.0})
    # Evaluate + log the SAME bar twice — dedup by candidate+instrument+timestamp.
    for _ in range(2):
        ss.log_shadow_signals(ss.check_shadow_signals("GBP_JPY", ctx))
    import csv as _csv
    with open(ss.LOG_FILE) as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "EARLY_MOMENTUM_v2"


def test_episode_count_collapses_overlapping_horizons(tmp_path, monkeypatch):
    from datetime import datetime, timezone, timedelta
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    t0 = datetime(2026, 1, 5, 1, 0, 0, tzinfo=timezone.utc)

    def sig(ts):
        return {"candidate_id": "EARLY_MOMENTUM",
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "instrument": "GBP_JPY", "direction": "LONG",
                "entry": 217.0, "stop": 216.0, "atr": 0.5,
                "adx": 20.0, "adx_slope": 0.0, "structure": "UPTREND", "extra": ""}

    # 3 fires within the 30-bar (120h) horizon of t0 → ONE episode; +200h → new
    ss.log_shadow_signals([sig(t0), sig(t0 + timedelta(hours=4)),
                           sig(t0 + timedelta(hours=8)), sig(t0 + timedelta(hours=200))])
    assert ss.get_shadow_tally("EARLY_MOMENTUM", "GBP_JPY")["logged"] == 4   # rows
    assert ss.episode_count("EARLY_MOMENTUM", "GBP_JPY") == 2                # episodes
