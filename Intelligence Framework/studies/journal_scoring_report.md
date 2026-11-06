# Pre-trade journal: the recorded ideas, scored (2026-11-06)

**Read-only.** `pre_trade_journal.csv` was read from a temp copy made by
`reality_run.py`; the copy was byte-identical after the run, and no ledger
was written.
- Code: `studies/journal_scoring.py`. Tests: `tests/test_journal_scoring.py`.
- **N is tiny. No conclusion is drawn about the owner's judgment.** This is
  a record of what happened, with its method.

## Premise check

The request said four ideas, each graded on its own stop_price and target.
The journal holds **six rows**, and the fields differ:
- **Row 1** (GBP/JPY long, 2026-07-31 PDT) has a target but **no stop**. It
  cannot be graded in R.
- **Rows 2–4** are one idea (a GBP/AUD short) checked three times on
  2026-09-09 PDT, with stops within 0.6 pip of each other.
- **Rows 2–5 have no target.** Row 6 has both.

**Four distinct ideas, three gradeable.** The framework's standard rule
(`shadow_signals.grade_pending_shadow`) uses **no target**:
- a stop touch within the next 30 H4 bars is −1R;
- otherwise R is the direction-signed (close of the 30th bar − entry) ÷ the
  risk.

So stop-only rows are graded by the standard rule unchanged.

**Overlap:** the ideas of 09-09, 09-10 and 09-11 have overlapping 30-bar
horizons, so by the framework's episode counting they are at most one
independent episode.

## How the entry was approximated, and a finding

- **No entry and no price at check were recorded.** But setup_check writes
  stop_pips = |price − stop| / pip, so the price it measured from is
  recoverable.
- **That price is the previous daily close, not the market.** On every
  GBP/AUD row it equals the prior D1 close: 0.00 pips on four rows, 0.40 on
  the fifth (rounding to 4 decimals). It lies outside the check hour's actual
  range.
  - Before 2026-09-30, `current_price` was the previous D1 close
    (data_at_source_spec P1).
  - **So every recorded distance in these rows is a distance from
    yesterday's close.**
- **That recovered price is therefore not used as an entry.** Two
  market-based approximations are graded instead:
  - **E2:** the close of the H4 bar containing the check time.
  - **E3:** the open of the first H1 bar after the check time.
- **Limit:** the hours of the check's own H4 bar after the check are not seen
  by the H4 rule. They were checked separately on H1 and change no grade.

## The scored ideas

| Idea (rows) | Pair, side, check time (Pacific) | Framework said | Against the framework? | Real stop distance (E2 / E3) | R (E2 / E3) |
|---|---|---|---|---|---|
| 1 (row 1) | GBP/JPY long, 2026-07-31 20:53 PDT | NO TRADE, grade C | yes | no stop recorded | **ungradeable**; target 215.5 not reached in 30 bars (high 213.306) |
| 2 (rows 2–4) | GBP/AUD short, 2026-09-09 09:17–12:06 PDT | NO TRADE, grade C | yes | 0.2 to 1.1 pips (recorded "6.6–7.2") | **−1.00 / −1.00** on each row: stopped |
| 3 (row 5) | GBP/AUD short, 2026-09-09 21:31 PDT | NO TRADE, grade C | yes | 3.3 / 3.2 pips (recorded "10.2") | **−1.00 / −1.00**: stopped |
| 4 (row 6) | GBP/AUD short, 2026-09-10 18:38 PDT | SHORT, grade B | no | 114.8 / 106.0 pips (recorded "92.6") | **+0.90 / +1.06**: not stopped; target 1.8732 not reached (low 1.87414) |

**Sensitivity:**
- **Ideas 2 and 3:** the result does not move. With a stop 0.2–3.3 pips from
  the market, any reasonable entry is stopped.
