# Spec: do scheduled US releases move GBP/JPY and GBP/AUD? (pre-registered, 2005–2013 STUDY data)

**Status:** pre-registered 2026-11-01 at the owner's direction (driver-coverage
proposal §7, decision 4: "US-event reactions" is the next study). This file,
the runner (`studies/us_event_reaction_test.py`) and the event table
(`studies/us_events_2005_2013.csv`, sources and checksums in
`studies/us_events_sources.json`) are committed together. Their sha256 is
recorded in validation_log in the same commit. No 2005–2013 outcome has been
computed. The run happens once, after this commit, and its output goes to
validation_log verbatim, whatever it says.

## 1. Why, and what is tested

- **The decision it informs.** The news gate stands aside around high-impact
  events in the pair's own currencies only. US events (Fed, US CPI, the jobs
  report) are left out (v1 boundary). The owner chose to bring US events in
  as **context first** and to decide on **gating** from evidence. This study
  is that evidence.
- **The reason they might matter.** GBP/JPY carries the yen's sensitivity
  to US yields through USD/JPY. AUD is risk-sensitive, and US data adds more
  AUD volatility than Chinese data (RBA Bulletin, Mathews 2016). Release
  surprises move currencies on the day (Andersen, Bollerslev, Diebold and
  Vega, *AER* 2003). Whether that survives into a **cross**, where the dollar
  partly cancels, is the open question.
- **The hypothesis.** On the trading day of a scheduled US release, the
  pair's daily range is larger than on comparable days without one.
- **Six cells**, each its own question: {GBP_JPY, GBP_AUD} × {FOMC, CPI, NFP}.
  - FOMC = the scheduled policy statement.
  - CPI = the monthly Consumer Price Index release.
  - NFP = the monthly Employment Situation release.
- **What this is not.** It is not a trading edge and has no direction. A
  bigger day is a risk to an open position or a fresh entry, which is what
  a gate guards against.

## 2. Data

- **Prices:** OANDA mid D1 and H4 candles, STUDY trading days
  2005-01-01 → 2013-12-30. They are fetched through
  `history_study_gate_s3.fetch`, which refuses the embargo and the sealed
  exam, and converted with the approved weekend rule
  (`history_study_convert.py`). This is the same pipeline as the carry
  study, and the data passed §3 items 1–4 and the Monday re-check.
- **Trading day:** a converted D1 session. Its date is the New York date of
  (open + 7 h), so a session runs 17:00 to 17:00 New York time. Every
  release in scope (08:30 ET for CPI and NFP; 12:30–14:15 ET for FOMC)
  falls inside the session that carries its own calendar date.
- **Events:** `studies/us_events_2005_2013.csv`, one row per release
  (`date,event,time_et,scheduled,source_id`). The dates come from the
  Federal Reserve and BLS release archives, with ALFRED as a cross-check
  where used. Raw-page checksums are in `us_events_sources.json` (313
  pages, including all 216 BLS releases and every FOMC statement). The raw
  pages themselves (77 MB) are kept outside the repo at
  `~/intel_study_archives/us_events_2005_2013/`, which is git-ignored, and
  their hashes were re-verified there.
  - Cross-checks: NFP matches ALFRED PAYEMS vintages 108/108. All 108 CPI
    dates appear in ALFRED CPIAUCSL vintages. FOMC matches the Fed press
    listing 70/70 for 2006–2013. All 21 fed funds target changes fall on a
    table FOMC date. The sourcing notes are in the archive's `NOTES.md`.
  - Each release is mapped to the session that holds it. A release at or
    after 17:00 ET, or on a weekend, belongs to the next weekday's session.
    Only one row is affected: the Sunday 2010-05-09 21:15 ET action maps to
    the Monday 2010-05-10 session.
  - Unscheduled FOMC actions (`scheduled=false`) form no cell. They are
    never used as controls and are listed descriptively. There are six,
    included where the Fed's historical page lists a statement for an FOMC
    call: 2007-08-10, 2007-08-17, 2008-01-22, 2008-03-11, 2008-10-08 and
    2010-05-09.

## 3. The measure

- **Range ratio** of day d: (high − low) ÷ the median (high − low) of the
  **20 trading days before d** (d itself excluded). The first 20 days are
  warm-up. It is unit-free, so the 2008 days do not swamp the rest.
- **Controls** for an event day e: trading days with
  - the same weekday as e,
  - within 28 calendar days of e (before or after),
  - no US event of any type (any of the three, scheduled or not),
  - a defined range ratio.
  An event day with no control is dropped and counted.
