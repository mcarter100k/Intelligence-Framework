# Chart reading method: top-down structure, Fibonacci and zones

> **Status: INFORMED PRIOR, written 2026-11-04.** This is a way of reading a
> chart, not a tested edge. Each rule is tagged with its evidence: a finding
> number (`R..`, see `research_findings.md`) where the framework has tested
> something close, or **UNTESTED** where it has not. Nothing here is
> VALIDATED, and none of it runs in the live brief.

The live framework does not do this markup. `levels_context.py` gives the
previous day and week highs and lows, the session high and low and the Asian
range. `regime_detection.py` labels structure internally. Neither produces
swing levels, zones or Fibonacci lines. This file is for the trader reading
a chart by hand, and for an agent asked "how would you mark this up?".

## 1. Top-down order

Read weekly, then daily, then 4-hour, then hourly. At each timeframe answer
three questions before moving down:

1. **Which way is the structure pointing?** Higher highs and higher lows (up),
   lower highs and lower lows (down), or neither.
2. **What was the last break?** The most recent close beyond a prior swing
   high or low, and when it happened.
3. **Where does that read fail?** The swing level whose break would flip it.

Then write one line per timeframe and look for disagreement. When they
disagree, the higher timeframe sets the direction to trade and the lower
timeframe sets the timing (**UNTESTED**). The framework stands aside when its
timeframes disagree; a hand read should at least name the conflict.

## 2. Swings and structure

- **A swing high** is a bar whose high is the highest of the k bars on each
  side; a swing low is the mirror. It is only confirmed k bars later. The
  2026-11-04 markup used k = 2 weekly, 3 daily, 4 on the 4-hour and 5 hourly
  (**UNTESTED** choice; any fixed k is fine if it is used every time).
- **Labels:** higher high, higher low, lower high, lower low. The first lower
  low after a run of higher lows (or the mirror) is the first crack in a trend.
- **A break needs to hold.** On GBP/AUD daily data, 71% of moves beyond a
  confirmed swing extreme closed back inside within 3 days. A break that had
  not gone about 1.5 daily ATR was more likely to fail than hold (R24).
- **On gold, only a close counts as a break, and even a close is a coin
  flip.** A wick through the latest daily swing was back inside within 3 days
  about half the time in 2006–2013 and 2 times in 3 in 2021–2026. A daily close
  beyond came back inside 43–45% of the time in both eras. Closes half a day's
  range or more beyond held more often in the older data (R45, descriptive).
- **Two hourly closes filter fakes but are not an edge.** On 2005–2013 GBP/AUD
  hourly data, 31% of first closes beyond a swing were fakes, and trades on
  them averaged −0.6R. Waiting for the second close removes them, yet the
  confirmed breaks still lost after costs (−0.11R), and so did entering on the
  retest (−0.09R) (R43). Use the rule to stay out of fakes, not as a reason
  to enter.
- **Filtering level breaks by trend and room did not create an edge.** Breaks
  of daily and weekly swing levels, taken only with the daily trend and only
  when the next level lay beyond a 1.5R or 2.5R target, lost −0.28 to −0.35R
  after costs on 2005–2013 GBP/AUD (R44). Zones still tell you where; they
  have not yet told anyone when to enter.
- **A 15-minute entry did not rescue the breakout.** Timing the same entries
  on the 15-minute chart (touch the level, then a candle closing back beyond
  it) lost about the same as hourly entries, and a tight stop under the
  15-minute low lost more: −0.26R, with three trades in four stopped (R46).
- **The last higher low is not a safe floor.** The first counter-trend move
  went beyond the last higher low (or lower high) in 40% of daily trend legs
  (R21). Deep bounces breach it more often, largely by construction (R22).

## 3. Fibonacci

**When to draw (UNTESTED as a rule):**
- Only after an **impulse that broke structure**: for a long, a move that took
  out a prior swing high.
- Only once the **extreme is confirmed**: price has pulled away from it and the
  timeframe below is making lower highs.
- The only mechanical definition the framework has tested is the first
  pullback study's: an H4 move of at least 2 daily ATR off a new 120-bar
  extreme (`docs/specs/first_pullback_study_spec.md` §4).

**How to anchor:**
- 0% at the wick of the swing that launched the move (the impulse origin).
- 100% at the wick of the new extreme.

**When to redraw or delete:**
- **New extreme:** move the 100% anchor to it. The old lines are stale.
- **Price breaks the origin:** the impulse failed. Delete the fib.
- **Same anchors rule every time.** Choosing anchors after seeing where price
  reacted makes any fib look right in hindsight.

**How deep the first pullback goes (R39, descriptive):** of the qualified
impulses in the 2005–2013 study data, the share that pulled back at least
this far within about 10 sessions of the move's start:

