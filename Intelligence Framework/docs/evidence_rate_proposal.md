# Proposal: raise the evidence rate before hunting more ideas

**Status:** PROPOSED 2026-11-06, for team review. Docs only. Nothing is
built, fetched or run, and no protected module, ledger or SEALED EXAM bar is
touched by this proposal.

## The decision asked

The framework cannot prove or disprove a realistic edge in any useful time,
because its candidates produce too few independent trades. Before more ideas
are tested, the team should choose how to raise the number of independent
trades per year. **Recommendation:** widen the instrument universe (pre-named,
partitioned before anyone looks), stay on the 4-hour timeframe, and size every
test to the edge its N can actually detect. Six decisions are listed in §6.

## 1. The problem, in numbers

- **No edge found so far.** 42 hypotheses are recorded in
  `foundation/research_findings.md`; none is VALIDATED. All three frozen
  candidates failed on 2005–2013 data they never saw: three cells REFUTED,
  two INCONCLUSIVE with no edge shown (FCS-1, R40–R42, 2026-11-04).
- **The forward ledger is slow.** 32 graded signals since 2026-07-29, at most
  20 in any one candidate cell, and fewer independent episodes than that. No
  cell has reached the N = 20 futility checkpoint.
- **The candidates trade rarely.** 4.3 to 27.3 independent episodes a year per
  candidate and pair (FCS-1 counts); the typical cell is about 10.7.
- **Proof needs far more trades than that.** Episodes needed for 80% power,
  per-episode SD 1.2R (`power_check.n_required`):

  | Edge to detect | one-sided α 0.05 | α 0.01 (as FCS-1 used) | Years at 10.7 a year (α 0.05) |
  |---|---|---|---|
  | +0.15R | 396 | 643 | 37 |
  | +0.25R | 143 | 232 | 13 |
  | +0.50R | 36 | 58 | 3.4 |

- **The sealed exam is too small for any current candidate.** Over its 7.30
  years a typical cell yields about 78 episodes; +0.15R needs 396. The team's
  2026-11-05 ruling recorded this as a structural mismatch between the
  validation bar and the trade frequency (`data_map_spec.md` §11.6, M40).

So the bottleneck is not ideas or engineering. It is the rate at which honest
evidence arrives. More ideas tested at this rate produce more INCONCLUSIVE
results.

## 2. Constraints any answer must respect

- The data map (`docs/specs/data_map_spec.md`): STUDY learns, USED is never
  proof, FORWARD alone grades live claims, and the SEALED EXAM is one frozen
  spec and one run under M40 (SUPPORTED on STUDY first, minimum detectable
  edge stated before opening).
- **The data map covers GBP/AUD and GBP/JPY only.** Any other instrument's
  history has no partition yet. It must get one, by ruling, before anyone looks
  at it, or its 2014–2021 data cannot serve as an exam.
- Frozen candidates change only by a new id and a fresh ledger;
  `shadow_signals.py` is protected.
- No instrument may be chosen for a test by looking at how a rule performed on
  it.

## 3. What is already in hand

- A validated research archive with a repeatable pipeline: GBP/AUD, GBP/JPY,
  GBP/USD, AUD/USD, USD/JPY and gold, daily / 4-hour / hourly, every span
  labelled and hash-pinned, the sealed block refused at fetch, build and load
  (`studies/research_archive_report.md`, `studies/leg_data_report.md`).
  Adding a pair is a fetch-and-verify run, not new engineering.
- The account offers 68 currency pairs. OANDA's price-history endpoint also
  serves instruments the account cannot trade (gold, silver confirmed
  2026-11-05).
- Two descriptive studies that bear on the levers below:
  - **Session movement** (2005–2013 and 2021–2026): movement concentrates in
    the London morning and the London/New York overlap, but the pre-set
    day-trading precondition FAILED on modern data for both pairs.
  - **Currency legs**: the two crosses' weekly returns correlated −0.01
    (2005–2013) and +0.20 (2021–2026), +0.33 in the most volatile weeks. Two
    instruments can be close to independent even when they share a currency.

## 4. The options

### A. Breadth: run each candidate on more instruments (recommended)

Independent trades scale with the number of instruments, discounted by how
much their outcomes move together. A rough guide is effective episodes ≈
total ÷ (1 + (k − 1) × ρ̄), with k instruments and ρ̄ the average correlation
of their trade outcomes. Illustration at 10.7 episodes a year per instrument:

| Instruments | Avg outcome correlation | Effective episodes / year | Over the 7.30-year exam |
|---|---|---|---|
| 1 | — | 11 | 78 |
| 5 | 0.2 | 30 | 217 |
| 10 | 0.2 | 38 | 279 |
| 10 | 0.1 | 56 | 411 |
| 20 | 0.1 | 74 | 539 |

- **What it buys:** with about 10 nearly independent instruments, the sealed
  exam becomes large enough to test a +0.15R claim, and the forward ledger
  reaches meaningful N in a few years rather than decades.
- **What it does not buy:** with correlated instruments the gain shrinks fast
  (10 pairs at ρ̄ 0.2 still fall short). Breadth alone may not close the gap.
