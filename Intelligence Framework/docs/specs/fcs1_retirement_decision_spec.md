# Decision paper: which shadow candidates should keep running after FCS-1

**Status:** PROPOSED 2026-11-05. **This is a decision for the team, not a build.**
Nothing is retired by this file. If the team decides to retire anything, the
code change gets its own build spec and review, because `shadow_signals.py` is
protected.

**Why now (owner, 2026-11-05):** "Retirement — it's a decision, not a build,
and it changes the other two." It comes before two pieces of work that depend
on it:
- the revised shadow-to-digest spec, whose content changes if EARLY_MOMENTUM_v2 stops;
- the shadow-block wording (display inventory item 8).

The owner also asked whether "refuted on 2005–2013" was a pre-registered run or
an in-sample look. If it was pre-registered, "the question isn't how to word
the shadow block — it's whether these three should still be running at all."

## 1. The question for the team

For each of the five candidate/pair cells, should it **keep running** in the
live shadow harness, or **retire**? A second question covers what "retire"
does mechanically (§7).

## 2. What FCS-1 was

FCS-1 was a **pre-registered run with honest N, not an in-sample look.**
- **Pre-registered first.** The spec, runner, suite test and data hashes were
  committed (81f25bb) before any 2005–2013 fire or outcome had been computed.
- **Counts before results.** Fires and episodes were logged and committed
  (af004a3) before the single full run (`data_map_spec` §9).
- **Byte-identical rules and grading.** The candidates are the live functions,
  called unmodified, and graded by the live rule.
- **Costs.** Era spread and period financing were applied.
- **Independent episodes.** Episodes do not overlap: a 30-bar horizon on the
  bar index.
- **Verdict rule fixed in advance:**
  - SUPPORTED needs a Bonferroni-corrected lower bound above 0;
  - REFUTED needs the 90% upper bound below +0.15R;
  - anything else is INCONCLUSIVE.
- **Never seen before.** The candidates were designed on 2023–26 data. None
  of them had been run on this span.

Result (`studies/frozen_candidates_study_result.md`, R40–R42):

| Cell | Episodes | Mean R | Median R | 90% upper bound | Verdict |
|---|---|---|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | 246 | −0.099 | −1.019 | +0.042 | **REFUTED** |
| THRUST_PULLBACK GBP/AUD | 51 | −0.130 | −0.163 | +0.035 | **REFUTED** |
| MOMENTUM_JOIN GBP/AUD | 98 | −0.095 | −1.060 | +0.117 | **REFUTED** |
| MOMENTUM_JOIN GBP/JPY | 96 | −0.012 | −1.042 | +0.222 | INCONCLUSIVE |
| THRUST_PULLBACK GBP/JPY | 39 | +0.056 | −0.256 | +0.312 | INCONCLUSIVE |

EARLY_MOMENTUM_v2 has no GBP/AUD cell: by its spec it is GBP/JPY only.

**Correction (2026-11-05).** The display-claim inventory (validation_log
2026-11-05, item 8) says "all three refuted in history". **That is wrong.**
Three of five cells were refuted. Each candidate other than EARLY_MOMENTUM_v2
has one refuted cell and one inconclusive cell.

**What the study's own spec says a REFUTED verdict does** (§8): "reported to
the team as evidence on that cell. The candidates are frozen and live;
retiring one is the team's decision, not this study's." That is why this paper
exists.

## 3. How solid each refutation is (new, post-hoc; never changes a verdict)

The checks below were chosen **after** the verdicts were known. They are
reported to inform the decision, never to change a verdict. Method:
- recompute each cell's episodes with the study's own functions;
- take the 90% upper bound under other cost assumptions, and a family-corrected bound.

Run read-only through `scripts/reality_run.py --no-env`, which reported the
project unchanged by hash. Script:
`/private/tmp/claude-501/-Users-quis-Intelligence-Framework/cb7308f6-2c1b-4e2b-8502-e98d9c7a79b6/scratchpad/retire/sens.py`.
**Control:** the "pre-registered" column reproduces the published bounds
exactly in all five cells.

Upper bound on mean R under each assumption; below +0.15R means "refuted
under that assumption".

| Cell | Pre-registered (era spread, 90%) | Family-corrected (era spread, 98% = 0.10/5) | Today's spread (flat 3 pips, 90%) | No costs at all (90%) |
|---|---|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | +0.042 | +0.134 | +0.077 | +0.128 |
| THRUST_PULLBACK GBP/AUD | +0.035 | +0.140 | +0.060 | +0.088 |
| MOMENTUM_JOIN GBP/AUD | +0.117 | **+0.251** | **+0.166** | **+0.209** |
| MOMENTUM_JOIN GBP/JPY | +0.222 | +0.374 | +0.247 | +0.277 |
| THRUST_PULLBACK GBP/JPY | +0.312 | +0.479 | +0.325 | +0.371 |

