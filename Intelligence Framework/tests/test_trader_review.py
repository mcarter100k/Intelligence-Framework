"""
test_trader_review.py — scripts/trader_review.py, the trader review loop
(foundation/trader_review.md).

Every test runs in its own tmp_path (conftest chdir), which is where the
tool's cwd-relative ledgers land. Protections pinned here:
  P1 a taken idea is scored only from its trades.csv fill, never from memory
  P2 scoring appends; the IDEA row's bytes never change
  P3 a week that has not ended cannot be written (no mid-week rule changes)
  P4 a week is written once
  P5 run outside the project folder, nothing is written
  P6 a missing framework read is counted on its own, never as a disagreement
  P7 a missing journal reads "not started", never as a week of zeros
  P8 R: the stop defines it, the sign follows the direction, paper pays the spread
"""
import csv
import os
import re
import sys
from datetime import datetime, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import trader_review as tr  # noqa: E402

BANNED = re.compile(r'\bADX\b|HH/HL|LH/LL|\bpivot\b|ATR ratio')

# Wed 4 Nov 2026 20:00 UTC = Wed 12:00 PST (ISO week 2026-W45)
WED = datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)
# Sat 7 Nov 2026 18:00 UTC = Sat 10:00 PST, same week
SAT = datetime(2026, 11, 7, 18, 0, tzinfo=timezone.utc)


def scripted(*answers):
    it = iter(answers)
    return lambda _prompt: next(it)


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "session_context_log.csv").write_text("timestamp\n")
    # exclusions reads its registry by absolute path; give it an empty one
    import exclusions
    reg = tmp_path / "excluded_rows.csv"
    reg.write_text(",".join(exclusions.FIELDS) + "\n")
    monkeypatch.setattr(exclusions, "REGISTRY_FILE", str(reg))
    return tmp_path


def rows(path="idea_journal.csv"):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# A taken GBP/JPY long: zone, trigger, entry 212.17, stop 211.45, target 213.78
TAKEN_LONG = ("GBP_JPY", "LONG", "first-pullback", "212.0-212.2", "hourly higher low",
              "212.17", "211.45", "213.78", "B+", "yes", "calm", "")
PASSED_SHORT = ("GBP_AUD", "SHORT", "retest-fade", "1.930", "hourly turns down",
                "1.9300", "1.9360", "1.9180", "B", "no", "against the daily", "bored", "")


def write_stack(path, ts, pair="GBP_JPY", direction="LONG", fw="NO TRADE",
                grade="C", against="True"):
    import setup_check
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=setup_check._JOURNAL_FIELDS)
        w.writeheader()
        w.writerow({"stack_id": f"STACK_{pair}", "timestamp": ts, "instrument": pair,
                    "direction": direction, "framework_direction": fw,
                    "framework_grade": grade, "against_framework": against})


def write_fill(pair="GBP_JPY", direction="LONG", open_price=212.17, stop=211.45,
               close_price=213.61, opened="2026-11-04 21:00:00"):
    import trade_logger
    path = os.path.abspath("trades.csv")
    trade_logger._append_row({"row_type": "OPEN", "position_id": "GBPJPY-001",
                              "timestamp_utc": opened, "instrument": pair,
                              "direction": direction, "open_price": open_price,
                              "stop": stop, "size": 0.01}, path)
    trade_logger._append_row({"row_type": "CLOSE", "position_id": "GBPJPY-001",
                              "timestamp_utc": "2026-11-05 10:00:00", "instrument": pair,
                              "direction": direction, "open_price": open_price,
                              "stop": stop, "close_price": close_price}, path)


# ── P8 arithmetic ────────────────────────────────────────────────────────────

def test_r_multiple_long_short_and_cost():
    assert tr.r_multiple("LONG", 212.17, 211.45, 213.61) == 2.0
    assert tr.r_multiple("LONG", 212.17, 211.45, 211.45) == -1.0
    assert tr.r_multiple("SHORT", 1.9300, 1.9360, 1.9180) == 2.0
    assert tr.r_multiple("SHORT", 1.9300, 1.9360, 1.9360) == -1.0
    # a 4-pip spread on a 60-pip stop costs 0.067R
    assert tr.r_multiple("SHORT", 1.9300, 1.9360, 1.9360, cost=0.0004) == -1.067
    with pytest.raises(ValueError):
        tr.r_multiple("LONG", 1.0, 1.0, 1.1)


def test_process_score_is_rules_followed_over_five():
    keys = [k for k, _ in tr.PROCESS_QUESTIONS]
    assert tr.process_score({k: True for k in keys}) == 1.0
    assert tr.process_score({keys[0]: True, keys[2]: True}) == 0.4
    assert tr.process_score({}) == 0.0


