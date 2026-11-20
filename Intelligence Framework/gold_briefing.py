"""
gold_briefing.py
────────────────
The gold BRIEFING: a daily read at 3:45 AM PT on trading days, before gold's
4-8 AM PT window (docs/specs/configuration_detector_spec.md §14, §14.1,
§14.2). It states where price is, the nearest qualifying levels either side,
the US releases before the next BRIEFING, the clock, volatility, the alert
history, and the two fixed sentences. It recommends nothing.

    python3 gold_briefing.py [--summary-out PATH]

Exit codes (the wrapper reads them):
    0  rendered; the full text is on stdout and the one-line summary in PATH
    3  gold's market is closed: one line on stdout, nothing to send
    2  an input failed: the reason is on stdout, sent as a failed BRIEFING
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import gold_levels as G
from display_time import to_display

PT = ZoneInfo("America/Los_Angeles")
NY = ZoneInfo("America/New_York")
INSTRUMENT = "XAU_USD"
STALE_MIN = 30                       # a price older than this is flagged (§14.2)
TERCILE_CUTS = (1.206, 1.480)        # R50's cut points, % of price (§13.4 item 8)
NOTIFICATION_LOG = "notification_log.csv"
CALENDAR = "calendar.csv"

WINDOW_SENTENCES = (
    "Gold's 4–8 AM PT hours usually carry most of the day's range. That says "
    "movement is likely available, not which way it goes.",
    "A trade on this window was tested and REFUTED (R49). Volatility clusters; "
    "direction does not.")
FIXED_SENTENCES = (
    "This configuration being present is not evidence that it pays. Whether it "
    "does is an open question (Track B).",
    "No direction is recommended.")
HISTORY_NOT_LIVE = ("ARRIVAL and LEVEL BREAK alerts are not live yet, so there is "
                    "no alert history to show.")
HISTORY_NOT_BUILT = ("ALERT HISTORY NOT BUILT: the notification ledger holds ARRIVAL or "
                     "LEVEL BREAK rows, and this BRIEFING cannot list them yet.")


# ── the market gate (§10 gate 2) ─────────────────────────────────────────────

def market_open(now):
    """Gold trades when the FX week is open and outside its daily break,
    5:00-6:00 PM New York."""
    from regime_detection import _market_status
    if not _market_status(_now=now)["open"]:
        return False
    return now.astimezone(NY).hour != 17


def next_briefing(now):
    """The next 3:45 AM PT on a day gold is open."""
    d = now.astimezone(PT).date()
    for k in range(1, 10):
        cand = datetime.combine(d + timedelta(days=k), datetime.min.time(), PT).replace(hour=3, minute=45)
        if market_open(cand.astimezone(timezone.utc)):
            return cand.astimezone(timezone.utc)
    return None


# ── inputs read from files ───────────────────────────────────────────────────

def read_calendar(path=CALENDAR):
    """(rows, problem): rows are (utc time, currency, event, impact)."""
    try:
        with open(path, newline="") as f:
            rows = [(datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc),
                     r["currency"], r["event"], r["impact"]) for r in csv.DictReader(f)]
    except (OSError, KeyError, ValueError) as exc:
        return None, f"the news calendar could not be read ({type(exc).__name__})"
    if not rows:
        return None, "the news calendar is empty"
    return rows, ""


def alert_rows(path=NOTIFICATION_LOG):
    """Notification ledger rows whose category's first word is ARRIVAL or LEVEL."""
    try:
        with open(path, newline="") as f:
            return [r for r in csv.DictReader(f)
                    if (r.get("category") or "").split(" ")[0] in ("ARRIVAL", "LEVEL")]
    except OSError:
        return []


# ── rendering ────────────────────────────────────────────────────────────────

def money(x):
    return f"${x:,.2f}"


