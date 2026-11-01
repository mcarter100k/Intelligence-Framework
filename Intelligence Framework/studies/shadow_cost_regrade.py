"""Re-grade the shadow ledger with trading costs (driver-coverage proposal step 3).

Read-only. The frozen grader scores mid prices with no spread and no
financing (foundation/candidates.md §5a; R32: financing is about 0.1R per
5-day GBP/JPY hold). This study shows each graded episode's R beside the
same R after costs, so the futility checkpoint (N=20, bound +0.15R) and any
later review can see what costs do. It never edits the ledger and never
changes r_multiple (AGENTS trap T6: a cost change to a frozen candidate is a
new id, never an in-place edit).

Parameters, fixed before the run (validation_log 2026-11-01):
  * Episodes: shadow_signals.graded_episodes, the live definition (graded,
    valid, non-excluded rows; first fire per 30-bar episode). All graded
    valid rows are also reported, for the typical cost per fire.
  * Candidates: EARLY_MOMENTUM_v2, THRUST_PULLBACK, MOMENTUM_JOIN.
    EARLY_MOMENTUM (v1) is retired and its rows predate the grader's
    500-bar window.
  * Positive control: every graded row's raw R is recomputed from freshly
    fetched H4 bars with the grader's own rule; any mismatch with the
    ledger's r_multiple (2 dp) aborts the study.
  * Spread: 3.0 pips round trip (study convention, data_map_spec era
    2021->); sensitivity 4.0 (execution tools, risk_config).
  * Financing: OANDA's quoted annual rates on 2026-11-01
    (studies/instrument_probe_report.md): GBP_JPY long +1.60% / short -3.66%;
    GBP_AUD long -1.89% / short -0.18%, applied to the whole period (the
    endpoint gives no history: an approximation). Sensitivity: every rate
    1 point worse.
  * Rollovers: one per 17:00 New York crossed while the position is open,
    Wednesday's counted 3 times (the weekend). Entry is the close of the fire
    bar; a rollover at that instant is not counted. Exit is the stop-hit bar
    (the position is open at its start) or the close of bar 30.
  * Cost-adjusted R = raw R - spread/risk + financing/risk, all in pips,
    risk = |entry - stop|.

usage:
  python3 -I shadow_cost_regrade.py selftest
  python3 scripts/reality_run.py script studies/shadow_cost_regrade.py run <report_md>
"""
import csv
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

NY = ZoneInfo("America/New_York")
HORIZON = 30
CANDIDATES = ("EARLY_MOMENTUM_v2", "THRUST_PULLBACK", "MOMENTUM_JOIN")
PIP = {"GBP_JPY": 0.01, "GBP_AUD": 0.0001}
SPREAD = 3.0
SPREAD_SENS = 4.0
RATES = {("GBP_JPY", "LONG"): 0.0160, ("GBP_JPY", "SHORT"): -0.0366,
         ("GBP_AUD", "LONG"): -0.0189, ("GBP_AUD", "SHORT"): -0.0018}
RATE_SENS = -0.01
MIN_N = 20


def rollover_nights(entry_time, exit_time):
    """Nights of financing between entry and exit: each 17:00 New York strictly
    after entry and at or before exit counts 1, Wednesday's counts 3."""
    nights = 0
    t = entry_time.astimezone(NY)
    day = t.date()
    while True:
        roll = datetime(day.year, day.month, day.day, 17, 0, tzinfo=NY)
        if roll > exit_time.astimezone(NY):
            break
        if roll > t and roll.weekday() < 5:
            nights += 3 if roll.weekday() == 2 else 1
        day += timedelta(days=1)
    return nights


def regrade_row(row, opens, H, L, C, spread=SPREAD, rate_shift=0.0):
    """Recompute one graded row from bars. Returns a dict, or raises ValueError on a
    reproduction mismatch (the positive control)."""
    inst, direction = row["instrument"], row["direction"]
    pip = PIP[inst]
    ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    ei = opens.index(ts)
    entry, stop = float(row["entry"]), float(row["stop"])
    risk = abs(entry - stop)
    hit_bar = None
    for j in range(ei + 1, ei + 1 + HORIZON):
        if (direction == "LONG" and L[j] <= stop) or (direction == "SHORT" and H[j] >= stop):
            hit_bar = j
            break
    if hit_bar is not None:
        raw = -1.0
        exit_time = opens[hit_bar]
    else:
        sign = 1 if direction == "LONG" else -1
        raw = round(sign * (C[ei + HORIZON] - entry) / risk, 2)
        exit_time = opens[ei + HORIZON] + timedelta(hours=4)
    if abs(raw - float(row["r_multiple"])) > 0.005:
        raise ValueError(f"reproduction mismatch {row['candidate_id']} {row['timestamp']}: "
                         f"recomputed {raw}, ledger {row['r_multiple']}")
    entry_time = opens[ei] + timedelta(hours=4)
    nights = rollover_nights(entry_time, exit_time)
    rate = RATES[(inst, direction)] + rate_shift
    risk_pips = risk / pip
    fin_pips = entry * rate * nights / 365 / pip
    return {"timestamp": row["timestamp"], "direction": direction, "raw": raw,
            "nights": nights, "spread_r": spread / risk_pips, "fin_r": fin_pips / risk_pips,
            "adj": raw - spread / risk_pips + fin_pips / risk_pips, "risk_pips": risk_pips,
            "stopped": hit_bar is not None}


