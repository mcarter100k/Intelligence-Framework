"""
test_safe_writes.py — every evidence writer, under real concurrency
(docs/specs/safe_ledger_writes_spec.md). Each defect here was reproduced
on main before the fix (validation_log, Phase 3).

The race tests run the REAL grader in-process and, at the moment it starts
writing its rewrite (after its read, before its rows), start a REAL second
process that appends with the REAL append function. Both the grader's own
update and the other process's row must survive.
"""
from _paths import ROOT
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

from _paths import ROOT as _ROOT


def _rows(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def _race(ledger, appender_code, run_grader, monkeypatch):
    """Start a REAL second process that appends to `ledger` the instant the
    grader FINISHES READING it (when its read handle closes), and give it
    0.7s. That is exactly the stale-snapshot window of a read-modify-write:
    without a lock held from the read to the write, the append lands and the
    grader's write-back destroys it.

    (The first version triggered at the grader's header write, which sits
    inside the write's own lock; mutation testing showed removing the
    grader's outer lock did not fail it. Validation_log, Phase 3.)"""
    import builtins
    real_open = builtins.open
    base = os.path.basename(ledger)
    state = {"proc": None}

    def fire():
        if state["proc"] is None:
            state["proc"] = subprocess.Popen(
                [sys.executable, "-c", textwrap.dedent(appender_code)],
                env=dict(os.environ, PYTHONPATH=_ROOT, PYTHONDONTWRITEBYTECODE="1"))
            time.sleep(0.7)

    class _ReadHandle:
        def __init__(self, f):
            self._f = f
        def __getattr__(self, n):
            return getattr(self._f, n)
        def __iter__(self):
            return iter(self._f)
        def __enter__(self):
            self._f.__enter__()
            return self
        def __exit__(self, *a):
            r = self._f.__exit__(*a)
            fire()
            return r
        def close(self):
            self._f.close()
            fire()

    def hooked(file, mode="r", *a, **k):
        f = real_open(file, mode, *a, **k)
        if (state["proc"] is None and isinstance(file, (str, os.PathLike))
                and os.path.basename(os.fspath(file)) == base
                and not any(c in mode for c in "wax+")):
            return _ReadHandle(f)
        return f

    monkeypatch.setattr(builtins, "open", hooked)
    result = run_grader()
    monkeypatch.setattr(builtins, "open", real_open)
    assert state["proc"] is not None, "the grader never read the ledger: race not exercised"
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
    line = bl.backup(str(proj), stamp="2026-09-30T221500Z")
    day = proj / "backups" / "2026-09-30T221500Z"
    assert line == ("backup 2026-09-30T221500Z: 3 files, "
                    f"{sum((proj / f).stat().st_size for f in ('regime_classification_log.csv', 'shadow_signal_log.csv', 'logs/health_state.json'))} "
                    "bytes, all sha256 verified -> backups/2026-09-30T221500Z")
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


def test_every_run_gets_its_own_backup_and_none_is_ever_overwritten(tmp_path):
    """Review R1/R6: a daily slot keyed by UTC date let a late run take the
    next day's slot (so that day's grader ran with no fresh backup), and a
    delete-then-rename could destroy a complete backup."""
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    bl.backup(str(proj), stamp="2026-10-01T003000Z")          # late-firing run
    (proj / "regime_classification_log.csv").write_text("log_id\nA\nB\n")
    line = bl.backup(str(proj), stamp="2026-10-01T231500Z")   # next normal run
    assert line.startswith("backup 2026-10-01T231500Z:")
    assert (proj / "backups" / "2026-10-01T003000Z" / "regime_classification_log.csv").read_text() == "log_id\nA\n"
    assert (proj / "backups" / "2026-10-01T231500Z" / "regime_classification_log.csv").read_text() == "log_id\nA\nB\n"
    again = bl.backup(str(proj), stamp="2026-10-01T231500Z")   # same second: new folder
    assert again.startswith("backup 2026-10-01T231500Z-2:")
    assert (proj / "backups" / "2026-10-01T231500Z" / "regime_classification_log.csv").read_text() == "log_id\nA\nB\n"


def test_trade_log_is_backed_up(tmp_path):
    """Review R5: AGENTS.md lists trade_log.csv as evidence; it was omitted."""
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    (proj / "trade_log.csv").write_text("date,bias\n2026-04-02,BEARISH\n")
    bl.backup(str(proj), stamp="2026-09-30T221500Z")
    assert (proj / "backups" / "2026-09-30T221500Z" / "trade_log.csv").read_text() == \
        "date,bias\n2026-04-02,BEARISH\n"


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
        bl.backup(str(proj), stamp="2026-09-30T221500Z")
    assert not (proj / "backups" / "2026-09-30").exists()
    assert [p for p in os.listdir(proj / "backups") if not p.startswith(".")] == []


def test_backup_main_reports_failure_and_exits_zero(tmp_path, monkeypatch, capsys):
    bl = _backup_module()
    monkeypatch.setattr(bl, "backup", lambda *a, **k: (_ for _ in ()).throw(OSError("no space")))
    assert bl.main(["x"]) == 0
    assert capsys.readouterr().out.startswith("BACKUP FAILED: OSError: no space")


def test_a_corrupted_copy_fails_the_backup(tmp_path, monkeypatch):
    """The hash check must actually reject a bad copy; without this test the
    verification step could be deleted and every other backup test pass."""
    bl = _backup_module()
    proj = _evidence_project(tmp_path)
    real = bl.shutil.copy2

    def corrupting(src, dst):
        real(src, dst)
        with open(dst, "ab") as f:
            f.write(b"CORRUPTED")
    monkeypatch.setattr(bl.shutil, "copy2", corrupting)
    with pytest.raises(RuntimeError, match="hash mismatch"):
        bl.backup(str(proj), stamp="2026-09-30T221500Z")
    assert not (proj / "backups" / "2026-09-30").exists()



# ── review findings R3, R4 ────────────────────────────────────────────────────

def test_r4_appending_to_an_empty_shadow_log_writes_the_header(tmp_path, monkeypatch):
    import shadow_signals as ss
    p = tmp_path / "shadow_signal_log.csv"
    p.write_text("")                      # e.g. what B2's truncation left behind
    monkeypatch.setattr(ss, "LOG_FILE", str(p))
    ss.log_shadow_signals([{"candidate_id": "MOMENTUM_JOIN", "timestamp": "2026-01-01T00:00:00Z",
                            "instrument": "GBP_AUD", "direction": "LONG", "entry": "1",
                            "stop": "0.9", "atr": "1", "adx": "30", "adx_slope": "9",
                            "structure": "UPTREND", "extra": ""}])
    rows = _rows(str(p))
    assert len(rows) == 1 and rows[0]["candidate_id"] == "MOMENTUM_JOIN"


def _hs_module(state):
    s = importlib.util.spec_from_file_location("hs", os.path.join(_ROOT, "scripts", "health_state.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    m.STATE_FILE = state
    return m


def test_r3_a_save_error_never_swallows_the_alert(tmp_path, monkeypatch, capsys):
    import ledger_io
    hs = _hs_module(str(tmp_path / "h.json"))
    hs.record_failure("outcomes", "x")
    monkeypatch.setattr(ledger_io, "atomic_write_text",
                        lambda p, t, lock=True: (_ for _ in ()).throw(OSError("disk full")))
    hs.main(["x", "record-failure", "outcomes", "x"])
    out = capsys.readouterr()
    assert out.out.startswith("ALERT:OUTCOMES UNHEALTHY")
    assert "state NOT saved: OSError: disk full" in out.err


def test_r3_an_unavailable_lock_still_counts_once_and_says_so(tmp_path, monkeypatch, capsys):
    import ledger_io
    hs = _hs_module(str(tmp_path / "h.json"))

    def no_lock(path, timeout=60):
        raise ledger_io.LedgerLockTimeout("held elsewhere")
    monkeypatch.setattr(ledger_io, "locked", no_lock)
    hs.record_failure("brief", "x")
    assert json.load(open(tmp_path / "h.json"))["jobs"]["brief"]["consecutive_failures"] == 1
    assert "lock unavailable" in capsys.readouterr().err
