"""
decision_channel_inventory.py — Phase 2 of
docs/specs/decision_channel_measurement_spec.md (frozen at c151e3c).

COUNTS AND WINDOWS ONLY. This script reads the day logs, the signal ledger
and the exclusion registry, and (with --fetch) the OANDA H4 bar TIMESTAMPS
needed to place runs on each instrument's own bar index. It never reads a
bar's prices or a brief's printed price, and it computes no accuracy, no R
and no directional statistic.

Run it with every side effect neutralized (rule 10), from the live checkout:
  python3 scripts/reality_run.py script <worktree>/studies/decision_channel_inventory.py \
      --code <worktree> -- --project "/Users/quis/Intelligence Framework" \
      --out <worktree>/studies --fetch

Outputs (to --out): decision_channel_inventory_report.md,
decision_channel_onsets.csv (for foundation/tools/episodes.py) and
decision_channel_h4_index_<INST>.csv (bar open times only).
"""
from __future__ import annotations

import argparse
import bisect
import csv
import glob
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

INSTRUMENTS = ("GBP_AUD", "GBP_JPY")
HORIZON = 30                                   # H4 bars (spec: shared definitions)
GAP_HOURS = 12.0                               # scheduler-gap threshold
REGISTRY_TOLERANCE_S = 60
CLOSED_BANNER = "Market closed — analysis based on last close."
NOT_LIVE_FLAGS = ("Price is the previous daily close", "Price source unknown")
TZ_OFFSETS = {"PDT": -7, "PST": -8, "MDT": -6, "MST": -7,
              "CDT": -5, "CST": -6, "EDT": -4, "EST": -5}

HEADER_RE = re.compile(r"^===== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([A-Z]{3,4}) =====$")
INST_RE = re.compile(r"^  (GBP/AUD|GBP/JPY)  \|")
DECISION_RE = re.compile(r"^  DECISION +(LONG|SHORT|STAND ASIDE)\b")
ERROR_RE = re.compile(r"^  REASON +Framework error")