def _summary(xs):
    if not xs:
        return "N 0"
    return (f"N {len(xs)}; mean {statistics.fmean(xs):+.3f}R; median {statistics.median(xs):+.3f}R"
            + ("" if len(xs) >= MIN_N else f"  (INSUFFICIENT: N<{MIN_N})"))


# Self-test ---------------------------------------------------------------------

def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    utc = timezone.utc
    # Rollovers: Mon 2026-10-05 09:00 UTC -> Thu 2026-10-08 09:00 UTC crosses Mon, Tue, Wed (x3) 17:00 NY = 5
    check("Mon->Thu crosses Mon, Tue, Wed(x3) = 5 nights",
          rollover_nights(datetime(2026, 10, 5, 9, tzinfo=utc), datetime(2026, 10, 8, 9, tzinfo=utc)) == 5)
    # Entry exactly at the rollover instant (21:00 UTC in EDT) is not charged that night
    check("entry at 17:00 NY is not charged that rollover",
          rollover_nights(datetime(2026, 10, 5, 21, tzinfo=utc), datetime(2026, 10, 6, 20, tzinfo=utc)) == 0)
    check("exit at exactly 17:00 NY is charged that rollover",
          rollover_nights(datetime(2026, 10, 5, 20, tzinfo=utc), datetime(2026, 10, 5, 21, tzinfo=utc)) == 1)
    # Winter time: 17:00 NY = 22:00 UTC after 2026-11-01
    check("winter: 21:30 UTC is before the 22:00 UTC rollover",
          rollover_nights(datetime(2026, 11, 2, 12, tzinfo=utc), datetime(2026, 11, 2, 21, 30, tzinfo=utc)) == 0
          and rollover_nights(datetime(2026, 11, 2, 12, tzinfo=utc), datetime(2026, 11, 2, 22, 0, tzinfo=utc)) == 1)
    check("Fri -> Mon: Friday's rollover only (weekend carried on Wednesday)",
          rollover_nights(datetime(2026, 10, 9, 12, tzinfo=utc), datetime(2026, 10, 12, 12, tzinfo=utc)) == 1)

    # Hand-computed regrade: GBP_JPY LONG entry 210.00, stop 209.00 (100 pips risk),
    # 31 bars from Mon 2026-10-05 05:00 UTC, flat at 210.00, close of bar 30 = 210.50 -> raw +0.50R
    opens = [datetime(2026, 10, 5, 5, tzinfo=utc) + timedelta(hours=4 * k) for k in range(40)]
    H = [210.2] * 40
    L = [209.8] * 40
    C = [210.0] * 40
    C[30] = 210.5
    row = {"candidate_id": "X", "instrument": "GBP_JPY", "direction": "LONG", "timestamp": "2026-10-05T05:00:00Z",
           "entry": "210.0", "stop": "209.0", "r_multiple": "0.5"}
    g = regrade_row(row, opens, H, L, C)
    exit_t = opens[30] + timedelta(hours=4)
    n = rollover_nights(opens[0] + timedelta(hours=4), exit_t)
    fin_r = 210.0 * 0.016 * n / 365 / 0.01 / 100
    check(f"timed exit: raw +0.50, spread 0.03R, {n} nights, financing {fin_r:+.4f}R",
          g["raw"] == 0.5 and abs(g["spread_r"] - 0.03) < 1e-12 and g["nights"] == n
          and abs(g["fin_r"] - fin_r) < 1e-12 and abs(g["adj"] - (0.5 - 0.03 + fin_r)) < 1e-12)
    check(f"exit Sat 2026-10-10 09:00 UTC (synthetic bars run through the weekend): nights = 5 + Thu + Fri = 7 ({n})", n == 7)
    # Stop hit on bar 3: exit time is that bar's open; raw -1
    L2 = list(L)
    L2[3] = 208.9
    row2 = dict(row, r_multiple="-1.0")
    g2 = regrade_row(row2, opens, H, L2, C)
    check(f"stop on bar 3: raw -1.0, exit at bar 3's open, nights {g2['nights']}",
          g2["raw"] == -1.0 and g2["stopped"]
          and g2["nights"] == rollover_nights(opens[0] + timedelta(hours=4), opens[3]))
    # Positive control: a ledger R that disagrees with the bars aborts
    try:
        regrade_row(dict(row, r_multiple="0.7"), opens, H, L, C)
        aborted = False
    except ValueError:
        aborted = True
    check("a ledger R that the bars do not reproduce aborts", aborted)
    # Short side pays GBP_JPY financing (negative rate) -> financing cost
    rows3 = dict(row, direction="SHORT", stop="211.0", r_multiple="-0.5")
    g3 = regrade_row(rows3, opens, H, L, C)
    check(f"GBP_JPY short pays financing ({g3['fin_r']:+.4f}R < 0)", g3["raw"] == -0.5 and g3["fin_r"] < 0)
    print("SELFTEST", "OK" if ok else "FAILED")
    return ok


