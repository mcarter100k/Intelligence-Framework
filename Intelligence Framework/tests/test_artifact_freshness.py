"""
test_artifact_freshness.py — regime_log_restore spec item 4a (pinned).

Silence must never mean "fine": every evidence artifact has an expected
cadence, and anything past it renders a STALE line that the wrapper turns
into a health FAILURE. The cadence table itself is pinned — changing an
expected cadence is a reviewed decision, not a drive-by edit.
"""
from _paths import ROOT
import os
import sys
import time

sys.path.insert(0, os.path.join(ROOT,
                                "scripts"))
import artifact_freshness as af


def test_cadence_table_pinned():
    assert af.CADENCES == [
        ("regime_classification_log.csv", 72),
        ("session_context_log.csv",       72),
        ("calendar.csv",                 192),
        ("storylines.md",                216),
        ("shadow_signal_log.csv",        504),
        # Old -> new 2026-11-15 (alert_importance_spec N7): trade_signal_log.csv
        # had a 720h cadence here from 2026-09-16. With operating data it
        # failed every run from 2026-11-12 during an honest stand-aside month.
        # It is now watched by agreement_lines() (tests below). trade_log.csv
        # is frozen historical evidence under READ_SIDE_NO_CADENCE.
    ]


def _touch(path, age_hours, now):
    """An artifact `age_hours` old. Live ledgers are aged by their newest
    row (visible_failures_spec D6/F6), so they get a real timestamped row at
    that age. Other files are aged by mtime."""
    mtime = now - age_hours * 3600
    with open(path, "w") as f:
        if os.path.basename(path) in af.ROW_TIMESTAMPED:
            stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
            f.write(f"timestamp,x\n{stamp},1\n")
        else:
            f.write("x")
    os.utime(path, (mtime, mtime))


def test_fresh_and_stale_detection(tmp_path):
    now = time.time()
    proj = str(tmp_path)
    # regime log stale (100h > 72h), session log fresh, calendar fresh,
    # storylines past due (240h > 216h), shadow log fresh
    _touch(os.path.join(proj, "regime_classification_log.csv"), 100, now)
    _touch(os.path.join(proj, "session_context_log.csv"),         5, now)
    _touch(os.path.join(proj, "calendar.csv"),                   50, now)
    _touch(os.path.join(proj, "storylines.md"),                 240, now)
    _touch(os.path.join(proj, "shadow_signal_log.csv"),         100, now)

    lines = af.check(now=now, proj=proj)

    assert len(lines) == len(af.CADENCES)
    by_name = {ln.split(": ", 1)[1].split(" — ")[0]: ln for ln in lines}
    assert by_name["regime_classification_log.csv"].startswith("STALE:")
    assert "expected within 72h" in by_name["regime_classification_log.csv"]
    assert by_name["session_context_log.csv"].startswith("fresh:")
    assert by_name["calendar.csv"].startswith("fresh:")
    # Human-written: a DUE reminder, never a STALE run failure
    # (visible_failures_spec D5).
    assert by_name["storylines.md"].startswith("DUE:")
    assert by_name["shadow_signal_log.csv"].startswith("fresh:")


def test_missing_artifact_is_stale(tmp_path):
    lines = af.check(now=time.time(), proj=str(tmp_path))
    machine = [ln for ln in lines if "storylines.md" not in ln]
    assert all(ln.startswith("STALE:") and "MISSING" in ln for ln in machine)
    human = [ln for ln in lines if "storylines.md" in ln]
    assert human and human[0].startswith("DUE:") and "MISSING" in human[0]


def test_six_week_outage_would_have_fired(tmp_path):
    """Regression pin for the actual incident: a regime log 6 weeks old."""
    now = time.time()
    proj = str(tmp_path)
    for rel, _ in af.CADENCES:
        _touch(os.path.join(proj, rel), 1, now)
    _touch(os.path.join(proj, "regime_classification_log.csv"),
           6 * 7 * 24, now)
    stale = [ln for ln in af.check(now=now, proj=proj)
             if ln.startswith("STALE:")]
    assert len(stale) == 1
    assert "regime_classification_log.csv" in stale[0]


