"""
decision_channel_followups.py — B3 and B4 of the week-of-10/17 fix set,
on the Phase 2 inventory (docs/specs/decision_channel_measurement_spec.md).

B3: every OPEN-market directional decision in the day logs: time (UTC and
    Pacific), pair, direction and the price the brief printed. Data only.
B4: the independent-episode count (and the gradeable bound) under both
    handlings of concurrent same-stamp runs: merged-if-agreeing (the rule
    added after the spec commit) and counted-as-error.

Reads the day logs and the exclusion registry read-only, and uses the H4
bar index already committed by the inventory run (no network call).

Usage: python3 studies/decision_channel_followups.py \
           --project "/Users/quis/Intelligence Framework" --out studies/decision_channel_followups_report.md
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "decision_channel_inventory", os.path.join(_HERE, "decision_channel_inventory.py"))
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)
PACIFIC = ZoneInfo("America/Los_Angeles")
# Before this merge the brief's "Price:" was the previous daily close, not a
# live quote, and carried no flag saying so (docs/specs/data_at_source_spec.md P1).
LIVE_PRICE_MERGE = datetime.fromisoformat("2026-09-30T08:54:45+00:00")   # 6471072


def bar_index(inst: str) -> list[datetime]:
    with open(os.path.join(_HERE, f"decision_channel_h4_index_{inst}.csv")) as f:
        return [datetime.fromisoformat(r["time"].replace("Z", "+00:00")) for r in csv.DictReader(f)]


def episodes(runs, dropped, bars):
    out = {}
    for inst in inv.INSTRUMENTS:
        onsets, eps = inv.episodes_for(inst, runs, dropped, bars[inst])
        out[inst] = (onsets, eps, Counter(inv.episode_status(o, inst, bars[inst]).split(" (")[0]
                                          for o in eps))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    logs = os.path.join(a.project, "logs")
    registry = inv.load_registry(os.path.join(a.project, "excluded_rows.csv"))
    bars = {i: bar_index(i) for i in inv.INSTRUMENTS}
    L = ["# Decision-channel follow-ups (B3, B4)\n"]

    runs = inv.parse_runs(logs)
    dropped = inv.apply_registry(runs, registry)
    rows = [(r, inst) for r in runs for inst in inv.INSTRUMENTS
            if r["inst"][inst]["status"] in ("LONG", "SHORT") and (runs.index(r), inst) not in dropped]
    L.append(f"## B3. Open-market directional decisions ({len(rows)})\n")
    L.append("| # | UTC | Pacific | pair | direction | printed price | price basis |")
    L.append("|---|---|---|---|---|---|---|")
    for n, (r, inst) in enumerate(rows, 1):
        p = r["inst"][inst]["prices"]
        L.append(f"| {n} | {inv.iso(r['t'])} | {r['t'].astimezone(PACIFIC):%a %Y-%m-%d %H:%M %Z} | "
                 f"{inst} | {r['inst'][inst]['status']} | "
                 f"{', '.join(f'{x:g}' for x in p) or '—'} | "
                 + ("previous daily close (before 6471072)" if r["t"] < LIVE_PRICE_MERGE
                    else "flagged not live" if r["inst"][inst]["not_live_price"]
                    else "live (after 6471072, no not-live flag)") + " |")
    L.append("")

    L.append("## B4. Concurrent-run handling: episodes and gradeable bound\n")
    L.append("| handling | GBP_AUD episodes | GBP_JPY episodes | total | gradeable (at most) | statuses |")
    L.append("|---|---|---|---|---|---|")
    for label, flag in (("merged if every copy agrees (as reported)", False),
                        ("every concurrent group counted as RUN ERRORED", True)):
        rs = inv.parse_runs(logs, concurrent_as_error=flag)
        res = episodes(rs, inv.apply_registry(rs, registry), bars)
        tot = sum((c for _, _, c in res.values()), Counter())
        L.append(f"| {label} | {len(res['GBP_AUD'][1])} | {len(res['GBP_JPY'][1])} | "
                 f"{sum(len(e) for _, e, _ in res.values())} | {tot.get('ELIGIBLE', 0)} | "
                 f"{dict(sorted(tot.items()))} |")
        for inst, (onsets, eps, _) in res.items():
            for o in eps:
                L.append(f"|  | {inst} {o['run']['local']} {o['direction']} | | | | "
                         f"{inv.episode_status(o, inst, bars[inst])} |")
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
