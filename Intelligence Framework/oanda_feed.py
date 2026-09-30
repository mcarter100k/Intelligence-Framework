"""
oanda_feed.py
─────────────
Lightweight OANDA integration for the GBP/AUD framework.

Does exactly three things:
  1. get_live_price()     — real-time mid-price for the NOW section
  2. get_daily_bars()     — recent daily OHLCV as yfinance fallback
  3. get_weekly_bars()    — recent weekly OHLCV as yfinance fallback

No base classes. No config system. No caching layer. Just requests.

SETUP:
  Set two environment variables (add to ~/.zshrc or ~/.bashrc):

    export OANDA_API_KEY="your-live-api-key"
    export OANDA_ACCOUNT_ID="your-account-id"

  Your config.yaml shows environment: "live" so the live base URL is used.
  If you want to use a practice account instead, set:
    export OANDA_ENVIRONMENT="practice"

HOW IT'S USED IN THE FRAMEWORK:
  - liquidity_context.py calls get_live_price() to replace the last yfinance close
  - htf_structure.py, regime_detection.py, liquidity_context.py call
    get_daily_bars() / get_weekly_bars() as silent fallbacks when yfinance fails
  - If OANDA is unavailable or not configured, all functions return None
    and the framework falls back to yfinance silently

SECURITY:
  API key is read from environment variable only — never hardcoded.
  Never commit your API key to git.
"""

from __future__ import annotations

import os
import time
import requests
from typing import Optional

import pandas as pd


# ── Config ────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    env = os.environ.get("OANDA_ENVIRONMENT", "live").lower()
    if env == "practice":
        return "https://api-fxpractice.oanda.com"
    return "https://api-fxtrade.oanda.com"


