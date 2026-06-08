"""
glossary.py

Single source of truth for every term this framework uses.
Every label, every regime name, every signal type — defined here in plain English.

Rule: if a term appears in any printed output, it MUST be in TERMS.
      The test test_all_output_terms_in_glossary enforces this automatically.

Usage:
    from glossary import explain, TERMS
    print(explain("LONG"))
    print(explain("ADX"))
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# THE MASTER GLOSSARY
# Key   = the exact string that appears in framework output (case matters for
#         lookup, but explain() is case-insensitive)
# Value = plain-English definition (one or two sentences max)
# ─────────────────────────────────────────────────────────────────────────────

TERMS: dict[str, str] = {

    # ── Pair ──────────────────────────────────────────────────────────────────
    "GBP/AUD": (
        "The exchange rate between the British Pound and the Australian Dollar. "
        "The number tells you how many Australian dollars one British pound buys. "
        "If GBP/AUD = 2.03, one pound buys 2.03 Australian dollars."
    ),

    # ── Direction ─────────────────────────────────────────────────────────────
    "LONG": (
        "You are BUYING GBP/AUD. You profit when the price RISES after you buy. "
        "Plain English: 'I think the pound is going to get stronger against the aussie.'"
    ),
    "SHORT": (
        "You are SELLING GBP/AUD. You profit when the price FALLS after you sell. "
        "Plain English: 'I think the aussie is going to strengthen, or the pound weaken.'"
    ),
    "NO TRADE": (
        "The signals are not clear enough to justify risking money right now. "
        "Standing aside IS a decision — protecting capital is part of the edge."
    ),
    "BUY": "Same as LONG. You are purchasing GBP/AUD expecting the price to rise.",
    "SELL": "Same as SHORT. You are selling GBP/AUD expecting the price to fall.",

    # ── Grades ────────────────────────────────────────────────────────────────
    "A+": (
        "Everything aligned — trend, location, session, sweep, timing all agree. "
        "Maximum size (1.5% risk per trade). Rare — 1-2 times per week at most."
    ),
    "A": (
        "Strong setup. Most signals agree. One or two things could be better. "
        "Standard full size (1.0% risk). Let it run to target."
    ),
    "B+": (
        "Direction is clear but not everything is perfect. Valid trade. "
        "Standard size (0.5% risk). Manage it actively — don't set and forget."
    ),
    "B": (
        "Direction is there but real conflicts exist. Half size (0.25% risk). "
        "Tight stop required. Only take when B+ conditions are very close."
    ),
    "C": (
        "Too many factors working against you. DO NOT TRADE. "
        "Standing aside here IS your edge. Protecting capital is the job."
    ),

    # ── Conviction ────────────────────────────────────────────────────────────
    "conviction": (
        "A number from 0 to 100 measuring how strongly all signals agree. "
        "Think of it as a jury: 0 = completely divided, 100 = unanimous. "
        "High conviction means most of your evidence points the same direction."
    ),

    # ── Three tiers ───────────────────────────────────────────────────────────
    "structural_score": (
        "How aligned is the big picture — HTF trend, interest rates, COT, macro? "
        "This answers: 'Is the overall trend on my side?' Covers weeks to months."
    ),
    "tactical_score": (
        "How aligned is today's environment — currency strength, cross-market, leg decomp? "
        "This answers: 'Is today actually a good day to act on that big picture?'"
    ),
    "execution_score": (
        "How aligned is the exact timing — price levels, session, news, intraday fakeout? "
        "This answers: 'Is THIS the right moment to enter right now?'"
    ),
    "STRUCTURAL": "Big-picture signals covering weeks to months (HTF trend, rates, COT, macro).",
    "TACTICAL": "Medium-term signals covering hours to days (currency strength, cross-market).",
    "EXECUTION": "Timing signals covering minutes to hours (levels, session, news, intraday).",

    # ── HTF contexts ──────────────────────────────────────────────────────────
    "ESTABLISHED_UPTREND": (
        "Price has been rising for 5+ months AND rising the past 4 weeks. "
        "Both the big picture and the recent picture agree: the trend is UP. "
        "Look for opportunities to BUY on dips."
    ),
    "ESTABLISHED_DOWNTREND": (
        "Price has been falling for 5+ months AND falling the past 4 weeks. "
        "Both timeframes agree: the trend is DOWN. "
        "Look for opportunities to SELL on rallies."
    ),
    "PULLBACK_IN_UPTREND": (
        "Main trend is UP but price has dipped lower for the past 2-4 weeks. "
        "This dip is a BUYING OPPORTUNITY — the trend is still intact. "
        "Wait for the dip to find support, then buy."
    ),
    "COUNTER_TREND_BOUNCE": (
        "Main trend is DOWN but price has bounced UP recently. "
        "This bounce is temporary — the dominant direction is still down. "
        "Wait for the bounce to exhaust at resistance, then sell."
    ),
    "RANGING": (
        "No clear trend on either timeframe. Price is bouncing between levels. "
        "Trade the edges of the range. Avoid the middle. Do not trade breakouts here."
    ),
    "HH_HL": (
        "Higher High / Higher Low — each price peak and trough is higher than the last. "
        "This is the definition of an uptrend. Think: staircase going up."
    ),
    "LH_LL": (
        "Lower High / Lower Low — each price peak and trough is lower than the last. "
        "This is the definition of a downtrend. Think: staircase going down."
    ),
    "TRANSITIONAL": (
        "The market is shifting between contexts. No clean structural label. "
        "Treat as RANGING — trade edges only, reduce size."
    ),

    # ── Market regime ─────────────────────────────────────────────────────────
    "TRENDING_UP": (
        "Price has clear upward momentum right now — ADX is above 25. "
        "Structure signals are weighted heavily. The trend does the work."
    ),
    "TRENDING_DOWN": (
        "Price has clear downward momentum — ADX above 25. "
        "Structure signals weighted heavily. Sell strength, not weakness."
    ),
    "VOLATILE": (
        "News or an event is driving sharp, unpredictable moves. "
        "Technical signals are less reliable. Reduce size significantly. Wait for dust to settle."
    ),
    "DEFAULT": (
        "Mixed or unclear regime — default signal weights applied. "
        "No single regime is dominant. Treat as moderate conviction only."
    ),

    # ── Indicators ────────────────────────────────────────────────────────────
    "ADX": (
        "Average Directional Index. A number from 0-100 measuring trend STRENGTH. "
        "It does NOT tell you direction — only how strong the move is. "
        "Below 20 = ranging/choppy. Above 25 = genuine trend. Above 40 = strong trend."
    ),
    "ATR": (
        "Average True Range. The average number of pips GBP/AUD moves in a single day. "
        "If ATR = 155 pips, the market typically moves 155 pips from low to high each day."
    ),
    "fuel_pct": (
        "What percentage of today's typical daily range has already been used. "
        "Below 50% = plenty of room left. Above 80% = very little room — avoid new entries."
    ),
    "MA50": (
        "The 50-day moving average price. A widely-watched level of trend support/resistance. "
        "Price above MA50 = trend support holding. Price below MA50 = structure breaking down."
    ),

    # ── Macro quadrants ───────────────────────────────────────────────────────
    "GOLDILOCKS": (
        "Economy growing, inflation low. Investors happy and buying risky assets. "
        "AUD tends to rise (Australia exports commodities to a growing world). "
        "Effect on GBP/AUD: BEARISH (AUD getting stronger)."
    ),
    "REFLATION": (
        "Economy booming, inflation rising. Commodities in high demand. AUD benefits. "
        "Effect on GBP/AUD: tends to favor AUD over GBP — BEARISH signal."
    ),
    "STAGFLATION": (
        "Growth slowing but inflation still rising. Worst of both worlds. "
        "Investors flee to safety. GBP benefits as relative safe haven. "
        "Effect on GBP/AUD: BULLISH."
    ),
    "DEFLATION": (
        "Growth and inflation both falling. Full risk-off mode. "
        "Commodity currencies (AUD) sold hard. "
        "Effect on GBP/AUD: AUD falls — BULLISH for GBP/AUD."
    ),

    # ── Value context ─────────────────────────────────────────────────────────
    "PREMIUM": (
        "Price is above fair value — it is expensive compared to recent history. "
        "Good location to SELL. Bad location to buy."
    ),
    "STRONG PREMIUM": (
        "All three value measures say price is expensive. Best location to SHORT. "
        "The market is stretched above equilibrium."
    ),
    "DISCOUNT": (
        "Price is below fair value — it is cheap compared to recent history. "
        "Good location to BUY. Bad location to sell."
    ),
    "STRONG DISCOUNT": (
        "All three value measures say price is cheap. Best location to BUY. "
        "The market is stretched below equilibrium."
    ),
    "FAIR VALUE": (
        "Price is roughly where it should be — near the 10-day average. "
        "Neither cheap nor expensive. Less directional signal from location alone."
    ),
    "fair_value": (
        "The 10-day average price — the market's equilibrium. "
        "Price tends to drift back toward this over time. "
        "When far above it, the rubber band is stretched."
    ),
    "weekly_mid": (
        "The exact midpoint of this week's highest and lowest price. "
        "Upper half of the week = expensive. Lower half = cheap."
    ),

    # ── Liquidity & sweeps ────────────────────────────────────────────────────
    "sweep_down": (
        "A key LOW was broken — stop-losses from longs were triggered — then price reversed UP. "
        "Institutional trap: big money bought at that swept low. BULLISH signal."
        "Plain English: 'They shook the weak hands out at the bottom. The bounce is real.'"
    ),
    "sweep_up": (
        "A key HIGH was broken — stop-losses from shorts were triggered — then price reversed DOWN. "
        "Institutional trap: big money sold at that swept high. BEARISH signal. "
        "Plain English: 'They flushed the breakout buyers at the top. The drop is real.'"
    ),
    "Sweep": (
        "When price deliberately runs through a key level to trigger stop-losses sitting there, "
        "then immediately reverses. The stop-losses provided the liquidity big money needed "
        "to fill their own orders. The real direction is the reversal."
    ),
    "PDH": "Previous Day High — yesterday's highest price. A common resistance level.",
    "PDL": "Previous Day Low — yesterday's lowest price. A common support level.",
    "PWH": "Previous Week High — this or last week's highest price. Significant resistance.",
    "PWL": "Previous Week Low — this or last week's lowest price. Significant support.",
    "nearest_pool": (
        "The closest cluster of stop-loss orders to the current price. "
        "This is the most likely next target for a sweep."
    ),

    # ── Currency strength ─────────────────────────────────────────────────────
    "Currency Strength": (
        "How strong or weak each currency is TODAY compared to ALL other major currencies. "
        "Not just vs the pair being traded — a global ranking of currency performance."
    ),
    "differential": (
        "GBP strength score minus AUD strength score. "
        "Positive = GBP outperforming AUD today (bullish for GBP/AUD). "
        "Negative = AUD outperforming GBP today (bearish for GBP/AUD)."
    ),

    # ── COT ───────────────────────────────────────────────────────────────────
    "COT": (
        "Commitment of Traders — a US government report published every Friday. "
        "Shows what large institutional traders (hedge funds, banks) have been "
        "building in terms of long or short positions for each currency."
    ),
    "Hedge Fund Positioning": (
        "What large institutional traders (hedge funds, banks) are positioned: "
        "long or short. When they're extremely one-sided (extreme positioning), "
        "the framework flips to a contrarian signal."
    ),
    "CONTRARIAN": (
        "When 80%+ of institutional money is on the same side, the trade is crowded. "
        "Everyone who wanted to buy already bought — there's no one left to push price up. "
        "The framework FLIPS the COT signal: extreme long = watch for reversal DOWN."
    ),
    "extreme positioning": (
        "When institutional traders are overwhelmingly positioned one way (80%+ long or short). "
        "Contrarian signal — the crowded trade tends to unwind."
    ),

    # ── Cross-market ──────────────────────────────────────────────────────────
    "VIX": (
        "The Fear Index. Measures how panicked the stock market is. "
        "High VIX (above 30) = panic, bad for AUD. Low VIX (below 20) = calm, good for AUD."
    ),
    "NORMAL": "VIX below 20. Markets calm. Investors taking risk. AUD tends to benefit.",
    "ELEVATED": "VIX 20-30. Some fear building. Caution warranted.",
    "PANIC_BUILDING": "VIX above 30 and rising. Investors panicking. AUD likely under pressure.",
    "PANIC_FADING": "VIX was high but is now falling. Relief rally more likely than continuation down.",
    "risk_on": (
        "Investors are confident and buying risky assets (stocks, commodities, AUD). "
        "AUD tends to rise in risk-on environments → BEARISH for GBP/AUD."
    ),
    "risk_off": (
        "Investors are scared and selling risky assets, buying safety (bonds, gold, GBP). "
        "AUD tends to fall → BULLISH for GBP/AUD."
    ),
    "RISK_ON": "Same as risk_on. Investors buying risky assets. AUD benefits. Bearish GBP/AUD.",
    "RISK_OFF": "Same as risk_off. Investors fleeing to safety. AUD falls. Bullish GBP/AUD.",
    "DXY": (
        "US Dollar Index — how strong the USD is against a basket of major currencies. "
        "Rising DXY often signals risk-off globally. Usually negative for AUD."
    ),

    # ── Interest rates ────────────────────────────────────────────────────────
    "Carry Signal": (
        "Money naturally flows toward the currency with the higher interest rate. "
        "If BoE rate > RBA rate, GBP earns more interest → slightly BULLISH for GBP/AUD. "
        "This is a slow background signal — it rarely drives a single day's move."
    ),
    "Rate Path Signal": (
        "Where interest rates are HEADING matters more than where they are today. "
        "If BoE is expected to raise rates AND RBA is expected to cut, "
        "GBP/AUD will likely rise even before the change happens."
    ),
    "hawkish": (
        "A central bank is leaning toward RAISING interest rates. "
        "BULLISH for that bank's currency — higher rates attract global investment."
    ),
    "dovish": (
        "A central bank is leaning toward CUTTING interest rates. "
        "BEARISH for that bank's currency — lower rates reduce investment appeal."
    ),
    "BoE": "Bank of England — the UK central bank. Sets GBP interest rates.",
    "RBA": "Reserve Bank of Australia — Australia's central bank. Sets AUD interest rates.",
    "STALE": (
        "The data is too old to be reliable. When a signal is marked STALE, "
        "its score is set to zero so it doesn't mislead the decision."
    ),

    # ── Intraday / Asian range ────────────────────────────────────────────────
    "Asian range": (
        "The high and low price during the overnight Asian session (22:00-07:00 UTC). "
        "This range becomes a reference point when London opens. "
        "Most fakeouts happen when London breaks through one side of this range."
    ),
    "BULLISH_FAKEOUT": (
        "London opened and broke BELOW the Asian low, trapping longs, then reversed UP. "
        "Big money bought at the swept low. The reversal up is the real direction. "
        "Trade: BUY the reversal. Stop just below the swept Asian low."
    ),
    "BEARISH_FAKEOUT": (
        "London opened and broke ABOVE the Asian high, trapping breakout buyers, then reversed DOWN. "
        "Big money sold at the swept high. The reversal down is the real direction. "
        "Trade: SELL the reversal. Stop just above the swept Asian high."
    ),
    "CLEAN_BREAK_UP": (
        "Price broke above the Asian high AND is holding above it — no reversal. "
        "This is a genuine breakout, not a trap. Trade the continuation upward."
    ),
    "CLEAN_BREAK_DOWN": (
        "Price broke below the Asian low AND is holding below it — genuine breakdown. "
        "Trade the continuation downward."
    ),
    "BOTH_SWEPT": (
        "BOTH the Asian high AND low were swept in the same session. "
        "Total chaos — no clean directional signal. "
        "The framework hard-blocks this: NO TRADE."
    ),
    "INSIDE_RANGE": (
        "Price is still inside the Asian range — no breakout or fakeout yet. "
        "No intraday signal. Wait."
    ),
    "fakeout": (
        "When price breaks through a key level (triggering stop-losses), "
        "then immediately reverses. The break was a trap to collect liquidity, "
        "not a genuine directional move."
    ),

    # ── Sessions ──────────────────────────────────────────────────────────────
    "London Session": (
        "07:00-16:00 UTC. When European banks are open and trading. "
        "This is when GBP pairs come alive. Most large GBP moves happen in the first 2 hours. "
        "Grade bonuses are applied for entries here."
    ),
    "New York Session": (
        "13:00-22:00 UTC. US banks are open. The second major session for GBP/AUD. "
        "Overlapping with London (13:00-16:00) is the most volatile window of the day."
    ),
    "London/New York Overlap": (
        "13:00-16:00 UTC. Both major sessions running simultaneously. "
        "Highest volume and liquidity. Maximum grade bonus applied here."
    ),
    "Tokyo Session": (
        "00:00-09:00 UTC. Asian banks trading. GBP/AUD barely moves. "
        "Wider spreads, thin volume. Grade is capped at A (never A+) during Tokyo."
    ),
    "Sydney Session": (
        "22:00-07:00 UTC. Australian banks open but GBP is asleep. Mostly noise. "
        "The Asian range is built during this window."
    ),
    "Off-hours": "Market is open but no major session is active. Thin liquidity. Avoid trading.",

    # ── Leg decomposition ─────────────────────────────────────────────────────
    "Leg Decomposition": (
        "Breaking GBP/AUD into its two parts: GBP/USD and AUD/USD. "
        "Understanding which leg is driving the move tells you how sustainable it is. "
        "Both legs pushing in the same direction = strongest signal."
    ),
    "BOTH_CONFIRMING_BULLISH": (
        "GBP/USD is RISING and AUD/USD is FALLING simultaneously. "
        "Both legs of GBP/AUD are pushing it higher. Strongest possible bullish signal."
    ),
    "BOTH_CONFIRMING_BEARISH": (
        "GBP/USD is FALLING and AUD/USD is RISING simultaneously. "
        "Both legs pushing GBP/AUD lower. Strongest possible bearish signal."
    ),
    "GBP_STRENGTH_LED": (
        "GBP/AUD rising mainly because GBP is getting stronger — AUD is just sitting still. "
        "Moderate bullish signal. One engine, not two."
    ),
    "AUD_WEAKNESS_LED": (
        "GBP/AUD rising because AUD is falling — GBP is not especially strong. "
        "Moderate bullish signal. Watch for AUD to stabilize."
    ),
    "GBP_WEAKNESS_LED": (
        "GBP/AUD falling mainly because GBP is weakening — AUD is not especially strong. "
        "Moderate bearish signal."
    ),
    "AUD_STRENGTH_LED": (
        "GBP/AUD falling because AUD is strengthening — GBP is not especially weak. "
        "Moderate bearish signal."
    ),
    "GBP_OUTPACING": "GBP rising faster than AUD — slight bullish lean for GBP/AUD.",
    "AUD_OUTPACING": "AUD rising faster than GBP — slight bearish lean for GBP/AUD.",
    "NEUTRAL": (
        "No clear directional lean from this signal. "
        "GBP/USD and AUD/USD moving together or in opposite directions that cancel out."
    ),
    "UNKNOWN": "Not enough data to determine a signal. This layer is not counted in scoring.",

    # ── Trade math ────────────────────────────────────────────────────────────
    "pips": (
        "The smallest meaningful price movement for GBP/AUD = 0.0001. "
        "If price moves from 2.0300 to 2.0350, that is 50 pips."
    ),
    "stop_loss": (
        "A pre-set price where your trade automatically closes if wrong. "
        "Limits your maximum loss on one trade. Think: maximum acceptable pain point."
    ),
    "Stop Loss": (
        "A pre-set price where your trade closes if you are wrong. "
        "Always set before entering. Never move it further against you."
    ),
    "target": (
        "The price where you plan to take profit if you are right. "
        "Set before entering the trade. The destination, not a moving goalpost."
    ),
    "R:R": (
        "Risk:Reward ratio. How much you stand to MAKE vs how much you are RISKING. "
        "2.5:1 means for every $100 risked, you could make $250. "
        "Minimum acceptable after spread: 1.5:1."
    ),
    "spread": (
        "The difference between the buy price and sell price — the broker's fee. "
        "GBP/AUD typical spread: 3-5 pips. This comes out of every trade automatically. "
        "Always use spread-adjusted R:R — not the raw number."
    ),
    "lot_size": (
        "How many units of currency you are trading. "
        "1 standard lot = 100,000 units. For GBP/AUD, 1 pip = ~$10 per standard lot. "
        "The framework calculates lot size from: (account × risk%) ÷ (stop pips × pip value)."
    ),
    "entry_zone": (
        "The price range where you should place your trade — typically ±8 pips around "
        "the key level being tested. Enter anywhere inside this zone."
    ),
    "invalidation": (
        "A specific price or condition that proves your trade idea is wrong. "
        "If invalidation triggers, exit immediately — the premise has failed."
    ),

    # ── Auto-label outcomes ────────────────────────────────────────────────────
    "WIN": (
        "The market moved 20+ pips in the direction the framework predicted within 24 hours. "
        "The framework was right."
    ),
    "LOSS": (
        "The market moved 20+ pips AGAINST the direction the framework predicted. "
        "The framework was wrong."
    ),

    # ── Session guard ─────────────────────────────────────────────────────────
    "HALTED": (
        "Daily loss limit has been reached. No more trades today. "
        "The machine enforces what your mind won't under pressure."
    ),
    "SESSION_CLOSED": (
        "Maximum trades per session reached. No more entries today. "
        "Over-trading is one of the biggest account killers — this prevents it."
    ),
    "ACTIVE": "No limits hit. Trading is permitted. Session guard is green.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def explain(term: str) -> str:
    """
    Return a plain-English explanation for a framework term.

    Case-insensitive exact match first, then partial match.
    Always returns a string — never raises.

    Plain English: type any term from the report and get a clear explanation.
    """
    if not term or not term.strip():
        return "Usage: explain('TERM')  —  e.g. explain('ADX') or explain('conviction')"

    search = term.strip()

    # 1. Exact match (case-insensitive)
    for k, v in TERMS.items():
        if k.lower() == search.lower():
            return _format(k, v)

    # 2. Partial match — key contains the search term
    matches = [(k, v) for k, v in TERMS.items() if search.lower() in k.lower()]
    if matches:
        if len(matches) == 1:
            return _format(matches[0][0], matches[0][1])
        return "Multiple matches:\n" + "\n\n".join(_format(k, v) for k, v in matches[:4])

    # 3. Reverse partial — search term contains the key (min key length 3 to avoid
    #    single-letter keys like "A" matching inside every long search string)
    matches = [(k, v) for k, v in TERMS.items()
               if len(k) >= 3 and k.lower() in search.lower()]
    if matches:
        return "\n\n".join(_format(k, v) for k, v in matches[:3])

    return (
        f"Term '{term}' not found in glossary.\n"
        f"Run: python explain.py   (no args) to see all {len(TERMS)} defined terms."
    )


def _format(term: str, definition: str) -> str:
    """Format a single glossary entry for display."""
    bar = "─" * 44
    return f"\n{bar}\n  {term}\n{bar}\n  {definition}\n{bar}"


def all_terms() -> list[str]:
    """Return sorted list of all defined term keys."""
    return sorted(TERMS.keys())
