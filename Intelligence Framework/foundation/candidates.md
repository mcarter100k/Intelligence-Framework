# Frozen shadow candidates — specs and evidence

> **AS OF 2026-09-29 (ledger read at the audit).** Every count, N, R value and status below is a snapshot of that read, not a current figure. Re-read `shadow_signal_log.csv` before quoting any of them.

Exact definitions of the pre-registered candidates and what the ledger shows.

> Citations: `VL:n` = `validation_log.md` line n; `AUDIT §n` = `docs/audit_2026-09-29.md`; other paths are repo files. Line numbers are as of the 2026-09-29 audit (commit efd293e) — search by content if they have drifted.

## RETIRED BY OWNER DECISION, 2026-11-17 (ruling M1)

**All three candidates are retired by owner decision, not by verdict:**
EARLY_MOMENTUM_v2, THRUST_PULLBACK and MOMENTUM_JOIN.
- On 2026-11-17 the owner moved the framework to gold only. Every GBP/AUD
  and GBP/JPY job, alert and candidate logging was stopped (validation_log
  2026-11-17, M1).
- None of them reached the N=20 futility checkpoint.
- This closes R40–R42's open retirement question by owner ruling.
- **No edge or lack of edge is claimed by this retirement.**

**Episode counts frozen where they stand.** Counted with
`shadow_signals.graded_episodes` and `get_shadow_tally` on the live ledger,
read-only, after the last grader run (2026-11-17 15:15 PT):

| Candidate | Independent episodes | Graded / logged rows | Per episode (diagnostic, not evidence) |
|---|---|---|---|
| EARLY_MOMENTUM_v2 | 6 (GBP/JPY) | 27 / 28 (1 open, never to be graded) | avg +0.17R, median −0.02R, without the best −0.17R |
| THRUST_PULLBACK | 2 (GBP/JPY) | 2 / 2 | avg +0.80R, median +0.80R, without the best −0.33R |
| MOMENTUM_JOIN | 2 (1 GBP/AUD, 1 GBP/JPY) | 7 / 11 (4 open, never to be graded) | avg −1.00R |

**The ledgers, the shadow logs and the candidate history are kept intact,
as evidence.**

## 5a. Common rules for all candidates (`shadow_signals.py`)

- Frozen 2026-07-29. `FLAG_N=30`, `REVIEW_N=60` graded episodes. `HORIZON=30` H4 bars.
- Futility checkpoint (2026-10-19, docs/specs/futility_rule_spec.md): once, at N=20 graded independent episodes; if the 90% one-sided upper bound on mean R is below +0.15R, the candidate is REFUTED and retired. As of 2026-10-19: EM_v2 3 episodes (R −0.55, −0.39, +0.34; avg −0.20R), THRUST_PULLBACK 1 (−0.33R), MOMENTUM_JOIN 1 (−1.00R).
- **Context:** the last 300 **complete** H4 bars. ADX (Wilder 14), ATR series (n−14), and **structure from `_detect_structure` on H4 bars** (`:83-107`).
- **Entry:** the last complete H4 close, stamped with that bar's **open** time.
- **Grading** (`:575-639`)
  - Look at bars ei+1 … ei+30.
  - hit = LONG `min(L) ≤ stop` / SHORT `max(H) ≥ stop`.
  - `r = −1.0` if hit, else `(close[ei+30] − entry)·sign / |entry−stop|`.
  - Also records MFE/MAE/net pips.
  - Mid prices; **no spread, no financing.**