# Run ------------------------------------------------------------------------------

def run(report):
    import shadow_signals as S
    from oanda_feed import get_h4_bars
    bars = {}
    for inst in PIP:
        df = get_h4_bars(pair=inst.replace("_", ""), count=500)
        if df is None or df.empty:
            raise RuntimeError(f"no H4 bars for {inst}")
        opens = [t.to_pydatetime().astimezone(timezone.utc) for t in df.index]
        bars[inst] = (opens, [float(v) for v in df["High"]], [float(v) for v in df["Low"]],
                      [float(v) for v in df["Close"]])
    with open(S.LOG_FILE, newline="") as f:
        ledger = list(csv.DictReader(f))
    is_excluded = S.excluder("shadow_signal_log.csv")
    lines = ["# Shadow ledger re-graded with costs (read-only)", "",
             f"Spread {SPREAD} pips round trip (sensitivity {SPREAD_SENS}); financing at OANDA's "
             f"2026-11-01 quoted rates (sensitivity: 1 point worse); rollovers at 17:00 New York, "
             f"Wednesday x3. Raw R is the frozen grader's; adjusted R never replaces it.", ""]
    reproduced = 0
    for cand in CANDIDATES:
        graded = [r for r in ledger if r["candidate_id"] == cand and str(r.get("outcome_filled")) == "True"
                  and not S.is_invalid_spec(r) and not is_excluded(r)]
        all_rows = [regrade_row(r, *bars[r["instrument"]]) for r in graded]
        reproduced += len(all_rows)
        eps = {r["timestamp"] + r["instrument"] for r in S.graded_episodes(cand)}
        ep_rows = [(r, g) for r, g in zip(graded, all_rows) if r["timestamp"] + r["instrument"] in eps]
        sens = [regrade_row(r, *bars[r["instrument"]], spread=SPREAD_SENS, rate_shift=RATE_SENS)
                for r, _ in ep_rows]
        lines += [f"## {cand}", "",
                  f"- Episodes, raw R (frozen grader): {_summary([g['raw'] for _, g in ep_rows])}",
                  f"- Episodes, cost-adjusted R: {_summary([g['adj'] for _, g in ep_rows])}",
                  f"- Episodes, cost-adjusted R at {SPREAD_SENS} pips and rates 1 point worse: "
                  f"{_summary([g['adj'] for g in sens])}",
                  f"- All graded fires ({len(all_rows)}): mean spread cost "
                  f"{statistics.fmean([g['spread_r'] for g in all_rows]) if all_rows else 0:.3f}R, mean financing "
                  f"{statistics.fmean([g['fin_r'] for g in all_rows]) if all_rows else 0:+.3f}R, mean nights "
                  f"{statistics.fmean([g['nights'] for g in all_rows]) if all_rows else 0:.1f}",
                  "", "| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r, g in ep_rows:
            lines.append(f"| {r['timestamp'][:16]} | {r['instrument']} | {g['direction']} | {g['risk_pips']:.0f} | "
                         f"{g['nights']} | {g['raw']:+.2f} | {-g['spread_r']:+.3f} | {g['fin_r']:+.3f} | {g['adj']:+.3f} |")
        lines.append("")
    lines.insert(4, f"Positive control: {reproduced} graded rows; every raw R reproduced from freshly fetched "
                    f"H4 bars to 2 dp (a mismatch would have aborted the run).")
    lines.insert(5, "")
    text = "\n".join(lines)
    with open(report, "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    elif sys.argv[1] == "run":
        run(sys.argv[2])
    else:
        sys.exit(__doc__)
