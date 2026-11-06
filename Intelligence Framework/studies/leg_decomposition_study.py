"""Currency-leg decomposition and pair correlation: implements
docs/specs/leg_decomposition_study_spec.md (frozen at 671033a, before this file
existed) and nothing else. Descriptive and risk only: no trading rule, no
change to risk_config.

usage: python3 -I leg_decomposition_study.py <cross_archive_dir> <leg_archive_dir>

No network. Reads the two research archives through research_archive.load
(hash-checked, SEALED refused). Stdout is the report body.
"""
import hashlib
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from statistics import NormalDist

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_convert as C  # noqa: E402
import research_archive as A  # noqa: E402

UTC = timezone.utc
PERIODS = ("STUDY", "USED", "FORWARD")
MAIN = ("GBP_AUD", "GBP_JPY", "GBP_USD", "AUD_USD", "USD_JPY")
CROSSES = ("GBP_AUD", "GBP_JPY")
OWN_LEG = {"GBP_AUD": "AUD_USD", "GBP_JPY": "USD_JPY"}
GOLD_START = date(2006, 3, 21)
MANIFESTS = {
    "cross": "4af4983e5f986dbd86fed8420f0b87db19c8b4fdca62b26ab24037aeed893f87",
    "legs": "e66eaf44d51b691adf4802aafd8980f56dc90d10035ac22848484f9c680edcc1",
}
ID_CORR_MIN, ID_MEDIAN_BP_MAX, ID_BIG_BP = 0.999, 1.0, 10.0
MIN_WEEK_DAYS = 3
N_FLOOR = 20
LAG_CELLS = 6
ALPHA_LAG = 1 - 0.95 ** (1 / LAG_CELLS)
RHO_ONE, RHO_INDEP = 0.7, 0.3


# ── pure helpers (pinned by tests/test_leg_decomposition_study.py) ───────────

def reconstruct(pair, r):
    """Cross return implied by the USD legs (§4 identity)."""
    if pair == "GBP_AUD":
        return r["GBP_USD"] - r["AUD_USD"]
    if pair == "GBP_JPY":
        return r["GBP_USD"] + r["USD_JPY"]
    raise ValueError(pair)


def aligned(closes, insts):
    common = set.intersection(*(set(closes[i]) for i in insts))
    return sorted(common)


def daily_returns(closes, insts, dates):
    return {i: np.log(np.array([closes[i][t] for t in dates[1:]]) /
                      np.array([closes[i][t] for t in dates[:-1]])) for i in insts}


def weekly(returns, ret_dates, min_days=MIN_WEEK_DAYS):
    """Sum daily returns by ISO week of the session day. Returns
    (weekly returns {inst: array}, weekly realised vol {inst: array}, excluded weeks)."""
    groups = defaultdict(list)
    for k, t in enumerate(ret_dates):
        groups[C.session_day(t).isocalendar()[:2]].append(k)
    keep = [w for w in sorted(groups) if len(groups[w]) >= min_days]
    wr = {i: np.array([returns[i][groups[w]].sum() for w in keep]) for i in returns}
    rv = {i: np.array([math.sqrt((returns[i][groups[w]] ** 2).sum()) for w in keep]) for i in returns}
    return wr, rv, len(groups) - len(keep)


def ols(y, *xs):
    X = np.column_stack([np.ones(len(y)), *xs])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sst = ((y - y.mean()) ** 2).sum()
    return beta, resid, 1 - (resid ** 2).sum() / sst


def corr_ci(x, y):
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1])
    if n <= 3:
        return r, float("nan"), float("nan"), n
    if abs(r) >= 0.999999:
        return r, r, r, n
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return r, math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se), n


def f2_sf(f, d2):
    """Exact P(F(2, d2) > f) = (d2 / (d2 + 2 f)) ** (d2 / 2)."""
    return (d2 / (d2 + 2 * f)) ** (d2 / 2)


def lag_test(y, x1, x2):
    """r_y(t) on x1(t-1), x2(t-1): (b1, b2, F, p, R2, N)."""
    yy, a, b = y[1:], x1[:-1], x2[:-1]
    beta, resid, r2 = ols(yy, a, b)
    n = len(yy)
    ssr_u = (resid ** 2).sum()
    ssr_r = ((yy - yy.mean()) ** 2).sum()
    d2 = n - 3
    f = ((ssr_r - ssr_u) / 2) / (ssr_u / d2)
    return float(beta[1]), float(beta[2]), float(f), f2_sf(f, d2), float(r2), n


