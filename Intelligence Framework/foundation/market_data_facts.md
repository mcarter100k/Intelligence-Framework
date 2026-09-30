# Market and data facts — OANDA, sessions, pairs, feeds

Hard-won facts about the data itself. Most silent bugs in this framework came from violating one of these (pip scale, bar stamping, the forming bar, DST).

> Citations: `VL:n` = `validation_log.md` line n; `AUDIT §n` = `docs/audit_2026-09-29.md`; other paths are repo files. Line numbers are as of the 2026-09-29 audit (commit efd293e) — search by content if they have drifted.

## 2a. OANDA candle conventions

| Fact | Detail | Source |
|---|---|---|
| Timestamp = bar OPEN | "OANDA D bars are stamped at bar OPEN" | `regime_detection.py:769-771` |
| Daily alignment | NY 17:00 close. A D1 bar opens **21:00 UTC (NY summer time) / 22:00 UTC (winter)**. Trading day D = NY time ≤17:00 on D | `studies/gbpaud_personality_profile.py:32-35`; `historical_scenario_replay.py:55-58`; AUDIT §2 #15 |
| `complete` flag | `_get_bars` requests `count+1` and **drops** `complete=false` (the forming bar). So the live feed never includes the forming bar | `oanda_feed.py:194,208-209`; VL:1185-1190 |
| `to=` semantics | Candles whose open time is strictly less than `to` are returned. `to = <date>T22:00Z` includes that session | `historical_scenario_replay.py:53-58` |
| Price type | `price="M"` (mid). No bid/ask in any study or grader | `oanda_feed.py:195`; profile caveat `:386` |
| Max count | 5,000 per request. Studies page with from/to | `oanda_feed.py:194`; `gbpaud_personality_profile.py:15` |
| H4 slots | 6 per day, aligned to 17:00 NY. Opens at 21, 01, 05, 09, 13, 17 UTC in summer; 22, 02, 06, 10, 14, 18 UTC in winter. In PDT: 14:00 (slot 0 = rollover), 18:00, 22:00, 02:00, 06:00, 10:00 | `gbpaud_secondplay_scouting_report.md:36-42`; `stage2_gate_report.md:36-37` |
| Bars per year (modern, 2014→) | **258–260 D1/yr, 6.00 H4/day** (about 1,550 H4/yr). 3y profile: 784 D1 (≈261/yr), 4,704 H4, 18,816 H1 (24.0/day) | `docs/specs/data_map_spec.md:20`; profile report `:11-15` |
| Old convention (pre-2014 OANDA) | 330–360 raw "D1" rows/yr (weekend/extra candles). H4 ~4.8–5.7 bars/day, with 70–95 short days/yr. Unusable until converted | `data_map_spec.md:27-29` |
| Holidays | Missing weekdays over 3y: Dec 25 and Jan 1 only (6 days) | profile report `:12` |
| Forward-window clock | 30 H4 bars ≈ **168 clock hours**, not 120 (weekends) | AUDIT §2 #3 |
| Calendar vs bar count | 14 calendar days with holiday gaps = **8 real bars** vs 10 by calendar approximation. Count bars from the index | VL:1004-1013 |
| ATR series length | `compute_atr_series` returns **n − 14** values: 300 H4 bars → 286 ATR, offset 14. Map by index with `atr[b − (len(C)−len(atr))]` | VL:2226-2234; `shadow_signals.py:162-171` |
| ADX math | Wilder: TR/DM init = sum of the first 14; DX init = average of the first 14; clamped to 0–100. Needs ≥28 bars. Audit: correct | `regime_detection.py:457-528`; AUDIT §1 |
| Structure (pivot) rule | A pivot needs 3 bars each side higher/lower, plus one later close back through it. **It cannot confirm a trend mid-leg**; it confirms on the first bounce, so first-leg participation is lost by design | `regime_detection.py:282-296`; VL:2003-2006; VL:1960-1966 |
| Live windows | `get_regime` fetches D1 220, H4 120, W 110. The shadow harness fetches H4 300. The grader fetches H4 500 (≈83 days) | `regime_detection.py:802,906,966`; `shadow_signals.py:83,581`; `loss_autopsy_spec.md:52-53` |
| Weekly trend | 3-bar average vs 3-bar average `lookback` weeks ago; ±0.5% threshold. LT 20 weeks, ST 4 weeks | `regime_detection.py:551-617` |
| History depth | OANDA GBP_AUD earliest D **2004-05-31**, H4 **2004-06-01**. The project first loaded yfinance ≈2021-04-26 and OANDA ≈2021-05/07. **H4 was never loaded before 2023-04-30** | `gbpaud_profile_followup_report.md:100-106`; `data_map_spec.md:7-9` |

## 2b. Sessions, DST, clock facts