def to_utc(stamp: str, tz: str) -> datetime:
    if tz not in TZ_OFFSETS:
        raise ValueError(f"unknown timezone abbreviation in run header: {tz!r}")
    local = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    return (local - timedelta(hours=TZ_OFFSETS[tz])).replace(tzinfo=timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── parsing ─────────────────────────────────────────────────────────────────

def parse_runs(logs_dir: str) -> list[dict]:
    """One dict per run header. Instrument status per the spec's table."""
    runs, by_stamp = [], {}
    for path in sorted(glob.glob(os.path.join(logs_dir, "brief_*.log"))):
        cur = None
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                m = HEADER_RE.match(line)
                if m:
                    # Concurrent wrappers (launchd catching up after wake) write
                    # the same header stamp, stacked and interleaved or one
                    # after the other: one run group, accepted only if every
                    # copy agrees (classify_run).
                    local = f"{m[1]} {m[2]}"
                    if local in by_stamp:
                        cur = by_stamp[local]
                        cur["concurrent"] += 1
                        continue
                    cur = {"file": os.path.basename(path), "local": local,
                           "t": to_utc(m[1], m[2]), "lines": [], "concurrent": 1}
                    by_stamp[local] = cur
                    runs.append(cur)
                elif cur is not None:
                    cur["lines"].append(line)
    for r in runs:
        try:
            r["inst"] = classify_run(r.pop("lines"), r["concurrent"])
        except ValueError as e:
            raise ValueError(f"{r['file']} run {r['local']}: {e}") from None
    runs.sort(key=lambda r: r["t"])
    return runs


def classify_run(lines: list[str], concurrent: int = 1) -> dict:
    # stdout ends where the wrapper's appended stderr section begins
    for i, ln in enumerate(lines):
        if ln.startswith("----- stderr"):
            lines = lines[:i]
            break
    blocks: dict[str, list[str]] = {}
    cur = None
    for ln in lines:
        m = INST_RE.match(ln)
        if m:
            cur = m[1].replace("/", "_")
            blocks.setdefault(cur, [])
        elif cur is not None:
            blocks[cur].append(ln)
    out = {}
    group_error = concurrent > 1 and any(ERROR_RE.match(ln) for ln in lines)
    for inst in INSTRUMENTS:
        b = blocks.get(inst)
        if concurrent > 1:
            # Interleaved copies: lines cannot be trusted to sit under their
            # own instrument header. Accept only an unambiguous group.
            decs = [DECISION_RE.match(ln)[1] for ln in (b or []) if DECISION_RE.match(ln)]
            if group_error:
                out[inst] = {"status": "RUN ERRORED", "decision": None,
                             "cause": f"{concurrent} concurrent runs, error page in output"}
                continue
            if len(decs) != concurrent or len(set(decs)) != 1:
                out[inst] = {"status": "RUN ERRORED", "decision": None,
                             "cause": f"{concurrent} concurrent runs, unreadable interleave"}
                continue
        if b is None:
            out[inst] = {"status": "RUN ERRORED", "decision": None,
                         "cause": "no block for the instrument (empty output or crash)"}
            continue
        decisions = [DECISION_RE.match(ln)[1] for ln in b if DECISION_RE.match(ln)]
        if len(decisions) > concurrent:
            raise ValueError(f"{inst}: {len(decisions)} DECISION lines for "
                             f"{concurrent} stacked header(s)")
        err = [i for i, ln in enumerate(b) if ERROR_RE.match(ln)]
        if len(set(decisions)) > 1:
            out[inst] = {"status": "RUN ERRORED", "decision": None,
                         "cause": f"{concurrent} concurrent runs disagree: {decisions}"}
        elif err:
            cause = []
            for ln in b[err[0]:]:
                if not ln.strip():
                    break
                cause.append(ln.strip())
            text = " ".join(cause).replace("REASON ", "", 1).strip()
            out[inst] = {"status": "RUN ERRORED", "decision": None, "cause": text}
        elif not decisions:
            out[inst] = {"status": "RUN ERRORED", "decision": None,
                         "cause": "block has no DECISION line"}
        else:
            closed = any(CLOSED_BANNER in ln for ln in b)
            d = decisions[0]
            out[inst] = {"status": "MARKET CLOSED" if closed else d,
                         "decision": d, "closed": closed,
                         "not_live_price": any(fl in ln for ln in b for fl in NOT_LIVE_FLAGS)}
    return out


def load_registry(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"exclusion registry not found: {path}")
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)(?:_(GBP_[A-Z]{3}))?$", r["log_id"])
            if not m:
                raise ValueError(f"registry log_id not a timestamp id: {r['log_id']!r}")
            out.append({"t": datetime.fromisoformat(m[1].replace("Z", "+00:00")),
                        "inst": m[2], **r})
    return out


def apply_registry(runs, registry):
    """Point-of-use filter: returns {(run index, inst): registry row}."""
    hits = {}
    for i, r in enumerate(runs):
        for e in registry:
            if abs((r["t"] - e["t"]).total_seconds()) <= REGISTRY_TOLERANCE_S:
                for inst in INSTRUMENTS:
                    if e["inst"] in (None, inst):
                        hits[(i, inst)] = e
    return hits


# ── bar index (timestamps only) ─────────────────────────────────────────────

def fetch_bar_index(inst: str, count: int) -> list[datetime]:
    from oanda_feed import get_h4_bars, is_configured, last_error
    if not is_configured():
        raise RuntimeError("OANDA not configured: run under scripts/reality_run.py")
    df = get_h4_bars(pair=inst.replace("_", ""), count=count)
    if df is None or df.empty:
        raise RuntimeError(f"H4 fetch failed for {inst}: {last_error()}")
    return sorted(t.to_pydatetime().astimezone(timezone.utc) for t in df.index)


def bar_of(bars: list[datetime], t: datetime) -> int:
    if not bars or t < bars[0]:
        raise ValueError(f"{iso(t)} is before the bar index")
    return bisect.bisect_right(bars, t) - 1


# ── episodes ────────────────────────────────────────────────────────────────

