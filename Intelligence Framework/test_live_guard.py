"""
test_live_guard.py — scheduled runs must flag a live checkout that is not on main.

From 2026-09-16 to 2026-09-29 launchd ran an unmerged branch for 13 days
unnoticed (2026-09-29 audit). scripts/live_guard.sh is sourced by every
scheduled wrapper; these tests drive it under /bin/bash against throwaway
git repos, with `notify` stubbed so no real notification is ever posted.
"""
import glob
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(ROOT, "scripts", "live_guard.sh")

pytestmark = pytest.mark.skipif(
    not os.path.exists("/bin/bash") or subprocess.run(
        ["git", "--version"], capture_output=True).returncode != 0,
    reason="needs /bin/bash and git")


def _repo(tmp_path, branch):
    proj = tmp_path / "proj"
    (proj / "logs").mkdir(parents=True)
    run = lambda *a: subprocess.run(["git", "-C", str(proj), *a], check=True,
                                    capture_output=True)
    run("init", "-q", "-b", "main")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "--allow-empty", "-m", "init")
    if branch == "DETACHED":
        run("checkout", "-q", "--detach")
    elif branch != "main":
        run("checkout", "-q", "-b", branch)
    return proj


def _guard(proj):
    script = (f'PROJ="{proj}"\n'
              'notify() { echo "NOTIFY|$1|$2|$3"; }\n'
              f'. "{GUARD}"\n'
              'live_guard "logs/brief_test.log"\n'
              'echo "rc=$?"\n')
    r = subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True)
    log = proj / "logs" / "brief_test.log"
    return r.stdout, (log.read_text() if log.exists() else "")


def test_main_is_silent(tmp_path):
    out, log = _guard(_repo(tmp_path, "main"))
    assert "NOTIFY" not in out and log == "" and "rc=0" in out


@pytest.mark.parametrize("branch", ["feat/exclusion-registry", "DETACHED"])
def test_off_main_alerts_in_log_and_notification(tmp_path, branch):
    out, log = _guard(_repo(tmp_path, branch))
    assert log.startswith("##ALERT## LIVE BRANCH:")
    assert "NOTIFY|ALERT|" in out and "rc=0" in out
    expected = branch if branch != "DETACHED" else "detached HEAD"
    assert expected in log


def test_every_scheduled_wrapper_runs_the_guard():
    wrappers = glob.glob(os.path.join(ROOT, "scripts", "scheduled_*.sh")) + [
        os.path.join(ROOT, "scripts", "weekly_heartbeat.sh")]
    assert len(wrappers) == 4
    for w in wrappers:
        body = open(w).read()
        assert '. "$PROJ/scripts/live_guard.sh"' in body, w
        assert 'live_guard "$LOG"' in body, w
        # the guard needs notify(), so notify.sh must be sourced before it
        assert body.index("scripts/notify.sh") < body.index("scripts/live_guard.sh"), w
