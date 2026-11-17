# GLS-1 report: what lower-timeframe structure does on gold, 2021–2026

**DESCRIPTIVE, not tradeable. 2021–2026 only, a regime-specific description
(gold rose 205% to January 2026, then fell up to 26.6%). Structures counted
on history; none is a signal.** Tables marked *Selected on the outcome* were
chosen with hindsight.

- Spec: `docs/specs/gold_ltf_structure_spec.md` v5 (af63c76).
- Runner: `studies/gold_ltf_structure_study.py` (284236c).
- Counts stage: logged 823585c.
- Verbatim output: `studies/gold_ltf_structure_result.md` (sha256
  `ad1a837ce322377d983a2fdc10f62f81e242bda9e0f582dca936118b743ef63e`).
- Run 2026-11-17: one run; project unchanged by hash.
- Costs: every cost in part B is a labelled placeholder except the measured
  OANDA spread. **There is no venue for gold** (gold plan §0a).

## The short answer

1. **A tighter entry did not beat the 4-hour entry in any cell, before or
   after costs.**
   - Every paired difference (30-, 15- or 5-minute entry minus the 4-hour
     entry on the same setup) has a 95% interval that includes zero, except
     two cells where the lower timeframe was **worse**:
     - long 30-minute at the next close: −0.136R before costs, −0.156R
       after CFD costs;
     - long 5-minute at ten sessions: −0.567R after CFD costs.
2. **Tight stops take out most winners on noise.**
   - Of the long setups that went on to work, a normal structure stop was
     hit before the exit (next close → ten sessions):
     - 5-minute: **63% → 88%**;
     - 15-minute: 49% → 77%;
     - 30-minute: 29% → 66%.
   - After those stops were hit, the move ran a median **21R** (5-minute,
     next close) in the stopped trade's direction. That is the Episode 1
     failure, and on gold it is the usual case, not the exception.
3. **No pattern resolved differently from gold's own drift.**
   - Across 216 structure × timeframe × direction × hold cells, only 2 put
     the drift baseline outside their 95% interval. About 11 would do so by
     chance.
   - The patterns appear about as often where 4-hour swings fail as where
     they start: the intervals overlap in 53 of 54 cells.
4. **Pullbacks: deeper means less likely to continue, and nothing measured
   tells the two cases apart.**
   - On 4-hour swing legs, once the pullback reached each level, the share
     that continued to a new extreme (rather than giving it all back):
     - 38.2%: **56%**;
     - 50%: **43%**;
     - 61.8%: **32%**.
   - Neither pullback speed nor 15-minute structure inside the pullback
     separates continuation from reversal in any cell.
5. **The venue did not change the entry ranking.**
   - CFD and futures placeholders rank the four entries in the same order
     for longs at every hold.
   - The two short flips are within noise.
   - The question the ranking was meant to answer is moot here: the entries
     are not separable from each other to begin with.

## 1. The setups and entries (part A, before costs)

516 four-hour structure breaks: 286 long, 230 short. Four of the 520 were
dropped because they fell in the daily-ATR warm-up.

Each setup is entered four ways with the same exit:

- **4-hour:** at the setup bar's close, with the 4-hour structure stop.
- **30-, 15- and 5-minute:** at the first lower-timeframe break after the
  setup, within 10 sessions, with that timeframe's stop.

| Entry | Long trades | Short trades | Median stop (long) | Stop under the framework's 0.3-ATR minimum (long / short) |
|---|---|---|---|---|
| 4-hour | 286 | 230 | $40.29 (1.32 ATR) | 0% / 0.4% |
| 30-minute | 265 | 200 | $14.11 (0.43 ATR) | 25% / 34% |
| 15-minute | 270 | 215 | $9.47 (0.28 ATR) | 55% / 57% |
| 5-minute | 281 | 223 | $4.89 (0.16 ATR) | **84% / 88%** |

**Most 5-minute entries break the framework's own stop rule.** Its minimum
stop is 0.3 daily ATR (`risk_and_execution.md`).

**Why winners get stopped.** In the setups that worked, price first went
against the entry by a median of about **0.3 daily ATR**, whatever the
entry timeframe:

| Entry | Median adverse move against the entry (long, next close) |
|---|---|
| 4-hour | 0.32 ATR |
| 30-minute | 0.30 ATR |
| 15-minute | 0.34 ATR |
| 5-minute | 0.28 ATR |

