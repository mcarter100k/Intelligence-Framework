"""test_missed_moves.py — studies/missed_moves.py (report-only).

Synthetic bars + a synthetic regime log, day log, trade-signal log and shadow
log. Covers: move detection (zig-zag, size filter, still-running leg),
alignment (decision of record, reasons, shadow with/against), the rule-9
distinction between "framework not running" and "stood aside" (a positive
control: the same move flips from NOT_RUNNING to SAT_OUT only when reads
exist), exclusions respected, and plain-English output.
"""
import csv
import hashlib
import importlib.util
import os
from datetime import datetime, timedelta, timezone

import pytest

from _paths import ROOT
from test_brief_display import _assert_clean

_PATH = os.path.join(ROOT, "studies", "missed_moves.py")


def _load():
    spec = importlib.util.spec_from_file_location("missed_moves", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mm = _load()

UTC = timezone.utc
T0 = datetime(2026, 1, 20, 0, 0, tzinfo=UTC)          # first H4 bar open
PIP = 0.0001
BASE = 1.9000


def _h4_path():
    """Waypoints in pips (ATR is exactly 100 pips):
    idx 0-5 flat 0; 6-15 +30 each -> 300; 16-20 -30 each -> 150;
    21-22 +60 each -> 270; 23-34 -30 each -> -90; 35 +30 -> -60.
    Legs: 0->15 up 300 (MOVE), 15->20 down 150 (too small),
    20->22 up 120 (too small), 22->34 down 360 still running (MOVE)."""
    p = [0] * 6
    for _ in range(10):
        p.append(p[-1] + 30)
    for _ in range(5):
        p.append(p[-1] - 30)
    for _ in range(2):
        p.append(p[-1] + 60)
    for _ in range(12):
        p.append(p[-1] - 30)
    p.append(p[-1] + 30)
    return p


def _bars():
    h4 = []
    for i, pips in enumerate(_h4_path()):
        c = round(BASE + pips * PIP, 5)
        h4.append((T0 + timedelta(hours=4 * i), c + 0.0005, c - 0.0005, c))
    d1 = [(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=d), 1.905, 1.895, 1.900)
          for d in range(40)]
    return h4, d1


def _h(n):
    return T0 + timedelta(hours=n)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _regime(t, stand_down=True, pair="GBP_AUD", d1="VOLATILE", sub="", excluded=False):
    return {"log_id": f"{_iso(t)}_{pair}", "timestamp": _iso(t), "instrument": pair,
            "regime_d1": d1, "regime_h4": "TRENDING_UP", "stand_down": str(stand_down),
            "subtype": sub, "_excluded": excluded}


def _brief(t, decision="STAND ASIDE", reason="The daily chart gives no trend direction",
           kind="READ", pair="GBP_AUD"):
    return {"time": t, "pair": pair, "decision": decision, "reason": reason,
            "kind": kind, "file": "brief_x.log"}


def _run(regime=(), briefs=(), signals=(), shadows=(), **kw):
    return mm.analyse(["GBP_AUD"], {"GBP_AUD": _bars()}, list(regime), list(briefs),
                      list(signals), list(shadows), **kw)


# ── move detection ───────────────────────────────────────────────────────────

def test_daily_atr_is_the_brief_atr_and_has_no_lookahead():
    _, d1 = _bars()
    pts = mm.daily_atr_points(d1)
    assert abs(pts[0][1] - 0.01) < 1e-12
    # first ATR is computed at the close of D bar 14 (open Jan 15 + 24 h)
    assert pts[0][0] == datetime(2026, 1, 16, tzinfo=UTC)
    assert mm.atr_at(pts, datetime(2026, 1, 15, 23, 59, tzinfo=UTC)) is None


def test_zigzag_finds_both_big_moves_and_drops_the_small_legs():
    h4, d1 = _bars()
    moves, _ = mm.find_moves("GBP_AUD", h4, d1)
    got = [(m["start_i"], m["end_i"], m["dir"], round(m["pips"]), m["running"]) for m in moves]
    assert got == [(0, 15, "UP", 300, False), (22, 34, "DOWN", 360, True)]
    m1 = moves[0]
    assert m1["start"] == _h(4) and m1["end"] == _h(64)          # bar closes
    assert abs(m1["mult"] - 3.0) < 1e-9 and m1["bars"] == 15
    assert abs(moves[1]["mult"] - 3.6) < 1e-9


