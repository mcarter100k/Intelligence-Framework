"""Where the project is, for the tests. The tests live in tests/; the code,
scripts and ledgers they check are one level up. A wrong root would make
some tests skip or collect nothing, so it is asserted, not assumed."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
assert os.path.isfile(os.path.join(ROOT, "decision_brief.py")), f"not the project root: {ROOT}"
