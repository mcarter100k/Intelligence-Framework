# Spec: weekend-session candles in the OANDA STUDY data (PROPOSED — not approved, not built)

**Status:** PROPOSED 2026-10-22 for owner/team review, per the owner's
2026-10-22 ruling: "first report how the live path handles them today (file
and line). The study must apply the identical treatment. If live has no
explicit rule, propose folding into the following Monday (Sunday open,
combined high/low, Monday close) as a spec change for team review. Don't
implement either way until I approve." **Nothing here is implemented.**

---

## 1. How the live path handles weekend candles today: no explicit rule

| Where | What it does |
|---|---|
| `oanda_feed.py:249-251` (`_get_bars`) | Drops only candles with `complete=false`. There is no weekday filter, so a weekend candle, if OANDA served one, would reach every indicator as an ordinary bar. |
| `regime_detection.py:750-755` (`is_trading_day`) | The one trading calendar: Saturday and Sunday are not trading days. It is used for market status (`regime_detection.py:778-787`) and for D1 staleness (`decision_brief.py:461-463`), not to filter bars. |
| `shadow_signals.py:395-413` (`_h4_bar_opens`) | Builds the H4 bar index from that calendar, so it has no weekend slots. A time inside a weekend would map, by `bisect`, onto the preceding Friday's last bar. |

**The live feed serves none.** There are 0 weekend-session candles in the
30,810 cached OANDA bars for 2022-05-31 → 2026-09-10 (`studies/data_cache/`),
and 0 in the 2021-04-27 → 2021-12-31 remainder (2026-10-20 depth check). The
live rule is therefore "never encountered". The two places that model
weekends at all disagree: the feed would include such a candle, while the
calendar and the H4 index say it does not exist. There is no identical
treatment to copy, so this spec proposes one.

## 2. What the STUDY data contains (timestamps only, 2005–2013)

Two different kinds of weekend-session candle exist. A session's trading
day is the New York date of (open + 7 h).

| Kind | Session | Typical H4 opens (NY) | D1 candles per year, GBP_AUD / GBP_JPY |
|---|---|---|---|
| **Sunday-session** | Sat 17:00 → Sun 17:00 NY | Sun 13:00 (≈420 of them), Sun 09:00 (125–151); fewer at other hours | 51–53 / 50–53 a year 2005–2012; 5 in 2013 |
| **Saturday-session** | Fri 17:00 → Sat 17:00 NY | Fri 17:00 (≈250), i.e. Friday after-close quotes | 21–47 / 18–48 a year 2005–2012; 9 in 2013 |

- 429 weekends per pair carry at least one weekend candle. The most in one
  weekend is 2 D1 and 12 H4.
- **2011 is anomalous:** about 233 Saturday-session and about 260
  Sunday-session H4 candles per pair, i.e. near-continuous weekend quoting.
- These are counts of candles that exist, not anything about prices.

## 3. Proposal A (the owner's): fold Sunday-session candles into the following Monday

- **D1:** Monday′ = open of the Sunday-session candle; high = max(Sunday-session
  high, Monday high); low = min of the two lows; close = Monday close.
- **H4:** every Sunday-session H4 candle folds into Monday's first H4 slot
  (17:00 NY Sunday). Open = the earliest folded candle's open; high/low
  combined; close = that slot's close. If the 17:00 slot is missing, they
  fold into the first Monday H4 that exists.
- **No Monday session** (a Monday Dec 25 or Jan 1): fold into the next
  trading session.
- The folded series has no weekend rows. D1 counts become the weekday counts
  already measured (259–262 a year), and H4 stays 6 per full session.

## 4. Open question the ruling does not settle: Saturday-session candles

Saturday-session candles start at Friday 17:00 NY. They are quotes after
Friday's close, not a Sunday open. Options:

- **(A′) Fold them into the following Monday too** (the literal rule). Monday's
  open becomes a Friday-evening price, and the weekend gap disappears into
  Monday's range.
- **(B) Drop them.** This matches what the live feed shows for that period
  today, which is nothing; the market is closed from Fri 17:00 to Sun 17:00 NY.
  Friday's close and Monday's open stay as the modern convention builds them.
- **(C) Fold them into the preceding Friday.** This changes Friday's close,
  the anchor of every daily indicator. Not recommended.

**Recommendation: (B) for Saturday-session candles.** Note that the same
argument would also support dropping Sunday-session candles: modern
sessions open at 17:00 Sunday, so pre-open quotes do not exist in live
data. Folding them (Proposal A) keeps pre-open moves inside Monday's
range; dropping them makes Monday bars match the modern construction
exactly. Both are defensible. The choice must be made before any STUDY
statistic exists, and it applies identically to every candidate.

## 5. Consequences for the gate

- §3 items 1, 2 and 4 do not depend on the rule. Item 4's baseline excludes
  Mondays, and its four dates fall on Thursdays and a Friday
  (data_map_spec §11.4).
- §3 item 3 must be re-run on Monday sessions of the converted series once
  a rule is approved and built. Tuesday–Friday sessions are untouched by
  any option.
- **Implementation (after approval only):** a study-side conversion function
  under `studies/`, with tests that pin each case (Sunday-only,
  Saturday-only, both, 2011-style continuous weekends, holiday Monday).
  The live path is unaffected, since it never receives weekend candles.
