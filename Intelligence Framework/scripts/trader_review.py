"""
trader_review.py — the trader review loop (foundation/trader_review.md).

Grades the trader, not the model. Three commands, run from the
Intelligence Framework folder:

  python3 scripts/trader_review.py idea     log an idea, taken OR passed
  python3 scripts/trader_review.py score    score an idea once it is over
  python3 scripts/trader_review.py list     ideas still waiting for a score
  python3 scripts/trader_review.py review [--week 2026-W45] [--no-write]
                                            the weekly review

Reuses, never duplicates:
  setup_check.py   the framework's read at the time (its pre_trade_journal.csv
                   row for the same pair and direction, if run in the last
                   6 hours); otherwise the latest brief's DECISION line
  trade_logger.py  real fills: a taken idea is scored ONLY from its
                   trades.csv OPEN + CLOSE rows, never from memory
  trade_management after-spread reward-to-risk (get_management_plan),
                   pip size and the round-trip spread assumption
  risk_config      the grade -> risk % table
  ledger_io        every write (append_row under locked)
  exclusions       candidate rows authorized out of every tally
  display_time     Pacific display; weeks are Monday-Sunday Pacific

Ledgers (cwd-relative, gitignored, append-only):
  idea_journal.csv       TWO-ROW: an IDEA row when logged, a SCORE row when
                         scored. Scoring never edits the IDEA row. A re-score
                         appends a new SCORE row; the latest one counts.
  trader_review_log.csv  one row per week: the numbers, ONE lesson and AT MOST
                         ONE rule change. A week that has not ended cannot be
                         written (no mid-week rule changes), and a week is
                         written once.

Sends no notifications (AGENTS.md rule 12).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_PROJECT, os.path.join(_PROJECT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# cwd-relative on purpose: reality_run and the test suite run from a temp
# directory holding copies, so nothing here can reach the real ledgers.
IDEAS_FILE = "idea_journal.csv"
REVIEWS_FILE = "trader_review_log.csv"
STACK_FILE = "pre_trade_journal.csv"
TRADES_FILE = "trades.csv"
NOTIFY_FILE = "notification_log.csv"
SHADOW_FILE = "shadow_signal_log.csv"
SIGNAL_FILE = "trade_signal_log.csv"
BRIEF_FILE = os.path.join("logs", "latest_brief.log")
# Written by every scheduled brief. Its presence is how the tool knows it is
# running in the project folder (or a reality_run copy of it), so an idea is
# never journaled into a stray file somewhere else.
_HOME_MARKER = "session_context_log.csv"

PAIRS = ("GBP_AUD", "GBP_JPY")
PLAYS = ("first-pullback", "base-break", "coil-break", "retest-fade",
         "none-named")
STATES = ("calm", "rushed", "revenge", "FOMO", "bored")
EXIT_REASONS = ("target", "stop", "invalidation", "discretionary", "time")
# Plain words on screen, the design's loss-species codes in the ledger.
LOSS_SPECIES = {"news": "event_window", "stopped-then-reversed": "stopped_then_reversed",
                "chased": "exhaustion_entry", "never-went-my-way": "never_onside",
                "bled-out": "bled_out", "other": "other"}
RULE_BREAKS = ("moved stop", "skipped partial", "sized up", "entered early",
               "other")
PROCESS_QUESTIONS = (
    ("process_plan_complete", "Was the plan complete before entry"),
    ("process_size_per_grade", "Was the size right for the grade"),
    ("process_stop_untouched", "Was the stop left alone (never widened)"),
    ("process_partial_at_1r", "Did you take half off at +1R (yes if it never reached +1R)"),
    ("process_exit_by_rule", "Did you exit by your rule"),
)
STACK_MAX_AGE_HOURS = 6
MIN_N_FOR_CLAIMS = 20            # trader_review.md §5

IDEA_FIELDS = [
    "row_type", "idea_id", "timestamp_utc", "pair", "direction", "play",
    "zone", "trigger", "entry", "stop", "target", "planned_rr_after_spread",
    "grade", "risk_pct", "taken", "pass_reason", "pre_trade_state",
    "framework_read", "framework_read_source", "agrees_with_framework",
    "stack_id", "note",
    "position_id", "exit_price", "exit_reason", "scored_on", "r_realized",
    "mfe_r", "mae_r", "rule_breaks", "loss_species",
    *[k for k, _ in PROCESS_QUESTIONS], "process_score",
]
REVIEW_FIELDS = [
    "week", "written_utc", "ideas", "taken", "passed", "against_framework",
    "read_not_recorded", "taken_scored", "taken_avg_r", "taken_median_r",
    "taken_win_pct", "process_avg", "paper_scored", "paper_avg_r",
    "top_rule_break", "notifications_total", "notifications_material",
    "lesson", "rule_change", "applies_from",
]


class NotInProject(RuntimeError):
    pass


# ── small helpers ─────────────────────────────────────────────────────────────

def _read(path: str) -> Optional[List[Dict]]:
    """Rows, or None when the file does not exist (path not proven here)."""
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append(path: str, fields: List[str], row: Dict) -> None:
    from ledger_io import append_row, locked
    with locked(path):
        append_row(path, fields, {k: row.get(k, "") for k in fields})


def _parse_ts(s: str) -> Optional[datetime]:
    s = (s or "").strip().replace(" ", "T")
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _f(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pip(pair: str) -> float:
    from trade_management import _pip_factor
    return 1.0 / _pip_factor(pair)


def _spread_price(pair: str) -> float:
    from trade_management import SPREAD_PIPS
    return SPREAD_PIPS * _pip(pair)


def require_project_dir() -> None:
    if not os.path.exists(_HOME_MARKER):
        raise NotInProject(
            "Run this from the Intelligence Framework folder (it holds "
            f"{_HOME_MARKER}). Nothing was written.")


# ── R, process, weeks: the pure arithmetic ───────────────────────────────────

def r_multiple(direction: str, entry: float, stop: float, exit_price: float,
               cost: float = 0.0) -> float:
    """sign·(exit − entry − cost)/|entry − stop|. The stop defines R."""
    risk = abs(entry - stop)
    if risk == 0:
        raise ValueError("entry equals stop: R is undefined")
    sign = 1.0 if direction == "LONG" else -1.0
    return round((sign * (exit_price - entry) - cost) / risk, 3)


def excursion_r(direction: str, entry: float, stop: float, price: float) -> float:
    """How far a price is from entry in R, in the trade's favour (+) or against (−)."""
    sign = 1.0 if direction == "LONG" else -1.0
    return round(sign * (price - entry) / abs(entry - stop), 3)


