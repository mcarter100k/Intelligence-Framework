# Spec: evidence-loop repair (2026-09-16 team ruling, three parts)

**Status:** team-directed 2026-09-16, following the Step 2 integration
inventory (validation_log, same date). Step 2's inventory entry landed on
`main` as `dbe2b67` under separate authorization.
**Branch:** `feat/evidence-loop-repair`. **Merge held for team review.**

**Protected files touched:** `decision_brief.py`, `trade_outcome_logger.py`.
**Free-zone:** `scripts/artifact_freshness.py`, tests, `validation_log.md`.

---

## PART 1 — `trade_outcome_logger`: the live defect

### The defect

`log_signal()`'s only caller is `shadow/market_brain.py:297`, quarantined
2026-07-29. `record_outcome()` and `get_accuracy_by_signal_type()` have no
caller anywhere. `trade_signal_log.csv` was last written **2026-06-28** and
holds **2 lines** — a header and one row — while `run_outcome_check.py:60`
calls `check_pending_trade_outcomes()` against it nightly at 15:15.

The grader has been grading a ledger nothing live fills. Third instance of
the quarantine-orphan class (after `log_regime`, 2026-09-09, and
`last_run.json`, 2026-09-16).

### The concrete loss

**The first live SHORT in framework history was never logged.**
From `logs/brief_2026-09-10.log`, the 18:04:14 PDT scheduled run:

```
GBP/AUD  |  Thu 10 Sep 2026 6:04 PM PDT
Price: 1.8879  |  ATR: 84.3 pips
DECISION     SHORT ▼ — look for sell entries
CONFIDENCE   50/100  |  Rating: B
POSITION     50% of standard size
ENTRY        No bearish engulfing in trade direction — level 1.8862
```

A real directional call, at a real price, with a grade and a size — and no
row in the ledger built to grade it. That single row is unrecoverable.

### FIX

Wire `log_signal` into the live path in `decision_brief.get_decision_brief`,
at the point where the official decision and `entry_line` are both in scope
(after `entry_line` is built, ~line 394). Fires **only** when
`decision_str` is `LONG` or `SHORT`.

Contract mirrors the `log_regime` restore exactly:

- **closed market skipped** — re-reading a closed market is not a new signal
- **loud on failure** — one `stderr` line naming the instrument and the
  exception, captured by the wrapper's day log; never silent
- **never fatal** — a logger failure must not break a brief
- **freshness is the backstop** — a persistently failing logger surfaces as
  a STALE line (see WATCHLIST below)

Payload per the ruling: instrument, direction, conviction, grade, size, and
entry context. `regime` supplies the market fields `log_signal` already
maps; `_official` supplies direction/conviction/grade/`size_mult`;
`entry_line` supplies the entry context.

### Schema: additive migration, two columns

`_FIELDS` has no size or entry-context column. Two are appended —
`size_pct`, `entry_context` — via the additive-migration pattern already
established and reviewed for `pre_trade_journal.csv`
(`setup_check._migrate_journal_header`, 2026-09-09): every existing row is
preserved verbatim in its old columns and left blank in the new ones. This
is **the logger maintaining its own schema, never an edit of recorded
values**. The one existing 2026-06-28 row is preserved byte-for-byte in its
original columns.

### `record_outcome` / `get_accuracy_by_signal_type`

Both are verified reachable from the grading and reporting paths, or the
reason they are not is stated plainly in the run report. Neither is wired
speculatively: `check_pending_trade_outcomes` is already the live grader
entry point and calls `_fill_outcome` internally, so `record_outcome` is the
**manual single-row** path and may legitimately have no scheduled caller. That
finding is recorded either way rather than papered over.

### LEDGER INTEGRITY (binding)

**2026-06-28 → the fix date is UNOBSERVED, not absent.** No accuracy claim,
base rate, or N may cite that window. **No backfill** — the signals that
were not logged are gone, and inventing them would be the exact dishonesty
this framework exists to prevent. Any report reading that span must say
"path not proven live", never "0 signals".

### WATCHLIST

`trade_signal_log.csv` gets a **720h** cadence — generous on purpose,
because a directional decision is not a daily event and an honest run of
STAND ASIDE days must not raise a health failure.

**`trade_log.csv` — deviation from the ruling, with cause (standing rule 5).**
The ruling asked for a cadence here too. Premise inspection says no:
`trade_logger.py:22` calls it "the April-era framework-snapshot file …
historical", and `trade_logger_repair_spec.md:23-28` already ran this
inspection and ruled it "stays untouched as historical evidence." It is a
different schema entirely (bias / confidence / value_zone, not trades),
superseded by `trades.csv`, and **deliberately writer-less**.

A cadence on a deliberately frozen file renders STALE on every run
forever — measured at **3987h** on the first live check — which the
wrapper converts into a health FAILURE, which alerts daily, which teaches
the operator to ignore the channel. That is the same harm this spec cites
when refusing to invent a cadence for `trades.csv`, and it would damage
the very alerting path Part 1 depends on.

