# Spec: display timezone (freeze exception, display-layer only, 2026-09-10)

**Status:** team-directed freeze exception, user-requested. Every time a
human reads renders in ONE configurable zone; internals stay UTC.
**Branch:** `feat/display-timezone`. Merge held for review.

## 1. One config, one helper

New root module `display_time.py` (added to the PROTECTED list — it sits
on the render path of protected modules): `DEFAULT_DISPLAY_TZ =
"America/Los_Angeles"`, overridden by the `DISPLAY_TZ` env var.
`to_display(dt, style)` renders an aware-or-naive-UTC datetime in the
display zone — styles `full` ("Tue 08 Sep 2026 9:07 PM PDT"), `time`
("9:07 PM PDT"), `day_time` ("Sun 2:00 PM PDT"). The abbreviation comes
from zoneinfo BY DATE — PDT/PST switch automatically; no hardcoded
abbreviation anywhere. All Python render sites route through it. The
sanctioned shell form for wrapper log headers is
`TZ="${DISPLAY_TZ:-America/Los_Angeles}" date …` — the same OS zone
database, same config variable, no second conversion path.

## 2. Converted render sites (survey-complete)

- `decision_brief` header timestamp (was "%H:%M UTC").
- Market-closed note (`_market_status`): "Next open Sun 2:00 PM PDT." —
  converted at the source; the machine field `next_open_utc` becomes true
  ISO-UTC ("…T21:00:00Z", consumed by nothing today, verified by grep).
- News gate: `check_news_gate` result gains `event_time_utc` (ISO-Z,
  additive; window math untouched). The filter's stand-down reason and
  setup_check's CLOCK line append "(at 11:00 PM PDT)" from it.
- Wrapper "=====" block headers + the calendar-fetch header line
  (brief/outcomes/heartbeat) via the TZ-env date form. Log FILENAMES
  (brief_<date>.log) are organizational, not prose — unchanged.
- `health_state.py status()` (rendered by the weekly heartbeat) shows
  last-success in display time; `health_state.json` storage stays UTC.
- `latest_brief.log` inherits the converted wrapper headers.
- Digest text: verified to carry no timestamps. `trade_logger`
  prompts/echo: verified to render no times — nothing to convert (the
  directive listed it; the survey found only ledger-internal UTC stamps,
  untouched by rule 3).

## 3. Untouched, with verification

Every CSV ledger timestamp, bar timestamps, session snapshots,
health_state.json contents, dedup keys, launchd schedules, market-hours
logic (Sun 21:00 UTC open), calendar window math. **calendar.csv storage
verified UTC-aware:** `calendar_fetch._parse_events` converts every event
via `astimezone(timezone.utc)` before writing naive-UTC "YYYY-MM-DD
HH:MM" (docstring states it; code line confirms it); today's
"2026-09-11 06:00" GBP GDP row is 06:00 UTC (= 07:00 London release);
`news_gate` compares naive-UTC to naive-UTC. Display converts; gating
compares in UTC.

## 4. Gates

- **Gate 1:** helper pinned on a January date (PST) and a July date
  (PDT), all three styles; env override honored; news gate fires at the
  IDENTICAL UTC instant with DISPLAY_TZ = LA / New York / UTC; official
  decisions byte-identical; rendered header/note/clock sweep contains no
  bare "UTC" (machine fields and ledgers exempt); the filter's pinned
  reason updated to carry the local-time parenthetical.
- **Gate 2 (REALITY):** live brief, live setup_check, and a real digest
  run rendered in LA time; the CLOCK line showing Friday's UK GDP
  (2026-09-11 06:00 UTC) as Thu 11:00 PM PDT — exercised against the real
  calendar.csv with the gate's own `now` parameter placed inside the
  2-hour window (real file, real code path, controlled clock — the
  release itself is Friday).
