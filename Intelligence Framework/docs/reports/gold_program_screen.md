# Gold price-action program: M41 screen (owner rulings E1–E8, 2026-11-17)

**What this is:** the screen the owner asked for before any program plan or
spec. For every proposed rule: its episode count on gold's 2006–2013 STUDY bars
(counts only; no outcome was looked at), its smallest detectable effect, and the
90% upper bound of its GBP result where one exists. Under methodology M41, a rule
whose smallest detectable effect exceeds the best available estimate's upper
bound is shelved before it is specced. Plus the horizon check (E7).

**Script:** `studies/gold_program_screen.py`, run once through
`scripts/reality_run.py --no-env` (exit 0, stderr empty, project unchanged by
hash). The run used a scratch copy that differs only in its two import paths.
Full output in the appendix.

## 1. Episode counts (E2: real bar index, episodes not sessions)

- GBP replications reuse the original detectors unchanged: first pullback
  (`first_pullback_study.find_entries`, 13-week trend, 30-bar episodes), hourly
  breakout (`breakout_confirmation_study.find_events` and `retest_fill`, 24-bar
  episodes), daily/weekly breaks (`htf_breakout_study` levels, trend and events,
  120-bar episodes).
- R44's count is an **upper bound**: it is taken before R44's obstacle and
  stop-width filters.
- Never-tested patterns use **provisional definitions**, written in the script,
  that exist only to count: H4 bars, the markup's swing rule (k = 4), 30-bar
  episodes. A spec would fix each definition before any outcome is seen.
- Any 30-bar rule on gold's H4 STUDY bars has at most **403** episodes.

## 2. The screen (provisional threshold for 24 tests, SD 1.2R)

