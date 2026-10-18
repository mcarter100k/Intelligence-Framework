"""
test_wrapper_behavior.py — the scheduled wrappers, EXECUTED, not text-matched.

Each test builds a throwaway project from this repo's real scripts/, stubs
the Python target (decision_brief.py / run_outcome_check.py), and runs the
real wrapper under /bin/bash 3.2 (the interpreter launchd uses) with
/usr/bin/python3 on PATH (launchd's). Notifications go to a stub osascript
that records its arguments; HOME is fake so no real notifier is ever used.

Why: the old tests only checked that certain strings appeared in the wrapper
source. They stayed green while weekly_heartbeat.sh could not even be parsed,
and none of them could see the Phase 2 defects (docs/specs/visible_failures_spec.md
D1-D5), each of which is pinned here by running the real script.
"""
from _paths import ROOT
import json
import re
import os
import shutil
import subprocess
import textwrap
import time

import pytest

from _paths import ROOT as _ROOT
pytestmark = pytest.mark.skipif(
    not (os.path.exists("/bin/bash") and os.path.exists("/usr/bin/python3")),
    reason="needs launchd's /bin/bash and /usr/bin/python3")

_LEDGERS = ["regime_classification_log.csv", "session_context_log.csv",
            "shadow_signal_log.csv", "trade_signal_log.csv"]

CRASH = """
    import sys
    sys.stderr.write('Traceback (most recent call last):\\n  File "x", line 1\\n'
                     'ZeroDivisionError: boom\\n')
    sys.exit(1)
"""
STAND_ASIDE = """
    print('GBP/AUD\\n  DECISION     STAND ASIDE — conditions not right to trade')
"""


def _project(tmp_path, brief=STAND_ASIDE, outcome="print('graded 0')",
             storylines_age_h=1):
    proj = tmp_path / "proj"
    (proj / "logs").mkdir(parents=True)
    shutil.copytree(os.path.join(_ROOT, "scripts"), proj / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "launchd"))
    # scripts/health_state.py and backup_ledgers.py import the root-level
    # ledger_io (docs/specs/safe_ledger_writes_spec.md)
    shutil.copy(os.path.join(_ROOT, "ledger_io.py"), proj / "ledger_io.py")
    now = time.time()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
    for name in _LEDGERS:
        (proj / name).write_text(f"timestamp,x\n{stamp},1\n")
    (proj / "calendar.csv").write_text("time,currency,event,actual,forecast,previous,impact\n")
    story = proj / "storylines.md"
    story.write_text("notes\n")
    old = now - storylines_age_h * 3600
    os.utime(story, (old, old))
    for name, body in (("decision_brief.py", brief),
                       ("run_outcome_check.py", outcome),
                       ("calendar_fetch.py", "print('calendar ok')")):
        (proj / name).write_text(textwrap.dedent(body))
    git = lambda *a: subprocess.run(["git", "-C", str(proj), *a], check=True,
                                    capture_output=True)
    git("init", "-q", "-b", "main")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "--allow-empty", "-m", "init")
    stub = tmp_path / "bin"
    stub.mkdir()
    notes = tmp_path / "notifications.txt"
    (stub / "osascript").write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{notes}"\n')
    (stub / "osascript").chmod(0o755)
    return proj


