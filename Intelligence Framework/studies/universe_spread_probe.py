"""Breadth universe, step C1: real spreads from the account and the ruled
selection (team ruling 2026-11-06: independence first, spread second).

usage: python3 -I universe_spread_probe.py <n_sessions>      (run via reality_run)

Read-only. For every CURRENCY instrument on the account, one request for
bid/ask H1 candles over the last <n_sessions> complete weekday sessions (a
recent window; no 2014-2021 bar is requested). From each candle only the
closing spread is kept (ask close - bid close), in pips (the instrument's
pipLocation) and in basis points of the closing mid. Prices are discarded on
receipt; only spreads are printed.

Selection (select(), pinned by tests/test_universe_spread_probe.py), the
ruled criteria in order:
  1. no currency in more than MAX_PER_CURRENCY (3) selected pairs;
  2. crosses (no USD leg) before any USD pair;
  3. within each group, lowest median spread in basis points of price;
  4. at most CAP (10) pairs; GBP_AUD and GBP_JPY are included first;
  5. pairs already examined for edge are excluded (EXCLUDED).
Greedy in that order; the order dependence is stated, not hidden.
"""
import os
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UTC = timezone.utc
INCLUDED = ("GBP_AUD", "GBP_JPY")
EXCLUDED = {"GBP_USD": "lagged returns tested as predictors (leg study, 2026-11-05)",
            "AUD_USD": "lagged returns tested as predictors (leg study, 2026-11-05)",
            "USD_JPY": "lagged returns tested as predictors (leg study, 2026-11-05)"}
CAP = 10
MAX_PER_CURRENCY = 3
LIQUID_HOURS_UTC = range(7, 16)


def legs(pair):
    return tuple(pair.split("_"))


def is_cross(pair):
    return "USD" not in legs(pair)


def select(spread_bps, included=INCLUDED, excluded=EXCLUDED, cap=CAP, max_per=MAX_PER_CURRENCY):
    """Return (chosen pairs in order, skipped {pair: reason})."""
    chosen, counts, skipped = [], Counter(), {}
    for p in included:
        chosen.append(p)
        counts.update(legs(p))
    pool = [p for p in spread_bps if p not in chosen]
    crosses = sorted((p for p in pool if is_cross(p)), key=lambda p: (spread_bps[p], p))
    majors = sorted((p for p in pool if not is_cross(p)), key=lambda p: (spread_bps[p], p))
    for p in crosses + majors:
        if p in excluded:
            skipped[p] = "excluded: " + excluded[p]
            continue
        if len(chosen) >= cap:
            skipped[p] = "cap reached"
            continue
        full = [c for c in legs(p) if counts[c] + 1 > max_per]
        if full:
            skipped[p] = f"would put {', '.join(full)} in more than {max_per} pairs"
            continue
        chosen.append(p)
        counts.update(legs(p))
    return chosen, skipped


def main(n_sessions):
    from oanda_feed import _account_id, _base_url, _headers
    acct = _account_id()
    r = requests.get(f"{_base_url()}/v3/accounts/{acct}/instruments", headers=_headers(), timeout=30)
    r.raise_for_status()
    inst = {i["name"]: i for i in r.json()["instruments"] if i.get("type") == "CURRENCY"}
    now = datetime.now(UTC)
    frm = now - timedelta(days=int(n_sessions * 7 / 5) + 4)
    stats = {}
    for name in sorted(inst):
        pip = 10 ** int(inst[name]["pipLocation"])
        c = requests.get(f"{_base_url()}/v3/instruments/{name}/candles", headers=_headers(), timeout=30,
                         params={"granularity": "H1", "price": "BA", "from": frm.strftime("%Y-%m-%dT%H:%M:%SZ")})
        c.raise_for_status()
        rows = []
        for k in c.json().get("candles", []):
            if not k.get("complete"):
                continue
            t = datetime.strptime(k["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
            if t.weekday() >= 5:
                continue
            a, b = float(k["ask"]["c"]), float(k["bid"]["c"])
            rows.append((t, (a - b) / pip, (a - b) / ((a + b) / 2) * 1e4))   # prices dropped here
        sessions = sorted({t.date() for t, _, _ in rows})[-n_sessions:]
        keep = [x for x in rows if x[0].date() in sessions]
        liq = [x for x in keep if x[0].hour in LIQUID_HOURS_UTC]
        stats[name] = {"n": len(keep), "pips": statistics.median(x[1] for x in keep),
                       "bps": statistics.median(x[2] for x in keep),
                       "liq_pips": statistics.median(x[1] for x in liq) if liq else float("nan"),
                       "first": keep[0][0], "last": keep[-1][0]}
    span = (min(s["first"] for s in stats.values()), max(s["last"] for s in stats.values()))
    print(f"CURRENCY instruments on the account: {len(inst)}; H1 bid/ask closes over the last "
          f"{n_sessions} weekday sessions ({span[0]:%Y-%m-%d %H:%M} to {span[1]:%Y-%m-%d %H:%M} UTC); "
          f"spreads only, prices discarded\n")
    print("| pair | cross? | median spread, pips | median spread, bp of price | London/NY hours median, pips | H1 closes |")
    print("|---|---|---|---|---|---|")
    for name in sorted(stats, key=lambda p: (not is_cross(p), stats[p]["bps"])):
        s = stats[name]
        print(f"| {name} | {'yes' if is_cross(name) else 'no'} | {s['pips']:.2f} | {s['bps']:.2f} | "
              f"{s['liq_pips']:.2f} | {s['n']} |")
    chosen, skipped = select({p: s["bps"] for p, s in stats.items()})
    print(f"\n## Selected universe ({len(chosen)} pairs)\n")
    print("| # | pair | cross? | median spread, pips | bp of price |")
    print("|---|---|---|---|---|")
    for k, p in enumerate(chosen, 1):
        print(f"| {k} | {p} | {'yes' if is_cross(p) else 'no'} | {stats[p]['pips']:.2f} | {stats[p]['bps']:.2f} |")
    counts = Counter(c for p in chosen for c in legs(p))
    print("\n## Currency count (limit 3)\n")
    print("| currency | pairs | " + " | ".join(sorted(counts)) + " |")
    print("|---|---|" + "---|" * len(counts))
    print("| count | | " + " | ".join(str(counts[c]) for c in sorted(counts)) + " |")
    print(f"\nlargest count: {max(counts.values())} (limit {MAX_PER_CURRENCY}): "
          f"{'MET' if max(counts.values()) <= MAX_PER_CURRENCY else 'VIOLATED'}")
    print("\n## Passed over before the cap, in ranked order\n")
    for p in [p for p in sorted(skipped, key=lambda p: (not is_cross(p), stats[p]['bps']))
              if not skipped[p].startswith("cap")][:25]:
        print(f"- {p} ({stats[p]['bps']:.2f} bp): {skipped[p]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(int(sys.argv[1]))
