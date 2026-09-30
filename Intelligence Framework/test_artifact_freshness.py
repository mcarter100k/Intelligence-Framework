"""
test_artifact_freshness.py — regime_log_restore spec item 4a (pinned).

Silence must never mean "fine": every evidence artifact has an expected
cadence, and anything past it renders a STALE line that the wrapper turns
into a health FAILURE. The cadence table itself is pinned — changing an
expected cadence is a reviewed decision, not a drive-by edit.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "scripts"))
import artifact_freshness as af


def test_cadence_table_pinned():
    assert af.CADENCES == [
        ("regime_classification_log.csv", 72),
        ("session_context_log.csv",       72),
        ("calendar.csv",                 192),
        ("storylines.md",                216),
        ("shadow_signal_log.csv",        504),
        # Added 2026-09-16, evidence_loop_repair_spec.md Part 1: the ledger
        # sat at 2 lines from 2026-06-28 while run_outcome_check graded it
        # nightly, unwatched. 720h is generous on purpose — a directional
        # decision is NOT a daily event and an honest run of STAND ASIDE
        # days must not raise a health failure. trade_log.csv is NOT here:
        # it is frozen historical evidence, inventoried under
        # READ_SIDE_NO_CADENCE instead (see that table's reason).
        ("trade_signal_log.csv",         720),
    ]


def _touch(path, age_hours, now):
    with open(path, "w") as f:
        f.write("x")
    mtime = now - age_hours * 3600
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
    """D6: newest row 2000h old, file rewritten just now by a grader."""
    now = time.time()
    _ledger(os.path.join(str(tmp_path), "trade_signal_log.csv"), 2000, now,
            mtime_age_hours=0)
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "trade_signal_log" in ln][0]
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


def test_unparseable_rows_fall_back_to_file_time(tmp_path):
    now = time.time()
    _touch(os.path.join(str(tmp_path), "session_context_log.csv"), 5, now)
    line = [ln for ln in af.check(now=now, proj=str(tmp_path))
            if "session_context" in ln][0]
    assert line.startswith("fresh:") and "file time" in line


def test_a_due_human_file_never_renders_stale(tmp_path):
    """D5: the wrapper fails a run on ^STALE: only."""
    now = time.time()
    _touch(os.path.join(str(tmp_path), "storylines.md"), 5000, now)
    lines = af.check(now=now, proj=str(tmp_path))
    story = [ln for ln in lines if "storylines.md" in ln][0]
    assert story.startswith("DUE:") and not story.startswith("STALE:")
