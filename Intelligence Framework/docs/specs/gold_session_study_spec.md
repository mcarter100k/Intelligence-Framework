# Spec: gold (XAU/USD) session movement study, descriptive (2021-04-27 → 2026-09-09)

**Status:** FROZEN 2026-11-10, owner request ("add gold as a practice chart;
run the session study first"). Committed before the wrapper exists and
before any gold session statistic is computed.

**Free zone:** studies, tests and data outside the repo. No protected module,
no ledger, no SEALED EXAM bar.
- Gold is **not tradeable** on the OANDA account (probe 2026-11-10); this is
  for a practice markup only.
- Gold is outside the data map's partition (which covers GBP/AUD and GBP/JPY
  only); its 2014–2021 data has never been fetched. **This study uses no
  2014–2021 bar and proves nothing.** The USED span is learning only.

## 1. Question

**When during the day does gold move?** Same purpose and limits as
`session_movement_study_spec.md` §1: descriptive, no entries, no direction,
no costs, no claim about profitability.

## 2. Data

`~/intel_study_archives/leg_data/modern/` (fetched 2026-11-05 through the
guarded modern fetch; validated in `studies/leg_data_report.md`: in the USED
span, hourly bars rebuild every 4-hour bar exactly and daily bars match):

| File | sha256 |
|---|---|
| XAU_USD_H1.csv | `f57466f89b9e1ee8f5bb4f85967ab018a0a57b6ec325df2271afc0579fac2ef0` |
| XAU_USD_H4.csv | `4b47947d319735a068560e2e20411426cbeb286fdb751e2e5e57a10c39a96892` |
| XAU_USD_D.csv | `3f78111011d647aa223e51984249e805534747cdf9ecfe12c0fd74f4e0493f0a` |

**Window:** study days from 2021-04-27 to 2026-09-09, the same as the GBP
replication.

## 3. Method: the unmodified runner, driven by a wrapper

As in the replication (`session_movement_replication_spec.md` §3):
- The code pins on `session_movement_study.py`, `session_movement_data.py`
  and `history_study_convert.py` must equal their values at 2f7c68b.
- `studies/gold_session_study.py` rebinds only these inputs:

| Input | Value | Why |
|---|---|---|
| Instrument list | `("XAU_USD",)` | the one instrument studied |
| Unit | `{"XAU_USD": 1.0}` | every figure the runner labels "pips" is **US dollars** for gold |
| Hash table | the three gold files above | the data pins |
| Day window | 2021-04-27 → 2026-09-09 | the same as the GBP replication |
| `session_movement_data.expected_hours` | the FX window minus every hour opening at **17:00 New York** | Gold has a daily one-hour trading break (5–6 PM New York). Checked 2026-11-10: 0 gold H1 bars open at 17:00 New York, against 1,435 for GBP/AUD over the same years. Without this change no gold day would ever count as complete. |

- Everything else is the same as the original spec: the five questions, the
  fixed UTC blocks, the definitions and the two reading rules (§5 DST steps,
  §6 evenness).
- **No control run is needed:** the rebound `expected_hours` is the only
  change in a definition, it is gold-specific, and a test pins it (the
  17:00-New-York hour removed, every other hour unchanged).

## 4. Reported

- The runner's own output, verbatim.
- A plain-English summary in Pacific time. It is set beside the published
  GBP/AUD 2021–2026 profile **descriptively only**; nothing is tested between
  the two.
- Anything else noticed is recorded as a hypothesis, not computed.

## 5. Limits

- **Hourly values are consistent, not verified.** They agree with the
  4-hour bars, but no second data source has checked them hour by hour
  (`session_movement_report.md` §6).
- **One era:** 2021–2026.
- **The Pacific clock shifts with daylight saving.** London and New York move
  their clocks; Tokyo does not.
