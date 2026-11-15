# Spec: does a second hourly close confirm a breakout? (pre-registered, GBP/AUD 2005–2013 STUDY data)

**Status:** pre-registered 2026-11-14 at the owner's request ("let's just go
back in history and see how things played"). Study id **BCS-1**. This file,
the runner (`studies/breakout_confirmation_study.py`) and its suite test
(`tests/test_breakout_confirmation_selftest.py`) are committed together, with
their sha256 and the data files' sha256 recorded in validation_log in the same
commit. No 2005–2013 outcome of these rules has been computed. The counts
stage (events, entries and episodes only, no R) runs after this commit and is
logged before the full run. The full run happens once, and its output goes to
validation_log verbatim, whatever it says.

## 1. Why, and the question

- **The trigger.** During the W46 markup (`markups/2026-W46.md`) the owner
  adopted a breakout rule: **a break is two closed hourly candles in a row
  beyond the level; if the second closes back inside, it was a fake.** In the
  W46 scoring window, six first closes beyond a line were seen on GBP/AUD:
  five were fakes on the next candle and one confirmed (Fri 2026-11-13 04:00
  PST), then retested the line and ran on.
- **The question.** On nine years of GBP/AUD hourly data the rule was not
  designed on:
  1. How often is a first hourly close beyond a swing level a fake (the next
     close is back inside)?
  2. Does waiting for the second close improve the trade, compared with
     entering on the first close? And does waiting further for a retest of the
     level help again?
  3. Does any of the three entries have an edge after costs?
- **Provenance (M6).** The rule comes from one week of 2026 charts (FORWARD
  span), which plays no part in this test. The level definition is the
  playbook's hourly swing (k = 5, `markups/README.md`). The stop buffer
  (0.25 daily ATR) is the level-fade study's (R14). The 24-hour horizon and
  the 12-hour retest window are round choices made here, before any outcome,
  without a grid. None was chosen by looking at 2005–2013 results.
- **Frame (data_map_spec §5).** A 2005–2013 result answers "does this survive
  conditions it was not designed on", not "does this work now".

## 2. Prior work, and how this differs

- **R24** (2026-09-11): on GBP/AUD **daily** bars, 71% of overshoots beyond the
  prior confirmed swing extreme closed back inside within 3 days (N = 69,
  descriptive, no entries, no costs). This study is on **hourly** bars, counts
  next-candle fakes, and grades entries after costs.
- **R7** (fakeout-then-go, REFUTED) asked whether failed breaks *precede* real
  moves. This study does not trade the fake or its reversal; a fake is simply
  no trade.
- **R14** (level fades, REFUTED) traded rejections at levels. This study trades
  the other side: closes through levels.
- **R10 / THRUST_PULLBACK** (H4 consolidation breakouts) were grid-selected.
  Nothing here is selected from a grid.

## 3. Data

- **Prices:** OANDA mid H1 and D1 candles for GBP_AUD, STUDY span
  2005-01-01 → 2013-12-30, read through `studies/research_archive.load` with
  `spans={"STUDY"}` from `~/intel_study_archives/research_archive/`. The
  archive's own manifest hash is checked by the loader, and the runner pins
  the files' sha256 as well:
  - `GBP_AUD_H1.csv` `f170a0403ac306de24f3b5ca4910a6b66fec009da5de335e9f4f1a1ff8b36768`
    (STUDY: 56,077 bars, 2005-01-02 22:00Z → 2013-12-30 21:00Z)
  - `GBP_AUD_D.csv` `24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6`
    (STUDY: 2,343 sessions)
- **Already converted.** The archive's STUDY bars carry the approved weekend
  rule (Saturday sessions dropped, Sunday sessions folded into Monday); every
  STUDY bar belongs to a Monday–Friday session.
- **Refusals.** The runner refuses any file whose hash differs, and any bar
  opening before 2005-01-01 or at or after 2013-12-30 22:00 UTC (the embargo
  and the SEALED EXAM). It makes no network call.
- **The bar index** is the STUDY H1 series in time order. Weekend and holiday
  gaps are simply adjacent bars on the index.
- **Not used:** 2014-01-01 → 2021-04-25 (SEALED EXAM), USED (2021–2026) and
  FORWARD.