def process_score(answers: Dict[str, bool]) -> float:
    """One point per rule followed, divided by 5 (trader_review.md §3)."""
    return round(sum(1 for k, _ in PROCESS_QUESTIONS if answers.get(k)) / 5, 2)


def week_of(ts: datetime) -> str:
    from display_time import display_zone
    y, w, _ = ts.astimezone(display_zone()).isocalendar()
    return f"{y}-W{w:02d}"


def week_monday(week: str) -> date:
    m = re.fullmatch(r"(\d{4})-W(\d{2})", week or "")
    if not m:
        raise ValueError(f"week must look like 2026-W45, got {week!r}")
    return date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)


def default_review_week(now: datetime) -> str:
    """Saturday or Sunday: this week. Monday to Friday: last week."""
    from display_time import display_zone
    local = now.astimezone(display_zone())
    if local.weekday() >= 5:
        return week_of(now)
    return week_of(now - timedelta(days=7))


def week_is_over(week: str, now: datetime) -> bool:
    """The trading week ends Friday afternoon Pacific; a review may be written
    from the Saturday of that week."""
    from display_time import display_zone
    saturday = week_monday(week) + timedelta(days=5)
    return now.astimezone(display_zone()).date() >= saturday


# ── the framework's read at the time ─────────────────────────────────────────

