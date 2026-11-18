"""
test_run_count.py — scripts/run_count.py, the heartbeat's EXPECTED vs ACTUAL
run count. A run that never happened fails nothing, so the health channel
could not see the 2026-09-12 -> 09-14 and 2026-10-06 -> 10-08 gaps.
"""
from _paths import ROOT
import os
import plistlib
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from _paths import ROOT as _ROOT
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import run_count  # noqa: E402

LA = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 10, 18, 19, 30, tzinfo=timezone.utc)      # Sun 12:30 PM PDT


def _plist(d, name, args, sci):
    with open(d / name, "wb") as f:
        plistlib.dump({"Label": name, "ProgramArguments": args,
                       "StartCalendarInterval": sci}, f)


def _schedule(tmp_path):
    a = tmp_path / "agents"
    a.mkdir()
    for p in os.listdir(os.path.join(_ROOT, "scripts", "launchd")):
        if p.endswith(".plist"):
            (a / p).write_bytes(open(os.path.join(_ROOT, "scripts", "launchd", p), "rb").read())
    return a


def _logs(tmp_path, kind, stamps):
    d = tmp_path / "proj" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{kind}_x.log", "a") as f:
        for s in stamps:
            f.write(f"===== {s} =====\nok\n")
    return str(tmp_path / "proj")


def test_the_installed_schedule_gives_21_brief_and_7_outcome_slots_a_week(tmp_path):
    sched = run_count.schedule(str(_schedule(tmp_path)))
    assert sorted(n for n, _ in sched["brief"]) == [
        "com.quis.intelligence.brief-asia.plist", "com.quis.intelligence.brief-london.plist",
        "com.quis.intelligence.brief-ny.plist"]            # ny passes "digest" last
    start = datetime(2026, 10, 11, 19, 30, tzinfo=timezone.utc)
    assert len(run_count.slots(sched["brief"], start, NOW - run_count.GRACE, LA)) == 21
    assert len(run_count.slots(sched["outcomes"], start, NOW - run_count.GRACE, LA)) == 7


