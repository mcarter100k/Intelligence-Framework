# Spec: make failures visible (Phase 2 of the 2026-09-29 audit plan)

Status: this spec is committed before any build commit on
`feat/phase2-visible-failures`. The owner directed Phase 2 in session
2026-09-29.
Protected files touched: `oanda_feed.py`, `regime_detection.py`.
Merge is HELD for owner review.
Everything else (`scripts/`, tests, docs) is free zone.

## Why

AGENTS.md M32: "the error path must not look like a quiet market". The
39-day outage showed what happens otherwise: failures that look like normal
operation go unnoticed for weeks. The audit found seven places where they
still do.

**Each defect below was reproduced on `main` (58433b4) before any change,**
by running the real wrapper scripts in a throwaway project with stub
targets, and by driving the real `get_regime` with simulated OANDA failures.
The raw output is in the Phase 2 entry of validation_log.md.

| # | Defect (reproduced) | Observed on main |
|---|---|---|
| D1 | The grader crashing with a traceback is recorded as a SUCCESS | health after the crash: `consecutive_failures: 0`, `last_success_utc` set |
| D2 | The brief's non-`##ALERT##` stderr (e.g. "regime logger failed") is discarded | the line was absent from the day log |
| D3 | A brief crash's traceback is lost; it is only counted as "no output" | no Traceback in the day log |
| D4 | Both jobs share one failure counter, so a grader success sends a false RECOVERED for a failing brief | notifications: UNHEALTHY, then "RECOVERED after 2 failed runs" from the grader |
| D5 | The stale human-written `storylines.md` fails every healthy brief run | health: 1 failure, reason `STALE: storylines.md` |
| D6 | Freshness uses file mtime, so a grader rewrite hides a ledger whose newest row is 2000h old | `fresh: trade_signal_log.csv — 0h old` |
| D7 | A revoked key (401), an OANDA outage (503) and a timeout all read "Not enough data to calculate regime indicators", after exactly 1 attempt | all three cases, attempts=1 |

## Changes

1. **Per-job health (`scripts/health_state.py`).**
   - Usage becomes `record-failure <job> <reason>` / `record-success <job>`.
     Jobs are `brief` and `outcomes`.
   - Each job keeps its own streak, its own daily alert, and its own RECOVERED
     line, prefixed with the job's name.
   - The old flat state migrates into the `brief` job on first read, because
     the stored streak today comes from brief failures.
   - `status` prints every job.
   - **Fixes D4.**
2. **Wrappers record crashes and keep error output.**
   - `scheduled_brief.sh` appends the full stderr to the day log, not only
     `##ALERT##` lines.
   - Both wrappers capture the Python exit code. A nonzero exit, or
     "Traceback" in the output, is a FAILURE with a reason naming it.
   - The outcome wrapper's failure grep gains "Traceback" and the nonzero
     exit check.
   - **Fixes D1–D3.**
3. **Human-cadence artifacts remind; they never fail a run.**
   - `storylines.md` is written by the owner, not by a live job. Per rule 8
     ("a cadence requires a live writer"), past-due renders as a `DUE:` line
     that shows in the day log and the Sunday heartbeat, not as a `STALE:`
     line that fails the run.
   - **Fixes D5.**
4. **Freshness by the newest row.** For the four CSV ledgers written by the
   live path, age is measured from the newest row's `timestamp` column. mtime
   remains the fallback only for files with no parseable row timestamp
   (calendar, storylines). **Fixes D6.**
5. **OANDA errors say what happened, and transient ones retry (protected).**
   - `oanda_feed._get_bars` classifies every failure: HTTP 401/403 as
     credentials rejected, HTTP 429 as rate limited, HTTP 5xx as an OANDA
     server error, a timeout, a connection failure, or missing credentials.
     The latest classification is exposed through `oanda_feed.last_error()`.
   - Transient failures (timeout, connection, 429, 5xx) retry twice, waiting
     1s and then 2s. Credential errors never retry.
   - `get_regime` reports `OANDA unreachable — <classification>` when the D1
     fetch returned nothing, and keeps "Not enough data" for genuinely short
     history.
   - The dead retry at `regime_detection.py:803-810` is removed; the callee
     never raises, so it could not run.
   - **Fixes D7.**
6. **Carried from Phase 1, item 6.**
   - The static substring pins on the wrapper sources
     (`test_notify_helper::test_wrappers_source_helper_and_use_categories`,
     `test_daily_digest::test_wrapper_digest_gated_on_argument`) are replaced
     by behavioral tests that run the real wrappers.
   - To make that possible, the wrappers read their project directory from
     `INTEL_PROJ`, defaulting to the current hardcoded path. launchd sets
     nothing, so production is unchanged.

## Out of scope (recorded)

- `get_live_price` error classification. It has no live caller.
- A transient H4 failure still yields STAND_DOWN for that run. The retry
  reduces how often; the underlying logic is Phase 5.

## Verification (evidence-validation standard, AGENTS.md rule 11)

- **Gate 1.**
  - Behavioral wrapper tests for D1–D6, and feed/regime tests for D7.
  - Every new test must FAIL against `main`'s code (controlled comparison)
    and pass on the branch.
  - Mutation tests on each fix.
  - The full suite, under the whole-project guard.
- **Gate 2.**
  - Re-run the same BEFORE measurement scripts against the branch: all 7
    defects must now report ok.
  - `scripts/reality_run.py brief` and `grader` against the live ledgers
    with the branch code: project UNCHANGED, no failure markers.
  - A real OANDA call with a deliberately invalid key, in a reality_run with
    a scratch `.env`, must show the credentials classification and exactly
    1 attempt.
- **Gate 3 (PENDING).**
  - The first scheduled brief and grader runs after merge record per-job
    health.
  - The first real storylines `DUE:` line appears in the Sunday heartbeat.
