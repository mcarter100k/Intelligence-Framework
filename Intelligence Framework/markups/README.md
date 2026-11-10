# Markup playbook: the weekly routine, why each step exists, and how to label

One file per week (`2026-W46.md`, …). This playbook stays the same every
week; change it only through the Friday review, one rule at a time.

**Status:** a way of reading charts (INFORMED PRIOR), not a tested edge. Where
the framework has evidence, it is cited. Everything else is judgement, and
the weekly scoring is how we find out whether that judgement is any good.

---

## 1. The weekly loop

| When | You | Why |
|---|---|---|
| **Sunday, before the 2:00 PM PT open** | Screenshot last week's chart. Delete 4-hour and hourly marks, broken zones and stale fibs. Do the top-down read yourself (§2), then send it for review. | The screenshot keeps last week gradeable. Redoing the lower timeframes stops old noise from anchoring you. Reading first, before any review, is how the skill gets built. |
| **Each day** | Update 4-hour and hourly only. Leave weekly and daily zones alone unless one breaks. | Higher-timeframe levels move slowly. Redrawing them mid-week is usually reacting to noise. |
| **Friday after the 2:00 PM PT close** | Screenshot. Score every zone (§5). Write one lesson and at most one rule change. | Fixed scoring turns the week into evidence instead of a story. One change at a time shows which change helped. |

## 2. The top-down read: three questions per timeframe

Read **monthly → weekly → daily → 4-hour → hourly**, and answer these three
for each before moving down:

1. **Which way is it pointing?** Higher highs and higher lows (up), lower
   highs and lower lows (down), or neither.
   *Why:* structure tells you who has been in control. Bigger timeframes
   reflect bigger, slower money; smaller ones are mostly noise around it.
2. **What was the last break?** The most recent close beyond a swing high or
   low, with its date.
   *Why:* it is the market's latest change of mind. A trend is only a trend
   until something breaks it.
3. **Where is the read wrong?** The swing price whose break flips it.
   *Why:* deciding this before you trade is what keeps a dead idea from
   being held. It becomes the logic behind your stop.

**When the timeframes disagree, write the conflict down.** The higher
timeframe sets the direction and the lower one sets the timing (UNTESTED).
The framework stands aside when its timeframes disagree, so a hand read
should at least name the disagreement.

## 3. Swings: the same rule every week

- **A swing high** is a candle whose high is the highest of the k candles on
  each side; a swing low is the mirror.
- **The rule:** k = 2 monthly and weekly, 3 daily, 4 on the 4-hour, 5 hourly.
- **Exact prices** come from `studies/markup_swings.py` (OANDA candles), not
  from eyeballing a screenshot.
- **Why a fixed rule:** if you choose swing points after seeing where price
  reacted, every line looks right in hindsight. A fixed rule makes your
  marks reproducible, so the Friday scoring means something.
- **A swing is confirmed only k candles later.** Until then it is a
  candidate, not a level.

## 4. Zones

- **A zone is a price band where several reasons overlap.** For example, an
  old breakout level, a Fibonacci line and a spike low.
  - *Why a band, not a line:* price does not respect exact numbers. Spread
    alone is about 5 pips on GBP/AUD, and different traders see the same
    level a few pips apart.
  - *Why several reasons:* one reason is a line anyone could draw. Overlap
    is what makes a zone worth watching (UNTESTED that it beats a single
    line).
- **Width:** no wider than about half a daily average range (about 60 pips
  on GBP/AUD now). Wider than that, it tells you nothing.
- **At most three zones above price and three below.**
  - *Why:* about 58% of all bars already sit near some level (R15). With
    more lines, price is always "at a level", and you can justify any trade.
- **Levels give location, not timing.** About 90% of big turns happen at a
  level, but trading the rejection at a level won 50% of the time, with a
  median of −1R (R14). Use zones for where to watch, where to put stops and
  where to take profit. **A touch is not an entry.** Wait for the timeframe
  below to turn.
- **Fibonacci:**
  - Anchor 0% at the wick that launched the move and 100% at the new
    extreme.
  - On a new extreme, move the 100% anchor. If the origin breaks, delete the
    fib.
  - Most first pullbacks reach 38.2% (R39), but buying that first touch
    showed no edge (R37, R38). Treat 38.2–50% as one zone, never as an exact
    line.

## 5. Scoring (the same every week; fixed before the week starts)

| Result | Meaning |
|---|---|
| **Reached** | Price traded into the zone |
| **Held** | After reaching it, price moved away by half a daily average range before a daily close through the far side |
| **Broke** | A daily close clean through the far side |
| **Never reached** | Neither |

- **Count all four, never just the hits.**
- **Scoring starts when the markup is saved.** Anything earlier is context.

---

## 6. How to label everything (TradingView)

### Zone names

- **R1, R2, R3** above price and **S1, S2, S3** below, numbered **outward from
  price** (1 = nearest). Renumber every Sunday.
  - *Why:* the name tells you where it sits relative to price today. It
    matches the weekly file, so the chart and the Friday table line up.
- **Name zones by position, not by "support" or "resistance".** A broken
  resistance becomes support (this week's S1 is the old range top). The
  number tells you where the zone is; the label says what it was built from.

### The text on each zone box

Write it as `ID · timeframe of origin · reasons · date set`.

Example: `S1 · W · range-top retest · 23.6% · set 11/09`

- *Why:* in two weeks you will not remember why you drew it. The reasons and
  the date are what let you judge whether it still matters.

### Colour by timeframe, not by role

| Timeframe of origin | Style |
|---|---|
| Monthly / weekly | darkest colour, thickest border |
| Daily | medium |
| 4-hour | light |
| Hourly | thin, dotted |

*Why:* roles flip, but the timeframe a zone came from does not. Strength
comes from the timeframe, so the colour should tell you how much weight a
zone carries at a glance.

### Swing labels

- **HH, HL, LH, LL** at confirmed swings only, on the timeframe they belong
  to.
- In TradingView, set each label's **visibility to its own timeframe range**
  (weekly labels on weekly and above, and so on), so the hourly chart is not
  buried in weekly labels.

### The last break

A short arrow or line at the level, labelled in plain words with the date.

Example: `wk close above 1.9402 · 11/06`

### The "read is wrong" line (the most important line on the chart)

- One dashed line per timeframe at the price where that timeframe's read
  flips.
- Example: `W wrong below 1.9230`
- *Why:* this is the line that decides whether you are still right. Make it
  impossible to miss.

### Fibonacci

- **One active fib per timeframe,** labelled with its anchors.
- Example: `Fib D 1.8858→1.9529`
- Delete it the day it goes stale (§4).

### When a zone breaks mid-week

- **Do not delete it.** Restyle it grey, add `broke 11/12`, and delete it on
  Sunday.
- *Why:* the Friday review needs to see it, or the scoring quietly forgets
  your misses.

### Screenshots

Name them `GBPAUD_W46_start.png` and `GBPAUD_W46_end.png`, one per pair, on
the weekly and daily charts.
