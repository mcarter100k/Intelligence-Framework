---
name: trading-foundation
description: A solo FX trader's proven research discipline and knowledge base, distilled from the Intelligence Framework (GBP/AUD, GBP/JPY on OANDA). It covers honest evidence rules (non-overlapping N, INFORMED PRIOR vs VALIDATED, pre-registration, statistical power, costs and swap), 44 already-tested hypotheses (most refuted: don't re-test them), exact risk and trade-management rules, a top-down chart-reading method (structure, Fibonacci, zones; untested), a trader review loop, and a catalogue of silent failures to avoid. Use this skill whenever the user evaluates a trade idea, setup, indicator or strategy; asks "does this work" or "is this an edge"; designs a backtest, study or forward test; reads a win rate or sample size; grades or journals trades; does a weekly or monthly trading review; sizes a position or sets stops and targets; marks up a chart or asks where to draw a Fibonacci or a level; or changes code that produces or grades trading evidence, even if they don't mention the framework by name.
---

# Trading Foundation

This skill holds what survived a hard audit of a solo trader's FX framework.
Two things survived: the **method** (how to know whether something works
without fooling yourself) and the **knowledge** (what has already been
tested, and what the data and the market are actually like). Everything
here was paid for, often with months of silently broken evidence, so use
it before spending effort again.

The trader's goal is to keep growing. That means turning ideas into honest
evidence quickly, and grading their own decisions, not only a model's.
Measure your help against that: is the user now closer to a real answer,
or holding a more confident-sounding guess?

## How to advise on the owner's work (applies everywhere)

When reviewing, critiquing or suggesting changes to anything the owner made
(code, configs, charts, docs, picks, plans):

1. **Ask what it's for before saying remove or change it.** If the purpose
   isn't clear from context, ask. Don't assume.
2. **Check the rule fits before citing it.** Every rule has a scope (near
   price, live path only, GBP pairs only, N ≥ 20...). Say why this case is
   inside that scope. If it isn't, the rule doesn't apply.
3. **Label every recommendation:**
   - **Required:** breaks a stated rule or evidence (cite it)
   - **Untested:** reasonable, but nobody has checked it
   - **Preference:** my judgement; the owner can ignore it
4. **When the owner pushes back, re-check the premise; don't defend it.** If
   the reason doesn't hold, say so plainly in the first line and give
   corrected advice.

## Reference files (read the one the task needs)

| File | Read when |
|---|---|
| `references/research_findings.md` | **Any new idea, before testing it.** 44 prior tests with honest N. Refuted premises include compression-precedes-moves, fakeout-then-go, hourly breakout confirmation, filtered daily/weekly level breaks, structural precursors, level fades and first-bounce entries |
| `references/methodology.md` | Designing any study or backtest, judging any result, writing a verdict. 39 principles, each with the incident that produced it |
| `references/risk_and_execution.md` | Sizing, stops, targets, daily limits, in-trade management |
| `references/trader_review.md` | Journaling, grading trades, weekly or monthly review, "how am I doing" |
| `references/market_data_facts.md` | Touching OANDA data, bar times, sessions and DST, pip scale, spreads, data feeds |
| `references/candidates.md` | The frozen shadow candidates (EARLY_MOMENTUM_v2, THRUST_PULLBACK, MOMENTUM_JOIN): specs and evidence |
| `references/incident_catalogue.md` | Changing code that writes, grades or displays evidence, or runs unattended |
| `references/chart_reading_method.md` | Marking up a chart: top-down order, swings, when and how to draw a Fibonacci, how deep pullbacks go (R39), zones. A method, not a tested edge: each rule is tagged UNTESTED or with its finding |

## Tools

- `scripts/power_check.py`: can this N tell an edge from zero? Gives power
  at N, the N required, the smallest detectable edge, the false-pass rate,
  and a bootstrap lower bound on observed R values. Run it before agreeing
  to any sample-size gate, and on any set of observed R values. Standard
  library only.
- `scripts/episodes.py`: counts independent (non-overlapping) episodes on the
  instrument's own bar index, graded rows only.

## Working modes

### 1. "Is this idea / setup / indicator any good?"

1. **Check `research_findings.md` first.** If the idea, or a close cousin,
   was already tested, say so with its N and result. Re-testing a refuted
   premise without a genuinely new angle wastes the one scarce resource,
   independent observations.
2. State the idea as a **testable thesis**: entry rule, stop, exit or
   horizon, instruments and timeframe. "Buy strength" is not testable.
   "Enter on a new 12-bar H4 high when ADX ≥ 30 and rising; stop 1.5 ATR;
   exit at 30 bars" is.
3. Ask whether there is an a-priori reason for an edge (carry, documented
   1–12-month time-series momentum, a structural flow), or whether it was
   drawn from a few memorable charts. Several of this framework's
   candidates came from 3–4 hand-circled moves, and none has shown an edge
   even in-sample. Say which case applies.
4. Give it a **status label**: REFUTED / INCONCLUSIVE / INFORMED PRIOR /
   VALIDATED. Nothing is VALIDATED without honest, non-overlapping N that
   clears a pre-registered, adequately powered test.
5. Propose the **fastest honest test** (mode 2). Usually that is a
   pre-registered historical run on OANDA data plus micro-size forward
   trades, not years of waiting on a forward ledger.

### 2. Designing a study, backtest or forward test

Pre-register the following before looking at results (details in
`methodology.md`):

- **Spec frozen:** exact rules, a candidate id, and the data span. Any later
  change means a new id and a fresh ledger.
- **Data partition:** keep study data separate from the one-shot exam
  data. Data already looked at is "learning only, never proof".
