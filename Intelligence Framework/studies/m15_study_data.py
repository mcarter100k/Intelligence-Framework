"""GBP_AUD 15-minute STUDY data (2005-2013) for BCS-3, and its check against
the research archive's verified H1 bars.

usage:
  python3 -I m15_study_data.py fetch <out_dir>            (needs OANDA credentials)
  python3 -I m15_study_data.py verify <out_dir> <archive_dir>

fetch pulls OANDA M15 mid candles through the embargo-guarded
history_study_gate_s3.fetch (it refuses the 2013-12-30 22:00Z ->
2021-04-26 21:00Z block), keeps Monday-Friday sessions only, and writes
GBP_AUD_M15.csv and data_hashes.json outside the repo.

verify re-hashes the file, then aggregates each hour's four M15 bars and
compares them with the archive's STUDY H1 bar for that hour. It prints counts
and |difference| in pips only: no price level, range or outcome.
"""
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_study_convert as C  # noqa: E402
import history_study_gate_s3 as G  # noqa: E402  guarded fetch + sealed block

PAIR, PIP, TOL = "GBP_AUD", 0.0001, 0.5
NAME = f"{PAIR}_M15.csv"


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def keep(t):
    """STUDY M15 bar: a Monday-Friday session, outside the sealed block."""
    if G.BLOCK_START <= t < G.BLOCK_END:
        raise G.Blocked(f"blocked candle {t.isoformat()}")
    return t < G.BLOCK_START and C.session_day(t).weekday() < 5


def fetch(out_dir):
    repo = os.path.dirname(HERE)
    if os.path.abspath(out_dir).startswith(repo + os.sep):
        raise SystemExit("refused: out_dir must be outside the repo")
    os.makedirs(out_dir, exist_ok=True)
    cl = G.P.Client(dict(os.environ))
    raw = G.fetch(cl, PAIR, "M15")
    rows = {t: v for t, v in raw.items() if keep(t)}
    p = os.path.join(out_dir, NAME)
    G.save(p, rows)
    with open(os.path.join(out_dir, "data_hashes.json"), "w") as fh:
        json.dump({NAME: sha(p)}, fh, indent=1)
    print(f"{PAIR} M15: fetched {len(raw)}, kept {len(rows)} (dropped {len(raw) - len(rows)} weekend-session bars); "
          f"first {min(rows).isoformat()}, last {max(rows).isoformat()}; requests {cl.requests}; sha256 {sha(p)}")


def load(out_dir):
    with open(os.path.join(out_dir, "data_hashes.json")) as fh:
        h = json.load(fh)[NAME]
    p = os.path.join(out_dir, NAME)
    if sha(p) != h:
        raise RuntimeError(f"{NAME}: sha256 differs from data_hashes.json: refused")
    out = {}
    with open(p) as fh:
        for r in csv.DictReader(fh):
            t = datetime.fromisoformat(r["time_utc"])
            if not keep(t):
                raise RuntimeError(f"{t.isoformat()} is not a STUDY weekday-session bar: refused")
            out[t] = tuple(float(r[k]) for k in "ohlc")
    return out


def aggregate(m15):
    """{hour open: (o, h, l, c, n bars)} from M15 bars."""
    by = defaultdict(list)
    for t in sorted(m15):
        by[t.replace(minute=0)].append(t)
    return {hr: (m15[ts[0]][0], max(m15[x][1] for x in ts), min(m15[x][2] for x in ts), m15[ts[-1]][3], len(ts))
            for hr, ts in by.items()}


def compare(agg, h1, tol=TOL):
    """Counts of hours matched within tol pips on all four prices, by part."""
    res = {"archive hours": len(h1), "m15 hours": len(agg), "hours in both": 0, "all four within tol": 0,
           "archive hours with no M15": 0, "M15 hours not in archive": 0, "full hours (4 bars)": 0,
           "max |diff| pips o/h/l/c": [0.0] * 4, "hours over tol": []}
    for hr, v in h1.items():
        a = agg.get(hr)
        if a is None:
            res["archive hours with no M15"] += 1
            continue
        res["hours in both"] += 1
        res["full hours (4 bars)"] += a[4] == 4
        diffs = [abs(a[i] - v[i]) / PIP for i in range(4)]
        for i in range(4):
            res["max |diff| pips o/h/l/c"][i] = max(res["max |diff| pips o/h/l/c"][i], round(diffs[i], 2))
        if max(diffs) <= tol:
            res["all four within tol"] += 1
        else:
            res["hours over tol"].append(hr)
    res["M15 hours not in archive"] = sum(1 for hr in agg if hr not in h1)
    return res


def verify(out_dir, archive_dir):
    import research_archive as RA
    m15 = load(out_dir)
    h1 = RA.load(archive_dir, PAIR, "H1", {"STUDY"})
    res = compare(aggregate(m15), h1)
    over = res.pop("hours over tol")
    for k, v in res.items():
        print(f"{k}: {v}")
    print(f"hours over tol: {len(over)}; first 10: {[t.isoformat() for t in over[:10]]}")
    print(f"share within tol: {res['all four within tol'] / res['hours in both']:.4%}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "fetch":
        fetch(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "verify":
        verify(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
