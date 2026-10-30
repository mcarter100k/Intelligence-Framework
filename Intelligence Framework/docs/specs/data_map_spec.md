# Spec: data map — pre-registered partition of all GBP_AUD / GBP_JPY history (Stage 1)

**Status:** team-directed 2026-09-11. This commit IS the pre-registration:
no bar in the STUDY or SEALED EXAM spans may be opened until this file is on
`main`, and then only per the stage gates below. Written BEFORE any
conversion work and BEFORE any data statistic on the mapped spans.
**Sources:** earliest-load inventory 2026-09-11 (validate_adx_threshold
yfinance ≈ 2021-04-26; OANDA count-family loads ≈ 2021-05/2021-07; H4 never
loaded before 2023-04-30) and the 2004→2021 bar census (counts only), both
reported in-session 2026-09-11. Census raw timestamps were kept outside the
repo; only counts were reported.

---

## 1. The map

| Span | Dates | Role |
|---|---|---|
| STUDY | 2005-01-01 → 2013-12-31 | Learning on old-convention data, AFTER the conversion gate passes (Stage 3). Both pairs. |
| SEALED EXAM | 2014-01-01 → 2021-04-25 | One frozen spec, one run, then spent. Modern convention, clean (census: 258–260 D1/yr, 6.00 H4/day). Stays closed until the team opens it explicitly. |
| USED | 2021-04-26 → 2026-09-10 | Already touched by committed studies/validators (inventory above). Learning only — NEVER proof. |
| FORWARD | 2026-09-10 → | The live shadow ledger (N per candidate starts at the 2026-09-10 fix). The only span that can ever grade a live claim. |

**2004 is EXCLUDED** (GBP_AUD starts 2004-06-01, partial year; H4 unusable
at 1.00 bar/day in the census). It belongs to no span and is not opened.

STUDY-era raw data is old-convention (census: 330–360 raw "D1" rows/yr from
weekend/extra candles; H4 ~4.8–5.7 bars/day with 70–95 short days/yr) and is
unusable until converted — see the gate in §3.

**Exam split rule (decided NOW, before anything is opened):** the SEALED
EXAM is split into two sub-exams (2014-01-01→2017-08-31 and
2017-09-01→2021-04-25, one frozen spec + one run each) ONLY IF the STUDY
half yields ≥ 8 trades/yr for the candidate under test. Otherwise it remains
a single exam. This decision is made from the Stage-3 frequency count and
recorded in validation_log BEFORE any exam-spec is written.

---

## 2. Condition 1 — data provenance + feed-overlap check

Our OANDA history was first loaded ~2021 (D1) / 2023-04-30 (H4), and OANDA's
own pre-2014 candles are old-convention. STUDY data therefore comes from a
second provider, named here:

- **Primary: Dukascopy** (historical candles/tick, early-2000s coverage).
- **Fallback: HistData.com** (M1 archives), used only if Dukascopy lacks
  either pair for 2005-01-01.
- First act of Stage 2 is a **coverage confirmation** for both pairs from
  2005-01-01. If neither provider covers the start, the STUDY start moves
  forward to the first covered date and that amendment is committed BEFORE
  conversion begins.
- **Failure ladder (team amendment, 2026-09-11):** a failed overlap check on
  Dukascopy means try HistData and RE-RUN the overlap check; if both
  providers fail it, **history-validation is declared INFEASIBLE** — the
  same standing as a too-low trade count (§9) — and the forward ledger is
  the only path. The actual overlap numbers are reported either way.

**Feed-overlap check (mandatory, Stage 2, before any STUDY statistic):**
pull 2023-09-01 → 2026-09-10 (the profile window, both pairs, D1 + H4) from
the chosen provider, convert to the same 17:00-NY alignment, and compare
bar-by-bar against the OANDA cache. Report per field (O/H/L/C): median and
p95 |diff| in pips, and the **disagreement rate** = % of bars with any field
differing by > 5 pips (GBP_AUD) / > 5 JPY-pips (GBP_JPY).
*Acceptance (APPROVED as proposed, 2026-09-11):*
disagreement rate ≤ 2% AND median |close diff| ≤ 1.5 pips; otherwise the
§2 failure ladder applies — no STUDY work on a feed we can't reconcile.
**Precedent this exists to honor:** v1 thresholds were validated on yfinance
and traded on OANDA; that mismatch was a real defect (validation_log,
Honesty Correction / Audit Item 2).

---

