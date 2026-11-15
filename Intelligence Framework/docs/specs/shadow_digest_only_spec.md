# Spec: shadow signals go to the daily digest, not their own notification

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**SUPERSEDED 2026-11-15** by `docs/specs/alert_importance_spec.md` (N3, N4),
which adopts this design with the shadow clause read from the ledger.
**Scope:** `scripts/scheduled_brief.sh`, `scripts/scheduled_outcome_check.sh`,
`scripts/daily_digest.py` (free zone, but a notification path: rule 12).
**Owner decision, 2026-11-05:** shadow signals no longer notify on their own;
they appear in the 07:30 digest (answer: "Digest only").

## 1. Why

- **SHADOW is most of what reaches the owner.**
  - VERIFIED, count of `notification_log.csv` on 2026-11-05: 14 of 37
    notifications ever sent were SHADOW. The rest were ALERT 5, DIGEST 16 and
    HEARTBEAT 2.
  - OBSERVED: three of the four notifications stamped 2026-11-03 (UTC) were
    SHADOW.
- **Nothing in a shadow signal can be acted on.** It is logged, never traded,
  and the brief says so. EARLY_MOMENTUM_v2, the candidate that fires most, was
  REFUTED on 2005–2013 (R42).
- **The SHADOW summary already leaks.**
  - The wrapper builds it with an unanchored
    `grep -E 'EARLY_MOMENTUM|THRUST_PULLBACK|MOMENTUM_JOIN'`
    (`scheduled_brief.sh`, the SUMMARY block).
  - OBSERVED: summaries quote THE FULL PICTURE text ("EARLY_MOMENTUM_v2
    candidate: LONG entered at · …").

## 2. Change

1. **Brief wrapper.**
   - Remove the SHADOW category.
   - Remove the candidate-name grep from the DECISION summary, which becomes
     the decisions only.
   - The shadow-candidate ERROR path is unchanged: `SHADOW_ERR` still rides the
     health plumbing to an ALERT after two consecutive failures.
2. **Digest.**
   - `daily_digest.py` adds one clause when any candidate fired since the
     previous digest: `· shadow (not traded): EARLY_MOMENTUM_v2 GBP/JPY LONG
     212.23 (+1 more)`.
   - It names at most one fire plus a count.
   - The clause comes last, and the line before the `→` pointer stays at or
     under 300 characters, so `notify.sh`'s 400 cut and the osascript 220 cut
     drop the shadow clause before the decisions or the watch.
   - Fires are read from the anchored `SHADOW SIGNALS` block (`^ ? ?SHADOW
     SIGNALS`) of each run since the previous digest, never by grepping
     candidate names anywhere in the text.
3. **Outcomes wrapper ("shadow graded" SHADOW notification).** Team decides
   (question 1). Recommended: remove it too. The tally is in every brief, and a
   nightly grading ping is the same kind of notification the owner turned off.
4. **Notification ledger.** No new SHADOW rows from the brief wrapper, and from
   the outcomes wrapper if (3) is approved. Old rows stay.
   `trader_review.py` counts all notifications weekly, so its count drops; it
   reads no category.

## 3. Rule 12

| Case | Expected |
|---|---|
| Stand-aside run, a candidate fires | No notification; the fire is in the brief and the next digest |
| DECISION LONG run, a candidate fires | One DECISION notification; its summary names no candidate |
| Candidate raises (ERROR) twice | Health ALERT, as today |
| 07:30 digest, fires since the last digest | The digest line ends with the shadow clause |
| 07:30 digest, no fires | The digest line is unchanged from today |
| Market closed digest | Unchanged from today; a shadow clause only if a fire happened |
| Outcomes graded | No notification (if question 1 is approved) |
| Feed text containing a candidate name or "SHADOW SIGNALS" at a wrapped indent | Neither digest nor summary is changed |

## 4. Out of scope

Candidate logic, grading and ledgers. The candidates keep logging (frozen);
what to do with the REFUTED ones is a separate team decision (R40–R42).

## 5. Gates

**Gate 1:**
- The real wrapper for each §3 row.
- Old → new test changes recorded with dates: `test_wrapper_behavior.py` shadow
  routing tests (about lines 183, 295, 338) and the outcomes routing test (about
  473). No floor test is touched.
- Positive control: a SHADOW SIGNALS block at 0–2 spaces is read; the same
  text at 13 spaces is not.

**Mutation:**
- SHADOW category restored.
- Candidate grep restored in the DECISION summary.
- Digest reads names unanchored.
- Shadow clause placed before the decisions.
- `SHADOW_ERR` path removed.

Each must be caught.

**Gate 2:** a real `scheduled_brief.sh digest` run and a non-digest run under
`scripts/reality_run.py`, with notifications stubbed and the project unchanged
by hash.

**Gate 3, PENDING LIVE CONFIRMATION:** the first real shadow fire after merge
sends nothing, and appears in the next 07:30 digest.

## 6. Questions for the team

1. Remove the outcomes wrapper's "shadow graded" notification too? Recommended:
   yes.
2. Which runs count as "since the previous digest": the day logs' runs after the
   last DIGEST row in `notification_log.csv` (recommended), or this run only?
