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

from _paths import ROOT
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
    assert len(wrappers) == 5      # 4 -> 5 on 2026-11-19: scheduled_briefing.sh (configuration_detector_spec §14.2)
    for w in wrappers:
        body = open(w).read()
        assert '. "$PROJ/scripts/live_guard.sh"' in body, w
        assert 'live_guard "$LOG"' in body, w
        # the guard needs notify(), so notify.sh must be sourced before it
        assert body.index("scripts/notify.sh") < body.index("scripts/live_guard.sh"), w


# ── Live code must match main (2026-11-01, incident I31) ──────────────────────
# At 00:03 on 2026-11-01 an unreviewed edit left levels_context.py unparseable
# in the live checkout. entry_confirmation imports it lazily inside
# `try/except Exception`, so the brief would have degraded silently. The
# guard now alerts whenever a tracked code file (*.py, *.sh) under $PROJ
# differs from HEAD. These repos mirror production: the git root is ABOVE
# the project folder (the real root is $HOME) and the folder name has a space.

def _nested_repo(tmp_path):
    root = tmp_path / "home"
    proj = root / "Intel Proj"
    (proj / "logs").mkdir(parents=True)
    (proj / "scripts").mkdir()
    (proj / "levels_context.py").write_text('result = {}\nresult["prev_week_high"] = 1\n')
    (proj / "scripts" / "wrapper.sh").write_text("echo ok\n")
    (proj / "storylines.md").write_text("# storylines\n")
    (root / "personal.py").write_text("x = 1\n")
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True,
                                    capture_output=True)
    run("init", "-q", "-b", "main")
    run("add", "-A")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return root, proj


def test_clean_live_code_is_silent(tmp_path):
    _, proj = _nested_repo(tmp_path)
    out, log = _guard(proj)
    assert "NOTIFY" not in out and log == "" and "rc=0" in out


def test_unparseable_python_alerts_and_says_so(tmp_path):
    # the I31 edit, byte for byte
    _, proj = _nested_repo(tmp_path)
    (proj / "levels_context.py").write_text('result = {}\nresult["n] = 1\n')
    out, log = _guard(proj)
    assert log.startswith("##ALERT## LIVE CODE MODIFIED:")
    assert "levels_context.py (does not parse)" in log
    assert "NOTIFY|ALERT|" in out and "levels_context.py" in out and "rc=0" in out


def test_parseable_edit_still_alerts(tmp_path):
    # an edit that parses is still unreviewed code on the live path
    _, proj = _nested_repo(tmp_path)
    (proj / "levels_context.py").write_text('result = {}\nresult["prev_week_low"] = 1\n')
    out, log = _guard(proj)
    assert log.startswith("##ALERT## LIVE CODE MODIFIED:")
    assert "levels_context.py" in log and "does not parse" not in log
    assert "NOTIFY|ALERT|" in out


def test_staged_and_shell_and_deleted_edits_alert(tmp_path):
    root, proj = _nested_repo(tmp_path)
    (proj / "scripts" / "wrapper.sh").write_text("echo changed\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)  # staged, uncommitted
    (proj / "levels_context.py").unlink()
    out, log = _guard(proj)
    assert "scripts/wrapper.sh" in log
    assert "levels_context.py (deleted)" in log
    assert "NOTIFY|ALERT|" in out


@pytest.mark.parametrize("what", ["doc", "outside_project", "untracked"])
def test_non_code_or_out_of_scope_changes_do_not_reach_the_owner(tmp_path, what):
    # rule 12: the owner hears only about live code. A storylines edit is the
    # owner's own writing; files elsewhere under $HOME are not this project;
    # an untracked .py is imported by nothing on the live path.
    root, proj = _nested_repo(tmp_path)
    if what == "doc":
        (proj / "storylines.md").write_text("# storylines\nGBP: neutral\n")
    elif what == "outside_project":
        (root / "personal.py").write_text("x = 2\n")
    else:
        (proj / "scratch.py").write_text("x = (\n")
    out, log = _guard(proj)
    assert "NOTIFY" not in out and log == "" and "rc=0" in out


def test_alert_repeats_while_the_condition_persists(tmp_path):
    # Deliberate, like the branch alert: every scheduled run while live code
    # is modified says so, until it is committed through review or reverted.
    _, proj = _nested_repo(tmp_path)
    (proj / "levels_context.py").write_text('result = {}\nresult["n] = 1\n')
    _guard(proj)
    out, log = _guard(proj)
    assert log.count("##ALERT## LIVE CODE MODIFIED:") == 2
    assert "NOTIFY|ALERT|" in out


def test_off_main_and_modified_code_both_alert(tmp_path):
    root, proj = _nested_repo(tmp_path)
    subprocess.run(["git", "-C", str(root), "checkout", "-q", "-b", "feat/x"], check=True)
    (proj / "levels_context.py").write_text('result = {}\nresult["n] = 1\n')
    out, log = _guard(proj)
    assert "##ALERT## LIVE BRANCH:" in log and "##ALERT## LIVE CODE MODIFIED:" in log
    assert out.count("NOTIFY|ALERT|") == 2