def framework_read(pair: str, direction: str, now: datetime) -> Dict[str, str]:
    """Prefers a setup_check row for this pair and direction from the last
    STACK_MAX_AGE_HOURS; else the latest brief's DECISION. When neither is
    found it says so: 'not recorded' is never counted as a disagreement."""
    rows = _read(STACK_FILE) or []
    for r in reversed(rows):
        ts = _parse_ts(r.get("timestamp", ""))
        if (r.get("instrument") == pair and r.get("direction") == direction
                and ts and timedelta(0) <= now - ts
                <= timedelta(hours=STACK_MAX_AGE_HOURS)):
            fw = (r.get("framework_direction") or "").strip()
            grade = (r.get("framework_grade") or "").strip()
            against = (r.get("against_framework") or "").strip().lower()
            return {
                "framework_read": f"{fw} (grade {grade})" if grade else fw,
                "framework_read_source": f"pre-trade check {r.get('stack_id', '')}",
                "agrees_with_framework": ("NO" if against == "true" else
                                          "YES" if against == "false" else ""),
                "stack_id": r.get("stack_id", ""),
            }
    if os.path.exists(BRIEF_FILE):
        from daily_digest import _ERROR, _sections, pair_decisions
        text = open(BRIEF_FILE, encoding="utf-8").read()
        head = re.search(r"^LATEST RUN — (.+)$", text, re.M)
        name = pair.replace("_", "/")
        # An error page renders "DECISION STAND ASIDE" too: a failed run is no
        # read at all, never a stand-aside to agree or disagree with (team
        # review 2026-11-05, defect 7).
        if any(n == name and _ERROR.search(block) for n, block in _sections(text)):
            return {"framework_read": "not recorded (the latest brief run failed)",
                    "framework_read_source":
                        f"brief of {head.group(1) if head else 'unknown time'}",
                    "agrees_with_framework": "", "stack_id": ""}
        for d in pair_decisions(text):
            if d.startswith(name + " "):
                call = d[len(name) + 1:]
                if call == "?":
                    break
                agrees = ("YES" if call == direction else "NO")
                return {
                    "framework_read": call,
                    "framework_read_source":
                        f"brief of {head.group(1) if head else 'unknown time'}",
                    "agrees_with_framework": agrees,
                    "stack_id": "",
                }
    return {"framework_read": "not recorded",
            "framework_read_source": "no pre-trade check in the last "
                                     f"{STACK_MAX_AGE_HOURS} hours and no brief log here",
            "agrees_with_framework": "", "stack_id": ""}


# ── prompts ──────────────────────────────────────────────────────────────────

Ask = Callable[[str], str]


def _choose(ask: Ask, prompt: str, options, allow_blank=False) -> str:
    lower = {o.lower(): o for o in options}
    while True:
        raw = ask(f"  {prompt} ({' / '.join(options)}): ").strip()
        if not raw and allow_blank:
            return ""
        if raw.lower() in lower:
            return lower[raw.lower()]
        print(f"  Please enter one of: {' / '.join(options)}")


def _number(ask: Ask, prompt: str, allow_blank=False) -> Optional[float]:
    while True:
        raw = ask(f"  {prompt}: ").strip()
        if not raw and allow_blank:
            return None
        v = _f(raw)
        if v is not None:
            return v
        print("  Enter a number, e.g. 212.17" + (" (or leave blank)" if allow_blank else ""))


def _text(ask: Ask, prompt: str, required=False) -> str:
    while True:
        raw = ask(f"  {prompt}: ").strip()
        if raw or not required:
            return raw
        print("  This one needs an answer.")


def _yes(ask: Ask, prompt: str) -> bool:
    return _choose(ask, prompt, ("yes", "no")) == "yes"


# ── idea ─────────────────────────────────────────────────────────────────────

