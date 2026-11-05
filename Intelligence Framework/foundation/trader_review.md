# Trader review loop — grading the trader, not only the model

The 2026-09-29 audit's central finding on growth: the framework graded its
own model and never graded the trader. Zero real trades were logged in 4.5
months, and the four trade ideas recorded in `pre_trade_journal.csv` were
never scored. A model ledger takes years to reach a verdict. Your own
decisions reach N much faster, and they are the thing you are trying to
improve.

This file is the template for that loop. It reuses rules that already exist
in the framework (`setup_check.py`, `trade_management.py`, `risk_config.py`
and `session_guard.py`; see `risk_and_execution.md`) rather than inventing new
ones.

## 0. How to run it (tool added 2026-11-04: `scripts/trader_review.py`)

Run every command from the Intelligence Framework folder. The tool refuses to
write anywhere else.

| When | Command | What it records |
|---|---|---|
| Before a trade (recommended) | `python3 setup_check.py GBP_JPY LONG --target 213.78` | The six lines and **the framework's read**, live |
| Every idea, taken or passed | `python3 scripts/trader_review.py idea` | Your plan: play, zone, trigger, entry, stop, target, grade, feeling. It copies the framework's read from a pre-trade check of the same pair and direction in the last 6 hours, or else from the latest brief, or else marks it "not recorded" |
| Entering and exiting a taken trade | `python3 trade_logger.py open`, later `close` | Your real fills (size 0.0 for a practice trade) |
| When an idea is over | `python3 scripts/trader_review.py score` | Taken: R from the trades.csv fills only (never from memory), the five process questions, rule breaks. Passed: R on paper from your plan prices, less the 4-pip spread, or "never filled" |
| Anytime | `python3 scripts/trader_review.py list` | Ideas still waiting for a score |
| Weekend | `python3 scripts/trader_review.py review` | Steps 1–6 below, then ONE lesson and AT MOST ONE rule change. A week can only be written once it has ended, and only once. `--no-write` shows the numbers without writing; `--week 2026-W45` picks a week |

Ledgers: `idea_journal.csv` (an IDEA row, then a SCORE row; scoring never
edits the IDEA row) and `trader_review_log.csv` (one row per week). Both are
gitignored, append-only and backed up nightly. The tool sends no
notifications. §5's monthly check prints its own `power_check.py` command once
there are 20 scored trades.

---

## 1. Before the trade: six lines, each answerable in words

From `setup_check.py`. If any line is blank, the verdict is "nothing here
says NOW".

| Line | Question | Fails if |
|---|---|---|
| BIAS | Which way and why, in one sentence? | You can't say it without indicator names |
| REGIME | What is the market doing: trending, quiet range, exhausted, or unresolved? | The honest answer is "not sure" |
| PLAY | Name it: coil-break, base-break, first-pullback or retest-fade | **"If you can't name it, it's a feeling, not a trade."** |
| CLOCK | Is there a high-impact release in this pair's currencies within 2h? Is it the right session? | Inside the lockout (2h before, 0.5h after) |
| FUEL | How much of today's typical range is left? | The move is already spent |
| RISK | Stop, target, size | Stop <0.3 or >1.5 daily ATR, R:R <1.5 after spread, risk above the grade's % |

Also record **the framework's read** at that moment, and whether you agree.
Trading against it is allowed; that is the point of a soft gate. But it is
**flagged**, so the review can later show whose read was better.

## 2. The journal row: one per idea, taken OR not

Log ideas you pass on too. A passed idea is scored on paper exactly like a
taken one. That is how you learn whether your filter or your execution is
the weak link.

| Field | Notes |
|---|---|
| `idea_id`, `timestamp_utc`, `pair`, `direction` | |
| `play` | One of the named plays |
| `framework_read`, `agrees_with_framework` | Copied from the brief |
| `taken` | TRUE/FALSE. If FALSE, why? |
| `entry`, `stop`, `target`, `planned_rr_after_spread` | Planned, before entry |
| `risk_pct`, `grade` | From the grade table; C means no trade |
| `pre_trade_state` | One word: calm / rushed / revenge / FOMO / bored |
| `exit`, `exit_reason` | Target / stop / invalidation / discretionary |
| `r_realized` | `sign·(exit−entry)/|entry−stop|`, after spread. **The stop defines R; net-at-horizon is not a result.** |
| `mfe_r`, `mae_r` | How far it went for and against you, in R |
| `rule_breaks` | e.g. moved stop, skipped partial, sized up, entered early |
| `loss_species` | For losers: event_window / stopped_then_reversed / exhaustion_entry / never_onside / bled_out |

## 3. Two scores per trade, kept separate

- **Outcome:** `r_realized`. Noisy; judge it only in aggregate.
- **Process:** did you follow the plan? Score 1 point for each of plan
  complete, size per grade, stop untouched, partial taken at +1R, and exit by
  rule. Divide by 5.

A good-process loss is fine. A bad-process win is a warning, because it
teaches the wrong lesson.

## 4. Weekly review (about 20 minutes, same time every week)

1. Count ideas (taken / passed), and count trades against the framework.
2. Taken trades: avg R, **median R**, win %, process score.
3. Passed ideas: paper avg R. Positive means your filter is too tight;
   negative means it is saving you.
4. You versus the framework versus the candidates: on the same weeks, whose
   calls scored better in R?
5. Rule-break tally. Which rule broke most, and in what `pre_trade_state`?
6. Read the week's notifications (`notification_log.csv`) and record
   **MATERIAL / TOTAL**. Material means it told you something you did
   not already know. One number, recorded, not interpreted (week of
   2026-10-11: 2 of 12).
7. **One** lesson, and **at most one** rule change, written down *before*
   next week starts. Never change a rule mid-week: that is in-sample tuning
   on yourself.

## 5. Monthly: what is it telling you, honestly?

- Run `tools/power_check.py --rs <your R values>`. Until N ≥ 20 independent
  trades it is INSUFFICIENT, so don't conclude anything about edge. Process
  score and rule breaks are meaningful sooner.
- Check the **median** beside the average, and the average **without your
  best trade**. If one trade carries the month, the month is inconclusive.
- Anything you now "know" gets a status label: INFORMED PRIOR until the
  numbers earn more.

## 6. Where real N comes from fastest

- **Micro-size live or practice trades** on candidate fires and your own
  named plays. These give real fills, real slippage and real execution reps.
- **Scoring every journal idea**, taken or not.
- **A pre-registered historical test** on OANDA 2014–2021 for mechanical
  rules (`methodology.md` M11–M13).
- Not waiting. At about 0.3–0.7 fires a week, the forward model ledger alone
  reaches a verdict in 2028–2030.