def _headers() -> dict:
    api_key = os.environ.get("OANDA_API_KEY", "")
    if not api_key:
        raise ValueError("OANDA_API_KEY environment variable not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _account_id() -> str:
    acct = os.environ.get("OANDA_ACCOUNT_ID", "")
    if not acct:
        raise ValueError("OANDA_ACCOUNT_ID environment variable not set")
    return acct


def _pair(pair: str = "GBPAUD") -> str:
    """Convert GBPAUD → GBP_AUD for OANDA API."""
    if "_" not in pair and len(pair) == 6:
        return f"{pair[:3]}_{pair[3:]}"
    return pair


# ── 1. Live mid-price ─────────────────────────────────────────────────────────

def get_live_price(pair: str = "GBPAUD", timeout: int = 5) -> Optional[float]:
    """
    Fetch the current live mid-price from OANDA.

    Returns float (e.g. 1.9163) or None if unavailable.
    Falls back gracefully — never raises, never breaks the report.

    Uses the account pricing endpoint which gives real-time bid/ask.
    Mid = (best_bid + best_ask) / 2
    """
    try:
        instrument = _pair(pair)
        url = f"{_base_url()}/v3/accounts/{_account_id()}/pricing"
        params = {"instruments": instrument}

        resp = requests.get(url, headers=_headers(), params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        prices = data.get("prices", [])
        if not prices:
            return None

        price_data = prices[0]

        # Get best bid and ask
        bids = price_data.get("bids", [])
        asks = price_data.get("asks", [])

        if bids and asks:
            bid = float(bids[0]["price"])
            ask = float(asks[0]["price"])
            mid = round((bid + ask) / 2, 5)
            return mid

        # Fallback: use closeoutBid/closeoutAsk
        closeout_bid = price_data.get("closeoutBid")
        closeout_ask = price_data.get("closeoutAsk")
        if closeout_bid and closeout_ask:
            return round((float(closeout_bid) + float(closeout_ask)) / 2, 5)

        return None

    except ValueError:
        # API key or account ID not configured — silent, expected during setup
        return None
    except Exception:
        # Network error, rate limit, anything else — fail silently
        return None


# ── 2. Daily bars ─────────────────────────────────────────────────────────────

def get_daily_bars(pair: str = "GBPAUD", count: int = 100,
                   timeout: int = 10) -> Optional[pd.DataFrame]:
    """
    Fetch recent daily OHLCV bars from OANDA.

    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    with a DatetimeIndex (UTC), compatible with how yfinance data is used.
    Returns None if unavailable.
    """
    return _get_bars(pair, granularity="D", count=count, timeout=timeout)


def get_weekly_bars(pair: str = "GBPAUD", count: int = 110,
                    timeout: int = 10) -> Optional[pd.DataFrame]:
    """
    Fetch recent weekly OHLCV bars from OANDA.

    Returns a DataFrame matching yfinance format.
    Returns None if unavailable.
    """
    return _get_bars(pair, granularity="W", count=count, timeout=timeout)


def get_h4_bars(pair: str = "GBPAUD", count: int = 120,
                timeout: int = 10) -> Optional[pd.DataFrame]:
    """Fetch recent 4-hour OHLCV bars from OANDA."""
    return _get_bars(pair, granularity="H4", count=count, timeout=timeout)


def get_m15_bars(pair: str = "GBPAUD", count: int = 10,
                 timeout: int = 10) -> Optional[pd.DataFrame]:
    """Fetch recent 15-minute OHLCV bars from OANDA."""
    return _get_bars(pair, granularity="M15", count=count, timeout=timeout)


def get_hourly_bars(pair: str = "GBPAUD", count: int = 72,
                    timeout: int = 10) -> Optional[pd.DataFrame]:
    """
    Fetch recent 1-hour OHLCV bars from OANDA.

    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    with a UTC DatetimeIndex. count=72 covers the last 3 trading days.
    Returns None if unavailable.
    """
    return _get_bars(pair, granularity="H1", count=count, timeout=timeout)


# ── Failure classification (docs/specs/visible_failures_spec.md D7) ─────────
# Before: every failure (revoked key, OANDA outage, timeout) returned None
# after ONE attempt, and the trader read "Not enough data to calculate regime
# indicators" for all of them. Now each failure is classified, transient ones
# retry, and the latest classification is available to the caller.
_RETRY_WAITS = (1.0, 2.0)          # seconds before retry 1 and retry 2
_last_error: Optional[str] = None


def last_error() -> Optional[str]:
    """Plain-English classification of the most recent failed fetch, or
    None when the most recent fetch succeeded."""
    return _last_error


def _classify(exc: Exception) -> tuple:
    """(message, transient) for a failed request."""
    if isinstance(exc, requests.HTTPError):
        code = getattr(getattr(exc, "response", None), "status_code", None)
        if code in (401, 403):
            return (f"HTTP {code}: OANDA rejected the credentials (key revoked, "
                    f"expired, or for the wrong environment)", False)
        if code == 429:
            return ("HTTP 429: rate limited by OANDA", True)
        if code is not None and code >= 500:
            return (f"HTTP {code}: OANDA server error", True)
        return (f"HTTP {code}: request rejected by OANDA", False)
    if isinstance(exc, requests.Timeout):
        return ("request timed out", True)
    if isinstance(exc, requests.ConnectionError):
        return ("connection failed (network down or OANDA unreachable)", True)
    if isinstance(exc, ValueError) and "environment variable" in str(exc):
        return (f"credentials missing: {exc}", False)
    return (f"{type(exc).__name__}: {exc}", False)


def _get_bars(pair: str, granularity: str, count: int,
              timeout: int) -> Optional[pd.DataFrame]:
    """Internal: fetch OHLCV candles from OANDA instruments endpoint."""
    global _last_error
    try:
        instrument = _pair(pair)
        url = f"{_base_url()}/v3/instruments/{instrument}/candles"
        params = {
            "granularity": granularity,
            "count":       min(count + 1, 5000),  # +1 because current incomplete bar is filtered
            "price":       "M",  # mid prices
        }

        for attempt in range(len(_RETRY_WAITS) + 1):
            try:
                resp = requests.get(url, headers=_headers(), params=params,
                                    timeout=timeout)
                resp.raise_for_status()
                break
            except Exception as exc:
                msg, transient = _classify(exc)
                if not transient or attempt == len(_RETRY_WAITS):
                    tries = attempt + 1
                    _last_error = (f"{msg} ({granularity} {instrument}, "
                                   f"{tries} attempt{'s' if tries > 1 else ''})")
                    return None
                time.sleep(_RETRY_WAITS[attempt])
        data = resp.json()

        candles = data.get("candles", [])
        if not candles:
            return None

        rows = []
        for c in candles:
            if not c.get("complete", True):
                continue  # skip incomplete (current) bar
            try:
                dt  = pd.to_datetime(c["time"]).tz_convert("UTC")
                mid = c["mid"]
                rows.append({
                    "Datetime": dt,
                    "Open":     float(mid["o"]),
                    "High":     float(mid["h"]),
                    "Low":      float(mid["l"]),
                    "Close":    float(mid["c"]),
                    "Volume":   int(c.get("volume", 0)),
                })
            except (KeyError, ValueError, TypeError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df = df.set_index("Datetime").sort_index()
        _last_error = None
        return df

    except Exception as exc:
        _last_error, _ = _classify(exc)
        return None


# ── 3. Status check ───────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if OANDA credentials are present in environment."""
    return bool(
        os.environ.get("OANDA_API_KEY", "").strip() and
        os.environ.get("OANDA_ACCOUNT_ID", "").strip()
    )


def check_connection() -> dict:
    """
    Test OANDA connectivity. Useful for debugging setup.
    Run: python oanda_feed.py

    Returns dict with status, price (if successful), and any error.
    """
    if not is_configured():
        return {
            "ok":    False,
            "error": "OANDA_API_KEY or OANDA_ACCOUNT_ID not set in environment",
            "hint":  "export OANDA_API_KEY='your-key' && export OANDA_ACCOUNT_ID='your-id'",
        }

    price = get_live_price()
    if price:
        return {"ok": True, "price": price, "pair": "GBP/AUD", "source": "OANDA live"}
    else:
        return {
            "ok":    False,
            "error": "Connected but price fetch failed — check account ID and permissions",
        }


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nTesting OANDA connection...")
    result = check_connection()
    if result["ok"]:
        print(f"  ✅ Connected — GBP/AUD live price: {result['price']}")
        print("\nTesting daily bars (last 5)...")
        bars = get_daily_bars(count=5)
        if bars is not None:
            print(bars[["Open", "High", "Low", "Close"]].to_string())
        else:
            print("  ⚠️  Daily bars unavailable")
    else:
        print(f"  ❌ {result['error']}")
        if "hint" in result:
            print(f"  Hint: {result['hint']}")
    print()
