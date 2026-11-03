# Spec: the first pullback after a range turn (pre-registered, 2005–2013 STUDY data)

**Status:** pre-registered 2026-11-03 at the owner's request. This file, the
runner (`studies/first_pullback_study.py`) and its suite test
(`tests/test_first_pullback_selftest.py`) are committed together, with their
sha256 and the data files' sha256 recorded in validation_log in the same
commit. No 2005–2013 outcome of this rule has been computed. The counts stage
(entries and episodes only, no R) runs after this commit and is logged before
the full run. The full run happens once, and its output goes to validation_log
verbatim, whatever it says.

## 1. Why, and the question

- **The trigger.** The framework stood aside through a GBP/AUD rally from the
  2026-10-28 low of 1.8873 to 1.9257 on 2026-11-03. The owner's own entry for
  that move: after the turn off the range low, buy the first 4-hour pullback
  to the 38.2% retracement of the impulse, in line with the bigger trend.
- **The question.** Does that rule, written down exactly and traded the same
  way every time, make money after costs on data it was not designed on?
- **Provenance (M6).** The rule comes from one memorable chart. That chart is
  in the USED span (2026), which plays no part in this test. The parameters
  below are the owner's levels (38.2%, 50%) plus round-number choices made
  here, before any outcome, without a grid. None was chosen by looking at
  2005–2013 results.
- **Frame (data_map_spec §5).** A 2005–2013 result answers "does this survive
  conditions it was not designed on", not "does this work now".

## 2. Prior work, and how this differs from R20

- **R20** (first-bounce with-trend entries, 2026-09-11): negative in every one
  of 8 cells, but every cell had N < 30, 21 of the 41 legs were in-sample, and
  it was descriptive only. Its legs were D1 trend legs from the structure
  labels; entry at 50–85% progress towards the last lower high / higher low;
  target at the prior extreme; GBP/AUD only, 2023–2026.
- **This study differs in the parts that matter:**
  1. **The leg** starts at a 20-day range extreme (a turn), not mid-way through
     a labelled D1 trend.
  2. **The entry** is a fixed fraction (38.2% or 50%) of the impulse on H4,
     not progress towards a structural level.
  3. **The bigger trend** is the 13-week direction of price, not the D1
     structure label. R23 showed that label lags and gives back 116% of a
     move.
  4. **The exit** is a fixed 30-bar horizon graded on the stop, with costs
     and financing.
  5. **The evidence:** both pairs, nine years of STUDY data never used for
     this rule, and enough episodes for a confidence bound, which R20 never
     had.
- **Why it is not a re-test of a refuted premise.** R20 was not a refutation:
  it was a small, in-sample, descriptive sample. This is the first adequately
  sized out-of-sample test of a with-trend pullback entry. The honest prior is
  against it, though. R20 was negative in every cell. R14 (level fades) and
  R17 (THRUST_PULLBACK) found no edge in related entries. That prior is
  stated now, so a negative result is not a surprise and a positive one gets
  no benefit of the doubt.
- **R27:** with-trend pullback entries are scarce (the first-bounce entry was
  empty in 75% of weeks). The counts stage shows whether this rule is
  equally scarce before any R is seen.
- **R10/R17 (in-sample selection):** there is no grid here. Two cells, both
  named by the owner, are reported whatever they show.

## 3. Data

- **Prices:** OANDA mid D1 and H4 candles, STUDY partition, 2005-01-01 →
  2013-12-30. These are the files fetched by the US-event study through the
  embargo-guarded `history_study_gate_s3.fetch`, at
  `~/intel_study_archives/us_event_reaction_data/`. Their sha256 values were
  recorded in validation_log on 2026-11-01 and are pinned in the runner:
  - `GBP_JPY_D.csv` `ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a`
  - `GBP_JPY_H4.csv` `f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764`
  - `GBP_AUD_D.csv` `661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939`
  - `GBP_AUD_H4.csv` `a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77`
- **Refusals.** The runner refuses any file whose hash differs, and any bar
  opening before 2005-01-01 or at or after 2013-12-30 22:00 UTC (the start of
  the embargo and the SEALED EXAM). It makes no network call.
- **Conversion:** the approved weekend rule (`history_study_convert.convert`):
  Saturday-session candles dropped, Sunday-session candles folded into
  Monday. The bar index is the converted H4 series. A session is the New York
  date of (open + 7 h).
- **Not used:** 2014-01-01 → 2021-04-25 (SEALED EXAM), and 2021-04-26 onward
  (USED, learning only).

## 4. The rule (long side; the short side is the exact mirror)

### 4.1 The range extreme (anchor)

- An H4 bar whose low is **strictly lower than every low of the previous 119
  H4 bars**: a new low over 120 bars, about 20 trading sessions.
