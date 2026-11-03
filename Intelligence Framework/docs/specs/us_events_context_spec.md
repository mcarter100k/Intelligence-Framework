# Spec: US events in the brief as context only (no gating)

**Status:** spec for team review, written 2026-11-01 BEFORE the build
(protected-path rule). Touches three PROTECTED modules: `calendar_fetch.py`,
`news_gate.py` and `decision_brief.py`. Built on branch
`feat/us-events-context`. **It does not merge without team review.**

**Revision 1 (2026-11-01, after team review; owner approved the rebuild).**
Two reviewers returned REQUEST CHANGES and rule 12 FAIL
(validation_log 2026-11-01 CORRECTION). This revision is committed before the
rebuild. Changes, old → new:
- §1.1: a malformed USD row used to reject the whole feed. Now it is skipped
  and counted. USD rows are also confined to the GBP/AUD/JPY rows' feed week.
- §1.3: titles were sanitized by a two-word replace. Now an allow-list.
  Same-time releases are grouped, a silent cap at 3 becomes "+N more", and
  the line sits below every warning note. Three wordings are corrected.
- §1.4 (new): the notification wrapper's triggers are anchored to real
  label lines.
- §2 I1 and I3: rewritten to match. §3 lists the test changes.

**Revision 2 (2026-11-03, after re-review; owner approved).** The code
reviewer approved Rev 1. The adversarial reviewer returned REQUEST CHANGES
(rule 12 FAIL on the digest path): a trigger phrase glued to a preceding
letter or digit (`xWATCH FOR`, `xFramework error`, `9DECISION`) passed the
Rev 1 sanitizer, which used `\b`. The 07:30 DIGEST and `latest_view` match
those phrases anywhere in the text. Changes, old → new:
- §1.3 titles:
  - Trigger phrases are rewritten wherever they occur, in the exact casing
    the consumers match (all case-sensitive), with no word boundaries, after
    the capitals rule, repeated until nothing changes.
  - Accented letters are transliterated (NFKD) before the allow-list, not
    dropped.
- §1.3 grouping: every time slot is shown, up to 4 slots. Each slot shows up
  to 3 titles, then `+k more`. Slots beyond 4 become `+N later`. Before Rev 2,
  a busy first slot could hide a later slot's time.
- §1.1: the fetch's skip notes are reduced to the allow-list and truncated.
- §1.5 (new): `scripts/daily_digest.py` and `scripts/latest_view.py` are
  anchored to label lines, as the wrapper was in Rev 1.