- **Costs and risks:** spreads differ by pair and must be set per pair, in
  advance; outcome correlation is unknown until measured (the figures above
  are illustrative, not estimates); a rule designed on GBP pairs may simply
  not transfer, which is itself a useful, fast answer; live tracking of more
  instruments is a protected-path change needing its own spec.
- **The one hard requirement:** the instrument list and its partition are
  fixed by ruling **before** any of its data is fetched for study, and the
  test is pooled and pre-registered, so no pair is cherry-picked afterwards.

### B. Frequency: trade a shorter timeframe (not recommended now)

- More bars per year means more episodes, but the cost of a trade grows
  relative to the move. A 3-pip spread is, on 2021–2026 average ranges:

  | Timeframe | GBP/AUD | GBP/JPY |
  |---|---|---|
  | 1-hour | 11.3% of the bar's average range | 10.1% |
  | 4-hour | 5.6% | 4.9% |
  | Daily | 2.2% | 1.9% |

- The session study's pre-set precondition for intraday trading failed on
  modern data for both pairs.
- **Verdict:** doubling the cost burden to gain N is the wrong trade while no
  edge exists at 4 hours. Revisit only for a candidate that shows an edge large
  enough to pay hourly costs.

### C. Claim size: test only for large edges (adopt alongside A)

- A +0.5R claim needs about 36 episodes (58 at α 0.01). Already permitted by
  §11.6 rule 2(b).
- **Limit:** large edges are rare, and every result so far has sat near zero.
  On its own this mostly produces honest REFUTED verdicts on big claims. Its
  real use is to set each test's bar to what its N can detect, as M40 requires.

### D. Status quo

- Keep two pairs, keep the ledger running, test new ideas as they come.
- **Consequence:** at about 10 episodes a year per cell, no realistic edge
  (+0.15R to +0.25R) can be confirmed for 13 to 37 years. Every new idea
  joins the INCONCLUSIVE column.

## 5. Recommended plan (each step gated; nothing starts without the ruling)

1. **Universe ruling.** The team names the instrument universe by criteria
   fixed now, not by performance: for example, the most liquid pairs on the
   account by typical spread, capped at about 10. GBP/AUD and GBP/JPY keep their
   existing partition; any other pair already studied for edge is excluded. It
   records each pair's spread assumption by era.
2. **Partition ruling.** The data map is extended to the universe with the
   same spans and embargoes, so each new pair's 2014–2021 data is sealed
   before it is ever fetched. The team first confirms which of these
   instruments' 2014–2021 data, if any, has already been looked at; the
   2026-11-05 records show the USD legs and gold were fetched only for STUDY,
   USED and FORWARD.
3. **Data.** Fetch and verify the universe for STUDY, USED and FORWARD with
   the existing pipeline (the same checks as every archive file so far).
4. **Measure the breadth gain before relying on it.** One descriptive,
   pre-registered study: the correlation of weekly returns across the
   universe, per period, giving the real ρ̄ in place of the illustrative
   0.1–0.2 above.
5. **Size the first test to the N it will have.** With the measured ρ̄,
   compute the effective N and the minimum detectable edge for a pooled test
   (M40), and only then choose what to test.
6. **Test.** One pre-registered pooled test of one rule across the universe on
   STUDY. A sealed-exam proposal follows only if it is SUPPORTED and the exam's
   power line clears the bar.

Steps 1–4 are a few days of work on existing tools. No protected module
changes until a candidate earns live tracking.

## 6. Decisions for the team

1. Adopt breadth (A) as the primary lever, with claim sizing (C) applied to
   every test? Or another option?
2. The universe criteria and the cap (suggested: lowest typical spread, about
   10 pairs; the two current pairs keep their partition; no other pair
   previously studied for edge).
3. Extend the data map's partition to the universe before any fetch, with
   the same spans and embargoes?
4. Stay on the 4-hour timeframe and set aside the hourly option (B) until an
   edge exists?
5. Approve the descriptive cross-instrument correlation study (step 4) as the
   first run?
6. Which rule is the first pooled test? None of the current candidates showed
   an edge on its own pairs; the team may prefer a new, pre-registered rule
   over re-running a refuted one on more instruments.

## 7. What this proposal does not do

- It proposes no trading rule, filter or entry condition.
- It does not change `risk_config`, `shadow_signals.py` or any ledger.
- It does not open, fetch or count the SEALED EXAM for any instrument.
- It makes no claim that breadth will produce an edge. It only makes the
  answer arrive in years rather than decades.

## Sources

`foundation/research_findings.md`; `docs/specs/data_map_spec.md` §1, §11.2,
§11.6; `foundation/methodology.md` M40; validation_log 2026-11-04 (FCS-1) and
2026-11-05 (sealed-exam ruling, session movement study and replication,
research archive, currency legs); `studies/session_movement_replication_report.md`;
`studies/leg_decomposition_report.md`; `foundation/tools/power_check.py`.
Figures in §1 and §4 were computed 2026-11-06 with `power_check.n_required`
and from the reports' published numbers; the effective-episode table is
illustrative arithmetic, not an estimate.
