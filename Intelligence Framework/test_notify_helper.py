"""
test_notify_helper.py
─────────────────────
Pins scripts/notify.sh (docs/specs/notify_click_through_spec.md): correct
terminal-notifier invocation with click-to-open URL, the always-appended log
pointer, and the osascript fallback on every failure shape (missing binary,
hung binary, nonzero exit). Runs bash with a fake $HOME whose stub binaries
record their argv; no real notification is posted.

Run: pytest test_notify_helper.py
"""
import os
import time
import subprocess

import pytest

_PROJ = os.path.dirname(os.path.abspath(__file__))
_HELPER = os.path.join(_PROJ, "scripts", "notify.sh")


def _run(tmp_path, tn_body=None, watchdog="2",
         call='notify "SHADOW" "hello world" "logs/brief_2026-09-09.log"'):
    """Source the helper under a fake HOME + stub osascript; return
    (tn_argv_or_None, osa_argv_or_None)."""
    home = tmp_path / "home"
    macos = home / "Applications" / "terminal-notifier.app" / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    tn_log = tmp_path / "tn.argv"
    osa_log = tmp_path / "osa.argv"

    if tn_body is not None:
        tn = macos / "terminal-notifier"
        tn.write_text(f'#!/bin/bash\nprintf \'%s\\n\' "$@" > "{tn_log}"\n{tn_body}\n')
        tn.chmod(0o755)

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    osa = stub_bin / "osascript"
    osa.write_text(f'#!/bin/bash\nprintf \'%s\\n\' "$@" > "{osa_log}"\n')
    osa.chmod(0o755)

    env = dict(os.environ, HOME=str(home),
               PATH=f"{stub_bin}:/usr/bin:/bin",
               NOTIFY_WATCHDOG_SECS=watchdog)
    script = f'PROJ="{_PROJ}"; . "{_HELPER}"; {call}'
    r = subprocess.run(["bash", "-c", script], env=env,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0                       # exit-0 discipline, always
    tn_argv = tn_log.read_text().splitlines() if tn_log.exists() else None
    osa_argv = osa_log.read_text() if osa_log.exists() else None
    return tn_argv, osa_argv


def test_terminal_notifier_invocation_pinned(tmp_path):
    tn, osa = _run(tmp_path, tn_body="exit 0")
    assert osa is None                             # no fallback on success
    args = dict(zip(tn[0::2], tn[1::2]))
    assert args["-title"] == "Intelligence Framework"
    assert args["-subtitle"] == "SHADOW"
    assert args["-message"] == "hello world → logs/brief_2026-09-09.log"
    # click target: absolute file URL, space %20-encoded, pointing at the log
    assert args["-open"] == (
        "file://" + _PROJ.replace(" ", "%20") + "/logs/brief_2026-09-09.log")

def test_pointer_always_appended(tmp_path):
    tn, _ = _run(tmp_path, tn_body="exit 0",
                 call='notify "HEARTBEAT" "healthy" "logs/heartbeat_x.log"')
    args = dict(zip(tn[0::2], tn[1::2]))
    assert args["-message"].endswith("→ logs/heartbeat_x.log")

def test_missing_binary_falls_back_to_osascript_with_pointer(tmp_path):
    tn, osa = _run(tmp_path, tn_body=None)
    assert tn is None
    assert "hello world → logs/brief_2026-09-09.log" in osa
    assert "Intelligence Framework" in osa and "SHADOW" in osa

def test_hung_binary_watchdog_fires_fallback(tmp_path):
    # simulates the unauthorized first post: binary blocks forever.
    # `exec` makes the stub BE the blocking process, as the real binary is.
    # The first version ran `sleep 300` as a CHILD of the stub script: the
    # watchdog killed the script and orphaned the sleep, one leaked process
    # per test run (found 2026-09-29: two orphans alive after two runs).
    pidfile = tmp_path / "tn.pid"
    tn, osa = _run(tmp_path, watchdog="1",
                   tn_body=f'echo $$ > "{pidfile}"; exec sleep 300')
    assert osa is not None                         # message not lost
    assert "hello world" in osa

    pid = int(pidfile.read_text())
    for _ in range(50):                            # kill delivery is async
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        os.kill(pid, 9)
        raise AssertionError(f"hung notifier process {pid} survived the watchdog")

def test_nonzero_exit_falls_back(tmp_path):
    tn, osa = _run(tmp_path, tn_body="exit 3")
    assert osa is not None
    assert "hello world" in osa

def test_success_does_not_double_notify(tmp_path):
    tn, osa = _run(tmp_path, tn_body="exit 0")
    assert tn is not None and osa is None


# ── wrapper category routing (static pins on the wrapper sources) ──────────────

def _src(name):
    with open(os.path.join(_PROJ, "scripts", name)) as f:
        return f.read()

def test_wrappers_source_helper_and_use_categories():
    brief = _src("scheduled_brief.sh")
    assert '. "$PROJ/scripts/notify.sh"' in brief
    assert 'CATEGORY="ALERT"' in brief and 'CATEGORY="DECISION"' in brief \
        and 'CATEGORY="SHADOW"' in brief
    assert 'notify "$CATEGORY" "$SUMMARY" "$LOG"' in brief
    out = _src("scheduled_outcome_check.sh")
    assert '. "$PROJ/scripts/notify.sh"' in out
    assert 'notify "SHADOW"' in out
    hb = _src("weekly_heartbeat.sh")
    assert 'notify "HEARTBEAT"' in hb
    # health path in both daily wrappers: ALERT vs RECOVERED
    for s in (brief, out):
        assert 'HCAT="ALERT"' in s and 'HCAT="RECOVERED"' in s
    # no wrapper calls osascript directly anymore (only the helper's fallback)
    for name in ("scheduled_brief.sh", "scheduled_outcome_check.sh",
                 "weekly_heartbeat.sh"):
        for line in _src(name).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "osascript" not in stripped, (name, line)
