"""Gold 30/15/5-minute mid candles and 5-minute bid/ask for the 2021-2026 USED
span, for GLS-1 (docs/specs/gold_ltf_structure_spec.md, ruling F1: USED only).

usage:
  python3 -I gold_subhourly_used_data.py fetch <out_dir> <archive_dir>   (needs OANDA credentials)
  python3 -I gold_subhourly_used_data.py verify <out_dir> <archive_dir>

fetch pulls through history_study_gate_s3.guard in 7-day windows (OANDA's
5,000-candle cap). The guard keeps a one-day margin after the sealed block, so
the first fetched session starts 2021-04-27 21:00Z, one session after the
archive's USED start. Nothing after the USED end (2026-09-09 21:00Z) is
requested. Files go outside the repo, with data_hashes.json.

verify re-hashes the files, aggregates each hour's sub-bars and compares them
with the archive's USED H1 bar: share of fully covered hours within $0.05
(the GLS-1 §7.1 bar is 99%) and every larger disagreement. Prints counts and
dollar differences only.
"""
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_study_gate_s3 as G  # noqa: E402  guarded windows + sealed block

P = G.P
UTC = timezone.utc
START = G.BLOCK_END + timedelta(days=1)                  # 2021-04-27 21:00Z
END = datetime(2026, 9, 9, 21, 0, tzinfo=UTC)            # close of the last USED H1 bar
MID = {"M30": 2, "M15": 4, "M5": 12}
H1_PIN = "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be"
TOL, BAR = 0.05, 0.99


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def pull(cl, gran, price):
    rows, lo = {}, START
    while lo < END:
        hi = min(lo + timedelta(days=7), END)
        G.guard(lo, hi)
        st, p = cl.candles("XAU_USD", {"granularity": gran, "price": price, "from": P.iso(lo), "to": P.iso(hi)})
        if st != 200:
            raise RuntimeError(f"{gran} {price} {lo}: HTTP {st} {p}")
        for c in p.get("candles", []):
            t = P.parse(c["time"])
            if G.BLOCK_START <= t < G.BLOCK_END:
                raise G.Blocked(f"API returned blocked candle {t}; aborting")
            if not c.get("complete", True) or not START <= t < END:
                continue
            if price == "M":
                rows[t] = tuple(float(c["mid"][k]) for k in "ohlc")
            else:
                rows[t] = (float(c["bid"]["c"]), float(c["ask"]["c"]))
        lo = hi
    return rows


def write(path, header, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for t in sorted(rows):
            w.writerow([t.isoformat(), *rows[t]])


def fetch(out_dir):
    if os.path.abspath(out_dir).startswith(os.path.dirname(HERE) + os.sep):
        raise SystemExit("refused: out_dir must be outside the repo")
    os.makedirs(out_dir, exist_ok=True)
    cl = P.Client(dict(os.environ))
    hashes = {}
    for g in MID:
        rows = pull(cl, g, "M")
        name = f"XAU_USD_{g}_USED.csv"
        write(os.path.join(out_dir, name), ["time_utc", "o", "h", "l", "c"], rows)
        hashes[name] = sha(os.path.join(out_dir, name))
        print(f"{g} mid: {len(rows)} bars, {min(rows).isoformat()} -> {max(rows).isoformat()}; sha256 {hashes[name]}")
    rows = pull(cl, "M5", "BA")
    name = "XAU_USD_M5_BA_USED.csv"
    write(os.path.join(out_dir, name), ["time_utc", "bid_c", "ask_c"], rows)
    hashes[name] = sha(os.path.join(out_dir, name))
    print(f"M5 bid/ask: {len(rows)} bars, {min(rows).isoformat()} -> {max(rows).isoformat()}; sha256 {hashes[name]}")
    with open(os.path.join(out_dir, "data_hashes.json"), "w") as fh:
        json.dump(hashes, fh, indent=1)
    print(f"requests {cl.requests}")


def load(path):
    out = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            out[datetime.fromisoformat(r["time_utc"])] = tuple(float(r[k]) for k in "ohlc")
    return out


def verify(out_dir, archive_dir):
    hashes = json.load(open(os.path.join(out_dir, "data_hashes.json")))
    for name, h in hashes.items():
        got = sha(os.path.join(out_dir, name))
        if got != h:
            raise SystemExit(f"{name}: sha256 {got} != recorded {h}")
    arch_path = os.path.join(archive_dir, "XAU_USD_H1.csv")
    if sha(arch_path) != H1_PIN:
        raise SystemExit("archive H1 is not the pinned file")
    h1 = {}
    for r in csv.DictReader(open(arch_path)):
        t = datetime.fromisoformat(r["time_utc"])
        if r["span"] == "USED" and START <= t and t + timedelta(hours=1) <= END:
            h1[t] = tuple(float(r[k]) for k in "ohlc")
    ok_all = True
    for g, k in MID.items():
        sub = load(os.path.join(out_dir, f"XAU_USD_{g}_USED.csv"))
        hours = defaultdict(list)
        for t, v in sub.items():
            hours[t.replace(minute=0)].append((t, v))
        full, within, bad = 0, 0, []
        for hr, v in sorted(h1.items()):
            bars = sorted(hours.get(hr, []))
            if len(bars) != k:
                continue
            full += 1
            agg = (bars[0][1][0], max(b[1][1] for b in bars), min(b[1][2] for b in bars), bars[-1][1][3])
            d = max(abs(x - y) for x, y in zip(agg, v))
            if d <= TOL:
                within += 1
            else:
                bad.append((hr, d))
        share = within / full if full else 0.0
        ok = share >= BAR
        ok_all &= ok
        print(f"{g}: bars {len(sub)}; archive H1 hours {len(h1)}; fully covered {full} ({100 * full / len(h1):.2f}%); "
              f"within ${TOL:.2f}: {within} ({100 * share:.3f}%) -> {'PASS' if ok else 'FAIL'}; larger: {len(bad)}")
        for hr, d in bad[:20]:
            print(f"   {hr.isoformat()} |d| ${d:.3f}")
        if len(bad) > 20:
            print(f"   ... {len(bad) - 20} more")
    print("VERIFY " + ("PASS" if ok_all else "FAIL"))


if __name__ == "__main__":
    mode, out_dir, archive_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    fetch(out_dir) if mode == "fetch" else verify(out_dir, archive_dir)
