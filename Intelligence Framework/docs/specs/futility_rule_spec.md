# Spec: futility checkpoint for the shadow candidates (2026-10-19)

**Status:** team review given 2026-10-19 (the review message is the
authority). This spec was committed before any further grading of the
candidates. Once committed it is frozen: a later change gets a new spec and
a dated validation_log entry.

## The gap

The framework had a rule for when to ACCEPT a candidate (FLAG at N=30, REVIEW
at N=60) and no rule for when to ABANDON one. A losing candidate therefore
ran the full clock by default. At about 0.7–0.9 independent episodes a week,
reaching N=30 takes most of a year.

## The rule

1. **Who it applies to.** All three frozen candidates equally:
   EARLY_MOMENTUM_v2, THRUST_PULLBACK and MOMENTUM_JOIN. Not only the one
   currently losing.
2. **What counts as an episode.** A graded, valid row (not `is_invalid_spec`,
   not in the exclusion registry). Episodes are independent: a fire starts a
   new episode only 30 or more H4 bars after the previous episode's start,
   on the instrument's own bar index (`foundation/tools/episodes.py`
   semantics, M34), not clock hours. **An episode's R is the R of its first
   fire**: the entry that would have been taken. A candidate's episodes are
   pooled across its pairs.
3. **When it is evaluated.** Exactly once per candidate: when its graded
   episode count first reaches **N = 20**, on those first 20 episodes in time
   order. It is a checkpoint, not a continuous test, and it is never
   re-evaluated.
4. **The bound.** The 90% one-sided UPPER confidence bound on mean R:
   `foundation/tools/power_check.bootstrap_upper_bound(rs)`, a percentile
   bootstrap with 10,000 resamples and seed 7. It mirrors the existing lower
   bound and carries the same under-coverage label.
5. **The decision.**
   - If the upper bound is **below +0.15R**, the candidate is **REFUTED and
     retired.** If even the optimistic end of the range falls short of the
     smallest edge worth trading, more observations change only the
     precision, not the conclusion.
   - Otherwise it runs to N=30 (FLAG) and N=60 (REVIEW) as before.
6. **What retiring means.** A dated validation_log entry records the
   episodes, the bound and the verdict. `foundation/candidates.md` marks the
   candidate REFUTED. Its ledger rows stay (they are append-only evidence).
   Removing the candidate from the live harness (`shadow_signals._CANDIDATES`)
   is a protected change with its own review. Until then its fires are
   logged but never counted toward any decision.

## It does NOT fire today

Graded independent episodes as of 2026-10-19, counted per section 2:
- EARLY_MOMENTUM_v2: 3
- THRUST_PULLBACK: 1
- MOMENTUM_JOIN: 1

No candidate is near N=20. **Nothing is retired by this commit**, and this
rule must not be read as a disguised way to kill a candidate. It has no
code path that acts on its own.

## Disclosure (this rule was not written blind)

This rule was written after EARLY_MOMENTUM_v2 results were visible, so it is
**not** blind pre-registration.

- **What the author saw.** The review message that commissioned the rule
  described EM_v2 as "4 graded episodes averaging about −0.95R". Before
  writing this spec the author read the ledger. Counted per section 2, it
  shows **3 graded independent episodes with first-fire R of −0.55, −0.39 and
  +0.34 (mean −0.20R)**. All 16 graded EM_v2 rows average −0.245R. The
  heartbeat's clock-hour counter (the known overcount, audit item 3) shows 4,
  including one ungraded fire. The author could not reproduce −0.95R by any
  counting tried. Both figures are recorded here; the rule depends on
  neither.
- **The +0.15R threshold was not fitted to that data.** It is the framework's
  own pre-existing minimum-edge figure, already used in M10 and in
  `power_check.py`'s documented examples ("`--edge 0.15 --sd 1.2`") before
  this rule existed.
- **N was not chosen by testing which value would retire EM_v2.** The review
  proposed N=15, the midpoint to the existing FLAG gate. This spec moves it
  to N=20 for the reason below. 20 is the framework's pre-existing minimum N
  for any claim (M3) and the existing gate on the bootstrap. Neither 15 nor
  20 retires EM_v2 today, since it has 3 episodes.

A stopping rule written after seeing bad numbers, and not disclosed, would
be outcome fitting. This one is disclosed, and its threshold and checkpoint
come from rules the framework already had.

## The N=15 vs N≥20 tension, resolved: checkpoint at N=20

The bootstrap bound is gated at N≥20 (M3: below 20 is INSUFFICIENT for any
claim). A futility retirement is a claim: REFUTED. Using the bound at N=15
would be using it below its own gate, which this framework forbids.

A design simulation (`studies/futility_rule_simulation.py`, synthetic R
only) also shows the bound is not trustworthy at small N for some R shapes.
For a candidate whose true mean is exactly +0.15R, the rule wrongly fires:

| R shape | N=15 | N=20 | N=30 |
|---|---|---|---|
| near-binary: stopped at −1R, or a +2.5R winner | 8.4% | 16.0% | 8.7% |
| normal, SD 1.2R, floored at −1R | 6.9% | 5.6% | 4.7% |

Against a nominal 10%, the near-binary shape swings with N: lattice effects
of the percentile bootstrap. The live R distributions are not yet known
well enough to rule that shape out.

**The cost of N=20 over N=15** is about 5 more episodes, roughly 6–7 weeks
at the current rate. That is still about 10 episodes before the FLAG gate.

**Known limit (recorded, not hidden): the rule only catches clear losers.**
For a candidate whose true mean is −0.20R, the rule fires only 30–49% of the
time at N=15–30 (the same simulation). With SD near 1.2R, the 90% upper
bound sits roughly 0.3–0.4R above the observed mean. The rule is asymmetric
by design: it protects a real edge from early retirement at the price of
letting mild losers run to N=30.

## Tooling

`power_check.py` gains `bootstrap_upper_bound`, the mirror of
`bootstrap_lower_bound`. It is reported only from N≥20 and carries the same
under-coverage label. It is pinned in `tests/test_foundation_tools.py` with a
positive control: a sample whose bound must fall below +0.15R and one whose
bound must not.

## Not in scope

- Automating the check. Whoever runs the review evaluates it when a
  candidate reaches 20 episodes.
- Changing `shadow_signals.py`'s frozen constants.
- Fixing the clock-hour episode counter (audit item 3; its own spec).