def log_idea(ask: Ask = input, now: Optional[datetime] = None) -> Dict:
    from risk_config import GRADE_CONFIG
    from trade_management import get_management_plan
    require_project_dir()
    now = now or _now()
    print(f"\n  {'─' * 56}\n  LOG AN IDEA — taken or passed, every one counts\n  {'─' * 56}")
    pair = _choose(ask, "Pair", PAIRS)
    direction = _choose(ask, "Direction", ("LONG", "SHORT"))
    play = _choose(ask, "Play", PLAYS)
    zone = _text(ask, "Zone you are watching (e.g. 212.0-212.2)")
    trigger = _text(ask, "What has to happen before you enter")
    while True:
        entry = _number(ask, "Planned entry price")
        stop = _number(ask, "Stop price (where the idea is wrong)")
        target = _number(ask, "Target price")
        ok = (stop < entry < target) if direction == "LONG" else (target < entry < stop)
        if ok:
            break
        side = "below entry, target above" if direction == "LONG" else "above entry, target below"
        print(f"  For a {direction} the stop goes {side}. Try again.")
    grade = _choose(ask, "Your grade", tuple(GRADE_CONFIG))
    plan = get_management_plan(entry, stop, target, direction, grade=grade,
                               instrument=pair)
    rr = plan.get("effective_rr", "")
    print(f"  Reward to risk after the spread: {rr} to 1"
          + ("" if plan.get("valid") else "  (below the 1.5 minimum — recorded anyway)"))
    taken = _yes(ask, "Are you taking it")
    pass_reason = "" if taken else _text(ask, "Why are you passing", required=True)
    state = _choose(ask, "How are you feeling right now", STATES)
    note = _text(ask, "Anything else (optional)")

    fw = framework_read(pair, direction, now)
    row = {
        "row_type": "IDEA",
        "idea_id": f"{now.strftime('%Y%m%dT%H%M%SZ')}_{pair}_{direction}",
        "timestamp_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pair": pair, "direction": direction, "play": play, "zone": zone,
        "trigger": trigger, "entry": entry, "stop": stop, "target": target,
        "planned_rr_after_spread": rr, "grade": grade,
        "risk_pct": GRADE_CONFIG[grade]["risk_pct"],
        "taken": "YES" if taken else "NO", "pass_reason": pass_reason,
        "pre_trade_state": state, "note": note, **fw,
    }
    _append(IDEAS_FILE, IDEA_FIELDS, row)
    print(f"\n  Recorded idea {row['idea_id']}")
    print(f"  Framework's read: {fw['framework_read']} ({fw['framework_read_source']})")
    if fw["agrees_with_framework"] == "NO":
        print("  You are against the framework's read. That is allowed, and it is in the record.")
    if taken and grade == "C":
        print("  Grade C means no trade by the rules. If you take it, the review will show it.")
    if taken:
        print("  When you enter: python3 trade_logger.py open   (your real fill)")
    print("  When it is over: python3 scripts/trader_review.py score\n")
    return row


# ── score ────────────────────────────────────────────────────────────────────

def latest_rows(rows: List[Dict]) -> Dict[str, Dict]:
    """idea_id -> {"idea": IDEA row, "score": latest SCORE row or None}."""
    out: Dict[str, Dict] = {}
    for r in rows:
        if r.get("row_type") == "IDEA":
            out[r["idea_id"]] = {"idea": r, "score": None}
        elif r.get("row_type") == "SCORE" and r.get("idea_id") in out:
            out[r["idea_id"]]["score"] = r
    return out


def find_fill(idea: Dict, position_id: str = "") -> Optional[Dict]:
    """The trades.csv OPEN and CLOSE rows for this idea: the given position,
    or the newest closed position on the same pair and direction opened
    after the idea was logged."""
    rows = _read(TRADES_FILE) or []
    opens = {r["position_id"]: r for r in rows if r.get("row_type") == "OPEN"}
    closes = {r["position_id"]: r for r in rows if r.get("row_type") == "CLOSE"}
    if position_id:
        pid = position_id.upper()
        return ({"open": opens[pid], "close": closes[pid]}
                if pid in opens and pid in closes else None)
    t0 = _parse_ts(idea.get("timestamp_utc", ""))
    best = None
    for pid, o in opens.items():
        to = _parse_ts(o.get("timestamp_utc", ""))
        if (pid in closes and o.get("instrument") == idea["pair"]
                and o.get("direction") == idea["direction"]
                and t0 and to and to >= t0):
            best = {"open": o, "close": closes[pid]}
    return best


