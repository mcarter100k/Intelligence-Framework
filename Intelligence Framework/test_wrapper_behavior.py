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
import json
import os
import shutil
import subprocess
import textwrap
import time

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
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


def _heartbeat_project(tmp_path, storylines_age_h=1, health=None):
    proj = _project(tmp_path, storylines_age_h=storylines_age_h)
    y = _yesterday()
    for kind in ("brief", "outcomes"):
        (proj / "logs" / f"{kind}_{y}.log").write_text("===== run =====\nok\n")
    if health is not None:
        (proj / "logs" / "health_state.json").write_text(json.dumps(health))
    return proj


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
