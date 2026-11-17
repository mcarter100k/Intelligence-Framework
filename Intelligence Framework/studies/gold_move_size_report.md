# How far gold moves, in percent of price (gold plan C1)

**Spec:** `docs/specs/gold_move_size_study_spec.md` (commit 4e0957f, frozen
before the runner). **Runner:** `studies/gold_move_size_study.py` (commit
d0151a1). **Run:** once, 2026-11-16 19:35 PST, through
`scripts/reality_run.py --no-env`; project unchanged. Output verbatim in
validation_log 2026-11-16. **Finding:** R47. **Descriptive only:** no
entries, no R, no costs.

## The answer in plain words

1. **A typical gold day moves about 1.4–1.6% of its price.** The median
   day's range (high to low, including any gap from the previous close) was
   **1.61%** in 2006–2013 and **1.35%** in 2021–2026. The 14-day average
   range (ATR, the markup tool's "daily average range") had a median of
   **1.69%** and **1.38%**.
2. **In percent, gold was a little calmer in 2021–2026 than in 2006–2013**
   (the typical day was 0.84 times as big), even though its moves in dollars
   were bigger ($29.81 against $17.83 a day), because gold cost about $2,030
   instead of $1,120. The middle halves overlap (1.13–2.32% and 0.98–1.88%),
   so by the spec's rule the eras do not clearly differ.
3. **A 4-hour bar is about a third of a day, and an hour about a sixth.** The
   median 4-hour range was 0.34 (2006–13) and 0.36 (2021–26) of the median
   day; the hour 0.16 and 0.17. The same in both eras.
4. **2026 is gold's wildest year in either era.** Its median day moved
   **2.26%** and its median ATR was **2.61%** (through 2026-09-08), more than
   2008, the crisis year (2.51% and 2.47%). The quietest years were 2021 and
   2023, at about 1.1%.

| | 2006–2013 | 2021–2026 |
|---|---|---|
| Typical day (median range) | 1.61% | 1.35% |
| Quiet day / busy day (p10 / p90) | 0.84% / 3.23% | 0.77% / 2.58% |
| 14-day average range (median ATR) | 1.69% | 1.38% |
| Typical 4-hour bar | 0.55% | 0.48% |
| Typical hour | 0.25% | 0.23% |
| Median gold price | $1,123 | $2,029 |

## What it means for the markup

- **Keep the markup's thresholds in "daily ranges", not dollars.** Zones no
  wider than half a day's average range, "held" = half a day away, stops of
  0.3–1.5 daily ranges: those rules resize themselves as gold's price and
  mood change. A fixed dollar figure doesn't. $45 was 7.5% of gold at $600 and
  is about 1.2% at $3,860.
- **Right now gold is unusually busy.** On 2026-11-16 at 4:06 PM PST the
  markup tool's daily average range was $87.05 at a price of $3,859.58:
  **2.26% of price**. That is 1.63 times the 2021–2026 median (1.38%) and
  close to 2026's own median (2.61%). So today's "half a day" ($43.52) is a
  wide zone by gold's long-run standards. If gold calms down to its 2021–2026
  normal, half a day at today's price would be about $27.
- **To compare moves across eras, use percent.** A $100 day was a disaster at
  $600 gold and an ordinary day at $4,000.

## Limits

- **Bars are not independent.** Busy days cluster, so no confidence interval
  is given; the medians and ranges are descriptions.
- **Ranges include gaps**, weekend gaps included (C6 will measure those on
  their own).
- **2026 stops at 2026-09-08** (the USED span's end); the FORWARD span was not
  used. Today's figure comes from the live markup tool, not from this study.
- **Nothing here is an edge.** It only replaces borrowed or one-week dollar
  figures with gold's own, era-comparable sizes.
