# Spec: US events in the brief as context only (no gating)

**Status:** spec for team review, written 2026-11-01 BEFORE the build
(protected-path rule). Touches three PROTECTED modules: `calendar_fetch.py`,
`news_gate.py` and `decision_brief.py`. Built on branch
`feat/us-events-context`. **It does not merge without team review.**

**Owner decisions behind it** (driver-coverage proposal §7, 2026-11-01):
- US events come in as **context first**.
- Gating is decided from evidence. The pre-registered study (R35, R36) found
  all six US-release cells INCONCLUSIVE, so a gate is not justified.
- This spec therefore adds information and changes **no decision**.

## 1. What changes

1. **`calendar_fetch.py`**
   - Keep HIGH-impact **USD** events as well as GBP/AUD/JPY, so the fetch
     set becomes GBP, AUD, JPY, USD.
   - Validation still requires **at least one GBP/AUD/JPY** row. A feed that
     parses only USD events is rejected and the old file is kept, exactly as
     an empty feed is today.
   - Schema unchanged.
   - CNY stays out (not decided).

2. **`news_gate.py`**
   - `PAIR_CURRENCIES` and `check_news_gate` are **unchanged**. USD still
     gates neither pair.
   - New read-only function `us_event_context(now, calendar_path, hours=24)`.
     It returns a status, the upcoming HIGH-impact USD events in the next 24
     hours (UTC time and title), and the calendar's coverage end. It never
     raises and never gates. Statuses:
     - `ok`: calendar present, covering now, with at least one USD row in the file.
     - `no_us_rows`: calendar present and covering now, but it holds no USD
       rows. This is a file written before this change, or a feed week with
       no US high-impact events.
     - `stale` / `missing`: same rules as the gate (`covered_through`, file
       absent or unreadable).

3. **`decision_brief.py`**
   - A new field `us_events_line`, computed in `get_decision_brief` from
     `us_event_context()`.
   - It renders as one line `  US DATA    …`, placed after the existing
     news-calendar honesty line. Plain English throughout; times through
     `display_time.to_display(style="day_time")`.

   | Status | Rendered text |
   |---|---|
   | `ok`, events ahead | `<title> <Day time>` for up to 3 events, joined by ` · `, then ` — for information; the framework does not stand aside for US releases.` |
   | `ok`, none, and coverage reaches 24h ahead | `none in the next 24 hours.` |
   | `ok`, none, coverage ends sooner | `none before <coverage end, day_time>; later days are not in this week's calendar yet.` |
   | `no_us_rows` | `not checked — this calendar carries no US events yet (it refreshes Sundays).` |
   | `stale` / `missing` | `not checked — news calendar out of date.` |

## 2. What must not change (each pinned by a test)

- **I1, decisions:** for both pairs, `check_news_gate` returns the same
  dict with and without USD rows in the calendar, over a sweep of times
  across a feed week, including active vs stale. So `apply_filter`, the
  decision and the REASON line cannot change.
- **I2, the frozen shadow stamp (trap T1):** `pre_release` and therefore
  `news_window` are part of I1's dict equality.
  `shadow_signals.py` is not touched.
- **I3, no false notifications (rule 12):**
  - The wrapper sends DECISION for any brief line containing uppercase
    `DECISION` without `STAND ASIDE` (`scripts/scheduled_brief.sh:128,151`).
  - The US line must never contain uppercase `DECISION` or `ALERT`; event
    titles are sanitized so that holds whatever the feed sends.
  - The test runs the wrapper's own grep pipeline on a rendered stand-aside
    brief carrying a US event titled `RATE DECISION` and asserts no DECISION
    category. It also asserts the line never reaches stderr, the ALERT
    channel.
  - No new notification is added.
- **I4, plain English (rule 4):** the rendered line passes the banned-token
  floor in `tests/test_brief_display.py`. The floor itself is not edited.
- **I5, rule 9:** "none" renders only from status `ok`. It never renders
  from a calendar without USD rows, a stale calendar, or a missing one.

## 3. Tests that change, old → new

- `tests/test_calendar_fetch.py::test_happy_path_writes_news_gate_schema`
  - Old: a HIGH-impact USD event is filtered out (`["GBP", "AUD", "JPY"]`).
  - New: it is kept (`["GBP", "USD", "AUD", "JPY"]` by time).
  - This is not a floor test.
- `tests/test_news_gate.py::test_usd_event_gates_neither_pair` is
  **unchanged** and must still pass.

## 4. Verification

- **Gate 1:** the tests above, each with a mutation shown to fail it.
  Mutants include:
  - USD added to `PAIR_CURRENCIES`;
  - the uppercase sanitizer removed;
  - "none" rendered for `no_us_rows`;
  - validation accepting a USD-only feed.
- **Gate 2, through `scripts/reality_run.py`:**
  1. The real brief on the live calendar. It is fetched before this change,
     so it holds no USD rows and must render `not checked — this calendar
     carries no US events yet`.
  2. A real ForexFactory fetch into a temp path. It must hold USD rows.
  3. The brief against that file, rendering real US events, with the
     decisions identical to run 1 (I1 on real data).
- **Gate 3, PENDING LIVE CONFIRMATION:** the first Sunday calendar fetch
  after merge writes USD rows, and the next brief renders real US events.

## 5. Out of scope

- Gating on US events. Not justified (R35, R36); it would need its own spec.
- US events in the DIGEST or in `setup_check`.
- CNY events.
- Archiving forecasts or actuals (proposal step 6, its own spec).