- This bar is the anchor. Its low is the impulse origin A.

### 4.2 The impulse

- The extreme B is the highest high of the bars **after** the anchor bar.
  The anchor bar's own high is excluded, because on that bar the high may
  have come before the low.
- The leg **qualifies** once B − A ≥ **2.0 × D1 ATR**.
  - D1 ATR is the simple mean of the true range of the **14 sessions completed
    before the anchor's session**.
  - The ATR is fixed at the anchor.
- **Lifetime:** the fill must come on one of the 60 H4 bars after the anchor
  bar (about 10 sessions). Otherwise the leg expires.
- **Replacement:** a new 120-bar low replaces the current leg. The move
  failed, and a new leg starts from the new low.

### 4.3 With the bigger trend

- The **13-week direction**: the sign of the close of the last completed D1
  session minus the close 65 sessions before it. It uses only sessions
  completed before the fill bar's session.
  - Longs need it **> 0**; shorts need it **< 0**.
  - A flat reading (0) is neither.
- **Why this measure:** it is the time-series momentum horizon (1–12 months)
  for which there is published evidence. Three months is "bigger" than a
  one-week trade. It is known at the time and does not lag like the
  structure label (R23).

### 4.4 Entry: the first pullback

- At each H4 close at which the leg is qualified, a buy limit rests for the
  next bar at **level = B − f × (B − A)**:
  - **f = 0.382**: the 38.2% cell, the owner's entry;
  - **f = 0.5**: the 50% cell, the pre-declared second cell.
  - B is the extreme as of that close. A new high on the next bar does not
    move the order during the bar.
- **The first bar whose low reaches the level is THE pullback.** It fills at
  **min(open, level)**: the level, or the open if the bar gaps below it.
- **That first touch consumes the leg.** If the 13-week direction is not with
  the trade at that moment, there is no trade, and later touches of the same
  leg are not taken. This is the "first pullback" rule; a second or third
  pullback is a different setup.
- No order rests before the leg qualifies. A dip on the bar that qualifies
  the leg is not an entry.
- Each cell runs its own detector. The 50% cell does not see the 38.2% cell's
  touches.

### 4.5 The short side

- The short side is the exact mirror: a new 120-bar high, an impulse down of
  at least 2 ATR, a sell limit at B + f × (A − B), and a 13-week direction
  < 0.
- The runner implements this by negating prices. That guarantees the mirror
  and is checked by the self-test.
- **Why the short side is included:** the owner's logic (turn off a range
  extreme, then the first pullback with the bigger trend) does not depend on
  direction, and neither GBP cross has a structural drift that makes one side
  special. Long and short episodes are pooled in each cell and reported
  separately as a secondary result.

## 5. Stop, horizon, grading and costs

### 5.1 Primary stop: the impulse origin

- The stop is A − 0.1 × ATR (for a short, A + 0.1 × ATR).
- The impulse origin is the structural invalidation: if the range low breaks,
  the turn failed.
- With a 2-ATR minimum impulse, the risk is at least 0.86 ATR (38.2%) or
  1.1 ATR (50%). That keeps the stop out of noise (M16).

### 5.2 Secondary stop: the 61.8% level

- The stop is the 61.8% retracement level minus 0.1 × ATR.
- Same entries, same episodes. It is reported but never changes a verdict.
- In the 50% cell it sits only 11.8% of the impulse away from the entry.

### 5.3 Horizon and grading

- The fill bar is bar 0. The stop is checked on the fill bar and the 30 bars
  after it, on the real converted H4 index.
- **Stopped means −1R**, whatever happens later (M14). A fill bar that reaches
  the stop is stopped on that bar. Price passes the entry level before it
  reaches the stop, so that order is certain.
- Otherwise R = (close of bar 30 − entry) ÷ risk.
- **Gaps through the stop** are graded −1R (the repo convention). The loss at
  the gap's open is kept as a secondary sensitivity.
- **A fill at or through the stop** (the bar opens beyond the stop) is graded
  −1R at the intended risk. This is conservative.
- **Ungraded:** a fill whose 30-bar horizon runs past the last STUDY bar is
  ungraded and counted. The horizon never reaches into the embargo.

### 5.4 Costs, charged on every trade

- **Primary spread: the era schedule from data_map_spec §4**, applied by
  entry year (round trip, in pips):

  | Pair | 2005–2009 | 2010–2013 |
  |---|---|---|
  | GBP_AUD | 10 | 7 |
  | GBP_JPY | 6 | 5 |

  - **Deviation from the request, stated:** the request named a 3.0-pip
    spread. data_map_spec §4 is frozen. It says the era schedule applies in
    "every STUDY/EXAM computation" and that "no result computed under a
    different schedule is citable". So the verdict uses the era schedule.
  - **The 3.0-pip spread (the present-day cost) is a pre-declared
    secondary,** reported beside the verdict for every cell. Era spreads are
    the more conservative of the two. A cell that passes on era spreads
    passes on 3.0 pips too.