def episodes_for(inst, runs, dropped, bars):
    seq = [(i, r) for i, r in enumerate(runs)
           if r["inst"][inst]["status"] != "RUN ERRORED" and (i, inst) not in dropped]
    onsets, prev_dec, prev_i = [], None, None
    for k, (i, r) in enumerate(seq):
        d = r["inst"][inst]["decision"]
        if d in ("LONG", "SHORT") and d != prev_dec:
            onsets.append({"k": k, "i": i, "run": r, "direction": d,
                           "prev_i": prev_i})
        prev_dec, prev_i = d, i
    # censoring: no earlier observed run, or an UNOBSERVED window between
    for o in onsets:
        reasons = []
        if o["prev_i"] is None:
            reasons.append("no earlier observed run")
        else:
            span = runs[o["prev_i"]:o["i"] + 1]
            errs = [x for x in runs[o["prev_i"] + 1:o["i"]]
                    if x["inst"][inst]["status"] == "RUN ERRORED"]
            if errs:
                reasons.append(f"{len(errs)} errored run(s) between")
            gaps = [(a["t"], b["t"]) for a, b in zip(span, span[1:])
                    if (b["t"] - a["t"]).total_seconds() / 3600 > GAP_HOURS]
            if gaps:
                reasons.append(f"{len(gaps)} scheduler gap(s) > {GAP_HOURS:g}h between")
        o["censored"] = "; ".join(reasons)
    # signal run: first OPEN run inside the episode still carrying the direction
    for o in onsets:
        o["signal"], o["awaiting_open"] = None, False
        for k in range(o["k"], len(seq)):
            r = seq[k][1]["inst"][inst]
            if r["decision"] != o["direction"]:
                break
            if not r["closed"]:
                o["signal"] = seq[k][1]
                break
        else:
            o["awaiting_open"] = o["signal"] is None
    # spacing on the bar index
    eps, start = [], None
    for o in onsets:
        o["bar"] = bar_of(bars, o["run"]["t"]) if bars else None
        if bars is None:
            o["episode"] = None
            continue
        if start is None or o["bar"] - start >= HORIZON:
            start = o["bar"]
            o["episode"] = True
            eps.append(o)
        else:
            o["episode"] = False
    return onsets, eps


def episode_status(o, inst, bars) -> str:
    if o["censored"]:
        return "ONSET-CENSORED"
    if o["signal"] is None:
        return "AWAITING OPEN" if o["awaiting_open"] else "NEVER ACTIONABLE"
    if o["signal"]["inst"][inst]["not_live_price"]:
        return "PRICE NOT OBSERVED"
    st = o["signal"]["t"]
    after = len(bars) - bisect.bisect_left(bars, st)
    if after < HORIZON:
        return f"PENDING ({after}/{HORIZON} bars)"
    return "ELIGIBLE (structure and leg-minimum not yet checked)"


# ── report ──────────────────────────────────────────────────────────────────

def unobserved_windows(runs, first_log_day):
    wins = [("start of record", f"everything before {first_log_day}",
             "no day log exists before the first wrapper run", "—")]
    # errored stretches (either instrument)
    stretch = []                               # run indices
    def flush():
        if not stretch:
            return
        idx = list(stretch)
        stretch[:] = [runs[i] for i in idx]
        before = runs[idx[0] - 1]["local"] if idx[0] > 0 else "—"
        after = runs[idx[-1] + 1]["local"] if idx[-1] + 1 < len(runs) else "(still errored)"
        causes = Counter(c for x in stretch for c in
                         {x["inst"][i]["cause"] for i in INSTRUMENTS
                          if x["inst"][i]["status"] == "RUN ERRORED"})
        cause = "; ".join(f"{c} ×{n}" for c, n in causes.most_common(3))
        insts = sorted({i for x in stretch for i in INSTRUMENTS
                        if x["inst"][i]["status"] == "RUN ERRORED"})
        wins.append(("RUN ERRORED", f"{stretch[0]['local']} → {stretch[-1]['local']}"
                     f" (last good before: {before}; first good after: {after})",
                     cause, f"{len(stretch)} run(s), {'+'.join(insts)}"))
        stretch.clear()
    for n, r in enumerate(runs):
        if any(r["inst"][i]["status"] == "RUN ERRORED" for i in INSTRUMENTS):
            stretch.append(n)
        else:
            flush()
    flush()
    for a, b in zip(runs, runs[1:]):
        h = (b["t"] - a["t"]).total_seconds() / 3600
        if h > GAP_HOURS:
            wins.append(("SCHEDULER GAP", f"{a['local']} → {b['local']}",
                         f"no run for {h:.1f} h", "—"))
    return wins