- I3a gains a real `scheduled_brief.sh digest` run.
- §3 lists the test changes.

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
   - **A USD row can never fail the gated fetch (Rev 1).** A USD row that
     cannot be read (missing or unparseable date, a date with no UTC offset,
     a non-text title) is skipped and counted, never raised. GBP/AUD/JPY rows
     keep today's fail-closed behaviour exactly.
   - **USD rows are confined to the feed week (Rev 1).** A USD row later than
     `news_gate.covered_through(newest GBP/AUD/JPY row)` is dropped and
     counted. `check_news_gate` takes staleness from the newest row of any
     currency, so without this a stray next-week USD row could turn a stale
     gate active. The real feed is a single week, so this should never fire.
     It is enforced in code because nothing else guarantees it.
   - The success line reports skipped and dropped rows, e.g.
     `… and 4 US events (context only); skipped 1 US row (unreadable or
     outside this calendar's week) …`. It goes to the log only.

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
   - It renders as one line `  US DATA    …`. Plain English throughout;
     times go through `display_time.to_display(style="day_time")`.
   - **Placement (Rev 1):** the line goes immediately before the header's
     closing border, below every warning note (price source, market closed,
     feed stale, news calendar). It used to be inserted above the
     market-closed and price notes.
   - **Grouping (Rev 1):** releases at the same time are listed once with
     their shared time. At most 4 titles are shown; any more add
     `· +N more`. Before Rev 1, the 4th and later events were dropped silently.
   - **Titles (Rev 1), allow-list in `_us_title`:**
     1. Any character outside ASCII letters, digits, space and `.,&()'%+:/-`
        becomes a space. That covers `#`, `|`, `_`, control characters,
        newlines and non-ASCII look-alikes.
     2. `/` survives only between lowercase letters or digits (`m/m`, `y/y`),
        so no `XXX/YYY` pair-header shape can form.
     3. Whitespace is collapsed.
     4. All-capital words of 5 or more letters are capitalised
        (`DECISION` → `Decision`), and each wrapper or digest phrase
        (DECISION, ALERT, SHADOW SIGNALS, FRAMEWORK ERROR, EXIT IF,
        WATCH FOR, STAND ASIDE, STAND DOWN, REASON) is capitalised word by
        word in any casing. Short acronyms (FOMC, CPI, ISM) are kept.
     5. Titles over 60 characters are cut at a word boundary, followed by `...`.
     6. An empty result becomes `US release`.
   - **Rev 2:**
     - Step 0: NFKD-transliterate (é → e) before the allow-list.
     - Step 4 also rewrites every consumer trigger phrase in its exact
       casing wherever it occurs, with no word boundary, until a pass
       changes nothing: `DECISION`, `ALERT`, `SHADOW SIGNALS`,
       `Framework error`, `EXIT IF`, `WATCH FOR`, `STAND ASIDE`,
       `STAND DOWN`, `REASON`. So `xWATCH FOR` → `xWatch For`.
     - The capitals rule runs first, so `FRAMEWORK error` → `Framework error`
       is then caught as well.
     - Grouping: up to 4 time slots, each with up to 3 titles then `+k more`;
       `+N later` for further slots.
   - **Untimed events:** the feed carries no all-day marker. Observed
     2026-11-01: "Congressional Elections" arrives as `10:16` ET, and real
     releases also land on odd minutes (03:50, 18:50). So the feed's time is
     shown as given; detecting untimed events is not possible from this
     source.

   | Status | Rendered text |
   |---|---|
   | `ok`, events ahead | groups `<title>, <title> <Day time>` joined by ` · `, optional ` · +N more`, then ` — for information; the framework does not stand aside for US releases.` |
   | `ok`, none, and coverage reaches 24h ahead | `none in the next 24 hours.` |
   | `ok`, none, coverage ends sooner | `none before <coverage end, day_time>; later days are not in this week's calendar yet.` |
   | `no_us_rows` | `not checked — the saved news calendar holds no US events (it refreshes when over a day old).` (Rev 1; was "it refreshes Sundays", which is wrong: `scripts/scheduled_brief.sh:46` re-fetches whenever the file is over 24 h old) |
   | `stale` | `not checked — news calendar out of date.` |
   | `missing` | `not checked — news calendar missing.` (Rev 1; was shown as "out of date") |

5. **`scripts/daily_digest.py` and `scripts/latest_view.py` (free zone,
   rule 12; Rev 2).** These match brief text too. Their patterns become:
   - error: `^ ? ?REASON +Framework error` (was `"Framework error" in text`);
   - watch: `^ ? ?(?:EXIT IF|WATCH FOR)` (was unanchored);
   - decision: `^ ? ?DECISION` (was `^\s*`, which matches any indent and
     even newlines);
   - pair header: `^ ? ?(GBP/[A-Z]{3})\s+\|`;
   - market closed: `^ ? ?Market closed — …`.
   All use multi-line mode. Empty output still reads "run failed".

4. **`scripts/scheduled_brief.sh` (free zone, rule 12; Rev 1)**
   - Every trigger read from the brief's stdout is anchored to a real label
     line. Label lines start with 0–2 spaces; wrapped continuation lines
     start with 13 or 15. So the patterns become `^ ? ?DECISION `,
     `^ ? ?SHADOW SIGNALS`, `^ ? ?REASON +Framework error` and
     `^ ? ?[A-Z]{3}/[A-Z]{3}( |$)` for pair headers. This covers the
     market-closed gate, the suppression log line, the per-pair ledger
     state, the category choice and the summary.
     - Plain `^ *` is not enough: a wrapped title word can start a
       continuation line.
   - This closes the whole class, including own-currency titles that
     `gate_reason` already puts into REASON lines unsanitized (pre-existing).
     The sanitizer stays as a second layer.

