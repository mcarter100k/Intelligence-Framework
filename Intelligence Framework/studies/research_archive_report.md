# Research archive — build report (2026-11-05)

**What it is:** one labelled, hash-pinned history of GBP/AUD and GBP/JPY
(daily, 4-hour and hourly OANDA mid prices), built around the sealed exam.
It follows the team ruling of 2026-11-05: **A + D**, recorded in
`docs/specs/data_map_spec.md` §11.6.

- **Code:** `studies/research_archive.py`, which builds, verifies and loads it.
- **Location:** `~/intel_study_archives/research_archive/`, outside the repo.
- **Scope:** research only. The live framework never reads it.

## Spans (by session day: the New York date of open + 7 h)

| Span | Sessions | Role |
|---|---|---|
| STUDY | 2005-01-03 → 2013-12-30 | learning; old convention, converted by the approved weekend rule |
| USED | 2021-04-27 → 2026-09-09 | learning only, never proof |
| FORWARD | 2026-09-11 → 2026-11-05 (build date) | description only; never a test for an idea designed on it |
| none | 2013-12-31 → 2021-04-26 (embargo + SEALED EXAM) and 2026-09-10 | not stored |

- **The 2026-09-10 boundary session** belongs to no span. This is the first
  application of §11.6 rule 5, because §1 gives that day to both USED and
  FORWARD. It is **flagged for the team to confirm.**
  - **Confirmed by the team, 2026-11-05:** the day is stored in neither
    period. One day per pair is a trivial cost for an unambiguous seam.
- **The reserved label `SEEN_NOT_PROOF`** is for a spent exam (§11.6 rule 4).
  It is unused.

## Files (manifest `2026-11-06T05:38:12+00:00`)

| File | Rows | STUDY | USED | FORWARD | sha256 |
|---|---|---|---|---|---|
| GBP_AUD_D.csv | 3,778 | 2,343 | 1,395 | 40 | `24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6` |
| GBP_AUD_H1.csv | 90,514 | 56,077 | 33,477 | 960 | `f170a0403ac306de24f3b5ca4910a6b66fec009da5de335e9f4f1a1ff8b36768` |
| GBP_AUD_H4.csv | 22,640 | 14,030 | 8,370 | 240 | `2c6ce7655335879e5312260abfd1d96a7e469ae72fd6d36246e9c2475715a1d4` |
| GBP_JPY_D.csv | 3,778 | 2,343 | 1,395 | 40 | `fff4fe7f8f0ca983d196970cd190a2148facc253ef70627708d35a09bab7417e` |
| GBP_JPY_H1.csv | 90,510 | 56,073 | 33,477 | 960 | `4a73a71b5195d84f18fb58ef417ca41ba6e7555fd65c6cb9f7bd778ca98f8d73` |
| GBP_JPY_H4.csv | 22,638 | 14,028 | 8,370 | 240 | `80c608e7c5f0efb68d0c47ebde60da15c98320e309ba63f8e16515f1611c7ebc` |

**Sources, all hash-checked before assembly:**
- STUDY daily and 4-hour: `us_event_reaction_data/`.
- STUDY hourly: `session_movement_data/` (session movement study, Phase 1).
- USED and FORWARD: `modern_data/`, fetched 2026-11-05 through
  `reality_run.py` (exit 0, stderr empty, project unchanged by hash).
  - 396 requests.
  - The first candle opens 2021-04-26 14:00 PDT (21:00 UTC, the first USED
    session).
  - **0 candles opened before it** (checked on receipt; any would have
    aborted the run before writing).
  - **0 weekend-session candles.**

## Verification (`verify`, run through `reality_run.py --no-env`: exit 0, stderr empty, project unchanged)

**Integrity, every file:**
- hash matches the manifest;
- 0 span-label mismatches;
- 0 bars in the sealed block;
- 0 bars in the boundary embargo;
- 0 weekend-session bars;
- 0 reserved labels.

**Consistency, every span of both pairs:**
- Hourly bars rebuild every 4-hour bar exactly: STUDY 14,030 / 14,028,
  USED 8,370 / 8,370, FORWARD 240 / 240.
- Daily high and low equal the session's 4-hour extremes within 0.5 pip, and
  the open and close are exact, in every session: STUDY 2,343, USED 1,395,
  FORWARD 40.

**Gaps:**
- STUDY: holidays only (session movement study, Phase 1).
- USED: 9 runs, 171 hours.
  - Seven are the 24-hour Christmas and New Year closures, 2022–2026.
  - Two are late Sunday opens: 2021-11-21 (2 h) and 2023-01-01 (1 h).
- FORWARD: none.

**Positive controls, run on a copy of the real archive:**
- **Planted sealed bar:** a 2017 bar, with the manifest re-hashed so that
  only the content checks could catch it. verify → FAIL. Restored → PASS.
- **Price defects:** +1 pip on the bar that sets a 4-hour high, 3 per span.
  Caught **9 of 9**.
- **Tampered file without a re-hash:** FAIL.
- **Loader:** it refuses `SEALED` and an empty span set. On GBP/JPY hourly it
  returns STUDY 56,073 bars, USED 33,477, FORWARD 960, and all three
  together 90,510.

**Limit, stated:**
- verify checks that the timeframes agree with each other; it cannot check
  them against a second source.
- A wrong hourly value that leaves its 4-hour and daily bars unchanged is
  undetectable. The first, badly aimed price control, a +1 pip on a bar
  that was not its bucket's high, passed for exactly this reason.