def identity_check(actual, recon):
    res_bp = np.abs(actual - recon) * 1e4
    corr = float(np.corrcoef(actual, recon)[0, 1])
    shifted = float(np.corrcoef(actual[1:], recon[:-1])[0, 1])
    med = float(np.median(res_bp))
    return {"corr": corr, "median_bp": med, "p99_bp": float(np.percentile(res_bp, 99)),
            "max_bp": float(res_bp.max()), "over_10bp": int((res_bp > ID_BIG_BP).sum()),
            "shifted_corr": shifted, "pass": corr >= ID_CORR_MIN and med <= ID_MEDIAN_BP_MAX, "n": len(actual)}


def stress_mask(measure):
    thr = statistics.quantiles(list(measure), n=5, method="inclusive")[3]
    return measure >= thr


def risk_verdict(rho, n):
    if n < N_FLOOR:
        return "INSUFFICIENT (no verdict)"
    if rho >= RHO_ONE:
        return "JUSTIFIED (count as one position)"
    if rho <= RHO_INDEP:
        return "OVER-CONSERVATIVE (costs a position slot for no reason)"
    return f"BETWEEN — effective independent positions 2/(1+ρ) = {2 / (1 + rho):.2f}; ruling is the team's"


def fmt_ci(c):
    r, lo, hi, n = c
    tag = " INSUFFICIENT" if n < N_FLOOR else ""
    return f"{r:+.3f} [{lo:+.3f}, {hi:+.3f}] (N {n}{tag})"


# ── run ──────────────────────────────────────────────────────────────────────

def _closes(arc, inst, period, start=None):
    bars = A.load(arc, inst, "D", {period})
    return {t: v[3] for t, v in bars.items() if start is None or C.session_day(t) >= start}


