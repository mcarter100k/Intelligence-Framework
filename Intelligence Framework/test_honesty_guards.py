"""
test_honesty_guards.py

Pins the two honesty guards from docs/specs/honesty_repairs_spec.md:

  1. shadow invalid_spec guard — a row whose stop sits on the non-adverse
     side of entry is unscoreable by construction and is excluded from every
     tally, episode count, and brief display, and never scored as R.
  2. regime independent-state counting — back-to-back reruns of an unchanged
     market state count as ONE observation in accuracy tallies.

Fixtures are inline synthetic rows shaped like the 2026-09-08 first-grading
exhibit (SHORT with stale-swing stop below entry). The live ledgers are
never a test target.

Run: pytest test_honesty_guards.py
"""
from datetime import datetime, timezone, timedelta

import shadow_signals as ss
import regime_classifier_logger as rcl


# ── helpers ────────────────────────────────────────────────────────────────────

def _row(direction, entry, stop, ts="2026-07-29T05:00:00Z",
         cid="EARLY_MOMENTUM", inst="GBP_JPY", **over):
    r = {"candidate_id": cid, "timestamp": ts, "instrument": inst,
         "direction": direction, "entry": entry, "stop": stop, "atr": 0.35,
         "adx": 20.0, "adx_slope": 5.0, "structure": "DOWNTREND", "extra": ""}
    r.update(over)
    return r


# ── 1. the predicate itself, both directions, pinned ───────────────────────────

def test_invalid_spec_short_stop_below_entry():
    # the real defect shape: SHORT entered above a stale swing-high stop
    assert ss.is_invalid_spec(
        {"direction": "SHORT", "entry": "218.352", "stop": "217.996"}) is True

def test_invalid_spec_short_stop_at_entry():
    assert ss.is_invalid_spec(
        {"direction": "SHORT", "entry": "218.0", "stop": "218.0"}) is True

def test_valid_short_stop_above_entry():
    # the one valid 2026-07-29 row: 32.9 pips of real adverse room
    assert ss.is_invalid_spec(
        {"direction": "SHORT", "entry": "217.667", "stop": "217.996"}) is False

def test_invalid_spec_long_stop_above_entry():
    assert ss.is_invalid_spec(
        {"direction": "LONG", "entry": "216.0", "stop": "216.5"}) is True

def test_valid_long_stop_below_entry():
    assert ss.is_invalid_spec(
        {"direction": "LONG", "entry": "217.0", "stop": "216.0"}) is False

def test_unreadable_geometry_is_not_scoreable():
    assert ss.is_invalid_spec({"direction": "SHORT", "entry": "x", "stop": ""}) is True
    assert ss.is_invalid_spec({"direction": "", "entry": "1", "stop": "2"}) is True


# ── 2. exclusion from tally / episodes / pending display ───────────────────────

def _seed_mixed_ledger(tmp_path, monkeypatch):
    """One valid SHORT + two invalid (stop below entry) SHORTs, same shape as
    the graded 2026-07-29/30 EARLY_MOMENTUM rows."""
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ss.log_shadow_signals([
        _row("SHORT", 217.667, 217.996, ts="2026-07-29T05:00:00Z"),   # valid
        _row("SHORT", 218.352, 217.996, ts="2026-07-29T21:00:00Z"),   # invalid
        _row("SHORT", 218.572, 217.996, ts="2026-07-30T05:00:00Z"),   # invalid
    ])

def test_tally_excludes_invalid_rows(tmp_path, monkeypatch):
    _seed_mixed_ledger(tmp_path, monkeypatch)
    t = ss.get_shadow_tally("EARLY_MOMENTUM", "GBP_JPY")
    assert t["logged"] == 1          # not 3
    assert t["graded"] == 0

def test_episode_count_excludes_invalid_rows(tmp_path, monkeypatch):
    _seed_mixed_ledger(tmp_path, monkeypatch)
    assert ss.episode_count("EARLY_MOMENTUM", "GBP_JPY") == 1

def test_all_invalid_candidate_counts_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ss.log_shadow_signals([_row("SHORT", 218.352, 217.996)])
    assert ss.get_shadow_tally("EARLY_MOMENTUM", "GBP_JPY")["logged"] == 0
    assert ss.episode_count("EARLY_MOMENTUM", "GBP_JPY") == 0

def test_pending_display_skips_invalid_newest(tmp_path, monkeypatch):
    # newest pending row is invalid → the brief surfaces the older VALID one
    _seed_mixed_ledger(tmp_path, monkeypatch)
    p = ss.latest_pending_signal("GBP_JPY")
    assert p is not None
    assert p["entry"] == 217.667     # the valid row, not the newest row

def test_pending_display_none_when_only_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ss.log_shadow_signals([_row("SHORT", 218.572, 217.996)])
    assert ss.latest_pending_signal("GBP_JPY") is None


# ── 3. grader never scores an invalid row ──────────────────────────────────────