def score_idea(ask: Ask = input, now: Optional[datetime] = None,
               idea_id: str = "") -> Optional[Dict]:
    require_project_dir()
    now = now or _now()
    ideas = latest_rows(_read(IDEAS_FILE) or [])
    if not ideas:
        print("\n  No ideas logged yet. Start with: python3 scripts/trader_review.py idea\n")
        return None
    if not idea_id:
        waiting = [k for k, v in ideas.items() if v["score"] is None]
        for k in waiting:
            i = ideas[k]["idea"]
            print(f"    {k}  {'taken' if i['taken'] == 'YES' else 'passed'}"
                  f"  entry {i['entry']} stop {i['stop']} target {i['target']}")
        default = waiting[-1] if len(waiting) == 1 else ""
        idea_id = _text(ask, "Idea id to score" + (f" [{default}]" if default else "")) or default
    if idea_id not in ideas:
        print(f"  '{idea_id}' is not a logged idea.")
        return None
    idea = ideas[idea_id]["idea"]
    if ideas[idea_id]["score"] is not None:
        print("  This idea already has a score. A new score is appended; the latest one counts.")
    pair, direction = idea["pair"], idea["direction"]
    row = {"row_type": "SCORE", "idea_id": idea_id,
           "timestamp_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "pair": pair, "direction": direction}

    if idea["taken"] == "YES":
        pid = _text(ask, "Position id from trades.csv (Enter = find it)")
        fill = find_fill(idea, pid)
        if fill is None:
            print("  No closed trade found in trades.csv for this idea. Record the real\n"
                  "  fill first (python3 trade_logger.py open / close), then score it.\n"
                  "  A taken trade is never scored from memory.")
            return None
        o, c = fill["open"], fill["close"]
        entry, stop, exit_price = float(o["open_price"]), float(o["stop"]), float(c["close_price"])
        row.update(position_id=o["position_id"], exit_price=exit_price,
                   scored_on="FILL (trades.csv)",
                   r_realized=r_multiple(direction, entry, stop, exit_price))
        answers = {k: _yes(ask, q) for k, q in PROCESS_QUESTIONS}
        row.update({k: "YES" if v else "NO" for k, v in answers.items()})
        row["process_score"] = process_score(answers)
        breaks = _text(ask, "Rules broken, separated by ';' "
                            f"({' / '.join(RULE_BREAKS)}), or blank for none")
        row["rule_breaks"] = breaks
    else:
        entry, stop = float(idea["entry"]), float(idea["stop"])
        if not _yes(ask, f"Did price reach your entry at {idea['entry']}"):
            row.update(scored_on="PAPER: never filled", exit_reason="not filled")
            _append(IDEAS_FILE, IDEA_FIELDS, row)
            print("\n  Scored: it never filled, so there is no result to count.\n")
            return row
        exit_price = _number(ask, "Where would your plan have exited")
        row.update(exit_price=exit_price,
                   scored_on=f"PAPER: plan prices less the {_spread_price(pair) / _pip(pair):.0f}-pip spread",
                   r_realized=r_multiple(direction, entry, stop, exit_price,
                                         cost=_spread_price(pair)))
    row["exit_reason"] = _choose(ask, "Exit reason", EXIT_REASONS)
    best = _number(ask, "Best price while it was on (blank to skip)", allow_blank=True)
    worst = _number(ask, "Worst price while it was on (blank to skip)", allow_blank=True)
    if best is not None:
        row["mfe_r"] = excursion_r(direction, entry, stop, best)
    if worst is not None:
        row["mae_r"] = excursion_r(direction, entry, stop, worst)
    if float(row["r_realized"]) < 0:
        row["loss_species"] = LOSS_SPECIES[_choose(ask, "What kind of loss", tuple(LOSS_SPECIES))]
    _append(IDEAS_FILE, IDEA_FIELDS, row)
    print(f"\n  Scored {idea_id}: {float(row['r_realized']):+.2f}R ({row['scored_on']})"
          + (f", process {row['process_score']}" if "process_score" in row else "") + "\n")
    return row


def list_waiting() -> List[str]:
    require_project_dir()
    ideas = latest_rows(_read(IDEAS_FILE) or [])
    waiting = [k for k, v in ideas.items() if v["score"] is None]
    if not ideas:
        print("\n  No ideas logged yet.\n")
    elif not waiting:
        print(f"\n  All {len(ideas)} ideas are scored.\n")
    else:
        print(f"\n  Waiting for a score ({len(waiting)}):")
        for k in waiting:
            print(f"    {k}  {'taken' if ideas[k]['idea']['taken'] == 'YES' else 'passed'}")
        print()
    return waiting


# ── weekly review ────────────────────────────────────────────────────────────

def _in_week(ts: str, week: str) -> bool:
    dt = _parse_ts(ts)
    return bool(dt) and week_of(dt) == week


def _avg(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 3) if xs else None


def week_numbers(week: str) -> Dict:
    """Everything for review steps 1-6, from the ledgers in the current
    directory. A missing ledger is reported as such, never as a zero."""
    rows = _read(IDEAS_FILE)
    ideas = latest_rows(rows or [])
    wk = [v for v in ideas.values() if _in_week(v["idea"]["timestamp_utc"], week)]
    taken = [v for v in wk if v["idea"]["taken"] == "YES"]
    passed = [v for v in wk if v["idea"]["taken"] == "NO"]
    t_scored = [v for v in taken if v["score"] and _f(v["score"]["r_realized"]) is not None]
    p_scored = [v for v in passed if v["score"] and _f(v["score"]["r_realized"]) is not None]
    t_r = [float(v["score"]["r_realized"]) for v in t_scored]
    p_r = [float(v["score"]["r_realized"]) for v in p_scored]
    proc = [float(v["score"]["process_score"]) for v in t_scored
            if _f(v["score"].get("process_score")) is not None]
    breaks: Dict[str, int] = {}
    by_state: Dict[str, int] = {}
    for v in t_scored:
        for b in filter(None, (x.strip() for x in v["score"].get("rule_breaks", "").split(";"))):
            breaks[b] = breaks.get(b, 0) + 1
            st = v["idea"].get("pre_trade_state", "")
            by_state[f"{b} while {st}"] = by_state.get(f"{b} while {st}", 0) + 1
    all_taken_r = [float(v["score"]["r_realized"]) for v in ideas.values()
                   if v["idea"]["taken"] == "YES" and v["score"]
                   and _f(v["score"]["r_realized"]) is not None]

    notes = _read(NOTIFY_FILE)
    shadow = _read(SHADOW_FILE)
    signals = _read(SIGNAL_FILE)
    if shadow is not None:
        from exclusions import filter_rows
        shadow = filter_rows(shadow, "shadow_signal_log.csv")
    sh_wk = [r for r in (shadow or []) if _in_week(r.get("timestamp", ""), week)]
    sh_graded = [float(r["r_multiple"]) for r in sh_wk if _f(r.get("r_multiple")) is not None]
    sg_wk = [r for r in (signals or []) if _in_week(r.get("timestamp", ""), week)]

    return {
        "week": week,
        "journal_exists": rows is not None,
        "ideas": len(wk), "taken": len(taken), "passed": len(passed),
        # A TRADE against the framework's read (taken ideas only); a missing
        # read is counted on its own, never as agreement or disagreement.
        "against_framework": sum(1 for v in taken if v["idea"].get("agrees_with_framework") == "NO"),
        "read_not_recorded": sum(1 for v in wk if not v["idea"].get("agrees_with_framework")),
        "taken_unscored": len(taken) - len(t_scored),
        "taken_scored": len(t_scored), "taken_avg_r": _avg(t_r),
        "taken_median_r": round(statistics.median(t_r), 3) if t_r else None,
        "taken_win_pct": round(100 * sum(1 for x in t_r if x > 0) / len(t_r)) if t_r else None,
        "process_avg": _avg(proc),
        "paper_scored": len(p_scored), "paper_avg_r": _avg(p_r),
        "paper_never_filled": sum(1 for v in passed if v["score"]
                                  and v["score"].get("scored_on", "").startswith("PAPER: never")),
        "breaks": breaks, "breaks_by_state": by_state,
        "top_rule_break": max(breaks, key=breaks.get) if breaks else "",
        "all_taken_r": all_taken_r,
        "notifications_total": (sum(1 for r in notes if _in_week(r.get("timestamp_utc", ""), week))
                                if notes is not None else None),
        "candidates_fired": len(sh_wk) if shadow is not None else None,
        "candidates_graded_r": sh_graded,
        "framework_calls": len(sg_wk) if signals is not None else None,
    }


def _r(x) -> str:
    return "—" if x is None else f"{x:+.2f}R"


def render_review(n: Dict) -> str:
    mon = week_monday(n["week"])
    L = [f"  WEEKLY REVIEW  {n['week']}  (Mon {mon:%d %b} – Sun {mon + timedelta(days=6):%d %b}, Pacific)",
         "  " + "─" * 60]
    if not n["journal_exists"]:
        L.append("  1 IDEAS     No idea journal here yet: the loop has not started, so there is\n"
                 "              nothing to count (not the same as a week with no ideas).")
    else:
        L.append(f"  1 IDEAS     {n['ideas']} logged: {n['taken']} taken, {n['passed']} passed. "
                 f"Trades against the framework's read: {n['against_framework']}"
                 + (f"; framework read not recorded for {n['read_not_recorded']}"
                    if n["read_not_recorded"] else "") + ".")
        if n["taken"] == 0:
            L.append("  2 TAKEN     No trades taken this week.")
        else:
            L.append(f"  2 TAKEN     {n['taken_scored']} scored"
                     + (f" ({n['taken_unscored']} still waiting for a score)" if n["taken_unscored"] else "")
                     + f". Average {_r(n['taken_avg_r'])}, middle result {_r(n['taken_median_r'])}, "
                     f"won {'—' if n['taken_win_pct'] is None else str(n['taken_win_pct']) + '%'}, "
                     f"process {'—' if n['process_avg'] is None else n['process_avg']}.")
        if n["passed"] == 0:
            L.append("  3 PASSED    No ideas passed this week.")
        else:
            verdict = ""
            if n["paper_avg_r"] is not None:
                verdict = (" Positive: your filter may be too tight." if n["paper_avg_r"] > 0
                           else " Negative or flat: your filter is saving you.")
                if n["paper_scored"] < MIN_N_FOR_CLAIMS:
                    verdict += f" ({n['paper_scored']} scored: far too few to conclude.)"
            L.append(f"  3 PASSED    {n['paper_scored']} scored on paper, average {_r(n['paper_avg_r'])}"
                     + (f"; {n['paper_never_filled']} never reached the entry" if n["paper_never_filled"] else "")
                     + "." + verdict)
    fc = n["framework_calls"]
    cf = n["candidates_fired"]
    g = n["candidates_graded_r"]
    L.append(f"  4 VERSUS    You: {_r(n['taken_avg_r'])} over {n['taken_scored']} trades. "
             f"Framework: {'no trade-signal ledger here' if fc is None else str(fc) + ' trade calls'}. "
             f"Candidates: {'no shadow ledger here' if cf is None else str(cf) + ' fired'}"
             + (f", {len(g)} graded, average {_r(_avg(g))} (rows, not independent episodes)" if g else "")
             + ".")
    if n["breaks"]:
        worst = "; ".join(f"{k} ({v})" for k, v in sorted(n["breaks_by_state"].items(), key=lambda kv: -kv[1]))
        L.append(f"  5 RULES     Broken most: {n['top_rule_break']}. By state: {worst}.")
    else:
        L.append("  5 RULES     No rule breaks recorded on scored trades.")
    nt = n["notifications_total"]
    L.append("  6 ALERTS    " + ("No notification ledger here." if nt is None else
                                  f"{nt} notifications this week. How many told you something new?"))
    allr = n["all_taken_r"]
    L.append("  " + "─" * 60)
    if len(allr) < MIN_N_FOR_CLAIMS:
        L.append(f"  All time: {len(allr)} scored trades. Under {MIN_N_FOR_CLAIMS}: no claims about edge;\n"
                 "  process score and rule breaks mean something sooner.")
    else:
        L.append(f"  All time: {len(allr)} scored trades. Monthly check: python3 foundation/tools/"
                 f"power_check.py --rs {' '.join(str(x) for x in allr)}")
    return "\n".join(L)


def write_review(n: Dict, ask: Ask = input, now: Optional[datetime] = None) -> Optional[Dict]:
    """Step 7: one lesson, at most one rule change. Refuses a week that has
    not ended and a week already written."""
    now = now or _now()
    week = n["week"]
    if not week_is_over(week, now):
        print(f"\n  {week} is not over yet. Rules never change mid-week, so the review\n"
              "  is written from Saturday. Use --no-write to look at the numbers now.\n")
        return None
    for r in _read(REVIEWS_FILE) or []:
        if r.get("week") == week:
            print(f"\n  {week} was already reviewed on {r.get('written_utc', '')[:10]}. One review per\n"
                  "  week; next week's review is where a change of mind goes.\n")
            return None
    material = None
    if n["notifications_total"] is not None:
        while material is None or not 0 <= material <= n["notifications_total"]:
            material = _number(ask, f"Of the {n['notifications_total']} notifications, how many told you something new")
    lesson = _text(ask, "The ONE lesson from this week", required=True)
    change = _text(ask, "At most ONE rule change for next week (blank for none)")
    applies = week_monday(week) + timedelta(days=7)
    row = {k: n.get(k, "") for k in REVIEW_FIELDS}
    row.update(written_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               notifications_material="" if material is None else int(material),
               notifications_total="" if n["notifications_total"] is None else n["notifications_total"],
               lesson=lesson, rule_change=change or "none",
               applies_from=applies.isoformat())
    for k in ("taken_avg_r", "taken_median_r", "taken_win_pct", "process_avg", "paper_avg_r"):
        if row[k] is None:
            row[k] = ""
    _append(REVIEWS_FILE, REVIEW_FIELDS, row)
    print(f"\n  Review for {week} recorded. Rule change applies from Monday {applies:%d %b}"
          if change else f"\n  Review for {week} recorded. No rule change.")
    print()
    return row


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Trader review loop: ideas, scores, weekly review")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("idea")
    sc = sub.add_parser("score")
    sc.add_argument("--id", default="")
    sub.add_parser("list")
    rv = sub.add_parser("review")
    rv.add_argument("--week", default="")
    rv.add_argument("--no-write", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "idea":
            log_idea()
        elif a.cmd == "score":
            score_idea(idea_id=a.id)
        elif a.cmd == "list":
            list_waiting()
        elif a.cmd == "review":
            require_project_dir()
            week = a.week or default_review_week(_now())
            n = week_numbers(week)
            print("\n" + render_review(n) + "\n")
            if not a.no_write:
                write_review(n)
        else:
            p.print_help()
    except NotInProject as e:
        print(f"\n  {e}\n")
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\n  Stopped. Nothing was written for the unfinished entry.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