- **Paired effect** of e: ratio(e) − the mean ratio of its controls.
  - Same-weekday matching removes the day-of-week pattern (NFP is a Friday).
  - The ±28-day window removes slow volatility regimes.
- **Primary statistic per cell:** the mean paired effect. +0.25 means event
  days run 25% of a normal day's range larger than comparable days.

## 4. The test

- **Bounds:** one-sided percentile-bootstrap bounds on the mean paired
  effect, resampling events (20,000 resamples, seed
  `uer:<pair>:<event>`).
- **Family correction:** Bonferroni across the 6 cells, so each one-sided
  bound is taken at α = 0.05 / 6 ≈ 0.0083.
- **Materiality threshold:** **+0.10**. A gate is worth considering only if
  the day is reliably at least 10% of a normal day's range larger.

## 5. Verdict per cell (decided now)

| Verdict | Condition |
|---|---|
| **MATERIAL** | lower bound ≥ +0.10 |
| **NOT MATERIAL** | upper bound < +0.10 |
| **INCONCLUSIVE** | anything else |

- **MATERIAL** means the event belongs in a future gating spec for that
  pair. The gate itself is a separate, protected change with its own spec
  and team review.
- **NOT MATERIAL** means context-only is enough for that pair and event.
- **INCONCLUSIVE** keeps the status quo: context only, gate not justified.

## 6. Power (stated before the run)

- **Spread** (2022–2026 GBP/AUD daily data, learning only): the range ratio
  has standard deviation 0.51 across all days. With about 7 controls per
  event, the paired effect's SD is about 0.55.
- **Expected N:** about 72 FOMC, 108 CPI and 108 NFP events per pair, before
  warm-up and dropped events.
- **Bound margin** at α = 0.0083: about 0.15 (FOMC) and 0.13 (CPI, NFP).
  - **MATERIAL** therefore needs an observed mean of roughly **+0.23 to
    +0.26**.
  - At 80% power, a true effect of about **+0.27 (CPI, NFP) to +0.31
    (FOMC)** is needed.
  - **NOT MATERIAL** needs an observed mean below about **−0.03 to −0.06**.
    Event days would have to be no bigger than normal ones, or smaller.
- **The consequence:** a real but modest effect (+0.10 to +0.20) will most
  likely read **INCONCLUSIVE**. That is the test being honest about its
  reach.

## 7. Secondary analyses (reported; never change a verdict; descriptive only)

1. **Close-to-close move:** |close(d) − close(d−1)| over the same
   20-day median range, paired against the same controls.
2. **Round trip within 3 days:** the share of days whose close-to-close
   move is fully given back (a close at or beyond the previous close) by
   any of the next 3 closes. Event days are compared with control days.
   This compares with R25, where about half of major-release moves
   round-trip on GBP/AUD.
3. **Sub-periods:** 2005-01→2008-06, 2008-07→2009-06 (the crisis),
   2009-07→2013-12. These are the same cuts as the carry study.
4. **Unscheduled FOMC actions:** each one's range ratio, listed.
5. **Counts:** events per year per cell, events dropped (warm-up, no
   session, no control) and the mean number of controls.

## 8. Run discipline

1. **`selftest`** must print `SELFTEST OK`. It checks:
   - the verdict boundaries;
   - a hand-computed range ratio, including that the day itself is outside
     its own normaliser;
   - control selection: same weekday, ±28 days, never another event type,
     never an unscheduled action;
   - the session-date mapping of a 17:00-New-York candle;
   - the round-trip rule;
   - a known effect (+0.40 at N=108, which must be MATERIAL);
   - a zero effect (MATERIAL in at most about 1% of runs);
   - the embargo refusal.
2. **Commit** this spec, the runner and the event table, with their sha256
   in validation_log. This is the pre-registration.
3. **`counts`** (through `scripts/reality_run.py`): fetch the STUDY
   candles, store them with their sha256 outside the repo, and print
   **counts only**: matched events, drops and controls per cell. No ratio,
   range or effect is printed. Record that in validation_log before any
   outcome.
4. **`full`**: runs once on exactly those files. It refuses if any file's
   hash differs. The output goes verbatim to validation_log, and each
   cell's verdict goes into `foundation/research_findings.md`.
5. **Any change** to this spec after step 2 is a new pre-registration with
   a new id, logged as such. Nothing is tuned after seeing a result.