## 4. The rules (long side; the short side is the exact mirror)

### 4.1 The level: the latest confirmed hourly swing high

- **Swing high** at bar i: H[i] is strictly greater than every other high in
  bars i−5 … i+5 (the playbook's hourly k = 5; `studies/markup_swings.swings`).
- It is **confirmed at the close of bar i+5** and usable from bar i+6.
- **The active level** is the most recently confirmed swing high. A newly
  confirmed swing high replaces it at once, whether or not the old one was
  ever broken.
- **A level ends** when it is replaced, or when it is confirmed broken (§4.3,
  variant B). It does **not** end on a fake: the owner's rule keeps watching
  the same line, as on 2026-11-13 when the fifth close above 1.9475 confirmed.

### 4.2 The first close (an event)

- **An event** is a bar j, at or after the level's first usable bar
  (j ≥ i + 6), with **C[j] > level** and **C[j−1] ≤ level** (a fresh close
  beyond). At j = i + 6 the second condition always holds, because
  C[i+5] ≤ H[i+5] < H[i].
- **A fake** is an event whose next bar closes back at or inside the level:
  C[j+1] ≤ level. **A confirmation** is C[j+1] > level.

### 4.3 The three entries (the three cells)

All three use the same level and the same stop rule; they differ only in
when, and at what price, they enter.

| Cell | Entry | Price |
|---|---|---|
| **A: first close** | every event | the close of bar j |
| **B: two closes** | every confirmation; the level then ends | the close of bar j+1 |
| **C: two closes + retest** | after a B confirmation, a buy limit at the level rests on bars j+2 … j+13 (12 hours); the first bar whose low reaches it fills; none fills → no trade | min(open, level) of the fill bar |

- A fake is no trade for B and C. A takes it (A does not know yet).
- A C order, once placed, rests for its 12 bars whatever later levels do.
- An event on the last STUDY bar (no next close) is counted and not traded.
- A takes every fresh close beyond while the level lives, so one level can
  give A several entries (the episode rule, §6, keeps one per 24 bars).

### 4.4 Stop

- **Stop = level − 0.25 × D1 ATR(14)**, the ATR from the 14 sessions completed
  before the entry bar's session (simple mean of true range), as in the level
  fade study's 0.25-ATR stop buffer.
- In words: the trade is wrong once price is clearly back under the broken
  level.
- Risk = entry − stop, in pips. A and B entries are above the level, so their
  risk is larger than C's (whose entry is at the level, risk 0.25 ATR).

### 4.5 Horizon and grading

- **A and B:** entry at the close of the entry bar e. The stop is checked on
  bars e+1 … e+24; otherwise R = (close of bar e+24 − entry) ÷ risk.
- **C:** the fill bar f is bar 0. The stop is checked on bars f … f+24; a fill
  bar that reaches the stop is stopped on that bar (price passes the level
  before the stop, so the order is certain). Otherwise R = (close of bar
  f+24 − entry) ÷ risk.
- **Stopped means −1R**, whatever happens later (M14). A bar that opens
  through the stop is graded −1R (repo convention); the loss at that bar's
  open is kept as a secondary sensitivity.
- **A C fill at or through the stop** (the fill bar opens at or below the
  stop) is −1R at the intended risk (level − stop).
- **Ungraded:** an entry whose horizon runs past the last STUDY bar is
  ungraded and counted. Nothing reaches into the embargo.

### 4.6 The short side

The exact mirror: swing lows, closes below, stop above the level. The runner
implements it by negating prices (high ↔ low) and reusing the long-side code;
the self-test checks a hand-built short gives the same R as its mirror long.

## 5. Costs, charged on every trade

- **Primary spread: the era schedule from data_map_spec §4**, by entry year,
  round trip: GBP_AUD **10.0 pips 2005–2009, 7.0 pips 2010–2013**. The
  verdict uses it (data_map_spec §4 is frozen and binding on STUDY results).
- **Secondary spreads, reported beside each verdict:** a flat **3.0 pips**
  (the studies' historic present-day figure) and a flat **5.1 pips** (the
  measured 2026-10-07 → 11-06 GBP/AUD median, validation_log 2026-11-06).
- **Financing:** period policy rates from `studies/policy_rates_2003_2014.json`
  on the entry session's date; a side earns side × (r_GBP − r_AUD) − 1.0%
  a year (markup), a paying side pays the gap plus the markup. In pips:
  entry price × net rate × nights ÷ 365 ÷ pip.
  - **Nights:** `shadow_cost_regrade.rollover_nights` (each 17:00 New York
    rollover strictly after entry and at or before exit; Wednesday's counts 3).
  - **Entry instant:** A and B: the close of the entry bar (its open + 1 h).
    C: the fill bar's open.
  - **Exit instant:** the stop bar's open if stopped; otherwise the close of
    the horizon bar (its open + 1 h).
- **R after costs** = raw R − spread ÷ risk + financing ÷ risk.

## 6. Episodes

- Per cell, long and short trades are pooled on the H1 bar index and sorted by
  entry bar (C: the fill bar).
- A trade starts a new episode only if its entry bar is **24 or more bars
  after the current episode's first entry** (the
  `foundation/tools/episodes.count_episodes` rule; the self-test checks they
  agree). **An episode's R is the R of its first trade.**
- Same-bar ties (a long and a short on one bar) are ordered long first, and
  the counts stage reports how many there are.

## 7. Cells and the test

- **Three cells:** GBP_AUD × {A first close, B two closes, C two closes +
  retest}. Each is its own question.
- **The statistic:** mean episode R after era spread and financing.
- **Lower bound:** percentile bootstrap, one-sided, Bonferroni over 3 cells:
  confidence 1 − 0.05/3 = **0.98333…**; `power_check.bootstrap_lower_bound`,
  20,000 resamples, seed 7.
- **Upper bound for refutation:** the futility standard, **90%** one-sided,
  `power_check.bootstrap_upper_bound`, 20,000 resamples, seed 7.
- **Reported for every cell:** N with tier, mean, median, SD, both bounds,
  mean without the best episode, max drawdown in R, win rate, stop-outs, mean
  risk, spread, financing and nights.

## 8. Verdict per cell (decided now)

| Verdict | Condition |
|---|---|
| **INSUFFICIENT** | N < 20 episodes |
| **SUPPORTED** | Bonferroni lower bound > 0 **and** mean without the best episode > 0 |
| **REFUTED** | 90% upper bound < +0.15R |
| **INCONCLUSIVE** | anything else |

- **SUPPORTED** is the strongest verdict STUDY data can give. It earns a
  sealed-exam spec of its own (a team decision), not a trade.
- **REFUTED** is recorded in research_findings as a refuted premise.
- **The owner's question 2 ("does waiting help?") is descriptive** (§10 items
  1–4). It never changes a verdict. A cell can be REFUTED while still showing
  that its filter removed losers; both are reported.

