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


def header_drift(path, expected):
    """The header check itself. None when the file's header equals the
    writer's schema, else a human-readable description of the drift.
    Returns None for a missing or empty file: nothing to compare."""
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if header is None or header == expected:
        return None
    return (
        f"{os.path.basename(path)} has drifted from the writer's schema.\n"
        f"  on disk : {header}\n"
        f"  in code : {expected}\n"
        f"  missing from file: {[c for c in expected if c not in header]}\n"
        f"  extra in file    : {[c for c in header if c not in expected]}\n"
        "A drifted header reads back as None for the missing columns on "
        "every historical row. Run the module's additive migration — never "
        "hand-edit the ledger.")


@pytest.mark.parametrize("ledger,module,attr", LEDGERS,
                         ids=[l[0] for l in LEDGERS])
def test_on_disk_header_matches_the_writing_modules_schema(ledger, module,
                                                           attr):
    path = os.path.join(_ROOT, ledger)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        pytest.skip(f"{ledger} not present or empty — nothing to compare")
    drift = header_drift(path, _schema(module, attr))
    assert drift is None, drift


def test_every_ledger_in_the_repo_is_covered():
    """A new ledger must not be able to appear unwatched. If this fails,
    add the ledger to LEDGERS with the module that writes it — or, if it is
    not a ledger, say so here."""
    not_ledgers = {
        "calendar.csv",     # fetched feed, schema owned by calendar_fetch
        "trade_log.csv",    # frozen April-era historical evidence
    }
    covered = {l[0] for l in LEDGERS} | not_ledgers
    on_disk = {f for f in os.listdir(_ROOT)
               if f.endswith(".csv") and not f.startswith("test")}
    uncovered = on_disk - covered
    assert not uncovered, (
        f"ledger(s) with no header check: {sorted(uncovered)}")


def test_the_check_would_have_caught_the_2026_09_16_drift(tmp_path):
    """The guard must be shown to fire on the real historical case: a header
    missing shadow_direction and shadow_conviction. It calls the SAME
    header_drift() the live check uses. The first version rebuilt the
    comparison inline and passed even if the real check was broken
    (2026-09-29 audit)."""
    import trade_outcome_logger as tol
    expected = list(tol._FIELDS)
    p = tmp_path / "trade_signal_log.csv"

    drifted = [c for c in expected
               if c not in ("shadow_direction", "shadow_conviction",
                            "size_pct", "entry_context")]
    with open(p, "w", newline="") as f:
        csv.writer(f).writerow(drifted)
    drift = header_drift(str(p), expected)
    assert drift is not None, "the check did not fire on the known drift"
    assert "shadow_direction" in drift and "shadow_conviction" in drift

    with open(p, "w", newline="") as f:          # and stays quiet when fixed
        csv.writer(f).writerow(expected)
    assert header_drift(str(p), expected) is None
