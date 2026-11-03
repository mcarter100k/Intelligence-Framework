"""missed_moves.py — what standing aside cost: every sizable move the framework
sat out, lined up with what it said at the time. REPORT-ONLY.

Never imported by the live path. Writes no ledger: it reads the ledgers and
the day logs, and writes one markdown report (to --out, default stdout).
Descriptive only: a hindsight move size is NOT an achievable profit.

Parameters, fixed before the first real run (2026-11-03):
  * Bars: OANDA mid H4 candles (complete only) and D candles, per pair.
  * Daily ATR: Wilder ATR(14) on D candles, regime_detection.compute_atr_series
    (the brief's own ATR). The ATR in force at time t is the one computed at
    the close of the last D candle that closed at or before t (close = open +
    24 h). No look-ahead into the bar being measured.
  * Zig-zag on H4 CLOSES (not highs/lows), reversal threshold REV = 1.0 x the
    daily ATR in force at each bar: a swing high is confirmed when a close
    falls REV x ATR below the running highest close, and vice versa. The
    leg after the last confirmed swing runs to the latest extreme close and
    is marked "still running" (it has not reversed yet).
  * A move is a zig-zag leg of at least K = 2.0 x the daily ATR in force at
    the leg's start bar. Size in pips is |close(end) - close(start)|.
  * Move window: from the close of the start bar to the close of the end
    bar; the move's bars are start+1 .. end.
  * Runs. Evidence of what the framework said, per pair:
      - regime_classification_log.csv rows (primary record of a run);
      - brief day logs logs/brief_*.log: each "===== <date> <time> <zone> ====="
        block, split per pair at "GBP/xxx  |" (the daily_digest.py rule);
        DECISION / REASON lines, the market-closed banner, and
        "Framework error" pages;
      - trade_signal_log.csv rows (issued trade signals).
    A brief block and a regime row (or signal) for the same pair within 10
    minutes are the same run. Runs of one pair within 10 minutes of each
    other are collapsed into one (the later one stands).
  * Decision of record for a run: the brief's DECISION line if the brief
    exists (it is what the trader read); else a matched trade signal's
    direction; else the regime row: stand_down True = STAND ASIDE, stand_down
    False = NOT RECORDED (before the 2026-09-30 logic, stand_down False often
    rendered as STAND ASIDE, so it is never read as a trade).
  * Run kinds: a READ (LONG / SHORT / STAND ASIDE / NOT RECORDED); an ERROR
    (the brief rendered "Framework error"): no read; CLOSED (the brief carried
    the market-closed banner): no live read.
  * Bar state: at each H4 bar's close, the latest run at or before it, if
    that run is at most 12 hours old. No run within 12 hours = framework not
    running. An ERROR or CLOSED run in force = framework not running for that
    bar (shown separately in the coverage section).
  * Verdict per move, from the READ runs that governed any of its bars or ran
    inside its window: any LONG/SHORT = traded (with / against / both ways);
    else any STAND ASIDE = sat out; else only NOT RECORDED = not recorded;
    no READ at all = framework not running. "Sat out entirely" = sat out,
    framework running for every bar, no NOT RECORDED run.
  * Stand-aside reason: from the brief's REASON text (plain-English
    categories); where no brief exists, from the regime row (daily regime not
    trending / exhaustion subtype / otherwise the 4-hour chart).
  * Shadow fires: shadow_signal_log.csv rows for the pair with a timestamp in
    the move window; with = the move's direction.
  * Exclusions: exclusions.excluder() on every ledger read (regime log, trade
    signals, shadow log). A brief block within 10 minutes of an excluded
    regime row for the same pair is dropped too (it is the same run).
  * Scope: a move is listed only if it starts at or after the pair's first
    run (any source). Moves before that are out of scope and not listed.

usage:
  python3 scripts/reality_run.py --code <worktree> script \\
      <worktree>/studies/missed_moves.py --brief-logs <project>/logs \\
      --out missed_moves_report.md
  (ledgers are read by relative path: reality_run copies them into its temp
  working directory.)
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

K_DEFAULT = 2.0          # move size, in daily ATRs
REV_DEFAULT = 1.0        # zig-zag reversal threshold, in daily ATRs
ATR_PERIOD = 14
STALE_HOURS = 12.0       # a run speaks for at most this long
MATCH_MINUTES = 10.0     # brief block <-> regime row <-> signal
H4 = timedelta(hours=4)
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
DECIMALS = {"GBP_AUD": 5, "GBP_JPY": 3}
PAIRS = ("GBP_AUD", "GBP_JPY")

# Header zone abbreviations seen in the day logs (machine-local `date`).
ZONE_OFFSETS = {"UTC": 0, "GMT": 0, "BST": 1, "EDT": -4, "EST": -5, "CDT": -5,
                "CST": -6, "MDT": -6, "MST": -7, "PDT": -7, "PST": -8}

STAND, LONG, SHORT, UNREC = "STAND ASIDE", "LONG", "SHORT", "NOT RECORDED"
READ, ERROR, CLOSED = "READ", "ERROR", "CLOSED"

# Plain-English stand-aside reason categories (trader-facing labels).
R_NEWS = "a big news event was due"
R_DAILY = "daily chart gave no clear trend"
R_H4 = "4-hour chart did not line up"
R_STRETCHED = "move judged too stretched to chase"
R_WEEKLY = "weekly trend blocked that direction"
R_WEAK = "setup too weak to trade"
R_OTHER = "other reason"

VERDICT_LABEL = {
    "NOT_RUNNING": "Framework not running",
    "SAT_OUT": "Sat out",
    "WITH": "Traded with the move",
    "AGAINST": "Traded against the move",
    "BOTH": "Traded both ways",
    "UNRECORDED": "Decision not recorded",
}


def _utc(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")) \
            .astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


# ── 1. Moves ──────────────────────────────────────────────────────────────────

def daily_atr_points(d1):
    """[(close_time, atr)] from D bars [(open_time, high, low, close)]."""
    from regime_detection import compute_atr_series
    if len(d1) < ATR_PERIOD + 1:
        return []
    series = compute_atr_series([b[1] for b in d1], [b[2] for b in d1],
                                [b[3] for b in d1], ATR_PERIOD)
    return [(d1[ATR_PERIOD + k][0] + timedelta(hours=24), a)
            for k, a in enumerate(series)]


def atr_at(points, t):
    """The daily ATR in force at t: computed at the last D close <= t."""
    best = None
    for close_t, a in points:
        if close_t <= t:
            best = a
        else:
            break
    return best


def zigzag(closes, thresholds):
    """Swing points on closes. thresholds[i] is the reversal distance at bar
    i. Returns (pivots, last): pivots = confirmed swing indices in order;
    last = index of the latest extreme after the final confirmed swing (the
    still-running leg's end), or None if no swing was ever confirmed."""
    n = len(closes)
    if n == 0:
        return [], None
    pivots, direction = [], 0
    hi = lo = ext = 0
    for i in range(1, n):
        c, thr = closes[i], thresholds[i]
        if direction == 0:
            if c > closes[hi]:
                hi = i
            if c < closes[lo]:
                lo = i
            if c - closes[lo] >= thr:
                pivots.append(lo); direction, ext = 1, i
            elif closes[hi] - c >= thr:
                pivots.append(hi); direction, ext = -1, i
        elif direction == 1:
            if c > closes[ext]:
                ext = i
            elif closes[ext] - c >= thr:
                pivots.append(ext); direction, ext = -1, i
        else:
            if c < closes[ext]:
                ext = i
            elif c - closes[ext] >= thr:
                pivots.append(ext); direction, ext = 1, i
    return pivots, (ext if direction != 0 else None)


def find_moves(pair, h4, d1, k=K_DEFAULT, rev=REV_DEFAULT):
    """Moves of >= k daily ATRs. h4 / d1: [(open_time, high, low, close)]."""
    pts = daily_atr_points(d1)
    bars = [b for b in h4 if atr_at(pts, b[0] + H4) is not None]
    if len(bars) < 2:
        return [], bars
    atrs = [atr_at(pts, b[0] + H4) for b in bars]
    closes = [b[3] for b in bars]
    pivots, last = zigzag(closes, [rev * a for a in atrs])
    legs = [(a, b, False) for a, b in zip(pivots, pivots[1:])]
    if pivots and last is not None and last != pivots[-1]:
        legs.append((pivots[-1], last, True))
    moves = []
    for s, e, running in legs:
        size = abs(closes[e] - closes[s])
        atr = atrs[s]
        if atr and size >= k * atr:
            moves.append({
                "pair": pair, "start_i": s, "end_i": e,
                "start": bars[s][0] + H4, "end": bars[e][0] + H4,
                "from_px": closes[s], "to_px": closes[e],
                "dir": "UP" if closes[e] > closes[s] else "DOWN",
                "pips": size / PIP[pair], "atr_pips": atr / PIP[pair],
                "mult": size / atr, "bars": e - s, "running": running,
            })
    return moves, bars


# ── 2. What the framework said ────────────────────────────────────────────────

_HDR = re.compile(r"(?m)^=====\s*(\d{4}-\d{2}-\d{2}) ([0-9:]{8}) ([A-Z]{2,5})\s*=====\s*$")
_PAIR_HDR = re.compile(r"(GBP/[A-Z]{3})\s+\|")
_DECISION = re.compile(r"^\s*DECISION\s+(LONG|SHORT|STAND ASIDE)\b", re.M)
_REASON = re.compile(r"^\s*REASON\s+(.*(?:\n[ \t]{6,}\S.*)*)", re.M)
_CLOSED_BANNER = re.compile(r"Market closed — analysis based on last close")


def parse_brief_logs(logs_dir):
    """[{time, pair, decision, reason, kind, file}] per pair block, plus the
    count of blocks whose header zone could not be read."""
    out, unparsed = [], 0
    for path in sorted(glob.glob(os.path.join(logs_dir, "brief_*.log"))):
        try:
            text = open(path, errors="replace").read()
        except OSError:
            continue
        hdrs = list(_HDR.finditer(text))
        starts = [m.start() for m in hdrs] + [len(text)]
        for i, m in enumerate(hdrs):
            off = ZONE_OFFSETS.get(m.group(3))
            if off is None:
                unparsed += 1
                continue
            t = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S") \
                .replace(tzinfo=timezone(timedelta(hours=off))).astimezone(timezone.utc)
            block = text[starts[i]:starts[i + 1]]
            secs = [(p.group(1), p.start()) for p in _PAIR_HDR.finditer(block)]
            for j, (name, s) in enumerate(secs):
                sec = block[s:secs[j + 1][1] if j + 1 < len(secs) else len(block)]
                d = _DECISION.search(sec)
                r = _REASON.search(sec)
                reason = " ".join(x.strip() for x in r.group(1).split("\n")) if r else ""
                kind = READ
                if reason.startswith("Framework error"):
                    kind = ERROR
                elif _CLOSED_BANNER.search(sec):
                    kind = CLOSED
                out.append({"time": t, "pair": name.replace("/", "_"),
                            "decision": d.group(1) if d else None,
                            "reason": reason, "kind": kind,
                            "file": os.path.basename(path)})
    return out, unparsed


def classify_reason(text):
    """Plain-English category for a brief's stand-aside REASON text."""
    t = (text or "").lower()
    if "major economic event" in t:
        return R_NEWS
    if "exhaustion move" in t or "violent one-way move" in t:
        return R_STRETCHED
    if "blocked" in t and ("weekly" in t or "20-week" in t):
        return R_WEEKLY
    if "grades c" in t:
        return R_WEAK
    if ("transition zone" in t or "gives no trend" in t
            or "has not confirmed" in t):
        return R_DAILY
    if ("trend intact" in t or "has not resolved" in t
            or "range breaking" in t or "timeframe conflict" in t
            or "4-hour chart" in t):
        return R_H4
    return R_OTHER


def reason_from_regime(row):
    """Fallback category when no brief text exists for the run."""
    sub = (row.get("subtype") or "")
    if "EXHAUSTION" in sub:
        return R_STRETCHED
    if row.get("regime_d1") in ("VOLATILE", "RANGING") or "d1=" in sub:
        return R_DAILY
    return R_H4


def _read_csv(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _excluder(ledger):
    try:
        import exclusions
        return exclusions.excluder(ledger)
    except Exception as exc:          # fail open, loudly (exclusions.py rule)
        print(f"exclusion registry unavailable ({exc}); nothing excluded",
              file=sys.stderr)
        return lambda row: False


def build_runs(pair, regime_rows, briefs, signals):
    """Merge the three sources into one time-ordered run list for a pair.
    Returns (runs, stats). Excluded rows must already be marked with
    row["_excluded"] = True (they are dropped here, with any brief block or
    signal that is the same run)."""
    win = timedelta(minutes=MATCH_MINUTES)
    stats = Counter()
    rrows = [dict(r, _t=_utc(r.get("timestamp", ""))) for r in regime_rows
             if r.get("instrument") == pair]
    rrows = [r for r in rrows if r["_t"] is not None]
    excluded_t = [r["_t"] for r in rrows if r.get("_excluded")]
    stats["regime rows excluded"] = len(excluded_t)
    rrows = [r for r in rrows if not r.get("_excluded")]
    bl = [b for b in briefs if b["pair"] == pair]
    sg = [dict(s, _t=_utc(s.get("timestamp", ""))) for s in signals
          if s.get("instrument") == pair and not s.get("_excluded")]
    sg = [s for s in sg if s["_t"] is not None]

    def near(t, items, key):
        best = None
        for it in items:
            d = abs(it[key] - t)
            if d <= win and (best is None or d < abs(best[key] - t)):
                best = it
        return best

    runs, used_b, used_s = [], set(), set()
    for r in rrows:
        b = near(r["_t"], bl, "time")
        s = near(r["_t"], sg, "_t")
        if b is not None:
            used_b.add(id(b))
        if s is not None:
            used_s.add(id(s))
        run = {"time": r["_t"], "kind": READ, "source": "regime log"}
        if b is not None and b["kind"] != READ:
            run.update(kind=b["kind"], decision=None, reason=None)
        elif b is not None and b["decision"]:
            run["decision"] = b["decision"]
            run["reason"] = classify_reason(b["reason"]) if b["decision"] == STAND else None
            run["source"] = "regime log + brief"
            sd = r.get("stand_down") == "True"
            if sd != (b["decision"] == STAND):
                stats["regime stand_down disagrees with brief"] += 1
            else:
                stats["regime stand_down agrees with brief"] += 1
        elif s is not None:
            run["decision"] = s.get("direction") if s.get("direction") in (LONG, SHORT) else UNREC
            run["reason"] = None
            run["source"] = "regime log + trade signal"
        elif r.get("stand_down") == "True":
            run["decision"], run["reason"] = STAND, reason_from_regime(r)
        else:
            run["decision"], run["reason"] = UNREC, None
        if b is None:
            stats["regime rows with no brief block"] += 1
        runs.append(run)
    for b in bl:
        if id(b) in used_b:
            continue
        if any(abs(b["time"] - t) <= win for t in excluded_t):
            stats["brief blocks dropped with an excluded row"] += 1
            continue
        stats["brief blocks with no regime row"] += 1
        run = {"time": b["time"], "kind": b["kind"], "source": "brief log only",
               "decision": None, "reason": None}
        if b["kind"] == READ:
            s = near(b["time"], sg, "_t")
            if b["decision"]:
                run["decision"] = b["decision"]
                if b["decision"] == STAND:
                    run["reason"] = classify_reason(b["reason"])
            elif s is not None:
                run["decision"] = s.get("direction")
            else:
                run["decision"] = UNREC
            if s is not None:
                used_s.add(id(s))
        runs.append(run)
    for s in sg:
        if id(s) not in used_s and s.get("direction") in (LONG, SHORT):
            stats["trade signals with no run"] += 1
            runs.append({"time": s["_t"], "kind": READ, "source": "trade signal only",
                         "decision": s["direction"], "reason": None})
    runs.sort(key=lambda x: x["time"])
    collapsed = []
    for run in runs:
        if collapsed and run["time"] - collapsed[-1]["time"] <= win:
            collapsed[-1] = run
            stats["runs collapsed (re-runs within 10 minutes)"] += 1
        else:
            collapsed.append(run)
    return collapsed, stats


def bar_states(bars, runs, stale_hours=STALE_HOURS):
    """Per bar: index of the run in force at its close, or None."""
    out, j = [], -1
    stale = timedelta(hours=stale_hours)
    for b in bars:
        close = b[0] + H4
        while j + 1 < len(runs) and runs[j + 1]["time"] <= close:
            j += 1
        if j >= 0 and close - runs[j]["time"] <= stale:
            out.append(j)
        else:
            out.append(None)
    return out


def bar_label(runs, idx):
    if idx is None:
        return "not running"
    r = runs[idx]
    if r["kind"] == ERROR:
        return "framework error"
    if r["kind"] == CLOSED:
        return "market closed"
    return r["decision"]


def align(move, states, runs, shadows):
    """What the framework said during one move."""
    idxs = states[move["start_i"] + 1: move["end_i"] + 1]
    labels = [bar_label(runs, i) for i in idxs]
    nbars = len(labels)
    running = sum(1 for x in labels if x in (STAND, LONG, SHORT, UNREC))
    governing = {i for i in idxs if i is not None}
    governing |= {i for i, r in enumerate(runs)
                  if move["start"] <= r["time"] <= move["end"]}
    reads = [runs[i] for i in sorted(governing) if runs[i]["kind"] == READ]
    dec = Counter(r["decision"] for r in reads)
    want = LONG if move["dir"] == "UP" else SHORT
    against = SHORT if want == LONG else LONG
    if not reads:
        verdict = "NOT_RUNNING"
    elif dec[LONG] or dec[SHORT]:
        verdict = ("BOTH" if dec[want] and dec[against]
                   else "WITH" if dec[want] else "AGAINST")
    elif dec[STAND]:
        verdict = "SAT_OUT"
    else:
        verdict = "UNRECORDED"
    reasons = Counter(r["reason"] for r in reads if r["decision"] == STAND and r["reason"])
    order = {r["reason"]: k for k, r in reversed(list(enumerate(reads)))}
    top = sorted(reasons, key=lambda c: (-reasons[c], order.get(c, 0)))
    fires = [s for s in shadows if move["start"] <= s["_t"] <= move["end"]]
    return {
        "verdict": verdict, "bars": nbars, "running_bars": running,
        "label_counts": Counter(labels), "runs": len(reads), "dec": dec,
        "reasons": reasons, "top_reason": top[0] if top else None,
        "entire": (verdict == "SAT_OUT" and running == nbars and not dec[UNREC]),
        "fires": fires,
        "fires_with": sum(1 for s in fires if s.get("direction") == want),
        "fires_against": sum(1 for s in fires if s.get("direction") == against),
    }


# ── 3. Report ─────────────────────────────────────────────────────────────────

def _when(dt):
    try:
        from display_time import to_display
        s = to_display(dt)
        if s:
            return s
    except Exception:
        pass
    return dt.strftime("%a %d %b %Y %H:%M UTC")


def _pct(a, b):
    return f"{100.0 * a / b:.0f}%" if b else "n/a"


def _said(a):
    if a["verdict"] == "NOT_RUNNING":
        return "Nothing: framework not running for the whole move"
    d = a["dec"]
    parts = []
    for key, word in ((STAND, "stood aside"), (LONG, "said buy"),
                      (SHORT, "said sell"), (UNREC, "decision not recorded")):
        if d[key]:
            parts.append(f"{word} {d[key]}")
    s = f"{VERDICT_LABEL[a['verdict']]}: {', '.join(parts)} of {a['runs']} runs"
    off = a["bars"] - a["running_bars"]
    if off:
        s += f"; framework not running for {_pct(off, a['bars'])} of the move"
    return s


def _fires(a):
    if not a["fires"]:
        return "none"
    c = Counter((s.get("candidate_id"), s.get("direction")) for s in a["fires"])
    items = ", ".join(f"{cid} {'buy' if d == LONG else 'sell'} x{n}"
                      for (cid, d), n in sorted(c.items()))
    return (f"{len(a['fires'])} ({a['fires_with']} with the move, "
            f"{a['fires_against']} against): {items}")


def _pair_name(p):
    return p.replace("_", "/")


def render(results, coverage, params, notes):
    """results: [(move, align)] in scope; coverage: {pair: dict}."""
    k, rev = params["k"], params["rev"]
    L = []
    L.append("# Missed moves: what standing aside cost")
    L.append("")
    L.append(f"Every move of at least {k:g} times a normal day's range, measured "
             "from one turning point to the next on 4-hour closing prices, lined "
             "up with what the framework said while it happened.")
    L.append("")
    L.append("**Hindsight warning.** A move's size is measured from the exact "
             "turn to the exact turn, which nobody can know at the time. It is "
             "NOT a profit that was available. This report is descriptive: it "
             "shows which kinds of move the framework stood aside from, not "
             "what trading them would have earned.")
    L.append("")
    n = len(results)
    v = Counter(a["verdict"] for _, a in results)
    sat = [(m, a) for m, a in results if a["verdict"] == "SAT_OUT"]
    entire = sum(1 for _, a in sat if a["entire"])
    reasons = Counter()
    for _, a in sat:
        if a["top_reason"]:
            reasons[a["top_reason"]] += 1
    pips = Counter()
    for m, _ in sat:
        pips[m["pair"]] += m["pips"]
    L.append("## Summary")
    L.append("")
    per_pair = ", ".join(f"{_pair_name(p)} {sum(1 for m, _ in results if m['pair'] == p)}"
                         for p in params["pairs"])
    L.append(f"- Moves found: {n} ({per_pair}).")
    L.append(f"- Sat out (framework running and standing aside whenever it ran): "
             f"{len(sat)}. Of these, sat out entirely (running for the whole move): "
             f"{entire}; partly while the framework was not running: {len(sat) - entire}.")
    L.append(f"- Traded with the move: {v['WITH']}. Traded against it: {v['AGAINST']}. "
             f"Traded both ways: {v['BOTH']}.")
    L.append(f"- Framework not running for the whole move (no read, so NOT "
             f"\"stood aside\"): {v['NOT_RUNNING']}. Decision not recorded: "
             f"{v['UNRECORDED']}.")
    if reasons:
        L.append("- Most common main reason when it sat out: "
                 + "; ".join(f"{r} ({c} move{'' if c == 1 else 's'})" for r, c in reasons.most_common()) + ".")
    else:
        L.append("- Most common main reason when it sat out: none (no move was sat out).")
    tot = "; ".join(f"{_pair_name(p)} {pips[p]:.0f} pips" for p in params["pairs"])
    L.append(f"- Total size of the moves sat out: {tot}. Pips are not comparable "
             "across the two pairs, and none of this is an achievable profit.")
    if n and n < 20:
        L.append(f"- Sample: {n} moves. INSUFFICIENT (under 20) for any judgement "
                 "about what the framework is blind to; read it as a list of cases.")
    L.append("")
    L.append("## The moves")
    L.append("")
    L.append("| # | Pair | Direction | From → to | Started | Ended | Size | Versus a normal day | Length | What the framework said | Main reason it stood aside | Shadow ideas that fired |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, (m, a) in enumerate(results, 1):
        dp = DECIMALS[m["pair"]]
        ended = _when(m["end"]) + (" (still running)" if m["running"] else "")
        L.append(
            f"| {i} | {_pair_name(m['pair'])} | {'up' if m['dir'] == 'UP' else 'down'} | "
            f"{m['from_px']:.{dp}f} → {m['to_px']:.{dp}f} | {_when(m['start'])} | {ended} | "
            f"{m['pips']:.0f} pips | {m['mult']:.1f} times | "
            f"{m['bars']} four-hour bars ({m['bars'] * 4 / 24:.1f} days) | {_said(a)} | "
            f"{a['top_reason'] or '—'} | {_fires(a)} |")
    if not results:
        L.append("| — | — | — | — | — | — | — | — | — | No move in scope | — | — |")
    L.append("")
    L.append("## When the framework was actually running")
    L.append("")
    L.append("A gap below means no read at all. It is never counted as standing aside.")
    L.append("")
    for p in params["pairs"]:
        c = coverage.get(p)
        if not c:
            L.append(f"- {_pair_name(p)}: no runs on record, so every move is out of scope.")
            continue
        L.append(f"- {_pair_name(p)}: first run {_when(c['first'])}, last run "
                 f"{_when(c['last'])}. Runs: {c['reads']} with a read, "
                 f"{c['errors']} error pages, {c['closed']} market-closed reads. "
                 f"Of {c['bars']} four-hour bars in that window, the framework had a "
                 f"read in force for {c['running']} ({_pct(c['running'], c['bars'])}); "
                 f"not running {c['off']}, error page {c['err_bars']}, "
                 f"market-closed read {c['closed_bars']}.")
        for s, e, nb in c["gaps"]:
            L.append(f"  - Not running: {_when(s)} to {_when(e)} ({nb} four-hour bars)")
        if c.get("gaps_more"):
            L.append(f"  - and {c['gaps_more']} shorter gaps")
        if c.get("out_of_scope"):
            L.append(f"  - {c['out_of_scope']} moves started before the first run: "
                     "out of scope, not listed.")
    L.append("")
    L.append("<!-- trader-facing section ends -->")
    L.append("")
    L.append("## Methods (technical)")
    L.append("")
    L.append(f"- Zig-zag on H4 mid closes, reversal threshold {rev:g} x daily ATR(14) "
             f"(Wilder, regime_detection.compute_atr_series), ATR in force = last D "
             f"candle closed at or before the H4 bar's close. Moves = legs >= {k:g} x "
             f"the ATR in force at the leg's start bar. The leg after the last "
             f"confirmed swing is reported as still running.")
    L.append(f"- Runs: regime_classification_log.csv rows, brief day-log blocks, "
             f"trade_signal_log.csv rows; matched within {MATCH_MINUTES:g} min; "
             f"re-runs within {MATCH_MINUTES:g} min collapsed. A run is in force for "
             f"at most {STALE_HOURS:g} h. Decision of record: brief DECISION > trade "
             f"signal > regime stand_down (True = stand aside; False = not recorded).")
    L.append("- Exclusions: exclusions.excluder() applied to the regime log, the "
             "trade signal log and the shadow log; brief blocks matching an excluded "
             "regime row are dropped.")
    for line in notes:
        L.append(f"- {line}")
    L.append("")
    return "\n".join(L) + "\n"


def coverage_for(pair, bars, runs, states, max_gaps=12):
    if not runs:
        return None
    first, last = runs[0]["time"], runs[-1]["time"]
    window = [(b, s) for b, s in zip(bars, states)
              if first <= b[0] + H4 <= last + timedelta(hours=STALE_HOURS)]
    labels = [bar_label(runs, s) for _, s in window]
    gaps, cur = [], None
    for (b, _), lab in zip(window, labels):
        if lab == "not running":
            if cur is None:
                cur = [b[0], b[0] + H4, 0]
            cur[1] = b[0] + H4
            cur[2] += 1
        elif cur is not None:
            gaps.append(tuple(cur)); cur = None
    if cur is not None:
        gaps.append(tuple(cur))
    long_gaps = [g for g in gaps if g[2] >= 3]
    return {
        "first": first, "last": last,
        "reads": sum(1 for r in runs if r["kind"] == READ),
        "errors": sum(1 for r in runs if r["kind"] == ERROR),
        "closed": sum(1 for r in runs if r["kind"] == CLOSED),
        "bars": len(window),
        "running": sum(1 for x in labels if x in (STAND, LONG, SHORT, UNREC)),
        "off": labels.count("not running"),
        "err_bars": labels.count("framework error"),
        "closed_bars": labels.count("market closed"),
        "gaps": sorted(long_gaps, key=lambda g: -g[2])[:max_gaps],
        "gaps_more": max(0, len(long_gaps) - max_gaps) + (len(gaps) - len(long_gaps)),
    }


def analyse(pairs, bars_by_pair, regime_rows, briefs, signals, shadows,
            k=K_DEFAULT, rev=REV_DEFAULT, date_from=None, date_to=None):
    """Pure core: everything after the data is loaded. Rows carry
    row["_excluded"] already. Returns (results, coverage, stats)."""
    results, coverage, all_stats = [], {}, {}
    for pair in pairs:
        h4, d1 = bars_by_pair[pair]
        runs, stats = build_runs(pair, regime_rows, briefs, signals)
        moves, bars = find_moves(pair, h4, d1, k, rev)
        states = bar_states(bars, runs)
        sh = [dict(s, _t=_utc(s.get("timestamp", ""))) for s in shadows
              if s.get("instrument") == pair and not s.get("_excluded")]
        sh = [s for s in sh if s["_t"] is not None]
        cov = coverage_for(pair, bars, runs, states)
        out_scope = 0
        for m in moves:
            if not runs or m["start"] < runs[0]["time"]:
                out_scope += 1
                continue
            if date_from and m["start"] < date_from:
                continue
            if date_to and m["start"] > date_to:
                continue
            results.append((m, align(m, states, runs, sh)))
        if cov:
            cov["out_of_scope"] = out_scope
            coverage[pair] = cov
        all_stats[pair] = stats
    results.sort(key=lambda x: x[0]["start"])
    return results, coverage, all_stats


def _mark_excluded(rows, ledger):
    if rows is None:
        return []
    ex = _excluder(ledger)
    return [dict(r, _excluded=ex(r)) for r in rows]


def _fetch(pair, start):
    import oanda_feed
    days = (datetime.now(timezone.utc) - start).days + 1
    h4 = oanda_feed.get_h4_bars(pair, count=min(5000, days * 6 + 300), timeout=20)
    d1 = oanda_feed.get_daily_bars(pair, count=min(5000, days + 60), timeout=20)
    if h4 is None or d1 is None:
        raise SystemExit(f"OANDA fetch failed for {pair}: {oanda_feed.last_error()}")
    conv = lambda df: [(ix.to_pydatetime(), float(r.High), float(r.Low), float(r.Close))
                       for ix, r in df.iterrows()]
    return conv(h4), conv(d1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Missed-moves report (read-only).")
    ap.add_argument("--k", type=float, default=K_DEFAULT)
    ap.add_argument("--reversal", type=float, default=REV_DEFAULT)
    ap.add_argument("--pairs", nargs="+", default=list(PAIRS))
    ap.add_argument("--regime-log", default="regime_classification_log.csv")
    ap.add_argument("--trade-log", default="trade_signal_log.csv")
    ap.add_argument("--shadow-log", default="shadow_signal_log.csv")
    ap.add_argument("--brief-logs", default="logs")
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--out", help="markdown report path (default: stdout)")
    a = ap.parse_args(argv)
    if a.out and not a.out.endswith(".md"):
        ap.error("--out must be a .md file (this tool never writes a ledger)")

    regime = _read_csv(a.regime_log)
    if regime is None:
        raise SystemExit(f"regime log not found: {a.regime_log}")
    regime = _mark_excluded(regime, "regime_classification_log.csv")
    signals = _mark_excluded(_read_csv(a.trade_log), "trade_signal_log.csv")
    shadows = _mark_excluded(_read_csv(a.shadow_log), "shadow_signal_log.csv")
    briefs, unparsed = parse_brief_logs(a.brief_logs)
    notes = [f"Sources: {a.regime_log} ({len(regime)} rows, "
             f"{sum(r['_excluded'] for r in regime)} excluded), {a.trade_log} "
             f"({len(signals)} rows, {sum(r['_excluded'] for r in signals)} excluded), "
             f"{a.shadow_log} ({len(shadows)} rows, "
             f"{sum(r['_excluded'] for r in shadows)} excluded), "
             f"{len(briefs)} pair blocks from {a.brief_logs}"
             f" ({unparsed} blocks skipped: unknown header zone)."]
    times = [t for t in (_utc(r.get("timestamp", "")) for r in regime) if t]
    times += [b["time"] for b in briefs]
    if not times:
        raise SystemExit("no runs on record")
    start = min(times) - timedelta(days=40)
    bars = {p: _fetch(p, start) for p in a.pairs}
    df = _utc(a.date_from + "T00:00:00Z") if a.date_from else None
    dt = _utc(a.date_to + "T23:59:59Z") if a.date_to else None
    results, coverage, stats = analyse(a.pairs, bars, regime, briefs, signals,
                                       shadows, a.k, a.reversal, df, dt)
    for p in a.pairs:
        h4 = bars[p][0]
        notes.append(f"{p}: {len(h4)} H4 bars {h4[0][0]:%Y-%m-%d %H:%M} to "
                     f"{h4[-1][0]:%Y-%m-%d %H:%M} UTC (open times); run matching: "
                     + ", ".join(f"{k} {v}" for k, v in sorted(stats[p].items())))
    report = render(results, coverage,
                    {"k": a.k, "rev": a.reversal, "pairs": a.pairs}, notes)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"report written: {a.out}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
