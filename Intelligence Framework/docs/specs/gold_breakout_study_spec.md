# Spec: do gold's breaks of a daily swing hold? (descriptive, GBP/AUD benchmark)

**Status:** FROZEN 2026-11-14, owner request ("start your breakout study
now"). `docs/gold_plan.md` Phase C, study C2. Committed before the runner
(`studies/gold_breakout_study.py`) exists and before any gold breakout
statistic is computed. The run happens once, after the runner is committed,
and its output goes to validation_log verbatim, whatever it says.

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar (§2 checks this). **Descriptive only:
no entries, no R, no costs, no claim that anything pays.**

## 1. Question and why

**When gold trades past the latest confirmed daily swing high or low, how
often is it back inside within a few days?** Up and down separately, per era,
with GBP/AUD measured by the same code as the benchmark.

- **The decision it informs:** the owner's weekly markup (`markups/README.md`).
  "What was the last break?" and every zone depend on whether a break of a
  swing is likely to stick or to fail. The only figure we have is GBP/AUD's
  (R24: 71% failed within 3 days, N 69, 2023–2026), measured with the live
  framework's swing detector, not the markup's rule. Nothing says gold behaves
  the same.
- **Why the GBP/AUD benchmark:** a gold figure means more next to a figure
  computed identically. It also checks the result against R24's
  neighbourhood. R24 used a different swing detector, so that comparison is
  context, not a pass/fail control.

## 2. Data

| Instrument | File (under `~/intel_study_archives/`) | sha256 |
|---|---|---|
| XAU_USD | `research_archive_legs/XAU_USD_D.csv` | `6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca` |
| GBP_AUD | `research_archive/GBP_AUD_D.csv` | `24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6` |

- Both hashes equal the archive manifests' entries (checked 2026-11-14). The
  runner refuses to run on any other bytes.
- **Eras = the archive's span labels:** STUDY (2005–2013; gold from 2006) and
  USED (2021-04-27 → 2026-09-09). FORWARD (40 days) is not used.
- **Gold starts at the 2006-03-21 session** (the first daily row opening
  2006-03-20T22:00Z): the same start the leg study adopted on 2026-11-05
  (validation_log), because gold's first OANDA hours have no 4-hour bar.
  This was listed as team ruling T2 in `docs/gold_plan.md`; it is noted for
  the team, not waited on.
- **No 2014-01-01 → 2021-04-25 bar is read.** Checked 2026-11-14: zero such
  rows in either file. The runner also refuses any row dated in that span.
- **Each era is processed on its own.** Swings, ATR and events never carry
  across the 2014–2021 gap.

## 3. Definitions (fixed)

- **Swing:** the markup's rule (`markups/README.md` §3), computed by the same
  function the markup uses (`studies/markup_swings.swings`, k = 3 on the daily).
  A swing at day i is **confirmed at the close of day i + 3** and becomes a
  level from day i + 4.
- **The level on day d:** the latest swing high (and, separately, swing low)
  confirmed by the close of day d − 1. "Latest" = most recently confirmed.
- **ATR:** Wilder ATR(14) of the daily bars, **as of day d − 1** (known at the
  time). Days before the first ATR value are warm-up: events there are
  counted and excluded.
- **Each level can produce one event per definition**, the first time it
  qualifies.

**Definition W (wick break; R24's definition, for comparison):**
- **Event:** day d's high goes above the level (upside) or its low below it
  (downside).
- **Failed** if any close on days d, d + 1 or d + 2 is back inside (below an
  upside level, above a downside level); **held** otherwise.
- **Overshoot:** the furthest price beyond the level over days d … d + 4, in
  ATR.
- An event without days d + 2 (or d + 4, for the overshoot) inside its era is
  **ungraded**: counted, excluded.

**Definition C (close break; the markup's "last break"):**
- **Event:** day d closes beyond the level.
- **Failed** if any close on days d + 1, d + 2 or d + 3 is back inside;
  **held** otherwise.
- **Distance at the close:** how far day d's close is beyond the level, in ATR.
  This is known at the close, so it is the figure a trader could act on.
- An event without day d + 3 inside its era is **ungraded**.

## 4. Reported

For each instrument × era × side (up, down, both) × definition:
1. Events, failed, held, ungraded, warm-up. The failed share with a 95%
   Wilson interval.
2. W only: overshoot in ATR, p50 / p75 / p90, for failed and for held events.
3. C only: held share by the distance at the close, in buckets
   **< 0.25, 0.25–0.5, 0.5–1.0, ≥ 1.0 ATR**.
4. Gold minus GBP/AUD failed share, per era and definition, with a 95%
   Newcombe (hybrid score) interval.
5. Gold up minus gold down failed share, per era and definition, same interval.
6. The failed share by calendar year (both sides, both definitions).

## 5. Reading rules (fixed before the run)

1. **Any cell with fewer than 20 graded events is INSUFFICIENT:** its numbers
   are shown and never read.
2. **"Most breaks fail"** if the failed share's 95% lower bound is above 50%.
   **"Most breaks hold"** if its upper bound is below 50%. Otherwise **"about
   even"**.
3. **Gold differs from GBP/AUD** only if the interval of the difference (§4.4)
   excludes 0, both cells graded N ≥ 20. Same for up vs down (§4.5).
4. **Stable across eras** only if both eras give the same rule-2 reading.
   Opposite readings are reported as **"not stable across eras"**.
5. **The intervals assume independent events.** Breaks a few days apart are
   not fully independent, so the intervals are approximate and somewhat too
   narrow. This is stated beside the result.
6. **Nothing here is an entry rule or an edge.** A high failure rate does not
   mean fading breaks pays. R14 (fading levels) was refuted on GBP pairs, and
   R43 (confirming breaks with closes) refuted today.

## 6. Tests before the run

`tests/test_gold_breakout_study.py`, on synthetic bars:
- a planted failed break and a planted held break, counted exactly (up and down,
  both definitions);
- a swing is not a level until 3 closes after it;
- each level fires once; eras never share swings;
- a row in the exam span, or a file with the wrong hash, is refused;
- the Wilson and Newcombe intervals reproduce published values;
- the ATR series' last value equals `markup_swings.atr`.

A mutation run shows the tests catch: a wrong failure window, a level used before
confirmation, a reused level, ATR taken on day d instead of d − 1, and the
exam-span refusal removed.

## 7. Run

Once, through `scripts/reality_run.py --no-env script <worktree absolute path>`
(no network needed), with the archive root as the argument. Output: verbatim
to validation_log; written up in `studies/gold_breakout_report.md` in plain
words; a finding number in `foundation/research_findings.md`; the inventory row
"Breakouts holding" updated.
