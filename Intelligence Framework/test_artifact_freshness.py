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
    # storylines stale (240h > 216h), shadow log fresh
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
    assert by_name["storylines.md"].startswith("STALE:")
    assert by_name["shadow_signal_log.csv"].startswith("fresh:")


def test_missing_artifact_is_stale(tmp_path):
    lines = af.check(now=time.time(), proj=str(tmp_path))
    assert all(ln.startswith("STALE:") and "MISSING" in ln for ln in lines)


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
