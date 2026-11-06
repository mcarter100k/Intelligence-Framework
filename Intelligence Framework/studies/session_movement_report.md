# Session movement study: when GBP/AUD and GBP/JPY move (descriptive, 2005–2013 STUDY data)

**Spec:** `docs/specs/session_movement_study_spec.md` (frozen, commit 85e5c19).
**Runner:** `studies/session_movement_study.py` (commit 2f7c68b), run once.
**Data:** `studies/session_movement_data.py` (Phase 1, commit 0a38135).
**Phase 3:** `docs/specs/asian_range_london_direction_spec.md`, PROPOSED and NOT RUN.

**What this study is, and is not:**
- It describes WHEN the two pairs move.
- It has no entry, no direction, no costs and no strategy.
- **It does not say whether day trading these pairs would make money.** That
  is the team's call, and nothing here answers it.

Times are shown in Pacific, as PST (winter) and PDT (summer), with UTC
alongside. The study's blocks and hours are fixed in UTC.

---

## 1. Ordering: spec before any statistic

| Event | Pacific | UTC |
|---|---|---|
| Phase 1 committed (data + validation; no movement statistic) | 2026-11-05 20:50:03 PST | 2026-11-06 04:50:03 |
| **Spec committed (frozen question list), 85e5c19** | **2026-11-05 20:52:58 PST** | **2026-11-06 04:52:58** |
| Runner committed, 2f7c68b (did not exist at the spec commit) | 2026-11-05 20:56:29 PST | 2026-11-06 04:56:29 |
| **First computation (runner's own timestamp, after the hash check)** | **2026-11-05 20:56:37 PST** | **2026-11-06 04:56:37** |

- The spec precedes the first computation by 3 min 39 s.
- The runner file did not exist when the spec was committed. An `ls` at
  that moment returned "No such file".

## 2. Phase 1: hourly data and its validation

**Source:** OANDA H1 mid candles, pulled through the embargo-guarded STUDY
fetch (`history_study_gate_s3.fetch`).
- That fetch refuses the SEALED EXAM block before sending and after receipt.
- The run went through `scripts/reality_run.py`: exit 0, stderr empty,
  project files unchanged by hash.
- 212 requests.
- The data is stored outside the repo in
  `~/intel_study_archives/session_movement_data/`, with sha256 values
  (spec §2).

| | GBP/AUD | GBP/JPY |
|---|---|---|
| H1 candles stored | 58,729 | 58,594 |
| Span (first → last bar open) | 2005-01-02 10:00 PST → 2013-12-30 13:00 PST | same |
| Candles inside the embargo / SEALED EXAM block | **0** | **0** |
| Off-the-hour opens | 0 | 0 |

**Validation by aggregation.** Raw H1 bars were summed into the
framework's own H4 slots (17:00, 21:00, 01:00, 05:00, 09:00 and 13:00 New
York). Each bucket was compared with the H4 bars the framework already
holds (`~/intel_study_archives/us_event_reaction_data/`, hashes verified):
the open of the first H1, the close of the last, the highest high and the
lowest low.

| | GBP/AUD | GBP/JPY |
|---|---|---|
| H4 bars compared | 15,281 | 15,191 |
| **Matching exactly on open, high, low and close** | **15,281 (100.000%)** | **15,191 (100.000%)** |
| … built from all 4 H1 bars | 14,198 of 14,198 | 14,186 of 14,186 |
| … built from 1–3 H1 bars (hours with no trading) | 1,083 of 1,083 | 1,005 of 1,005 |
| H1 buckets with no held H4 bar / held H4 bars with no H1 inside | 0 / 0 | 0 / 0 |
| Differences in pips (any field) | none (0 nonzero) | none (0 nonzero) |

**The check can fail. Positive controls:**
- **Planted defects:** a 1-pip defect was planted on the bar that sets a
  bucket's open, high, low or close, in 20 random buckets per pair (5 per
  field). All **20 of 20** were caught per pair, each at exactly that
  bucket and field, with a 1.000-pip difference.
- **Misaligned slots:** shifting the slots by one hour made 14,732 of
  15,162 (GBP/AUD) and 14,695 of 15,098 (GBP/JPY) buckets mismatch.
- **Verdict:** the H1 feed is validated by construction against the
  framework's H4.
  - **Correction, added 2026-11-05 after the run (team review):** "validated
    by construction" overstates it.
  - The check proves four values per 4-hour block: the first hourly open,
    the last hourly close, the highest hourly high and the lowest hourly low.
  - It does not prove the other hourly values, which most of Q1 is built
    from. See §6, "What the data check did not verify".
  - The figures below are unchanged.

**Gaps.** A gap is a missing hour inside the weekly market window, Sun
17:00 → Fri 17:00 New York.
- GBP/AUD: 18 runs, 227 missing hours.
- GBP/JPY: 13 runs, 231 missing hours.
- **Every gap is a Christmas or New Year holiday** (Dec 24–26, Dec 31 –
  Jan 1). The longest are 42 h (2012-12-24 11:00 PST → 12-26 05:00 PST) and
  30 h (2012-12-31 → 2013-01-01).
- Every gap, with its date and duration, is listed in
  `studies/session_movement_gaps_GBP_AUD.csv` and `…_GBP_JPY.csv`.

**Weekend rule** (approved, `study_weekend_candle_spec.md` §6, applied
unchanged):

| | GBP/AUD | GBP/JPY |
|---|---|---|
| Saturday-session H1 dropped | 731 | 691 |
| Sunday-session H1 folded into Monday's first bar | 1,921 (420 Mondays) | 1,830 (420 Mondays) |

**Complete trading days that survive.** A study day runs 21:00 → 21:00 UTC,
Monday–Friday, 2005-01-03 → 2013-12-30. It is complete when every
scheduled hour is present.

| | GBP/AUD | GBP/JPY |
|---|---|---|
| Days with any bar | 2,343 | 2,342 |
| **Complete days** | **2,325** | **2,327** |
| Incomplete (all holidays) | 18 | 15 |
| Complete per weekday | Mon 465, Tue 463, Wed 465, Thu 466, Fri 466 | Mon 466, Tue 463, Wed 466, Thu 466, Fri 466 |
| Complete per year | 255–260 | 255–260 |

**Premise notes:**
- **The cited source is for other pairs.** The instruction cited
  `instrument_probe_report.md` for "OANDA serves history from 2002-05-06".
  That date is for the USD legs at daily granularity, not these pairs.
- **These pairs are still covered.** `history_depth_report.md` §1 shows H1
  for GBP/AUD from 2004-05-31 and GBP/JPY from 2002-05-07. Both cover the
  STUDY start, so the substance held and the work went ahead.
- **The pipeline is not daily and 4-hour only.** `oanda_feed.get_hourly_bars`
  and a 2022–2026 H1 cache exist, but there was no STUDY-era H1. That is
  what was pulled.

---

## 3. What the numbers say about WHEN these pairs move (plain English)