def test_check_never_raises_and_exits_zero(tmp_path):
    assert af.main(["af"]) == 0
    assert af.main(["af", "check"]) == 0
    assert af.main(["af", "bogus"]) == 0


# ── visible_failures_spec D5 / D6 ─────────────────────────────────────────────

def _ledger(path, row_age_hours, now, mtime_age_hours=0):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                          time.gmtime(now - row_age_hours * 3600))
    with open(path, "w") as f:
        f.write(f"timestamp,x\n{stamp},1\n")
    m = now - mtime_age_hours * 3600
    os.utime(path, (m, m))


def test_a_grader_rewrite_cannot_hide_a_dead_writer(tmp_path):
    """D6: newest row 2000h old, file rewritten just now by a grader.
    (Ledger changed from trade_signal_log to shadow_signal_log 2026-11-15:
    the former left CADENCES; the protection is unchanged.)"""
    now = time.time()
    _ledger(os.path.join(str(tmp_path), "shadow_signal_log.csv"), 2000, now,
            mtime_age_hours=0)
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "shadow_signal_log" in ln][0]
    assert line.startswith("STALE:") and "newest row" in line


def test_newest_row_not_last_line_decides(tmp_path):
    now = time.time()
    p = os.path.join(str(tmp_path), "regime_classification_log.csv")
    new = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 900 * 3600))
    with open(p, "w") as f:
        f.write(f"timestamp,x\n{new},1\n{old},2\n")
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "regime_classification" in ln][0]
    assert line.startswith("fresh:")


def test_f6_a_ledger_with_no_timestamped_rows_is_stale_not_file_time(tmp_path):
    """Review F6: falling back to mtime let a grader rewrite of a header-only
    ledger read as fresh, the hole D6 closed."""
    now = time.time()
    p = os.path.join(str(tmp_path), "shadow_signal_log.csv")   # was trade_signal_log (2026-11-15)
    with open(p, "w") as f:
        f.write("timestamp,x\n")                  # header only, mtime = now
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "shadow_signal" in ln][0]
    assert line.startswith("STALE:") and "no timestamped rows" in line


def test_non_ledger_files_still_use_file_time(tmp_path):
    now = time.time()
    _touch(os.path.join(str(tmp_path), "calendar.csv"), 5, now)
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "calendar" in ln][0]
    assert line.startswith("fresh:") and "file time" in line


def test_a_due_human_file_never_renders_stale(tmp_path):
    """D5: the wrapper fails a run on ^STALE: only."""
    now = time.time()
    _touch(os.path.join(str(tmp_path), "storylines.md"), 5000, now)
    lines = af.check(now=now, proj=str(tmp_path))
    story = [ln for ln in lines if "storylines.md" in ln][0]
    assert story.startswith("DUE:") and not story.startswith("STALE:")


# ── N7: the trade-signal writer is checked by agreement (alert_importance_spec) ──

def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _regime(path, rows):
    with open(path, "w") as f:
        f.write("timestamp,instrument,stand_down,logic_version\n")
        for t, inst, sd, ver in rows:
            f.write(f"{_iso(t)},{inst},{sd},{ver}\n")


def _trades(path, rows):
    with open(path, "w") as f:
        f.write("signal_id,timestamp,instrument\n")
        for t, inst in rows:
            f.write(f"x,{_iso(t)},{inst}\n")


def test_n7_a_trade_call_with_its_row_agrees(tmp_path):
    now = time.time()
    _regime(tmp_path / "regime_classification_log.csv",
            [(now - 3600, "GBP_JPY", "False", "p5-2026-09-30"),
             (now - 7200, "GBP_JPY", "True", "p5-2026-09-30")])
    _trades(tmp_path / "trade_signal_log.csv", [(now - 3600 + 5, "GBP_JPY")])
    assert af.agreement_lines(now=now, proj=str(tmp_path)) == [
        "agree: trade_signal_log.csv — all 1 trade calls in the last 720h have their row"]