It is therefore inventoried under `READ_SIDE_NO_CADENCE` with that reason:
accounted for and visible on every check, never alarming. **Team to
confirm** — if a cadence is still wanted, the file first needs a live
writer, which is a different piece of work.

---

## PART 2 — orphan detection, promoted to a test

### Root cause (why three instances, not three bugs)

The 2026-07-29 quarantine was audited **one-directionally**: what `shadow/`
imports was checked; what imports `shadow/`'s functions, and what consumes
artifacts `shadow/` writes, was not. Every severed connection since is the
same omission surfacing again. A fourth is a matter of time until the audit
runs in both directions automatically.

### The test

Fails when a live-core module's function or artifact has no live
producer/consumer and is not allowlisted with a written reason. Built from
the start with the four things the Step 2 pass proved are required:

1. **Alias-resolved imports** — `from x import apply_filter as _apply_filter`
   (`regime_detection.py:1104`). Without this the test claims `apply_filter`,
   one of the two suite floors, is dead code.
2. **Indirect dispatch** — values held in a list or dict and called through a
   loop (`shadow_signals.py:218`, `_CANDIDATES`). Without this the test
   claims the frozen candidates stopped accruing evidence.
3. **CLI entry points** — a `__main__` block makes a module reachable even
   with no importer (`setup_check.py`).
4. **An allowlist with a reason per entry.**

A guard that fires on working code gets deleted. Both false positives above
were caught only by hand-verifying against source before reporting; the test
must not need that.

### Allowlist (reason required, never a bare name)

| entry | reason |
|---|---|
| `risk_config`, `session_guard` | promoted out of quarantine 2026-09-09; awaiting the enforcement spec that wires the breaker into the live path |
| `nearest_resistance`, `nearest_support`, `find_confluence_zones` | known-unused; seeds for the level-map work, listed not deleted |
| `get_m5_bars`, `get_session_history_today` | known-unused helpers |
| `get_size_note`, `format_grade_block`, `print_risk_rules`, `calculate_lot_size` | `risk_config` display/sizing helpers, unused pending the breaker wiring |
| `can_trade` | test-only pending the gate spec |
| `storylines.md` | **correctly writer-less** — a human writes it in the Sunday session; its 216h freshness cadence is the control. Never "fix" this one. |

Known-unused is **listed, not deleted**.

---

## PART 3 — validation_log entries

(a) The Step 2 integration inventory in full, including both false positives
    and what they would have cost. **Already landed on `main` (`dbe2b67`)**
    under the separate authorization; not repeated here.
(b) The quarantine-orphan class: three instances, one event
    (2026-07-29), one root cause (one-directional audit), one systemic
    control (Part 2).
(c) The standing rule below.

### STANDING RULE — A ZERO FROM AN UNVERIFIED PATH IS NOT DATA

Every ledger-derived display must distinguish **"no observations"** from
**"path not proven live."** Three times a can't-fire has rendered as a
no-setup: `log_regime` (2026-09-09), THRUST_PULLBACK, and now
`trade_signal_log`. A zero that has never been shown capable of being
non-zero is not evidence of absence — it is absence of evidence, and the
display must say which one it is.

---

## Tests (pinned, per part)

**Part 1:** a LONG and a SHORT decision each produce exactly one ledger row
with the right direction/grade/conviction/size/entry context; STAND ASIDE
produces none; a closed market produces none; a raising logger emits one
stderr line and does not break the brief; the additive migration preserves
the existing row verbatim and blanks the new columns.

**Part 2:** the alias case, the indirect-dispatch case, and the `__main__`
case each resolve as LIVE (regression pins for the two real false
positives); a synthetic orphan IS caught; every allowlist entry carries a
non-empty reason.

**Watchlist:** both new artifacts appear; their cadences are pinned.

Full suite green (1280 + shadow 868 at branch point). Neither floor touched.

## Gate 2 — REALITY, and one conflict raised

The ruling asks for a forced live LONG/SHORT showing **a real row landing in
`trade_signal_log.csv`**. Executed as: real OANDA regime data, the real
`get_decision_brief` path, a forced directional decision, a real CSV write —
**with the ledger path pointed at a temporary file.**

**The conflict, raised rather than resolved unilaterally (standing rule 5):**
writing that row to the real `trade_signal_log.csv` would insert a signal
the framework never issued into an append-only evidence ledger, inside the
very window this spec declares UNOBSERVED. That contradicts PART 1's own
ledger-integrity clause. The wiring is proven end-to-end either way; what
the temp-file run cannot prove is a row produced by a decision the market
actually caused.

**Recommendation:** the real-file row is a Gate 3 item, cleared by the first
genuine LONG or SHORT. Team to rule — if the team wants a marked
verification row in the real ledger instead, `trades.csv` PAPER rows are the
precedent and a marker column would be needed.

## Gate 3 — PENDING LIVE CONFIRMATION

- **First real row in `trade_signal_log.csv` from a genuine directional
  decision.** Only the market can perform this.
- Carried forward: the degraded-pass branch firing; the first live GBP/JPY
  `m15_trigger = True`.
