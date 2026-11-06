# Session movement study, replication: 2021-04-27 → 2026-09-09 (USED) against 2005–2013 (STUDY)

**Spec:** `docs/specs/session_movement_replication_spec.md` (frozen, 9d0365f),
an addendum to `session_movement_study_spec.md` (85e5c19).

**Code:**
- `studies/session_movement_replication.py`, a wrapper that drives the
  unmodified runner;
- `studies/session_movement_compare.py`, the side-by-side comparison.

**What it is not:** descriptive only. USED is learning only, never proof.
**Nothing here says whether day trading these pairs would make money.**
Times are Pacific (PST / PDT), with UTC alongside.

---

## 1. Ordering: spec before any statistic

| Event | Pacific | UTC |
|---|---|---|
| **Addendum spec committed, 9d0365f** (wrapper and comparison did not exist: `ls` → "No such file") | **2026-11-05 22:40:46 PST** | 2026-11-06 06:40:46 |
| Wrapper + comparison committed, 398c91b | 22:42:43 PST | 06:42:43 |
| Control run (2005–2013 inputs) | 22:42:53 PST | 06:42:53 |
| **Modern run, first computation** | **22:43:15 PST** | 06:43:15 |
| Comparison-summary fix committed, 4754684 (see §3) | 22:43:59 PST | 06:43:59 |

The first USED-span statistic was computed 2 min 29 s after the addendum
spec was committed.

## 2. The control: the wrapper changes nothing in the computation

**Code pins.** Before any computation, the wrapper hashes the three files the
computation depends on. All three equal their values at the original run
(2f7c68b):

| File | sha256 |
|---|---|
| `session_movement_study.py` | `2302ab42…935d` |
| `session_movement_data.py` | `3f2d4314…55ff1` |
| `history_study_convert.py` | `584ff76d…a553` |

**The control run.** It went through the same rebinding path, with the
2005–2013 inputs.
- **Its stdout equals the published run's stdout: 32,672 of 32,672 bytes,
  with only the two timestamp lines removed from each side.**
  - Published: run start 04:56:37 UTC.
  - Control: run start 06:42:53 UTC.
- **The comparison can fail:** changing one digit in a copy of the control
  output (the GBP/AUD 14:00 mean, 60.2 → 60.3) made it FAIL.
- **Runs:** exit 0, stderr empty, and the project unchanged by hash, for the
  control, the modern run and the comparison.

## 3. Correction during the run

- **What happened:** the comparison's first output ended with a summary line
  that miscounted: "5 of 20 Q3 comparisons and 2 ratio comparisons". It
  listed 3 Q3 items and 2 ratio items.
- **What it did not affect:** every verdict in the tables was right.
- **The fix:** the summary now counts the two kinds separately (4754684,
  pinned by two tests). The comparison was re-run on the same inputs.
- **Checked:** the diff between the two outputs is that one line.

## 4. Whether the 2005–2013 picture holds on modern data (plain English)

**The shape of the day holds.**
- **Same two busy windows:** the London morning, 07:00–09:00 UTC (23:00–01:00
  PST), and the London/New York overlap, 12:00–15:00 UTC (04:00–07:00 PST).
- **Same busiest hour:** 14:00 UTC (06:00 PST / 07:00 PDT), in both pairs and
  both periods.
- **Prices move less.** Every hour moves fewer pips than it did in
  2005–2013.

**The concentration is stronger now. This is a MATERIAL difference** (single
gate: no significance test was possible).
- **The ratios:** the busiest hour now moves 2.40 times the quietest for
  GBP/AUD (was 1.77), and 2.53 times for GBP/JPY (was 1.92).
- **Where the change comes from:** mostly the quiet hours getting relatively
  quieter.
  - The late New York afternoon is now GBP/AUD's quietest hour: 20:00 UTC,
    12:00 PST.
  - The 2005–2013 quietest hour was 04:00 UTC.

**Where the daily high and low form is mostly unchanged.**
- **17 of 20 comparisons are CONSISTENT WITH THE EARLIER PERIOD.**
- **Three are MATERIAL**, passing both gates:
  - **GBP/AUD lows form more often in the Tokyo block:** 25.7% of days,
    was 16.9% (+8.8 points).
  - **GBP/AUD lows form less often in the New York afternoon:** 18.3%, was
    25.2% (−6.9).
  - **GBP/JPY highs form less often in the Sydney block** (the first three
    hours of the day): 14.5%, was 19.6% (−5.1).
- **One passed the statistical gate only,** so it is CONSISTENT: GBP/AUD
  highs in the overlap block (+4.4 points).
- **Still no block owns the day.** The largest share of highs or lows in any
  block is 26.3% (GBP/AUD) and 24.5% (GBP/JPY).

**Extremes are still mostly set by the Pacific morning.** By 15:00 UTC (07:00
PST), the day's high is already in place on 74% (GBP/AUD) and 70% (GBP/JPY)
of days. The low is in place on 75% and 78%. The 2005–2013 figures were
69–75%. This was shown, not tested.

**Volatility: ATR, numbers only.** No rule is proposed. The figures are for
the team's separate stop-floor question.

| Mean ATR (pips) | 1-hour | 4-hour | Daily |
|---|---|---|---|
| GBP/AUD 2005–2013 | 46.2 | 89.5 | 216.5 |
| GBP/AUD 2021–2026 | 26.5 | 53.8 | 136.3 |
| GBP/JPY 2005–2013 | 39.8 | 79.7 | 200.6 |
| GBP/JPY 2021–2026 | 29.7 | 61.3 | 159.2 |

These are means over the whole USED span. The "~104 / ~136" quoted for
"now" was not a repo figure (spec §8).

**Day-trading precondition** (fixed in the spec: busiest hour more than
2.5 × the quietest, AND a block holding ≥ 35% of highs or of lows):

| Pair | Busiest ÷ quietest | Largest block share | Result |
|---|---|---|---|
| GBP/AUD | 2.40 | 26.3% | **FAIL** |
| GBP/JPY | 2.53 | 24.5% | **FAIL** |

**DST boundary rule:** no sharp step at any block boundary in either pair
(modern steps 0.72–1.49). The modern run's own reading rules are in §8 below.

## 5. Hypotheses recorded, NOT computed

1. **The fall in GBP/JPY highs in the Sydney block** may be the 2005–2013
   weekend-fold artifact disappearing. Modern data has no folded weekend
   quoting.
   - Test: compare Mondays against Tuesday–Friday in each period.
   - This is hypothesis 3 of the original report.
2. **GBP/AUD's lows have moved from the New York afternoon to the Tokyo
   block.** Is this tied to the Australian session gaining weight in
   GBP/AUD's daily range? Its Tokyo-block median share rose from 0.48 to
   0.54 (shown, not tested).
3. **The stronger concentration** may come from the late New York hours
   thinning, rather than the busy hours getting busier. Test: compare each
   hour's share of the day's total range between periods.
4. **The day of the week** might show where the changes sit. The modern
   weekday tables are in the verbatim output and were not compared.

## 6. Limits carried

- **The verification caveat applies to both periods**
  (`session_movement_report.md` §6, "What the data check did not verify").
  The hourly figures are consistent with verified 4-hour data, not verified
  bar by bar.
  - Q1 and the busiest-to-quietest ratio are built mostly from unverified
    hourly values.
  - Q3 and Q4 are proven only to the 4-hour block.
  - Hourly ATR is unverified; 4-hour and daily ATR rest on checked bars.
  - A second, independent data source would close the gap. None has been
    sourced.
- **The ratio comparison is single-gate.** The runner's outputs carry no
  spread, so no significance test was possible.
- **The Q3 tests use the printed one-decimal percentages.** That is at most
  0.05 points of rounding.
