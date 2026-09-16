# Spec: level-source repair (R1–R5 of the 2026-09-16 team ruling)

**Status:** team-directed 2026-09-16, Step 1 of a three-step sequence.
Step 0 (interim neutralization, authorized standalone) landed on `main`
as `1f7d2ac`. Step 2 (integration inventory) is read-only and runs after
this merges.
**Branch:** `feat/level-source-repair`. **Merge held for team review.**

**Protected files touched (3 of 19):** `entry_confirmation.py`,
`levels_context.py`, `intraday_context.py`.
**Free-zone files touched:** `scripts/artifact_freshness.py`, tests,
`AGENTS.md`.
`oanda_feed.py` is NOT changed (per ruling).

---

## 1. Defects

### DEFECT 1 — orphaned read (PRIMARY, ruling R1)

`entry_confirmation.py:180-190` (PROTECTED) reads `last_run.json` and
feeds `levels_as_list()` into the M15 level-proximity check that gates
`m15_trigger`. The file's only writer is `shadow/market_brain.py`
(lines 1734, 2449, 3429, 3529) — QUARANTINED 2026-07-29. Nothing on the
live path has written it since; content froze at 2026-06-10
(`price 1.9076`).

Violates the AGENTS.md quarantine contract: *"never cite their output…
their priors are not evidence."* A PROTECTED live-core module was
consuming a quarantined module's artifact.

Degradation was backwards: `entry_confirmation` treats *level
unavailable* as a PASS, so a DELETED file degrades gracefully while a
PRESENT-but-stale file is trusted. Step 0 restored the graceful mode by
renaming the file aside; this spec removes the dependency.

### DEFECT 2 — no pair keying (ruling R2)

`last_run.json` holds ONE pair's levels with no instrument key, while
`get_key_levels()` is pair-parameterized.

Reproduced 2026-09-16 before acting (standing rule 5): GBP_JPY at
208.8685 against stored levels 1.8718–1.90906, tolerance
`_M15_LEVEL_PROXIMITY_PIPS` (25) × `pip_size` (0.01) = 0.25. Minimum
achievable distance ≈ 207.0 against a 0.25 tolerance — `near_key_level`
could never be True. And because the file EXISTED, `_level_available`
was True, so the code took the gating `else` branch
(`entry_confirmation.py:227-231`, *"not near a key level"*) rather than
the degraded-pass branch.

**Consequence: `m15_trigger`, and therefore `entry_ready`, could never
be True on GBP_JPY** — silently, since the file froze. One pair's entry
path was dead for 98 days with no error, no log line, and no failing
test. Recorded as a first-class defect, not a footnote.

### DEFECT 3 — weekly semantics (ruling R5)

`levels_context.py:10` documents `weekly_high`/`weekly_low` as *"current
week's extremes (key swing targets)"*. `levels_context.py:73-79` calls
`get_weekly_bars(count=2)` and takes `.iloc[-1]`; the feed filters
incomplete bars, so the value returned is the last COMPLETED week.

Observed 2026-09-16 ~08:00 UTC: returned `weekly_high` 1.88838 (week of
Sep 7–11) against spot 1.88975 — a "swing target" price had already
traded through. Current week-to-date was high 1.89512 / low 1.88617.

### DEFECT 4 — `asian_*` is not pair-parameterized (NEW — blocks R1)

Found while specifying R1; not in the team ruling. **R1 cannot be
implemented correctly without it.**