## 9. Power (stated before the run)

- **Assumed SD of episode R:** 1.2R.
- **Expected N (a guess, replaced by the counts stage):** hourly k = 5 swing
  highs and lows appear roughly once or twice a day each, so A and B should
  each have an episode on most trading days after the 24-bar collapse:
  roughly **1,000–2,000 episodes per cell** over 2,343 sessions. C will have
  fewer (only retested confirmations), perhaps **400–1,200**.
- **From `power_check` at α = 0.05/3 (one-sided), SD 1.2:**

  | N | Power for +0.15R | Smallest edge detectable at 80% |
  |---|---|---|
  | 300 | 52% | +0.21R |
  | 600 | 83% | +0.15R |
  | 1,000 | 97% | +0.11R |
  | 1,500 | >99% | +0.09R |
  | 2,000 | >99% | +0.08R |

- **N required for +0.15R at 80% power: 565 episodes per cell.** Unlike every
  swing-frequency study so far, this one can reach it. If the counts stage
  shows a cell below 565, its verdict is read with the power at its N, stated
  in the report.

## 10. Secondary analyses (reported; never change a verdict; descriptive)

1. **Fake rate:** of all events (first closes), the share whose next close is
   back inside; longs and shorts; by year.
2. **What the second close filters:** cell A's graded trades split by whether
   their event was a fake or a confirmation: N, mean R and median R of each
   group (all trades, not episodes; overlapping, so descriptive only).
3. **The price of waiting:** for confirmations, the mean and median of
   (B entry − A entry) in pips and as a share of daily ATR; and the paired
   difference R(B) − R(A) on the same confirmed events (all trades).
