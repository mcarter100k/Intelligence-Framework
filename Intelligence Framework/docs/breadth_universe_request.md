# Ruling request: the breadth universe and its partition (2026-11-06)

**Rulings received 2026-11-17 (owner):**
- **Universe:**
  - amendment (a), pegs count as their anchor, ACCEPTED;
  - **L6:** same-anchor pairs dropped (EUR_DKK, USD_HKD);
  - **EUR_CHF dropped.** The SNB floor distorts STUDY, and the January 2015
    break lies inside the sealed exam;
  - **SGD capped at two pairs;**
  - **gold added,** with any non-FX instrument the owner could reach.
    - On this account there are none: all 68 instruments are currencies
      (broker probe, 2026-11-17).
    - Gold itself is not tradeable on the account (404
      `INSTRUMENT_NOT_TRADEABLE`).
- **Partition, L7:** new pairs take the existing partition boundaries
  exactly (§4's proposed text).
- **Not yet done:** the universe re-selection under these rules.
  - The 68-pair spread table of §1 was never stored. Only the pairs that
    mattered were recorded.
  - Re-selection therefore needs a fresh read-only spread probe.
  - The weekly construction was ruled 2026-11-17 (N1;
    `breadth_gate_spec.md` §4 item 3). Nothing ruled now stands between
    the probe and the measurement.
- **Ruling M1 (2026-11-17)** stops the GBP pairs' live jobs and alerts. It
  does not remove GBP/AUD or GBP/JPY from this research universe.

**For the team.** These are steps 1 and 2 of the gate sequence
(`docs/specs/breadth_gate_spec.md` §5). Nothing for the new pairs has been
fetched beyond the spread measurement below, and nothing has been measured.
**Two rulings are needed before any fetch.**

## 1. Real spreads (account data, 2026-11-06)

Source: `studies/universe_spread_probe.py`, read-only, run through
`reality_run.py` (exit 0, stderr empty, project unchanged).
- **What was taken:** bid/ask H1 closes for all 68 currency pairs on the
  account, over the last 20 weekday sessions (2026-10-07 → 2026-11-06 UTC).
- **What was kept:** only the spread. **Prices were discarded on receipt.**
  No 2014–2021 bar was requested for any pair.

Spreads of the pairs that matter here (median of H1 closes; the full
68-pair table is in the run output, validation_log 2026-11-06):

| Pair | Median spread, pips | Basis points of price | London/NY hours, pips |
|---|---|---|---|
| GBP_AUD | 5.10 | 2.68 | 4.90 |
| GBP_JPY | 3.50 | 1.65 | 3.40 |

**Cost finding:**
- **GBP/AUD's real median spread is 5.1 pips** (4.9 in London/New York
  hours).
- The framework assumes 3.0 pips in studies (`data_map_spec` §4, 2021
  onward) and 4.0 in execution tools (`risk_config` `HARD_LIMITS`).
- GBP/JPY's 3.5 is close to its assumed 3.0.

This window is one month. It is not a re-grading of any study, and the team
should decide whether the cost assumptions need a dated amendment.

## 2. The ruled criteria, applied literally

The criteria, in this order:
1. at most 3 pairs per currency;
2. crosses before USD pairs;
3. lowest spread in basis points of price;
4. cap 10, with GBP/AUD and GBP/JPY included;
5. pairs examined for edge excluded (GBP_USD, AUD_USD, USD_JPY, whose
   lagged returns were tested as predictors on 2026-11-05).

| # | Pair | Spread, pips | bp |
|---|---|---|---|
| 1 | GBP_AUD | 5.10 | 2.68 |
| 2 | GBP_JPY | 3.50 | 1.65 |
| 3 | HKD_JPY | 24.80 | 1.23 |
| 4 | EUR_HKD | 13.60 | 1.55 |
| 5 | EUR_JPY | 2.80 | 1.58 |
| 6 | EUR_DKK | 12.00 | 1.61 |
| 7 | GBP_HKD | 16.80 | 1.61 |
| 8 | CAD_SGD | 1.90 | 2.08 |
| 9 | AUD_NZD | 2.70 | 2.17 |
| 10 | SGD_CHF | 1.50 | 2.34 |

Currency count:

