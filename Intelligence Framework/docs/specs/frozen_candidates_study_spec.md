# Spec: the frozen shadow candidates on the 2005–2013 STUDY data (pre-registered)

**Status:** pre-registered 2026-11-04 at the owner's request ("start with 1
and 2": item 2 was "pre-register a test for joining momentum on 2005–2013
data, with costs"). This is the STUDY's named purpose in
`data_map_spec.md` §8 (team amendment 2026-09-11): the three frozen
candidates, each its own question, parameters byte-identical, graded by the
live grading rule. This file, the runner (`studies/frozen_candidates_study.py`)
and its suite test (`tests/test_frozen_candidates_selftest.py`) are committed
together, with their sha256 and the data files' sha256 in validation_log in
the same commit. **No 2005–2013 fire or outcome of any candidate has been
computed.** The counts stage (`data_map_spec` §9: fires and episodes only, no
R) runs after this commit and is logged before the full run. The full run
happens once, and its output goes to validation_log verbatim.

Study id: **FCS-1**.

## 1. Why, and the question

The missed-move report (`studies/missed_moves_report.md`) found the framework
traded with 1 of 20 large moves since July 2026. Large moves are momentum
expansions that can be joined but not predicted (R9). The three shadow
candidates are the framework's rules for joining them. They have 1–3 graded
forward episodes each, and the forward ledger reaches a decision only around
2028–30 (R31). This study asks, for each candidate on each pair:

> Traded on every 4-hour bar as frozen, graded by the live rule, after era
> spread and financing, does the candidate earn a positive average R on
> 2005–2013 data it was not designed on?

Per `data_map_spec` §5 the claim any answer supports is **"does this survive
conditions it wasn't designed on"**, never "does this work now".

## 2. Prior work

| Finding | What it showed | How this differs |
|---|---|---|
| R30 (audit, 2026-09-29) | In-sample replay on the 2023–26 cache, 3-pip cost: no candidate/pair cell shows an edge; MOMENTUM_JOIN GBP/JPY +0.48R, N=23, outlier-driven | The candidates were designed on that data. This is 9 years they never saw, with era costs and financing |
| R17 (2026-09-11) | THRUST_PULLBACK GBP/AUD walk-forward: 22 episodes, −0.10R, no spread | THRUST_PULLBACK was selected from an in-sample grid (R10). This is its first test outside that window |
| R16, R29, `candidates.md` | Forward ledger: 1–3 graded episodes per candidate | Forward N stays the only evidence about the present (§12) |

## 3. Data

- The files fetched and hashed for the US-event study:
  `~/intel_study_archives/us_event_reaction_data/{GBP_AUD,GBP_JPY}_{D,H4}.csv`,
  sha256 pinned in the runner (the same four values as
  `studies/first_pullback_study.py`). A differing hash refuses the run.
- Converted with the approved weekend rule (`studies/history_study_convert.py`),
  exactly as the first pullback study.
- STUDY span only: trading days 2005-01-01 → 2013-12-30
  (`data_map_spec` §11.2). Any bar outside it refuses the run. The SEALED
  EXAM is not touched.
- D1 bars are used only for the trading-day calendar of the financing count.

## 4. The rule: the live code, called unmodified

- **Context.** At each converted H4 bar i with i ≥ 299, the context is built
  exactly as `shadow_signals._load_ctx` builds it from a 300-bar fetch: the
  300 bars ending at bar i, `compute_atr_series`, `_compute_adx` now and
  without the last 12 bars, `_detect_structure`, the pair's pip size. The
  runner uses the functions imported from `shadow_signals` /
  `regime_detection`, and the self-test proves its context equals
  `_load_ctx`'s on the same bars, field for field.
- **Candidates.** Each function in `shadow_signals._CANDIDATES`, the live
  candidate list, is called on every such bar with that context, in the live
  order. Nothing is re-implemented. Two differences from the live entry point
  `check_shadow_signals`, both outside the candidates' rules: a candidate
  error aborts the run (live prints an alert and carries on), and the
  news-window stamp is not added (it reads today's calendar, and the news
  gate is outside the STUDY's scope, `data_map_spec` §8; it never affects a
  grade). The self-test proves the fires match `check_shadow_signals` on
  every bar of a synthetic series.
- **Cadence: every bar.** The live harness checks only the bar that is latest
  when a brief runs, about two-thirds of bars (`candidates.md`, AUDIT §2 #4;
  changing that is the team's item). This study measures the rule, not the
  live schedule.
- **Invalid rows** (`shadow_signals.is_invalid_spec`: stop on the wrong side
  of entry) are dropped, as the live tally drops them.
- **Cells (5):** MOMENTUM_JOIN × {GBP_AUD, GBP_JPY}, THRUST_PULLBACK ×
  {GBP_AUD, GBP_JPY}, EARLY_MOMENTUM_v2 × GBP_JPY (it never fires on
  GBP/AUD). Long and short are pooled per cell, as live.

## 5. Grading: the live rule

As `shadow_signals.grade_pending_shadow`, with the same arithmetic:

- Entry = the fire bar's close; stop = the candidate's stop; risk =
  |entry − stop|.
- Bars i+1 … i+30: if any bar's low (long) or high (short) touches the stop,
  R = −1.0.
- Otherwise R = (close of bar i+30 − entry) / risk, signed for the side.
- A fire with fewer than 30 bars after it before the data ends is ungraded
  and not counted.

The self-test proves equality with `grade_pending_shadow` itself, run on a
temporary ledger.

## 6. Costs (primary)

Primary R = live R − era spread / risk + financing / risk.

- **Era spread**, round trip (`data_map_spec` §4, frozen): GBP_AUD 10 pips
  2005–2009, 7 pips 2010–2013; GBP_JPY 6 / 5.
- **Financing**: the first pullback study's `financed()`, unchanged: policy
  rates from `studies/policy_rates_2003_2014.json`, rate gap minus a 1%
  markup a year, rollover nights from entry (the open of bar i+1) to exit (the
  open of the stop bar, or the close of bar i+30), Wednesday counted three
  times.

## 7. Episodes

Per cell, on the pair's converted bar index: the first graded fire starts an
episode; a fire starts a new one only 30 or more bars after the current
episode's first fire (`shadow_signals.graded_episodes`,
`foundation/tools/episodes.py`). The episode's R is its first fire's R.
Same-bar ties cannot occur within a cell (one fire per candidate per bar).

