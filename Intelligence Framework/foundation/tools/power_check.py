"""
power_check.py — can this sample size actually tell an edge from zero?

The framework's original gates (FLAG at N=30, DECISION at N=60, pass at
avg R >= +0.15) turned out to be coin flips: at N=60 with a per-trade SD of
1.2R, a true +0.15R edge is detected only ~25% of the time and a zero-edge
strategy "passes" ~17% of the time. Run this BEFORE committing to a gate.

Usage:
  python power_check.py --edge 0.15 --sd 1.2 --n 60        # power at N
  python power_check.py --edge 0.15 --sd 1.2 --power 0.8   # N required
  python power_check.py --sd 1.2 --n 60                    # smallest detectable edge
  python power_check.py --rs -1 -1 2.3 -0.5 1.1 ...        # bootstrap CI on observed R

One-sided test, normal approximation. Standard library only.
"""
from __future__ import annotations

import argparse
import math
import random
from statistics import NormalDist, mean, median, stdev

_Z = NormalDist()


def power_at_n(edge: float, sd: float, n: int, alpha: float = 0.05) -> float:
    """P(reject 'edge <= 0') when the true mean R is `edge`."""
    z_crit = _Z.inv_cdf(1 - alpha)
    return 1 - _Z.cdf(z_crit - edge / (sd / math.sqrt(n)))


def n_required(edge: float, sd: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Independent episodes needed to detect `edge` with the given power."""
    z = _Z.inv_cdf(1 - alpha) + _Z.inv_cdf(power)
    return math.ceil((z * sd / edge) ** 2)


def min_detectable_edge(sd: float, n: int, power: float = 0.8, alpha: float = 0.05) -> float:
    return (_Z.inv_cdf(1 - alpha) + _Z.inv_cdf(power)) * sd / math.sqrt(n)


def false_pass_rate(threshold: float, sd: float, n: int) -> float:
    """P(observed avg R >= threshold) when the true edge is ZERO."""
    return 1 - _Z.cdf(threshold / (sd / math.sqrt(n)))


def bootstrap_lower_bound(rs: list[float], conf: float = 0.90,
                          iters: int = 10_000, seed: int = 7) -> float:
    """One-sided lower confidence bound on mean R by percentile bootstrap."""
    rng = random.Random(seed)
    n = len(rs)
    means = sorted(mean(rng.choices(rs, k=n)) for _ in range(iters))
    return means[int((1 - conf) * iters)]


def _report_observed(rs: list[float]) -> None:
    n = len(rs)
    print(f"N (independent episodes)      : {n}" + ("   INSUFFICIENT (<20)" if n < 20 else ""))
    print(f"avg R / median R              : {mean(rs):+.3f} / {median(rs):+.3f}")
    if n >= 2:
        print(f"SD of R                       : {stdev(rs):.3f}")
    best = max(rs)
    rest = [r for r in rs if r != best] or [0.0]
    print(f"avg R without best episode    : {mean(rest):+.3f}"
          + ("   <- outlier-driven" if mean(rs) > 0 >= mean(rest) else ""))
    if n >= 5:
        print(f"90% one-sided lower bound     : {bootstrap_lower_bound(rs):+.3f}"
              "   (edge claimed only if > 0)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edge", type=float, help="true mean R to detect (e.g. 0.15)")
    ap.add_argument("--sd", type=float, default=1.2, help="per-episode SD in R (1.2 typical; ~2.0 for fat-tailed trend exits)")
    ap.add_argument("--n", type=int, help="independent episodes")
    ap.add_argument("--power", type=float, help="target power (e.g. 0.8)")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--threshold", type=float, help="pass threshold on avg R, for false-pass rate")
    ap.add_argument("--rs", type=float, nargs="+", help="observed per-episode R values")
    a = ap.parse_args()

    if a.rs:
        _report_observed(a.rs)
        return
    if a.edge and a.power:
        print(f"N required: {n_required(a.edge, a.sd, a.power, a.alpha)} independent episodes "
              f"(edge {a.edge:+}R, SD {a.sd}R, power {a.power:.0%}, alpha {a.alpha})")
    elif a.edge and a.n:
        print(f"Power: {power_at_n(a.edge, a.sd, a.n, a.alpha):.0%} "
              f"(edge {a.edge:+}R, SD {a.sd}R, N={a.n})")
    elif a.n:
        print(f"Smallest edge detectable at 80% power: {min_detectable_edge(a.sd, a.n):+.2f}R "
              f"(SD {a.sd}R, N={a.n})")
    if a.threshold is not None and a.n:
        print(f"Zero-edge false-pass rate at avg R >= {a.threshold:+}: "
              f"{false_pass_rate(a.threshold, a.sd, a.n):.0%}")


if __name__ == "__main__":
    main()