`levels_context.py:106-107` calls `get_intraday_context()`, whose
signature ([intraday_context.py:60](../../intraday_context.py#L60))
takes NO pair argument and internally calls `get_hourly_bars(count=96)`
with the feed's default pair — always GBPAUD. Every other level in
`get_key_levels` honors the `pair` argument; `asian_high`/`asian_low`
do not.

Proven 2026-09-16 — `get_key_levels("GBPJPY")` returns:

```
prev_day_high 209.231   prev_day_low  208.252
weekly_high   211.224   weekly_low    207.100
session_high  209.021   session_low   208.724
asian_high      1.89232 asian_low       1.88924   <-- GBP/AUD
```

`levels_as_list` then emits
`[1.88924, 1.88932, 207.1, 208.252, 208.724, 209.021, 209.231, 211.224]`
— a mixed-scale list from a PROTECTED module.

**Honest severity: latent, not active.** The contaminants sit ~207 below
any JPY price, so they cannot currently produce a false proximity match,
and `nearest_support`/`nearest_resistance` happen to return correct
answers today. The defect matters because R1 wires `get_key_levels` into
the live entry path — from that commit forward the contaminated values
ARE in the live level set — and because the function signature lies
about being pair-specific.

---

## 2. Fixes

### FIX 1+2 (R1) — `entry_confirmation` calls `get_key_levels` directly

Replace the `last_run.json` read at `entry_confirmation.py:180-190`
with a direct, pair-keyed call. `oanda_pair` is already in scope at
`entry_confirmation.py:112` (`pair_cfg.instrument.replace("_", "")`),
which is exactly the format `get_key_levels` expects.

```python
_level_available = False
_levels: List[float] = []
try:
    from levels_context import get_key_levels, levels_as_list
    _levels = levels_as_list(get_key_levels(oanda_pair))
    _level_available = bool(_levels)
except Exception:
    _level_available = False
```

The file dependency is removed entirely — no reader, no staleness class,
nothing to add to a watchlist. This resolves DEFECT 1 and DEFECT 2 in
one change. The `json` and `Path` imports local to that block go with it.

`last_run.json.orphaned-2026-09-16` is retained as an artifact and is
never read again.

### FIX 3 (R5) — weekly semantics

Per the ruling, prior-week extremes are legitimate levels and are kept
under an honest name; current-week extremes are added.

1. **Rename** `weekly_high`/`weekly_low` → `prev_week_high`/
   `prev_week_low`. Docstring corrected to *"previous completed week's
   extremes"*. Safe: no live consumer reads these keys by name —
   `levels_as_list`, `nearest_resistance` and `nearest_support` all
   iterate values generically, and the identically-named keys in
   `shadow/market_brain.py:139-140` belong to that module's own dict and
   are unaffected.
2. **Add** `current_week_high`/`current_week_low`, aggregated from this
   week's COMPLETED daily bars:

   ```
   cur_open = <last completed weekly bar timestamp> + 7 days
   this_week = daily[daily.index >= cur_open]
   current_week_high = this_week.High.max()   # None if empty
   current_week_low  = this_week.Low.min()    # None if empty
   ```

   Today's still-forming session is already covered by
   `session_high`/`session_low`, so the pair composes to a complete
   week-to-date range without reading an incomplete bar.
3. **Empty-week case:** between the weekly open and the first completed
   daily bar, `this_week` is empty and both keys are `None` — consistent
   with the module's standing contract that any level which cannot be
   fetched is `None`.

`oanda_feed.py` is unchanged; the incomplete-bar filter stays intact
everywhere.

### FIX 4 — pair-parameterize the Asian range

`get_intraday_context(pair: str = "GBPAUD")`, threading `pair` into its
`get_hourly_bars` call. A defaulted parameter is backward compatible for
both existing callers (`levels_context.py:107` live,
`shadow/market_brain.py:256` quarantined, which keeps the default).
`get_key_levels` passes its own `pair` through.

Chosen over computing the Asian range inside `levels_context` so that
the two modules cannot drift apart on what "the Asian range" means. The
root cause is a pair-specific function without a pair parameter; the fix
addresses the root rather than routing around it.

---

## 3. Guards

### GUARD A (R3) — freshness covers the read side

`scripts/artifact_freshness.py` currently watches five artifacts, all
write-side. That is why this defect was invisible.

Add an explicit **read-side inventory**: every artifact the live path
reads, each carrying either a cadence or an explicit
`NO_CADENCE(<reason>)` marker. Only cadence-bearing entries can report
STALE; `NO_CADENCE` entries are listed so the boundary is documented
rather than assumed.

Initial inventory, with honest cadences:

| artifact | side | cadence | note |
|---|---|---|---|
| `calendar.csv` | read+write | 192h | already watched |
| `storylines.md` | read | 216h | already watched |
| `trades.csv` | read | `NO_CADENCE` | event-driven — weeks without a trade is normal, a cadence here would false-alarm |
| `.env` | read | `NO_CADENCE` | credentials, not an evidence artifact |

After FIX 1 there is no `last_run.json` entry to add — R1 deletes the
staleness class instead of monitoring it, which is the stronger outcome.

A test asserts every path the live path reads appears in the inventory,
so a new read cannot be introduced silently.

### GUARD B (R4) — quarantine-boundary test

New test asserting no live-core module imports from, or references a
path under, `shadow/` or `legacy_validators/` — string literals
included, not just imports.

**Honest limit, stated so this test is not mistaken for the control it
resembles: it would NOT have caught DEFECT 1.** `entry_confirmation`
referenced `last_run.json` — a bare filename at the repo root, with no
`shadow/` substring anywhere. The artifact was written by a quarantined
module but did not live in a quarantined path.

The control that WOULD have caught it is orphan detection: *every file
artifact a live module reads must have a live writer.* That is precisely
what Step 2's integration inventory produces. **Recommendation for the
team: after Step 2 reports, promote its orphan rule into a test.** Guard
B is worth having, but it closes a narrower hole than the one this
finding exposed.

---

## 4. Tests (pinned, per defect)

Gate 1 — controlled input:

- **D1:** `entry_confirmation` never opens `last_run.json`; a file
  planted at that path does not change `_level_available`.
- **D2:** `get_key_levels` called through the entry path with
  `GBP_JPY` yields levels all within one order of magnitude of a JPY
  price; with `GBP_AUD`, of an AUD price. Pin the regression directly:
  a GBP_JPY entry check with an in-direction M15 engulfing CAN reach
  `m15_trigger = True`.
- **D3:** `prev_week_high`/`prev_week_low` equal the last completed
  weekly bar; `current_week_high`/`current_week_low` equal the max/min
  of this week's completed dailies; both are `None` on an empty week;
  the old `weekly_*` keys are gone from the returned dict.
- **D4:** `get_key_levels("GBPJPY")` contains NO value below 100, and
  `get_key_levels("GBPAUD")` none above 100 — the mixed-scale assertion,
  pinned against fixed bars.
- **Guard A:** every live-path read appears in the inventory;
  `NO_CADENCE` entries never report STALE.
- **Guard B:** as described, with its documented limit in the test's
  own docstring.

Full suite must stay green (currently 1018 + shadow). Neither floor —
the banned-token display test, nor the stand-down consistency matrix —
is touched or weakened.

## 5. Gate 2 — REALITY (mandatory, both pairs)

Real OANDA, real files, run on the branch, actual output pasted into the
run report and `validation_log.md`:

- `get_key_levels` for BOTH pairs, full dict, showing every value
  correctly scaled — **GBP_JPY must show a correctly-scaled level set
  for the first time since the artifact froze.**
- A real `decision_brief.py GBP_AUD GBP_JPY` run, confirming no
  regression in rendered output.
- `scripts/artifact_freshness.py check` showing the read-side inventory
  live.

No mock results may appear in the REALITY section.

## 6. Gate 3 — PENDING LIVE CONFIRMATION

- The degraded-pass branch firing in production (carried forward from
  Step 0; requires an in-direction M15 engulfing).
- The first GBP_JPY `m15_trigger = True` in live scheduled output —
  the proof that DEFECT 2's silent kill is actually lifted. Only the
  market can perform this.

## 7. Out of scope

The one-week level horizon, and the unwired `find_confluence_zones`,
`nearest_resistance`, `nearest_support` and `get_round_number_levels`
in `levels_context.py`. Raised as context in the finding; a level-map
spec is its own piece of work and is not bundled into a defect repair.
