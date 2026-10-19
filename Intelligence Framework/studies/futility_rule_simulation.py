"""
futility_rule_simulation.py — design calculation for the futility checkpoint
(docs/specs/futility_rule_spec.md). Synthetic R only: it reads no ledger
and no candidate's results.

Question: if a candidate's TRUE mean R is m, how often is the 90% one-sided
percentile-bootstrap UPPER bound on its observed mean below +0.15R (the
futility condition) at N = 15, 20 and 30 independent episodes?
  m = +0.15 : the rule should rarely fire (nominal 10%); firing = wrongly
              retiring a candidate with exactly the minimum edge.
  m = +0.30 : firing = retiring a real edge.
  m = -0.20 : firing = correctly retiring a loser (the rule's power).

Two R shapes, both right-skewed like stop-limited trades:
  stop/winner : -1R (stopped) or +2.5R, nearly binary
  floored     : normal, SD 1.2R, floored at -1R

Bootstrap: 2,000 resamples per bound (power_check uses 10,000; 2,000 keeps
3,000 simulations per cell tractable). Seed 11.

Usage: python3 studies/futility_rule_simulation.py
"""
import random
import statistics as st

SIMS, ITERS, SEED = 3000, 2000, 11


def upper_bound(rs, rng, conf=0.90):
    means = sorted(st.fmean(rng.choices(rs, k=len(rs))) for _ in range(ITERS))
    return means[int(conf * ITERS) - 1]


def stop_or_winner(mu, rng):
    win = 2.5
    return win if rng.random() < (mu + 1) / (win + 1) else -1.0


def floored_normal(mu, rng):
    return max(-1.0, rng.gauss(mu, 1.2))


def main():
    rng = random.Random(SEED)
    print("P(futility fires) = P(90% upper bound on mean R < +0.15R)")
    for name, gen in (("stop/winner (-1 or +2.5R)", stop_or_winner),
                      ("normal SD 1.2R floored at -1R", floored_normal)):
        for mu in (0.15, 0.30, -0.20):
            cells = []
            for n in (15, 20, 30):
                hits = sum(upper_bound([gen(mu, rng) for _ in range(n)], rng) < 0.15
                           for _ in range(SIMS))
                cells.append(f"N={n}: {hits / SIMS:5.1%}")
            print(f"  {name:30s} true mean {mu:+.2f}R  " + "  ".join(cells))


if __name__ == "__main__":
    main()
