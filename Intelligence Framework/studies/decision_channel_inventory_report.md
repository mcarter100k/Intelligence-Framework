# Decision-channel inventory (Phase 2)

Spec: `docs/specs/decision_channel_measurement_spec.md` (frozen at c151e3c). Counts and windows only: no prices, no accuracy, no R.

H4 bar index fetched 2026-10-18T02:19:07Z (timestamps only): GBP_AUD 901 bars 2026-03-20T17:00:00Z → 2026-10-16T17:00:00Z, GBP_JPY 901 bars 2026-03-20T17:00:00Z → 2026-10-16T17:00:00Z

## 1. Where decision history survives

- **Day logs** `logs/brief_*.log`: 79 files with runs, 241 runs, 2026-07-29 02:33:10 PDT → 2026-10-17 18:06:54 PDT (2026-07-29T09:33:10Z → 2026-10-18T01:06:54Z). Header zones: {'PDT': 215, 'MDT': 4, 'EDT': 22}. Form: the full brief text per run, two instrument blocks.
- **Concurrent run groups** (identical header stamp, merged into one observation; accepted only if every copy agrees and none is an error page — parser rule added after the spec commit, format only): 3. 2026-09-09 00:32:26 EDT ×2 → GBP_AUD RUN ERRORED, GBP_JPY RUN ERRORED; 2026-09-14 09:16:50 PDT ×3 → GBP_AUD STAND ASIDE, GBP_JPY SHORT; 2026-10-08 10:03:57 PDT ×3 → GBP_AUD RUN ERRORED, GBP_JPY RUN ERRORED
- **trade_signal_log.csv**: 13 rows, 2026-06-28T21:39:15Z → 2026-10-13T14:30:07Z; 0 excluded by the registry. Form: one row per logged directional signal.

| signal_id | ledger direction | matching day-log run (±10 min) | day-log decision |
|---|---|---|---|
| 2026-06-28T21:39:15Z_GBP_AUD | LONG | NONE | — |
| 2026-09-25T01:01:54Z_GBP_JPY | SHORT | 2026-09-24 18:01:55 PDT | SHORT |
| 2026-09-25T09:36:42Z_GBP_JPY | SHORT | 2026-09-25 02:36:44 PDT | SHORT |
| 2026-09-25T14:41:38Z_GBP_JPY | SHORT | 2026-09-25 07:41:40 PDT | SHORT |
| 2026-10-09T01:00:09Z_GBP_JPY | SHORT | 2026-10-08 18:00:11 PDT | SHORT |
| 2026-10-09T09:30:08Z_GBP_JPY | SHORT | 2026-10-09 02:30:10 PDT | SHORT |
| 2026-10-09T14:30:04Z_GBP_JPY | SHORT | 2026-10-09 07:30:06 PDT | SHORT |
| 2026-10-12T01:00:09Z_GBP_JPY | SHORT | 2026-10-11 18:00:10 PDT | SHORT |
| 2026-10-12T09:44:31Z_GBP_JPY | SHORT | 2026-10-12 02:44:32 PDT | SHORT |
| 2026-10-12T14:38:38Z_GBP_JPY | SHORT | 2026-10-12 07:38:40 PDT | SHORT |
| 2026-10-13T01:05:32Z_GBP_JPY | SHORT | 2026-10-12 18:05:33 PDT | SHORT |
| 2026-10-13T09:33:35Z_GBP_JPY | SHORT | 2026-10-13 02:33:36 PDT | SHORT |
| 2026-10-13T14:30:07Z_GBP_JPY | SHORT | 2026-10-13 07:30:08 PDT | SHORT |

## 2–3. Status counts per instrument (each run × instrument is exactly one)

| instrument | LONG (open) | SHORT (open) | STAND ASIDE (open) | MARKET CLOSED | of which closed+directional | RUN ERRORED | registry-dropped |
|---|---|---|---|---|---|---|---|
| GBP_AUD | 0 | 3 | 79 | 31 | 6 | 128 | 0 |
| GBP_JPY | 0 | 13 | 69 | 31 | 8 | 128 | 0 |

Runs that would raise a DECISION notification: old trigger 28, with the Phase 0 market-status gate 16 (derived from the parsed statuses; the real wrapper replay is in the Gate 2 report).

## 4. UNOBSERVED windows