## 3. Conversion gate (Stage 2 — verification numbers only, no price statistics)

STUDY-era data is converted to the modern convention: 17:00-NY daily close,
6 H4 bars/day. The gate, run per pair per year 2005–2013:

1. **D1 count** in [252, 262] per full year (holidays only; census shows the
   modern feed at 258–260).
2. **H4 regularity:** exactly 6 bars on ≥ 99% of trading days; residual
   short days listed by date (holiday half-days only).
3. **Internal consistency:** on a fixed sample of 50 days/pair/year, D1
   high == max of that day's 6 H4 highs and D1 low == min of the H4 lows
   (tolerance 0.5 pip).
4. **Known-date spot checks** (existence + elevated-range sign check only,
   no statistics recorded beyond pass/fail): 2008-10-24 (GBP/JPY panic),
   2010-05-06 (flash crash), 2011-03-17 (G7 yen intervention), 2013-04-04
   (BoJ QQE).

Stage 2 reports THESE numbers and nothing else. Any gate failure stops the
sequence; no STUDY statistic exists until the gate passes and the pass is
recorded in validation_log.

---

## 4. Condition 2 — period-appropriate spreads (committed before any statistic)

Round-trip spread schedule, applied by era in every STUDY/EXAM computation.
*APPROVED as proposed, 2026-09-11 — now frozen:*

| Era | GBP_AUD (pips) | GBP_JPY (JPY-pips) |
|---|---|---|
| 2005–2009 | 10 | 6 |
| 2010–2013 | 7 | 5 |
| 2014–2017 | 5 | 4 |
| 2018–2021 | 4 | 4 |
| 2021→ (USED/FORWARD) | 3 | 3 |

The 2021→ row matches the SPREAD_PIPS = 3.0 already used by the committed
studies. Modern costs on old data manufacture profit that never existed;
no result computed under a different schedule is citable.

---

## 5. Condition 3 — non-stationarity stated as a limit

2005–2013 spans the GFC and ZIRP; 2014–2021 spans COVID. The claim any STUDY
or EXAM result can support is **"does this survive conditions it wasn't
designed on"** — NOT "does this work." No result from these spans may be
quoted, in the log or the brief, without that frame. Regime mix, spread
regime, and market microstructure all differ from the FORWARD span; the
forward ledger remains the only evidence about the present.

---

## 6. Condition 4 — pre-commit success criteria, in numbers

The exam-spec (a later artifact, per candidate) MUST contain numeric
criteria — trades/year, win rate, average R, max drawdown — committed before
the exam is opened. An exam without committed numbers cannot be opened.
*APPROVED 2026-09-11 with two team amendments, both binding:*

- **N counts INDEPENDENT EPISODES** — non-overlapping horizons per the
  shadow-harness counting rule (`shadow_signals.episode_count()` semantics)
  — never raw trades or raw fires.
- **Median winner R and median loser R are reported alongside avg R**, and a
  positive avg R driven by a single outlier is **INCONCLUSIVE, not
  VALIDATED**. Operational test: if removing the single best episode drops
  avg R below the VALIDATED threshold, the result is INCONCLUSIVE.

Template (echoes FLAG_N=30 / REVIEW_N=60; frozen per candidate at exam-spec
commit after team review):

- **VALIDATED:** N ≥ 60 independent episodes AND avg R ≥ +0.15 (surviving
  the single-outlier removal test) AND win rate ≥ 35% AND max drawdown
  ≤ 12R.
