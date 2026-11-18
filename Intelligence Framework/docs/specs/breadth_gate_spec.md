# Spec: the breadth go/no-go gate (bands RULED 2026-11-06; definitions 1–2 RULED 2026-11-17, definition 3 awaiting ruling)

**Owner rulings, 2026-11-17 (recorded verbatim in substance):**
- **L5:** ruling C3 (§3) governs, not the 2026-11-17 brief's "> 0.20
  NO-GO, stop". The weekly ρ̄ is a screen, not a verdict.
- **L8:**
  - definition 1 (the mean of |ρ|, signed mean beside it) ACCEPTED;
  - definition 2 (the verdict on the larger of the STUDY and USED ρ̄)
    ACCEPTED;
  - definition 3 (the weekly construction) is to be stated for a ruling. It
    is stated in full in §4 item 3 below.

**Status:**
- The three bands below are the team's ruling of 2026-11-06, recorded
  verbatim. They are committed before any universe data exists for
  measurement.
- Three definitions the ruling did not fix are PROPOSED in §4 for the team
  to confirm with the universe and partition rulings.
- **Nothing is measured until those rulings are given** (`docs/breadth_universe_request.md`).

## 1. The gate (ruled)

ρ̄ is the average pairwise correlation across the breadth universe (proxy:
§3).

| ρ̄ | Verdict |
|---|---|
| ρ̄ ≤ 0.11 | **GO.** Breadth closes the gap at 10 pairs. |
| 0.11 < ρ̄ ≤ 0.20 | **PARTIAL.** Report the pair count that would be needed, and whether it is reachable. |
| ρ̄ > 0.20 | **NO-GO.** Breadth is refuted as a strategy; the team needs a different answer. |

**Why it is the decision point (the ruling's arithmetic, reproduced):**
effective episodes = n·k ÷ (1 + (k − 1)·ρ̄), with n = 10.7 episodes a year ×
7.30 exam years = 78.1 per instrument. As k grows, this tends to n ÷ ρ̄
whatever the number of instruments:

| ρ̄ | Ceiling (episodes over the exam) |
|---|---|
| 0.10 | 781 |
| 0.15 | 521 |
| 0.20 | 391, below the 396 needed for +0.15R at one-sided α 0.05 |

Break-even ρ̄:

| Universe | Break-even ρ̄ |
|---|---|
| 10 pairs | ≤ 0.108 |
| 20 pairs | ≤ 0.155 |

## 2. Two arithmetic notes for the team (not changes to the ruling)

1. **The GO boundary is rounded.** At exactly ρ̄ = 0.11 and 10 pairs, the
   effective count is 392.5, just short of 396. The exact 10-pair break-even
   is 0.108. A measured ρ̄ between 0.108 and 0.110 would read GO while falling
   about 1% short. It is recorded so that case is not argued afterwards.
2. **The bands assume one-sided α 0.05.** At the α 0.01 that FCS-1 used,
   +0.15R needs 643 episodes:
   - the 10-pair break-even becomes ρ̄ ≤ 0.024;
   - the 20-pair break-even becomes ρ̄ ≤ 0.075;
   - the ρ̄ = 0.10 ceiling (781) still clears it.
   
   They also assume 10.7 episodes a year per instrument. The frozen cells
   ranged from 4.3 to 27.3.

## 3. The proxy, and what it cannot settle (ruled, C3)

- **What the formula needs:** the correlation of **episode outcomes**: R of
  trades that overlap in time.
- **What is measured instead:** the correlation of **weekly log returns**.
  Trades that do not overlap in time are independent however the prices
  move, so return correlation is typically an upper bound on outcome
  correlation, and often a loose one.
- **It is not a theorem.** For two same-direction trades with stops and
  targets on correlated prices, outcome correlation is usually below return
  correlation, but no strict bound is proven here.
- **How it is read:**
  - ρ̄ (proxy) ≤ 0.11: **GO**, settled.
  - ρ̄ (proxy) > 0.11: **the proxy does not settle it.** The report states
    what the real measurement needs — one rule run across the universe,
    correlating only the R of contemporaneous episodes — and stops. A
    figure such as 0.25 is not a refutation.

## 4. Definitions PROPOSED for team confirmation (open until ruled)

1. **Sign: ρ̄ is the mean of |ρᵢⱼ|** over all pairs i < j, with the signed
   mean reported beside it.
   - *Why:* the candidates trade both directions. A short on one pair and a
     long on another, when the two are negatively correlated, gives
     positively correlated outcomes. A signed mean would let negative
     correlations cancel positive ones and understate the overlap.
2. **Period: the verdict uses the larger of the STUDY and USED ρ̄**
   (conservative). Both are reported, never pooled. FORWARD has too few
   weeks.
3. **Weeks (stated for the owner's ruling, L8):** the construction in
   `studies/leg_decomposition_study.py` (`aligned`, `daily_returns`,
   `weekly`):
   1. **Daily closes.** OANDA daily mid candles, aligned to the 17:00 New
      York day (gold's daily candles share that alignment: 22:00 UTC in
      winter).
   2. **Common dates only.** A date is used only if every instrument in the
      universe has a daily candle on it (the intersection).
   3. **Daily log return** = ln(close ÷ previous common date's close). A
      date missing for any one instrument (for example a metals holiday)
      drops out for all of them. The next return then spans the gap, for
      every instrument.
   4. **Session day** = the candle's time in New York plus 7 hours, as a
      date: the trading date of `_market_status`.
   5. **Weekly return** = the sum of the daily log returns whose session
      days fall in the same ISO week (Monday–Sunday).
   6. **Thin weeks dropped.** Weeks with fewer than 3 daily returns are
      excluded.
   7. **The correlations.** Pearson correlation of the weekly returns for
      each pair of instruments, per era. ρ̄ = the mean of |ρ| (definition
      1), and the verdict uses the larger era (definition 2).
   - **Open choices within it, for the ruling:**
     - (a) keep the gap-spanning returns of step 3, or drop them;
     - (b) whether the 3-day minimum of step 6 stands.

## 5. Sequence (ruled, C4)

1. Universe ruling.
2. Partition ruling, with every new pair's 2014–2021 span sealed before it
   is fetched.
3. Fetch and verify.
4. Measure.
5. Stop and report.

M40 governs throughout. No sealed-exam bar is fetched, counted or opened
for any instrument. Choosing the first rule to test is the proposal's
decision 6 and stays open.
