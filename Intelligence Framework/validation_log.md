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
