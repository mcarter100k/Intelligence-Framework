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

## 2025-06-25 — ADX Threshold Validation (Problem 1)
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

## 2025-06-25 — Problem 1 Live API Validation

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

## 2025-06-25 — Problem 2 Stress Test + Deep Verification

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

## 2025-06-25 — Problem 2 Final Sign-off

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

## 2025-06-25 — ATR Spike Multiplier Validation (Problem 3)
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

## 2025-06-25 — Problem 3 Live Historical Replay Validation

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

## 2025-06-28 — Four-Issue Implementation + Validation

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

## 2025-06-28 — Problem 5: Confluence Scoring Rebuild

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

## 2025-06-28 — Problem 6: Composite Regime Resolution Table

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

## 2025-06-28 — Problem 7: Validation Infrastructure

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

## 2025-06-28 — Problem 8: No-Trade Filter + Counter-Trend Override

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

## 2025-06-29 — Priority 1: Decision Brief + Entry Confirmation

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
- [ ] **First loss autopsied at scheduled grading time** (added 2026-09-09)
      — a future graded loss gets its loss_species stamped by the scheduled
      run_outcome_check path (the backfill proved the classifier on the
      founding exhibit; only time provides a fresh loss).
- [ ] **First real session walked by the promoted circuit breaker** (added
      2026-09-09) — a day with live CLOSE rows in trades.csv exercises the
      R-curve and limits on real trading, not fixtures.
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