## 8. Verdict per cell (decided now)

- **INSUFFICIENT:** N < 20 episodes.
- **SUPPORTED:** the one-sided bootstrap lower bound on mean primary R, at
  99% (Bonferroni: 0.05 / 5 cells), is above 0 **and** the mean without the
  single best episode is above 0.
- **REFUTED:** the one-sided 90% bootstrap upper bound is below +0.15R (the
  smallest edge worth trading, as in the futility rule).
- **INCONCLUSIVE:** anything else.

Bootstrap: `foundation/tools/power_check`, 20,000 resamples, seed 7.

**What a verdict does:**
- SUPPORTED: the candidate may be proposed to the team for its one-shot
  SEALED EXAM opening (`data_map_spec` §7, §8). Only the team opens it.
- REFUTED: reported to the team as evidence on that cell. The candidates are
  frozen and live; retiring one is the team's decision, not this study's.
  The live futility checkpoint is unaffected.
- INCONCLUSIVE / INSUFFICIENT: nothing changes.

## 9. Power (stated before the run)

SD 1.2R assumed, one-sided α 0.01:

| Episodes N | Power for +0.15R | Smallest edge detectable at 80% |
|---|---|---|
| 40 | 6% | +0.60R |
| 80 | 11% | +0.43R |
| 150 | 21% | +0.31R |
| 250 | 36% | +0.24R |

N required for +0.15R at 80% power: 643. **SUPPORTED needs a large edge at
any N this data can give.** REFUTED is reachable: it needs the 90% upper
bound under +0.15R.

## 10. The counts stage (`data_map_spec` §9)

Printed before any R: per cell, fires, invalid fires dropped, graded fires,
ungraded at data end, episodes (long / short), episodes per year, and the
`data_map_spec` §1 exam-split flag (≥ 8 episodes a year). Logged and
committed before the full run. The full run then covers all five cells; a
cell under 20 episodes is reported INSUFFICIENT. Per §9, a cell near 25
episodes means "too selective to validate on history" for that cell, and is
recorded as such.

## 11. Secondary analyses (reported; never change a verdict)

- Before costs (the live rule's R alone).
- Flat 3.0-pip spread (present-day cost) plus financing.
- Stops filled at the stop bar's open when it gapped through the stop.
- Long and short episodes separately.
- Three sub-periods: 2005-01 → 2008-06, 2008-07 → 2009-06, 2009-07 → 2013-12.
- By year.
- Financing markup 0% and 2%.
- Median winner and median loser R; share stopped.

## 12. Run discipline

1. **`selftest`** must print `SELFTEST OK`. On synthetic bars stamped on the
   real H4 calendar, it checks:
   - the context equals `_load_ctx`'s (feed patched), field for field;
   - the replay's fires equal `check_shadow_signals` driven through
     `_load_ctx` bar by bar, and each candidate fires at least once (so the
     equality is not vacuous);
   - grades equal `grade_pending_shadow` on a temporary ledger (R to 2
     decimals, stop flag), and episodes equal `graded_episodes` on it;
   - a hand-computed timed exit, a stop on bar i+30, no stop check on the
     fire bar, a short;
   - era spread and a financing number against hand arithmetic;
   - the verdict boundaries with the Bonferroni level actually applied;
   - the window, data-hash and report-exists refusals.
2. **Mutation-tested** (at least 8 mutants, each reported caught or survived)
   before the pre-registration commit.
3. **Commit** this spec, the runner and the suite test, with sha256s in
   validation_log. That is the pre-registration.
4. **`counts`** through `scripts/reality_run.py --no-env`. Logged and
   committed before `full`.
5. **`full`** once. It refuses if the report exists or a data hash differs.
   Output verbatim to validation_log and `studies/frozen_candidates_study_result.md`;
   each cell's verdict into `foundation/research_findings.md`.
6. **Any change** after step 3 is a new pre-registration with a new id.

## 13. Limits, stated now

- **Mid prices; H4 resolution.** Inside a bar the order of events is unknown.
  The live rule ignores it too (a touch is a stop).
- **The live schedule is not modelled** (§4). If the team changes it, this
  result describes the new schedule better than the old.
- **Financing at the entry-day rate**, as in the first pullback study.
- **Old era:** the 2008 crisis and the start of zero rates. A pass would
  still need the sealed exam and the forward ledger.
- **Data already seen by other studies** (US events, carry, first pullback),
  never by these candidates. The candidates were designed on 2023–26 data.