## 2. What must not change (each pinned by a test)

- **I1, decisions:** for both pairs, `check_news_gate` returns the same
  dict with and without USD rows in the calendar, over a sweep of times
  across a feed week, including active vs stale. So `apply_filter`, the
  decision and the REASON line cannot change.
  - **Rev 1:** the USD rows in the sweep pass through the fetch's own
    confinement function, not a test-side filter, so removing the
    confinement fails I1.
  - **I1b (Rev 1), fetch side:** a feed of valid GBP/AUD/JPY rows plus any
    malformed USD row writes exactly the GBP/AUD/JPY rows `main` would write.
    A next-week USD row is dropped.
- **I2, the frozen shadow stamp (trap T1):** `pre_release` and therefore
  `news_window` are part of I1's dict equality.
  `shadow_signals.py` is not touched.
- **I3, no false notifications (rule 12; rewritten in Rev 1):**
  - The original I3 checked only the DECISION grep, with a copied pipeline
    string that a mutated wrapper still satisfied.
  - **I3a, wrapper layer:** run the **real** `scheduled_brief.sh` on the
    `test_wrapper_behavior` harness. The rendered briefs carry an
    **unsanitized** US line, crafted so that `DECISION LONG`,
    `SHADOW SIGNALS`, `REASON Framework error` and `USD/JPY` each start a
    wrapped continuation line.
    - On an open-market stand-aside brief: no notification, no ledger row,
      and no health failure over two runs.
    - On an open-market GBP/JPY LONG brief: exactly `GBP/JPY LONG`, with
      ledger state `GBP_JPY=LONG/open`.
    - Positive control: the same LONG brief without the US line notifies
      identically, and a real label line still fires.
  - **I3b, sanitizer layer:** across an adversarial title corpus × every
    padding that moves the trigger across a wrap boundary, the rendered
    line contains none of the wrapper or digest phrases (case-sensitive),
    no `#`, `|` or `_`, no `[A-Z]{3}/[A-Z]{3}`, and only ASCII.
  - Each layer is proven alone, so either one failing is caught.
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
- **Rev 1:**
  - `tests/test_us_events_context.py`: the old wrapper-string I3 test and
    its control are replaced by I3a and I3b above. Neither was a floor test.
  - All existing `tests/test_wrapper_behavior.py` cases must pass unchanged
    under the anchored wrapper.
- **Rev 2:**
  - `tests/test_daily_digest.py::test_framework_error_reads_as_failed_run`
    (or whichever test feeds the bare `"... Framework error — do not trade
    ..."` string). Old: a bare phrase anywhere means "run failed". New: the
    fixture is a real error-page REASON line. Wording elsewhere must not
    fail the digest. Not a floor test.
  - The I3b corpus gains prefix-glued titles.
  - The grouping test expectation follows the new slot rule.
  - The I1 test comment is corrected: it calls `_confine_context_rows`
    directly, so it catches a mutant inside the function. Removing the call
    from `fetch_calendar` is caught by the dropped-row test.

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
- **Gate 3, PENDING LIVE CONFIRMATION:** the first calendar fetch after
  merge writes USD rows (Sunday's launchd job, or the brief's re-fetch of a
  file over 24 h old), and the next brief renders real US events.
- **Rev 1 mutants, added:**
  - malformed USD row raised again;
  - confinement removed;
  - each wrapper anchor reverted to unanchored;
  - `/` rule removed;
  - phrase capitalisation removed;
  - grouping removed (silent cap);
  - line placed above the warnings.

## 5. Out of scope

- Gating on US events. Not justified (R35, R36); it would need its own spec.
- US events in the DIGEST or in `setup_check`.
- CNY events.
- Archiving forecasts or actuals (proposal step 6, its own spec).
- Rev 1, deferred with reasons:
  - "released at …" for the last two hours (reviewer: optional);
  - splitting the weekly heartbeat's event count into own-currency and US
    (non-blocking);
  - committing a mutation runner script (non-blocking);
  - fixing `reality_run --code`'s missing calendar (separate change, known
    since 2026-10-18).