- **Financing:** period-appropriate policy rates from
  `studies/policy_rates_2003_2014.json` (BoE, RBA and BoJ step functions, as
  in the carry study), taken on the entry session's date.
  - A side earns its rate gap minus a **1.0% a year broker markup**:
    side × (r_GBP − r_quote) − 1.0%. A paying side pays the gap plus the
    markup.
  - In pips: entry price × net rate × nights ÷ 365 ÷ pip size.
  - **Nights:** `shadow_cost_regrade.rollover_nights` counts each 17:00 New
    York rollover after the entry and at or before the exit, with
    Wednesday's counted 3 times.
    - The entry instant is the fill bar's open. H4 bars open on the 17:00
      New York boundary, so a rollover at that instant comes before the fill
      and is not charged.
    - The exit is the stop bar's open, or the close of bar 30.
- **R after costs** = raw R − spread ÷ risk + financing ÷ risk, everything in
  pips.

## 6. Episodes

- Per cell, long and short trades are pooled on the pair's converted H4 bar
  index and sorted by fill bar.
- A trade starts a new episode only if its fill bar is **30 or more bars
  after the current episode's first fill**. This is the
  `foundation/tools/episodes.count_episodes` rule, and the self-test checks
  the two agree.
- **An episode's R is the R of its first trade**: the one that would have
  been taken.
- Same-bar ties (a long and a short on one bar) are ordered long first. This
  is expected to be vanishingly rare, and the counts stage reports it if it
  happens.

## 7. Cells and the test

- **Four cells:** {GBP_AUD, GBP_JPY} × {38.2%, 50%}. Each is its own question.
- **The statistic:** the mean episode R after era spread and financing.
- **Lower bound:** a percentile bootstrap, one-sided, with a Bonferroni
  correction over 4 cells: confidence 1 − 0.05/4 = **0.9875**.
  - It uses `power_check.bootstrap_lower_bound` with 20,000 resamples and
    seed 7.
- **Upper bound for refutation:** the framework's futility standard
  (`docs/specs/futility_rule_spec.md`), a **90%** one-sided upper bound.
  - It uses `power_check.bootstrap_upper_bound` with 20,000 resamples and
    seed 7.
  - It is uncorrected. A correction would only make refutation harder, and
    the 90% level is the bar already adopted for the shadow candidates.
- **Reported for every cell:** N with its tier (N < 20 INSUFFICIENT, 20–59
  developing), mean, median, SD, both bounds, the mean without the best
  episode, max drawdown in R (cumulative episode R in time order), win rate,
  median winner and median loser, stop-outs, and the average spread cost,
  financing, nights and risk.

## 8. Verdict per cell (decided now)

| Verdict | Condition |
|---|---|
| **INSUFFICIENT** | N < 20 episodes. No verdict. |
| **SUPPORTED** | Bonferroni lower bound > 0 **and** mean without the best episode > 0 |
| **REFUTED** | 90% upper bound < +0.15R: even the optimistic end is below the smallest edge worth trading |
| **INCONCLUSIVE** | anything else |

- **SUPPORTED** is the strongest verdict STUDY data can give. It means the
  rule earns a sealed-exam spec of its own (data_map_spec §7, a team
  decision). It does not mean "trade it".
- **REFUTED** is recorded in research_findings as a refuted premise for that
  pair and level.
- **INCONCLUSIVE** changes nothing: the framework keeps standing aside on
  this setup.
- **Median R and max drawdown** are reported beside the verdict and do not
  change it. A SUPPORTED cell with a −1R median or a drawdown beyond 12R
  (the data_map §6 template) will be flagged as such in the reading.

## 9. Power (stated before the run)

- **Assumed SD of episode R:** 1.2R (power_check's default; −1R losses and a
  long right tail).
- **Expected N:** not counted from these data before this commit. A rough
  prior comes from R27, which found H4 swings of at least 1 ATR about twice
  a week on GBP/AUD. A turn off a 20-day extreme followed by a 2-ATR impulse
  may come 1–3 times a month per pair across both sides. After the trend
  filter, the touch requirement and episode collapse, that suggests roughly
  **40–120 episodes per cell over nine years**. The counts stage replaces
  this guess with the real number before any R is computed.
- **From `power_check` at α = 0.0125 (one-sided):**

  | N | Power for a +0.15R edge | Smallest edge detectable at 80% power |
  |---|---|---|
  | 40 | 7% | +0.58R |
  | 60 | 10% | +0.48R |
  | 100 | 16% | +0.37R |
  | 150 | 24% | +0.30R |

