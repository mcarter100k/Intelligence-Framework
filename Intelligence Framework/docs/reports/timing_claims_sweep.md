# Timing claims sweep: every time-of-day and session claim against chance

**Date:** 2026-11-16. **Requested by:** the owner's remediation brief, Part 2.2.
**Script:** `studies/timing_claims_sweep.py`, run once through
`scripts/reality_run.py --no-env` (exit 0, stderr empty, project files
unchanged by hash). Its full output is in the remediation report's appendix.
**Nothing here deletes a finding.** Claims within two standard errors of
chance are labelled **UNINFORMATIVE** (owner ruling R2, 2026-11-16: correctly
measured, but within 2 SE of what chance alone produces, so it supports no
inference).

## Method

- **Observed figures** are recomputed with the session study's own code on the
  same hash-pinned files: GBP/AUD and GBP/JPY 2005–2013 (STUDY), gold 2021-04-27
  → 2026-09-09 (USED, gold's daily break removed as in the gold session study).
  Every recomputed figure equals the published one (checks in the table).
- **Two chance baselines** for each claim, both a driftless random walk:
  - **uniform:** equal variance in every trading hour (the arcsine-law setting);
  - **vol-shaped:** each UTC hour's variance set to that hour's observed
    Parkinson variance, so busy hours stay busy. This is the fair comparator
    for claims about when extremes form.
  - Each simulated day reuses an observed day's exact hours (20 steps an hour,
    5 simulated days per observed day, seed 7) and is scored by the same code.
- **Standard error:** binomial for shares of days, bootstrap for medians,
  sd/√n for hourly means. Days are treated as independent.
- **Flag:** "within 2 SE of chance" if |observed − vol-shaped| < 2 SE.

## Results

### Gold (XAU/USD), 2021–2026, 1,325 complete days (`studies/gold_session_report.md`)

| Claim | Observed | Uniform | Vol-shaped | Diff (SE) | Flag |
|---|---|---|---|---|---|
| Busiest hours 12:00–15:00 UTC (4–7 AM PST) | $13.45/h vs $7.78/h for other hours | equal hours | — | +27.8 SE* | beyond chance |
| Busiest hour moves 2.84× the quietest | 2.84 (13:00 vs 21:00 UTC) | 1.00 | — | busiest hour +17.6 SE above the all-hours mean | beyond chance |
| London/NY block (4–8 AM PST) covers a median 67% of the day's range | 0.669 | 0.402 | 0.589 | +10.6 | beyond chance |
| The day's high forms in that block on 32% of days | 32.0% | 11.9% | 22.1% | +7.7 | beyond chance |
| The day's low forms in that block on 30% of days | 30.3% | 12.4% | 24.1% | +5.0 | beyond chance |
| **By 7 AM PST the high is already set on 67% of days** | **67.0%** | 65.7% (analytic arcsine 17/23: 65.87%) | **66.2%** | **+0.6** | **UNINFORMATIVE** (within 2 SE) |
| By 7 AM PST the low is already set on 73% of days | 73.1% | 65.3% | 65.9% | +6.0 | beyond chance |

*Hours within a day are not independent, so this SE is optimistic; the gap is
large enough that the reading does not change.

Further gold readings from the same run (not headline claims in the report,
listed for completeness): high set by 01:00 PST 36.0% vs 42.6% chance (−5.0 SE,
fewer than chance); high in the Sydney block 9.4% vs 16.6% (−9.1 SE); high and
low in the same block 9.5% vs 2.2% (+9.0 SE).

### GBP/AUD and GBP/JPY, 2005–2013, 2,325 / 2,327 days (`studies/session_movement_report.md`)