- **FAILED:** N ≥ 30 AND (avg R ≤ 0.0 OR max drawdown > 20R).
- **INCONCLUSIVE:** anything else — including N < 30 ("exam cannot validate
  at this frequency") and outlier-driven positives. The exam is still
  spent.

---

## 7. Condition 5 — sealed-exam enforcement

- The exam-spec and its runner are committed together; their SHA-256 hashes
  are recorded in validation_log in the same commit.
- Opening requires an explicit team instruction recorded in validation_log.
- The run is a **single command**; the runner refuses to run if an
  exam-opened marker exists, and its first action is to commit that marker
  (`docs/specs/exam_opened_<candidate>_<date>.marker`) — a second run is a
  visible violation, not a quiet possibility.
- The output goes to validation_log **regardless of outcome**, verbatim.
- No peeking, no re-tuning, no second run. Once opened, the span is spent
  for that spec permanently. A materially different future spec needs a
  fresh team ruling on whether any sealed data remains for it.

---

## 8. What the STUDY tests (team amendment, 2026-09-11)

Named explicitly, because the exam can only answer the question it was
opened for:

- **The STUDY tests the frozen shadow candidates, each evaluated
  SEPARATELY as its own question:** THRUST_PULLBACK (both pairs),
  EARLY_MOMENTUM_v2 (GBP/JPY only), MOMENTUM_JOIN (both pairs) — exactly as
  frozen in `shadow_signals.py` (2026-07-29; EARLY_MOMENTUM_v2 2026-09-09),
  spec parameters byte-identical, graded by the live grading rule.
- **The live decision path is OUT of the STUDY's scope.** Its inputs —
  calendar/news gate, session context, weekly context, COT — cannot be
  reconstructed for 2005–2013 honestly; a stripped-down replica would test
  something that never ran live. If the team wants it examined, that is a
  separate spec with its own data ruling.
- **A SEALED-EXAM opening names exactly ONE candidate** in its exam-spec;
  the exam is spent for that candidate alone (§7). Candidates not named
  keep their claim on the sealed span only per a fresh team ruling.

---

## 9. Trade-frequency reality check (STUDY half, Stage 3)

Before any performance number is discussed, Stage 3 reports the **episode
count** the candidate produces on the 9-year STUDY span (non-overlapping
episodes, the shadow-harness counting rule). Explicitly:

- ~200 episodes → we finally have honest N; proceed per this spec.
- ~25 episodes → the framework is too selective to validate on history; the
  forward ledger is the only path, and the SEALED EXAM stays closed
  indefinitely (recorded as such).
- The count itself is committed to validation_log either way, and drives
  the §1 exam-split decision (≥ 8 trades/yr).

---

## 10. Sequence (stage gates)

1. **Stage 1:** spec written and committed on `main` (f5eea4f). STOP.
   Report to team. No data touched. **APPROVED 2026-09-11 with the
   amendments now folded into §2, §6, §8; spread schedule and overlap
   thresholds approved as proposed.**
2. **Stage 2 (after team review):** provider coverage confirmation →
   source + convert STUDY data → feed-overlap check → conversion gate.
   Report the verification numbers ONLY — no price statistics.
3. **Stage 3 (after gate passes):** STUDY-half work, starting with the §9
   frequency count.
4. **SEALED EXAM:** stays closed until the team opens it explicitly, per §7.

All formerly-PROPOSED items were finalized in the 2026-09-11 Stage-1 review
(spreads and overlap thresholds approved as proposed; success criteria
approved as amended in §6; provider approved with the §2 failure ladder).
This file is now fixed; further change requires a fresh team ruling.

---

## 11. Dated amendments (appended; §1–§10 above are unchanged)

### 11.1 — 2026-10-22: STUDY data source is OANDA (owner ruling)

Amends the provider named in §2. **OANDA's own candles are the STUDY data
source** (mid prices, default 17:00-NY alignment, the same request as the
live feed). Basis: the 2026-10-20 depth check (studies/history_depth_report.md).
OANDA serves both pairs from before 2005. Its 2005–2013 weekday grid meets
the §3 count tests, and its historical API matched the framework's stored
bars and live-recorded closes exactly (30,810 + 76 bars, 0.0 pips).
**Dukascopy attempt 2 of 2 is NOT spent. It stays the fallback**, under the
2026-10-20 ruling's conditions. The §2 feed-overlap check does not apply to
a same-broker source; the reduced gate above takes its place. The §3
conversion gate still applies in full. **No study builds on this data until
§3 items 3 and 4 pass.**

### 11.2 — 2026-10-22: seal embargo (owner ruling)

Bars within one trading day of the seal belong to **no span** (the same
standing as 2004). That covers both edges of the SEALED EXAM and one trading
day on each side of each edge, plus any weekend or holiday candles between
them. A candle belongs to the span of its session's trading day. Session D
runs 17:00 New York on D−1 → 17:00 on D, which is how OANDA stamps it.

| Edge | Embargoed trading days | Candle opens embargoed (UTC, half-open) |
|---|---|---|
| STUDY → SEALED | 2013-12-31 (STUDY side), 2014-01-01 (SEALED side) | [2013-12-30T22:00Z, 2014-01-01T22:00Z) |
| SEALED → USED | 2021-04-23 (SEALED side), the weekend including the **2021-04-25 Sunday-open candle**, 2021-04-26 (USED side) | [2021-04-22T21:00Z, 2021-04-26T21:00Z) |

Effective spans: STUDY = trading days 2005-01-01 → **2013-12-30**; SEALED
EXAM = **2014-01-02 → 2021-04-22**; USED = **2021-04-27** → 2026-09-10.
The ruling named the 2021-04-25 candle and "anything within one trading day
of the seal". Applying the margin to both sides of both edges is the
reading recorded here; narrowing it is a fresh ruling. Requests near an
edge must stop at least one candle short, because OANDA returns the candle
*containing* `from` (observed 2026-10-20).

### 11.3 — 2026-10-22: correction to the §1 census reading (INFERRED)

§1 and §2 (lines 27–29) describe OANDA's STUDY-era H4 as "~4.8–5.7 bars/day
with 70–95 short days/yr" and its D1 as "330–360 raw rows/yr". Measured on
the 17:00-NY session grid (2026-10-20, timestamps only), the weekday grid
is intact:
- **Weekday D1:** 259–262 a year.
- **H4 sessions with all 6 bars:** 99.23–100% of weekdays.
- **Extras:** 14–101 weekend-session D1 candles a year sit on top of that grid.

**Evidence for the correction (arithmetic match):** H4 rows ÷ D1 rows *with
weekend candles counted as days* gives 4.71–5.75 across 2005–2013, matching
"~4.8–5.7". Raw D1 rows are 331–361 for 2005–2012, matching "330–360". The
census measured the weekend extras, not missing weekday bars.
**Status: INFERRED.** The census method and raw timestamps were never
recorded, so the explanation rests on the arithmetic match alone. The
original text above stands as written.

### 11.4 — 2026-10-22: how §3 items 3–4 are run on OANDA data (declared before any price is fetched)

- **Data:** OANDA D1 and H4, mid, default alignment, STUDY span less the
  §11.2 embargo. Candles are fetched as served; **no weekend-candle
  treatment is applied** (that rule is pending:
  docs/specs/study_weekend_candle_spec.md).
- **Item 3 (internal consistency):**
  - **Eligible days:** weekday trading days with one aligned D1 candle and
    all six aligned H4 candles.
  - **Fixed sample:** per pair per year, `random.Random(f"data_map_s3_item3:{pair}:{year}").sample(sorted(eligible), 50)`.
  - **A day passes when** |D1 high − max of its six H4 highs| ≤ 0.5 pip
    AND |D1 low − min of its six H4 lows| ≤ 0.5 pip.
  - **Item 3 passes only if all 900 sampled days pass** (50 × 9 years × 2 pairs).
  - **Reported, not gated:** the same test on every eligible weekday, and on
    every weekend session against that session's own H4 candles. Monday
    sessions change under any fold, so item 3 is re-run on Mondays once a
    weekend rule is approved and built.
- **Item 4 (known-date spot checks):**
  - **Existence:** the D1 candle for the named trading day exists, for both
    pairs on all four dates.
  - **Elevated range (sign only):** the day's D1 high−low exceeds the median
    high−low of the 20 preceding Tuesday–Friday trading days in the same
    series. Mondays are excluded so the result cannot change under a
    weekend rule; weekend candles are excluded too.
  - **Pairs for the range check:** both pairs on 2008-10-24 and 2010-05-06
    (broad-market events). GBP/JPY only on 2011-03-17 and 2013-04-04 (yen
    events); GBP/AUD is not computed on those two dates.
  - **Item 4 passes only if all 4 × 2 existence checks and all 6 range
    checks pass.** Pass/fail only; no range is recorded.
- **Items 1–2** are recomputed on the same fetch with the embargo applied.
- **Output:** match counts, pass/fail, and |difference| in pips for item
  3. No price level, range or average.

### 11.5 — 2026-10-29: the STUDY span also tests one new hypothesis (owner ruling)

§8 named the frozen shadow candidates as what the STUDY tests. On
2026-10-29 the owner directed one additional pre-registered test on the
same span: **carry after a quiet week** (docs/specs/carry_quiet_week_spec.md),
with GBP/JPY and GBP/AUD each as its own cell.
- **Multiple testing across studies:** each hypothesis tested on this span
  adds to the number of questions asked of it. Each study must report what
  it tested, and later readers count them.
- **The frozen-candidate tests in §8 and §9 are unaffected.** They remain
  the span's first purpose.
- **The SEALED EXAM is untouched.** Opening it for any candidate still
  requires §7.
