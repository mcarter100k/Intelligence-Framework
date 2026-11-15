# Spec: do 15-minute entries change the breakout results? (pre-registered, GBP/AUD 2005–2013 STUDY)

**Status:** pre-registered 2026-11-15 at the owner's request. Study id **BCS-3**.
This file, the runner (`studies/m15_entry_study.py`), the data tool
(`studies/m15_study_data.py`) and their suite test
(`tests/test_m15_entry_selftest.py`) are committed together, with hashes in
validation_log, before any outcome of these rules is computed.

## 1. Why, and the question

- **The trigger.** BCS-1 (R43) and BCS-2 (R44) judged entries on hourly closes.
  The owner: "the H1 and below gives you better entry and you can see market
  structure for precise entries… go and check the H1 and below and see if you
  get the same results."
- **The question.** Keep everything else identical to BCS-1 and BCS-2: the same
  levels, the same hourly two-close confirmation, the same stops, filters,
  targets and management. If the entry is timed on the 15-minute chart, does
  the result change?
- **The 15-minute entry (the only change):**
  - after the hourly confirmation closes, watch the next 48 M15 bars (12
    hours, the same window as BCS-1/2's retest entry C);
  - the **touch:** an M15 low at or below the level (for longs);
  - the **trigger:** the first M15 bar, from the touch on, that closes above
    the level **and** above its own open (a bullish bar), like the owner's
    engulfing entry. The touch bar itself may trigger.
  - **Enter at the trigger bar's close.**
  - **Cancelled** if an M15 low reaches the stop line (§4) before a trigger.
- **Provenance (M6).** The entry is a written-down version of what the owner
  described (precise entry on lower-timeframe structure at the retest). No
  parameter here was chosen from data. The window and stops are the earlier
  studies' own. **(choice)** marks the one new setting.
- **Multiple testing, said now.** This is the third breakout test on the same
  nine years (after BCS-1 and BCS-2). A pass earns only a sealed-exam spec
  (M40).

## 2. Data

- **H1 and D1:** the research archive, STUDY span only, via
  `research_archive.load` (BCS-1 pins `f170a040…6768`, `24e4bbe9…f7f6`).
- **M15 (new):** fetched 2026-11-15 by `studies/m15_study_data.py fetch`,
  through the embargo-guarded `history_study_gate_s3.fetch`, to
  `~/intel_study_archives/m15_study/GBP_AUD_M15.csv`.
  - sha256 `83ef82bb1bf885895c8ef33d998d02bc3569a7d02434d21a80e36531b97925b6`.
  - 224,208 bars from 2005-01-02 22:00Z to 2013-12-30 21:15Z. Monday–Friday
    sessions only (6,028 weekend-session bars dropped).
  - The last STUDY hour has 2 of its 4 bars, because the fetch window ends at
    21:30Z.
- **Verified against the archive H1** before any statistic:
  - all 56,077 hours are present in both;
  - 99.25% match on all four prices within 0.5 pip;
  - 419 of the 420 mismatches are the first hour after a weekend or holiday,
    where the archive folded old-data Sunday-session bars into Monday;
  - the other one is the last partial hour;
  - closes differ by more than 0.5 pip only in that last partial hour.
- **Refused:** a changed M15 hash; any bar in the sealed block.

## 3. Cells (each replays an earlier study with only the entry changed)

| Cell | Levels and confirmation | Stop | Exit | Compare with |
|---|---|---|---|---|
| **H1** | BCS-1: latest confirmed hourly swing (k = 5); two hourly closes | level − 0.25 ATR (BCS-1) | timed: 96 M15 bars (= 24 hours) | BCS-1 B −0.106R, C −0.094R |
| **HTF-1.5** | BCS-2: daily/weekly swings; daily trend filter; obstacle check | BCS-2 recipe: level − 0.25 ATR − 15 pips, 0.3–1.5 ATR | 1.5R target, half at +1R, breakeven, trail; 480 M15 bars (= 120 hours) | BCS-2 B −0.346R, C −0.280R |
| **HTF-2.5** | same | same | 2.5R target, same management | same |

- **Cancel lines:** H1 cell: level − 0.25 ATR. HTF cells: level − 0.25 ATR
  − 15 pips (the zone stop).
- **ATR:** D1 ATR(14) from completed sessions, taken at the first M15 bar after
  the confirmation (for the cancel line) and at the entry bar (for the stop).
- **Trend and obstacle:** evaluated at the H1 bar containing the entry.
- **Grading:** on M15 bars, using BCS-1's `grade_close_entry` (H1 cell) and
  BCS-2's `manage` (HTF cells), unchanged. The stop is checked first on each
  bar.
- **Short side:** the exact mirror.

## 4. Costs, episodes, test

- **Costs:** the era spread (10.0 / 7.0 pips) plus financing at period
  policy rates with a 1.0% markup. The entry instant is the M15 close; the
  exit is the stop bar's open or the bar's close.
- **Episodes:** H1 cell 96 M15 bars; HTF cells 480 M15 bars (the same clock
  spans as BCS-1/2).
- **Test:** Bonferroni over 3 cells (lower bound at 0.98333), 90% upper bound.
  SUPPORTED needs lower > 0 and the mean without the best episode > 0.
  REFUTED needs upper < +0.15R. 20,000 resamples, seed 7.

## 5. Power (stated before counts)

- **H1 cell:** BCS-1 had 2,139 confirmations, and 73% retested within 12 hours.
  After the trigger and the episode collapse, perhaps **700–1,100 episodes**.
  The smallest edge detectable is about +0.11R.
- **HTF cells:** BCS-2's retest cells had 55–59 episodes, so expect about
  **40–60**. The smallest detectable edge is about +0.5R: these cells can only
  catch a large edge.

## 6. Secondary (descriptive; never changes a verdict)

Per cell:
- the entry funnel (confirmations, triggers, cancels, no-retests);
- the wait to entry;
- before costs; flat 3.0 and 5.1 pips; gap-open stops;
- long and short; sub-periods; by year; exits;
- **tight stop**: below the lowest M15 low since the touch, minus 15 pips,
  with no 0.3 ATR floor (capped at 1.5 ATR). This tests the owner's
  "precise entry, tight stop" directly **(choice)**.

HTF cells only:
- no partial; no filters.

## 7. Run discipline

1. `selftest` prints `SELFTEST OK` (28 checks). Mutation test: 16 caught, 1
   equivalent, logged.
2. The pre-registration commit.
3. `counts` (no R), logged and committed.
4. `full` once, verbatim to validation_log and
   `studies/m15_entry_study_result.md`; verdicts to research_findings.

## 8. Limits

- A mechanical stand-in for reading 15-minute structure: one touch-and-close
  rule.
- Within-bar order on M15 is unknown; the stop is checked first (conservative).
- Week-open hours differ from the archive's folded H1 bars (the high and low
  of about 419 hours).
- The same nine years as the previous two tests.
