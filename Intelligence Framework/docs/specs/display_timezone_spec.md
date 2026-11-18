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

## Addendum (2026-09-10): the view's "today" is the display day

Loose end from the first build: `latest_brief.log` grouped "TODAY SO FAR"
by the log FILE's boundary (system-clock midnight), so at 9:33 PM PDT the
view showed one run — the file had rolled at midnight Eastern. Ruling:
**one clock for the view — the display zone.**

- `latest_view.py` now derives today's date in DISPLAY_TZ, reads every
  candidate day file that could hold it (D−1, D, D+1 by filename), and
  keeps the blocks whose ===== header carries today's display date. Since
  the first build, headers ARE written in the display zone, so header-date
  grouping IS display-day grouping; blocks stamped in another zone during
  the one-time transition day group by their stamped date (documented
  quirk, gone within a day).
- LATEST RUN = the newest of today's blocks (newest block overall when
  today has none yet, marked as such). Alert/RECOVERED/flip lines carried
  from today's blocks only.
- Log file NAMING is unchanged (records, not display); the view's closing
  line names every file the section drew from:
  "Full record: brief_2026-09-09.log, brief_2026-09-10.log".
- Digest failure fallback (pointing at the current day file) unchanged.

Pins: a display day spanning two files groups both; other-date blocks
excluded; the sources line lists exactly the files drawn from; signals
follow their blocks; empty state graceful. Gate 2: real regeneration at a
moment when the display day spans two files.

## Addendum (2026-11-18): 12-hour clock with the "PT" label (owner directive)

Owner directive, 2026-11-18: "All times printed to the owner use 12-hour
format with AM/PM and the Pacific label: '3:45 AM PT', '6:00 PM PT',
'11:30 PM PT'. Never 24-hour." It covers every alert type (BRIEFING,
ARRIVAL, LEVEL BREAK, BREAK, release warnings), the decision brief, the
heartbeat, the digest, and every report written for the owner. Log files,
timestamps inside code, filenames and ISO datetimes in data are unaffected.

**What changes in `display_time.py`:**
- The helper already printed 12-hour AM/PM. What changes is the label: the
  Pacific zone now prints **"PT"** all year, not "PST"/"PDT". This amends
  §1's "abbreviation from zoneinfo by date". §1 existed so the label would
  never be wrong across a DST change. "PT" is correct on both sides of it.
- Any other `DISPLAY_TZ` keeps zoneinfo's abbreviation by date (for
  example "EST"). Only Pacific has an owner-chosen label.
- A new style, `day_date`, gives "Thu 12 Nov 6:00 AM PT" for the alert and
  report lines that need the date without the year.

**Paths that built a time string of their own, now routed through the
helper:**

| Path | Before | After |
|---|---|---|
| Heartbeat header (`weekly_heartbeat.sh`) | `===== heartbeat 2026-11-15 12:30:06 PST =====` | `===== heartbeat Sun 15 Nov 2026 12:30 PM PT =====` |
| Heartbeat calendar line | `newest 2026-11-19 00:30` (UTC, unlabelled) | `newest Wed 18 Nov 2026 4:30 PM PT` |
| Heartbeat freshness STALE line (`artifact_freshness.py`) | `first: GBP_AUD 2026-11-17T15:30Z` | `first: GBP_AUD Tue 17 Nov 2026 7:30 AM PT` |
| Latest-run view (`latest_view.py`) | `LATEST RUN — 2026-11-17 07:30:05 PST`; today's runs as `2026-11-17 02:33:55 PST …`; the copied block began with its `=====` log header | `LATEST RUN — Tue 17 Nov 2026 7:30 AM PT`; today's runs as `2:33 AM PT …`; the log header line is not repeated under LATEST RUN |
| Gold alert prototypes (`studies/ccd1_arrival_lastweek.py`, `studies/ccd1_prototype.py`) | `Sun 11-15 18:00 PT` | `Sun 15 Nov 6:00 PM PT` |

**Already routed through the helper (they change label only):** the decision
brief header, the market-closed note, the news-gate stand-down reason,
setup_check's CLOCK line, the US-events lines, and the heartbeat health line.

**Unchanged, by the directive's own exclusion:**
- the `=====` run headers inside the brief, outcomes and calendar day logs.
  They are log records, and `run_count.py`, `latest_view.py` and two
  studies parse them in their 24-hour form;
- the log filenames;
- every CSV and JSON timestamp.

**Not converted in this change (reported, not hidden):** older report-only
studies print hour-of-day tables with 24-hour labels. Examples are
`session_movement_study.py`, `session_movement_compare.py`,
`gbpaud_personality_profile.py`, `gbpaud_scouting_verify.py`,
`markup_swings.py`, `gold_spread_windows.py`, `gold_2026_release_reactions.py`
and `history_monday_open_check.py`. Their committed results are methodology
records and are not rewritten. Any of them that is run again for the owner
is converted first.

**Gates:**
- **Gate 1.** `tests/test_owner_clock.py` checks every owner-facing producer
  above against a 24-hour-clock pattern. The pattern itself is tested both
  ways: it catches "07:30", "18:00 PT" and "12:30:06 PST", and it passes
  "6:00 AM PT".
  - The helper is swept over every hour of a winter day and a summer day,
    in every style. The 24 renders of each day must all differ, and the
    hours must map as 00 → 12 AM, 12 → 12 PM and 13 → 1 PM.
  - The display-claims render sweep gains the same clock check.
  - Mutation tests: put the helper back on a 24-hour clock and drop each
    route. Each one must fail a test.
- **Gate 2.** Real runs through `scripts/reality_run.py`: the decision
  brief, the heartbeat and the gold replay. Their actual output is shown.
