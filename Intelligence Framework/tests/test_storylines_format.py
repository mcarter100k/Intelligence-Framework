"""
test_storylines_format.py — the macro read must be machine-readable (I32).

Until 2026-11-01 setup_check's FUEL line could never say AGREES or
CONFLICTS: the parser reads `GBP: neutral` lines, and storylines.md wrote
`## GBP — …` / `Bias: NEUTRAL.` only, so parse_storylines returned no views.
The owner chose (2026-11-01, docs/driver_coverage_proposal.md §7) to add one
machine-readable line per currency, with no code change.

The live-file check applies from the first storylines.md approved AFTER
that decision: an older file is the known-unreadable one (I32) and skips.
"""
import os
import shutil

import pytest

from _paths import ROOT
from setup_check import parse_storylines

LIVE = os.path.join(ROOT, "storylines.md")
DECISION_DATE = "2026-11-01"

# The template given to the owner: the existing prose, plus one line per
# currency directly under its heading.
TEMPLATE = """# storylines.md — week of 2026-11-02 (approved 2026-11-02)

## GBP — passenger, not driver
GBP: neutral
Bias: NEUTRAL. No BoE meeting this week.

## AUD — second-strongest currency on the board
AUD: bullish
Bias: BULLISH. RBA expected to hike.

## JPY — policy regime change in progress
JPY: bearish
Bias: BEARISH (yen). INTERVENTION-WATCH: lit.
"""


def _assert_machine_readable(path):
    st = parse_storylines(path)
    if not st["header_date"] or st["header_date"] < DECISION_DATE:
        pytest.skip(f"storylines.md approved {st['header_date']}: written before "
                    f"the {DECISION_DATE} format decision (I32); checked from the "
                    f"next approval on")
    missing = {"GBP", "AUD", "JPY"} - set(st["views"])
    assert not missing, (
        f"storylines.md (approved {st['header_date']}) has no machine-readable "
        f"bias for {sorted(missing)}. Add a line like 'GBP: neutral' "
        f"(bullish / bearish / neutral) under each currency heading, or the "
        f"pre-trade FUEL check cannot compare a trade with the macro read.")


def test_template_given_to_the_owner_parses(tmp_path):
    p = tmp_path / "storylines.md"
    p.write_text(TEMPLATE)
    st = parse_storylines(str(p))
    assert st["views"] == {"GBP": "neutral", "AUD": "bullish", "JPY": "bearish"}
    assert st["header_date"] == "2026-11-02"
    assert st["intervention_watch"] is True


def test_live_storylines_is_machine_readable():
    if not os.path.exists(LIVE):
        pytest.skip("no storylines.md")
    _assert_machine_readable(LIVE)


def test_the_live_check_fires_on_a_new_file_without_the_lines(tmp_path):
    # Positive control: the real file, re-dated past the decision, must fail
    # the live check. Proves the skip above is not hiding a check that can't fire.
    if not os.path.exists(LIVE):
        pytest.skip("no storylines.md")
    p = tmp_path / "storylines.md"
    text = open(LIVE, encoding="utf-8").read()
    for ccy in ("GBP", "AUD", "JPY"):
        text = "\n".join(l for l in text.splitlines()
                         if not l.upper().startswith(f"{ccy}:"))
    import re
    text = re.sub(r"approved \d{4}-\d{2}-\d{2}", "approved 2026-11-08", text, count=1)
    p.write_text(text)
    with pytest.raises(AssertionError, match="no machine-readable bias"):
        _assert_machine_readable(str(p))
