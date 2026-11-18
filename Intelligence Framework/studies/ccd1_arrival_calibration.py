"""ccd1_arrival_calibration.py — fire-rate calibration of the ARRIVAL alert
(docs/specs/configuration_detector_spec.md §13 and §15, addendum commit 3f83bcc,
written before any count). Report-only.

Counts how often the ARRIVAL alert would have fired on 2021-04-27 -> 2026-09-09
(the USED span; no FORWARD bar, no sealed bar) for gold, GBP/AUD and GBP/JPY,
over the §15 grid of tolerance and level list. This is not a hypothesis test:
no outcome is computed, and nothing after an arrival bar is read except the
closes that re-arm a level (spec §15).

usage: python3 ccd1_arrival_calibration.py <intel_study_archives root>
"""
import bisect, hashlib, os, statistics, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
sys.path.insert(0, os.path.dirname(W))
import ccd1_prototype as P
from regime_detection import compute_atr_series

NY = ZoneInfo("America/New_York")
START, END = "2021-04-26T21:00", "2026-09-09T21:00"      # USED sessions 2021-04-27 .. 2026-09-09
D1_WIN, H4_WIN = 220, 120
REARM = 0.50                                               # spec §13.3
BREAK_MARGIN = 0.10                                        # spec §17, owner ruling Q1: a LEVEL BREAK closes >= 0.10 x simple ATR beyond
TOLS = (0.05, 0.10, 0.15, 0.20)
LISTS = {"all five": {"D1", "H4", "RANGE", "PDAY", "PWEEK"},
         "no 4-hour swings": {"D1", "RANGE", "PDAY", "PWEEK"},
         "no prior session": {"D1", "H4", "RANGE", "PWEEK"},
         "daily swings + prior week": {"D1", "PWEEK"}}
FILES = {
    "XAU_USD": ("research_archive_legs", {"D": "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca",
                                          "H4": "e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c",
                                          "H1": "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be"}),
    "GBP_AUD": ("modern_data", {"D": "3f17cd0e7d2b7ab3492d22044876dc4703423fbd60a5d77edfc202abf0530100",
                                "H4": "623f0f5e09e2f8d39e2637eb1d307751a72be155d6214aa1fddf9deadcd77042",
                                "H1": "7c8f899f31e4f1f4d92e6c932d202ff8d3375bd5c69eb8d684b8b3f5c3509fed"}),
    "GBP_JPY": ("modern_data", {"D": "3635903a1d7d573f1489d61fd1f8eada21d1e3429feccb8a83e717700fdbc3d6",
                                "H4": "3d5131f99184ef1642b5aa075e3a8dea9cadcfb918e59cd42d6c9d7af6bfcf47",
                                "H1": "f0d2437c79778e9fbe003282a7d4f3ec5301b14b54f179f26a1c9640597e1cd3"}),
}
EXAM = ("2014-01-01", "2021-04-25")