The median 5-minute stop is 0.16 ATR, about half the typical heat a winner
takes. The 15-minute stop (0.28 ATR) is about the same size as that heat.
The 30-minute stop (0.43 ATR) is wider.

**The deciding number (*Selected on the outcome*)**: the share of setups
that worked whose entry was stopped before the exit.

| Entry | Long: +1 / +2 / +5 / +10 sessions | Short: +1 / +2 / +5 / +10 |
|---|---|---|
| 4-hour | 1.1% / 2.8% / 9.1% / 22.2% | 0.0% / 1.0% / 6.9% / 18.6% |
| 30-minute | 29.3% / 42.5% / 55.1% / 65.9% | 29.6% / 42.2% / 56.9% / 68.6% |
| 15-minute | 48.9% / 57.4% / 67.6% / 77.3% | 46.5% / 54.9% / 64.7% / 74.5% |
| 5-minute | **62.5% / 68.8% / 81.8% / 88.1%** | 58.8% / 65.7% / 75.5% / 82.4% |

How far those stopped winners then ran, as a median in R of the stop that
was hit (long):

| Entry | Next close | Ten sessions |
|---|---|---|
| 30-minute | 6.5R | 4.1R |
| 15-minute | 12.4R | 8.8R |
| 5-minute | 21.0R | 15.9R |

The 4-hour row is low partly by construction. "Worked" means the target was
reached before the 4-hour stop, so a 4-hour entry can only be stopped after
its target.

**R before costs, per setup** (a missed entry counts 0R), with the paired
difference from the 4-hour entry. Long:

| Hold | 4-hour | 30-minute (paired) | 15-minute (paired) | 5-minute (paired) |
|---|---|---|---|---|
| +1 | +0.045 | +0.020 (**−0.136**, CI −0.254 to −0.004) | −0.013 (−0.123) | +0.182 (+0.121) |
| +5 | +0.194 | +0.322 (+0.059) | +0.406 (+0.165) | +0.176 (−0.036) |
| +10 | +0.333 | +0.426 (+0.021) | +0.362 (−0.029) | −0.066 (−0.424, CI −0.860 to +0.053) |

- **Shorts:** no paired difference excludes zero.
- **The positive long figures are mostly the span's uptrend.** A 4-hour
  long at ten sessions made +0.333R per setup (CI +0.115 to +0.548), while a short
  lost −0.186R. §4 has no drift baseline; the paired differences cancel the
  drift, which is why they are the comparison that matters.
- **The lower-timeframe means swing on rare large winners.** The 5-minute
  long median is −1.000R in every cell, and its share positive falls from
  24% to 7%.

**Hindsight ratio (F2):** the share of trades positive before costs in the
setups that worked, divided by the same share in all setups.

- Longs: **1.30 to 1.60**.
- Shorts: **1.38 to 2.19**.
- Highest for 5-minute shorts (2.19 at +5 and +10).
- So selecting on the outcome inflates the apparent hit rate by 30% to
  120%. That is how much an eye that already knows which swings worked
  would add.

**Wait buckets (H1):** no consistent pattern by wait. The buckets past one
session are small (30-minute 7–12 bars: 23–39 trades; 15-minute: 3–4).

**1-session cut (secondary):** close to the main result, because almost
every entry comes within a session (5-minute: all of them).

**Volatility (H3), before costs, per setup:**

| Cell | Low volatility | Middle | High |
|---|---|---|---|
| Long, 5-minute, +5 | **−0.489R** (CI −0.813 to −0.131) | +0.344 | +0.765 (CI −0.344 to +2.123) |
| Long, 4-hour, +5 | +0.405 (CI +0.124 to +0.711) | +0.057 | +0.098 |

- **The quiet-market failure of 5-minute longs is clear:** its interval
  excludes zero.
- **The volatile-market success is not established:** the interval spans
  zero.
- **Shorts show neither.**
- **Many cells were split, with no correction:** read the single
  significant cell as a description, not a rule.

## 2. Costs (part B; placeholders except the measured spread)

The realised cost was much smaller than the full-hold financing table in
spec §1.3 suggested. **Tight entries are mostly stopped out early, so they
rarely carry financing for long.**

| Long, 5-minute, +10 | Before costs | CFD (both pay) | Futures (basis carry) |
|---|---|---|---|
| Mean net R per setup | −0.066 | −0.311 (cost 0.245R) | −0.215 (cost 0.149R) |

| Long, 4-hour, +10 | Before costs | CFD | Futures |
|---|---|---|---|
| Mean net R per setup | +0.333 | +0.228 (cost 0.105R) | +0.267 (cost 0.066R) |

