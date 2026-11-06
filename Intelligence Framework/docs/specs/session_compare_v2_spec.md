# Spec v2: compare every scheduled run with the previous one; flips always alert, character changes go to the digest

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**Supersedes:** `session_compare_spec.md`. That file is unchanged on disk. Both
reviewers returned APPROVE WITH CHANGES and neither passed rule 12 (validation_log
2026-11-05 TEAM REVIEW round 2).
**Protected:** `session_memory.py`, `decision_brief.py`.
**Also touches (free zone):**
- `scripts/scheduled_brief.sh` (run lock, run source);
- `scripts/daily_digest.py` (the character-change clause);
- `.gitignore` (the lock directory).

**Owner decisions applied (validation_log 2026-11-05, "FIXED (free zone): the
digest's watch clause…", decisions 1–2):**
1. **Decision flips** (filter allowed ↔ stand aside) and **exit-watch** always
   alert, whatever the gap or price move. Only **character changes**
   (a regime-only change, STAND ASIDE on both sides) are gated. The size gate is
   withdrawn.
2. **Option (a).** Evening alerts only for decision flips and exit-watch.
   Character changes go to the digest. The precondition, the digest naming its
   pair (c177531), has landed, so (a) is unblocked.

## 1. Why (unchanged from v1, re-verified)

- **The evening run never compares.**
  - `session_memory._get_today_rows` keeps only rows whose timestamp starts
    with today's UTC date (`session_memory.py:344-359`, the test at :351-352).
  - The 18:00 PT run is the first row of its UTC day, so `get_session_delta`
    returns None (`:113-115`), and `_machine_flags` returns `[]` on no delta
    (`decision_brief.py:1276-1278`).
  - OBSERVED today: the 18:00 rows `2026-11-06T02:00:05Z` (GBP_AUD) and
    `02:00:06Z` (GBP_JPY) in `session_context_log.csv` are the first of their
    UTC day.
- **Missed changes.**
  - Adversarial replay: GBP/JPY's filter went from allowed to stand aside at
    the 2026-10-14 evening run, and no alert went out.
  - Since the 2026-09-30 rules, a previous-run reader would have raised 16 new
    alerts: 2 filter flips and 14 regime-only.
- **`None` means three things.**
  - It covers a first run, a missing ledger, and any exception (`:209-210`,
    a bare `except` that says nothing).
  - When this run's row was not written, the function compares the two
    previous rows and prints "Conditions unchanged". Reproduced by the code
    reviewer.
- **"Conditions unchanged" ignores price** (`:341`). There is no price column
  (`FIELDNAMES`, `:32-41`).

## 2. Change

### 2.1 Run identity and serialization (review S1, code review 6)

- **`run_id`.** `decision_brief.py`'s `__main__` makes one `run_id` per process:
  UTC `YYYYMMDDTHHMMSSZ` plus `-<pid>`. It is passed to
  `log_session_snapshot(..., run_id=...)` and written to a new `run_id`
  column. `get_session_delta(instrument, run_id)` finds this run's own row by
  `run_id`, never by timestamp.
  - Why: three wrappers wrote same-second rows on 2026-09-14 at 16:16:48–49Z
    (OBSERVED in the ledger).
- **Run lock in the wrapper.**
  - `scheduled_brief.sh` takes an mkdir lock (`$PROJ/.brief_run.lock`,
    gitignored) before `decision_brief.py` and releases it after. Catch-up
    runs then execute one after another.
  - It uses mkdir because launchd runs bash 3.2 (`test_shell_syntax.py`).
  - The lock holds a PID file. A lock whose PID is not alive is taken over.
  - If the wait exceeds 120 s, the run proceeds and the SESSION status is
    `not checked (runs overlapped)`. It is never `compared`.
- **The read happens under the append's lock.** `log_session_snapshot`
  appends and reads back the previous row inside one `ledger_io.locked`
  span, so no other process can append between them. It returns the row it
  wrote (or None) for `get_session_delta` to use.

### 2.2 Which row is "previous" (review S5, S6; code review 4)

- **Run source.**
  - A new `run_source` column holds `scheduled` when the wrapper set
    `INTEL_RUN_SOURCE=scheduled`, and `manual` otherwise.
  - **A scheduled run compares with the previous scheduled row for the
    instrument, whatever its calendar day.**
  - A manual run compares with the previous row of either source. It prints
    its SESSION line and emits no `##ALERT##` line. So a manual or agent run
    can never use up the scheduled comparison.
  - OBSERVED off-schedule rows: 2026-10-15 02:20 PDT and 10-19 19:49 PDT.
- **Rows written before this ships** have no `run_source`. They count as
  scheduled for the first comparison only. That one-time transition is
  tested (§5).
- **Exclusions stay.** The new reader applies
  `exclusions.filter_rows(rows, "session_context_log.csv")`, as today
  (`session_memory.py:359`), with a mutation that drops it (code review 5).

### 2.3 One status, always returned (review S2, S5; code review 4, 7)

`get_session_delta` always returns a dict with `status` and, when it applies,
`reason`:

| status | When | SESSION line (plain English, via `display_time`) | Flags? |
|---|---|---|---|
| `compared` | Own row found, previous scheduled row ≤ 7 days old, same `logic_version` | Change text, or "Same regimes, structure and filter since 7:33 AM; price +137 pips (1.2× a normal day's range)" | yes |
| `compared, rules changed` | As above, but different `logic_version` | Regime/structure change text, plus "filter not compared (rules changed)" | regime only, as a character change; never a filter flip (existing guard, `:146-152`) |
| `first run` | No earlier row for the instrument, ever | "First run for this pair" | no |
| `no recent run` | Previous row older than 7 days | "No run within 7 days (last Wed 23 Dec, 7:33 AM)" | no |
| `not checked` | Own row missing, a read error, or runs overlapped | "Not checked — <reason>". The reason also goes to stderr, so the day log has it | no |
| `market closed` | No snapshot by design (`:56-57`) | "Market closed — not compared" | no |

- **These strings are the only source of the change status** for
  `brief_summary_block_spec.md` §3. Its "first run today" and "no change since
  7:33 AM" are superseded: "today" is wrong under previous-run semantics, and
  "no change" hides price.
- **Examples use real times.** "Since Fri 6:00 PM" cannot occur: Friday 18:00 PT
  is market-closed, and the ledger has 0 Friday 18:xx rows. A weekend gap
  reads "since Fri 7:33 AM".
- **"Same … filter"** appears only under `compared`. Under `rules changed` the
  line names what it did not compare (review S2: today's code returns
  "Conditions unchanged" across a rules change, DEMONSTRATED).

### 2.4 Price in "unchanged" (code review 2)

- **New columns** (additive, via `ledger_io.migrate_header`, inside
  `_append_row` as today, `:362-370`):
  - `price` (the regime's `current_price`);
  - `price_basis` (`live` / `prior_close` / `market_closed`, set at
    `regime_detection.py:872-878`);
  - `atr_pips` (this run's daily ATR).
- **A move is shown only when both rows are `live`.** Otherwise:
  - "price not comparable" when a basis differs;
  - "price not recorded" when a row has no price (pre-migration rows).
  - **Never 0** (rule 9).
- **Display only.** A price move raises no alert.

### 2.5 Classification and routing (owner decisions 1–2; review S3, S4)

`get_session_delta` returns `changes`, a list of classes, computed once.
`_machine_flags` reads that list instead of parsing summary text: its
`"CONDITIONS IMPROVED" in summary` branches (`decision_brief.py:1293-1297`) are
unreachable today, because `_build_summary` emits those words only when
`filter_changed` (`session_memory.py:319-325`). They are removed.

| Class | Definition | Route on every scheduled run |
|---|---|---|
| `decision_flip` | `filter_allowed` differs, same `logic_version` | **ALERT, always**: no gap or size gate, any hour, any gap length ≤ 7 days |
| `exit_watch` | the `_machine_flags` class (b) conditions, as amended by `watch_for_truth_v2_spec.md` if that merges first (§7) | **ALERT, always** |
| `character` | D1 or H4 regime changed, or structure confirmed from TRANSITIONAL, with `filter_allowed` False on both rows (STAND ASIDE both sides), or across a rules change | **No phone notification.** SESSION line shows it; the next 07:30 digest carries it (§2.6) |
| `regime_while_allowed` | regime changed with `filter_allowed` True on both rows | ALERT (a live trade's context changed; rare, tested) |

- **One rule for every run.** The rule applies the same way at 02:30, 07:30
  and 18:00. The owner's words were "evening alerts"; §8 question 1 confirms
  this reading.
- **This removes an existing alert.** Today a 02:30 or 07:30 run that sees a
  regime-only change sends an ALERT: all 5 ALERTs in `notification_log.csv`
  are of that kind (adversarial review S3). Under this spec they go to the
  digest. That is a change to an existing notification path, tested in §3.
- **Nothing is suppressed permanently** (review S4b). A character change is
  never dropped. It is shown in this run's SESSION line, and the digest finds
  it from the ledger, whatever later runs compare.

### 2.6 The digest's character clause (option a)

- **Source.** `scripts/daily_digest.py` gains a clause built from
  `session_context_log.csv`, not from day logs (adversarial review R2: the
  day-log parse renders garbage on 2026-09-14).
  - It reads rows with stdlib `csv` plus `exclusions.filter_rows`
    (`exclusions.py` imports only the stdlib, :40-45).
  - It uses scheduled rows written after the previous `DIGEST` row's
    `timestamp_utc` in `notification_log.csv`.
- **What it counts.** Per pair, the `character` changes between adjacent
  compared rows, plus the net state, first row against last.
- **Wording:**
  - one change: `· GBP/JPY 4-hour: trending up → moving sideways since Thu 6:00 PM (still stand aside)`;
  - several: `· 2 character changes since last digest`.
- **Never dropped.** The short marker survives every length cut. The
  osascript cut keeps the first 220 characters, so the marker goes **before**
  the watch clause.
- **Shared length test.** It runs the longest real watch clause together with
  this clause and the shadow marker of the pending shadow-digest v2, so the
  two specs cannot jointly overflow (code review 5 on the shadow spec).
- **Rule 9.** An unreadable ledger renders `· changes since last digest: not checked`, never silence.

## 3. Rule 12: should it reach the owner?

Every row is a Gate-1 test through the real wrapper (§5).

| # | Case | Market | Change vs previous scheduled run | Expected notification |
|---|---|---|---|---|
| 1 | Evening, filter stand-aside → allowed | open | decision flip | **ALERT** "GBP/JPY: conditions improved — the framework now allows a trade", since 7:33 AM |
| 2 | Evening, allowed → stand aside | open | decision flip | **ALERT** "…has stood down since 7:33 AM" |
| 3 | Evening, 4-hour regime changed, stand aside both | open | character | **none** at 18:00; SESSION shows it; next digest carries it |
| 4 | 02:30 or 07:30, regime changed, stand aside both | open | character | **none**; digest. Today this sends an ALERT (old → new, dated) |
| 5 | Evening, nothing changed, price moved 137 pips | open | none | **none**; SESSION "Same … since 7:33 AM; price +137 pips (…)" |
| 6 | Exit-watch condition newly met | open | exit_watch | **ALERT**, any hour |
| 7 | Sunday 18:00 after the weekend, filter flipped Friday afternoon | open | decision flip (gap 58.5 h) | **ALERT** "…since Fri 7:33 AM". No size gate |
| 8 | Same, regime-only | open | character | **none**; Monday digest |
| 9 | Friday 18:00, Saturday ×3, Sunday 02:30 and 07:30 (closed), Sunday 18:00 open | closed → open | closed rows: no snapshot | **0 notifications** on the closed runs; only row 7/8's outcome at Sunday 18:00 (review S7) |
| 10 | Three wrappers in the same second (catch-up after sleep) | open | run 1 sees the change | **One** ALERT (run 1), runs 2–3 compare with run 1 and are quiet |
| 11 | A manual run at 10:00 sees the flip; 18:00 scheduled run | open | flip vs previous scheduled row | **ALERT at 18:00** (the manual run did not use up the comparison); the manual run itself sends nothing |
| 12 | Decision rules changed between the rows, filter differs | open | rules changed | **none**; SESSION "filter not compared (rules changed)" |
| 13 | Own row not written (write error) | open | not checked | **none**; SESSION "Not checked — snapshot not written"; reason in day log |
| 14 | Previous row 9 days old (outage) | open | no recent run | **none**; SESSION "No run within 7 days (last …)" |
| 15 | Very first row for the pair | open | first run | **none** |
| 16 | Regime change while the filter allowed a trade on both rows | open | regime_while_allowed | **ALERT** |
| 17 | 07:30 digest after row 3 or 4 | open | — | DIGEST includes the character clause naming pair and change |
| 18 | Error page (framework error) | — | no snapshot (`get_decision_brief` returns `_error_brief` before logging, `decision_brief.py:304-306`) | existing health ALERT only; no session flag |

## 4. Out of scope

- Which file an alert opens (`alert_opens_own_run_v2_spec.md`).
- Shadow notifications (shadow-digest v2, waiting on the retirement decision).
- WATCH FOR wording and the exit-watch definitions (`watch_for_truth_v2_spec.md`).
- SESSION-note wording other than "Conditions unchanged" and the status
  strings (display-claims spec, inventory item 5).

## 5. Gates

**Gate 1 (controlled inputs):**
- **Session memory**, on temp ledgers with a frozen clock:
  - 02:30, 07:30 and 18:00 PT in PST and PDT: the 18:00 run compares with
    07:30, and 02:30 with 18:00;
  - first run ever; 9-day gap; a corrupt row; a missing ledger; own row not
    written;
  - same-second rows with distinct `run_id`s;
  - manual between scheduled rows;
  - pre-migration rows without `run_source`, `price`, `price_basis`
    (one-time transition; price "not recorded");
  - `prior_close` beside `live` ("not comparable");
  - an excluded row is skipped;
  - rules changed.
- **The real chain** (code review 8): the real `decision_brief.py` `__main__`
  with a mocked `get_regime`, so session_memory → `_machine_flags` → stderr
  `##ALERT##` → the real `scheduled_brief.sh` (sandbox project and stub
  notifier, `tests/test_wrapper_behavior.py` helpers). One test per §3 row,
  asserting the exact notifications, categories and summaries.
- **Lock:** two wrappers started together run in sequence; a stale lock with
  a dead PID is taken over; a held lock past 120 s gives `not checked (runs
  overlapped)`.
- **Digest:** the character clause from a ledger fixture; marker position
  under the 220 and 400 cuts; the joint length test with the longest watch
  clause; unreadable ledger → "not checked".
- **Floors:** stand-down matrix T34–T41 and the banned-token test pass
  unweakened. DECISION and filter are identical across `test_decision_logic.py`.

**Mutation** (each must be caught):
- revert to the UTC-day filter;
- identify the own row by timestamp;
- let manual rows serve as the scheduled baseline;
- drop the exclusions filter;
- render "Same … filter" under `rules changed`;
- flag under `first run` or `no recent run`;
- gate a decision flip on gap length;
- send a character change as an ALERT;
- drop the digest marker under the 220 cut;
- compare a `prior_close` price as a move.

**Gate 2:** `scripts/reality_run.py --code <worktree> brief` at an evening hour
against copies of the live ledgers. It shows a `compared` SESSION line where
`main` shows none, with the project unchanged by hash. Separately, the real
wrapper in a sandbox replays 3 real day-log sequences with stub notifiers.

**Gate 3, PENDING LIVE CONFIRMATION:**
- the first scheduled 18:00 run after merge shows a `compared` SESSION line;
- the first real evening decision flip sends one ALERT;
- the first real character change appears in the next digest and nowhere
  else.

## 6. Limits

- **Detection is no faster than the runs.** A flip between runs is reported at
  the next scheduled run, up to about 10.5 hours later (07:30 → 18:00).
- **Net state can hide a round trip.** The digest's net-state wording can hide
  a change that reversed between digests. The change count says so.

## 7. Merge order

`_machine_flags` is edited by this spec and by `watch_for_truth_v2_spec.md`;
`session_memory.py` by this spec and the display-claims spec (SESSION notes,
item 5). Recommended order:
1. `watch_for_truth_v2_spec.md` first, so the exit-watch flags are true
   before evening runs start sending them;
2. this spec;
3. the display-claims spec's SESSION-note fixes, rebased on §2.3's strings.

If the team prefers this spec first, class (b) ships unchanged and its
evening use is listed in Gate 3 (adversarial review W4).

## 8. Questions for the team

1. **"Evening alerts only for decision flips and exit-watch"**: apply to every
   run (recommended; removes today's 02:30/07:30 regime-only ALERTs, row 4),
   or to the evening run only?
2. **Lock wait:** 120 s, then proceed as `not checked`?
3. **Row 16** (regime change while allowed both sides): ALERT as proposed?
