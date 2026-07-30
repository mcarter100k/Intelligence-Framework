#!/usr/bin/env python3
"""
notify.py
─────────
Runs the framework, evaluates grade, and fires a Mac notification
if the setup meets the threshold.

Usage:
    python notify.py                    # uses default threshold (B+ and above)
    python notify.py --threshold A      # only notify for A and A+
    python notify.py --force            # always notify regardless of grade
    python notify.py --test             # test notification without running framework

Called automatically by cron — never needs manual interaction.

Mac notification appears in top-right corner with sound.
Grade C and below → silent log only, no notification.
"""

import subprocess
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# ── Add framework directory to path ──────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# ── Config ────────────────────────────────────────────────────────────────────
LOG_FILE     = SCRIPT_DIR / "logs" / "notify.log"
GRADE_ORDER  = ["A+", "A", "B+", "B", "C"]
NOTIFY_SOUND = "Ping"   # Mac system sounds: Ping, Glass, Hero, Basso, Funk

# Circuit breaker — the trade journal it reads, and a nominal account balance.
# pnl_r is already stored as a percentage, so the balance only guards the
# balance<=0 case; set it to your real account size if you want it meaningful.
JOURNAL_FILE    = SCRIPT_DIR / "run_journal.csv"
ACCOUNT_BALANCE = 10_000

# Session names matched to cron run times (PT)
SESSION_LABELS = {
    "23":  "Pre-London",     # 11pm PT = midnight approaching
    "04":  "Pre-NY",         # 4am PT = NY about to open
    "13":  "NY-Close",       # 1pm PT = NY closing
}


def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts}  {msg}\n")
    print(f"{ts}  {msg}")


