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
        from risk_config  import get_size_note

        report = build_market_report()

        setup  = report.get("setup", {})
        layers = report.get("layers", {})
        conf   = report.get("conviction_score", 0)
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

        quality   = setup.get("quality", "LOW")
        wait_for  = setup.get("wait_for", "")
        primary   = report.get("primary_state", "UNKNOWN")
        bias      = report.get("overall_bias", "NEUTRAL")

        # Get grade
        _ev_risk      = setup.get("event_risk", False)
        _sweep_dn     = layers.get("liquidity", {}).get("sweep_down", False)
        _sweep_up     = layers.get("liquidity", {}).get("sweep_up", False)
        _sweep_conf   = (_sweep_dn and bias == "BEARISH") or (_sweep_up and bias == "BULLISH")
        _val_al       = layers.get("value", {}).get("value_aligned", False)
        _htf_conflict = report.get("live_vs_structural_conflict", False)
        _htf_bias     = report.get("layers", {}).get("htf", {}).get("lt_trend", "")
        _is_counter   = (
            (_htf_bias == "DOWNTREND" and bias == "BULLISH") or
            (_htf_bias == "UPTREND"   and bias == "BEARISH")
        )

        size_info = get_size_note(
            quality          = quality,
            alignment        = conf,
            is_counter_trend = _is_counter,
            event_risk       = _ev_risk,
            session          = sess,
            sweep_confirmed  = _sweep_conf,
            is_value_aligned = _val_al,
            htf_conflict     = _htf_conflict,
        )

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
            "grade":        size_info.get("grade", "C"),
            "risk_pct":     size_info.get("risk_pct", 0),
            "label":        size_info.get("label", ""),
            "quality":      quality,
            "alignment":    conf,
            "session":      sess,
            "primary":      primary,
            "bias":         bias,
            "price":        price,
            "wait_for":     wait_for,
            "trigger_price": trigger_price,
            "proximity_pips": proximity,
            "event_risk":   _ev_risk,
            "allowed":      size_info.get("allowed", False),
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "grade": "C"}


def _build_notification_text(result: dict, session_label: str) -> tuple:
    """Build notification title, subtitle, message."""
    grade    = result.get("grade", "C")
    price    = result.get("price")
    primary  = result.get("primary", "")
    prox     = result.get("proximity_pips")
    risk_pct = result.get("risk_pct", 0)
    session  = result.get("session", "")
    bias     = result.get("bias", "")

    # Title — grade and session
    title = f"GBP/AUD {grade} Setup — {session_label}"

    # Subtitle — primary state truncated
    subtitle = primary[:50] if primary else "Framework Alert"

    # Message — key numbers
    price_str = f"Price: {price:.4f}" if price else "Price: N/A"
    prox_str  = f" | {prox}p to trigger" if prox is not None else ""
    bias_str  = f" | {bias}"
    risk_str  = f" | {risk_pct}% risk" if risk_pct > 0 else " | NO TRADE"

    message = f"{price_str}{prox_str}{bias_str}{risk_str}"

    return title, subtitle, message


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

    # Decide whether to notify
    should_notify = (
        args.force or
        (not args.silent and _grade_meets_threshold(grade, args.threshold))
    )

    # Extra condition: proximity boost — always notify if within 30 pips of trigger
    # regardless of grade (B or above)
    if (not args.silent and prox is not None and prox <= 30 and
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