def test_size_threshold_and_reversal_threshold_are_parameters():
    h4, d1 = _bars()
    moves, _ = mm.find_moves("GBP_AUD", h4, d1, k=3.5)
    assert [round(m["pips"]) for m in moves] == [360]
    # a reversal threshold of 2 ATR ignores the 150- and 120-pip swings:
    # one rise 0->15, one fall 15->34 (390 pips)
    moves, _ = mm.find_moves("GBP_AUD", h4, d1, rev=2.0)
    assert [(m["start_i"], m["end_i"]) for m in moves] == [(0, 15), (15, 34)]


# ── rule 9: not running vs stood aside (positive control) ────────────────────

def _move2(results):
    return next(a for m, a in results if m["start_i"] == 22)


def test_no_runs_during_a_move_is_framework_not_running_never_stood_aside():
    regime = [_regime(_h(2))]                  # in scope, but nothing near move 2
    results, cov, _ = _run(regime)
    a = _move2(results)
    assert a["verdict"] == "NOT_RUNNING" and a["running_bars"] == 0
    report = mm.render(results, cov, {"k": 2.0, "rev": 1.0, "pairs": ["GBP_AUD"]}, [])
    row = next(ln for ln in report.splitlines() if ln.startswith("| 2 |"))
    assert "framework not running for the whole move" in row and "stood aside" not in row.lower()


def test_positive_control_the_same_move_reads_sat_out_once_reads_exist():
    regime = [_regime(_h(2))] + [_regime(_h(h)) for h in range(90, 142, 8)]
    a = _move2(_run(regime)[0])
    assert a["verdict"] == "SAT_OUT" and a["entire"] is True
    assert a["running_bars"] == a["bars"] == 12


def test_partly_running_move_is_sat_out_but_not_entirely():
    regime = [_regime(_h(h)) for h in (2, 10, 18, 26)]       # stops at 26 h
    results, cov, _ = _run(regime)
    m1 = next(a for m, a in results if m["start_i"] == 0)
    assert m1["verdict"] == "SAT_OUT" and m1["entire"] is False
    # bars closing 8..36 h are within 12 h of a run; 40..64 h are not
    assert m1["running_bars"] == 8 and m1["bars"] == 15
    report = mm.render(results, cov, {"k": 2.0, "rev": 1.0, "pairs": ["GBP_AUD"]}, [])
    assert "framework not running for 47% of the move" in report


def test_error_pages_are_not_reads():
    regime = [_regime(_h(2))]
    briefs = [_brief(_h(h), decision="STAND ASIDE", kind="ERROR",
                     reason="Framework error — do not trade: OANDA") for h in range(94, 142, 8)]
    results, cov, _ = _run(regime, briefs)
    a = _move2(results)
    assert a["verdict"] == "NOT_RUNNING"
    assert a["label_counts"]["framework error"] > 0
    assert cov["GBP_AUD"]["errors"] == 6


def test_moves_before_the_first_run_are_out_of_scope():
    regime = [_regime(_h(80))]                  # after move 1 started
    results, cov, _ = _run(regime)
    assert [m["start_i"] for m, _ in results] == [22]
    assert cov["GBP_AUD"]["out_of_scope"] == 1


# ── alignment ────────────────────────────────────────────────────────────────

def test_brief_decision_is_the_decision_of_record_and_disagreement_is_counted():
    # regime says stand_down False (pre-2026-09-30 meaning); the brief said STAND ASIDE
    regime = [_regime(_h(2))] + [_regime(_h(h), stand_down=False) for h in range(90, 142, 8)]
    briefs = [_brief(_h(h) + timedelta(minutes=1)) for h in range(90, 142, 8)]
    results, _, stats = _run(regime, briefs)
    a = _move2(results)
    assert a["verdict"] == "SAT_OUT" and a["dec"]["STAND ASIDE"] == 7
    assert stats["GBP_AUD"]["regime stand_down disagrees with brief"] == 7