def test_n7_a_trade_call_without_its_row_is_stale(tmp_path):
    """Positive control: the dead writer this check exists for."""
    now = time.time()
    _regime(tmp_path / "regime_classification_log.csv",
            [(now - 3600, "GBP_JPY", "False", "p5-2026-09-30")])
    _trades(tmp_path / "trade_signal_log.csv", [(now - 3600 + 1200, "GBP_JPY"),   # 20 min off
                                                (now - 3600, "GBP_AUD")])          # wrong pair
    line = af.agreement_lines(now=now, proj=str(tmp_path))[0]
    assert line.startswith("STALE: trade_signal_log.csv — 1 of 1 trade calls")


def test_n7_a_quiet_stand_aside_month_is_not_stale(tmp_path):
    now = time.time()
    _regime(tmp_path / "regime_classification_log.csv",
            [(now - h * 3600, "GBP_JPY", "True", "p5-2026-09-30") for h in range(1, 700, 8)])
    _trades(tmp_path / "trade_signal_log.csv", [(now - 900 * 3600, "GBP_JPY")])
    line = af.agreement_lines(now=now, proj=str(tmp_path))[0]
    assert line.startswith("agree:") and "no open-market trade call" in line


def test_n7_rows_before_the_logic_version_are_not_counted(tmp_path):
    """Before 2026-09-30 the filter could allow while the decision stood
    aside (10 real such rows in late September have no trade row)."""
    now = time.time()
    _regime(tmp_path / "regime_classification_log.csv",
            [(now - 3600, "GBP_JPY", "False", "")])
    _trades(tmp_path / "trade_signal_log.csv", [])
    assert af.agreement_lines(now=now, proj=str(tmp_path))[0].startswith("agree:")


def test_n7_rows_outside_the_window_are_not_counted(tmp_path):
    now = time.time()
    _regime(tmp_path / "regime_classification_log.csv",
            [(now - 800 * 3600, "GBP_JPY", "False", "p5-2026-09-30"),   # too old
             (now + 3600, "GBP_JPY", "False", "p5-2026-09-30")])        # in the future
    _trades(tmp_path / "trade_signal_log.csv", [])
    assert af.agreement_lines(now=now, proj=str(tmp_path))[0].startswith("agree:")


def test_n7_a_missing_regime_log_is_never_an_all_clear(tmp_path):
    line = af.agreement_lines(now=time.time(), proj=str(tmp_path))[0]
    assert line.startswith("unchecked:") and "missing" in line


def test_n7_a_crashing_check_fails_the_run(monkeypatch, capsys):
    """It used to print nothing, which the wrapper read as healthy."""
    def boom(*a, **k):
        raise RuntimeError("disk gone")
    monkeypatch.setattr(af, "check", boom)
    assert af.main(["x", "check"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("STALE: artifact_freshness — the check itself failed (RuntimeError: disk gone)")



# ── Stopped writers (owner ruling M1, 2026-11-17; AGENTS rule 8) ──────────────
def test_a_ledger_whose_writer_is_stopped_reads_stopped_never_stale(tmp_path):
    now = time.time()
    lines = af.check(now=now, proj=str(tmp_path),
                     stopped={"brief": ["com.quis.intelligence.brief-asia"]})
    for rel in ("regime_classification_log.csv", "session_context_log.csv", "shadow_signal_log.csv"):
        assert any(ln.startswith(f"stopped: {rel}") for ln in lines), lines
        assert not any(ln.startswith(f"STALE: {rel}") for ln in lines), lines
    assert any(ln.startswith("STALE: calendar.csv") for ln in lines), lines   # not a brief ledger


def test_control_the_same_missing_ledgers_are_stale_when_the_writer_runs(tmp_path):
    lines = af.check(now=time.time(), proj=str(tmp_path), stopped={})
    for rel in ("regime_classification_log.csv", "session_context_log.csv", "shadow_signal_log.csv"):
        assert any(ln.startswith(f"STALE: {rel}") for ln in lines), lines
