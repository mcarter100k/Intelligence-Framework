# Intelligence Framework

A decision framework for two FX pairs, GBP/AUD and GBP/JPY, on OANDA data.
Three times a day it reads the market, decides LONG / SHORT / STAND ASIDE
for each pair, and records every decision so the market can grade it later.
Rules for working here are in [AGENTS.md](AGENTS.md); the evidence record
is [validation_log.md](validation_log.md).

## Where things are

| Folder | What is in it |
|---|---|
| project root | The live code (the Python modules below), the evidence ledgers (`*.csv`), and the two records: `validation_log.md` and `storylines.md` |
| `scripts/` | The scheduled jobs (`scheduled_*.sh`, `weekly_heartbeat.sh`), their helpers, and the verification tools. See [scripts/README.md](scripts/README.md) |
| `tests/` | The test suite. Run it with `python -m pytest -q` from the project root. `conftest.py` stays at the root so its evidence guard covers the whole project |
| `studies/` | Research scripts and their reports: the methodology record, never imported by the live code and never deleted. See [studies/README.md](studies/README.md) |
| `docs/specs/` | One spec per change to the protected code, committed before the change was built. See [docs/specs/README.md](docs/specs/README.md) |
| `foundation/` | The curated knowledge base that builds the `trading-foundation` skill |
| `logs/`, `backups/` | Day logs written by the scheduled jobs, and nightly hash-checked ledger copies (both gitignored) |

The live modules stay flat at the root on purpose. The scheduled jobs run
them by file name, their ledger paths are relative to the root, and the
verification tool copies root-level ledgers only.

## The live modules, by job

**Making the decision** (in call order)
- `oanda_feed.py`: fetches prices and bars from OANDA; drops the bar still forming.
- `regime_detection.py`: labels each timeframe (trending up or down, sideways, no clear direction) from trend strength and swing structure, and assembles everything the decision needs.
- `news_gate.py`: stands the pair aside around high-impact news.
- `no_trade_filter.py`: the single authority on standing aside; it allows a trade only if the official decision would take it.
- `official_decision.py`: turns a regime the filter passed into direction, conviction and grade.
- `levels_context.py`, `intraday_context.py`, `entry_confirmation.py`: key price levels, the Asian-session range, and the hourly/15-minute entry check shown under the decision.
- `decision_brief.py`: runs all of the above for each pair and renders the plain-English brief. **Entry point:** `python3 decision_brief.py GBP_AUD GBP_JPY`.
- `display_time.py`: the one place a time becomes human-readable (Pacific by default).

**Recording and grading the evidence**
- `regime_classifier_logger.py` → `regime_classification_log.csv`
- `trade_outcome_logger.py` → `trade_signal_log.csv` (logs each directional decision and grades it)
- `session_memory.py` → `session_context_log.csv` (one snapshot per run; "what changed since the last brief")
- `shadow_signals.py` → `shadow_signal_log.csv` (the frozen research candidates and their grader)
- `run_outcome_check.py`: the nightly grader. **Entry point:** `python3 run_outcome_check.py`.
- `ledger_io.py`: every ledger write goes through it (locked, crash-safe).
- `exclusions.py` → `excluded_rows.csv`: rows kept out of every tally, each one authorized in validation_log.
- `calendar_fetch.py` → `calendar.csv`: the weekly news calendar.

**Manual tools** (run by the trader, not scheduled)
- `setup_check.py` → `pre_trade_journal.csv`: the pre-trade checklist.
- `trade_logger.py` → `trades.csv`: the trade journal (open and close rows).
- `trade_management.py`: stop and target math, used by both tools above.

**Dormant** (protected, but nothing calls them yet)
- `session_guard.py`, `risk_config.py`: the daily-loss circuit breaker and risk rules. They must be wired in or deleted; that is an owner decision.

`trade_log.csv` is frozen historical evidence with no writer.

## Rules that matter most

- The 21 modules listed in AGENTS.md are protected: a change needs a spec and team review before it merges.
- Ledgers are append-only and are written only through `ledger_io.py`.
- Nothing is called done without evidence that could have failed (the `evidence-validation` skill).