- The STUDY feed itself was checked against the held 4-hour bars in the
  session movement study. That check has the same limit as this one (below).

**What "consistent" leaves unverified** (added 2026-11-05, team review):
- **What each check proves.** The hourly → 4-hour check proves four values
  per 4-hour block: the first hourly open, the last hourly close, the single
  highest hourly high and the single lowest hourly low. The 4-hour → daily
  check does the same one level up.
- **What it leaves unproven:**
  - **Other hourly highs.** Every other hourly high is only proven to be at
    or below its block's high, by any amount.
  - **Other hourly lows.** The same holds for lows, above the block's low.
  - **Intermediate opens and closes.** These are not checked at all.
  - **Within-block timing.** Which hour inside a block made the block's
    high or low is not proven.
- **What this means for users of the archive:**
  - **Hourly range and timing figures** rest mostly on unproven values.
    Examples: each hour's high minus low, the hour an extreme formed, hourly
    ATR.
  - **4-hour and daily values** rest on proven ones.
  - **The session movement study's Q1** is exactly such a figure.
- **Both sides are OANDA data,** so an error in OANDA's own records would
  pass.
- **What would close the gap:** a second, independent data source for the
  same spans, compared hour by hour. None has been sourced.

## How to use it

```python
from research_archive import load
bars = load("~/intel_study_archives/research_archive", "GBP_JPY", "H1", spans={"STUDY", "USED"})
```

- Name the spans every time.
- Report which spans a result used.
- Remember that none of them is proof: STUDY and USED are learning, and
  FORWARD is the live ledger's job.

## Full output (verbatim)

### assemble
```
GBP_AUD_D.csv: rows 3778; STUDY 2343; USED 1395; FORWARD 40; dropped {'boundary_embargo': 1}
GBP_AUD_H4.csv: rows 22641; STUDY 14030; USED 8370; FORWARD 241; dropped {'boundary_embargo': 6}
GBP_AUD_H1.csv: rows 90521; STUDY 56077; USED 33477; FORWARD 967; dropped {'boundary_embargo': 24}
GBP_JPY_D.csv: rows 3778; STUDY 2343; USED 1395; FORWARD 40; dropped {'boundary_embargo': 1}
GBP_JPY_H4.csv: rows 22639; STUDY 14028; USED 8370; FORWARD 241; dropped {'boundary_embargo': 6}
GBP_JPY_H1.csv: rows 90517; STUDY 56073; USED 33477; FORWARD 967; dropped {'boundary_embargo': 24}
GBP_AUD_H4.csv: trimmed 1 bar(s) after the last complete session 2026-11-05
GBP_AUD_H1.csv: trimmed 7 bar(s) after the last complete session 2026-11-05
GBP_JPY_H4.csv: trimmed 1 bar(s) after the last complete session 2026-11-05
GBP_JPY_H1.csv: trimmed 7 bar(s) after the last complete session 2026-11-05
FORWARD last session 2026-11-05; manifest written
```

### verify
```
GBP_AUD_D.csv: hash OK; rows 3778 (manifest 3778); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_AUD_H1.csv: hash OK; rows 90514 (manifest 90514); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_AUD_H4.csv: hash OK; rows 22640 (manifest 22640); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_JPY_D.csv: hash OK; rows 3778 (manifest 3778); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_JPY_H1.csv: hash OK; rows 90510 (manifest 90510); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_JPY_H4.csv: hash OK; rows 22638 (manifest 22638); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0

## GBP_AUD
STUDY: H1->H4 compared 14030, exact 14030, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2343 sessions, high/low within 0.5 pip 2343, open+close exact 2343, D1 with no H4 0 | H1 gap runs 18 (227 h), runs of 3 h or more 13
USED: H1->H4 compared 8370, exact 8370, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1395 sessions, high/low within 0.5 pip 1395, open+close exact 1395, D1 with no H4 0 | H1 gap runs 9 (171 h), runs of 3 h or more 7
    gap 2022-12-25 14:00 PST -> 2022-12-26 14:00 PST  24 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 14:00 PST  24 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 14:00 PST  24 h
    gap 2024-12-24 14:00 PST -> 2024-12-25 14:00 PST  24 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 14:00 PST  24 h
    gap 2025-12-24 14:00 PST -> 2025-12-25 14:00 PST  24 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 14:00 PST  24 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 0 (0 h), runs of 3 h or more 0

## GBP_JPY
STUDY: H1->H4 compared 14028, exact 14028, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2343 sessions, high/low within 0.5 pip 2343, open+close exact 2343, D1 with no H4 0 | H1 gap runs 13 (231 h), runs of 3 h or more 12
USED: H1->H4 compared 8370, exact 8370, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1395 sessions, high/low within 0.5 pip 1395, open+close exact 1395, D1 with no H4 0 | H1 gap runs 9 (171 h), runs of 3 h or more 7
    gap 2022-12-25 14:00 PST -> 2022-12-26 14:00 PST  24 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 14:00 PST  24 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 14:00 PST  24 h
    gap 2024-12-24 14:00 PST -> 2024-12-25 14:00 PST  24 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 14:00 PST  24 h
    gap 2025-12-24 14:00 PST -> 2025-12-25 14:00 PST  24 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 14:00 PST  24 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 0 (0 h), runs of 3 h or more 0

VERIFY: PASS
```
