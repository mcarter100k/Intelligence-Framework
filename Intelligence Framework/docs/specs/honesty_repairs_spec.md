# Spec: honesty repairs (Branch 1 of the 2026-09-09 post-audit directive)

**Status:** team-directed 2026-09-09 (post-audit directive, accepts the
2026-09-08 audit in full). No live-behavior change: nothing here alters what
fires, what is logged at fire time, or the tradeable path's decisions.
**Branch:** `feat/honesty-repairs`. Merge held for team review.

## Motivating evidence (from the 2026-09-08 first grading)

The three EARLY_MOMENTUM rows graded 2026-09-08 exposed a spec defect: rows 2
and 3 (SHORT entries 218.352 / 218.572) carry the stale swing-high stop
217.996 — *below* entry on a SHORT. For such rows the grader's hit test
(`max(fut_h) >= stop` for a SHORT) is trivially true at entry, so they are
**unscoreable by construction**: guaranteed −1.0R regardless of what the
market does. Both scored −1.0R while price moved 877.7 / 899.7 pips in the
signal's favor. Counting them as evidence would poison every tally they touch.

## Item 1 — grader/reporting validity guard (`shadow_signals.py`, PROTECTED)

A row is **invalid_spec** when its stop sits on the non-adverse side of entry:

- SHORT: `stop <= entry`
- LONG:  `stop >= entry`

The flag lives **entirely in the grading/reporting layer** — a predicate
`is_invalid_spec(row)` evaluated when rows are read. Ledger rows are NEVER
edited, no column is added for it, and fire-time logging is untouched.

Exclusions (invalid rows never counted):

- `get_shadow_tally` — excluded from logged / graded / wins / avg_net
- `episode_count` — excluded before episode collapse
- `latest_pending_signal` — never surfaced to the brief narrative
- `grade_pending_shadow` — invalid pending rows are **never scored as R**:
  the grader skips them (leaves them ungraded) and reports how many it
  skipped. Rows graded before this guard existed (rows 2–3) keep their ledger
  values untouched and are excluded by the reporting predicate.

The code comment at the predicate must state WHY: unscoreable by
construction (hit test true at entry), not merely mislabeled.

## Housekeeping f (code half) — regime-log independent-state counting
(`regime_classifier_logger.py`, PROTECTED)

Same anti-inflation principle as shadow episode counting: back-to-back reruns
of an unchanged market state are one observation, not N. In the **accuracy
tally layer only** (`get_regime_accuracy` / `get_accuracy_report`):

- rows collapse into one independent state when they share
  `(instrument, prediction_type, price_at_log, adx_d1, adx_h4)` AND fall
  within one outcome window (`prediction_window` daily bars) of the state's
  first row;
- a collapsed state counts once; its outcome is the FIRST row's outcome (the
  original observation — later identical rows are echoes of it);
- the report prints independent-state N alongside raw row count so the
  deflation is visible, never silent.

`check_pending_outcomes` still fills every row — the ledger stays complete;
only the *counting* dedupes. Verified against the live ledger: the 22 pending
2026-07-29 rows = 5 independent states; the three 2026-06-28 filled rows
remain 3 (distinct snapshots).

## Housekeeping f (ledger half) — synthetic row removal

`session_context_log.csv` line 17 (`2026-07-29T04:23:31Z, GBP_AUD, ADX
100.0/100.0, filter_allowed=True`) is a test fixture written into the live
ledger — impossible market values, the only `filter_allowed=True` row of its
day. **Team-directed one-time removal** (post-audit directive item f),
recorded in `validation_log.md` with what/why. This is an explicit,
documented exception to the never-edit-ledgers rule, made by the team, not
by an agent's judgment; the row's full content is preserved in the log entry.

## Item 3 — validation_log entries (append-only)

(a) "First shadow grading 2026-09-08" — Episode 1 = −1.0R from the one valid
row; rows 2–3 invalid_spec, excluded; THRUST_PULLBACK / MOMENTUM_JOIN stops
valid by construction (opposite box edge / 1.5×ATR — verified in code).
Clears the Gate-3 "first shadow grading" pending item with date + evidence.

(b) "39-day outage post-mortem" — root cause, what was lost (5 weeks of
shadow evaluation, unrecoverable), what was recovered, and the honest current
status: **the scheduled path is still failing as of 2026-09-09** (credentials
live in the interactive shell; launchd starts wrappers in a bare env and
`oanda_feed` reads `os.environ` only). The fix is sequenced into the
heartbeat spec (Branch 3), where the wrappers are already under edit.

## Housekeeping c / d / e

- **c.** Install `com.quis.intelligence.calendar.plist` (present in repo,
  never loaded). Gate-3 "first Sunday fetch" stays open until it fires.
- **d.** AGENTS.md: add `calendar_fetch.py` and `setup_check.py` to the
  PROTECTED list (dated note) — both sit on the automated / decision-adjacent
  path; the review boundary must match the execution boundary.
- **e.** Commit `studies/level_fade_study.py` and write its refutation entry
  from a fresh real run's actual output (evidence honesty: the entry cites
  numbers the run actually printed, not remembered ones).

## Gates

- **Gate 1:** pinned tests — invalid_spec predicate both directions,
  exclusion from tally/episodes/pending, grader skip, regime independent-state
  collapse (echo runs collapse; distinct snapshots don't).
- **Gate 2 (REALITY):** real-ledger run showing EARLY_MOMENTUM tallies with
  rows 2–3 excluded (1 row / 1 episode / 1 graded), real
  `run_outcome_check.py` output, real `get_accuracy_report` showing 5
  independent states pending, `launchctl list` showing the calendar job
  loaded, real `level_fade_study.py` output.
