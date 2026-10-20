"""Reduced gate: OANDA historical API bars today vs the framework's own stored
bars. Reports DIFFERENCES only (pips), never price levels.

usage: python3 -I history_depth_reduced_gate.py <env_file> <inputs_dir> <out_dir>

inputs_dir holds copies of:
  gbpaud_D.csv gbpaud_H4.csv gbpaud_H1.csv gbpjpy_D_overlap.csv
  gbpjpy_H4_overlap.csv   (studies/data_cache, OANDA pulls of 2026-09-10/11)
  regime_classification_log.csv  (live ledger; rows with price_basis=d1_close)
"""
import csv
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_depth_oanda_probe as P  # noqa: E402  (guard + client)

NY = ZoneInfo("America/New_York")
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
CACHE = [("GBP_AUD", "D", "gbpaud_D.csv"), ("GBP_AUD", "H4", "gbpaud_H4.csv"),
         ("GBP_AUD", "H1", "gbpaud_H1.csv"), ("GBP_JPY", "D", "gbpjpy_D_overlap.csv"),
         ("GBP_JPY", "H4", "gbpjpy_H4_overlap.csv")]


def fetch_ohlc(cl, pair, gran, s, e):
    out = {}
    e = min(e, datetime.now(timezone.utc) - timedelta(minutes=1))
    lo = s
    while lo < e:
        hi = min(lo + timedelta(days=31), e)
        P.guard(lo, hi)
        st, p = cl.candles(pair, {"granularity": gran, "price": "M",
                                  "from": P.iso(lo), "to": P.iso(hi)})
        if st != 200:
            raise RuntimeError(f"{pair} {gran}: HTTP {st} {p}")
        for c in p.get("candles", []):
            if not c.get("complete", True):
                continue
            m = c["mid"]
            out[P.parse(c["time"])] = tuple(float(m[k]) for k in "ohlc")
        lo = hi
    return out


def dist(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    q = lambda f: xs[min(len(xs) - 1, int(round(f * (len(xs) - 1))))]
    return {"n": len(xs), "nonzero": sum(1 for x in xs if x > 0), "median": q(0.5),
            "p95": q(0.95), "p99": q(0.99), "max": xs[-1]}


def cache_compare(cl, inputs, pair, gran, fname):
    stored = {}
    with open(os.path.join(inputs, fname)) as fh:
        for r in csv.DictReader(fh):
            t = datetime.fromisoformat(r["time"].replace(" ", "T")).astimezone(timezone.utc)
            stored[t] = tuple(float(r[k]) for k in ("Open", "High", "Low", "Close"))
    s, e = min(stored), max(stored) + timedelta(hours=1)
    api = fetch_ohlc(cl, pair, gran, s, e)
    common = sorted(set(stored) & set(api))
    pip = PIP[pair]
    diffs = {k: [] for k in "OHLC"}
    exact = 0
    for t in common:
        d = [round(abs(a - b) / pip, 3) for a, b in zip(stored[t], api[t])]
        for k, v in zip("OHLC", d):
            diffs[k].append(v)
        exact += all(v < 1e-6 for v in d)
    return {"pair": pair, "gran": gran, "stored_rows": len(stored), "api_rows": len(api),
            "stored_first": min(stored).isoformat(), "stored_last": max(stored).isoformat(),
            "compared": len(common), "exact_all_fields": exact,
            "stored_only": len(set(stored) - set(api)), "api_only": len(set(api) - set(stored)),
            "abs_diff_pips": {k: dist(v) for k, v in diffs.items()}}


def close_time(start_utc):
    ny = start_utc.astimezone(NY)
    nxt = datetime(ny.year, ny.month, ny.day, 17, tzinfo=NY) + timedelta(days=1)
    return nxt.astimezone(timezone.utc)


def ledger_compare(cl, inputs):
    rows = []
    with open(os.path.join(inputs, "regime_classification_log.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("price_basis") == "d1_close" and r.get("price_at_log"):
                rows.append(r)
    res = {"rows": len(rows), "per_pair": {}}
    for pair in ("GBP_AUD", "GBP_JPY"):
        pr = [r for r in rows if r["instrument"] == pair]
        if not pr:
            continue
        ts = [datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) for r in pr]
        api = fetch_ohlc(cl, pair, "D", min(ts) - timedelta(days=10), max(ts) + timedelta(days=1))
        starts = sorted(api)
        diffs, exact, prev_match, unmatched = [], 0, 0, []
        for r, T in zip(pr, ts):
            done = [s for s in starts if close_time(s) <= T]
            if not done:
                unmatched.append(r["timestamp"])
                continue
            s = done[-1]
            d = round(abs(float(r["price_at_log"]) - api[s][3]) / PIP[pair], 3)
            diffs.append(d)
            if d < 1e-6:
                exact += 1
            elif len(done) > 1 and abs(float(r["price_at_log"]) - api[done[-2]][3]) / PIP[pair] < 1e-6:
                prev_match += 1
        res["per_pair"][pair] = {"rows": len(pr), "compared": len(diffs), "exact": exact,
                                 "mismatch_matching_previous_bar": prev_match,
                                 "unmatched": unmatched, "abs_diff_pips": dist(diffs),
                                 "first_log": min(ts).isoformat(), "last_log": max(ts).isoformat()}
    return res


def main():
    env_file, inputs, out = sys.argv[1:4]
    cl = P.Client(P.load_env(env_file))
    result = {"cache": [cache_compare(cl, inputs, *c) for c in CACHE],
              "ledger_d1_close": ledger_compare(cl, inputs), "requests": None}
    result["requests"] = cl.requests
    with open(os.path.join(out, "reduced_gate.json"), "w") as fh:
        json.dump(result, fh, indent=1)
    for c in result["cache"]:
        print(c["pair"], c["gran"], "compared", c["compared"], "exact", c["exact_all_fields"],
              "stored_only", c["stored_only"], "api_only", c["api_only"],
              {k: (v.get("nonzero"), v.get("max")) for k, v in c["abs_diff_pips"].items()})
    for p, v in result["ledger_d1_close"]["per_pair"].items():
        print("ledger", p, {k: v[k] for k in ("rows", "compared", "exact", "mismatch_matching_previous_bar")},
              v["abs_diff_pips"], "unmatched", len(v["unmatched"]))
    print("requests", cl.requests)


if __name__ == "__main__":
    main()