- **invalid_spec** rows (stop on the non-adverse side) are excluded from every tally.
- **Dedup key:** candidate + instrument + timestamp.
- **Not news-gated.** Fires inside a gate window get stamped `news_window=true`.
- **Episode collapse:** fixed 2026-10-19 (docs/specs/shadow_tally_spec.md). Graded rows only; a new episode starts 30+ H4 bars after the current one's first fire, on the bar index; the episode's R is its first fire's R. Before that it was 120 clock hours with ungraded rows counted (AUDIT §2 #3), which read EM_v2 as 4 episodes instead of 3 (I30).
- **Cadence:** evaluated only at brief run times. The 01Z and 13Z H4 bars are never checked, which halves the firing rate and biases the sample by session (AUDIT §2 #4).

**Loss species** (frozen 2026-09-09; first match wins; `:456-512`)
1. `event_window`: the `news_window` stamp is present.
2. `stopped_then_reversed`: after the stop-hit bar, price ran ≥ **2R** beyond entry in the trade direction.
3. `exhaustion_entry`: entry is ≥ **2.0 fire-time ATR** beyond the 20-bar mean close.
4. `never_onside`: MFE < **0.25R**.
5. `bled_out`: everything else.

## 5b. The candidates

| Candidate | Pairs | Trigger | Stop | Status and evidence (ledger read 2026-09-29) |
|---|---|---|---|---|
| **EARLY_MOMENTUM (v1)**: RETIRED 2026-09-09 | GBP/JPY | H4 ADX **18 ≤ adx < 25** + confirmed structure UPTREND→LONG / DOWNTREND→SHORT | Last swing (`latest_sl` / `latest_sh`); fallback entry ∓ 1.5×ATR | 3 rows: 1 valid, **−1.0R** (MFE 809.2, stopped_then_reversed); rows 2–3 invalid_spec. Retired because the stale swing could sit on the wrong side of entry |
| **EARLY_MOMENTUM_v2**: frozen 2026-09-09 | GBP/JPY only | Same as v1 (`EM_ADX_LO=18.0`, `EM_ADX_HI=25.0`) | Same, plus the **GUARD**: a swing on the non-adverse side means **NO FIRE** (no fallback substitution) | **1 graded episode** (2026-09-18T05 → 09-21, 6 LONG rows, all losers: −0.55 / −0.65 / −0.80 / −0.53 / −1.0 / −1.0). 6 rows pending (1 LONG 09-22, 5 SHORT 09-25 → 09-28). ~0.7 fires/week. **Spec discrepancy:** the spec doc says "D1 structure", but code uses H4 structure (`shadow_signals.py:139-146`; the pivot entry VL:1237 says "confirmed H4 structure") |
| **THRUST_PULLBACK**: frozen 2026-07-29; N starts 2026-09-10 (ATR-index fix) | Both | A box of the previous **18** bars with height ≤ **3.0×ATR(b)**. A break bar b in the last **10** bars closes beyond the box with body ≥ **1.0×ATR(b)**. A later bar trades back within **0.25×ATR** of the broken edge. The prior bar closed on the box side and the **current bar closes back beyond the edge** | **Far box edge** (LONG: box_lo; SHORT: box_hi) | Live: 1 pending row (2026-09-28T05 GBP_JPY SHORT, same bar as an EM_v2 fire). 2026-07-29 → 09-10 is **UNOBSERVED** (IndexError). Historical GBP/AUD walk-forward: 22 episodes, 36% win, avgR −0.10, medR −0.40, in-sample (R17). ~0.4 fires/week |
| **MOMENTUM_JOIN**: frozen 2026-07-29, INFORMED PRIOR ("expected weakest") | Both | H4 ADX ≥ **30** and ADX slope ≥ **+8** over **12** bars (ADX now minus ADX computed without the last 12 bars), structure UPTREND/DOWNTREND, and the current bar makes a **new 12-bar** high/low | entry ∓ **1.5×ATR** | Live: 3 pending GBP/AUD LONG rows (2026-09-28T05, T09, 09-29T05). In-sample audit replay: GBP/JPY +0.48R, N=23, t=0.94, median −1R. ~0.3 fires/week |

**2005–2013 STUDY replay (FCS-1, 2026-11-04; R40–R42).** Every H4 bar, live code, live grading, era spread and financing, 9 years none of the candidates was designed on:
- EARLY_MOMENTUM_v2 GBP/JPY: 246 episodes, −0.099R, **REFUTED**.
- THRUST_PULLBACK: GBP/AUD 51 episodes, −0.130R, **REFUTED**; GBP/JPY 39, +0.056R, INCONCLUSIVE.
- MOMENTUM_JOIN: GBP/AUD 98 episodes, −0.095R, **REFUTED**; GBP/JPY 96, −0.012R, INCONCLUSIVE.
- No cell SUPPORTED. The candidates stay frozen and logging; what to do with the REFUTED cells is the team's decision.

**Evidence status (AUDIT §3)**
- Real trades: **0**.
- Live-path directional calls graded: 1, probably synthetic (the 2026-06-28 +150.0-pip row).
- History check: VL:559 admits synthetic data was injected that day.

---
