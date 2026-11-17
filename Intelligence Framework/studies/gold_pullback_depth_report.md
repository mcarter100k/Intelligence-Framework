# How deep gold's first pullback goes (gold plan C3)

**Spec:** `docs/specs/gold_pullback_depth_study_spec.md` (commit 4e0957f,
frozen before the runner). **Runner:** `studies/gold_pullback_depth_study.py`
(commit d0151a1). **Run:** once, 2026-11-16 19:35 PST, through
`scripts/reality_run.py --no-env`; project unchanged. Output verbatim in
validation_log 2026-11-16. **Finding:** R48. **Descriptive only:** no
entries, no R, no costs.

## What was measured

A "big move" is R39's definition, run by its own unchanged code: on the 4-hour
chart, a move of at least **2 daily ranges** away from a **new 20-day low**
(a rally) or **new 20-day high** (a fall). For each one, did the first
pullback come back to 23.6%, 38.2%, 50%, 61.8%, 78.6% or all the way (100%)
of the move within about 10 sessions?

Legs: 2006–2013, 45 rallies and 57 falls; 2021–2026, 32 rallies and 44 falls.

## The answer in plain words

| First pullback reached | Rallies 2006–13 | Rallies 2021–26 | Falls 2006–13 | Falls 2021–26 |
|---|---|---|---|---|
| 23.6% | 93.3% | 100% | 100% | 100% |
| **38.2%** | **71.1%** | **78.1%** | **89.5%** | **81.8%** |
| **50%** | **62.2%** | **59.4%** | **75.4%** | **68.2%** |
| 61.8% | 55.6% | 43.8% | 59.6% | 50.0% |
| 78.6% | 28.9% | 28.1% | 42.1% | 34.1% |
| 100% (whole move given back) | 20.0% | 18.8% | 24.6% | 25.0% |

1. **23.6% is too shallow to matter.** Nearly every first pullback went past
   it (93–100%).
2. **38.2% is reached by most first pullbacks**, in rallies and falls, in both
   eras (the spec's "most reach it" in all four cells).
3. **50% is about even in rallies** (62% and 59%) **but reached by most bounces
   in falls** (75% and 68%). Pooled, 69.6% and 64.5%.
4. **61.8% is a coin flip** (44–60%), and 78.6% is reached by only about a
   third.
5. **About 1 big move in 5 was entirely given back** within 10 sessions
   (19–25%).
6. **The same in both eras.** Every reading at 23.6–61.8% matched between
   2006–2013 and 2021–2026.
7. **Gold is about like the GBP pairs.** Pooled, 38.2% was reached 81.4% / 80.3%
   of the time (GBP/AUD 81.0%, GBP/JPY 89.6% in R39) and 50% 69.6% / 64.5%
   (66.1% and 74.1%). Context only; not a test.

**Do falls bounce deeper than rallies pull back?** Falls reached every depth
more often than rallies in both eras (one tie, at 23.6% in 2021–2026), but
only one of 12 comparisons was clear: in 2006–2013, 89.5% of fall bounces reached 38.2% against 71.1% of rally pullbacks
(−18 points, interval −34 to −3). In 2021–2026 the same comparison was −4
points, not clear. With 12 comparisons, one clear result could be chance.
**It's a hint worth watching, not a fact.**

**An example from the data:** the most recent fall in the 2021–2026 data
started from the $4,697.11 high (the 4-hour bar opening Aug 24, 2026, 2 PM PT;
the weekly chart's August peak). It fell to $4,282.63, a drop of $414.48, or
3.8 daily ranges. The bounce reached the 38.2% level ($4,440.96) in the 4-hour
bar opening **Sep 2, 10 PM PT**. Checked by hand from the raw 4-hour prices:
no earlier bar reached its level.

## What it means for the markup

- **Expect the first pullback to reach at least 38.2%.** A zone at 23.6% will
  usually be run through.
- **Don't treat 50% or 61.8% as a floor.** Each is about even.
- **A stop at 61.8% gets reached by the first pullback alone about half the
  time; just past the move's origin, about 1 time in 5.** That says where a
  stop is *not* safe from ordinary pullbacks. It doesn't say where a trade
  pays.
- **Reaching a level is not holding it.** Buying the first touch of 38.2% or
  50% showed no edge on the GBP pairs (R37, R38); it is untested on gold. This
  study measures depth, not entries.

## Limits

- **Legs overlap and are few:** 32–57 per cell. A rally leg and a fall leg can
  run at the same time, so the intervals are approximate and somewhat too
  narrow.
- **Shares are lower bounds for "eventually":** a move that qualified late in
  its 10-session window had less time to pull back.
- **One definition of a big move** (R39's). Hand-drawn weekly or daily fibs
  use different anchors and may behave differently.
- **2006–2013 and 2021–2026 were mostly rising markets** for gold, yet falls
  still gave enough legs in each era (57 and 44) for a reading.
