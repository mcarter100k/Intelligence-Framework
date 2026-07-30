# studies/ — research & methodology record

Methodology record cited by `validation_log.md`. **Never delete — reproducibility.**

These are standalone research scripts (run by hand, not imported by the live
system). They document how the framework's premises were tested — including the
three refuted at honest N (compression, fakeout-then-go, structural precursor)
and the ADX head-to-head. Each adds the project root (and `shadow/`) to
`sys.path` at startup so it can import the core modules from here.

Contents:
- `precursor_study.py` — reverse-methodology precursor analysis (the negative result)
- `structure_engine_study.py` — v2 box/breakout detector sweep + acid test
- `structure_primary_headtohead.py` — ADX-primary vs structure-primary P&L
- `trade_frequency_backtest.py` — signal-frequency backtest
- `validate_thresholds_v2.py` — non-overlapping-window threshold re-validation (current)
- `validate_h4_thresholds.py`, `validate_confluence_weights.py` — further validators
- `hypothesis_volatile_entries.py` — volatile-entry hypothesis study
- `historical_scenario_replay.py` — known-event replay harness (imported by the studies above)
- `verify_shadow_path.py` — shadow-path verification (references the quarantined stack)

For the *invalidated* v1 validators, see `legacy_validators/`.
