# Spec: weekly/daily level breaks, with trend, obstacle check and fixed targets (pre-registered, GBP/AUD)

**Status:** pre-registered 2026-11-14 at the owner's request. Study id
**BCS-2**. This file, the runner (`studies/htf_breakout_study.py`) and its
suite test (`tests/test_htf_breakout_selftest.py`) are committed together, with
their sha256 in validation_log, before any outcome of these rules is computed.
Counts are logged and committed before the single full run.

## 1. Why, and the question

- **The trigger.** BCS-1 (R43) refuted every break of an automatic hourly swing
  line, in any context, on a timed exit. The owner asked for the test of how
  they actually trade:
  1. zones from the weekly and daily charts;
  2. trading only in the higher-timeframe direction;
  3. skipping trades when the first obstacle is too close;
  4. fixed 1.5R or 2.5R targets with the framework's management rules.
- **The question.** Do two-close breaks of weekly and daily levels, taken only
  with the daily trend and only when the first obstacle lies beyond the target,
  have an edge after costs?
- **Provenance (M6).** Every rule below is the owner's stated method, or a
  framework rule already on file (swing k values from `markups/README.md`, stop
  bounds and management from `foundation/risk_and_execution.md`, the stop
  recipe of 2026-11-14). Choices made here, before any outcome and without a
  grid, are marked **(choice)**.
- **Multiple testing, said now.** This is the second test of breakouts on the
  same nine years. Each new test on the same data raises the chance of a lucky
  pass. The Bonferroni correction covers the four cells here, not the history
  of tests. That is why a pass earns only a sealed-exam spec (M40), never a
  trade.
- **The owner's note "passes on 2005–2026".** The verdict uses STUDY
  (2005–2013) only. USED (2021–2026) has been looked at (the owner's charts
  and markups), so data_map_spec allows it as learning only. It is run here as
  a replication with no verdict.

## 2. Data

- The research archive (`~/intel_study_archives/research_archive/`) through
  `research_archive.load`, which checks the manifest hash and refuses the
  sealed block. The runner also pins the files' sha256 (BCS-1 pins, reused):
  `GBP_AUD_H1.csv` `f170a040…6768`, `GBP_AUD_D.csv` `24e4bbe9…f7f6`.
- **STUDY** (verdict): 2005-01-02 → 2013-12-30, refused at or after
  2013-12-30 22:00 UTC.
- **USED** (replication): bars from 2021-04-26 21:00 UTC with session day up to
  2026-09-09; anything else refused.
- Weekly bars are built from the D1 sessions (Monday-keyed weeks of session
  days). No weekly file is read.

## 3. Bar index and time

- H1 bars in time order per span. Each H1 bar's **k** = the number of D1
  sessions completed before its own session (`bisect` on session days).
  Daily and weekly information is used only once complete.

## 4. The rules (long side; the short side is the exact mirror)

### 4.1 Levels: weekly and daily swing highs

- **Daily level:** a D1 swing high, k = 3 (strictly above the 3 sessions each
  side). Usable once the confirming session completes (k ≥ swing + 4).
  **Expires** 120 sessions after the swing session **(choice)**.
- **Weekly level:** a weekly swing high, k = 2 (strictly above 2 weeks each
  side). Usable once week w+2 completes. **Expires** 520 sessions (about two
  years) after the swing week's last session **(choice)**.
- A level that price has already closed above when it becomes usable is
  consumed at once (never traded).

### 4.2 Events, fakes, confirmations

- **Event** at bar j: C[j−1] ≤ level < C[j] for a live level. If several levels
  are crossed, the highest one is the event's level (the far edge).
- **Fake:** C[j+1] ≤ level. The level stays live.
- **Confirmation:** C[j+1] > level. Every live level at or below C[j+1] is
  consumed.

### 4.3 The daily trend

- From the D1 swings (k = 3) usable at the entry bar's k: the last two swing
  highs and the last two swing lows. **Up** = higher high and higher low;
  **down** = lower high and lower low; anything else (or fewer than two of
  each) = no trend.
- Longs only when up; shorts only when down (via the mirror).

### 4.4 Entry and stop

- **B:** market entry at the confirming close (bar j+1).
- **C:** after the confirmation, a limit at the level on bars j+2 … j+13;
  filled at min(open, level) on the first bar whose low reaches it.
