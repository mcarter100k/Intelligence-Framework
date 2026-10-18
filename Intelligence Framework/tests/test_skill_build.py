"""
test_skill_build.py — the installed skill ships exactly what its SKILL.md documents (M30).

build_skill.sh copies foundation/*.md into references/ and the tools into
scripts/ by glob, with no check against the tables agents read. A new file
shipped undocumented; a renamed one left the table pointing at a path that
does not exist, and the loading agent silently read nothing (I24's schema
drift, in skill form). This runs the real build into tmp_path and compares
the shipped set to the documented set, in both directions.
"""
import os
import re
import subprocess

import pytest

from _paths import ROOT
FOUNDATION = os.path.join(ROOT, "foundation")

# (skill, section heading in its SKILL.md, shipped subdirectory, file pattern)
CASES = [
    ("trading-foundation", "## Reference files", "references", r"`references/([^`/]+\.md)`"),
    ("trading-foundation", "## Tools", "scripts", r"`scripts/([^`/]+\.py)`"),
    ("evidence-validation", "## Bundled instrument", "scripts", r"`scripts/([^`/]+\.py)`"),
]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    dest = tmp_path_factory.mktemp("skills")
    r = subprocess.run(["/bin/bash", os.path.join(FOUNDATION, "build_skill.sh"), str(dest)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dest


def _section(text, heading):
    """The body under the line that starts with `heading`, up to the next ## heading."""
    start = re.search(rf"^{re.escape(heading)}\b.*$", text, re.M).start()
    nxt = text.find("\n## ", start + len(heading))
    return text[start:nxt if nxt != -1 else len(text)]


@pytest.mark.skipif(not os.path.exists("/bin/bash"), reason="no /bin/bash")
@pytest.mark.parametrize("skill,heading,subdir,pattern", CASES,
                         ids=[f"{c[0]}:{c[2]}" for c in CASES])
def test_shipped_equals_documented(built, skill, heading, subdir, pattern):
    with open(os.path.join(FOUNDATION, "skills", skill, "SKILL.md")) as f:
        documented = set(re.findall(pattern, _section(f.read(), heading)))
    shipped_dir = built / skill / subdir
    shipped = set(os.listdir(shipped_dir)) if shipped_dir.is_dir() else set()
    assert documented, f"no {subdir}/ entries parsed from {skill} '{heading}'"
    assert sorted(documented - shipped) == [], f"documented in {skill} but not shipped"
    assert sorted(shipped - documented) == [], f"shipped in {skill} but not documented"
