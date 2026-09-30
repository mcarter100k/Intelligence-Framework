"""
test_shell_syntax.py — every shell wrapper must parse under /bin/bash.

launchd runs the wrappers with macOS /bin/bash (3.2), not the Homebrew
bash 5 on an interactive PATH. weekly_heartbeat.sh parsed under bash 5 but
failed under 3.2 (an apostrophe inside a heredoc inside $( )), so the
Sunday heartbeat never ran under launchd from its 2026-09-09 build until
the 2026-09-29 audit. This pins the interpreter launchd actually uses.
"""
import glob
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = sorted(glob.glob(os.path.join(ROOT, "scripts", "*.sh"))
                 + glob.glob(os.path.join(ROOT, "scripts", "launchd", "*.sh")))


@pytest.mark.skipif(not os.path.exists("/bin/bash"), reason="no /bin/bash")
@pytest.mark.parametrize("path", SCRIPTS, ids=os.path.basename)
def test_wrapper_parses_under_system_bash(path):
    r = subprocess.run(["/bin/bash", "-n", path], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_every_launchd_plist_is_uninstallable():
    plists = {os.path.basename(p)[:-len(".plist")] for p in
              glob.glob(os.path.join(ROOT, "scripts", "launchd", "*.plist"))}
    with open(os.path.join(ROOT, "scripts", "launchd", "uninstall.sh")) as f:
        body = f.read()
    missing = sorted(n for n in plists if n not in body)
    assert not missing, f"uninstall.sh omits: {missing}"
