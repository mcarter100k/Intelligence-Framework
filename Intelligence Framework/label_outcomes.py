"""
label_outcomes.py
─────────────────
Automatically fills next_day_close and outcome_label in run_journal.csv.

HOW IT WORKS:
  1. Reads run_journal.csv
  2. Finds rows where next_day_close is empty AND the date is before today
  3. Fetches GBP/AUD daily closing prices from yfinance (already used by the framework)
  4. Matches each journal row's date to the next trading day's closing price
  5. Derives outcome_label automatically:
       WIN     = price moved 20+ pips in the direction of the bias
       LOSS    = price moved 20+ pips against the bias
       NEUTRAL = price stayed within 20 pips either way
  6. Writes the updated rows back to run_journal.csv

USAGE:
  python label_outcomes.py          ← labels all unlabeled past rows
  python label_outcomes.py --dry    ← preview without writing

This runs automatically at the start of every `python main.py` call (optional).
You can also run it manually any time.

OUTCOME DEFINITION:
  The bias field in the journal is what the framework believed (BULLISH/BEARISH/FLAT).
  We compare: entry price (at run time) vs next-day close.
  If framework said BEARISH and price went DOWN 20+ pips → WIN
  If framework said BEARISH and price went UP 20+ pips   → LOSS
  If price moved < 20 pips either way                    → NEUTRAL

  You can change WIN_THRESHOLD_PIPS below to match your style.
  20 pips is a reasonable default for GBP/AUD daily timeframe.

NOTES:
  - yfinance returns daily bars. We use the close of the day AFTER the run date.
  - If you ran multiple times on the same day, all same-day rows get the same next_day_close.
  - Weekends and holidays: yfinance skips non-trading days automatically.
  - next_london_open is approximated as the open of the next trading day bar.
  - trigger_fired, trade_taken, pnl_r still need manual entry — we can't know those.
"""

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# yfinance used as fallback if OANDA unavailable
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    yf = None

JOURNAL_PATH   = Path(__file__).parent / "run_journal.csv"
TICKER         = "GBPAUD=X"
WIN_THRESHOLD_PIPS = 20   # pips needed to call WIN or LOSS
DRY_RUN        = "--dry" in sys.argv


def _to_pips(price_diff: float) -> int:
    """Convert raw GBP/AUD price difference to pips (4th decimal place)."""
    return round(abs(price_diff) * 10000)


def fetch_daily_closes(start_date: date, end_date: date) -> dict[str, dict]:
    """
    Fetch GBP/AUD daily OHLC for the date range.
    Tries OANDA first (uses FX standard 5pm NY close = 21:00 UTC).
    Falls back to yfinance if OANDA unavailable.
    Returns dict keyed by date string 'YYYY-MM-DD' with {open, close} values.
    """
    # ── Try OANDA first ───────────────────────────────────────────────────────
    try:
        from oanda_feed import get_daily_bars, is_configured
        if is_configured():
            days_needed = (end_date - start_date).days + 10  # buffer
            df = get_daily_bars(count=max(days_needed, 30))
            if df is not None and not df.empty:
                result = {}
                for ts, row in df.iterrows():
                    # OANDA timestamps are 21:00 UTC (5pm NY) — use the DATE portion
                    # as the trading day key (the day the session opened)
                    # e.g. 2026-04-02 21:00 UTC = the Apr 2 FX session close
                    day_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
                    result[day_str] = {
                        "open":  float(row.get("Open",  0) or 0),
                        "close": float(row.get("Close", 0) or 0),
                    }
                if result:
                    return result
    except Exception:
        pass  # Fall through to yfinance

    # ── Fallback: yfinance ────────────────────────────────────────────────────
    try:
        fetch_start = (start_date - timedelta(days=3)).strftime("%Y-%m-%d")
        fetch_end   = (end_date   + timedelta(days=5)).strftime("%Y-%m-%d")

        df = yf.download(
            TICKER,
            start=fetch_start,
            end=fetch_end,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )

        if df.empty:
            return {}

        if hasattr(df.columns, "levels"):
            df.columns = df.columns.droplevel(1)

        result = {}
        for ts, row in df.iterrows():
            day_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
            result[day_str] = {
                "open":  float(row.get("Open",  0) or 0),
                "close": float(row.get("Close", 0) or 0),
            }
        return result
    except Exception:
        return {}


def next_trading_day_close(run_date: str, price_data: dict) -> tuple[float, float]:
    """
    Given a run date string, find the next trading day's close and open.
    Returns (next_day_close, next_london_open).
    next_london_open = open of the next trading day (approximation).
    """
    try:
        d = date.fromisoformat(run_date)
    except ValueError:
        return 0.0, 0.0

    # Walk forward up to 5 days to find the next trading day
    for i in range(1, 6):
        next_d = (d + timedelta(days=i)).strftime("%Y-%m-%d")
        if next_d in price_data:
            return price_data[next_d]["close"], price_data[next_d]["open"]

    return 0.0, 0.0