**The day has two busy windows, the same in both pairs.**
- **The London morning:** 07:00–09:00 UTC, which is 23:00–01:00 PST or
  00:00–02:00 PDT.
- **The London/New York overlap:** 12:00–15:00 UTC, which is 04:00–07:00 PST
  or 05:00–08:00 PDT.
- **The single busiest hour** is 14:00 UTC (06:00 PST / 07:00 PDT) in both
  pairs:
  - GBP/AUD: an average hour moves 60 pips from high to low.
  - GBP/JPY: 54 pips.
- **The quietest stretches:**
  - the Asian afternoon, 02:00–04:00 UTC (18:00–20:00 PST);
  - the hours around the New York close, 20:00–22:00 UTC (12:00–14:00 PST).
- **A smaller bump** comes at the Tokyo open, 00:00 UTC (16:00 PST).
- **Prior evidence agrees.** The earlier GBP/AUD profile on 2023–2026 data
  (USED span, learning only) also peaked at 07:00 PDT, which is the same
  14:00 UTC hour.

**Concentration is real but moderate. No hour is dead.**
- The busiest hour moves about **1.8 times** (GBP/AUD) and **1.9 times**
  (GBP/JPY) as much as the quietest.
- Even the quietest hour averages 34 pips (GBP/AUD) and 28 pips (GBP/JPY).
- By the rule fixed in the spec (§6), movement is CONCENTRATED, not evenly
  spread.

**No single session owns the day.**
- **Typical block size:** on a typical day, the London block's own
  high-to-low covers about half of the whole day's range. The median share
  is 0.53 for GBP/AUD and 0.57 for GBP/JPY. The overlap block is similar,
  at 0.52 and 0.54.
- **Where the extremes form:** the daily high and low are spread almost
  evenly across the five blocks. Each block holds 17–25% of highs and of
  lows, even though the blocks run 3 to 7 hours.
- **High and low together:** they fall in the same block on only 3.6%
  (GBP/AUD) and 4.7% (GBP/JPY) of days.
- **Read the block percentages with care.** Even prices that move at random
  tend to make a window's extremes near its start and its end. So the
  Sydney block (which opens the day) and the New York afternoon (which
  closes it) are flattered by their position.
  - This study did not compute that random-walk baseline; it is not on the
    frozen list.
  - It is recorded as a hypothesis (§5 below). Until it is run, "which
    session makes the high" cannot be read as a session effect.

**By the Pacific morning, most days already have their high and low.**

| Already in place by | Highs set (GBP/AUD, GBP/JPY) | Lows set (GBP/AUD, GBP/JPY) |
|---|---|---|
| 03:00 UTC (19:00 PST the evening before) | 34%, 30% | 28%, 29% |
| 09:00 UTC (01:00 PST / 02:00 PDT) | 51%, 48% | 44%, 49% |
| 15:00 UTC (07:00 PST / 08:00 PDT) | 72%, 72% | 69%, 75% |

- On roughly 7 days in 10, someone starting at 07:00 PST is trading inside
  a range whose high is already set, and the same for its low.
- That is the structural fact behind "a late entry is chasing". It does
  not say whether chasing loses money.

**Day of week matters.**
- **Friday's London/New York overlap is the busiest window of the week in
  both pairs.**
  - Hourly averages from 12:00 to 15:00 UTC: 61–65 pips (GBP/AUD) and 53–59
    pips (GBP/JPY).
  - The overlap block's median share of Friday's range: 0.60 and 0.59,
    against 0.52 (GBP/AUD) and 0.54 (GBP/JPY) over all days.
- **Monday is different at both ends.**
  - **Day start:** the day-start (Sydney) block holds Monday's high on 30%
    (GBP/AUD) and 32% (GBP/JPY) of Mondays, against 16–20% on other days.
    By 03:00 UTC, the high is already set on 43% of Mondays, against 25–34%
    on other days.
  - **Part of this is an artifact of the old data.** Monday's first bar
    carries the pre-open weekend quoting of 2005–2013, folded in by the
    approved rule. Modern data has no such quotes.
  - **The overlap:** Monday is the quietest overlap of the week.
  - **GBP/JPY's peak hour:** on Mondays, Tuesdays and Wednesdays it is the
    London open (07:00–08:00 UTC), not the overlap.

**How the pairs differ.**
- **Pip sizes:** the pairs' pips are different sizes. Compare the shapes,
  not the pip levels.
- **The shapes are very similar.**
- **GBP/JPY leans more to the London morning:**
  - a larger London block share (median 0.57, against 0.53);
  - more daily lows made in London (22.5%, against 19.9%);
  - a slightly steeper busiest-to-quietest ratio (1.92, against 1.77).
- **GBP/AUD's daily high** forms slightly more often in the Tokyo block
  (22.4%, against 19.5%).

**Average true range by holding timeframe.** These are numbers only, with
no interpretation and no rule proposal. They are for the team's separate
stop-floor question.

| Pips | 1-hour | 4-hour | Daily |
|---|---|---|---|
| GBP/AUD | 46.2 | 89.5 | 216.5 |
| GBP/JPY | 39.8 | 79.7 | 200.6 |

- These are 2005–2013 levels, an era that includes the 2008 crisis. They
  are not today's levels.
- For comparison, the USED-span GBP/AUD profile reports a median daily
  range measure of 110–134 pips for 2023–2026 (learning only).
- The weekday splits are within a few percent of each other (full table
  below).

## 4. Reading rules fixed in the spec

- **DST boundary steps (§5): none met the rule.** Every step at a block
  boundary lies between 0.81 and 1.24. None is sharp (≥ 1.5 or ≤ 0.667),
  so the rule does not call for a DST-aware re-run.
- **Observed: the steepest rise is inside a block.** It comes at 06:00 UTC
  (from 37 to 46 pips for GBP/AUD, and from 33 to 42 for GBP/JPY), which is
  inside the TOKYO block. That block's last hour therefore already behaves
  like a European morning.
- **Phase 3 gate (§6): CONCENTRATED.** The Asian-range breakout question is
  not moot. Whether to run it is the team's decision.

## 5. Hypotheses recorded, NOT computed

Each of these would need its own pre-registered run.

1. **Random-walk baseline for Q3/Q4:** do the daily extremes form at the
   day's start and end more or less often than random price paths of the
   same length and the same hourly activity would give? Without it, block
   percentages are not session effects.
2. **Friday overlap and US releases:** is the Friday overlap concentration
   driven by US data releases (for example payrolls)? This needs an event-day
   split using `us_events_2005_2013.csv`.
3. **The Monday day-start block:** is its prominence the folded weekend
   quoting? Test on modern-convention data, or with fold Mondays excluded.
4. **DST-aware blocks:** do blocks anchored to London and New York local
   time sharpen the London-open and New York-open peaks, given the 06:00 UTC
   rise inside TOKYO?
5. **Era stability:** does the 2005–2013 hourly shape hold in modern data?
   The one prior USED-span GBP/AUD profile agrees on the peak hour, but USED
   data is learning only.
