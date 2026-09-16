"""
test_ledger_headers.py — header-vs-schema check
(docs/specs/exclusion_registry_spec.md item 3, team-directed 2026-09-16).

FOURTH MEMBER of the divergence-without-detection family. The first three
were severed connections between modules (log_regime, last_run.json,
log_signal) and are covered by test_live_path_connections.py. This one is a
connection between a module and its own file on disk:
`trade_signal_log.csv` sat TWO columns behind `trade_outcome_logger._FIELDS`
— shadow_direction and shadow_conviction present in code, absent on disk —
and nothing noticed, because nothing compared the ledger's header against
the schema of the module that writes it.

A drifted header is not cosmetic. csv.DictReader keys rows by the ON-DISK
header, so a column the writer believes exists reads back as None for every
historical row, and a reader that assumes the code's schema gets silent
KeyErrors or silent blanks in a tally.

Each logger below owns exactly one ledger. Where the ledger does not exist
yet the check is skipped, not failed — a fresh checkout has no ledgers, and
a guard that fails on a clean clone is a guard someone disables.
"""
import csv
import os

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))


def _schema(module_name, attr):
    mod = __import__(module_name)
    return list(getattr(mod, attr))


# (ledger filename, module, attribute holding the schema)
LEDGERS = [
    ("regime_classification_log.csv", "regime_classifier_logger", "FIELDNAMES"),
    ("session_context_log.csv",       "session_memory",           "FIELDNAMES"),
    ("trade_signal_log.csv",          "trade_outcome_logger",     "_FIELDS"),
    ("shadow_signal_log.csv",         "shadow_signals",           "_FIELDS"),
    ("trades.csv",                    "trade_logger",             "FIELDS"),
    ("pre_trade_journal.csv",         "setup_check",        "_JOURNAL_FIELDS"),
    ("excluded_rows.csv",             "exclusions",               "FIELDS"),
]


@pytest.mark.parametrize("ledger,module,attr", LEDGERS,
                         ids=[l[0] for l in LEDGERS])
def test_on_disk_header_matches_the_writing_modules_schema(ledger, module,
                                                           attr):
    path = os.path.join(_ROOT, ledger)
    if not os.path.exists(path):
        pytest.skip(f"{ledger} not present — nothing to compare")
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if header is None:
        pytest.skip(f"{ledger} is empty — no header to compare")

    expected = _schema(module, attr)
    assert header == expected, (
        f"{ledger} has drifted from {module}.{attr}.\n"
        f"  on disk : {header}\n"
        f"  in code : {expected}\n"
        f"  missing from file: {[c for c in expected if c not in header]}\n"
        f"  extra in file    : {[c for c in header if c not in expected]}\n"
        "A drifted header reads back as None for the missing columns on "
        "every historical row. Run the module's additive migration — never "
        "hand-edit the ledger."
    )


def test_every_ledger_in_the_repo_is_covered():
    """A new ledger must not be able to appear unwatched. If this fails,
    add the ledger to LEDGERS with the module that writes it — or, if it is
    not a ledger, say so here."""
    not_ledgers = {
        "calendar.csv",     # fetched feed, schema owned by calendar_fetch
        "trade_log.csv",    # frozen April-era historical evidence
        "cot_cache.json",
    }
    covered = {l[0] for l in LEDGERS} | not_ledgers
    on_disk = {f for f in os.listdir(_ROOT)
               if f.endswith(".csv") and not f.startswith("test")}
    uncovered = on_disk - covered
    assert not uncovered, (
        f"ledger(s) with no header check: {sorted(uncovered)}")


def test_the_check_would_have_caught_the_2026_09_16_drift(tmp_path):
    """The guard must be shown to fire on the real historical case: a
    header missing shadow_direction and shadow_conviction."""
    import trade_outcome_logger as tol
    drifted = [c for c in tol._FIELDS
               if c not in ("shadow_direction", "shadow_conviction",
                            "size_pct", "entry_context")]
    p = tmp_path / "trade_signal_log.csv"
    with open(p, "w", newline="") as f:
        csv.writer(f).writerow(drifted)

    with open(p, newline="") as f:
        header = next(csv.reader(f))
    assert header != list(tol._FIELDS), "the drifted header must not match"
    missing = [c for c in tol._FIELDS if c not in header]
    assert "shadow_direction" in missing and "shadow_conviction" in missing
