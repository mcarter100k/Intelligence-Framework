# Spec: compare every run with the previous run, and say honestly when it didn't

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**Protected:** `session_memory.py`, `decision_brief.py`.
**Source:** the 2026-11-05 TEAM REVIEW entry in validation_log (defects 1–3).

## 1. Why

**The evening run never compares, so it can never raise a flip alert.**
- `session_memory._get_today_rows` keeps rows whose timestamp starts with
  today's **UTC** date.
- UTC midnight is 16:00 PST (17:00 PDT), between the 07:30 and 18:00 runs, so
  the 18:00 run is the first row of its UTC day.
- `get_session_delta` therefore returns None at 18:00, and `_machine_flags`
  returns `[]` on no delta.
- No regime-change, filter-flip or exit-watch alert can fire on the evening run.
- The 02:30 run compares only with 18:00, so a change between 07:30 and 18:00 is
  never compared at all.

**Evidence:**
- VERIFIED by both reviewers on temp ledger copies.
- OBSERVED: `logs/brief_2026-11-04.log` has SESSION lines for the 02:33 and
  08:37 runs only.
- OBSERVED: GBP/JPY's 4-hour went VOLATILE → TRENDING_UP between 15:33Z
  11-03 and 02:00Z 11-04, with no ALERT row.
- VERIFIED by a read-only count of `session_context_log.csv`, 2026-09-09 → 11-05
  (2026-11-05, specs round). 76 rows are the first of their UTC day. Against
  the previous row for the same pair, 34 changed D1 regime, H4 regime, D1
  structure or (same logic version) the filter:

  | Gap to the previous row | Rows | Changed |
  |---|---|---|
  | under 12 h (the evening run) | 56 | 23 |
  | 12–36 h | 2 | 1 |
  | over 36 h (weekends) | 18 | 10 |

  Every one of those changes went uncompared.

**`None` means three things.**
- `get_session_delta` returns None for:
  - a genuine first run;
  - a missing ledger;
  - any exception (a corrupt row).
- When this run's snapshot was not written, it compares the two previous rows
  and reports "Conditions unchanged" for a comparison that never involved this
  run. A write failure is swallowed in `log_session_snapshot`; a closed market
  skips the write by design. Reproduced by the code reviewer.
- Rule 9: a zero from an unverified path is not data.

**"Conditions unchanged" ignores price.**
- OBSERVED: GBP/AUD moved 137 pips (daily range 114) between the 02:44 and
  07:33 runs on 11-05 under that line.
- The snapshot has no price column.

## 2. Change

1. **Previous run, not "today".** Compare this run's row with the previous row
   for the same instrument, whatever the calendar day.
   - The prior time is rendered through `display_time` with its day when it is
     not today: "since 7:33 AM", "since Fri 6:00 PM".
   - The reader scans only recent rows (for example the last 7 days) so the
     ledger's growth does not slow the brief.
2. **This run's own row.** `log_session_snapshot` returns the timestamp it
   wrote, or None. `get_session_delta(instrument, own_ts)` compares only when
   the newest row is exactly `own_ts`.
3. **An explicit status, always returned:**
   - `compared`;
   - `first run` (no earlier row for the instrument);
   - `not checked` (own row not written, not newest, or a read error; the reason
     is kept);
   - `market closed` (no snapshot by design).

   The brief's SESSION line renders each status in its own words. "Conditions
   unchanged" appears only under `compared`.
4. **Say what "unchanged" covers.**
   - Wording: "Same regimes, structure and filter since <time>".
   - Add a `price` column (additive, `ledger_io.migrate_header`) holding the
     regime's `current_price`.
   - Show the move: "price +137 pips (1.2 daily ranges)".
   - **Display only.** A price move raises no alert (see question 2).
5. **`_machine_flags` reads the new status** and emits flags only under
   `compared`. Its logic is otherwise unchanged; the `same_rules` filter guard
   stays.

## 3. Rule 12: this adds alerts

On the history above, at most about 23 extra evening notifications over 8
weeks. That is fewer than 3 a week for both pairs, because one run sends one
joined ALERT. Plus up to 10 after weekend gaps. Each case is tested for
whether it should reach the owner:

| Case | Expected |
|---|---|
| Evening run, regime changed since 07:30 | One ALERT naming the pair, saying "since 7:33 AM" |
| Evening run, nothing changed | No notification |
| Market closed (no snapshot) | No notification; SESSION says market closed |
| First run after the weekend, regime changed | Team decides (question 1); the text names "since Fri 6:00 PM" |
| Own row not written / read error | No notification; SESSION says not checked; the failure is in the day log |
| Decision rules changed between the rows | No filter-flip alert (existing guard) |
| Two runs in the same minute | The second compares with the first; no duplicate alert for the same change |

## 4. Out of scope

- Which file an alert opens (`alert_opens_own_run_spec.md`).
- Shadow notifications (`shadow_digest_only_spec.md`).
- WATCH FOR wording (`watch_for_truth_spec.md`).
- The exit-watch approximations in `_machine_flags` class (b), beyond reading the
  new status.

## 5. Gates

**Gate 1:**
- On temp ledgers with a frozen clock:
  - 02:30, 07:30 and 18:00 Pacific in both PST and PDT; the 18:00 run compares
    with 07:30.
  - First run ever; weekend gap; a corrupt row; a missing ledger.
  - Own row not written: status `not checked`, never "unchanged".
  - Two same-second rows.
- The price column migrates additively. Old rows read with an empty price, and
  the move renders as "price not recorded", never as 0.
- The real wrapper, for every row of the §3 table: notifications sent,
  categories and summaries.
- Floors: stand-down matrix T34–T41 and the banned-token test pass unweakened.
  DECISION and filter are unchanged across `test_decision_logic.py`.

**Mutation:**
- Revert to the UTC-day filter.
- Drop the own-row check.
- Render "unchanged" under `not checked`.
- Flag under `first run`.
- Drop the price column from the comparison display.

Each must be caught.

**Gate 2:** a real brief under `scripts/reality_run.py`, run at an evening hour
against copies of the live ledgers. It shows a compared SESSION line where `main`
shows none, and the project is unchanged by hash.

**Gate 3, PENDING LIVE CONFIRMATION:**
- The first scheduled 18:00 run after merge shows a compared SESSION line.
- The first real evening flip sends one ALERT.

## 6. Questions for the team

1. **Weekend and gap flips: alert or show only?** Recommended: alert, with
   "since <day time>" in the text. A regime change across the weekend is new on
   Sunday evening.
2. **Should a large price move with no regime change ever notify?** Recommended:
   no, display only. It would be a new alert class with no evidence behind it.
3. **Reader window:** 7 days. Longer gaps render as "first run since <date>" and
   do not alert.