6. **GBP/JPY early-week peak:** is its early-week London-open peak (against a
   late-week overlap peak) stable, or noise across about 465 days per weekday?

## 6. Limits

- **2005–2013 only.** The era includes the financial crisis and zero rates.
- **Mid prices; no spread.**
- **Fixed UTC blocks smear by one hour** across the London and New York
  boundaries twice a year (§4: no sharp boundary step).
- **The study day is not the framework's day in winter.** The study day is
  21:00 → 21:00 UTC; the framework's day starts at 17:00 New York.
- **Monday figures carry the folded weekend quoting.** Q1 excludes the 420
  fold bars; Q2–Q4 keep them, per the approved rule.
- **Descriptive figures carry no VALIDATED label.**
- **N:** every weekday cell holds 463–466 complete days, and every hourly
  cell at least 34 bars. The smallest is Monday 21:00 UTC, because winter
  Mondays open at 22:00 UTC. No cell is below N = 20.
- **What the data check did not verify** (added 2026-11-05, team review; the
  figures are unchanged and the study was not re-run).
  - **What was compared.** The Phase 1 check compared each 4-hour block
    built from hourly bars with the 4-hour bar OANDA serves. It proves four
    values per block:
    - the first hour's open;
    - the last hour's close;
    - the single highest hourly high;
    - the single lowest hourly low.
  - **What it leaves unchecked:**
    - **Other hourly highs.** Every other hourly high in the block is only
      proven to be at or below the block's high. It could be wrong by any
      amount under that ceiling and the check would still pass.
    - **Other hourly lows.** The same holds for lows, above the block's low.
    - **Intermediate opens and closes.** These are not checked at all.
  - **Why it matters here.** Q1 measures each hour's high minus its low. So
    it is built almost entirely from values the check did not prove. If an
    hour's high were too low and its low too high, its range would be wrong
    and the check would still match exactly.
  - **The same limit, elsewhere in the study:**
    - **Q3 and Q4:** the day's high and low values are proven, but only to
      the 4-hour block they sit in. Which hour inside that block made them
      rests on the unproven hourly values.
    - **Q2:** it uses session blocks that do not line up with the 4-hour
      blocks, so it too depends partly on unproven hourly values.
    - **Q5:** the 4-hour and daily figures rest on bars that were checked;
      the hourly figure does not.
  - **Both series come from one source.** Both sides of the check are
    OANDA data. An error present in OANDA's own records would pass.
  - **The right word is "consistent", not "verified".** The hourly data is
    probably fine, but "probably fine" is not "verified". This report's
    hourly figures are **consistent with the verified 4-hour data**, not
    verified bar by bar.
  - **What would close the gap:** a second, independent data source for the
    same 2005–2013 span, compared hour by hour. None has been sourced.

---

## 7. Full output of the single run (verbatim stdout)

`scripts/reality_run.py --no-env --code <worktree> script <worktree>/studies/session_movement_study.py ~/intel_study_archives/session_movement_data ~/intel_study_archives/us_event_reaction_data`

Result: exit 0, stderr 0 bytes, `project files : UNCHANGED (verified by hash)`.

