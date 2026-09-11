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

**Feed-overlap check (mandatory, Stage 2, before any STUDY statistic):**
pull 2023-09-01 → 2026-09-10 (the profile window, both pairs, D1 + H4) from
the chosen provider, convert to the same 17:00-NY alignment, and compare
bar-by-bar against the OANDA cache. Report per field (O/H/L/C): median and
p95 |diff| in pips, and the **disagreement rate** = % of bars with any field
differing by > 5 pips (GBP_AUD) / > 5 JPY-pips (GBP_JPY).
*PROPOSED acceptance (frozen at Stage-2 commit unless team amends):*
disagreement rate ≤ 2% AND median |close diff| ≤ 1.5 pips; otherwise STOP
and report — no STUDY work on a feed we can't reconcile.
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
*PROPOSED — frozen at Stage-2 commit unless the team amends in review:*

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
*PROPOSED template (echoes FLAG_N=30 / REVIEW_N=60; frozen per candidate at
exam-spec commit after team review):*

- **VALIDATED:** N ≥ 60 episodes AND avg R ≥ +0.15 AND win rate ≥ 35% AND
  max drawdown ≤ 12R.
- **FAILED:** N ≥ 30 AND (avg R ≤ 0.0 OR max drawdown > 20R).
- **INCONCLUSIVE:** anything else — including N < 30, which is reported as
  "exam cannot validate at this frequency," and the exam is still spent.

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

## 8. Trade-frequency reality check (STUDY half, Stage 3)

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

## 9. Sequence (stage gates)

1. **Stage 1 (this commit):** spec written and committed on `main`. STOP.
   Report to team. No data touched.
2. **Stage 2 (after team review):** provider coverage confirmation →
   source + convert STUDY data → feed-overlap check → conversion gate.
   Report the verification numbers ONLY — no price statistics.
3. **Stage 3 (after gate passes):** STUDY-half work, starting with the §8
   frequency count.
4. **SEALED EXAM:** stays closed until the team opens it explicitly, per §7.

Anything marked *PROPOSED* above is finalized (accepted or amended) in the
Stage-1→2 team review and frozen in the Stage-2 commit; everything else in
this file is fixed by this commit.
