"""
long_side_diagnosis.py — why 16 of 16 open-market directional decisions
were SHORT (week-of-10/17 item 3). DIAGNOSIS ONLY: nothing on the decision
path is changed, no threshold is moved, nothing is written outside --out.

Two parts:

  funnel  (3B) Where the long side is lost. Per pair, counted on
          regime_classification_log.csv (exclusions applied at use) and on
          the day logs: UP vs DOWN regime classifications, the direction the
          official path derives from them, how many clear the 20-week gate and
          the resolution table, and the final decision of the matching run.
          Local files only.

  mirror  (3A, empirical half) Real OANDA D1/H4/W bars are reflected about
          their mean (p -> 2m - p, highs and lows swapped), which turns every
          up move into the same-sized down move and leaves every bar-to-bar
          difference (ATR, ADX, pivots, pips) unchanged. The real get_regime
          and the official decision run on both at many as-of points with the
          feed functions mocked. A mirror-symmetric path returns the mirrored
          decision at every point; each mismatch is listed with its inputs.
          Needs credentials: run through scripts/reality_run.py.

Usage:
  python3 studies/long_side_diagnosis.py funnel --project "/Users/quis/Intelligence Framework" --out <md>
  python3 scripts/reality_run.py script <this> --code <worktree> -- mirror --out <md> [--points 300]
"""
from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

INSTRUMENTS = ("GBP_AUD", "GBP_JPY")
# weekly_context -> the 20-week trend it implies. Exact: each context label
# is emitted for one lt_trend only (regime_detection._compute_weekly_context).
LT_OF_CONTEXT = {"ESTABLISHED_UPTREND": "UPTREND", "PULLBACK_IN_UPTREND": "UPTREND",
                 "ESTABLISHED_DOWNTREND": "DOWNTREND", "COUNTER_TREND_BOUNCE": "DOWNTREND",
                 "RANGING": "RANGING"}
LIVE_PRICE_MERGE = datetime(2026, 9, 30, 8, 54, 45, tzinfo=timezone.utc)   # 6471072
_HERE = os.path.dirname(os.path.abspath(__file__))


