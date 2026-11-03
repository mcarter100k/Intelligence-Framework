# Spec v4: range + volatile wording, test amendments to v3

**Status:** spec for team review, written 2026-11-03, before any build.
**Supersedes v3 (`range_volatile_wording_v3_spec.md`, `ee639a2`) only where
stated below. Everything else in v3 stands as written**, including the
wording table (§3), which review approved. v1–v3 bodies are untouched. Scope
is unchanged: `decision_brief.py` rendered REASON only; `regime_detection.py`
is out of scope.

## 1. Wording: one change (review point 4)

- The `""` row's opening becomes **"The 4-hour chart's volatility is
  outside its normal range,"**. The word "well" is dropped.
- Reason: GBP/AUD's spike threshold is 1.2× the average
  (`regime_detection.py:51`), so "well outside" overstates it.

## 2. W5 replaced: which cells change

v3 said every (RANGING, VOLATILE) cell renders the §3 sentence. That is
false. In `_render_reason`, four earlier branches return first: news gating
(`decision_brief.py:504`), `filter_block` (`:515`), `atr_comp` (`:518`), and
`atr_vs_avg ≥ 2.0` "Extreme ATR spike" (`:522`). The rule becomes:

- **A cell renders the §3 sentence if and only if `main` rendered a REASON
  beginning "Range breaking down" for it.** Those are the target cells.
  Generating the golden file records each cell's target flag.
- **Every non-target cell, in any regime, (RANGING, VOLATILE) included,
  must match `main` exactly.** Branch order is not changed.
- **Storage:** one combined sha256 over the sorted non-target cells, plus
  a per-cell list written only on mismatch, so a failure names its cells.
  The target-cell keys are stored as a plain list. No multi-megabyte JSON
  is committed.
- **Grid, v3's plus these fields:**
  - `stand_down_reason` ∈ {"", "RANGING D1 + VOLATILE H4 — range breaking
    down, wait", "news: high-impact release in 45 minutes"};
  - `filter_block` as a string ∈ {"", "blocked"}, not a boolean;
  - fixed values: `execution_mode = "STAND_DOWN"`, `instrument` ∈ {GBP_AUD,
    GBP_JPY} (so `atr_comp` and the spike multiplier take each pair's real
    config), `atr_spike_multiplier` from that config, and
    `decision["reason"] = ""`.
- A test asserts that the target list is non-empty, and that it contains
  both the conflict path (`:535`) and the STAND DOWN path (`:597`). An empty
  target set would make W5 pass vacuously.

## 3. Unreachability pin replaced: through `get_regime`

- v3's sweep of `_classify_ex` outputs cannot pin anything.
  `_classify_ex` takes `slope` as an argument, and the forcing to ±1 happens
  in `get_regime` (`regime_detection.py:971-976`).
- New test: drive `get_regime` with the H4 feed monkeypatched to synthetic
  series that produce UPTREND, DOWNTREND and TRANSITIONAL structure at
  4-hour trend strength 25+, including a series whose raw 10-bar price
  change opposes its structure. Wrap `_classify_ex` to record every 4-hour
  call. Assert:
  1. for UPTREND/DOWNTREND, the slope passed has the structure's sign;
  2. no 4-hour result is `STRUCTURE_DISAGREES` or the residual `""` at
     trend strength 25+ without a spike or compression.
- **Mutant:** replace `:971-976` with the raw price change for every
  structure. The test must fail.
  - This is a test of protected code's current behaviour. It changes no
    protected code. If the mutant cannot make it fail, the test is wrong
    and the build stops.

## 4. Mutants (adds to v3 §6)

- §2: a non-target cell reworded must fail W5. An empty target set must
  fail the non-empty check.
- §3: the slope-forcing mutant above.
