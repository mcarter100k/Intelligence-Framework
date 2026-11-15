"""
test_wrapper_behavior.py — the scheduled wrappers, EXECUTED, not text-matched.

Each test builds a throwaway project from this repo's real scripts/, stubs
the Python target (decision_brief.py / run_outcome_check.py), and runs the
real wrapper under /bin/bash 3.2 (the interpreter launchd uses) with
/usr/bin/python3 on PATH (launchd's). Notifications go to a stub osascript
that records its arguments; HOME is fake so no real notifier is ever used.

Why: the old tests only checked that certain strings appeared in the wrapper
source. They stayed green while weekly_heartbeat.sh could not even be parsed,
and none of them could see the Phase 2 defects (docs/specs/visible_failures_spec.md
D1-D5), each of which is pinned here by running the real script.
"""
from _paths import ROOT
import json
import re
import os
import shutil
import subprocess
import textwrap
import time

import pytest

from _paths import ROOT as _ROOT
pytestmark = pytest.mark.skipif(
    not (os.path.exists("/bin/bash") and os.path.exists("/usr/bin/python3")),
    reason="needs launchd's /bin/bash and /usr/bin/python3")

_LEDGERS = ["regime_classification_log.csv", "session_context_log.csv",
            "shadow_signal_log.csv", "trade_signal_log.csv"]

CRASH = """
    import sys
    sys.stderr.write('Traceback (most recent call last):\\n  File "x", line 1\\n'
                     'ZeroDivisionError: boom\\n')
    sys.exit(1)
"""
STAND_ASIDE = """
    print('GBP/AUD\\n  DECISION     STAND ASIDE — conditions not right to trade')
"""


def _project(tmp_path, brief=STAND_ASIDE, outcome="print('graded 0')",
             storylines_age_h=1):
    proj = tmp_path / "proj"
    (proj / "logs").mkdir(parents=True)
    shutil.copytree(os.path.join(_ROOT, "scripts"), proj / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "launchd"))
    # scripts/health_state.py and backup_ledgers.py import the root-level
    # ledger_io (docs/specs/safe_ledger_writes_spec.md)
    shutil.copy(os.path.join(_ROOT, "ledger_io.py"), proj / "ledger_io.py")
    now = time.time()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
    for name in _LEDGERS:
        (proj / name).write_text(f"timestamp,x\n{stamp},1\n")
    (proj / "calendar.csv").write_text("time,currency,event,actual,forecast,previous,impact\n")
    story = proj / "storylines.md"
    story.write_text("notes\n")
    old = now - storylines_age_h * 3600
    os.utime(story, (old, old))
    for name, body in (("decision_brief.py", brief),
                       ("run_outcome_check.py", outcome),
                       ("calendar_fetch.py", "print('calendar ok')")):
        (proj / name).write_text(textwrap.dedent(body))
    git = lambda *a: subprocess.run(["git", "-C", str(proj), *a], check=True,
                                    capture_output=True)
    git("init", "-q", "-b", "main")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "--allow-empty", "-m", "init")
    stub = tmp_path / "bin"
    stub.mkdir()
    notes = tmp_path / "notifications.txt"
    (stub / "osascript").write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{notes}"\n')
    (stub / "osascript").chmod(0o755)
    return proj


