# SPEC: setup_check — pre-trade evidence stack tool (team approved 2026-07-31)

> Review record. Saved verbatim from the team's approval before building,
> per AGENTS.md: protected-path specs become repo artifacts first.

The pre-trade evidence stack tool. Reads the decision path,
NEVER modifies it. Scope: GBP_AUD and GBP_JPY only.

Usage: python3 setup_check.py GBP_JPY LONG [--target 215.50]
Output in under ~2s, plain English (banned-token rules apply):

  LINE 1 BIAS      auto: weekly + daily direction from get_regime
  LINE 2 REGIME    auto: regime + session delta + official
                   decision state (flag loudly if the framework
                   itself says stand aside — "you are trading
                   against the framework's read" is information,
                   not a block)
  LINE 3 PLAY      suggested: from H4/H1/15m structure state +
                   engulfing + nearest-level proximity (reuse
                   entry_confirmation internals — refactor its
                   guts into importable functions if needed;
                   its existing behavior and tests unchanged),
                   pattern-matched to: base-break / coil-break /
                   first-pullback / retest-fade / none-named
  LINE 4 CLOCK     auto: news_gate result + intervention-zone
                   flag for JPY (static condition note when the
                   storylines file marks it)
  LINE 5 FUEL      suggested: direction checked against
                   storylines.md per leg — AGREES / CONFLICTS /
                   stale-file warning. Never generated.
  LINE 6 RISK      auto: nearest structural invalidation from
                   pivots, distance in pips, R to --target if
                   given, MAX_STOP_ATR_MULTIPLE breach flag
                   (reuse trade_management math — wire it, its
                   FLAG status resolves to live-core here)

- Interactive confirm: user accepts/overrides lines 3 and 5
  with one keystroke each; everything logged either way.
- SOFT GATE: always logs. Blanks/overrides/conflicts flagged
  in the record, never blocked.
- Writes pre_trade_journal.csv (gitignored, append-only,
  ledger rules): stack_id, timestamp, instrument, direction,
  all six lines + auto/confirmed/blank markers, framework
  decision at that moment.
- trade_logger.py gains an optional stack_id field to link
  execution to its pre-trade record.
- storylines.md: create with a template header + staleness
  convention (dated header line; >8 days = stale).
- Tests: full stack renders on live regime mock; stand-aside
  flag fires; stale storylines warn; R math pinned; soft gate
  logs blanks; no live-core behavioral changes (full suite).