def test_stand_down_false_without_a_brief_is_not_recorded_not_a_trade():
    regime = [_regime(_h(2))] + [_regime(_h(h), stand_down=False) for h in range(90, 142, 8)]
    a = _move2(_run(regime)[0])
    assert a["verdict"] == "UNRECORDED"


def test_trade_signal_direction_gives_with_against_and_both():
    regime = [_regime(_h(2))] + [_regime(_h(h), stand_down=False) for h in range(90, 142, 8)]
    sig = lambda h, d: {"timestamp": _iso(_h(h) + timedelta(seconds=2)),
                        "instrument": "GBP_AUD", "direction": d, "_excluded": False}
    assert _move2(_run(regime, signals=[sig(98, "SHORT")])[0])["verdict"] == "WITH"
    assert _move2(_run(regime, signals=[sig(98, "LONG")])[0])["verdict"] == "AGAINST"
    both = [sig(98, "LONG"), sig(106, "SHORT")]
    assert _move2(_run(regime, signals=both)[0])["verdict"] == "BOTH"


def test_reasons_are_classified_and_the_main_one_is_the_most_common():
    regime = [_regime(_h(2))] + [_regime(_h(h)) for h in range(90, 142, 8)]
    texts = ["Major economic event ahead — BOJ Policy Rate in 82 minutes"] * 2 + \
            ["Range breaking down — 4-hour chart volatile inside daily chart range"] * 4 + \
            ["daily chart in transition zone (trend strength 20/100)"]
    briefs = [_brief(_h(h), reason=t) for h, t in zip(range(90, 142, 8), texts)]
    a = _move2(_run(regime, briefs)[0])
    assert a["reasons"] == {mm.R_NEWS: 2, mm.R_H4: 4, mm.R_DAILY: 1}
    assert a["top_reason"] == mm.R_H4


@pytest.mark.parametrize("text,cat", [
    ("Major economic event ahead — CPI m/m in 14 minutes", "R_NEWS"),
    ("The market is in an exhaustion move — fade, don't follow.", "R_STRETCHED"),
    ("Short blocked: dominant 20-week trend is uptrend.", "R_WEEKLY"),
    ("Range mid-zone or edge blocked by the dominant weekly trend", "R_WEEKLY"),
    ("Setup grades C (conviction 15 of 100)", "R_WEAK"),
    ("The daily chart gives no trend direction to follow", "R_DAILY"),
    ("Daily chart trend strength is 26/100 — but price structure has not confirmed", "R_DAILY"),
    ("daily chart in transition zone (trend strength 21.7/100) — 4-hour chart trending up", "R_DAILY"),
    ("daily chart trend intact (trending down), 4-hour chart ranging — pullback", "R_H4"),
    ("Daily downtrend intact, but the 4-hour chart has not resolved", "R_H4"),
    ("something new", "R_OTHER"),
])
def test_reason_categories(text, cat):
    assert mm.classify_reason(text) == getattr(mm, cat)


def test_regime_fallback_reason_when_no_brief_exists():
    assert mm.reason_from_regime({"regime_d1": "VOLATILE", "subtype": ""}) == mm.R_DAILY
    assert mm.reason_from_regime({"regime_d1": "TRENDING_DOWN", "subtype": "h4=EXHAUSTION"}) == mm.R_STRETCHED
    assert mm.reason_from_regime({"regime_d1": "TRENDING_DOWN", "subtype": ""}) == mm.R_H4


def test_shadow_fires_with_and_against_the_move():
    regime = [_regime(_h(2))]
    sh = lambda h, d, ex=False: {"candidate_id": "EARLY_MOMENTUM_v2", "timestamp": _iso(_h(h)),
                                 "instrument": "GBP_AUD", "direction": d, "_excluded": ex}
    shadows = [sh(100, "SHORT"), sh(110, "LONG"), sh(120, "SHORT"), sh(300, "SHORT"),
               sh(104, "SHORT", ex=True)]
    a = _move2(_run(regime, shadows=shadows)[0])
    assert (len(a["fires"]), a["fires_with"], a["fires_against"]) == (3, 2, 1)