- **The periods differ in more than era.**
  - 2005–2013 carries folded weekend quoting.
  - 2021–2026 has none.
  - The fixed UTC blocks smear by one hour twice a year in both.
- **The weekday breakdown was not compared** (spec §4).

---

## 7. Side-by-side comparison (verbatim output of `session_movement_compare.py`, after the summary fix)

`scripts/reality_run.py --no-env --code <worktree> script <worktree>/studies/session_movement_compare.py <worktree>/studies/session_movement_report.md <modern stdout>`
gave exit 0, stderr 0 bytes, project UNCHANGED.

```
# Side by side: 2005–2013 (STUDY) against 2021-04-27 → 2026-09-09 (USED)

Šidák per-comparison α for 20 comparisons: 0.0026 (family-wise rate at a naive 0.05 each: 64%).


## GBP_AUD

### Q1. Hourly range (pips; levels differ with each era's volatility — compare shapes)

| UTC hour | Pacific | 2005–2013 mean | median | 2021–2026 mean | median |
|---|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 37.8 | 29.5 | 22.2 | 18.6 |
| 22:00 | 14:00 PST / 15:00 PDT | 38.4 | 29.8 | 20.6 | 17.1 |
| 23:00 | 15:00 PST / 16:00 PDT | 39.2 | 31.0 | 18.3 | 15.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 46.7 | 36.3 | 27.3 | 22.8 |
| 01:00 | 17:00 PST / 18:00 PDT | 46.3 | 35.9 | 30.7 | 26.4 |
| 02:00 | 18:00 PST / 19:00 PDT | 35.2 | 29.3 | 25.8 | 22.8 |
| 03:00 | 19:00 PST / 20:00 PDT | 35.5 | 27.0 | 23.4 | 20.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 34.1 | 26.0 | 21.9 | 17.3 |
| 05:00 | 21:00 PST / 22:00 PDT | 37.4 | 29.4 | 23.2 | 19.9 |
| 06:00 | 22:00 PST / 23:00 PDT | 46.3 | 39.0 | 28.7 | 25.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 53.0 | 44.4 | 32.8 | 29.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 55.5 | 45.6 | 32.0 | 28.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 54.0 | 44.0 | 28.8 | 25.5 |
| 10:00 | 02:00 PST / 03:00 PDT | 49.3 | 40.2 | 27.9 | 24.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 48.1 | 38.7 | 28.1 | 23.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 54.7 | 43.1 | 33.3 | 28.4 |
| 13:00 | 05:00 PST / 06:00 PDT | 56.0 | 45.0 | 35.8 | 31.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 60.2 | 48.3 | 39.1 | 35.2 |
| 15:00 | 07:00 PST / 08:00 PDT | 57.5 | 45.9 | 34.5 | 30.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 48.3 | 37.8 | 25.0 | 21.8 |
| 17:00 | 09:00 PST / 10:00 PDT | 42.4 | 33.0 | 21.6 | 18.8 |
| 18:00 | 10:00 PST / 11:00 PDT | 42.7 | 33.0 | 19.8 | 16.4 |
| 19:00 | 11:00 PST / 12:00 PDT | 42.0 | 30.6 | 17.8 | 14.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 38.6 | 29.0 | 16.3 | 13.7 |

Busiest ÷ quietest hour: 2005–2013 1.77 (busiest 14:00, quietest 04:00 UTC); 2021–2026 2.40 (busiest 14:00, quietest 20:00 UTC); difference +0.63 → **MATERIAL — SINGLE-GATE**

### Q2. Median share of the day's range, per block

| block | 2005–2013 | 2021–2026 |
|---|---|---|
| SYDNEY | 0.297 | 0.237 |
| TOKYO | 0.483 | 0.543 |
| LONDON | 0.531 | 0.510 |
| LDN_NY | 0.522 | 0.543 |
| NY_PM | 0.394 | 0.312 |

### Q3. Where the daily high and low form (N days 2325 and 1386)

| block | extreme | 2005–2013 | 2021–2026 | difference (pts) | z | p (two-sided) | p < 0.05 | p < 0.0026 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| SYDNEY | high | 20.7% | 17.6% | -3.1 | -2.30 | 0.0212 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| SYDNEY | low | 18.0% | 15.1% | -2.9 | -2.28 | 0.0226 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| TOKYO | high | 22.4% | 26.3% | +3.9 | +2.70 | 0.0070 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| TOKYO | low | 16.9% | 25.7% | +8.8 | +6.46 | 0.0000 | yes | yes | MATERIAL |
| LONDON | high | 16.7% | 14.2% | -2.5 | -2.02 | 0.0432 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| LONDON | low | 19.9% | 18.2% | -1.7 | -1.27 | 0.2040 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| LDN_NY | high | 17.5% | 21.9% | +4.4 | +3.30 | 0.0010 | yes | yes | CONSISTENT WITH THE EARLIER PERIOD (statistical gate only) |
| LDN_NY | low | 20.0% | 22.7% | +2.7 | +1.95 | 0.0508 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| NY_PM | high | 22.7% | 20.1% | -2.6 | -1.86 | 0.0632 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| NY_PM | low | 25.2% | 18.3% | -6.9 | -4.86 | 0.0000 | yes | yes | MATERIAL |

High and low in the same block: 2005–2013 3.6%, 2021–2026 4.3% (shown, not tested)

### Q4. Share of days with the extreme already in place

| by | 2005–2013 high | 2021–2026 high | 2005–2013 low | 2021–2026 low |
|---|---|---|---|---|
| hour 6 | 34.2% | 32.8% | 27.7% | 29.2% |
| hour 12 | 50.9% | 50.1% | 44.1% | 50.1% |
| hour 18 | 71.9% | 73.8% | 69.0% | 75.4% |

### Q5. Mean ATR(14), pips (numbers only)

| timeframe | 2005–2013 | 2021–2026 |
|---|---|---|
| H1 | 46.2 | 26.5 |
| H4 | 89.5 | 53.8 |
| D1 | 216.5 | 136.3 |

## GBP_JPY

### Q1. Hourly range (pips; levels differ with each era's volatility — compare shapes)

| UTC hour | Pacific | 2005–2013 mean | median | 2021–2026 mean | median |
|---|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 27.9 | 21.8 | 17.7 | 15.0 |
| 22:00 | 14:00 PST / 15:00 PDT | 29.7 | 23.5 | 20.9 | 16.4 |
| 23:00 | 15:00 PST / 16:00 PDT | 33.3 | 26.6 | 23.3 | 18.7 |
| 00:00 | 16:00 PST / 17:00 PDT | 41.3 | 33.2 | 33.7 | 29.1 |
| 01:00 | 17:00 PST / 18:00 PDT | 36.5 | 29.8 | 30.4 | 25.8 |
| 02:00 | 18:00 PST / 19:00 PDT | 30.2 | 24.0 | 24.5 | 20.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 28.7 | 22.2 | 22.6 | 17.6 |
| 04:00 | 20:00 PST / 21:00 PDT | 29.2 | 22.2 | 22.0 | 17.4 |
| 05:00 | 21:00 PST / 22:00 PDT | 32.9 | 26.0 | 24.0 | 19.8 |
| 06:00 | 22:00 PST / 23:00 PDT | 41.8 | 34.7 | 33.0 | 27.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 50.4 | 41.9 | 40.8 | 34.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 52.7 | 44.6 | 40.2 | 34.7 |
| 09:00 | 01:00 PST / 02:00 PDT | 48.8 | 40.0 | 34.9 | 29.6 |
| 10:00 | 02:00 PST / 03:00 PDT | 43.6 | 35.8 | 31.3 | 27.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 42.0 | 33.7 | 32.3 | 27.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 49.5 | 38.8 | 38.6 | 32.1 |
| 13:00 | 05:00 PST / 06:00 PDT | 50.5 | 41.0 | 41.2 | 35.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 53.5 | 43.0 | 44.6 | 38.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 49.9 | 39.9 | 38.1 | 32.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 40.6 | 32.1 | 29.0 | 24.7 |
| 17:00 | 09:00 PST / 10:00 PDT | 36.1 | 27.8 | 25.1 | 21.2 |
| 18:00 | 10:00 PST / 11:00 PDT | 35.2 | 26.5 | 23.0 | 18.4 |
| 19:00 | 11:00 PST / 12:00 PDT | 33.4 | 24.6 | 20.5 | 16.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 29.2 | 22.6 | 18.1 | 14.4 |

Busiest ÷ quietest hour: 2005–2013 1.92 (busiest 14:00, quietest 21:00 UTC); 2021–2026 2.53 (busiest 14:00, quietest 21:00 UTC); difference +0.61 → **MATERIAL — SINGLE-GATE**

### Q2. Median share of the day's range, per block

| block | 2005–2013 | 2021–2026 |
|---|---|---|
| SYDNEY | 0.260 | 0.220 |
| TOKYO | 0.460 | 0.468 |
| LONDON | 0.571 | 0.548 |
| LDN_NY | 0.535 | 0.538 |
| NY_PM | 0.364 | 0.329 |

### Q3. Where the daily high and low form (N days 2327 and 1386)

| block | extreme | 2005–2013 | 2021–2026 | difference (pts) | z | p (two-sided) | p < 0.05 | p < 0.0026 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| SYDNEY | high | 19.6% | 14.5% | -5.1 | -3.94 | 0.0001 | yes | yes | MATERIAL |
| SYDNEY | low | 17.2% | 16.9% | -0.3 | -0.23 | 0.8143 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| TOKYO | high | 19.5% | 20.2% | +0.7 | +0.52 | 0.6044 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| TOKYO | low | 20.6% | 23.8% | +3.2 | +2.28 | 0.0223 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| LONDON | high | 19.2% | 18.5% | -0.7 | -0.53 | 0.5985 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| LONDON | low | 22.5% | 20.2% | -2.3 | -1.65 | 0.0997 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| LDN_NY | high | 18.7% | 22.3% | +3.6 | +2.65 | 0.0080 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |
| LDN_NY | low | 20.7% | 22.9% | +2.2 | +1.58 | 0.1146 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| NY_PM | high | 23.0% | 24.5% | +1.5 | +1.04 | 0.2975 | no | no | CONSISTENT WITH THE EARLIER PERIOD |
| NY_PM | low | 19.0% | 16.2% | -2.8 | -2.15 | 0.0315 | yes | no | CONSISTENT WITH THE EARLIER PERIOD |

High and low in the same block: 2005–2013 4.7%, 2021–2026 5.5% (shown, not tested)

### Q4. Share of days with the extreme already in place

| by | 2005–2013 high | 2021–2026 high | 2005–2013 low | 2021–2026 low |
|---|---|---|---|---|
| hour 6 | 30.3% | 25.6% | 29.0% | 31.2% |
| hour 12 | 48.2% | 44.4% | 49.1% | 51.7% |
| hour 18 | 72.4% | 70.0% | 74.6% | 77.9% |

### Q5. Mean ATR(14), pips (numbers only)

| timeframe | 2005–2013 | 2021–2026 |
|---|---|---|
| H1 | 39.8 | 29.7 |
| H4 | 79.7 | 61.3 |
| D1 | 200.6 | 159.2 |

## Day-trading precondition (USED span; ratio > 2.5 AND a block ≥ 35% of highs or lows)

| pair | busiest ÷ quietest | largest block share of highs or lows | result |
|---|---|---|---|
| GBP_AUD | 2.40 | 26.3% | **FAIL** |
| GBP_JPY | 2.53 | 24.5% | **FAIL** |

## Materiality summary

MATERIAL differences: 3 of 20 Q3 comparisons (GBP_AUD TOKYO low, GBP_AUD NY_PM low, GBP_JPY SYDNEY high); 2 of 2 ratio comparisons, single-gate (GBP_AUD, GBP_JPY).
```