def _inventory():
    s = importlib.util.spec_from_file_location(
        "decision_channel_inventory", os.path.join(_HERE, "decision_channel_inventory.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ── 3B: the funnel ──────────────────────────────────────────────────────────

def funnel(project: str) -> list[str]:
    sys.path.insert(0, project)
    from no_trade_filter import _derive_direction
    from exclusions import excluder
    inv = _inventory()
    runs = inv.parse_runs(os.path.join(project, "logs"))
    is_excl = excluder("regime_classification_log.csv")
    with open(os.path.join(project, "regime_classification_log.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    kept = [r for r in rows if not is_excl(r)]
    L = ["## 3B. Funnel\n",
         f"`regime_classification_log.csv`: {len(rows)} rows, {len(rows) - len(kept)} excluded "
         f"by the registry at use, {len(kept)} counted. Each row is one market-open "
         f"classification. The final decision is the day-log run within 10 minutes of the "
         f"row (`decision_channel_inventory.parse_runs`).\n"]

    def match(r):
        t = _utc(r["timestamp"])
        near = [x for x in runs if abs((x["t"] - t).total_seconds()) <= 600]
        return near[0]["inst"][r["instrument"]] if near else None

    for era, pred in (("all rows", lambda r: True),
                      ("logic p5-2026-09-30 (current rules)", lambda r: r["logic_version"] == "p5-2026-09-30"),
                      ("before p5 (blank logic_version)", lambda r: r["logic_version"] == "")):
        sub = [r for r in kept if pred(r)]
        L.append(f"### {era}: {len(sub)} rows\n")
        L.append("| pair | rows | D1 UP / DOWN / RANGING / VOLATILE | H4 UP / DOWN | derived LONG / SHORT / none "
                 "| LONG / SHORT past the 20-week gate and table | D1 VOLATILE with H4 trending UP / DOWN "
                 "| final decision in the day log: LONG / SHORT / STAND ASIDE / closed / error / no run |")
        L.append("|---|---|---|---|---|---|---|---|")
        for inst in INSTRUMENTS:
            rr = [r for r in sub if r["instrument"] == inst]
            d1 = Counter(r["regime_d1"] for r in rr)
            h4 = Counter(r["regime_h4"] for r in rr)
            der = Counter(_derive_direction(r["regime_d1"], r["execution_mode"]) for r in rr)
            passed = Counter()
            for r in rr:
                d = _derive_direction(r["regime_d1"], r["execution_mode"])
                lt = LT_OF_CONTEXT.get(r["weekly_context"], "UNAVAILABLE")
                blocked = ((d == "SHORT" and lt == "UPTREND") or (d == "LONG" and lt == "DOWNTREND")
                           or r["execution_mode"] == "STAND_DOWN" or lt == "UNAVAILABLE")
                if d in ("LONG", "SHORT") and not blocked:
                    passed[d] += 1
            ovr = Counter(r["regime_h4"] for r in rr if r["regime_d1"] == "VOLATILE"
                          and r["regime_h4"] in ("TRENDING_UP", "TRENDING_DOWN"))
            fin = Counter()
            for r in rr:
                m = match(r)
                fin[m["status"] if m else "no run"] += 1
            L.append(f"| {inst} | {len(rr)} | {d1['TRENDING_UP']} / {d1['TRENDING_DOWN']} / "
                     f"{d1['RANGING']} / {d1['VOLATILE']} | {h4['TRENDING_UP']} / {h4['TRENDING_DOWN']} | "
                     f"{der['LONG']} / {der['SHORT']} / {der['NONE']} | {passed['LONG']} / {passed['SHORT']} | "
                     f"{ovr['TRENDING_UP']} / {ovr['TRENDING_DOWN']} | {fin['LONG']} / {fin['SHORT']} / "
                     f"{fin['STAND ASIDE']} / {fin['MARKET CLOSED']} / {fin['RUN ERRORED']} / {fin['no run']} |")
        L.append("")

    # every D1 UP classification, row by row: where did each one stop?
    L.append("### Every D1 TRENDING_UP row and where it stopped\n")
    L.append("| pair | UTC | H4 | execution mode | weekly context | derived | final decision |")
    L.append("|---|---|---|---|---|---|---|")
    for r in kept:
        if r["regime_d1"] != "TRENDING_UP":
            continue
        m = match(r)
        L.append(f"| {r['instrument']} | {r['timestamp']} | {r['regime_h4']} | {r['execution_mode']} | "
                 f"{r['weekly_context']} | {_derive_direction(r['regime_d1'], r['execution_mode'])} | "
                 f"{m['status'] if m else 'no run'} |")
    L.append("")

    # day logs: the daily-chart wording of every open-market, non-errored run
    L.append("### Day-log cross-check: the daily chart as the brief rendered it\n")
    L.append("Every open-market, non-errored run (`parse_runs` statuses), MARKET STATE unwrapped. "
             "'trending up' / 'trending down' is the TRENDING_UP / TRENDING_DOWN rendering "
             "(trend labels carry no subtype); 'rising' / 'falling' is an unconfirmed trend "
             "(regime stays VOLATILE).\n")
    by = defaultdict(Counter)
    for x in runs_with_state(os.path.join(project, "logs"), inv):
        by[x["inst"]][(x["d1"], x["status"])] += 1
    L.append("| pair | daily-chart wording | LONG | SHORT | STAND ASIDE |")
    L.append("|---|---|---|---|---|")
    for inst in INSTRUMENTS:
        words = sorted({w for (w, _) in by[inst]})
        for w in words:
            L.append(f"| {inst} | {w} | {by[inst][(w, 'LONG')]} | {by[inst][(w, 'SHORT')]} | "
                     f"{by[inst][(w, 'STAND ASIDE')]} |")
    L.append("")
    return L


_D1_WORDS = (("trending up", "trending up"), ("trending down", "trending down"),
             ("in a strong uptrend", "in a strong uptrend"),
             ("in a strong downtrend", "in a strong downtrend"),
             ("rising", "rising (unconfirmed)"), ("falling", "falling (unconfirmed)"),
             ("moving sideways", "moving sideways"), ("no clear direction", "no clear direction"))


def runs_with_state(logs: str, inv) -> list[dict]:
    """Open-market, non-errored run x pair, with the unwrapped daily-chart wording."""
    runs = inv.parse_runs(logs)
    texts = {}
    for p in sorted(glob.glob(os.path.join(logs, "brief_*.log"))):
        cur = None
        for line in open(p, encoding="utf-8", errors="replace"):
            m = inv.HEADER_RE.match(line.rstrip("\n"))
            if m:
                cur = f"{m[1]} {m[2]}"
                texts.setdefault(cur, [])
            elif cur:
                texts[cur].append(line.rstrip("\n"))
    out = []
    for r in runs:
        if r["concurrent"] > 1:
            continue                                   # interleaved text: wording unreadable
        blocks, inst = {}, None
        for ln in texts.get(r["local"], []):
            m = inv.INST_RE.match(ln)
            if m:
                inst = m[1].replace("/", "_")
                blocks[inst] = []
            elif inst:
                blocks[inst].append(ln)
        for i in INSTRUMENTS:
            st = r["inst"][i]["status"]
            if st not in ("LONG", "SHORT", "STAND ASIDE") or i not in blocks:
                continue
            ms, grab = [], False
            for ln in blocks[i]:
                if ln.startswith("  MARKET STATE"):
                    grab = True
                    ms.append(ln[len("  MARKET STATE"):])
                elif grab:
                    if not ln.strip():
                        break
                    ms.append(ln)
            text = re.sub(r"\s+", " ", " ".join(ms))
            d1 = re.search(r"Daily chart: ([^|(]*)", text)
            phrase = d1.group(1).strip().lower() if d1 else ""
            word = next((lab for key, lab in _D1_WORDS if phrase.startswith(key)), f"other: {phrase[:30]}")
            out.append({"inst": i, "status": st, "d1": word, "t": r["t"]})
    return out


# ── 3A: the mirror test ─────────────────────────────────────────────────────

def _mirror(df):
    m = (df["High"].max() + df["Low"].min()) / 2.0
    out = df.copy()
    out["High"], out["Low"] = 2 * m - df["Low"], 2 * m - df["High"]
    for c in ("Open", "Close"):
        if c in df:
            out[c] = 2 * m - df[c]
    return out


def _pcts(W, cut):
    """The 20-week and 4-week % changes exactly as _compute_weekly_context's
    _trend_dir computes them, on the closed weekly bars at `cut`."""
    import regime_detection as rd
    c = list(W[W.index + timedelta(days=7) <= cut].tail(110)["Close"])
    out = []
    for lb in (rd._WEEKLY_LT_LOOKBACK, rd._WEEKLY_ST_LOOKBACK):
        recent, past = sum(c[-3:]) / 3, sum(c[-(lb + 3):-lb]) / 3
        out.append((recent - past) / past * 100)
    return out


def mirror(points: int) -> list[str]:
    from unittest import mock
    import regime_detection as rd
    from official_decision import get_official_decision
    from oanda_feed import _get_bars, is_configured
    if not is_configured():
        raise SystemExit("OANDA not configured: run through scripts/reality_run.py")
    FLIP = {"TRENDING_UP": "TRENDING_DOWN", "TRENDING_DOWN": "TRENDING_UP",
            "UPTREND": "DOWNTREND", "DOWNTREND": "UPTREND", "LONG": "SHORT", "SHORT": "LONG",
            "ESTABLISHED_UPTREND": "ESTABLISHED_DOWNTREND", "ESTABLISHED_DOWNTREND": "ESTABLISHED_UPTREND",
            "PULLBACK_IN_UPTREND": "COUNTER_TREND_BOUNCE", "COUNTER_TREND_BOUNCE": "PULLBACK_IN_UPTREND"}
    f = lambda v: FLIP.get(v, v)
    open_now = rd._market_status(_now=datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc))
    L = ["## 3A (empirical). Mirror test on real bars\n",
         "Bars reflected about their mean: every up move becomes the same-sized down move, "
         "and ATR, ADX, pivots and pip distances are unchanged. Feed functions mocked; the "
         "market forced open; no news gate. Compared per as-of point: D1 and H4 regime, D1 "
         "structure, 20-week and 4-week trend, weekly context, filter allowed, direction, "
         "conviction. Weekly context is compared through the label pairing "
         "ESTABLISHED_UP<->DOWN and PULLBACK_IN_UPTREND<->COUNTER_TREND_BOUNCE.\n"]
    fields = ("regime_d1", "regime_h4", "structure", "lt_trend", "st_trend", "weekly_context",
              "filter_allowed", "direction", "conviction")
    for inst in INSTRUMENTS:
        pair = inst.replace("_", "")
        d1 = _get_bars(pair, "D", 1200, 30)
        h4 = _get_bars(pair, "H4", 5000, 30)
        wk = _get_bars(pair, "W", 400, 30)
        if any(x is None or x.empty for x in (d1, h4, wk)):
            raise SystemExit(f"{inst}: bar fetch failed")
        md1, mh4, mwk = _mirror(d1), _mirror(h4), _mirror(wk)
        # as-of points: H4 bar closes, evenly spaced, leaving full look-back windows
        start = max(d1.index[300], wk.index[120], h4.index[200])
        cand = [t for t in h4.index if t >= start]
        step = max(1, len(cand) // points)
        asof = cand[::step][:points]
        mism, n, dirs, label_only = [], 0, Counter(), Counter()
        for t in asof:
            cut = t + timedelta(hours=4)          # this H4 bar has closed
            def run(D, H, W):
                dd = D[D.index + timedelta(days=1) <= cut].tail(220)    # live count=220
                hh = H[H.index + timedelta(hours=4) <= cut].tail(120)
                ww = W[W.index + timedelta(days=7) <= cut].tail(110)
                with mock.patch("regime_detection._oanda_ok", return_value=True), \
                     mock.patch("regime_detection._oanda_daily_bars", return_value=dd), \
                     mock.patch("regime_detection._oanda_h4_bars", return_value=hh), \
                     mock.patch("regime_detection._oanda_weekly_bars", return_value=ww), \
                     mock.patch("regime_detection._oanda_live_price", return_value=float(hh["Close"].iloc[-1])), \
                     mock.patch("regime_detection._market_status", return_value=open_now), \
                     mock.patch("news_gate.check_news_gate", return_value={"gating": False}):
                    r = rd.get_regime(inst)
                r = dict(r)
                r.update({k: v for k, v in get_official_decision(r).items() if k in ("direction", "conviction")})
                return r
            a, b = run(d1, h4, wk), run(md1, mh4, mwk)
            if a.get("error") or b.get("error"):
                mism.append((t, "error", a.get("error"), b.get("error")))
                continue
            n += 1
            dirs[(a["direction"], b["direction"])] += 1
            lt_st_mirror = (f(a.get("lt_trend")) == b.get("lt_trend")
                            and f(a.get("st_trend")) == b.get("st_trend"))
            for k in fields:
                if f(a.get(k)) != b.get(k):
                    if k == "weekly_context" and lt_st_mirror:
                        label_only[(a.get("lt_trend"), a.get("st_trend"), a.get(k), b.get(k))] += 1
                        continue
                    extra = ""
                    if k in ("lt_trend", "st_trend", "weekly_context"):
                        extra = " | 20w/4w pct orig " + "/".join(f"{x:+.3f}%" for x in _pcts(wk, cut)) \
                                + ", mirror " + "/".join(f"{x:+.3f}%" for x in _pcts(mwk, cut))
                    mism.append((t, k, a.get(k), f"{b.get(k)}{extra}"))
        bad_pts = len({m[0] for m in mism})
        L.append(f"### {inst}: {n} as-of points, {bad_pts} with any mismatch\n")
        L.append("Direction pairs (original, mirror): " +
                 ", ".join(f"{k[0]}/{k[1]} {v}" for k, v in sorted(dirs.items())) + "\n")
        if label_only:
            L.append("Weekly-context differences with the 20-week and 4-week trends mirrored exactly "
                     "(the label table itself, regime_detection.py:591-618): " + "; ".join(
                         f"lt={k[0]} st={k[1]}: original {k[2]}, mirror {k[3]} x{v}"
                         for k, v in sorted(label_only.items())) + "\n")
        by_field = Counter(m[1] for m in mism)
        L.append("Mismatches by field: " + (", ".join(f"{k} {v}" for k, v in by_field.most_common()) or "none") + "\n")
        if mism:
            L.append("| as-of (bar open, UTC) | field | original | mirror |")
            L.append("|---|---|---|---|")
            for t, k, x, y in mism[:60]:
                L.append(f"| {t:%Y-%m-%dT%H:%MZ} | {k} | {x} | {y} |")
            L.append("")
    return L


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("part", choices=["funnel", "mirror"])
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--out", required=True)
    ap.add_argument("--points", type=int, default=300)
    a = ap.parse_args()
    L = funnel(a.project) if a.part == "funnel" else mirror(a.points)
    text = "\n".join(L) + "\n"
    with open(a.out, "w") as fh:
        fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
