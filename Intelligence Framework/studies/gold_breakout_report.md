# Gold breakout study (C2): do gold's breaks of a daily swing hold?

**Spec:** `docs/specs/gold_breakout_study_spec.md`, frozen at 23:17:42 PST on
2026-11-14 (commit c523494, rebased as 12be852), before the runner existed.
- Runner and tests committed at 23:22:54 PST (1be3e23, rebased as 7c3e5e4).
- First computation 23:23:02 PST. Run once through `reality_run.py --no-env`:
  exit 0, stderr empty, project unchanged by hash.
- Output verbatim: validation_log, 2026-11-14 entry "GOLD BREAKOUT STUDY (C2)".

**What it is:** descriptive only. No entries, no R, no costs, and no claim
that anything pays. The study data (2006–2013) and the used data (2021–2026)
are learning data, not proof. The 2014–2021 data was not read.

**Gold is not tradeable on the OANDA account.** This is for the weekly markup.

---

## The question in plain words

On the daily chart, take the most recent confirmed swing high or low (the
markup's rule: 3 candles each side). When price trades past it, how often is
it back on the other side within a few days?

Two ways of counting a break:

| Name | A break is… | It failed if… |
|---|---|---|
| **Wick break** (the GBP/AUD R24 definition) | a day's high or low trades past the level, even by a wick | any close that day or on the next two days is back inside |
| **Close break** (the markup's "last break") | a day **closes** past the level | any close on the next three days is back inside |

GBP/AUD was measured with the same code, as the benchmark.

## What we found

Today's daily average range is about **$90**, so 0.25 of a day ≈ $22,
0.5 ≈ $45, 1 ≈ $90, 2 ≈ $180.

### 1. A wick through a level is not a break

| Wick breaks: share back inside within 3 days | 2006–2013 | 2021–2026 |
|---|---|---|
| Gold, both directions | 51% (N 175): about even | **66% (N 116): most fail** |
| Gold, upward | 45% (N 98) | 59% (N 68) |
| Gold, downward | 60% (N 77) | **77% (N 48): most fail** |
| GBP/AUD, both directions | 72% (N 217): most fail | 69% (N 124): most fail |

- In 2021–2026, **two out of three** wicks through a gold swing level were back
  inside within three days. That is close to GBP/AUD's rate.
- In 2006–2013, gold was a coin flip, and its upside wicks held much more often
  than GBP/AUD's (gold 21 points lower; the gap is clear).
- The answer changed between eras, so "not stable across eras" (rule 4).

### 2. A daily close beyond is better, but still a coin flip

| Close breaks: share back inside within 3 days | 2006–2013 | 2021–2026 |
|---|---|---|
| Gold, both directions | 43% (N 151): about even | 45% (N 96): about even |
| Gold, upward | **32% (N 82): most hold** | 42% (N 59) |
| Gold, downward | 57% (N 69) | 49% (N 37) |
| GBP/AUD, both directions | 53% (N 170) | 46% (N 98) |

- Waiting for a **close** past the level cut the failure rate from about
  half-to-two-thirds to about **four in ten**, in both eras.
- Even so, a close beyond is still close to even odds. It does not confirm a
  break by itself.
- Gold and GBP/AUD look the same on this measure in 2021–2026.

### 3. How far past the level the close finished

Held share of close breaks, by how far beyond the level the breakout day
closed (known at that close):

| Close beyond the level | 2006–2013 | 2021–2026 |
|---|---|---|
| less than 0.25 day (< ≈ $22 now) | 35% held (N 51) | 52% held (N 31) |
| 0.25–0.5 day (≈ $22–45) | 62% held (N 37) | 44% held (N 32) |
| 0.5–1 day (≈ $45–90) | 65% held (N 49) | 61% held (N 23) |
| a full day or more (> ≈ $90) | 93% held (N 14): **too few** | 90% held (N 10): **too few** |

- In 2006–2013, closes that barely cleared the level held only about a third of
  the time; closes half a day or more beyond held about two thirds of the time.
- In 2021–2026 the middle bucket breaks that pattern. Treat "further is safer"
  as a lean, not a rule.
- The big closes (a full day or more) held 9 times in 10, but there are only 24
  of them across both eras.

### 4. Breaks that held ran far; breaks that failed did not

How far price went past the level in the five days from the break
(wick breaks):

| | 2006–2013 | 2021–2026 |
|---|---|---|
| Failed breaks, middle value | 0.70 of a day (≈ $63) | 0.78 (≈ $70) |
| Held breaks, middle value | 1.78 of a day (≈ $160) | 2.26 (≈ $203) |

This is known only afterwards, so it is not a signal. It says what a real break
of a gold daily swing has usually looked like: about two days' range, while a
fake has typically run less than one.

## What this means for your markup

1. **A wick through a level is not "the last break".** Only a daily close
   counts. This is already the playbook's rule; on gold it now has numbers
   behind it.
2. **After a close beyond, expect about 4 in 10 to come back inside within 3
   days.** Don't move a zone, or flip a floor to a ceiling, on one close.
   Wait for it to hold.
3. **A barely-there close (under ≈ $22 beyond) is the weakest kind.** Closes
   half a day or more beyond held more often in the older data. That is a lean,
   not a rule.
4. **Direction mattered in both eras, in different ways.** Upside breaks held
   more in 2006–2013, and downside wicks failed most in 2021–2026, both of
   them big rising markets. A possible reading is that breaks against the big
   trend fail more often. **That is a hypothesis, not tested here.** With
   gold's monthly chart now turned down, it is a reason for caution, not a
   rule.

## What it does not say

- **Nothing here is a trade.** A 66% failure rate does not mean fading wicks
  pays. Fading levels (R14) and confirming breaks (R43, R44) were all refuted on
  GBP/AUD once costs and stops were counted.
- **Not independent.** Breaks a few days apart are related, so the intervals are
  a little too narrow.
- **Two rising markets dominate the data.** Gold fell in 2011–2013 and in
  parts of 2022, but most of both eras was a climb. Today's market may not
  behave like either.

## Numbers behind the readings (the frozen rules)

- A cell under 20 graded events is INSUFFICIENT and is not read.
- "Most fail" / "most hold" needs the whole 95% interval above / below 50%.
- Gold vs GBP/AUD, or up vs down, "differs" only if the interval of the
  difference excludes zero:
  - Wick, 2006–2013: gold vs GBP/AUD −20.9 points [−30.1, −11.3] differs (upward −29.8 [−41.9, −16.2] differs).
  - Wick, 2021–2026: gold vs GBP/AUD −2.2 [−13.9, +9.6] no clear difference; gold up vs down −18.3 [−33.5, −0.8] differs.
  - Close, 2006–2013: gold up vs down −24.8 [−39.1, −8.9] differs; gold vs GBP/AUD upward −19.6 [−33.8, −4.2] differs.
  - Close, 2021–2026: every comparison "no clear difference".
- GBP/AUD wick breaks in 2021–2026, 69% failed, sit beside R24's 71%
  (2023–2026, a different swing detector). As expected, this was context, not
  a control.