def _run(tmp_path, proj, wrapper, *args):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
           "INTEL_NO_ENV_FILE": "1", "INTEL_PROJ": str(proj)}
    r = subprocess.run(["/bin/bash", str(proj / "scripts" / wrapper), *args],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr           # exit-0 discipline, always


def _log(proj, kind):
    return "".join(p.read_text() for p in (proj / "logs").glob(f"{kind}_*.log"))


def _notes(tmp_path):
    p = tmp_path / "notifications.txt"
    return p.read_text() if p.exists() else ""


def _jobs(proj):
    p = proj / "logs" / "health_state.json"
    return json.loads(p.read_text())["jobs"] if p.exists() else {}


# ── D1-D5 (docs/specs/visible_failures_spec.md) ───────────────────────────────

def test_d1_grader_traceback_is_a_failure(tmp_path):
    proj = _project(tmp_path, outcome=CRASH)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    job = _jobs(proj)["outcomes"]
    assert job["consecutive_failures"] == 1
    assert job["last_failure_reason"] == "grader crashed (exit 1): ZeroDivisionError: boom"


def test_d2_brief_stderr_reaches_the_day_log(tmp_path):
    proj = _project(tmp_path, brief=STAND_ASIDE + """
    import sys
    sys.stderr.write('regime logger failed: disk full (non-fatal)\\n')
""")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "regime logger failed: disk full" in _log(proj, "brief")


def test_d3_brief_crash_is_logged_and_counted(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    log = _log(proj, "brief")
    assert "Traceback (most recent call last)" in log and "ZeroDivisionError" in log
    assert _jobs(proj)["brief"]["last_failure_reason"] == \
        "brief crashed (exit 1): ZeroDivisionError: boom"


def test_d4_grader_success_never_recovers_a_failing_brief(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    notes = _notes(tmp_path)
    assert "BRIEF UNHEALTHY" in notes
    assert "RECOVERED" not in notes
    assert _jobs(proj)["brief"]["consecutive_failures"] == 2


def test_d4_the_brief_recovers_only_on_its_own_success(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")
    (proj / "decision_brief.py").write_text(textwrap.dedent(STAND_ASIDE))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "RECOVERED: brief healthy again after 2 failed runs" in _notes(tmp_path)


def test_d5_a_due_human_file_never_fails_a_run(tmp_path):
    proj = _project(tmp_path, storylines_age_h=500)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _jobs(proj)["brief"]["consecutive_failures"] == 0
    assert "DUE: storylines.md" in _log(proj, "brief")
    assert "UNHEALTHY" not in _notes(tmp_path)


def test_a_stale_machine_ledger_still_fails_the_run(tmp_path):
    """D5 must not blunt the real alarm: a dead live writer still fails."""
    proj = _project(tmp_path)
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 200 * 3600))
    (proj / "regime_classification_log.csv").write_text(f"timestamp,x\n{old},1\n")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _jobs(proj)["brief"]["last_failure_reason"].startswith(
        "STALE: regime_classification_log.csv")


# ── notification routing (replaces the static source-text pins) ──────────────

def test_a_directional_decision_notifies_decision(tmp_path):
    proj = _project(tmp_path, brief="""
        print('GBP/AUD\\n  DECISION     SHORT — conditions line up')
    """)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "DECISION"' in _notes(tmp_path)


def test_a_shadow_signal_notifies_shadow(tmp_path):
    proj = _project(tmp_path, brief=STAND_ASIDE + """
    print('SHADOW SIGNALS\\n  MOMENTUM_JOIN LONG')
""")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "SHADOW"' in _notes(tmp_path)


def test_an_alert_line_notifies_alert_and_wins(tmp_path):
    proj = _project(tmp_path, brief="""
        import sys
        print('GBP/AUD\\n  DECISION     SHORT — x\\nSHADOW SIGNALS')
        sys.stderr.write('##ALERT## GBP/AUD regime flipped\\n')
    """)
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "ALERT"' in notes and "regime flipped" in notes


def test_a_quiet_stand_aside_notifies_nothing(tmp_path):
    proj = _project(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""


# ── market-status gate on DECISION (docs/specs/decision_channel_measurement_spec.md, Phase 0) ──
# Each brief here is RENDERED by the real producer (DecisionBrief.format with
# regime_detection._market_status's banner), not hand-typed, so a change to
# the banner wording or header layout fails these tests instead of silently
# disabling the gate. Week of 2026-10-11: 6 of 12 DECISION notifications
# fired with the market closed.

_SAT = (2026, 10, 17, 1, 12)      # Fri 6:12 PM PDT = Sat 01:12 UTC: closed
_WED = (2026, 10, 14, 15, 0)      # Wed 8:00 AM PDT: open


def _rendered(instrument, decision, when):
    from datetime import datetime, timezone
    import decision_brief as db
    from regime_detection import _market_status
    st = _market_status(_now=datetime(*when, tzinfo=timezone.utc))
    trade = decision in ("LONG", "SHORT")
    return db.DecisionBrief(
        instrument=instrument, timestamp="t", price=1.9189, atr_pips=100.9,
        decision=decision, reason="r", conviction=45 if trade else 0,
        grade="B" if trade else "C", size_pct=35 if trade else 0,
        market_state="m", invalidation="i", regime_log="l",
        stand_down=not trade, override_fired=False, execution_mode="X",
        adx_d1=19.0, adx_h4=33.0, weekly_context="W", error=None,
        market_open=st["open"], market_note=st["note"],
        entry_line="level 1.9189" if trade else "",
        target_line="set your own" if trade else "").format()


def _brief_printing(tmp_path, text, extra=""):
    """A stub decision_brief.py that prints `text` byte-for-byte (launchd's
    python3 may run with an ASCII stdout; the banner has an em dash)."""
    src = tmp_path / "rendered_brief.txt"
    src.write_bytes(text.encode("utf-8"))
    return (f"import sys\nsys.stdout.buffer.write(open({str(src)!r}, 'rb').read())\n"
            f"sys.stdout.flush()\n{extra}")


def test_g1_a_closed_market_decision_does_not_notify(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "SHORT", _SAT)
    assert "Market closed" in text and "DECISION     LONG" in text
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""
    assert "DECISION notification suppressed: market closed" in _log(proj, "brief")


def test_g2_an_open_market_decision_still_notifies(tmp_path):
    """Positive control: the gate is not a blanket mute."""
    text = _rendered("GBP_AUD", "LONG", _WED)
    assert "Market closed" not in text and "DECISION     LONG" in text
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "DECISION"' in notes and "GBP/AUD LONG" in notes
    assert "suppressed" not in _log(proj, "brief")


def test_g3_the_gate_is_per_instrument_and_keeps_closed_lines_out_of_the_summary(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "SHORT", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "DECISION"' in notes
    assert "GBP/JPY SHORT" in notes and "LONG" not in notes.split("→")[0]


def test_g4_a_flip_alert_still_fires_when_closed(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(
        tmp_path, text, "sys.stderr.write('##ALERT## GBP/AUD regime flipped\\n')\n"))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "ALERT"' in notes and "regime flipped" in notes


def test_g5_a_health_alert_still_fires_when_closed(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30 * 86400))
    (proj / "regime_classification_log.csv").write_text(f"timestamp,x\n{stale},1\n")
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")       # 2 consecutive failures notify
    notes = _notes(tmp_path)
    assert 'subtitle "ALERT"' in notes and 'subtitle "DECISION"' not in notes


def test_g6_a_shadow_signal_still_fires_when_closed_without_the_decision(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + "\nSHADOW SIGNALS\n  MOMENTUM_JOIN LONG\n"
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "SHADOW"' in notes and "MOMENTUM_JOIN" in notes
    assert "GBP/AUD LONG" not in notes and "DECISION LONG" not in notes


def test_g7_the_heartbeat_still_fires_after_a_closed_market_brief(tmp_path):
    proj = _heartbeat_project(tmp_path)
    text = _rendered("GBP_AUD", "LONG", _SAT)
    (proj / "decision_brief.py").write_text(_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert 'subtitle "HEARTBEAT"' in _notes(tmp_path)


def test_g8_the_digest_still_fires_when_closed(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    notes = _notes(tmp_path)
    assert 'subtitle "DIGEST"' in notes and 'subtitle "DECISION"' not in notes


def test_g10_a_decision_notification_names_its_pair(tmp_path):
    """The summary said a decision was issued but not for which pair."""
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_JPY", "SHORT", _WED)))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/JPY SHORT", msg


def test_g11_decisions_on_both_pairs_name_both(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _WED) + _rendered("GBP_JPY", "SHORT", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/AUD LONG · GBP/JPY SHORT", msg


def test_g12_shadow_lines_still_follow_the_named_decisions(tmp_path):
    text = (_rendered("GBP_JPY", "SHORT", _WED)
            + "\nSHADOW SIGNALS\n  MOMENTUM_JOIN   SHORT   fired\n")
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/JPY SHORT · MOMENTUM_JOIN SHORT fired", msg


def test_g9_the_wrapper_marker_is_the_producers_banner():
    """The wrapper greps prose because the brief has no machine marker
    (decision_brief.py is protected). Pin the exact string at both ends."""
    import re
    from datetime import datetime, timezone
    from regime_detection import _market_status
    src = open(os.path.join(_ROOT, "scripts", "scheduled_brief.sh"), encoding="utf-8").read()
    m = re.search(r"^CLOSED_MARKER='([^']+)'$", src, re.M)
    assert m, "scheduled_brief.sh must define CLOSED_MARKER='...'"
    marker = m.group(1)
    closed = _market_status(_now=datetime(*_SAT, tzinfo=timezone.utc))
    opened = _market_status(_now=datetime(*_WED, tzinfo=timezone.utc))
    assert closed["open"] is False and closed["note"].startswith(marker)
    assert opened["open"] is True and marker not in opened["note"]
    assert marker in _rendered("GBP_AUD", "LONG", _SAT)
    assert marker not in _rendered("GBP_AUD", "LONG", _WED)


def test_digest_is_sent_only_with_the_digest_argument(tmp_path):
    proj = _project(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "DIGEST" not in _notes(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert 'subtitle "DIGEST"' in _notes(tmp_path)


def test_graded_shadow_outcome_notifies_from_the_grader(tmp_path):
    """Pins the ROUTING only: a graded shadow outcome sends a SHADOW
    notification. The tally text comes from a heredoc that imports the real
    modules (pandas), which launchd's /usr/bin/python3 here cannot, so the
    tally's content is not asserted by this test."""
    proj = _project(tmp_path, outcome="print('GBP_JPY: 1 shadow-signal outcomes filled')")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert 'subtitle "SHADOW"' in _notes(tmp_path)


def test_no_graded_shadow_outcome_sends_no_shadow_notification(tmp_path):
    proj = _project(tmp_path, outcome="print('GBP_JPY: 0 trade-signal outcomes filled')")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert "SHADOW" not in _notes(tmp_path)


# ── code-review findings (visible_failures_spec addendum) ─────────────────────

def test_f1_grader_crash_reason_comes_from_stderr_not_stdout(tmp_path):
    """stdout printed before the crash, flushed only at exit, must never be
    named as the cause."""
    proj = _project(tmp_path, outcome="""
        import sys
        print('GBP_AUD: 3 regime outcomes filled')
        raise KeyError('instrument')
    """)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason == "grader crashed (exit 1): KeyError: 'instrument'"
    log = _log(proj, "outcomes")
    assert "GBP_AUD: 3 regime outcomes filled" in log and "KeyError" in log


def _yesterday():
    return subprocess.run(["/bin/bash", "-c",
                           "date -v-1d +%F 2>/dev/null || date -d yesterday +%F"],
                          capture_output=True, text=True).stdout.strip()


# The schedule as installed (scripts/launchd), written out independently of
# scripts/run_count.py so the heartbeat's expected-vs-actual line is checked
# against a fixture it did not generate.
_SLOTS = {"brief": ((2, 30), (7, 30), (18, 0)), "outcomes": ((15, 15),)}


def _local_zone():
    from zoneinfo import ZoneInfo
    real = os.path.realpath("/etc/localtime")
    return ZoneInfo(real.split("zoneinfo/", 1)[1])


def _write_week_of_runs(proj, skip=lambda kind, t: False):
    """One run header per scheduled slot over the last 8 days (UTC stamps);
    `skip` drops slots to simulate a scheduler gap. Returns the dropped count."""
    from datetime import datetime, timedelta, timezone
    tz, now, dropped = _local_zone(), datetime.now(timezone.utc), 0
    for back in range(8, -1, -1):
        day = (now.astimezone(tz) - timedelta(days=back)).date()
        for kind, hm in _SLOTS.items():
            for h, m in hm:
                t = datetime(day.year, day.month, day.day, h, m, tzinfo=tz).astimezone(timezone.utc)
                if t > now:
                    continue
                if skip(kind, t):
                    dropped += 1
                    continue
                p = proj / "logs" / f"{kind}_{day.isoformat()}.log"
                with open(p, "a") as f:
                    f.write(f"===== {t.strftime('%Y-%m-%d %H:%M:%S')} UTC =====\nok\n\n")
    return dropped


def _install_schedule(tmp_path):
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    for p in os.listdir(os.path.join(_ROOT, "scripts", "launchd")):
        if p.endswith(".plist"):
            shutil.copy(os.path.join(_ROOT, "scripts", "launchd", p), agents / p)


def _heartbeat_project(tmp_path, storylines_age_h=1, health=None, skip=None):
    proj = _project(tmp_path, storylines_age_h=storylines_age_h)
    _install_schedule(tmp_path)
    _write_week_of_runs(proj, **({"skip": skip} if skip else {}))
    if health is not None:
        (proj / "logs" / "health_state.json").write_text(json.dumps(health))
    return proj


def test_c1_the_heartbeat_reports_expected_vs_actual_runs(tmp_path):
    proj = _heartbeat_project(tmp_path)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    log = _log(proj, "heartbeat")
    assert re.search(r"runs \(last 7d, launchd schedule\): brief 21 expected / 21 on time / \d+ ran; "
                     r"outcomes 7 expected / 7 on time / \d+ ran", log), log
    assert "SHORTFALL" not in log
    assert "NEEDS ATTENTION" not in _notes(tmp_path)


def test_c1_a_scheduler_gap_is_a_shortfall_that_needs_attention(tmp_path):
    """The 2026-09-12 -> 09-14 shape: two days with no runs at all, and zero
    failures recorded, because nothing ran to fail."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    gap = (now - timedelta(days=4), now - timedelta(days=2))
    proj = _heartbeat_project(tmp_path, skip=lambda k, t: gap[0] <= t < gap[1],
                              health={"jobs": {"brief": {"consecutive_failures": 0},
                                               "outcomes": {"consecutive_failures": 0}}})
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes, log = _notes(tmp_path), _log(proj, "heartbeat")
    assert "runs: SHORTFALL" in log and "brief 6 of 21 scheduled runs missing or over 60 min late" in log, log
    assert "NEEDS ATTENTION" in notes and "SHORTFALL" in notes


def test_c1_no_installed_schedule_is_loud_not_a_pass(tmp_path):
    proj = _project(tmp_path)
    _write_week_of_runs(proj)                  # runs present, no plists installed
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert "schedule MISSING" in _log(proj, "heartbeat")
    assert "NEEDS ATTENTION" in _notes(tmp_path)


def test_f9_heartbeat_always_notifies_and_reports_healthy(tmp_path):
    proj = _heartbeat_project(tmp_path)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "HEARTBEAT"' in notes and "healthy |" in notes
    assert "NEEDS ATTENTION" not in notes


def test_f7_an_eight_day_old_storylines_is_not_needs_attention(tmp_path):
    """Old heartbeat: 'STALE (>7d)' tripped NEEDS ATTENTION at 8 days, inside
    the owner's 216h cadence."""
    proj = _heartbeat_project(tmp_path, storylines_age_h=8 * 24)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert "NEEDS ATTENTION" not in _notes(tmp_path)
    assert "STALE" not in _log(proj, "heartbeat")


def test_f7_a_past_due_storylines_is_a_due_reminder_not_attention(tmp_path):
    proj = _heartbeat_project(tmp_path, storylines_age_h=20 * 24)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    log = _log(proj, "heartbeat")
    assert "DUE (your 9-day cadence; a reminder)" in log
    assert "NEEDS ATTENTION" not in _notes(tmp_path)


def test_f9_heartbeat_surfaces_an_unhealthy_job_by_name(tmp_path):
    proj = _heartbeat_project(tmp_path, health={"jobs": {
        "brief": {"consecutive_failures": 0},
        "outcomes": {"consecutive_failures": 3,
                     "last_failure_reason": "grader crashed (exit 1): KeyError"}}})
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes = _notes(tmp_path)
    assert "NEEDS ATTENTION" in notes and "outcomes: UNHEALTHY" in notes


# ── Phase 3: nightly backup (docs/specs/safe_ledger_writes_spec.md) ───────────

def test_the_backup_runs_before_the_grader_rewrites_anything(tmp_path):
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    log = _log(proj, "outcomes")
    b = log.index("all sha256 verified -> backups/")
    assert b < log.index("GRADER RAN")
    days = [d for d in os.listdir(proj / "backups") if not d.startswith(".")]
    assert len(days) == 1
    day = proj / "backups" / days[0]
    assert (day / "regime_classification_log.csv").read_text() == \
        (proj / "regime_classification_log.csv").read_text()


def test_a_failed_backup_is_an_outcomes_failure_and_the_grader_does_not_run(tmp_path):
    """Review R2: the grader used to rewrite the ledgers anyway."""
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    (proj / "backups").write_text("a FILE where the backups folder must go")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason.startswith("BACKUP FAILED")
    log = _log(proj, "outcomes")
    assert "GRADER SKIPPED" in log and "GRADER RAN" not in log


def test_a_crashed_or_missing_backup_script_also_stops_the_grader(tmp_path):
    """Review R10: only a '^BACKUP FAILED' line used to count; a traceback or
    a missing script was recorded as success and the grader ran."""
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    (proj / "scripts" / "backup_ledgers.py").unlink()
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason.startswith("BACKUP FAILED: no success line")
    assert "GRADER RAN" not in _log(proj, "outcomes")
