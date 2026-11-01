# Validation Log
## Intelligence Framework — Parameter Validation History

---

> ⚠️ **HONESTY CORRECTION (2026-07-29)** — two integrity issues affect the
> early (2025) entries below, found in the 2026 code audit:
>
> 1. **Sample sizes (N) are unreliable.** Several tables (e.g. the 2025-06-25
>    ADX tables) show win rates with the N column blanked to "—".
>    `validate_adx_threshold.py` prints "—" for a band **only when N == 0** — and
>    in that case prints **no** win rate. A row showing both a win% **and** N="—"
>    therefore was **not** produced by the script as displayed; treat those
>    sample counts as unknown, not as reported.
> 2. **Overlapping forward windows inflated N ~20×** on the P1/P3 backtests, so
>    every 2025 ADX/ATR "VALIDATED" finding was demoted **VALIDATED → INFORMED
>    PRIOR** on 2026-06-29 (see *Audit Item 2* below). The constants are kept as
>    informed priors; the win-rate **magnitudes** are not validated.
>
> The outcome loop (`run_outcome_check.py`) now records real, non-overlapping
> outcomes for both the regime and trade-signal logs, to replace these priors
> with measured accuracy over time.

---

## 2026-06-25 — ADX Threshold Validation (Problem 1)
<!-- Date corrected 2026-09-11: header read 2025-06-25; git history (commit
     2026-06-25 "Add Problems 2-3 …"; the repo's first commit is 2026-05-16)
     shows the actual run date. Transcription fix only — NOT a re-run;
     content untouched. See the 2026-09-11 housekeeping entry. -->
<!-- ⚠️ N column below is hand-blanked ("—") and not script output — see the
     Honesty Correction banner at the top of this file. Findings demoted to
     INFORMED PRIOR (Audit Item 2, 2026-06-29). -->



**Script:** `validate_adx_threshold.py`  
**Data:** 5-year D1, 1,295 valid bars per pair  
**Method:** Momentum vs mean-reversion win rate by ADX band, 20-bar forward window

### GBP/AUD Results
| ADX Band | N | Mom% | MR% | Edge |
|---|---|---|---|---|
| 0–15 | — | 38.7% | — | MEAN REV |
| 15–18 | — | 44.0% | — | MEAN REV |
| 18–20 | — | 43.7% | — | MEAN REV |
| 20–22 | — | 54.4% | — | COIN FLIP |
| 22–25 | — | 55.8% | — | MOMENTUM (only qualifying band) |
| 25–28 | — | 47.4% | — | COIN FLIP |
| 28–32 | — | 31.7% | — | MEAN REV (strongest inversion) |
| 32–40 | — | 49.1% | — | COIN FLIP |
| 40+ | — | 48.2% | — | COIN FLIP |

### GBP/JPY Results
| ADX Band | Edge |
|---|---|
| 0–22 | COIN FLIP / MEAN REV |
| 22–32 | COIN FLIP |
| 32–40 | 42.4% MEAN REV |
| 40+ | 17.3% MOMENTUM = **82.7% MEAN REV** — exhaustion confirmed |

### Key Findings
1. Wilder's ADX 25 threshold is empirically wrong for both pairs
2. ADX is a regime STATE indicator, not a trend ENTRY signal
3. Momentum win rates collapse at ADX 25–28 — textbook threshold = exit signal, not entry
4. GBP/JPY ADX 40+ is mean-reverting 82.7% of the time — trend exhaustion
5. No ADX band sustains >55% momentum across two consecutive bands

### Parameter Changes
| Parameter | Old Value | New Value | Reason |
|---|---|---|---|
| `_ADX_RANGING_THRESHOLD` | 20 | 18 | Mean reversion dominant below 18 |
| `_ADX_TRANSITION_HIGH` | 25 (implicit) | 25 | Unchanged — still the cautious trend start |
| `_ADX_EXHAUSTION_THRESHOLD` | none | 32 | Late-trend warning for both pairs |
| `_ADX_JPY_EXHAUSTION` | none | 35 | GBP/JPY-specific exhaustion level |

### Next Validation
Re-run `validate_adx_threshold.py` after 6 months of new data to check for threshold drift.

---
*Next entry: Problem 2 — Structure confirmation (HH/HL vs slope)*

---

## 2026-06-25 — Problem 1 Live API Validation

**Script:** Live validation script (inline, no mocks)
**Data:** Live OANDA feed — real market data 2025-06-25
**Method:** 10 sanity checks per pair against real prices, ATR, ADX, regime output

### Live Data Snapshot

| Field | GBP/AUD | GBP/JPY |
|---|---|---|
| Regime | VOLATILE (ADX 19.1 — transition zone) | RANGING (ADX 12.3 — mean-rev dominant) |
| Price | 1.9083 | 213.072 |
| ATR | 106.9 pips | 123.1 pips |
| ATR vs avg | 1.04x (normal) | 1.06x (normal) |
| Daily fuel | 78% used | 78% used |
| Exhaustion | False | False |

### Empirical Regime Consistency Check
- GBP/AUD ADX 19.1 → VOLATILE (transition zone 18–25, no statistical edge) ✓ consistent with backtest finding
- GBP/JPY ADX 12.3 → RANGING (mean-reversion dominant below 18) ✓ consistent with backtest finding

### Bugs Caught by Live Validation (would not have been caught by mock)

**Bug 1 — OANDA pair parameter ignored**
- `_oanda_daily_bars(count=90)` was not passing the instrument parameter
- GBP/JPY was silently fetching GBP/AUD data
- Fix: pass `pair.instrument` to the OANDA call
- Severity: CRITICAL — all GBP/JPY signals would have been wrong

**Bug 2 — Hardcoded pip math**
- `atr_pips` and `range_used` used hardcoded `* 10000`
- GBP/JPY would have shown ~12,300 pips ATR instead of 123
- Fix: use `pair.pip_size` via `to_pips()` method on PairConfig
- Severity: CRITICAL — position sizing and fuel calculations wrong for all JPY pairs

### Validation Result
10/10 checks passed on both pairs. Problem 1 fully validated on live data.

### Why Mocks Cannot Replace Live Validation
Both bugs were invisible to the mock because the mock bypasses the data fetch
layer entirely. Live validation is mandatory before any problem is marked complete.
This is now a standing requirement for all future problems.

---
*Next entry: Problem 2 — Structure confirmation (HH/HL pivot detection)*

---

## 2026-06-25 — Problem 2 Stress Test + Deep Verification

**Script:** stress_test_regime_p2.py (15 scenarios) + 4-part manual verification  
**Method:** Extreme historical conditions + internal state inspection on all 
TRANSITIONAL results + NaN propagation analysis

### Scenarios Tested
| Scenario | Result | Verified Correct |
|---|---|---|
| Flash crash (800-pip single candle) | No crash, valid structure | Yes |
| BoJ V-reversal (symmetrical) | TRANSITIONAL | Yes — identical partition halves, LH/LL and HH/HL both fail |
| COVID volatility (500-pip drops) | Valid, sh > sl invariant holds | Yes |
| Tight sine consolidation | TRANSITIONAL | Yes — hh=True AND ll=True simultaneously, broadening wedge |
| Monotonic run (25 bars) | Partition fallback used | Yes |
| Flat market (30 identical closes) | TRANSITIONAL | Yes — all pivots at identical price, no HH/LH possible |
| Empty data [] | No crash, early return | Yes — guard added this session |
| Trend → range → downtrend | DOWNTREND | Yes — LH+LL proven mathematically |
| NaN values in data | No crash | Partially — NaN test hit slope fallback, not partition |
| Micro-pivots (alternating bars) | TRANSITIONAL | Yes — all pivots identical price |
| Slope fallback accuracy | Correct direction | Yes |
| GBP/JPY price range | Valid, sh in 120-220 | Yes |
| 7-bar minimum | Fallback triggered | Yes |
| Single bar | No crash | Yes |
| Pivot at first bar | No crash, valid | Yes |

### Issues Found in Deep Verification
**Issue 1 — NaN propagation in partition method**
- NaN stress test passed for wrong reason: 13-bar input hit slope fallback before reaching partition
- Real risk: `max([nan, 1.80, 1.85])` returns NaN if NaN is first element
- Fix: input sanitization guard added at top of _detect_structure()
- OANDA data arrives clean, but guard required for robustness

**Issue 2 — DOWNTREND by 0.08-pip margin in trend-range-down scenario**
- latest_sh vs prior_sh differ by 0.0000082 price units on GBP/AUD
- Caused by flat sine section producing nearly identical partition highs
- Acceptable — real market pivots differ by tens of pips minimum
- No fix required

### Verification Discipline Established
Deep verification after stress tests is now standing protocol:
1. Show actual code, not just test results
2. Trace TRANSITIONAL results to their specific cause
3. Identify tests that passed for the wrong reason
4. Fix issues found, even low-probability ones

---
*Next entry: Problem 3 — ATR spike multiplier pair-specific validation*

---

## 2026-06-25 — Problem 2 Final Sign-off

### Test Coverage Summary
| Layer | Result |
|---|---|
| Unit tests — _detect_structure() | 18/18 |
| Problem 1 regression suite | 62/62 |
| Live OANDA validation | 26/26 |
| Stress tests — 15 extreme scenarios | 40/40 |
| NaN guard verification | 3/3 |
| Syntax check | PASS |

### Problem 2 Status: CLOSED
Slope-based direction detection fully replaced by pivot-confirmed 
HH/HL structure detection. NaN guard in place. Empty data handled.
All historical market conditions tested and verified.

---
*Next entry: Problem 3 — ATR spike multiplier pair-specific validation*

---

## 2026-06-25 — ATR Spike Multiplier Validation (Problem 3)
<!-- ⚠️ "observations per pair" below omits the actual count, and cells read
     "—"/"N<15" that validate_atr_threshold.py skips (continue) rather than
     prints — so this table is not faithful script output. Demoted to INFORMED
     PRIOR (Audit Item 2, 2026-06-29). See top-of-file Honesty Correction. -->

**Script:** validate_atr_threshold.py  
**Data:** 5-year D1, observations per pair *(count not recorded — see correction banner)*  
**Method:** ATR ratio bands vs momentum + MR win rate, 20-bar forward window  
**Degraded definition:** both signals < 52% win rate simultaneously

### GBP/AUD Results
| ATR Band | Mom% | MR% | Both Degraded? |
|---|---|---|---|
| 0.8x–1.0x | — | — | No |
| 1.0x–1.2x | — | — | No |
| 1.2x–1.4x | 46.8% | 51.1% | YES — threshold found |
| 1.4x+ | N<15 | N<15 | Insufficient data |

**Finding:** Signal degrades at 1.2x, not 1.5x. Textbook threshold fires too late.

### GBP/JPY Results — Anomalous
| ATR Band | Mom% | MR% | Verdict |
|---|---|---|---|
| 0.8x–1.0x | 49.4% | 47.6% | Both degraded — compression zone |
| 1.0x–1.2x | 39.2% | 61.0% | MR wins strongly |
| 1.2x–1.4x | 46.7% | 54.3% | MR wins |
| 1.4x–1.6x | 57.9% | 42.1% | Mom wins |

**Finding:** ATR ratio is not a single-threshold instrument for GBP/JPY.  
Two distinct states identified:
1. Compression (< 0.8x): pre-BoJ coil — directional ambiguity, both signals fail
2. Spike (>= 1.5x): conservative default retained — post-intervention chaos

**Structural insight:** GBP/JPY spike zones are directional (one signal recovers 
and wins). Only the compression zone is genuinely untradeable. This is consistent 
with BoJ intervention dynamics: compression precedes the move, spike follows it.

### Parameter Changes
| Parameter | Old Value | New Value | Pair | Reason |
|---|---|---|---|---|
| `atr_spike_multiplier` | 1.5 (global) | 1.2 | GBP/AUD | Validated degradation at 1.2x |
| `atr_spike_multiplier` | 1.5 (global) | 1.5 | GBP/JPY | Conservative default retained |
| `atr_compression_min` | none | 0.0 | GBP/AUD | No compression filter needed |
| `atr_compression_min` | none | 0.8 | GBP/JPY | Pre-BoJ coil stand-down |

### Architectural Change
`_ATR_SPIKE_MULTIPLIER` global constant removed.  
ATR parameters moved to `PairConfig` dataclass — each pair owns its thresholds.  
This pattern will extend to all future pair-specific parameters.

---
*Next entry: Problem 4 — Counter-trend conflict stand-down logic*

---

## 2026-06-25 — Problem 3 Live Historical Replay Validation

**Script:** Historical compression replay (inline, live OANDA data)
**Data:** 1,226 bars — GBP/JPY D1, Aug 2021 to Jun 2026
**Method:** Compute ATR ratio on every bar, find all compression events < 0.8x

### Results
- Total bars analyzed: 1,226
- Compression events found: 11 (0.9% of all bars)
- Threshold confirmed: all events in 0.7–0.8x band, nothing below 0.7x

### Historical Compression Clusters
| Period | Bars | Deepest Ratio | Price Level | Context |
|---|---|---|---|---|
| Apr 2023 | 1 | 0.796x | ~167 | Isolated pre-move coil |
| May–Jun 2024 | 8 | 0.728x | ~200 handle | Sustained BoJ pre-intervention coil |
| Jun 2026 | 3 | ~0.791x | ~215 | Developing coil (current) |

### Key Findings
1. Compression is rare (0.9%) but real — not a noise signal
2. May–Jun 2024 cluster: 8 consecutive bars of silence before a BoJ-driven move — exactly the pre-intervention coil the threshold was designed to detect
3. 0.8x threshold is correctly calibrated — tight enough to catch real compression, loose enough to not fire on normal low-volatility days
4. Current bar at 1.056x correctly returns False — consistent with live validation

### Bugs Caught on Live Data (not catchable by mock)
- `compute_atr_series` promoted to public module-level function (was inline)
- OANDA call signature corrected: `instrument=` → `pair=`

### Why Mock Was Rejected
Mock in Verification 3 proved flag wires up in code.
Historical replay proves it fires on real market conditions that match
the BoJ intervention thesis. These are different questions.
Mock is permanently banned from final problem validation.

### P1 Regression
62/62 — no regressions from Problem 3 changes.

---
*Next entry: Problem 4 — Counter-trend conflict stand-down logic*

---

## 2026-06-28 — Four-Issue Implementation + Validation

**Issues resolved:** H4 multi-timeframe, htf_structure absorption,
decision_engine gates, market_brain pair routing

**Test coverage:**
| Layer | Result |
|---|---|
| P1 regression suite | 62/62 |
| Four-issue unit tests | 46/46 |
| Conflict boundary checks | 11/11 |
| Five code verifications | 5/5 |
| Live OANDA — GBP/AUD | 10/10 |
| Live OANDA — GBP/JPY | 9/9 |

### Issue 1 — H4 Multi-Timeframe (stubs replaced)
- `get_h4_bars()` added to `oanda_feed.py`
- `_compute_adx()` extracted as shared helper — zero duplication
- Real H4 regime, ADX, and structure now computed in `get_regime()`
- `_detect_conflict()` and `_stand_down_check()` wired to real values
- `regime_h4`, `adx_h4`, `timeframe_conflict`, `stand_down` all real

### Issue 2 — htf_structure.py absorbed
- `_compute_weekly_context()` added to `regime_detection.py`
- `_compute_ma_context()` added to `regime_detection.py`
- `lt_trend`, `st_trend`, `weekly_context`, `context_note`,
  `ma50`, `ma200`, `price_vs_ma50`, `price_vs_ma200` in return dict
- `htf_structure.py` deleted — 618 lines of duplicate work removed
- Bar count bumped to 220 so MA200 computes correctly

### Issue 3 — decision_engine.py hard gates
- `_no_trade_result()` helper added
- `stand_down=True` → immediate NO TRADE before any scoring
- `atr_compression=True` → immediate NO TRADE before any scoring
- `timeframe_conflict=True` → conviction -20, surfaces in conflicts list
- `adx_exhaustion=True` → grade capped at B

### Issue 4 — market_brain.py pair routing
- `build_market_report(instrument="GBP_AUD")` parameter added
- `get_regime(instrument)` called with correct instrument
- All hardcoded `"GBP_AUD"` references replaced with instrument param
- `from htf_structure import get_htf_structure` removed

### Critical architectural decision made during validation
**VOLATILE D1 ≠ conflict with H4 trend.**
`_detect_conflict()` was incorrectly flagging `VOLATILE_D1_TRENDING_H4`
and `TRENDING_D1_VOLATILE_H4` as directional conflicts.

Fix: conflict means opposite directional signals only:
- `TRENDING_UP + TRENDING_DOWN` → conflict (opposite direction)
- `TRENDING_DOWN + TRENDING_UP` → conflict (opposite direction)
- `RANGING + VOLATILE` → conflict (unstable range)
- `VOLATILE D1 + any H4` → NOT conflict → stand-down owned by `_stand_down_check`
- `TRENDING D1 + VOLATILE H4` → NOT conflict → H4 noise in D1 trend

**Why this matters:** D1 trending with H4 volatile is a legitimate
setup — D1 direction is established, H4 is just noisy. Calling it a
conflict would have reduced conviction on valid trades. Stand-down and
conflict are now separate concerns with separate responses.

### Bugs Caught on Live Data
- `_detect_conflict`: RANGING + VOLATILE case missing — added
- `_stand_down_check`: stub replaced with real three-trigger logic
- `_no_trade_result`: missing `stand_down` and `reason` keys in return dict
- `_detect_conflict`: VOLATILE_D1_TRENDING_H4 incorrectly classified as
  conflict — removed, ownership moved to `_stand_down_check`

### Live Market State at Validation (2025-06-28)
| Field | GBP/AUD | GBP/JPY |
|---|---|---|
| D1 regime | VOLATILE | RANGING |
| H4 regime | TRENDING_UP | VOLATILE |
| ADX H4 | 42.2 | 22.1 |
| Conflict | False (corrected) | False |
| Stand down | True (D1 VOLATILE) | False |
| Weekly context | COUNTER_TREND_BOUNCE | PULLBACK_IN_UPTREND |
| MA50 | 1.8865 | 214.07 |
| MA200 | 1.9566 | 209.63 |

GBP/AUD stand_down=True confirmed on live data — framework correctly
identified D1 VOLATILE + H4 strong trend + weekly counter-trend bounce
as untradeable. This output was invisible before the rebuild.

---
*Next entry: Problem 5*

---

## 2026-06-28 — Problem 5: Confluence Scoring Rebuild

**What was built:**
- `trade_outcome_logger.py` — CSV-based signal logger with outcome tracking
- `validate_confluence_weights.py` — weight recommendation script
- `decision_engine.py` weight tables annotated and partially validated
- `market_brain.py` logger integration

**Test coverage:**
| Layer | Result |
|---|---|
| P1 regression suite | 62/62 |
| Weight table code verification | Confirmed in source |
| Live logger test — GBP/AUD | NO TRADE (stand_down) — correct |
| Live logger test — GBP/JPY | NO TRADE (conviction floor) — correct |
| Weight annotation audit | 9 VALIDATED + 36 PRIOR = 45 total |

### Weight Changes Made
| Weight | Old | New | Status | Source |
|---|---|---|---|---|
| TRENDING `htf` | 0.30 | 0.22 | PRIOR | Trend degrades at ADX 25-28 |
| TRENDING `regime` | 0.04 | 0.12 | VALIDATED P1 | ADX zones have known accuracy |
| TRENDING `structure` | — | 0.10 | VALIDATED P2 | HH/HL is real signal |
| RANGING `regime` | 0.03 | 0.15 | VALIDATED P1 | Ranging classification is real |
| RANGING `structure` | — | 0.05 | VALIDATED P2 | Structure less reliable in ranges |
| VOLATILE `regime` | 0.03 | 0.20 | VALIDATED P1 | Transition zone correctly identified |
| VOLATILE `structure` | — | 0.00 | VALIDATED P2 | No structure signal in volatile |

### Annotation Status
- 9 weights marked VALIDATED with specific P1/P2/P3 source
- 36 weights marked PRIOR — hypotheses pending outcome data
- Re-validation trigger: run validate_confluence_weights.py
  after 60 logged outcomes per regime per pair

### What the Framework Still Cannot Do
- Self-validate weights (no outcome data yet — starts accumulating today)
- Derive currency strength, COT, cross-market weights from evidence
- Confirm whether news impact scoring correlates with actual moves

### Live Market State at Validation (2025-06-28)
Both pairs NO TRADE:
- GBP/AUD: stand_down=True (D1 VOLATILE hard gate)
- GBP/JPY: conviction=10 below floor (RANGING, no setup)
Logger correctly skipped both — fires only on tradeable signals.

---
*Next entry: Problem 6 — Composite regime resolution table*

---

## 2026-06-28 — Problem 6: Composite Regime Resolution Table

**What was built:**
- `RESOLUTION_TABLE` — 16-cell deterministic D1/H4 lookup table
- `get_composite_regime()` — lookup function with unknown combination fallback
- Resolution wired into `get_regime()` return dict
- `decision_engine.py` applies `size_mult` to conviction
- `stand_down` forced True when `execution_mode == STAND_DOWN`

**Test coverage:**
| Layer | Result |
|---|---|
| P1 regression suite | 62/62 |
| Table completeness (16 × 3 keys) | 48/48 |
| HIGH confidence cases | 9/9 |
| PULLBACK cases | 7/7 |
| STAND_DOWN cases | 21/21 |
| LOW confidence cases | 8/8 |
| Unknown combination default | 3/3 |
| Live output contract | 14/14 |
| Total | 110/110 |
| Live consistency verification | PASS — both pairs |

### Resolution Table Summary
| D1 | H4 | Composite | Mode | Confidence | Size |
|---|---|---|---|---|---|
| TRENDING_UP | TRENDING_UP | TRENDING_UP | CONTINUATION | HIGH | 1.0 |
| TRENDING_DOWN | TRENDING_DOWN | TRENDING_DOWN | CONTINUATION | HIGH | 1.0 |
| RANGING | RANGING | RANGING | FADE_EXTREMES | MEDIUM | 0.75 |
| VOLATILE | VOLATILE | VOLATILE | STAND_DOWN | NONE | 0.0 |
| TRENDING_UP | RANGING | TRENDING_UP | PULLBACK_ENTRY | MEDIUM | 0.75 |
| TRENDING_DOWN | RANGING | TRENDING_DOWN | PULLBACK_ENTRY | MEDIUM | 0.75 |
| RANGING | TRENDING_UP | RANGING | REDUCED_MOMENTUM | LOW | 0.5 |
| RANGING | TRENDING_DOWN | RANGING | REDUCED_MOMENTUM | LOW | 0.5 |
| TRENDING_UP | TRENDING_DOWN | VOLATILE | STAND_DOWN | NONE | 0.0 |
| TRENDING_DOWN | TRENDING_UP | VOLATILE | STAND_DOWN | NONE | 0.0 |
| VOLATILE | TRENDING_UP | VOLATILE | STAND_DOWN | NONE | 0.0 |
| VOLATILE | TRENDING_DOWN | VOLATILE | STAND_DOWN | NONE | 0.0 |
| VOLATILE | RANGING | VOLATILE | STAND_DOWN | NONE | 0.0 |
| RANGING | VOLATILE | VOLATILE | STAND_DOWN | NONE | 0.0 |
| TRENDING_UP | VOLATILE | TRENDING_UP | REDUCED_MOMENTUM | LOW | 0.5 |
| TRENDING_DOWN | VOLATILE | TRENDING_DOWN | REDUCED_MOMENTUM | LOW | 0.5 |

### Live Market State at Validation (2025-06-28)
| Field | GBP/AUD | GBP/JPY |
|---|---|---|
| D1 | VOLATILE | RANGING |
| H4 | TRENDING_UP | VOLATILE |
| Composite | VOLATILE | VOLATILE (via RANGING+VOLATILE) |
| Mode | STAND_DOWN | STAND_DOWN |
| Reason | D1 VOLATILE overrides H4 trend | Range breaking down — wait |
| Consistency | ✓ | ✓ |

### Key Design Decision
Resolution table is the single source of truth for composite regime.
`_composite_regime()` removed — `get_composite_regime()` replaces it.
`stand_down` is forced True when `execution_mode == STAND_DOWN`,
ensuring the hard gate and resolution table can never disagree.

### Re-validation Trigger
After 60+ outcomes per D1/H4 combination, run outcome analysis
to confirm size_mult and confidence assignments match actual win rates.
Combinations with < 15 historical outcomes should be treated as
unvalidated — do not increase size_mult above 0.5 until validated.

---
*Next entry: Problem 7 — Validation infrastructure (regime logging)*

---

## 2026-06-28 — Problem 7: Validation Infrastructure

**What was built:**
- `regime_classifier_logger.py` — regime classification logger
- `run_outcome_check.py` — daily outcome measurement script
- `market_brain.py` — log_regime() integrated after get_regime()

**Test coverage:**
| Layer | Result |
|---|---|
| P1 regression suite | 62/62 |
| Unit tests | 25/25 |
| Live validation — GBP/AUD | 12/12 |
| Live validation — GBP/JPY | 12/12 |

### What This Builds
Every framework run now writes one row per pair to
`regime_classification_log.csv` with:
- Full regime state at classification time
- Testable prediction (MOMENTUM_WIN / MR_WIN / VOL_EXPANSION)
- Outcome window (20 bars for TRENDING/RANGING, 8 for VOLATILE)

`run_outcome_check.py` fills outcomes automatically when
enough bars have elapsed. `get_regime_accuracy()` flags any
regime with accuracy < 55% after 60+ samples as needing review.

### Validation Contract Now Enforced
| Regime | Prediction | Window |
|---|---|---|
| TRENDING_UP/DOWN | Momentum win rate > 50% | 20 bars |
| RANGING | Mean reversion win rate > 50% | 20 bars |
| VOLATILE | Realized vol > 1.3x ATR baseline | 8 bars |

### Re-validation Trigger
Run `validate_adx_threshold.py` when any regime shows
`needs_review=True` with >= 60 samples. This closes the
self-improvement loop — outcome data drives threshold revision.

### Live Classifications at Validation (2026-06-28)
| Instrument | Regime | Execution | Price | ATR |
|---|---|---|---|---|
| GBP/AUD | VOLATILE | STAND_DOWN | 1.9142 | 103.2 pips |
| GBP/JPY | RANGING→VOLATILE | STAND_DOWN | 213.478 | 116.5 pips |

Both classifications written to live log. Outcomes will be
measured automatically in ~20 trading days.

### Note on Accuracy Report
TRENDING_DOWN: 0% in the report is synthetic test data
injected during Test 7 to verify the needs_review flag.
Not real market data. Log cleaned post-validation.

---
*Next entry: Problem 8 — No-trade filter and counter-trend override*

---

## 2026-06-28 — Problem 8: No-Trade Filter + Counter-Trend Override

**What was built:**
- `no_trade_filter.py` — standalone FilterResult module,
  single source of truth for all stand-down decisions
- Counter-trend override logic with 5 explicit conditions
- `apply_filter()` integrated into `decision_engine.py`
- `get_regime()` now surfaces all filter fields in output

**Test coverage:**
| Layer | Result |
|---|---|
| P1 regression suite | 62/62 |
| Unit tests | 37/37 |
| Stress tests | 32/32 |
| Live validation — GBP/AUD | All 7 keys present, consistent |
| Live validation — GBP/JPY | All 7 keys present, consistent |

### Hard Block Conditions (no override possible)
1. ATR compression (GBP/JPY pre-BoJ coil)
2. Opposite-trend conflict (D1 up + H4 down or vice versa)
3. Extreme ATR spike (ratio >= 2.0x)
4. RANGING D1 + VOLATILE H4 (range breaking down)
5. Both timeframes VOLATILE

### Counter-Trend Override — ALL 5 conditions required
1. Stand-down is D1 VOLATILE only (not conflict, not ATR)
2. H4 regime is TRENDING with ADX >= 25.0
3. Weekly context is directional (not RANGING)
4. H4 direction aligns with weekly structure bias
5. D1 structure confirmed (UPTREND or DOWNTREND, not TRANSITIONAL)

When fires: `execution_mode=COUNTER_TREND_OVERRIDE`,
`size_mult=0.35`, `confidence=LOW`
Status: UNVALIDATED — requires outcome data before size increase

### Key Design Decisions
- Override is NOT a loophole — all 5 conditions are hard requirements
- GBP/AUD current state (H4 up + weekly COUNTER_TREND_BOUNCE with
  lt_trend=DOWNTREND) correctly blocked — H4 up misaligns with
  bearish weekly structure
- `float(None)` bug caught in stress test — fixed with or-guards
  on all float coercions in `apply_filter()`

### Live Market State at Validation (2025-06-28)
| Field | GBP/AUD | GBP/JPY |
|---|---|---|
| Filter allowed | False | False |
| Mode | STAND_DOWN | STAND_DOWN |
| Reason | D1 VOLATILE — no override | RANGING+VOLATILE breakdown |
| Override fired | False | False |
| Consistency | OK | OK |

### Bugs Caught
- `float(None)` crash on empty/None dict input — fixed with
  `or 0.0` guards on all three float coercions

---
*Problem 8 complete. All 8 problems closed.*
*Next: Final framework audit before Phase 1 trading.*

---

## 2026-06-29 — Priority 1: Decision Brief + Entry Confirmation

**What was built:**
- `decision_brief.py` — 7-field trader-facing brief,
  readable in under 10 seconds
- `entry_confirmation.py` — H1 + 15min precision entry
  module, activates only on LONG/SHORT decisions
- `market_brain.py` — brief integrated into report output

**Architecture decision:**
Two-brief model. Regime brief (Weekly/D1/H4) renders always.
Entry brief (H1/15min) renders only when decision is LONG/SHORT.
30min skipped — no institutional basis in FX.
5min deferred to Phase 2 (trade management only).

**Team agreement:**
H1 and 15min thresholds are unvalidated — using D1 conservative
defaults. Every entry brief logged for Phase 1 review.
H1-specific ADX/ATR validation runs in parallel with Phase 1
using same methodology as Problem 1.

**Live output — 2026-06-29 00:27 UTC:**
| Pair | Decision | Reason |
|---|---|---|
| GBP/AUD | STAND DOWN | D1 VOLATILE ADX 21.2 |
| GBP/JPY | STAND DOWN | RANGING+VOLATILE breakdown |

Entry briefs suppressed — both pairs STAND DOWN.

**Bug fixed post-output:**
`_build_reason()` conflict branch imprecise for RANGING+VOLATILE —
generated "trend in opposite directions" when no trending
conflict existed. Fixed to check conflict_type before
generating reason text.

**Enhancement logged for future sprint:**
ADX direction of travel (rising vs falling) in MARKET STATE
line — ADX rising toward 25 is different from ADX falling
toward 18. Surface in brief when regime is VOLATILE.

---
*Next: Failure mode taxonomy + behavioral testing*

---

## 2026-06-29 — FM-1 + FM-7 Behavioral Testing + Brief Fixes

**Scripts:** fm1_corruption_tests.py, fm7_signal_acceptance.py
**Results:** FM-1 16/16, FM-7 14/14, P1 regression 62/62

### Bugs Found and Fixed

**FM-1 Real Gap — Invalid instrument silent fallback**
- Empty string, None, EUR_USD, garbage strings all fell
  back silently to GBP_AUD analysis
- Fix: get_regime() now returns _error_result() on unknown
  instrument with list of valid instruments

**FM-7 Real Gap — Output paralysis in brief pipeline**
- get_decision_brief() was calling make_decision() with
  regime-only report — direction was always NO TRADE,
  conviction always 10
- Fix: brief now derives direction from filter output
  directly (filter_allowed, execution_mode, confidence)
- Verified: synthetic clean uptrend → LONG, conviction 75,
  grade A, size 100%

**FM-7 Test Fix — Wrong patch targets**
- Tests patched oanda_feed.* functions which are already
  bound in regime_detection at import time
- Fix: patch regime_detection._oanda_* directly

### Failure Mode Status
| FM | Status |
|---|---|
| FM-1 Silent Data Corruption | TESTED — 16/16 |
| FM-2 Threshold Boundary | TESTED — unit suite |
| FM-3 Regime Misclassification | FOUND + FIXED — replay |
| FM-4 Compounding Layer Error | FOUND + FIXED — weekly gate |
| FM-5 Brief Divergence | FOUND + FIXED — size/reason bugs |
| FM-6 Statistical Regime Drift | MONITORED — outcome logger |
| FM-7 Output Paralysis | TESTED — LONG confirmed at 75 conviction |

### Live Brief Confirmed Working
Both pairs render clean plain-English briefs in terminal.
No technical jargon. No translation artifacts.
Decision, reason, exit condition all actionable in < 10 seconds.

---
*Next session: remaining behavioral tests +
Phase 1 readiness audit*

---

## 2026-06-29 — Audit Item 1: Dual Decision Path Resolved

**Problem:** decision_brief.py derived decisions from filter output
(FM-7 fix) while market_brain.py still used make_decision() with the
full signal stack. Two paths could disagree on identical data —
FM-5 divergence built into the architecture by our own fix.

**Team decision:** Filter-derived path becomes the SINGLE official
decision path. Signal-stack scoring moved to SHADOW MODE — computed
and logged alongside every official decision, influencing nothing.
After 60+ outcomes with both paths recorded, accuracy comparison
determines whether signal weights earn their way back in.

**What was built:**
- official_decision.py — single canonical decision function.
  Every conviction component traceable to a validated source:
  confidence tier (P6 resolution table), structure alignment (P2),
  H4 momentum (pending H4 validation, conservative +5),
  exhaustion penalty (P1), override cap at 45 (P8).
- decision_brief.py and market_brain.py both call the same function.
- trade_outcome_logger.py logs shadow_direction + shadow_conviction.
- decision_engine.py marked SHADOW MODE — no logic removed.

**Bug caught during verification (would have shipped):**
Counter-trend override was unreachable through the official path.
_derive_direction() reads D1 regime — but in an override D1 is
VOLATILE by definition; direction comes from H4. The original test
asserted only conviction <= 45, which 0 satisfied, so a NO TRADE
on a filter-approved override passed the test.

Fix: COUNTER_TREND_OVERRIDE derives direction from regime_h4.
Verified: LONG at conviction 45 (40+10+5 capped), grade B, size 0.35.

**Lesson recorded:** a passing test that asserts the wrong invariant
is worse than no test — it certifies broken behavior. Assertions must
pin the expected value, not just a bound.

**Verification:** 62/62 regression, live briefs unchanged,
override reachable in both directions, H4-not-trending fails safe.

---
*Next: Audit Item 2 — re-run threshold validation with corrected
methodology*

---

## 2026-06-29 — Audit Item 2: Threshold Re-validation (v2)

**Script:** validate_thresholds_v2.py
**Corrections vs v1:** structure-based direction (not slope),
OANDA data, NON-OVERLAPPING windows, spread-adjusted (3.0 pips RT)

### Headline: v1 sample sizes were inflated ~20x
Overlapping windows made ~60 independent observations look like
1,295. All v1 ADX band findings are NOT SUPPORTED at honest N —
not disproved, unvalidated. All ADX/ATR thresholds reclassified
VALIDATED → INFORMED PRIOR. Constants unchanged (still best
available estimates; direction consistent across v1 and v2).

### v2 empirical findings (the only bands with N >= 15)
| Pair | ATR band | N | Mom% | MR% | Avg net pips |
|---|---|---|---|---|---|
| GBP/AUD | 0.8-1.0x | 16 | 56.2% | 43.8% | -24.8 |
| GBP/AUD | 1.0-1.2x | 18 | 72.2% | 27.8% | +166.1 |
| GBP/JPY | 0.8-1.0x | 29 | 55.2% | 44.8% | +8.6 |
| GBP/JPY | 1.0-1.2x | 16 | 25.0% | 75.0% | -263.9 |

Finding 1: GBP/AUD trend-following at normal ATR is real
(72%, +166 net pips, N=18).
Finding 2: GBP/JPY at 1.0-1.2x ATR mean-reverts hard (75%,
-264 net pips trend-following, N=16). Actioned: -20 conviction
penalty on JPY trend trades in this zone (official_decision.py).

### Methodology lesson (recorded permanently)
Serial correlation from overlapping windows inflated v1
confidence. The Researcher's own audit caught it — one problem
too late. Standing rule: every backtest reports non-overlapping
N alongside nominal N, or it does not get a VALIDATED label.

### Path to real validation
Daily bars cannot produce sufficient N in reasonable time
(~12 non-overlapping obs/pair/year). Validation N comes from:
(a) H4-based re-validation (audit item 2b, queued), and
(b) the live outcome loggers measuring the actual traded horizon.

---
*Next: Audit Item 3 — JPY pip bug in regime_classifier_logger*

---

## 2026-06-29 — Audit Item 3: JPY Pip Bug in Outcome Measurement

**Bug:** _measure_outcome() VOL_EXPANSION branch hardcoded
* 0.0001 pip conversion — 100x wrong for GBP/JPY. Same bug class
as Problem 4's live-data findings, surviving in the logger.

**Fix:** instrument passed through to _measure_outcome();
pip_size resolved from PAIRS. Dead pre-assignment removed.

**Data integrity:** 0 GBP/JPY outcomes were filled pre-fix —
fix landed before any corruption.

**Verified:** JPY expansion at 1.37x scores True; JPY quiet
market at 0.26x scores False (old code: 26x → always True);
GBP/AUD behavior unchanged. 62/62 regression.

---
*Next: Audit Item 4 — incomplete daily bar handling*

---

## 2026-07-03 — Audit Item 4: Incomplete Daily Bar Handling

**Bug:** get_regime() fed the forming daily bar into ADX, ATR,
structure, and MA calculations. Intraday runs got biased readings
— the last bar could be 2 hours old with 22 hours left to form.

**Fix:** _split_live_bar(df, threshold_hours) splits any OANDA
dataframe into (closed_df, live_row, age_hours). D1: 24h, H4:
4h, weekly: 168h. Closed bars drive all regime calculations.
Fuel gauge uses live bar H/L when present; falls back to last
closed bar on weekends.

**Brief shows freshness:** header now displays "⚠ Last closed
bar is Xh old — market may be closed" (age > 30h) or "Daily
bar in progress — analysis uses last closed bar" (live).

**Test fixture update:** SECTION 3 mock DataFrame given a
tz-aware DatetimeIndex (last bar 5 days ago) so _split_live_bar
sees all bars as complete. Logic unchanged; fixture brought in
line with production expectations. 1 test needed fixture update.

**Verified:** _split_live_bar 3/3 cases; live pairs show
last_closed_bar_age_hours=33.5h, live_bar_in_progress=False
(weekend — expected); ⚠ warning appears in both briefs. 62/62
regression.

---
*Next: Audit Item 5 — session-open staleness detection*

---

## 2026-07-03 — Audit Item 5: Market-Closed Behavior

**Detection from Item 4:** last_closed_bar_age_hours + live_bar_in_progress
already landed. This item adds correct closed-market behavior.

**What was built:**
- _market_status(_now=None): FX hours helper (Sun 21:00 – Fri 21:00 UTC).
  Private _now= parameter allows deterministic testing without patching
  the immutable datetime.datetime type (Python 3.14 constraint).
- get_regime() returns market_open/market_note; _error_result() stubs added.
- Brief header: market_note replaces the generic "⚠ Last closed bar"
  warning when market_open=False. Market-open path unchanged.
- log_session_snapshot(): skips write when market_open=False.
  Caller passes regime.get("market_open", True).

**Verified:** 6/6 _market_status cases (Sat, Sun pre/post-open, Wed,
Fri pre/post-close); 62/62 regression; both briefs show definitive
"Market closed — ... Next open Sun 21:00 UTC."; session log row count
unchanged (11 before, 11 after — no writes while closed).

---

## 2026-07-03 — Audit Item 6: Entry System Consolidation

**Change:** `entry_watcher.py` deleted; engulfing detection and level proximity
ported into `entry_confirmation.py`.

**What was ported:**
- `_detect_engulfing(highs, lows, opens, closes)` — strict engulfing only
  (bullish body engulfs previous body entirely; bearish body engulfs previous
  body entirely). Port adapts from dict-based candle API to array-based API
  using the last two candles. Other entry_watcher patterns (pin bar, rejection,
  momentum close) not ported — insufficient N for any prior validation.
- Level proximity: M15 trigger now requires engulfing in direction AND price
  within `_M15_LEVEL_PROXIMITY_PIPS = 25` pips of a key level (loaded from
  `last_run.json` via `levels_context.levels_as_list`). If `last_run.json`
  absent or `levels_context` unavailable, degrades to engulfing-only trigger
  with "level check unavailable" note in `m15_signal`.

**Import sites:** No file imported `entry_watcher` via a Python `import` or
`from` statement. The only reference was a docstring comment in
`trade_management.py:52` — updated to reference `entry_confirmation`.

**New EntryBrief fields:** `engulfing_detected`, `near_key_level`,
`key_level_price`, `trigger_basis`.

**Data integrity:** No historical data corrupted — `entry_watcher.py` was a
standalone polling module, not a data-writing module.

**Tests:** 4 `_detect_engulfing` unit tests pass (TE1–TE4); 62/62 P1 suite
unchanged.

**Status:** INFORMED PRIOR — engulfing trigger is a precise entry definition,
not a validated edge. `trigger_basis` field logged for Phase 1 outcome review.

---

## 2026-07-06 — Audit Item 7: Stand-down Logic Consolidated to Single Source

**Problem:** Three implementations of stand-down logic existed simultaneously:
1. `no_trade_filter.apply_filter()` — declared source of truth
2. `regime_detection._stand_down_check()` — legacy, pre-filter, could diverge
3. `decision_engine.make_decision()` inline `stand_down`/`atr_compression` checks — shadow path

**Changes:**

`regime_detection.py`:
- Deleted `_stand_down_check()` entirely (conditions: D1 VOLATILE, extreme ATR
  spike ≥ 2.0x, opposite-trend conflict).
- Deleted `_ATR_STANDDOWN_THRESHOLD = 2.0` constant (only used by deleted function).
- Deleted `_OPPOSITE_CONFLICT_TYPES` constant (only used by deleted function).
- Removed `_stand_down_check()` call from `get_regime()`.
- Removed the resolution-table enforcement block
  (`if execution_mode == "STAND_DOWN": stand_down = True`) — the filter already
  blocks on exec_mode STAND_DOWN via the resolution_note path.
- `stand_down` and `stand_down_reason` now derived directly from filter result:
  `stand_down = not _fr.allowed; stand_down_reason = _fr.reason if not _fr.allowed else ""`.

`decision_engine.py`: Already clean — `make_decision()` went directly to
`apply_filter` with no inline checks. TASK 2 was already complete; confirmed
with grep and AST inspection.

**Tests retargeted from `_stand_down_check` to `apply_filter`:**
The three `_stand_down_check` trigger conditions are now T35, T37, T38 in
the consistency matrix (Section 5):
- T35 — D1 VOLATILE no override (was condition 1)
- T37 — Opposite trend conflict (was condition 3)
- T38 — Extreme ATR spike 2.5x (was condition 2)

**Section 5 consistency matrix (T34–T41):** 8 scenarios × 2 assertions = 16
new tests. All pass. Full suite: **78/78**.

**Anti-drift guarantee:** The `T{n}b` assertion in each matrix row reads
`not filter_result.allowed == not expected_allowed`. If anyone re-introduces a
second stand-down computation and it diverges, a new column asserting
`second_path == (not _af(r).allowed)` will catch the drift immediately.

**Behavioral check:** Both live briefs unchanged — stand aside reasons identical
before and after consolidation.

---

## 2026-07-11 — Audit Items 8–11: Instrumentation Honesty Fixes

### Item 8 — `session_memory.py` threshold deduplication

Deleted local constants `_ADX_TREND_THRESHOLD`, `_ADX_RANGE_THRESHOLD`,
`_ATR_SPIKE_AUD`, `_ATR_SPIKE_JPY`, `_ATR_COMPRESS_JPY`. Now imports
`_ADX_TRANSITION_HIGH`, `_ADX_RANGING_THRESHOLD`, `PAIRS` directly from
`regime_detection`. ATR spike/compression thresholds resolved from
`PAIRS[instrument].atr_spike_multiplier` and `.atr_compression_min` at
call time in `_atr_note()`. Compression check now pair-generic (only fires
when `comp_min > 0`), so GBP/AUD is correctly skipped.

### Item 9 — `regime_classifier_logger.py` two-checkpoint contract

Replaced single `needs_review` gate with two checkpoints:
- `MIN_SAMPLES_FLAG = 60` — pattern emerging, watch closely
- `MIN_SAMPLES_REVISE = 150` — actionable, rerun threshold validation

`get_regime_accuracy()` returns `flagged` and `actionable` instead of
`needs_review`. `get_accuracy_report()` shows:
- `flagged` only: `← FLAG — watch closely, not yet actionable`
- `actionable`: `← REVISE — rerun threshold validation`

`MIN_SAMPLES_FOR_REVIEW = MIN_SAMPLES_FLAG` kept as alias for
`run_outcome_check.py` import compatibility.

### Item 10 — `decision_brief.py` DATA BASIS honesty

`_build_regime_log()` now suppresses percentage for `n < 20` (accuracy not
yet meaningful). Calibration tiers: developing (20–59), flag threshold
(60–149), validated sample (150+). Flag/revise markers appended when the
two-checkpoint gates fire.

### Item 11 — `regime_classifier_logger.py` real bar counting

Renamed `_estimate_bars_elapsed` → `_estimate_bars_elapsed_calendar`
(fallback only). New `_count_bars_after(log_time, index)` counts timestamps
in the OANDA DatetimeIndex strictly after `log_time` — exact, no calendar
approximation. `check_pending_outcomes()` accepts `recent_index=` kwarg;
`run_outcome_check.py` passes `raw.index`. Falls back to calendar
approximation when index unavailable.

**Key difference:** 14 calendar days with holiday gaps yields 8 real bars
but 10 via calendar approximation — the two methods disagree, confirming the
fix is non-trivial.

**Tests:** Item 9: 6/6 · Item 10: 11/11 · Item 11: 5/5.  
Full suite: **78/78**. Both briefs unchanged.

---

## 2026-07-11 — Audit Item 13: Latency Baseline

**Environment:** macOS, OANDA live API, warm Python process (modules already imported).

### `get_decision_brief` (full path — OANDA → regime → official decision → brief)

| Run | GBP/AUD | GBP/JPY |
|-----|---------|---------|
| 1   | 0.48s   | 0.53s   |
| 2   | 0.49s   | 0.50s   |
| 3   | 0.52s   | 0.55s   |
| **min** | **0.48s** | **0.50s** |
| **med** | **0.49s** | **0.53s** |
| **max** | **0.52s** | **0.55s** |

Cold start (first call including Python import overhead): **~1.1s** (0.5–0.6s
import + first OANDA connection; subsequent calls reuse the HTTP session).

### `build_market_report` with `instrument=` only

> **⚠ MEASURED OFF-HOURS — market-closed guard (`market_brain.py:69`) returns
> before any OANDA fetch. These numbers measure the closed path only.
> `get_decision_brief` timings (0.49–0.53s) ARE valid — it does not use
> `market_brain`. `build_market_report` latency for the full signal-stack path
> is UNMEASURED. Re-run during live market hours.**

Returns in **<0.01s** warm — `get_session_context()` fires first and returns
`market_closed=True` (weekend). The guard at `market_brain.py:69` returns
immediately with only `layers["session"]` populated; all OANDA calls are
skipped. This timing tells us nothing about the full signal-stack execution.

### Interpretation

`get_decision_brief` runs consistently under **0.6s warm** — valid on any day.
`build_market_report` full-path timing: **not yet measured**.

No optimization needed for the brief path at this stage. Flag for review if
warm median exceeds 2s.

### TODO — Audit Item 13b

Re-measure `build_market_report(instrument="GBP_AUD")` during live market hours
(Sun 21:00 UTC onward). Run `scripts/verify_shadow_path.py` as first check of
the next session — confirms regime layer is populated and shadow path executes.
Compare full-path warm time against `get_decision_brief` baseline above.

---

## 2026-07-11 — Audit Item 14: Phase 0 Session Memory — Status Confirmed

**Status: COMPLETE and integrated.**

### What it logs (9 fields per run)

| Field | Source |
|-------|--------|
| `timestamp` | `datetime.now(UTC)` at brief run time |
| `instrument` | "GBP_AUD" or "GBP_JPY" |
| `adx_d1` | `regime["adx"]` |
| `adx_h4` | `regime["adx_h4"]` |
| `atr_ratio` | `regime["atr_vs_avg"]` |
| `regime_d1` | `regime["regime_d1"]` |
| `regime_h4` | `regime["regime_h4"]` |
| `structure_d1` | `regime["structure"]` |
| `filter_allowed` | `regime["filter_allowed"]` |

**Log file:** `session_context_log.csv` — 13 rows written since 2026-06-30,
across both instruments and multiple sessions.

### Delta logic

`get_session_delta(instrument)` reads all rows for the current instrument
today, compares `today_rows[-1]` (current) to `today_rows[-2]` (previous):
- ADX D1 and H4 deltas (rising/falling/stable with ±0.5 dead-band)
- ATR ratio trend (expanding/contracting/stable with ±0.05 dead-band)
- Regime change detection (D1, H4, composite)
- Filter change detection — surfaces as the highest-priority session event
- Summary string: plain English, shown in brief as SESSION line

### Market-closed guard (Audit Item 5)

`log_session_snapshot()` checks `market_open` before writing:
```python
if not market_open:
    return
```
Closed-market deltas (weekends, post-Friday-21:00 UTC) are noise — skipped.

### Threshold import fix (Audit Item 8)

`_adx_note()` and `_atr_note()` no longer use locally-duplicated constants.
`_ADX_TRANSITION_HIGH`, `_ADX_RANGING_THRESHOLD` imported from
`regime_detection`; ATR spike/compression thresholds resolved from
`PAIRS[instrument].atr_spike_multiplier` / `.atr_compression_min` at call
time, so session notes stay in sync with any future threshold change
automatically.

### Phase 0 unit tests

78/78 — all pass (Sections 1–5 in `test_regime_detection_p1.py`).

---

## 2026-07-11 — Audit Item 13 Follow-up: FIX A + B + C

### FIX A — Closed-market decision path regression (Audit Item 1 regression)

**Bug:** `build_market_report` early-return branch (line 75–78) hand-built the
decision dict instead of calling `get_official_decision`. This violated Audit
Item 1's single-decision-path guarantee for the closed-market case.

**Fix:** `market_brain.py:75–82` — replaced hand-built dict with:
```python
from official_decision import get_official_decision
report["decision"]       = get_official_decision({
    "filter_allowed": False,
    "filter_reason":  ses.get("close_reason", "Market closed"),
})
report["shadow_decision"] = None
report["path_divergence"] = False
```

`get_official_decision` at `filter_allowed=False` returns `direction="NO TRADE"`,
`conviction=0`, `grade="C"`, `source="official_filter_path"` — canonical output
identical to the open-market NO TRADE path. The hand-built dict used `primary_reason`
(shadow path key); the canonical path uses `reason` — inconsistency resolved.

**Verified:** direction=NO TRADE, conviction=0, grade=C, reason carries
close_reason text, source="official_filter_path", shadow_decision=None,
path_divergence=False. 78/78 regression. Both briefs unchanged.

### FIX B — Item 13 latency annotation

The Item 13 `build_market_report` benchmark (<0.01s) was measured off-hours.
`get_session_context()` returned `market_closed=True`; the guard at line 69
returned before any OANDA fetch. The numbers measure the closed path only.

Annotation added to the Item 13 entry above. `get_decision_brief` timings
(0.49–0.53s) remain valid — that path does not use `market_brain`.

### FIX C — Shadow path verification script

`scripts/verify_shadow_path.py` created. Runs `build_market_report`, checks
that `layers["regime"]` is present and `shadow_decision is not None`. Exits
cleanly with message if market is closed. Run at Sun 21:00 UTC (Audit Item 13b).

---
*Next: Audit Item 13b (first live session) + Audit Item 15 — [pending]*

---

## 2026-07-29 — Brief-honesty fixes + cleanup backlog

**Fixed (brief must not lie):**
- `filter_reason` / brief REASON now distinguish two D1-VOLATILE causes:
  ADX 18-25 = "transition zone, no statistical edge"; ADX 25-32 with
  unconfirmed pivot structure = "trending band, structure not confirmed".
  The old single "transition zone" label mislabeled 25-32 structure-gate
  stand-downs and sent the team chasing a phantom threshold bug.
- D1 staleness warning now measured from bar CLOSE (open + 24h), weekend-aware,
  and only fires when the newest complete bar is genuinely behind the expected
  close AND the market is open. The old "bar open > 30h" test false-alarmed
  every weekday morning (a completed D1 bar's open is always > 24h old).

**Cleanup backlog (do NOT refactor mid-pivot — logged for later):**
- `_split_live_bar` (regime_detection) is largely VESTIGIAL for the daily path:
  `oanda_feed._get_bars` already filters incomplete candles at fetch time
  (`if not c.get("complete", True): continue`), so `_split_live_bar` never has
  a live bar to split — it only recomputes an age from the last COMPLETE bar's
  open. Two mechanisms guard one concern. Reconcile when the price-structure
  engine work settles the data-fetch layer.

**Range trading:** GATED OFF (`official_decision.RANGE_TRADING_ENABLED = False`)
pending team review + non-overlapping validation. Unreviewed unvalidated
heuristic at 0.75x size; precedent = counter-trend override (reviewed, 0.35x)
lost on the 2026-05-15 280-pip rally. Logic retained, output gated to NO TRADE.

---

## 2026-07-29 — Evidence loop is LIVE (first run)

`run_outcome_check.py` executed against the logged classifications for the
first time. It grades each classification/signal against the price exactly
`prediction_window` bars after it was logged (non-overlapping; window-bar, not
latest-bar) and fills both `regime_classification_log.csv` and
`trade_signal_log.csv`.

First-run result (2026-07-29): 3 regime outcomes filled (most rows too recent —
20-bar window not yet elapsed). GBP_AUD VOLATILE 0/2, GBP_JPY RANGING 1/1,
GBP_AUD trade-signal TRENDING_UP 1/1. All N trivially small — noise, not signal.
The loop now accumulates real evidence over time; nothing here is actionable
until N reaches the flag (60) / actionable (150) thresholds.

**Cadence — run daily as part of the morning routine, after the D1 close:**
    python3 run_outcome_check.py
Suggested: once per day, any time after ~22:00 UTC (post D1 close). Safe to
run more often — it only fills rows whose window has elapsed, and is idempotent.

---

## 2026-07-29 — Pivot to shadow-signal harness (evidence is forward now)

Three historical premises tested and REFUTED at honest N this session:
- Compression does NOT distinctively precede large moves (box tightness effect
  |d| ~0.3-0.4, and the trader's own moves had WIDE boxes — precursor_study.py).
- Fakeout-then-go is BACKWARDS — real moves have FEWER prior failed breaks than
  quiet periods (both pairs).
- No structural precursor discriminates a coming 150-pip move (all |d| < 0.5,
  N ~150/pair, matched controls).

The four circled moves are momentum-EXPANSION events (ADX 34-47 and accelerating,
volatility expanding), not base breakouts. Conclusion: you don't predict these,
you JOIN them. Every road through the PAST is exhausted for these candidates —
the only remaining evidence is FORWARD.

`shadow_signals.py` logs three FROZEN "join momentum" candidates every time they
fire, with a measured 30-H4-bar outcome, WITHOUT trading:
- EARLY_MOMENTUM (GBP/JPY): H4 ADX 18-25 + confirmed H4 structure.
- THRUST_PULLBACK (both): RANGE_ONLY N=18 X=3.0 box, break body>=1.0 ATR, then
  pullback within 0.25 ATR of the edge + close back within 10 bars.
- MOMENTUM_JOIN (both): ADX>=30 + ADX slope(12)>=+8 + structure + new 12-bar
  extreme. INFORMED PRIOR — derived from an outlier profile of 3 moves; expected
  weakest; logged to test honestly.

**SPEC FROZEN 2026-07-29.** Parameters may not change once logging begins; any
change starts a new candidate id (e.g. EARLY_MOMENTUM_v2) with a fresh log — no
mid-stream tuning. **Review per candidate: FLAG at N=30 graded outcomes;
DECISION REVIEW at N=60.** Signals are logged, never traded, and are NOT wired
into official_decision's tradeable path. Grade daily via run_outcome_check.py.

---

## 2026-07-29 — Automation layer (scheduling only) + episode-counting guardrail

Added launchd scheduling + notification wrappers (scripts/scheduled_brief.sh,
scripts/scheduled_outcome_check.sh, scripts/launchd/). NO changes to decision or
shadow logic — wrappers run the existing entry points, log output, and notify
only on a signal / graded shadow outcome.

**Episode counting:** Review N at the 30/60 gates counts independent EPISODES
(non-overlapping 30-H4-bar horizons), not raw rows — a candidate that fires on
consecutive bars of the same move is one piece of evidence, not many.
`shadow_signals.episode_count()` implements this; the brief tally shows both
("12 rows / 4 episodes"). Trigger specs remain FROZEN — this is counting
methodology, not a spec change.

---

## 2026-07-29 — Codebase reorganization (cleanup audit #2)

Reachability audit from the four live entry points (daily brief, nightly grader,
scheduled wrappers, test suite) reclassified the tree. No decision or shadow
logic changed; files moved with `git mv` (history preserved).

**studies/** — 10 research scripts moved (7 root + 3 from scripts/). Methodology
record cited above; never deleted. sys.path bootstraps updated to add the
project root (+ shadow/) so they still import core modules from studies/.

**shadow/** — the 18-module legacy signal stack (market_brain, decision_engine +
16 signal/support modules only they import, 8,692 lines) + notify.py + their 6
dependent tests, QUARANTINED. Finding: build_market_report was never scheduled;
the official-vs-shadow comparison logged **0 rows** — structurally incapable of
accumulating (it triggered only on official tradeable signals, via an
unscheduled caller). Superseded by shadow_signals.py, which triggers on its own
frozen conditions and is collecting. REACTIVATION CONDITION: promote back only
with a concrete evidence path — wire build_market_report into a scheduled run
FIRST and show the comparison accumulates. Do not cite these modules' priors as
evidence. NOTE: session_guard (circuit breaker) + risk_config live here, so the
parked circuit-breaker item (2.2) now depends on promotion.

**Hygiene:** trade_log.csv and calendar.csv gitignored (untracked, kept on disk —
evidence/data never deleted). calendar.csv was 118-day-old fallback feeding a
now-quarantined module.

**Live tree after:** 13 core modules + 3 manual tools (trade_management,
trade_logger, update_calendar) + config. Live core imports nothing from shadow/
(verified). Shadow tests pass from shadow/ via shadow/conftest.py; 1018 tests
green overall.

---

## 2026-07-30 — Pre-news stand-down gate built (per repo spec)

Built exactly to `docs/specs/news_gate_spec.md` (team approved 2026-07-29;
saved as a repo artifact and committed BEFORE building — new standing process
for protected-path changes).

- `news_gate.py` (new live core, lean, zero shadow/ imports): HIGH-impact
  events for the pair's OWN currencies within 2 hours → gate. USD events out
  of scope — **known v1 boundary**. calendar.csv missing or >7 days old →
  gate INACTIVE with an honesty note ("news calendar stale — event risk
  unchecked"); stale data never gates and never pretends coverage.
- `no_trade_filter.apply_filter`: gate fires → hard stand-down with pinned
  reason ("Major economic event ahead — <event> in <time>. Markets reprice
  violently around releases; standing aside until after."). Gate state is
  computed upstream in `get_regime` so the filter stays deterministic from its
  input dict (stand-down consistency floor untouched).
- `decision_brief`: news reason wins first in REASON; FULL PICTURE narrates
  the release in plain English; stale/missing calendar renders one honest
  line without gating.
- `scripts/scheduled_brief.sh`: runs `update_calendar.py` before the brief
  when calendar.csv is >24h old — logged, never fatal. NOTE (honest boundary):
  `update_calendar.py` is a status/instruction tool for the MANUAL-entry
  workflow, not an auto-fetcher; the refresh step logs staleness + refresh
  steps, it does not fetch data.
- Shadow signals NOT gated (candidates must be graded through real news
  conditions); fires inside a news window get `news_window=true` stamped in
  the ledger's extra field — context only, candidate specs untouched.

Tests: +11 pinned (fires at 90 min / silent at 3 h / own-currencies only /
USD gates neither pair / low-impact ignored / stale→note-not-gate / missing→
safe-inactive / filter reason pinned / inactive gate ignored / brief line
pinned / shadow-not-gated with stamp). Suite 1018 → **1029 green**; banned-token
and stand-down floors untouched. Live brief on both pairs shows the stale-
calendar honesty line (calendar last row 2026-04-01) and no behavior change
elsewhere.

---

## 2026-07-31 — Calendar auto-fetch built (per repo spec)

Built to `docs/specs/calendar_autofetch_spec.md`. Source selected + live-probed:
ForexFactory weekly JSON (`nfs.faireconomy.media/ff_calendar_thisweek.json`);
format assumptions documented in `calendar_fetch.py`'s docstring. Filters to
HIGH-impact GBP/AUD/JPY, writes the exact news_gate schema, validates before
commit-to-disk (>=1 event, all inside now-24h..now+8d, currencies sane), keeps
the existing file untouched on ANY failure (atomic replace; loud log; the
brief's stale-calendar note is the backstop). Weekly launchd job
`com.quis.intelligence.calendar` Sun 12:00 LA via `scheduled_calendar.sh`;
`scheduled_brief.sh`'s >24h check is the mid-week retry, now calling the
fetcher (manual `update_calendar.py` remains as fallback). +5 pinned tests
(happy path/schema, malformed preserved, bad shape preserved, empty rejected,
network fail exit-0). Suite 1029 → 1034 green. Live fetch replaced the
118-day-stale manual file; the brief's stale note cleared. Known boundary: a
week with zero high-impact GBP/AUD/JPY events fails validation by design and
keeps the old file (conservative; stale note reappears after 7 days).

---

## 2026-07-31 — setup_check pre-trade evidence stack built (per repo spec)

Built to `docs/specs/setup_check_spec.md`. `setup_check.py` READS the decision
path (get_regime / official decision / entry_confirmation / news_gate /
session delta — all read-only, no snapshots written), renders the six-line
stack in plain English, soft-gates (always logs to `pre_trade_journal.csv`,
gitignored append-only; blanks/overrides/conflicts flagged, never blocked).
Trading against the framework's read is FLAGGED information, not a block.
`storylines.md` created (dated-header staleness convention, >8 days = stale;
JPY INTERVENTION-WATCH marker). PLAY pattern mapping is deterministic and
documented (coil-break / base-break / first-pullback / retest-fade /
none-named) — suggested only, human confirms. `trade_management` wired
live-core: MAX_STOP_ATR_MULTIPLE=1.5 breach flag + R-to-target math; made
self-contained (local SPREAD_PIPS / MIN_RR_AFTER_SPREAD constants — its old
`risk_config` import pointed into quarantined shadow/ and only worked by
sys.path luck; fixed). `trade_logger.log_open` gains optional stack_id link.
+13 pinned tests; suite 1034 → 1047 green. Live run: 1.1s, all six lines,
against-framework flag correct on a real NO-TRADE read.

KNOWN BOUNDARY (pre-existing, surfaced during build): `trade_logger.py`
imports `trade_receiver`, which was deleted in the old workspace audit
(0e4af6e) — the tool cannot run until repaired or retired. stack_id addition
is inert until then. Team decision needed: repair or retire.

---

## 2026-07-31 — Alert expansion built (per repo spec)

Built to `docs/specs/alert_expansion_spec.md`. Watched-condition flips now
route to phone notifications via the scheduled wrapper. Implementation is
confined to the wrapper layer + a pure read of the brief's session delta
(`decision_brief._machine_flags` / `_emit_alerts`) — NO decision-logic
changes; alerts go to STDERR (##ALERT## prefix) so the human brief on stdout
stays byte-identical. Classes: (a) regime change / filter flip / conditions
improved-deteriorated; (b) EXIT-IF newly satisfied vs prior run — v1 covers
the two stand-down watches (structure newly confirmed; daily trend strength
crossing 25 with the 4-hour >= 25 as the "holding" proxy). KNOWN v1 BOUNDARY:
trade-side swing-break watches are not evaluated (no prior price in the
session snapshot). (c) shadow fires — verified already wired, kept.
Zero-noise rule pinned: no flip → silent; unchanged stand-aside days →
silent. +11 pinned tests; suite 1047 → 1058 green. Live check: unchanged
weekend read produced zero alert lines and a byte-identical brief; wrapper
exit 0.

---

## PENDING LIVE CONFIRMATION (Gate 3 — cleared only by reality, with date + evidence)

Seeded 2026-07-31 per the Two-Gate Verification Standard (AGENTS.md rule 7).
An entry leaves this list only when the real event has occurred and its
evidence (log line / ledger row / notification) is cited here.

- [x] **First real alert fire** — a watched-condition flip (##ALERT## line)
      produced by a scheduled run on real data, routed to a notification.
      **CLEARED 2026-09-09** — 40 days after seeding, on the first full day
      of healthy scheduled runs: `##ALERT## GBP/AUD: the market regime
      changed since the last run.` at logs/brief_2026-09-09.log lines 342
      and 467, emitted by the launchd runs of 05:32:52 and 10:30:15 EDT
      (real prices in both blocks) and routed by the wrapper's ALERT
      category through notify() — delivered via the osascript fallback,
      as terminal-notifier permission was still off at those hours.
      Evidence caveat (team amendment at approval): both fires were the
      GBP/AUD H4 RANGING↔VOLATILE oscillation at trend strength 17-18 —
      the boundary flap later logged as an open question (alert
      materiality/debounce). The MECHANISM is what this entry clears;
      the flip itself was marginal, not a tradeable regime change.
- [x] **First FILTER-FLIP alert fire** (added and cleared 2026-09-16) — the
      second of the three alert variants in
      docs/specs/alert_expansion_spec.md (regime change / filter flip /
      exit-watch). The 2026-09-09 clearing above covered the regime-change
      variant only. **CLEARED 2026-09-16 — MECHANISM ONLY, TRIGGER
      SYNTHETIC:** `##ALERT## GBP/AUD: conditions deteriorated — the
      framework has stood down since the last run.` emitted by a real brief
      run at 02:16 PDT on real OANDA prices. The end-to-end plumbing is
      demonstrated: session_memory detected a filter transition, built the
      plain-English line, and decision_brief routed it to the ##ALERT##
      machine channel where the wrapper would have notified.
      **The trigger was NOT genuine.** The transition was manufactured by
      the Gate-2 contamination logged the same day (`0d5607a`): a synthetic
      `filter_allowed=True` row compared against the next honest `False`
      row. Nothing deteriorated; the framework had stood down throughout.
      Same shape as the caveat on the entry above — mechanism proven,
      trigger not real — and recorded that way deliberately, because a
      cleared Gate-3 entry that quietly rested on a synthetic trigger would
      be exactly the "zero from an unverified path" failure inverted:
      a ONE from a path that only appeared to fire. **A genuine filter flip
      on real market movement is still owed** and is NOT covered by this
      entry.
- [ ] **First Sunday calendar auto-fetch** — com.quis.intelligence.calendar
      fires on schedule and calendar.csv updates (logs/calendar_*.log).
- [ ] **First real setup_check use** — a pre-trade stack run before an actual
      trading decision, logged to pre_trade_journal.csv.
- [ ] **First EARLY_MOMENTUM_v2 fire** (added 2026-09-09) — a real scheduled
      run logs a v2 row whose stop passes the validity guard (adverse side,
      by construction). Proves the guard passes valid states through, not
      just that it blocks invalid ones (Gate-1 pins cover blocking).
- [ ] **First healthy SCHEDULED runs post-outage** (added 2026-09-09) —
      launchd fires the brief and outcome wrappers, `.env` sourcing delivers
      credentials, logs show real prices / real grading with no error
      markers, health counter stays 0. Expected at the first scheduled
      slots after the heartbeat branch is live. (Manual bare-env runs
      already proved the mechanism — Gate 2, 2026-09-09 — but only launchd
      itself can prove launchd.)
      **PARTIAL 2026-09-09 — brief half PROVEN, twice:** launchd fired the
      brief wrapper at 05:32:52 and 10:30:15 EDT with real prices (1.8762 /
      208.51), no error markers, and health_state last_success
      2026-09-09T14:30:15Z written from the scheduled context — `.env`
      sourcing works under launchd. Outcomes wrapper: its next scheduled
      slot tonight clears the rest. NOTE, recorded honestly: both fires
      landed on the PACIFIC-interpreted instants (05:32/10:30 EDT), not
      the re-based Eastern 02:30/07:30 — the session launchd has not
      picked up the timezone change (needs logout/reboot). One consistent
      clock, but the old one; team to choose reboot vs. accept.
- [ ] **First Sunday heartbeat via launchd** (added 2026-09-09) —
      com.quis.intelligence.heartbeat fires Sunday 12:30 local, notification
      received, logs/heartbeat_<date>.log written. First eligible Sunday:
      2026-09-13.
- [x] **Click-through notification confirmed by a human** (added 2026-09-09)
      — user enables Allow for terminal-notifier (System Settings →
      Notifications), then clicks a real notification and the day's log
      opens. Until enabled, all notifications arrive via the osascript
      fallback (pointer text included) — nothing is lost meanwhile.
      **CLEARED 2026-09-09** — user enabled Allow (posts flipped from
      exit 3 to exit 0), was sent a TEST notification targeting
      logs/brief_2026-09-09.log, and returned that file's full content in
      chat. Recorded on that basis: the click opened the exact click
      target. (If it was opened another way, this clearance should be
      corrected by a new dated entry — the Honesty Correction format.)
- [ ] **First scheduled regime-classification row** (added 2026-09-10, per
      docs/specs/regime_log_restore_narrative_truth_spec.md) — a launchd
      brief run appends a regime_classification_log.csv row with the
      subtype column populated where a subtype exists. Manual Gate-2 runs
      already proved the wiring; only launchd proves launchd. First
      eligible slot: the next scheduled brief after merge.
- [ ] **First freshness-driven UNHEALTHY fire** (added 2026-09-10) — a real
      (or deliberately induced, INTEL-style forced) staleness of an
      evidence artifact drives scheduled_brief.sh → health_state.py
      record-failure with a "STALE:" reason, and the daily UNHEALTHY alert
      names the artifact. Tests pin the mechanism; only reality proves the
      chain end-to-end.
- [ ] **First THRUST_PULLBACK observation post-fix** (added 2026-09-10, per
      the ledger-integrity entry of the same date) — a scheduled run either
      logs the candidate's first-ever valid row or, over time, its honest
      zeros accumulate from a check that demonstrably EVALUATES (no
      SHADOW CANDIDATE ERROR marker in the logs). Its N starts here.
- [ ] **First SHADOW CANDIDATE ERROR alert via the scheduled path** (added
      2026-09-10) — if a candidate ever raises again, the ##ALERT## line
      must appear in the day log, a notification must fire, and
      health_state must record the failure. Pinned in tests; only a real
      (or deliberately induced) error proves the full chain.
- [ ] **First loss autopsied at scheduled grading time** (added 2026-09-09)
      — a future graded loss gets its loss_species stamped by the scheduled
      run_outcome_check path (the backfill proved the classifier on the
      founding exhibit; only time provides a fresh loss).
- [ ] **First real session walked by the promoted circuit breaker** (added
      2026-09-09) — a day with live CLOSE rows in trades.csv exercises the
      R-curve and limits on real trading, not fixtures.
- [ ] **First closed-market DECISION suppressed by a scheduled run** (added
      2026-10-17) — after the Phase 0 gate merges, a launchd run while the
      market is closed with a directional decision writes
      `DECISION notification suppressed: market closed` to the day log
      and sends no DECISION notification. A later open-market directional
      run must still notify. Proven so far on replayed real text and one
      live brief, not on a scheduled run.
      **PARTLY CLEARED 2026-10-18 (closed half).** The scheduled runs at
      02:30:07 and 07:30:09 PDT (main 733a63a) each logged GBP/AUD LONG
      under the closed-market banner, followed by `DECISION notification
      suppressed: market closed` (logs/brief_2026-10-18.log). **Still
      open (open half):** the 18:00:08 PDT open-market run was STAND ASIDE
      on both pairs, so an open-market directional notification has not
      yet been observed on the scheduled path.
- [ ] **Scheduled heartbeat reports expected vs on-time runs** (added
      2026-10-18) — the Sunday 12:30 PM launchd heartbeat writes the
      `runs (last 7d, launchd schedule): …` line, and a real gap raises
      `runs: SHORTFALL`. Proven on real logs replayed at past dates and on
      a scratch copy, not yet on a scheduled run.
      **PARTLY CLEARED 2026-10-18 (reporting half).** The 12:30:05 PDT
      launchd heartbeat wrote `runs (last 7d, launchd schedule): brief 21
      expected / 21 on time / 21 ran; outcomes 7 expected / 7 on time / 7
      ran` (logs/heartbeat_2026-10-18.log). **Still open:** a live
      `runs: SHORTFALL`; this week had no gap.
- [ ] **First row in notification_log.csv from a scheduled run** (added
      2026-10-18) — blocked on team review of
      docs/specs/notification_ledger_spec.md (branch
      feat/notification-review, unmerged).
      **UNBLOCKED 2026-10-19:** team review given; merged 42e15b8. Cleared
      by the first row a real scheduled notification writes (at the latest,
      Tuesday's 07:30 DIGEST).
- [ ] **Live-script cleanup merged and running** (added 2026-10-18) —
      branch chore/live-scripts-cleanup (latest_view parser fix, wrapper
      headers, install.sh) is held until Sunday 2026-10-18's 18:00 run
      lands, so it cannot confound Gate 3 E1-E4. Cleared by the first
      scheduled 07:30 DIGEST after the merge: logs/latest_brief.log names a
      directional run's decision instead of a bare pair.
- [x] **First shadow grading** — run_outcome_check grades the first shadow
      ledger rows when their 30-bar horizons elapse (~2026-08-05 for the
      2026-07-29 EARLY_MOMENTUM fires).
      **CLEARED 2026-09-08** — 34 days late (see the outage post-mortem
      entry, 2026-09-09): a manual `run_outcome_check.py` from a
      credentialed shell graded all 3 EARLY_MOMENTUM rows
      (shadow_signal_log.csv, outcome_filled=True, mtime 2026-09-09
      00:07:55). Evidence + honest reading: entry "First shadow grading",
      2026-09-09.

---

## 2026-07-31 — trade_logger repaired (per amended repo spec)

Built to `docs/specs/trade_logger_repair_spec.md` (amended: premise inspection
showed trade_log.csv is an orphaned framework-snapshot file, not a trade
ledger — it stays untouched as evidence). New `trades.csv` ledger (gitignored,
append-only), TWO-ROW convention: OPEN row at entry, CLOSE row at exit, linked
by position_id — closing never edits the open row; open positions are derived,
no pending-state file. stack_id links to pre_trade_journal.csv with the most
recent matching stack offered as default. Instrument-correct pip math. All
bridge-module/MT5 remnants stripped (enforced by test). Gate 1: +5 pinned
tests (schema, full flow, stack default, id increment, remnant scan); suite
1058 → 1063 green. Gate 2 (REALITY): real end-to-end use on the live brief —
PAPER SHORT GBP_JPY at the real Friday close 212.264 (post-crash: GBP/JPY fell
~600 pips 07-31; ATR 161.6p), stop/target from real ATR, closed against the
same real price minutes later (BE, market closed) — both ledger rows verbatim
in the run report. Bug found by tests: def-time default-arg binding (same
class as calendar_fetch) — fixed; a test artifact briefly written to the real
trades.csv was removed before first real use.

---

## 2026-09-09 — First shadow grading (2026-09-08): Episode 1 = −1.0R, and a spec defect

The first shadow rows were graded 2026-09-08 by a manual `run_outcome_check.py`
from a credentialed shell (ledger mtime 2026-09-09 00:07:55Z-4). All three
EARLY_MOMENTUM GBP_JPY SHORT rows filled. Honest reading:

**Episode 1 = −1.0R** from the ONE valid row:
  row 1 · 2026-07-29T05:00Z · entry 217.667, stop 217.996 (32.9 pips adverse)
  → hit_stop=True, r_multiple=−1.0, MAE 102.1, **MFE 809.2**, net +529.1.
  Stopped at 33 pips; the move then ran ~800 pips in the signal's direction.
  This row is the founding noise-stop exhibit for the loss-autopsy program.

**Rows 2–3 are invalid_spec — excluded from all evidence:**
  row 2 · entry 218.352, stop 217.996 · row 3 · entry 218.572, stop 217.996 —
  the stale swing-high stop sits BELOW the SHORT entries. For such rows the
  grader's hit test (`max(fut_h) >= stop`) is trivially true at entry:
  guaranteed −1.0R whatever the market does — **unscoreable by construction**,
  not merely mislabeled. Both "lost" −1.0R while price moved 877.7 / 899.7
  pips in the signal's favor. Their ledger rows stay verbatim (append-only);
  the exclusion lives in the grading/reporting layer
  (`shadow_signals.is_invalid_spec`, per docs/specs/honesty_repairs_spec.md).

Defect source (read in code): `check_early_momentum` uses `latest_sh` as the
SHORT stop; when price rallies above that stale swing while structure still
reads DOWNTREND, the stop lands on the wrong side. **EARLY_MOMENTUM v1 is
RETIRED** for this defect; v2 (identical trigger + stop-validity guard, no
valid adverse-side swing = no fire) is specified in
docs/specs/early_momentum_v2_spec.md with a fresh ledger id, per SPEC FREEZE.

THRUST_PULLBACK and MOMENTUM_JOIN stops verified valid by construction in
code: opposite box edge (entry is beyond the near edge by definition of the
break) and entry ∓ 1.5×ATR respectively — always adverse side.

Tally after exclusion: EARLY_MOMENTUM = 1 row / 1 episode / 1 graded / −1.0R.
Gates: FLAG N=30, DECISION N=60 — nothing here is evidence of edge or its
absence; N=1.

---

## 2026-09-09 — 39-day outage post-mortem (2026-07-31 → 2026-09-08)

**Root cause:** launchd starts the scheduled wrappers in a bare environment.
OANDA credentials lived only in the interactive shell (`~/.zshrc`-style
export); `.env` held only ALPHA_VANTAGE_API_KEY, and `oanda_feed` reads
`os.environ` exclusively (it never loads `.env`). So `is_configured()` was
False for **every scheduled run from the first one** (outcomes 2026-07-29
15:16 PDT) — the audit found 250 of 256 brief renders were the error page and
42/42 scheduled grader runs exited before grading.

**Why it was silent:** the error path resolves to STAND ASIDE (no notify),
emits no ##ALERT##, and the wrappers exit 0 by design — indistinguishable
from a healthy quiet market. The heartbeat spec (Branch 3,
docs/specs/heartbeat_spec.md) exists so this failure class can never be
silent again.

**Lost, unrecoverable:** ~5 weeks of shadow-candidate evaluation
(2026-07-31 → 2026-09-07). Fires that were never observed cannot be
reconstructed — reconstructing them from historical data would be in-sample
selection, exactly what the forward ledger exists to avoid. Notably the
GBP/AUD 1.9035 break (week of 2026-08-24) passed unobserved.

**Recovered:** the July EARLY_MOMENTUM episode, graded 2026-09-08 (entry
above). The regime ledger's 22 pending rows remain fillable when within
their windows' data reach.

**Honest current status (2026-09-09):** the root cause PERSISTS for
scheduled runs — the 2026-09-08 18:15 scheduled grader still failed with
"OANDA not configured". Manual runs from the credentialed shell work.
Credential delivery to launchd context is sequenced into the heartbeat
build (Branch 3), where the wrappers are already under edit. Until that
merges, only manual runs produce evidence.

---

## 2026-09-09 — Level-fade study: FOURTH refutation (entry edge), location confirmed descriptively

`studies/level_fade_study.py` (committed with this entry; approved for the
record 2026-08-01, entry written from a fresh run's actual output —
2026-09-09, H4 2023-07-13 → 2026-09-08, 3.2y per pair, spread 3.0p,
frozen params in the file header).

**REFUTED — rejection-at-level entries carry no edge at honest N:**
- GBP_AUD: N=1682 rejections — win 50%, median R −1.0, fake rate 76%.
- GBP_JPY: N=1627 rejections — win 50%, median R −1.0, fake rate 77%.
- The rejection trigger adds NOTHING over raw touches (both 50% win).
- D1 alignment adds nothing on GBP_AUD (50% vs 49%) and is INVERTED on
  GBP_JPY (aligned 39% vs against 55%, medMAE 178 vs 119) — alignment with
  D1 structure made level fades WORSE on the pair where it mattered.
- Touch number: no monotone effect (48–54% band).
This is the fourth refuted entry premise (after compression-precedes-moves,
fakeout-then-go, structural-precursor). The spread-adjusted median trade
stops out (medR −1.0 across every slice at MIN_N-honest sample sizes).

**CONFIRMED (descriptive, NOT tradeable):** significant turns (≥100-pip
legs) occur at pre-existing levels far above base rate — GBP_AUD 93%
(702/758) vs 59% base (1.56x lift); GBP_JPY 90% (768/851) vs 58% (1.54x).
Turns are knowable in LOCATION while remaining unpredictable in TIMING —
the tested trigger fails to convert location knowledge into entry edge.
Levels stay useful for stop/target placement and context, not for fading.

Full output: run of 2026-09-09 (also preserved with the Branch-1 run
report). Study is report-only; framework unchanged by the run.

---

## 2026-09-09 — session_context_log.csv: directed removal made moot by designed pruning

Post-audit directive item (f) ordered removal of the synthetic row at line 17
(`2026-07-29T04:23:31Z,GBP_AUD,100.0,100.0,1.0,TRENDING_UP,TRENDING_UP,
UPTREND,True` — ADX pinned at 100.0 on both timeframes with
filter_allowed=True: a test-fixture signature, preserved verbatim here and
in the 2026-09-08 audit artifact). **No removal was performed.** Before the
branch touched the file, the 2026-09-09 00:07 manual run wrote fresh rows
and `session_memory._prune_old_entries()` (PRUNE_DAYS=30, pruning on every
write — designed behavior documented in the module docstring since build)
dropped all rows older than 30 days, the synthetic row among them. The file
now holds the header + 2 rows of 2026-09-09. An agent script targeting the
exact row content asserted zero matches and aborted without writing.

Correction to the 2026-09-08 audit's framing, same-care-as-positives: this
ledger is a designed **rolling 30-day window**, not an append-only archive —
the only ledger with retention. The synthetic row's origin (how a fixture
reached the live file, 2026-07-29) remains unexplained; the row itself is
now gone by retention, not by edit.

---

## 2026-09-09 — EARLY_MOMENTUM_v2 built (per docs/specs/early_momentum_v2_spec.md)

Built on `feat/early-momentum-v2`: v1 removed from the candidate roster
(retired — entry above), `check_early_momentum_v2` = byte-identical trigger
and parameters + the stop-validity guard (stale swing on the non-adverse
side = NO FIRE; the no-swing 1.5×ATR fallback unchanged). Fresh ledger id;
v1 rows untouched. Frozen 2026-09-09.

Gate 1: trigger pins carried over verbatim + 7 guard pins (both directions,
at-entry boundary, fallback preserved, guarded state writes no ledger row);
suite 1081 → 1088 green. Gate 2 (REALITY): live evaluation on real OANDA H4
ctx — GBP_JPY close 208.060, ADX 64.0, DOWNTREND, latest_sh 211.823 → no
fire (ADX far above band, correct); GBP_AUD ADX 17.9 → no fire; real brief
rendered with live price 208.51 and no shadow section (nothing fired —
coherent). Gate 3 pending: first real v2 fire through the guard.

---

## 2026-09-09 — Heartbeat built (Spec A, per docs/specs/heartbeat_spec.md): the outage class is closed

Built on `feat/heartbeat`:

- **Item 0 (builder addition, flagged in the spec):** wrappers source the
  gitignored `.env` (`set -a`) before Python; OANDA credentials added to
  `.env` from the working shell env. This closes the 39-day root cause —
  launchd's bare env — without touching `oanda_feed`. `INTEL_NO_ENV_FILE=1`
  is the documented knob to force a failure deliberately.
- **Item 1:** `scripts/health_state.py` + `logs/health_state.json` —
  2 consecutive failed runs notify "FRAMEWORK UNHEALTHY — <reason> — Nth
  consecutive failed run", repeating daily (not per-run) until healthy;
  recovery notifies once ("RECOVERED after N failed runs"). Both wrappers
  wired (brief: `Framework error`/empty output; outcomes: `GRADER EARLY
  EXIT`/`not configured`/`no data`/empty).
- **Item 2:** `run_outcome_check.py` early exit is now loud and
  machine-detectable ("GRADER EARLY EXIT — … — nothing graded this run").
- **Item 3:** `scripts/weekly_heartbeat.sh` +
  `com.quis.intelligence.heartbeat` (Sun 12:30 local, installed and loaded)
  — ALWAYS notifies: health state, yesterday's run/error status, shadow
  graded tallies (valid rows only), calendar age/newest event, storylines
  age. Silence on a Sunday is itself the alarm.

Gate 1: 10 pinned tests (failure #1 silent / #2 alerts / same-day quiet /
next-day repeat / recovery once / corrupt state = zero / loud grader exit);
suite 1088 → 1098 green. Gate 2 (REALITY): forced failure ×2 through the
REAL brief wrapper (`INTEL_NO_ENV_FILE=1`, OANDA vars unset) — run 1 silent
(counter 1), run 2 fired the real notification, line 99 of
logs/brief_2026-09-09.log; then a REAL healthy run in a launchd-identical
bare env (OANDA vars unset, `.env` sourcing only) rendered live prices
1.8762 / 208.51, printed "RECOVERED after 2 failed runs" once, counter
reset to 0; outcomes wrapper healthy bare-env run graded against real OANDA
(counter stayed 0); real heartbeat run produced the report + notification
(and honestly flagged yesterday's ERRORS PRESENT and storylines 37d STALE);
`launchctl list` shows all six jobs. Gate 3 pending: first scheduled
healthy runs via launchd; first Sunday heartbeat (2026-09-13).

---

## 2026-09-09 — Circuit breaker promoted (Spec B, per docs/specs/circuit_breaker_promotion_spec.md)

`session_guard.py`, `risk_config.py` and `test_session_guard.py` moved out
of `shadow/` via git mv (history preserved) and into the PROTECTED list
(16 → 18). Per the directive's DECISION, the adapter lives IN THE BREAKER:
it reads the live trades.csv two-row ledger (OPEN/CLOSE by position_id, UTC
day boundary), derives per-day realized R from prices
(direction-signed (close−open)/|open−stop|), and enforces
MAX_DAILY_LOSS_R=2.0 (new), MAX_DAILY_LOSS_PCT=2.0 (kept — via return_pct
whenever the ledger carries it), MAX_TRADES_PER_SESSION=2 (unchanged).
Append-only ledgers were NOT modified to fit the consumer. Fail-closed
preserved: wrong columns / unparseable file → HALTED; absent/empty →
ACTIVE. Standing rule adopted (doc + risk_config): combined open risk
sharing a currency leg counts as ONE position against limits
(`count_leg_grouped_positions`, connected components over legs).

Gate 1: the 8 original behavioral pins preserved one-for-one on the new
schema + 8 new breaker pins + 13 first-ever risk_config pins (grade
ladder, lot-size arithmetic, limit wiring, standing rule); live suite
1098 → 1119 green (the moved file's 8 old tests left the shadow count:
868 there, also green). Gate 2 (REALITY): against the real trades.csv the
breaker returns ACTIVE, 0 positions today, 0.0R (only rows are the
2026-08-01 PAPER pair — correctly not today); against the real
trade_log.csv (wrong schema) it still fails CLOSED. NOT wired into the
live decision path — where the breaker gates is a separate protected-path
spec for team decision (out of scope here by design). Gate 3 pending:
first real session with live CLOSE rows walking the R curve.

---

## 2026-09-09 — Loss autopsy built (Spec C, per docs/specs/loss_autopsy_spec.md); the founding exhibit speaks

Built on `feat/loss-autopsy`: species taxonomy frozen (event_window >
stopped_then_reversed > exhaustion_entry > never_onside > bled_out, first
match wins; classified only for R-losing rows passing the invalid_spec
guard), hooked at the grading seam inside `grade_pending_shadow` — after
the outcome fields, before the file rewrite; triggers untouched. One
column appended to the ledger schema (`loss_species`) with an additive
header migration by the logger (old values preserved verbatim; recorded
here). `backfill_loss_species()` classifies already-graded valid rows.

Gate 1: 11 pinned tests — one per species, priority pins, wins
unclassified, invalid rows never autopsied, migration losslessness; suite
1119 → 1130 green. Gate 2 (REALITY): real backfill on the live ledger
against real H4 history — **the founding exhibit (2026-07-29T05:00Z, valid
row 1) classified `stopped_then_reversed`**: stopped at 32.9 pips, then an
~800-pip run in the signal's direction after the stop-hit bar (≥2R
threshold passed by ~24R). Rows 2–3 left blank (invalid_spec — never
autopsied). All pre-existing column values byte-identical after migration.
Gate 3 pending: first loss classified at scheduled grading time.

N discipline, stated before anyone asks: one classified loss is an
anecdote with a good filing system. Species tallies inform nothing until
a candidate reaches its FLAG gate (N=30 graded episodes).

---

## 2026-09-09 — Tally correction: net-at-horizon is clairvoyance, not performance; R respects the stop

Review ruling (2026-09-09): the definitive win/loss outcome is R-multiple.
`hit_stop=True` ⇒ LOSS, always, regardless of where price sat 30 bars
later — the framework was stopped out and did not hold the position.
`get_shadow_tally` previously counted `net_30bars_pips > 0` as a win, so
the founding exhibit (stopped for −1.0R at 32.9 pips, net +529.1 at
horizon) showed as "1 win". Corrected: wins come from `r_multiple > 0`;
`net_30bars_pips` REMAINS in the ledger as a diagnostic field — the loss
autopsy needs it to identify noise-stops — but determines win/loss
nowhere. Founding exhibit's honest line: **LOSS, −1.0R, species
stopped_then_reversed, net +529.1 (diagnostic only).**

Gate 1: 3 pins (stopped-with-positive-net is never a win; unstopped
positive R is; unstopped negative R isn't); suite 1130 → 1133 green.
Gate 2 (REALITY): corrected live tally — EARLY_MOMENTUM
{logged: 1, graded: 1, wins: 0, avg_net: +529.1}, 1 episode.

**Housekeeping (same branch): launchd fleet re-based onto one clock.**
All 6 jobs unloaded and reloaded via scripts/launchd/install.sh under the
current system timezone (America/New_York): the four original jobs had
kept their July (Pacific-loaded) firing instants through the machine's
PDT→MDT→EDT moves while the two jobs added 2026-09-09 registered on
Eastern — two clocks in one fleet. Fixed local instants now, all Eastern:
brief-london 02:30, brief-ny 07:30, outcomes 15:15, brief-asia 18:00,
calendar Sun 12:00, heartbeat Sun 12:30. Verified: `launchctl list` shows
all six; StartCalendarInterval dumped per plist. Consequence, stated for
the record: the scheduled UTC instants shift by the Pacific/Eastern
offset from their August values; the first post-reinstall scheduled runs
are the live confirmation (Gate-3 entry already open).

---

## 2026-09-09 — Exhaustion subtype display (per docs/specs/exhaustion_subtype_display_spec.md)

Diagnostic (same day, read-only): the GBP/JPY brief rendered "4-hour chart:
moving sideways (trend strength 64/100)". Trace: `_classify`'s deliberate
GBP/JPY exhaustion branch (adx ≥ 35 → RANGING, "fade don't follow" — the
82.7% mean-reversion prior) flattened by a display layer with one phrase for
two meanings of RANGING. Classification routing correct; wording dishonest.

Built: `_classify_ex` returns (regime, subtype) at the ONE place that knows
the threshold — `_classify` is now a thin wrapper, every call site and
routing decision byte-identical (pinned across the branch matrix).
`get_regime` exposes `regime_d1_subtype` / `regime_h4_subtype` /
`structure_h4`; the display derives nothing. REASON / MARKET STATE / FULL
PICTURE render exhaustion states as "in a strong <direction from confirmed
structure>, flagged as overextended — the framework does not chase this
(trend strength N/100)"; quiet RANGING keeps "moving sideways"; filter
reasons get a subtype-aware token pre-pass so "RANGING D1" can never render
as sideways during D1 exhaustion.

**Recorded as directed, mirrored in AGENTS.md:** RANGING is overloaded
(quiet vs JPY exhaustion). PRECONDITION: promoting EXHAUSTION to a
first-class regime — classifier, composite table, conflict logic, tests —
is REQUIRED before RANGE_TRADING_ENABLED may ever be set True. Not built
now.

Gate 1: 15 pins (subtype source, routing matrix unchanged, all three
sections' wording both ways, D1 equivalent, structure fallback,
banned-token check, official decision identical with/without the new
fields); suite 1133 → 1148 green, shadow 868 green. Gate 2 (REALITY):
below, live GBP/JPY 64/100 exhaustion state.

---

## 2026-09-09 — Notification click-through built (per docs/specs/notify_click_through_spec.md)

Built on `feat/notify-click-through`: terminal-notifier **3.1.0** installed
from the official prebuilt release (repo julienXX/terminal-notifier,
verified via the GitHub API; URL + SHA-256 recorded in the spec; no brew,
no Xcode) to ~/Applications/terminal-notifier.app. One shared
`scripts/notify.sh` `notify <CATEGORY> <msg> <log>` now serves all three
wrappers (ALERT / RECOVERED / SHADOW / DECISION / HEARTBEAT), with click
opening the day's log via a %20-encoded file URL and every message ending
in a "→ logs/…" pointer so the fallback still says where to look. A
bounded watchdog (15s) guarantees a hung or failing post falls back to
osascript — a notification is never lost and a scheduled run can never
hang on a permission dialog. Wrapper firing conditions and texts unchanged.

Gate 1: 7 helper pins (invocation args + URL encoding, pointer, missing/
hung/nonzero-exit fallbacks, no double-notify) + wrapper routing pin;
suite 1150 → 1157 green. Gate 2 (REALITY): real posts through the
installed binary; the exact -open URL opened the log via the system
handler (`open` exit 0); fallback exercised with the binary renamed and
restored. **One-time approval flagged, per the spec's instruction:** the
first real post surfaced macOS 13's authorization dialog, which was
answered Don't Allow — posts now exit 3, the helper's fallback carried
every message (observed live), and tccutil cannot reset this service class
(exit 70). Click-through stays dormant until System Settings →
Notifications → terminal-notifier is set to Allow.

---

## 2026-09-09 — First full scheduled evidence day; two observations for team decision

The heartbeat/credentials merge met its first real day. From
logs/brief_2026-09-09.log, in order: the Gate-2 forced failures (00:32,
ALERT at 2nd consecutive), the recovery (00:32:38, RECOVERED after 2), then
TWO healthy launchd runs (05:32:52, 10:30:15 EDT) with real prices, the
exhaustion wording live in scheduled production output (GBP/JPY 4-hour
"in a strong downtrend, flagged as overextended — the framework does not
chase this (trend strength 64-65/100)"), and the first two real ##ALERT##
flips, routed to notifications. Three Gate-3 items moved (two cleared, one
partial — see the pending section).

**Observation 1 — launchd timezone (team decision needed):** last night's
re-base to America/New_York did not change firing instants: the session
launchd still resolves StartCalendarInterval in Pacific (05:32/10:30 EDT
observed against plists saying 02:30/07:30). The fleet is on ONE consistent
clock — the Pacific one. Realizing Eastern needs a logout/reboot; until
then expect outcomes 18:15 EDT, Sunday calendar 15:00 EDT, heartbeat
15:30 EDT. No action taken.

**Observation 2 — session-delta display bug (reported, not fixed):**
"⚡ SESSION Since 3h 53min ago: Regime changed (no clear direction → no
clear direction)" — session_memory.py:130 sets regime_changed on D1 OR H4
change, but the render (session_memory.py:297-299) prints only the D1
pair, so an H4-only flip (GBP/AUD H4 RANGING↔VOLATILE at trend strength
17-18) displays as X → X. Same display-honesty class as the exhaustion
fix; also the source of both of today's ##ALERT## flips (borderline
oscillation chatter at the RANGING/VOLATILE boundary). Team decides
whether to fix the render alone or also debounce the flip alert.

---

## 2026-09-09 — setup_check plain-English rewrite (per docs/specs/setup_check_plain_english_spec.md)

Built on `feat/setup-check-plain-english`: every line now reads as a
colleague explaining — BIAS/REGIME in decision_brief's voice (exhaustion
subtypes honored), the "since last run: Since…" duplication fixed, PLAY
asks "Agree?" or says "it's a feeling, not a trade", CLOCK/FUEL/RISK per
the directed templates. New NOISE FLAG: stop closer than
MIN_STOP_ATR_MULTIPLE (0.3, INFORMED PRIOR, Episode-1 exhibit cited in the
code) × daily range renders "hit by accident, not by being wrong"; with
--target the flattering-ratio warning fires. Overrides ('o') now CAPTURE
the human's read into the record (previously lost). Advisory VERDICT
(negative/positive/Mixed) computed after confirms, printed last, and
carried in the journal's risk column — the 21-column schema unchanged.
Parser addition (additive): "approved YYYY-MM-DD" accepted as the dated
header — the live storylines.md always used that form and was being
treated as undated. Banned tokens extended (invalidation / none-named /
structural / bare regime / bare stack in sentence bodies; header renamed
PRE-TRADE CHECK) — the sweep caught "Regime changed" leaking through the
delta path during build; reworded.

Gate 1: 26 new pins (every line variant, all three verdicts, extended ban,
journal round-trip) + 4 old wording pins updated (markers/math pins
unchanged); suite 1157 → 1183 green, shadow 868. Gate 2 (REALITY): live
GBP/AUD SHORT rendered in full — nearest level 1.8769, 7 pips above price,
0.09x the 83-pip daily range → noise flag fired; storyline "last approved
2026-08-03" named from the real file; verdict "stop inside noise, against
the framework's read. Nothing here says NOW." — printed and logged
(id 20260909T161724Z_GBP_AUD_SHORT, real journal row).

**Amendment (team ruling, 2026-09-09, same day):** verdict promoted from a
risk-column suffix to a real `verdict` column — the journal's 22nd, additive,
old rows blank, loss_species-style logger migration; schema pinned at 22 by
test. Gate 2 (REALITY): a real setup_check run migrated the live
pre_trade_journal.csv 21 → 22 columns — both pre-ruling rows verbatim with
blank verdict, the new row (20260909T163506Z_GBP_AUD_SHORT) carrying
"VERDICT: stop inside noise, against the framework's read. Nothing here
says NOW." in its own column. The one interim row written under the draft
build (20260909T161724Z) keeps its " | VERDICT:" suffix inside `risk` —
recorded history in an append-only ledger, left untouched.

---

## 2026-09-09 — Unconfirmed-trend display subtype (per docs/specs/unconfirmed_trend_display_spec.md)

Stage-1 diagnostic (read-only, recorded in the spec): GBP_AUD D1
TRANSITIONAL is confirmation LAG, not a bug — highs stepped down
(1.91912 → 1.89716) but the last CONFIRMED swing low is 1.90733
(2026-08-04) vs 1.90030 (07-27): a higher low recorded before the ~290-pip
decline, because in a persistent fall no new low survives the 3-bar shape
plus close-above confirmation. The blocking pair: the swing lows. Engine
output matched hand replication exactly.

Stage-2 build on `feat/unconfirmed-trend-display`: subtype
UNCONFIRMED_TREND single-sourced at _classify_ex's trending-band
fallthrough (regime stays VOLATILE — routing pinned unchanged); get_regime
exposes FACTS (signed 10-session closed-bar pip change, the leg's pending
extreme + age, the engine's lh/hl flags — description, not
classification). Display: "Daily chart: falling — down 290 pips over the
last 10 sessions — but the confirmation rule isn't met yet"; FULL PICTURE
"the engine is waiting for the latest low to confirm"; EXIT IF names the
real pending pivot with the engine's TRUE rule and is honesty-gated (only
promised when the other pivot pair already agrees and the candidate would
complete the pattern). Deviations from the directive's illustrative text,
flagged in the spec: the fact computes to −290 (not the example −302), and
the parenthetical "(three sessions closing above it)" was rendered as the
actual rule (3-bar shape, then ONE close above).

OPEN QUESTIONS logged as directed: (1) does transition-zone VOLATILE
(18–25) deserve the same factual treatment? Its current "choppy with no
clear direction" wording was kept verbatim per the directive, though that
sits in tension with "choppy is permitted ONLY for quiet RANGING". (2) the
H4 subtype is exposed but unrendered (directed templates were daily-only).
(3) observed residual: DATA BASIS still labels the accuracy record "daily
chart no clear direction" — it is keyed to the regime bucket the outcomes
are actually logged under; renaming it touches evidence lineage, team call.

Gate 1: 16 pins (subtype source, routing matrix, both display sentences,
EXIT IF young/complete/three honesty fallbacks, vocabulary ban,
transition-zone + H4 wording unchanged, official decision identical);
suite 1184 → 1200 green, shadow 868. Gate 2 (REALITY): live GBP/AUD brief
rendered the new daily sentence and the concrete EXIT IF naming the real
pending low 1.8732 with its true 2-sessions-plus-close condition.

---

## 2026-09-09 — Unresolved-direction polish (per docs/specs/unresolved_direction_polish_spec.md)

**On the record, as directed: the structure rule cannot confirm a trend
mid-leg; it confirms on the first bounce — by design, and the cost is
first-leg participation. The subtype is now logged so the unresolved
bucket can be split in future accuracy analysis.**

Built on `feat/unresolved-direction-polish` (after merging the
unconfirmed-trend branch to main): TRANSITION_ZONE subtype named at the
classifier's 18–25 branch (routing unchanged); transition-zone VOLATILE
renders "no clear direction yet (trend strength X/100, transition zone)"
on both timeframes; "choppy" removed from the VOLATILE vocabulary (ban:
everywhere except quiet RANGING); H4 UNCONFIRMED_TREND renders the
falling/rising template with its own fact (`h4_change_pips_10`), phrased
"over the last 40 hours" — a session-count phrase on H4 would be a unit
lie; DATA BASIS label → "daily unresolved-direction bucket (transition
zone + unconfirmed trends)" with the VOLATILE evidence key untouched;
regime_classification_log.csv gained the additive `subtype` column (26th,
loss_species migration pattern, schema pinned) populated by log_regime as
`d1=<sub>;h4=<sub>`. The live ledger was migrated via the logger: 26
headers, all 25 old rows verbatim with blank subtype.

**FINDING, flagged for team decision (not fixed here — behavioral):
nothing on the live path calls `log_regime` any more.** Only the module's
own docstring references it; the evidence loop grades old rows but has
accrued no new classification since 2026-07-29. "Populated on every new
classification" is built at the logger; a caller must be re-wired (own
spec) before new rows — and their subtypes — accumulate.

Gate 1: 12 new pins + 2 superseded pins updated; suite 1200 → 1212 green,
shadow 868. Gate 2 (REALITY): live briefs on BOTH pairs — GBP/AUD "falling
— down 290 pips …", GBP/JPY daily "falling — down 878 pips …" beside the
H4 exhaustion sentence; DATA BASIS shows the new bucket label with the
same 3-outcome record; live ledger migrated 25 → 26 columns.

**Addendum (final before freeze, 2026-09-09):** daily DIGEST notification
folded into this branch per docs/specs/daily_digest_spec.md — the 07:30
job's plist passes the `digest` argument (deterministic, not
clock-guessed; reinstalled and verified in launchctl), the wrapper posts
ONE category-DIGEST notification with both pairs' decisions + the concrete
watch condition, clicking through to logs/latest_brief.log (generated on
the digest run by scripts/latest_view.py — the ONLY slice of the held
latest-view spec that is built; the full every-run version stays held).
Gate 1: 8 pins (digest line incl. concrete-watch preference and failed-run
wording; view layout incl. error runs and alert lines; digest strictly
arg-gated; only brief-ny's plist passes the arg); suite 1212 → 1220 green.
Gate 2 (REALITY): real `scheduled_brief.sh digest` run — real DIGEST
notification, real view (latest block + all five earlier runs digested +
both ##ALERT## lines + pointer), click URL opens it; a real non-digest run
posted no digest and left the view byte-identical. Gate 3 pending: first
scheduled 07:30 digest via launchd.

---

## 2026-09-10 — Display timezone (freeze exception, per docs/specs/display_timezone_spec.md)

User-requested display-layer exception during the freeze: every time a
human reads now renders in ONE configurable zone (`display_time.py`,
DEFAULT America/Los_Angeles, `DISPLAY_TZ` env override; PROTECTED list
18 → 19). Abbreviations come from zoneinfo by date — PST/PDT switch
automatically, nothing hardcoded. Converted: brief header, market-closed
note ("Next open Sun 2:00 PM PDT"; the machine field next_open_utc became
true ISO-Z), news-gate stand-down reason and setup_check CLOCK gain
"(at 11:00 PM PDT)" from the gate's new additive `event_time_utc` field,
wrapper ===== headers (sanctioned shell form: TZ-env date), heartbeat's
last-success line. Verified untouched: all ledger/bar/dedup timestamps,
market-hours logic, calendar window math; calendar_fetch confirmed to
store naive-UTC (astimezone(utc) before write — the 2026-09-11 06:00 GBP
GDP row is 06:00 UTC). trade_logger verified to render no times; digest
text carries none.

Gate 1: 12 pins (PST and PDT dates, styles, env override, gate firing at
the identical UTC instant under LA/NY/UTC display zones, official
decision byte-identical, market-note + filter-reason + CLOCK renders, no
bare "UTC" in prose); suite 1220 → 1232 green, shadow 868. Gate 2
(REALITY): live brief header "Wed 09 Sep 2026 9:30 PM PDT"; live
setup_check; real digest run with view header "2026-09-09 21:31:03 PDT";
Friday's UK GDP (real calendar.csv, gate's own now parameter inside the
window) rendered "GDP m/m in 1h 30m (at 11:00 PM PDT)". Freeze resumes on
merge — this exception adds no queue items.

**Addendum (2026-09-10, same exception): the view's "today" is the display
day.** The first build grouped "TODAY SO FAR" by the log FILE's midnight
(system clock): at 9:33 PM PDT the view showed one run because the file
had rolled at midnight Eastern. latest_view.py now derives today in
DISPLAY_TZ, reads the candidate day files (D−1/D/D+1 by name — file
NAMING unchanged: records, not display), keeps blocks whose ===== header
carries today's display date, and closes with "Full record:" naming every
file drawn from. Pins: display day spanning two files; other-date blocks
excluded; sources line exact; signals follow their blocks; empty-day
fallback. Suite 1232 → 1233 green. Gate 2 (REALITY): regenerated at
21:37 PDT — the previously-truncated moment — TODAY SO FAR now lists all
ten of the display day's runs across brief_2026-09-09.log +
brief_2026-09-10.log with both alerts, sources named. Transition-day
quirk documented: blocks stamped pre-conversion (EDT) group by their
stamped date; coherent from the first full display day onward.

---

## 2026-09-10 — launchd fleet re-based explicitly to America/Los_Angeles (freeze-adjacent correction)

**WHY, on the record:** the outcomes job must run AFTER the 21:00 UTC
daily close. At 15:15 America/Los_Angeles it fires at 22:15 UTC — after
the close, grading the just-closed bar. If the same wall-time were ever
interpreted as Eastern, 15:15 EDT = 19:15 UTC — BEFORE the close — and
the grader would grade stale bars. The zone is therefore part of the
schedule's correctness, not a preference.

Done, no restart: all six plists now carry
`EnvironmentVariables TZ=America/Los_Angeles` (matching DISPLAY_TZ), the
user-session env is pinned (`launchctl setenv TZ America/Los_Angeles`),
and all six were reinstalled. Verification dump: london 02:30 / ny 07:30
(+digest arg intact) / outcomes 15:15 / asia 18:00 / calendar Sun 12:00 /
heartbeat Sun 12:30 — every plist TZ=America/Los_Angeles; observed firing
basis is already Pacific (yesterday's fires at 02:32/07:30/18:00 PT).

**Honest limit, recorded so nobody trusts the wrong key:** launchd
computes StartCalendarInterval in the SESSION's zone, not from the
plist's EnvironmentVariables (those pin the job's process env — display
and any date math inside the wrappers). Today the session computes in
Pacific (observed). After any reboot/login the session zone follows the
system setting (currently America/New_York) unless the pinned session
env carries over — SO: after any reboot or timezone change, the first
outcomes fire time must be checked against 22:15 UTC (the Sunday
heartbeat and the dated log headers make this a one-glance check). If it
ever shifts to 19:15 UTC, the machine's system zone must be set to
America/Los_Angeles — that, not the plist key, governs the schedule.

---

## 2026-09-10 — State-dependent labels (freeze exception, per docs/specs/state_dependent_labels_spec.md)

Label honesty, same class as the regime subtype fixes: a STAND ASIDE
brief has no position to exit, so its condition slot is now labeled
**WATCH FOR**, and the concrete pending-pivot sentence carries the
directed guard so it never over-promises: "…the downtrend is confirmed
then — the trade still depends on the filter, the calendar, and a valid
stop. Revisit then." LONG/SHORT briefs render **ENTRY** (trigger + level
from the entry brief — the same read-only computation the trade path
already prints), **EXIT IF** with its meaning restored (a position
exists; this is where it is wrong), and **TARGET** stated honestly: the
framework does not generate targets — set your own, it must pay ≥1.5x
after the spread. FULL PICTURE already phrased both states correctly
("This changes when…" / stop-as-invalidation) and inherits the guard via
the shared sentence. The daily digest's watch extraction accepts both
labels. Decisions byte-identical (display fields only).

Gate 1: 6 new pins (labels per state, slot order, guard both directions,
generic sentence unguarded, digest under both labels) + 2 pins updated;
suite 1233 → 1239 green, shadow 868. Gate 2 (REALITY): live briefs on
BOTH pairs render WATCH FOR with the guarded concrete sentence —
GBP/AUD's pending low 1.8732 now one session from shape-complete;
GBP/JPY naming its own pending low 207.1000. Zero "EXIT IF" on live
stand-aside briefs.

**POST-FREEZE QUEUE, first item (recorded, NOT built):** "IF IT
CONFIRMS" conditional plan on stand-aside briefs when the WATCH FOR
condition is within 2 sessions — play name, trigger, stop, first target,
noise-stop check pre-run, storyline agreement — explicitly conditional,
never a signal. Spec after 2026-09-16.

---

## 2026-09-10 — Evidence loss: regime classification never logged from the live path (freeze exception, safety class; docs/specs/regime_log_restore_narrative_truth_spec.md)

**The loss, stated honestly:** regime_classification_log.csv holds 25 rows,
all from two manual bursts (2026-06-28 validation work; 2026-07-28/29
cleanup-audit verification). `log_regime`'s only caller ever was the shadow
stack's `market_brain.build_market_report` (exception-swallowed), which was
never scheduled; the official brief path never called the write side at all
(it imports only `get_regime_accuracy`). The 2026-07-29 quarantine (commit
2188ad5) removed the last reachable caller. Every scheduled brief since the
system went live classified a regime and made an implicit prediction that
was never recorded — including the resolution-table cells whose re-evaluation
mandate ("60+ outcomes per combination") this ledger was supposed to feed.
**No backfill.** Reconstructed rows would be lookahead-contaminated
hindsight, not predictions. The gap stands as recorded evidence loss; the
DATA BASIS lines' small N is the honest consequence.

**Discovery path:** the 2026-09-10 18:04 PDT GBP/AUD brief rendered a live
SHORT @0.5x whose REASON inverted the raw state ("4-hour trending inside
daily trending_down" — H4 was the unresolved one, ADX 22 transition zone)
and whose FULL PICTURE asserted "All three timeframes line up" from the
existence of the decision, not from the fields. The diagnostic that traced
those two template defects found the dead ledger while hunting the raw
values (session_context_log.csv row 2026-09-11T01:04:13Z supplied them:
regime_d1 TRENDING_DOWN, regime_h4 VOLATILE, adx_d1 25.9, adx_h4 22.0,
cell → REDUCED_MOMENTUM 0.5x).

**Item-0 ruling (recorded):** the (TRENDING_DOWN, VOLATILE) cell's "wait
for H4 to resolve" exists only in its note string; no code gates on H4
between the table and the decision (H4's entire influence: a +5 conviction
bonus it fails to earn). Tonight's SHORT was mechanically intended behavior
with semantically ambiguous authorship. **Cell behavior unchanged in this
build** — an H4 gate is live trading logic: separate spec, separate review,
and it needs the outcome data this build restores.

**Built (branch feat/regime-log-restore-narrative-truth, merge held):**
1. `log_regime` wired into `get_decision_brief` §1c — every live open-market
   run logs classification + prediction, subtype column included; closed
   market skipped (no new bar, no new prediction); failure = stderr line,
   never silent, never fatal.
2. REDUCED_MOMENTUM REASON renders per the actual (d1, h4) cell — the
   D1-trending/H4-unresolved wording now matches the table note; raw-token
   leak killed; exhaustion honesty preserved.
3. FULL PICTURE alignment is derived from regime fields (weekly via
   weekly_context + lt_trend, daily, 4-hour vs decision sign); unresolved
   and opposed timeframes are named; the reduced-size sentence renders only
   when size_mult < 1.0.
4. Systemic: scripts/artifact_freshness.py (pinned cadence table: regime log
   72h, session log 72h, calendar 192h, storylines 216h, shadow log 504h) —
   wrapper records a health FAILURE on any STALE artifact (rides the
   existing 2-consecutive/daily-repeat UNHEALTHY plumbing); Sunday heartbeat
   prints the full freshness report and treats STALE as NEEDS ATTENTION.
   Narrative-truth matrix pinned (test_narrative_truth.py), banned-token
   floor extended to raw snake_case tokens (shadow candidate IDs exempt by
   name).

Gate 1: 15 new pinned tests; suite 1239 → 1254 green. Gate 2 (REALITY) and
Gate 3 pending entries: see below and the PENDING LIVE CONFIRMATION list.

---

## 2026-09-10 — LEDGER INTEGRITY: THRUST_PULLBACK rows from go-live to this fix are UNOBSERVED, not absent (freeze exception, safety class — fourth silent failure)

**The defect:** `compute_atr_series` returns n − 14 values (the live H4 feed:
300 bars → 286 ATR values), and `check_thrust_pullback` indexed `atr[b]`
with a bar index from the longer array. Its break-bar window (b = n−11 …
n−2) lies entirely past the ATR list's end for EVERY series length the
guard admits, so the check raised IndexError on its first candidate bar on
**every live call since go-live (2026-07-29)** — before evaluating a single
box. `check_shadow_signals` swallowed the exception into "no signal", so a
structurally can't-fire candidate logged as a market with no setups.
Diagnostic reproduction (2026-09-10): bars n=300, len(atr)=286, offset=14,
candidates b=289..298 vs max valid ATR index 285 — IndexError at the
box-tightness line, rendered as a clean empty result.

**Why Gate 1 never saw it:** every THRUST_PULLBACK test fixture built
`atr` the SAME length as the bars — a shape the live path never produces.
The trigger logic was correct and fully pinned; the pins ran against an
impossible input. (Recorded as a standing lesson: fixtures must carry the
live data SHAPE, not just the live data logic — this is the same class as
the Two-Gate standard's founding cases.)

**Ledger ruling (integrity note):** THRUST_PULLBACK has ZERO rows for
2026-07-29 → 2026-09-10 because it could not observe, not because the
market offered nothing. That window is **UNOBSERVED, not absent** — it must
never be cited as "no setups occurred", and no episode count, base rate, or
FLAG/DECISION clock includes it. **THRUST_PULLBACK's N starts at this fix.**
No backfill: replaying the window now would grade with today's knowledge of
the bug window's prices — lookahead-contaminated, refused.

**The fix (branch feat/thrust-pullback-alignment, merge held; stacked on
feat/regime-log-restore-narrative-truth — merge order matters):** bar→ATR
index mapping (`off = len(C) − len(atr)`; `_atr_at(b) = atr[b − off]`) with
a defensive `b − off < 0` skip. Every frozen spec parameter (TP_BOX_N 18,
TP_BOX_X 3.0, TP_BODY_ATR 1.0, TP_PULLBACK_ATR 0.25, TP_PULLBACK_BARS 10)
is byte-identical — a computation repair, not a trigger change, so the
candidate id stays THRUST_PULLBACK per the frozen-spec rules (same ruling
class as EARLY_MOMENTUM v1→v2 is the CONTRAST: that changed fire behavior
by adding a guard; this makes the specified computation happen at all).
`check_shadow_signals` no longer swallows: any candidate error prints a
machine `##ALERT## SHADOW CANDIDATE ERROR` line on stderr; the wrapper
routes it to the day log + a notification AND records a health FAILURE
(daily UNHEALTHY repeat until fixed); the Sunday heartbeat counts the
marker among error markers. One broken candidate never silences the rest.
Remaining known swallow (scope-noted, not changed): the news-gate context
stamp try/except in check_shadow_signals — failure there loses only the
`news_window` annotation, never a signal.

Gate 1: 6 new pins (live-shape contract n−14; evaluates + fires at live
shape; identical behavior at legacy equal-length shape; loud error marker;
error never silences other candidates; healthy runs emit no marker) —
suite 1254 → 1260 green. Gate 2 (REALITY): live OANDA both pairs — bars
300 / atr 286 / offset 14 exactly as diagnosed; check_thrust_pullback
evaluated cleanly to an HONEST zero on both (pre-fix: guaranteed
IndexError); no error marker emitted.

---

## 2026-09-11 — Housekeeping: validate_adx_threshold header date corrected (transcription, not a re-run)

The "ADX Threshold Validation (Problem 1)" entry header read **2025-06-25**;
git history shows the script landed 2026-06-25 (commit "Add Problems 2-3:
pivot structure detection, pair-specific ATR thresholds, empirical
validation") and the repo's first commit is 2026-05-16 — a 2025 run is
impossible. Header corrected to **2026-06-25**. Content untouched; findings
remain INFORMED PRIOR per Audit Item 2. Directed by the team 2026-09-11
alongside the data-map spec (docs/specs/data_map_spec.md).

Noted, left as-is pending team ruling: the neighboring early entries
("2025-06-25" Problem 1 Live API / Problem 2 / Problem 3, "2025-06-28"
Problems 4-8) show the same year pattern predating the repo's first commit.
Only the entry named in the directive was corrected.

---

## 2026-09-11 — Housekeeping (team-directed): ALL impossible-year headers corrected (transcription, not re-runs)

Completes the correction opened in the entry above and supersedes its
"left as-is pending team ruling" note. Eleven further entry headers carried
2025 dates that are mechanically impossible — **the repo's first commit is
2026-05-16**, so no 2025 run exists. Corrected in place, year only, content
untouched, no re-runs:

- 2025-06-25 → 2026-06-25: Problem 1 Live API Validation; Problem 2 Stress
  Test + Deep Verification; Problem 2 Final Sign-off; ATR Spike Multiplier
  Validation (Problem 3); Problem 3 Live Historical Replay Validation.
- 2025-06-28 → 2026-06-28: Four-Issue Implementation + Validation;
  Problem 5: Confluence Scoring Rebuild; Problem 6: Composite Regime
  Resolution Table; Problem 7: Validation Infrastructure; Problem 8:
  No-Trade Filter + Counter-Trend Override.
- 2025-06-29 → 2026-06-29: Priority 1: Decision Brief + Entry Confirmation.

Mechanism of the original error: transcription at write time (a year typo
propagated across one writing session), surfaced by the 2026-09-11
earliest-load inventory when git dates were checked against log headers.
All statuses (INFORMED PRIOR demotions etc.) unchanged.

---

## 2026-09-11 — STAGE 2 (data_map_spec §10): overlap check FAILED — history-validation INFEASIBLE under today's sourcing

Executed per docs/specs/data_map_spec.md (f5eea4f, amended 67578e5).
Verification numbers only; no price statistics; **no STUDY bar was
converted — the ladder stopped the sequence before conversion.**

**Sourcing record (all attempts 2026-09-11):**
- `datafeed.dukascopy.com` (raw bi5, M1/tick-capable): HTTP 503 then
  connection timeouts, all session — unreachable.
- HistData.com (named fallback): site reachable, but `/get.php` returns
  0 bytes for every dataset; the form token is served EMPTY even to a
  fully-rendered headless-Chrome DOM. Download flow non-functional
  programmatically.
- `freeserv.dukascopy.com` chart feed (same provider, H1 transport):
  used for the overlap check. Coverage probes: GBP_JPY hourly available
  ≥ 2005-02-01; GBP_AUD hourly begins between 2006-03-15 and 2006-04-15
  (exact first bar not pinned — sequence stopped first).

**Feed-overlap check** (2023-09-01 → 2026-09-10, freeserv mid vs OANDA mid,
frozen thresholds: disagreement ≤ 2%, median |close diff| ≤ 1.5 pips):

| pair/TF | matched | med O/H/L/C (pips) | disagree >5p |
|---|---|---|---|
| GBP_AUD D1 | 784 | 4.22 / 0.30 / 0.30 / 1.55 | 53.6% |
| GBP_AUD H4 | 4704 | 0.30 / 0.25 / 0.25 / 0.30 | 12.7% |
| GBP_JPY D1 | 784 | 2.90 / 0.20 / 0.20 / 1.65 | 39.7% |
| GBP_JPY H4 | 4704 | 0.25 / 0.15 / 0.15 / 0.20 | 9.2% |

**FAIL on both pairs.** Decomposition (same check, verdict unchanged): the
17:00-NY rollover dominates — H4 slot-0 disagreement 62%/44% vs 2.83%/2.24%
on all other slots — but even the non-rollover slots exceed the 2% bar and
both D1 close medians exceed 1.5 pips, so the failure is not solely the
H1-transport's inability to reproduce tick-accurate rollover opens.

**Ladder ruling (spec §2):** Dukascopy FAIL → HistData re-run NOT EXECUTABLE
(endpoint dead) → **history-validation is INFEASIBLE as of 2026-09-11
sourcing conditions.** The forward ledger remains the only path. The SEALED
EXAM stays closed; the STUDY span stays unopened.

**Re-attempt condition (team decision, not self-authorized):** if
`datafeed.dukascopy.com` becomes reachable, an M1/tick-based re-attempt
would remove the rollover-granularity component of the disagreement; the
residual (~2.2–2.8% mid-session, ~1.6-pip close offset between liquidity
pools) may still fail the frozen thresholds — that is what they are for.

Full numbers: studies/stage2_gate_report.md. Script:
studies/stage2_source_convert_gate.py (sourcing record in header).

---

## 2026-09-16 — STEP 0 (team-authorized interim): `last_run.json` neutralized

**This replaces a WRONG level filter with NO level filter. That is an
improvement, not a fix.** The repair is specified in
docs/specs/level_source_repair_spec.md (Step 1); this entry records only
the interim action, authorized standalone by the team without spec or
branch.

**Action:** `last_run.json` → `last_run.json.orphaned-2026-09-16`
(renamed, NOT deleted — it is an artifact; gitignored, so a plain `mv`,
no `git mv` applies). `entry_confirmation.py:180-190` now finds no file,
sets `_level_available = False`, and its M15 trigger takes the
`elif not _level_available` degraded-pass branch instead of the `else`
branch that was silently gating on 2026-06-10 levels.

**Why it was authorized ahead of the spec.** The file's only writer is
`shadow/market_brain.py` (quarantined 2026-07-29); nothing on the live
path has written it since. Content frozen at 2026-06-10, `price 1.9076`,
levels 1.8718–1.90906 — 98 days stale and single-pair. Because the file
EXISTED, `entry_confirmation` (PROTECTED) trusted it. A deleted file
degrades gracefully; a stale file does not. The interim restores the
graceful mode.

**Defect 2 confirmed independently before acting (standing rule 5).** The
team's code-review finding reproduces: the file carries ONE pair's levels
with no instrument key, while `get_key_levels` is pair-parameterized.
Measured this session — GBP_JPY 208.8685 vs GBP_AUD 1.8903, stored levels
1.8718–1.90906, proximity threshold 25 pips (`_M15_LEVEL_PROXIMITY_PIPS`
× 0.01 = 0.25 for JPY). Minimum achievable distance ≈ 207.0 against a 0.25
tolerance: `near_key_level` could never be True on GBP_JPY, and with
`_level_available` True the code took the `else` branch
(entry_confirmation.py:227-231, "not near a key level"), never the
degraded-pass branch. **`m15_trigger`, and therefore `entry_ready`, could
never be True on GBP_JPY** — silently, since the file froze. One pair's
entry path has been dead for 98 days with no error, no log line, and no
test failure. Recorded as a separate defect, not a footnote.

**Verification.** Controlled: replicating entry_confirmation.py:180-190
against the working tree returns `exists=False`, `_levels=[]`,
`_level_available=False` → degraded-pass branch reachable. REALITY (both
pairs, live OANDA): `get_entry_brief` returns normally with no exception
from the absent file; GBP/AUD structure level 1.8904, GBP/JPY 208.8800 —
**the first correctly-scaled GBP/JPY level this path has produced since
the file froze.** No decision output changed (both pairs STAND ASIDE).

**Gate 3 — PENDING LIVE CONFIRMATION:** the degraded-pass branch itself
is reachable but was not *observed* firing — it requires an in-direction
engulfing on M15, which did not occur during verification. Clear this
when a real entry check takes the branch and logs
"level check unavailable (degraded trigger)".

**Not addressed here** (all held for the Step 1 spec): the orphaned read
itself (R1), pair keying (R2/Defect 2), weekly semantics (R5),
read-side freshness coverage (R3), and the quarantine-boundary test (R4).


---

## 2026-09-16 — Step 1: level-source repair (per docs/specs/level_source_repair_spec.md)

Built on `feat/level-source-repair`, spec committed first (`aaac3e3`).
**Merge held for team review.** Four defects closed; two guards added.

**D1 — orphaned read (R1).** `entry_confirmation.py:176-190` no longer
reads `last_run.json`; it calls `get_key_levels(oanda_pair)` directly.
The file dependency is removed rather than monitored — a staleness class
deleted beats one watched. `last_run.json.orphaned-2026-09-16` is
retained and never read again.

**D2 — no pair keying.** Resolved by the same change: `oanda_pair` was
already in scope at entry_confirmation.py:112. Pinned three ways — the
lookup receives `GBPJPY`; a JPY-scale level within tolerance now reaches
`m15_trigger = True`; and an AUD-scale level set against a JPY price is
pinned as still blocking, so the defect itself is a regression test, not
just a memory.

**D3 — weekly semantics (R5).** `weekly_high`/`weekly_low` →
`prev_week_high`/`prev_week_low` with the docstring corrected to what the
code always did. `current_week_high`/`current_week_low` added, aggregated
from this week's COMPLETED daily bars, with `session_*` covering today;
`None` on an empty week. Rationale recorded in the module: a high or low
is a recorded fact, not a revisable computation, so week-to-date data
carries none of the risk that justifies dropping a forming bar for an
indicator. `oanda_feed.py` unchanged. No consumer read the old keys by
name (`levels_as_list`, `nearest_*` iterate values); the same-named keys
in `shadow/market_brain.py:139-140` are that module's own dict —
confirmed by the shadow suite staying at 868 green.

**D4 — Asian range never pair-keyed (found while specifying R1, not in
the ruling).** `get_intraday_context()` took no pair and always fetched
GBPAUD, so `get_key_levels("GBPJPY")` returned six JPY-scale levels
beside `asian_high 1.89232` / `asian_low 1.88924`. Fixed at the root —
the signature now carries `pair="GBPAUD"`, defaulted so both existing
callers are unaffected. Severity was stated as latent rather than active
in the spec and that holds: the contaminants sat ~207 below any JPY
price and could not produce a false match. It had to be fixed in the same
change because R1 wires `get_key_levels` into the live entry path.

**Guard A (R3) — freshness covers the read side.** `READ_SIDE_NO_CADENCE`
added to `scripts/artifact_freshness.py`: `trades.csv` (event-driven —
weeks without a trade is normal) and `.env`. These render `watched:`
lines, never `STALE:`, so the wrapper's `^STALE:` grep cannot turn normal
operation into a health failure. A cadence was deliberately NOT invented
for either — a manufactured cadence would produce false alarms and teach
the operator to ignore the channel. `last_run.json` is deliberately
absent from the inventory because R1 deleted the read.

**Guard B (R4) — quarantine boundary,** with its limit recorded in the
test's own docstring: **it would NOT have caught D1.** `last_run.json`
is a bare repo-root filename with no `shadow/` substring; the artifact
was written by a quarantined module but did not live in a quarantined
path. The control that would have caught it is orphan detection, which
needs Step 2's read/write map. Recommend promoting that rule to a test
once Step 2 reports. Guard B scans string constants via AST excluding
docstrings — comments and docstrings never execute, and live modules
legitimately cite `shadow/market_brain.py` when explaining the boundary;
a guard that forced those explanations to be deleted would make the
boundary less legible. It is proved to fire on synthetic breaches and
proved not to fire on the prose forms live modules actually contain.

**Why these survived 98 days:** every one is a CONNECTION defect — a
reader whose writer was quarantined, a pair argument never threaded, a
signature that lied about being pair-specific. All the affected modules
had passing component tests throughout. The suite was component-shaped
and the defects lived between components. `test_live_path_connections.py`
exists to be the connection-shaped half.

**Gate 1:** 20 new tests (8 connection, 12 per-defect). Suite
1260 → 1280 green; shadow 868 green, unchanged. Neither floor touched.
AGENTS.md suite count corrected 1018 → 1280 (stale documentation, not a
behavior change).

**Gate 2 — REALITY (live OANDA, both pairs, 2026-09-16 ~08:50 UTC):**

```
GBPAUD  prev_day 1.89456/1.88938   prev_week 1.88838/1.87323
        current_week 1.89512/1.88617  session 1.89035/1.88904
        asian 1.89232/1.88924        contaminants: NONE
GBPJPY  prev_day 209.231/208.252   prev_week 211.224/207.100
        current_week 209.231/207.457  session 209.021/208.724
        asian 209.479/208.901        contaminants: NONE
```

**`asian_*` on GBP/JPY reads 209.479/208.901 — the first correctly-scaled
value that field has ever returned for this pair.** Real
`decision_brief.py GBP_AUD GBP_JPY` run: both pairs rendered normally
(GBP/AUD 1.8898 STAND ASIDE, GBP/JPY 209.038 STAND ASIDE), no exception,
no output regression. `artifact_freshness.py check` live: five cadence
lines fresh, two `watched:` lines present. No mock results appear above.

**Gate 3 — PENDING LIVE CONFIRMATION:**
- The degraded-pass branch firing in production (carried from Step 0).
- **The first GBP/JPY `m15_trigger = True` in live scheduled output** —
  the market's own proof that D2's silent kill is lifted. Controlled
  tests show the path is reachable; only reality can show it reached.

**Out of scope, unchanged:** the one-week level horizon and the unwired
`find_confluence_zones` / `nearest_resistance` / `nearest_support` /
`get_round_number_levels`. A level-map spec is its own work and was not
bundled into a defect repair.

**Step 2** (integration inventory, read-only) is held until this merges.


---

## 2026-09-16 — Step 2: integration inventory (read-only pass; team-authorized log)

One mechanical pass over the 19 live-core modules: what each READS, WRITES,
needs from env, who CALLS it, and whether each connection is currently live.
No repo changes; the analyzer ran from a scratchpad. Logged in full at team
direction because this IS the spec for anyone who rebuilds the guard later.

### Artifact map — writer → reader

```
calendar.csv                  W calendar_fetch, update_calendar
                              R calendar_fetch, news_gate, update_calendar
pre_trade_journal.csv         W setup_check          R setup_check, trade_logger
regime_classification_log.csv W/R regime_classifier_logger
session_context_log.csv       W/R session_memory
shadow_signal_log.csv         W/R shadow_signals
trade_signal_log.csv          W trade_outcome_logger R trade_outcome_logger
trades.csv                    W/R trade_logger       R session_guard
health_state.json             W/R scripts/health_state
storylines.md                 W — NOBODY —           R setup_check
```

`storylines.md` having no machine writer is CORRECT: a human writes it in
the Sunday session, and its 216h freshness cadence is precisely the control
for a human who stops. Recorded so a future orphan sweep does not "fix" it.

### Env dependencies

```
oanda_feed.py    OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT
display_time.py  DISPLAY_TZ
```

### Module reachability

All 19 resolve LIVE except three, each for a different reason:
`setup_check.py` is a manual CLI entry point (`__main__`, no importer — not
an orphan); `risk_config.py` is imported by NO live module — only tests and
four quarantined files; `session_guard.py`'s only importer is `risk_config`.
**The circuit-breaker chain therefore has no live entry point at all.** This
matches the AGENTS.md note that where it GATES the live path is a pending
spec, but states it more sharply: both modules were promoted OUT of
quarantine 2026-09-09 and their only real importers are still the
quarantined modules they were promoted away from.

### Orphans found

**LIVE DEFECT — `trade_outcome_logger.py`** (own spec, Part 1):
`log_signal()`'s only caller is `shadow/market_brain.py:297` (quarantined
2026-07-29); `record_outcome()` and `get_accuracy_by_signal_type()` have no
caller anywhere. `trade_signal_log.csv` last written **2026-06-28, 2 lines**
(header + one row), while `run_outcome_check.py:60` grades it nightly.
Neither it nor `trade_log.csv` (2026-04-02, 6 lines) is in the freshness
watchlist. Third instance of the quarantine-orphan class.

**Known-unused, listed NOT deleted** (several are seeds for the level-map
work): `levels_context.nearest_resistance/nearest_support/`
`find_confluence_zones`, `oanda_feed.get_m5_bars`,
`session_memory.get_session_history_today`, `risk_config.get_size_note/`
`format_grade_block/print_risk_rules`, `risk_config.calculate_lot_size`
(test-only), `session_guard.can_trade` (test-only, pending gate spec).

### TWO FALSE POSITIVES — and what they would have cost

Recorded because a guard built without both will fail loudly on working
code, which is the fastest way to get a guard deleted.

1. **Alias-resolved imports.** The first pass reported `apply_filter()` and
   `get_filter_summary()` as orphans. `regime_detection.py:1104` imports
   both under aliases (`as _apply_filter`, `as _get_filter_summary`).
   Reporting that unchecked would have claimed the single stand-down
   authority — one of the two suite floors — was dead code.
2. **Indirect dispatch.** The second pass reported all three FROZEN shadow
   candidates as having no live caller. `shadow_signals.py:218` holds them
   in `_CANDIDATES = [...]` and dispatches `for fn in _CANDIDATES`, so they
   are referenced as values and never called by name. Reporting that
   unchecked would have claimed the evidence ledger had stopped accruing.

Both were caught by hand-verifying every claim against source before
reporting. Every surviving claim in this entry was verified the same way.

### Method limits (stated, not hidden)

Static AST analysis with best-effort constant propagation: module constants,
local path aliases, parameter defaults, aliased imports, `__main__` entry
points. It cannot resolve a path built at runtime from a loop variable —
`scripts/artifact_freshness.py` reads all five watched artifacts through
one, and is classified by reading, not by inference. Dynamic dispatch beyond
list/dict registries is out of reach.


---

## 2026-09-16 — Evidence-loop repair (per docs/specs/evidence_loop_repair_spec.md)

Built on `feat/evidence-loop-repair`, spec committed first (`3e94f16`).
**Merge held for team review.**

### PART 1 — `trade_outcome_logger` wired into the live path

`log_signal` now has a live caller. `decision_brief.get_decision_brief`
logs every LONG/SHORT decision at the point where the official decision and
`entry_line` are both in scope. Contract matches the `log_regime` restore
exactly: **closed market skipped, loud on stderr, never fatal.**

**THE CONCRETE LOSS — named, per the ruling.** The first live SHORT in
framework history produced no ledger row and is unrecoverable:

```
logs/brief_2026-09-10.log, 18:04:14 PDT scheduled run
GBP/AUD  |  Thu 10 Sep 2026 6:04 PM PDT   Price: 1.8879  ATR: 84.3 pips
DECISION     SHORT ▼        CONFIDENCE 50/100  |  Rating: B
POSITION     50% of standard size
ENTRY        No bearish engulfing in trade direction — level 1.8862
```

**LEDGER INTEGRITY (binding).** 2026-06-28 → 2026-09-16 is **UNOBSERVED,
not absent.** No accuracy claim, base rate, or N may cite that window. No
backfill was performed and none may be: the signals that were not logged
are gone, and inventing them would be the exact dishonesty this framework
exists to prevent.

**Schema.** Additive migration on the real ledger, same guarantee as
`setup_check._migrate_journal_header` (reviewed 2026-09-09). Inspection
found the header was ALREADY two columns behind `_FIELDS` — `shadow_direction`
and `shadow_conviction` were missing — so the migration added four, not two.
The single 2026-06-28 row was verified preserved **verbatim**, blank in
every new column. Row count unchanged at 1.

**`record_outcome` / `get_accuracy_by_signal_type` — stated plainly rather
than wired speculatively.** `check_pending_trade_outcomes` is the scheduled
grader entry point and fills outcomes through the same `_fill_outcome`
helper (`trade_outcome_logger.py:289` vs `:206`), so `record_outcome` is a
parallel MANUAL single-row path and legitimately has no scheduled caller.
`get_accuracy_by_regime` IS called live (`run_outcome_check.py:68`);
`get_accuracy_by_signal_type` is its by-signal-type sibling, unused pending
a report that needs that cut. Both allowlisted with those reasons.

### PART 2 — orphan detection promoted to a test

Fails when a live-core function or artifact has no live producer/consumer
and no allowlist entry. Built with all four requirements from the start:
alias-resolved imports, indirect dispatch (names referenced as VALUES, not
just called), `__main__` entry points, and a reason per allowlist entry —
with the two Step 2 false positives pinned as explicit regression tests, so
a future rebuild cannot reintroduce them.

It immediately found one orphan not in the drafted allowlist:
`shadow_signals.backfill_loss_species`. Inspected rather than rubber-stamped
— its own docstring (`shadow_signals.py:502`) says "Manual/one-time path —
scheduled runs classify at grading time." Allowlisted with that citation.

**Root cause recorded.** The 2026-07-29 quarantine was audited
ONE-DIRECTIONALLY: what `shadow/` imports was checked; what imports
`shadow/`'s functions, and what consumes artifacts `shadow/` writes, was
not. Three severed connections followed from that single omission —
`log_regime` (2026-09-09), `last_run.json` and `trade_signal_log`
(2026-09-16). One event, one omission, three instances. This test runs the
audit in the other direction, automatically.

### DEVIATION FROM THE RULING — `trade_log.csv` cadence (standing rule 5)

The ruling directed that `trade_log.csv` be given a freshness cadence.
**Not done, with cause.** `trade_logger.py:22` calls it "the April-era
framework-snapshot file … historical"; `trade_logger_repair_spec.md:23-28`
already ran this premise inspection and ruled it "stays untouched as
historical evidence." Different schema entirely (bias / confidence /
value_zone, not trades), superseded by `trades.csv`, deliberately
writer-less.

A cadence on a deliberately frozen file renders STALE on every run forever
— **measured at 3987h on the first live check** — which the wrapper turns
into a health FAILURE, which alerts daily, which trains the operator to
ignore the channel. That would damage the very alerting path Part 1 relies
on, and it is the same harm this spec cites when refusing to invent a
cadence for `trades.csv`. Inventoried under `READ_SIDE_NO_CADENCE` with
that reason instead: visible on every check, never alarming. **Team to
confirm.** A cadence would first require the file to have a live writer,
which is separate work.

### Gate 1

17 new tests (8 trade-signal wiring, 9 orphan detection). Suite
1280 → **1297 green**; shadow **868**, unchanged. Neither floor touched.
`test_cadence_table_pinned` updated deliberately — that pin exists so a
cadence change is a reviewed decision, and this is one.

### Gate 2 — REALITY (live OANDA, 2026-09-16 09:08 UTC)

Real `get_regime("GBP_AUD")` against live OANDA; only the stand-down gate
and the direction were forced. Every market value in the row below is the
live one:

```
REAL regime: price 1.8898  atr 81.1p  adx 21.9/34.8  D1 VOLATILE
             H4 TRENDING_UP  structure DOWNTREND  weekly ESTABLISHED_DOWNTREND
ROW WRITTEN: 2026-09-16T09:08:09Z_GBP_AUD  GBP_AUD  SHORT  grade B
             conviction 50  price_at_signal 1.8898  atr_pips 81.1
             size_pct 50
             entry_context "No bearish engulfing in trade direction
                            — level 1.88924"
```

`artifact_freshness.py check` live: `trade_signal_log.csv` fresh (720h),
`trade_log.csv` present under no-cadence, no STALE lines.

**THE LEDGER PATH WAS REDIRECTED TO A TEMP FILE FOR THIS RUN, AND THE REAL
`trade_signal_log.csv` IS UNCHANGED AT 1 ROW.** The ruling asked for the
row to land in the real ledger. It was not, and this is raised rather than
resolved unilaterally: that row would be a signal the framework never
issued, written into an append-only evidence ledger, inside the very window
this entry declares UNOBSERVED. The wiring is proven end-to-end either way;
what a temp-file run cannot prove is a row caused by a real decision.
**Recommendation: the real-file row is a Gate 3 item.** If the team wants a
marked verification row in the real ledger instead, `trades.csv` PAPER rows
are the precedent and a marker column would be required first.

### Gate 3 — PENDING LIVE CONFIRMATION

- **First real row in `trade_signal_log.csv` from a genuine directional
  decision.** Only the market can perform this.
- Carried forward: the degraded-pass branch firing in production; the first
  live GBP/JPY `m15_trigger = True`.

---

## 2026-09-16 — THE QUARANTINE-ORPHAN CLASS: three instances, one omission

Recorded as a class, not three bugs, because the fix for a class is a
control and the fix for a bug is a patch.

| # | found | severed connection | silent for |
|---|---|---|---|
| 1 | 2026-09-09 | `log_regime` had no live caller — classifications stopped accruing | ~6 weeks |
| 2 | 2026-09-16 | `entry_confirmation` read `last_run.json`, whose only writer was quarantined | 98 days |
| 3 | 2026-09-16 | `log_signal` had no live caller while `run_outcome_check` graded its empty ledger nightly | 80 days |

**One event:** the 2026-07-29 `shadow/` quarantine.
**One omission:** the audit ran in one direction only — what `shadow/`
imports was checked; what imports `shadow/`'s functions, and what consumes
the artifacts `shadow/` writes, was not.
**One control:** `test_live_path_connections.py` now runs the audit in the
other direction on every suite run.

Why all three survived so long: each is a CONNECTION defect, and the test
apparatus is component-shaped. Every affected module had passing component
tests throughout. Components were tested; the wires between them were not.

---

## 2026-09-16 — STANDING RULE: A ZERO FROM AN UNVERIFIED PATH IS NOT DATA

**Every ledger-derived display must distinguish "no observations" from
"path not proven live."**

Three times now a can't-fire has rendered as a no-setup:

- `log_regime` (2026-09-09) — an unwired logger read as a quiet classifier
- THRUST_PULLBACK — a candidate that could not fire read as one that found
  no setup
- `trade_signal_log` (2026-09-16) — an empty ledger graded nightly read as
  a framework that issued no signals, while it had in fact issued at least
  one (GBP/AUD SHORT, 2026-09-10)

A zero that has never been shown capable of being non-zero is not evidence
of absence; it is absence of evidence. Any report, display, or DATA BASIS
line covering such a span must say which one it is. Applies immediately to
the 2026-06-28 → 2026-09-16 trade-signal window, which is UNOBSERVED.


---

## 2026-09-16 — Housekeeping (team-directed): schema divergence without detection

Recorded at team direction alongside the AGENTS.md standing-policy additions.
Committed directly to `main` as team-directed housekeeping — the precedent is
the 2026-09-11 housekeeping entries (`bd1aa24`, `44bb7e8`) and today's Step 2
inventory log (`dbe2b67`); no behavior changes, docs and log only.

**Finding.** Before the evidence-loop repair, `trade_signal_log.csv`'s header
was **two columns behind `_FIELDS`**: `shadow_direction` and
`shadow_conviction` were absent from the file while present in the code's
schema. This was discovered while executing Part 1's migration, not by any
check — nothing compared the ledger's header against the schema that writes
it.

**Why it belongs with the three orphans.** Same family: *divergence without
detection*. In each case a connection drifted and nothing noticed, because
nothing was looking at the joint.

- `log_regime` — a live-path WRITE lost its caller
- `last_run.json` — a live-path READ lost its writer
- `log_signal` — a live-path WRITE lost its caller, and its ledger was
  graded empty
- `trade_signal_log.csv` header — a live-path SCHEMA drifted from the code
  that writes it

The first three are now covered by `test_live_path_connections.py`. **The
fourth is not.** No test compares a ledger's on-disk header against the
`_FIELDS`/`FIELDNAMES` list of the module that writes it. Recorded as a gap,
not fixed here: the detection would be a small test per logger, and it is a
team decision whether to add it.

**Migration outcome.** Four columns added in total (`shadow_direction`,
`shadow_conviction`, `size_pct`, `entry_context`). The single 2026-06-28 row
was verified **preserved verbatim** in its original columns and blank in all
four new ones; row count unchanged at 1. The logger maintaining its own
schema, never an edit of recorded values — same guarantee as
`setup_check._migrate_journal_header` (reviewed 2026-09-09).

**Standing policy adopted, AGENTS.md rules 8 and 9 (2026-09-16):**
*A cadence requires a live writer* (precedents `trades.csv`,
`trade_log.csv`) and *a zero from an unverified path is not data*. Rule 9 was
directed to this log; it is ALSO promoted into AGENTS.md because a standing
rule that lives only in an append-only log is one future agents will not
read. Flagged for the team — revert the AGENTS.md half if the duplication is
unwanted.


---

## 2026-09-16 — CORRECTION: two ledger rows contaminated by the Gate 2 verification run

**Self-reported. Two append-only evidence rows carry synthetic values.
Neither ledger was edited — corrections are new dated entries, never
rewrites.**

### What happened

The Gate 2 REALITY run for the evidence-loop repair forced a directional
decision through the real `get_decision_brief` path. The trade-signal ledger
was correctly redirected to a temp file, **but `get_decision_brief` also
calls `log_session_snapshot` and `log_regime`, and those two were not
redirected.** Both wrote a row built from the forced regime.

### The affected rows — exact, do not use

`session_context_log.csv`
```
2026-09-16T09:08:08Z,GBP_AUD,21.9,34.8,0.93,VOLATILE,TRENDING_UP,DOWNTREND,True
                                                                          ^^^^
```
`filter_allowed=True` is **SYNTHETIC**. Reality was `False`. Every other
field is genuine live OANDA data.

`regime_classification_log.csv`
```
2026-09-16T09:08:08Z_GBP_AUD ... execution_mode=NORMAL ... stand_down=False
```
`execution_mode=NORMAL` and `stand_down=False` are **SYNTHETIC**. Reality
was `STAND_DOWN` / `True`. Every other field is genuine. The honest row for
the same market state is `2026-09-16T09:07:52Z_GBP_AUD`, logged 16 seconds
earlier, which carries `STAND_DOWN` / `True`.

**This row carries a PREDICTION and will be picked up by the grader.** It
must be excluded from any accuracy computation, base rate, or N. It is one
row; the correct handling is exclusion by `log_id`, never deletion.

### Observed consequence

The next real brief emitted a **false alert**:

```
##ALERT## GBP/AUD: conditions deteriorated — the framework has stood down
since the last run.
```

Nothing deteriorated. `session_memory` compared the honest 09:16:46Z row
against the synthetic 09:08:08Z one and correctly reported a filter flip
that never occurred. Run through the scheduled wrapper this would have
fired a real macOS notification.

### Root cause and the lesson

A verification run that exercises a real end-to-end path inherits **every**
side effect on that path, not just the one under test. Redirecting one
ledger is not isolation. `get_decision_brief` writes to three ledgers; only
one was accounted for.

**Rule for future Gate 2 runs that force inputs through a live path: enumerate
every writer on that path and redirect or neutralize all of them.** The
existing test helper `_neutralize_side_effects` in
`test_regime_log_wiring.py` and `test_trade_signal_wiring.py` already does
exactly this for the unit tests — it was not applied to the REALITY run,
which is the one that touches real files.

This is also a live instance of the rule adopted in the same session: the
false alert is a channel screaming without cause, and the cost of that is
an operator who stops reading it.

**Not fixed by editing.** Both rows stand in the record, flagged here.


---

## 2026-09-16 — Exclusion registry, header check, rules 8-10 (per docs/specs/exclusion_registry_spec.md)

Built on `feat/exclusion-registry`, spec committed first (`2bc5246`).
**Merge held for team review.**

### Why a prose correction was not enough

The CORRECTION entry earlier today (`0d5607a`) named two contaminated rows
and told a human to exclude them. **The grader is not a human.** It runs at
15:15, and `regime_classification_log.csv 2026-09-16T09:08:08Z_GBP_AUD`
carries a prediction with a synthetic `stand_down=False`. Left alone it
would have been graded and fed into DATA BASIS. Documentation is not a
control; this is the control.

### `exclusions.py` (NEW — protected list 19 → 20)

Append-only `excluded_rows.csv`:
`log_id, ledger, date, reason, authorizing_entry`. Seeded with both
contaminated rows, each citing the CORRECTION entry.

Four design rules, each recorded in the module because each is a place this
could have gone wrong:

1. **Ledgers are NEVER edited.** The module only reads. An exclusion is an
   act of interpretation recorded BESIDE the evidence.
2. **Filter at USE, never at READ.** `check_pending_outcomes` and
   `check_pending_trade_outcomes` read rows and write them back; filtering
   at read would have DELETED the excluded rows from append-only ledgers —
   the precise harm this module exists to prevent. Excluded rows are
   skipped for grading and passed through to the write-back untouched.
3. **Every exclusion names an authorizing entry** or `append_exclusion`
   raises. An unauthorized exclusion is indistinguishable from hiding an
   inconvenient result.
4. **Fail OPEN, loudly.** An unreadable registry excludes nothing and says
   so on stderr. A grader that silently excluded a whole ledger because a
   file went missing would be worse than one that excluded nothing.

Wired into every tally the ruling named: `check_pending_outcomes`,
`get_regime_accuracy`, `check_pending_trade_outcomes`,
`get_accuracy_by_regime`, `get_accuracy_by_signal_type`, session-delta
comparisons (`_get_today_rows`), and shadow `episode_count` /
`get_shadow_tally` — the last two sitting beside the existing
`is_invalid_spec` exclusion, which is the same idea that already existed
for a different reason.

### Header-vs-schema check — the fourth divergence member

`test_ledger_headers.py`, seven ledgers parameterized, asserting the
on-disk header equals the writing module's `FIELDNAMES`/`_FIELDS`. An
absent ledger is SKIPPED, not failed: a fresh checkout has no ledgers, and
a guard that fails on a clean clone is a guard someone disables. A
companion test asserts no `.csv` in the repo escapes coverage.

All seven currently match. The check is proved to fire against the real
historical case — a header missing `shadow_direction` / `shadow_conviction`.

### The guards caught something on their own

Adding `exclusions.py` to the live core made `test_every_live_artifact_is_inventoried`
fail immediately: `excluded_rows.csv` was a new live-path artifact with no
inventory entry. **That is the first time these guards have caught anything
other than the case they were built from.**

It was resolved under STANDING RULE 8 on the rule's first day: the
registry's writer is a human authorization event, so it can have no
cadence. Inventoried under `READ_SIDE_NO_CADENCE`, never alarmed on; its
integrity control is `test_exclusions.py`, not freshness.

### Gate 1

23 new tests (14 exclusion, 9 header). Suite 1297 → **1320 green**; shadow
**868** unchanged. Neither floor touched. `append_exclusion` is
allowlisted as an orphan with the reason that matters: **no grader calls
it, deliberately** — a grader able to write its own exclusions is the
entire failure mode this registry exists to prevent.

### Gate 2 — REALITY (live, 2026-09-16 ~09:30 UTC)

No neutralization applied and none needed: nothing is forced, every input
is genuine, and the grader's writes ARE the behavior under test. That
distinction is exactly what rule 10 draws.

Real `session_context_log.csv`, GBP_AUD, today:

```
rows physically in the ledger  : 7      <- synthetic row still present
synthetic row on disk          : True   <- never removed, never will be
rows reaching delta comparison : 6
synthetic row reaching a delta : False
surviving row w/ filter_allowed=True : None
```

Real `run_outcome_check.py` run, both pairs, completed clean with the
exclusion wiring live:

```
GBP_AUD: 0 regime outcomes filled
  TRENDING_DOWN : 100% (2/2) [7 rows -> 2 independent]
  VOLATILE      : 0%   (0/3) [8 rows -> 3 independent]
GBP_JPY: 0 regime outcomes filled
  RANGING  : 100% (1/1)     VOLATILE : 100% (2/2) [9 rows -> 2 independent]
```

The excluded row remains `outcome_filled=False` after a real grader pass —
in the ledger, out of every tally.

**Honest limit:** both 2026-09-16 rows are ~7 hours old against a 20-bar
D1 window, so neither was gradeable today regardless. This Gate 2 proves
the wiring runs clean on real data and that the session-delta exclusion
works on the real ledger; the decisive "would have been graded but was
not" case is covered by the controlled tests, and by the Gate 3 entry
below.

### Gate 3 — PENDING LIVE CONFIRMATION

- **The excluded row surviving a SCHEDULED 15:15 grader run ungraded**, and
  still ungraded once its 20-bar window has elapsed — that is the moment
  exclusion is the only thing preventing a grade.
- Carried forward: first real `trade_signal_log.csv` row from a genuine
  directional decision; the degraded-pass branch firing; first live
  GBP/JPY `m15_trigger = True`; **a genuine filter-flip alert on real
  market movement** (see the Gate-3 list — the mechanism is cleared, the
  trigger is not).

### AGENTS.md

Rule 10 added as directed. Rule 9 stays per ruling 1. `exclusions.py`
joins the PROTECTED list (19 → 20).


---

## 2026-09-29 — Full audit + owner-approved removals (branch `chore/audit-cleanup`)

Six review passes, recorded in full in `docs/audit_2026-09-29.md` (verdict,
scorecard, ranked defects, removal manifest, roadmap). The owner approved
the removals in session. Nothing in this entry changes a ledger.

**Removed (all recoverable from git history):**
- `shadow/`: 9,016 LOC and 868 tests. 0 comparisons ever logged.
- `legacy_validators/`: invalidated 2026-06-29.
- `studies/verify_shadow_path.py`
- `update_calendar.py`: superseded by `calendar_fetch.py`.
- About 300 LOC of unreferenced functions and constants in live modules, plus 18 unused imports.
- `intraday_context.py` cut from 544 to 113 lines. Only the Asian range was ever consumed. The removed fakeout logic encoded a premise this log had already refuted.
- `test_decision_invariants.py` keeps the 3 live-module invariants that previously sat under `shadow/`.

**Fixed:** `scripts/weekly_heartbeat.sh` never ran under launchd, because
`/bin/bash` 3.2 could not parse an apostrophe inside the heredoc at line 35.
Three Sunday heartbeats were lost (09-13, 09-20, 09-27). The 2026-09-09
Gate 2 had run under Homebrew bash 5. New guard: `test_shell_syntax.py`.
`uninstall.sh` now covers the heartbeat plist.

**Evidence-integrity findings, logged here and NOT yet fixed** (see the audit for the full list):
- `current_price` is the previous closed D1 bar. `_get_bars` drops the forming candle, so `_split_live_bar` never splits. `trade_signal_log.price_at_signal` and `regime_classification_log.price_at_log` therefore carry prices up to about 24h stale.
- The regime-accuracy tally is not evidence:
  - MR_WIN measures against the outcome window's own mean.
  - VOL_EXPANSION is near-impossible to pass.
  - The "independent" N is inflated about 2x.
- `shadow_signals.episode_count` treats 30 H4 bars as 120 clock hours (true: about 168h). It also counts ungraded rows.
- Candidates are evaluated only on the H4 bar that is latest at brief time, so about half of all bars are never checked.
- The integration tests (`-m integration`) write synthetic rows to the real ledgers. This is the likely origin of the unexplained 2026-07-29T04:23:31Z row.
- The trade_signal row 2026-06-28T21:39:15Z (exactly +150.0 pips) and the regime row 2026-06-28T23:19:58Z_GBP_AUD carry synthetic signatures. **They are candidates for the exclusion registry and are pending an owner ruling.**

### Gate 3 — PENDING LIVE CONFIRMATION

- First Sunday heartbeat actually delivered under launchd (after merge).

---

## 2026-09-29 — Exclusion registry fixes (per docs/specs/exclusion_registry_fixes_spec.md; Phase 0)

The code review found three defects in the registry merged earlier today.

**D1. A malformed or missing registry disabled every exclusion silently.**
- **Fix.** `_load()` now catches every read error. A bad row is skipped on its own and the valid rows still apply.
- **Alerting.** Every failure prints one line per process, prefixed `##ALERT## EXCLUSION REGISTRY`. The prefix is what the brief wrapper keeps from stderr, so the alert reaches the log.
- **Call sites.** One helper, `exclusions.excluder()`, replaces 7 copy-pasted `try/except → set()` guards that swallowed every error. The two `filter_rows` sites lose their `except: pass` blocks.

**D2. `grade_pending_shadow` and `latest_pending_signal` ignored the registry.** Both now skip excluded rows. The grader writes them back untouched.

**D3. Two tests passed with exclusion switched off.**
- The regime test now also pins `n_raw` and `correct`.
- The session test now freezes its clock.

### Gate 1
- The suite is green: 572 passed.
- **Against the old code:** all 9 new D1/D2 tests fail, each for its target reason.
- **With exclusion disabled on the new code:** both fixed D3 tests fail. They can now detect the failure they claim to guard.

### Gate 2 (REALITY)
Real OANDA runs of `run_outcome_check.py` and `decision_brief.py` from a temp working directory, on copies of the real ledgers. The project hashes were identical before and after (rule 10).

**Healthy registry:**
- Both runs exited 0.
- No registry alerts.
- `2026-09-16T09:08:08Z_GBP_AUD` is still `outcome_filled=False` after a real grader pass.
- **Honest limit:** that row is about 10 D1 bars old against a 20-bar window, so it was not yet gradeable regardless.

**Corrupted copy of the registry** (the review's short-row repro), actual output:
```
##ALERT## EXCLUSION REGISTRY: line 4 is malformed and was SKIPPED (other rows still apply): {'log_id': 'JUST_AN_ID', 'ledger': None, ...}
```
The valid exclusion still held: the row stayed ungraded.

### Gate 3 — PENDING LIVE CONFIRMATION
- A scheduled 15:15 grader run, after the row's 20-bar window has elapsed, leaves `2026-09-16T09:08:08Z_GBP_AUD` ungraded. This carries over from the 2026-09-16 entry.

---

## 2026-09-29 — Phase 1: the test suite cannot touch evidence or the network

**Measured before changing anything.** A probe plugin recorded every network lookup and every write outside a temp directory, per test.

**Default suite:**
- 0 real writes.
- 2 live authenticated OANDA calls, both from `test_regime_detection_p1.py`'s `mocked_regime` fixture. It mocked only D1; H4 and weekly went to the live API. So the 29 contract cases asserted on synthetic D1 data mixed with the live market.

**`-m integration` (run in a worktree):**
- `test_full_brief_produces_long_on_clean_uptrend` wrote synthetic rows to three ledgers: `trade_signal_log.csv` ×2, `session_context_log.csv` and `regime_classification_log.csv`.
- It is the likely origin of the unexplained 2026-07-29T04:23:31Z session row.

**Built:**
- **`conftest.py`: every test runs in its own tmp_path**, so relative ledger paths land there. The absolute-path writers (pre-trade journal, trades.csv, calendar) are redirected too.
- **A session-wide network block.** Only `integration` tests lift it. The first version blocked per test, which missed module-scoped fixtures, the exact case above. It was caught in testing.
- **A session guard.** It hashes every real evidence file and FAILS the run on any change. It is proven in a throwaway project: it fails a contaminating run and passes a clean one.
- **`mocked_regime` now mocks D1, H4 and weekly.** The contract cases now run the real tradeable path (TRENDING_UP/TRENDING_UP, CONTINUATION).
- **Weak tests fixed:**
  - The "logs nothing" wiring tests now assert `brief.error is None`, so a crash no longer passes them.
  - The header "would have caught it" test now calls the real check, and fails when that check is broken.
  - A cwd-dependent `open("scripts/...")` in `test_alert_flags.py` now uses an absolute path.
- **`scripts/reality_run.py`: the Gate-2 tool that rule 10 had referred to.** It runs from a temp cwd with ledger copies and `.env`, hashes the project before and after, and fails with exit 2 on any escape.

**Caught during its own Gate 2:**
- The first version of `reality_run.py` certified an ERROR PAGE as a successful run. Trailing `--project/--code` options were swallowed as script arguments, so it ran the wrong project with no credentials. The brief exits 0 on an error page.
- **Fixed:**
  - Options are now parsed intermixed.
  - A missing `.env` is flagged.
  - A failure marker in the output (error page, traceback, grader early exit) returns exit 3: "NOT a valid REALITY GATE".
  - Ten days of real brief and outcome logs contain none of the markers, so there are no false positives.

### Gate 1
585 passed in the worktree; the 6 ledger-header cases skip there because the ledgers are absent.

### Gate 2 (REALITY)
**`-m integration`:** runs against live OANDA; 2 passed. No ledger files were created in the project (before: 3 synthetic ledgers).

**`reality_run.py brief --project <live> --code <branch>`:**
```
exit code        : 0
ledger copy changed: regime_classification_log.csv (115 -> 117 lines)
ledger copy changed: session_context_log.csv (161 -> 163 lines)
ledger copy changed: shadow_signal_log.csv (20 -> 21 lines)
project files    : UNCHANGED (verified by hash)
```

**`reality_run.py grader`:** exit 0. Shadow outcomes filled in the copy; project UNCHANGED.

---

## 2026-09-29 — CORRECTION: Phase 1 was reported finished before it was fully validated. Validation completed.

**What was overclaimed.** The Phase 1 entry above and the merge report
presented Phase 1 as done. The owner asked whether every claim was
validated. Six were not:
1. "The default suite makes no network calls." The block itself was tested, but the whole suite was never re-measured after the change.
2. The new `brief.error is None` assertions were never shown to fail on a crash.
3. The no-op-migration assertion was never shown to be able to fail.
4. The integration run was checked only with `ls *.csv`. That would miss writes to `logs/`, subfolders, and absolute paths.
5. The session guard watched only root `.csv`/`.json` and `logs/health_state.json`.
6. The audit's orphaned-process finding (T7) was never checked.

**How each was validated.** All evidence was observed in session.

**1. The default suite makes no network calls.**
- **Instrument:** an interpreter-level probe (`sys.addaudithook`), which no test can monkeypatch.
- **Positive control:** a planted test that writes to its project and resolves `api-fxtrade.oanda.com` was caught: 1 lookup, 1 write.
- **On the live checkout:** 591 passed, **0 non-local lookups, 0 writes** other than `/dev/null`.

**2 and 3. Mutation tests** (in a disposable worktree).
- **Mutant A:** the brief raises right after fetching the regime.
  - The 3 new "logs nothing" tests: **3 failed**.
  - The same 3 tests from before Phase 1: **3 passed**. They could never detect a crash.
- **Mutant B:** the no-op migration creates the missing file.
  - The new test: **1 failed**. The old test: **1 passed**.

**4. `-m integration` against live OANDA**, in a copy of main seeded with copies of the real ledgers and `health_state.json`.
- The probe saw 13 lookups (allowed for these tests) and **0 writes**.
- A before/after hash of every file: **153 non-cache files identical**. Only Python bytecode caches differed.

**5. The session guard.**
- **Weakness shown first:** a planted test appending to `logs/` and another creating a root file both passed under the old guard.
- **Fix:** the guard now hashes every project file, excluding caches, `venv/` and `.git`.
- **After:** the same run exits 1 and names both files.
- **Permanent tests** now cover both cases.
- **Regression check:** the full suite under the stricter guard has no alert, so no existing test writes anywhere in the project.

**6. Orphaned processes: confirmed, and fixed.**
- `test_hung_binary_watchdog_fires_fallback`'s stub ran `sleep 300` as a child. The watchdog killed the stub and left the sleep orphaned.
- **Controlled PID-set diff:** the old test gives exactly **1 new orphan per run** (PID 10019). The fixed stub (`exec sleep 300`) gives **0**.
- The fixed test also now asserts that the hung process is dead.
- The orphans leaked by this session's earlier runs (8775, 9675, 10019) were killed.

**Every Phase 1 safeguard was shown to fail when removed (mutants C–G).** Each mutation was confirmed to have changed the file, and each broke its test:
- C: remove the H4 mock
- D: remove the network block
- E: remove the tmp_path chdir
- F: remove the absolute-writer redirects
- G: disable the session guard's failure

**Standing rule adopted (owner-directed):** no claim without observed evidence. See AGENTS.md rule 11 and the `evidence-validation` skill.

---

## 2026-09-29 — Phase 2: failures are visible (per docs/specs/visible_failures_spec.md)

**Method (AGENTS.md rule 11).** Every defect was reproduced on main (58433b4) before any change, using the real wrappers in a throwaway project and the real `get_regime` with simulated OANDA failures. The same scripts were re-run after the change.

| # | Defect | BEFORE (main) | AFTER (branch) |
|---|---|---|---|
| D1 | Grader traceback | recorded as SUCCESS | `outcomes` failure: "grader crashed (exit 1): ZeroDivisionError: boom" |
| D2 | Brief non-ALERT stderr | absent from the day log | present |
| D3 | Brief crash | traceback lost; "no output" | traceback logged; "brief crashed (exit 1): ZeroDivisionError: boom" |
| D4 | Shared health counter | UNHEALTHY, then a false "RECOVERED after 2 failed runs" from the grader | "BRIEF UNHEALTHY" only |
| D5 | Stale human `storylines.md` | fails every healthy brief | a `DUE:` line; the run stays healthy |
| D6 | Grader rewrite of a ledger whose newest row is 2000h old | `fresh ... 0h old` | `STALE ... 2000h ago (newest row)` |
| D7 | 401 / 503 / timeout | "Not enough data to calculate regime indicators", 1 attempt each | credentials rejected (1 attempt); server error (3); timed out (3) |

**`/code-review`.** It found 10 findings. Each was verified before fixing: 9 confirmed, 1 not reproduced (F1, fixed defensively). See the spec addendum.

### Gate 1
- **Full suite:** 635 passed in the worktree, with 0 network lookups (audit-hook probe).
- **Controlled comparison:** the new tests run against main's code fail 38 times with assertion failures. The 8 preserved-behavior pins pass on both.
- **Mutation tests:** 16 mutants (M1–M9 build, M10–M16 review fixes), each applied, each failing its guarding test, each reverted.

### Correction discovered during Gate 1
- A later full run failed 3/3 on F6, with or without the probe.
- **Cause:** mutant M14 was the same length as the original line (54 chars), and it was reverted within the same second. Python kept the mutant's cached `.pyc`, although the source diff was clean.
- **After clearing `__pycache__`:** 635/635, twice. Every Gate 2 run that imports worktree code was redone from a clean cache, with identical results.
- **Fix to the method:** the `evidence-validation` skill now requires clearing caches and re-running the test after each revert.

### Gate 2 (REALITY)
- **Real OANDA with a deliberately invalid key** (scratch project, via `reality_run.py`): the brief says "credentials rejected (HTTP 401): key revoked, expired, or for the wrong environment (D GBP_AUD, 1 attempt)". `reality_run` returns exit 3, so an error page never certifies.
- **`reality_run brief` / `grader` with the branch code against the live ledgers:** exit 0, no failure markers, project UNCHANGED by hash.
- **Real wrappers end to end,** in a full copy of the project (the live ledgers, the legacy `health_state.json`, `.env`, the venv, and `storylines.md` at its real 459h age). Notifications went to a stub. Every live file was hashed before and after and was **UNCHANGED**.
  - The legacy flat health state migrated into `jobs.brief`.
  - A healthy run then sent "RECOVERED: brief healthy again after 1 failed runs", a true recovery since the failures were storylines.
  - `DUE: storylines.md — last written 459h ago` was logged, with 0 UNHEALTHY notifications.
  - The stderr section was logged.
  - The grader's SHADOW tally rendered under the venv, the one part the harness could not assert.
  - The branch guard alerted, correctly, because the copy is not a git checkout.

### Gate 3 — PENDING LIVE CONFIRMATION
- The first scheduled brief and grader runs after merge write per-job health.
- The first real scheduled brief after merge logs `DUE: storylines.md` and records success.
- The next Sunday heartbeat reports both jobs, and shows DUE without NEEDS ATTENTION.

---

## 2026-09-30 — Phase 3: safe ledger writes (per docs/specs/safe_ledger_writes_spec.md)

**Method (AGENTS.md rule 11).** Every defect was reproduced on main (67a8aef) with real processes and the real logger functions, on copies of the live ledgers. The instrument controls were:
- every second-process appender first shown to append on its own;
- every run recorded that the second process ran and exited 0;
- the trigger placed at the end of the grader's READ.

The same script was re-run on the branch.

| # | Defect | BEFORE (main) | AFTER (branch) |
|---|---|---|---|
| B1a–c | A grader's read-modify-write destroys a concurrently appended row | shadow 19→19, regime 114→114, trade 4→4: row lost in all three | 19→20, 114→115, 4→5: row kept in all three |
| B2 | SIGKILL mid-rewrite of a real regime-ledger copy | 114 rows → **0** | 114 → 114 |
| B3 | Session log deletes rows older than 30 days | a 59-day-old row deleted | kept |
| B4 | No backups | none | hash-verified folder per nightly run |
| B5 | 40 concurrent health updates | 16, 32, 33, 34, 37 of 40 counted | 40 of 40 |

**Supersedes the 2026-09-09 entry** ("session_context_log.csv … a designed **rolling 30-day window**, not an append-only archive"). As of this merge the ledger is append-only, which is what AGENTS.md already said. The pruning it described has already cost evidence: the 2026-07-29 synthetic row, which Phase 1 traced to the integration tests, was deleted by it. Owner to confirm at merge review (spec addendum).

### Gate 1
- **Full suite:** 666 passed (worktree, clean cache, `PYTHONDONTWRITEBYTECODE=1`), with 0 network lookups (audit-hook probe).
- **Controlled comparison:** the 12 new-behavior tests fail on main's code. The three race tests fail on the "the other process's row survived" assertion.
- **Mutation tests:** 25 mutants, each applied, each failing its test, each reverted with caches cleared and the test re-run to PASS:
  - MA–MK: the build;
  - MR1–MR10: the review fixes;
  - the restructured health lock, caught 3 of 3.

### Correction during Gate 1
Mutants MD, ME and MF survived the first race tests, because the trigger sat inside the write's own lock. The trigger was moved, the tests and the B1 measurement were re-run before and after, and all three mutants now fail. The spec addendum lists every instrument correction.

### Gate 2 (REALITY)
- **`reality_run brief` / `grader`** with the branch code against the live ledgers: exit 0, no failure markers, project UNCHANGED by hash.
- **Real wrappers on a full project copy** (the live ledgers, `.env`, the venv), with the brief and the grader **launched simultaneously**:
  - 0 pre-existing rows lost in any ledger;
  - shadow: the grader's fill (9→10 graded) and the brief's new row (19→20) both kept;
  - backup `2026-09-30T070502Z`: 9 files, all sha256 verified, 0 mismatches on an independent re-hash;
  - no leftover temp files; health `brief: 0`, `outcomes: 0`;
  - the live project was UNCHANGED (every file hashed).
  - **Honest limit:** the exact interleaving of the two wrappers was not instrumented. The deterministic race proof is B1.

### Gate 3 — PENDING LIVE CONFIRMATION
- The first scheduled 15:15 run after merge writes `backups/<stamp>/` with a verified manifest, then grades.
- `session_context_log.csv` still holds its 2026-09-09 rows after 2026-10-09, which is when they would first have been pruned.
- **Off-machine backup:** backups on the same disk do not survive disk loss. This is the owner's decision.

---

## 2026-09-30 — Phase 3 follow-ups (owner-directed): exact wrapper overlap; skill auto-loading

### 1. Exact overlap of the concurrent real-wrapper run
This was NOT CHECKED in the Phase 3 report. It is now measured with `scripts/trace/`. The tracer's positive control recorded the expected lock, append, read, replace and unlock sequence. The runs used the real wrappers and the real venv on full copies of the project, with the live project UNCHANGED by hash both times.

**Natural run** (both wrappers launched at the same instant):
- The brief and the grader were alive together for **1,322 ms**.
- Inside that window they alternated on the SAME ledgers:
  - regime: grader 790 ms, brief 1,123, grader 1,151, brief 1,873;
  - shadow: grader 1,019, brief append 1,322, grader rewrite 1,392. That rewrite read the brief's row under the lock.
- **0 overlapping lock holds** by different processes. There was no contention: critical sections last about 0.2–2 ms and never collided.

**Forced collision** (the grader held inside its regime-ledger lock for 4 s):
- The grader held the lock 725 → 4,739 ms.
- The brief found it busy at 1,100 ms and retried 151 times at about 20 ms.
- The brief acquired it **6.7 ms after release** (4,746 ms) and appended.
- The regime ledger went 114 → 116, with both brief rows present; 0 overlapping holds.
- **Honest limit:** in this run the grader had nothing due, so it read under the lock without rewriting. The rewrite-plus-waiting-append case is the deterministic B1 proof.

### 2. Why `evidence-validation` was "Unknown skill" here, and proof it loads on its own
**Cause (process tree plus timestamps):**
- This session runs in PID 64042 (the Cursor extension, Claude Code **v2.1.284**), started **2026-09-29 21:00:47**.
- `~/.claude/skills` itself was created **21:00:48**, one second later, by the claude.ai skill sync.
- Per the Claude Code docs (skills.md, "Edit a skill during a session"), a top-level skills directory that did not exist at session start is not watched until `/reload-skills`.
- The skills themselves were never the problem.

**Evidence the skills are correct:**
- `claude plugin validate ~/.claude/skills` reports "✔ Validation passed".
- Names match their directories; the descriptions are 732 and 869 chars (the listing cap is 1,536).
- A fresh headless session (v2.1.285) lists both skills among 36 at startup.

**Auto-trigger eval:** `foundation/tools/skill_trigger_eval.py` runs fresh headless sessions from a scratch directory with every modifying tool disallowed.
- 6 should-trigger prompts: correct skill invoked **18/18**.
- 3 near-miss prompts: no skill invoked **9/9**.
- **27/27 total.**

**Fix going forward:** any NEW session loads both skills. In a session that predates the skills directory, run `/reload-skills`.

### Gate 3 — PENDING
- `/reload-skills` in the pre-existing session makes the Skill tool resolve `evidence-validation` there. It needs the owner to type the command; the result is to be recorded.

---

## 2026-09-30 — Phase 4: data at the source (per docs/specs/data_at_source_spec.md). Merge HELD

**Method (AGENTS.md rule 11).** Each defect was reproduced on main (ce4cab6) with controls, then re-measured with the same script.

| # | Defect | BEFORE (main) | AFTER (branch) |
|---|---|---|---|
| P1 | The brief's price is the previous D1 close | GBP/AUD 1.8938 vs live 1.90163: **78.3 pips**. GBP/JPY: 6.5 pips | 0.2 and 0.0 pips; `price_basis=live` |
| P2 | Market hours hard-coded at 21:00 UTC | 4 wrong cases after DST / on holidays; the summer controls correct | all 7 correct |
| P3 | A weekly outage silently skips the 20-week gate | allowed ("All filter conditions passed"); the control was blocked | stands down ("Weekly trend data unavailable…"); the control is unchanged |

**`/code-review`.** 10 findings, all reproduced, then fixed and re-measured. See the spec addendum, including the design correction: classification and the regime ledger use the closed D1 bar; only the display and the trade entry are live.

### Gate 1
- **Full suite:** 703 passed (worktree, clean cache), with 0 network lookups (audit-hook probe).
- **Controlled comparison:** 17 of 26 new tests fail on main's code. With the mock target made tolerant they fail on behavior: P1 price 1.851 vs live, P3 RANGING vs UNAVAILABLE, and UNAVAILABLE printed raw. The 9 that pass on main are the cases main already got right.
- **Mutation tests:** 18 mutants (M1–M9, MV1–MV9), each applied, failing, reverted, caches cleared, and re-run to PASS.
- **Correction:** the V-fix commit message stated "703 passed" before the full suite was run; it was verified afterwards (703 passed).

### Gate 2 (REALITY)
- **`reality_run brief` / `grader`** with the branch code against the live ledgers: exit 0, project UNCHANGED.
  - The brief shows live prices: 1.9021, where it showed the stale 1.8938.
  - The regime copy migrated additively. The 114 pre-existing rows show **0 field differences** against the live ledger, all with a blank basis. The new rows carry `price_at_log` = the D1 close and `price_basis=d1_close`.
- **Forced live-price failure:** the brief shows "Price is the previous daily close — the live price could not be fetched".
- **The real wrappers end to end** (brief and grader launched together on a project copy):
  - live prices in the day log;
  - `DUE:` logged;
  - a verified backup before grading;
  - health `brief: 0`, `outcomes: 0`;
  - the live project UNCHANGED.

### Merge preconditions (owner)
1. The Phase 2/3 Gate-3 checks of the 02:30 brief and the 15:15 grader pass.
2. Owner approval of this branch.
3. Owner approval of the controlled header migration of the two LIVE ledgers at merge: backup first, then the loggers' own `migrate_header`, then a field-by-field comparison against the backup, which must show 0 differences.

### Gate 3 — PENDING
- The first scheduled briefs after merge show live prices within 3 pips of the mid.
- The first real Sunday-open and Friday-close boundaries after 2026-11-01 are handled correctly.

---

## 2026-09-30 — Phase 5: decision logic (per docs/specs/decision_logic_spec.md). Merge HELD

**Method (AGENTS.md rule 11).** Each defect was reproduced on main (6471072)
with controls (`scratchpad/p5/measure.py`), then re-measured with the same
script.

| # | Defect | BEFORE (main) | AFTER (branch) |
|---|---|---|---|
| D1 | GBP/JPY H4 exhaustion traded as a pullback | LONG, conviction 70, **grade A**, size 0.75 | NO TRADE: "exhaustion move — fade, don't follow" |
| D2 | ADX ≥ 32 trend from slope alone | ADX 33 + TRANSITIONAL → TRENDING_DOWN | VOLATILE / UNCONFIRMED_TREND. Control: ADX 33 + DOWNTREND is still a trend |
| D3 | The conflict hard block could never fire | Stopped only by the fallthrough | The named block "Opposite trend conflict…" |
| D4 | Filter allows, then official vetoes | 3 RANGING cells | 0 |
| D5a | Uncovered calendar reads all-clear | `active=True, note=''` | inactive, stale note |
| D5b | Gate drops at the release | 5 min after: not gating | gating until +30 min. Control: 60 min before, gating |
| D6 | Missing levels loosen the trigger | `entry_ready=True` | `entry_ready=False` (H1 confirmed: the trigger sits at the edge) |
| D7 | Grade C shown as a trade (the real 2026-09-25 row) | SHORT, 30, C, size 0.75 | NO TRADE |

**Owner decisions (2026-09-30):** floor changes authorized; exhaustion →
stand aside; ADX ≥ 32 needs structure; grade C = no trade.

### Gate 1
- **Full suite:** 751 passed (worktree, clean cache). Audit-hook probe: 0
  network lookups; the only write is `/dev/null`, which the probe's own
  positive control also shows. The control catches a planted project write
  and a DNS lookup.
- **Invariant sweep:** 36,864 cells (regime × regime × structure × weekly ×
  ATR × pair × exhaustion …) run through main's and the branch's code.
  - Filter/official disagreements: main **6,912** → branch **0**.
  - Grade-C trades: main **5,472** → branch **0**.
  - 8,016 cells changed, **all** trade → NO TRADE, each explained by the
    exhaustion or grade-C rule. **0** cells go blocked → trade.
- **History replay** (the same cached OANDA candles through both codes; live
  price and news gate pinned; 825 days with H4 data × 2 pairs):

  | Pair | Trades (main → branch) | Grade-C trades (main → branch) | Filter/official disagreements (main → branch) |
  |---|---|---|---|
  | GBP/AUD | 144 → 74 | 60 → 0 | 171 → 0 |
  | GBP/JPY | 95 → 55 | 24 → 0 | 154 → 0 |

  - Every changed day was attributed to D1/D2/D3/D4/D7, or to a reason text
    now made accurate (the filter gets the real ADX).
  - **One newly-permitted trade:** GBP/JPY 2026-01-26. D2 on the H4 (ADX
    32.4, TRANSITIONAL): LONG B. Disclosed in the spec addendum; N=1
    outcome +262 at 5 bars, −48 at 20.
- **New tests:** 43, of which 37 fail on main's code. 23 of those fail on
  behavior; 14 fail because the new API is absent on main. The 6 that pass
  are the controls and the case main already got right.
- **Mutations:** 24 mutants (M01–M17, V1–V6b), each applied, failing, reverted
  (hash-verified), caches cleared. **0 survivors**; the full suite passes
  after all reverts.
- **One unexplained suite failure (OPEN).** One full run just before the
  docs commit reported "1 failed, 750 passed". Its output was not captured
  (only the tail line), so the failing test is **NOT KNOWN**.
  - It did not reproduce in the next **31 consecutive full runs**: 6 plus 20
    serial, and 5 with all 8 cores saturated by busy loops. Every failure
    output was captured.
  - The timing-sensitive tests I read synchronize correctly: the lock tests
    wait on a "held" handshake, and the concurrency tests pass in either
    order.
  - **Standing instruction:** every future suite run keeps full `-rf` output,
    so a recurrence is identified, not re-guessed.
- **`/code-review`:** 10 findings, all reproduced on the branch before
  fixing, then re-measured fixed (spec addendum V1–V10).
  - **Instrument correction:** my first AFTER run of the repro script omitted
    the new `filter_block` key, which `get_regime` supplies. So V3/V5 read
    unfixed.
  - The live path was then verified: `get_regime` returns the filter's block
    and reason (test), and a full `get_decision_brief` REASON shows the
    grade-C reason (test).
  - The corrected script shows all five fixed.

### Gate 2 (REALITY)
- **`reality_run brief` with the branch code against the live ledgers:** exit 0,
  project UNCHANGED (hash).
  - The regime and session copies migrated additively: 116 + 162 old rows,
    **0 field differences** (3,132 + 1,458 fields). The trade copy had 0
    differences with no new row (no trade today, and `log_signal` runs only
    on a trade).
  - The checker's positive control found 1 of 1 planted changes. **Its first
    run reported 0:** the control wrote through an unclosed file. It was
    fixed and re-run.
- **Controlled comparison, same live data (2026-09-30 ~09:47 UTC):** both
  pairs STAND ASIDE on both codes.
  - **GBP/JPY on main** logged `filter_allowed=True` while its brief said
    "Reduced Momentum … no signal met conviction threshold". That is D4
    contaminating the live session ledger today.
  - **The branch** logs False, with "exhaustion move" and `logic_version`.
- **`reality_run grader`:** exit 0, project UNCHANGED. The shadow-ledger copy
  is byte-identical to main's grader run on the same data.
- **The real wrappers on a project copy with the branch code** (a bare
  environment, `/bin/bash`):
  - brief wrapper: exit 0, both ledgers migrated, and the new rows carry
    `p5-2026-09-30`;
  - grader wrapper: exit 0, "backup … all sha256 verified" (independently
    9/9) before grading;
  - LIVE BRANCH alert fired as designed (the copy has no .git).
- **The branch news gate against the real calendar.csv:** active, not gating,
  covered through 2026-10-04 03:59 UTC. Note: `reality_run --code <worktree>`
  reads the worktree's (absent) calendar, so its brief showed "calendar
  missing". That is an instrument limit, not a defect.

### Merge preconditions — see the spec ("Merge preconditions")
The Gate-3 checks for Phases 2/3/4; owner approval; the controlled ledger
migration immediately after the merge, outside the job windows.

### Gate 3 — PENDING
- The first scheduled briefs under `p5-2026-09-30`: record the decisions,
  and compare them with main's code on the same inputs.
- The first real post-release window: the gate holds 30 min after the event.
- The first Monday with last week's calendar, if the Sunday fetch fails: the
  note, not an all-clear.

### 2026-09-30 — Phase 5, second `/code-review` (of 83eb51b). Owner approved Phase 5 at 03:2x PDT
- **10 findings**, 9 reproduced as stated. R2b (the 20-week alignment reason
  has raw labels) predates Phase 5 and was noted for Phase 6. Fixes: see
  spec Addendum 2.
- **Same instrument, before/after.** `repro_review2.py` shows R1/R2a/R3/R5
  fixed.
  - The first AFTER run still showed R6 unfixed. The instrument passed
    ADX/structure without running the classifier, so the new cause subtype
    was absent.
  - With the classifier's output passed in, R6 on 83eb51b gives the
    "stair-step" wording, and on the fix gives "direction turns to agree".
- **Suite:** 757 passed (branch, clean cache, `-rf`).
- **Mutations:** **33** mutants (M01–M17, V1–V6b, R1–R10), all killed with a
  real test failure (exit 1 ×33). Every revert was hash-verified, and the
  full suite passes after all reverts.
- **History replay** (the same cached candles, 825 days × 2 pairs), fixed code
  vs the first branch build: **0 decision/regime fields changed**. 16
  GBP/AUD reason texts changed; all are review-1 V2 naming unconfirmed
  structure at ADX ≥ 32.

### 2026-09-30 — Phase 5 merged (010ed03, 08:44 PDT) and live ledgers migrated (08:49 PDT)
- The owner approved the merge and, after an auto-mode permission block, explicitly allowed the migration.
- **Backup:** `backups/2026-09-30T154429Z` (backup_ledgers.py: "all sha256 verified").
  - Independently re-verified 9/9.
  - The live ledgers were byte-identical to it before the migration.
- **Migration:** each logger's own `migrate_header` (all three rewrote).
- **Field-by-field against the backup:**

  | Ledger | Rows | Diffs |
  |---|---|---|
  | regime | 118 → 118 | **0 of 3,186 fields** |
  | trade | 4 → 4 | **0 of 128** |
  | session | 164 → 164 | **0 of 1,476** |

  - Old columns are unchanged and in order, and `logic_version` is appended
    blank on every old row.
  - The checker found 1 of 1 planted changes per ledger.
- **Live-checkout suite:** **763 passed, 0 skipped.** The 6 ledger-header checks that skip in a worktree ran and passed.
- **Gate 3 — PENDING:** the 15:15 PDT grader and the 18:00 brief are the first scheduled runs on p5 code; new rows must carry `p5-2026-09-30`.

---

## 2026-09-30 — Issue 4: the session "Regime changed" message names the timeframe (per docs/specs/regime_change_message_spec.md). Merge HELD

**Defect (live, 02:30 PDT GBP/AUD):** `Regime changed (no clear direction → no clear direction)`. The session rows were D1 VOLATILE→VOLATILE and H4 TRENDING_UP→VOLATILE.

**Before/after, same instrument** (`scratchpad/i4/measure.py`, today's two real rows replayed):

| | Main | Branch |
|---|---|---|
| H4-only change (real rows) | `(no clear direction → no clear direction)` | `Regime changed — 4-hour chart: trending up → no clear direction` |
| Both changed | the H4 change is dropped | both named, daily first |

### Gate 1
- **Tests:** 11 new tests. 9 fail on main's code; the 2 that pass are the controls (no change; a flip without a change).
- **Mutations:** 7/7 killed, with the full suite passing after the reverts.
- **Full suite:** 768 passed (worktree).
- **Audit probe:** 0 network lookups; the only write is /dev/null (the same as its positive control).
- **`/code-review`:** 8 findings, all reproduced, all fixed (spec addendum). This includes a latent UTC-midnight race in the Phase 5 session test, now frozen.

### Gate 2
- **`reality_run brief`** with the branch against the live ledgers: exit 0, project UNCHANGED (hash).
- **Rendering not exercised live:** no regime change happened in the 35 min since the last run ("Conditions unchanged").
- **Phase 5's same-rules guard observed live on this run:**
  - GBP/JPY's pre-migration row has `filter_allowed=True` with a blank version; the new p5 row has `False`.
  - The session line correctly says "Conditions unchanged", with no false "DETERIORATED".

### Gate 3 — PENDING
The first live brief after a single-timeframe regime change.

---

## 2026-09-30 — R2b (Phase 5 review 2): the 20-week alignment gate's dead exceptions removed; the reason states the real rule (per docs/specs/weekly_alignment_wording_spec.md + addendum)

- **Owner direction:** "fix the 10 more problems from the 2nd code review". Nine were already fixed in Phase 5; R2b was the one left open.
- **Correction during the work:**
  - My first build reworded the exception ("allowed only when … bouncing against the main trend").
  - `/code-review` showed that sentence promised something that can never happen: the exceptions are unreachable.
- **Unreachability proven with the real classifier:** over all 9 lt × st combinations (each one realized), COUNTER_TREND_BOUNCE never pairs with lt=UPTREND, and PULLBACK_IN_UPTREND never pairs with lt=DOWNTREND. The exceptions have been dead since d661d81 (2026-06-28).
- **What the gate actually is:** never trade against the 20-week trend. The reason now says exactly that, coded `weekly_alignment`.

### Gate 1
- **No decision changes:**
  - Grid of 6,912 reachable cells, main vs branch: **0 differences**, with the identical 864 gate-blocked cells.
  - History replay, 825 days × 2 pairs: **0 decision differences**.
  - The one behavior change is on impossible hand-built dicts (the exception pairing), which are now blocked. That is stricter, and it is pinned.
- **Tests:** 13 new. The rendered REASON for every reachable blocked combination has no raw labels. The gate stays silent with the trend or on a RANGING 20-week.
- **Mutations:** 6/6 killed, including restoring either dead exception. The full suite passes after the reverts.
- **`_render_reason`:** now the single REASON pipeline. The banned-token floor test and three others use it (stronger: they now check what the trader sees).
- **`/code-review`:** two rounds, with 8 findings in round 2, all addressed.
- **Full suite:** 781 passed (worktree).

### Gate 2
- `reality_run brief`: exit 0, project UNCHANGED (hash).

### Open owner decision
Whether a counter-trend exception is wanted at all. It has never been active.

---

## 2026-10-15 — Foundation skill repair: the honest-number instruments were themselves unverified (foundation/ free zone)

**Defect class.** The instruments that produce the framework's honest numbers (`foundation/tools/power_check.py`, `episodes.py`) had no tests, and both failed silently rather than loudly. That is I5 ("return an error, never default silently") and M19 (a check that cannot fail proves nothing), turned on the instruments themselves.

**BEFORE (main 7d46138, each reproduced on unmodified code before any fix):**
- `power_check --rs`, "avg R without best episode":
  - six −1R gave **+0.000** (every episode equal to the max was removed, then 0.0 was substituted);
  - N=1 gave **+0.000**;
  - `[-1,-1,-1,2.5,2.5]` gave **−1.000**, against a true **−0.125**.
- The percentile-bootstrap lower bound printed from N=5.
- `episodes.to_bar_index`:
  - `…09:00:00Z` mapped to bar 2, but `…09:00:00+00:00` (the same instant) mapped to bar 1;
  - fires in 2020 and 2030 were clamped onto bars 0 and 5 with no error;
  - fires that existed nowhere on the bar index still produced a clean episode count.
- `--graded-col` counted three "pending" rows as three episodes.

**AFTER:**
- Exactly one episode is removed (`sorted(rs)[:-1]`), and the line is omitted below N=2.
- The bootstrap is kept as a percentile bootstrap (the honest minimum), gated at N≥20 (M3) and labelled as under-covering on skewed R.
- Timestamps are parsed to UTC instants. A fire outside the bar index, or an unparseable or timezone-less stamp, raises an error naming the value.
- Ungraded sentinels are dropped, and the drop count is printed.
- New `--cells K`: a Sidak correction. Six cells at 0.05 each give a **26%** family-wise false-pass rate. A 0.15R edge at SD 1.2R needs **667** episodes, not 396.

**Skill system:**
- `test_skill_build.py` runs the real `build_skill.sh` and asserts that what ships equals what SKILL.md documents, in both directions.
- It was red on main: `skill_trigger_eval.py` shipped undocumented. Owner decision: stop shipping it.
- SKILL.md gained two lines: the risk limits are **unenforced** (no live caller, AUDIT §4); the code's FLAG_N=30 is an attention trigger, not a validity verdict (M10).
- `candidates.md` has an as-of banner.
- No evidence count, N, R value or status was changed.

### Gate 1
- **New tests:** `test_foundation_tools.py` (25) and `test_skill_build.py` (3).
- **Shown able to fail:**
  - 15/20 of the Phase 1 tests fail on the main tools;
  - 4/5 of the Phase 3 tests fail on the Phase 1 tool;
  - the build test is red on the main tree, and red on a planted `zz_unlisted.md`, a renamed reference and a planted tool.
- **Mutants:** 17/17 killed (`PYTHONDONTWRITEBYTECODE=1`; caches cleared and hashes checked after each revert). These cover the tests that pin already-correct arithmetic.
- **Controlled comparison:** the 2-decimal anchors alone let an `n−1` drift in `power_at_n` and `false_pass_rate` survive (both still round to 0.25 and 0.17). The added 4-decimal pins kill it.
- **Full suite (worktree):** 809 passed, 6 skipped (the ledger-header tests skip because the worktree has no ledgers). The live project hash was unchanged across the run.

### Gate 2
- `build_skill.sh` was run into `~/.claude/skills`. In the installed tree, exactly 4 files changed by sha256: `trading-foundation/SKILL.md`, `references/candidates.md`, `scripts/power_check.py` and `scripts/episodes.py`.
- evidence-validation is byte-identical, and `skill_trigger_eval.py` is absent.
- The installed tools, run on the original reproductions, give −1.000, an omitted line, −0.125, and exit 2 naming the 2020 stamp.

### Phase 4 — trigger rate on protected-path prompts (measured; no action taken)
`skill_trigger_eval.py` was run with 3 new prompts × 3 runs: Cursor-bundled CLI v2.1.300, fresh headless sessions, scratch cwd, 2026-10-15 08:52–08:56Z.

| Prompt | trading-foundation invoked |
|---|---|
| Thrust filter in entry_confirmation.py | 3/3 |
| Grading-loop refactor in shadow_signals.py | 3/3 |
| "The regime logger is missing a column" | **0/3** |
| **Protected-path total** | **6/9** |
| Controls: original should-trigger prompts | 18/18 |
| Controls: nulls | 9/9 silent |

- Both skills were listed at startup in 36/36 runs.
- The standing claim "nothing triggers on a protected-module edit" is therefore **not true as stated**: prompts carrying trading or grading vocabulary trigger; a plain schema edit does not.
- **Limits:** the sessions ran outside the repo (no AGENTS.md loaded), with N=3 per prompt.
- **The owner decides** between a new skill and a description edit.

## 2026-10-17 — The decision channel was never graded: Phase 0 market-status gate; measurement pre-registered; inventory stops below N=10

**Finding.** The official DECISION channel (LONG / SHORT / STAND ASIDE) is the one the owner reads and acts on. It has had **no grader for the framework's entire life**:
- shadow candidates have a grader;
- regime classifications have one (audit-invalidated, I18);
- `trade_signal_log.csv`, meant to hold this channel, sat empty for 80 days (I23).

Nothing below grades decision accuracy; that effect is too small for the N available.

### Phase 0 — closed-market DECISION notifications suppressed (commit 9283552, `scripts/` free zone)
- **Change.** `scheduled_brief.sh` drops an instrument's DECISION line from the notification test and summary when that instrument's block carries the closed-market banner. ALERT, health, SHADOW, DIGEST and HEARTBEAT are not gated.
- **Why the wrapper matches prose.** The brief has no machine-readable market flag, and adding one means editing protected `decision_brief.py`. The banner string is therefore pinned at both ends by tests g1–g9: the briefs are rendered by the real `DecisionBrief.format` with the real `_market_status` banner and run through the real wrapper under `/bin/bash` 3.2.
- **Gate 1:**
  - Before the fix: 6 of the 9 new tests failed (closed decisions notified).
  - Mutants: 6/6 killed (no gate; blanket mute in the wrapper; blanket mute in `notify.sh`; banner reworded in `regime_detection`; no per-instrument reset; gate inverted).
  - Every "still fires" test (ALERT, health ALERT, SHADOW, HEARTBEAT, DIGEST) failed under at least one over-broad mutant.
  - After the reverts: 10/10 pass with caches cleared.
- **Gate 2 (real text, same instrument before and after):** every real day-log run was replayed through the old wrapper (main) and the new one (branch), in sandboxes with stub notifiers.

  | Runs replayed | DECISION notifications, old | new |
  |---|---|---|
  | Week of 10/11 | **12** | **6** |
  | All 246 run blocks | **28** | **16** |

  - In the week of 10/11, the six suppressed runs are exactly the six with the closed banner.
  - The all-runs figures match the inventory parser's independently derived 28/16.
  - A live brief (`reality_run.py brief --code <worktree>`, 2026-10-18T02:20Z, market closed, GBP/AUD LONG; project UNCHANGED by hash) notified DECISION through the old wrapper and nothing through the new one.
- **Gate 3: PENDING.** A scheduled closed-market run after the merge (see the PENDING LIVE CONFIRMATION list).

### Known defect left deliberately unfixed (Phase 0(b), one change at a time)
The DECISION trigger tests a STATE, not an EDGE:
- **Re-announcement.** An unchanged decision notifies again on every run. In the week of 10/11, the same GBP/JPY SHORT notified 8 times (replay: 2 of them closed-market, 6 open-market).
- **Silent withdrawal.** A decision returning to STAND ASIDE notifies zero times. GBP/JPY went from SHORT to STAND ASIDE at 2026-10-13 18:00 PDT: the replay shows 0 notifications under both wrappers.

This needs its own spec.

### Pre-registration (M5, M11)
- `docs/specs/decision_channel_measurement_spec.md` was committed as **c151e3c at 2026-10-18T02:13:07Z**.
- The **first market-data pull** (H4 bar timestamps) was at **2026-10-18T02:19:07Z**, six minutes later.
- The spec discloses what had been seen before it was written: the log format, and one full run, 2026-10-16 18:12 PDT.
- One parser rule was added **after** the spec commit. It is a format rule, not a definition. Concurrent wrapper runs that share a header stamp merge into one observation, accepted only if every copy agrees and none is an error page; otherwise the group is RUN ERRORED. Three such groups exist: 09-09 00:32 EDT ×2, 09-14 09:16 PDT ×3, 10-08 10:03 PDT ×3.

### Phase 2 inventory (counts and windows only) — `studies/decision_channel_inventory_report.md`
**Sources:**
- **Day logs:** 241 runs from 2026-07-29 02:33 PDT to 2026-10-17 18:06 PDT.
- **trade_signal_log.csv:** 13 rows. 12 match a day-log run with the same direction. One row has no day-log run: `2026-06-28T21:39:15Z_GBP_AUD`. It predates the first day log and carries round values (price 1.91, ATR 95.0). It is not in the registry and has not been touched.

**Run × instrument status:**

| Instrument | LONG open | SHORT open | STAND ASIDE open | MARKET CLOSED (directional) | RUN ERRORED |
|---|---|---|---|---|---|
| GBP_AUD | 0 | 3 | 79 | 31 (6) | 128 |
| GBP_JPY | 0 | 13 | 69 | 31 (8) | 128 |

- **The framework has never issued a LONG while the market was open.** All 4 LONG lines are closed-market runs from 10/16 to 10/17.
- The counts were cross-checked by grep:
  - 262 error REASON lines (126 × 2 + 4 + 6 inside the merged groups);
  - 62 closed banners;
  - the directional lines agree once the 09-14 triple is merged.

**Raw directional occurrences vs onsets vs independent episodes:**
- GBP_AUD: 9 occurrences, 2 onsets, 2 episodes.
- GBP_JPY: 21 occurrences, 3 onsets, 3 episodes.
- `foundation/tools/episodes.py` agrees on every onset it can place: GBP_AUD 1 = 1, GBP_JPY 3 = 3.
- Positive control on the real index: an added fire 29 bars after an onset was absorbed; one 30 bars after became a new episode.
- `episodes.py` refuses the GBP_AUD LONG onset of 2026-10-17T01:12Z. It falls after the last bar's open (the weekend), so the tool fails loudly as designed (I5).

**UNOBSERVED windows:**
- everything before 2026-07-29;
- RUN ERRORED, credentials: 07-29 (2 runs) and 07-30 → 07-31 (6 runs);
- **RUN ERRORED, the outage: 08-01 → 09-09** (118 runs, "OANDA not configured");
- RUN ERRORED, 09-16 18:01 ("Not enough data to calculate regime indicators");
- RUN ERRORED, 10-08 10:03 (concurrent group with error pages);
- SCHEDULER GAP 09-12 02:43 → 09-14 09:16 (54.6 h);
- SCHEDULER GAP 10-06 07:32 → 10-08 10:03 (50.5 h).

**Exclusion registry.** It has 2 entries (2026-09-16T09:08:08Z, authorized by the 2026-09-16 CORRECTION). Neither matches any day-log run.

**Gradeable for Measurement A: at most 3 of 5.**
- 1 is AWAITING OPEN: the GBP/AUD LONG of 10/16, first issued four hours after the weekly close; no open-market run has carried it yet.
- 1 is ONSET-CENSORED: GBP/JPY 10-08, which follows the 50.5 h scheduler gap and an errored group.
- Structure and leg-minimum checks could only lower the 3.

**STOP RULE MET (< 10). Measurement A was not run.** No price statistic was computed. The script uses only the H4 bars' timestamps; their prices are fetched but never used. The owner decides whether to run or wait. At the observed onset rate (5 in about 81 days, of which about 40 days were unobserved), reaching 10 gradeable episodes takes months, not weeks.

### Found along the way (recorded, not fixed)
- **`reality_run.py` false positive.** It exits 3 on any stdout containing "Framework error … not configured", including a report that quotes the outage's error text. The inventory run fetched correctly (901 H4 bars per instrument) and the project hash was unchanged. Its exit 3 is the scanner matching the report's own content.
- **`test_data_at_source.py` depends on the clock (pre-existing on main a3e070b).** 4 tests fail whenever the real market is closed, because `get_regime` reads the real clock and takes the `market_closed` price basis. Pinning only `_market_status` to a Wednesday gives 37/37. Branch suite on Saturday 2026-10-17: 820 passed, 4 failed (these four), 6 skipped. The rule-2 "green" condition is not met on a weekend for a reason unrelated to this change.
- **Measurement C premise.** The task described TOLERANCE = 0.25 × ATR as "the existing near-level tolerance". The live tolerance is a fixed 25 pips (`entry_confirmation._M15_LEVEL_PROXIMITY_PIPS`). It is frozen as instructed, with the mismatch noted in the spec.
- **Hypothesis for a future pre-registered run (not tested):** the scheduler gap is part of the channel's latency. GBP/JPY's 09-11 onset was first actionable at 09-14 09:16, after a 54.6 h gap with no runs.

## 2026-10-18 — Week-of-10/17 fix set (B2): the 2026-06-28 trade_signal_log row excluded

- **Row.** `2026-06-28T21:39:15Z_GBP_AUD` in `trade_signal_log.csv`. It is excluded from every tally through `exclusions.append_exclusion`. The row itself was not edited or deleted.
- **Why.**
  - `docs/audit_2026-09-29.md` §2 item 5 flags this row (the trade-signal grader's only graded row, exactly +150.0 pips) as looking synthetic.
  - This log's 2026-06-28 note records synthetic data injected that day.
  - The row predates the first day log (2026-07-29), so no brief run produced it, and it carries round values: price 1.91, ATR 95.0.
- **Observed.** `excluder("trade_signal_log.csv")` on the real row returned False before the append and True after. A tally through `filter_rows` keeps 12 of 13 rows. The registry diff is 1 line added, 0 removed.

## 2026-10-18 — The notification channel was never tested for whether it should reach the owner; week-of-10/17 fix set

**Defect class.** The suite had 820 tests, and every one asked whether a DECISION was correct. None asked whether a notification should reach the owner's phone: market status, an unchanged state, actionability. That was true for the framework's entire life. It is why 6 closed-market DECISION notifications went out in the week of 10/11 and no test caught it. The owner found it by reading his own week's notifications on a Saturday. Proposed rule 12 (AGENTS.md, team review) makes this a merge condition.

### Merged to main (free zone; suite green on a Saturday clock at each merge)
- **A1 `88a5046`: weekend-proof data-at-source tests.** The 4 tests that read the real clock now get an open-market time through `_market_status(_now=…)`, as test_v8 already did. No assertion changed.
  - Before, on the real Saturday clock (02:54Z): 4 failed, 33 passed.
  - After: 37 passed on the real Saturday clock, and 37 passed with the clock pinned to a Wednesday.
  - Live checkout after the merge: 815 passed.
- **A2 `6fa0326`: Phase 0 merged alone (9283552).** Live checkout: 824 passed.
- **C1 `3415303`: the heartbeat reports EXPECTED vs ON-TIME runs** (`scripts/run_count.py`). Expected slots come from the installed launchd plists, in the system zone.
  - **The first version (a plain run count) failed on real data.** launchd's three catch-up runs at wake (09-14 09:16) repaid the slots slept through, so the 09-12 → 09-14 gap read 21/21 at the 09-20 heartbeat. Slots are now met only by a run within 60 min after them, one run per slot. The 60 min is an operational threshold taken from the measured lateness of 246 runs: 223 within 15 min, 16 at 60+ min.
  - On the real logs, replayed at each Sunday:

    | Heartbeat | Brief slots on time / expected |
    |---|---|
    | 09-14 (the late heartbeat) | 14/21 |
    | 09-20 | 18/21 |
    | 10-11 | 15/21 |
    | 09-27, 10-04, 10-18 | 21/21 (no false alarm) |

  - Scratch copy with 2 days of logs removed: NEEDS ATTENTION | SHORTFALL. Mutants: 8/8 killed.
- **C2 `1e399d2`: reality_run detects a failure, not a mention of one.** Failures are now anchored line shapes: the brief's error REASON line, `GRADER EARLY EXIT — ` at line start, and a column-0 Traceback on stderr. The bare "not configured" marker was dropped.
  - Before: a report quoting the outage text exited 3.
  - After, on real runs: the inventory study (4 quoted error lines) exits 0; a real brief with `--no-env` (genuine error page) exits 3.
  - Mutants: 6/6 killed.
- **Phase B `6bd6c37`.**
  - **B1:** replay harness committed as `studies/decision_gate_replay.py`. It reproduces 12 → 6 and 28 → 16.
  - **B2:** the 2026-06-28 row was excluded (entry above).
  - **B3:** `studies/decision_channel_followups_report.md` lists the 16 open-market directional decisions. All are SHORT: 3 GBP/AUD on 09-10/09-11, 13 GBP/JPY. Rows 1–7 predate the live-price merge `6471072` (2026-09-30T08:54Z), so the price those briefs printed was the previous daily close.
  - **B4:** see the finding below.

### Findings recorded, not fixed
- **B4: the post-hoc concurrent-run rule changed the gradeable count, not the episode count.** There are 5 independent episodes under either handling. The gradeable bound is 3 with merged-if-agreeing and 2 with counted-as-error (GBP/JPY's 09-11 episode becomes NEVER ACTIONABLE). The stop decision (< 10) is unaffected.
- **Measurement A spec gap.** The spec's PRICE NOT OBSERVED rule keys on the brief's not-live flag, which did not exist before `6471072`. So pre-09-30 briefs printed a stale close with no flag, and 3 of the 3 "eligible" episodes predate it. The spec is frozen, so any run of Measurement A needs a v2 that treats pre-`6471072` prices as not observed.
- **The 07:30 DIGEST renders every directional decision as "?".** `daily_digest.py` expects "—" right after the word, but directional lines read `LONG  ▲ —` / `SHORT ▼ —`.
  - Observed on the real 10/12 run (`GBP/JPY ?`) and tonight's run (`GBP/AUD ?`).
  - 8 morning runs in the record carried a directional decision.
  - This is a notification-content defect of exactly the class above; it needs its own fix.
- **The DECISION notification text does not name the pair** (`DECISION LONG ▲ — look for buy entries`).
- **The conftest evidence guard worked as a positive control.** When the notification ledger was wired, `test_notify_helper.py` (which pointed PROJ at the repo root) wrote rows into the worktree's project root. The session failed with "TEST RUN CHANGED REAL EVIDENCE FILES". The live project was untouched, and the test now runs in a temp project.

### Held for team review (branch `feat/notification-review`, not merged)
- **D3:** `docs/specs/notification_ledger_spec.md` plus the build. Mutants: 8/8 killed. Gate 2: real brief text through the real wrappers gave 3 notifications sent and 3 rows; the closed-market DECISION gave no row; an error page records ERROR.
- **D1:** AGENTS.md rule 12. The task called it "rule 11", but rule 11 already exists, so it is numbered 12.
- **D2:** a trader_review §4 step recording MATERIAL / TOTAL. It depends on D3.

## 2026-10-18 — I8 live-path confirmation: three GBP/AUD rows printed the previous daily close (note only; I8 not fixed)

- **The rows.** The three GBP/AUD SHORT runs on 2026-09-10 18:04, 09-11 02:38 and 09-11 07:32 PDT (01:04Z, 09:38Z, 14:32Z) all printed 1.8879.
- **Source of the price.** That is the close of the OANDA D1 bar that opened 2026-09-09T21:00Z (1.88794).
- **The real price.** It was 1.8866, 1.8842 and 1.8861 (H1 closes of the hours containing each run). The printed price lay outside each hour's traded range (highs 1.88737, 1.88525, 1.88639).
- **What this adds.** Next to I8's three GBP/JPY rows of 2026-09-25 (209.984), this is the same defect on a second pair, observed on the live path.
- **Premise note for whoever weighs I8.** The data-at-source merge `6471072` (2026-09-30) made the displayed price OANDA's live mid, and later briefs print varying prices (studies/decision_channel_followups_report.md rows 8–16). So I8's stale-price consequence appears closed since 09-30; its "`_split_live_bar` vestigial" part was not examined here.

## 2026-10-18 — Long-side diagnosis: no mechanical directional defect; the long side was lost at the daily classification (studies/long_side_diagnosis_report.md)

- **Finding that prompted it.** All 16 open-market directional decisions in 81 days were SHORT.
- **Funnel (3B).** Over 179 market-open classifications (registry applied at use), daily TRENDING_UP occurred **0 times on either pair**, against 14 TRENDING_DOWN on GBP/AUD and 22 on GBP/JPY.
  - When daily structure confirmed UPTREND (21 GBP/AUD rows, 9 GBP/JPY rows), daily ADX was below the 25 that TRENDING_UP needs in 20 of 21 and 9 of 9.
  - From 2026-09-25, GBP/AUD's daily ADX with UPTREND structure never exceeded 19.3.
  - The day logs agree: "Daily chart: trending up" never appears in any open-market run.
- **Symmetry (3A).** The full path was read, and three asymmetries were found; none changes a decision:
  1. The weekly label table, `regime_detection.py:607-614`. It has a display effect: "strong downtrend on all timeframes" is shown while the 4-week trend is flat.
  2. A latent tie in the structure slope fallback, `:398`.
  3. An unused moving-average tie, `:650-651`.
- **Mirror test on real bars.** Bars reflected about their mean through the real `get_regime` and official decision gave 0 direction mismatches in 600 as-of points.
  - A planted one-sided rule was detected by the same test (3 and 8 direction mismatches). It was reverted, and the project hash was unchanged throughout.
  - On ~3 years of real bars the same code gives 16 LONG / 5 SHORT (GBP/AUD) and 18 / 3 (GBP/JPY) at sampled points.
- **Verdict.** A window artifact. The window held falls with daily ADX ≥ 25 and confirmed structure, and a slow rally that never reached that bar. It is not a code defect.
- **Hypothesis recorded, not tested.** A symmetric ADX gate may pass fewer grinding rallies than sharp falls.

## 2026-10-18 — Notification content: the digest names directional decisions; DECISION notifications name the pair (merged 3b00341)

- **`daily_digest.py` (`4f6e046`).**
  - Before: on the real 10/12 and 10/17 07:30 runs it printed "GBP/JPY ?" and "GBP/AUD ?".
  - After: "GBP/JPY SHORT" and "GBP/AUD LONG".
  - Over every real 07:xx run: 8 of 8 directional mornings showed "?" before the fix and 0 after; the 60 other digests are unchanged.
  - Pinned on the real fixtures and on the exact lines `DecisionBrief.format` renders. A glyph mutant (▲ → △, reverted) fails the pin.
- **`scheduled_brief.sh` (`122bb87`).**
  - The summary now reads "GBP/AUD LONG", or "GBP/AUD LONG · GBP/JPY SHORT" when both pairs carry a decision.
  - The new tests g10–g12 failed on the old format. Mutants killed: pair dropped, pair set once, ungated source.
  - On the real 10/12 run the notification reads "GBP/JPY SHORT · …"; the two real closed-market LONG briefs send nothing.
- **Still open, not fixed.** The shadow line appended to a DECISION summary is a truncated fragment that does not name its pair ("EARLY_MOMENTUM_v2 candidate: LONG entered at").

## 2026-10-18 — Deep code review: five reviewers, each checked by an adversarial verifier; free-zone cleanup merged; protected cleanup held for review

**Method.** Five read-only reviewers covered dead code, redundancy, structure and naming, free-zone hygiene, and comments. Each was followed by a skeptic told to refute every finding.
- Results: 72 findings, 43 confirmed, 29 corrected, 0 refuted outright.
- The corrections mattered:
  - `session_context.py` is a previously used path, so it is unavailable as a new name.
  - Folding `intraday_context` into `levels_context` would not remove its silent-failure path.
  - `validate_h4_thresholds` is not superseded by v2.
- The live project's 613 files were hash-identical before and after the review.

**Merged to main (c483c5b, free zone):**
- The 56 test files moved to `tests/`. Collected test ids are identical before and after (855). `tests/_paths.py` asserts the project root: a wrong root used to skip tests silently, and now fails collection.
- LIVE_CORE gained `ledger_io.py`, and a test requires it to equal AGENTS.md's protected list. Dropping a name fails it.
- `historical_scenario_replay` refuses to run inside the project. From the project root it would have written synthetic rows into the live ledgers.
- Test hygiene:
  - an `or True` assertion removed;
  - invariant 1 no longer allows grade C (OBSERVED: the C rule itself is caught by the decision grid, not by this line);
  - the `trades.csv` schema now comes from the writer.
- Indexes: a root README (each module's job and ledger), plus `scripts/`, `studies/` and `docs/specs/`. Dead foundation citations now point to git history; the dead `shadow/` path was dropped from 9 studies.
- Live checkout: 857 passed, 0 skipped. The installed skill was rebuilt; exactly the 3 edited reference files changed.

**Held: `chore/protected-hygiene`.** Team review is required (docs/specs/code_hygiene_spec.md, committed first). 22 files, −643 / +398.
- Comments and docstrings in 12 protected modules. The AST of every one, docstrings removed, is identical to main.
- Unreachable code removed:
  - `_split_live_bar`, which never split;
  - 12 `get_regime` outputs nothing read, including about 90 lines of legacy prose and the fuel block;
  - nine yfinance-era guards;
  - dead members;
  - the already-run loss backfill.
- `calendar_fetch` writes through `ledger_io`.
- **Gate 2:** with `reality_run`, branch against unchanged main run the same way, the real brief and the real grader have identical stdout, stderr and ledger copies (market closed, so prices are static). The mirror test on 600 points of real history is identical to main. Each new or changed check was shown to fail on a mutant.
- **Not done, for the owner or team:** renames (names proposed in the spec), wiring or deleting `session_guard`/`risk_config`, a raising pip-size helper, the episode-count methodology, and protecting `trade_management.py`.

**Held: `chore/live-scripts-cleanup`** (free zone, but on the scheduled path). It is held until the Gate 3 runs land.
- `latest_view` now uses the digest's parser. On the real 10/12 and 10/13 views, "GBP/JPY" becomes "GBP/JPY SHORT".
- The view is written atomically.
- Wrapper headers now describe what each job does (comment-only, proven by a diff with comments removed).
- `install.sh` loses a redundant chmod.

**Found:**
- **`reality_run --code <worktree>` runs the brief without the news calendar.** `news_gate` reads `calendar.csv` from beside its own module, and a worktree has none. Every Gate 2 run from a worktree has exercised a brief with the news gate inactive ("news calendar missing"). Recorded, not fixed.
- **`git grep` with `\b` in a basic pattern matched nothing, silently.** Two searches in this review returned false zeros until they were redone with a positive control. Searches that back a deletion must carry a control.

## 2026-10-18 — Team review of the code-hygiene work: decisions; a known Gate 2 blind spot recorded

**Decisions** (recorded in full in docs/specs/code_hygiene_spec.md §D):
- **1A, comment-only edits to 12 protected modules: approved and merged.** The AST of each module, docstrings removed, was re-proven identical to main at merge time.
- **1B, code removals: approved, held until after Sunday's 18:00 PDT run.** The `_split_live_bar` removal will merge as its own commit closing I8.
- **Renames: deferred.** methodology.md, incident_catalogue.md and this log cite modules by name and line.
- **Circuit breaker: keep, do not wire.** It is now a prerequisite before the first real-money trade (AGENTS.md). Until then the risk limits are unenforced.
- **The 10 `gbpaud_*` studies: commit them as they are,** each with a citation-integrity header.

**Known Gate 2 blind spot (record only; fix queued for after Sunday).**
- `scripts/reality_run.py --code <worktree>` runs the brief with **no news calendar**. `news_gate` reads `calendar.csv` from beside its own module, and a worktree has none (`.gitignore`).
- Observed 2026-10-18: the same unchanged code printed "news calendar stale" when run from the live checkout and "news calendar missing" when run from a worktree.
- So no Gate 2 run from a worktree has ever exercised the news gate. It matters more than it looks: I28 found that news staleness **fails open**. The gate is unexercised and fail-open at the same time.
- The verification tooling is deliberately left unchanged right before a verification window. Until the fix lands, read any worktree Gate 2 as "news gate not tested".

**For Gate 3 triage.** A 56-file test reorganization (c483c5b) and these comment-only edits merged on the night of 2026-10-17. Neither touches what the scheduled jobs execute: the tests are not on the live path, and the comments are AST-identical. If a scheduled run misbehaves, rule both out first.

## 2026-10-18 — Gate 3 window (Sunday): E1-E4 observed on the scheduled path; E5 blocked

All four runs used main 733a63a: the gate, the run count, the digest fix and tonight's comment-only edits, but none of the held branches. Notification delivery is not recorded until the notification ledger merges, so "nothing sent" below rests on the wrapper's own record, not on a delivery record.

**E1, 02:30:07 PDT (closed).** GBP/AUD LONG under the closed banner; GBP/JPY STAND ASIDE. The log has `DECISION notification suppressed: market closed`.
- VERIFIED: the DECISION notification was suppressed (the gate's own line; its tests were shown able to fail).
- OBSERVED: nothing else had a trigger (no health change, no ##ALERT##, no shadow signal).
- The calendar auto-fetch also ran.

**E2, 07:30:09 PDT (closed).** The same result as E1, with the suppression line.
- The 07:30 DIGEST fired; it is not gated. Recomputed with main's daily_digest.py from this run's exact output, it read "GBP/AUD LONG · GBP/JPY STAND ASIDE — watch: …". The "?" fix is live. That text is recomputed; the wrapper does not log what was sent.
- **Finding: the DIGEST conveys a closed-market directional decision with no market-closed note.** At 07:30 on a Sunday it sent "GBP/AUD LONG". This is the should-it-reach-the-owner class of proposed AGENTS rule 12. Recorded, not fixed.
- logs/latest_brief.log showed the 02:30 run as "GBP/AUD · GBP/JPY STAND ASIDE", with no direction. That is the latest_view copy of the old parser, live-confirmed; the fix is on chore/live-scripts-cleanup.

**E3, 12:30:05 PDT heartbeat: VERIFIED.** It reported `brief 21 expected / 21 on time / 21 ran; outcomes 7 expected / 7 on time / 7 ran`, healthy. A live SHORTFALL has not occurred; the detector was shown on replayed real gaps (14/21 and 15/21).

**E4, 18:00:08 PDT (open; live prices GBP/AUD 1.9138, GBP/JPY 210.471): the case did not arise.** Both pairs were STAND ASIDE. An open-market directional notification remains unobserved on the scheduled path.

**E5: blocked.** feat/notification-review (the notification ledger, AGENTS rule 12) has not had team review.

**Decision-channel consequence (no statistic computed).** The GBP/AUD LONG issued Friday 2026-10-16 18:12 PDT, after the weekly close, became STAND ASIDE at the first open-market run. Under docs/specs/decision_channel_measurement_spec.md, that episode is **NEVER ACTIONABLE**. The reversal also notified nobody: that is known defect 0(b), the silent withdrawal, here harmless because the LONG had never been notified (the gate held it).


## 2026-10-18 — CORRECTION: the heartbeat run-count test (C1, merged 3415303) failed for 30 minutes after every scheduled slot

- **The claim, and why it was wrong.** It was reported VERIFIED on 2026-10-18. It hardcoded "21 expected", but `run_count` correctly leaves a slot out of the count for its first 30 minutes, since that run may still be going. So the suite went red from :00-:30 after every brief slot, and from :15-:45 after the grader's.
- **Observed.** The heartbeat test failed at 18:06 PDT on main: 2 failed, the output showing "brief 20 expected". The code was right; the test was wrong.
- **Fix.** The test now requires on-time = expected, with expected 21 (or 20 while a slot is in its grace window), and a SHORTFALL of exactly 6 missing.
  - Fixed test at 18:06, inside the window: 3 passed. Main's old version at the same time: 2 failed.
  - Still caught: a run count that never raises a shortfall, and one that is short by one.
- **How it was missed.** Every earlier suite run happened to land outside a grace window. The original test was not exercised at the time-of-day boundary its own code defines.

## 2026-10-18 — I8 closed: `_split_live_bar` removed (its own commit, per the 2026-10-18 team review)

- **The two halves of I8.**
  - **The stale price** was closed by the live-price merge `6471072` (2026-09-30). The brief now prints OANDA's live mid (data_at_source_spec P1).
  - **The vestigial split** is removed in this commit. `oanda_feed._get_bars` drops the forming candle, and a complete candle is stamped at its open, so it is always at least one bar-length old. `age_hours < threshold_hours` could therefore never hold, and the split never happened.
- **Live-path evidence for the stale half.**
  - The three GBP/AUD SHORT runs on 2026-09-10 18:04, 09-11 02:38 and 09-11 07:32 PDT all printed 1.8879. That is the close of the D1 bar opened 2026-09-09T21:00Z (1.88794).
  - The real prices at those times were 1.8866, 1.8842 and 1.8861, and 1.8879 lay outside each hour's traded range (validation_log 2026-10-18, "I8 live-path confirmation").
  - The three GBP/JPY 2026-09-25 rows (209.984) were the first instance.
- **What the commit removes.**
  - `_split_live_bar` is replaced by `_closed_bar_age_hours`. The age it returns still feeds the brief's stale-feed warning.
  - Removed: the `live_bar_d1` value, the `live_bar_in_progress` key and field, the unreachable "Daily bar in progress" line, and the weekly fallback that only existed for a split.
  - It also removes the one case where the split could have fired: a 167-hour weekly candle in a spring-forward week, which would have wrongly dropped a completed weekly bar for about an hour after the Friday close (INFERRED from the code; never observed).
- **Why remove it rather than keep it as a guard:** M31, delete a staleness class rather than watch it. This closes the backlog entries at data_at_source_spec "Out of scope" and this log's 2026-07-29 cleanup backlog.
- **Evidence:**
  - Full suite green.
  - The real brief and grader via `reality_run`, branch against unchanged main run the same way: stdout, stderr and ledger copies identical.
  - The mirror test on 600 real as-of points is identical to main.
  - incident_catalogue.md I8 is marked CLOSED. The closure takes effect when this commit merges to main, after the 2026-10-18 18:00 PDT Gate 3 run.

## 2026-10-19 — The shadow candidates had no abandonment rule for their entire life; futility checkpoint adopted

**Finding.** From the 2026-07-29 spec freeze until today, the candidates' review gates were FLAG at N=30 and REVIEW at N=60 (AGENTS.md; `shadow_signals.FLAG_N`/`REVIEW_N`). There was no rule for when to ABANDON one, so a losing candidate ran to N=30 at minimum by default. The framework's only FAILED criterion (M10: N≥30 and avg R ≤ 0, from data_map_spec 2026-09-11) governs the historical exam, not the forward candidates. It too starts at N=30. At 0.7–0.9 episodes a week, that is most of a year.

**Adopted** (docs/specs/futility_rule_spec.md, committed ff3cf12 before any further grading):
- once, at N=20 graded independent episodes;
- 90% one-sided upper bound on mean R below +0.15R → REFUTED and retired;
- applies to all three candidates;
- **it does not fire today**: EM_v2 has 3 episodes, THRUST_PULLBACK 1, MOMENTUM_JOIN 1. Nothing was retired.

**Disclosure (in full in the spec).**
- The rule was written with EM_v2 results visible. The commissioning message said "4 graded episodes averaging about −0.95R". The ledger, counted by the spec's method, shows 3 episodes with first-fire R of −0.55, −0.39 and +0.34 (mean −0.20R). The clock-hour counter shows 4. −0.95R could not be reproduced.
- The +0.15R threshold is the framework's pre-existing minimum edge (M10; power_check's examples).
- The checkpoint was moved from the proposed N=15 to N=20 because N=20 is the bootstrap's own gate and M3's minimum for any claim. A design simulation (studies/futility_rule_simulation.py, synthetic R) shows the bound is unstable below it: a true +0.15R candidate is wrongly retired 8.4% at N=15 and 16.0% at N=20 on near-binary R, and 6.9% / 5.6% on smoother R.
- **Known limit:** a true −0.20R loser is retired only 30–49% of the time at N=15–30. The rule catches clear losers, not mild ones.

**Tooling.**
- `power_check.bootstrap_upper_bound` mirrors the lower bound: percentile bootstrap, N≥20, same under-coverage label. The CLI prints whether the futility condition fires.
- Tests: the positive control retires a −0.48R sample and keeps a +0.75R one.
- Mutants killed: printed below N=20, wrong percentile, fire/no-fire label inverted. The label mutant first survived and the test was strengthened.


## 2026-10-19 — The brief stops showing the invalid regime-accuracy percentage (docs/specs/accuracy_line_suppression_spec.md)

- **The line.** Every morning DATA BASIS read "daily unresolved-direction bucket: 49 outcomes logged, 0% accuracy (developing)". Read plainly, that is wrong 49 of 49. It came from a measure the audit ruled invalid (item 2, I18).
- **The change.** For buckets with 20 or more outcomes, the brief now shows the count, and says accuracy is not shown because the way it is measured is known to be wrong and is being repaired. No percentage, tier or accuracy-driven advice. The rows are still logged and graded; only the display changed.
- **Gate 1.** 4 of 5 new tests fail on the old code. The fifth, under-20 wording unchanged, fails on a mutant. The banned-token display test still passes.
- **Gate 2 parity.** The real brief ran back to back on main's code and this branch via reality_run, at 16:26:57Z and 16:26:59Z with the market open.
  - The DECISION lines are identical (both pairs STAND ASIDE), and stderr is empty in both.
  - The only stdout difference, with times and prices masked, is GBP/AUD's DATA BASIS line.
  - Every ledger copy's rows are identical in their decision fields. The comparison catches a planted stand_down flip.
  - Both runs came from worktrees, so neither exercised the news calendar (the known Gate 2 blind spot); the comparison is like for like.

## 2026-10-19 — The shadow tally overstated N and showed no R; a reviewer read −0.95R where the truth was −0.20R (docs/specs/shadow_tally_spec.md)

**The chain.**
- The brief's shadow tally read "17 rows / 4 episodes, 16 graded, 5 wins, -79 avg pips".
- It had two faults:
  - **N was inflated.** Episodes were split at 120 clock hours, but 30 H4 bars span about 168 hours once a weekend falls inside them (M34). Ungraded rows counted too.
  - **R was missing.** The line gave a win count with no breakeven figure, and net pips, but no R.
- A reviewer converted the line to R using the pending signal's stop, and reported "4 graded episodes averaging about −0.95R".
- That figure commissioned a doctrine change: the futility rule (entry above, same date). Its disclosure recorded that −0.95R "could not be reproduced"; this entry is the explanation.
- **The truth, from the ledger:** 3 independent episodes, with first-fire R of −0.55, −0.39 and +0.34. Mean −0.20R, median −0.39R, −0.47R without the best one.
- The futility rule itself is unaffected. It fires at N=20 and was adopted on its own grounds; nothing was retired.

**Class.** The display layer caused an analytic error downstream. This is a new instance of an old class: a count from an unproven path read as evidence (M24), and N counted in rows or clock time rather than episodes on the bar index (M34). The numbers in the line were each true. What made it misleading was which numbers it chose to show.

**What changed (merged as one branch, `fix/tally-episodes-r`).**
- **Episodes** (`shadow_signals.graded_episodes`): graded, valid, non-excluded rows only. A new episode starts 30 or more H4 bars after the current one's first fire, counted on the trading-calendar bar index. An episode's R is its first fire's R. `episode_count()` was removed; `get_shadow_tally()` carries `episodes` and `episode_rs`, and keeps its old keys.
- **The tally, as rendered by today's real brief:**
  ```
        tally: 3 independent episodes from 16 graded rows (2 still open)
               per episode: avg -0.20R, median -0.39R, without the best one -0.47R
               diagnostic only: avg -79 pips at bar 30 over the graded rows
               (futility check at 20 episodes, flag at 30, review at 60)
  ```
  The win count is dropped. The candidates exit at bar 30, not at a fixed target, so there is no single breakeven rate to show beside it. The heartbeat and nightly-grader summaries show the same episode count and avg R.
- **Digest:** when every pair's block says the market is closed, the 07:30 digest leads with "MARKET CLOSED until <next open> — no live calls", then lists each pair as its last read. It is not suppressed. A single closed pair shows as "<pair> last read <decision> (market closed)".
- **AGENTS.md rule 2:** the hand-written test count was removed. It went stale three times (853 recorded vs 865 actual, most recently).

**Corrected tallies, real ledger (copy, hash-verified unchanged), 2026-10-19:**

| Candidate | Pair | Graded rows | Episodes | Episode R | Old count |
|---|---|---|---|---|---|
| EARLY_MOMENTUM_v2 | GBP/JPY | 16 of 17 | 3 | −0.55, −0.39, +0.34 (avg −0.20R) | 4 |
| THRUST_PULLBACK | GBP/JPY | 1 of 1 | 1 | −0.33 | 1 |
| MOMENTUM_JOIN | GBP/AUD | 5 of 5 | 1 | −1.00 | 1 |
| EARLY_MOMENTUM (retired v1) | GBP/JPY | 1 of 1 valid | 1 | −1.00 | 1 |

All are INSUFFICIENT (N < 20).

**Evidence.**
- **Two implementations agree.** `shadow_signals` (a calendar-built bar index) and `foundation/tools/episodes.py` (the real OANDA H4 index in `studies/`) give the same episode starts and R in every candidate/pair cell: 0 disagreements. Under a clock-hour mutant the same comparison reports 1 disagreement (EM_v2), so it can fail.
- **Gate 1.** The 7 new tally tests all fail on main's code. Six mutants were each killed: clock hours, ungraded rows counted, the without-best line shown at 1 episode, plural "rows" at 1, the last fire's R used, the win count restored. The ungraded-row mutant first survived (the R parse also dropped open rows); the test was fixed to give an open row an R value.
- The 2 digest-fix tests fail on main's code. Three mutants were killed: gate removed, every pair treated as closed (this one also fails the open-market pin), and a closed pair left as a bare direction.
- Three older tests built episodes from ungraded rows; they now grade them, each documenting old → new. The old digest test that expected "GBP/AUD LONG" for the closed 10-17 run now expects the last-read form.
- **Gate 2 parity.** The real brief was run via reality_run on main's code and then on the branch, back to back (18:03:21Z and 18:03:23Z, market open; an EARLY_MOMENTUM_v2 LONG fired, so the tally rendered in both).
  - The DECISION lines are identical (both pairs STAND ASIDE), and stderr is empty in both.
  - With times and prices masked, the only stdout difference is the tally line.
  - Ledger copies are identical on every decision field (stand_down, filter_allowed, regimes, confidence, size). The comparison catches a planted stand_down flip.
  - The digest of both real runs is the same from main's and the branch's digest code.
  - The project hash was unchanged across both runs.
- **Suite:** 869 passed on the branch.

### Gate 3 — PENDING LIVE CONFIRMATION
- **The closed-market digest on the scheduled path:** the first 07:30 run with the market closed after this merge (Sat 2026-10-24). Until then the closed path has only been run on the real captured 10-17 brief.
- **The new SHADOW summary in the nightly grader's notification:** the first night a shadow outcome is graded after this merge.
- **The new shadow line in the weekly heartbeat:** its next scheduled run.

---

## 2026-10-19 — Data map Stage 2 request stopped before sourcing (rule 5: the brief's premise was wrong); raw Dukascopy feed found reachable

*Recorded 2026-10-20. The stop happened 2026-10-19 and was reported in-session; no entry was written at the time.*

**The request:** "source and convert the STUDY partition", described as a plan pre-registered in September "and never run."

**The premise failed inspection.** Stage 2 had run on 2026-09-11 (commit `5c0e0ab`; entry "STAGE 2 (data_map_spec §10): overlap check FAILED", above). It failed the frozen overlap thresholds on both pairs, and the ladder declared history validation INFEASIBLE. That entry makes any re-attempt on the raw feed "a team decision, not self-authorized", and no later ruling existed. A search of validation_log, foundation/, docs/ and all commit subjects found none. Under AGENTS.md rule 5 the run stopped before any download. Nothing in the repo changed (`git status` empty).

**Reachability probe (header-only, no price data):** 2026-10-19 23:50 PDT (2026-10-20 06:50 UTC). One overlap-window file per pair (the 2023-09-04 10:00 UTC tick hour), nothing from 2014–2021.

| request | result |
|---|---|
| GBPAUD tick hour | HTTP 200, 14,875 bytes |
| GBPJPY tick hour | first try: TLS failure (curl exit 35, after 9.4 s); retry: HTTP 200 |
| **control:** same host, nonexistent pair `NOSUCHPAIR` | **HTTP 404** |

The 404 control shows the probe can tell a served file from a missing one. `datafeed.dukascopy.com` was unreachable all session on 2026-09-11. On this date it served, intermittently. That is the condition the 09-11 entry named for a re-attempt.

---

## 2026-10-20 — TEAM RULING: history data — OANDA depth check first; Dukascopy raw-feed re-attempt authorized as ATTEMPT 2 OF A MAXIMUM OF 2

This is the team decision the 2026-09-11 Stage 2 entry requires before any re-attempt.

**Authorized, with conditions:**
- **Thresholds unchanged:** ≤ 2% disagreement outside the rollover bar, ≤ 1.5-pip median close difference. "Changing a threshold to pass is cheating. Trying the source the spec originally named is not."
- **The Dukascopy re-attempt is attempt 2 of a maximum of 2.** If it fails, Dukascopy history validation is INFEASIBLE and closed permanently. The cap is what distinguishes this from retrying until a gate passes.
- **The 09-11 FAIL stays in the record.** This entry adds; nothing is replaced or amended.
- **Order:** Phase 1, an OANDA depth check with a reduced gate against the framework's own stored bars. Phase 2, the Dukascopy attempt, only if Phase 1 comes up short, and only after a short spec is committed stating the attempt number, the unchanged thresholds and the expected outcome. Phase 3, a HistData re-probe.
- **Boundaries:** the SEALED EXAM is not sourced, converted, counted or opened in any phase. Verification numbers only. Free zone; no protected module, no ledger written.

**Reasoning, as given:** the 09-11 run never tested the specified source. The spec named Dukascopy's RAW feed as primary. It was unreachable, so that run fell back to the hourly chart feed, a different and lower-quality product. HistData returned 0 bytes, so that rung was never executed either. This is therefore the first execution of the test as specified, not a second attempt at the same test. The OANDA-first order follows the 2026-09-29 audit (§5 item 2): same broker, same bar construction, same timestamps as the live system, so there is no foreign feed to reconcile.

**Two premise conflicts found on inspection (rule 5), recorded with the ruling:**
1. Phase 1 task 2 asked for bar counts over 2014-01-01 → 2021-12-31. Everything up to 2021-04-25 is the SEALED EXAM, which the ruling's own boundary says is "not counted." Not done. The STUDY span (2005–2013) and the unsealed remainder (2021-04-27 → 2021-12-31) were counted instead, labelled as a substitution.
2. The audit's "OANDA's own 2014–2021 data" is the SEALED EXAM itself. Using it means opening the exam under data_map_spec §7 (one frozen candidate spec, hashes, marker, one run), not a change of data source. Not acted on.

---

## 2026-10-20 — History data Phase 1 (OANDA depth): OANDA's own 2005–2013 weekday grid is intact; Phase 2 NOT RUN pending a ruling; Phase 3: HistData functional

Run under the ruling above, on branch `feat/history-depth-attempt2`. Full numbers, every gap and the scripts are in studies/history_depth_report.md. Verification numbers only. OANDA candles outside the reduced-gate window were reduced to timestamps on receipt. **No sealed-exam bar was counted or stored.** The project hash (659 files) was identical before and after.

**Phase 1 — OANDA depth (this live account, mid prices, default 17:00-NY alignment):**
- **Earliest candle:** GBP_AUD D1 2004-05-31, H4 2004-06-01. GBP_JPY D1 2002-05-07, H4 2002-05-08. Both pairs cover the STUDY start.
- **STUDY 2005–2013 as served: D1 fails the §3 band.** There are 273–361 candles a year against [252, 262], because of 14–101 weekend-session candles a year (the "old convention").
- **The weekday grid underneath passes the §3 counts, both pairs, all nine years:**
  - aligned weekday D1 candles: 259–262 a year;
  - weekday sessions with all 6 H4 bars: 99.23–100% (needs ≥ 99%);
  - 0 misaligned candles;
  - every gap and short session falls on Dec 24–26 or Dec 31–Jan 2.
- **USED remainder 2021-04-27 → 2021-12-31:** 179 D1 / 1,074 H4 per pair, 100% full sessions, 0 weekend candles.
- **API constraints (observed):**
  - hard limit of 5,000 candles per request, enforced on `count` and on the count a `from`/`to` window implies;
  - `to` in the future is rejected;
  - `from` returns the candle *containing* that instant;
  - 30 back-to-back requests returned 200 with no throttling.
- **Reduced gate — exact match:**
  - September cache vs OANDA today: 30,810 of 30,810 bars identical on O/H/L/C (2022-05-31 → 2026-09-10; diff 0.0 pips at median, p95 and max).
  - Live-recorded D1 closes in `regime_classification_log.csv` (`price_basis=d1_close`, 2026-09-30 → 2026-10-19): 76 of 76 identical.
  - **Control:** a planted +1-pip H4 close and a +2-pip ledger close were each reported exactly.
  - **Limit:** this proves stability for 2022–2026 only. Nothing stored from 2005–2013 exists to compare against.
- **Verdict:** can OANDA alone cover the STUDY span at D1/H4? **Not as served (NO).** On counts, **YES** once the weekend-session candles are set aside; same broker, nothing to reconcile. It is not a gate pass yet:
  - §3 items 3 (D1/H4 internal consistency) and 4 (known-date spot checks) need prices and were not run;
  - whether weekend-session candles are dropped or folded into Monday is a conversion rule the team has not set.
- **Census correction (INFERRED):** data_map_spec §1's "H4 ~4.8–5.7 bars/day with 70–95 short days/yr" reproduces as H4 rows ÷ D1 rows *including weekend candles* (4.71–5.75). It measured the weekend extras, not missing weekday bars. The census method was not recorded, so this rests on the arithmetic match. The spec text is unchanged; it is fixed absent a team ruling.

**Sealed-edge incident:**
- A request with `from=2021-04-26T00:00Z` returned the candle containing that instant. That candle opens Sunday 2021-04-25 17:00 New York: its label is sealed, its session (Monday 04-26) is USED.
- The post-receipt guard aborted. Nothing was written, and only the timestamp was printed.
- The guard now keeps a one-day margin, and the Monday 2021-04-26 session was given up.
- **The spec does not say which side of the seal a Sunday-open candle belongs to; that is for the team to rule.**

**Phase 2 — Dukascopy attempt 2 of 2: NOT RUN.** Phase 1 came back neither as the ruling's YES nor as clearly short. It found a same-broker path, the outcome the OANDA-first order was designed to prefer. Attempt 2 is the last Dukascopy attempt and cannot be taken back, so spending it now is the team's call. No Phase 2 spec was committed, and nothing was requested from Dukascopy.

**Phase 3 — HistData: endpoint FUNCTIONAL (2026-10-20 00:09 PDT)**, a change from the 2026-09-11 "0 bytes":
- **GBPJPY:** offered 2002–2026, so all STUDY years. The 2005 archive downloaded as a valid zip with a 351,750-row M1 csv.
- **GBPAUD:** offered 2007–2026 only. The 2007 archive's first row is 2007-09-30, so HistData lacks GBP/AUD for 2005-01 → 2007-09.
- A not-offered year (GBPAUD 2005) serves an empty form token, which was the 2026-09-11 symptom.
- Archives were kept outside the repo, not extracted, and not used.

**For team review:**
1. Is the OANDA path adopted for the STUDY span?
   - If so: the weekend-candle rule (drop vs fold), then §3 items 3–4 on OANDA data.
   - If not: whether to spend Dukascopy attempt 2.
2. Which side of the seal the 2021-04-25 Sunday-open candle belongs to.
3. Whether data_map_spec §1's census line and foundation/market_data_facts.md:19 are corrected in light of the census finding.

---

## 2026-10-22 — OWNER RULING on the history-depth report: OANDA adopted for the STUDY span; seal embargo; census corrected (INFERRED); weekend-candle rule PROPOSED, not built; §3 items 3–4 declared before running

**Decisions (owner, 2026-10-22):**
1. **OANDA is the STUDY data source.** Dukascopy attempt 2 of 2 is **not spent** and stays the fallback under the 2026-10-20 conditions.
2. **Weekend candles:** report the live path's handling first, and the study applies the identical treatment. With no explicit live rule, propose folding into the following Monday as a spec change for review. **No implementation until approved.**
3. **Seal embargo:** the 2021-04-25 Sunday candle and anything within one trading day of the seal belong to neither side.
4. **Census correction:** appended, dated, marked INFERRED; no in-place rewrites.
5. **Run §3 items 3 and 4 on OANDA STUDY data. No study builds on this data until they pass.**

**What was done before any price was fetched:**
- **Live weekend handling: no explicit rule.**
  - `oanda_feed.py:249-251` drops only incomplete candles, so a weekend candle would enter the indicators as an ordinary bar.
  - `regime_detection.py:750-755` (`is_trading_day`) and `shadow_signals.py:395-413` (`_h4_bar_opens`) treat Saturday and Sunday as non-existent.
  - The live feed serves none: 0 weekend-session candles in 30,810 cached bars for 2022–2026.
  - **Proposal written:** docs/specs/study_weekend_candle_spec.md (PROPOSED).
    - Sunday-session candles fold into Monday per the ruling.
    - **Open question raised:** Saturday-session candles are Friday after-close quotes (Fri 17:00 NY), not a Sunday open. The literal rule would make Monday's open a Friday-evening price. The spec recommends dropping them and asks for a ruling.
- **Embargo recorded** in data_map_spec §11.2.
  - It covers one trading day on each side of each seal edge: [2013-12-30T22:00Z, 2014-01-01T22:00Z) and [2021-04-22T21:00Z, 2021-04-26T21:00Z).
  - Effective spans: STUDY → 2013-12-30; SEALED 2014-01-02 → 2021-04-22; USED from 2021-04-27.
  - Applying the margin to both sides of both edges is the reading recorded; narrowing it is a fresh ruling.
- **Census correction appended** to data_map_spec §11.3 and foundation/market_data_facts.md (Corrections). The original text stands.
- **How items 3–4 are run is declared in data_map_spec §11.4, committed before the fetch:**
  - item 3: a seeded fixed sample of 50 days per pair per year; 0.5-pip tolerance; all 900 must pass;
  - item 4: existence on both pairs for all four dates; a sign-only range check against the median of the 20 preceding Tuesday–Friday days; both pairs on the two broad-market dates, GBP/JPY only on the two yen dates.

---

## 2026-10-22 — STUDY conversion gate (data_map_spec §3) on OANDA data: PASS on the weekday grid, both pairs; Mondays re-run after the weekend rule; no study yet

The gate was run 01:09 PDT exactly as declared in data_map_spec §11.4, committed in `340aef0` (01:08:35 PDT) before any price was fetched. Full tables: studies/history_study_gate_report.md; script: studies/history_study_gate_s3.py. Verification numbers only.

- **Span:** STUDY trading days 2005-01-01 → 2013-12-30 (embargo applied).
- **Sealed block:** **0 of 36,522 stored candles fall inside the embargo-plus-sealed block** (a planted 2017 candle is flagged by the same check).
- **Live project:** the hash (690 files) was identical before and after.
- **No weekend-candle rule was applied** (it is PROPOSED, not approved).

| §3 item | GBP_AUD | GBP_JPY |
|---|---|---|
| 1. weekday D1 in [252, 262], every year | PASS, 258–262 | PASS, 258–262 |
| 2. ≥ 99% of sessions with all 6 H4 | PASS, 99.23–100% | PASS, 99.23–100% |
| 3. D1 high/low vs H4 max/min ≤ 0.5 pip, seeded 50/yr | PASS, 450/450, max diff 0.0 pips | PASS, 450/450, max diff 0.0 pips |
| 4. known dates: exists + range above its 20-day Tue–Fri median | PASS (4 exist, 2 range) | PASS (4 exist, 4 range) |

**Supplementary (not gated):**
- Every eligible weekday: 2,334/2,334 per pair.
- Every weekend session against its own H4 bars: 686/686 GBP_AUD, 678/678 GBP_JPY, all 0.0 pips.

**Controls (all behaved as designed):**
- A day planted 0.6 pip off fails, and 0.4 pip off passes.
- One planted day flips the item-3 gate to FAIL (449/450).
- The known-missing 2012-12-25 fails existence.
- A range just below its baseline fails the strict sign check; just above, it passes.

**Status:**
- **The gate PASSES on OANDA's STUDY-span weekday grid.**
- Monday sessions change under any weekend rule, so item 3 is re-run on Mondays once the rule (docs/specs/study_weekend_candle_spec.md, PROPOSED) is approved and built. Weekend sessions' internal consistency suggests a fold stays consistent; that is INFERRED until it is run.
- **No study builds on this data until then.** The §9 frequency count and the exam-split decision remain Stage 3 work.
- Dukascopy attempt 2 stays unspent.

---

## 2026-10-22 — OWNER RULINGS on weekend candles: Saturday sessions DROP; Sunday sessions FOLD into Monday, approved after verifying the live Monday candle; embargo two-sided reading confirmed

**Rulings (owner, 2026-10-22):**
1. Saturday-session candles (open Fri 17:00 New York): **drop** in the study.
2. Sunday-session candles: **fold into the following Monday**, provided current OANDA data first shows a recent Monday daily candle opening at Sunday 17:00 New York and containing the Sunday open. Read-only; three recent Mondays.
3. **Embargo:** the two-sided reading in data_map_spec §11.2 is confirmed as written.
4. After the fold is built, re-run check 3 on every Monday in the study span and report counts per year before and after the rule. **No study starts until the Monday re-check passes.**

**Step-2 verification (read-only, 2026-10-22 01:25 PDT):** CONFIRMED on the Mondays of 2026-10-19, 10-12 and 10-05, both pairs.
- The Monday D1 opens Sunday 14:00 PDT (17:00 New York).
- There are 0 M1 candles from Friday 17:00 to Sunday 17:00 New York.
- The first quote of the week is Sunday 14:04 PDT.
- D1 open = the week's first M1 open, 0.0 pips; D1 high, low and close = the session's M1 max, min and last close, 0.0 pips.
- **Control:** the D1 open against the M1 open one hour later differs by 2.1–30.3 pips.
- The project hash was identical before and after.

**study_weekend_candle_spec.md is now APPROVED.** The status line was updated as directed, the rule is appended as §6, and the original proposal text stands. The Monday re-check's pass criterion is declared in §6 before the conversion is built or run.

---

## 2026-10-22 — Weekend-candle rule built; Monday re-check PASS on both pairs. The OANDA STUDY data is ready for a pre-registered study

**Built:**
- `studies/history_study_convert.py`, the rule exactly as approved in study_weekend_candle_spec.md §6: Saturday sessions dropped; Sunday sessions folded into the next weekday session with Sunday open, combined high/low, target close and target timestamp; an error if there is no target. It is a pure function and is never imported by the live path.
- **Gate 1:** 12 tests in `tests/test_history_study_convert.py`. They cover Sunday-only, Saturday-only, both, 2011-style continuous weekends, a holiday Monday, a missing first Monday slot, no target, folded-Monday consistency, inputs unmodified, and DST labelling.
- **Six mutants each killed:**

  | Mutant | Tests failing |
  |---|---|
  | Saturday folded like Sunday | 2 |
  | target keeps its own open | 6 |
  | Sunday close kept | 6 |
  | fold backwards | 7 |
  | H4 folded into the last slot | 5 |
  | Sunday dropped instead of folded | 6 |

  Each mutant was confirmed applied and confirmed reverted byte-identical, and the clean tests passed 12/12 with no bytecode.
- **Mutation-run correction:** the first mutation pass used `git checkout` to revert an untracked file. The revert failed and the mutants stacked, so only M1 of that pass was valid. It was discarded and redone with copy-based reverts, verified per mutant.

**Monday re-check** (2026-10-22 01:28 PDT, the criterion committed in `096be86` before the build). Inputs: the stored STUDY candles from the §3 gate fetch. Full tables: studies/history_study_monday_recheck_report.md.

| | GBP_AUD | GBP_JPY |
|---|---|---|
| Sunday sessions folded (D1 / H4 candles) | 420 (420 / 771) | 420 (420 / 710) |
| Saturday-session candles dropped (D1 / H4) | 266 / 480 | 258 / 453 |
| Mondays passing check 3, before → after | 468/468 → 468/468, 0.0 pips | 468/468 → 468/468, 0.0 pips |
| Weekend candles left | 0 | 0 |
| D1 rows/yr after (items 1–2 still pass) | 258–262 | 258–262 |
| **Control:** half-built fold (D1 folded, H4 not) | 162 of 468 Mondays fail | 135 of 468 Mondays fail |

- **Short holiday Mondays** (2006-12-25, 2007-01-01) were listed and untested, as declared. The one that received a fold (GBP_AUD 2006-12-25) is consistent at 0.0 pips (supplementary).
- **The fold counts match the 2026-10-22 timestamp census exactly:** 420 Sunday-session D1 per pair; 771/710 Sunday H4; 266/258 Saturday D1; 480/453 Saturday H4.

**Status:** PASS on both pairs, by the declared criterion. Together with the §3 gate, the converted OANDA STUDY data (2005-01-01 → 2013-12-30) now meets every data-side condition in data_map_spec. **A study still needs its own pre-registration, starting with the §9 frequency count.** The live project hash was identical before and after (verified against the pre-check snapshot).

---

## 2026-10-29 — Weekly range study (exploratory, USED span): no directional weekly tendency; volatility clusters

The owner asked what happens in weeks of 200+ pips versus under 200 on the weekly timeframe. It was run on the USED span (learning only, never proof): weeks of 2021-05-03 → 2026-08-31, 279 per pair, OANDA mid weekly candles checked against their daily candles (279/279 agree within 0.5 pip). The untouched 2005–2013 STUDY data stays fresh for confirmation. Full numbers: studies/weekly_range_study_report.md; script: studies/weekly_range_study.py.

- **Split:** 200+ pip weeks were 80% of GBP/AUD weeks and 88% of GBP/JPY weeks.
- **Volatility clusters (real):** after a 200+ week, the next was 200+ 83% / 90% of the time; after a quieter week, 71% / 76%.
- **No direction persistence:** next-week continuation was 46–60% in every group, every confidence interval spanning 50%.
- **Weekly shape matches a random walk:** trend vs indecision weeks, close location, extremes on Monday or Friday, and Monday agreeing with the week. This was checked against a directionless random walk, including a version weighted by each weekday's real activity.
  - **Control:** the simulation reproduces the closed-form random-walk values (59% for the high on Monday or Friday; 65% for Monday agreeing with the week).
  - **Borderline only:** GBP/AUD extremes set midweek, 21% (CI 16–26) vs 15.7% expected; GBP/JPY Monday agreement, 60% (CI 54–66) vs 64.3%. Among about 100 comparisons, these are consistent with chance.
- **GBP/JPY's up-skew** (58% up-closing big weeks; 40% of weekly lows on Monday) matches the pair's 2021–26 rise, a regime and not a weekly habit.
- **Guard:** OANDA stamps a weekly candle at the previous Friday 17:00 New York. The study's first window assumed a Sunday stamp; the post-receipt guard aborted the run before anything was stored, and the window was corrected. No embargoed, sealed or forward week was used.
- **Status:** INFORMED PRIOR at most. The candidate hypotheses for a pre-registered 2005–2013 test are listed in the report.

---

## 2026-10-29 — PRE-REGISTRATION: carry after a quiet week (GBP/JPY and GBP/AUD), 2005–2013 STUDY data

Owner direction 2026-10-29: test both pairs, thoroughly. **No 2005–2013 outcome has been computed at this commit.**

**Committed together (sha256):**
- spec `docs/specs/carry_quiet_week_spec.md`: `5dd3033c856493ced8779fde1505e6ae8e4cc990b38e191e588ba14f82c3cc4d`
- runner `studies/carry_quiet_week_test.py`: `36c2c3c45fb415a3c1a7c2c00a5a687a421aa9038929f4cf2a5fc281b14e2d92`
- rates `studies/policy_rates_2003_2014.json`: `5df23e1891630678f2c10184ba8b261498d8a56193a6cc81710f6a83d6a6eacf`

**The test in brief** (the spec is binding):
- **Rule:** after a week quieter than its previous 26-week median, hold the carry side Monday open → Friday close the next week. That is long GBP/JPY and short GBP/AUD, from the rates table each week.
- **Costs:** era spreads plus 6 days of financing at the rate gap less 1% a year.
- **Measure:** typical-week units.
- **Pass:** a one-sided 95% bootstrap lower bound > 0 (Šidák for two cells) **and** the mean without the best week > 0.
- **REFUTED** if mean ≤ 0. **INCONCLUSIVE** otherwise.

**Power, stated before the run:** about 222 trades per pair can detect about +0.11–0.12 typical-week units, roughly 30–40 pips a week. Carry alone (about 10 pips a week) is below that, so a small real effect most likely reads INCONCLUSIVE.

**Rates sources:**
- Bank of England Bank Rate table and RBA cash rate table, fetched and parsed 2026-10-29, page checksums in the rates file.
- Bank of Japan overnight call rate target: dates confirmed in the BoJ's own documents (July 13–14 2006 → 0.25%; Feb 20–21 2007 → 0.5%; Oct 31 2008 → 0.3%; Dec 18–19 2008 → 0.1%), held at 0.1% thereafter (conservative).
- FRED and the BoJ statistics portal were unreachable, so they were not used.

**Self-test of the test machinery:** `SELFTEST OK`.
- A zero edge passed the bound in 14 of 300 simulated runs (about 5%, as intended).
- **Seven mutants each made it fail:** weakened bar, outlier rule removed, financing sign flipped, quiet test inverted, normaliser shifted a week, carry side reversed, markup ignored.
- **Before that:** the first self-test missed the weakened bar and the removed outlier rule, and a later version missed the shifted normaliser. The decision rule was extracted and tested at its boundaries, and the hand-computed case was rebuilt with rising ranges, before this commit.

**data_map_spec §11.5** records the owner ruling that the STUDY span also tests this hypothesis.

---

## 2026-10-29 — carry after a quiet week: counts stage (before any outcome)

Run 2026-10-29 23:51 PDT, after pre-registration commit `55cd404`. **Counts only; no outcome computed.**

| | GBP/JPY | GBP/AUD |
|---|---|---|
| Weeks (2005-01-03 → 2013-12-30) | 470, 1 excluded (< 3 sessions) | 470, 1 excluded |
| Weeks with 26 weeks of history and a next week | 442 | 442 |
| **Quiet-week trades** | **233** | **224** |
| Side held (from the rates table) | long, every week | short, every week |
| Weekend rule applied | 420 Sundays folded, 258 Saturdays dropped | 420 folded, 266 dropped |

- **Trades per year:** GBP/JPY 10, 30, 19, 25, 36, 34, 28, 28, 23; GBP/AUD 10, 29, 18, 26, 41, 26, 25, 33, 16 (2005 → 2013).
- **The N is in line with the power plan** (about 222).
- **Data checksums** recorded for the full stage:
  - GBP_JPY_D `ca160240…`, GBP_JPY_H4 `f06892d1…`
  - GBP_AUD_D `661a9d49…`, GBP_AUD_H4 `a59db994…`
  - full values in the run's `data_hashes.json`
- **Cross-check against the 2026-10-22 gate fetch: NOT CHECKED.** Those files no longer exist. The weekend-rule counts, computed independently, equal the 2026-10-22 census exactly.
- The live project hash was identical before and after.


---

## 2026-10-29 — RESULT: carry after a quiet week — GBP/JPY REFUTED, GBP/AUD INCONCLUSIVE (2005–2013 STUDY data)

Run once, 2026-10-29 23:52 PDT, under pre-registration `55cd404` and on the data recorded at the counts stage `e568867` (sha256 verified by the runner). The live project hash was identical before and after. **Verbatim output:**

# Carry after a quiet week — pre-registered test result (2005–2013 STUDY data)

Spec: docs/specs/carry_quiet_week_spec.md. Run once, on the candles recorded at the counts stage (sha256 verified). Units: **typical-week ranges** (a trade's pips divided by the median weekly range of the 26 weeks before it), the primary measure; pips are secondary.

## GBP/JPY: **REFUTED**

- Side held: long GBP/JPY in 233 of 233 weeks (the higher-yielding currency bought).
- **Primary (typical-week units):** N 233; mean -0.003; one-sided 95% lower bound -0.075 (normal-approximation check -0.076); median -0.033; mean without the best week -0.012; winning weeks 48%
- Pips: N 233; mean -13.701 pips; one-sided 95% lower bound -45.077 pips (normal-approximation check -45.181); median -10.317 pips; mean without the best week -17.475 pips; winning weeks 48%
- Average trade in pips: price move -11.9, spread −5.5, financing +3.7, net -13.7
- Worst drawdown: -20.38 typical-week ranges (-8984 pips); worst week -1126 pips; longest losing run 7 weeks

**Secondary (never changes the verdict):**

- Carry in every week (no quiet filter): N 442; mean +0.014; one-sided 95% lower bound -0.047 (normal-approximation check -0.047); median +0.033; mean without the best week +0.008; winning weeks 52%
- Carry after non-quiet weeks: N 209; mean +0.033; one-sided 95% lower bound -0.069 (normal-approximation check -0.067); median +0.121; mean without the best week +0.022; winning weeks 57%
- Does 'quiet' add anything? Quiet minus non-quiet mean -0.037, 90% interval -0.162 to +0.088
- 2005-01 to 2008-06 (before the crisis): N 74, mean +0.080, winning weeks 57%
- 2008-07 to 2009-06 (the crisis): N 30, mean -0.118, winning weeks 40%
- 2009-07 to 2013-12 (after): N 129, mean -0.025, winning weeks 44%
- Net pips by year: 2005 +1406 (10), 2006 +2091 (30), 2007 -2345 (19), 2008 -2991 (25), 2009 -653 (36), 2010 -1099 (34), 2011 -1098 (28), 2012 +520 (28), 2013 +977 (23)
- Cost sensitivity, financing markup 0%: mean +0.004, lower bound -0.069
- Cost sensitivity, financing markup 2%: mean -0.011, lower bound -0.084
- Cost sensitivity, spread x1.5: mean -0.011, lower bound -0.084

## GBP/AUD: **INCONCLUSIVE**

- Side held: short GBP/AUD in 224 of 224 weeks (the higher-yielding currency bought).
- **Primary (typical-week units):** N 224; mean +0.033; one-sided 95% lower bound -0.035 (normal-approximation check -0.035); median +0.036; mean without the best week +0.025; winning weeks 51%
- Pips: N 224; mean +30.241 pips; one-sided 95% lower bound +1.083 pips (normal-approximation check +0.610); median +14.632 pips; mean without the best week +26.329 pips; winning weeks 51%
- Average trade in pips: price move +34.6, spread −8.7, financing +4.3, net +30.2
- Worst drawdown: -9.38 typical-week ranges (-3010 pips); worst week -616 pips; longest losing run 7 weeks

**Secondary (never changes the verdict):**

- Carry in every week (no quiet filter): N 442; mean -0.008; one-sided 95% lower bound -0.073 (normal-approximation check -0.073); median +0.042; mean without the best week -0.015; winning weeks 51%
- Carry after non-quiet weeks: N 218; mean -0.049; one-sided 95% lower bound -0.164 (normal-approximation check -0.162); median +0.061; mean without the best week -0.064; winning weeks 51%
- Does 'quiet' add anything? Quiet minus non-quiet mean +0.082, 90% interval -0.046 to +0.213
- 2005-01 to 2008-06 (before the crisis): N 78, mean +0.058, winning weeks 54%
- 2008-07 to 2009-06 (the crisis): N 27, mean +0.091, winning weeks 48%
- 2009-07 to 2013-12 (after): N 119, mean +0.003, winning weeks 50%
- Net pips by year: 2005 +871 (10), 2006 -309 (29), 2007 +133 (18), 2008 +2814 (26), 2009 +3246 (41), 2010 +1558 (26), 2011 +887 (25), 2012 -814 (33), 2013 -1612 (16)
- Cost sensitivity, financing markup 0%: mean +0.041, lower bound -0.027
- Cost sensitivity, financing markup 2%: mean +0.025, lower bound -0.041
- Cost sensitivity, spread x1.5: mean +0.022, lower bound -0.044

**Reading** (the verdicts above are the pre-registered ones; nothing here changes them):
- **GBP/JPY: REFUTED.** Buying after quiet weeks lost money on average, and the 2021–2026 observation did not survive conditions it was not found on.
  - Carry in every week was flat too (+0.014, bound −0.047).
  - The losses concentrate in 2007–2008, the carry unwind; the worst week was −1,126 pips.
- **GBP/AUD: INCONCLUSIVE.** The mean is positive (+0.033 typical-week units, about +30 pips a week after costs), but the 95% lower bound is −0.035.
  - The pip-measured bound is slightly positive (+1.1 pips), but pips were declared secondary in advance. The pip total is carried by the volatile 2008–09 weeks (+6,060 of the net), which risk-equal sizing removes. Reporting the better-looking measure would be the forking path the pre-registration exists to stop.
  - The quiet filter's advantage over non-quiet weeks (+0.082) has an interval spanning zero.
  - This effect is below what 224 trades can resolve, as the power statement warned.
- **Status:** GBP/JPY carry-after-quiet REFUTED on 2005–2013. GBP/AUD INCONCLUSIVE; it is not a candidate for the sealed exam on this evidence. Both are recorded in foundation/research_findings.md (R33, R34).

## 2026-11-01 — INCIDENT: protected live file broken overnight (restored); FINDING: the macro read was never machine-readable

**Incident (I31).** At 2026-11-01 00:03:54 PDT `levels_context.py` in the live checkout (`main`) was modified: line 98 `result["prev_week_high"]` became `result["n]`, a syntax error. Origin unknown (no framework agent session was running; it reads as a stray keystroke over a selection). Observed:
- `git status` showed `M levels_context.py`; `ast.parse` → `SyntaxError: unterminated string literal (detected at line 98)`.
- The broken copy and its diff were saved outside the repo, then the file was restored with `git checkout`. After the restore: status clean, the file parses, and the full suite on the live checkout gave `888 passed, 2 deselected` with the conftest evidence guard passing.
- Impact had it run: `entry_confirmation.py:177-182` imports the module inside `try/except Exception`, so the brief would not have crashed. The 15-minute key-level check would have gone quietly unavailable. No scheduled run executed while the file was broken (next brief 02:30 PDT).
- Control added: the live guard alerts when tracked code in the live checkout differs from `main` (branch `feat/live-code-guard`, entry to follow).

**Finding (I32).** `setup_check.parse_storylines()` on the live `storylines.md` returns `views: {}` (no GBP, AUD or JPY bias). A control file with `GBP: neutral` / `AUD: bullish` / `JPY: bullish` lines returns all three. So the pre-trade FUEL check could never return AGREES or CONFLICTS; the journal holds only `neutral` (4) and `stale` (5). `storylines.md` has also been stale since its 2026-09-10 approval. Proposed remedy (owner's choice, docs/driver_coverage_proposal.md §7): add one machine-readable line per currency to the file; no code change.

**Also recorded today:** `docs/capability_inventory.md` (what the framework covers and doesn't, for the owner's goal of being sharp in the markets) and `docs/driver_coverage_proposal.md` (four agent reviews of what moves GBP/JPY and GBP/AUD, and a staged plan). Both are proposals; nothing in them changes the tradeable path.

## 2026-11-01 — Live guard: alert when live code differs from main (incident I31 control)

**Change** (`scripts/live_guard.sh`, free zone; branch `feat/live-code-guard`). On every scheduled run, after the branch check, the guard lists tracked `*.py` / `*.sh` files under the project folder that differ from HEAD (staged or not). If there are any, it writes `##ALERT## LIVE CODE MODIFIED: …` to the day log and sends an ALERT naming each file, marked `(does not parse)` or `(deleted)` where true. Docs, ledgers, untracked files and files elsewhere under `$HOME` never alert. The branch check no longer returns early, so both alerts can fire on one run.

**Gate 1 — tests** (`tests/test_live_guard.py`, 8 new, in repos whose git root sits above a project folder with a space in its name, as in production):
- Before the change: 5 of the new alert tests failed against the old guard.
- After: `tests/test_live_guard.py` + `tests/test_shell_syntax.py` 24 passed.
- Rule 12 (should it reach the owner): alerts on unparseable, parseable, staged, shell and deleted edits; silent on a clean checkout, a `storylines.md` edit, a change outside the project, and an untracked `.py`; repeats every run while the condition persists (deliberate, as the branch alert does); fires next to the branch alert when both hold.

**Mutation tests** (each applied, confirmed by `cmp`, reverted, confirmed identical, suite re-passed 13/13):

| Mutant | Caught by |
|---|---|
| M1 drop `--relative` | unparseable test (paths break) |
| M2 drop the `*.py`/`*.sh` filter | doc test |
| M3 drop the parse check | unparseable test |
| M4 diff unstaged only (no `HEAD`) | staged test |
| M5 code guard disabled | 5 alert tests |
| M6 include untracked files | untracked test |
| M7 drop the `(deleted)` mark | deleted test |
| M8 restore the old early return on main | 5 alert tests |
| M9 root-relative pathspec, `--relative` kept | **survived: equivalent mutant**, `--relative` alone keeps out-of-project files out |
| M10 root-relative pathspec and no `--relative` | outside-project test (+1) |

**Gate 2 — reality** (real git, real files, `/bin/bash` 3.2, notify stubbed so nothing was posted):
- Real live checkout (clean): no output, no log written, project hash identical before and after.
- Throwaway worktree of `main` with the actual broken `levels_context.py` from 00:03 replayed:
  `##ALERT## LIVE CODE MODIFIED: Live code differs from main: levels_context.py (does not parse). Scheduled runs are executing unreviewed edits. …`
  (A `LIVE BRANCH` alert fired alongside it only because the probe worktree's branch could not be named `main`.)

**Full suite on the branch (2026-11-01):** 890 passed, 7 skipped (the gitignored ledgers are absent in a worktree), 2 deselected.

**Gate 3 — PENDING LIVE CONFIRMATION:** the first scheduled run after merge executes the new guard on the clean live checkout and stays silent (no `LIVE CODE MODIFIED` line in that day's log). A real alert from launchd on a real edit has not happened and should not be manufactured.

## 2026-11-01 — Owner decisions on the driver-coverage proposal; storylines format test

**Owner decisions** (docs/driver_coverage_proposal.md §7, answered 2026-11-01):
1. Storylines: the owner adds one machine-readable line per currency (`GBP: neutral`, bullish / bearish / neutral) under each heading of `storylines.md`. No code change.
2. Live instrument probe: approved, one read-only instruments listing plus history depth, through `scripts/reality_run.py`.
3. US events: context first in the brief; the frozen shadow `news_window` stamp stays on own-currency events. Gating is decided later from evidence.
4. Next study: how US events (FOMC, US CPI, jobs report) move GBP/JPY and GBP/AUD.

**Test** (`tests/test_storylines_format.py`, free zone):
- The template given to the owner parses to all three views.
- The live file must carry all three views once approved on or after 2026-11-01. The current file (approved 2026-09-10) skips with the I32 reason.
- Positive control: the real file re-dated to 2026-11-08 without the lines fails the check.
- Mutation: making the check vacuous (`missing = set()`) → the control fails (1 failed); reverted → 2 passed, 1 skipped.

**Gate 3 — PENDING LIVE CONFIRMATION:** the first `storylines.md` approved after 2026-11-01 passes `test_live_storylines_is_machine_readable`, and a real `setup_check` run prints FUEL AGREES or CONFLICTS.

## 2026-11-01 — Instrument probe (owner-approved): the account offers currency pairs only

**What ran.** `studies/instrument_probe.py`, read-only: the account's instrument list, then the first and latest daily candle of each target present. Through `scripts/reality_run.py --code <worktree> script …`, twice (the second after a `sys.path` convention fix): both exit 0, `project files : UNCHANGED (verified by hash)`, stderr empty, second output byte-identical to the first. Verbatim output: `studies/instrument_probe_report.md`.

**Gate 1.** `tests/test_instrument_probe.py`, canned responses: availability per target, the account id and key never printed, financing read when present, an HTTP failure raises rather than printing a report. Mutants caught: unmasked id (1 failed), swallowed HTTP errors (1 failed), skipped availability check (2 failed); reverted → 3 passed.

**Result (VERIFIED, REALITY GATE):**
- `Instruments offered by type: CURRENCY 68`. No yields, equity indices, metals or commodities: all 14 non-currency targets `NOT OFFERED`.
- USD_JPY, GBP_USD, AUD_USD daily history `2002-05-06 → 2026-10-29`; USD_CNH `2011-02-06 → 2026-10-29`.
- Financing today: `GBP_JPY: longRate 0.016 shortRate -0.0366`; `GBP_AUD: longRate -0.0189 shortRate -0.0018`. Read as annual rates paid to (+) or by (−) the holder (INFERRED convention). This matches policy-rate gaps less a markup of about 0.9–1.0 point (BoE 3.75 − BoJ 1.25 = 2.5 → +1.6; BoE 3.75 − RBA 4.60 = −0.85 → −1.89). The rates in that check come from web reports.

**Consequences.** Cross-market context from OANDA is limited to the USD legs; yields, VIX and commodities need outside sources with their own feed validation. The US-event study can use USD legs and both crosses on one feed.

## 2026-11-01 — PRE-REGISTRATION: do scheduled US releases move GBP/JPY and GBP/AUD? (2005–2013 STUDY data)

**Owner direction:** driver-coverage proposal §7, decision 4. The study decides whether US events (FOMC, CPI, the jobs report) belong in the news gate; until then they come in as context only (decision 3).

**Committed together, before any 2005–2013 outcome is computed:**

| File | sha256 |
|---|---|
| `docs/specs/us_event_reaction_spec.md` | `932a22d99b79dc514d9df01224b90260b591f5a7d8c4dd4c51dff35b8841841f` |
| `studies/us_event_reaction_test.py` | `045067698abfb861d11c0f475d72a0f21255086f18be13fabbcc3f6c35399c49` |
| `studies/us_events_2005_2013.csv` | `0f898806a110f5a4c1c063bd772e93102085eb743b47069d95f788103fed8aa2` |
| `studies/us_events_sources.json` | `1c2aadab293095ae8bc7643af890b408701187e3c778a38c2d5576950f813f8f` |

**The test (spec §3–§5).**
- Six cells: {GBP_JPY, GBP_AUD} × {FOMC, CPI, NFP}.
- Primary measure per event: the paired range-ratio effect. That is the day's range over the median of the 20 prior days, minus the mean of same-weekday, event-free control days within ±28 days.
- Bounds: Bonferroni one-sided bootstrap at α = 0.05/6.
- Verdicts: MATERIAL if the lower bound ≥ +0.10; NOT MATERIAL if the upper bound < +0.10; otherwise INCONCLUSIVE.
- Power stated in advance: MATERIAL needs an observed mean of roughly +0.23 to +0.26; a modest real effect most likely reads INCONCLUSIVE.

**Event table (VERIFIED in this session, independently of the agent that compiled it):**
- 294 rows: 72 scheduled FOMC, 6 unscheduled FOMC, 108 CPI, 108 NFP. 313 source pages, all hashes re-verified (0 mismatches), first in the scratchpad and again in the persistent archive `~/intel_study_archives/us_events_2005_2013/`.
- Checks: no duplicates; exactly one CPI and one NFP in each of the 108 months; the only weekend row is the Sunday 2010-05-09 21:15 ET action, which maps to the Monday session.
- 8 dates spot-checked against the raw pages, all found: 2013-10-22 NFP and 2013-10-30 CPI (shutdown shifts), 2010-07-16 CPI, 2006-04-07 NFP, and FOMC on 2008-12-16, 2005-06-30, 2012-09-13 and 2007-06-28. The negative control (the pre-shutdown 2013-10-04 NFP date) is absent from both the page and the table.
- The agent's cross-checks, not re-run here: NFP vs ALFRED PAYEMS 108/108; CPI within ALFRED CPIAUCSL vintages 108/108; FOMC vs the Fed press listing 70/70 (2006–2013); all 21 fed funds target changes on a table date.
- 62 FOMC rows have no release time. Scheduled statements are all daytime, so the session is the release date either way (INFERRED from the meeting format; times stated where a Fed page gives them).

**Self-test:** `SELFTEST OK` (20 checks). 12 mutants, each caught (FAIL count ≥ 1, no crash): day inside its own normaliser; event days as controls; any-weekday controls; a 35-day window; no Bonferroni; a strict threshold; round trip at d+3 only; UTC date instead of session date; embargo check removed; unscheduled kept as a cell; unscheduled not excluded from controls; no evening roll. Reverted identical, caches cleared, `SELFTEST OK` again. The self-test also runs in the suite (`tests/test_us_event_reaction_selftest.py`).

**Full suite on the branch:** 896 passed, 8 skipped (the gitignored ledgers are absent in a worktree), 2 deselected.

**Next:** the `counts` stage through `scripts/reality_run.py` (counts only, no outcome), recorded here before `full` runs once.

## 2026-11-01 — US release reactions: counts stage (before any outcome)

Run: `scripts/reality_run.py --code <worktree> script studies/us_event_reaction_test.py counts <.env> ~/intel_study_archives/us_event_reaction_data`. Exit 0, `project files : UNCHANGED (verified by hash)`, stderr empty, 424 OANDA requests through the embargo-guarded fetch. Counts only, no ratio, range or effect printed.

| Cell | Events in table | Matched | Dropped | Mean controls per event |
|---|---|---|---|---|
| GBP_JPY FOMC | 72 | 72 | 0 | 7.38 |
| GBP_JPY CPI | 108 | 107 | 1 warm-up (Jan 2005) | 6.66 |
| GBP_JPY NFP | 108 | 107 | 1 warm-up (Jan 2005) | 6.17 |
| GBP_AUD FOMC | 72 | 72 | 0 | 7.38 |
| GBP_AUD CPI | 108 | 107 | 1 warm-up | 6.66 |
| GBP_AUD NFP | 108 | 107 | 1 warm-up | 6.17 |

- Trading days: 2,343 per pair (2005-01-03 → 2013-12-30). Weekend rule: GBP_JPY 420 Sundays folded, 258 Saturdays dropped; GBP_AUD 420 folded, 266 dropped. That matches the carry study's counts stage on the same pipeline exactly (2026-10-29).
- Data hashes (the `full` stage refuses any other file): GBP_JPY_D `ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a`, GBP_JPY_H4 `f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764`, GBP_AUD_D `661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939`, GBP_AUD_H4 `a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77`; event table `0f898806…8aa2`.
- Every N is at or near the power statement's assumption (72 / 108; about 7 controls). The power statement stands unchanged.

## 2026-11-01 — RESULT: US release reactions — all six cells INCONCLUSIVE (2005–2013 STUDY data)

Run once: `scripts/reality_run.py --code <worktree> script studies/us_event_reaction_test.py full ~/intel_study_archives/us_event_reaction_data studies/us_event_reaction_result.md`. Exit 0, `project files : UNCHANGED (verified by hash)`, stderr empty. The data and event-table hashes were checked against the counts stage by the runner before computing. Verbatim output:

### US release reactions — pre-registered test result (2005–2013 STUDY data)

Spec: docs/specs/us_event_reaction_spec.md. Bonferroni α per cell 0.0083 (one-sided), threshold +0.10, 20000 resamples.

#### GBP_JPY

##### FOMC: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 72; mean effect +0.096; one-sided bounds [-0.042, +0.242]; median -0.012; SD 0.509; dropped {'no_session': 0, 'warm_up': 0, 'no_control': 0}
- Event-day mean ratio 1.182 vs control mean 1.087

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.065, median -0.107
- Round trip within 3 days: event days 42% (N 72) vs control days 43% (N 530)
- 2005-01 to 2008-06 (before the crisis): N 28, mean effect +0.098
- 2008-07 to 2009-06 (the crisis): N 8, mean effect +0.080
- 2009-07 to 2013-12 (after): N 36, mean effect +0.097

##### CPI: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 107; mean effect +0.062; one-sided bounds [-0.079, +0.216]; median -0.054; SD 0.638; dropped {'no_session': 0, 'warm_up': 1, 'no_control': 0}
- Event-day mean ratio 1.156 vs control mean 1.093

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.032, median -0.083
- Round trip within 3 days: event days 40% (N 107) vs control days 45% (N 712)
- 2005-01 to 2008-06 (before the crisis): N 41, mean effect +0.117
- 2008-07 to 2009-06 (the crisis): N 12, mean effect +0.121
- 2009-07 to 2013-12 (after): N 54, mean effect +0.008

##### NFP: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 107; mean effect +0.093; one-sided bounds [-0.015, +0.207]; median +0.016; SD 0.478; dropped {'no_session': 0, 'warm_up': 1, 'no_control': 0}
- Event-day mean ratio 1.170 vs control mean 1.078

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.066, median +0.005
- Round trip within 3 days: event days 47% (N 107) vs control days 45% (N 659)
- 2005-01 to 2008-06 (before the crisis): N 41, mean effect -0.012
- 2008-07 to 2009-06 (the crisis): N 12, mean effect -0.032
- 2009-07 to 2013-12 (after): N 54, mean effect +0.200

- Unscheduled FOMC actions (descriptive): 2007-08-10 ratio 1.69; 2007-08-17 ratio 3.05; 2008-01-22 ratio 1.79; 2008-03-11 ratio 1.65; 2008-10-08 ratio 1.91; 2010-05-10 ratio 2.72

#### GBP_AUD

##### FOMC: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 72; mean effect +0.177; one-sided bounds [+0.027, +0.369]; median +0.144; SD 0.602; dropped {'no_session': 0, 'warm_up': 0, 'no_control': 0}
- Event-day mean ratio 1.272 vs control mean 1.095

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.047, median -0.012
- Round trip within 3 days: event days 44% (N 72) vs control days 42% (N 531)
- 2005-01 to 2008-06 (before the crisis): N 28, mean effect +0.077
- 2008-07 to 2009-06 (the crisis): N 8, mean effect +0.212
- 2009-07 to 2013-12 (after): N 36, mean effect +0.248

##### CPI: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 107; mean effect +0.022; one-sided bounds [-0.072, +0.122]; median -0.016; SD 0.427; dropped {'no_session': 0, 'warm_up': 1, 'no_control': 0}
- Event-day mean ratio 1.098 vs control mean 1.076

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.026, median -0.048
- Round trip within 3 days: event days 44% (N 107) vs control days 43% (N 713)
- 2005-01 to 2008-06 (before the crisis): N 41, mean effect +0.078
- 2008-07 to 2009-06 (the crisis): N 12, mean effect +0.012
- 2009-07 to 2013-12 (after): N 54, mean effect -0.017

##### NFP: **INCONCLUSIVE**

- **Primary (range ratio, paired):** N 107; mean effect +0.076; one-sided bounds [-0.043, +0.208]; median -0.023; SD 0.544; dropped {'no_session': 0, 'warm_up': 1, 'no_control': 0}
- Event-day mean ratio 1.117 vs control mean 1.041

**Secondary (never changes the verdict):**

- Close-to-close move, paired: mean effect +0.001, median -0.059
- Round trip within 3 days: event days 37% (N 107) vs control days 52% (N 659)
- 2005-01 to 2008-06 (before the crisis): N 41, mean effect -0.069
- 2008-07 to 2009-06 (the crisis): N 12, mean effect +0.109
- 2009-07 to 2013-12 (after): N 54, mean effect +0.179

- Unscheduled FOMC actions (descriptive): 2007-08-10 ratio 1.28; 2007-08-17 ratio 3.62; 2008-01-22 ratio 1.15; 2008-03-11 ratio 1.36; 2008-10-08 ratio 6.18; 2010-05-10 ratio 2.20


**Reading** (the verdicts above are the pre-registered ones; nothing here changes them):
- **All six cells INCONCLUSIVE.** Scheduled US releases do not reliably widen GBP/JPY or GBP/AUD days by 10% or more of a normal day, and that size of effect cannot be ruled out either.
  - The means are positive (+0.02 to +0.18), but the medians are near zero (−0.05 to +0.14). A typical release day is about a normal day; a minority of big days carries the mean.
  - This fits the dollar partly cancelling in a cross.
- **Closest call: GBP/AUD on FOMC days.** Mean +0.177, Bonferroni lower bound +0.027 (above zero, below +0.10), median +0.144. It is the cell to re-examine if more data is ever opened.
- **Unscheduled FOMC actions** were large on both pairs (1.15–6.18× a normal day), but they cannot be gated in advance.
- **Round trips** (secondary): event days give back their move about as often as control days, 37–47% against 42–52%. The exception is GBP/AUD on NFP days, 37% against 52%.
- **Consequence for the plan:** owner decision 3 stands. US events come into the brief as context only (proposal step 5). A US gate is not justified on this evidence.
- **Status:** recorded as R35 (GBP/JPY) and R36 (GBP/AUD) in foundation/research_findings.md; tested-hypothesis count 34 → 36.

## 2026-11-01 — Shadow ledger cost re-grade: parameters fixed before the run (proposal step 3)

`studies/shadow_cost_regrade.py` (sha256 `6cb2e4c91ad600756c3070789f7600008b36946ab3521ee2f38ef4dc3be51fdf`), committed before it is run. It is read-only: it never edits the ledger or `r_multiple` (trap T6), and adjusted R is shown beside raw R, never instead of it.
- **Episodes:** the live `shadow_signals.graded_episodes` (graded, valid, non-excluded, first fire per 30-bar episode). All graded rows are also costed.
- **Candidates:** EARLY_MOMENTUM_v2, THRUST_PULLBACK, MOMENTUM_JOIN. Retired EARLY_MOMENTUM v1 is out: retired, and its rows are older than the grader's 500-bar window.
- **Positive control:** every graded row's raw R is recomputed from freshly fetched H4 bars with the grader's rule. A mismatch with the ledger beyond 0.005 aborts the run.
- **Spread:** 3.0 pips round trip; sensitivity 4.0.
- **Financing:** OANDA's quoted rates on 2026-11-01 applied to the whole period. That is an approximation; the endpoint keeps no history. GBP_JPY long +1.60% / short −3.66%; GBP_AUD long −1.89% / short −0.18%. Sensitivity: every rate 1 point worse.
- **Rollovers:** each 17:00 New York crossed while open, Wednesday ×3. Entry is at the fire bar's close, and a rollover at that instant is not charged. Exit is at the stop-hit bar's open, or the close of bar 30.
- **Self-test:** OK (10 checks). 7 mutants: 6 caught; C7 (UTC instead of New York as the loop's start day) is an equivalent mutant, because aware comparisons make it the same.
- **Full suite on the branch:** see the commit (suite run before commit).

## 2026-11-01 — RESULT: shadow ledger re-graded with costs (read-only; all candidates INSUFFICIENT)

Run: `scripts/reality_run.py --code <worktree> script studies/shadow_cost_regrade.py run …`. Exit 0, `project files : UNCHANGED (verified by hash)`, stderr empty. Full suite on the branch before the parameters commit: 897 passed, 8 skipped, 2 deselected. Verbatim report (`studies/shadow_cost_regrade_report.md`):

### Shadow ledger re-graded with costs (read-only)

Spread 3.0 pips round trip (sensitivity 4.0); financing at OANDA's 2026-11-01 quoted rates (sensitivity: 1 point worse); rollovers at 17:00 New York, Wednesday x3. Raw R is the frozen grader's; adjusted R never replaces it.

Positive control: 28 graded rows; every raw R reproduced from freshly fetched H4 bars to 2 dp (a mismatch would have aborted the run).

#### EARLY_MOMENTUM_v2

- Episodes, raw R (frozen grader): N 4; mean -0.400R; median -0.470R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 4; mean -0.411R; median -0.513R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 4; mean -0.442R; median -0.535R  (INSUFFICIENT: N<20)
- All graded fires (20): mean spread cost 0.025R, mean financing +0.004R, mean nights 6.0

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-18T05:00 | GBP_JPY | LONG | 311 | 7 | -0.55 | -0.010 | +0.021 | -0.539 |
| 2026-09-25T17:00 | GBP_JPY | SHORT | 182 | 7 | -0.39 | -0.016 | -0.080 | -0.487 |
| 2026-10-02T17:00 | GBP_JPY | LONG | 144 | 7 | +0.34 | -0.021 | +0.045 | +0.364 |
| 2026-10-19T09:00 | GBP_JPY | LONG | 83 | 5 | -1.00 | -0.036 | +0.056 | -0.980 |

#### THRUST_PULLBACK

- Episodes, raw R (frozen grader): N 1; mean -0.330R; median -0.330R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 1; mean -0.418R; median -0.418R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 1; mean -0.443R; median -0.443R  (INSUFFICIENT: N<20)
- All graded fires (1): mean spread cost 0.015R, mean financing -0.073R, mean nights 7.0

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-28T05:00 | GBP_JPY | SHORT | 200 | 7 | -0.33 | -0.015 | -0.073 | -0.418 |

#### MOMENTUM_JOIN

- Episodes, raw R (frozen grader): N 2; mean -1.000R; median -1.000R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 2; mean -1.038R; median -1.038R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 2; mean -1.074R; median -1.074R  (INSUFFICIENT: N<20)
- All graded fires (7): mean spread cost 0.049R, mean financing -0.039R, mean nights 3.3

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-28T05:00 | GBP_AUD | LONG | 55 | 1 | -1.00 | -0.054 | -0.018 | -1.072 |
| 2026-10-21T05:00 | GBP_JPY | LONG | 60 | 3 | -1.00 | -0.050 | +0.046 | -1.004 |


**Reading** (descriptive; no verdict changes; the frozen raw R and the futility rule stand as written):
- **The positive control held:** 28 of 28 graded rows were reproduced from fresh bars. The ledger, the feed and the grader agree.
- **Costs move each episode by −0.01R to −0.09R.**
  - Short GBP/JPY pays the most financing, about −0.08R a week.
  - Tight-stop MOMENTUM_JOIN pays about 0.05R in spread.
  - Long GBP/JPY earns carry (+0.02 to +0.06R) that roughly offsets its spread.
- **For the futility checkpoint** (N=20, 90% bound vs +0.15R on raw R): costs of this size make every candidate's real edge smaller than its raw R by about 0.01–0.04R on average (EARLY_MOMENTUM_v2 −0.011R). That should be read beside any raw result near the bar.
- Every candidate is negative before costs and more negative after, at N = 4, 1 and 2 episodes: INSUFFICIENT throughout.

## 2026-11-01 — BUILT, AWAITING TEAM REVIEW: US events in the brief as context only (branch `feat/us-events-context`, NOT merged)

**Spec:** `docs/specs/us_events_context_spec.md`, committed before the build (9fb643f). Protected modules touched: `calendar_fetch.py`, `news_gate.py`, `decision_brief.py`. **Do not merge without team review.**

**Change.**
- `calendar_fetch` keeps HIGH-impact USD rows; at least one GBP/AUD/JPY row is still required.
- `news_gate.us_event_context()` is new and read-only. `check_news_gate` and `PAIR_CURRENCIES` are unchanged.
- The brief gets one `US DATA` line: information only, sanitized against the wrapper's DECISION/ALERT triggers. It says "not checked" unless the calendar is current and carries USD rows.

**Gate 1** (`tests/test_us_events_context.py`, 15 new tests; one listed test changed old → new per spec §3):
- I1/I2: `check_news_gate` is identical with and without USD rows across 60 random calendars × a 47-minute sweep of a feed week × both pairs. That is over 10,000 comparisons, with active, stale and gating branches all exercised.
- I3: the wrapper's own DECISION pipeline (asserted verbatim from `scripts/scheduled_brief.sh`) does not fire on a stand-aside brief carrying a `FED RATE DECISION ##ALERT##` title. Positive control: the unsanitized title does fire it. Nothing is written to stderr.
- I4: the banned-token floor (`_assert_clean`) passes on every rendered state.
- I5: "none" comes only from status `ok`.
- **Mutation:** 9 of 9 caught. USD in `PAIR_CURRENCIES` (2 failed); sanitizer removed (1); "none" for `no_us_rows` (1); USD-only feed accepted (1); medium-impact USD counted (1); USD dropped at fetch (2); line placed above the news note (1); no coverage-end branch (1); past events listed (3). Reverted → 33 passed.
- **Harness note:** the first mutation pass reported "no tests ran" for every mutant. zsh does not word-split an unquoted `$T`, so pytest got one bogus path. It was re-run under `/bin/bash` with the results above. A "no tests ran" line is a failed measurement, not a pass.
- Full suite on the branch: 913 passed, 8 skipped (the gitignored ledgers are absent in a worktree), 2 deselected.

**Gate 2 — REALITY** (all through `scripts/reality_run.py --code <worktree>`; every run exit 0, `project files : UNCHANGED (verified by hash)`, stderr empty):
1. Real brief, worktree with no calendar: `⚠ news calendar missing — event risk unchecked` / `US DATA    not checked — news calendar out of date.`
2. Real brief on a copy of the live `calendar.csv` (last week's file, so stale): `⚠ news calendar stale — event risk unchecked` / `US DATA    not checked — news calendar out of date.`
3. Real ForexFactory fetch into a temp file: `calendar.csv updated: 10 high-impact GBP/AUD/JPY events and 4 US events (context only) through 2026-11-06 16:00 UTC.` The USD rows were Congressional Elections (11-03), and Average Hourly Earnings m/m, Non-Farm Employment Change and Unemployment Rate (11-06 13:30).
   - The real brief against it: `US DATA    none in the next 24 hours.` for both pairs.
   - Against the same file without USD rows: `US DATA    not checked — this calendar carries…`.
   - DECISION / REASON / CONFIDENCE / POSITION identical with vs without USD rows for both pairs: `True`. The market was closed (Sunday), so both briefs stood aside; I1 is the stronger proof.
4. The line from the real fetched calendar at pinned clocks:
   - Thu 18:00 UTC: `Average Hourly Earnings m/m Fri 5:30 AM PST · Non-Farm Employment Change Fri 5:30 AM PST · Unemployment Rate Fri 5:30 AM PST — for information; the framework does not stand aside for US releases.`
   - Mon 18:00 UTC: `Congressional Elections Tue 7:16 AM PST — …`
   - Sat 18:00 UTC: `none before Sat 8:59 PM PST; later days are not in this week's calendar yet.`

**Found along the way (pre-existing, deferred):** with `--code <worktree>`, `reality_run.py brief` reads no calendar. `news_gate._CALENDAR_FILE` is module-relative, so it resolves to the worktree, where `calendar.csv` is gitignored and absent. Earlier `--code` brief runs therefore exercised the "calendar missing" path, visibly marked in the output. A fix (copy the live calendar into the run, or make the path cwd-relative under reality_run) is a separate change.

**Gate 3 — PENDING LIVE CONFIRMATION (after merge only):** the first Sunday calendar fetch after merge writes USD rows; the next brief renders real US events; no DECISION notification is ever sent because of the line.

## 2026-11-01 — CORRECTION: team review of `feat/us-events-context` found two overclaims in the entry above; REQUEST CHANGES

**What was claimed without sufficient evidence (entry above, and the team brief of the same day):**
1. *"Decisions can't change"* (spec I1). False on the fetch side. `calendar_fetch._parse_events` now parses the date of every USD row it keeps and raises on a bad one (calendar_fetch.py:91-94); before the change USD rows were dropped before the date check. One malformed USD row therefore rejects the whole week's feed, the gated GBP/AUD/JPY calendar goes stale, and a stale calendar fails open (I28): news stand-asides stop.
   - Observed 2026-11-01 (pure function, temp cwd, no network): feed = one valid GBP row + one USD row dated `"Tentative"`. Branch → `REJECTED: unparseable event date: 'Tentative'`; main → `parsed 1`. Control: the GBP row alone parses on both.
   - I1's test is also conditional: `check_news_gate` takes staleness from the newest row of any currency, and the test filters out USD rows beyond the own rows' feed week (test_us_events_context.py:98-100). The adversarial reviewer observed a next-week USD row flip `stale` → `active`. It holds only while the feed is one week, which nothing enforces.
2. *"The line cannot trigger a false DECISION alert"* (spec I3, labelled VERIFIED). False.
   - `_us_title` strips `#` after replacing the trigger words (decision_brief.py:460-462). Observed: `_us_title("FED DECI#SION LONG")` → `'FED DECISION LONG'`; `_us_title("AL#ERT")` → `'ALERT'`.
   - The wrapper reacts to more than DECISION. The adversarial reviewer ran the real `scheduled_brief.sh` and observed: a `SHADOW SIGNALS` title sends a SHADOW notification; a `Framework error` title over 2 runs sends "BRIEF UNHEALTHY"; a wrapped line beginning `XXX/YYY` is read as a pair header and the notification names `USD/JPY LONG`.
   - The I3 test does not pin the live trigger. It asserts the pipeline string occurs somewhere in the wrapper, and line 129 (the suppression check) carries the same string as the real trigger at line 151. A reviewer mutated line 151 to `grep -i 'DECISION'` and I3 still passed.
3. *Counts.* "15 new tests": `pytest --collect-only tests/test_us_events_context.py` → 17 collected (14 functions, parametrized). "Reverted → 33 passed": a reviewer got 34 on the same three files.

**What held up (re-checked by reviewers):** full branch suite `913 passed, 8 skipped, 2 deselected` (reproduced twice independently); mutants M1 sanitizer removed, M2 USD-only feed accepted and M3 USD in `PAIR_CURRENCIES` each re-run and caught; `check_news_gate` and `PAIR_CURRENCIES` untouched; rejecting a USD-only feed agreed correct; 24-hour window agreed (briefs run 18:00, 02:30, 07:30 Pacific).

**Review verdicts:** code reviewer REQUEST CHANGES; adversarial reviewer rule 12 FAIL. **Not mergeable as built.** Requested changes, both reviewers unless noted:
1. A malformed USD row is skipped (logged), never fails the gated fetch; test: valid GBP + malformed USD → write succeeds.
2. Enforce the single-feed-week assumption (`_validate`), or drop I1's filter so the case fails visibly.
3. Sanitizer becomes an allow-list (character set, length cap, `/` and `|` neutralized), stripping before case-folding, covering every wrapper and digest token.
4. Anchor the wrapper's DECISION, SHADOW SIGNALS and Framework error greps to their label lines (free-zone, `test_wrapper_behavior.py`). Rebuild I3 on that harness over an adversarial title corpus, with an open-market LONG control, asserting the notification and the notification ledger.
5. Same-time grouping plus "+N more" instead of a silent cap at 3 (code reviewer).
6. US DATA moves below the market-closed and price-source notes (code reviewer, observed above them).
7. Wording: "(it refreshes Sundays)" is wrong, since the wrapper re-fetches when the file is over 24 h old (scheduled_brief.sh:46); a missing calendar should not read "out of date"; untimed events should not render as exact times.

**Gate 3 entry above is void** until a rebuilt branch passes review.

## 2026-11-01 — REBUILT (Rev 1), AWAITING RE-REVIEW: US events in the brief, the team's requested changes (branch `feat/us-events-context`, NOT merged)

**Owner approved the rebuild.** Spec Rev 1 was committed before the build (spec `cbf7fb2`, then build `b6262e9`). `main` was merged into the branch (`6ca1ce4`) to settle the append-only conflict in this log: both sides kept, main's entries first, 0 deletions against either parent (`git diff --numstat`).

**Changes, one per requested item (see the CORRECTION entry above):**
1. A USD row that can't be read is skipped and counted, never fatal. That covers an unparseable or missing date, a date with no UTC offset, and a non-text title or forecast. The GBP/AUD/JPY parsing block is byte-identical to `main`'s (compared programmatically).
2. USD rows later than `covered_through(newest own row)` are dropped by `calendar_fetch._confine_context_rows`. I1 now runs its USD rows through that function, not a test-side filter.
3. Allow-list sanitizer (`_us_title`):
   - ASCII letters, digits and `.,&()'%+:/-` only;
   - `/` only inside `m/m`-style ratios;
   - capitals ≥ 5 letters and every trigger phrase capitalised;
   - capped at 60 characters.
4. `scheduled_brief.sh`: every stdout trigger is anchored to label lines with `^ ? ?` (labels start 0–2 spaces in, continuations 13–15). This covers DECISION, SHADOW SIGNALS, REASON Framework error and the pair header, in the closed-market gate, the suppression line, the ledger state, the category and the summary.
5. Same-time releases are grouped, max 4 titles, then `+N more`.
6. The line goes immediately before the header border, below every warning.
7. Wording: missing → "news calendar missing", and "refreshes when over a day old" replaces "refreshes Sundays". Untimed events are **not fixable from this source**: the feed has no all-day marker. Observed in the raw feed 2026-11-01: "Congressional Elections" arrives as `2026-11-03T10:16:00-05:00`, and real releases also sit on odd minutes (03:50, 18:50).

**Gate 1:**
- `tests/test_us_events_context.py`: 26 tests.
  - I1b: 5 malformed-USD variants; the dirty feed writes a file byte-identical to the clean feed's.
  - An own-currency malformed row still rejects the feed.
  - A next-week USD row is dropped, and coverage is the own rows' week.
  - I3b: 17 attack titles × 40 paddings = 680 rendered briefs. None carries a trigger phrase, `#`, `|`, `_` or `XXX/YYY`.
  - Ordinary titles survive unchanged. Grouping and placement are each pinned.
- `tests/test_wrapper_behavior.py`: 5 new I3a tests, run on the **real** wrapper under `/bin/bash`, with the US line **unsanitized** and each trigger starting a wrapped line (a precondition test asserts it does).
  - Stand-aside brief, two runs: no notification, no ledger row, 0 health failures.
  - LONG: ledger `GBP_JPY=LONG/open`, summary exactly `GBP/JPY LONG`.
  - Closed-market LONG: suppressed.
  - Control without the US line: identical notification.
  - All existing wrapper tests pass unchanged under the anchors.
- **Mutation: 19 of 19 caught.** Each mutant was confirmed applied, run under `/bin/bash` with `PYTHONDONTWRITEBYTECODE=1`, reverted byte-identical with caches cleared. The reverted copy gave 93 passed.
  - Wrapper: W1 DECISION, W2 SHADOW and W3 error greps unanchored; W4 ledger header, W5 summary DECISION, W6 summary header, W7 closed-gate header and W10 ledger error each set back to `^ *`.
  - Fetch: S1 a malformed USD row raises again; S2 confinement removed. S2 was caught by I1 itself and by the dropped-row test.
  - Sanitizer: S3 `/` rule removed; S4 phrase capitalisation removed; S5 `#` allowed; S6 length cap removed.
  - Display: S7 grouping removed; S8 silent cap; S9 line placed above the warnings; S10 missing shown as out of date.
  - Gate: S11 USD added to `PAIR_CURRENCIES`.
- Full suite on the merged branch: **928 passed, 8 skipped, 2 deselected** (8 skips: gitignored ledgers absent in a worktree).

**Gate 2 — REALITY** (`scripts/reality_run.py --code <worktree>`; every run exit 0, `project files : UNCHANGED (verified by hash)`, stderr 0 bytes):
1. Real ForexFactory fetch with the branch code into the temp dir: `calendar.csv updated: 10 high-impact GBP/AUD/JPY events and 4 US events (context only) through 2026-11-06 16:00 UTC.` The US rows were Congressional Elections (11-03 15:16 UTC) and AHE m/m, NFP and Unemployment Rate (11-06 13:30).
2. The line from that real file:
   - at Thu 18:00 UTC: `Average Hourly Earnings m/m, Non-Farm Employment Change, Unemployment Rate Fri 5:30 AM PST — for information; the framework does not stand aside for US releases.`
   - at Sat 18:00 UTC: `none before Sat 8:59 PM PST; later days are not in this week's calendar yet.`
   - from the same file without US rows: `not checked — the saved news calendar holds no US events (it refreshes when over a day old).`
   - with no file: `not checked — news calendar missing.`
3. Real brief on the fetched calendar (copied into the worktree for the run, removed after; the worktree status was clean). Header:
   `Market closed — analysis based on last close. Next open Sun 2:00 PM PST.` / `US DATA    none in the next 24 hours.` / border. The line sits below the warning.
4. DECISION / REASON / CONFIDENCE / POSITION identical with vs without US rows, both pairs: `True`. Caveat: Sunday, market closed, so both stood aside. I1 is the stronger proof.
5. The anchored triggers on the real output: 0 non-stand-aside DECISION lines, 0 SHADOW / error label lines.

**Deferred (spec §5 Rev 1):**
- "released at …" for the last 2 hours (optional);
- splitting the heartbeat's event count;
- committing a mutation runner;
- the `reality_run --code` calendar gap (known since 2026-10-18; this run worked around it again by copying the calendar in).

**Gate 3 — PENDING LIVE CONFIRMATION (after merge only):**
- The first calendar fetch after merge (Sunday's job, or the brief's re-fetch of a file over 24 h old) writes USD rows.
- The next brief renders them.
- No notification is ever caused by the line.