def test_grader_skips_invalid_rows_and_scores_valid(tmp_path, monkeypatch, capsys):
    import pandas as pd
    _seed_mixed_ledger(tmp_path, monkeypatch)

    # 40 real-shaped H4 bars from 2026-07-29T05:00Z; price collapses so the
    # valid SHORT both hits its stop early (high 218.1 > 217.996) and shows
    # a large favorable excursion — the noise-stop exhibit shape.
    idx = pd.date_range("2026-07-29T05:00:00Z", periods=40, freq="4h")
    df = pd.DataFrame({
        "Open":  [217.7] * 2 + [216.0] * 38,
        "High":  [218.1] * 2 + [216.5] * 38,
        "Low":   [217.3] * 2 + [210.0] * 38,
        "Close": [217.6] * 2 + [212.0] * 38,
    }, index=idx)

    import oanda_feed
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: True)
    monkeypatch.setattr(oanda_feed, "get_h4_bars",
                        lambda pair, count=500: df)

    filled = ss.grade_pending_shadow("GBP_JPY")
    out = capsys.readouterr().out
    assert filled == 1                                   # ONLY the valid row
    assert "2 invalid_spec shadow row(s) skipped" in out # loud, not silent

    import csv
    with open(ss.LOG_FILE) as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["outcome_filled"] == "True"           # valid row scored
    assert rows[0]["hit_stop"] == "True"
    assert rows[0]["r_multiple"] == "-1.0"
    assert rows[1]["outcome_filled"] == "False"          # invalid rows untouched
    assert rows[2]["outcome_filled"] == "False"
    assert rows[1]["r_multiple"] == "" and rows[2]["r_multiple"] == ""


# ── 4. regime independent-state counting ───────────────────────────────────────

def _reg_row(ts, price="1.9056", adx_d1="26.8", adx_h4="27.9",
             pred="MOMENTUM_WIN", window="20", correct="True",
             inst="GBP_AUD", regime="TRENDING_DOWN"):
    return {"log_id": f"{ts}_{inst}", "timestamp": ts, "instrument": inst,
            "composite_regime": regime, "prediction_type": pred,
            "prediction_window": window, "price_at_log": price,
            "adx_d1": adx_d1, "adx_h4": adx_h4,
            "outcome_filled": "True", "outcome_correct": correct}

def test_echo_runs_collapse_to_one_state():
    rows = [_reg_row("2026-07-29T04:31:42Z"),
            _reg_row("2026-07-29T04:32:05Z"),
            _reg_row("2026-07-29T05:26:24Z")]
    reps = rcl._independent_states(rows)
    assert len(reps) == 1
    assert reps[0]["timestamp"] == "2026-07-29T04:31:42Z"   # FIRST row kept

def test_distinct_snapshot_stays_separate():
    rows = [_reg_row("2026-07-29T04:31:42Z", adx_h4="28.3"),
            _reg_row("2026-07-29T05:16:54Z", adx_h4="27.9")]   # adx moved
    assert len(rcl._independent_states(rows)) == 2

def test_same_state_beyond_window_is_new_observation():
    rows = [_reg_row("2026-07-01T00:00:00Z", window="8"),
            _reg_row("2026-07-20T00:00:00Z", window="8")]      # 19d > 8d window
    assert len(rcl._independent_states(rows)) == 2

def test_accuracy_counts_states_not_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    rows = [_reg_row("2026-07-29T04:31:42Z", correct="False"),
            _reg_row("2026-07-29T04:32:05Z", correct="True"),   # echo — ignored
            _reg_row("2026-07-29T04:34:37Z", correct="True")]   # echo — ignored
    import csv
    with open(rcl.LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    acc = rcl.get_regime_accuracy(instrument="GBP_AUD")
    d = acc["TRENDING_DOWN"]
    assert d["n"] == 1 and d["n_raw"] == 3
    assert d["correct"] == 0            # the FIRST row's outcome, echoes ignored
    assert "[3 rows -> 1 independent]" in rcl.get_accuracy_report("GBP_AUD")

def test_live_ledger_shape_pinned_5_states_from_22_echoes():
    """The 2026-07-29 pending block: 22 rows, 5 distinct snapshots (inline
    fixture mirroring the audit's grouping — the live CSV is not read)."""
    shapes = [  # (n_rows, price, adx_d1, adx_h4, pred, window, inst)
        (3, "1.9056",  "26.8", "28.3", "MOMENTUM_WIN",  "20", "GBP_AUD"),
        (4, "1.9056",  "26.8", "27.9", "MOMENTUM_WIN",  "20", "GBP_AUD"),
        (6, "1.9056",  "26.8", "27.9", "VOL_EXPANSION", "8",  "GBP_AUD"),
        (3, "217.77",  "23.1", "16.8", "VOL_EXPANSION", "8",  "GBP_JPY"),
        (6, "217.77",  "23.1", "18.6", "VOL_EXPANSION", "8",  "GBP_JPY"),
    ]
    t0 = datetime(2026, 7, 29, 4, 31, 42, tzinfo=timezone.utc)
    rows, minute = [], 0
    for n, price, d1, h4, pred, win, inst in shapes:
        for _ in range(n):
            ts = (t0 + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append(_reg_row(ts, price=price, adx_d1=d1, adx_h4=h4,
                                 pred=pred, window=win, inst=inst))
            minute += 3
    assert len(rows) == 22
    assert len(rcl._independent_states(rows)) == 5
