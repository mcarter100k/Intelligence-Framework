# Spec: carry after a quiet week (pre-registered test on the 2005–2013 STUDY data)

**Status:** pre-registered 2026-10-29 at the owner's direction ("let's do both
and be very thorough"). This file, the runner
(`studies/carry_quiet_week_test.py`) and the rates table
(`studies/policy_rates_2003_2014.json`) are committed together, and their
sha256 is recorded in validation_log in the same commit. No 2005–2013 outcome
has been computed. The run happens once, after this commit; its output goes
to validation_log verbatim, whatever it says.

## 1. Where the idea came from, and what is actually tested

- **The exploratory observation** (2021–2026 USED span, learning only;
  `studies/weekly_range_study_report.md`): GBP/JPY weeks quieter than the
  pair's previous 26-week median closed up 67% of the time (CI 58–75%).
  - That is a **same-week** observation. A week is only known to be quiet
    once it has ended, so it cannot be traded as it stands.
- **The reason it might be real:** carry. In calm markets, borrowing the
  low-rate currency to hold the high-rate one pushes the high-rate side up.
  The same study found quiet weeks tend to follow quiet weeks
  (volatility clustering).
- **The tradeable hypothesis tested here:** after a quiet week, hold the
  carry side (buy the higher-yielding currency) for the whole of the next
  week. The average result is above zero after spread and financing.
- **Two cells, each its own question:**
  - **CQW_GBPJPY:** the carry side is long (UK rates were above Japan's
    throughout 2005–2013).
  - **CQW_GBPAUD:** the carry side is short (Australian rates were above UK
    rates throughout 2005–2013).
  - The side is computed from the rates table for every trade week, not
    assumed.

## 2. Data

- **Source:** OANDA mid D1 and H4 candles, STUDY trading days
  2005-01-01 → 2013-12-30 (data_map_spec §1 and the §11.2 embargo). Fetched
  through `history_study_gate_s3.fetch`, which refuses the embargo and the
  sealed exam before and after each request.
- **Conversion:** the approved weekend rule (`studies/history_study_convert.py`;
  study_weekend_candle_spec.md §6). The data passed §3 items 1–4 and the
  Monday re-check (validation_log 2026-10-22).
- **Weeks:** the Monday–Friday sessions sharing an ISO week of their session
  date.
  - Open = the first session's open, which after the fold is the Sunday
    open. Close = the last session's close.
  - Range = highest high − lowest low.
  - Weeks with fewer than 3 sessions are excluded.

## 3. The rule

- **Quiet week t:** range_t ≤ the median range of the 26 included weeks
  before it. The first 26 weeks are warm-up.
- **Trade week t+1:** the week immediately after t (exactly 7 days later).
  No trade if that week is missing or excluded.
- **Side:** the sign of (base rate − quote rate) on the trade week's first
  session. Rates come from `policy_rates_2003_2014.json`: Bank of England
  Bank Rate, the RBA cash rate target, and the Bank of Japan overnight call
  rate target. Sources and page checksums are inside the file.
- **Entry and exit:** in at the trade week's open, out at its close. No
  stop: the hypothesis is about the week's drift, and a stop would change
  the question.

## 4. Costs (charged on every trade)

- **Spread, round trip, by era** (data_map_spec §4): GBP/AUD 10 pips
  (2005–09) and 7 pips (2010–13); GBP/JPY 6 and 5 pips.
- **Financing:** the carry side receives |rate gap| − **1.0% a year**
  (broker markup; the net can be negative).
  - It is paid for **6 days**: rollovers on Mon, Tue, Wed (×3) and Thu, with
    the exit before Friday's 17:00 New York rollover.
  - Formula: entry price × net rate × 6/365, in pips.

## 5. The measure

- **Outcome per trade:** pips = side × (close − open) − spread + financing.
- **Primary measure:** the same in **typical-week units**, dividing by the
  median range of the 26 weeks ending at the signal week.
  - This sizes every trade to the same risk, so the volatile 2008 weeks do
    not swamp nine years.
  - Pips are reported as a secondary measure.

## 6. The test

- **Statistic:** the mean of the primary measure, per cell.
- **Pass bar:** a **one-sided 95% lower confidence bound** from a percentile
  bootstrap (10,000 resamples, seed `cqw:<pair>`).
  - 95%, not 90%, because there are two cells (a Šidák adjustment at a 90%
    family level ≈ 94.9%).
- **Cross-check:** a normal-approximation bound is reported beside it. It is
  not part of the verdict.

## 7. Verdict per cell (decided now)

| Verdict | Condition |
|---|---|
| **SUPPORTED** | lower bound > 0 **and** the mean without the single best week > 0 |
| **REFUTED** | mean ≤ 0 |
| **INCONCLUSIVE** | anything else, including a positive mean whose bound is ≤ 0, or one carried by a single week |

- **SUPPORTED** is the strongest verdict this data can give. It is not
  VALIDATED. Learning-span and study-span results answer "does this survive
  conditions it wasn't designed on", not "does this work" (data_map_spec §5).
- A SUPPORTED cell becomes a candidate for the one-shot SEALED EXAM
  (data_map_spec §7: one candidate, a frozen exam spec, one run) and for
  micro-size forward trades. Both are separate decisions.
- REFUTED or INCONCLUSIVE is logged with the same care, and the idea is
  closed or parked.

## 8. Power (stated before the run)

- **Expected size:** about 222 quiet-week trades per pair, from 9 years ≈
  469 weeks, less 26 warm-up weeks, about half of them quiet.
- **Spread of weekly outcomes** (2021–2026 data, learning only): standard
  deviation 0.68 typical-week units (GBP/AUD) and 0.72 (GBP/JPY).
- **What the test can detect:** at 80% power, a true mean of about
  **+0.11 to +0.12 typical-week units**. At recent weekly ranges that is
  roughly **30–40 pips a week**.
- **The consequence:** carry alone, about 10 pips a week at a 4% rate gap,
  is below what this test can see. An effect that small will most likely
  read **INCONCLUSIVE**, not SUPPORTED. That is the test being honest about
  its reach, not a failure.

## 9. Secondary analyses (reported; never change a verdict; no multiple-test correction, so descriptive only)

1. **Does "quiet" add anything?** The same carry trade in every week, and
   after non-quiet weeks. The quiet-minus-non-quiet difference is reported
   with a 90% bootstrap interval.
2. **Pips:** mean, median, net pips by year, and the average price move,
   spread and financing.
3. **Sub-periods:** 2005-01→2008-06 (before the crisis),
   2008-07→2009-06 (the crisis), 2009-07→2013-12 (after).
4. **Cost sensitivity:** financing markup 0% and 2%; spread ×1.5.
5. **Risk:** worst drawdown, worst week, and longest losing run.

## 10. Run discipline

1. **`selftest`** must print `SELFTEST OK`.
   - It checks a known edge (must pass), a zero edge (passes about 5% of
     the time), a single-week fluke and the boundaries of the verdict rule.
   - It also checks a hand-computed trade, including spread, financing, the
     carry side and the normaliser window.
   - Seven deliberate code mutations each made it fail (validation_log,
     this commit).
2. **`counts`** fetches the data, stores it with its sha256, and prints
   counts only: weeks, exclusions, quiet-week trades per year, and the side
   held. No outcome is computed or shown.
3. **`full`** refuses to run unless the stored data still matches the
   recorded hashes. It runs once. Its output goes to validation_log
   verbatim.

No change to anything above after this commit; a different rule is a new
spec with a new id.
