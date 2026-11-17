# Spec GTP-1: gold trend pullback (pre-registration draft) — SHELVED

**Status: SHELVED 2026-11-16.** Not frozen, not run, nothing computed. Kept
for the record; not deleted. Restarting it needs a new id (GTP-2) and a new
review.

**Why shelved (episode arithmetic, from R48's published STUDY counts):**
- 2006–2013 held **45** qualified rally legs; **32** of them (71.1%) reached
  38.2% (R48: rallies, STUDY, 38.2% reached 32 of 45). 32 is the ceiling on
  long trades before the 6-month filter, the trigger, cancellations and the
  risk skips remove any.
- Falls: 57 legs, 51 reached 38.2% (89.5%), and only a minority of them fall
  while the 6-month trend points down.
- Realistic counts after the filters: about **12–20 long** and fewer short
  episodes (independent reviewers, 2026-11-16; INFERRED, not computed).
- At N < 20 this spec's own verdict table (§5) returns **INSUFFICIENT**. The
  run could not even give the "clearly no" that §6 promised, and a pass could
  not be confirmed on the sealed exam (about 4 episodes a year).

**Amendments (2026-11-16):**
- 2026-11-16: status changed from DRAFT to SHELVED, for the reason above.
- 2026-11-16: §1 corrected: R37's 38.2% cell (the same level as this spec) was
  **REFUTED**, not INCONCLUSIVE (`foundation/research_findings.md` R37). R38's
  cells were INCONCLUSIVE.
- 2026-11-16: §1 corrected: the stop justification used the share of **all**
  qualified legs reaching 78.6%. The rule trades only legs that reached 38.2%.
  Conditional shares from R48's counts (reached 78.6% ÷ reached 38.2%):
  - STUDY rallies 13 ÷ 32 = **40.6%**; STUDY falls 24 ÷ 51 = **47.1%**;
  - USED rallies 9 ÷ 25 = 36.0%; USED falls 15 ÷ 36 = 41.7%.
  The stop beyond 78.6% is therefore reached by roughly 4 in 10 trades'
  first pullback, not "about a third".
- 2026-11-16: §1 corrected: "trend-following over 1–12 months is documented"
  cited the gold plan, which is circular. The literature supports holding for
  1–12 months; this rule holds about 5 sessions, so that support does not
  transfer to the trade horizon (reviewers' point, recorded; the primary
  literature was not re-read here: NOT CHECKED).

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar.

## 1. The idea, and why it might work

**Trade gold only in the direction of its 6-month trend: after a big move
that way, wait for the pullback to reach 38.2%, then enter when a 4-hour
candle closes back in the trend direction.**

- **A reason that doesn't come from our charts.** Trend-following over 1–12
  months is documented across commodities (gold plan F1(a)). The 6-month
  direction is a slow trend of that kind, not a chart-pattern trend.
- **What our own gold facts add (descriptive, not outcomes of this rule):**
  - most first pullbacks reach 38.2%, and 23.6% is too shallow (R48);
  - a touch of a level is not an entry: buying the touch showed no edge on
    the GBP pairs (R14, R37, R38), so this rule waits for a close back in the
    trend direction;
  - a close counts, a wick doesn't (R45);
  - 78.6% was reached by about 41% (rallies) and 47% (falls) of the first
    pullbacks that had reached 38.2% (R48's counts, 2006–2013; amended
    2026-11-16), so a stop beyond it is not beyond ordinary pullbacks.
- **The honest prior is against it.** The closest tested cousins (R37, R38:
  first pullback with the 13-week trend, GBP pairs) showed no edge: R37's
  38.2% cell was REFUTED and the other three cells INCONCLUSIVE (amended
  2026-11-16), and every other GBP entry rule tested so far failed. This spec
  differs in three ways: gold, a 6-month trend instead of 13 weeks, and a
  close-back trigger instead of the touch. A negative result will not be a
  surprise; a positive one gets no benefit of the doubt.
- **Provenance (M6):** the 38.2% and 78.6% choices come from R39/R48, which
  looked at pullback depth in both eras but never at this rule's outcome. The
  6-month horizon and the 30-bar exit are round choices made here, without a
  grid.

## 2. Data

- **Prices:** `~/intel_study_archives/research_archive_legs/XAU_USD_D.csv`
  (sha256 `6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca`)
  and `XAU_USD_H4.csv` (`e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c`),
  the files C2 and C3 used. The runner refuses other bytes.
- **The verdict comes from STUDY only:** 2006-03-21 → 2013-12-30.
- **USED (2021-04-26 → 2026-09-09) is a learning check:** the same frozen
  rule, reported separately, never part of the verdict (gold plan F4).
- **Never read:** 2014-01-01 → 2021-04-25 (proposed as gold's sealed exam,
  team ruling T1) and FORWARD. The runner refuses any such row.
- **News dates (STUDY):** `studies/us_events_2005_2013.csv` (CPI, NFP, FOMC;
  scheduled rows only).
- **News dates (USED):** a 2021–2026 table must be assembled from the BLS
  archives and the Fed's calendar before the runner is written, with each
  date's source, the same way as the 2005–2013 table. Until then the USED
  check runs without the news rule, and says so.
- **Prerequisite P1, FOMC statement times:** the 2005–2013 table leaves
  `time_et` blank for FOMC. The runner uses 2:15 PM ET before 2013-03-20 and
  2:00 PM ET from then on. The Fed's 2013-03-13 press release says statements
  "will now be released at 2 p.m.". The earlier 2:15 PM time must be
  confirmed from the Fed's own statement pages and recorded with its source
  before the runner is written.

## 3. The rule (long side; the short side is the exact mirror)

### 3.1 Trend

- **6-month direction:** the sign of the close of the last completed daily
  session minus the close 126 sessions before it, using only sessions
  completed before the bar being judged.
- Longs need it > 0, shorts < 0. Zero is neither.

### 3.2 The big move and the pullback (R39's detector)

- `studies/first_pullback_study.find_entries`, imported unchanged, with
  `use_trend=False` and level 0.382:
  - anchor: a new 120-bar H4 low (A);
  - qualified: the high since the anchor (B) is at least 2.0 daily ATR above
    A (simple 14-session ATR, fixed at the anchor);
  - the pullback: the first bar, within 60 bars of the anchor, whose low
    reaches B − 0.382 × (B − A).
- The leg is used only if the 6-month direction is > 0 **at the touch bar**.

### 3.3 Trigger (entry)

- From the touch bar on, track the pullback's lowest low so far and the bar
  that made it.
- **Trigger:** the first H4 bar that **closes above the high of the bar that
  made the pullback's lowest low**. The touch bar itself can be that bar.
- **Entry:** the trigger bar's close. That price is known at the close.
- **Cancelled, no trade,** if any of these comes first:
  - a low reaches the stop line (§3.4);
  - 30 H4 bars (about 5 sessions) pass after the touch bar without a trigger;
  - the 6-month direction turns ≤ 0;
  - a new 120-bar low replaces the leg.
- **News rule:** no trigger may be taken on an H4 bar whose 4-hour span
  contains a scheduled FOMC statement, CPI or NFP release time. The next H4
  close that meets the trigger condition can still be taken.
- One trade per leg.

### 3.4 Stop, exit

- **Stop:** B − 0.786 × (B − A) − 0.1 × ATR, fixed at the touch.
- **Risk:** entry − stop. **Skipped and counted** if the risk is above 1.5 ATR
  (the framework's widest stop) or below 0.3 ATR (inside daily noise).
- **Exit:** the close of the 30th H4 bar after the entry bar, unless stopped.
  **A stopped trade is −1R** whatever happens later (M14). A bar that gaps
  through the stop is −1R; the loss at the gap's open is kept as a secondary.
- **Secondary exits (reported, never the verdict):** a limit at B (the move's
  extreme); and a 60-bar timed exit.
- **Ungraded:** a trade whose 30 bars run past the era's end is counted and
  excluded.

### 3.5 Costs

- **Spread:** $0.50 round trip on every trade (primary). OANDA's measured
  median quote in Oct–Nov 2026 was $0.47; $0.50 is a larger share of price at
  2006–2013's $550–$1,900 gold, so it is the conservative choice.
- **Secondary spread:** 0.012% of the entry price (the 2026 quote as a share
  of price).
- **Financing,** for each night held past 5 PM New York (Wednesday counted 3
  times, the framework's `rollover_nights`):
  - longs pay the US policy rate + 2.5% a year on the entry price;
  - shorts pay 2.5% a year and receive nothing.
  - **Prerequisite P2:** the US policy-rate history 2006–2013 and 2021–2026
    (the Fed's target rate, or the top of the target range) is built from the
    Fed or FRED, with sources and sha256, before the runner is written.
  - The 2.5% markup is a placeholder for a broker's charge, chosen to be
    unfavourable. A venue's real figure replaces it in any later test (gold
    plan Phase E).
- **R after costs** = (exit − entry − spread − financing) ÷ risk, all in
  dollars.

## 4. Episodes

- Long and short trades are counted on the H4 bar index, per era.
- A trade starts a new episode only if its entry bar is at least 30 bars
  after the current episode's first entry (`episodes.count_episodes`). An
  episode's R is its first trade's R.

## 5. Cells and the test

- **Two cells:** longs and shorts, each its own question (gold plan §1 rule
  4). Both pooled is reported, with no verdict.
- **Statistic:** the mean episode R after costs.
- **Lower bound:** one-sided percentile bootstrap, Bonferroni over 2 cells:
  97.5%. 20,000 resamples, seed 7 (`power_check.bootstrap_lower_bound`).
- **Upper bound:** the 90% one-sided bound, the futility standard
  (`power_check.bootstrap_upper_bound`).
- **Baseline, against gold's drift:** for each trade, 200 random entries on
  H4 bars of the same era where the 6-month direction has the same sign. Each
  is in the same direction, with the same risk in ATR, the same 30-bar exit
  and the same costs. Reported: the rule's mean minus the baseline's mean.
  This shows whether the rule beats simply being long (or short) with the
  trend.

| Verdict | Condition |
|---|---|
| **INSUFFICIENT** | fewer than 20 episodes |
| **SUPPORTED** | Bonferroni lower bound > 0, **and** the mean without the best episode > 0, **and** the rule beats its baseline |
| **REFUTED** | 90% upper bound < +0.15R |
| **INCONCLUSIVE** | anything else |

SUPPORTED means the rule earns a sealed-exam spec (T1) and nothing more.
Median R, max drawdown and win rate are shown beside the verdict.

## 6. Power (stated before the run)

- **Expected N, guessed from R48's counts (not this rule's):** 2006–2013 had
  45 rally legs and 57 fall legs. After the 6-month filter, the trigger and
  cancellations, perhaps **20–40 long episodes and 10–30 short**. The short
  cell may well be INSUFFICIENT: gold rose through most of 2006–2011, and its
  falls in this era are mainly 2011–2013 (gold plan, Phase C).
- **From `power_check`** (SD 1.2R, one-sided, α = 0.025):

  | Episodes | Smallest edge spotted 80% of the time | Power for +0.15R |
  |---|---|---|
  | 20 | +0.75R | 8% |
  | 30 | +0.61R | 10% |
  | 40 | +0.53R | 12% |
  | 60 | +0.43R | 16% |

- **N needed for +0.15R: 503 per cell.** This data cannot reach it.
- **What that means, said now:**
  - SUPPORTED is reachable only for a large edge (about +0.5R or more).
  - A real but small edge would read INCONCLUSIVE.
  - REFUTED needs an observed mean below about −0.13R at N = 30, or −0.05R
    at N = 60.
  - **This test can say "clearly no" or "big yes", not "small yes".**

## 7. Secondary results (reported; never change a verdict)

1. R before costs; the 0.012% spread; financing markup at 0% and 5%.
2. The B target and the 60-bar exit.
3. Gap stops filled at the gap's open.
4. No news rule.
5. Entry at the touch instead of the trigger (shows what the trigger adds).
6. A 12-month trend instead of 6 (one alternative, named now, not a grid).
7. By year: N and mean R. Counts: legs, touches with and against the trend,
   triggers, each cancellation reason, risk skips, news skips, ungraded.

## 8. Tests before the run

`tests/test_gold_trend_pullback.py`, on synthetic bars:
- a planted leg that touches 38.2%, then closes above the low bar's high:
  one long at that close, graded by hand (timed exit and a stop);
- no trigger before the touch; cancellation on the stop line, on 30 bars, on
  the trend turning, and on a new low;
- the news rule skips a bar containing a release and takes the next one;
- the 6-month direction uses completed sessions only;
- risk skips at 0.3 and 1.5 ATR;
- the short side as an exact mirror (negated prices give identical R);
- costs: spread and financing against hand numbers, with Wednesday's triple
  night;
- episodes match `episodes.count_episodes`;
- the baseline draws only same-sign trend bars and uses the trade's risk;
- the verdict boundaries; exam-span and wrong-hash refusals.

A mutation run (at least 8 mutants, each reported caught or survived) comes
before the freeze commit.

## 9. Run discipline

1. The owner reviews this draft. Changes are made, then the spec is frozen in
   its own commit.
2. Prerequisites P1 (FOMC times) and P2 (policy rates) are built and hashed.
3. The runner and tests are written and committed; the suite is green.
4. **Counts stage:** legs, touches, triggers, cancellations and episodes per
   cell, with no R. Logged and committed before the full run.
5. **Full run, once,** through `scripts/reality_run.py --no-env`. Its output
   goes verbatim to validation_log and to `studies/gold_trend_pullback_result.md`,
   with a finding number, whatever it says.
