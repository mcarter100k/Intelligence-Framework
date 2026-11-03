# studies/: the research and methodology record

Standalone research scripts and their reports. They are run by hand, are
never imported by the live code, and are **never deleted**: validation_log.md
and foundation/ cite them by file name. Each one adds the project root to
`sys.path` so it can import the live modules read-only.

Any study that calls OANDA or runs the real brief must run through
`scripts/reality_run.py script studies/<name>.py`. That runs it in a temp
directory and fails if the project changed. `historical_scenario_replay.py`
refuses to run inside the project.

## Decision channel (2026-10-17 onward)

| Script | Report | Question |
|---|---|---|
| `decision_channel_inventory.py` | `decision_channel_inventory_report.md` | What decision history exists, and how many independent episodes can be graded? (pre-registered: docs/specs/decision_channel_measurement_spec.md) |
| `decision_gate_replay.py` | `decision_gate_replay_report.md` | How many DECISION notifications the market-closed gate removes, replayed on real day-log text |
| `decision_channel_followups.py` | `decision_channel_followups_report.md` | Every open-market directional decision; episode count under both concurrent-run handlings |
| `long_side_diagnosis.py` | `long_side_diagnosis_report.md` | Why all 16 open-market decisions were SHORT: the funnel, plus a mirror test of the decision path |
| `missed_moves.py` | `missed_moves_report.md` | Every move of 2+ normal days' range the framework sat out, lined up with what it said; "not running" kept apart from "stood aside" (descriptive; hindsight size is not profit) |

## GBP/AUD profile series (prior-session; committed 2026-10-18 for citation integrity, not re-verified)

foundation/ cites these about 20 times. They were committed exactly as found, each with a two-line header saying so.

| Script | Report |
|---|---|
| `gbpaud_personality_profile.py` | `gbpaud_personality_profile_report.md` |
| `gbpaud_profile_followup.py` | `gbpaud_profile_followup_report.md` |
| `gbpaud_scouting_verify.py` | `gbpaud_scouting_verify_report.md` |
| `gbpaud_secondplay_scouting.py` | `gbpaud_secondplay_scouting_report.md` |
| `gbpaud_weekly_opportunity.py` | `gbpaud_weekly_opportunity_report.md` |

## Data and feed

| Script | Report | Question |
|---|---|---|
| `stage2_source_convert_gate.py` | `stage2_gate_report.md` | Stage 2 of docs/specs/data_map_spec.md: source conversion and the feed-overlap gate |
| `instrument_probe.py` | `instrument_probe_report.md` | Which cross-market instruments the live account offers, their daily history, and today's financing rates (owner-approved, 2026-11-01) |
| `us_event_reaction_test.py` | `us_event_reaction_result.md` (after the run) | Do scheduled US releases (FOMC, CPI, jobs report) widen GBP/JPY and GBP/AUD daily ranges? Pre-registered: docs/specs/us_event_reaction_spec.md; event table `us_events_2005_2013.csv` |
| `shadow_cost_regrade.py` | `shadow_cost_regrade_report.md` | The shadow ledger's graded episodes re-graded with spread and financing, read-only, beside the frozen raw R (proposal step 3) |

## Premises tested (most were refuted at honest N; see foundation/research_findings.md)

| Script | Question |
|---|---|
| `precursor_study.py` | Do structural precursors come before the big moves? (reverse methodology; negative result) |
| `structure_engine_study.py` | Does consolidation followed by breakout have an edge on H4? (v2 detector) |
| `structure_primary_headtohead.py` | Does the framework need trend strength (ADX) for confirmation, or is structure enough? |
| `level_fade_study.py` | Are turns knowable by location (key levels) even when their timing is not? |
| `hypothesis_volatile_entries.py` | Is a "no clear direction" daily chart a better or worse place to enter? |
| `trade_frequency_backtest.py` | How often does the framework actually issue a tradeable signal? |

## Threshold validation

| Script | Question |
|---|---|
| `validate_thresholds_v2.py` | Daily trend-strength thresholds, re-validated with non-overlapping windows (the current method) |
| `validate_h4_thresholds.py` | The same audit for the 4-hour thresholds |
| `validate_confluence_weights.py` | Weight updates read from trade_signal_log.csv |

## Harness

| Script | Note |
|---|---|
| `historical_scenario_replay.py` | Replays known market events through the brief. Only the D1/H4/weekly bars are historical, so its output is not evidence. Other studies import its `_fetch_historical` |

The invalidated v1 validators (overlapping windows) were removed on
2026-09-29 and survive only in git history: `git show 4eb9241^:"Intelligence Framework/legacy_validators/README.md"`.