4. **Retest rate:** of B confirmations, the share that fill a C order within
   12 bars, and the mean R of B trades that were later retested versus not.
5. R before costs, and the 3.0-pip and 5.1-pip spreads, with full statistics.
6. Stops filled at the gap open: the count of bars opening through the stop
   and the statistics with gap losses.
7. Long and short episodes separately.
8. Sub-periods: 2005-01 → 2008-06, 2008-07 → 2009-06 (the crisis),
   2009-07 → 2013-12; and by year: N and mean R.
9. **Session of the first close** (UTC hour of the event bar's close, no DST
   adjustment): Asia 22:00–07:00, London 07:00–12:00, London/New York
   12:00–17:00, late New York 17:00–22:00: fake rate, and the N and mean R of
   cell B trades in each. Descriptive; four looks invite a lucky one.
10. Event counts: swing highs and lows confirmed, levels replaced unbroken,
    events, fakes, confirmations, C orders filled and expired, ungraded at the
    end of data, same-bar ties.

## 11. Run discipline

1. **`selftest`** must print `SELFTEST OK`. On synthetic bars it checks:
   - the swing rule (strict, k = 5, confirmation delay, equal highs not a
     swing); replacement by a newer swing; the C[j−1] ≤ level requirement;
   - a replica of the 2026-11-13 sequence (four fakes then a confirmation on
     one level): A enters five times, B once at the fifth event's next close,
     and the level ends there;
   - a fake (no B), a confirmation (B at C[j+1]);
   - the C limit: a fill at the level, a fill at the open on a gap below the
     level, the 12-bar window inclusive and bar 13 excluded, a fill bar that
     also hits the stop (−1R), a fill through the stop;
   - the stop from completed-session ATR only; a timed exit by hand; stops on
     bars 24 and 25 after entry (inside and outside); a gap through the stop;
     ungraded at the end of data;
   - the short mirror giving an identical R;
   - costs: era spreads by year, the 3.0 and 5.1 secondaries, financing for a
     long and a short against hand numbers, the entry instant at the bar close
     for A/B;
   - episode collapse matching `episodes.count_episodes`;
   - the verdict boundaries, Bonferroni applied (0.98333…), a known +0.6R
     edge SUPPORTED, a −0.2R edge REFUTED;
   - the embargo and sealed-exam refusal and the data-hash refusal.
2. **The self-test is mutation-tested** (at least 8 mutants, each reported as
   caught or survived) before the pre-registration commit.
3. **Commit** this spec, the runner and the suite test, with their sha256 and
   the data sha256 in validation_log. This is the pre-registration.
4. **`counts`** (through `scripts/reality_run.py --no-env`) prints swings,
   levels, events, fakes, confirmations, retests, entries and episodes per
   cell, by side and by year. **No R, no stop outcome, no price change after
   entry.** (The fake count is the answer to question 1 and is a count of
   closes, so it is printed here.) Logged and committed before `full`.
5. **`full`** runs once. It refuses if the report file exists or a data hash
   differs. Its output goes verbatim to validation_log and
   `studies/breakout_confirmation_study_result.md`. Each cell's verdict goes
   into `foundation/research_findings.md`.
6. **Any change** to this spec after step 3 is a new pre-registration with a
   new id. Nothing is tuned after a result is seen.

## 12. Limits, stated now

- **Mid prices.** Entries at a close or a limit at the level are mid prices;
  the spread charge covers the ask/bid approximately.
- **Hourly resolution.** Within a bar the order of events is unknown. The rules
  avoid depending on it except the gap sensitivity.
- **Swing lines, not the owner's zones.** The owner's markups use zones and a
  "far edge" rule. A swing line is the automatic, testable stand-in; zone
  breaks are not tested here.
- **One stop, one horizon.** A 0.25-ATR stop and a 24-hour exit. A different
  exit could change the answer; that would be a new pre-registration, not a
  sweep of this one.
- **Old era, one pair.** 2005–2013 includes the 2008 crisis and much wider
  spreads. GBP/JPY and gold are not tested here.
- **A pass is not a trade.** SUPPORTED would still need the sealed exam and the
  forward ledger.