What this shows:
- **EARLY_MOMENTUM_v2 and THRUST_PULLBACK GBP/AUD stay refuted under every
  assumption.** That includes zero costs and a correction for testing five
  cells. Their refutation is robust.
- **MOMENTUM_JOIN GBP/AUD's refutation is fragile.**
  - It holds only with the 2005–2013 spread, which was 10 pips until 2009 and
    7 after, against about 3 today.
  - It holds only at the uncorrected per-cell level.
  - At today's spread its upper bound is +0.166: an edge of +0.15R is not
    ruled out.
- **Why the correction column matters.** The pre-registered REFUTED rule is
  per cell, with no correction for five cells. If every cell truly had +0.15R,
  the chance that at least one would be wrongly refuted is roughly
  1 − 0.9⁵ ≈ 41% (approximate: the cells are not independent).

## 4. The forward ledger today (read-only, 2026-11-05)

Counted by `shadow_signals.get_shadow_tally` on a copy of
`shadow_signal_log.csv` through `reality_run.py`:

| Cell | Rows logged | Graded | Independent episodes (first-fire R) |
|---|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | 24 | 20 | 4: −0.55, −0.39, +0.34, −1.00 |
| MOMENTUM_JOIN GBP/AUD | 5 | 5 | 1: −1.00 |
| MOMENTUM_JOIN GBP/JPY | 2 | 2 | 1: −1.00 |
| THRUST_PULLBACK GBP/JPY | 2 | 2 | 2: −0.33, +1.94 |
| THRUST_PULLBACK GBP/AUD | 0 | 0 | none (it has never fired live) |

The other 3 rows are EARLY_MOMENTUM v1, retired 2026-09-09 for a stop defect,
and stay out of every tally.

**What reaches the owner.** EARLY_MOMENTUM_v2 is 24 of the 36 ledger rows, and
12 of the 15 since 2026-10-01.

**Correction (2026-11-05).** In conversation I said the two GBP/JPY cells that
would stay running were "most of what's been pinging you". That was wrong:
they are 3 of the 15 rows since October.

**What forward evidence can decide, and when:**
- The futility checkpoint (`futility_rule_spec.md`) fires once, at 20 pooled
  episodes per candidate.
- EARLY_MOMENTUM_v2 has 4 episodes in seven weeks. At that rate it reaches 20
  in roughly six months.
- Even then, the forward ledger can only refute a clear loser (futility spec,
  "Known limit").
- At N=20 the bound sits roughly 0.3–0.4R above the observed mean. FCS-1's
  246 episodes already put EARLY_MOMENTUM_v2's upper bound at +0.04R.

## 5. What the study cannot say

- **Era.** 2005–2013 includes the 2008 crisis and the start of zero rates. The
  claim it supports is "does this survive conditions it wasn't designed on",
  never "does this work now" (`data_map_spec` §5). The forward ledger is the
  only evidence about the present, and it is slow (§4).
- **Cadence.**
  - The study checked every 4-hour bar. The live harness checks only the bar
    that is latest when a brief runs, about two-thirds of bars (the owner's
    item 3, left for the team).
  - The study measures the rule, not the live schedule.
  - A candidate that fails on every bar would need its edge concentrated in
    the bars the live schedule happens to see. No mechanism for that is known.
- **Mid prices, 4-hour resolution.** The same limitation as the live grader.

## 6. Costs of each choice

The candidates are shadow-only: nothing trades on them. **Retiring a candidate
costs no trades.**

| | If we keep a refuted cell running | If we retire a cell that actually works today |
|---|---|---|
| What it costs | Pings: EARLY_MOMENTUM_v2 is most of them. A shadow block reading "evidence accumulating" for a rule history refuted. A futility clock that runs about six more months to tell us less than FCS-1 already did | The candidate's forward record stops |
| Can it be undone? | — | Yes. The sealed 2014–2021 exam is still unopened, and a new candidate id can be pre-registered with a fresh ledger at any time (AGENTS.md frozen-spec rule) |

## 7. What "retire" would mean mechanically (for the team to choose)

- **M1 — records only** (the futility spec §6 precedent):
  - a validation_log entry, `foundation/candidates.md` marked REFUTED, notes on R40–R42;
  - fires still logged, shown and notified, but counted toward nothing;
  - **the owner keeps getting the pings.**