- **The sealed exam (2014–2021) is irreversible. Never propose spending it
  unless:**
  - the candidate is SUPPORTED on study data; AND
  - the spec states, before opening, the expected N and the minimum
    detectable edge at that N.
  - At swing frequency, +0.15R needs about 396 episodes, which the exam
    cannot supply.
  - Rule M40 in `methodology.md`; `data_map_spec.md` §11.6.
- **Episodes, not rows:** set the horizon in bars on the real bar index. A
  30-bar H4 horizon is about 168 clock hours, not 120. Count graded
  episodes only.
- **Costs:** spread appropriate to the period, **plus financing/swap** (GBP/JPY
  swap ≈ 0.1R per 5-day hold, the same size as the edges being hunted).
  Grade on the stop: a stopped trade is −1R, whatever happened later.
- **Power:** run `scripts/power_check.py`. With SD ≈ 1.2R, a 0.15R edge needs
  about 400 independent episodes for 80% power. The framework's old N=60 /
  0.15R gate had 16–36% power and let zero-edge strategies pass 17–28% of the
  time. If the required N is unreachable, say so plainly and suggest more
  instruments, more history, or a larger-effect hypothesis.
  The frozen code still runs `FLAG_N = 30` and `REVIEW_N = 60`
  (`shadow_signals.py:50-51`, recorded in `candidates.md`), while M10's audit
  correction holds N=60 at 0.15R to be a coin flip. Treat the code's N=30
  flag as an attention trigger, not a validity verdict; per M10, validity
  requires the pre-registered lower-confidence-bound test at the N that
  power demands.
- **Success criteria as numbers:** a lower confidence bound on avg R above 0,
  median R beside avg R, avg R after removing the best episode, max drawdown
  in R, and a correction when testing several candidate/pair cells.
- **Feed validated** before any statistic. Two feeds of "the same" market
  disagree by pips.

### 3. Reading a result someone shows you

Ask, in this order:

1. Is N independent episodes or raw rows?
2. Is it in-sample? Did this same data choose the parameters?
3. Are costs and swap included?
4. What are the median R and the avg R without the best trade?
5. Did the result come from a path proven able to be non-zero? "A zero from
   an unverified path is not data."

Then state the status label and what would move it.

### 4. Grading trades and reviewing the trader

Use `trader_review.md`. Key points:

- Log **every idea**, taken or passed, with the framework's read, and score
  passed ideas on paper too.
- Keep two scores per trade: outcome (R) and process (followed the plan).
- In the weekly review, allow one lesson and at most one rule change,
  decided before the next week begins.
- Below 20 trades, make no claims about edge. Process metrics are meaningful
  sooner.

### 5. Sizing, stops, targets and management

Use the exact rules in `risk_and_execution.md`:

- **Risk per trade by grade:** A+ 1.5%, A 1.0%, B+ 0.5%, B 0.25%, C = no
  trade.
- **Daily limits:** stop at 2R or 2%. Maximum 2 positions, and positions
  that share a currency leg count as one.
- **Stops:** between 0.3 and 1.5 daily ATR.
- **Reward:** ≥1.5R after spread.
- **Management:** at +1R move to breakeven and close 50%; from +1.5R trail
  0.5R behind price.

Note that these are INFORMED PRIORS that no real trade has exercised yet.
They are also UNENFORCED: `risk_config.py` and `session_guard.py` have no
live caller (`risk_and_execution.md`; AUDIT §4), so nothing on the live path
caps risk, daily loss or open positions today. Never describe a limit as
active.
Where a tool contradicts them (for example, a brief showing grade C with
75% size), flag it rather than pick one silently.

### 6. Changing code that produces, grades or displays evidence

Read `incident_catalogue.md` first. The recurring failure is **silent**: an
error that renders as "no setup", a writer that is never called, or a test
that passes for the wrong reason. The controls that work:

- **Neutralize every side effect** on a verification run. Tests redirect
  every ledger; they never write the real ones.
- **Test the wires, not just the components.** Check that the live entry
  point actually calls the writer.
- **Make errors distinguishable from quiet markets.** Use loud markers, keep
  health counters per job, and treat a crash as a failure.
- **Evidence ledgers are append-only.** Fix mistakes with exclusions and
  dated corrections, never by editing rows.
- **Run shell wrappers under the interpreter the scheduler actually uses.**
  launchd runs `/bin/bash` 3.2.
- **Get the price and pip scale right.** Use the real price at signal time,
  not the last closed bar. Pip size is 0.01 for JPY, 0.0001 otherwise.
- **Fix the class of bug with a test,** not with another standing rule.

### 7. Marking up a chart

Use `chart_reading_method.md`. Read top-down (weekly, daily, 4-hour, hourly),
give each timeframe its direction, last break and the level where that read
fails, then build zones where several reasons overlap. Get exact swing
prices from OANDA candles, not a screenshot. Say plainly which parts are
tested (levels give location, not timing; most first pullbacks reach 38.2%;
buying the touch shows no edge) and which are judgement.

## Output shape for an idea or result evaluation

```
VERDICT: <status label> — <one line>
PRIOR WORK: <matching finding(s) from research_findings, or "none found">
THESIS: <testable rule set>
EVIDENCE: N=<independent> | avg R <x> | median R <y> | w/o best <z> | costs <incl/excl>
POWER: <what N is needed for the claimed edge; is it reachable?>
FASTEST HONEST TEST: <concrete next step>
RISKS / TRAPS: <which incidents or principles apply>
```

Keep it plain-English where the trader reads it. Internal names and indicator
jargon belong in logs, not in the verdict.