- **FX week**
  - The code hard-codes Sun 21:00 → Fri 21:00 UTC (`regime_detection.py:735-751`).
  - This is **wrong in winter** (22:00) and ignores holidays (AUDIT §2 #15).
- **Daily grading must run after the D1 close (21:00 UTC in summer).**
  - 15:15 America/Los_Angeles = 22:15 UTC, which is correct.
  - 15:15 EDT = 19:15 UTC, which is *before* the close and grades stale bars.
  - launchd computes StartCalendarInterval in the **session's** timezone, not from the plist's `EnvironmentVariables` (VL:2100-2127).
- **Staleness checks**
  - Measure a D1 bar's staleness from its CLOSE (open + 24h), weekend-aware. A completed D1 bar's open is always >24h old, so "open > 30h" false-alarmed every weekday morning (VL:1179-1182).
  - Weekly-bar age threshold: 168h (VL:844).
- **Release local times.** Handle DST per event: RBA/AU CPI in Sydney time, BoE/UK CPI in London, US prints in New York (`gbpaud_secondplay_scouting_report.md:46-48`).
  - Example: a GBP GDP release at 06:00 UTC is 07:00 London (`docs/specs/display_timezone_spec.md:49`).
  - calendar_fetch stores naive UTC (VL:2066-2069).
- **Rollover.** The 17:00-NY hour dominates cross-feed disagreement: H4 slot-0 disagreement is 62% (AUD) / 44% (JPY) vs 2.83% / 2.24% on other slots (VL:2350-2354).

## 2c. Pair scales and typical magnitudes

| | GBP/AUD | GBP/JPY |
|---|---|---|
| pip_size | 0.0001 (5 dp) | 0.01 (3 dp) |
| Price range seen | 1.8540–2.1647 (2023–26) | ~167 (2023) → ~218 (Jul 2026) → ~208 (Sep 2026) |
| D1 ATR seen | Median 107–136 by year (p25 ~100–131). Live: 106.9 (Jun), 103.2, 84.3, 81.1 pips | Live: 123.1, 116.5, 144.3, **161.6** (after the ~600-pip fall on 2026-07-31) |
| Spike multiplier (PRIOR) | 1.2x | 1.5x |
| Compression stand-down (PRIOR) | none (0.0) | <0.8x |
| Exhaustion (PRIOR) | ADX ≥32 late-trend flag | ADX ≥35 → "fade, don't follow" |

Sources: `regime_detection.py:53-69`; VL:93-100, VL:549-553, VL:1541-1542, VL:2648; profile report.

**Pip bugs are the most common data defect class.** They showed up three times:
- Hard-coded `*10000`: JPY ATR read 12,300 pips instead of 123 (VL:114-118).
- Hard-coded `*0.0001` in outcome measurement: 100x wrong for JPY (VL:815-829).
- A 25-pip proximity threshold for JPY must equal 0.25 price units (VL:2398-2400).

## 2d. Data-source findings (Stage 2, 2026-09-11)

- **datafeed.dukascopy.com** (raw bi5, M1/tick): HTTP 503, then timeouts, all session.
- **HistData.com**: `/get.php` returns **0 bytes** for every dataset. The form token is served empty even to a rendered headless-Chrome DOM.
- **freeserv.dukascopy.com** (H1 transport) coverage: GBP_JPY hourly ≥ **2005-02-01**. GBP_AUD hourly begins between **2006-03-15 and 2006-04-15**.

**Overlap check vs OANDA mid, 2023-09-01 → 2026-09-10**

| pair/TF | matched | median \|diff\| O/H/L/C (pips) | p95 O/H/L/C | disagree >5 pips | HLC-only disagree |
|---|---|---|---|---|---|
| GBP_AUD D1 | 784 | 4.22 / 0.30 / 0.30 / 1.55 | 18.15 / 5.70 / 5.20 / 6.20 | **53.57%** | 19.52% |
| GBP_AUD H4 | 4,704 | 0.30 / 0.25 / 0.25 / 0.30 | 6.90 / 4.00 / 3.40 / 2.70 | 12.73% | 8.01% (slot-0 62.24%, other slots 2.83%) |
| GBP_JPY D1 | 784 | 2.90 / 0.20 / 0.20 / 1.65 | 12.75 / 4.05 / 3.85 / 5.80 | **39.67%** | 14.67% |
| GBP_JPY H4 | 4,704 | 0.25 / 0.15 / 0.15 / 0.20 | 5.25 / 2.35 / 1.95 / 2.65 | 9.16% | 5.23% (slot-0 43.75%, other slots 2.24%) |

Source: `studies/stage2_gate_report.md`; VL:2341-2354.

**Residual:** about 2.2–2.8% mid-session disagreement and a ~1.6-pip close offset between liquidity pools remain even without rollover (VL:2363-2365).

**Lesson:** two feeds of "the same" market disagree on daily opens by pips. Thresholds validated on one feed (v1 used yfinance) do not transfer blindly to another (OANDA) (`data_map_spec.md:68-70`).

**Calendar source:** ForexFactory weekly JSON (`nfs.faireconomy.media/ff_calendar_thisweek.json`), filtered to HIGH impact GBP/AUD/JPY (VL:1339-1355).

## 2e. Spreads used

| Context | Value | Source |
|---|---|---|
| All committed studies (v2, level fade, precursor, gbpaud, hypothesis) | **3.0 pips round trip** | VL:774; `level_fade_study.py:39`; `data_map_spec.md:110` |
| Era schedule (frozen) | GBP_AUD / GBP_JPY: 2005–09 **10/6**; 2010–13 **7/5**; 2014–17 **5/4**; 2018–21 **4/4**; 2021→ **3/3** | `data_map_spec.md:97-112` |
| Execution tools | **4.0 pips** ("GBP/AUD typical broker spread") | `risk_config.py:35`; `trade_management.py:31` |
| Shadow grader | **none** (mid, no spread, no financing) | `shadow_signals.py:605-619`; profile caveat `:386` |

"Modern costs on old data manufacture profit that never existed" (`data_map_spec.md:111-112`).

## 2f. Operational measurements

- Brief latency: warm 0.48–0.55s; cold ~1.1s (VL:1024-1036).
- Staleness cadences (`scripts/artifact_freshness.py:55-69`):

| Artifact | Cadence |
|---|---|
| regime log | 72h |
| session log | 72h |
| calendar | 192h |
| storylines | 216h |
| shadow log | 504h |
| trade_signal_log | 720h |

---
