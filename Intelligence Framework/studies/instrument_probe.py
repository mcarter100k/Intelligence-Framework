"""
instrument_probe.py — which cross-market instruments does this OANDA account
offer, and how much daily history does each have? (owner-approved 2026-11-01,
docs/driver_coverage_proposal.md step 2)

Read-only: GET /v3/accounts/{id}/instruments, then for each target present
one GET of its first and its latest daily candle. No orders, no ledger
writes. Run it only through scripts/reality_run.py:

    python3 scripts/reality_run.py --code <worktree> script studies/instrument_probe.py

The account id is masked in all output; the key is never printed. Any HTTP
failure raises, so reality_run sees a traceback and refuses to certify.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oanda_feed import _account_id, _base_url, _headers

# What the driver-coverage reviews asked for (proposal §3), by role.
TARGETS = [
    ("USD legs", ["USD_JPY", "GBP_USD", "AUD_USD", "USD_CNH"]),
    ("Yields", ["USB02Y_USD", "USB10Y_USD", "UK10YB_GBP", "DE10YB_EUR"]),
    ("Equities", ["SPX500_USD", "NAS100_USD", "JP225_USD", "AU200_AUD", "UK100_GBP"]),
    ("Commodities", ["XCU_USD", "XAU_USD", "BCO_USD", "WTICO_USD", "NATGAS_USD"]),
]
FINANCING_OF = ["GBP_JPY", "GBP_AUD"]


def _get(path: str, params: dict | None = None) -> dict:
    r = requests.get(_base_url() + path, headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def masked(acct: str) -> str:
    return ("*" * max(len(acct) - 4, 0)) + acct[-4:]


def first_and_last_daily(name: str) -> tuple[str, str]:
    path = f"/v3/instruments/{name}/candles"
    first = _get(path, {"granularity": "D", "price": "M", "count": 1,
                        "from": "1990-01-01T00:00:00Z"})["candles"]
    last = _get(path, {"granularity": "D", "price": "M", "count": 1})["candles"]
    return (first[0]["time"][:10] if first else "none",
            last[0]["time"][:10] if last else "none")


def main() -> int:
    acct = _account_id()
    data = _get(f"/v3/accounts/{acct}/instruments")
    instruments = {i["name"]: i for i in data.get("instruments", [])}
    print(f"INSTRUMENT PROBE — account {masked(acct)} — {_base_url().split('//')[1]}")
    by_type = Counter(i.get("type", "?") for i in instruments.values())
    print("Instruments offered by type: "
          + ", ".join(f"{t} {n}" for t, n in sorted(by_type.items())))
    print()
    for group, names in TARGETS:
        print(f"## {group}")
        for name in names:
            if name not in instruments:
                print(f"  {name:<12} NOT OFFERED")
                continue
            first, last = first_and_last_daily(name)
            print(f"  {name:<12} offered ({instruments[name].get('type', '?')}): "
                  f"daily history {first} → {last}")
        print()
    print("## Financing (as reported by the instruments endpoint)")
    for name in FINANCING_OF:
        fin = (instruments.get(name) or {}).get("financing")
        if fin:
            print(f"  {name}: longRate {fin.get('longRate')} shortRate {fin.get('shortRate')}")
        else:
            print(f"  {name}: no financing field returned")
    others = sorted(n for n, i in instruments.items() if i.get("type") != "CURRENCY")
    print()
    print(f"## All non-currency instruments ({len(others)})")
    print("  " + (", ".join(others) if others else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
