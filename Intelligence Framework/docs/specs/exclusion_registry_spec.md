# Spec: exclusion registry, header check, and two standing rules

**Status:** team-directed 2026-09-16 (three rulings + one new requirement),
following the self-reported Gate-2 contamination logged the same day
(`0d5607a`).
**Branch:** `feat/exclusion-registry`. **Merge held for team review.**

**Protected files touched:** `regime_classifier_logger.py`,
`trade_outcome_logger.py`, `session_memory.py`, `shadow_signals.py`, and
**`exclusions.py` (NEW — joins the protected list, 19 → 20)**.
**Free-zone:** `scripts/artifact_freshness.py`, tests, `AGENTS.md`,
`validation_log.md`.

**Process note, stated rather than glossed:** the ruling said "spec first."
The spec artifact does precede every build commit on this branch, which is
what AGENTS.md rule 1b requires. But the urgent item — the grader runs at
15:15 today against a contaminated row — was built before this document was
written. Commit order is correct; authoring order was not. Recorded because
this team's process is worth more than the appearance of having followed it.

---

## RULING 1 — Rule 9 stays (no action)

`A ZERO FROM AN UNVERIFIED PATH IS NOT DATA` remains in AGENTS.md as
written. No change.

---

## ITEM 2 — Machine-readable exclusion (URGENT: contamination is live)

### The gap

`validation_log.md` protects a **human** reading the record. The grader is
**code**: it runs nightly at 15:15, and would have graded the contaminated
`regime_classification_log.csv` row — a row whose `stand_down=False` is
synthetic — and fed the result into DATA BASIS. A prose correction is not a
control.

### `exclusions.py` (new, protected)

Registry `excluded_rows.csv`, append-only, schema:
`log_id, ledger, date, reason, authorizing_entry`.

Four design rules, each load-bearing:

1. **Ledgers are NEVER edited.** The module only reads. Excluding a row is
   an act of interpretation recorded *beside* the evidence.
2. **Filter at the point of USE, never at the point of READ.** Several
   graders read rows and write them back; filtering at read would delete
   rows from an append-only ledger — the exact harm this exists to prevent.
   `check_pending_outcomes` therefore *skips* excluded rows and passes them
   through to the write-back untouched.
3. **Every exclusion names an authorizing `validation_log` entry.**
   `append_exclusion` raises without one. An unauthorized exclusion is
   indistinguishable from hiding an inconvenient result.
4. **Fail OPEN, loudly.** An unreadable registry excludes nothing and says
   so on stderr. A grader that silently excludes everything because a file
   is missing is worse than one that excludes nothing.

### Identity

`regime_classification_log.csv` and `trade_signal_log.csv` carry an id
column. `session_context_log.csv` and `shadow_signal_log.csv` do not, so a
row is nameable by its bare `timestamp` **or** by `timestamp_instrument`.
Both are accepted: the authorizing entry may cite either, and a bare
timestamp excludes every instrument logged at that instant — the
conservative reading.

### Wiring (every tally named in the ruling)

| function | module | treatment |
|---|---|---|
| `check_pending_outcomes` | `regime_classifier_logger` | skip; row passed through to write-back |
| `get_regime_accuracy` | `regime_classifier_logger` | filtered before tally |
| `check_pending_trade_outcomes` | `trade_outcome_logger` | skip; row passed through |
| `get_accuracy_by_regime` | `trade_outcome_logger` | filtered before tally |
| `get_accuracy_by_signal_type` | `trade_outcome_logger` | filtered before tally |
| `_get_today_rows` → session deltas | `session_memory` | filtered (read feeds comparisons only) |
| `episode_count`, `get_shadow_tally` | `shadow_signals` | skip, beside the existing `is_invalid_spec` exclusion |

### Seed

Both rows from the 2026-09-16 contamination:
`session_context_log.csv / 2026-09-16T09:08:08Z` and
`regime_classification_log.csv / 2026-09-16T09:08:08Z_GBP_AUD`, each citing
the CORRECTION entry.

### Pinned test (the requirement, in one line)

**An excluded row cannot reach any tally** — pinned separately for regime
accuracy, trade accuracy, session deltas, and shadow episode counts.

---

## ITEM 3 — Header-vs-schema check

Fourth member of the *divergence-without-detection* family. The first three
were connections between modules; this is a connection between a module and
its own file on disk. `trade_signal_log.csv` sat two columns behind
`trade_outcome_logger._FIELDS` and nothing compared them.

Not cosmetic: `csv.DictReader` keys rows by the **on-disk** header, so a
column the writer believes exists reads back as `None` for every historical
row.

`test_ledger_headers.py` asserts, per ledger, that the on-disk header equals
the writing module's `_FIELDS`/`FIELDNAMES` — seven ledgers, parameterized.
A missing ledger is **skipped, not failed**: a fresh checkout has no
ledgers, and a guard that fails on a clean clone is a guard someone
disables. A companion test asserts no `.csv` in the repo escapes coverage,
so a new ledger cannot appear unwatched.

---

## ITEM 4 — AGENTS.md rule 10

> **VERIFICATION RUNS MUST NEUTRALIZE EVERY SIDE EFFECT ON THE PATH THEY
> EXERCISE**, not only the one under test. `get_decision_brief` writes three
> ledgers; a Gate-2 run that redirects one contaminates two. Precedents:
> `trades.csv` test spill (2026-09-11), `session_context_log` +
> `regime_classification_log` contamination (2026-09-16). Use the
> `_neutralize_side_effects` helper for any run that touches real files.

Second instance this week, so it is a class, not an incident. The rule adds
the reason the cure cannot be remediation: a contaminated row can never be
removed from an append-only ledger, so the only remedy is a registry entry
suppressing it from every tally forever. **Prevention is the whole of the
cure.**

---

## Gate 1

New tests: 14 exclusion, 9 header, plus live-core/inventory updates.
Suite 1297 → 1320 green; shadow 868 unchanged. Neither floor touched.

`excluded_rows.csv` is itself inventoried under `READ_SIDE_NO_CADENCE` —
**rule 8 applied on its first day to a file created in the same commit.**
Its writer is a human authorization event, so it can have no cadence; its
integrity control is `test_exclusions.py`, not freshness. The
already-committed guards caught this omission automatically, which is the
first evidence they work on something other than the case they were built
from.

## Gate 2 — REALITY

Run the real nightly grader (`run_outcome_check.py`) against live data and
show the excluded regime row **remains ungraded** while honest rows grade
normally.

No neutralization is required here and none is applied — nothing is forced.
The grader's writes ARE the behavior under test and every input is genuine,
which is precisely the distinction rule 10 draws.

## Gate 3 — PENDING LIVE CONFIRMATION

- The excluded row surviving a **scheduled** 15:15 grader run ungraded
  (this spec's Gate 2 proves a manual run; only the scheduler proves the
  scheduled one).
- Carried forward: first real `trade_signal_log.csv` row from a genuine
  directional decision; the degraded-pass branch firing; first live
  GBP/JPY `m15_trigger = True`.
