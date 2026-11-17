# GLS-1: gold lower-timeframe structure, a descriptive catalogue

**Status: DRAFT v3, rulings F1–F6 and G1–G4 applied. No outcome has been measured.**
Every definition below is fixed before any 30/15/5-minute gold outcome is
looked at (team addition 4, 2026-11-17). Committing this file is the
pre-registration timestamp. A change after a measurement starts gets a new id
(GLS-2), never an edit here.

**Changes before any measurement (dated, kept so the history is visible):**
- 2026-11-17, v1 (commit cd3be60): first draft, four questions for the team.
- 2026-11-17, v2 (rulings F1–F6, same day): span 2021–2026 only (F1); both
  hindsight groups kept, no-hindsight first, a named hindsight ratio (F2);
  thresholds scaled by each timeframe's measured median range, the √6
  conversion removed (F3); 15-minute pullback test kept, justified by measured
  pullback length (F4); §4 reframed from "does a pattern predict a 10-session
  move" to "what does a lower-timeframe entry add to a swing already taken"
  (F5); spread measured by hour instead of assumed (F6). The 2021–2026
  30/15/5-minute fetch and the F3/F4/F6 inputs were run before this version;
  none of them is an outcome (§1.2).
- 2026-11-17, v3 (rulings G1–G4, same day): the setup is the 4-hour
  structure break, with the 4-hour entry as the baseline; the 67 daily breaks
  become a side result (G1). The entry window is each timeframe's p75 wait,
  with time-to-entry buckets (G2). Spread by year and hour, pooled as a side
  result (G3). Financing as a labelled placeholder, reported as a share of
  risk by timeframe, hold, year and side (G4). The G2 and G4 inputs were
  measured before this version (§1.3); none is an outcome. Two of the
  rulings' premises did not survive measurement and are reported in §1.3, not
  resolved.

**What this is:** descriptive work under owner ruling E4. It uses no family
slots and M41 does not apply. Every output is stamped **DESCRIPTIVE, not
tradeable**, as R39 and R48 are. Reaching a level is not holding it, and a
pattern appearing is not a pattern paying.

**What this is not:** a signal, a classifier, or an input to any decision. The
live display (team addition 3b) is a separate change to the protected path and
gets its own spec; it inherits no claim from this catalogue.

Source: team additions 1–7 (2026-11-17), pasted to the session that drafted
this file.

---

## 1. Data (team addition 2: measured before anything else)

Probe finished 2026-11-17 10:43 AM PT through `scripts/reality_run.py` (exit 0,
project unchanged by hash). Every request was a bounded window passed through
`history_study_gate_s3.guard`, so no sealed-block candle could be returned.
56 two-week windows (quarterly 2006–2026, plus the last STUDY weeks and the
first USED weeks), 520 requests.

| | 30-minute | 15-minute | 5-minute |
|---|---|---|---|
| Earliest candle OANDA serves | 2006-03-19 20:00Z | 2006-03-19 20:15Z | 2006-03-19 20:25Z |
| Archive H1 starts | 2006-03-20 00:00Z | same | same |
| STUDY bars / (archive H1 × bars per hour) | 2.01 / 2 | 3.96 / 4 | 11.68 / 12 |
| STUDY hours with every sub-bar present | 98.1% | 96.4% | 92.6% |
| USED hours with every sub-bar present | 99.9% | 99.9% | 99.8% |
| Aggregated sub-bars vs archive H1, within $0.05 (STUDY / USED) | 99.8% / 100% | 99.9% / 100% | 99.9% / 100% |
| Largest disagreement (STUDY / USED) | $2.00 / $0.00 | $2.00 / $0.00 | $2.00 / $0.00 |

- All three timeframes exist for both STUDY (2006-03 → 2013-12) and USED
  (2021-04 → 2026-09). The study is **not** limited to 2021–2026.
- STUDY 5-minute coverage is thinner: 87.6% of expected bars in the two
  sampled mid-2006 windows, at least 95% in every window from October 2006 on. OANDA prints no candle
  for a 5-minute period with no price change, so a missing bar is a quiet
  period, not a hole to fill. **No bar is forward-filled.**
- A few STUDY hours disagree with the archive by up to $2.00. STUDY is not
  fetched (F1), so they are not chased.

