"""
main.py
────────
Primary entrypoint for the GBP/AUD intelligence framework.

Usage
─────
  python main.py          →  full market brain report (recommended)
  python main.py events   →  calendar events only
  python main.py strength →  currency strength only
  python main.py liq      →  liquidity levels only
"""

import sys
import time
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

from config           import LOG_CONFIG
from forex_calendar   import ForexCalendarScraper
from forex_analyzer   import ForexEventAnalyzer
from news_analysis    import analyze_economic_event
from trade_logic      import analyze_impact
from market_brain     import build_market_report, print_report
from trade_logger     import run_log
from entry_watcher    import watch as run_watch
from currency_strength import get_currency_strength
from session_context   import get_session_context
from liquidity_context import get_liquidity_context
from htf_structure     import get_htf_structure
from interest_rates    import get_rate_differential
from cot_data          import get_cot_data
from regime_detection  import get_regime
from cross_market      import get_cross_market


# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    log_dir = Path(LOG_CONFIG["directory"])
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG["level"]),
        format=LOG_CONFIG["format"],
        filename=log_dir / f"forex_{datetime.now().strftime('%Y%m%d')}.log",
    )


# ── Sub-commands ──────────────────────────────────────────────────────────────

def run_events() -> None:
    """Print this week's calendar events with post-release analysis."""
    scraper  = ForexCalendarScraper()
    analyzer = ForexEventAnalyzer()
    df = scraper.get_weekly_calendar()

    if df.empty:
        print("❌ No events found.")
        return

    print(f"\n{'═' * 60}")
    print("  GBP/AUD ECONOMIC CALENDAR")
    print(f"{'═' * 60}\n")

    for _, event in df.iterrows():
        actual   = str(event.get("actual",   "")).strip()
        forecast = str(event.get("forecast", "")).strip()
        previous = str(event.get("previous", "")).strip()
        currency = str(event.get("currency", "")).strip()
        name     = str(event.get("event",    "")).strip()

        has_actual   = bool(actual)
        has_forecast = bool(forecast)

        print(f"  [{currency}] {event.get('time')}  |  {event.get('impact')}")
        print(f"  {name}")

        if has_actual and has_forecast:
            # ── POST-RELEASE ──────────────────────────────────────────────────
            print(f"  Status   : RELEASED")
            print(f"  Actual: {actual}  |  Forecast: {forecast}  |  Previous: {previous}")

            # FIX: pass currency so direction maps correctly to GBP/AUD
            bias = analyze_impact(name, actual, forecast, currency)
            print(f"  Trade bias : {bias}")

            analysis = analyzer.analyze_event(name, actual, forecast, previous, currency)
            print(analysis)

        elif has_forecast or bool(previous):
            # ── PREVIEW ───────────────────────────────────────────────────────
            print(f"  Status   : UPCOMING")
            print(f"  Forecast: {forecast}  |  Previous: {previous}")
            context = analyze_economic_event(name, forecast, previous, currency)
            print(f"  Context  : {context}")

        print(f"\n{'─' * 60}\n")
        time.sleep(0.2)


def run_strength() -> None:
    print("\n" + "═" * 60)
    data = get_currency_strength(["GBP", "AUD"])
    print(format_strength_report(data))
    print("═" * 60 + "\n")


def run_liquidity() -> None:
    print("\n" + "═" * 60)
    data = get_liquidity_context()
    print(format_liquidity_report(data))
    print("═" * 60 + "\n")


def run_session() -> None:
    print("\n" + "═" * 60)
    ctx = get_session_context()
    print(format_session_report(ctx))
    print("═" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def _receiver_status() -> dict | None:
    """Check if trade_receiver.py is running. Returns status dict or None."""
    try:
        with urllib.request.urlopen("http://localhost:5001/status", timeout=1) as r:
            import json
            return json.loads(r.read())
    except Exception:
        return None


def run_trades() -> None:
    """Print trade performance summary from trades.csv."""
    from trade_receiver import print_stats
    print_stats()


def main() -> None:
    _setup_logging()

    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "brain"

    if cmd == "events":
        run_events()
    elif cmd == "strength":
        run_strength()
    elif cmd == "liq":
        run_liquidity()
    elif cmd == "session":
        run_session()
    elif cmd == "trades":
        run_trades()
    elif cmd == "log":
        subcmd = sys.argv[2].lower() if len(sys.argv) > 2 else ""
        run_log(subcmd)
    elif cmd == "watch":
        run_watch()
    elif cmd == "receiver":
        # Start the trade receiver directly
        from trade_receiver import start_server, print_stats, PORT
        print(f"  {'═'*50}")
        print(f"  TRADE RECEIVER — Intelligence Framework")
        print(f"  {'═'*50}")
        print(f"  Listening on http://localhost:{PORT}")
        print(f"  Waiting for MT5 TradeLogger EA...")
        print(f"  (Ctrl+C to stop)\n")
        try:
            start_server(PORT).serve_forever()
        except KeyboardInterrupt:
            print("\n  Stopped.")
            print_stats()
    else:
        # Default: full market brain — show receiver status at bottom
        # Optional trade-type flags: --intraday  or  --swing
        _trade_type = "auto"
        if "--intraday" in sys.argv:
            _trade_type = "intraday"
        elif "--swing" in sys.argv:
            _trade_type = "swing"
        report = build_market_report(trade_type=_trade_type)
        print_report(report)

        status = _receiver_status()
        if status:
            open_pos = status.get("open_positions", 0)
            pos_note = f"  {open_pos} open position(s) being tracked" if open_pos else "  No open positions"
            print(f"\n  Receiver: CONNECTED  {pos_note}")


if __name__ == "__main__":
    main()
