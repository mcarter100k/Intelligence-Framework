"""ccd1_arrival_lastweek.py — owner ruling N4 (2026-11-17). Report-only.

Replays the chosen ARRIVAL alert (spec §13; ruling M3: daily swings, range
boundaries, prior session, prior week; tolerance 0.10 x simple ATR) over the
last seven days of live gold hourly bars and prints, alert by alert, what it
would have sent, with times in Pacific. The arming state is warmed up on the
bars before the window. Then it traces the $3,832.46 level through tonight's
break. Read-only (run through scripts/reality_run.py); writes nothing.

Prototype rendering only: the live alert is built after this, from the spec.
"""
import bisect, csv, os, statistics, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
sys.path.insert(0, os.path.dirname(W))
import ccd1_arrival_calibration as A
import ccd1_prototype as P
import oanda_feed as F
from display_time import to_display

PT = ZoneInfo("America/Los_Angeles")
TOL = 0.10
KINDS = {"D1", "RANGE", "PDAY", "PWEEK"}                    # ruling M3
ALL5 = {"D1", "H4", "RANGE", "PDAY", "PWEEK"}               # distances and the briefing (N3)
NAMES = {"D1": "daily swing", "H4": "4-hour swing", "RANGE": "hourly range edge",
         "PDAY": "prior session", "PWEEK": "prior week"}
WATCH = 3832.46


def pt(t):
    """12-hour Pacific through the one helper (display_timezone_spec addendum 2026-11-18)."""
    return to_display(t, style="day_date")


def series(df):
    return {"t": [x.to_pydatetime() for x in df.index], "H": [float(v) for v in df["High"]],
            "L": [float(v) for v in df["Low"]], "C": [float(v) for v in df["Close"]]}


def fires_detail(s, sets, tol, kinds, trace=None):
    """A.fires with the levels that fired kept (same logic, line for line);
    `trace(t, lid, event)` sees arming changes for chosen levels."""
    h1 = s["H1"]
    armed, out = {}, []
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
                if trace: trace(t, lid, "FIRED")
        for kind, lid, p in lv:
            if kind in kinds and lid not in {f[1] for f in fired} and abs(h1["C"][t] - p) >= A.REARM * atr:
                if trace and not armed.get(lid): trace(t, lid, f"armed (close {h1['C'][t]:.2f}, {abs(h1['C'][t] - p) / atr:.2f} ATR away)")
                armed[lid] = True
        if fired:
            out.append((t, fired))
    return out


def origin(lid, kind, s, t):
    d1 = s["D"]
    if kind == "D1":
        return f"the daily swing of the session that opened {pt(d1['t'][int(lid[2:])])}"
    if kind == "PDAY":
        k = int(lid[3:])
        return f"{'high' if lid.startswith('PDH') else 'low'} of the session that opened {pt(d1['t'][k])}"
    if kind == "PWEEK":
        return f"{'high' if lid.startswith('PWH') else 'low'} of trading week {lid[3:]}"
    return "the current hourly range (spec §4)"


def history(s, p, start, t, tol_px, below):
    """Visits within tolerance of p on hourly bars from `start` to t-1; held =
    no hourly close beyond p (below it if the level is under price)."""
    h1 = s["H1"]
    i0 = bisect.bisect_left(h1["t"], start)
    visits, inside = [], False
    for i in range(i0, t):
        near = h1["L"][i] <= p + tol_px and h1["H"][i] >= p - tol_px
        if near and not inside:
            visits.append([i, True])
        if near:
            beyond = h1["C"][i] < p if below else h1["C"][i] > p
            if beyond:
                visits[-1][1] = False
        inside = near
    return len(visits), sum(1 for v in visits if v[1]), (h1["t"][visits[-1][0]] if visits else None)


def start_of(lid, kind, s, t):
    d1, h1 = s["D"], s["H1"]
    if kind in ("D1",):
        return d1["t"][int(lid[2:])]
    if kind == "PDAY":
        return d1["t"][int(lid[3:])]
    if kind == "PWEEK":
        return h1["t"][t] - timedelta(days=14)
    return h1["t"][t] - timedelta(hours=P.RUN_MAX)