- **M2 — stop calling the retired cells** (recommended):
  - `check_shadow_signals` skips each retired candidate/pair;
  - the candidate functions stay byte-identical and importable;
  - ledger rows stay;
  - pending rows still get graded, so the record completes: EARLY_MOMENTUM_v2
    has 4 open rows, and their grading will notify once each;
  - a protected change with its own build spec.
- **M3 — keep logging, stop displaying and notifying:**
  - retired cells' fires are written but never shown;
  - it keeps a silent forward check on the retirement;
  - but no decision rule would read it: evidence nobody reads, plus rows on
    every counter.

**Build prerequisite for M2 or M3, found while writing this paper:**
- `studies/frozen_candidates_study.py` replays `shadow_signals._CANDIDATES`
  directly (line 91).
- Its self-test checks, bar by bar, that the replay's fires equal
  `check_shadow_signals` (lines 251–262). That test runs in the suite
  (`tests/test_frozen_candidates_selftest.py`).
- Any harness change that skips a cell, or removes a candidate from that
  list, would break FCS-1's reproducibility and fail that test.
- So the build must first pin FCS-1 to its own frozen copy of the
  three-function list, with an unfiltered entry point (free zone). Only then
  can the live harness change.

## 8. Recommendation (mine; for the team to accept, amend or reject)

| Cell | Recommendation | Why |
|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | **Retire** | Refuted under every assumption in §3, at the best power of any cell (246 episodes; +0.24R would have shown at 80%). Forward: 4 episodes averaging −0.40R. Most of the pings |
| THRUST_PULLBACK GBP/AUD | **Retire** | Refuted under every assumption. The in-sample walk-forward was also negative (R17, −0.10R). It has never fired live, so retiring it changes nothing visible: this is record-keeping |
| MOMENTUM_JOIN GBP/AUD | **Keep running**, recorded as "refuted at the era's costs, not at today's" | The pre-registered verdict stands as REFUTED. But at today's spread the bound is +0.166R, and the live candidate would trade at today's spread. **Reviewers should challenge this:** it is a post-hoc rescue of a refuted cell, and the alternative (retire it, as the pre-registered verdict reads) is defensible |
| MOMENTUM_JOIN GBP/JPY | Keep running | Inconclusive: no edge shown, none ruled out |
| THRUST_PULLBACK GBP/JPY | Keep running | Inconclusive, with only 39 episodes (6% power) |

Mechanics: **M2**, after pinning FCS-1's candidate list.

If accepted:
- EARLY_MOMENTUM_v2 stops entirely.
- THRUST_PULLBACK runs on GBP/JPY only, which is already all it has ever fired on.
- MOMENTUM_JOIN runs on both pairs.

## 9. What changes downstream if this is accepted

- **The shadow-to-digest spec v2** (waiting on this) covers MOMENTUM_JOIN on
  both pairs plus THRUST_PULLBACK GBP/JPY. On the record since October, that
  is 3 rows in five weeks instead of 15.
- **Shadow-block wording (display item 8).** Kept cells say what history
  showed: inconclusive on 2005–2013 (no edge shown, none ruled out), plus
  MOMENTUM_JOIN GBP/AUD's cost caveat. The words "evidence accumulating"
  change in the display-claims spec.
- **The futility checkpoint** pools episodes across pairs per candidate. With
  THRUST_PULLBACK GBP/AUD retired, THRUST_PULLBACK's count comes from GBP/JPY
  only. No episode changes today: GBP/AUD has none.
- **Records.** `foundation/candidates.md`, R40–R42, the skill rebuild, and
  AGENTS.md's frozen-candidates paragraph, which names all three as live.

## 10. Questions for the team

1. Accept, amend or reject each of the five recommendations in §8.
2. MOMENTUM_JOIN GBP/AUD: honour the pre-registered REFUTED (retire), or keep
   it on the today's-spread sensitivity? Either way, record the reason.
3. Mechanics: M1, M2 or M3?
4. Should a retired cell's past forward episodes still count toward its
   candidate's futility checkpoint? Today this affects nothing: THRUST_PULLBACK
   GBP/AUD has no episodes.
5. When the four open EARLY_MOMENTUM_v2 rows grade, should they still notify
   (once each), or go only to the record?

## Not in scope

- Building anything.
- Changing any frozen parameter.
- Opening the sealed 2014–2021 exam.
- The live harness's every-bar cadence (the owner's item 3, already with the team).