def load(path, sha):
    raw = open(path, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != sha:
        raise SystemExit(f"{path}: sha256 {got} is not the pinned {sha}")
    out = {"t": [], "H": [], "L": [], "C": []}
    lines = raw.decode().splitlines()
    head = lines[0].split(",")
    for line in lines[1:]:
        r = dict(zip(head, line.split(",")))
        t = r["time_utc"]
        if EXAM[0] <= t[:10] <= EXAM[1]:
            raise SystemExit(f"{path}: row {t} lies in the sealed span; refusing")
        if not (START <= t[:16] <= END):
            continue
        out["t"].append(datetime.fromisoformat(t))
        out["H"].append(float(r["h"])); out["L"].append(float(r["l"])); out["C"].append(float(r["c"]))
    return out


def session_index(d1_times, tt):
    """Index of the daily bar whose 24-hour span holds tt. A live feed leaves
    out the session in progress, so an hour past the last bar's span belongs
    to a session that is not in the list yet: its index is len(d1_times),
    and every bar in the list is then complete. (Found 2026-11-17 by the
    seven-day replay: taking the last bar as "containing" made the prior
    session one day stale for every hour of the live session.)"""
    k = bisect.bisect_right(d1_times, tt) - 1
    if k == len(d1_times) - 1 and tt >= d1_times[-1] + timedelta(hours=24):
        return len(d1_times)
    return k


def trading_week(t):
    d = (t.astimezone(NY) + timedelta(hours=7)).date()
    return d.isocalendar()[:2]


def swing_table(s):
    """Per confirmed swing: (pivot i, price, kind, confirm j, broken b)."""
    H, L, C = s["H"], s["L"], s["C"]
    ph, pl = P.pivots(H, L)
    ch, cl = P.confirm_index(H, L, C, ph, pl)
    n = len(C)
    out = []
    for i in ph:
        if i in ch:
            b = next((j for j in range(i + 1, n) if C[j] > H[i]), n)
            out.append((i, H[i], "high", max(ch[i], i + P.K), b))
    for i in pl:
        if i in cl:
            b = next((j for j in range(i + 1, n) if C[j] < L[i]), n)
            out.append((i, L[i], "low", max(cl[i], i + P.K), b))
    out.sort()
    tab = _Table(out)
    tab.keys = [r[0] for r in out]
    return tab


def active(table, last, win):
    """Swings usable when bars 0..last are complete: confirmed by then, not
    broken by then, pivot within the last `win` bars. `table` is sorted by
    pivot index and carries its index list as table.keys."""
    lo = bisect.bisect_left(table.keys, last - win + 1)
    hi = bisect.bisect_right(table.keys, last)
    return [(i, p, k) for i, p, k, j, b in table[lo:hi] if j <= last and b > last]


class _Table(list):
    pass


def level_sets(ins, s):
    d1, h4, h1 = s["D"], s["H4"], s["H1"]
    d_tab, h4_tab = swing_table(d1), swing_table(h4)
    trs = [None] + [max(d1["H"][i] - d1["L"][i], abs(d1["H"][i] - d1["C"][i - 1]), abs(d1["L"][i] - d1["C"][i - 1]))
                    for i in range(1, len(d1["C"]))]
    wk = [trading_week(t) for t in d1["t"]]
    sets = []
    watr_all = compute_atr_series(d1["H"], d1["L"], d1["C"])   # watr_all[m] uses bars 0..m+14
    for t in range(len(h1["t"])):
        tt = h1["t"][t]
        kd = session_index(d1["t"], tt)                    # daily bar containing this hour
        if kd < 15:
            sets.append(None); continue
        atr = statistics.fmean(trs[kd - 14:kd])             # simple 14-day ATR, completed days (§13.2)
        lv = []
        for i, p, k in active(d_tab, kd - 1, D1_WIN):
            lv.append(("D1", f"D1{i}", p))
        j4 = bisect.bisect_right(h4["t"], tt - timedelta(hours=4)) - 1   # last 4-hour bar closed by this hour's open
        if j4 >= 0:
            for i, p, k in active(h4_tab, j4, H4_WIN):
                lv.append(("H4", f"H4{i}", p))
        lv.append(("PDAY", f"PDH{kd - 1}", d1["H"][kd - 1]))
        lv.append(("PDAY", f"PDL{kd - 1}", d1["L"][kd - 1]))
        cur_wk = wk[kd] if kd < len(wk) else trading_week(tt)   # live session not in the list
        pw = [i for i in range(max(0, kd - 12), kd) if wk[i] < cur_wk]
        if pw:
            last_wk = wk[pw[-1]]
            idx = [i for i in pw if wk[i] == last_wk]
            lv.append(("PWEEK", f"PWH{last_wk}", max(d1["H"][i] for i in idx)))
            lv.append(("PWEEK", f"PWL{last_wk}", min(d1["L"][i] for i in idx)))
        # range boundaries by §4 on bars up to t-1 (Wilder ATR, as BREAK detection runs)
        if t - 1 - P.RUN_MAX - P.K >= 0:
            watr = watr_all[kd - 1 - 14]                    # Wilder ATR through daily bar kd-1
            lo = max(0, t - 1 - P.RUN_MAX - 10)
            H, L, C = h1["H"][lo:t], h1["L"][lo:t], h1["C"][lo:t]
            ph, pl = P.pivots(H, L)
            ch, cl = P.confirm_index(H, L, C, ph, pl)
            rng = P.find_range(H, L, C, len(C) - 1, watr, set(ph), set(pl), ch, cl)
            if rng:
                lv.append(("RANGE", f"RH{rng['high']:.5f}", rng["high"]))
                lv.append(("RANGE", f"RL{rng['low']:.5f}", rng["low"]))
        sets.append((atr, lv))
    return sets


def fires_detail(s, sets, tol, kinds):
    """[(bar index, [(kind, lid, price), ...]), ...]: every ARRIVAL with the
    levels it arrived at (spec §13.3)."""
    h1 = s["H1"]
    armed = {}
    out = []
    for t, row in enumerate(sets):
        if row is None:
            continue
        atr, lv = row
        fired = []
        for kind, lid, p in lv:
            if kind not in kinds:
                continue
            if armed.get(lid) and h1["L"][t] <= p + tol * atr and h1["H"][t] >= p - tol * atr:
                armed[lid] = False
                fired.append((kind, lid, p))
        done = {f[1] for f in fired}
        for kind, lid, p in lv:
            if kind in kinds and lid not in done and abs(h1["C"][t] - p) >= REARM * atr:
                armed[lid] = True
        if fired:
            out.append((t, fired))
    return out


def fires(s, sets, tol, kinds):
    h1 = s["H1"]
    return [h1["t"][t] for t, _ in fires_detail(s, sets, tol, kinds)]


def level_breaks(s, sets, arrivals, kinds, margin=0.0, min_gap=0):
    """LEVEL BREAK (spec §17): [(bar index, [(price, side, arrival bar), ...])].
    A price that produced an ARRIVAL is watched from that bar, on the side the
    previous close was on; it stays watched while any level of a firing type
    has that price (to the cent) in the current hour's set (P4); it breaks on
    the first hourly close beyond it on the other side (the arrival bar
    included), once. The approach cooldown plays no part (P1).
    `margin` is the distance beyond the level, in simple daily ATR, that a
    close needs. The spec's rule is BREAK_MARGIN (0.10, ruling Q1); a close
    beyond by less leaves the level watched. `min_gap` (hours after the
    arrival) exists only for the P2 options table. The defaults (0, 0)
    reproduce the P2 "as written" figures."""
    C = s["H1"]["C"]
    by_t = dict(arrivals)
    watched, out = {}, []
    for t, row in enumerate(sets):
        if row is None:
            continue
        atr, lv = row
        for kind, lid, p in by_t.get(t, []):
            key = round(p, 2)
            side = 1 if C[t - 1] >= p else -1            # +1: price was above the level
            watched[key] = (p, side, t)
        present = {round(p, 2) for kind, lid, p in lv if kind in kinds}
        broke = []
        for key in list(watched):
            p, side, t0 = watched[key]
            if key not in present:
                del watched[key]                          # no qualification holds
                continue
            beyond = (p - C[t]) if side == 1 else (C[t] - p)     # distance closed through, in price
            if t - t0 >= min_gap and beyond > 0 and beyond >= margin * atr:
                broke.append((p, side, t0))
                del watched[key]
        if broke:
            out.append((t, broke))
    return out


def main(root):
    print("# ARRIVAL fire-rate calibration (spec §13/§15, addendum 3f83bcc); counts only, no outcome\n")
    data, sets = {}, {}
    for ins, (sub, shas) in FILES.items():
        data[ins] = {k: load(os.path.join(root, sub, f"{ins}_{k}.csv"), sha) for k, sha in shas.items()}
        sets[ins] = level_sets(ins, data[ins])
        h1 = data[ins]["H1"]
        n_lv = [len(r[1]) for r in sets[ins] if r]
        print(f"{ins}: hourly bars {len(h1['t'])} ({h1['t'][0]:%Y-%m-%d} -> {h1['t'][-1]:%Y-%m-%d}); "
              f"levels per bar median {statistics.median(n_lv):.0f}, max {max(n_lv)}")
    t0 = min(d["H1"]["t"][0] for d in data.values())
    t1 = max(d["H1"]["t"][-1] for d in data.values())
    weeks = (t1 - t0).days / 7
    all_weeks = sorted({trading_week(t0 + timedelta(days=k)) for k in range((t1 - t0).days + 1)
                        if (t0 + timedelta(days=k)).weekday() < 5})
    print(f"span {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}: {weeks:.1f} calendar weeks, {len(all_weeks)} trading weeks\n")
    print("| Level list | Tolerance (ATR) | Gold / week | GBP/AUD / week | GBP/JPY / week | **Total / week** | Total: median week | Total: 90th-pct week |")
    print("|---|---|---|---|---|---|---|---|")
    for name, kinds in LISTS.items():
        for tol in TOLS:
            per, wkc = {}, Counter()
            for ins in FILES:
                f = fires(data[ins], sets[ins], tol, kinds)
                per[ins] = len(f) / len(all_weeks)
                for t in f:
                    wkc[trading_week(t)] += 1
            counts = sorted(wkc.get(w, 0) for w in all_weeks)
            p90 = counts[int(0.9 * (len(counts) - 1))]
            print(f"| {name} | {tol:.2f} | {per['XAU_USD']:.1f} | {per['GBP_AUD']:.1f} | {per['GBP_JPY']:.1f} | "
                  f"**{sum(per.values()):.1f}** | {statistics.median(counts):.0f} | {p90} |")


if __name__ == "__main__":
    main(sys.argv[1])
