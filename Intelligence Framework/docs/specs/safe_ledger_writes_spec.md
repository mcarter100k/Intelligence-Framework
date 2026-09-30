# Spec: safe ledger writes (Phase 3 of the 2026-09-29 audit plan)

Status: this spec is committed before any build commit on
`feat/phase3-safe-writes`. The owner directed Phase 3 in session
2026-09-29.

Protected files touched: `shadow_signals.py`, `regime_classifier_logger.py`,
`trade_outcome_logger.py`, `session_memory.py`, `exclusions.py`,
`setup_check.py`. New protected module: `ledger_io.py`, which is on the
evidence path. Merge is HELD for owner review.

## Why

The ledgers are append-only evidence, and "a contaminated row can never be
removed" (AGENTS.md rule 10). The same is true of a lost row: it can never
be re-observed. Yet every writer uses a bare `open("w")` or `open("a")` with
no locking. Launchd fires missed jobs together on wake; the 2026-09-14 brief
and grader ran 1 second apart. Nothing is backed up.

**Every defect below was reproduced on `main` (67a8aef) before any change,**
using real processes and the real logger functions on copies of the live
ledgers. Instrument controls: each second-process appender was first shown
to append on its own (a positive control), and each run recorded that the
second process actually ran and exited 0.

| # | Defect (reproduced) | Observed on main |
|---|---|---|
| B1a | The shadow grader's read-modify-write destroys a row another process appended meanwhile | 2nd process ran and exited 0; its row absent after grading |
| B1b | Same, in the regime grader | Same |
| B1c | Same, in the trade-signal grader | Same |
| B2 | A crash mid-rewrite truncates the ledger | SIGKILL during a rewrite of a copy of the real regime ledger: **114 rows became 0** |
| B3 | `session_context_log.csv` deletes rows older than 30 days on every write | A 59-day-old row was gone after one append |
| B4 | No backups exist | No backup tool, no backups/ |
| B5 | Concurrent health updates lose writes | 40 concurrent `record_failure`: 16, 32, 33, 34 and 37 of 40 counted across runs |

B3 has already cost evidence. The unexplained 2026-07-29 synthetic session
row, which Phase 1 traced to the integration tests, was deleted by this
prune, so that attribution can never be checked against the row itself.
The 2026-09-16 contaminated row that the exclusion registry names will be
deleted around 2026-10-16.

## Design: `ledger_io.py` (stdlib only; runs on Python 3.9 and later)

- **`locked(path)`** is an exclusive `fcntl.flock` on a sidecar file,
  `.<name>.lock`, in the same directory.
  - It uses a sidecar because `os.replace` swaps the data file's inode, so a
    lock on the data file itself would not survive an atomic rewrite.
  - It is **re-entrant within a process**: a depth count keyed by real path.
    Separate `open()` calls in one process would otherwise deadlock on BSD
    `flock`.
  - It has a 60s timeout. On timeout it raises `LedgerLockTimeout`: loud,
    never a silent unlocked write.
- **`atomic_write_rows(path, fieldnames, rows)`** writes a temp file in the
  same directory, flushes and fsyncs it, `os.replace`s it over the ledger,
  and keeps the original file mode. A crash leaves either the old file or
  the new one, never a partial file.
- **`append_row(path, fieldnames, row)`** runs under the lock. It writes the
  header when the file is new or empty, appends, then flushes and fsyncs.
- **Every read-modify-write holds `locked(path)` from its read to its
  write.** That covers the three graders, `backfill_loss_species`, the four
  header migrations, `log_shadow_signals`' dedupe-then-append, and
  `health_state`'s load-modify-save. None of these touches the network
  inside the lock (verified by reading the code): the graders fetch bars
  before reading the ledger.
- **Other writers** use the same primitives: `exclusions.append_exclusion`,
  `setup_check`'s journal, `trade_logger`'s `trades.csv`, and `health_state`.
  `calendar_fetch` already writes atomically.

## Decision: `session_context_log.csv` becomes append-only (recommended default; owner confirms at review)

- Pruning is removed. The 30-day window stays where it is actually used:
  `_get_today_rows` already reads only today's rows.
- **Cost:** 161 rows in 20 days is 13 KB, about 240 KB a year.
- **Alternative considered:** move pruned rows to an archive file instead of
  deleting them. This keeps the window, but it adds a second file to reason
  about and fixes nothing that simply keeping the rows does not.