def test_reruns_within_ten_minutes_collapse_to_one_run():
    regime = [_regime(_h(2))] + [_regime(_h(98) + timedelta(minutes=m)) for m in (0, 3, 6)]
    runs, stats = mm.build_runs("GBP_AUD", regime, [], [])
    assert len(runs) == 2
    assert stats["runs collapsed (re-runs within 10 minutes)"] == 2


# ── exclusions ───────────────────────────────────────────────────────────────

def _registry(tmp_path, monkeypatch, rows):
    import exclusions
    path = tmp_path / "excluded_rows.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(exclusions.FIELDS)
        for log_id, ledger in rows:
            w.writerow([log_id, ledger, "2026-11-03", "test", "test entry"])
    monkeypatch.setattr(exclusions, "REGISTRY_FILE", str(path))


def test_excluded_regime_row_and_its_brief_block_are_dropped(tmp_path, monkeypatch):
    t = _h(110)
    _registry(tmp_path, monkeypatch, [(f"{_iso(t)}_GBP_AUD", "regime_classification_log.csv")])
    raw = [_regime(_h(2)), _regime(t)]
    for r in raw:
        r.pop("_excluded")
    regime = mm._mark_excluded(raw, "regime_classification_log.csv")
    assert [r["_excluded"] for r in regime] == [False, True]
    briefs = [_brief(t + timedelta(minutes=2))]
    results, _, stats = _run(regime, briefs)
    assert _move2(results)["verdict"] == "NOT_RUNNING"
    assert stats["GBP_AUD"]["brief blocks dropped with an excluded row"] == 1
    # positive control: with an empty registry the same row makes it SAT_OUT
    _registry(tmp_path, monkeypatch, [])
    regime = mm._mark_excluded(raw, "regime_classification_log.csv")
    assert _move2(_run(regime, briefs)[0])["verdict"] == "SAT_OUT"


def test_excluded_trade_signal_is_not_a_trade(tmp_path, monkeypatch):
    t = _h(98)
    _registry(tmp_path, monkeypatch, [(f"{_iso(t)}_GBP_AUD", "trade_signal_log.csv")])
    raw = [{"signal_id": f"{_iso(t)}_GBP_AUD", "timestamp": _iso(t),
            "instrument": "GBP_AUD", "direction": "LONG"}]
    regime = [_regime(_h(2)), _regime(t, stand_down=True)]
    signals = mm._mark_excluded(raw, "trade_signal_log.csv")
    assert _move2(_run(regime, signals=signals)[0])["verdict"] == "SAT_OUT"
    _registry(tmp_path, monkeypatch, [])
    signals = mm._mark_excluded(raw, "trade_signal_log.csv")
    regime = [_regime(_h(2)), _regime(t, stand_down=False)]
    assert _move2(_run(regime, signals=signals)[0])["verdict"] == "AGAINST"


# ── day-log parsing ──────────────────────────────────────────────────────────

_DAYLOG = """----- calendar auto-fetch -----
===== 2026-10-29 02:44:43 PDT =====
═══════
  GBP/AUD  |  Thu 29 Oct 2026 2:44 AM PDT
  Price: 1.8922  |  ATR: 100.7 pips
═══════

  DECISION     STAND ASIDE — conditions not right to trade

  REASON       Major economic event ahead — BOJ
               Policy Rate in 82 minutes.

  CONFIDENCE   0/100  |  Rating: C

═══════
  GBP/JPY  |  Thu 29 Oct 2026 2:44 AM PDT
═══════

  DECISION     SHORT ▼ — sell

  REASON       daily chart trend intact (trending
               down), 4-hour chart ranging.

===== 2026-11-01 05:00:00 PST =====
  GBP/AUD  |  Sun 01 Nov 2026
  Market closed — analysis based on last close. Next open Sun 2:00 PM PST.
  DECISION     LONG  ▲ — buy

  REASON       something
===== 2026-11-02 05:00:00 PST =====
  GBP/AUD  |  Mon 02 Nov 2026
  DECISION     STAND ASIDE — conditions not right to trade

  REASON       Framework error — do not trade: OANDA
               unreachable.
===== 2026-11-02 06:00:00 XYZ =====
  GBP/AUD  |  Mon 02 Nov 2026
  DECISION     STAND ASIDE
"""


