# Gold spec remediation: pre-run fixes (report)

**Date:** 2026-11-16. **Branch:** `feat/gold-rule-specs` (worktree, not merged).
**Brief:** the owner's "Gold spec remediation — pre-run fixes", Parts 1–7.
**Nothing was run for specs B, C or PRC-1. No sealed-exam (2014-01-01 →
2021-04-25) data was fetched, loaded or read.** Every computation below is one
of: a unit test; OANDA 2026 candles (live, read-only, through
`scripts/reality_run.py`); or the existing archives already used by committed
studies (GBP 2005–2013 STUDY, gold 2021–2026 USED).

Evidence labels: VERIFIED (observed, and the check was shown able to fail);
OBSERVED (observed, ability to fail not shown); INFERRED; PENDING (needs the
run the brief forbids, or the owner); NOT CHECKED.

## Conflicts that need the owner's ruling (AGENTS.md rule 5)

1. **Part 1.1: the shared financing helper was not changed in place.**
   `studies/shadow_cost_regrade.rollover_nights` charges an exit landing on
   17:00 New York by design: its docstring says so, committed self-tests pin it
   (`shadow_cost_regrade.py` selftest: an exit at exactly 21:00Z on 2026-10-05
   is charged 1 night; `first_pullback_study.py:523`), and the first-pullback
   spec pre-registered it ("at or before the exit"). Changing it would break
   those tests and silently re-cost the committed results that use it: R37,
   R38 (`first_pullback_study.py`), R43 (`breakout_confirmation_study.py`), R44
   (`htf_breakout_study.py`), R46 (`m15_entry_study.py`) and the shadow-cost
   regrade. **Done instead:** a new function `studies/gold_rule_costs.held_nights`
   with the corrected boundary, used by every gold spec. **For the owner:**
   R37's 38.2% cell is REFUTED with a 90% upper bound of +0.140R against the
   +0.15R bar (research_findings R37, "marginal"); its timed exits close on H4
   slot boundaries, one in six of which is 17:00 New York. Whether the
   boundary charge moved that bound is NOT CHECKED (financing can add or
   subtract R by side). A declared re-costing of those studies would settle
   it; it was not run.
2. **Part 2.1: there is no "finding" to mark REFUTED in research_findings.md.**
   The 67% statistic is not a numbered entry there. It lives in
   `studies/gold_session_report.md`, the capability inventory and the specs
   index. It is also a correct measurement whose value happens to equal
   chance; REFUTED would say the measurement was wrong. **Done instead:** the
   arithmetic is recorded beside the claim in the session report and the
   inventory (dated notes), in the sweep, and in spec B's amendments; spec B no
   longer cites it. **For the owner:** add a research_findings row labelled
   REFUTED as written, or a different label (for example UNINFORMATIVE).
3. **Part 6.2: the owner's 2026 origin figures do not reproduce.** The weekend
   group matches (owner −$1.59, t −0.08; reproduced −$1.60, t −0.08, N 11), but
   same-week (owner +$34.74, t 1.71; reproduced +$14.38, t 0.76, N 17) and all
   (owner +$20.46, t 1.37; reproduced +$8.10, t 0.58, N 28) do not. Four other
   definitions were tried (appendix C); none gives +$34.74. They are recorded
   in PRC-1 as reported by the owner and not reproduced, not as OBSERVED.
4. **Part 6.4: the regime description does not match the candles.** Measured:
   −10.2% from the first 2026 open to the 2026-11-12 close; −30.7% from the
   2026 high; median daily range 2.21% of price (appendix B). The brief says
   about −27% and about 2.7%. PRC-1 uses the measured figures.
5. **Part 3.1: the family size.** The brief fixes m = 7 (A 2 + B 2 + C 3).
   With A shelved and PRC-1 added, the tests that can run are 6 (α 0.00851);
   counting A's two cells plus PRC-1 gives 8 (α 0.00639). **The specs use
   m = 7, α = 0.0073, as instructed**, and list GTP-1 as one held slot. The
   owner may rule m = 8 (stricter).
6. **Part 1.1 / 1.3 / 1.4 / 5.2 / 5.3 ask for per-trade numbers.** Before/after
   night counts for every trade, gap-affected trades and the change in mean R,
   the empirical SD of R, B's days traded before and after, and the share of
   trades and R each cap removes all exist only by running the rules on STUDY
   data. Part 7 forbids running B and C, and computing outcomes before freezing
   breaks pre-registration. All are written into the specs as required outputs
   and are PENDING the run.

## Item by item