def calendar_lines(after):
    try:
        rows = [r for r in csv.DictReader(open("calendar.csv")) if r["currency"] == "USD" and r["impact"] == "High"]
    except OSError:
        return "news calendar missing"
    all_rows = list(csv.DictReader(open("calendar.csv")))
    first = min(datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc) for r in all_rows)
    if after < first - timedelta(days=1):
        return "not available: only the current week's calendar is stored, and this hour is before it"
    nxt = sorted(datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc) for r in rows
                 if datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc) > after)
    if not nxt:
        return "no High-impact US release left in the stored week"
    ev = [r["event"] for r in rows if datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc) == nxt[0]]
    mins = int((nxt[0] - after).total_seconds() // 60)
    return f"{', '.join(ev)} at {pt(nxt[0])}, in {mins // 60}h {mins % 60:02d}m"


def window_line(now):
    p = now.astimezone(PT)
    start = p.replace(hour=4, minute=0, second=0, microsecond=0)
    end = p.replace(hour=8, minute=0, second=0, microsecond=0)
    if p < start:
        m = int((start - p).total_seconds() // 60)
        return f"before gold's 4-8 AM PT window (it opens in {m // 60}h {m % 60:02d}m)"
    if p < end:
        return f"inside gold's 4-8 AM PT window ({int((end - p).total_seconds() // 60)} minutes left)"
    return "after gold's 4-8 AM PT window"


def main():
    s = {"H1": series(F.get_hourly_bars("XAU_USD", count=1000)),
         "H4": series(F.get_h4_bars("XAU_USD", count=500)),
         "D": series(F.get_daily_bars("XAU_USD", count=520))}
    h1, d1 = s["H1"], s["D"]
    now = datetime.now(timezone.utc)
    print(f"bars: hourly {len(h1['t'])} ({pt(h1['t'][0])} -> {pt(h1['t'][-1])}), 4-hour {len(s['H4']['t'])}, daily {len(d1['t'])}")
    print(f"run at {pt(now)}; window: hourly bars closing in the last 7 days\n")
    sets = A.level_sets("XAU_USD", s)
    watch_ids = set()
    for row in sets:
        if row:
            for kind, lid, p in row[1]:
                if abs(p - WATCH) < 0.005:
                    watch_ids.add(lid)
    log = []
    det = fires_detail(s, sets, TOL, KINDS, trace=lambda t, lid, ev: log.append((t, lid, ev)) if lid in watch_ids else None)
    assert [h1["t"][t] for t, _ in det] == A.fires(s, sets, TOL, KINDS)       # same logic as the calibration
    trs = [None] + [max(d1["H"][i] - d1["L"][i], abs(d1["H"][i] - d1["C"][i - 1]), abs(d1["L"][i] - d1["C"][i - 1]))
                    for i in range(1, len(d1["C"]))]
    cut = now - timedelta(days=7)
    shown = [(t, f) for t, f in det if h1["t"][t] + timedelta(hours=1) >= cut]
    print(f"ARRIVAL alerts in the window: {len(shown)}\n")
    for t, fired in shown:
        atr, lv = sets[t]
        c = h1["C"][t]
        sent = h1["t"][t] + timedelta(hours=1)
        kd = A.session_index(d1["t"], h1["t"][t])
        pct_series = [statistics.fmean(trs[k - 14:k]) / d1["C"][k - 1] * 100 for k in range(kd - 250, kd + 1)]
        apct = atr / d1["C"][kd - 1] * 100
        rank = 100 * sum(x < apct for x in pct_series[:-1]) / len(pct_series[:-1])
        terc = "low" if apct < 1.206 else ("middle" if apct <= 1.480 else "high")
        print("=" * 78)
        print(f"ARRIVAL — gold — sent {pt(sent)} (hourly bar {pt(h1['t'][t])} to {pt(sent)}, close ${c:,.2f})")
        others = [(k, l, p) for k, l, p in lv if k in ALL5]
        for kind, lid, p in fired:
            below = p < c if abs(p - c) > 1e-9 else h1["C"][t - 1] > p
            n, held, last = history(s, p, start_of(lid, kind, s, t), t, TOL * atr, below)
            side = [x for x in others if abs(x[2] - p) > TOL * atr]
            if below:
                far = sorted((x for x in side if x[2] > c), key=lambda x: x[2])
                beyond = sorted((x for x in side if x[2] < p), key=lambda x: -x[2])
            else:
                far = sorted((x for x in side if x[2] < c), key=lambda x: -x[2])
                beyond = sorted((x for x in side if x[2] > p), key=lambda x: x[2])
            fmt = lambda x: (f"${x[2]:,.2f} ({NAMES[x[0]]}), ${abs(x[2] - c):,.2f} = {abs(x[2] - c) / atr:.2f} ATR from the close"
                             if x else "none among the qualifying levels")
            print(f"  Price has arrived at ${p:,.2f}, {'an' if NAMES[kind][0] in 'aeiouh' else 'a'} {NAMES[kind]} level ({origin(lid, kind, s, t)}).")
            print(f"    It is {'below' if below else 'above'} the close. Since it formed: {n} earlier visits within ${TOL * atr:,.2f}, "
                  f"{held} held (no hourly close through it), last {pt(last) if last else 'never'}.")
            print(f"    Nearest level the other way: {fmt(far[0] if far else None)}")
            print(f"    Next level beyond this one:  {fmt(beyond[0] if beyond else None)}")
            br = ("A wick beyond a gold daily swing failed 66% of the time and a daily close beyond came back inside 45% "
                  "of the time, 2021-2026 (R45)." if kind == "D1" else "No break base rate has been measured for this kind of level.")
            print(f"    {br}")
        print(f"  Minimum stop at the 14-day average range (${atr:,.2f}): same session ${0.30 * atr:,.2f}; "
              f"10-session hold ${0.60 * atr:,.2f} to ${0.84 * atr:,.2f}. A stop at the median adverse move stops about "
              f"half of the winners by construction; these are floors, not recommendations.")
        print(f"  Next scheduled release: {calendar_lines(sent)}.")
        print(f"  Clock: {window_line(sent)}. Gold's 4-8 AM PT hours usually carry most of the day's range. That says "
              f"movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). "
              f"Volatility clusters; direction does not.")
        print(f"  Volatility: the 14-day average range is {apct:.2f}% of price, above {rank:.0f}% of the last 250 days; "
              f"{terc} third by R50's cut points.")
        print("  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).")
        print("  No direction is recommended.")
    # LEVEL BREAK (spec §17, ruling P1): a close through a price that produced an ARRIVAL, while it still qualifies
    brk = A.level_breaks(s, sets, det, KINDS, margin=A.BREAK_MARGIN)
    shown_b = [(t, b) for t, b in brk if h1["t"][t] + timedelta(hours=1) >= cut]
    print("\n" + "=" * 78)
    print(f"LEVEL BREAK alerts in the window: {len(shown_b)}")
    for t, broke in shown_b:
        atr, lv = sets[t]
        c, sent = h1["C"][t], h1["t"][t] + timedelta(hours=1)
        print("=" * 78)
        print(f"LEVEL BREAK — gold — sent {pt(sent)} (hourly bar {pt(h1['t'][t])} to {pt(sent)}, close ${c:,.2f})")
        for p, side, t0 in broke:
            quals = sorted({NAMES[k] for k, l, q in lv if k in KINDS and round(q, 2) == round(p, 2)})
            at_arrival = sorted({NAMES[k] for k, l, q in dict(det)[t0] if round(q, 2) == round(p, 2)})
            told = ("Price arrived at this level and closed through it in the same hour" if t0 == t else
                    f"The level you were told about at {pt(h1['t'][t0] + timedelta(hours=1))} has given way")
            print(f"  {told}: the hour closed at ${c:,.2f}, ${abs(c - p):,.2f} ({abs(c - p) / atr:.2f} ATR) "
                  f"{'below' if side == 1 else 'above'} ${p:,.2f}.")
            print(f"    Qualified then as: {', '.join(at_arrival)}. Qualifies now as: {', '.join(quals)}.")
            others = [x for x in lv if x[0] in ALL5 and abs(x[2] - p) > TOL * atr]
            nxt = sorted((x for x in others if (x[2] < c if side == 1 else x[2] > c)), key=lambda x: abs(x[2] - c))
            back = sorted((x for x in others if (x[2] > p if side == 1 else x[2] < p)), key=lambda x: abs(x[2] - c))
            fmt = lambda x: (f"${x[2]:,.2f} ({NAMES[x[0]]}), ${abs(x[2] - c):,.2f} = {abs(x[2] - c) / atr:.2f} ATR from the close"
                             if x else "none among the qualifying levels")
            print(f"    Next level beyond: {fmt(nxt[0] if nxt else None)}")
            print(f"    Nearest level the other way (back through ${p:,.2f}): {fmt(back[0] if back else None)}")
            print("    No break base rate has been measured for this kind of level." if not any(k == "D1" for k, l, q in lv if round(q, 2) == round(p, 2))
                  else "    A daily close beyond a gold daily swing came back inside 45% of the time, 2021-2026 (R45).")
        print(f"  Minimum stop at the 14-day average range (${atr:,.2f}): same session ${0.30 * atr:,.2f}; 10-session hold "
              f"${0.60 * atr:,.2f} to ${0.84 * atr:,.2f}. Floors, not recommendations.")
        print(f"  Next scheduled release: {calendar_lines(sent)}. Clock: {window_line(sent)}.")
        print("  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).")
        print("  No direction is recommended.")
    print("\n" + "=" * 78)
    print(f"TRACE of ${WATCH:,.2f} (level ids {sorted(watch_ids)}), last 7 days:")
    for t, lid, ev in log:
        if h1["t"][t] + timedelta(hours=1) >= cut:
            print(f"  {pt(h1['t'][t])} {lid}: {ev}")
    print("Presence of the level in each day's set (first and last hour it was listed):")
    for lid in sorted(watch_ids):
        hrs = [t for t, row in enumerate(sets) if row and any(l == lid for _, l, _ in row[1])]
        if hrs:
            print(f"  {lid}: listed from {pt(h1['t'][hrs[0]])} to {pt(h1['t'][hrs[-1]])} ({len(hrs)} hours)")


if __name__ == "__main__":
    main()