| kind | window (header times) | cause | size |
|---|---|---|---|
| start of record | everything before 2026-07-29 | no day log exists before the first wrapper run | — |
| RUN ERRORED | 2026-07-29 07:30:05 PDT → 2026-07-29 18:00:06 PDT (last good before: 2026-07-29 02:33:10 PDT; first good after: 2026-07-29 19:08:44 PDT) | Framework error — do not trade: OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_I ×2 | 2 run(s), GBP_AUD+GBP_JPY |
| RUN ERRORED | 2026-07-30 02:30:06 PDT → 2026-07-31 18:06:14 PDT (last good before: 2026-07-29 19:08:44 PDT; first good after: 2026-07-31 20:57:00 PDT) | Framework error — do not trade: OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_I ×6 | 6 run(s), GBP_AUD+GBP_JPY |
| RUN ERRORED | 2026-08-01 02:34:57 PDT → 2026-09-09 00:32:26 EDT (last good before: 2026-07-31 20:57:00 PDT; first good after: 2026-09-09 00:32:38 EDT) | Framework error — do not trade: OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_I ×117; 2 concurrent runs, error page in output ×1 | 118 run(s), GBP_AUD+GBP_JPY |
| RUN ERRORED | 2026-09-16 18:01:27 PDT → 2026-09-16 18:01:27 PDT (last good before: 2026-09-16 07:30:08 PDT; first good after: 2026-09-17 02:39:41 PDT) | Framework error — do not trade: Not enough data to calculate regime indicators ×1 | 1 run(s), GBP_AUD+GBP_JPY |
| RUN ERRORED | 2026-10-08 10:03:57 PDT → 2026-10-08 10:03:57 PDT (last good before: 2026-10-06 07:32:43 PDT; first good after: 2026-10-08 18:00:11 PDT) | 3 concurrent runs, error page in output ×1 | 1 run(s), GBP_AUD+GBP_JPY |
| SCHEDULER GAP | 2026-09-12 02:43:17 PDT → 2026-09-14 09:16:50 PDT | no run for 54.6 h | — |
| SCHEDULER GAP | 2026-10-06 07:32:43 PDT → 2026-10-08 10:03:57 PDT | no run for 50.5 h | — |

## 5. Exclusion registry

- `2026-09-16T09:08:08Z` (session_context_log.csv, authorized by: validation_log.md 2026-09-16 — CORRECTION: two ledger rows contaminated by the Gate 2 verification run): day-log runs matched within 60s: none
- `2026-09-16T09:08:08Z_GBP_AUD` (regime_classification_log.csv, authorized by: validation_log.md 2026-09-16 — CORRECTION: two ledger rows contaminated by the Gate 2 verification run): day-log runs matched within 60s: none

## 2 & 6. Onsets, episodes, gradeability

### GBP_AUD

Raw directional DECISION occurrences: 9. Onsets (state changes into LONG/SHORT): 2. Independent episodes (30-bar spacing on the H4 index): 2.

| onset run | direction | bar | episode? | signal run (first open) | status |
|---|---|---|---|---|---|
| 2026-09-10 18:04:14 PDT | SHORT | 746 | yes | 2026-09-10 18:04:14 PDT | ELIGIBLE (structure and leg-minimum not yet checked) |
| 2026-10-16 18:12:44 PDT | LONG | 900 | yes | — | AWAITING OPEN |

### GBP_JPY

Raw directional DECISION occurrences: 21. Onsets (state changes into LONG/SHORT): 3. Independent episodes (30-bar spacing on the H4 index): 3.

| onset run | direction | bar | episode? | signal run (first open) | status |
|---|---|---|---|---|---|
| 2026-09-11 18:02:16 PDT | SHORT | 750 | yes | 2026-09-14 09:16:50 PDT | ELIGIBLE (structure and leg-minimum not yet checked) |
| 2026-09-24 18:01:55 PDT | SHORT | 806 | yes | 2026-09-24 18:01:55 PDT | ELIGIBLE (structure and leg-minimum not yet checked) |
| 2026-10-08 18:00:11 PDT | SHORT | 866 | yes | 2026-10-08 18:00:11 PDT | ONSET-CENSORED — 1 errored run(s) between; 1 scheduler gap(s) > 12h between |

### Gradeability (pooled)

- AWAITING OPEN: 1
- ELIGIBLE: 3
- ONSET-CENSORED: 1

**Gradeable for Measurement A: at most 3.** Structure-undefined and sub-minimum legs need prices and can only lower this number.

**STOP RULE MET (fewer than 10).** Measurement A is not run. The owner decides whether to run or wait.
