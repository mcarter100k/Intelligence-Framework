"""
news_analysis.py
────────────────
Qualitative narrative for economic events BEFORE the actual is released
(preview mode). Also used post-release for a plain-language context blurb.

No numeric comparison is done here — that lives in trade_logic.py.
"""


# Full names for common economic abbreviations
_EVENT_NAMES = {
    "cpi":          "CPI (Consumer Price Index — measures everyday inflation)",
    "pmi":          "PMI (Purchasing Managers Index — business activity survey, 50+ = growth)",
    "gdp":          "GDP (Gross Domestic Product — total economic output)",
    "hpi":          "HPI (House Price Index — tracks property price changes)",
    "rpi":          "RPI (Retail Price Index — a UK inflation measure)",
    "ppi":          "PPI (Producer Price Index — factory input costs, leads future CPI)",
    "m4":           "M4 (Money Supply — total money circulating in the UK economy)",
    "brc":          "BRC (British Retail Consortium shop price survey)",
    "fpc":          "FPC (Financial Policy Committee — Bank of England stability committee)",
    "mpc":          "MPC (Monetary Policy Committee — sets UK interest rates)",
    "employment":   "Employment Change (how many jobs were added or lost)",
    "unemployment": "Unemployment Rate (percentage of people without a job)",
    "retail sales": "Retail Sales (how much consumers are spending in shops)",
    "trade balance":"Trade Balance (difference between exports and imports)",
    "building approvals": "Building Approvals (number of new construction permits — signals future growth)",
    "current account": "Current Account (UK's total trade and income balance with the world)",
    "business investment": "Business Investment (how much companies are spending on growth)",
    "mortgage approvals": "Mortgage Approvals (how many home loans were approved — signals housing demand)",
    "net lending":  "Net Lending (total new borrowing by consumers — signals spending confidence)",
    "cash rate":    "Cash Rate (the RBA's official interest rate)",
    "interest rate":"Interest Rate Decision (central bank sets the cost of borrowing money)",
}

def _expand_event_name(event: str) -> str:
    """Return event name with plain-English expansion if known."""
    name_lower = event.lower()
    for key, full_name in _EVENT_NAMES.items():
        if key in name_lower:
            return full_name
    return event  # return as-is if not found

def analyze_economic_event(event: str, forecast: str, previous: str, currency: str = "GBP") -> str:
    """
    Return a short qualitative blurb describing what the event measures and
    how a beat vs miss typically moves GBP/AUD.

    Parameters
    ----------
    event    : event name string
    forecast : consensus forecast (string, may be empty)
    previous : prior reading (string, may be empty)
    currency : "GBP" or "AUD" — determines directional mapping
    """
    name = event.lower()
    pair_direction = _pair_direction_label(currency)

    # ── Interest rates ─────────────────────────────────────────────────────────
    if "interest rate" in name or "rate decision" in name or "cash rate" in name:
        if currency == "GBP":
            return (
                f"🏦 BoE rate decision. A hike (above {forecast}) strengthens GBP → "
                f"GBPAUD {pair_direction('bullish')}. A cut or hold below forecast weakens GBP."
            )
        else:
            return (
                f"🏦 RBA rate decision. A hike (above {forecast}) strengthens AUD → "
                f"GBPAUD {pair_direction('bearish')}. A cut or hold weakens AUD."
            )

    # ── Inflation / CPI ────────────────────────────────────────────────────────
    if "cpi" in name or "inflation" in name or "rpi" in name:
        return (
            f"📊 Inflation print. Above-forecast CPI ({forecast}) raises rate-hike "
            f"expectations → {currency} strengthens → GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── Employment / Labour ────────────────────────────────────────────────────
    if "employment" in name or "payroll" in name or "nonfarm" in name or "labour" in name or "labor" in name:
        return (
            f"💼 Employment data. A strong beat boosts {currency} → "
            f"GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── Unemployment (inverted) ────────────────────────────────────────────────
    if "unemployment" in name or "jobless" in name or "claimant" in name:
        return (
            f"💼 Unemployment data (inverted — lower is better). "
            f"Below-forecast reading strengthens {currency} → "
            f"GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── GDP ────────────────────────────────────────────────────────────────────
    if "gdp" in name or "gross domestic" in name:
        return (
            f"📈 GDP release. Above-forecast growth ({forecast}) strengthens {currency} → "
            f"GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── Retail Sales ──────────────────────────────────────────────────────────
    if "retail" in name and "sales" in name:
        return (
            f"🛒 Retail Sales. Strong consumer spending supports {currency} → "
            f"GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── PMI ───────────────────────────────────────────────────────────────────
    if "pmi" in name or "purchasing managers" in name:
        return (
            f"🏭 PMI data. Above 50 = expansion; above forecast ({forecast}) supports "
            f"{currency} → GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── Commodity prices ─────────────────────────────────────────────────────
    if "commodity" in name and "price" in name:
        return (
            f"🛢️  Commodity Prices ({currency}). Tracks the prices Australia receives for its exports "
            f"(iron ore, coal, gas, gold). If commodity prices rise, Australian exporters earn more "
            f"→ AUD tends to strengthen → GBPAUD goes DOWN."
        )

    # ── Trade Balance ─────────────────────────────────────────────────────────
    if "trade balance" in name or "current account" in name:
        return (
            f"⚖️  Trade/Current Account. A narrowing deficit or wider surplus "
            f"supports {currency} → GBPAUD {pair_direction('bullish' if currency == 'GBP' else 'bearish')}."
        )

    # ── Central bank communications (no numeric forecast) ────────────────────
    if any(k in name for k in ["fpc", "monetary policy", "mpc", "rba statement",
                                "boe statement", "governor", "minutes", "statement"]):
        if currency == "GBP":
            return (
                f"🏦 Bank of England communication. Watch for hawkish language "
                f"(rate hike signals = GBP bullish) or dovish language (cut signals = GBP bearish). "
                f"No numeric forecast — read the tone of the statement."
            )
        else:
            return (
                f"🏦 Reserve Bank of Australia communication. Watch for hawkish language "
                f"(rate hike signals = AUD bullish) or dovish language (cut signals = AUD bearish). "
                f"No numeric forecast — read the tone of the statement."
            )

    # ── Bond auctions ─────────────────────────────────────────────────────────
    if "bond" in name or "auction" in name or "gilt" in name:
        return (
            f"📊 Bond auction. A strong bid (low yield) signals demand for {currency} assets. "
            f"Watch the bid-to-cover ratio for sentiment clues."
        )

    # ── Generic fallback ──────────────────────────────────────────────────────
    # Only show nan warning if forecast is genuinely missing
    if not forecast or str(forecast).lower() in ("nan", "none", ""):
        return (
            f"📌 {event} ({currency}). No numeric forecast published. "
            f"Compare actual vs previous reading when released."
        )
    return (
        f"📌 {event} ({currency}). Forecast: {forecast} | Previous: {previous}. "
        "Compare actual vs forecast for directional bias when released."
    )


def _pair_direction_label(currency: str):
    """Return a closure that maps bullish/bearish to a GBPAUD label."""
    def label(direction: str) -> str:
        if currency == "GBP":
            return "📈 BULLISH" if direction == "bullish" else "📉 BEARISH"
        else:
            # AUD strong = GBPAUD falls
            return "📉 BEARISH" if direction == "bullish" else "📈 BULLISH"
    return label