def _run(tmp_path, proj, wrapper, *args):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
           "INTEL_NO_ENV_FILE": "1", "INTEL_PROJ": str(proj)}
    r = subprocess.run(["/bin/bash", str(proj / "scripts" / wrapper), *args],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr           # exit-0 discipline, always


def _log(proj, kind):
    return "".join(p.read_text() for p in (proj / "logs").glob(f"{kind}_*.log"))


def _notes(tmp_path):
    p = tmp_path / "notifications.txt"
    return p.read_text() if p.exists() else ""


def _jobs(proj):
    p = proj / "logs" / "health_state.json"
    return json.loads(p.read_text())["jobs"] if p.exists() else {}


# ── D1-D5 (docs/specs/visible_failures_spec.md) ───────────────────────────────

def test_d1_grader_traceback_is_a_failure(tmp_path):
    proj = _project(tmp_path, outcome=CRASH)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    job = _jobs(proj)["outcomes"]
    assert job["consecutive_failures"] == 1
    assert job["last_failure_reason"] == "grader crashed (exit 1): ZeroDivisionError: boom"


def test_d2_brief_stderr_reaches_the_day_log(tmp_path):
    proj = _project(tmp_path, brief=STAND_ASIDE + """
    import sys
    sys.stderr.write('regime logger failed: disk full (non-fatal)\\n')
""")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "regime logger failed: disk full" in _log(proj, "brief")


def test_d3_brief_crash_is_logged_and_counted(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    log = _log(proj, "brief")
    assert "Traceback (most recent call last)" in log and "ZeroDivisionError" in log
    assert _jobs(proj)["brief"]["last_failure_reason"] == \
        "brief crashed (exit 1): ZeroDivisionError: boom"


def test_d4_grader_success_never_recovers_a_failing_brief(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    notes = _notes(tmp_path)
    assert "BRIEF UNHEALTHY" in notes
    assert "RECOVERED" not in notes
    assert _jobs(proj)["brief"]["consecutive_failures"] == 2


def test_d4_the_brief_recovers_only_on_its_own_success(tmp_path):
    proj = _project(tmp_path, brief=CRASH)
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")
    (proj / "decision_brief.py").write_text(textwrap.dedent(STAND_ASIDE))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "RECOVERED: brief healthy again after 2 failed runs" in _notes(tmp_path)


def test_d5_a_due_human_file_never_fails_a_run(tmp_path):
    proj = _project(tmp_path, storylines_age_h=500)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _jobs(proj)["brief"]["consecutive_failures"] == 0
    assert "DUE: storylines.md" in _log(proj, "brief")
    assert "UNHEALTHY" not in _notes(tmp_path)


def test_a_stale_machine_ledger_still_fails_the_run(tmp_path):
    """D5 must not blunt the real alarm: a dead live writer still fails."""
    proj = _project(tmp_path)
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 200 * 3600))
    (proj / "regime_classification_log.csv").write_text(f"timestamp,x\n{old},1\n")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _jobs(proj)["brief"]["last_failure_reason"].startswith(
        "STALE: regime_classification_log.csv")


# ── notification routing (replaces the static source-text pins) ──────────────

def test_a_directional_decision_notifies_decision(tmp_path):
    proj = _project(tmp_path, brief="""
        print('GBP/AUD\\n  DECISION     SHORT — conditions line up')
    """)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "DECISION"' in _notes(tmp_path)


def test_a_shadow_signal_sends_nothing_and_is_logged(tmp_path):
    """Old -> new 2026-11-15 (alert_importance_spec N3): was "notifies SHADOW".
    A shadow fire is paper evidence; it reaches the owner in the digest."""
    proj = _project(tmp_path, brief=STAND_ASIDE + """
    print('SHADOW SIGNALS\\n  MOMENTUM_JOIN LONG')
""")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""
    assert "SHADOW not sent (digest only)" in _log(proj, "brief")


def test_an_actionable_flip_notifies_alert_and_carries_the_decision(tmp_path):
    """Old -> new 2026-11-15 (N2, N5): the flip was the bare text "GBP/AUD
    regime flipped" and the ALERT replaced the DECISION. Now only a flip that
    changes what the framework allows notifies, and a decision change in the
    same run rides in the same notification instead of being lost."""
    proj = _project(tmp_path, brief="""
        import sys
        print('GBP/AUD\\n  DECISION     SHORT — x\\nSHADOW SIGNALS')
        sys.stderr.write('##ALERT## GBP/AUD: conditions improved — the framework now allows a trade. Check the brief.\\n')
    """)
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert notes.count("display notification") == 1
    assert 'subtitle "ALERT"' in notes and "now allows a trade" in notes
    assert "GBP/AUD SHORT" in notes


def test_a_quiet_stand_aside_notifies_nothing(tmp_path):
    proj = _project(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""


# ── market-status gate on DECISION (docs/specs/decision_channel_measurement_spec.md, Phase 0) ──
# Each brief here is RENDERED by the real producer (DecisionBrief.format with
# regime_detection._market_status's banner), not hand-typed, so a change to
# the banner wording or header layout fails these tests instead of silently
# disabling the gate. Week of 2026-10-11: 6 of 12 DECISION notifications
# fired with the market closed.

_SAT = (2026, 10, 17, 1, 12)      # Fri 6:12 PM PDT = Sat 01:12 UTC: closed
_WED = (2026, 10, 14, 15, 0)      # Wed 8:00 AM PDT: open


def _rendered(instrument, decision, when, us_line=""):
    from datetime import datetime, timezone
    import decision_brief as db
    from regime_detection import _market_status
    st = _market_status(_now=datetime(*when, tzinfo=timezone.utc))
    trade = decision in ("LONG", "SHORT")
    return db.DecisionBrief(
        instrument=instrument, timestamp="t", price=1.9189, atr_pips=100.9,
        decision=decision, reason="r", conviction=45 if trade else 0,
        grade="B" if trade else "C", size_pct=35 if trade else 0,
        market_state="m", invalidation="i", regime_log="l",
        stand_down=not trade, override_fired=False, execution_mode="X",
        adx_d1=19.0, adx_h4=33.0, weekly_context="W", error=None,
        market_open=st["open"], market_note=st["note"],
        entry_line="level 1.9189" if trade else "",
        target_line="set your own" if trade else "",
        us_events_line=us_line).format()


def _brief_printing(tmp_path, text, extra=""):
    """A stub decision_brief.py that prints `text` byte-for-byte (launchd's
    python3 may run with an ASCII stdout; the banner has an em dash)."""
    src = tmp_path / "rendered_brief.txt"
    src.write_bytes(text.encode("utf-8"))
    return (f"import sys\nsys.stdout.buffer.write(open({str(src)!r}, 'rb').read())\n"
            f"sys.stdout.flush()\n{extra}")


def test_g1_a_closed_market_decision_does_not_notify(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "SHORT", _SAT)
    assert "Market closed" in text and "DECISION     LONG" in text
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""
    assert "DECISION notification suppressed: market closed" in _log(proj, "brief")


def test_g2_an_open_market_decision_still_notifies(tmp_path):
    """Positive control: the gate is not a blanket mute."""
    text = _rendered("GBP_AUD", "LONG", _WED)
    assert "Market closed" not in text and "DECISION     LONG" in text
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "DECISION"' in notes and "GBP/AUD LONG" in notes
    assert "suppressed" not in _log(proj, "brief")


def test_g3_the_gate_is_per_instrument_and_keeps_closed_lines_out_of_the_summary(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "SHORT", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "DECISION"' in notes
    assert "GBP/JPY SHORT" in notes and "LONG" not in notes.split("→")[0]


def test_g4_a_closed_pairs_flip_does_not_notify(tmp_path):
    """Old -> new 2026-11-15 (alert_importance_spec N1): was "a flip alert
    still fires when closed". Even an actionable flip waits for the open."""
    text = _rendered("GBP_AUD", "LONG", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(
        tmp_path, text, "sys.stderr.write('##ALERT## GBP/AUD: exit-watch fired — x. Check the brief.\\n')\n"))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""
    assert "ALERT not sent (market closed or nothing to act on): GBP/AUD: exit-watch" in _log(proj, "brief")


def test_g5_a_health_alert_still_fires_when_closed(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30 * 86400))
    (proj / "regime_classification_log.csv").write_text(f"timestamp,x\n{stale},1\n")
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")       # 2 consecutive failures notify
    notes = _notes(tmp_path)
    assert 'subtitle "ALERT"' in notes and 'subtitle "DECISION"' not in notes


def test_g6_a_closed_market_shadow_signal_sends_nothing(tmp_path):
    """Old -> new 2026-11-15 (N1, N3): was "a shadow signal still fires when
    closed". The same MOMENTUM_JOIN SHORT notified 4 times over the
    2026-11-14 weekend from one ledger row."""
    text = _rendered("GBP_AUD", "LONG", _SAT) + "\nSHADOW SIGNALS\n  MOMENTUM_JOIN LONG\n"
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""


def test_g7_the_heartbeat_still_fires_after_a_closed_market_brief(tmp_path):
    proj = _heartbeat_project(tmp_path)
    text = _rendered("GBP_AUD", "LONG", _SAT)
    (proj / "decision_brief.py").write_text(_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert 'subtitle "HEARTBEAT"' in _notes(tmp_path)


def test_g8_a_closed_market_digest_is_not_sent(tmp_path):
    """Old -> new 2026-11-15 (N1): was "the digest still fires when closed".
    Weekend digests said only "MARKET CLOSED ... no live calls"."""
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "STAND DOWN", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert _notes(tmp_path) == ""
    assert "DIGEST not sent: market closed" in _log(proj, "brief")
    assert (proj / "logs" / "latest_brief.log").exists()        # the view is still refreshed


def test_g8_control_one_open_pair_still_digests(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "STAND DOWN", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert 'subtitle "DIGEST"' in _notes(tmp_path)


def test_g10_a_decision_notification_names_its_pair(tmp_path):
    """The summary said a decision was issued but not for which pair."""
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_JPY", "SHORT", _WED)))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/JPY SHORT", msg


def test_g11_decisions_on_both_pairs_name_both(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _WED) + _rendered("GBP_JPY", "SHORT", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/AUD LONG · GBP/JPY SHORT", msg


def test_g12_the_decision_summary_names_decisions_only(tmp_path):
    """Old -> new 2026-11-15 (N3): shadow lines no longer follow the decision.
    The candidate-name grep produced "is watching the EARLY_MOMENTUM_v2
    candidate: · MOMENTUM_JOIN SHORT @ 211.026" (2026-11-13 18:00)."""
    text = (_rendered("GBP_JPY", "SHORT", _WED)
            + "\nSHADOW SIGNALS\n  MOMENTUM_JOIN   SHORT   fired\n")
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    msg = _notes(tmp_path).split('display notification "', 1)[1].split(" → ")[0]
    assert msg == "GBP/JPY SHORT", msg


def test_g9_the_wrapper_marker_is_the_producers_banner():
    """The wrapper greps prose because the brief has no machine marker
    (decision_brief.py is protected). Pin the exact string at both ends."""
    import re
    from datetime import datetime, timezone
    from regime_detection import _market_status
    src = open(os.path.join(_ROOT, "scripts", "scheduled_brief.sh"), encoding="utf-8").read()
    m = re.search(r"^CLOSED_MARKER='([^']+)'$", src, re.M)
    assert m, "scheduled_brief.sh must define CLOSED_MARKER='...'"
    marker = m.group(1)
    closed = _market_status(_now=datetime(*_SAT, tzinfo=timezone.utc))
    opened = _market_status(_now=datetime(*_WED, tzinfo=timezone.utc))
    assert closed["open"] is False and closed["note"].startswith(marker)
    assert opened["open"] is True and marker not in opened["note"]
    assert marker in _rendered("GBP_AUD", "LONG", _SAT)
    assert marker not in _rendered("GBP_AUD", "LONG", _WED)


# ── notification ledger (docs/specs/notification_ledger_spec.md) ─────────────
# One row per notification ACTUALLY sent. Before it, the week-of-10/11 recap
# was rebuilt from day logs and delivery was inferred from wrapper code.

_NL_FIELDS = ["timestamp_utc", "category", "pairs", "decision_state", "summary"]


def _ledger(proj):
    import csv
    p = proj / "notification_log.csv"
    if not p.exists():
        return None, []
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def _error_page(instrument):
    import decision_brief as db
    return db.DecisionBrief(
        instrument=instrument, timestamp="t", price=0.0, atr_pips=0.0,
        decision="STAND DOWN", reason="Framework error — do not trade: OANDA not configured",
        conviction=0, grade="C", size_pct=0, market_state="Unavailable", invalidation="i",
        regime_log="l", stand_down=True, override_fired=False, execution_mode="X",
        adx_d1=0.0, adx_h4=0.0, weekly_context="W", error="OANDA not configured").format()


def test_d3_a_sent_decision_writes_one_row_with_pairs_and_state(tmp_path):
    from datetime import datetime, timedelta, timezone
    text = _rendered("GBP_AUD", "LONG", _WED) + _rendered("GBP_JPY", "STAND DOWN", _WED)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    header, rows = _ledger(proj)
    assert header == _NL_FIELDS and len(rows) == 1, (header, rows)
    r = rows[0]
    assert r["category"] == "DECISION" and r["pairs"] == "GBP_AUD GBP_JPY"
    assert r["decision_state"] == "GBP_AUD=LONG/open;GBP_JPY=STAND ASIDE/open"
    assert r["summary"].startswith("GBP/AUD LONG → logs/brief_"), r["summary"]   # pair-named summary (122bb87)
    t = datetime.strptime(r["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert abs(datetime.now(timezone.utc) - t) < timedelta(minutes=5)


def test_d3_a_suppressed_closed_market_decision_writes_no_row(tmp_path):
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "STAND DOWN", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _ledger(proj)[1] == [] and _notes(tmp_path) == ""


def test_d3_a_failed_send_writes_no_row(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_AUD", "LONG", _WED)))
    (tmp_path / "bin" / "osascript").write_text("#!/bin/bash\nexit 1\n")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _ledger(proj)[1] == []


def test_d3_the_terminal_notifier_path_writes_a_row_too(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_AUD", "LONG", _WED)))
    tn = tmp_path / "home" / "Applications" / "terminal-notifier.app" / "Contents" / "MacOS"
    tn.mkdir(parents=True)
    (tn / "terminal-notifier").write_text("#!/bin/bash\nexit 0\n")
    (tn / "terminal-notifier").chmod(0o755)
    _run(tmp_path, proj, "scheduled_brief.sh")
    rows = _ledger(proj)[1]
    assert [r["category"] for r in rows] == ["DECISION"]
    assert _notes(tmp_path) == ""                     # osascript fallback not used


def test_d3_an_error_page_is_recorded_as_error_not_stand_aside(tmp_path):
    text = _error_page("GBP_AUD") + _error_page("GBP_JPY")
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    rows = [r for r in _ledger(proj)[1] if r["category"] == "DIGEST"]
    assert len(rows) == 1
    assert rows[0]["decision_state"] == "GBP_AUD=ERROR/open;GBP_JPY=ERROR/open"


def test_d3_a_closed_market_run_writes_no_row(tmp_path):
    """Old -> new 2026-11-15 (N1): a closed digest used to be sent and
    recorded with the closed state; now nothing is sent, so no row."""
    text = _rendered("GBP_AUD", "LONG", _SAT) + _rendered("GBP_JPY", "STAND DOWN", _SAT)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert _ledger(proj)[1] == []


def test_d3_the_heartbeat_row_carries_no_pairs(tmp_path):
    proj = _heartbeat_project(tmp_path)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    rows = _ledger(proj)[1]
    assert [(r["category"], r["pairs"], r["decision_state"]) for r in rows] == [("HEARTBEAT", "", "")]


def test_d3_a_failed_ledger_write_is_in_the_day_log_and_the_notification_still_goes(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_AUD", "LONG", _WED)))
    (proj / "notification_log.csv").mkdir()           # unwritable as a file
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "DECISION"' in _notes(tmp_path)
    assert "NOTIFICATION LEDGER WRITE FAILED" in _log(proj, "brief")


def _digest_pointer(tmp_path):
    notes = [ln for ln in _notes(tmp_path).splitlines() if 'subtitle "DIGEST"' in ln]
    assert len(notes) == 1, notes
    return notes[0].split(" → ", 1)[1].split('"', 1)[0]


def test_a_fresh_view_is_what_the_digest_opens(tmp_path):
    """Positive control for the stale-view check: a normal digest run regenerates
    the view, its first line is this run, and the click goes there."""
    proj = _project(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert _digest_pointer(tmp_path) == "logs/latest_brief.log"
    first = (proj / "logs" / "latest_brief.log").read_text().splitlines()[0]
    assert first.startswith("LATEST RUN — ") and first[len("LATEST RUN — "):] in _log(proj, "brief")


def test_a_stale_view_is_never_what_the_digest_opens(tmp_path):
    """latest_view.py always exits 0 and leaves the old file when it fails (team
    review 2026-11-05, defect 5): the digest must then open the day log."""
    proj = _project(tmp_path)
    (proj / "scripts" / "latest_view.py").write_text("import sys\nsys.exit(0)\n")   # fails silently
    (proj / "logs" / "latest_brief.log").write_text(
        "LATEST RUN — 2026-11-04 07:33:53 PST\n  GBP/AUD  |  old\n  DECISION     LONG\n")
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert _digest_pointer(tmp_path).startswith("logs/brief_")


def test_a_failed_ledger_write_for_the_digest_lands_in_the_day_log(tmp_path):
    """notify.sh wrote the failure into the file the notification opens; for the
    DIGEST that is the view the next run overwrites (team review 2026-11-05,
    defect 4). The record must reach the append-only day log."""
    proj = _project(tmp_path)
    (proj / "notification_log.csv").mkdir()           # unwritable as a file
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert _digest_pointer(tmp_path) == "logs/latest_brief.log"     # the view path was taken
    assert "NOTIFICATION LEDGER WRITE FAILED" in _log(proj, "brief")
    assert "NOTIFICATION LEDGER WRITE FAILED" not in (proj / "logs" / "latest_brief.log").read_text()


def test_digest_is_sent_only_with_the_digest_argument(tmp_path):
    proj = _project(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "DIGEST" not in _notes(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert 'subtitle "DIGEST"' in _notes(tmp_path)


def test_graded_shadow_outcome_sends_no_tally(tmp_path):
    """Old -> new 2026-11-15 (alert_importance_spec N4): a graded outcome used
    to send a nightly SHADOW tally. Now only a review gate notifies."""
    proj = _project(tmp_path, outcome="print('GBP_JPY: 1 shadow-signal outcomes filled')")
    _gate_inputs(proj, episodes=3, market_open=True)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert "SHADOW" not in _notes(tmp_path) and "REVIEW" not in _notes(tmp_path)


def test_no_graded_shadow_outcome_sends_no_shadow_notification(tmp_path):
    proj = _project(tmp_path, outcome="print('GBP_JPY: 0 trade-signal outcomes filled')")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert "SHADOW" not in _notes(tmp_path)


# ── code-review findings (visible_failures_spec addendum) ─────────────────────

def test_f1_grader_crash_reason_comes_from_stderr_not_stdout(tmp_path):
    """stdout printed before the crash, flushed only at exit, must never be
    named as the cause."""
    proj = _project(tmp_path, outcome="""
        import sys
        print('GBP_AUD: 3 regime outcomes filled')
        raise KeyError('instrument')
    """)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason == "grader crashed (exit 1): KeyError: 'instrument'"
    log = _log(proj, "outcomes")
    assert "GBP_AUD: 3 regime outcomes filled" in log and "KeyError" in log


def _yesterday():
    return subprocess.run(["/bin/bash", "-c",
                           "date -v-1d +%F 2>/dev/null || date -d yesterday +%F"],
                          capture_output=True, text=True).stdout.strip()


# The schedule as installed (scripts/launchd), written out independently of
# scripts/run_count.py so the heartbeat's expected-vs-actual line is checked
# against a fixture it did not generate.
_SLOTS = {"brief": ((2, 30), (7, 30), (18, 0)), "outcomes": ((15, 15),)}


def _local_zone():
    from zoneinfo import ZoneInfo
    real = os.path.realpath("/etc/localtime")
    return ZoneInfo(real.split("zoneinfo/", 1)[1])


def _write_week_of_runs(proj, skip=lambda kind, t: False):
    """One run header per scheduled slot over the last 8 days (UTC stamps);
    `skip` drops slots to simulate a scheduler gap. Returns the dropped count."""
    from datetime import datetime, timedelta, timezone
    tz, now, dropped = _local_zone(), datetime.now(timezone.utc), 0
    for back in range(8, -1, -1):
        day = (now.astimezone(tz) - timedelta(days=back)).date()
        for kind, hm in _SLOTS.items():
            for h, m in hm:
                t = datetime(day.year, day.month, day.day, h, m, tzinfo=tz).astimezone(timezone.utc)
                if t > now:
                    continue
                if skip(kind, t):
                    dropped += 1
                    continue
                p = proj / "logs" / f"{kind}_{day.isoformat()}.log"
                with open(p, "a") as f:
                    f.write(f"===== {t.strftime('%Y-%m-%d %H:%M:%S')} UTC =====\nok\n\n")
    return dropped


def _install_schedule(tmp_path):
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    for p in os.listdir(os.path.join(_ROOT, "scripts", "launchd")):
        if p.endswith(".plist"):
            shutil.copy(os.path.join(_ROOT, "scripts", "launchd", p), agents / p)


def _heartbeat_project(tmp_path, storylines_age_h=1, health=None, skip=None):
    proj = _project(tmp_path, storylines_age_h=storylines_age_h)
    _install_schedule(tmp_path)
    _write_week_of_runs(proj, **({"skip": skip} if skip else {}))
    if health is not None:
        (proj / "logs" / "health_state.json").write_text(json.dumps(health))
    return proj


def test_c1_the_heartbeat_reports_expected_vs_actual_runs(tmp_path):
    proj = _heartbeat_project(tmp_path)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    log = _log(proj, "heartbeat")
    # 21 brief and 7 outcomes slots a week; a slot in its 30-minute grace
    # window is not yet expected, so the count is one lower right after a slot.
    m = re.search(r"runs \(last 7d, launchd schedule\): brief (\d+) expected / (\d+) on time / \d+ ran; "
                  r"outcomes (\d+) expected / (\d+) on time / \d+ ran", log)
    assert m, log
    assert m[1] == m[2] and m[1] in ("20", "21") and m[3] == m[4] and m[3] in ("6", "7"), log
    assert "SHORTFALL" not in log
    assert "NEEDS ATTENTION" not in _notes(tmp_path)


def test_c1_a_scheduler_gap_is_a_shortfall_that_needs_attention(tmp_path):
    """The 2026-09-12 -> 09-14 shape: two days with no runs at all, and zero
    failures recorded, because nothing ran to fail."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    gap = (now - timedelta(days=4), now - timedelta(days=2))
    proj = _heartbeat_project(tmp_path, skip=lambda k, t: gap[0] <= t < gap[1],
                              health={"jobs": {"brief": {"consecutive_failures": 0},
                                               "outcomes": {"consecutive_failures": 0}}})
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes, log = _notes(tmp_path), _log(proj, "heartbeat")
    assert "runs: SHORTFALL" in log, log
    assert re.search(r"brief 6 of 2[01] scheduled runs missing or over 60 min late", log), log
    assert "NEEDS ATTENTION" in notes and "SHORTFALL" in notes


def test_c1_no_installed_schedule_is_loud_not_a_pass(tmp_path):
    proj = _project(tmp_path)
    _write_week_of_runs(proj)                  # runs present, no plists installed
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert "schedule MISSING" in _log(proj, "heartbeat")
    assert "NEEDS ATTENTION" in _notes(tmp_path)


def test_f9_heartbeat_always_notifies_and_reports_healthy(tmp_path):
    proj = _heartbeat_project(tmp_path)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "HEARTBEAT"' in notes and "healthy |" in notes
    assert "NEEDS ATTENTION" not in notes


def test_f7_an_eight_day_old_storylines_is_not_needs_attention(tmp_path):
    """Old heartbeat: 'STALE (>7d)' tripped NEEDS ATTENTION at 8 days, inside
    the owner's 216h cadence."""
    proj = _heartbeat_project(tmp_path, storylines_age_h=8 * 24)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    assert "NEEDS ATTENTION" not in _notes(tmp_path)
    assert "STALE" not in _log(proj, "heartbeat")


def test_f7_a_past_due_storylines_is_a_due_reminder_not_attention(tmp_path):
    proj = _heartbeat_project(tmp_path, storylines_age_h=20 * 24)
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    log = _log(proj, "heartbeat")
    assert "DUE (your 9-day cadence; a reminder)" in log
    assert "NEEDS ATTENTION" not in _notes(tmp_path)


def test_f9_heartbeat_surfaces_an_unhealthy_job_by_name(tmp_path):
    proj = _heartbeat_project(tmp_path, health={"jobs": {
        "brief": {"consecutive_failures": 0},
        "outcomes": {"consecutive_failures": 3,
                     "last_failure_reason": "grader crashed (exit 1): KeyError"}}})
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    notes = _notes(tmp_path)
    assert "NEEDS ATTENTION" in notes and "outcomes: UNHEALTHY" in notes


# ── Phase 3: nightly backup (docs/specs/safe_ledger_writes_spec.md) ───────────

def test_the_backup_runs_before_the_grader_rewrites_anything(tmp_path):
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    log = _log(proj, "outcomes")
    b = log.index("all sha256 verified -> backups/")
    assert b < log.index("GRADER RAN")
    days = [d for d in os.listdir(proj / "backups") if not d.startswith(".")]
    assert len(days) == 1
    day = proj / "backups" / days[0]
    assert (day / "regime_classification_log.csv").read_text() == \
        (proj / "regime_classification_log.csv").read_text()


def test_a_failed_backup_is_an_outcomes_failure_and_the_grader_does_not_run(tmp_path):
    """Review R2: the grader used to rewrite the ledgers anyway."""
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    (proj / "backups").write_text("a FILE where the backups folder must go")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason.startswith("BACKUP FAILED")
    log = _log(proj, "outcomes")
    assert "GRADER SKIPPED" in log and "GRADER RAN" not in log


def test_a_crashed_or_missing_backup_script_also_stops_the_grader(tmp_path):
    """Review R10: only a '^BACKUP FAILED' line used to count; a traceback or
    a missing script was recorded as success and the grader ran."""
    proj = _project(tmp_path, outcome="print('GRADER RAN')")
    (proj / "scripts" / "backup_ledgers.py").unlink()
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    reason = _jobs(proj)["outcomes"]["last_failure_reason"]
    assert reason.startswith("BACKUP FAILED: no success line")
    assert "GRADER RAN" not in _log(proj, "outcomes")


# ── I3a: feed text that wraps onto a new line never poses as a label ────────
# (docs/specs/us_events_context_spec.md §1.4 and I3a, team review 2026-11-01).
# The US line here is deliberately UNSANITIZED, so this proves the wrapper's
# anchors alone; the title allow-list is proven alone in
# test_us_events_context.py (I3b). Each trigger is placed to start a wrapped
# continuation line, the position that defeated the old "^ *"-free greps.

_FILL = "a" * 36
_RAW_US = " ".join([_FILL, "DECISION LONG", _FILL, "SHADOW SIGNALS", _FILL,
                    "REASON Framework error", _FILL, "USD/JPY LONG", _FILL])
_STARTS = ["DECISION LONG", "SHADOW SIGNALS", "REASON Framework error", "USD/JPY LONG"]


def _continuations(text):
    return [l.strip() for l in text.split("\n") if l.startswith(" " * 13) and l.strip()]


def test_i3a_precondition_each_trigger_starts_a_wrapped_line():
    starts = _continuations(_rendered("GBP_JPY", "STAND DOWN", _WED, _RAW_US))
    for trig in _STARTS:
        assert trig in starts, (trig, starts)


def test_i3a_wrapped_triggers_on_a_stand_aside_brief_send_nothing(tmp_path):
    text = _rendered("GBP_JPY", "STAND DOWN", _WED, _RAW_US)
    assert "Market closed" not in text                    # open market: the gate is not what stops it
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    _run(tmp_path, proj, "scheduled_brief.sh")            # two runs: a health ALERT needs two failures
    assert _notes(tmp_path) == ""
    assert _ledger(proj)[1] == []
    assert _jobs(proj)["brief"]["consecutive_failures"] == 0, _jobs(proj)


def test_i3a_wrapped_triggers_do_not_change_a_real_decision(tmp_path):
    with_us = _rendered("GBP_JPY", "LONG", _WED, _RAW_US)
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, with_us))
    _run(tmp_path, proj, "scheduled_brief.sh")
    rows = _ledger(proj)[1]
    assert [r["category"] for r in rows] == ["DECISION"], rows
    assert rows[0]["decision_state"] == "GBP_JPY=LONG/open", rows[0]
    assert rows[0]["summary"].split(" → ")[0] == "GBP/JPY LONG", rows[0]


def test_i3a_control_the_same_decision_without_the_us_line(tmp_path):
    """Positive control: the harness notifies, and identically, without it."""
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_JPY", "LONG", _WED)))
    _run(tmp_path, proj, "scheduled_brief.sh")
    rows = _ledger(proj)[1]
    assert [r["category"] for r in rows] == ["DECISION"]
    assert rows[0]["decision_state"] == "GBP_JPY=LONG/open"
    assert rows[0]["summary"].split(" → ")[0] == "GBP/JPY LONG"
    assert 'subtitle "DECISION"' in _notes(tmp_path)


def test_i3a_a_wrapped_pair_name_cannot_reopen_a_closed_market(tmp_path):
    """The US line sits below the market-closed banner, so an unanchored
    pair-header match on its continuation would reset the closed flag and
    let a closed-market LONG notify."""
    text = _rendered("GBP_JPY", "LONG", _SAT, _RAW_US)
    assert text.index("Market closed") < text.index("USD/JPY LONG")
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == "" and _ledger(proj)[1] == []


# Rev 2 (re-review 2026-11-03): the 07:30 DIGEST matched label words anywhere,
# so "xWATCH FOR …" replaced the real watch and "xFramework error" read as a
# failed run. Unsanitized text again, so this proves the digest's anchors alone.
_RAW_DIGEST = " ".join(["xFramework error review", "xWATCH FOR a 500 pip drop", _FILL,
                        "WATCH FOR a 500 pip drop", _FILL, "REASON Framework error", _FILL])


def _digest_rows(tmp_path, text):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    return [(r["category"], r["decision_state"], r["summary"].split(" → ")[0])
            for r in _ledger(proj)[1]]


def test_i3a_feed_text_never_steers_the_digest(tmp_path):
    with_us = _rendered("GBP_JPY", "STAND DOWN", _WED, _RAW_DIGEST)
    assert "WATCH FOR a 500 pip drop" in with_us and "xFramework error" in with_us
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    got = _digest_rows(tmp_path / "a", with_us)
    control = _digest_rows(tmp_path / "b", _rendered("GBP_JPY", "STAND DOWN", _WED))
    assert control and control[0][0] == "DIGEST" and "watch: i" in control[0][2], control
    assert got == control, (got, control)


# ── range + volatile REASON (docs/specs/range_volatile_wording_v3_spec.md W4) ──
# The new sentences render inside a stand-aside brief's REASON line; they must
# never cause a notification (rule 12). Control: an open-market LONG notifies.

def _range_volatile_brief(when):
    from datetime import datetime, timezone
    import decision_brief as db
    from regime_detection import _market_status
    st = _market_status(_now=datetime(*when, tzinfo=timezone.utc))
    why = db._render_reason(
        {"regime_d1": "RANGING", "regime_h4": "VOLATILE", "regime_h4_subtype": "UNCONFIRMED_TREND",
         "h4_change_pips_10": 190, "adx": 14.8, "timeframe_conflict": True,
         "conflict_type": "RANGING_D1_VOLATILE_H4", "atr_vs_avg": 1.0},
        {"reason": ""}, "STAND DOWN", False)
    assert why.startswith("The 4-hour chart has been rising")
    return db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9259, atr_pips=109.6,
        decision="STAND DOWN", reason=why, conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="l", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=14.8, adx_h4=33.0,
        weekly_context="W", error=None, market_open=st["open"], market_note=st["note"]).format()


def test_range_volatile_reason_sends_nothing(tmp_path):
    text = _range_volatile_brief(_WED)
    assert "The 4-hour chart has been rising" in text and "Market closed" not in text
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    rows = _ledger(proj)[1]
    assert [r["category"] for r in rows] == ["DIGEST"], rows          # the daily digest only
    assert rows[0]["decision_state"] == "GBP_AUD=STAND ASIDE/open"
    assert 'subtitle "DECISION"' not in _notes(tmp_path) and 'subtitle "ALERT"' not in _notes(tmp_path)


def test_range_volatile_control_a_long_still_notifies(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_AUD", "LONG", _WED)))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert [r["category"] for r in _ledger(proj)[1]] == ["DECISION"]


# ── alert importance (docs/specs/alert_importance_spec.md, 2026-11-15) ────────
# Rule 12: each case asks whether the owner should be told at all.

def _brief_with_alert(tmp_path, when, line, decision="STAND DOWN"):
    text = _rendered("GBP_JPY", decision, when)
    return _brief_printing(tmp_path, text, f"sys.stderr.write({('##ALERT## ' + line + chr(10))!r})\n")


def test_n2_a_bare_regime_change_sends_nothing(tmp_path):
    proj = _project(tmp_path, brief=_brief_with_alert(
        tmp_path, _WED, "GBP/JPY: the market regime changed since the last run. Check the brief."))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""
    assert "ALERT not sent (market closed or nothing to act on): GBP/JPY: the market regime" in _log(proj, "brief")


def test_n2_improved_without_a_decision_change_sends_nothing(tmp_path):
    proj = _project(tmp_path, brief=_brief_with_alert(
        tmp_path, _WED, "GBP/JPY: conditions improved since the last run. Check the brief."))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert _notes(tmp_path) == ""


@pytest.mark.parametrize("line", [
    "GBP/JPY: conditions improved — the framework now allows a trade. Check the brief.",
    "GBP/JPY: conditions deteriorated — the framework has stood down since the last run.",
    "GBP/JPY: exit-watch fired — daily price structure just confirmed a direction. Check the brief.",
])
def test_n2_an_open_actionable_flip_notifies(tmp_path, line):
    proj = _project(tmp_path, brief=_brief_with_alert(tmp_path, _WED, line))
    _run(tmp_path, proj, "scheduled_brief.sh")
    notes = _notes(tmp_path)
    assert 'subtitle "ALERT"' in notes and line.split(" — ")[1][:20] in notes


def test_n1_a_system_alert_line_is_sent_even_when_closed(tmp_path):
    proj = _project(tmp_path, brief=_brief_with_alert(
        tmp_path, _SAT, "EXCLUSION REGISTRY: unreadable registry"))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "ALERT"' in _notes(tmp_path) and "EXCLUSION REGISTRY" in _notes(tmp_path)


def _decision_runs(tmp_path, decisions):
    """Run the wrapper once per decision on GBP/JPY (open market); return the
    notification text after each run."""
    proj = None
    seen = []
    for i, d in enumerate(decisions):
        text = _rendered("GBP_JPY", d, _WED)
        if proj is None:
            proj = _project(tmp_path, brief=_brief_printing(tmp_path, text))
        else:
            (tmp_path / "rendered_brief.txt").write_bytes(text.encode("utf-8"))
        _run(tmp_path, proj, "scheduled_brief.sh")
        seen.append(_notes(tmp_path))
    return proj, seen


def test_n5_an_unchanged_decision_notifies_once(tmp_path):
    _, seen = _decision_runs(tmp_path, ["SHORT", "SHORT", "SHORT"])
    assert seen[-1].count("display notification") == 1 and "GBP/JPY SHORT" in seen[-1]


def test_n5_a_withdrawn_decision_notifies(tmp_path):
    _, seen = _decision_runs(tmp_path, ["SHORT", "STAND DOWN"])
    assert "GBP/JPY back to stand aside — the SHORT idea is withdrawn" in seen[-1]


def test_n5_a_reversal_notifies(tmp_path):
    _, seen = _decision_runs(tmp_path, ["LONG", "SHORT"])
    assert "GBP/JPY SHORT (was LONG)" in seen[-1]


def test_n5_a_stand_aside_with_no_record_is_silent(tmp_path):
    proj, seen = _decision_runs(tmp_path, ["STAND DOWN"])
    assert seen[-1] == ""
    assert json.loads((proj / "logs" / "alert_state.json").read_text())["decisions"] == {
        "GBP_JPY": "STAND ASIDE"}


def test_n5_an_error_brief_neither_notifies_nor_changes_the_record(tmp_path):
    proj, _ = _decision_runs(tmp_path, ["SHORT"])
    (tmp_path / "rendered_brief.txt").write_bytes(_error_page("GBP_JPY").encode("utf-8"))
    before = _notes(tmp_path)
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "DECISION"' not in _notes(tmp_path)[len(before):]
    assert json.loads((proj / "logs" / "alert_state.json").read_text())["decisions"] == {
        "GBP_JPY": "SHORT"}


def test_n5_a_broken_state_helper_falls_back_loudly(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_JPY", "SHORT", _WED)))
    (proj / "logs" / "alert_state.json").write_text("{not json")
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert 'subtitle "DECISION"' in _notes(tmp_path) and "GBP/JPY SHORT" in _notes(tmp_path)
    assert "ALERT STATE FAILED" in _log(proj, "brief")


def test_n6_two_runs_started_together_never_overlap(tmp_path):
    """The lock serializes the runs, so the second brief compares against the
    first run's snapshot instead of seeing the same flip. (Decision repeats are
    also stopped by alert_state's own file lock, so a one-notification count
    alone could not show the run lock works; the run windows can.)"""
    runs = tmp_path / "runs.txt"
    brief = (f"import time\nopen({str(runs)!r}, 'a').write(f'start {{time.time()}}\\n')\n"
             "time.sleep(2)\n"
             f"open({str(runs)!r}, 'a').write(f'end {{time.time()}}\\n')\n"
             + _brief_printing(tmp_path, _rendered("GBP_JPY", "SHORT", _WED)))
    proj = _project(tmp_path, brief=brief)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
           "INTEL_NO_ENV_FILE": "1", "INTEL_PROJ": str(proj)}
    procs = [subprocess.Popen(["/bin/bash", str(proj / "scripts" / "scheduled_brief.sh")],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for _ in range(2)]
    assert [p.wait(timeout=90) for p in procs] == [0, 0]
    events = [ln.split() for ln in runs.read_text().splitlines()]
    assert [e[0] for e in events] == ["start", "end", "start", "end"], events
    assert float(events[2][1]) >= float(events[1][1])             # second began after first ended
    assert _notes(tmp_path).count("display notification") == 1
    assert not (proj / "logs" / ".brief.lock").exists()          # released


def test_n6_a_stale_lock_is_taken_over(tmp_path):
    proj = _project(tmp_path, brief=_brief_printing(tmp_path, _rendered("GBP_JPY", "SHORT", _WED)))
    lock = proj / "logs" / ".brief.lock"
    lock.mkdir()
    old = time.time() - 31 * 60
    os.utime(lock, (old, old))
    _run(tmp_path, proj, "scheduled_brief.sh")
    assert "stale brief lock taken over" in _log(proj, "brief")
    assert 'subtitle "DECISION"' in _notes(tmp_path)


def _write_exclusions_stub(proj):
    (proj / "exclusions.py").write_text("def filter_rows(rows, name):\n    return rows\n")


def test_n3_the_digest_carries_shadow_fires_since_the_last_digest(tmp_path):
    proj = _project(tmp_path)
    _write_exclusions_stub(proj)
    now = time.time()
    t_digest = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 7200))
    t_fire = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
    t_old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 9000))
    (proj / "notification_log.csv").write_text(
        "timestamp_utc,category,pairs,decision_state,summary\n"
        f"{t_digest},DIGEST,GBP_AUD,x,y\n")
    (proj / "shadow_signal_log.csv").write_text(
        "candidate_id,timestamp,instrument,direction,entry\n"
        f"EARLY_MOMENTUM_v2,{t_old},GBP_JPY,LONG,212.0\n"
        f"MOMENTUM_JOIN,{t_fire},GBP_JPY,SHORT,211.026\n")
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    note = [ln for ln in _notes(tmp_path).splitlines() if 'subtitle "DIGEST"' in ln][0]
    assert "· shadow (not traded): MOMENTUM_JOIN GBP/JPY SHORT 211.026 →" in note
    assert "EARLY_MOMENTUM_v2" not in note                        # before the last digest


def test_n3_no_new_fire_no_clause(tmp_path):
    proj = _project(tmp_path)
    _write_exclusions_stub(proj)
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 600))
    (proj / "notification_log.csv").write_text(
        "timestamp_utc,category,pairs,decision_state,summary\n"
        f"{t},DIGEST,GBP_AUD,x,y\n")
    _run(tmp_path, proj, "scheduled_brief.sh", "digest")
    assert "shadow" not in _notes(tmp_path)


def _gate_inputs(proj, episodes, market_open):
    (proj / "shadow_signals.py").write_text(
        "def get_shadow_tally(c):\n"
        f"    return {{'episodes': {episodes} if c == 'MOMENTUM_JOIN' else 0}}\n")
    (proj / "regime_detection.py").write_text(
        f"def _market_status():\n    return {{'open': {market_open}}}\n")


def test_n4_a_review_gate_notifies_once(tmp_path):
    proj = _project(tmp_path, outcome="print('graded 0')")
    _gate_inputs(proj, episodes=20, market_open=True)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    notes = _notes(tmp_path)
    assert notes.count('subtitle "REVIEW"') == 1
    assert "MOMENTUM_JOIN reached 20 graded episodes: the futility checkpoint is due" in notes


def test_n4_a_gate_reached_while_closed_waits_for_the_open(tmp_path):
    proj = _project(tmp_path, outcome="print('graded 0')")
    _gate_inputs(proj, episodes=20, market_open=False)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert "REVIEW" not in _notes(tmp_path)
    _gate_inputs(proj, episodes=20, market_open=True)
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert _notes(tmp_path).count('subtitle "REVIEW"') == 1


def test_n4_a_failing_gate_check_is_logged_not_silent(tmp_path):
    proj = _project(tmp_path, outcome="print('graded 0')")
    (proj / "shadow_signals.py").write_text("raise ImportError('no pandas')\n")
    (proj / "regime_detection.py").write_text("def _market_status():\n    return {'open': True}\n")
    _run(tmp_path, proj, "scheduled_outcome_check.sh")
    assert "ALERT STATE FAILED — review gates not checked" in _log(proj, "outcomes")
