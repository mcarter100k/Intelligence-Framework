# Spec: how deep gold's first pullback goes (descriptive)

**Status:** FROZEN 2026-11-16, owner request ("go on C1 and C3").
`docs/gold_plan.md` Phase C, study C3. Committed before the runner
(`studies/gold_pullback_depth_study.py`) exists and before any gold pullback
statistic is computed. The run happens once, after the runner is committed,
and its output goes to validation_log verbatim, whatever it says.

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar (§2 checks this). **Descriptive only:
no entries, no R, no costs, no claim that anything pays.**

## 1. Question and why

**After gold makes a big move off a 20-day high or low, how far back does the
first pullback go: 23.6%, 38.2%, 50% or 61.8% of the move?** Pullbacks in
rallies and bounces in falls separately, per era.

- **The decision it informs:** where the owner draws zones on a gold
  Fibonacci, and where a stop is safe from an ordinary pullback
  (`foundation/chart_reading_method.md` §3). The only figures we have are
  GBP's (R39: 38.2% reached by 81–90% of first pullbacks, 50% by 66–74%,
  2005–2013). Nothing says gold behaves the same.
- **Why rallies and falls apart:** gold rose for most of both eras, so a
  pooled figure would mostly describe rallies (gold plan §1 rule 4). How a
  fall's bounce behaves is what a short needs.

## 2. Data

| File (under `~/intel_study_archives/research_archive_legs/`) | sha256 |
|---|---|
| `XAU_USD_D.csv` | `6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca` |
| `XAU_USD_H4.csv` | `e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c` |

- Both hashes equal the archive manifest's `files` entries (checked
  2026-11-16). The runner refuses to run on any other bytes.
- **Eras = the archive's span labels:** STUDY (gold from 2006) and USED
  (2021-04-26 → 2026-09-09). **FORWARD is not used** (the live shadow
  ledger's span, data_map_spec §1).
- **Gold starts at the 2006-03-21 session** (rows opening at or after
  2006-03-20T22:00Z), as in C2 (gold plan T2).
- **No 2014-01-01 → 2021-04-25 row is read.** The runner refuses any row
  dated in that span.
- **Each era is processed on its own:** the detector, the daily ATR and the
  13-week warm-up restart at each era's first bar. Nothing carries across the
  2014–2021 gap.
- STUDY bars are already converted by the archive (Sunday sessions folded
  into Monday); USED bars are OANDA's modern candles. Nothing is re-converted.

## 3. The leg and the touch (R39's definition, reused unchanged)

The detector is `studies/first_pullback_study.find_entries`, imported and
called unchanged, with `use_trend=False`, on the same parameters R39 used:

- **Anchor:** an H4 bar whose low is strictly below every low of the previous
  119 bars (a new 120-bar low, about 20 sessions).
- **Impulse:** the extreme B is the highest high of the bars after the anchor.
  The leg **qualifies** once B − A ≥ 2.0 × daily ATR, where the daily ATR is
  the simple mean true range of the 14 sessions completed before the anchor's
  session (`first_pullback_study.bar_context`, unchanged), fixed at the anchor.
- **The level** for a depth f is B − f × (B − A), with B the running extreme
  as of the previous close.
- **Reached:** the first bar after qualification whose low reaches the level,
  within 60 H4 bars of the anchor (about 10 sessions). It consumes the leg.
- **Expired:** 60 bars pass without reaching it. **Replaced:** a new 120-bar
  low comes first.
- **Falls:** the exact mirror, by negating prices
  (`first_pullback_study.mirrored`, unchanged). In a fall, "reached 38.2%"
  means the bounce climbed back 38.2% of the drop.
- Anchors before the daily ATR and the 13-week direction exist are warm-up
  and skipped, exactly as in R39 (the direction itself is not used).

**Depths:** 23.6%, 38.2%, 50%, 61.8% (the question), plus 78.6% and 100%
(the whole move given back) as secondaries. Each depth runs its own detector,
so the qualified legs are the same at every depth.

## 4. Reported

For each era × side (rallies, falls, both) × depth:
1. Qualified legs, reached, expired, and **cut off**: qualified legs whose
   60-bar window runs past the era's last bar without a touch. Cut-off legs
   are excluded from the share.
2. The reached share (reached ÷ (reached + expired)) with a 95% Wilson
   interval and its reading (§5).

Also:
3. The leg counts per era and side: anchors, warm-up, replaced, expired
   before qualifying.
4. Rallies minus falls, per era and depth: the difference in reached share
   with a 95% Newcombe (hybrid score) interval.
5. A check that the shares never rise with depth (a leg that reaches 50% has
   reached 38.2%). A failure is printed loudly and the run is not used.
6. Qualified legs per calendar year, per side.
7. **Context, not a test:** R39's GBP figures for 38.2% and 50% (quoted from
   `foundation/research_findings.md`, not recomputed) beside gold's STUDY
   figures.

## 5. Reading rules (fixed before the run)

1. **Any cell with fewer than 20 legs** (reached + expired) is INSUFFICIENT:
   its numbers are shown and never read.
2. **"Most reach it"** if the share's 95% lower bound is above 50%. **"Most
   don't"** if its upper bound is below 50%. Otherwise **"about even"**.
3. **Rallies and falls differ** at a depth only if the Newcombe interval
   excludes 0, both cells with N ≥ 20.
4. **Stable across eras** only if both eras give the same rule-2 reading.
5. **The intervals assume independent legs.** A rally leg and a fall leg can
   overlap in time, and legs a few days apart are related, so the intervals
   are approximate and somewhat too narrow. Stated beside the result.
6. **Shares are lower bounds for "eventually":** a leg that qualifies late in
   its 60-bar window has less time to pull back.
7. **Nothing here is an entry rule or an edge.** Reaching a level is not
   holding it: buying the first touch showed no edge on the GBP pairs (R37,
   R38), and fading levels was refuted (R14).

## 6. Tests before the run

`tests/test_gold_pullback_depth_study.py`, on synthetic bars:
- a planted rally leg that reaches 38.2% but not 50% is counted reached at
  23.6% and 38.2% and expired at 50% and deeper;
- the same leg mirrored is counted the same way as a fall;
- a leg whose window runs past the last bar is cut off, not expired;
- eras never share a leg, an ATR or a warm-up (the second era starts in
  warm-up);
- the monotonic check fires on a planted violation;
- the Wilson and Newcombe intervals reproduce published values (shared with
  C2's functions);
- a row in the exam span or a file with the wrong hash is refused, and a row
  before the gold start is skipped.

A mutation run shows the tests catch: cut-off legs counted as expired, falls
not mirrored, the context carried across eras, the exam-span refusal removed,
and the hash refusal removed.

## 7. Run

Once, through `scripts/reality_run.py --no-env script <worktree absolute path>`
(no network needed), with the archive folder as the argument. Output:
verbatim to validation_log; written up in
`studies/gold_pullback_depth_report.md` in plain words; a finding number in
`foundation/research_findings.md`; the inventory row "Pullback depth" updated;
`foundation/chart_reading_method.md` §3 gets gold's figures beside R39's.
