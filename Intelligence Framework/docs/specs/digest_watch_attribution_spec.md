# Spec: the digest's watch clause names its pair and comes from that pair

**Status:** owner-approved free-zone fix, 2026-11-05 ("start the digest fix now"); built on `fix/digest-attribution`. Amends the watch-clause rule in `daily_digest_spec.md` (that body is unchanged; this file records the change).

## Defect

`scripts/daily_digest.py` took the first EXIT IF / WATCH FOR sentence found anywhere in the run, preferring any "confirms as a swing" sentence, and printed it as `— watch: <sentence>` with no pair.
- Real case, 2026-10-12 07:30 (`tests/fixtures/brief_2026-10-12_digest_run.txt`): `GBP/AUD STAND ASIDE · GBP/JPY SHORT — watch: daily chart trend strength crosses 25 …`. That was GBP/AUD's stand-aside condition, and the SHORT's exit was dropped.
- Found by the code reviewer's display-claim inventory (validation_log 2026-11-05, round 2, item 1); re-run and confirmed before building.

## Change

- Each pair's clause is read from that pair's own section.
- One clause is shown:
  1. a pair with a LONG or SHORT (open, or last read on a closed market), labelled `exit if`;
  2. else a concrete pending-pivot watch;
  3. else the first pair's watch.
- The clause always names its pair: `— GBP/JPY exit if: …` or `— GBP/AUD watch: …`.
- Unchanged: the decision head, the closed-market head, the failed-run line, firing conditions, categories, every other notification.

## Gates

- **Gate 1:**
  - Attribution tests: a call wins over the other pair's pivot watch; the clause comes from its own section; never unnamed.
  - Old → new records in `test_daily_digest.py` (the 10-12 fixture and the two "watch:" prefixes).
  - The new tests fail on `main`'s builder (7 failed).
  - Mutation, 5/5 caught.
- **Rule 12 / Gate 2:** 40 real runs replayed through `main` and the branch in sandboxes. Categories, non-digest summaries and ledger state are identical in 40/40. Every digest differs only by the pair label on the same clause; the decision head is unchanged in 40/40. None of the 40 had a call; the call case rests on the real 10-12 fixture.
- **Gate 3, PENDING:** the first digest on a morning with a call shows that call's exit condition.

## Out of scope

The WATCH FOR wording itself (`watch_for_truth_spec.md`); digest length and the shadow clause (`shadow_digest_only_spec.md`).
