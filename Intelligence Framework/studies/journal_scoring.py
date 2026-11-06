"""Score the pre-trade journal's ideas on the framework's standard rule
(readiness task Part B, 2026-11-06). Read-only: never writes a ledger.

usage: python3 -I journal_scoring.py <journal_csv> <modern_data_dir>

The standard rule is shadow_signals.grade_pending_shadow's: from the H4 bar
`ei` of the signal, look at bars ei+1 .. ei+30; a touch of the stop is -1R;
otherwise R = direction-signed (close of bar ei+30 - entry) / |entry - stop|.
It uses no target.

The journal records no entry and no price at check. setup_check writes
stop_pips = |price - stop| / pip, so the price it measured from is recoverable
(M = stop -/+ stop_pips * pip). Before 2026-09-30 that price was the PREVIOUS
D1 CLOSE, not the market (data_at_source_spec P1); this script prints M beside
the prior D1 close to show it. M is therefore not an entry approximation and is
never graded. The entry is approximated two ways from market bars:
  E2  the close of the H4 bar containing the check time;
  E3  the open of the first H1 bar starting after the check time.
`ei` is the H4 bar containing the check time, so the hours of that bar after
the check are not seen by the H4 rule. A second pass checks them on H1.
A row with no stop cannot be graded in R; it is reported, not scored.
"""
import csv
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_archive as A  # noqa: E402
import session_movement_data as D  # noqa: E402

UTC = timezone.utc
HORIZON = 30
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def price_at_check(direction, stop, stop_pips, pip):
    """Recovered from setup_check's stop_pips = |price - stop| / pip."""
    return stop - stop_pips * pip if direction == "SHORT" else stop + stop_pips * pip


def grade(direction, entry, stop, fut_h, fut_l, exit_close):
    """The standard rule (shadow_signals.py, grade_pending_shadow)."""
    risk = abs(entry - stop) or 1e-9
    if direction == "LONG":
        hit, net = min(fut_l) <= stop, exit_close - entry
    else:
        hit, net = max(fut_h) >= stop, entry - exit_close
    return -1.0 if hit else round(net / risk, 2), hit


def bar_containing(times, t):
    prior = [b for b in times if b <= t]
    return prior[-1] if prior else None


def score_row(row, h4, h1):
    pair, direction = row["instrument"], row["direction"]
    pip = PIP[pair]
    t = parse_ts(row["timestamp"])
    t4 = sorted(h4)
    b = bar_containing(t4, t)
    i = t4.index(b)
    if i + HORIZON >= len(t4):
        return {"status": "horizon not elapsed"}
    fut = t4[i + 1:i + 1 + HORIZON]
    fut_h, fut_l = [h4[x][1] for x in fut], [h4[x][2] for x in fut]
    exit_close = h4[fut[-1]][3]
    out = {"h4_bar": b, "exit_bar": fut[-1], "exit_close": exit_close,
           "max_high": max(fut_h), "min_low": min(fut_l)}
    after = sorted(x for x in h1 if x > t)
    out["e3_bar"] = after[0]
    hb = bar_containing(sorted(h1), t)
    out["check_h1_range"] = (h1[hb][2], h1[hb][1])
    target = float(row["target"]) if row.get("target") else None
    if target is not None:
        out["target_reached"] = (min(fut_l) <= target) if direction == "SHORT" else (max(fut_h) >= target)
    if not row.get("stop_price"):
        out["status"] = "UNGRADEABLE (no stop recorded)"
        return out
    stop = float(row["stop_price"])
    measured = price_at_check(direction, stop, float(row["stop_pips"]), pip)
    entries = {"E2": h4[b][3], "E3": h1[after[0]][0]}
    rest = [x for x in sorted(h1) if x > t and x < fut[0]]           # H1 bars left in bar ei
    rest_hit = any((h1[x][1] >= stop) if direction == "SHORT" else (h1[x][2] <= stop) for x in rest)
    out["status"] = "graded"
    out["entries"] = entries
    out["measured_from"] = measured
    out["measured_inside_check_h1_range"] = (out["check_h1_range"][0] - pip <= measured
                                             <= out["check_h1_range"][1] + pip)
    out["recorded_stop_pips"] = float(row["stop_pips"])
    out["stop_touched_rest_of_check_bar"] = rest_hit
    out["grades"] = {k: grade(direction, e, stop, fut_h, fut_l, exit_close) for k, e in entries.items()}
    out["risk_pips"] = {k: abs(e - stop) / pip for k, e in entries.items()}
    return out


def prior_d1_close(d1, t):
    import history_study_convert as C
    prior = [b for b in sorted(d1) if C.session_day(b) < C.session_day(t)]
    return d1[prior[-1]][3] if prior else None


def main(journal, modern_dir):
    with open(os.path.join(modern_dir, "data_hashes.json")) as fh:
        A._check_hashes(modern_dir, __import__("json").load(fh)["files"])
    with open(journal, newline="") as fh:
        rows = list(csv.DictReader(fh))
    print(f"journal rows: {len(rows)} (read only)\n")
    for k, row in enumerate(rows, 1):
        pair = row["instrument"]
        h4 = D.load(os.path.join(modern_dir, f"{pair}_H4.csv"))
        h1 = D.load(os.path.join(modern_dir, f"{pair}_H1.csv"))
        d1 = D.load(os.path.join(modern_dir, f"{pair}_D.csv"))
        r = score_row(row, h4, h1)
        t = parse_ts(row["timestamp"])
        print(f"## Row {k}: {pair} {row['direction']} at {D.pt(t)}")
        print(f"  framework said: {row['framework_direction']} (grade {row['framework_grade']}); "
              f"against the framework: {row['against_framework']}")
        print(f"  recorded: stop {row['stop_price'] or '(none)'}, stop_pips {row['stop_pips'] or '(none)'}, "
              f"target {row['target'] or '(none)'}, r_to_target {row['r_to_target'] or '(none)'}")
        if "h4_bar" in r:
            print(f"  H4 bar of the check {D.pt(r['h4_bar'])}; horizon ends with the bar opening "
                  f"{D.pt(r['exit_bar'])}; exit close {r['exit_close']}; "
                  f"highest high {r['max_high']}, lowest low {r['min_low']} over the 30 bars")
        if "target_reached" in r:
            print(f"  target reached within the 30 bars: {r['target_reached']}")
        print(f"  status: {r['status']}")
        if r.get("status") == "graded":
            e = r["entries"]
            pdc = prior_d1_close(d1, t)
            print(f"  price setup_check measured from (recovered) {r['measured_from']:.5f}; previous D1 close "
                  f"{pdc}; inside the check hour's range: {r['measured_inside_check_h1_range']} "
                  f"-> recorded stop_pips {r['recorded_stop_pips']} is a distance from that, not from the market")
            print(f"  E2 close of the check's H4 bar {e['E2']}; E3 open of the next H1 bar "
                  f"({D.pt(r['e3_bar'])}) {e['E3']}")
            for name in ("E2", "E3"):
                g, hit = r["grades"][name]
                print(f"  {name}: risk {r['risk_pips'][name]:.1f} pips -> R {g:+.2f} (stop hit {hit})")
            print(f"  stop touched in the rest of the check's H4 bar (H1): "
                  f"{r['stop_touched_rest_of_check_bar']}")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
