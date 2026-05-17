"""
review_runs.py
──────────────
Weekly review script for the GBP/AUD trading framework.

Usage:
    python review_runs.py

What it does:
  - Reads run_journal.csv
  - Answers high-value questions about setup quality, bias distribution,
    win rates (if outcomes are filled in), and journal health
  - Tells you what's missing rather than breaking

Run this once a week. Takes < 30 seconds.

HOW TO USE:
  1. Run your framework daily (python main.py)
  2. Each morning, open run_journal.csv and fill in:
     - next_day_close  (GBP/AUD price at next-day London open)
     - outcome_label   (WIN / LOSS / NEUTRAL — did price go in bias direction by >20 pips?)
     - trigger_fired   (YES / NO — did the trigger checklist conditions get met?)
     - trade_taken     (YES / NO — did you actually enter a trade?)
     - pnl_r           (result in R if trade taken, e.g. +1.5 or -1.0)
  3. Run this script weekly to see what's working
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


JOURNAL_PATH = Path(__file__).parent / "run_journal.csv"
W = 66


def _divider(char="="):
    print(char * W)


def _section(title: str):
    print()
    print("-" * W)
    print(f"  {title}")
    print("-" * W)


def _pct(num: int, denom: int) -> str:
    if denom == 0:
        return "n/a"
    return f"{round(num / denom * 100)}%"


def load_journal() -> list[dict]:
    if not JOURNAL_PATH.exists():
        print(f"\n  No journal found at: {JOURNAL_PATH}")
        print("  Run `python main.py` at least once to create it.")
        sys.exit(0)

    with open(JOURNAL_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return rows


def review():
    rows = load_journal()
    total = len(rows)

    _divider()
    print(f"  GBP/AUD FRAMEWORK — WEEKLY REVIEW")
    print(f"  Journal: {JOURNAL_PATH.name}  |  {total} runs recorded")
    _divider()

    if total == 0:
        print("  No runs recorded yet.")
        return

    # Date range
    dates = [r.get("date", "") for r in rows if r.get("date")]
    if dates:
        print(f"  Period: {min(dates)}  →  {max(dates)}")

    # ── 1. Journal health ────────────────────────────────────────────────────
    _section("1. JOURNAL HEALTH")

    outcome_filled    = sum(1 for r in rows if r.get("outcome_label","").strip() not in ("","n/a"))
    trigger_filled    = sum(1 for r in rows if r.get("trigger_fired","").strip() not in ("","n/a"))
    trade_filled      = sum(1 for r in rows if r.get("trade_taken","").strip() not in ("","n/a"))
    next_close_filled = sum(1 for r in rows if r.get("next_day_close","").strip() not in ("","n/a"))

    print(f"  Runs with outcome_label filled   : {outcome_filled} / {total}  {_pct(outcome_filled, total)}")
    print(f"  Runs with next_day_close filled  : {next_close_filled} / {total}  {_pct(next_close_filled, total)}")
    print(f"  Runs with trigger_fired filled   : {trigger_filled} / {total}  {_pct(trigger_filled, total)}")
    print(f"  Runs with trade_taken filled     : {trade_filled} / {total}  {_pct(trade_filled, total)}")

    if outcome_filled < 10:
        print()
        print(f"  ⚠️  Less than 10 outcomes filled — review stats below are limited.")
        print(f"  Fill in outcome_label daily for meaningful analysis.")

    # ── 2. Action / primary state distribution ───────────────────────────────
    _section("2. WHAT THE FRAMEWORK SAID")

    action_counts = Counter(r.get("action","UNKNOWN") for r in rows)
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 30)
        print(f"  {action:<30}  {count:>3}  {_pct(count, total):>5}  {bar}")

    print()
    quality_counts = Counter(r.get("quality", r.get("quality_tier","?")) for r in rows)
    for q in ["HIGH", "MEDIUM", "LOW", "DO NOT TRADE"]:
        c = quality_counts.get(q, 0)
        print(f"  Quality {q:<12}  {c:>3}  {_pct(c, total):>5}")

    # ── 3. Setup type distribution ───────────────────────────────────────────
    _section("3. SETUP TYPES SEEN")

    setup_counts = Counter(r.get("setup_type", r.get("htf_context","?")) for r in rows)
    for setup, count in sorted(setup_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 25)
        print(f"  {setup[:40]:<40}  {count:>3}  {bar}")

    # ── 4. Win rates by quality (if outcomes exist) ──────────────────────────
    _section("4. WIN RATE BY QUALITY  (needs outcome_label filled)")

    rows_with_outcomes = [r for r in rows if r.get("outcome_label","").strip().upper() in ("WIN","LOSS","NEUTRAL")]
    if len(rows_with_outcomes) < 5:
        print(f"  Only {len(rows_with_outcomes)} outcomes filled — need at least 5 for meaningful stats.")
        print("  Fill in outcome_label (WIN / LOSS / NEUTRAL) daily.")
    else:
        by_quality: dict[str, list] = defaultdict(list)
        for r in rows_with_outcomes:
            q      = r.get("quality", r.get("quality_tier","?"))
            label  = r.get("outcome_label","").strip().upper()
            by_quality[q].append(label)

        for q in ["HIGH", "MEDIUM", "LOW"]:
            outcomes = by_quality[q]
            if not outcomes:
                continue
            wins  = outcomes.count("WIN")
            total_q = len(outcomes)
            print(f"  {q:<8}  {wins}/{total_q} correct  ({_pct(wins, total_q)})")

    # ── 5. Win rate by alignment score buckets ───────────────────────────────
    _section("5. WIN RATE BY ALIGNMENT SCORE  (needs outcome_label filled)")

    if len(rows_with_outcomes) < 10:
        print(f"  Need more outcomes to bucket by alignment score.")
    else:
        buckets: dict[str, list] = defaultdict(list)
        for r in rows_with_outcomes:
            try:
                score = int(float(r.get("conviction_score","0") or 0))
            except (ValueError, TypeError):
                score = 0
            bucket = "60-100" if score >= 60 else "40-59" if score >= 40 else "0-39"
            label  = r.get("outcome_label","").strip().upper()
            buckets[bucket].append(label)

        for bucket in ["60-100", "40-59", "0-39"]:
            outcomes = buckets[bucket]
            if not outcomes:
                continue
            wins = outcomes.count("WIN")
            print(f"  Alignment {bucket}  {wins}/{len(outcomes)} correct  ({_pct(wins, len(outcomes))})")

    # ── 6. Value alignment effect ────────────────────────────────────────────
    _section("6. VALUE ALIGNMENT EFFECT  (needs outcome_label filled)")

    if len(rows_with_outcomes) < 10:
        print("  Need more outcomes to measure value alignment effect.")
    else:
        aligned     = [r for r in rows_with_outcomes if r.get("value_aligned","").upper() == "YES"]
        misaligned  = [r for r in rows_with_outcomes if r.get("value_aligned","").upper() == "NO"]
        a_wins      = sum(1 for r in aligned    if r.get("outcome_label","").upper() == "WIN")
        m_wins      = sum(1 for r in misaligned if r.get("outcome_label","").upper() == "WIN")
        print(f"  Aligned location    : {a_wins}/{len(aligned)} correct  ({_pct(a_wins, len(aligned))})")
        print(f"  Misaligned location : {m_wins}/{len(misaligned)} correct  ({_pct(m_wins, len(misaligned))})")
        if len(aligned) >= 5 and len(misaligned) >= 5:
            edge = round(a_wins/len(aligned)*100 - m_wins/len(misaligned)*100) if len(misaligned) > 0 else 0
            if edge > 5:
                print(f"  ✅ Location alignment adds ~{edge}% accuracy — important signal")
            elif edge < -5:
                print(f"  ⚠️  Misaligned entries outperforming — review location logic")
            else:
                print(f"  Location alignment effect: small ({edge}%) — need more data")

    # ── 7. Trade discipline ──────────────────────────────────────────────────
    _section("7. TRADE DISCIPLINE  (needs trade_taken filled)")

    took_trades    = [r for r in rows if r.get("trade_taken","").upper() == "YES"]
    skipped_trades = [r for r in rows if r.get("trade_taken","").upper() == "NO"]

    if not took_trades and not skipped_trades:
        print("  trade_taken column not filled yet — fill YES/NO daily.")
    else:
        print(f"  Trades taken  : {len(took_trades)}")
        print(f"  Trades skipped: {len(skipped_trades)}")

        # Trades taken vs framework action
        took_when_wait = [r for r in took_trades if "WAIT" in r.get("action","").upper()]
        took_when_act  = [r for r in took_trades if "LOOK FOR" in r.get("action","").upper()]
        if took_when_wait:
            print(f"  ⚠️  Took {len(took_when_wait)} trades when framework said WAIT — review discipline")
        if took_when_act:
            print(f"  ✅ {len(took_when_act)} trades taken when framework said LOOK FOR — aligned")

        # P&L in R if available
        pnl_rows = [r for r in took_trades if r.get("pnl_r","").strip() not in ("","n/a")]
        if pnl_rows:
            try:
                pnl_values = [float(r["pnl_r"]) for r in pnl_rows]
                total_r    = round(sum(pnl_values), 2)
                win_trades = [v for v in pnl_values if v > 0]
                loss_trades = [v for v in pnl_values if v <= 0]
                print()
                print(f"  P&L ({len(pnl_values)} trades):  {total_r:+.2f}R total")
                print(f"  Win trades   : {len(win_trades)}  |  Avg: {round(sum(win_trades)/len(win_trades),2) if win_trades else 0:+.2f}R")
                print(f"  Loss trades  : {len(loss_trades)}  |  Avg: {round(sum(loss_trades)/len(loss_trades),2) if loss_trades else 0:+.2f}R")
            except (ValueError, TypeError):
                pass

    # ── 8. Recent bias summary (last 5 runs) ─────────────────────────────────
    _section("8. RECENT RUNS (last 5)")

    recent = rows[-5:]
    for r in recent:
        date   = r.get("date","?")
        time   = r.get("time_utc","?")
        action = r.get("action","?")[:25]
        qual   = r.get("quality", r.get("quality_tier","?"))
        price  = r.get("price","?")
        outcome = r.get("outcome_label","—")
        print(f"  {date} {time}  {qual:<8}  {action:<30}  {price:<8}  {outcome}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    _divider()
    print(f"  NEXT STEPS")
    _divider()
    to_fill = total - outcome_filled
    if to_fill > 0:
        print(f"  → Fill in outcome_label for {to_fill} runs  (open run_journal.csv)")
    if trade_filled < total // 2:
        print(f"  → Fill in trade_taken (YES/NO) for past runs")
    if outcome_filled >= 20:
        print(f"  → You have {outcome_filled} outcomes — enough to see early patterns")
    if outcome_filled >= 50:
        print(f"  ✅ {outcome_filled} outcomes — statistically meaningful for quality-tier analysis")
    print()


if __name__ == "__main__":
    review()
