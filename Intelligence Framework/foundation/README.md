# foundation/ — what is proven good in this framework

Distilled from the 2026-09-29 full audit (`docs/audit_2026-09-29.md`). The
audit found this framework has little value today as a *trading tool*: one
graded episode and zero real trades. Its lasting value is a rigorous research
**method** and a body of hard-won **knowledge**, most of it negative. This
folder keeps exactly that, and nothing the audit found broken is presented
here as evidence; broken things appear only as lessons.

## The short version

The method is worth keeping. Four entry premises were refuted at honest N: compression, fakeout-then-go, structural precursors and level fades. Two further fixed-rule plays were negative in every cell: first-bounce entries, and THRUST_PULLBACK in-sample. What survives is descriptive:
- Turns happen at levels about 90% of the time (1.5x base), but timing is unpredictable.
- About 71% of breaks beyond a swing fail within 3 days. The ones that hold go about 1.8 ATR.
- Holding until the structure label flips gives back about 116% of the move.
- Half of major-release moves round-trip in 3 days.
- A GBP/AUD week travels about 2.1 daily ATRs and usually contains two ≥1-ATR swings.

The execution rules are ready to wire in:
- Risk: 0.25–1.5% by grade; 2R / 2% daily stop; 2 positions; shared-leg-as-one.
- Stops: between 0.3 and 1.5 daily ATR.
- Reward: ≥1.5R after a 3–4-pip spread.
- Management: breakeven plus 50% at +1R, trail 0.5R from +1.5R.

The biggest gap is that nothing grades the trader. The best next evidence source is a pre-registered, cost- and swap-aware run on OANDA's own 2014–2021 data, followed by forward trading at micro size (AUDIT §5).

## Contents

| File | What it holds |
|---|---|
| `methodology.md` | 39 evidence-discipline principles, each with the incident that forced it |
| `research_findings.md` | 46 tested hypotheses with honest N. **Check here before testing any idea** |
| `chart_reading_method.md` | How to mark up a chart: top-down order, swings, Fibonacci anchors, pullback depth (R39), zones. A method, not a tested edge |
| `market_data_facts.md` | OANDA candle conventions, sessions and DST, pip scales, feed overlap, spreads |
| `risk_and_execution.md` | Exact risk, stop, target and management rules, and where they live in code |
| `candidates.md` | The frozen shadow candidates: exact specs and current evidence |
| `incident_catalogue.md` | 32 silent failures and contamination events, with the control each produced |
| `trader_review.md` | **The missing half:** the loop that grades the trader, not only the model |
| `tools/power_check.py` | Is this N enough? Power, required N, false-pass rate, bootstrap bound |
| `tools/episodes.py` | Honest non-overlapping episode counting on the real bar index |
| `skills/trading-foundation/SKILL.md` | Source of the `trading-foundation` skill built from this folder |
| `skills/evidence-validation/` | Source of the `evidence-validation` skill: no claim without observed evidence (owner rule, 2026-09-29), with the audit-hook probe |

## The skills

`build_skill.sh` builds every skill under `skills/` and installs it to
`~/.claude/skills/<name>/`, so each is available in every Claude session:
- **trading-foundation**: `SKILL.md`, plus this folder's `.md` files as
  `references/` and `tools/` as `scripts/`.
- **evidence-validation**: `SKILL.md` plus its own `scripts/`.

This folder is the single source of truth. Edit here, then rebuild:

    ./foundation/build_skill.sh             # installs to ~/.claude/skills/<name>
    ./foundation/build_skill.sh <dest-root> # or anywhere else

## Keeping it honest

- When a new study, incident or rule lands in `validation_log.md`, add it here
  with its citation.
- Status labels are the framework's own: REFUTED, INCONCLUSIVE,
  INFORMED PRIOR, VALIDATED. Nothing here is VALIDATED yet.
- Citations point at repo line numbers as of the audit; search by content
  if they drift.