def test_weeks_are_pacific_monday_to_sunday():
    # Sun 8 Nov 23:30 PST is still W45; Mon 9 Nov 00:30 PST is W46
    assert tr.week_of(datetime(2026, 11, 9, 7, 30, tzinfo=timezone.utc)) == "2026-W45"
    assert tr.week_of(datetime(2026, 11, 9, 8, 30, tzinfo=timezone.utc)) == "2026-W46"
    assert tr.default_review_week(WED) == "2026-W44"   # weekday: last week
    assert tr.default_review_week(SAT) == "2026-W45"   # weekend: this week
    assert not tr.week_is_over("2026-W45", WED)
    assert tr.week_is_over("2026-W45", SAT)


# ── P5 project folder guard ──────────────────────────────────────────────────

def test_outside_the_project_nothing_is_written(tmp_path):
    with pytest.raises(tr.NotInProject):
        tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    assert tr.main(["review", "--no-write"]) == 2
    assert not os.path.exists("idea_journal.csv")
    assert not os.path.exists("trader_review_log.csv")


# ── idea: the framework's read ───────────────────────────────────────────────

def test_idea_takes_the_framework_read_from_a_recent_pre_trade_check(project):
    write_stack("pre_trade_journal.csv", "2026-11-04T18:30:00Z")   # 1.5 h earlier
    row = tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    assert row["framework_read"] == "NO TRADE (grade C)"
    assert row["agrees_with_framework"] == "NO"
    assert row["stack_id"] == "STACK_GBP_JPY"
    [saved] = rows()
    assert saved["row_type"] == "IDEA" and saved["taken"] == "YES"
    assert saved["risk_pct"] == "0.5" and saved["planned_rr_after_spread"] != ""


def test_an_old_pre_trade_check_is_not_used(project):
    write_stack("pre_trade_journal.csv", "2026-11-04T10:00:00Z")   # 10 h earlier
    row = tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    assert row["framework_read"] == "not recorded"


def test_idea_falls_back_to_the_latest_brief(project):
    os.makedirs("logs")
    with open(tr.BRIEF_FILE, "w") as f:
        f.write("LATEST RUN — 2026-11-04 07:33:53 PST\n"
                "  GBP/JPY  |  Wed 04 Nov 2026 7:33 AM PST\n"
                "  DECISION     STAND ASIDE — conditions not right to trade\n")
    row = tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    assert row["framework_read"] == "STAND ASIDE"
    assert row["framework_read_source"] == "brief of 2026-11-04 07:33:53 PST"
    assert row["agrees_with_framework"] == "NO"


def test_a_stop_on_the_wrong_side_is_asked_again(project):
    answers = list(TAKEN_LONG)
    answers[5:5] = ["212.17", "212.50", "213.78"]       # stop above a long entry
    tr.log_idea(ask=scripted(*answers), now=WED)
    [saved] = rows()
    assert saved["stop"] == "211.45"


# ── P1 / P2 scoring ──────────────────────────────────────────────────────────