def signal_ledger(path, registry, runs):
    rows = list(csv.DictReader(open(path, newline=""))) if os.path.exists(path) else []
    excl = {e["log_id"] for e in registry if e["ledger"] == "trade_signal_log.csv"}
    kept = [r for r in rows if r["signal_id"] not in excl]
    matched = []
    for r in kept:
        t = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        near = [x for x in runs if abs((x["t"] - t).total_seconds()) <= 600]
        dec = [x["inst"][r["instrument"]]["decision"] for x in near]
        matched.append((r, near[0]["local"] if near else None, dec[0] if dec else None))
    return rows, kept, matched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="the live checkout (read-only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fetch", action="store_true", help="fetch the H4 bar index from OANDA")
    ap.add_argument("--count", type=int, default=900)
    a = ap.parse_args()

    runs = parse_runs(os.path.join(a.project, "logs"))
    registry = load_registry(os.path.join(a.project, "excluded_rows.csv"))
    dropped = apply_registry(runs, registry)
    bars = {}
    fetched_at = None
    if a.fetch:
        fetched_at = datetime.now(timezone.utc)
        for inst in INSTRUMENTS:
            bars[inst] = fetch_bar_index(inst, a.count)
            with open(os.path.join(a.out, f"decision_channel_h4_index_{inst}.csv"), "w",
                      newline="") as f:
                w = csv.writer(f)
                w.writerow(["time"])
                w.writerows([[iso(t)] for t in bars[inst]])

    L = []
    p = L.append
    first_day = runs[0]["local"][:10]
    p("# Decision-channel inventory (Phase 2)\n")
    p("Spec: `docs/specs/decision_channel_measurement_spec.md` (frozen at c151e3c). "
      "Counts and windows only: no prices, no accuracy, no R.\n")
    if fetched_at:
        p(f"H4 bar index fetched {iso(fetched_at)} (timestamps only): " + ", ".join(
            f"{i} {len(bars[i])} bars {iso(bars[i][0])} → {iso(bars[i][-1])}" for i in INSTRUMENTS) + "\n")

    p("## 1. Where decision history survives\n")
    files = sorted({r["file"] for r in runs})
    tzs = Counter(r["local"].split()[-1] for r in runs)
    p(f"- **Day logs** `logs/brief_*.log`: {len(files)} files with runs, {len(runs)} runs, "
      f"{runs[0]['local']} → {runs[-1]['local']} ({iso(runs[0]['t'])} → {iso(runs[-1]['t'])}). "
      f"Header zones: {dict(tzs)}. Form: the full brief text per run, two instrument blocks.")
    groups = [r for r in runs if r["concurrent"] > 1]
    p(f"- **Concurrent run groups** (identical header stamp, merged into one observation; "
      f"accepted only if every copy agrees and none is an error page — parser rule added "
      f"after the spec commit, format only): {len(groups)}. " + "; ".join(
        f"{r['local']} ×{r['concurrent']} → " + ", ".join(
            f"{i} {r['inst'][i]['status']}" for i in INSTRUMENTS) for r in groups))
    rows, kept, matched = signal_ledger(os.path.join(a.project, "trade_signal_log.csv"), registry, runs)
    if rows:
        ts = sorted(r["timestamp"] for r in rows)
        p(f"- **trade_signal_log.csv**: {len(rows)} rows, {ts[0]} → {ts[-1]}; "
          f"{len(rows) - len(kept)} excluded by the registry. Form: one row per logged directional signal.")
        p("\n| signal_id | ledger direction | matching day-log run (±10 min) | day-log decision |")
        p("|---|---|---|---|")
        for r, run, dec in matched:
            p(f"| {r['signal_id']} | {r['direction']} | {run or 'NONE'} | {dec or '—'} |")
    p("")

    p("## 2–3. Status counts per instrument (each run × instrument is exactly one)\n")
    p("| instrument | LONG (open) | SHORT (open) | STAND ASIDE (open) | MARKET CLOSED | of which closed+directional | RUN ERRORED | registry-dropped |")
    p("|---|---|---|---|---|---|---|---|")
    for inst in INSTRUMENTS:
        c = Counter(r["inst"][inst]["status"] for r in runs)
        cd = sum(1 for r in runs if r["inst"][inst]["status"] == "MARKET CLOSED"
                 and r["inst"][inst]["decision"] in ("LONG", "SHORT"))
        nd = sum(1 for (i, x) in dropped if x == inst)
        p(f"| {inst} | {c['LONG']} | {c['SHORT']} | {c['STAND ASIDE']} | {c['MARKET CLOSED']} | {cd} | {c['RUN ERRORED']} | {nd} |")
    old = sum(1 for r in runs if any(r["inst"][i]["decision"] in ("LONG", "SHORT") for i in INSTRUMENTS))
    new = sum(1 for r in runs if any(r["inst"][i]["decision"] in ("LONG", "SHORT")
                                     and not r["inst"][i]["closed"] for i in INSTRUMENTS))
    p(f"\nRuns that would raise a DECISION notification: old trigger {old}, "
      f"with the Phase 0 market-status gate {new} (derived from the parsed statuses; "
      "the real wrapper replay is in the Gate 2 report).\n")

    p("## 4. UNOBSERVED windows\n")
    p("| kind | window (header times) | cause | size |")
    p("|---|---|---|---|")
    for kind, win, cause, size in unobserved_windows(runs, first_day):
        p(f"| {kind} | {win} | {cause} | {size} |")
    p("")

    p("## 5. Exclusion registry\n")
    for e in registry:
        hit = [f"{runs[i]['local']} {inst}" for (i, inst), x in dropped.items() if x is e]
        p(f"- `{e['log_id']}` ({e['ledger']}, authorized by: {e['authorizing_entry'] or '—'}): "
          f"day-log runs matched within {REGISTRY_TOLERANCE_S}s: {', '.join(hit) or 'none'}")
    p("")

    p("## 2 & 6. Onsets, episodes, gradeability\n")
    onset_rows, totals = [], Counter()
    for inst in INSTRUMENTS:
        onsets, eps = episodes_for(inst, runs, dropped, bars.get(inst))
        raw = sum(1 for r in runs if r["inst"][inst]["decision"] in ("LONG", "SHORT"))
        p(f"### {inst}\n")
        p(f"Raw directional DECISION occurrences: {raw}. Onsets (state changes into LONG/SHORT): "
          f"{len(onsets)}. Independent episodes (30-bar spacing on the H4 index): "
          f"{len(eps) if bars else 'not computed (no bar index)'}.\n")
        p("| onset run | direction | bar | episode? | signal run (first open) | status |")
        p("|---|---|---|---|---|---|")
        for o in onsets:
            st = episode_status(o, inst, bars[inst]) if (bars and o["episode"]) else (
                "ABSORBED (inside previous episode's 30 bars)" if o["episode"] is False else "—")
            if o["episode"]:
                totals[st.split(" (")[0]] += 1
            p(f"| {o['run']['local']} | {o['direction']} | {o['bar']} | "
              f"{'yes' if o['episode'] else 'no'} | "
              f"{o['signal']['local'] if o['signal'] else '—'} | {st}"
              f"{' — ' + o['censored'] if o['censored'] and o['episode'] else ''} |")
            onset_rows.append({"instrument": inst, "onset_time": iso(o["run"]["t"]),
                               "direction": o["direction"],
                               "episode": o["episode"], "status": st})
        p("")
    with open(os.path.join(a.out, "decision_channel_onsets.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instrument", "onset_time", "direction", "episode", "status"])
        w.writeheader()
        w.writerows(onset_rows)
    p("### Gradeability (pooled)\n")
    for k, n in sorted(totals.items()):
        p(f"- {k}: {n}")
    elig = totals.get("ELIGIBLE", 0)
    p(f"\n**Gradeable for Measurement A: at most {elig}.** Structure-undefined and "
      "sub-minimum legs need prices and can only lower this number.")
    if elig < 10:
        p("\n**STOP RULE MET (fewer than 10).** Measurement A is not run. The owner decides "
          "whether to run or wait.")
    with open(os.path.join(a.out, "decision_channel_inventory_report.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