def derive_outcome(bias: str, entry_price: float, next_close: float) -> str:
    """
    WIN     = price moved WIN_THRESHOLD_PIPS+ in the bias direction
    LOSS    = price moved WIN_THRESHOLD_PIPS+ against the bias direction
    NEUTRAL = price moved less than WIN_THRESHOLD_PIPS either way
    """
    if not entry_price or not next_close:
        return ""

    diff_pips = _to_pips(next_close - entry_price)
    direction = "up" if next_close > entry_price else "down"

    if bias == "BEARISH":
        if direction == "down" and diff_pips >= WIN_THRESHOLD_PIPS:
            return "WIN"
        elif direction == "up" and diff_pips >= WIN_THRESHOLD_PIPS:
            return "LOSS"
        else:
            return "NEUTRAL"
    elif bias == "BULLISH":
        if direction == "up" and diff_pips >= WIN_THRESHOLD_PIPS:
            return "WIN"
        elif direction == "down" and diff_pips >= WIN_THRESHOLD_PIPS:
            return "LOSS"
        else:
            return "NEUTRAL"
    else:
        # FLAT / NEUTRAL bias — no directional call, can't label WIN/LOSS
        return "NEUTRAL"


def label_outcomes():
    if not JOURNAL_PATH.exists():
        print(f"Journal not found: {JOURNAL_PATH}")
        print("Run `python main.py` at least once first.")
        return

    with open(JOURNAL_PATH, newline="") as f:
        reader   = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows     = list(reader)

    if not rows:
        print("Journal is empty — no rows to label.")
        return

    today = date.today().isoformat()

    # Find rows that need labeling: date is before today, next_day_close is blank
    to_label = [
        r for r in rows
        if r.get("date", "") < today
        and not r.get("next_day_close", "").strip()
        and r.get("date", "")  # has a valid date
    ]

    if not to_label:
        print(f"✅ All past rows already labeled. ({len(rows)} total rows)")
        return

    print(f"Found {len(to_label)} rows to label (out of {len(rows)} total)...")

    # Determine date range to fetch
    dates = [r["date"] for r in to_label if r.get("date")]
    if not dates:
        print("No valid dates found.")
        return

    min_date = date.fromisoformat(min(dates))
    max_date = date.fromisoformat(max(dates))

    print(f"Fetching GBP/AUD daily data {min_date} → {max_date + timedelta(days=5)}...")

    try:
        price_data = fetch_daily_closes(min_date, max_date)
    except Exception as e:
        print(f"ERROR fetching price data: {e}")
        print("Check your internet connection and try again.")
        return

    if not price_data:
        print("No price data returned from yfinance. Check ticker or date range.")
        return

    print(f"Got {len(price_data)} trading days of data.")

    # Label each row
    labeled_count = 0
    for row in rows:
        run_date = row.get("date", "")
        if run_date >= today:
            continue  # don't label today — next_day_close not available yet
        if row.get("next_day_close", "").strip():
            continue  # already labeled

        try:
            entry_price = float(row.get("price", 0) or 0)
        except (ValueError, TypeError):
            entry_price = 0.0

        next_close, next_open = next_trading_day_close(run_date, price_data)

        if not next_close:
            print(f"  ⚠️  No next-day data for {run_date} — skipping")
            continue

        outcome = derive_outcome(row.get("bias", ""), entry_price, next_close)
        diff_pips = _to_pips(next_close - entry_price) if entry_price else 0

        if DRY_RUN:
            print(
                f"  {run_date}  bias={row.get('bias','?'):<8}  "
                f"entry={entry_price:.4f}  next_close={next_close:.4f}  "
                f"({'+' if next_close >= entry_price else '-'}{diff_pips}pips)  "
                f"→ {outcome}"
            )
        else:
            row["next_day_close"]  = f"{next_close:.4f}"
            row["next_london_open"] = f"{next_open:.4f}" if next_open else ""
            row["outcome_label"]   = outcome
            labeled_count += 1

    if DRY_RUN:
        print(f"\n[DRY RUN] No changes written. Remove --dry to apply.")
        return

    # Write back
    if labeled_count > 0:
        with open(JOURNAL_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Labeled {labeled_count} rows. Journal updated: {JOURNAL_PATH.name}")
    else:
        print("No rows needed updating.")

    # Summary of current label coverage
    with open(JOURNAL_PATH, newline="") as f:
        all_rows = list(csv.DictReader(f))
    labeled_total = sum(1 for r in all_rows if r.get("outcome_label","").strip())
    print(f"   Total labeled: {labeled_total} / {len(all_rows)}")


if __name__ == "__main__":
    label_outcomes()
