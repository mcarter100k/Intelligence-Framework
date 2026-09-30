"""
exclusions.py — machine-readable exclusion registry
(docs/specs/exclusion_registry_spec.md, team-directed 2026-09-16).

WHY THIS EXISTS. On 2026-09-16 a Gate-2 verification run contaminated two
append-only evidence rows. A correction entry was written to
validation_log.md — which protects a HUMAN reading the record. It does not
protect the GRADER, which is code, runs nightly at 15:15, and would have
graded the contaminated regime row and fed the result into DATA BASIS.

A ledger row can be wrong. The ledgers are append-only, so it can never be
removed. The registry is how a row stays in the record while being kept out
of every tally.

DESIGN RULES, all load-bearing:

  * Ledgers are NEVER edited. This module only ever READS. Excluding a row
    is an act of interpretation recorded beside the evidence, never an edit
    of the evidence.
  * Exclusion filters at the point of USE — tallies, accuracy, episode
    counts, deltas — NEVER at the point of read. Several graders read rows
    and write them back; filtering at read would delete rows from the
    ledger, which is the exact harm this module exists to avoid.
  * Every exclusion names an authorizing validation_log entry. An exclusion
    without a written authorization is indistinguishable from hiding an
    inconvenient result.
  * The registry is itself append-only.
  * Fail OPEN, loudly. If the registry cannot be read, nothing is excluded
    and the reason goes to stderr. A grader that silently excludes
    everything because a file is missing is worse than one that excludes
    nothing.

Registry schema (excluded_rows.csv):
    log_id            identifier as it appears in the ledger
    ledger            the ledger filename the id belongs to
    date              date the exclusion was authorized (YYYY-MM-DD)
    reason            why, in plain words
    authorizing_entry the validation_log.md entry that authorizes it
"""
from __future__ import annotations

import csv
import os
import sys
from typing import Callable, Dict, Iterable, List, Optional, Set

_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(_DIR, "excluded_rows.csv")

FIELDS = ["log_id", "ledger", "date", "reason", "authorizing_entry"]

# Which column carries a row's identity, per ledger. Where a ledger has no
# id column, identity is composed (see _row_identities).
_ID_FIELD = {
    "regime_classification_log.csv": "log_id",
    "trade_signal_log.csv":          "signal_id",
    "shadow_signal_log.csv":         None,   # composed: timestamp[_instrument]
    "session_context_log.csv":       None,   # composed: timestamp[_instrument]
}


_warned: Set[str] = set()


def _alert(msg: str) -> None:
    """One ##ALERT## line per distinct message per process.

    The ##ALERT## prefix is load-bearing: the brief wrapper keeps ONLY
    ##ALERT## lines from stderr, so a plain warning would be discarded and
    the failure would be silent again (exclusion_registry_fixes_spec D1).
    """
    if msg in _warned:
        return
    _warned.add(msg)
    print(f"##ALERT## EXCLUSION REGISTRY: {msg}", file=sys.stderr)


def _load() -> List[Dict]:
    """Every VALID registry row. Fails OPEN and LOUD — never silently excludes.

    Any read failure (missing file, OS error, bad encoding, CSV error, wrong
    header) excludes nothing and alerts. A malformed ROW is skipped on its
    own, with an alert, and every valid row still applies — one bad
    hand-edit must not switch off the whole registry.
    """
    if not os.path.exists(REGISTRY_FILE):
        _alert(f"{REGISTRY_FILE} not found — NOTHING excluded this run; "
               f"tallies may include contaminated rows")
        return []
    try:
        with open(REGISTRY_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            if "log_id" not in header or "ledger" not in header:
                _alert(f"header {header} lacks log_id/ledger — NOTHING "
                       f"excluded this run")
                return []
            raw = list(reader)
    except Exception as exc:     # OSError, UnicodeDecodeError, csv.Error, ...
        _alert(f"unreadable ({type(exc).__name__}: {exc}) — NOTHING "
               f"excluded this run; tallies may include contaminated rows")
        return []
    rows = []
    for n, r in enumerate(raw, start=2):          # line 1 is the header
        log_id, ledger = r.get("log_id"), r.get("ledger")
        if not isinstance(log_id, str) or not isinstance(ledger, str) \
                or not log_id.strip() or not ledger.strip():
            _alert(f"line {n} is malformed and was SKIPPED (other rows "
                   f"still apply): {r}")
            continue
        rows.append(r)
    return rows


def excluded_ids(ledger: str) -> Set[str]:
    """The excluded identifiers for one ledger. Call once per tally, not
    once per row."""
    return {r["log_id"].strip() for r in _load()
            if r["ledger"].strip() == ledger}


def excluder(ledger: str) -> Callable[[Dict], bool]:
    """A predicate `row -> True if excluded` for one ledger. Never raises.

    The single way call sites consult the registry. It replaces seven
    copy-pasted try/import/except blocks that each turned a registry error
    into a silent empty set. The registry is read once, here; a failure
    anywhere inside alerts and fails open.
    """
    try:
        ids = excluded_ids(ledger)
    except Exception as exc:
        _alert(f"lookup failed for {ledger} ({type(exc).__name__}: {exc}) "
               f"— NOTHING excluded this run")
        ids = set()
    if not ids:
        return lambda row: False
    return lambda row: bool(_row_identities(row, ledger) & ids)


def _row_identities(row: Dict, ledger: str) -> Set[str]:
    """Every identifier a row can legitimately be named by.

    session_context_log.csv has no id column, so a row is nameable by its
    bare timestamp OR by timestamp_instrument. Both are accepted: the
    authorizing entry may cite either, and a bare timestamp excludes every
    instrument logged at that instant, which is the conservative reading.
    """
    out: Set[str] = set()
    field = _ID_FIELD.get(ledger, "log_id")
    if field and row.get(field):
        out.add(str(row[field]).strip())
    ts = str(row.get("timestamp", "")).strip()
    inst = str(row.get("instrument", "")).strip()
    if ts:
        out.add(ts)
        if inst:
            out.add(f"{ts}_{inst}")
    return out


def is_excluded(row: Dict, ledger: str,
                excluded: Optional[Set[str]] = None) -> bool:
    """True when this row is registered as excluded from tallies."""
    ids = excluded if excluded is not None else excluded_ids(ledger)
    if not ids:
        return False
    return bool(_row_identities(row, ledger) & ids)


def filter_rows(rows: Iterable[Dict], ledger: str) -> List[Dict]:
    """Drop excluded rows from a sequence bound for a TALLY.

    Never use this on rows that will be written back — that would delete
    them from the ledger. Filter what you count, not what you read.
    """
    excluded = excluder(ledger)
    return [r for r in rows if not excluded(r)]


def append_exclusion(log_id: str, ledger: str, date: str, reason: str,
                     authorizing_entry: str) -> None:
    """Append one exclusion. The registry is append-only, like the ledgers
    it annotates. An exclusion with no authorizing entry is refused."""
    if not (log_id and ledger and date and reason and authorizing_entry):
        raise ValueError(
            "every exclusion needs log_id, ledger, date, reason AND an "
            "authorizing validation_log entry — an unauthorized exclusion "
            "is indistinguishable from hiding an inconvenient result")
    from ledger_io import append_row             # stdlib-only; no cycle
    append_row(REGISTRY_FILE, FIELDS,
               {"log_id": log_id, "ledger": ledger, "date": date,
                "reason": reason, "authorizing_entry": authorizing_entry})
