"""
test_safe_writes.py — every evidence writer, under real concurrency
(docs/specs/safe_ledger_writes_spec.md). Each defect here was reproduced
on main before the fix (validation_log, Phase 3).

The race tests run the REAL grader in-process and, at the moment it starts
writing its rewrite (after its read, before its rows), start a REAL second
process that appends with the REAL append function. Both the grader's own
update and the other process's row must survive.
"""
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import time

import pandas as pd
import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))


def _rows(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def _race(ledger, appender_code, run_grader, monkeypatch):
    real_wh = csv.DictWriter.writeheader
    state = {"proc": None}

    def hooked(self):
        if state["proc"] is None:
            state["proc"] = subprocess.Popen(
                [sys.executable, "-c", textwrap.dedent(appender_code)],
                env=dict(os.environ, PYTHONPATH=_ROOT, PYTHONDONTWRITEBYTECODE="1"))
            time.sleep(0.7)
        return real_wh(self)

    monkeypatch.setattr(csv.DictWriter, "writeheader", hooked)
    result = run_grader()
    monkeypatch.setattr(csv.DictWriter, "writeheader", real_wh)
    assert state["proc"] is not None, "the grader never wrote: race not exercised"
    assert state["proc"].wait(timeout=60) == 0, "the concurrent appender failed"
    return result


# ── B1: graders keep a concurrent append AND their own update ─────────────────

def test_shadow_grader_under_a_concurrent_append(tmp_path, monkeypatch):
    import oanda_feed
    import shadow_signals as ss
    p = str(tmp_path / "shadow_signal_log.csv")
    idx = pd.date_range("2026-09-01T01:00:00Z", periods=40, freq="4h")
    df = pd.DataFrame({"Open": 1.9, "High": 1.91, "Low": 1.899, "Close": 1.905}, index=idx)
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: True)
    monkeypatch.setattr(oanda_feed, "get_h4_bars", lambda **k: df)
    monkeypatch.setattr(ss, "LOG_FILE", p)
    ss.log_shadow_signals([{"candidate_id": "MOMENTUM_JOIN", "timestamp": idx[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "instrument": "GBP_AUD", "direction": "LONG", "entry": "1.9",
                            "stop": "1.89", "atr": "0.01", "adx": "35", "adx_slope": "9",
                            "structure": "UPTREND", "extra": ""}])
    appender = f"""
        import shadow_signals as ss
        ss.LOG_FILE = {p!r}
        ss.log_shadow_signals([{{"candidate_id": "MOMENTUM_JOIN", "timestamp": "2099-01-01T00:00:00Z",
            "instrument": "GBP_JPY", "direction": "LONG", "entry": "200", "stop": "199",
            "atr": "1", "adx": "30", "adx_slope": "9", "structure": "UPTREND",
            "extra": "FROM_OTHER_PROCESS"}}])
    """
    filled = _race(p, appender, lambda: ss.grade_pending_shadow("GBP_AUD"), monkeypatch)
    rows = _rows(p)
    assert filled == 1
    assert rows[0]["outcome_filled"] == "True"                    # grader's update
    assert any(r["extra"] == "FROM_OTHER_PROCESS" for r in rows)  # the append


_REGIME_ROW = {"log_id": "T_GBP_AUD", "timestamp": "2026-06-28T23:19:58Z", "instrument": "GBP_AUD",
               "regime_d1": "VOLATILE", "regime_h4": "TRENDING_UP", "composite_regime": "VOLATILE",
               "execution_mode": "STAND_DOWN", "confidence": "HIGH", "size_mult": "1.0",
               "adx_d1": "28.5", "adx_h4": "31.2", "atr_ratio": "1.1", "structure_d1": "UPTREND",
               "weekly_context": "ESTABLISHED_UPTREND", "timeframe_conflict": "False",
               "stand_down": "True", "price_at_log": "1.91", "atr_pips_at_log": "95.0",
               "prediction_type": "VOL_EXPANSION", "prediction_window": "8",
               "outcome_filled": "False"}


def test_regime_grader_under_a_concurrent_append(tmp_path, monkeypatch):
    import regime_classifier_logger as rcl
    p = str(tmp_path / "regime_classification_log.csv")
    monkeypatch.setattr(rcl, "LOG_FILE", p)
    rcl._write_row({k: _REGIME_ROW.get(k, "") for k in rcl.FIELDNAMES})
    idx = pd.date_range("2026-06-29", periods=60, freq="D", tz="UTC")
    closes = [1.91 + i * 0.001 for i in range(60)]
    appender = f"""
        import regime_classifier_logger as rcl
        rcl.LOG_FILE = {p!r}
        row = {{k: "" for k in rcl.FIELDNAMES}}
        row.update(log_id="FROM_OTHER_PROCESS", timestamp="2099-01-01T00:00:00Z",
                   instrument="GBP_JPY", outcome_filled="False")
        rcl._write_row(row)
    """
    filled = _race(p, appender, lambda: rcl.check_pending_outcomes(
        "GBP_AUD", closes, [c + 0.002 for c in closes], [c - 0.002 for c in closes], idx),
        monkeypatch)
    rows = _rows(p)
    assert filled == 1 and rows[0]["outcome_filled"] == "True"
    assert any(r["log_id"] == "FROM_OTHER_PROCESS" for r in rows)


def test_trade_grader_under_a_concurrent_append(tmp_path, monkeypatch):
    import trade_outcome_logger as tol
    p = str(tmp_path / "trade_signal_log.csv")
    monkeypatch.setattr(tol, "_LOG_FILE", p)
    tol.log_signal({"regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "current_price": 1.91},
                   {"direction": "LONG", "grade": "A", "conviction": 72, "size_mult": 1.0},
                   "GBP_AUD")
    first_ts = _rows(p)[0]["timestamp"]
    idx = pd.date_range(pd.Timestamp(first_ts).floor("D"), periods=60, freq="D")
    closes = [1.91 + i * 0.001 for i in range(60)]
    appender = f"""
        import trade_outcome_logger as tol
        tol._LOG_FILE = {p!r}
        tol.log_signal({{"regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "current_price": 200.0}},
                       {{"direction": "LONG", "grade": "B", "conviction": 50, "size_mult": 0.5}},
                       "GBP_JPY", entry_context="FROM_OTHER_PROCESS")
    """
    filled = _race(p, appender, lambda: tol.check_pending_trade_outcomes("GBP_AUD", closes, idx),
                   monkeypatch)
    rows = _rows(p)
    assert filled == 1 and rows[0]["outcome_filled"] == "True"
    assert any(r["entry_context"] == "FROM_OTHER_PROCESS" for r in rows)


# ── B3: the session log is append-only ────────────────────────────────────────

def test_session_log_keeps_rows_older_than_30_days(tmp_path, monkeypatch):
    import session_memory as sm
    p = str(tmp_path / "session_context_log.csv")
    monkeypatch.setattr(sm, "LOG_FILE", p)
    old = {k: "" for k in sm.FIELDNAMES}
    old.update(timestamp="2026-07-29T04:23:31Z", instrument="GBP_AUD")
    sm._append_row(old)
    sm.log_session_snapshot({"adx_d1": 20.0, "adx_h4": 25.0, "atr_vs_avg": 1.0,
                             "regime_d1": "VOLATILE", "regime_h4": "RANGING",
                             "structure": "TRANSITIONAL", "filter_allowed": False},
                            "GBP_AUD", market_open=True)
    stamps = [r["timestamp"] for r in _rows(p)]
    assert stamps[0] == "2026-07-29T04:23:31Z" and len(stamps) == 2


def test_a_failed_session_snapshot_is_reported_not_silent(tmp_path, monkeypatch, capsys):
    import session_memory as sm
    monkeypatch.setattr(sm, "LOG_FILE", str(tmp_path / "s.csv"))

    def boom(row):
        raise OSError("disk full (simulated)")
    monkeypatch.setattr(sm, "_append_row", boom)
    sm.log_session_snapshot({}, "GBP_AUD", market_open=True)     # never raises
    assert "session snapshot NOT logged for GBP_AUD: OSError: disk full" in capsys.readouterr().err


# ── B5: concurrent health updates ─────────────────────────────────────────────

def test_concurrent_health_updates_are_all_counted(tmp_path):
    state = str(tmp_path / "health_state.json")
    hs = os.path.join(_ROOT, "scripts", "health_state.py")
    code = textwrap.dedent(f"""
        import importlib.util
        s = importlib.util.spec_from_file_location("hs", {hs!r})
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        m.STATE_FILE = {state!r}
        m.record_failure("brief", "x")
    """)
    procs = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(30)]
    assert all(p.wait(timeout=60) == 0 for p in procs)
    assert json.load(open(state))["jobs"]["brief"]["consecutive_failures"] == 30


# ── B4: verified daily backups ────────────────────────────────────────────────

def _backup_module():
    s = importlib.util.spec_from_file_location(
        "backup_ledgers", os.path.join(_ROOT, "scripts", "backup_ledgers.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _evidence_project(tmp_path):
    proj = tmp_path / "proj"
    (proj / "logs").mkdir(parents=True)
    (proj / "regime_classification_log.csv").write_text("log_id\nA\n")
    (proj / "shadow_signal_log.csv").write_text("timestamp\n2026-09-01T00:00:00Z\n")
    (proj / "logs" / "health_state.json").write_text('{"jobs": {}}')
    return proj


def test_a_backup_copies_and_verifies_every_present_file(tmp_path):
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    line = bl.backup(str(proj), date="2026-09-30")
    day = proj / "backups" / "2026-09-30"
    assert line == ("backup 2026-09-30: 3 files, "
                    f"{sum((proj / f).stat().st_size for f in ('regime_classification_log.csv', 'shadow_signal_log.csv', 'logs/health_state.json'))} "
                    "bytes, all sha256 verified -> backups/2026-09-30")
    manifest = (day / "MANIFEST.txt").read_text().splitlines()
    for entry in manifest:
        parts = entry.split("\t")
        if parts[1] == "ABSENT":
            assert not (proj / parts[0]).exists()
            continue
        copy = day / parts[0].replace(os.sep, "__")
        assert hashlib.sha256(copy.read_bytes()).hexdigest() == parts[2]
        assert copy.read_bytes() == (proj / parts[0]).read_bytes()
    assert "trade_signal_log.csv\tABSENT" in manifest


def test_the_first_backup_of_a_day_is_never_overwritten(tmp_path):
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    bl.backup(str(proj), date="2026-09-30")
    (proj / "regime_classification_log.csv").write_text("log_id\nA\nB\n")
    assert "already taken" in bl.backup(str(proj), date="2026-09-30")
    assert (proj / "backups" / "2026-09-30" / "regime_classification_log.csv").read_text() == "log_id\nA\n"


def test_a_failed_backup_leaves_no_folder_that_looks_complete(tmp_path, monkeypatch):
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    calls = {"n": 0}
    real = bl.shutil.copy2

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full (simulated)")
        return real(src, dst)
    monkeypatch.setattr(bl.shutil, "copy2", flaky)
    with pytest.raises(OSError):
        bl.backup(str(proj), date="2026-09-30")
    assert not (proj / "backups" / "2026-09-30").exists()
    assert [p for p in os.listdir(proj / "backups") if not p.startswith(".")] == []


def test_backup_main_reports_failure_and_exits_zero(tmp_path, monkeypatch, capsys):
    bl = _backup_module()
    monkeypatch.setattr(bl, "backup", lambda *a, **k: (_ for _ in ()).throw(OSError("no space")))
    assert bl.main(["x"]) == 0
    assert capsys.readouterr().out.startswith("BACKUP FAILED: OSError: no space")