- **Idea 4:** it moves between +0.90 and +1.06R across the two
  approximations, a spread of 0.16R. If the recorded distance (92.6 pips,
  from yesterday's close) had been the true risk, the figure would read
  +1.36R. That is the size of the error the stale price introduces.
- **A scored row with an estimated entry is weaker evidence than one with a
  recorded entry.** These figures should be read as such.

**Against or with the framework (as recorded):**
- Ideas 1–3 went against its read (NO TRADE, grade C). Idea 4 agreed with
  it (SHORT, grade B).
- With N = 4 ideas, at most one of them independent of the others in time,
  nothing can be concluded about either the owner's or the framework's
  judgment.

## Full output of the run (verbatim)

```
journal rows: 6 (read only)

## Row 1: GBP_JPY LONG at 2026-07-31 20:53 PDT
  framework said: NO TRADE (grade C); against the framework: True
  recorded: stop (none), stop_pips (none), target 215.5, r_to_target (none)
  H4 bar of the check 2026-07-31 10:00 PDT; horizon ends with the bar opening 2026-08-07 10:00 PDT; exit close 212.911; highest high 213.306, lowest low 209.575 over the 30 bars
  target reached within the 30 bars: False
  status: UNGRADEABLE (no stop recorded)

## Row 2: GBP_AUD SHORT at 2026-09-09 09:17 PDT
  framework said: NO TRADE (grade C); against the framework: True
  recorded: stop 1.87692, stop_pips 7.2, target (none), r_to_target (none)
  H4 bar of the check 2026-09-09 06:00 PDT; horizon ends with the bar opening 2026-09-16 06:00 PDT; exit close 1.8856; highest high 1.89512, lowest low 1.87578 over the 30 bars
  status: graded
  price setup_check measured from (recovered) 1.87620; previous D1 close 1.8762; inside the check hour's range: False -> recorded stop_pips 7.2 is a distance from that, not from the market
  E2 close of the check's H4 bar 1.87694; E3 open of the next H1 bar (2026-09-09 10:00 PDT) 1.87694
  E2: risk 0.2 pips -> R -1.00 (stop hit True)
  E3: risk 0.2 pips -> R -1.00 (stop hit True)
  stop touched in the rest of the check's H4 bar (H1): False

## Row 3: GBP_AUD SHORT at 2026-09-09 09:35 PDT
  framework said: NO TRADE (grade C); against the framework: True
  recorded: stop 1.87692, stop_pips 7.2, target (none), r_to_target (none)
  H4 bar of the check 2026-09-09 06:00 PDT; horizon ends with the bar opening 2026-09-16 06:00 PDT; exit close 1.8856; highest high 1.89512, lowest low 1.87578 over the 30 bars
  status: graded
  price setup_check measured from (recovered) 1.87620; previous D1 close 1.8762; inside the check hour's range: False -> recorded stop_pips 7.2 is a distance from that, not from the market
  E2 close of the check's H4 bar 1.87694; E3 open of the next H1 bar (2026-09-09 10:00 PDT) 1.87694
  E2: risk 0.2 pips -> R -1.00 (stop hit True)
  E3: risk 0.2 pips -> R -1.00 (stop hit True)
  stop touched in the rest of the check's H4 bar (H1): False

## Row 4: GBP_AUD SHORT at 2026-09-09 12:06 PDT
  framework said: NO TRADE (grade C); against the framework: True
  recorded: stop 1.87686, stop_pips 6.6, target (none), r_to_target (none)
  H4 bar of the check 2026-09-09 10:00 PDT; horizon ends with the bar opening 2026-09-16 10:00 PDT; exit close 1.88815; highest high 1.89512, lowest low 1.87578 over the 30 bars
  status: graded
  price setup_check measured from (recovered) 1.87620; previous D1 close 1.8762; inside the check hour's range: False -> recorded stop_pips 6.6 is a distance from that, not from the market
  E2 close of the check's H4 bar 1.8768; E3 open of the next H1 bar (2026-09-09 13:00 PDT) 1.87697
  E2: risk 0.6 pips -> R -1.00 (stop hit True)
  E3: risk 1.1 pips -> R -1.00 (stop hit True)
  stop touched in the rest of the check's H4 bar (H1): True

## Row 5: GBP_AUD SHORT at 2026-09-09 21:31 PDT
  framework said: NO TRADE (grade C); against the framework: True
  recorded: stop 1.87782, stop_pips 10.2, target (none), r_to_target (none)
  H4 bar of the check 2026-09-09 18:00 PDT; horizon ends with the bar opening 2026-09-16 18:00 PDT; exit close 1.88235; highest high 1.89512, lowest low 1.87722 over the 30 bars
  status: graded
  price setup_check measured from (recovered) 1.87680; previous D1 close 1.8768; inside the check hour's range: False -> recorded stop_pips 10.2 is a distance from that, not from the market
  E2 close of the check's H4 bar 1.87749; E3 open of the next H1 bar (2026-09-09 22:00 PDT) 1.8775
  E2: risk 3.3 pips -> R -1.00 (stop hit True)
  E3: risk 3.2 pips -> R -1.00 (stop hit True)
  stop touched in the rest of the check's H4 bar (H1): False

## Row 6: GBP_AUD SHORT at 2026-09-10 18:38 PDT
  framework said: SHORT (grade B); against the framework: False
  recorded: stop 1.89716, stop_pips 92.6, target 1.8732, r_to_target invalid
  H4 bar of the check 2026-09-10 18:00 PDT; horizon ends with the bar opening 2026-09-17 18:00 PDT; exit close 1.87533; highest high 1.89512, lowest low 1.87414 over the 30 bars
  target reached within the 30 bars: False
  status: graded
  price setup_check measured from (recovered) 1.88790; previous D1 close 1.88794; inside the check hour's range: False -> recorded stop_pips 92.6 is a distance from that, not from the market
  E2 close of the check's H4 bar 1.88568; E3 open of the next H1 bar (2026-09-10 19:00 PDT) 1.88656
  E2: risk 114.8 pips -> R +0.90 (stop hit False)
  E3: risk 106.0 pips -> R +1.06 (stop hit False)
  stop touched in the rest of the check's H4 bar (H1): False

```