```
run start (UTC): 2026-11-06T04:56:37+00:00
hash GBP_AUD_H1.csv: OK
hash GBP_JPY_H1.csv: OK
hash GBP_AUD_H4.csv: OK
hash GBP_AUD_D.csv: OK
hash GBP_JPY_H4.csv: OK
hash GBP_JPY_D.csv: OK
first computation start (UTC): 2026-11-06T04:56:37+00:00


## GBP_AUD

Study days with bars 2343; complete 2325; fold bars excluded from Q1 420

### Q1. Hourly range profile

**Q1 GBP_AUD, all weekdays** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 1901 | 37.8 | 29.5 |
| 22:00 | 14:00 PST / 15:00 PDT | 2184 | 38.4 | 29.8 |
| 23:00 | 15:00 PST / 16:00 PDT | 2337 | 39.2 | 31.0 |
| 00:00 | 16:00 PST / 17:00 PDT | 2337 | 46.7 | 36.3 |
| 01:00 | 17:00 PST / 18:00 PDT | 2338 | 46.3 | 35.9 |
| 02:00 | 18:00 PST / 19:00 PDT | 2338 | 35.2 | 29.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 2338 | 35.5 | 27.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 2338 | 34.1 | 26.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 2338 | 37.4 | 29.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 2338 | 46.3 | 39.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 2338 | 53.0 | 44.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 2338 | 55.5 | 45.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 2334 | 54.0 | 44.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 2335 | 49.3 | 40.2 |
| 11:00 | 03:00 PST / 04:00 PDT | 2334 | 48.1 | 38.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 2334 | 54.7 | 43.1 |
| 13:00 | 05:00 PST / 06:00 PDT | 2335 | 56.0 | 45.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 2336 | 60.2 | 48.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 2337 | 57.5 | 45.9 |
| 16:00 | 08:00 PST / 09:00 PDT | 2336 | 48.3 | 37.8 |
| 17:00 | 09:00 PST / 10:00 PDT | 2336 | 42.4 | 33.0 |
| 18:00 | 10:00 PST / 11:00 PDT | 2336 | 42.7 | 33.0 |
| 19:00 | 11:00 PST / 12:00 PDT | 2335 | 42.0 | 30.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 2336 | 38.6 | 29.0 |

**Q1 GBP_AUD, Mon** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 34 | 31.4 | 27.3 |
| 22:00 | 14:00 PST / 15:00 PDT | 313 | 41.6 | 33.8 |
| 23:00 | 15:00 PST / 16:00 PDT | 469 | 42.1 | 34.0 |
| 00:00 | 16:00 PST / 17:00 PDT | 469 | 47.1 | 36.8 |
| 01:00 | 17:00 PST / 18:00 PDT | 469 | 43.8 | 34.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 469 | 34.5 | 28.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 469 | 33.9 | 26.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 469 | 31.9 | 25.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 469 | 36.1 | 29.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 469 | 45.0 | 38.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 469 | 51.7 | 44.3 |
| 08:00 | 00:00 PST / 01:00 PDT | 469 | 50.8 | 41.9 |
| 09:00 | 01:00 PST / 02:00 PDT | 468 | 47.7 | 40.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 469 | 44.5 | 36.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 468 | 43.7 | 34.8 |
| 12:00 | 04:00 PST / 05:00 PDT | 468 | 47.0 | 37.6 |
| 13:00 | 05:00 PST / 06:00 PDT | 468 | 48.8 | 39.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 469 | 55.2 | 42.2 |
| 15:00 | 07:00 PST / 08:00 PDT | 469 | 53.1 | 41.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 469 | 44.6 | 34.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 469 | 40.2 | 30.6 |
| 18:00 | 10:00 PST / 11:00 PDT | 467 | 37.6 | 29.2 |
| 19:00 | 11:00 PST / 12:00 PDT | 467 | 37.9 | 26.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 467 | 34.0 | 25.7 |

**Q1 GBP_AUD, Tue** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 466 | 34.9 | 27.0 |
| 22:00 | 14:00 PST / 15:00 PDT | 467 | 36.5 | 27.5 |
| 23:00 | 15:00 PST / 16:00 PDT | 466 | 36.2 | 29.1 |
| 00:00 | 16:00 PST / 17:00 PDT | 466 | 44.2 | 35.0 |
| 01:00 | 17:00 PST / 18:00 PDT | 466 | 44.5 | 35.1 |
| 02:00 | 18:00 PST / 19:00 PDT | 466 | 34.3 | 29.8 |
| 03:00 | 19:00 PST / 20:00 PDT | 466 | 39.5 | 28.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 466 | 38.9 | 27.2 |
| 05:00 | 21:00 PST / 22:00 PDT | 466 | 37.8 | 29.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 466 | 45.4 | 38.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 466 | 53.3 | 45.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 466 | 57.4 | 47.8 |
| 09:00 | 01:00 PST / 02:00 PDT | 465 | 55.9 | 47.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 465 | 49.1 | 40.9 |
| 11:00 | 03:00 PST / 04:00 PDT | 465 | 47.4 | 38.4 |
| 12:00 | 04:00 PST / 05:00 PDT | 465 | 49.9 | 41.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 465 | 54.4 | 44.5 |
| 14:00 | 06:00 PST / 07:00 PDT | 465 | 58.8 | 47.6 |
| 15:00 | 07:00 PST / 08:00 PDT | 465 | 55.6 | 44.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 465 | 47.9 | 37.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 465 | 40.0 | 32.7 |
| 18:00 | 10:00 PST / 11:00 PDT | 466 | 42.6 | 32.7 |
| 19:00 | 11:00 PST / 12:00 PDT | 465 | 44.0 | 32.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 466 | 38.0 | 28.4 |

**Q1 GBP_AUD, Wed** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 465 | 37.1 | 29.1 |
| 22:00 | 14:00 PST / 15:00 PDT | 466 | 37.3 | 28.7 |
| 23:00 | 15:00 PST / 16:00 PDT | 466 | 39.9 | 31.0 |
| 00:00 | 16:00 PST / 17:00 PDT | 466 | 47.2 | 36.2 |
| 01:00 | 17:00 PST / 18:00 PDT | 467 | 46.7 | 37.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 467 | 34.2 | 29.5 |
| 03:00 | 19:00 PST / 20:00 PDT | 467 | 33.8 | 27.4 |
| 04:00 | 20:00 PST / 21:00 PDT | 467 | 33.0 | 27.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 467 | 38.2 | 31.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 467 | 47.3 | 40.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 467 | 53.2 | 44.2 |
| 08:00 | 00:00 PST / 01:00 PDT | 467 | 58.3 | 48.0 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 57.7 | 45.3 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 53.1 | 41.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 49.0 | 40.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 55.1 | 43.1 |
| 13:00 | 05:00 PST / 06:00 PDT | 468 | 56.1 | 45.2 |
| 14:00 | 06:00 PST / 07:00 PDT | 468 | 59.3 | 47.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 468 | 58.9 | 47.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 468 | 49.1 | 37.1 |
| 17:00 | 09:00 PST / 10:00 PDT | 468 | 43.9 | 33.3 |
| 18:00 | 10:00 PST / 11:00 PDT | 468 | 47.7 | 35.1 |
| 19:00 | 11:00 PST / 12:00 PDT | 468 | 45.4 | 33.9 |
| 20:00 | 12:00 PST / 13:00 PDT | 468 | 41.0 | 29.9 |

**Q1 GBP_AUD, Thu** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 468 | 40.9 | 32.3 |
| 22:00 | 14:00 PST / 15:00 PDT | 469 | 38.7 | 30.1 |
| 23:00 | 15:00 PST / 16:00 PDT | 468 | 38.2 | 29.8 |
| 00:00 | 16:00 PST / 17:00 PDT | 468 | 50.4 | 39.4 |
| 01:00 | 17:00 PST / 18:00 PDT | 468 | 53.0 | 37.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 468 | 37.9 | 31.1 |
| 03:00 | 19:00 PST / 20:00 PDT | 468 | 35.2 | 27.7 |
| 04:00 | 20:00 PST / 21:00 PDT | 468 | 32.3 | 25.6 |
| 05:00 | 21:00 PST / 22:00 PDT | 468 | 37.1 | 29.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 468 | 46.0 | 39.3 |
| 07:00 | 23:00 PST / 00:00 PDT | 468 | 53.6 | 43.8 |
| 08:00 | 00:00 PST / 01:00 PDT | 468 | 57.4 | 47.3 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 55.4 | 46.4 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 50.4 | 43.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 52.3 | 40.4 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 58.5 | 45.3 |
| 13:00 | 05:00 PST / 06:00 PDT | 467 | 56.7 | 46.6 |
| 14:00 | 06:00 PST / 07:00 PDT | 467 | 62.4 | 52.0 |
| 15:00 | 07:00 PST / 08:00 PDT | 467 | 58.7 | 49.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 467 | 49.7 | 40.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 467 | 44.0 | 34.5 |
| 18:00 | 10:00 PST / 11:00 PDT | 468 | 43.5 | 33.2 |
| 19:00 | 11:00 PST / 12:00 PDT | 468 | 42.1 | 30.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 468 | 37.8 | 28.0 |

**Q1 GBP_AUD, Fri** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 468 | 38.7 | 30.5 |
| 22:00 | 14:00 PST / 15:00 PDT | 469 | 39.0 | 29.6 |
| 23:00 | 15:00 PST / 16:00 PDT | 468 | 39.8 | 30.0 |
| 00:00 | 16:00 PST / 17:00 PDT | 468 | 44.5 | 34.8 |
| 01:00 | 17:00 PST / 18:00 PDT | 468 | 43.4 | 33.2 |
| 02:00 | 18:00 PST / 19:00 PDT | 468 | 34.9 | 28.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 468 | 35.2 | 25.7 |
| 04:00 | 20:00 PST / 21:00 PDT | 468 | 34.4 | 25.6 |
| 05:00 | 21:00 PST / 22:00 PDT | 468 | 37.8 | 29.1 |
| 06:00 | 22:00 PST / 23:00 PDT | 468 | 47.9 | 40.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 468 | 53.4 | 44.8 |
| 08:00 | 00:00 PST / 01:00 PDT | 468 | 53.8 | 42.9 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 53.3 | 41.1 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 49.3 | 41.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 48.3 | 40.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 63.0 | 48.6 |
| 13:00 | 05:00 PST / 06:00 PDT | 467 | 64.0 | 52.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 467 | 65.3 | 53.0 |
| 15:00 | 07:00 PST / 08:00 PDT | 468 | 61.2 | 49.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 467 | 50.3 | 39.4 |
| 17:00 | 09:00 PST / 10:00 PDT | 467 | 43.7 | 32.8 |
| 18:00 | 10:00 PST / 11:00 PDT | 467 | 41.8 | 33.1 |
| 19:00 | 11:00 PST / 12:00 PDT | 467 | 40.5 | 30.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 467 | 42.1 | 33.0 |

### Q2. Share of daily range by block

Days with zero range excluded: 0. Winter Mondays' SYDNEY block holds 2 bars, not 3.

**Q2 GBP_AUD, all weekdays**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 2325 | 0.332 | 0.157 | 0.210 | 0.297 | 0.413 | 0.562 |
| TOKYO | 2325 | 0.509 | 0.284 | 0.368 | 0.483 | 0.630 | 0.775 |
| LONDON | 2325 | 0.549 | 0.326 | 0.413 | 0.531 | 0.669 | 0.798 |
| LDN_NY | 2325 | 0.537 | 0.308 | 0.405 | 0.522 | 0.655 | 0.787 |
| NY_PM | 2325 | 0.423 | 0.232 | 0.303 | 0.394 | 0.520 | 0.643 |

**Q2 GBP_AUD, Mon**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 465 | 0.457 | 0.240 | 0.323 | 0.432 | 0.568 | 0.702 |
| TOKYO | 465 | 0.507 | 0.292 | 0.377 | 0.484 | 0.612 | 0.755 |
| LONDON | 465 | 0.526 | 0.326 | 0.402 | 0.511 | 0.643 | 0.752 |
| LDN_NY | 465 | 0.502 | 0.283 | 0.361 | 0.489 | 0.614 | 0.742 |
| NY_PM | 465 | 0.402 | 0.231 | 0.291 | 0.378 | 0.480 | 0.601 |

**Q2 GBP_AUD, Tue**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 463 | 0.291 | 0.148 | 0.193 | 0.264 | 0.364 | 0.468 |
| TOKYO | 463 | 0.537 | 0.312 | 0.394 | 0.518 | 0.671 | 0.794 |
| LONDON | 463 | 0.571 | 0.345 | 0.431 | 0.560 | 0.693 | 0.835 |
| LDN_NY | 463 | 0.519 | 0.301 | 0.393 | 0.502 | 0.615 | 0.771 |
| NY_PM | 463 | 0.437 | 0.233 | 0.304 | 0.409 | 0.551 | 0.657 |

**Q2 GBP_AUD, Wed**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 465 | 0.299 | 0.143 | 0.193 | 0.265 | 0.367 | 0.515 |
| TOKYO | 465 | 0.490 | 0.267 | 0.343 | 0.462 | 0.612 | 0.781 |
| LONDON | 465 | 0.557 | 0.323 | 0.414 | 0.527 | 0.685 | 0.825 |
| LDN_NY | 465 | 0.517 | 0.303 | 0.390 | 0.500 | 0.631 | 0.752 |
| NY_PM | 465 | 0.427 | 0.233 | 0.294 | 0.399 | 0.544 | 0.654 |

**Q2 GBP_AUD, Thu**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.301 | 0.146 | 0.201 | 0.270 | 0.363 | 0.488 |
| TOKYO | 466 | 0.521 | 0.283 | 0.377 | 0.491 | 0.647 | 0.810 |
| LONDON | 466 | 0.557 | 0.323 | 0.413 | 0.553 | 0.685 | 0.801 |
| LDN_NY | 466 | 0.542 | 0.308 | 0.417 | 0.538 | 0.656 | 0.779 |
| NY_PM | 466 | 0.423 | 0.233 | 0.310 | 0.386 | 0.518 | 0.652 |

**Q2 GBP_AUD, Fri**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.309 | 0.159 | 0.200 | 0.277 | 0.378 | 0.513 |
| TOKYO | 466 | 0.490 | 0.274 | 0.359 | 0.478 | 0.598 | 0.733 |
| LONDON | 466 | 0.536 | 0.314 | 0.411 | 0.514 | 0.645 | 0.771 |
| LDN_NY | 466 | 0.605 | 0.372 | 0.469 | 0.598 | 0.732 | 0.859 |
| NY_PM | 466 | 0.425 | 0.241 | 0.315 | 0.403 | 0.519 | 0.631 |

### Q3. Where the daily high and low form

**Q3 GBP_AUD, all weekdays** (N days 2325)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 20.7% | 18.0% |
| TOKYO | 22.4% | 16.9% |
| LONDON | 16.7% | 19.9% |
| LDN_NY | 17.5% | 20.0% |
| NY_PM | 22.7% | 25.2% |

High and low in the same block: 3.6% of days

**Q3 GBP_AUD, Mon** (N days 465)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 29.7% | 24.5% |
| TOKYO | 21.5% | 16.3% |
| LONDON | 10.3% | 14.8% |
| LDN_NY | 16.8% | 19.8% |
| NY_PM | 21.7% | 24.5% |

High and low in the same block: 2.8% of days

**Q3 GBP_AUD, Tue** (N days 463)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 17.5% | 16.2% |
| TOKYO | 22.0% | 17.7% |
| LONDON | 20.3% | 23.5% |
| LDN_NY | 16.4% | 17.7% |
| NY_PM | 23.8% | 24.8% |

High and low in the same block: 4.5% of days

**Q3 GBP_AUD, Wed** (N days 465)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.5% | 17.0% |
| TOKYO | 24.3% | 16.6% |
| LONDON | 19.6% | 19.6% |
| LDN_NY | 15.9% | 18.9% |
| NY_PM | 21.7% | 28.0% |

High and low in the same block: 4.5% of days

**Q3 GBP_AUD, Thu** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 20.0% | 16.1% |
| TOKYO | 23.6% | 19.3% |
| LONDON | 14.2% | 21.0% |
| LDN_NY | 17.4% | 20.6% |
| NY_PM | 24.9% | 23.0% |

High and low in the same block: 2.6% of days

**Q3 GBP_AUD, Fri** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.0% | 16.1% |
| TOKYO | 20.6% | 14.6% |
| LONDON | 19.1% | 20.4% |
| LDN_NY | 20.8% | 23.0% |
| NY_PM | 21.5% | 26.0% |

High and low in the same block: 3.6% of days

### Q4. How early the extremes are set

**Q4 GBP_AUD, all weekdays** (N days 2325)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 34.2% | 27.7% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 50.9% | 44.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 71.9% | 69.0% |

**Q4 GBP_AUD, Mon** (N days 465)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 43.4% | 33.1% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 55.9% | 48.6% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 73.1% | 68.8% |

**Q4 GBP_AUD, Tue** (N days 463)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 31.1% | 26.3% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 50.3% | 44.9% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 71.7% | 70.2% |

**Q4 GBP_AUD, Wed** (N days 465)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 33.3% | 26.9% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 51.8% | 40.9% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 72.0% | 67.5% |

**Q4 GBP_AUD, Thu** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 34.3% | 27.5% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 49.8% | 44.6% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 70.2% | 70.2% |

**Q4 GBP_AUD, Fri** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 28.8% | 24.5% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 46.6% | 41.4% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 72.3% | 68.2% |

### Q5. Mean ATR(14) by timeframe (pips; numbers only)

| timeframe | all weekdays (N) | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|---|
| H1 | 46.2 (56063) | 46.7 (11230) | 44.6 (11174) | 45.8 (11214) | 47.0 (11224) | 46.9 (11221) |
| H4 | 89.5 (14016) | 90.1 (2809) | 88.6 (2790) | 88.9 (2803) | 89.6 (2807) | 90.2 (2807) |
| D1 | 216.5 (2329) | 216.0 (467) | 216.3 (464) | 216.6 (465) | 216.8 (466) | 216.5 (467) |


## GBP_JPY

Study days with bars 2342; complete 2327; fold bars excluded from Q1 420

### Q1. Hourly range profile

**Q1 GBP_JPY, all weekdays** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 1902 | 27.9 | 21.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 2184 | 29.7 | 23.5 |
| 23:00 | 15:00 PST / 16:00 PDT | 2337 | 33.3 | 26.6 |
| 00:00 | 16:00 PST / 17:00 PDT | 2337 | 41.3 | 33.2 |
| 01:00 | 17:00 PST / 18:00 PDT | 2339 | 36.5 | 29.8 |
| 02:00 | 18:00 PST / 19:00 PDT | 2338 | 30.2 | 24.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 2338 | 28.7 | 22.2 |
| 04:00 | 20:00 PST / 21:00 PDT | 2338 | 29.2 | 22.2 |
| 05:00 | 21:00 PST / 22:00 PDT | 2339 | 32.9 | 26.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 2338 | 41.8 | 34.7 |
| 07:00 | 23:00 PST / 00:00 PDT | 2338 | 50.4 | 41.9 |
| 08:00 | 00:00 PST / 01:00 PDT | 2338 | 52.7 | 44.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 2334 | 48.8 | 40.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 2334 | 43.6 | 35.8 |
| 11:00 | 03:00 PST / 04:00 PDT | 2334 | 42.0 | 33.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 2334 | 49.5 | 38.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 2335 | 50.5 | 41.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 2335 | 53.5 | 43.0 |
| 15:00 | 07:00 PST / 08:00 PDT | 2335 | 49.9 | 39.9 |
| 16:00 | 08:00 PST / 09:00 PDT | 2335 | 40.6 | 32.1 |
| 17:00 | 09:00 PST / 10:00 PDT | 2336 | 36.1 | 27.8 |
| 18:00 | 10:00 PST / 11:00 PDT | 2336 | 35.2 | 26.5 |
| 19:00 | 11:00 PST / 12:00 PDT | 2334 | 33.4 | 24.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 2335 | 29.2 | 22.6 |

**Q1 GBP_JPY, Mon** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 34 | 33.6 | 26.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 313 | 39.8 | 29.9 |
| 23:00 | 15:00 PST / 16:00 PDT | 469 | 36.9 | 30.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 469 | 44.5 | 35.1 |
| 01:00 | 17:00 PST / 18:00 PDT | 469 | 37.6 | 30.0 |
| 02:00 | 18:00 PST / 19:00 PDT | 469 | 30.7 | 23.4 |
| 03:00 | 19:00 PST / 20:00 PDT | 469 | 27.8 | 21.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 469 | 27.2 | 21.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 469 | 30.2 | 24.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 469 | 40.1 | 33.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 469 | 50.3 | 40.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 469 | 49.4 | 40.8 |
| 09:00 | 01:00 PST / 02:00 PDT | 468 | 43.7 | 36.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 468 | 40.5 | 31.9 |
| 11:00 | 03:00 PST / 04:00 PDT | 468 | 38.8 | 31.2 |
| 12:00 | 04:00 PST / 05:00 PDT | 468 | 41.6 | 34.4 |
| 13:00 | 05:00 PST / 06:00 PDT | 468 | 42.3 | 35.4 |
| 14:00 | 06:00 PST / 07:00 PDT | 468 | 49.4 | 38.5 |
| 15:00 | 07:00 PST / 08:00 PDT | 468 | 44.5 | 33.9 |
| 16:00 | 08:00 PST / 09:00 PDT | 468 | 37.1 | 30.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 468 | 31.7 | 23.9 |
| 18:00 | 10:00 PST / 11:00 PDT | 468 | 29.3 | 23.6 |
| 19:00 | 11:00 PST / 12:00 PDT | 466 | 29.9 | 22.7 |
| 20:00 | 12:00 PST / 13:00 PDT | 466 | 27.1 | 20.3 |

**Q1 GBP_JPY, Tue** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 466 | 25.8 | 20.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 467 | 27.2 | 21.6 |
| 23:00 | 15:00 PST / 16:00 PDT | 466 | 31.3 | 25.8 |
| 00:00 | 16:00 PST / 17:00 PDT | 466 | 40.7 | 32.7 |
| 01:00 | 17:00 PST / 18:00 PDT | 467 | 36.7 | 29.6 |
| 02:00 | 18:00 PST / 19:00 PDT | 466 | 31.3 | 23.6 |
| 03:00 | 19:00 PST / 20:00 PDT | 466 | 29.8 | 22.7 |
| 04:00 | 20:00 PST / 21:00 PDT | 466 | 29.4 | 22.8 |
| 05:00 | 21:00 PST / 22:00 PDT | 467 | 34.3 | 27.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 466 | 42.5 | 34.6 |
| 07:00 | 23:00 PST / 00:00 PDT | 466 | 52.1 | 43.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 466 | 53.1 | 45.9 |
| 09:00 | 01:00 PST / 02:00 PDT | 465 | 50.5 | 43.3 |
| 10:00 | 02:00 PST / 03:00 PDT | 465 | 42.4 | 36.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 465 | 40.5 | 33.4 |
| 12:00 | 04:00 PST / 05:00 PDT | 465 | 45.5 | 36.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 465 | 48.2 | 39.6 |
| 14:00 | 06:00 PST / 07:00 PDT | 465 | 52.3 | 42.8 |
| 15:00 | 07:00 PST / 08:00 PDT | 465 | 49.1 | 39.4 |
| 16:00 | 08:00 PST / 09:00 PDT | 465 | 38.1 | 31.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 466 | 34.9 | 26.6 |
| 18:00 | 10:00 PST / 11:00 PDT | 466 | 37.3 | 27.2 |
| 19:00 | 11:00 PST / 12:00 PDT | 465 | 34.0 | 24.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 466 | 28.2 | 22.0 |

**Q1 GBP_JPY, Wed** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 466 | 27.1 | 20.6 |
| 22:00 | 14:00 PST / 15:00 PDT | 466 | 28.0 | 22.3 |
| 23:00 | 15:00 PST / 16:00 PDT | 466 | 33.0 | 26.2 |
| 00:00 | 16:00 PST / 17:00 PDT | 466 | 40.3 | 32.3 |
| 01:00 | 17:00 PST / 18:00 PDT | 467 | 36.2 | 29.2 |
| 02:00 | 18:00 PST / 19:00 PDT | 467 | 29.2 | 24.1 |
| 03:00 | 19:00 PST / 20:00 PDT | 467 | 29.0 | 23.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 467 | 29.4 | 22.4 |
| 05:00 | 21:00 PST / 22:00 PDT | 467 | 34.3 | 25.6 |
| 06:00 | 22:00 PST / 23:00 PDT | 467 | 41.9 | 34.8 |
| 07:00 | 23:00 PST / 00:00 PDT | 467 | 49.9 | 42.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 467 | 55.0 | 47.0 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 52.2 | 42.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 46.5 | 37.3 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 42.7 | 33.6 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 48.1 | 38.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 468 | 49.9 | 39.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 468 | 52.0 | 42.2 |
| 15:00 | 07:00 PST / 08:00 PDT | 468 | 52.0 | 40.4 |
| 16:00 | 08:00 PST / 09:00 PDT | 468 | 41.4 | 32.4 |
| 17:00 | 09:00 PST / 10:00 PDT | 468 | 37.8 | 28.9 |
| 18:00 | 10:00 PST / 11:00 PDT | 468 | 40.3 | 29.8 |
| 19:00 | 11:00 PST / 12:00 PDT | 468 | 37.9 | 27.5 |
| 20:00 | 12:00 PST / 13:00 PDT | 468 | 30.4 | 22.5 |

**Q1 GBP_JPY, Thu** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 468 | 28.3 | 22.3 |
| 22:00 | 14:00 PST / 15:00 PDT | 469 | 28.3 | 22.8 |
| 23:00 | 15:00 PST / 16:00 PDT | 468 | 31.0 | 25.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 468 | 39.3 | 33.0 |
| 01:00 | 17:00 PST / 18:00 PDT | 468 | 36.0 | 29.6 |
| 02:00 | 18:00 PST / 19:00 PDT | 468 | 30.3 | 25.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 468 | 28.7 | 22.5 |
| 04:00 | 20:00 PST / 21:00 PDT | 468 | 28.6 | 22.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 468 | 33.1 | 26.3 |
| 06:00 | 22:00 PST / 23:00 PDT | 468 | 41.5 | 36.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 468 | 49.0 | 41.3 |
| 08:00 | 00:00 PST / 01:00 PDT | 468 | 53.5 | 45.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 49.5 | 41.5 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 44.9 | 37.4 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 45.1 | 36.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 55.1 | 44.5 |
| 13:00 | 05:00 PST / 06:00 PDT | 467 | 53.3 | 45.2 |
| 14:00 | 06:00 PST / 07:00 PDT | 467 | 55.2 | 44.5 |
| 15:00 | 07:00 PST / 08:00 PDT | 467 | 51.0 | 42.2 |
| 16:00 | 08:00 PST / 09:00 PDT | 467 | 44.4 | 34.3 |
| 17:00 | 09:00 PST / 10:00 PDT | 467 | 40.6 | 30.4 |
| 18:00 | 10:00 PST / 11:00 PDT | 467 | 37.2 | 28.4 |
| 19:00 | 11:00 PST / 12:00 PDT | 468 | 34.7 | 25.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 468 | 30.3 | 22.0 |

**Q1 GBP_JPY, Fri** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 468 | 29.9 | 23.0 |
| 22:00 | 14:00 PST / 15:00 PDT | 469 | 28.5 | 23.2 |
| 23:00 | 15:00 PST / 16:00 PDT | 468 | 34.4 | 26.3 |
| 00:00 | 16:00 PST / 17:00 PDT | 468 | 41.6 | 33.0 |
| 01:00 | 17:00 PST / 18:00 PDT | 468 | 36.1 | 30.0 |
| 02:00 | 18:00 PST / 19:00 PDT | 468 | 29.4 | 24.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 468 | 28.3 | 22.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 468 | 31.4 | 22.6 |
| 05:00 | 21:00 PST / 22:00 PDT | 468 | 32.7 | 25.5 |
| 06:00 | 22:00 PST / 23:00 PDT | 468 | 43.0 | 35.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 468 | 50.8 | 41.9 |
| 08:00 | 00:00 PST / 01:00 PDT | 468 | 52.3 | 42.8 |
| 09:00 | 01:00 PST / 02:00 PDT | 467 | 48.3 | 37.8 |
| 10:00 | 02:00 PST / 03:00 PDT | 467 | 43.6 | 36.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 467 | 42.8 | 34.5 |
| 12:00 | 04:00 PST / 05:00 PDT | 467 | 57.2 | 43.7 |
| 13:00 | 05:00 PST / 06:00 PDT | 467 | 58.9 | 47.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 467 | 58.7 | 47.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 467 | 52.7 | 43.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 467 | 41.9 | 34.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 467 | 35.6 | 27.2 |
| 18:00 | 10:00 PST / 11:00 PDT | 467 | 32.1 | 24.6 |
| 19:00 | 11:00 PST / 12:00 PDT | 467 | 30.5 | 23.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 467 | 30.2 | 26.0 |

### Q2. Share of daily range by block

Days with zero range excluded: 0. Winter Mondays' SYDNEY block holds 2 bars, not 3.

**Q2 GBP_JPY, all weekdays**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 2327 | 0.300 | 0.134 | 0.182 | 0.260 | 0.371 | 0.527 |
| TOKYO | 2327 | 0.487 | 0.253 | 0.340 | 0.460 | 0.616 | 0.758 |
| LONDON | 2327 | 0.583 | 0.339 | 0.440 | 0.571 | 0.715 | 0.847 |
| LDN_NY | 2327 | 0.547 | 0.315 | 0.407 | 0.535 | 0.670 | 0.805 |
| NY_PM | 2327 | 0.391 | 0.215 | 0.272 | 0.364 | 0.477 | 0.613 |

**Q2 GBP_JPY, Mon**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.428 | 0.193 | 0.277 | 0.397 | 0.538 | 0.714 |
| TOKYO | 466 | 0.503 | 0.275 | 0.352 | 0.467 | 0.634 | 0.784 |
| LONDON | 466 | 0.562 | 0.329 | 0.424 | 0.548 | 0.694 | 0.804 |
| LDN_NY | 466 | 0.497 | 0.278 | 0.363 | 0.460 | 0.627 | 0.746 |
| NY_PM | 466 | 0.361 | 0.201 | 0.247 | 0.338 | 0.435 | 0.573 |

**Q2 GBP_JPY, Tue**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 463 | 0.260 | 0.124 | 0.165 | 0.225 | 0.325 | 0.426 |
| TOKYO | 463 | 0.498 | 0.257 | 0.343 | 0.480 | 0.624 | 0.751 |
| LONDON | 463 | 0.592 | 0.355 | 0.455 | 0.576 | 0.719 | 0.870 |
| LDN_NY | 463 | 0.531 | 0.319 | 0.402 | 0.525 | 0.656 | 0.752 |
| NY_PM | 463 | 0.398 | 0.217 | 0.269 | 0.363 | 0.496 | 0.641 |

**Q2 GBP_JPY, Wed**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.271 | 0.140 | 0.177 | 0.242 | 0.336 | 0.437 |
| TOKYO | 466 | 0.483 | 0.250 | 0.350 | 0.461 | 0.604 | 0.744 |
| LONDON | 466 | 0.606 | 0.360 | 0.480 | 0.602 | 0.739 | 0.854 |
| LDN_NY | 466 | 0.537 | 0.320 | 0.406 | 0.524 | 0.657 | 0.781 |
| NY_PM | 466 | 0.413 | 0.229 | 0.294 | 0.388 | 0.501 | 0.642 |

**Q2 GBP_JPY, Thu**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.262 | 0.120 | 0.168 | 0.235 | 0.333 | 0.429 |
| TOKYO | 466 | 0.476 | 0.239 | 0.328 | 0.446 | 0.610 | 0.754 |
| LONDON | 466 | 0.592 | 0.329 | 0.446 | 0.576 | 0.746 | 0.863 |
| LDN_NY | 466 | 0.559 | 0.325 | 0.420 | 0.550 | 0.664 | 0.822 |
| NY_PM | 466 | 0.409 | 0.214 | 0.281 | 0.381 | 0.508 | 0.660 |

**Q2 GBP_JPY, Fri**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 466 | 0.277 | 0.126 | 0.175 | 0.245 | 0.331 | 0.469 |
| TOKYO | 466 | 0.474 | 0.247 | 0.321 | 0.445 | 0.603 | 0.739 |
| LONDON | 466 | 0.562 | 0.313 | 0.427 | 0.550 | 0.694 | 0.826 |
| LDN_NY | 466 | 0.609 | 0.354 | 0.461 | 0.586 | 0.742 | 0.902 |
| NY_PM | 466 | 0.376 | 0.210 | 0.272 | 0.356 | 0.456 | 0.552 |

### Q3. Where the daily high and low form

**Q3 GBP_JPY, all weekdays** (N days 2327)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 19.6% | 17.2% |
| TOKYO | 19.5% | 20.6% |
| LONDON | 19.2% | 22.5% |
| LDN_NY | 18.7% | 20.7% |
| NY_PM | 23.0% | 19.0% |

High and low in the same block: 4.7% of days

**Q3 GBP_JPY, Mon** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 32.4% | 24.9% |
| TOKYO | 18.5% | 15.9% |
| LONDON | 17.0% | 22.1% |
| LDN_NY | 15.2% | 18.9% |
| NY_PM | 17.0% | 18.2% |

High and low in the same block: 5.2% of days

**Q3 GBP_JPY, Tue** (N days 463)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.1% | 17.1% |
| TOKYO | 18.1% | 21.0% |
| LONDON | 21.2% | 21.8% |
| LDN_NY | 16.4% | 19.0% |
| NY_PM | 26.1% | 21.2% |

High and low in the same block: 3.7% of days

**Q3 GBP_JPY, Wed** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 16.1% | 14.2% |
| TOKYO | 18.7% | 26.0% |
| LONDON | 20.0% | 22.1% |
| LDN_NY | 20.0% | 19.3% |
| NY_PM | 25.3% | 18.5% |

High and low in the same block: 2.8% of days

**Q3 GBP_JPY, Thu** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 15.5% | 13.9% |
| TOKYO | 18.9% | 23.6% |
| LONDON | 19.7% | 24.5% |
| LDN_NY | 21.7% | 18.7% |
| NY_PM | 24.2% | 19.3% |

High and low in the same block: 5.4% of days

**Q3 GBP_JPY, Fri** (N days 466)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 15.9% | 16.1% |
| TOKYO | 23.4% | 16.7% |
| LONDON | 18.0% | 21.9% |
| LDN_NY | 20.4% | 27.5% |
| NY_PM | 22.3% | 17.8% |

High and low in the same block: 6.4% of days

### Q4. How early the extremes are set

**Q4 GBP_JPY, all weekdays** (N days 2327)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 30.3% | 29.0% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 48.2% | 49.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 72.4% | 74.6% |

**Q4 GBP_JPY, Mon** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 42.7% | 36.3% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 59.2% | 51.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 78.3% | 75.5% |

**Q4 GBP_JPY, Tue** (N days 463)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 27.2% | 29.2% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 46.7% | 48.4% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 70.2% | 72.6% |

**Q4 GBP_JPY, Wed** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 25.5% | 27.0% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 43.8% | 52.4% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 68.9% | 75.8% |

**Q4 GBP_JPY, Thu** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 27.9% | 27.3% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 42.9% | 48.9% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 72.5% | 75.1% |

**Q4 GBP_JPY, Fri** (N days 466)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 27.9% | 25.3% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 48.5% | 44.6% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 71.9% | 74.0% |

### Q5. Mean ATR(14) by timeframe (pips; numbers only)

| timeframe | all weekdays (N) | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|---|
| H1 | 39.8 (56059) | 40.5 (11224) | 38.3 (11178) | 39.3 (11214) | 40.0 (11223) | 40.7 (11220) |
| H4 | 79.7 (14014) | 80.9 (2806) | 79.0 (2792) | 79.0 (2803) | 79.3 (2807) | 80.4 (2806) |
| D1 | 200.6 (2329) | 200.5 (467) | 200.7 (464) | 200.4 (465) | 200.6 (466) | 200.7 (467) |


## Reading rules fixed in the spec (§5, §6)

| pair | boundary (UTC) | step = mean(hour b) ÷ mean(hour b−1) | sharp (≥1.5 or ≤0.667)? | DST-exposed? |
|---|---|---|---|---|
| GBP_AUD | 21:00 | 0.98 | no | yes |
| GBP_AUD | 00:00 | 1.19 | no | no |
| GBP_AUD | 07:00 | 1.15 | no | yes |
| GBP_AUD | 12:00 | 1.14 | no | yes |
| GBP_AUD | 16:00 | 0.84 | no | yes |
| GBP_JPY | 21:00 | 0.95 | no | yes |
| GBP_JPY | 00:00 | 1.24 | no | no |
| GBP_JPY | 07:00 | 1.21 | no | yes |
| GBP_JPY | 12:00 | 1.18 | no | yes |
| GBP_JPY | 16:00 | 0.81 | no | yes |

GBP_AUD: largest hourly mean 60.2 at 14:00 UTC; smallest 34.1 at 04:00 UTC; ratio 1.77
GBP_JPY: largest hourly mean 53.5 at 14:00 UTC; smallest 27.9 at 21:00 UTC; ratio 1.92

Phase 3 gate (§6): CONCENTRATED — Phase 3 question not moot (team decides)
```
