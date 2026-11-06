"""metals_availability_probe.py — does this OANDA account serve gold (or any
metal)? Read-only, owner-requested 2026-11-05 (currency-leg study, Phase 1).

Two independent questions, because an instrument can be absent from the
account's tradeable list yet still serve candles:
  1. GET /v3/accounts/{id}/instruments: instrument types offered, and every
     name containing XAU or XAG or of type METAL.
  2. GET /v3/instruments/{name}/candles?count=1&granularity=D for XAU_USD,
     XAG_USD and XAU_GBP: HTTP status and whether a candle came back.
Prints status codes, types, names and candle timestamps only; no price.

Run only through scripts/reality_run.py (it needs the .env credentials).
"""
import os
import sys
from collections import Counter

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oanda_feed import _account_id, _base_url, _headers  # noqa: E402

METALS = ("XAU_USD", "XAG_USD", "XAU_GBP")


def main():
    acct = _account_id()
    r = requests.get(f"{_base_url()}/v3/accounts/{acct}/instruments", headers=_headers(), timeout=30)
    r.raise_for_status()
    inst = r.json().get("instruments", [])
    types = Counter(i.get("type", "?") for i in inst)
    print(f"account instruments endpoint: HTTP {r.status_code}; {len(inst)} instruments; types {dict(types)}")
    metal = sorted(i["name"] for i in inst if i.get("type") == "METAL" or "XAU" in i["name"] or "XAG" in i["name"])
    print(f"  METAL-type or XAU/XAG names on the account: {metal if metal else 'none'}")
    for name in METALS:
        c = requests.get(f"{_base_url()}/v3/instruments/{name}/candles", headers=_headers(),
                         params={"count": 1, "granularity": "D", "price": "M"}, timeout=30)
        body = c.json() if c.headers.get("content-type", "").startswith("application/json") else {}
        got = body.get("candles", [])
        msg = body.get("errorMessage", "")
        print(f"candles endpoint {name}: HTTP {c.status_code}; candles returned {len(got)}"
              + (f"; latest candle time {got[-1]['time']}" if got else "")
              + (f"; error: {msg[:120]}" if msg else ""))


if __name__ == "__main__":
    main()
