"""
verify_shadow_path.py
──────────────────────
Run this at the start of the first live session (Sun 21:00 UTC or later)
to confirm:
  1. The full signal stack executes (market is open, no early return)
  2. The regime layer is populated with real OANDA data
  3. The shadow path runs alongside the official decision
  4. Any path divergence is surfaced

This script is Audit Item 13b.
Do NOT run while the market is closed — it will assert and exit cleanly
with a clear message rather than producing misleading results.

Usage: python3 scripts/verify_shadow_path.py
"""

import os as _os, sys as _sys  # studies path bootstrap (root + shadow)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, 'shadow')):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_brain import build_market_report

t0 = time.perf_counter()
r = build_market_report(instrument="GBP_AUD")
elapsed = time.perf_counter() - t0

print(f"Elapsed: {elapsed:.2f}s")
print(f"layers:      {list(r.get('layers', {}).keys())}")
print(f"official:    {r.get('decision')}")
print(f"shadow:      {r.get('shadow_decision')}")
print(f"divergence:  {r.get('path_divergence')}")
print(f"market_closed: {r.get('market_closed')}")

if r.get("market_closed"):
    print("\nMarket is closed — early-return path fired as expected.")
    print("Re-run after Sun 21:00 UTC to measure the full signal-stack path.")
    sys.exit(0)

assert "regime" in r.get("layers", {}), \
    "FAIL: regime layer missing — market may be closed or get_regime() errored"
assert r.get("shadow_decision") is not None, \
    "FAIL: shadow path did not execute (shadow_decision is None or missing)"

print("\nPASS — full path executed, regime layer present, shadow path ran.")
print(f"  official direction: {r['decision'].get('direction')}")
print(f"  shadow direction:   {r['shadow_decision'].get('direction') if r.get('shadow_decision') else 'N/A'}")
if r.get("path_divergence"):
    print("  *** PATH DIVERGENCE: official and shadow disagree — log for review ***")