- **N required for +0.15R at 80% power: 609 episodes per cell.** This data
  cannot reach that. Pooling all four cells would not either, because they
  share legs.
- **What that means, said now:**
  - **SUPPORTED** is reachable only if the true edge is large, roughly
    +0.4R or more.
  - **A real +0.15R edge would almost certainly read INCONCLUSIVE.**
  - **REFUTED needs an observed mean below roughly −0.05R (N = 60) to
    0.00R (N = 100)** (0.15 − 1.28 × 1.2 ÷ √N). With no edge at all, about 4
    to 5 runs in 10 would read REFUTED. With R20's −0.12R, about 7 in 10
    would (N = 60).
  - An INCONCLUSIVE verdict is therefore not "maybe it works". It is "this
    much history cannot tell". The forward ledger or a larger universe would
    be needed.

## 10. Secondary analyses (reported; never change a verdict; descriptive)

1. R before costs.
2. A flat 3.0-pip spread with financing (the present-day cost), with the full
   statistics.
3. Financing markup of 0% and 2%.
4. Stops filled at the gap open, with the count of gapped stops and of fills
   through the stop.
5. The secondary stop below the 61.8% level (§5.2), with the full statistics.
6. Long and short episodes separately.
7. No trend filter: every first touch is taken, and its own episodes are
   counted. This shows whether the 13-week filter adds anything.
8. Sub-periods, the same cuts as the carry and US-event studies:
   2005-01→2008-06, 2008-07→2009-06 (the crisis), 2009-07→2013-12.
9. By year: N and mean R.
10. Leg counts: anchors, qualified impulses, first touches, touches against
    the 13-week direction, expiries, replacements, warm-up, and fills
    ungraded at the end of the data.
11. Both pairs pooled at 38.2%, descriptive only. It is not a fifth cell and
    has no verdict.

## 11. Run discipline

1. **`selftest`** must print `SELFTEST OK`. It checks, on synthetic bars:
   - the leg detector: a replica of the owner's leg (A 1.8873, B 1.9257, ATR
     0.0120, entry at 1.9110312); the 2-ATR minimum; the 120-bar strict low;
     the anchor bar's high excluded; no order before qualification; the first
     touch consuming the leg, including against the trend; a flat trend; the
     inclusive leg window; replacement by a lower low; warm-up;
   - the fill: at the level; at the open on a gap; the order using the
     previous close's extreme;
   - the stop and horizon: a timed exit computed by hand; stop touches on
     bars 30 and 31 after the fill; a stop on the fill bar; a gap through the
     stop; a fill through the stop; ungraded at the end of data;
   - the short mirror, with an identical R; the 61.8% secondary stop;
   - costs: era spreads; financing for a long and a short against hand
     numbers; the 3.0 secondary; no rollover on a fill-bar stop; a DST-week
     rollover count;
   - context from completed sessions only, for both ATR and trend, and
     warm-up;
   - episode collapse, matching `episodes.count_episodes`;
   - the verdict boundaries; Bonferroni actually applied; a known +0.6R edge
     SUPPORTED; a −0.23R cell REFUTED; a zero edge SUPPORTED in at most about
     1.25% of runs;
   - the embargo and sealed-exam refusals, and the data-hash refusal.
2. **The self-test is mutation-tested** (at least 8 mutants, each reported as
   caught or survived) before the pre-registration commit.
3. **Commit** this spec, the runner and the suite test, with their sha256 and
   the data sha256 in validation_log. This is the pre-registration.
4. **`counts`** (through `scripts/reality_run.py --no-env`, so every side
   effect is neutralized and certified) prints legs, entries and episodes per
   cell, by side and by year. It prints no R, no stop and no outcome. That
   output is logged and committed before `full`.
5. **`full`** runs once. It refuses if the report file already exists or if a
   data hash differs. Its output goes verbatim to validation_log and to
   `studies/first_pullback_study_result.md`. Each cell's verdict goes into
   `foundation/research_findings.md`.
6. **Any change** to this spec after step 3 is a new pre-registration with a
   new id, logged as such. Nothing is tuned after a result is seen.

## 12. Limits, stated now

- **Mid prices.** A limit at the mid level fills in reality only when the
  ask (for a buy) reaches it. The spread charge covers this approximately.
- **H4 resolution.** Within one bar the order of events is unknown. The rules
  in §4.4 and §5.3 are chosen so that no case depends on it, except the gap
  sensitivity.
- **Financing on a fixed rate.** The rate is taken at entry. Changes during a
  trade (at most about 7 trading days) are ignored.
- **Old era.** The study spans the 2008 crisis and the start of zero rates.
  The result is about surviving other conditions, not about 2026.
- **One chart's idea.** The rule was suggested by one chart (M6). Testing it
  honestly is the point. A pass here would still need the sealed exam and
  the forward ledger.
