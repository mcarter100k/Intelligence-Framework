# Spec: how far gold moves, in percent of price (descriptive)

**Status:** FROZEN 2026-11-16, owner request ("go on C1 and C3").
`docs/gold_plan.md` Phase C, study C1. Committed before the runner
(`studies/gold_move_size_study.py`) exists and before any gold move-size
statistic is computed. The run happens once, after the runner is committed,
and its output goes to validation_log verbatim, whatever it says.

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar (§2 checks this). **Descriptive only:
no entries, no R, no costs, no claim that anything pays.**

## 1. Question and why

**How far does gold move in a day, a 4-hour bar and an hour, measured in
percent of price, in each era?**

- **The decision it informs:** every gold markup threshold is written in
  dollars from one week's notes: zones no wider than about $45 (half a day),
  "held" = about $45 away, the stop rule 0.3–1.5 daily ATR. A dollar figure
  goes stale as the price moves: $45 was about 7% of gold at $600 and about
  1% at $4,000. A percent-of-price figure carries across eras and prices.
- **Why the eras are reported apart:** gold was a different market in
  2006–2013 and 2021–2026 (gold plan §1 rule 3). Pooling them would hide that.

## 2. Data

| File (under `~/intel_study_archives/research_archive_legs/`) | sha256 |
|---|---|
| `XAU_USD_D.csv` | `6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca` |
| `XAU_USD_H4.csv` | `e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c` |
| `XAU_USD_H1.csv` | `eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be` |

- All three hashes equal the archive manifest's `files` entries (checked
  2026-11-16). The runner refuses to run on any other bytes.
- **Eras = the archive's span labels:** STUDY (gold from 2006) and USED
  (2021-04-26 → 2026-09-09). **FORWARD is not used:** that span belongs to the
  live shadow ledger (data_map_spec §1).
- **Gold starts at the 2006-03-21 session** (rows opening at or after
  2006-03-20T22:00Z), the start C2 and the leg study used (gold plan T2).
- **No 2014-01-01 → 2021-04-25 row is read.** The runner refuses any row
  dated in that span.
- **Each era is processed on its own.** No true range uses a close from the
  other era; the first bar of each era has no true range.
- STUDY bars are already converted by the archive (Sunday sessions folded
  into Monday, `history_study_convert`); USED bars are OANDA's modern candles.
  Gold's daily 5–6 PM New York break has no hourly bar. Nothing is re-converted.

## 3. Definitions (fixed)

- **True range % (TR%)** of bar i = max(high − low, |high − previous close|,
  |low − previous close|) ÷ previous close × 100. It includes any gap from the
  previous bar, weekend gaps included (C6 measures those on their own).
- **ATR %** of bar i = Wilder ATR(14) including bar i (the
  `gold_breakout_study.atr_series` function, whose last value equals
  `markup_swings.atr`) ÷ the close of bar i × 100. This is the figure the
  markup tool's "daily average range" would show, as a share of price.
  The first 14 bars of each era are warm-up.
- **Dollars** (context only): the same true range, unscaled.

## 4. Reported

For each era × timeframe (D, H4, H1):
1. Bars used, first and last open, and the bars excluded (era's first bar,
   ATR warm-up).
2. TR%: p10 / p25 / p50 / p75 / p90 and the mean.
3. ATR %: p25 / p50 / p75, and its value on the era's last bar.
4. Dollars: the median true range in dollars and the median close.
5. The size of a 4-hour bar and an hour compared with a day: the median H4 TR%
   ÷ the median D TR%, and the median H1 TR% ÷ the median D TR%.

Also:
6. By calendar year, daily bars: N, the median TR%, the median ATR % and the
   median close.
7. The USED-to-STUDY ratio of the median TR%, per timeframe.

## 5. Reading rules (fixed before the run)

1. **No interval is computed.** Bars are not independent: volatility comes in
   clusters, so a confidence interval from N bars would be far too narrow.
   The medians and the spread (p25–p75) are shown and read as descriptions.
2. **"The eras differ"** on a timeframe only if their p25–p75 ranges of TR% do
   not overlap. Otherwise the reading is **"overlapping"**; the ratio of
   medians (§4.7) is still shown.
3. **A year with fewer than 20 daily bars** is marked INSUFFICIENT.
4. **What it can be used for:** converting the markup's dollar thresholds
   into percent-of-price rules. **Nothing here is an entry rule or an edge.**

## 6. Tests before the run

`tests/test_gold_move_size_study.py`, on synthetic bars:
- TR% of a hand-computed bar, including a gap above and below the previous
  close;
- ATR % on the last bar equals `markup_swings.atr` ÷ that close;
- the first bar of each era has no true range (eras never share a close);
- ATR warm-up bars are excluded;
- percentiles on a known list;
- the H4 and H1 ratios on hand values;
- calendar-year grouping;
- a row in the exam span, a row before the gold start, or a file with the
  wrong hash is refused (the gold-start row is skipped, not refused);
- the era-overlap reading on hand values.

A mutation run shows the tests catch: TR% divided by the bar's own close
instead of the previous close, a true range that crosses eras, ATR warm-up
not excluded, the exam-span refusal removed, and the hash refusal removed.

## 7. Run

Once, through `scripts/reality_run.py --no-env script <worktree absolute path>`
(no network needed), with the archive folder as the argument. Output:
verbatim to validation_log; written up in `studies/gold_move_size_report.md`
in plain words; a finding number in `foundation/research_findings.md`; the
inventory row "Typical move size" updated.