- **Stop (the owner's recipe):**
  - zone bottom = level − 0.25 × D1 ATR(14) **(choice: the zone's depth)**;
  - stop = zone bottom − 15 pips (buffer);
  - if the stop is closer than **0.3 ATR** to entry, it is widened to 0.3 ATR;
  - if it is wider than **1.5 ATR**, there is no trade.
  - The ATR is from the 14 sessions completed before the entry bar's session.

### 4.5 The obstacle check (the owner's rule)

- **First obstacle:** the nearest level above the entry that is usable,
  unexpired and not consumed before the entry bar.
- **No trade if that obstacle lies before the target** (obstacle < entry +
  target distance). An obstacle at or beyond the target, or none, passes.

### 4.6 Targets (the cells)

- Target distance T = m × (risk + spread) + spread, so that
  (T − spread) ÷ (risk + spread) = m. This is the formula given to the owner on
  2026-11-14. **m = 1.5 or 2.5.**

### 4.7 Management (framework rules, `risk_and_execution.md`)

On every bar after entry, in this order:
1. **The stop**, as it stood at the bar's start: hit → the remainder exits there.
2. **+1R:** half the position closes at +1R. The stop moves to breakeven from
   the **next** bar.
3. **The target:** hit → the remainder exits there.
4. **Trail:** once the best high has reached +1.5R, the stop trails 0.5R behind
   the best high, from the next bar.

- **C's fill bar:** only the stop is checked on that bar. Favourable moves on
  the fill bar are ignored, because they may have come before the fill.
- **Time limit: 120 H1 bars** after entry **(choice)**. The remainder exits at
  that bar's close.
- **Gaps:** stops are filled at the stop (repo convention). The loss at a
  gapped open is a secondary.
- **R** = profit on both halves ÷ risk, then − spread ÷ risk, + financing ÷ risk.

### 4.8 Costs

- **STUDY:** the era spread (10.0 pips 2005–09, 7.0 pips 2010–13) by entry
  year, used in the target, the obstacle check and the cost. Financing as in
  BCS-1: period policy rates, a 1.0% markup, and nights per exit weighted by
  the size that exits.
- **USED:** the data_map 2021→ spread (3.0 pips), with 5.1 as a secondary. **No
  financing:** no policy-rate file covers 2021–2026, and this is stated as a
  limit.

## 5. Episodes

Per cell, long and short trades pooled on the H1 index. A new episode starts
**120 or more bars** after the current episode's first entry
(`episodes.count_episodes`). An episode's R is its first trade's R.

## 6. Cells, test and verdict

- **Four cells:** {B, C} × {1.5R, 2.5R}, on STUDY.
- **Lower bound:** percentile bootstrap, Bonferroni over 4 cells (confidence
  **0.9875**), 20,000 resamples, seed 7.
- **Upper bound:** 90%, one-sided.
- **Verdict:** INSUFFICIENT if N < 20. SUPPORTED if lower > 0 and the mean
  without the best episode > 0. REFUTED if upper < +0.15R. Otherwise
  INCONCLUSIVE.

## 7. Power

- **Expected N (a guess; the counts stage replaces it):** daily levels give
  roughly 30 swing highs and 30 swing lows a year. After confirmation, the
  trend filter, the obstacle check and the 120-bar episode collapse, perhaps
  **15–40 episodes a year per cell, so 130–360 over nine years.**
- **At α = 0.0125, SD 1.2:** N 150 → smallest detectable edge about +0.30R;
  N 300 → about +0.21R. N required for +0.15R at 80% = 609.
- **Said now:** unless the edge is large (about +0.2R to +0.3R or more), the
  likely verdict is INCONCLUSIVE, not SUPPORTED. REFUTED needs the observed
  mean to be well below +0.15R.

## 8. Secondary analyses (descriptive; never change a verdict)

Per cell:
- before costs; flat 3.0 and 5.1 pips;
- stops at the gap open;
- long and short; daily-level vs weekly-level breaks;
- sub-periods and by year; exit reasons; skip reasons;
- **no partial** (full size to target, breakeven at +1R);
- **each filter removed:** no trend filter; no obstacle check; neither.

Also:
- the fake rate at weekly and daily levels;
- the USED replication at 3.0 and 5.1 pips.

## 9. Run discipline

1. `selftest` prints `SELFTEST OK` (52 checks). It was mutation-tested before
   this commit: 20 mutants caught, 1 equivalent, reported in validation_log.
2. Commit this spec, the runner and the test, with their hashes, in
   validation_log (the pre-registration).
3. `counts` through `reality_run.py --no-env`: events, fakes, levels, trades,
   episodes and skips. No R. Logged and committed.
4. `full` runs once; it refuses an existing report. Its output goes verbatim to
   validation_log and `studies/htf_breakout_study_result.md`, and the verdicts
   to `foundation/research_findings.md`.
5. Any change after step 2 is a new id.

## 10. Limits

- **Mechanical zones.** The owner draws zones by eye. Here a zone is a swing
  price with a fixed depth of 0.25 ATR, an automatic stand-in.
- **Hourly resolution.** Same-bar ordering is conservative: the stop comes
  first, and favourable moves on C's fill bar are ignored.
- **The choices marked (choice)** (level life, zone depth, the 120-bar limit)
  could change the answer. Changing them is a new pre-registration.
- **Same nine years as BCS-1.** See §1 on multiple testing.