- AGENTS.md already lists this ledger as append-only. The 2026-09-09 entry
  that called it "a designed rolling window" is superseded by a new dated
  entry, not edited.

## Backups: `scripts/backup_ledgers.py`

- **When:** it runs at the START of the nightly outcome wrapper, before the
  grader rewrites anything, so a bad grader write is always recoverable
  from that morning's copy.
- **What:** it copies every evidence file into `backups/<UTC date>/`. That
  covers the four ledgers, `excluded_rows.csv`, `trades.csv`,
  `pre_trade_journal.csv` and `logs/health_state.json`.
- **How:** each copy is taken under that file's lock, so it is consistent.
  The script then verifies each copy by hash, and prints one summary line
  that the wrapper logs.
- **Rules:** the first backup of a day is kept (never overwritten). All days
  are kept, because they are small. `backups/` is gitignored.
- **Honest limit:** backups on the same disk do not survive disk loss or a
  lost laptop. An off-machine copy (Time Machine, or a private remote) is
  the owner's decision, recorded as a recommendation.

## Verification (evidence-validation standard, AGENTS.md rule 11)

- **Gate 1.**
  - Unit tests for `ledger_io`: re-entrancy, timeout, atomicity under an
    injected crash, and header-on-empty.
  - Behavioral tests for each call site.
  - The B1–B5 measurement script re-run on the branch must show every
    defect fixed.
  - The new tests must fail on main's code.
  - Mutation tests, with caches cleared and a re-run after every revert.
  - The full suite under the whole-project guard, and the audit-hook probe.
- **Gate 2.**
  - `reality_run` brief and grader against the live ledgers.
  - The real wrappers end to end on a full project copy, including the
    first real backup and its hash verification.
  - A real concurrent brief and grader on the copy.
- **Gate 3 (PENDING).**
  - The first scheduled 15:15 run writes `backups/<date>/` on the live
    machine.
  - `session_context_log.csv` keeps rows past 30 days, first visible around
    2026-10-09 for the 2026-09-09 rows.

## Addendum (2026-09-30): what verification changed

**Instrument corrections found while verifying.** Each was caught before
any result was reported as final.
- **Invalid appender:** the first B1 appender carried a field not in the
  shadow schema, so it crashed. A positive control now requires every
  appender to append on its own first.
- **Grader that never wrote:** the first trade setup was not due for
  grading because it passed a plain list where the grader needs a time
  index, which it silently read as 0 bars. The instrument now asserts that
  the grader actually wrote. That silent zero is itself a fragility, noted
  for Phase 6.
- **Implementation-dependent trigger:** the first "after" trigger fired on
  `open(ledger, "w")`, which the new code never calls.
- **Trigger inside the inner lock:** the second trigger fired at the
  rewrite's header write, which sits inside the write's own lock. Mutation
  testing proved this: removing each grader's OUTER lock (MD/ME/MF) still
  passed. The trigger now fires when the grader's READ handle closes, the
  start of the stale-snapshot window. Before and after were both re-measured
  with it: main loses the row in all three graders; the branch keeps it.

**`/code-review` findings.** Each was reproduced on the branch before
fixing (AGENTS.md rule 11). All 10 were confirmed. R8 did not reproduce
for a symlinked directory, but did for a symlinked file.

| # | Finding | Fix |
|---|---|---|
| R1/R6 | A UTC-day backup slot could be taken by a late run; delete-then-rename could destroy a complete backup | One folder per run (UTC stamp); an existing backup is never touched |
| R2/R10 | The grader ran even when the backup failed, crashed or was missing | The grader runs only after the backup's success line; otherwise "GRADER SKIPPED" and an outcomes failure (grading is idempotent) |
| R3 | A health save error swallowed the ALERT line | Save and lock errors are reported, never swallow the line; health stderr goes to the day log |
| R4 | `log_shadow_signals` appended headerless rows to a 0-byte ledger | Uses the header-aware `append_row` |
| R5 | `trade_log.csv` was not backed up | Added |
| R7 | New files were created 0600 | Created with umask permissions (0644) |
| R8 | A symlinked ledger took a different sidecar lock | The sidecar is derived from the realpath |
| R9 | Four hand-written migration copies | One `ledger_io.migrate_header` |

**Decision for the owner (Phase 3 merge review).** Should
`session_context_log.csv` be append-only (built here), or should it keep a
rolling window with pruned rows moved to an archive file?