def run(cross_arc, leg_arc):
    print(f"run start (UTC): {datetime.now(UTC).isoformat(timespec='seconds')}")
    for key, arc in (("cross", cross_arc), ("legs", leg_arc)):
        with open(os.path.join(arc, "manifest.json"), "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != MANIFESTS[key]:
            raise SystemExit(f"manifest hash mismatch: {key}")
        print(f"manifest {key}: OK")
    print(f"first computation start (UTC): {datetime.now(UTC).isoformat(timespec='seconds')}")

    data = {}
    print("\n## 1. Identity check (positive control; §4)\n")
    print("| period | pair | N days | corr(actual, reconstructed) | median \\|res\\| bp | p99 bp | max bp "
          "| days > 10 bp | corr with legs shifted 1 date | result |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    ok = True
    for p in PERIODS:
        closes = {i: _closes(leg_arc if i not in CROSSES else cross_arc, i, p) for i in MAIN}
        dates = aligned(closes, MAIN)
        r = daily_returns(closes, MAIN, dates)
        excluded_dates = {i: len(closes[i]) - len(dates) for i in MAIN}
        data[p] = (r, dates[1:], excluded_dates)
        for pair in CROSSES:
            ic = identity_check(r[pair], reconstruct(pair, r))
            ok &= ic["pass"]
            print(f"| {p} | {pair} | {ic['n']} | {ic['corr']:.6f} | {ic['median_bp']:.3f} | {ic['p99_bp']:.2f} | "
                  f"{ic['max_bp']:.2f} | {ic['over_10bp']} | {ic['shifted_corr']:+.4f} | "
                  f"{'PASS' if ic['pass'] else 'FAIL'} |")
    print("\nD1 bars not in the aligned set, per period: "
          + "; ".join(f"{p} {data[p][2]}" for p in PERIODS))
    if not ok:
        print("\nIDENTITY CHECK FAILED — stopping before any question (§4).")
        sys.exit(1)

    print("\n## 2. Q1 and Q2: share of each cross explained by one leg (daily R²)\n")
    print("| period | pair | N days | Q1 R² on GBP/USD | Q2 R² on own leg (own leg) |")
    print("|---|---|---|---|---|")
    q1 = {}
    for p in PERIODS:
        r = data[p][0]
        for pair in CROSSES:
            _, _, r2g = ols(r[pair], r["GBP_USD"])
            _, _, r2o = ols(r[pair], r[OWN_LEG[pair]])
            q1[(p, pair)] = r2g
            print(f"| {p} | {pair} | {len(r[pair])} | {r2g:.3f} | {r2o:.3f} ({OWN_LEG[pair]}) |")

    print("\n## 3. Q3, Q4, Q5: how the two crosses move together\n")
    print("Q4 is the remaining link after the GBP/USD component is removed, **which includes the US dollar** (§5).\n")
    print("| period | Q3 weekly corr, all weeks | Q4 daily residual corr | Q5 weekly corr, stress weeks "
          "| Q5 weekly residual corr, stress weeks | weeks excluded (< 3 days) |")
    print("|---|---|---|---|---|---|")
    res = {}
    for p in PERIODS:
        r, rd, _ = data[p]
        _, ea, _ = ols(r["GBP_AUD"], r["GBP_USD"])
        _, ej, _ = ols(r["GBP_JPY"], r["GBP_USD"])
        q4 = corr_ci(ea, ej)
        wr, rv, excl = weekly(r, rd)
        q3 = corr_ci(wr["GBP_AUD"], wr["GBP_JPY"])
        m = stress_mask((rv["GBP_AUD"] + rv["GBP_JPY"]) / 2)
        q5 = corr_ci(wr["GBP_AUD"][m], wr["GBP_JPY"][m])
        if m.sum() > 3:
            _, wa, _ = ols(wr["GBP_AUD"][m], wr["GBP_USD"][m])
            _, wj, _ = ols(wr["GBP_JPY"][m], wr["GBP_USD"][m])
            q5r = corr_ci(wa, wj)
        else:
            q5r = (float("nan"), float("nan"), float("nan"), int(m.sum()))
        res[p] = (q3, q4, q5, q5r)
        print(f"| {p} | {fmt_ci(q3)} | {fmt_ci(q4)} | {fmt_ci(q5)} | {fmt_ci(q5r)} | {excl} |")

    print("\n## 4. Risk verdict (§8; ρ = Q5 weekly cross-to-cross correlation in stress weeks)\n")
    print("| period | ρ | stress weeks | verdict |")
    print("|---|---|---|---|")
    verdicts = {}
    for p in PERIODS:
        rho, _, _, n = res[p][2]
        verdicts[p] = risk_verdict(rho, n)
        print(f"| {p} | {rho:+.3f} | {n} | {verdicts[p]} |")
    decided = {p: v.split(" ")[0] for p, v in verdicts.items() if not v.startswith("INSUFFICIENT")}
    print("\nStability across periods with a verdict: "
          + ("SAME" if len(set(decided.values())) <= 1 else "DIFFERS — a stability finding (§8)")
          + f" ({', '.join(f'{p} {v}' for p, v in decided.items())})")

    print("\n## 5. Phase 3: do yesterday's leg returns predict today's cross return? (§6)\n")
    print(f"Šidák α for {LAG_CELLS} cells: {ALPHA_LAG:.4f}\n")
    print("| period | pair | N | b(GBP/USD t−1) | b(own leg t−1) | F | p | predictive R² | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    for p in PERIODS:
        r = data[p][0]
        for pair in CROSSES:
            b1, b2, f, pv, r2, n = lag_test(r[pair], r["GBP_USD"], r[OWN_LEG[pair]])
            v = ("NO LEAD DETECTED" if pv >= ALPHA_LAG
                 else "LEAD DETECTED — RECORDED AS A HYPOTHESIS ONLY")
            print(f"| {p} | {pair} | {n} | {b1:+.4f} | {b2:+.4f} | {f:.3f} | {pv:.4f} | {r2:.4f} | {v} |")

    print("\n## 6. G1: gold (weekly correlation with each cross; descriptive, §7)\n")
    print("| period | corr(GBP/AUD, XAU/USD) | corr(GBP/JPY, XAU/USD) |")
    print("|---|---|---|")
    for p in PERIODS:
        closes = {"GBP_AUD": _closes(cross_arc, "GBP_AUD", p), "GBP_JPY": _closes(cross_arc, "GBP_JPY", p),
                  "XAU_USD": _closes(leg_arc, "XAU_USD", p, start=GOLD_START if p == "STUDY" else None)}
        insts = ("GBP_AUD", "GBP_JPY", "XAU_USD")
        dates = aligned(closes, insts)
        wr, _, _ = weekly(daily_returns(closes, insts, dates), dates[1:])
        print(f"| {p} | {fmt_ci(corr_ci(wr['GBP_AUD'], wr['XAU_USD']))} | "
              f"{fmt_ci(corr_ci(wr['GBP_JPY'], wr['XAU_USD']))} |")

    print("\n## 7. The requester's expected result (§9)\n")
    print("| period | Q1 R² ≥ 0.5 both pairs | 0.3 < Q3 < 0.7 | \\|Q4\\| ≤ 0.1 |")
    print("|---|---|---|---|")
    for p in PERIODS:
        q3, q4 = res[p][0], res[p][1]
        a = "MET" if all(q1[(p, x)] >= 0.5 for x in CROSSES) else "NOT MET"
        b = ("n/a (INSUFFICIENT)" if q3[3] < N_FLOOR else ("MET" if 0.3 < q3[0] < 0.7 else "NOT MET"))
        c = "MET" if abs(q4[0]) <= 0.1 else "NOT MET"
        print(f"| {p} | {a} | {b} | {c} |")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    run(sys.argv[1], sys.argv[2])