### 1.2 The 2021–2026 fetch and the inputs fixed before any outcome

All runs went through `scripts/reality_run.py` with the project unchanged by
hash. Scripts: `studies/gold_subhourly_used_data.py` (fetch, verify) and
`studies/gold_gls1_inputs.py` (the inputs). Files are outside the repo, in
`~/intel_study_archives/gold_subhourly_used/`.

| File | Bars | sha256 |
|---|---|---|
| XAU_USD_M30_USED.csv | 63,563 | `3f8636bc08cbfd6e193d21cc01147066524e8ff52975ba7ea697df1f1f18a828` |
| XAU_USD_M15_USED.csv | 127,112 | `ccc62418068d6f80fde399643b756638750fdd33c05a78bb9f1d882761ddc7f3` |
| XAU_USD_M5_USED.csv | 381,285 | `92c3957aa1ba9ef50b3cb18071b3a1124ace21c5d92aa228628a513779ca684b` |
| XAU_USD_M5_BA_USED.csv (bid/ask closes) | 381,285 | `2c42103ba35d866ba7ba1223b7861e05bd070d5df5528ccf3bbbc6563b5ad959` |

Every file runs from 2021-04-27 22:00Z to the last bar before 2026-09-09
21:00Z. 1,124 requests, all through the guard.

**Check against the archive H1 (§7.1 bar: 99% of fully covered hours within
$0.05): PASS.** Fully covered hours: 30-minute 99.93%, 15-minute 99.88%,
5-minute 99.82% of 31,793. Within $0.05: 100.000% on all three; no larger
disagreement. Positive control: a copy with one 30-minute close moved by $1
reported exactly that hour, $1.000. (A first control moved a bar that was not
its hour's high; the aggregate moved $0.029, under the bar. That control was
too weak, not the check.)

**Inputs (none is an outcome):**

- **F3 ratio ρ:** daily ATR ÷ the 4-hour bar's 14-bar median range, over
  8,231 4-hour bars: **median 3.130** (p10 2.350, p25 2.701, p75 3.606,
  p90 4.103). The rejected √6 conversion would have given 2.449, in a
  different unit (mean true range).
