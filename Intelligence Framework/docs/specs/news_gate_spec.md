# SPEC: pre-news stand-down gate (team approved 2026-07-29)

> Review record. Saved verbatim from the team's approval before building,
> per the process rule: protected-path specs become repo artifacts first.

Purpose: safety infrastructure, same class as the market-closed
gate. No edge claims, no direction prediction. The framework
declines to present its reading as valid inside a pre-release
window where its inputs are guaranteed to be repriced.

1. news_gate.py (live core, lean — do NOT promote or import
   anything from shadow/): reads calendar.csv. For a given
   instrument, returns whether a HIGH-impact event for that
   pair's own currencies (GBP, AUD for GBP_AUD; GBP, JPY for
   GBP_JPY — USD events deliberately out of scope, logged as a
   known v1 boundary) is within the next 2 hours; returns event
   name + minutes-until. Graceful degradation: calendar.csv
   missing or older than 7 days → gate INACTIVE, return a
   staleness note instead. Never block on bad data; never
   pretend coverage that isn't there.

2. no_trade_filter.py wiring: when the gate fires → stand-down,
   reason: "Major economic event ahead — <event> in <time>.
   Markets reprice violently around releases; standing aside
   until after." decision_brief renders it in REASON and the
   FULL PICTURE narrative in plain English. When the calendar
   is stale: one honest line in the brief ("news calendar stale
   — event risk unchecked") WITHOUT gating.

3. Refresh path: scheduled_brief.sh runs update_calendar.py
   before the brief when calendar.csv is older than 24h;
   refresh failures are logged and never fatal (exit 0
   discipline preserved).

4. Shadow signals are NOT gated — candidates must be graded
   through real news conditions. Optionally stamp the log's
   extra field with news_window=true at fire time (context
   only; candidate specs and triggers untouched — spec-freeze
   rules apply).

Tests (mocked calendar, pinned text): fires at 90 min; silent
at 3 h; gates only on the pair's own currencies (a USD event
does not gate either pair); stale calendar → note, not gate;
missing file → safe, inactive. Banned-token and stand-down
consistency floors untouched.