| Claim | Observed (AUD / JPY) | Vol-shaped (AUD / JPY) | Diff in SE (AUD / JPY) | Flag |
|---|---|---|---|---|
| Busiest hour 14:00 UTC; busiest/quietest 1.77 / 1.92 | 1.77 / 1.92 | 1.00 (no time effect) | +13.2 / +18.5 (busiest vs mean) | beyond chance |
| High set by 03:00 UTC: 34% / 30% | 34.2 / 30.3 | 29.1 / 28.0 | +5.2 / +2.4 | beyond chance |
| High set by 09:00 UTC: 51% / 48% | 50.9 / 48.2 | 44.4 / 45.5 | +6.3 / +2.6 | beyond chance |
| High set by 15:00 UTC: 72% / 72% | 71.9 / 72.4 | 66.0 / 66.9 | +6.3 / +5.9 | beyond chance |
| **Low set by 03:00 UTC: 28% / 29%** | 27.7 / 29.0 | 29.0 / 27.4 | **−1.4 / +1.7** | **UNINFORMATIVE (both)** |
| **Low set by 09:00 UTC: 44% / 49%** | 44.1 / 49.1 | 44.7 / 45.0 | **−0.6** / +4.0 | **UNINFORMATIVE (GBP/AUD)** |
| Low set by 15:00 UTC: 69% / 75% | 69.0 / 74.6 | 66.0 / 67.3 | +3.1 / +8.0 | beyond chance |
| London block median share 0.53 / 0.57 | 0.531 / 0.571 | 0.488 / 0.511 | +9.3 / +12.8 | beyond chance |
| Overlap block median share 0.52 / 0.54 | 0.522 / 0.535 | 0.484 / 0.488 | +6.8 / +7.6 | beyond chance |
| High and low in the same block 3.6% / 4.7% | 3.6 / 4.7 | 1.4 / 1.5 | +5.8 / +7.2 | beyond chance |
| Monday's day-start block holds the high 30% / 32% (16–20% other days) | 29.7 / 32.4 | 19.0 / 18.0 (all days) | +5.0 / +6.6 | beyond chance (the report already notes part is a weekend-fold artifact) |
| "Each block holds 17–25% of highs and lows" (spread almost evenly) | mixed | see output | — | **6 of 20 block cells UNINFORMATIVE** (GBP/AUD: high in London +1.1, high in London/NY +1.0, low in Sydney −1.4; GBP/JPY: high in Sydney +1.9, high in Tokyo +0.1, low in Sydney −1.0) |
| Sydney block median share (GBP/JPY 0.26), Tokyo (0.46) | 0.260 / 0.460 | 0.252 / 0.465 | +2.0 / −1.1 | **UNINFORMATIVE (GBP/JPY; output figures, not a report claim)** |

### research_findings.md and methodology.md

| Claim | Status |
|---|---|
| R19: swings cluster at the 14:00 PDT H4 slot (27.2%, against 1/6 = 16.7% by chance) | Already **ARTIFACT (REFUTED)** in research_findings (week-edge artifact; 11.1% once week-boundary bars are excluded). No further action. |
| R35/R36: US releases widen GBP days | Not a time-of-day claim; each already has its own paired baseline (same weekday, ±28 days). Out of scope. |
| methodology.md | No time-of-day or session claim found (searched for hour, session, AM, PM). |

## What the sweep calls into question (ruled 2026-11-16: UNINFORMATIVE)

1. **Gold: "by 7 AM PST the day's high is already set on 67% of days"** equals
   chance (+0.6 SE). It is a correct measurement with no information in it.
   Spec GMW-1 no longer cites it. It is not a numbered entry in
   `research_findings.md`; it appears in `studies/gold_session_report.md`, the
   capability inventory's gold section and the specs index line for the gold
   session study.
2. **GBP: "lows set by 03:00 UTC" (both pairs) and "by 09:00 UTC" (GBP/AUD)**
   are within chance.
3. **GBP: "the daily high and low are spread almost evenly across the five
   blocks"** is partly chance-shaped: 6 of the 20 block cells sit within 2 SE
   of the random-walk baseline. The report's own caution ("even prices that
   move at random tend to make a window's extremes near its start and its
   end") is confirmed and now quantified.

## Candidate question recorded (owner ruling R10, 2026-11-16; not specced, not acted on)

Gold's **low** is already set by 7 AM PST on 73.1% of days (+6.0 SE above
chance) while its **high** by 7 AM PST is indistinguishable from chance
(67.0%, +0.6 SE). That asymmetry may point at a split between gold's
overnight and daytime behaviour, worth measuring. **Scope note:** the sample is
2021-04-27 → 2026-09-09, a span in which gold mostly rose (about $1,800 to over
$4,000), not a falling year; how the asymmetry relates to gold's direction is
unexamined.

**Downgraded (owner ruling A3, 2026-11-16):** in a mostly rising span, "the low
is set early and the high late" is what upward drift produces, and the
baselines here are driftless. The question is not worth specifying until it is
tested against a drift-matched baseline. The gold plan carries it as low
priority, not as a live candidate.

## What survives

The busy-hour profiles, the London and London/NY block shares, gold's London/NY
share of the day and where its extremes form, gold's "low by 7 AM" figure, and
GBP's "high by 15:00 UTC" figures are all well beyond chance. Busy hours are
real; some "the extreme is already in" figures are what timing alone produces.

## Limits

- Days are treated as independent; volatility clusters, so SEs are somewhat
  optimistic.
- The vol-shaped baseline keeps each hour's average variance but not
  day-to-day changes in volatility or jumps at releases.
- Gold is 2021–2026 only (USED); GBP is 2005–2013 (STUDY).