- **F4 pullback length** (R48's legs, 2021–2026, rallies and falls together;
  from the open of the impulse's extreme bar to the close of the touch bar):

  | Level | Legs | 4-hour bars | 30-minute | 15-minute | 5-minute |
  |---|---|---|---|---|---|
  | 38.2% | 61 | median 6 (p25 3) | 46 (22) | **92 (44)** | 276 (132) |
  | 50% | 49 | 8 (4) | 62 (32) | **124 (64)** | 372 (192) |
  | 61.8% | 36 | 10 (6) | 77 (46) | **154 (92)** | 462 (276) |

- **F6 spread** (ask − bid at each 5-minute close, 381,285 closes): median
  $0.350, p90 $0.760 over the span. By Pacific hour the median runs $0.33
  to $0.35 from 5 PM to 12 PM, $0.394 at 1 PM, none at 2 PM (the daily
  break), $0.430 at 3 PM (the reopen) and $0.370 at 4 PM.
  **The year matters more than the hour:** median $0.254 in 2022, $0.390 in
  2024, $0.630 in 2025, $0.710 in 2026. As a share of price it is steady
  (median 0.014% to 0.019% every year), so the change mostly follows gold's
  price. **Conflict with F6 as worded:** F6 asked for the spread by hour
  across 2021–2026. That pooled figure understates 2025–2026 costs by about
  half and overstates 2022's. This spec prices each trade at **that year's
  median for that hour** (stress: that year's p90 for that hour) and also
  reports the pooled by-hour figure. Neither is chosen for being more
  convenient; the team may rule otherwise.
- **Cost share** (spread at that year's hour median ÷ the structure stop, at
  every structure break on each timeframe; an entry in the 2–3 PM PT break
  is priced at the 3 PM reopen):

  | Timeframe | Breaks | Median stop | Spread ÷ stop: median (p90) | At that hour's p90 spread: median (p90) |
  |---|---|---|---|---|
  | Daily | 67 | $114.20 | 0.4% (0.6%) | 0.6% (0.9%) |
  | 4-hour | 520 | $38.12 | 0.9% (1.7%) | 1.2% (2.2%) |
  | 30-minute | 3,672 | $12.86 | 2.8% (5.9%) | 3.6% (7.7%) |
  | 15-minute | 7,265 | $8.75 | 4.1% (9.3%) | 5.4% (12.5%) |
  | 5-minute | 21,652 | $4.86 | **7.4%** (16.9%) | 9.8% (22.6%) |

  The team's illustration (a $0.50 spread is 16.7% of a 5-minute stop)
  assumed a $3 stop. The measured median 5-minute stop is $4.86 and the
  median cost share 7.4%; 16.7% is about the 90th percentile. Even at the
  median it is 0.074R a trade, larger than GMW-1's whole gross effect
  (+0.027R).

### 1.3 Inputs for rulings G2–G4 (measured before v3; no trade outcome)

Script: `studies/gold_gls1_window_financing.py` (5 tests; 4 named mutants
caught), one run through `reality_run.py --no-env`, project unchanged by
hash. Rate file `fred_DFEDTARU.csv`, sha256
`8bf90ca4b8af7803315cec97a19bc1547e3369212d5dadcb01f4021eda4e8080`; the
Fed upper bound ran from 0.25% to 5.5% in the span.

**Setups (G1):** 520 four-hour structure breaks, **289 long and 231 short**.

**Wait from setup to the first valid entry (G2)**, in 4-hour bars of trading
time. A valid entry is the first structure break on that timeframe, in the
setup's direction, whose swing high was confirmed after the setup, before the
4-hour stop is touched (checked on 5-minute bars), within 10 sessions.

| Entry | Entered within 10 sessions | 4-hour stop touched first | Wait p25 / median / p75 / p90 | Window = p75 | Missed at that window | Missed at 1 session (6 bars) |
|---|---|---|---|---|---|---|
| 30-minute | 469 | 50 | 2 / 4 / 6 / 8 | **6 bars** | 134 (25.8%) | 134 (25.8%) |
| 15-minute | 489 | 31 | 1 / 2 / 3 / 5 | **3 bars** | 142 (27.3%) | 43 (8.3%) |
| 5-minute | 508 | 12 | 1 / 1 / 2 / 2 | **2 bars** | 43 (8.3%) | 12 (2.3%) |

Missed = 4-hour stop touched first + no entry within 10 sessions (one
30-minute setup) + entries slower than the window.

- **Premise correction (G2).** G2 expected a 1-session window to discard
  roughly half the setups, from the median 6-bar pullback (§1.2). Measured,
  a 1-session window keeps **74.2%, 91.7% and 97.7%** of setups (30/15/5-
  minute). The pullback measure in §1.2 runs from an impulse's extreme to a
  38.2% touch; this one runs from a 4-hour break to the next lower-timeframe
  break, a different and shorter interval. **The prescribed p75 window is
  shorter than 1 session on 15- and 5-minute entries**, so it discards more
  of the slow entries G2 wanted to keep: 27.3% against 8.3% on 15-minute.
  §4.2 applies the window as ruled and adds a secondary, all entries within
  10 sessions bucketed by wait, so the selection stays visible either way
  (§9).

**Spread and stop as shares of price, by year (G3; medians):**

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Spread ÷ price | 0.0156% | 0.0146% | 0.0140% | 0.0161% | 0.0185% | 0.0158% |
| 4-hour stop ÷ price | 1.470% | 1.724% | 1.495% | 1.539% | 2.076% | 3.286% |
| 30-minute stop ÷ price | 0.454% | 0.558% | 0.433% | 0.536% | 0.683% | 1.035% |
| 15-minute stop ÷ price | 0.307% | 0.365% | 0.285% | 0.344% | 0.449% | 0.681% |
| 5-minute stop ÷ price | 0.165% | 0.203% | 0.159% | 0.188% | 0.251% | 0.379% |

- **Finding (G3, recorded):** the spread held at **0.014–0.019% of price**
  in every year of the span.
- **Premise correction (G3).** That does not make the cost share of a stop
  constant, because structure stops are not price-scaled: they follow
  volatility, which rose against price in 2025–2026 (the 5-minute stop went
  from 0.159% of price in 2023 to 0.379% in 2026). The ratio of the two
  medians puts the 5-minute cost share near 8.8% in 2023 and 4.2% in 2026.
  Pricing by year (§3) carries this; nothing downstream assumes a constant
  share.

**Financing as a share of the structure stop (G4), median, hold to the close
of session +5** (all holds, +1/+2/+5/+10, are in the run output in
validation_log). Longs pay the Fed upper bound + 2.5% a year; shorts pay 2.5%
(GNC-1); secondary, shorts receive upper bound − 2.5% (negative = a credit).
Actual/365 at the entry date's rate.

| Entry | Side | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| 4-hour | long | 0.036R | 0.046R | 0.092R | 0.090R | 0.062R | 0.035R |
| 30-minute | long | 0.114R | 0.139R | 0.332R | 0.279R | 0.198R | 0.117R |
| 15-minute | long | 0.167R | 0.221R | 0.514R | 0.433R | 0.295R | 0.172R |
| 5-minute | long | 0.310R | 0.391R | **0.906R** | 0.793R | 0.516R | 0.312R |
| 5-minute | short, pays 2.5% | 0.300R | 0.233R | 0.306R | 0.255R | 0.195R | 0.129R |
| 5-minute | short, receives | 0.270R | 0.057R | −0.327R | −0.281R | −0.147R | −0.064R |

- **Financing is the largest cost for a tight entry held for days**: a
  5-minute long held five sessions paid 0.31–0.91R, against a median spread
  of 0.074R (§1.2). Over one session it is 0.05–0.16R, about the spread's
  size.
- **Premise correction (G4).** G4 expected carrying to be "nearly free in
  2021" and a 20× swing across the span. That is the policy rate alone
  (5.5 ÷ 0.25 = 22). The convention G4 accepted adds 2.5%, so longs paid
  2.75% a year in 2021 against 8.0% at the peak, 2.9×; measured on 5-minute
  longs held five sessions, 0.310R in 2021 against 0.793R in 2024, 2.6×. The
  team's 0.56R for a tight entry over five days at 2024 rates sits between
  the measured 15-minute (0.433R) and 5-minute (0.793R) figures.
- **Long and short differ (G4c):** under GNC-1, shorts pay 2.5% only, so a
  5-minute short held five sessions cost 0.13–0.31R against the long's
  0.31–0.91R. G4 said shorts "may receive"; GNC-1's convention never pays a
  short. The secondary shows what receiving would mean: a credit from 2023
  on. Both are reported; neither is from a broker.
- **What is reliable (G4):** the absolute level is unverified with any
  broker. The ratio across timeframes is arithmetic: financing in dollars is
  the same for every entry into one setup, so its share of risk scales with
  1 ÷ stop. A 5-minute long pays about 8.8× the 4-hour's share (2024, five
  sessions), whatever the rate.

## 2. Span (ruling F1)

**2021-04-27 → 2026-09-09 (USED) only.** A descriptive pass burns the era it
describes, so 2006–2013 stays unread at every timeframe this study touches.
That keeps a three-stage path open for anything this catalogue suggests:
**describe on 2021–2026, test on 2006–2013, confirm on the sealed exam.**
FORWARD (after 2026-09-09) and the sealed exam (2014-01-01 → 2021-04-25) are
never read.

- **Cost already paid:** R48 described pullback depth on both eras, so a
  hypothesis taken from R48 has only the sealed exam left. That is not a
  reason to repeat it here.
- **Regime label:** every result is **2021–2026 regime-specific**. Measured on
  the archive's daily closes in the span: gold rose **205%**, from $1,776.66
  (2021-04-26) to a high close of $5,418.55 (2026-01-27), then fell as much
  as **26.6%** (to $3,976.58, 2026-07-15) and ended the span **18.8%** below
  the high ($4,402.12, 2026-09-08). F1 described the fall as about 10%; the
  span's own closes show more. A catalogue from a span this trending and
  this volatile may not describe a quiet market.
- The fetch starts at 2021-04-27 21:00Z, one session after the archive's USED
  start, because the guard keeps a one-day margin after the sealed block.

## 3. Common objects

Every object below is known only at the close of the bar where it is
confirmed. Nothing uses a later bar to decide an earlier one.

- **Timeframes:** daily and 4-hour (the hash-pinned archive) and 30, 15 and
  5-minute (the §1.2 fetch), OANDA mid candles.
- **Swing point:** a bar whose high is strictly above the highs of the 4 bars
  on each side (swing high), or whose low is strictly below the 4 lows on each
  side (swing low): the screen's k = 4 rule, on every timeframe. It is
  confirmed at the close of the 4th bar after it.
- **Structure break (long):** the close of the first bar that closes above
  the most recently confirmed swing high; one per swing high. Short is the
  mirror.
- **Structure stop (long):** the most recent confirmed swing low below the
  entry price. Its distance is entry minus that low. Short is the mirror. No
  stop below the entry means no trade.
- **Daily ATR:** 14-session average true range from sessions completed before
  the bar's own (`first_pullback_study.bar_context`, unchanged).
- **Median range (ruling F3):** on any timeframe, the median of high minus
  low over the 14 bars before the bar in question. It replaces "T-ATR"
  everywhere in v1.
- **Session:** the 5 PM New York day, as in GMW-1.
- **Spread (rulings F6, G3):** measured, §1.2. A trade pays half the spread
  at entry and half at exit, each priced at **that year's median for that
  Pacific hour**; an entry or exit in the 2–3 PM PT break is priced at the
  3 PM reopen. Stress: that year's p90 for that hour. Side result only: the
  pooled 2021–2026 by-hour median, for comparison with older findings.
- **Financing (ruling G4): a labelled placeholder.**
  `studies/gold_rule_costs.held_nights`, priced as GNC-1 §3.3: longs pay the
  Fed upper bound + 2.5% a year, shorts pay 2.5%; secondary, shorts receive
  upper bound − 2.5%. Actual/365, at the entry date's rate from
  `fred_DFEDTARU.csv` (hash in §1.3), so it is priced by year. This is
  GNC-1's prerequisite P2: shared machinery. **The absolute level is
  unverified with any broker; the ratio across timeframes is arithmetic and
  holds whatever the rate.**

## 4. What a lower-timeframe entry adds to a swing already taken (ruling F5; reported first)

v1's winner ("price reaches +1 daily ATR within 10 sessions") is decided by
what the swing did, so it made the entry timeframe irrelevant. The question
actually asked is how to **enter** a swing the owner has already decided to
take. So each swing setup is entered four ways with the same exit, and the
difference is what the lower timeframe contributes: a better price and a
tighter stop, against more stop-outs and a larger cost share.

### 4.1 Swing setups (ruling G1)

- **All setups (no hindsight; the headline, reported first):** every 4-hour
  structure break, long and short (§3): **520, 289 long and 231 short**
  (§1.3), about two a week. The setup time t0 is that 4-hour bar's close. A
  setup with no 4-hour structure stop is dropped from every entry alike.
- **Setups that worked (hindsight group).** Every table for this group is
  headed **"Selected on the outcome"**. A setup worked if price reached
  1.0 daily ATR beyond the 4-hour entry before touching the 4-hour structure
  stop, within 10 sessions.
- **Side result, no verdict:** the 67 daily structure breaks, entered at the
  daily close (daily stop) and at 30/15/5-minute structure under the same
  windows, reported with the same rows and labelled side result.

### 4.2 The four entries

| Entry | When | Price | Stop |
|---|---|---|---|
| **4-hour (baseline)** | at t0 | t0's close | the 4-hour structure stop |
| **30-minute / 15-minute / 5-minute** | the first structure break on that timeframe, in the setup's direction, whose swing high was confirmed after t0 | that bar's close | that timeframe's structure stop |

- **Entry window (ruling G2):** each timeframe's p75 wait, fixed in §1.3:
  **30-minute 6, 15-minute 3, 5-minute 2 four-hour bars** of trading time
  from t0. An entry that does not come in time, or comes after the 4-hour
  stop has been touched, is **missed**: no trade. Missed rates (25.8%,
  27.3%, 8.3%) are reported with every table.
- **Time-to-entry buckets (G2), fixed now from §1.3:** 30-minute ≤ 2, 3–4,
  5–6 bars; 15-minute 1, 2, 3 bars; 5-minute 1, 2 bars. Every lower-
  timeframe result is also shown by bucket.
- **Secondary (§1.3 premise correction):** every entry within 10 sessions,
  bucketed the same way plus one bucket for waits beyond the window, so the
  slow entries the p75 window drops are shown, not silently removed.
- **Exit (identical for all four):** the close of the session t0 + h, for
  h = 1, 2, 5 and 10 sessions (team addition 7). An entry that would come
  after that exit is missed for that horizon.
- **Stop check:** on 5-minute bars for every entry, so all four are watched
  at the same resolution. A bar that touches the stop is a stop at the stop
  price; a gap through it fills at the bar's open. A stopped trade is −1R
  before costs.
- **R:** (exit − entry) / (entry − stop), long; mirrored for shorts. Costs
  (§3) are converted to R by the same stop distance.

### 4.3 What is reported, for each entry, horizon and side

1. Counts: setups, trades, missed, stopped.
2. Net R after spread and financing (mean, median, SD, mean without the best
   1%), with a session-block bootstrap 95% interval (2,000 resamples, seed
   20261117); also R before costs, and net at the p90 stress spread. The
   same rows in dollars per ounce and in daily ATR, which do not depend on
   position size (§4.4).
3. **Per setup**, counting a missed entry as 0R: the comparison the owner
   faces, because a missed swing earns nothing.
4. The paired difference, each lower-timeframe entry minus the 4-hour entry,
   on setups where both traded, with the same bootstrap interval.
5. **The deciding number (team addition 1, kept by F5):** in the setups that
   worked, the share whose lower-timeframe entry was stopped before the
   exit, with a 95% Wilson interval. These are winners a normal structure
   stop on that timeframe took out on noise. Beside it, how far those
   stopped setups went afterwards, in R of the stop that was hit (the
   Episode 1 measure: a 32.9-pip stop taken out on a move that ran 809).
6. **Adverse excursion in winners:** the furthest price went against each
   entry before the exit, in the setups that worked: p25, median, p75 and p90,
   in dollars and as a share of daily ATR, for each timeframe.
7. **Stop size and cost share:** stop distance quantiles in dollars and daily
   ATR; spread as a share of the stop; and the share of stops under 0.3 daily
   ATR, the framework's own minimum (`risk_and_execution.md`).
8. **Financing as a share of risk (ruling G4):** for each entry, hold, year
   and side, both short conventions, labelled placeholder (§3).
9. **The hindsight ratio (ruling F2), a named figure:** the share of trades
   net-positive at the exit in the setups that worked, divided by the same
   share in all setups, for each entry and horizon. It measures how much of
   the apparent result is selection on the outcome, and so how much the
   owner's eye would have to add to make it work.

Every table is split long and short (G4c). All-setups rows come first, then
"Selected on the outcome" rows, then the ratio, then the daily side result.

### 4.4 Size, stated before measuring

- **520 setups** (289 long, 231 short): a share has a 95% interval of about
  ±4.3 points on all setups, ±5.7 on longs and ±6.4 on shorts. After the
  window, about 386 / 378 / 477 trades (30/15/5-minute), about ±5 points.
  The setups that worked are a subset, counted at the counts stage.
- Means of R for tight entries will still be wide: the median 5-minute stop
  is about 1/8 of the 4-hour stop ($4.86 against $38.12, §1.2), so an
  untouched 5-minute trade held for days scores many R. Shares and medians
  are the readable outputs.
- R assumes the same money risked on every trade, so a tight stop means a
  large position. Every R table is repeated in dollars per ounce and in
  daily ATR, which do not depend on position size.
- The daily side result has 67 setups (±12 points on a share) and carries no
  verdict.

## 5. The catalogue (team addition 3a)

### 5.1 4-hour swing start (hindsight object; ruling F2 applies)

A confirmed 4-hour swing low from which price rose at least 1.0 daily ATR
before trading below that low, within 60 4-hour bars. Short is the mirror. A
**failed swing** is a confirmed 4-hour swing low that was traded below first.
The **window** of either is the 30/15/5-minute bars from the open of the
4-hour swing bar to the close of the next 4-hour bar (8 hours). Swing-start
and failed-swing tables are headed **"Selected on the outcome"**.

### 5.2 Structures (team addition 4; thresholds per ruling F3)

**Scale.** Each threshold is a multiple of the timeframe's own median range
(§3). The screen's thresholds were set in daily ATR on 4-hour bars; they carry
over through the measured ratio of daily ATR to the 4-hour median range,
**ρ = 3.130** (§1.2), so a screen threshold c becomes c × ρ median ranges.
The same multiples are used on every timeframe: the same shape at each
timeframe's own scale. That is a declared choice; it carries no random-walk
assumption.

| Screen threshold (daily ATR on 4-hour bars) | Here (median ranges) |
|---|---|
| 0.15 (level proximity) | 0.470 |
| 0.25 (equal lows; head beyond shoulders; shoulders equal) | 0.783 |
| 0.5 (neckline height) | 1.565 |

Every structure has a direction and a **completion bar**: the bar at whose
close it first becomes known.

| Structure | Definition (bullish; bearish is the mirror) | Completion bar |
|---|---|---|
| **Engulfing** | Exactly `entry_confirmation._detect_engulfing`: the bar closes up, its close ≥ the higher of the prior bar's open and close, and its open ≤ the lower of them. No size filter (the live definition has none) | The engulfing bar |
| **Engulfing at a level** | Engulfing whose low is within 0.470 median ranges of the most recent confirmed swing low | The engulfing bar |
| **Pin bar** | Range ≥ the median range; body ≤ 1/3 of the range; lower wick ≥ 2/3 of the range | The pin bar |
| **Pin bar at a level** | Pin bar whose low is within 0.470 median ranges of the most recent confirmed swing low | The pin bar |
| **Break and retest** | Level = the most recently confirmed swing high. Break = the first close above it. Retest = the first bar within the next 12 bars whose low touches the level. **Held** if that bar closes above the level; **failed** if it closes below | The retest bar |
| **Consolidation** | The 12 most recent completed bars span (highest high − lowest low) ≤ 2.0 median ranges, taken at the bar before the 12. It resolves at the first later close outside the span; its direction is the side of that close. (2.0 is this spec's own choice, not a screen threshold) | The resolving bar |
| **Double bottom** | Two consecutive confirmed swing lows within 0.783 median ranges of each other; the neckline (highest high between them) at least 1.565 median ranges above the higher low. Completes on the first close above the neckline within 60 bars of the second low's confirmation, before any close below the lower low | The breaking bar |
| **Double top** | The mirror of double bottom | The breaking bar |
| **Inverse head and shoulders** (bearish form: head and shoulders, the mirror) | Three consecutive confirmed swing lows; the middle one (the head) at least 0.783 median ranges below both shoulders; the shoulders within 0.783 median ranges of each other; neckline = the higher of the two peaks between them (the mirror of the screen's lower-of-two-troughs). Completes on the first close beyond the neckline within 60 bars of the right shoulder's confirmation, before any close beyond the head | The breaking bar |

Differences from the screen's 4-hour detectors: the screen's engulfing
required an opposite-coloured prior bar and a range filter; here the live
definition is used unchanged. The screen's pin bar compared with the mean
range of 14 bars; here, the median range.

### 5.3 What is reported

For each timeframe and each structure, long and short separately:

1. **How often:** occurrences per 1,000 bars.
2. **At swing starts ("Selected on the outcome"):** the share of 4-hour
   swing-start windows containing at least one completion, beside the share
   for failed-swing windows and for all 8-hour windows (the base rate), each
   with a 95% Wilson interval. A structure is only interesting if the
   swing-start share sits outside the base rate's interval; the report says
   plainly when it does not.
3. **What it resolved into (team addition 7):** from the completion close,
   the signed move in the structure's direction at the next session close,
   +2, +5 and +10 sessions, in daily ATR: mean, median, SD and share positive.
   Each beside the **drift-matched baseline**, the same measure from every
   close on that timeframe in the same direction over the same span (E7: a
   rising span makes any long look like an edge). Net of the measured spread
   (§3) as a share of daily ATR. Occurrences overlap; N is reported as
   occurrences and distinct sessions, and intervals use the session-block
   bootstrap.

## 6. Pullback continuation versus reversal (team addition 6)

**Not a classifier.** The starting answer is R48's base rate: roughly one move
in five is wholly given back within 10 sessions.

### 6.1 Populations (2021–2026 only)

- **R48 legs:** R48's detector unchanged (`first_pullback_study.find_entries`).
  Pre-registered, and small.
- **4-hour swing legs:** an impulse from a confirmed 4-hour swing low to the
  next confirmed swing high, at least 1.5 daily ATR tall. Larger, and new.

### 6.2 Outcome

For legs whose pullback reached 38.2%, 50% and 61.8% (measured from the
impulse's extreme): **continued** if price made a new extreme beyond the
impulse before retracing 100%; **reversed** if it retraced 100% first;
**unresolved** if neither within 60 4-hour bars. Base rates with 95% Wilson
intervals.

### 6.3 Candidate separators (each a simple split, with a Newcombe interval on the difference)

1. **Speed:** 4-hour bars from the impulse's extreme to the touch of the
   level, split at the population's median.
2. **Lower-timeframe structure inside the pullback:** at the touch, the
   direction of the most recent 15-minute structure break (§3).

**Why 15-minute (ruling F4), measured before the run (§1.2):** a median first pullback to 38.2% lasts 6 four-hour bars, which is
**92 fifteen-minute bars** (p25: 44). A swing point needs 9 bars and is
confirmed 4 bars later, so 15-minute bars give room for several swings and
breaks even in a short pullback. On 30-minute bars a short pullback (p25)
has only 22 bars, about two possible swings, so the structure is often not
there to read. On 5-minute bars the median pullback has 276 bars, and the
structure inside is mostly moves of a few dollars, where the spread is 7.4%
of a typical stop (§1.2). 15-minute is the middle: enough bars to have a
structure, coarse enough that it is not mostly spread. This is a judgement on
those measurements, not a test result.

The 15-minute fetch is shared machinery: R46 (15-minute entries) and GNC-1
(its M15 prerequisite) need the same series. This fetch covers 2021–2026
only; their 2006–2013 needs remain open.

### 6.4 Resolution, stated before measuring

R48's populations are too small to separate the cases. With an even split
and 50% shares, the 95% interval on a difference is about **±30 to ±42
percentage points** on 2021–2026 legs (computed 2026-11-17 from R48's USED
leg counts: falls at 38.2% ±30, rallies at 61.8% ±42). A separator would have
to move continuation by more than 30 points to show. The 4-hour swing
population exists to narrow that; its count is reported (§7.2) before any
outcome. **If no split's interval excludes zero, the report says none of them
separates the two cases.**

## 7. Run order

1. **Fetch:** done (§1.2).
2. **Counts stage:** every population, setup, entry and structure counted, no
   outcome computed, logged in validation_log before stage 3 (the GMW-1
   order).
3. **One run** of §4, then §5, then §6, through `reality_run.py --no-env`.
   Every number printed is reported, including the ones that show nothing.
4. The runner is written after this version is committed, with tests and
   named mutants: a look-ahead mutant for every confirmation delay; an entry
   that ignores "confirmed after t0"; an entry window not taken from §1.3;
   financing pooled across years or sides; a stop checked on the entry's own
   timeframe instead of 5-minute bars; an exit that differs between entries;
   a missed entry counted as a trade; a hindsight group not selected on the
   outcome; a drift baseline taken from the wrong direction.

## 8. Output stamp

Every table header and the report's first line: **DESCRIPTIVE, not tradeable.
2021–2026 only, a regime-specific description. Structures counted on history;
none is a signal.** Hindsight tables add **"Selected on the outcome"**.

## 9. Sign-off

v1's questions were answered by F1–F4 and v2's by G1–G4. Two points remain,
both from premises that did not survive measurement (§1.3):

1. **Entry window (G2).** The p75 window is applied as ruled, but it is
   shorter than one session on 15- and 5-minute entries and so drops more
   slow entries than a 1-session window would (27.3% against 8.3% missed on
   15-minute). The secondary keeps every entry within 10 sessions, bucketed.
   Keep the p75 window as primary, or make the 10-session bucketed view
   primary?
2. **Short financing (G4c).** GNC-1's convention charges shorts 2.5% and
   never credits them; G4 said shorts may receive. Both are reported. Which
   is primary?

Neither changes what is measured, only which line leads. The runner can be
written once these are signed.