def _mac_notify(title: str, subtitle: str, message: str, sound: str = NOTIFY_SOUND) -> None:
    """Fire a native Mac notification via osascript."""
    # Use terminal-notifier if available (no Script Editor on click)
    # Falls back to osascript display notification
    try:
        result = subprocess.run(
            ["which", "terminal-notifier"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run([
                "terminal-notifier",
                "-title",    title,
                "-subtitle", subtitle,
                "-message",  message,
                "-sound",    sound,
                "-sender",   "com.apple.Terminal",
            ], check=True, capture_output=True)
            return
    except Exception:
        pass

    # Fallback: osascript — clicking opens Terminal (not Script Editor) if
    # we use the 'tell application "Terminal"' form
    script = (
        f'tell application "System Events"\n'
        f'  display notification "{message}" '
        f'with title "{title}" '
        f'subtitle "{subtitle}" '
        f'sound name "{sound}"\n'
        f'end tell'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    except Exception as e:
        _log(f"Notification failed: {e}")


def _grade_meets_threshold(grade: str, threshold: str) -> bool:
    """Return True if grade is at or above threshold."""
    if grade not in GRADE_ORDER or threshold not in GRADE_ORDER:
        return False
    return GRADE_ORDER.index(grade) <= GRADE_ORDER.index(threshold)


def _get_session_label() -> str:
    hour = datetime.now().strftime("%H")
    return SESSION_LABELS.get(hour, "Scheduled")


def _run_framework() -> dict:
    """Run market_brain and extract key fields for notification."""
    try:
        from market_brain import build_market_report

        report = build_market_report()

        setup  = report.get("setup", {})
        layers = report.get("layers", {})
        _sess_dict = layers.get("session", {})
        sess   = (
            _sess_dict.get("session_label") or
            _sess_dict.get("session") or
            "Unknown"
        )
        price  = layers.get("liquidity", {}).get("current_price")
        if price is None:
            try:
                from oanda_feed import get_live_price
                price = get_live_price()
            except Exception:
                price = None

        # ── Decision surface — sourced ONLY from the official, filter-gated
        # decision. notify no longer re-grades: report["decision"] already
        # applies the no-trade filter (STAND_DOWN → NO TRADE), so a blocked
        # setup can never surface as a tradeable alert, and the grade/direction
        # shown always match report["decision"] (one source of truth).
        decision   = report.get("decision", {})
        direction  = decision.get("direction", "NO TRADE")
        grade      = decision.get("grade", "C")
        conviction = decision.get("conviction", 0)
        size_mult  = float(decision.get("size_mult", 0.0) or 0.0)
        reason     = decision.get("reason", "")
        allowed    = direction in ("LONG", "SHORT")

        quality   = setup.get("quality", "LOW")   # informational only now
        wait_for  = setup.get("wait_for", "")
        primary   = report.get("primary_state", "UNKNOWN")
        bias      = report.get("overall_bias", "NEUTRAL")
        _ev_risk  = setup.get("event_risk", False)

        # Event-risk safety overlay — a high-impact news lockout forces NO TRADE
        # regardless of grade (the official path does not yet read the calendar).
        if _ev_risk:
            allowed   = False
            direction = "NO TRADE"
            reason    = reason or "Event risk — high-impact news lockout"

        # Standard risk for the official grade, scaled by the filter's size
        # multiplier (e.g. reduced-size counter-trend override). One grade,
        # one source — no parallel re-grading.
        from risk_config import GRADE_CONFIG
        _base_risk = GRADE_CONFIG.get(grade, {}).get("risk_pct", 0.0)
        risk_pct   = (round(_base_risk * (size_mult if size_mult > 0 else 1.0), 2)
                      if allowed else 0.0)
        label      = GRADE_CONFIG.get(grade, {}).get("label", "")

        # Proximity to trigger — extract price from wait_for text
        trigger_price = None
        try:
            import re
            nums = re.findall(r'1\.\d{3,4}', wait_for)
            if nums:
                trigger_price = float(nums[0])
        except Exception:
            pass

        proximity = None
        if price and trigger_price:
            proximity = round(abs(price - trigger_price) * 10000)  # pips

        return {
            "ok":           True,
            "grade":        grade,
            "direction":    direction,
            "risk_pct":     risk_pct,
            "label":        label,
            "reason":       reason,
            "quality":      quality,
            "alignment":    conviction,
            "session":      sess,
            "primary":      primary,
            "bias":         bias,
            "price":        price,
            "wait_for":     wait_for,
            "trigger_price": trigger_price,
            "proximity_pips": proximity,
            "event_risk":   _ev_risk,
            "allowed":      allowed,
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "grade": "C"}


def _build_notification_text(result: dict, session_label: str) -> tuple:
    """Build notification title, subtitle, message."""
    grade     = result.get("grade", "C")
    price     = result.get("price")
    primary   = result.get("primary", "")
    prox      = result.get("proximity_pips")
    risk_pct  = result.get("risk_pct", 0)
    session   = result.get("session", "")
    direction = result.get("direction", "NO TRADE")
    allowed   = result.get("allowed", False)

    # Title — grade and session
    title = f"GBP/AUD {grade} Setup — {session_label}"

    # Subtitle — primary state truncated
    subtitle = primary[:50] if primary else "Framework Alert"

    # Message — key numbers. Directional word comes from the OFFICIAL decision
    # (LONG/SHORT/NO TRADE), never the raw aggregate bias — so the alert can no
    # longer read "BULLISH | NO TRADE".
    price_str = f"Price: {price:.4f}" if price else "Price: N/A"
    prox_str  = f" | {prox}p to trigger" if prox is not None else ""
    dir_str   = f" | {direction}" if allowed else " | NO TRADE"
    risk_str  = f" | {risk_pct}% risk" if (allowed and risk_pct > 0) else ""

    message = f"{price_str}{prox_str}{dir_str}{risk_str}"

    return title, subtitle, message


def build_trade_card(result: dict, session_label: str = "") -> str:
    """
    Build a full plain-English trade card from the framework result.

    Plain English: this is what you read before placing the trade.
                   Every number is explained. Every decision is visible.
                   No jargon without a plain-English label next to it.

    Args:
        result       : dict from _run_framework() — grade, bias, price, etc.
        session_label: human-readable session name (e.g. "Pre-London")

    Returns a multi-line string ready to print or log.
    """
    W = 56
    grade    = result.get("grade",    "C")
    bias     = result.get("bias",     "NEUTRAL")
    price    = result.get("price")
    risk_pct = result.get("risk_pct", 0.0)
    session  = result.get("session",  session_label or "Unknown")
    prox     = result.get("proximity_pips")
    wait_for = result.get("wait_for", "")
    quality  = result.get("quality",  "")
    allowed  = result.get("allowed",  False)
    alignment = result.get("alignment", 0)

    icon = {"A+": "🔥", "A": "✅", "B+": "⚡", "B": "⚠️ ", "C": "🚫"}.get(grade, "❓")

    # Direction in plain English
    if bias == "BULLISH":
        direction_plain = "LONG  — buy GBP/AUD, profit if price RISES"
    elif bias == "BEARISH":
        direction_plain = "SHORT — sell GBP/AUD, profit if price FALLS"
    else:
        direction_plain = f"NEUTRAL — no clear direction ({bias})"

    lines = [
        "═" * W,
        f"  {icon} GBP/AUD FRAMEWORK ALERT — {session_label or session}",
        "═" * W,
    ]

    # Grade block
    grade_desc = {
        "A+": "Everything aligned — rare, maximum conviction",
        "A":  "Most signals aligned — standard size, let it run",
        "B+": "Bias clear, one or two things off — manage actively",
        "B":  "Conflicted signals — small size only",
        "C":  "Too many factors against — stand aside",
    }.get(grade, "Unknown grade")

    lines += [
        f"  Grade      : {grade}  ({grade_desc})",
        f"  Direction  : {direction_plain}",
        f"  Conviction : {alignment}  (quality: {quality})",
        f"  {'─' * (W - 4)}",
    ]

    # Price and proximity
    price_str = f"{price:.5f}" if price else "N/A"
    lines.append(f"  Live price : {price_str}")
    if prox is not None:
        lines.append(
            f"  To trigger : {prox} pips away"
            f"  {'← CLOSE' if prox <= 30 else ''}"
        )
    if wait_for:
        lines.append(f"  Watch for  : {wait_for}")

    lines.append(f"  {'─' * (W - 4)}")

    # Size
    if allowed and risk_pct > 0:
        lines.append(f"  Risk size  : {risk_pct}% of account per trade")
        lines.append(
            f"  Plain English: if you have $10,000, risk ${risk_pct * 100:.0f} on this trade"
        )
    else:
        lines.append(f"  Risk size  : NO TRADE — grade {grade} does not meet threshold")

    lines.append("═" * W)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GBP/AUD Framework Notifier")
    parser.add_argument("--threshold", default="B+",
                        choices=["A+", "A", "B+", "B"],
                        help="Minimum grade to trigger notification (default: B+)")
    parser.add_argument("--force",  action="store_true",
                        help="Always notify regardless of grade")
    parser.add_argument("--test",   action="store_true",
                        help="Send a test notification without running framework")
    parser.add_argument("--silent", action="store_true",
                        help="Log only, never notify (useful for NY-close run)")
    args = parser.parse_args()

    session_label = _get_session_label()
    _log(f"=== Framework run — {session_label} ===")

    # Test mode
    if args.test:
        _log("Test notification fired")
        _mac_notify(
            title    = "GBP/AUD Framework — Test",
            subtitle = "Notification system working",
            message  = "If you see this, cron + osascript are both working ✅"
        )
        return

    # Run framework
    _log("Running market_brain...")
    result = _run_framework()

    if not result.get("ok"):
        _log(f"Framework error: {result.get('error', 'unknown')}")
        if args.force:
            _mac_notify(
                title    = "GBP/AUD Framework — Error",
                subtitle = "Framework failed to run",
                message  = str(result.get("error", ""))[:100]
            )
        return

    # ── Circuit breaker — stand aside if today's risk limits are hit ──────────
    # Consulted BEFORE any setup alert. A HALTED/SESSION_CLOSED status suppresses
    # setup notifications for the rest of the day (--force still bypasses, for
    # testing). Reads the manually-journaled trade rows in run_journal.csv.
    try:
        from session_guard import get_session_status, STATUS_ACTIVE
        sg = get_session_status(JOURNAL_FILE, account_balance=ACCOUNT_BALANCE)
        if sg["status"] != STATUS_ACTIVE:
            _log(f"Circuit breaker {sg['status']}: {sg['reason']}")
            if not args.force:
                _log("Circuit breaker active — suppressing setup alerts today")
                return
    except Exception as _sg_err:
        # A failure in the guard itself must not silently permit trading; log it.
        _log(f"Circuit breaker check failed (permitting run): {_sg_err}")

    grade    = result.get("grade", "C")
    price    = result.get("price")
    prox     = result.get("proximity_pips")
    allowed  = result.get("allowed", False)

    _price_str = f"{price:.4f}" if price else "N/A"
    _log(
        f"Grade: {grade} | Alignment: {result.get('alignment')} | "
        f"Price: {_price_str} | "
        f"Proximity: {str(prox)+'p' if prox is not None else 'N/A'} | Session: {result.get('session')}"
    )

    # Decide whether to notify. A live alert requires the OFFICIAL decision to
    # be tradeable (`allowed`) — a NO TRADE / event-risk-suppressed setup never
    # fires, even if a stale grade remains attached.
    should_notify = (
        args.force or
        (not args.silent and allowed and _grade_meets_threshold(grade, args.threshold))
    )

    # Extra condition: proximity boost — notify if within 30 pips of trigger
    # (still requires a tradeable official decision at grade B or above)
    if (not args.silent and allowed and prox is not None and prox <= 30 and
            _grade_meets_threshold(grade, "B")):
        should_notify = True
        _log(f"Proximity alert: {prox} pips to trigger — overriding threshold")

    if should_notify:
        title, subtitle, message = _build_notification_text(result, session_label)
        _mac_notify(title, subtitle, message)
        _log(f"Notification sent: {title} | {message}")
    else:
        _log(f"Grade {grade} below threshold {args.threshold} — silent run")


if __name__ == "__main__":
    main()