def test_a_taken_idea_is_never_scored_from_memory(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    before = open("idea_journal.csv", "rb").read()
    out = tr.score_idea(ask=scripted("", ""), now=SAT)
    assert out is None
    assert open("idea_journal.csv", "rb").read() == before


def test_a_taken_idea_is_scored_from_its_fill_and_the_idea_row_is_untouched(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    before = open("idea_journal.csv", "rb").read()
    write_fill()
    row = tr.score_idea(ask=scripted("", "",            # idea id, position id
                                     "yes", "yes", "yes", "no", "yes",
                                     "skipped partial",
                                     "target", "213.70", "212.00"), now=SAT)
    assert row["r_realized"] == 2.0                      # (213.61-212.17)/0.72
    assert row["process_score"] == 0.8
    assert row["scored_on"] == "FILL (trades.csv)"
    assert row["mfe_r"] == 2.125 and row["mae_r"] == -0.236
    after = open("idea_journal.csv", "rb").read()
    assert after.startswith(before)                      # append-only
    assert [r["row_type"] for r in rows()] == ["IDEA", "SCORE"]


def test_a_fill_opened_before_the_idea_is_not_matched(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    write_fill(opened="2026-11-03 09:00:00")
    assert tr.score_idea(ask=scripted("", ""), now=SAT) is None


def test_a_passed_idea_is_scored_on_paper_less_the_spread(project):
    tr.log_idea(ask=scripted(*PASSED_SHORT), now=WED)
    row = tr.score_idea(ask=scripted("", "yes", "1.9360", "stop", "", "",
                                     "stopped-then-reversed"), now=SAT)
    assert row["r_realized"] == -1.067                   # stopped, plus 4 pips
    assert row["loss_species"] == "stopped_then_reversed"
    assert row["scored_on"].startswith("PAPER")


def test_a_passed_idea_that_never_filled_has_no_result(project):
    tr.log_idea(ask=scripted(*PASSED_SHORT), now=WED)
    row = tr.score_idea(ask=scripted("", "no"), now=SAT)
    assert row["scored_on"] == "PAPER: never filled" and "r_realized" not in row
    n = tr.week_numbers("2026-W45")
    assert n["paper_scored"] == 0 and n["paper_never_filled"] == 1


def test_a_rescore_appends_and_the_latest_counts(project):
    tr.log_idea(ask=scripted(*PASSED_SHORT), now=WED)
    tr.score_idea(ask=scripted("", "yes", "1.9360", "stop", "", "", "other"), now=SAT)
    tr.score_idea(ask=scripted("yes", "1.9180", "target", "", ""), now=SAT,
                  idea_id=rows()[0]["idea_id"])
    assert [r["row_type"] for r in rows()] == ["IDEA", "SCORE", "SCORE"]
    assert tr.week_numbers("2026-W45")["paper_avg_r"] == pytest.approx(1.933, abs=1e-3)


# ── review: numbers and display ──────────────────────────────────────────────

def test_a_missing_journal_reads_as_not_started(project):
    text = tr.render_review(tr.week_numbers("2026-W45"))
    assert "the loop has not started" in text
    assert "0 logged" not in text


def test_an_empty_week_reads_as_zero_ideas(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    text = tr.render_review(tr.week_numbers("2026-W44"))
    assert "0 logged" in text and "has not started" not in text


def test_a_missing_read_is_not_a_disagreement(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)       # no stack, no brief
    n = tr.week_numbers("2026-W45")
    assert n["against_framework"] == 0 and n["read_not_recorded"] == 1
    assert "not recorded for 1" in tr.render_review(n)


def test_the_review_counts_trades_against_the_framework(project):
    write_stack("pre_trade_journal.csv", "2026-11-04T18:30:00Z")
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    tr.log_idea(ask=scripted(*PASSED_SHORT), now=WED)
    n = tr.week_numbers("2026-W45")
    assert (n["ideas"], n["taken"], n["passed"]) == (2, 1, 1)
    assert n["against_framework"] == 1                    # the taken long only
    assert n["read_not_recorded"] == 1                    # the passed short


def test_review_numbers_and_plain_words(project):
    tr.log_idea(ask=scripted(*TAKEN_LONG), now=WED)
    write_fill()
    tr.score_idea(ask=scripted("", "", "yes", "no", "yes", "yes", "yes",
                               "moved stop", "target", "", ""), now=SAT)
    with open("notification_log.csv", "w") as f:
        f.write("timestamp_utc,category,pairs,decision_state,summary\n"
                "2026-11-04T16:37:24Z,DIGEST,GBP_AUD GBP_JPY,x,y\n"
                "2026-10-27T16:37:24Z,DIGEST,GBP_AUD GBP_JPY,x,y\n")
    n = tr.week_numbers("2026-W45")
    assert n["taken_avg_r"] == 2.0 and n["taken_win_pct"] == 100
    assert n["process_avg"] == 0.8 and n["top_rule_break"] == "moved stop"
    assert n["notifications_total"] == 1
    text = tr.render_review(n)
    assert BANNED.search(text) is None, text
    assert "Under 20: no claims about edge" in text


# ── P3 / P4 writing the review ───────────────────────────────────────────────

def test_a_week_that_has_not_ended_cannot_be_written(project):
    n = tr.week_numbers("2026-W45")
    assert tr.write_review(n, ask=scripted("lesson"), now=WED) is None
    assert not os.path.exists("trader_review_log.csv")


def test_a_week_is_written_once(project):
    with open("notification_log.csv", "w") as f:
        f.write("timestamp_utc,category,pairs,decision_state,summary\n"
                "2026-11-04T16:37:24Z,DIGEST,GBP_AUD GBP_JPY,x,y\n")
    n = tr.week_numbers("2026-W45")
    row = tr.write_review(n, ask=scripted("5", "1", "waited for the trigger", ""), now=SAT)
    assert row["notifications_material"] == 1            # 5 > 1 total: asked again
    assert row["rule_change"] == "none" and row["applies_from"] == "2026-11-09"
    assert tr.write_review(n, ask=scripted("1", "again", "x"), now=SAT) is None
    with open("trader_review_log.csv", newline="") as f:
        assert len(list(csv.DictReader(f))) == 1


def test_main_review_no_write_runs_without_input(project, capsys):
    assert tr.main(["review", "--week", "2026-W45", "--no-write"]) == 0
    assert "WEEKLY REVIEW  2026-W45" in capsys.readouterr().out
    assert not os.path.exists("trader_review_log.csv")