| Rule | Gold episodes | Smallest detectable effect (K = 24) | GBP 90% upper bound | M41 reading |
|---|---|---|---|---|
| R37/R38 first pullback, 38.2% | 25 | +0.888R | +0.140R (GBP/AUD), +0.266R (GBP/JPY) | **Shelved:** out of reach |
| R37/R38 first pullback, 50% | 22 | +0.946R | +0.276R, +0.383R | **Shelved** |
| R43 hourly breakout, A | 1,287 | +0.124R | −0.114R | **Shelved:** bound below zero |
| R43 hourly breakout, B | 1,168 | +0.130R | −0.058R | **Shelved** |
| R43 hourly breakout, C | 877 | +0.150R | −0.020R | **Shelved** |
| R44 daily/weekly breaks, B | ≤ 50 | +0.628R | −0.184R, −0.171R | **Shelved** |
| R44 daily/weekly breaks, C | ≤ 31 | +0.797R | −0.113R, −0.096R | **Shelved** |
| R46 15-minute entries | not counted (no gold 15-minute data) | — | −0.056R, −0.215R, −0.128R | **Shelved:** bound below zero whatever N |
| R14 level fade | not counted (its detector is tied to the live framework's structure code and 2023–2026 data) | — | none: R14 predates episode-based bounds (median −1R, win 50%, overlapping rows) | M41 cannot apply |
| Double bottom/top: neckline break | 178 | +0.333R | none | M41 cannot apply |
| Double bottom/top: neckline retest | 136 | +0.381R | none | M41 cannot apply |
| Head and shoulders: neckline break | 38 | +0.720R | none | M41 cannot apply |
| Pin bar, anywhere | 212 | +0.305R | none | M41 cannot apply |
| Pin bar at a swing level | 57 | +0.588R | none | M41 cannot apply |
| Engulfing, anywhere | 284 | +0.263R | none | M41 cannot apply |
| Engulfing at a swing level | 80 | +0.496R | none | M41 cannot apply |
| Trendline break | 300 | +0.256R | none | M41 cannot apply |
| Trendline bounce | 243 | +0.285R | none | M41 cannot apply |

**Caveat on the GBP bounds:** using a GBP result as gold's estimate assumes it
transfers to gold. That is the screen's weakest assumption, and the owner asked
for it.

## 3. What the screen leaves (E8)

**Read strictly, M41 shelves every GBP replication and passes no rule.** The
nine never-tested pattern cells and R14 are not shelved only because no
estimate exists for M41 to compare against.

**Their reach, honestly:**
- Their smallest detectable effects are **+0.19R to +0.95R** per trade, even at
  the smallest family (K = 2). At SD 0.8R instead of 1.2R, the best two
  (trendline break, 300 episodes; engulfing anywhere, 284) reach about +0.13R.
- The largest gross effect any price-action rule has shown in this framework is
  **+0.10R** before costs (R43 cell C, GBP/AUD), and gold's GMW-1 showed +0.027R.
- So every surviving rule needs an edge **2 to 30 times larger than anything
  this framework has ever measured** before the test could see it.

**Recommendation (owner's call):** treat the framework's measured price-action
effects (gross ≤ +0.10R) as the class estimate for rules with none of their
own. On that reading **nothing survives**. That is a finding about the search
space, not a failure: **gold's 2006–2013 history cannot resolve a price-action
edge of plausible size (below about +0.15R) for any rule rarer than about 500
episodes, and the only rules frequent enough (hourly breakouts) already failed
on GBP.**

**Levers that would change this, each the owner's or team's decision:**
- **Add 2021–2026 (USED) as verdict data for gold.** Roughly 1.7× the episodes,
  cutting the smallest detectable effect by about a quarter (trendline break
  from +0.194R to about +0.15R at K = 2, SD 1.2R; from +0.256R to about +0.20R
  at K = 24). It means relabelling a span the framework treats as
  learning-only, and it has already been looked at descriptively (sessions,
  move size, pullback depth, the timing sweep), though never for these rules'
  outcomes.
- **Open 2014–2021 (the sealed exam) for discovery.** That would spend the
  exam, so no; listed only to say why not.
- **Higher-frequency definitions** (hourly patterns): more episodes, but the
  hourly breakouts were the clearest GBP failures.

## 4. Horizon (E7)

Representative rule: GMW-1 B1's direction (with the 4–7 AM PT move), timed
exits with no stop, on **2021–2026 (learning data; the STUDY span was not
used)**, 1,151 days. R is per GMW-1's stop distance d.

| Exit | Gross | Net of $0.50 | SD | t (gross) | Always-long drift |
|---|---|---|---|---|---|
| Same day 1:00 PM PT (GMW-1's exit) | −0.014R | −0.045R | 0.77R | −0.59 | +0.013R |
| Same session close (2 PM PT) | −0.014R | −0.046R | 0.79R | −0.59 | +0.023R |
| +1 session close | −0.067R | −0.099R | 1.63R | −1.40 | +0.134R |
| +2 sessions | −0.080R | −0.112R | 2.19R | −1.24 | +0.264R |
| +5 sessions | −0.021R | −0.053R | 3.53R | −0.20 | +0.519R |
| +10 sessions | +0.012R | −0.020R | 5.17R | +0.08 | +1.113R |

**Reading:**
- The cost is fixed (0.032R a trade here), but the spread of outcomes grows
  roughly with the square root of the holding time: 0.77R same-day, 5.2R at
  ten sessions. A longer hold makes the cost smaller *relative to the noise*,
  not relative to the edge, and the smallest detectable effect grows in step
  with the SD.
- The signal shows no edge at any horizon (largest |t| 1.40).
- At longer horizons **drift dominates**: always-long earns +1.11R at ten
  sessions in this rising span. Any multi-day gold test must be judged against
  a drift-matched baseline (same-direction random entries over the same
  dates), or it will mistake gold's trend for a rule's edge.
- **Horizon is a design dimension for every spec:** state it from a reason,
  and pair a long horizon with a drift-matched baseline. One representative
  rule cannot pick a horizon for the others; this shows why it must be chosen
  deliberately.

## 5. Approved alongside (E4, E5)

- **Tier 2 descriptive gold facts** (no family cost): approved. Not yet started.
- **Hand-drawn zones: forward Friday scoring, from Friday 2026-11-20.** It is
  exploratory: 20 scored zones (about a month at six a week) only reaches the
  futility minimum; no prior estimate exists, so M41 cannot screen it. It is
  the owner's journal: **the only test in the program that measures the owner
  rather than the past.**

## Appendix: screen output (verbatim)

```
# Part 1: episode counts, gold 2006-03-21 -> 2013-12-30 (STUDY); no outcomes

H4 bars 12105; ceiling for any 30-bar-episode rule: 403
- R37/R38 first pullback to 38.2% with the 13-week trend: entries 26, episodes 25
- R37/R38 first pullback to 50.0% with the 13-week trend: entries 22, episodes 22
- R43 hourly breakout, cell A: entries 2606, episodes 1287
- R43 hourly breakout, cell B: entries 1895, episodes 1168
- R43 hourly breakout, cell C: entries 1224, episodes 877
- R44 daily/weekly level breaks with the daily trend, entry B: entries 65, episodes 50 (upper bound: before the obstacle and stop-width filters)
- R44 daily/weekly level breaks with the daily trend, entry C: entries 36, episodes 31 (upper bound: before the obstacle and stop-width filters)
- double bottom/top: neckline break: events 311, episodes 178
- double bottom/top: neckline retest: events 205, episodes 136
- head and shoulders (and inverse): neckline break: events 42, episodes 38
- pin bar (H4), anywhere: events 395, episodes 212
- pin bar at a swing level: events 68, episodes 57
- engulfing (H4), anywhere: events 830, episodes 284
- engulfing at a swing level: events 93, episodes 80
- trendline break: events 948, episodes 300
- trendline bounce: events 554, episodes 243

# M41 arithmetic: smallest detectable effect at 80% power, SD 1.2R
- R37/R38 first pullback 38.2%: N 25; K=24: +0.888R; K=6: +0.775R; K=3: +0.711R; K=2: +0.671R
- R37/R38 first pullback 50.0%: N 22; K=24: +0.946R; K=6: +0.826R; K=3: +0.758R; K=2: +0.715R
- R43 hourly breakout cell A: N 1287; K=24: +0.124R; K=6: +0.108R; K=3: +0.099R; K=2: +0.094R
- R43 hourly breakout cell B: N 1168; K=24: +0.130R; K=6: +0.113R; K=3: +0.104R; K=2: +0.098R
- R43 hourly breakout cell C: N 877; K=24: +0.150R; K=6: +0.131R; K=3: +0.120R; K=2: +0.113R
- R44 daily/weekly breaks, entry B (upper bound): N 50; K=24: +0.628R; K=6: +0.548R; K=3: +0.503R; K=2: +0.475R
- R44 daily/weekly breaks, entry C (upper bound): N 31; K=24: +0.797R; K=6: +0.696R; K=3: +0.639R; K=2: +0.603R
- double bottom/top: neckline break: N 178; K=24: +0.333R; K=6: +0.290R; K=3: +0.266R; K=2: +0.251R
- double bottom/top: neckline retest: N 136; K=24: +0.381R; K=6: +0.332R; K=3: +0.305R; K=2: +0.288R
- head and shoulders (and inverse): neckline break: N 38; K=24: +0.720R; K=6: +0.628R; K=3: +0.577R; K=2: +0.544R
- pin bar (H4), anywhere: N 212; K=24: +0.305R; K=6: +0.266R; K=3: +0.244R; K=2: +0.230R
- pin bar at a swing level: N 57; K=24: +0.588R; K=6: +0.513R; K=3: +0.471R; K=2: +0.444R
- engulfing (H4), anywhere: N 284; K=24: +0.263R; K=6: +0.230R; K=3: +0.211R; K=2: +0.199R
- engulfing at a swing level: N 80; K=24: +0.496R; K=6: +0.433R; K=3: +0.398R; K=2: +0.375R
- trendline break: N 300; K=24: +0.256R; K=6: +0.224R; K=3: +0.205R; K=2: +0.194R
- trendline bounce: N 243; K=24: +0.285R; K=6: +0.248R; K=3: +0.228R; K=2: +0.215R

# Part 2: horizon, USED 2021-04-27 -> 2026-09-09 (learning data), GMW-1 B1 direction, timed exits (no stop)
- same day 1 PM (GMW-1's exit): N 1151; gross -0.0135R; net of $0.50 -0.0453R; SD 0.773R; t (gross) -0.59; mean cost 0.0318R; always-long drift +0.0127R
- same session close (2 PM): N 1151; gross -0.0139R; net of $0.50 -0.0456R; SD 0.791R; t (gross) -0.59; mean cost 0.0318R; always-long drift +0.0229R
- +1 session: N 1151; gross -0.0672R; net of $0.50 -0.0990R; SD 1.627R; t (gross) -1.40; mean cost 0.0318R; always-long drift +0.1336R
- +2 sessions: N 1151; gross -0.0801R; net of $0.50 -0.1118R; SD 2.194R; t (gross) -1.24; mean cost 0.0318R; always-long drift +0.2638R
- +5 sessions: N 1151; gross -0.0211R; net of $0.50 -0.0529R; SD 3.525R; t (gross) -0.20; mean cost 0.0318R; always-long drift +0.5186R
- +10 sessions: N 1151; gross +0.0117R; net of $0.50 -0.0200R; SD 5.171R; t (gross) +0.08; mean cost 0.0318R; always-long drift +1.1132R
```