def test_launchd_weekday_zero_and_seven_are_sunday(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    _plist(a, "com.quis.intelligence.x.plist", ["/bin/bash", "scheduled_brief.sh"],
           [{"Weekday": 0, "Hour": 9, "Minute": 0}, {"Weekday": 7, "Hour": 10, "Minute": 0}])
    s = run_count.slots(run_count.schedule(str(a))["brief"],
                        datetime(2026, 10, 12, tzinfo=timezone.utc), NOW, LA)
    assert [t.astimezone(LA).strftime("%a %H:%M") for t in s] == ["Sun 09:00", "Sun 10:00"]


def test_a_wildcard_schedule_is_a_loud_line_not_a_guess(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    _plist(a, "com.quis.intelligence.x.plist", ["/bin/bash", "scheduled_brief.sh"], {"Minute": 5})
    out = run_count.report(str(tmp_path), now=NOW, directory=str(a), tz=LA)
    assert out[0].startswith("runs: RUN COUNT UNAVAILABLE") and "wildcard" in out[0]


def test_an_unknown_header_zone_is_loud(tmp_path):
    proj = _logs(tmp_path, "brief", ["2026-10-17 07:30:00 XYZ"])
    out = run_count.report(proj, now=NOW, directory=str(_schedule(tmp_path)), tz=LA)
    assert out[0].startswith("runs: RUN COUNT UNAVAILABLE") and "XYZ" in out[0]


def test_counts_and_shortfall_on_header_stamps(tmp_path):
    full = [f"2026-10-{d:02d} {hm} PDT" for d in range(12, 19)
            for hm in ("02:30:05", "07:30:05", "18:00:05")]
    full = [s for s in full if s < "2026-10-18 12:30"]                 # 20 of them
    full.append("2026-10-11 18:00:05 PDT")                             # the 21st slot
    proj = _logs(tmp_path, "brief", full)
    _logs(tmp_path, "outcomes", [f"2026-10-{d:02d} 15:15:04 PDT"
                                 for d in range(12, 18)])              # 10-11 missing
    out = run_count.report(proj, now=NOW, directory=str(_schedule(tmp_path)), tz=LA)
    assert out[0] == ("runs (last 7d, launchd schedule): brief 21 expected / 21 on time / 21 ran; "
                      "outcomes 7 expected / 6 on time / 6 ran")
    assert out[1] == ("runs: SHORTFALL — outcomes 1 of 7 scheduled runs missing "
                      "or over 60 min late")


def test_a_slot_inside_the_grace_window_is_not_yet_expected(tmp_path):
    """A job that fired 15 minutes ago may still be running; its missing
    header is not a shortfall yet."""
    a = tmp_path / "a"
    a.mkdir()
    _plist(a, "com.quis.intelligence.x.plist", ["/bin/bash", "scheduled_brief.sh"],
           {"Hour": 12, "Minute": 15})                                 # 15 min before NOW
    _plist(a, "com.quis.intelligence.y.plist", ["/bin/bash", "scheduled_outcome_check.sh"],
           {"Hour": 12, "Minute": 15})
    proj = _logs(tmp_path, "brief", [f"2026-10-{d} 12:15:30 PDT" for d in range(12, 18)])
    _logs(tmp_path, "outcomes", [f"2026-10-{d} 12:15:30 PDT" for d in range(12, 18)])
    out = run_count.report(proj, now=NOW, directory=str(a), tz=LA)
    assert out == ["runs (last 7d, launchd schedule): brief 6 expected / 6 on time / 6 ran; "
                   "outcomes 6 expected / 6 on time / 6 ran"]


def test_catch_up_runs_at_wake_do_not_repay_missed_slots(tmp_path):
    """The real 2026-09-12 -> 09-14 shape: asleep from Sat 02:43, three
    catch-up runs at Mon 09:16. Counted, 21 runs met 21 slots; matched, the
    slots slept through stay missing."""
    week = [f"2026-09-{d:02d} {hm} PDT" for d in range(7, 15)
            for hm in ("02:30:05", "07:30:05", "18:00:05")]
    asleep = ("2026-09-12 07:30", "2026-09-14 09:16")
    kept = [s for s in week if not (asleep[0] <= s[:16] < asleep[1])]
    kept += ["2026-09-14 09:16:50 PDT"] * 3                         # catch-up at wake
    now = datetime(2026, 9, 14, 17, 30, tzinfo=timezone.utc)         # Mon 10:30 PDT
    proj = _logs(tmp_path, "brief", kept)
    _logs(tmp_path, "outcomes", [f"2026-09-{d:02d} 15:15:04 PDT" for d in range(7, 14)])
    out = run_count.report(proj, now=now, directory=str(_schedule(tmp_path)), tz=LA)
    assert out[0].startswith("runs (last 7d, launchd schedule): brief 21 expected / 14 on time / ")
    assert "brief 7 of 21 scheduled runs missing or over 60 min late" in out[1]



# ── Stopped jobs (owner ruling M1, 2026-11-17) ────────────────────────────────
GBP = {"com.quis.intelligence.brief-asia", "com.quis.intelligence.brief-london",
       "com.quis.intelligence.brief-ny", "com.quis.intelligence.outcomes"}


def test_disabled_jobs_are_not_expected_and_read_stopped(tmp_path):
    proj = _logs(tmp_path, "brief", [])
    out = run_count.report(proj, now=NOW, directory=str(_schedule(tmp_path)), tz=LA, disabled=GBP)
    assert "brief stopped (launchd job(s) disabled" in out[0] and "outcomes stopped" in out[0], out
    assert len(out) == 1 and "SHORTFALL" not in " ".join(out), out


def test_control_enabled_jobs_with_no_runs_are_a_shortfall(tmp_path):
    proj = _logs(tmp_path, "brief", [])
    out = run_count.report(proj, now=NOW, directory=str(_schedule(tmp_path)), tz=LA, disabled=set())
    assert "runs: SHORTFALL" in out[-1], out


def test_one_disabled_brief_job_drops_only_its_slots(tmp_path):
    proj = _logs(tmp_path, "brief", [])
    out = run_count.report(proj, now=NOW, directory=str(_schedule(tmp_path)), tz=LA,
                           disabled={"com.quis.intelligence.brief-london"})
    assert "brief 14 expected" in out[0], out              # 2 of 3 daily slots x 7 days
    assert "brief stopped" not in out[0], out


def test_parse_disabled_reads_launchctl_output():
    text = ('disabled services = {\n\t\t"com.quis.intelligence.heartbeat" => enabled\n'
            '\t\t"com.quis.intelligence.outcomes" => disabled\n'
            '\t\t"com.other.job" => true\n\t\t"com.x.y" => false\n}')
    assert run_count.parse_disabled(text) == {"com.quis.intelligence.outcomes", "com.other.job"}


def test_env_override_replaces_the_launchd_lookup(monkeypatch):
    monkeypatch.setenv("INTEL_LAUNCHD_DISABLED", "a.b, c.d")
    assert run_count.disabled_labels() == {"a.b", "c.d"}
    monkeypatch.setenv("INTEL_LAUNCHD_DISABLED", "")
    assert run_count.disabled_labels() == set()