| Item | What changed | Before → after / result | Label |
|---|---|---|---|
| 1.1 financing | `studies/gold_rule_costs.held_nights` + `tests/test_gold_rule_costs.py` (6 tests) | Tue 10:00 → Wed 14:00 PT: 4 → **1**; Wed 10:00 → Thu 14:00 PT: 4 → **3**; inside one session: 0 → **0** (same in daylight time). 3 mutants (exit boundary, entry boundary, Wednesday triple) all caught; restored source byte-identical; 6/6 pass | VERIFIED |
| 1.1 per-trade counts | — | requires running the rules | PENDING |
| 1.2 exits | B: exit 1:00 PM PT (12:00 PT bar's close); C: 1:00 PM PT next session; PRC-1: same; dated amendments | old exits were 17:00 New York | VERIFIED (spec text) |
| 1.2 spread | `studies/gold_spread_windows.py`, OANDA bid/ask M5, Sep 14 – Nov 13 2026, 12,396 candles | candle closing 1:00 PM PT: median **$0.48**, p90 $0.62; 13:00–14:00 PT: median $0.52, p90 $0.69; candle closing 2:00 PM PT: median **$0.66**, p90 **$1.54**; mid-session 06–12 PT: median $0.46, p90 $0.60; **14:00–15:00 PT: no candles (gold's daily break)**; reopen 15:00–16:00 PT: median $0.59. 1:00 PM PT is not materially wider than mid-session; no window change recommended | OBSERVED (45 trading days, 2026 quotes; STUDY-era spreads unmeasured) |
| 1.3 gaps | B, C, PRC-1: a bar opening beyond the stop fills at its open | trades affected and change in mean R | spec VERIFIED; numbers PENDING |
| 1.4 power | B, C, PRC-1: power at SD 1.2 / 2.0 / 3.0R at α 0.0073 | B: smallest edge +0.090R (SD 1.2) to +0.226R (SD 3.0) at N 1,900; C: +0.411R to +1.027R at N 92; C-FOMC +0.904R to +2.260R at N 19; PRC-1: +0.42R to +1.06R at N 87 (`power_check`) | OBSERVED (arithmetic); empirical SD PENDING |
| 2.1 67% | arithmetic recorded beside the claim; removed from B's reasons | (2/π)·asin(√(17/23)) = **65.87%**; vol-shaped chance 66.2%; observed 67.0%; +0.6 SE. 17 of 23 confirmed from the code: study day 21:00→21:00 UTC minus gold's break hour, cutoff 15:00 UTC | VERIFIED (recomputed observed equals the report's 67.0%) |
| 2.1 REFUTED label | not applied | see conflict 2 | PENDING (owner) |
| 2.2 sweep | `studies/timing_claims_sweep.py`, `docs/reports/timing_claims_sweep.md` | within 2 SE of chance: gold "high set by 7 AM PST"; GBP "lows by 03:00 UTC" (both), "by 09:00 UTC" (GBP/AUD); 6 of 20 GBP block-extreme cells; GBP/JPY Sydney and Tokyo block shares. Busy hours, block shares, gold's London/NY share and extremes, gold's "low by 7 AM", GBP's "high by 15:00 UTC" are beyond chance | OBSERVED (every recomputed observed figure equals its published value; the baseline simulation was not itself mutation-tested) |
| 3.1 Šidák | B §4.1, C §5, PRC-1 §6: α = 1 − 0.95^(1/7) = 0.0073 | was Bonferroni within each spec | VERIFIED (spec text; arithmetic shown) |
| 3.2 single line | B §4.2: m = +0.05R for both verdicts | N 1,900, SD 1.2: SUPPORTED if mean > +0.117R, REFUTED if < +0.015R; table at SD 2.0 and 3.0 in the spec. Also applied to C and PRC-1 for consistency (owner to confirm) | VERIFIED (spec text) |
| 3.3 exam rule | B §4.3, C §5, PRC-1 | if more than one passes, GMW-1 goes to the sealed exam | VERIFIED (spec text) |
| 4.1 shelve A | GTP-1 status SHELVED with the arithmetic | 45 rally legs, 32 reached 38.2% (R48); realistic 12–20 long episodes → INSUFFICIENT | VERIFIED (R48 counts); the 12–20 is INFERRED |
| 4.2 R37 | corrected in GTP-1 (header amendment and §1) | "INCONCLUSIVE" → **REFUTED** (38.2% cell; R38 cells INCONCLUSIVE). Searched docs, foundation, studies, markups and validation_log: no other document repeats it; the specs index already says REFUTED | VERIFIED |
| 4.2 78.6% | corrected in GTP-1 (amendment and §1) | conditional on reaching 38.2%: STUDY rallies 13 ÷ 32 = **40.6%**, falls 24 ÷ 51 = **47.1%**; USED rallies 9 ÷ 25 = 36.0%, falls 15 ÷ 36 = 41.7% (C3 output counts). The unconditional statements in the C3 report and chart_reading_method are correct as unconditional and unchanged | VERIFIED |
| 5.1 leakage | B's news-day side check removed | — | VERIFIED (spec text) |
| 5.2 same stop | B §3.3: d = window range + 0.05 ATR for both cells | days traded before/after | spec VERIFIED; counts PENDING |
| 5.3 caps | B, C: capped headline, uncapped required side result with shares removed | — | spec VERIFIED; numbers PENDING |
| 5.4 floors | B, C: 0.15 and 0.30 ATR both run; 0.30 binding if they disagree; the owner's management as a side result | `MIN_STOP_ATR_MULTIPLE = 0.3` at `setup_check.py:58` | VERIFIED (spec text) |
| 5.5 FOMC times | `studies/fomc_statement_times_2006_2013.csv`, 69 rows (63 scheduled, 6 unscheduled), one source per row | 13 SOURCED (the archive's Fed pages), 3 DERIVED (2011 notice: 12:30 + 1h45), 1 SOURCED_SECONDARY (NPR, 2012-06-20), 4 POSTED_TIME (Fed 2012 press-conference pages: 12:20–12:35 posting times), **48 UNSOURCED (44 scheduled)**, listed in the file | OBSERVED |
| 5.6 2026 counts | reproduced: `studies/gold_2026_release_reactions.py` + `studies/us_events_2026.csv` (each date sourced) | FOMC 6/7, CPI 6/11, NFP 8/10, all 20/28; the 2026-04-03 jobs report (Good Friday) has no candle | VERIFIED (same counts as the earlier measurement; reproduced by a committed script) |
| 5.7 decisions | B §8, C §8, PRC-1 §9 tables, named mutation sets | within-bar order, pooling, ATR, missing bars, holidays, the M15 check ($0.05, 99%, otherwise stop), same-day releases | VERIFIED (spec text) |
| 6 PRC-1 | `docs/specs/post_release_continuation_spec.md` | one test (same-week, event types pooled), weekend apart, α 0.0073, m +0.05R, no re-runs; N ≤ 87; REFUTED needs mean < −0.12R (SD 1.2) / −0.23R (SD 2.0); STUDY only, sealed exam untouched | VERIFIED (spec text); origin figures conflict 3 |

## Not closed

- Per-trade numbers (items 1.1, 1.3, 1.4, 5.2, 5.3): PENDING the counts stage
  and the run after sign-off.
- REFUTED label for the 67% statistic: owner's ruling (conflict 2).
- Re-costing R37/R38/R43/R44/R46 under the corrected boundary: owner's ruling
  (conflict 1).
- 44 scheduled FOMC meetings have no sourced statement time.
- The owner's PRC-1 origin figures: owner's computation needed (conflict 3).
- Prerequisite P2 (US policy-rate table) and GNC-1's M15 fetch: not started.
- STUDY-era (2006–2013) spreads: not measurable from our data; placeholders.
- The literature behind trend-following horizons (GTP-1): NOT CHECKED.
- The London fix timing confound (GMW-1): reviewer-stated, NOT CHECKED.

## Appendix A: timing claims sweep output (verbatim)

```
Baselines: REPS 5, STEPS 20, seed 7, bootstrap 500

## STUDY 2005-2013: GBP_AUD

Complete days scored: 2325 (simulated days per baseline: 11625, 11625)

### Hourly range profile (claims about busy and quiet hours)
- all hours mean 45.88; busiest hour 14:00 UTC mean 60.21 (se 1.09); quietest 04:00 UTC mean 34.09 (se 0.61); ratio 1.77
- chance baseline (no time-of-day effect): every hour equals the all-hours mean, ratio 1.00
- busiest hour minus all-hours mean: 13.2 se
- 12:00-15:00 UTC (04:00-07:00 PST) mean 56.97 vs other hours 44.28: difference 12.70 = 21.0 se (hours within a day are not independent; se is optimistic)
- hour means: 00 46.7, 01 46.3, 02 35.2, 03 35.5, 04 34.1, 05 37.4, 06 46.3, 07 53.0, 08 55.5, 09 54.0, 10 49.3, 11 48.1, 12 54.7, 13 56.0, 14 60.2, 15 57.5, 16 48.3, 17 42.4, 18 42.7, 19 42.0, 20 38.6, 21 37.8, 22 38.4, 23 39.2

### When the day's high and low are already set (Q4)
- high set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 34.2%; uniform 33.3%; vol-shaped 29.1%; se 1.0 pts; observed minus vol-shaped +5.1 pts (+5.2 se) -> beyond 2 SE
- high set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 50.9%; uniform 49.9%; vol-shaped 44.4%; se 1.0 pts; observed minus vol-shaped +6.5 pts (+6.3 se) -> beyond 2 SE
- high set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 71.9%; uniform 67.0%; vol-shaped 66.0%; se 0.9 pts; observed minus vol-shaped +5.8 pts (+6.3 se) -> beyond 2 SE
- low set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 27.7%; uniform 32.5%; vol-shaped 29.0%; se 0.9 pts; observed minus vol-shaped -1.3 pts (-1.4 se) -> WITHIN 2 SE OF CHANCE
- low set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 44.1%; uniform 49.0%; vol-shaped 44.7%; se 1.0 pts; observed minus vol-shaped -0.7 pts (-0.6 se) -> WITHIN 2 SE OF CHANCE
- low set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 69.0%; uniform 65.7%; vol-shaped 66.0%; se 1.0 pts; observed minus vol-shaped +3.0 pts (+3.1 se) -> beyond 2 SE

### Where the day's high and low form, by block (Q3)
- high in SYDNEY: observed 20.7%; uniform 22.9%; vol-shaped 19.0%; se 0.8 pts; +2.1 se -> beyond 2 SE
- high in TOKYO: observed 22.4%; uniform 21.6%; vol-shaped 19.0%; se 0.9 pts; +3.9 se -> beyond 2 SE
- high in LONDON: observed 16.7%; uniform 13.8%; vol-shaped 15.9%; se 0.8 pts; +1.1 se -> WITHIN 2 SE OF CHANCE
- high in LDN_NY: observed 17.5%; uniform 11.7%; vol-shaped 16.7%; se 0.8 pts; +1.0 se -> WITHIN 2 SE OF CHANCE
- high in NY_PM: observed 22.7%; uniform 30.0%; vol-shaped 29.5%; se 0.9 pts; -7.8 se -> beyond 2 SE
- low in SYDNEY: observed 18.0%; uniform 22.2%; vol-shaped 19.1%; se 0.8 pts; -1.4 se -> WITHIN 2 SE OF CHANCE
- low in TOKYO: observed 16.9%; uniform 21.4%; vol-shaped 19.1%; se 0.8 pts; -2.9 se -> beyond 2 SE
- low in LONDON: observed 19.9%; uniform 13.2%; vol-shaped 15.5%; se 0.8 pts; +5.2 se -> beyond 2 SE
- low in LDN_NY: observed 20.0%; uniform 12.2%; vol-shaped 16.7%; se 0.8 pts; +4.0 se -> beyond 2 SE
- low in NY_PM: observed 25.2%; uniform 31.0%; vol-shaped 29.6%; se 0.9 pts; -4.8 se -> beyond 2 SE
- high and low in the same block: observed 3.6%; uniform 1.6%; vol-shaped 1.4%; +5.8 se -> beyond 2 SE

### Block range as a share of the day's range, medians (Q2)
- SYDNEY: observed median 0.297; uniform 0.328; vol-shaped 0.274; se 0.004; +5.1 se -> beyond 2 SE
- TOKYO: observed median 0.483; uniform 0.536; vol-shaped 0.468; se 0.004; +3.7 se -> beyond 2 SE
- LONDON: observed median 0.531; uniform 0.447; vol-shaped 0.488; se 0.005; +9.3 se -> beyond 2 SE
- LDN_NY: observed median 0.522; uniform 0.393; vol-shaped 0.484; se 0.006; +6.8 se -> beyond 2 SE
- NY_PM: observed median 0.394; uniform 0.448; vol-shaped 0.431; se 0.005; -8.0 se -> beyond 2 SE

### Monday's day-start block holds the high (Q3 by weekday)
- Mon: high in SYDNEY 29.7% (N 465); vol-shaped all-days 19.0%; +5.0 se -> beyond 2 SE
- Tue: high in SYDNEY 17.5% (N 463); vol-shaped all-days 19.0%; -0.9 se -> WITHIN 2 SE OF CHANCE
- Wed: high in SYDNEY 18.5% (N 465); vol-shaped all-days 19.0%; -0.3 se -> WITHIN 2 SE OF CHANCE
- Thu: high in SYDNEY 20.0% (N 466); vol-shaped all-days 19.0%; +0.5 se -> WITHIN 2 SE OF CHANCE
- Fri: high in SYDNEY 18.0% (N 466); vol-shaped all-days 19.0%; -0.5 se -> WITHIN 2 SE OF CHANCE

## STUDY 2005-2013: GBP_JPY

Complete days scored: 2327 (simulated days per baseline: 11635, 11635)

### Hourly range profile (claims about busy and quiet hours)
- all hours mean 39.57; busiest hour 14:00 UTC mean 53.54 (se 0.75); quietest 21:00 UTC mean 27.89 (se 0.57); ratio 1.92
- chance baseline (no time-of-day effect): every hour equals the all-hours mean, ratio 1.00
- busiest hour minus all-hours mean: 18.5 se
- 12:00-15:00 UTC (04:00-07:00 PST) mean 51.19 vs other hours 37.89: difference 13.29 = 30.3 se (hours within a day are not independent; se is optimistic)
- hour means: 00 41.3, 01 36.5, 02 30.2, 03 28.7, 04 29.2, 05 32.9, 06 41.8, 07 50.4, 08 52.7, 09 48.8, 10 43.6, 11 42.0, 12 49.5, 13 50.5, 14 53.5, 15 49.9, 16 40.6, 17 36.1, 18 35.2, 19 33.4, 20 29.2, 21 27.9, 22 29.7, 23 33.3

### When the day's high and low are already set (Q4)
- high set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 30.3%; uniform 33.1%; vol-shaped 28.0%; se 1.0 pts; observed minus vol-shaped +2.3 pts (+2.4 se) -> beyond 2 SE
- high set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 48.2%; uniform 49.7%; vol-shaped 45.5%; se 1.0 pts; observed minus vol-shaped +2.7 pts (+2.6 se) -> beyond 2 SE
- high set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 72.4%; uniform 66.9%; vol-shaped 66.9%; se 0.9 pts; observed minus vol-shaped +5.5 pts (+5.9 se) -> beyond 2 SE
- low set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 29.0%; uniform 32.6%; vol-shaped 27.4%; se 0.9 pts; observed minus vol-shaped +1.6 pts (+1.7 se) -> WITHIN 2 SE OF CHANCE
- low set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 49.1%; uniform 49.6%; vol-shaped 45.0%; se 1.0 pts; observed minus vol-shaped +4.1 pts (+4.0 se) -> beyond 2 SE
- low set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 74.6%; uniform 66.4%; vol-shaped 67.3%; se 0.9 pts; observed minus vol-shaped +7.3 pts (+8.0 se) -> beyond 2 SE

### Where the day's high and low form, by block (Q3)
- high in SYDNEY: observed 19.6%; uniform 22.8%; vol-shaped 18.0%; se 0.8 pts; +1.9 se -> WITHIN 2 SE OF CHANCE
- high in TOKYO: observed 19.5%; uniform 21.8%; vol-shaped 19.4%; se 0.8 pts; +0.1 se -> WITHIN 2 SE OF CHANCE
- high in LONDON: observed 19.2%; uniform 13.1%; vol-shaped 17.0%; se 0.8 pts; +2.7 se -> beyond 2 SE
- high in LDN_NY: observed 18.7%; uniform 12.3%; vol-shaped 17.0%; se 0.8 pts; +2.1 se -> beyond 2 SE
- high in NY_PM: observed 23.0%; uniform 29.9%; vol-shaped 28.6%; se 0.9 pts; -6.4 se -> beyond 2 SE
- low in SYDNEY: observed 17.2%; uniform 22.5%; vol-shaped 18.0%; se 0.8 pts; -1.0 se -> WITHIN 2 SE OF CHANCE
- low in TOKYO: observed 20.6%; uniform 21.6%; vol-shaped 18.6%; se 0.8 pts; +2.4 se -> beyond 2 SE
- low in LONDON: observed 22.5%; uniform 13.4%; vol-shaped 17.7%; se 0.9 pts; +5.5 se -> beyond 2 SE
- low in LDN_NY: observed 20.7%; uniform 12.2%; vol-shaped 17.4%; se 0.8 pts; +3.9 se -> beyond 2 SE
- low in NY_PM: observed 19.0%; uniform 30.3%; vol-shaped 28.3%; se 0.8 pts; -11.4 se -> beyond 2 SE
- high and low in the same block: observed 4.7%; uniform 1.7%; vol-shaped 1.5%; +7.2 se -> beyond 2 SE

### Block range as a share of the day's range, medians (Q2)
- SYDNEY: observed median 0.260; uniform 0.331; vol-shaped 0.252; se 0.004; +2.0 se -> WITHIN 2 SE OF CHANCE
- TOKYO: observed median 0.460; uniform 0.536; vol-shaped 0.465; se 0.005; -1.1 se -> WITHIN 2 SE OF CHANCE
- LONDON: observed median 0.571; uniform 0.446; vol-shaped 0.511; se 0.005; +12.8 se -> beyond 2 SE
- LDN_NY: observed median 0.535; uniform 0.396; vol-shaped 0.488; se 0.006; +7.6 se -> beyond 2 SE
- NY_PM: observed median 0.364; uniform 0.445; vol-shaped 0.409; se 0.004; -10.2 se -> beyond 2 SE

### Monday's day-start block holds the high (Q3 by weekday)
- Mon: high in SYDNEY 32.4% (N 466); vol-shaped all-days 18.0%; +6.6 se -> beyond 2 SE
- Tue: high in SYDNEY 18.1% (N 463); vol-shaped all-days 18.0%; +0.1 se -> WITHIN 2 SE OF CHANCE
- Wed: high in SYDNEY 16.1% (N 466); vol-shaped all-days 18.0%; -1.1 se -> WITHIN 2 SE OF CHANCE
- Thu: high in SYDNEY 15.5% (N 466); vol-shaped all-days 18.0%; -1.5 se -> WITHIN 2 SE OF CHANCE
- Fri: high in SYDNEY 15.9% (N 466); vol-shaped all-days 18.0%; -1.3 se -> WITHIN 2 SE OF CHANCE

## USED 2021-04-27 -> 2026-09-09: XAU_USD

Complete days scored: 1325 (simulated days per baseline: 6625, 6625)

### Hourly range profile (claims about busy and quiet hours)
- all hours mean 8.52; busiest hour 13:00 UTC mean 14.41 (se 0.33); quietest 21:00 UTC mean 5.07 (se 0.46); ratio 2.84
- chance baseline (no time-of-day effect): every hour equals the all-hours mean, ratio 1.00
- busiest hour minus all-hours mean: 17.6 se
- 12:00-15:00 UTC (04:00-07:00 PST) mean 13.45 vs other hours 7.78: difference 5.68 = 27.8 se (hours within a day are not independent; se is optimistic)
- hour means: 00 8.0, 01 10.9, 02 8.0, 03 6.3, 04 5.2, 05 7.9, 06 8.2, 07 8.3, 08 8.3, 09 7.5, 10 7.2, 11 7.9, 12 11.7, 13 14.4, 14 14.2, 15 11.9, 16 9.1, 17 7.8, 18 7.6, 19 7.1, 20 5.8, 21 5.1, 22 6.0, 23 6.5

### When the day's high and low are already set (Q4)
- high set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 23.4%; uniform 30.7%; vol-shaped 29.9%; se 1.2 pts; observed minus vol-shaped -6.5 pts (-5.6 se) -> beyond 2 SE
- high set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 36.0%; uniform 49.0%; vol-shaped 42.6%; se 1.3 pts; observed minus vol-shaped -6.6 pts (-5.0 se) -> beyond 2 SE
- high set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 67.0%; uniform 65.7%; vol-shaped 66.2%; se 1.3 pts; observed minus vol-shaped +0.8 pts (+0.6 se) -> WITHIN 2 SE OF CHANCE
- low set by 03:00 UTC (19:00 PST / 20:00 PDT): observed 27.7%; uniform 30.9%; vol-shaped 28.6%; se 1.2 pts; observed minus vol-shaped -0.9 pts (-0.7 se) -> WITHIN 2 SE OF CHANCE
- low set by 09:00 UTC (01:00 PST / 02:00 PDT): observed 42.7%; uniform 48.1%; vol-shaped 41.1%; se 1.4 pts; observed minus vol-shaped +1.6 pts (+1.2 se) -> WITHIN 2 SE OF CHANCE
- low set by 15:00 UTC (07:00 PST / 08:00 PDT): observed 73.1%; uniform 65.3%; vol-shaped 65.9%; se 1.2 pts; observed minus vol-shaped +7.3 pts (+6.0 se) -> beyond 2 SE
- analytic arcsine, uniform, 17 of 23 trading hours elapsed: 65.87%

### Where the day's high and low form, by block (Q3)
- high in SYDNEY: observed 9.4%; uniform 19.4%; vol-shaped 16.6%; se 0.8 pts; -9.1 se -> beyond 2 SE
- high in TOKYO: observed 21.1%; uniform 23.7%; vol-shaped 21.3%; se 1.1 pts; -0.2 se -> WITHIN 2 SE OF CHANCE
- high in LONDON: observed 12.5%; uniform 14.0%; vol-shaped 11.6%; se 0.9 pts; +0.9 se -> WITHIN 2 SE OF CHANCE
- high in LDN_NY: observed 32.0%; uniform 11.9%; vol-shaped 22.1%; se 1.3 pts; +7.7 se -> beyond 2 SE
- high in NY_PM: observed 25.1%; uniform 31.0%; vol-shaped 28.3%; se 1.2 pts; -2.7 se -> beyond 2 SE
- low in SYDNEY: observed 12.4%; uniform 19.0%; vol-shaped 15.2%; se 0.9 pts; -3.1 se -> beyond 2 SE
- low in TOKYO: observed 23.5%; uniform 23.7%; vol-shaped 21.5%; se 1.2 pts; +1.8 se -> WITHIN 2 SE OF CHANCE
- low in LONDON: observed 12.8%; uniform 14.0%; vol-shaped 11.2%; se 0.9 pts; +1.8 se -> WITHIN 2 SE OF CHANCE
- low in LDN_NY: observed 30.3%; uniform 12.4%; vol-shaped 24.1%; se 1.3 pts; +5.0 se -> beyond 2 SE
- low in NY_PM: observed 20.9%; uniform 30.9%; vol-shaped 28.0%; se 1.1 pts; -6.4 se -> beyond 2 SE
- high and low in the same block: observed 9.5%; uniform 1.8%; vol-shaped 2.2%; +9.0 se -> beyond 2 SE

### Block range as a share of the day's range, medians (Q2)
- SYDNEY: observed median 0.138; uniform 0.268; vol-shaped 0.215; se 0.003; -25.1 se -> beyond 2 SE
- TOKYO: observed median 0.443; uniform 0.550; vol-shaped 0.483; se 0.006; -6.6 se -> beyond 2 SE
- LONDON: observed median 0.396; uniform 0.460; vol-shaped 0.398; se 0.006; -0.3 se -> WITHIN 2 SE OF CHANCE
- LDN_NY: observed median 0.669; uniform 0.402; vol-shaped 0.589; se 0.008; +10.6 se -> beyond 2 SE
- NY_PM: observed median 0.359; uniform 0.456; vol-shaped 0.406; se 0.006; -7.8 se -> beyond 2 SE
```

## Appendix B: 2026 release reactions (verbatim, `studies/gold_2026_release_reactions.py`)

```
2026-04-03 NFP: no M5 candle at the release (market closed); not measured
| release | price at release | 30-min change | next close change | kept | H4 entry (PT) | entry | dir | P&L to 14:00 PT | P&L to 13:00 PT | weekend |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01-09 NFP | 4473.51 | +9.39 | +124.14 | kept | Fri 06:00 | 4482.90 | +1 | +114.75 | +111.03 | yes |
| 2026-01-13 CPI | 4600.94 | +10.62 | +25.63 | kept | Tue 06:00 | 4611.56 | +1 | +15.01 | +21.07 | no |
| 2026-01-28 FOMC | 5282.85 | +0.69 | +87.38 | kept | Wed 14:00 | 5418.55 | +1 | -48.32 | -24.38 | no |
| 2026-02-11 NFP | 5082.59 | -16.82 | -160.51 | kept | Wed 06:00 | 5065.77 | -1 | +143.69 | +150.65 | no |
| 2026-02-13 CPI | 4966.89 | +20.37 | +25.11 | kept | Fri 06:00 | 4987.26 | +1 | +4.74 | n/a | yes |
| 2026-03-06 NFP | 5083.19 | +1.93 | +54.72 | kept | Fri 06:00 | 5085.12 | +1 | +52.79 | +56.09 | yes |
| 2026-03-11 CPI | 5191.09 | -23.56 | -111.84 | kept | Wed 06:00 | 5167.53 | -1 | +88.27 | +82.55 | no |
| 2026-03-18 FOMC | 4891.05 | -5.37 | -240.33 | kept | Wed 14:00 | 4818.41 | -1 | +167.69 | +174.35 | no |
| 2026-04-10 CPI | 4762.94 | +8.98 | -22.60 | reversed | Fri 06:00 | 4771.92 | +1 | -31.58 | -30.64 | yes |
| 2026-04-29 FOMC | 4547.84 | -14.78 | +74.22 | reversed | Wed 14:00 | 4543.72 | -1 | -78.35 | -73.45 | no |
| 2026-05-08 NFP | 4710.42 | +14.06 | +25.03 | kept | Fri 06:00 | 4724.48 | +1 | +10.97 | +9.17 | yes |
| 2026-05-12 CPI | 4697.53 | +8.21 | -8.39 | reversed | Tue 06:00 | 4705.74 | +1 | -16.60 | -17.36 | no |
| 2026-06-05 NFP | 4465.76 | -59.15 | -135.69 | kept | Fri 06:00 | 4406.60 | -1 | +76.54 | +79.97 | yes |
| 2026-06-10 CPI | 4141.59 | +5.64 | +69.60 | kept | Wed 06:00 | 4147.23 | +1 | +63.96 | +61.68 | no |
| 2026-06-17 FOMC | 4379.51 | -86.65 | -170.51 | kept | Wed 14:00 | 4257.65 | -1 | +48.65 | +40.44 | no |
| 2026-07-02 NFP | 4064.49 | +53.09 | +111.20 | kept | Thu 06:00 | 4117.58 | +1 | +58.11 | n/a | no |
| 2026-07-14 CPI | 4030.18 | +46.05 | +30.52 | kept | Tue 06:00 | 4076.22 | +1 | -15.53 | -19.11 | no |
| 2026-07-29 FOMC | 4044.29 | +23.64 | +58.98 | kept | Wed 14:00 | 4066.34 | +1 | +36.93 | +45.72 | no |
| 2026-08-07 NFP | 4309.94 | +51.49 | +80.30 | kept | Fri 06:00 | 4361.43 | +1 | +28.81 | +27.13 | yes |
| 2026-08-12 CPI | 4427.57 | +9.80 | -76.30 | reversed | Wed 06:00 | 4437.37 | +1 | -86.10 | -87.11 | no |
| 2026-09-04 NFP | 4472.16 | -78.39 | -66.10 | kept | Fri 06:00 | 4393.77 | -1 | -12.29 | n/a | yes |
| 2026-09-11 CPI | 4341.35 | +47.21 | -41.82 | reversed | Fri 06:00 | 4388.56 | +1 | -89.03 | -104.84 | yes |
| 2026-09-16 FOMC | 4359.60 | -37.33 | -17.76 | kept | Wed 14:00 | 4263.85 | -1 | -77.99 | -82.35 | no |
| 2026-10-02 NFP | 4187.26 | +30.48 | -46.73 | reversed | Fri 06:00 | 4217.74 | +1 | -77.22 | -76.87 | yes |
| 2026-10-14 CPI | 4153.38 | -55.47 | +17.31 | reversed | Wed 06:00 | 4097.91 | -1 | -72.78 | -77.73 | no |
| 2026-10-28 FOMC | 4040.29 | -3.97 | -19.72 | kept | Wed 14:00 | 4067.29 | +1 | -46.72 | -44.43 | no |
| 2026-11-06 NFP | 4059.62 | -14.97 | +81.06 | reversed | Fri 06:00 | 4044.65 | -1 | -96.04 | -97.04 | yes |
| 2026-11-10 CPI | 4072.05 | -19.92 | -84.35 | kept | Tue 06:00 | 4052.13 | -1 | +64.43 | +66.86 | no |

- FOMC: N 7; 30-min direction kept to the next close 6
- CPI: N 11; 30-min direction kept to the next close 6
- NFP: N 10; 30-min direction kept to the next close 8
- all: N 28; kept 20

Post-release continuation (gross dollars, no costs):
- exit 14:00 PT (the rollover): pooled: N 28, mean $+8.10, t +0.58; same-week: N 17, mean $+14.38, t +0.76; weekend holds: N 11, mean $-1.60, t -0.08
- exit 13:00 PT: pooled: N 25, mean $+7.66, t +0.48; same-week: N 16, mean $+13.59, t +0.67; weekend holds: N 9, mean $-2.89, t -0.11

2026 sessions 2026-01-01 -> 2026-11-12: first open 4326.40, last close 3884.68, change -10.2%; high 5602.23, change from the high -30.7%; median daily range 2.21% of price (N 224)
```

## Appendix C: PRC-1 origin diagnostic (verbatim; five definitions)

```
A dir=H4close-p0, exit next close | pooled N 28 mean +8.10 t +0.58 | same-week N 17 mean +14.38 t +0.76 | weekend N 11 mean -1.60 t -0.08
B dir=H4 candle (close-open), exit next close | pooled N 28 mean -10.50 t -0.76 | same-week N 17 mean -10.05 t -0.52 | weekend N 11 mean -11.19 t -0.55
C dir=30min, entry H4 close, exit next close | pooled N 28 mean +11.44 t +0.82 | same-week N 17 mean +19.87 t +1.06 | weekend N 11 mean -1.60 t -0.08
D dir=H4close-p0, exit SAME session close | pooled N 28 mean -4.77 t -0.69 | same-week N 17 mean -8.94 t -1.72 | weekend N 11 mean +1.68 t +0.11
E dir=H4close-p0, entry+exit from p0 (pnl=dir*(next-p0)) | pooled N 28 mean +46.13 t +3.03 | same-week N 17 mean +57.21 t +2.74 | weekend N 11 mean +28.99 t +1.35
```

## Appendix D: spread by Pacific window (verbatim; run from a scratch copy that differs from `studies/gold_spread_windows.py` only in its import path)

```
M5 bid/ask candles: 12396, 2026-09-13 17:00 -> 2026-11-13 13:55 PT
mid-session 06:00-12:00 PT: n 3240; spread at close median 0.460, p90 0.600, max 7.170; at open median 0.460
12:00-13:00 PT: n 540; spread at close median 0.470, p90 0.590, max 0.850; at open median 0.460
13:00-14:00 PT: n 540; spread at close median 0.520, p90 0.690, max 3.460; at open median 0.510
  13:00-13:30 PT: n 270; spread at close median 0.490, p90 0.640, max 0.780; at open median 0.490
  13:30-13:55 PT: n 270; spread at close median 0.540, p90 0.770, max 3.460; at open median 0.520
  the 12:55 candle (closes 13:00 PT): n 45; spread at close median 0.480, p90 0.620, max 0.790; at open median 0.470
  the 13:55 candle (closes 14:00 PT): n 45; spread at close median 0.660, p90 1.536, max 3.460; at open median 0.590
14:00-15:00 PT: no candles
15:00-16:00 PT (reopen): n 528; spread at close median 0.590, p90 0.800, max 1.400; at open median 0.600
hour 00 PT: n 540 median 0.460
hour 01 PT: n 540 median 0.450
hour 02 PT: n 540 median 0.460
hour 03 PT: n 540 median 0.450
hour 04 PT: n 540 median 0.460
hour 05 PT: n 540 median 0.470
hour 06 PT: n 540 median 0.480
hour 07 PT: n 540 median 0.490
hour 08 PT: n 540 median 0.470
hour 09 PT: n 540 median 0.440
hour 10 PT: n 540 median 0.440
hour 11 PT: n 540 median 0.460
hour 12 PT: n 540 median 0.470
hour 13 PT: n 540 median 0.520
hour 15 PT: n 528 median 0.590
hour 16 PT: n 528 median 0.540
hour 17 PT: n 540 median 0.520
hour 18 PT: n 540 median 0.510
hour 19 PT: n 540 median 0.490
hour 20 PT: n 540 median 0.485
hour 21 PT: n 540 median 0.500
hour 22 PT: n 540 median 0.490
hour 23 PT: n 540 median 0.460
```


## Addendum: owner rulings applied (2026-11-16)

| Ruling | What was done | Result | Label |
|---|---|---|---|
| R1 R37 re-cost | `studies/first_pullback_recost_r37.py`: the frozen runner's code, with timed exits that close exactly on the 17:00 New York roll no longer charged that night (stopped trades keep the original count: the stop is hit inside the bar, after the roll at its open). Positive control: the original costing reproduces R37 exactly (MATCH, both cells) or the script stops | 38.2%: 6 of 36 episodes' nights fell; upper bound **+0.140R** (unchanged to 3 dp), mean −0.011R, median −0.082 → −0.081R: **still REFUTED**. 50%: 3 of 30 changed; still INCONCLUSIVE. Dated amendment added to R37's row; original figures kept | VERIFIED (control matched; the change applied to 9 episodes) |
| R1 distances | R38, R43, R44, R46 checked against their thresholds (table below) | nearest is R38 38.2% at 0.116R from the +0.15R bar; none within 0.03R, so none re-costed | OBSERVED (from the committed figures) |
| R2 UNINFORMATIVE | label added to `foundation/research_findings.md` (definition and a table of the ten claims with baselines), `foundation/README.md`, the skill source; applied beside each claim in `studies/gold_session_report.md`, `studies/session_movement_report.md`, the inventory and the sweep | gold high-by-7 AM; GBP 03:00 lows (both pairs); GBP/AUD 09:00 lows; 6 of 20 block cells. The GBP/JPY Sydney and Tokyo block-share medians, also within chance, are output figures rather than report claims; labelled in the sweep only | VERIFIED (text) |
| R3 withdrawn | PRC-1 §1: the owner's figures marked withdrawn, with the cause | **Cause checked:** pricing Fed entries at the 30-minute price on the 2026 candles gives same-week +$34.73 (t 1.71), all +$20.46 (t 1.37), Fed 58.9% of the same-week total, matching the withdrawn figures. Origin now from candles only | VERIFIED |
| R4 Fed entry | PRC-1 §4: Fed entry at the 1:00 PM PT hourly close on decision day, exit 1:00 PM PT next session; no other spec used the 2:00 PM entry (GNC-1 enters 30 minutes after the release; GMW-1 has no Fed trades) | see conflict (c) below on "one financing night" | VERIFIED (text) |
| R5 regime | PRC-1 §2 and this report: −10.2% YTD, −30.7% from the high, 2.21% median daily range; two regimes | the rise into late January measured **+25.2%** to the highest close (Jan 28) and +29.5% to the intraday high (Jan 29), not "roughly 23%"; the measured figures are used | OBSERVED (OANDA daily candles) |
| R6 family | GMW-1 §4.1, GNC-1 §5, PRC-1 §6: six tests named; α = 1 − 0.95^(1/6) = 0.0085 (z 2.386) | B at N 1,900, SD 1.2: SUPPORTED above +0.116R, REFUTED below +0.015R; power and boundary tables recomputed | VERIFIED (text; `power_check` arithmetic) |
| R7 B only | GNC-1 and PRC-1: no SUPPORTED verdict; REFUTED by the futility standard (90% upper bound < +0.15R); the required sentence at the top | see conflict (a) | VERIFIED (text) |
| R8 | no change | — | — |
| R9 | 2a07814 kept; the branch is to be squashed on merge | not merged yet | PENDING (owner's go to merge) |
| R10 | candidate question recorded in the sweep and `docs/gold_plan.md` §0; not specced | see conflict (b) | VERIFIED (text) |

**Distance from threshold (R1):**

| Cell | Verdict | Lower | Upper (90%) | Upper − 0.15 | 0 − lower | Nearest | Re-cost? |
|---|---|---|---|---|---|---|---|
| R38 38.2% | INCONCLUSIVE | −0.250 | +0.266 | +0.116 | 0.250 | 0.116 | no |
| R38 50% | INCONCLUSIVE | −0.361 | +0.383 | +0.233 | 0.361 | 0.233 | no |
| R43 A | REFUTED | | −0.114 | −0.264 | — | 0.264 | no |
| R43 B | REFUTED | | −0.058 | −0.208 | — | 0.208 | no |
| R43 C | REFUTED | | −0.020 | −0.170 | — | 0.170 | no |
| R44 B-1.5 | REFUTED | | −0.184 | −0.334 | — | 0.334 | no |
| R44 B-2.5 | REFUTED | | −0.171 | −0.321 | — | 0.321 | no |
| R44 C-1.5 | REFUTED | | −0.113 | −0.263 | — | 0.263 | no |
| R44 C-2.5 | REFUTED | | −0.096 | −0.246 | — | 0.246 | no |
| R46 H1 | REFUTED | | −0.056 | −0.206 | — | 0.206 | no |
| R46 HTF-1.5 | REFUTED | | −0.215 | −0.365 | — | 0.365 | no |
| R46 HTF-2.5 | REFUTED | | −0.128 | −0.278 | — | 0.278 | no |

**Conflicts found while applying the rulings (reported, not resolved):**
- (a) **R7's sentence and the verdict set.** "This test can return REFUTED or
  INSUFFICIENT only" omits the third outcome: N ≥ 20 with the upper bound at or
  above +0.15R. The specs print the sentence as given and add that such a
  result is INCONCLUSIVE (not refuted; confirms nothing).
- (a2) **R6 and R7 together.** R6 counts a test in the family if it can
  produce a pass worth acting on; R7 removes SUPPORTED from GNC-1 and PRC-1,
  so by R6's own reasoning they could not produce a false pass, and the family
  would be GMW-1's two cells (α 0.0253). The specs use six (α 0.0085) as
  ruled, which is the stricter reading for GMW-1.
- (b) **R10's framing.** The 73% / 67% asymmetry was measured on 2021-04 →
  2026-09, a span in which gold mostly rose, not in a falling year. Recorded
  with that scope note.
- (c) **R4's "exactly one financing night".** A Fed trade holds one 17:00 New
  York roll, but most FOMC decisions are on Wednesdays, and the framework
  charges the Wednesday roll as 3 nights. PRC-1 states this and asks the owner
  to confirm the convention.
- (d) **R5's "roughly 23%".** Measured +25.2% (close) / +29.5% (high); the
  measured figures are used.

### Appendix E: R37 re-costing output (verbatim)

```
# R37 re-costing (owner ruling R1, 2026-11-16)

## GBP/AUD 38.2%
- original costing (positive control): N 36; mean -0.011R; median -0.082R; lower -0.269R; upper (90%) +0.140R; without best -0.057R; verdict REFUTED
  control vs committed R37 {'n': 36, 'mean': -0.011, 'median': -0.082, 'lower': -0.269, 'upper': 0.14}: MATCH
## GBP/AUD 50.0%
- original costing (positive control): N 30; mean +0.017R; median -0.220R; lower -0.384R; upper (90%) +0.276R; without best -0.088R; verdict INCONCLUSIVE
  control vs committed R37 {'n': 30, 'mean': 0.017, 'median': -0.22, 'lower': -0.384, 'upper': 0.276}: MATCH

## GBP/AUD 38.2%, corrected boundary
- re-costed: N 36; mean -0.011R; median -0.081R; lower -0.269R; upper (90%) +0.140R; without best -0.056R; verdict REFUTED
  episodes whose night count changed: 6 of 36; 2006-11-29 10->7, 2007-05-09 10->7, 2008-07-07 8->7, 2009-06-05 8->7, 2009-11-12 8->7, 2011-08-09 8->7

## GBP/AUD 50.0%, corrected boundary
- re-costed: N 30; mean +0.017R; median -0.221R; lower -0.384R; upper (90%) +0.276R; without best -0.087R; verdict INCONCLUSIVE
  episodes whose night count changed: 3 of 30; 2006-11-23 8->7, 2008-09-02 8->7, 2009-02-10 8->7
```


## Addendum 2: round-2 rulings applied (2026-11-16)

| Ruling | Done | Label |
|---|---|---|
| A1 | INCONCLUSIVE named as a verdict in GNC-1 and PRC-1; their top sentences now list REFUTED, INCONCLUSIVE, INSUFFICIENT | VERIFIED (text) |
| A2 | Family = GMW-1 B1 and B2, α = 1 − 0.95^(1/2) = 0.0253 (z 1.955). GMW-1 at N 1,900, SD 1.2: SUPPORTED above +0.104R, REFUTED below +0.015R; power at +0.15R 91% (SD 2.0), 59% (SD 3.0). REFUTED recorded as deliberately uncorrected, with the reason. GNC-1 and PRC-1 state they are outside the family | VERIFIED (text; `power_check` arithmetic) |
| A3 | The R10 question downgraded to low priority in `docs/gold_plan.md` and the sweep, with the drift explanation and "test against a drift-matched baseline first" | VERIFIED (text) |
| A4 | PRC-1: the Wednesday triple confirmed, not special-cased; Fed financing reported separately | VERIFIED (text) |
| A5 | +25.2% / +29.5% already in use (round 1) | VERIFIED |
| A6 | squash-merge, citation fix-up commit, push | see the final report |
| A7 | GNC-1: C-FOMC INSUFFICIENT by declaration (19 meetings with a time, 44 without); the run covers C-NFP and C-CPI. Running C still waits for the owner's sign-off, the M15 fetch and check, and P2 | VERIFIED (text); run PENDING |
| A8 | Measured effect in PRC-1's own R unit (below); reported in PRC-1 §11; family unchanged | OBSERVED |
| A9 | PRC-1 top note: the rule as specified has never been measured on any data | VERIFIED (text) |

**A8 result.** PRC-1 has no stop; its R unit is 0.5 × the 14-session daily
ATR before each event (median $50.29 across the 28 events). The round-2 note's
0.15 / 0.30 × median-range stops are not this spec's basis. In PRC-1's unit:
- candle origin (Fed at the 2:00 PM PT close), same-week: **+0.044R** gross,
  +0.024R after a $1 spread, SD 1.384R, effect 0.032 SD;
- withdrawn pricing, same-week: +0.460R, 0.318 SD (reference only).

At N ≈ 87 and the three-test α 0.0170, PRC-1 confirms with 80% power only an
effect of 0.318 SD (about +0.44R at SD 1.4R). The candle-measured effect is
about one tenth of that (power about 3%). PRC-1 can return SUPPORTED in
principle, for a large edge; no measured version of the rule shows one. Whether
it regains SUPPORTED, and rejoins the family, is the owner's call. The owner's
round-2 α for three tests (0.0171) is close to but not the Šidák value
(0.0170); Bonferroni gives 0.0167.

### Appendix F: A8 computation (code and output, verbatim)

Inputs: `events.json` (per-event ATR from the playbook measurement run, OANDA
daily candles; the 14 sessions completed before each event) and the verbatim
output of `studies/gold_2026_release_reactions.py` (Appendix B).

```python
"""Ruling A8: PRC-1's 2026 effect in its own R unit (0.5 x the 14-session daily ATR
before each event). Inputs: the per-event ATR from the playbook measurement run
(events.json, OANDA daily candles) and the per-trade P&L printed by
studies/gold_2026_release_reactions.py (its verbatim output)."""
import json, sys, math, statistics as st
from statistics import NormalDist
ev_json, rr_out = sys.argv[1], sys.argv[2]
name = {"FOMC decision": "FOMC", "CPI": "CPI", "Jobs report": "NFP"}
atr = {(name[x["event"]], x["date"]): x["atr"] for x in json.load(open(ev_json)) if "error" not in x}
def sgn(v): return (v > 0) - (v < 0)
recs = []
for l in open(rr_out):
    if not l.startswith("| 2026"):
        continue
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    d, e = c[0].split(); unit = 0.5 * atr[(e, d)]
    c30, nxt, p14 = float(c[2]), float(c[3]), float(c[8])
    p13 = None if c[9] == "n/a" else float(c[9])
    pw = sgn(c30) * (nxt - c30) if e == "FOMC" else p14
    recs.append(dict(unit=unit, atr=atr[(e, d)], wk=c[10] == "yes", R14=p14 / unit,
                     R13=None if p13 is None else p13 / unit, Rw=pw / unit, cost=1.0 / unit))
print(f"events {len(recs)}; median ATR ${st.median(r['atr'] for r in recs):.2f}; median unit ${st.median(r['unit'] for r in recs):.2f}")
for lab, key in (("2 PM Fed entry, exit 14:00 PT", "R14"), ("2 PM Fed entry, exit 13:00 PT", "R13"), ("withdrawn pricing, exit 14:00 PT", "Rw")):
    for grp, f in (("same-week", lambda r: not r["wk"]), ("weekend", lambda r: r["wk"]), ("all", lambda r: True)):
        xs = [r[key] for r in recs if f(r) and r[key] is not None]
        net = [r[key] - r["cost"] for r in recs if f(r) and r[key] is not None]
        m, sd = st.fmean(xs), st.stdev(xs)
        print(f"{lab} | {grp}: N {len(xs)} mean {m:+.3f}R after $1 {st.fmean(net):+.3f}R SD {sd:.3f}R t {m / (sd / math.sqrt(len(xs))):+.2f} d {m / sd:+.3f}")
for lab, a in (("Sidak 3", 1 - 0.95 ** (1 / 3)), ("Sidak 2", 1 - 0.95 ** 0.5)):
    za = NormalDist().inv_cdf(1 - a); dreq = (za + NormalDist().inv_cdf(0.8)) / math.sqrt(87)
    print(f"{lab}: alpha {a:.5f}; d needed at N 87 for 80% power {dreq:.3f}; power at d 0.032 {NormalDist().cdf(0.032 * math.sqrt(87) - za):.3f}, at 0.18 {NormalDist().cdf(0.18 * math.sqrt(87) - za):.2f}, at 0.30 {NormalDist().cdf(0.30 * math.sqrt(87) - za):.2f}")
```

```
events 28; median ATR $100.59; median unit $50.29
2 PM Fed entry, exit 14:00 PT | same-week: N 17 mean +0.044R after $1 +0.024R SD 1.384R t +0.13 d +0.032
2 PM Fed entry, exit 14:00 PT | weekend: N 11 mean -0.064R after $1 -0.082R SD 1.463R t -0.14 d -0.044
2 PM Fed entry, exit 14:00 PT | all: N 28 mean +0.002R after $1 -0.018R SD 1.389R t +0.01 d +0.001
2 PM Fed entry, exit 13:00 PT | same-week: N 16 mean +0.019R after $1 -0.001R SD 1.416R t +0.05 d +0.014
2 PM Fed entry, exit 13:00 PT | weekend: N 9 mean -0.095R after $1 -0.115R SD 1.671R t -0.17 d -0.057
2 PM Fed entry, exit 13:00 PT | all: N 25 mean -0.022R after $1 -0.042R SD 1.479R t -0.07 d -0.015
withdrawn pricing, exit 14:00 PT | same-week: N 17 mean +0.460R after $1 +0.440R SD 1.446R t +1.31 d +0.318
withdrawn pricing, exit 14:00 PT | weekend: N 11 mean -0.064R after $1 -0.082R SD 1.463R t -0.14 d -0.044
withdrawn pricing, exit 14:00 PT | all: N 28 mean +0.254R after $1 +0.235R SD 1.449R t +0.93 d +0.176
Sidak 3: alpha 0.01695; d needed at N 87 for 80% power 0.318; power at d 0.032 0.034, at 0.18 0.33, at 0.30 0.75
Sidak 2: alpha 0.02532; d needed at N 87 for 80% power 0.300; power at d 0.032 0.049, at 0.18 0.39, at 0.30 0.80
```
