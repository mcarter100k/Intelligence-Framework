# SPEC: weekly automatic calendar feed (team approved 2026-07-31)

> Review record. Saved verbatim from the team's approval before building,
> per AGENTS.md: protected-path specs become repo artifacts first.

Weekly automatic calendar feed. Replaces the manual-entry
workflow as primary; manual entry remains as fallback.

- calendar_fetch.py (live core adjacent, no shadow/ imports):
  fetches the coming week's economic calendar from a public
  source (ForexFactory weekly JSON feed or equivalent — Fable
  selects and DOCUMENTS the source + its format assumptions in
  the module docstring). Filters to high-impact GBP, AUD, JPY
  events. Writes calendar.csv in the schema news_gate.py reads.
- VALIDATION BEFORE COMMIT-TO-DISK: parsed events >= 1, all
  dates within the next 8 days, currencies sane. Any failure →
  keep the existing file untouched, log loudly. The existing
  stale-calendar honest note is the designed backstop — a
  failed fetch degrades to a visible warning, never a silent
  wrong calendar.
- launchd job com.quis.intelligence.calendar, Sunday 12:00 LA
  (before the 14:00 LA market open), plist + install.sh update.
  scheduled_brief.sh's existing >24h staleness check remains as
  the mid-week retry path, now calling the fetcher.
- Tests: mocked feed happy path; malformed feed → old file
  preserved; empty feed → rejected; network failure → exit 0,
  note logged.