def label(kind, lid):
    """The level's type in plain words, as the line's noun."""
    side = "high" if lid.startswith(("PDH", "PWH", "RH")) else "low"
    return {"D1": "a daily swing", "H4": "a 4-hour swing", "RANGE": f"the hourly range's {side}",
            "PDAY": f"the prior session's {side}", "PWEEK": f"the prior week's {side}"}[kind]


def origin(kind, lid, bars):
    d1 = bars["D"]
    if kind == "D1":
        return f"the daily swing of the session that opened {to_display(d1['t'][int(lid[2:])], 'day_date')}"
    if kind == "H4":
        return f"the 4-hour swing of the bar that opened {to_display(bars['H4']['t'][int(lid[2:])], 'day_date')}"
    if kind == "PDAY":
        return f"the session that opened {to_display(d1['t'][int(lid[3:])], 'day_date')}"
    if kind == "PWEEK":
        y, w = (int(x) for x in lid[3:].strip("()").split(","))
        return f"the trading week of {date.fromisocalendar(y, w, 1):%a %d %b}"
    return "the range on the hourly chart now"


def nearest(levels, price):
    above = [x for x in levels if x[2] > price]
    below = [x for x in levels if x[2] < price]
    return (min(above, key=lambda x: x[2]) if above else None,
            max(below, key=lambda x: x[2]) if below else None)