| AUD | CAD | CHF | DKK | EUR | GBP | HKD | JPY | NZD | SGD |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 1 | 1 | 3 | 3 | 3 | 3 | 1 | 2 |

The limit of 3 is met.

### This list defeats the ruling's purpose: rule 5 (stop and report)

**Four of the eight new pairs contain a pegged currency:**
- **HKD is held to the US dollar** (USD/HKD trades inside 7.75–7.85).
  - HKD_JPY behaves as USD_JPY, and EUR_HKD as EUR_USD.
  - **GBP_HKD behaves as GBP_USD, a pair the ruling excludes as already
    examined.**
  - These are dollar pairs in disguise. The ruling prefers crosses because
    the dollar cancels in them; in an HKD "cross" it does not.
- **DKK is held to the euro,** so EUR_DKK barely moves. It ranks well on
  spread as a share of price precisely because it does not move. It would
  produce almost no trades, and its spread would be large against its range.

The cause is that criterion 2 tests for the letters "USD", and criterion 3
measures cost against price rather than against movement. Neither choice
was wrong in itself, but together they select pegs.

## 3. Ruling 1 requested: the universe

**Proposed amendments, for the team to accept, change or reject:**
- **(a) Pegs count as their anchor.** HKD counts as USD and DKK as EUR, both
  in the currency cap and in the cross test.
- **(b) Same-anchor pairs are dropped.** EUR_DKK and USD_HKD go.
- **(c) Optional, later:** rank by spread relative to typical movement
  (spread ÷ H4 average range) instead of basis points of price. That needs
  each pair's price ranges, so it can only follow the partition ruling.

**Illustration under (a) and (b):** the same tested selection function, run
on the same spreads; no new data.

| # | Pair | Spread, pips | bp |
|---|---|---|---|
| 1 | GBP_AUD | 5.10 | 2.68 |
| 2 | GBP_JPY | 3.50 | 1.65 |
| 3 | EUR_JPY | 2.80 | 1.58 |
| 4 | SGD_JPY | 2.00 | 1.62 |
| 5 | EUR_GBP | 1.40 | 1.66 |
| 6 | EUR_CHF | 1.60 | 1.73 |
| 7 | CAD_SGD | 1.90 | 2.08 |
| 8 | AUD_NZD | 2.70 | 2.17 |
| 9 | SGD_CHF | 1.50 | 2.34 |
| 10 | AUD_CAD | 2.45 | 2.48 |

Currency count: GBP 3, AUD 3, JPY 3, EUR 3, SGD 3, CHF 2, CAD 2, NZD 1. All
ten pairs are true crosses.

**Two cautions on this list:**
- **SGD is a managed currency** (held to a basket band). Three of the ten
  pairs contain it.
- **EUR/CHF had a central-bank floor** at 1.20 from 2011-09-06 to 2015-01-15.
  About two of its nine STUDY years are a near-peg.

The team may want rule (a) to cover managed regimes too, or to exclude
EUR_CHF from STUDY-based measurement.

## 4. Ruling 2 requested: the partition (the proposal's decision 3, still open)

**Proposed text:** "The data map (§1, §11.2, §11.6) extends to the ruled
universe with identical spans and embargoes:
- STUDY: sessions 2005-01-01 → 2013-12-30;
- SEALED EXAM: 2014-01-02 → 2021-04-22, with embargoes at both edges;
- USED: 2021-04-27 → 2026-09-09;
- the 2026-09-10 boundary session in no span;
- FORWARD: 2026-09-11 onward.

Each new pair's SEALED EXAM span is sealed as of this ruling, before any of
its bars are fetched."

**What has been fetched for any pair outside the archive, as of this
request:**
- The 2026-11-01 instrument probe: first and latest daily candle for the
  USD legs only.
- This spread probe: one month of recent bid/ask, spreads only.

No 2014–2021 bar has been requested for any of them. The existing guard
refuses that block for every instrument, before sending and on receipt.

## 5. What happens after the two rulings

1. Fetch and verify the ruled pairs for STUDY, USED and FORWARD with the
   archive pipeline (`studies/leg_data.py` pattern).
2. Run the pre-registered ρ̄ measurement (`breadth_gate_spec.md`, with its §4
   definitions confirmed).
3. Report GO, PARTIAL or NO-GO, and stop.
