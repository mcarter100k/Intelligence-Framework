"""broker_capability_probe.py — what can this OANDA account actually do?
(execution readiness item A3, 2026-11-06). READ-ONLY.

Only GET requests. No order is placed, modified or cancelled, not even a test
one. Balance, NAV, P&L and the account id are never printed.

Reports:
  - account configuration: currency, hedging, guaranteed-stop mode, margin
    rate, open trade / position / pending-order counts;
  - per traded pair (GBP_AUD, GBP_JPY): minimum trade size, unit precision,
    maximum order units, margin rate, trailing-stop distance limits,
    guaranteed-stop settings, pip location;
  - whether the orders and trades endpoints answer a read for this token.
Whether the token may PLACE orders cannot be shown without placing one; the
report says so.

Run only through scripts/reality_run.py (it needs the .env credentials).
"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oanda_feed import _account_id, _base_url, _headers  # noqa: E402

PAIRS = ("GBP_AUD", "GBP_JPY")
ACCOUNT_FIELDS = ("currency", "hedgingEnabled", "guaranteedStopLossOrderMode", "marginRate",
                  "openTradeCount", "openPositionCount", "pendingOrderCount")
INSTRUMENT_FIELDS = ("type", "pipLocation", "displayPrecision", "tradeUnitsPrecision",
                     "minimumTradeSize", "maximumOrderUnits", "maximumPositionSize", "marginRate",
                     "minimumTrailingStopDistance", "maximumTrailingStopDistance",
                     "guaranteedStopLossOrderMode", "minimumGuaranteedStopLossDistance")


def get(path, **params):
    r = requests.get(f"{_base_url()}{path}", headers=_headers(), params=params, timeout=30)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


def main():
    acct = _account_id()
    host = "practice" if "fxpractice" in _base_url() else "live (fxtrade)"
    print(f"environment: {host}")
    st, body = get(f"/v3/accounts/{acct}")
    a = body.get("account", {})
    print(f"GET account: HTTP {st}")
    for k in ACCOUNT_FIELDS:
        print(f"  {k}: {a.get(k, '(absent)')}")
    print("  balance / NAV / P&L: present in the response, not printed"
          if "balance" in a else "  balance: absent from the response")
    st, body = get(f"/v3/accounts/{acct}/instruments", instruments=",".join(PAIRS))
    print(f"GET instruments: HTTP {st}")
    for ins in body.get("instruments", []):
        print(f"  {ins['name']}:")
        for k in INSTRUMENT_FIELDS:
            print(f"    {k}: {ins.get(k, '(absent)')}")
    for path in ("orders", "pendingOrders", "trades", "openTrades", "positions"):
        st, body = get(f"/v3/accounts/{acct}/{path}")
        n = len(body.get(path if path != "pendingOrders" else "orders", body.get(path, [])) or [])
        print(f"GET {path}: HTTP {st}; items returned {n}")
    print("order placement: NOT TESTED (it would require placing an order). "
          "The v3 API's order types are MARKET, LIMIT, STOP, MARKET_IF_TOUCHED, "
          "TAKE_PROFIT, STOP_LOSS, GUARANTEED_STOP_LOSS and TRAILING_STOP_LOSS; "
          "which of them this token may place is unverified.")


if __name__ == "__main__":
    main()