def test_day_log_blocks_are_parsed_per_pair_in_utc(tmp_path):
    (tmp_path / "brief_2026-10-29.log").write_text(_DAYLOG)
    blocks, unparsed = mm.parse_brief_logs(str(tmp_path))
    assert unparsed == 1
    got = [(b["time"], b["pair"], b["decision"], b["kind"]) for b in blocks]
    assert got == [
        (datetime(2026, 10, 29, 9, 44, 43, tzinfo=UTC), "GBP_AUD", "STAND ASIDE", "READ"),
        (datetime(2026, 10, 29, 9, 44, 43, tzinfo=UTC), "GBP_JPY", "SHORT", "READ"),
        (datetime(2026, 11, 1, 13, 0, tzinfo=UTC), "GBP_AUD", "LONG", "CLOSED"),
        (datetime(2026, 11, 2, 13, 0, tzinfo=UTC), "GBP_AUD", "STAND ASIDE", "ERROR"),
    ]
    assert blocks[0]["reason"] == "Major economic event ahead — BOJ Policy Rate in 82 minutes."
    assert mm.classify_reason(blocks[0]["reason"]) == mm.R_NEWS


def test_a_closed_market_read_never_counts_as_a_trade():
    regime = [_regime(_h(2))]
    briefs = [_brief(_h(h), decision="LONG", kind="CLOSED") for h in range(94, 142, 8)]
    a = _move2(_run(regime, briefs)[0])
    assert a["verdict"] == "NOT_RUNNING" and a["label_counts"]["market closed"] > 0


# ── report ───────────────────────────────────────────────────────────────────

def _report():
    regime = [_regime(_h(h)) for h in (2, 10, 18, 26)]
    briefs = [_brief(_h(h) + timedelta(minutes=1)) for h in (2, 10)]
    shadows = [{"candidate_id": "MOMENTUM_JOIN", "timestamp": _iso(_h(30)),
                "instrument": "GBP_AUD", "direction": "LONG", "_excluded": False}]
    results, cov, _ = _run(regime, briefs, shadows=shadows)
    return mm.render(results, cov, {"k": 2.0, "rev": 1.0, "pairs": ["GBP_AUD"]},
                     ["GBP_AUD: technical note with ATR and stand_down"])


def test_trader_facing_part_is_plain_english():
    report = _report()
    head, sep, tail = report.partition("<!-- trader-facing section ends -->")
    assert sep and "## Methods (technical)" in tail
    _assert_clean(head)
    assert "ATR" not in head and "zig-zag" not in head.lower()
    assert "GBP/AUD" in head and "MOMENTUM_JOIN buy x1" in head


def test_report_states_hindsight_and_the_parameters():
    report = _report()
    assert "NOT a profit that was available" in report
    assert "at least 2 times a normal day's range" in report
    assert "reversal threshold 1 x daily ATR(14)" in report
    assert "Sat out (framework running and standing aside whenever it ran): 1" in report
    assert "GBP/AUD 300 pips" in report


def _digest(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ("venv", "__pycache__", ".pytest_cache", ".git")]
        for f in fns:
            p = os.path.join(dp, f)
            out[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def test_main_end_to_end_reads_ledgers_writes_only_the_report(tmp_path, monkeypatch):
    fields = ["log_id", "timestamp", "instrument", "regime_d1", "regime_h4",
              "stand_down", "subtype"]
    with open(tmp_path / "regime_classification_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for h in (2, 10, 18, 26):
            w.writerow(_regime(_h(h)))
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(mm, "_fetch", lambda pair, start: _bars())
    before = _digest(str(tmp_path))
    mm.main(["--pairs", "GBP_AUD", "--out", "r.md"])
    after = _digest(str(tmp_path))
    assert set(after) - set(before) == {str(tmp_path / "r.md")}
    assert all(after[k] == v for k, v in before.items())
    text = (tmp_path / "r.md").read_text()
    assert "Moves found: 2 (GBP/AUD 2)" in text
    with pytest.raises(SystemExit):
        mm.main(["--pairs", "GBP_AUD", "--out", "ledger.csv"])
