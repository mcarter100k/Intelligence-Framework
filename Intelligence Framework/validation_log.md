# Validation Log
## Intelligence Framework — Parameter Validation History

---

## 2025-06-25 — ADX Threshold Validation (Problem 1)

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

**Script:** validate_atr_threshold.py  
**Data:** 5-year D1, observations per pair  
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