| Pullback reached | GBP/JPY (135 impulses) | GBP/AUD (121 impulses) |
|---|---|---|
| 23.6% | at least 89.6% (not measured) | at least 81.0% (not measured) |
| 38.2% | 89.6% | 81.0% |
| 50% | 74.1% | 66.1% |

So a 23.6% pullback is usually too shallow to plan around, especially on
GBP/JPY. **Reaching a level is not holding it:** buying the first touch of
38.2% or 50% showed no edge on either pair (R37, R38). Nothing tested yet says
which pullbacks stop shallow and which go deep.

**On gold (R48, descriptive):** the same detector on gold, rallies and falls
apart, 2006–2013 / 2021–2026:

| Pullback reached | Gold rallies | Gold falls (bounce) |
|---|---|---|
| 23.6% | 93.3% / 100% | 100% / 100% |
| 38.2% | 71.1% / 78.1% | 89.5% / 81.8% |
| 50% | 62.2% / 59.4% | 75.4% / 68.2% |
| 61.8% | 55.6% / 43.8% | 59.6% / 50.0% |
| Whole move given back | 20.0% / 18.8% | 24.6% / 25.0% |

Most gold pullbacks reach 38.2%; 50% and 61.8% are about even (50% is reached
by most fall bounces); about 1 move in 5 is wholly given back within 10
sessions. A stop at 61.8% is reached by the first pullback alone about half
the time. Gold is about like the GBP pairs. Legs: 32–57 per cell.

**Gold's sizes in percent (R47):** a typical day is 1.4–1.6% of price, a
4-hour bar about a third of a day, an hour about a sixth. Keep gold thresholds
in daily ranges, not dollars: the dollar size of "half a day" changes with
gold's price and mood (2.26% of price on 2026-11-16, 1.63× the 2021–26 median).

## 4. Zones

- **Build a zone where several reasons overlap** (**UNTESTED** that overlap
  beats a single level). Examples: an old breakout level, a Fibonacci line
  and a recent spike low within a few pips of each other.
- **Levels give location, not timing.** About 90% of big turns happen at an
  existing level, against about 58% of all bars sitting near one (R15). But
  trading rejections at levels won 50% of the time with a median of −1R
  (R14). Use levels for where to watch, where to put stops and where to take
  profit; do not treat a touch as a signal.

## 5. Trading a zone

Every step here is **UNTESTED** unless a finding is named.

1. **Only in the direction of the bigger structure.** The first pullback
   study's 13-week trend filter turned a negative result into an
   inconclusive one on GBP/JPY (R38: no filter −0.105R over 105 touches,
   with the filter +0.073R over 37).
2. **Wait for the timeframe below to turn** (a higher low, then a close back
   above its last lower high) rather than resting a limit order at the line.
3. **Stop beyond structure, not beyond a Fibonacci line.** The stop must sit
   between 0.3 and 1.5 daily ATR (`risk_and_execution.md`).
4. **Target the next higher-timeframe level.** It must pay at least 1.5R
   after spread (`risk_and_execution.md`).
5. **Do not pick the exact line.** Treat 38.2–50% as one zone. A split entry
   (half at each, one stop) avoids betting on a single line.
6. **First pullback only.** A second or third pullback in the same leg is a
   different setup and has not been tested.
7. **Log every setup, taken or passed** (`trader_review.md`). Without the log,
   none of the above can ever be graded.

## 6. Worked example: GBP/JPY, 2026-11-04

Read from OANDA mid-price candles at about 9 PM PST. Price 213.08.

| Timeframe | Read | Fails at |
|---|---|---|
| Weekly | Long-term up to 219.61; since July a lower high (217.48) and lower lows (207.10, 206.89). A bounce inside a correction, at the 213.25 halfway line of the drop | Uptrend back only above 217.48 |
| Daily | Lows stepping up 206.89 → 208.20 → 208.37 → 209.12; broke the 212.0 range top | Below 209.12 |
| 4-hour | Up-leg 209.57 → 213.78, higher lows 210.29 and 211.55. Fibonacci 38.2% 212.17, 50% 211.67, 61.8% 211.18 | Below 211.55 |
| Hourly | Lower high 213.55 and a break of the 213.12 low: pulling back | Back above 213.55 |

**Zone:** 212.0–212.2 (old breakout 212.0–212.12, 38.2% at 212.17, spike low
212.13). **Resistance:** 214.0–215.0 (weekly 61.8% at 214.75). The
framework's own brief stood aside (daily trend strength 18/100; timeframes
disagree). Chart: https://claude.ai/artifact/LKVfDHLDbZ33ebnCpWjmy2 (private
to the owner).

## 7. Open questions worth a pre-registered study

- What makes a first pullback stop shallow or go deep: momentum of the
  impulse, higher-timeframe resistance in its path, the trend filter?
- Does waiting for the timeframe below to turn beat a limit order at the zone?
- Do zones built from several overlapping reasons turn price more often than
  a single level?