def window_line(now):
    p = now.astimezone(PT)
    start = p.replace(hour=4, minute=0, second=0, microsecond=0)
    end = p.replace(hour=8, minute=0, second=0, microsecond=0)
    if p < start:
        m = int((start - p).total_seconds() // 60)
        return f"before gold's 4–8 AM PT window (it opens in {m // 60}h {m % 60:02d}m)"
    if p < end:
        return f"inside gold's 4–8 AM PT window ({int((end - p).total_seconds() // 60)} minutes left)"
    return "after gold's 4–8 AM PT window"


def volatility(d1, now):
    kd = G.session_index(d1["t"], now)
    trs = [None] + [max(d1["H"][i] - d1["L"][i], abs(d1["H"][i] - d1["C"][i - 1]), abs(d1["L"][i] - d1["C"][i - 1]))
                    for i in range(1, len(d1["C"]))]
    if kd - 250 < 15:
        return "Volatility: not enough daily history to rank it (needs 265 completed sessions)."
    pct = [statistics.fmean(trs[k - 14:k]) / d1["C"][k - 1] * 100 for k in range(kd - 250, kd + 1)]
    now_pct, past = pct[-1], pct[:-1]
    rank = 100 * sum(x < now_pct for x in past) / len(past)
    third = "low" if now_pct < TERCILE_CUTS[0] else ("middle" if now_pct <= TERCILE_CUTS[1] else "high")
    return (f"Volatility: the 14-day average daily range is {now_pct:.2f}% of price, above {rank:.0f}% of "
            f"the last 250 days; the {third} third by R50's cut points ({TERCILE_CUTS[0]:.3f}% and {TERCILE_CUTS[1]:.3f}%).")


def releases(now, until, cal):
    rows, problem = cal
    if rows is None:
        return [f"US releases: unknown, because {problem}."], None, None
    us = sorted((t, ev) for t, cur, ev, imp in rows if cur == "USD" and imp == "High" and now <= t < until)
    head = f"High-impact US releases before the next briefing ({to_display(until, 'day_date')}):"
    lines = [head]
    for t, ev in us:
        mark = ""
        p = t.astimezone(PT)
        if 4 <= p.hour < 8:
            mark = " (inside gold's 4–8 AM PT window)"
        lines.append(f"  {to_display(t, 'day_date')}  {ev}{mark}")
    if not us:
        lines.append("  none in the stored calendar.")
    last = max(t for t, *_ in rows)
    short = last < until
    if short:
        lines.append(f"  The stored calendar's last entry is {to_display(last, 'day_date')}; "
                     f"anything after it is not known yet.")
    return lines, us, (last if short else None)


def render(now, bars, price, price_time, cal, history_rows, levels=None):
    """(full text, one-line summary). `levels` defaults to gold_levels.levels_now."""
    row = levels if levels is not None else G.levels_now(bars, now)
    if row is None:
        raise ValueError("not enough daily history for the levels")
    atr, lv = row
    lines = [f"GOLD BRIEFING — {to_display(now)}", ""]
    lines.append(f"Price: {money(price)}, the close of the 15-minute bar ending {to_display(price_time, 'day_date')}.")
    age = int((now - price_time).total_seconds() // 60)
    if age > STALE_MIN:
        lines.append(f"That price is {age // 60}h {age % 60:02d}m old: gold may not be trading. "
                     f"Treat every distance below as of that time.")
    lines.append(f"ATR here means the 14-day average daily range: {money(atr)}.")
    lines.append("")
    up, down = nearest(lv, price)
    lines.append("Nearest qualifying levels:")
    for side, x in (("Above", up), ("Below", down)):
        if x is None:
            lines.append(f"  {side}: none among the qualifying levels.")
            continue
        kind, lid, p = x
        lines.append(f"  {side}: {money(p)}, {label(kind, lid)} ({origin(kind, lid, bars)}), "
                     f"{money(abs(p - price))} = {abs(p - price) / atr:.2f} ATR away.")
    lines.append("")
    until = next_briefing(now)
    rel_lines, us, ends = releases(now, until, cal)
    lines += rel_lines
    lines.append("")
    lines.append(f"Clock: {window_line(now)}.")
    lines += list(WINDOW_SENTENCES)
    lines.append("")
    lines.append(volatility(bars["D"], now))
    lines.append("")
    lines.append("Alert history, last 7 days: " + (HISTORY_NOT_BUILT if history_rows else HISTORY_NOT_LIVE))
    lines.append("")
    lines += list(FIXED_SENTENCES)

    def short(x, sign):
        return (f"{money(x[2])} {sign}{money(abs(x[2] - price))[1:]} ({abs(x[2] - price) / atr:.2f} ATR)"
                if x else "none")
    rel = ("US releases unknown" if us is None else
           f"{len(us)} US release{'s' if len(us) != 1 else ''} before the next briefing"
           + (f", first {to_display(us[0][0], 'time')}" if us else "")
           + (f"; the calendar ends {to_display(ends, 'day_time')}, later ones not known" if ends else ""))
    summary = (f"Gold {money(price)} at {to_display(price_time, 'time')}"
               + (" (stale)" if age > STALE_MIN else "")
               + f" · above {short(up, '+$')} · below {short(down, '-$')} · {rel}")
    return "\n".join(lines) + "\n", summary


# ── live entry point ─────────────────────────────────────────────────────────

def main(argv=None, now=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-out")
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    if not market_open(now):
        print(f"gold market closed at {to_display(now)}: no BRIEFING")
        return 3
    import oanda_feed as F
    got = {}
    for key, fn, count in (("D", F.get_daily_bars, 520), ("H4", F.get_h4_bars, 500),
                           ("H1", F.get_hourly_bars, 1000), ("M15", F.get_m15_bars, 4)):
        df = fn(INSTRUMENT, count=count)
        if df is None or len(df) == 0:
            print(f"BRIEFING FAILED: no {key} bars for gold ({F.last_error() or 'no reason given'})")
            return 2
        got[key] = G.series(df)
    m15 = got.pop("M15")
    price, price_time = m15["C"][-1], m15["t"][-1] + timedelta(minutes=15)
    try:
        text, summary = render(now, got, price, price_time, read_calendar(), alert_rows())
    except Exception as exc:                                   # a crash is a failure, never a quiet morning
        print(f"BRIEFING FAILED: {type(exc).__name__}: {exc}")
        return 2
    sys.stdout.write(text)
    if args.summary_out:
        with open(args.summary_out, "w") as f:
            f.write(summary + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