## 8. Modern run (verbatim stdout of `session_movement_replication.py modern`)

`scripts/reality_run.py --no-env --code <worktree> script <worktree>/studies/session_movement_replication.py modern ~/intel_study_archives/modern_data` gave exit 0, stderr 0 bytes, project UNCHANGED.

```
run start (UTC): 2026-11-06T06:43:15+00:00
hash GBP_AUD_H1.csv: OK
hash GBP_JPY_H1.csv: OK
hash GBP_AUD_H4.csv: OK
hash GBP_AUD_D.csv: OK
hash GBP_JPY_H4.csv: OK
hash GBP_JPY_D.csv: OK
first computation start (UTC): 2026-11-06T06:43:15+00:00


## GBP_AUD

Study days with bars 1399; complete 1386; fold bars excluded from Q1 0

### Q1. Hourly range profile

**Q1 GBP_AUD, all weekdays** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 1305 | 22.2 | 18.6 |
| 22:00 | 14:00 PST / 15:00 PDT | 1393 | 20.6 | 17.1 |
| 23:00 | 15:00 PST / 16:00 PDT | 1394 | 18.3 | 15.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 1395 | 27.3 | 22.8 |
| 01:00 | 17:00 PST / 18:00 PDT | 1395 | 30.7 | 26.4 |
| 02:00 | 18:00 PST / 19:00 PDT | 1395 | 25.8 | 22.8 |
| 03:00 | 19:00 PST / 20:00 PDT | 1395 | 23.4 | 20.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 1395 | 21.9 | 17.3 |
| 05:00 | 21:00 PST / 22:00 PDT | 1395 | 23.2 | 19.9 |
| 06:00 | 22:00 PST / 23:00 PDT | 1395 | 28.7 | 25.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 1395 | 32.8 | 29.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 1395 | 32.0 | 28.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 1395 | 28.8 | 25.5 |
| 10:00 | 02:00 PST / 03:00 PDT | 1395 | 27.9 | 24.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 1395 | 28.1 | 23.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 1395 | 33.3 | 28.4 |
| 13:00 | 05:00 PST / 06:00 PDT | 1395 | 35.8 | 31.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 1395 | 39.1 | 35.2 |
| 15:00 | 07:00 PST / 08:00 PDT | 1395 | 34.5 | 30.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 1395 | 25.0 | 21.8 |
| 17:00 | 09:00 PST / 10:00 PDT | 1395 | 21.6 | 18.8 |
| 18:00 | 10:00 PST / 11:00 PDT | 1395 | 19.8 | 16.4 |
| 19:00 | 11:00 PST / 12:00 PDT | 1395 | 17.8 | 14.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 1395 | 16.3 | 13.7 |

**Q1 GBP_AUD, Mon** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 190 | 35.6 | 27.3 |
| 22:00 | 14:00 PST / 15:00 PDT | 275 | 30.4 | 26.2 |
| 23:00 | 15:00 PST / 16:00 PDT | 276 | 23.5 | 18.4 |
| 00:00 | 16:00 PST / 17:00 PDT | 277 | 28.4 | 23.4 |
| 01:00 | 17:00 PST / 18:00 PDT | 277 | 30.5 | 26.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 277 | 24.2 | 21.0 |
| 03:00 | 19:00 PST / 20:00 PDT | 277 | 21.3 | 19.1 |
| 04:00 | 20:00 PST / 21:00 PDT | 277 | 19.1 | 15.8 |
| 05:00 | 21:00 PST / 22:00 PDT | 277 | 22.6 | 18.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 277 | 26.8 | 22.5 |
| 07:00 | 23:00 PST / 00:00 PDT | 277 | 30.8 | 27.8 |
| 08:00 | 00:00 PST / 01:00 PDT | 277 | 30.0 | 27.1 |
| 09:00 | 01:00 PST / 02:00 PDT | 277 | 28.6 | 24.8 |
| 10:00 | 02:00 PST / 03:00 PDT | 277 | 26.4 | 23.8 |
| 11:00 | 03:00 PST / 04:00 PDT | 277 | 26.6 | 22.5 |
| 12:00 | 04:00 PST / 05:00 PDT | 277 | 28.9 | 25.5 |
| 13:00 | 05:00 PST / 06:00 PDT | 277 | 31.3 | 28.1 |
| 14:00 | 06:00 PST / 07:00 PDT | 277 | 35.5 | 32.1 |
| 15:00 | 07:00 PST / 08:00 PDT | 277 | 31.1 | 26.3 |
| 16:00 | 08:00 PST / 09:00 PDT | 277 | 22.5 | 19.1 |
| 17:00 | 09:00 PST / 10:00 PDT | 277 | 19.8 | 17.3 |
| 18:00 | 10:00 PST / 11:00 PDT | 277 | 16.8 | 14.1 |
| 19:00 | 11:00 PST / 12:00 PDT | 277 | 15.5 | 13.3 |
| 20:00 | 12:00 PST / 13:00 PDT | 277 | 13.7 | 11.6 |

**Q1 GBP_AUD, Tue** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 18.7 | 15.7 |
| 22:00 | 14:00 PST / 15:00 PDT | 281 | 17.8 | 15.0 |
| 23:00 | 15:00 PST / 16:00 PDT | 281 | 16.5 | 14.0 |
| 00:00 | 16:00 PST / 17:00 PDT | 281 | 25.5 | 22.2 |
| 01:00 | 17:00 PST / 18:00 PDT | 281 | 28.7 | 25.6 |
| 02:00 | 18:00 PST / 19:00 PDT | 281 | 25.4 | 22.8 |
| 03:00 | 19:00 PST / 20:00 PDT | 281 | 28.5 | 21.8 |
| 04:00 | 20:00 PST / 21:00 PDT | 281 | 28.9 | 19.1 |
| 05:00 | 21:00 PST / 22:00 PDT | 281 | 26.3 | 21.7 |
| 06:00 | 22:00 PST / 23:00 PDT | 281 | 30.6 | 26.6 |
| 07:00 | 23:00 PST / 00:00 PDT | 281 | 34.9 | 31.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 281 | 32.8 | 28.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 281 | 29.6 | 26.4 |
| 10:00 | 02:00 PST / 03:00 PDT | 281 | 26.7 | 24.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 281 | 26.8 | 23.9 |
| 12:00 | 04:00 PST / 05:00 PDT | 281 | 31.4 | 28.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 281 | 34.6 | 31.2 |
| 14:00 | 06:00 PST / 07:00 PDT | 281 | 39.3 | 35.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 281 | 35.2 | 31.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 281 | 25.6 | 22.6 |
| 17:00 | 09:00 PST / 10:00 PDT | 281 | 20.8 | 18.6 |
| 18:00 | 10:00 PST / 11:00 PDT | 281 | 18.7 | 16.0 |
| 19:00 | 11:00 PST / 12:00 PDT | 281 | 16.5 | 14.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 281 | 14.9 | 12.8 |

**Q1 GBP_AUD, Wed** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 281 | 19.8 | 17.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 279 | 18.6 | 15.4 |
| 23:00 | 15:00 PST / 16:00 PDT | 279 | 17.0 | 14.8 |
| 00:00 | 16:00 PST / 17:00 PDT | 279 | 29.0 | 24.6 |
| 01:00 | 17:00 PST / 18:00 PDT | 279 | 33.9 | 28.9 |
| 02:00 | 18:00 PST / 19:00 PDT | 279 | 27.7 | 24.6 |
| 03:00 | 19:00 PST / 20:00 PDT | 279 | 22.4 | 20.4 |
| 04:00 | 20:00 PST / 21:00 PDT | 279 | 20.8 | 17.4 |
| 05:00 | 21:00 PST / 22:00 PDT | 279 | 22.4 | 19.8 |
| 06:00 | 22:00 PST / 23:00 PDT | 279 | 29.8 | 24.7 |
| 07:00 | 23:00 PST / 00:00 PDT | 279 | 34.1 | 29.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 279 | 33.0 | 29.2 |
| 09:00 | 01:00 PST / 02:00 PDT | 279 | 28.2 | 26.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 279 | 28.7 | 26.2 |
| 11:00 | 03:00 PST / 04:00 PDT | 279 | 27.6 | 23.8 |
| 12:00 | 04:00 PST / 05:00 PDT | 279 | 33.3 | 27.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 279 | 36.3 | 32.2 |
| 14:00 | 06:00 PST / 07:00 PDT | 279 | 38.6 | 34.8 |
| 15:00 | 07:00 PST / 08:00 PDT | 279 | 34.3 | 30.4 |
| 16:00 | 08:00 PST / 09:00 PDT | 279 | 25.1 | 22.1 |
| 17:00 | 09:00 PST / 10:00 PDT | 279 | 22.8 | 18.9 |
| 18:00 | 10:00 PST / 11:00 PDT | 279 | 25.5 | 19.2 |
| 19:00 | 11:00 PST / 12:00 PDT | 279 | 22.7 | 17.4 |
| 20:00 | 12:00 PST / 13:00 PDT | 279 | 17.3 | 14.6 |

**Q1 GBP_AUD, Thu** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 21.8 | 19.6 |
| 22:00 | 14:00 PST / 15:00 PDT | 278 | 18.5 | 15.9 |
| 23:00 | 15:00 PST / 16:00 PDT | 278 | 17.9 | 16.2 |
| 00:00 | 16:00 PST / 17:00 PDT | 278 | 29.0 | 22.9 |
| 01:00 | 17:00 PST / 18:00 PDT | 278 | 32.6 | 27.4 |
| 02:00 | 18:00 PST / 19:00 PDT | 278 | 27.2 | 24.4 |
| 03:00 | 19:00 PST / 20:00 PDT | 278 | 22.9 | 20.7 |
| 04:00 | 20:00 PST / 21:00 PDT | 278 | 20.8 | 17.6 |
| 05:00 | 21:00 PST / 22:00 PDT | 278 | 23.0 | 20.1 |
| 06:00 | 22:00 PST / 23:00 PDT | 278 | 28.6 | 24.9 |
| 07:00 | 23:00 PST / 00:00 PDT | 278 | 32.2 | 28.9 |
| 08:00 | 00:00 PST / 01:00 PDT | 278 | 32.9 | 30.0 |
| 09:00 | 01:00 PST / 02:00 PDT | 278 | 29.3 | 24.5 |
| 10:00 | 02:00 PST / 03:00 PDT | 278 | 29.2 | 26.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 278 | 32.8 | 25.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 278 | 38.5 | 31.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 278 | 38.4 | 34.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 278 | 39.8 | 36.6 |
| 15:00 | 07:00 PST / 08:00 PDT | 278 | 34.8 | 29.9 |
| 16:00 | 08:00 PST / 09:00 PDT | 278 | 26.8 | 23.5 |
| 17:00 | 09:00 PST / 10:00 PDT | 278 | 23.0 | 20.0 |
| 18:00 | 10:00 PST / 11:00 PDT | 278 | 19.1 | 16.5 |
| 19:00 | 11:00 PST / 12:00 PDT | 278 | 17.6 | 15.7 |
| 20:00 | 12:00 PST / 13:00 PDT | 278 | 15.8 | 13.8 |

**Q1 GBP_AUD, Fri** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 19.6 | 17.7 |
| 22:00 | 14:00 PST / 15:00 PDT | 280 | 17.9 | 15.5 |
| 23:00 | 15:00 PST / 16:00 PDT | 280 | 16.7 | 15.1 |
| 00:00 | 16:00 PST / 17:00 PDT | 280 | 24.6 | 21.6 |
| 01:00 | 17:00 PST / 18:00 PDT | 280 | 28.1 | 24.6 |
| 02:00 | 18:00 PST / 19:00 PDT | 280 | 24.6 | 21.5 |
| 03:00 | 19:00 PST / 20:00 PDT | 280 | 21.8 | 18.8 |
| 04:00 | 20:00 PST / 21:00 PDT | 280 | 19.6 | 17.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 280 | 21.9 | 19.8 |
| 06:00 | 22:00 PST / 23:00 PDT | 280 | 27.9 | 24.9 |
| 07:00 | 23:00 PST / 00:00 PDT | 280 | 31.7 | 28.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 280 | 31.0 | 28.4 |
| 09:00 | 01:00 PST / 02:00 PDT | 280 | 28.7 | 25.4 |
| 10:00 | 02:00 PST / 03:00 PDT | 280 | 28.3 | 23.8 |
| 11:00 | 03:00 PST / 04:00 PDT | 280 | 26.8 | 22.8 |
| 12:00 | 04:00 PST / 05:00 PDT | 280 | 34.4 | 29.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 280 | 38.4 | 33.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 280 | 42.3 | 37.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 280 | 36.9 | 32.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 280 | 24.8 | 20.9 |
| 17:00 | 09:00 PST / 10:00 PDT | 280 | 21.5 | 18.8 |
| 18:00 | 10:00 PST / 11:00 PDT | 280 | 19.2 | 16.0 |
| 19:00 | 11:00 PST / 12:00 PDT | 280 | 16.7 | 14.4 |
| 20:00 | 12:00 PST / 13:00 PDT | 280 | 19.8 | 16.4 |

### Q2. Share of daily range by block

Days with zero range excluded: 0. Winter Mondays' SYDNEY block holds 2 bars, not 3.

**Q2 GBP_AUD, all weekdays**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 1386 | 0.271 | 0.125 | 0.176 | 0.237 | 0.332 | 0.462 |
| TOKYO | 1386 | 0.559 | 0.305 | 0.404 | 0.543 | 0.702 | 0.856 |
| LONDON | 1386 | 0.529 | 0.312 | 0.390 | 0.510 | 0.645 | 0.778 |
| LDN_NY | 1386 | 0.564 | 0.330 | 0.415 | 0.543 | 0.693 | 0.842 |
| NY_PM | 1386 | 0.348 | 0.185 | 0.237 | 0.312 | 0.421 | 0.559 |

**Q2 GBP_AUD, Mon**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 275 | 0.385 | 0.200 | 0.263 | 0.351 | 0.476 | 0.599 |
| TOKYO | 275 | 0.552 | 0.304 | 0.414 | 0.520 | 0.692 | 0.836 |
| LONDON | 275 | 0.515 | 0.323 | 0.398 | 0.498 | 0.621 | 0.733 |
| LDN_NY | 275 | 0.529 | 0.308 | 0.387 | 0.513 | 0.636 | 0.811 |
| NY_PM | 275 | 0.319 | 0.173 | 0.230 | 0.289 | 0.380 | 0.510 |

**Q2 GBP_AUD, Tue**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 278 | 0.228 | 0.115 | 0.149 | 0.205 | 0.276 | 0.370 |
| TOKYO | 278 | 0.591 | 0.313 | 0.430 | 0.589 | 0.746 | 0.901 |
| LONDON | 278 | 0.542 | 0.317 | 0.398 | 0.530 | 0.658 | 0.820 |
| LDN_NY | 278 | 0.556 | 0.319 | 0.413 | 0.540 | 0.680 | 0.826 |
| NY_PM | 278 | 0.329 | 0.177 | 0.222 | 0.298 | 0.398 | 0.539 |

**Q2 GBP_AUD, Wed**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 279 | 0.233 | 0.116 | 0.150 | 0.211 | 0.281 | 0.382 |
| TOKYO | 279 | 0.553 | 0.297 | 0.386 | 0.531 | 0.699 | 0.865 |
| LONDON | 279 | 0.509 | 0.291 | 0.377 | 0.490 | 0.621 | 0.730 |
| LDN_NY | 279 | 0.531 | 0.325 | 0.390 | 0.501 | 0.652 | 0.790 |
| NY_PM | 279 | 0.374 | 0.194 | 0.241 | 0.330 | 0.449 | 0.606 |

**Q2 GBP_AUD, Thu**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 276 | 0.255 | 0.122 | 0.179 | 0.229 | 0.301 | 0.403 |
| TOKYO | 276 | 0.558 | 0.287 | 0.388 | 0.532 | 0.712 | 0.853 |
| LONDON | 276 | 0.536 | 0.323 | 0.375 | 0.502 | 0.661 | 0.823 |
| LDN_NY | 276 | 0.583 | 0.348 | 0.445 | 0.559 | 0.709 | 0.846 |
| NY_PM | 276 | 0.341 | 0.188 | 0.239 | 0.311 | 0.414 | 0.539 |

**Q2 GBP_AUD, Fri**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 278 | 0.256 | 0.129 | 0.176 | 0.227 | 0.307 | 0.413 |
| TOKYO | 278 | 0.540 | 0.322 | 0.405 | 0.526 | 0.659 | 0.800 |
| LONDON | 278 | 0.541 | 0.318 | 0.405 | 0.525 | 0.662 | 0.784 |
| LDN_NY | 278 | 0.620 | 0.383 | 0.469 | 0.593 | 0.767 | 0.885 |
| NY_PM | 278 | 0.377 | 0.208 | 0.261 | 0.340 | 0.464 | 0.596 |

### Q3. Where the daily high and low form

**Q3 GBP_AUD, all weekdays** (N days 1386)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 17.6% | 15.1% |
| TOKYO | 26.3% | 25.7% |
| LONDON | 14.2% | 18.2% |
| LDN_NY | 21.9% | 22.7% |
| NY_PM | 20.1% | 18.3% |

High and low in the same block: 4.3% of days

**Q3 GBP_AUD, Mon** (N days 275)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 29.5% | 24.0% |
| TOKYO | 20.4% | 21.8% |
| LONDON | 9.5% | 18.9% |
| LDN_NY | 24.4% | 19.6% |
| NY_PM | 16.4% | 15.6% |

High and low in the same block: 3.3% of days

**Q3 GBP_AUD, Tue** (N days 278)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 10.1% | 15.1% |
| TOKYO | 30.9% | 29.9% |
| LONDON | 13.3% | 14.0% |
| LDN_NY | 27.3% | 23.0% |
| NY_PM | 18.3% | 18.0% |

High and low in the same block: 5.4% of days

**Q3 GBP_AUD, Wed** (N days 279)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 15.8% | 12.2% |
| TOKYO | 28.7% | 29.4% |
| LONDON | 17.2% | 18.6% |
| LDN_NY | 14.0% | 16.5% |
| NY_PM | 24.4% | 23.3% |

High and low in the same block: 4.3% of days

**Q3 GBP_AUD, Thu** (N days 276)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.1% | 9.1% |
| TOKYO | 27.5% | 23.6% |
| LONDON | 16.3% | 22.1% |
| LDN_NY | 18.8% | 28.3% |
| NY_PM | 19.2% | 17.0% |

High and low in the same block: 5.1% of days

**Q3 GBP_AUD, Fri** (N days 278)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 14.7% | 15.1% |
| TOKYO | 23.7% | 23.7% |
| LONDON | 14.7% | 17.3% |
| LDN_NY | 24.8% | 26.3% |
| NY_PM | 21.9% | 17.6% |

High and low in the same block: 3.2% of days

### Q4. How early the extremes are set

**Q4 GBP_AUD, all weekdays** (N days 1386)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 32.8% | 29.2% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 50.1% | 50.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 73.8% | 75.4% |

**Q4 GBP_AUD, Mon** (N days 275)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 41.8% | 36.4% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 54.9% | 54.5% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 76.4% | 77.8% |

**Q4 GBP_AUD, Tue** (N days 278)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 24.1% | 29.1% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 46.8% | 52.2% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 74.8% | 74.8% |

**Q4 GBP_AUD, Wed** (N days 279)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 33.7% | 28.7% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 53.4% | 52.3% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 72.0% | 71.7% |

**Q4 GBP_AUD, Thu** (N days 276)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 35.1% | 23.6% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 49.3% | 43.8% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 75.7% | 77.2% |

**Q4 GBP_AUD, Fri** (N days 278)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 29.5% | 28.4% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 46.0% | 47.5% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 70.1% | 75.5% |

### Q5. Mean ATR(14) by timeframe (pips; numbers only)

| timeframe | all weekdays (N) | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|---|
| H1 | 26.5 (33463) | 26.7 (6645) | 25.9 (6730) | 26.4 (6696) | 27.2 (6672) | 26.3 (6720) |
| H4 | 53.8 (8356) | 53.8 (1662) | 53.3 (1680) | 53.6 (1668) | 54.5 (1666) | 53.7 (1680) |
| D1 | 136.3 (1381) | 135.7 (275) | 136.0 (278) | 136.4 (276) | 137.0 (275) | 136.3 (277) |


## GBP_JPY

Study days with bars 1399; complete 1386; fold bars excluded from Q1 0

### Q1. Hourly range profile

**Q1 GBP_JPY, all weekdays** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 1305 | 17.7 | 15.0 |
| 22:00 | 14:00 PST / 15:00 PDT | 1393 | 20.9 | 16.4 |
| 23:00 | 15:00 PST / 16:00 PDT | 1394 | 23.3 | 18.7 |
| 00:00 | 16:00 PST / 17:00 PDT | 1395 | 33.7 | 29.1 |
| 01:00 | 17:00 PST / 18:00 PDT | 1395 | 30.4 | 25.8 |
| 02:00 | 18:00 PST / 19:00 PDT | 1395 | 24.5 | 20.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 1395 | 22.6 | 17.6 |
| 04:00 | 20:00 PST / 21:00 PDT | 1395 | 22.0 | 17.4 |
| 05:00 | 21:00 PST / 22:00 PDT | 1395 | 24.0 | 19.8 |
| 06:00 | 22:00 PST / 23:00 PDT | 1395 | 33.0 | 27.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 1395 | 40.8 | 34.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 1395 | 40.2 | 34.7 |
| 09:00 | 01:00 PST / 02:00 PDT | 1395 | 34.9 | 29.6 |
| 10:00 | 02:00 PST / 03:00 PDT | 1395 | 31.3 | 27.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 1395 | 32.3 | 27.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 1395 | 38.6 | 32.1 |
| 13:00 | 05:00 PST / 06:00 PDT | 1395 | 41.2 | 35.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 1395 | 44.6 | 38.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 1395 | 38.1 | 32.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 1395 | 29.0 | 24.7 |
| 17:00 | 09:00 PST / 10:00 PDT | 1395 | 25.1 | 21.2 |
| 18:00 | 10:00 PST / 11:00 PDT | 1395 | 23.0 | 18.4 |
| 19:00 | 11:00 PST / 12:00 PDT | 1395 | 20.5 | 16.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 1395 | 18.1 | 14.4 |

**Q1 GBP_JPY, Mon** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 190 | 26.1 | 21.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 275 | 31.9 | 25.4 |
| 23:00 | 15:00 PST / 16:00 PDT | 276 | 28.1 | 22.1 |
| 00:00 | 16:00 PST / 17:00 PDT | 277 | 36.5 | 30.2 |
| 01:00 | 17:00 PST / 18:00 PDT | 277 | 33.8 | 27.1 |
| 02:00 | 18:00 PST / 19:00 PDT | 277 | 24.1 | 20.4 |
| 03:00 | 19:00 PST / 20:00 PDT | 277 | 21.9 | 17.0 |
| 04:00 | 20:00 PST / 21:00 PDT | 277 | 23.3 | 16.6 |
| 05:00 | 21:00 PST / 22:00 PDT | 277 | 24.5 | 19.1 |
| 06:00 | 22:00 PST / 23:00 PDT | 277 | 31.9 | 25.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 277 | 40.4 | 34.4 |
| 08:00 | 00:00 PST / 01:00 PDT | 277 | 38.9 | 32.3 |
| 09:00 | 01:00 PST / 02:00 PDT | 277 | 34.3 | 29.2 |
| 10:00 | 02:00 PST / 03:00 PDT | 277 | 30.9 | 26.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 277 | 31.3 | 26.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 277 | 34.2 | 29.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 277 | 35.6 | 29.6 |
| 14:00 | 06:00 PST / 07:00 PDT | 277 | 39.4 | 33.4 |
| 15:00 | 07:00 PST / 08:00 PDT | 277 | 34.8 | 28.2 |
| 16:00 | 08:00 PST / 09:00 PDT | 277 | 26.9 | 22.2 |
| 17:00 | 09:00 PST / 10:00 PDT | 277 | 21.5 | 18.7 |
| 18:00 | 10:00 PST / 11:00 PDT | 277 | 20.0 | 16.7 |
| 19:00 | 11:00 PST / 12:00 PDT | 277 | 18.1 | 15.6 |
| 20:00 | 12:00 PST / 13:00 PDT | 277 | 15.4 | 12.5 |

**Q1 GBP_JPY, Tue** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 14.7 | 13.2 |
| 22:00 | 14:00 PST / 15:00 PDT | 281 | 17.0 | 14.2 |
| 23:00 | 15:00 PST / 16:00 PDT | 281 | 21.1 | 17.2 |
| 00:00 | 16:00 PST / 17:00 PDT | 281 | 33.0 | 29.4 |
| 01:00 | 17:00 PST / 18:00 PDT | 281 | 28.7 | 23.9 |
| 02:00 | 18:00 PST / 19:00 PDT | 281 | 23.8 | 20.1 |
| 03:00 | 19:00 PST / 20:00 PDT | 281 | 23.4 | 18.2 |
| 04:00 | 20:00 PST / 21:00 PDT | 281 | 20.1 | 17.4 |
| 05:00 | 21:00 PST / 22:00 PDT | 281 | 24.5 | 20.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 281 | 32.9 | 27.4 |
| 07:00 | 23:00 PST / 00:00 PDT | 281 | 40.7 | 34.3 |
| 08:00 | 00:00 PST / 01:00 PDT | 281 | 41.3 | 37.0 |
| 09:00 | 01:00 PST / 02:00 PDT | 281 | 35.1 | 29.9 |
| 10:00 | 02:00 PST / 03:00 PDT | 281 | 29.9 | 26.4 |
| 11:00 | 03:00 PST / 04:00 PDT | 281 | 31.0 | 27.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 281 | 35.8 | 31.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 281 | 40.2 | 35.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 281 | 44.2 | 37.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 281 | 37.6 | 32.2 |
| 16:00 | 08:00 PST / 09:00 PDT | 281 | 28.7 | 25.1 |
| 17:00 | 09:00 PST / 10:00 PDT | 281 | 23.9 | 21.0 |
| 18:00 | 10:00 PST / 11:00 PDT | 281 | 21.9 | 18.3 |
| 19:00 | 11:00 PST / 12:00 PDT | 281 | 18.8 | 15.5 |
| 20:00 | 12:00 PST / 13:00 PDT | 281 | 16.8 | 14.0 |

**Q1 GBP_JPY, Wed** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 281 | 16.4 | 14.4 |
| 22:00 | 14:00 PST / 15:00 PDT | 279 | 17.9 | 14.2 |
| 23:00 | 15:00 PST / 16:00 PDT | 279 | 20.5 | 16.8 |
| 00:00 | 16:00 PST / 17:00 PDT | 279 | 30.3 | 27.0 |
| 01:00 | 17:00 PST / 18:00 PDT | 279 | 28.8 | 23.6 |
| 02:00 | 18:00 PST / 19:00 PDT | 279 | 23.5 | 18.8 |
| 03:00 | 19:00 PST / 20:00 PDT | 279 | 21.5 | 16.9 |
| 04:00 | 20:00 PST / 21:00 PDT | 279 | 23.1 | 17.2 |
| 05:00 | 21:00 PST / 22:00 PDT | 279 | 22.9 | 19.3 |
| 06:00 | 22:00 PST / 23:00 PDT | 279 | 33.3 | 27.4 |
| 07:00 | 23:00 PST / 00:00 PDT | 279 | 40.7 | 34.1 |
| 08:00 | 00:00 PST / 01:00 PDT | 279 | 37.5 | 32.9 |
| 09:00 | 01:00 PST / 02:00 PDT | 279 | 34.3 | 29.5 |
| 10:00 | 02:00 PST / 03:00 PDT | 279 | 32.3 | 28.3 |
| 11:00 | 03:00 PST / 04:00 PDT | 279 | 29.9 | 25.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 279 | 35.8 | 29.5 |
| 13:00 | 05:00 PST / 06:00 PDT | 279 | 40.7 | 35.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 279 | 43.7 | 39.7 |
| 15:00 | 07:00 PST / 08:00 PDT | 279 | 37.6 | 34.2 |
| 16:00 | 08:00 PST / 09:00 PDT | 279 | 28.5 | 24.7 |
| 17:00 | 09:00 PST / 10:00 PDT | 279 | 26.8 | 22.4 |
| 18:00 | 10:00 PST / 11:00 PDT | 279 | 27.9 | 21.9 |
| 19:00 | 11:00 PST / 12:00 PDT | 279 | 25.1 | 19.7 |
| 20:00 | 12:00 PST / 13:00 PDT | 279 | 20.9 | 15.1 |

**Q1 GBP_JPY, Thu** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 17.7 | 15.4 |
| 22:00 | 14:00 PST / 15:00 PDT | 278 | 20.0 | 16.3 |
| 23:00 | 15:00 PST / 16:00 PDT | 278 | 23.0 | 19.3 |
| 00:00 | 16:00 PST / 17:00 PDT | 278 | 33.2 | 28.2 |
| 01:00 | 17:00 PST / 18:00 PDT | 278 | 30.3 | 26.4 |
| 02:00 | 18:00 PST / 19:00 PDT | 278 | 24.2 | 20.5 |
| 03:00 | 19:00 PST / 20:00 PDT | 278 | 21.7 | 17.3 |
| 04:00 | 20:00 PST / 21:00 PDT | 278 | 21.6 | 18.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 278 | 24.0 | 19.3 |
| 06:00 | 22:00 PST / 23:00 PDT | 278 | 32.1 | 28.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 278 | 39.7 | 34.3 |
| 08:00 | 00:00 PST / 01:00 PDT | 278 | 42.2 | 36.1 |
| 09:00 | 01:00 PST / 02:00 PDT | 278 | 34.3 | 29.3 |
| 10:00 | 02:00 PST / 03:00 PDT | 278 | 32.2 | 28.2 |
| 11:00 | 03:00 PST / 04:00 PDT | 278 | 38.9 | 29.2 |
| 12:00 | 04:00 PST / 05:00 PDT | 278 | 46.9 | 38.1 |
| 13:00 | 05:00 PST / 06:00 PDT | 278 | 45.1 | 37.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 278 | 46.3 | 39.2 |
| 15:00 | 07:00 PST / 08:00 PDT | 278 | 38.9 | 33.2 |
| 16:00 | 08:00 PST / 09:00 PDT | 278 | 31.0 | 27.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 278 | 28.1 | 23.6 |
| 18:00 | 10:00 PST / 11:00 PDT | 278 | 22.7 | 18.8 |
| 19:00 | 11:00 PST / 12:00 PDT | 278 | 21.5 | 17.3 |
| 20:00 | 12:00 PST / 13:00 PDT | 278 | 17.4 | 14.1 |

**Q1 GBP_JPY, Fri** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 278 | 16.1 | 13.8 |
| 22:00 | 14:00 PST / 15:00 PDT | 280 | 17.7 | 14.6 |
| 23:00 | 15:00 PST / 16:00 PDT | 280 | 23.8 | 18.3 |
| 00:00 | 16:00 PST / 17:00 PDT | 280 | 35.8 | 31.0 |
| 01:00 | 17:00 PST / 18:00 PDT | 280 | 30.3 | 26.3 |
| 02:00 | 18:00 PST / 19:00 PDT | 280 | 27.1 | 21.6 |
| 03:00 | 19:00 PST / 20:00 PDT | 280 | 24.7 | 18.5 |
| 04:00 | 20:00 PST / 21:00 PDT | 280 | 21.6 | 17.1 |
| 05:00 | 21:00 PST / 22:00 PDT | 280 | 23.9 | 20.6 |
| 06:00 | 22:00 PST / 23:00 PDT | 280 | 34.9 | 27.6 |
| 07:00 | 23:00 PST / 00:00 PDT | 280 | 42.2 | 35.5 |
| 08:00 | 00:00 PST / 01:00 PDT | 280 | 41.1 | 34.3 |
| 09:00 | 01:00 PST / 02:00 PDT | 280 | 36.3 | 29.3 |
| 10:00 | 02:00 PST / 03:00 PDT | 280 | 31.1 | 26.2 |
| 11:00 | 03:00 PST / 04:00 PDT | 280 | 30.4 | 26.6 |
| 12:00 | 04:00 PST / 05:00 PDT | 280 | 40.4 | 33.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 280 | 44.0 | 37.8 |
| 14:00 | 06:00 PST / 07:00 PDT | 280 | 49.4 | 42.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 280 | 41.5 | 34.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 280 | 29.6 | 24.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 280 | 25.1 | 20.9 |
| 18:00 | 10:00 PST / 11:00 PDT | 280 | 22.6 | 18.0 |
| 19:00 | 11:00 PST / 12:00 PDT | 280 | 19.2 | 15.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 280 | 19.9 | 16.8 |

### Q2. Share of daily range by block

Days with zero range excluded: 0. Winter Mondays' SYDNEY block holds 2 bars, not 3.

**Q2 GBP_JPY, all weekdays**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 1386 | 0.251 | 0.112 | 0.150 | 0.220 | 0.309 | 0.443 |
| TOKYO | 1386 | 0.501 | 0.259 | 0.353 | 0.468 | 0.630 | 0.797 |
| LONDON | 1386 | 0.560 | 0.325 | 0.418 | 0.548 | 0.692 | 0.839 |
| LDN_NY | 1386 | 0.557 | 0.325 | 0.418 | 0.538 | 0.671 | 0.829 |
| NY_PM | 1386 | 0.361 | 0.177 | 0.235 | 0.329 | 0.450 | 0.595 |

**Q2 GBP_JPY, Mon**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 275 | 0.342 | 0.160 | 0.213 | 0.301 | 0.439 | 0.590 |
| TOKYO | 275 | 0.514 | 0.275 | 0.361 | 0.466 | 0.636 | 0.841 |
| LONDON | 275 | 0.550 | 0.306 | 0.400 | 0.532 | 0.696 | 0.823 |
| LDN_NY | 275 | 0.497 | 0.300 | 0.370 | 0.475 | 0.609 | 0.749 |
| NY_PM | 275 | 0.320 | 0.159 | 0.214 | 0.287 | 0.411 | 0.506 |

**Q2 GBP_JPY, Tue**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 278 | 0.216 | 0.106 | 0.139 | 0.189 | 0.261 | 0.355 |
| TOKYO | 278 | 0.515 | 0.298 | 0.376 | 0.472 | 0.633 | 0.805 |
| LONDON | 278 | 0.577 | 0.344 | 0.463 | 0.577 | 0.678 | 0.814 |
| LDN_NY | 278 | 0.565 | 0.355 | 0.427 | 0.559 | 0.669 | 0.812 |
| NY_PM | 278 | 0.355 | 0.184 | 0.233 | 0.329 | 0.444 | 0.568 |

**Q2 GBP_JPY, Wed**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 279 | 0.221 | 0.108 | 0.139 | 0.194 | 0.267 | 0.354 |
| TOKYO | 279 | 0.483 | 0.234 | 0.332 | 0.463 | 0.604 | 0.768 |
| LONDON | 279 | 0.559 | 0.303 | 0.403 | 0.547 | 0.698 | 0.857 |
| LDN_NY | 279 | 0.557 | 0.319 | 0.422 | 0.534 | 0.688 | 0.814 |
| NY_PM | 279 | 0.408 | 0.202 | 0.268 | 0.372 | 0.495 | 0.653 |

**Q2 GBP_JPY, Thu**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 276 | 0.242 | 0.103 | 0.149 | 0.219 | 0.314 | 0.413 |
| TOKYO | 276 | 0.486 | 0.240 | 0.333 | 0.469 | 0.644 | 0.765 |
| LONDON | 276 | 0.557 | 0.337 | 0.404 | 0.534 | 0.696 | 0.842 |
| LDN_NY | 276 | 0.581 | 0.339 | 0.457 | 0.564 | 0.695 | 0.869 |
| NY_PM | 276 | 0.372 | 0.173 | 0.248 | 0.336 | 0.474 | 0.612 |

**Q2 GBP_JPY, Fri**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 278 | 0.234 | 0.110 | 0.148 | 0.209 | 0.285 | 0.377 |
| TOKYO | 278 | 0.509 | 0.261 | 0.373 | 0.490 | 0.628 | 0.777 |
| LONDON | 278 | 0.559 | 0.333 | 0.411 | 0.539 | 0.691 | 0.830 |
| LDN_NY | 278 | 0.587 | 0.333 | 0.451 | 0.557 | 0.740 | 0.864 |
| NY_PM | 278 | 0.352 | 0.181 | 0.236 | 0.311 | 0.428 | 0.589 |

### Q3. Where the daily high and low form

**Q3 GBP_JPY, all weekdays** (N days 1386)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 14.5% | 16.9% |
| TOKYO | 20.2% | 23.8% |
| LONDON | 18.5% | 20.2% |
| LDN_NY | 22.3% | 22.9% |
| NY_PM | 24.5% | 16.2% |

High and low in the same block: 5.5% of days

**Q3 GBP_JPY, Mon** (N days 275)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.2% | 26.9% |
| TOKYO | 16.7% | 24.7% |
| LONDON | 14.5% | 22.9% |
| LDN_NY | 21.8% | 15.3% |
| NY_PM | 28.7% | 10.2% |

High and low in the same block: 4.7% of days

**Q3 GBP_JPY, Tue** (N days 278)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 11.2% | 14.0% |
| TOKYO | 25.9% | 25.2% |
| LONDON | 18.3% | 21.9% |
| LDN_NY | 23.4% | 23.0% |
| NY_PM | 21.2% | 15.8% |

High and low in the same block: 6.1% of days

**Q3 GBP_JPY, Wed** (N days 279)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 10.8% | 18.6% |
| TOKYO | 21.1% | 21.5% |
| LONDON | 17.2% | 17.9% |
| LDN_NY | 22.2% | 26.2% |
| NY_PM | 28.7% | 15.8% |

High and low in the same block: 6.1% of days

**Q3 GBP_JPY, Thu** (N days 276)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 18.8% | 11.2% |
| TOKYO | 17.4% | 24.3% |
| LONDON | 22.1% | 17.0% |
| LDN_NY | 20.7% | 26.8% |
| NY_PM | 21.0% | 20.7% |

High and low in the same block: 4.3% of days

**Q3 GBP_JPY, Fri** (N days 278)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 13.7% | 13.7% |
| TOKYO | 19.8% | 23.4% |
| LONDON | 20.5% | 21.2% |
| LDN_NY | 23.4% | 23.0% |
| NY_PM | 22.7% | 18.7% |

High and low in the same block: 6.1% of days

### Q4. How early the extremes are set

**Q4 GBP_JPY, all weekdays** (N days 1386)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 25.6% | 31.2% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 44.4% | 51.7% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 70.0% | 77.9% |

**Q4 GBP_JPY, Mon** (N days 275)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 29.1% | 42.5% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 42.2% | 65.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 67.3% | 85.1% |

**Q4 GBP_JPY, Tue** (N days 278)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 23.7% | 28.8% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 48.9% | 52.9% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 71.6% | 78.8% |

**Q4 GBP_JPY, Wed** (N days 279)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 19.4% | 29.4% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 40.1% | 49.1% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 66.7% | 79.6% |

**Q4 GBP_JPY, Thu** (N days 276)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 28.3% | 27.5% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 46.4% | 43.8% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 75.0% | 71.4% |

**Q4 GBP_JPY, Fri** (N days 278)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 27.7% | 28.1% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 44.6% | 47.8% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 69.4% | 74.8% |

### Q5. Mean ATR(14) by timeframe (pips; numbers only)

| timeframe | all weekdays (N) | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|---|
| H1 | 29.7 (33463) | 30.7 (6645) | 28.6 (6730) | 28.6 (6696) | 30.1 (6672) | 30.5 (6720) |
| H4 | 61.3 (8356) | 62.2 (1662) | 60.8 (1680) | 60.1 (1668) | 61.2 (1666) | 61.9 (1680) |
| D1 | 159.2 (1381) | 159.0 (275) | 159.0 (278) | 158.6 (276) | 159.8 (275) | 159.6 (277) |


## Reading rules fixed in the spec (§5, §6)

| pair | boundary (UTC) | step = mean(hour b) ÷ mean(hour b−1) | sharp (≥1.5 or ≤0.667)? | DST-exposed? |
|---|---|---|---|---|
| GBP_AUD | 21:00 | 1.36 | no | yes |
| GBP_AUD | 00:00 | 1.49 | no | no |
| GBP_AUD | 07:00 | 1.14 | no | yes |
| GBP_AUD | 12:00 | 1.18 | no | yes |
| GBP_AUD | 16:00 | 0.72 | no | yes |
| GBP_JPY | 21:00 | 0.98 | no | yes |
| GBP_JPY | 00:00 | 1.45 | no | no |
| GBP_JPY | 07:00 | 1.23 | no | yes |
| GBP_JPY | 12:00 | 1.20 | no | yes |
| GBP_JPY | 16:00 | 0.76 | no | yes |

GBP_AUD: largest hourly mean 39.1 at 14:00 UTC; smallest 16.3 at 20:00 UTC; ratio 2.40
GBP_JPY: largest hourly mean 44.6 at 14:00 UTC; smallest 17.7 at 21:00 UTC; ratio 2.53

Phase 3 gate (§6): CONCENTRATED — Phase 3 question not moot (team decides)
```
