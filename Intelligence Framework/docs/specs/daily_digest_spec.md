# Spec: daily DIGEST notification (final before freeze, 2026-09-09)

**Status:** team-directed, folded into `feat/unresolved-direction-polish`
per the final-before-freeze ruling. Wrapper/scripts layer only.

- **The 07:30 scheduled run — and never any other** — posts ONE digest
  notification, category **DIGEST** (not ALERT). Run selection is
  deterministic, not clock-guessing: the brief-ny launchd plist passes the
  argument `digest` to `scheduled_brief.sh`; every other invoker passes
  nothing. (The TZ question stays open — whichever wall-clock instant that
  job fires at, it is the one daily digest.)
- **Content, one line:** both pairs' decisions plus the concrete watch
  condition — `GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — watch: the low
  near 1.8732 confirms as a swing low`. The watch clause prefers a
  concrete pending-pivot sentence from either pair's EXIT IF; falls back
  to the first EXIT IF sentence; a failed run digests as "run failed —
  see the log" (the health path alerts separately).
  Built by `scripts/daily_digest.py` from the run's own output (testable
  on fixtures).
- **Click-through:** `logs/latest_brief.log`, generated on the digest run
  by `scripts/latest_view.py` using the held latest-view spec's layout
  (newest run block verbatim, one line per earlier run, the day's
  ALERT/RECOVERED/flip lines, pointer to the full record). **Only this
  slice of the latest-view spec is built** — the full every-run
  regeneration and repointing of all notifications stays unbuilt and held
  for review, as ruled. Implementation is Python, not the sketch's awk,
  for testability; the view is a regenerated non-evidence file like
  health_state.json. Digest generation failing falls back to pointing at
  the day log (exit-0 discipline).

Gate 1: digest builder pinned (both-pairs line, concrete watch preferred,
generic fallback, failed-run wording); view builder pinned (latest block
verbatim, per-run digest with error runs marked, alert lines carried,
pointer); wrapper pin (digest strictly arg-gated). Gate 2: real wrapper
run with the digest argument — real DIGEST notification, real
latest_brief.log, the click URL opening it; a non-digest run posting none.