- **Ranking flip check (J2), longs:** the same order under CFD and futures
  at every hold.
- **Ranking flip check (J2), shorts:** flips at +1 (30- vs 15-minute) and
  +10 (5-minute against 30-minute and 4-hour), each **within noise** (the
  paired differences' intervals include zero under both structures).
- **H2 flags:** no short cell was positive only because of a carry credit,
  CFD or futures.
- **Reading:** the futures placeholder costs less than the CFD by about
  0.04–0.10R a trade in these cells. That moves levels, not the order of
  the entries. Whether the venue decision matters more than the entry
  timeframe is not shown either way: the entries could not be told apart.

## 3. The catalogue (§5)

The 4-hour swing points (*Selected on the outcome*): 420 up and 381 down
starts; 246 and 281 failed swings; 8,321 base windows.

- **Frequency:** for example, 30-minute engulfing appears about 66 times per
  1,000 bars each way, and head and shoulders 1.6–1.8. The full table is
  in the output.
- **At swing starts, the pre-registered rule is weak, and I'm saying so
  here.**
  - The rule flags a structure when its swing-start share falls outside the
    *base* rate's 95% interval. That interval is narrow (8,321 windows),
    and the rule ignores the swing-start share's own uncertainty. It flags
    41 of 54 cells.
  - **A stricter reading, added after the run and labelled as such:** the
    base rate falls outside the swing-start share's own interval in 11 of
    54 cells.
  - In those 11, the failed-swing share is about the same. The
    consolidation cells are the clearest case: around 8% at swing starts,
    5–6% at failed swings, 16–18% base on 30-minute.
  - **Swing-start and failed-swing intervals overlap in 53 of 54 cells.**
    The one exception: 5-minute bullish pin bars, 86.7% at swing starts
    against 77.2% at failed swings.
  - **A structure appearing near a swing does not mark the swing that
    runs.**
- **What each resolved into (team addition 7):**
  - The signed move at +1, +2, +5 and +10 sessions, in daily ATR, against
    the drift baseline.
  - The drift baseline lies outside the structure's 95% interval in **2 of
    216** cells: 30-minute bullish consolidation at +1 (+0.143 against
    +0.058), and 30-minute failed bearish retest at +10. About 11 would do
    so by chance.
  - Bullish structures "worked" and bearish ones "failed" in this span
    because gold rose. Measured against that drift, they add nothing
    detectable.

## 4. Pullbacks (§6; not a classifier)

| Population | Reached 38.2%: continued | Reached 50% | Reached 61.8% |
|---|---|---|---|
| 4-hour swing legs | **56.2%** [50.3, 62.0] (153/272) | **43.1%** [36.6, 49.9] (91/211) | **31.6%** [25.2, 38.9] (55/174) |
| R48 legs | 65.4% [51.8, 76.8] (34/52) | 47.6% (20/42) | 33.3% (11/33) |

- **How these rates are measured:** the share is of resolved legs.
  Continued means a new extreme came before a 100% retrace, within 60
  4-hour bars.
- **Not the same as R48's one-in-five:** R48's "one move in five given
  back" is unconditional. Once a pullback has already reached 61.8%, about
  two in three are given back entirely.
- **Separators (team addition 6):**
  - Pullback speed and the direction of the last 15-minute structure break
    at the touch: **none separates continuation from reversal** in any
    cell.
  - The nearest was speed at 38.2% on swing legs: slow pullbacks continued
    63% against 52% for fast ones, a difference of −11.1 points (CI −22.5
    to +0.9).
  - Several R48 cells are INSUFFICIENT (a side under 20).

## 5. What this does and does not say

- **It says:** on 2021–2026 gold, refining a 4-hour entry down to 30-, 15-
  or 5-minute structure bought no measurable improvement and cost most
  winners. The common chart patterns resolved like the drift. Pullback
  depth carries a base rate, and speed and lower-timeframe structure added
  nothing to it.
- **It does not say:**
  - that tight entries cannot work: the volatile third is untested at this
    sample size;
  - anything about 2006–2013, which stays clean for a test;
  - anything about real costs: there is no venue.
- **Disclosed:**
  - One blind crash check ran before the counted run. Its output was
    deleted unread, and the run is deterministic.
  - The catalogue's swing-start rule is weak as pre-registered; the
    stricter reading was added after the run.
  - The 4-hour deciding number is low partly by construction.
  - There is no correction for the many cells; nothing here is a test.
