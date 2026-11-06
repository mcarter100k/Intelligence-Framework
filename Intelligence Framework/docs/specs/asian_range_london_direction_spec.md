# Spec: does the Asian range's breakout side predict the London direction? (PROPOSED, NOT RUN)

**Status:** PROPOSED 2026-11-05. **Spec only: nothing here has been run, and
no runner exists.**
- It is committed together with the session movement study spec
  (`session_movement_study_spec.md`), before any Phase 2 statistic exists.
  So neither the question, the gate nor the criteria below were shaped by
  Phase 2 results.
- It runs only if the team approves it after reading Phase 2. It then runs
  once.

---

## 1. Why this needs the full treatment

The session movement study is descriptive: it says when the pairs move.

This question is predictive: does what happens in Asia tell us which way
London goes? A predictive claim needs everything a descriptive one does
not:
- a pre-committed success criterion;
- a stated base rate;
- multiple-comparison control;
- honest N.

All four are fixed below.

## 2. Gate (decided before Phase 2 results)

The question is **moot** if Phase 2 finds movement evenly spread through
the day.
- "Evenly spread" is defined in `session_movement_study_spec.md` §6: for
  both pairs, the largest Q1 hourly mean is under 1.5 times the smallest.
- If the gate says moot, this spec is not run, and the observations are
  better spent elsewhere.
- If the gate says concentrated, running it is still the team's decision.

## 3. Data

- **Data:** the STUDY partition H1 already fetched and hash-verified in the
  session movement study (Phase 1, commit 0a38135, sha256 in that spec §2).
  The approved weekend rule applies, and complete study days only, as
  defined in that spec §3.
- **The SEALED EXAM is not used.** A SUPPORTED result here is at most a
  reason to write a separate sealed-exam proposal under data_map_spec §7.
  That proposal would carry its own frozen spec, costs and one run.
- **Contamination, stated:** Phase 2 describes the same STUDY days.
  - It computes no direction, so this outcome has not been seen.
  - But Q3 (where the daily high and low form) is adjacent information.
  - That is why this spec is fixed before Phase 2 runs.

## 4. Definitions (one primary version, no variants)

- **Asian range:** the TOKYO block, 00:00–07:00 UTC (16:00–23:00 PST /
  17:00–00:00 PDT). The Asian high is its highest high, and the Asian low
  its lowest low.
- **Break:** the first LONDON-block H1 bar, opening 07:00 to 11:00 UTC,
  whose high is above the Asian high (an up-break) or whose low is below the
  Asian low (a down-break).
  - If that first breaking bar does both, the day is AMBIGUOUS. It is
    counted and excluded.
  - If no London bar breaks, the day is NO SIGNAL. It is counted.
- **Outcome:** compare the close of the 15:00 UTC bar (the last bar of the
  London / New York overlap) with the close of the break bar.
  - **Continuation:** the move is in the break's direction.
  - **Reversal:** the move is against the break.
  - **Tie:** an exact tie is counted and excluded.
- Measuring from the break bar's close removes the mechanical link between
  "price broke up" and "London closed up".

## 5. Base rate (stated before running)

The no-information continuation rate is not assumed to be 50%. Drift and
time of day could move it.
- For each signal day with break hour h and side s, q_h(s) is the share of
  ALL complete study days on which the move from the close of hour h to the
  15:00 UTC close was in direction s.
- The base rate is p0 = the mean of q_h(s) over signal days.
- p0 is reported next to the 50% symmetry value.

## 6. Test and criteria (per pair; the pairs are never pooled)

- **Statistic:** hit rate = continuations ÷ (continuations + reversals).
- **Test:** two-sided, because continuation and reversal are both
  informative.
  - z = (hits − Σq) ÷ √(Σq(1 − q)), over signal days.
  - Two-sided p-value.
- **Multiple comparisons:** 2 tests (GBP/AUD, GBP/JPY) and one primary
  hypothesis. Holm correction at family α = 0.05.
- **Effect floor:** |hit rate − p0| ≥ 0.05 (5 percentage points). Smaller
  effects are treated as practically nil, whatever the p-value.
- **Verdict per pair:**

| Verdict | Requires |
|---|---|
| SUPPORTED (CONTINUATION or REVERSAL) | Holm-significant AND the effect floor met |
| REFUTED AT SIZE | the 95% interval for (hit rate − p0) lies inside (−0.05, +0.05) |
| INCONCLUSIVE | anything else |
| INSUFFICIENT | fewer than 200 signal days, which is the minimum to resolve 5 points at this α |

- **Honest N:** one observation per day at most. Each outcome window
  (07:00–16:00 UTC) sits inside one study day, so no two overlap. N is
  signal days, reported with the AMBIGUOUS, NO SIGNAL and tie counts and a
  by-year table of N.

## 7. What a result would and would not mean

- **SUPPORTED** says only that the breakout side carries information about
  the next few hours' direction in 2005–2013. It is not a strategy:
  - it has no stop, no target and no costs;
  - the era spread schedule (data_map_spec §4) is not applied.
- A trading rule built on it would need its own pre-registered spec.
- **Not tested here, recorded as hypotheses only:**
  - the Asian range including the SYDNEY block (21:00–07:00);
  - narrow versus wide Asian ranges;
  - other outcome horizons;
  - day of week.
  Each would be a separate pre-registered comparison.
