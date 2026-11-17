"""Read-only: is XAU_USD on this account's tradeable list today, and what financing
fields does OANDA return for listed instruments? No order is placed. Prints types,
names, financing rates and day-of-week charges; no price."""
import json, os, sys
from collections import Counter
import requests
sys.path.insert(0, sys.argv[1])
from oanda_feed import _account_id, _base_url, _headers
acct = _account_id()
r = requests.get(f"{_base_url()}/v3/accounts/{acct}/instruments", headers=_headers(), timeout=30)
print("instruments HTTP", r.status_code)
inst = r.json().get("instruments", [])
print("count", len(inst), "types", dict(Counter(i.get("type") for i in inst)))
print("metal-like names:", [i["name"] for i in inst if "XAU" in i["name"] or "XAG" in i["name"] or i.get("type") == "METAL"])
for name in ("GBP_AUD", "GBP_JPY", "EUR_USD"):
    i = next((x for x in inst if x["name"] == name), None)
    print(name, json.dumps(i.get("financing") if i else "not listed"))
r2 = requests.get(f"{_base_url()}/v3/accounts/{acct}/instruments", headers=_headers(), params={"instruments": "XAU_USD"}, timeout=30)
print("instruments?instruments=XAU_USD HTTP", r2.status_code, json.dumps(r2.json())[:300])
r3 = requests.get(f"{_base_url()}/v3/accounts/{acct}/summary", headers=_headers(), timeout=30)
a = r3.json().get("account", {})
print("summary HTTP", r3.status_code, {k: a.get(k) for k in ("currency", "marginRate", "hedgingEnabled", "guaranteedStopLossOrderMode", "openTradeCount", "pendingOrderCount")})
