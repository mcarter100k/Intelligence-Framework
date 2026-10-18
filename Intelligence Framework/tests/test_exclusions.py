"""
test_exclusions.py — machine-readable exclusion registry
(docs/specs/exclusion_registry_spec.md item 2, team-directed 2026-09-16).

THE REQUIREMENT, in one line: an excluded row cannot reach any tally.

Why it is code and not prose: on 2026-09-16 a Gate-2 verification run
contaminated two evidence rows. A correction entry went into
validation_log.md — which protects a human reading the record. The grader
is code. It runs nightly at 15:15 and would have graded the contaminated
regime row and fed the result into DATA BASIS. A human-readable correction
is not a control.
"""
from _paths import ROOT
import csv
import os

import pytest

import exclusions as ex

from _paths import ROOT as _ROOT

ENTRY = "validation_log.md 2026-09-16 — CORRECTION"


@pytest.fixture
def registry(tmp_path, monkeypatch):
    """An isolated registry — never the real one."""
    p = tmp_path / "excluded_rows.csv"
    monkeypatch.setattr(ex, "REGISTRY_FILE", str(p))
    return p


# ── the registry itself ───────────────────────────────────────────────────────

def test_seeded_with_the_two_contaminated_rows():
    """The real registry carries the 2026-09-16 contamination, both rows."""
    assert os.path.exists(ex.REGISTRY_FILE), "the registry must exist"
    assert "2026-09-16T09:08:08Z" in ex.excluded_ids("session_context_log.csv")
    assert ("2026-09-16T09:08:08Z_GBP_AUD"
            in ex.excluded_ids("regime_classification_log.csv"))


def test_every_real_exclusion_names_an_authorizing_entry():
    """An exclusion with no written authorization is indistinguishable from
    hiding an inconvenient result."""
    with open(ex.REGISTRY_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    for r in rows:
        assert r["authorizing_entry"].strip(), r
        assert r["reason"].strip(), r
        assert r["date"].strip(), r


def test_exclusion_without_authorization_is_refused(registry):
    with pytest.raises(ValueError):
        ex.append_exclusion("id", "some_log.csv", "2026-09-16", "because", "")
    with pytest.raises(ValueError):
        ex.append_exclusion("id", "some_log.csv", "2026-09-16", "", ENTRY)


def test_registry_is_append_only_in_practice(registry):
    ex.append_exclusion("a", "l.csv", "2026-09-16", "r1", ENTRY)
    ex.append_exclusion("b", "l.csv", "2026-09-16", "r2", ENTRY)
    assert ex.excluded_ids("l.csv") == {"a", "b"}


def test_exclusions_are_scoped_to_their_ledger(registry):
    ex.append_exclusion("shared-id", "ledger_a.csv", "2026-09-16", "r", ENTRY)
    assert ex.excluded_ids("ledger_a.csv") == {"shared-id"}
    assert ex.excluded_ids("ledger_b.csv") == set()


def test_missing_registry_fails_open_not_closed(tmp_path, monkeypatch, capsys):
    """Nothing excluded, rather than everything. A grader that silently
    excludes the whole ledger because a file is missing is worse than one
    that excludes nothing."""
    monkeypatch.setattr(ex, "REGISTRY_FILE", str(tmp_path / "nope.csv"))
    assert ex.excluded_ids("anything.csv") == set()
    assert ex.filter_rows([{"log_id": "x"}], "anything.csv") == [{"log_id": "x"}]


# ── identity matching ─────────────────────────────────────────────────────────

def test_id_column_ledger_matches_on_its_id(registry):
    ex.append_exclusion("2026-09-16T09:08:08Z_GBP_AUD",
                        "regime_classification_log.csv", "2026-09-16", "r",
                        ENTRY)
    row = {"log_id": "2026-09-16T09:08:08Z_GBP_AUD",
           "timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_AUD"}
    assert ex.excluder("regime_classification_log.csv")(row)


def test_idless_ledger_matches_on_bare_timestamp(registry):
    """session_context_log.csv has no id column. A bare timestamp is the
    conservative reading: it excludes every instrument logged at that
    instant."""
    ex.append_exclusion("2026-09-16T09:08:08Z", "session_context_log.csv",
                        "2026-09-16", "r", ENTRY)
    row = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_AUD"}
    assert ex.excluder("session_context_log.csv")(row)


def test_idless_ledger_also_matches_timestamp_instrument(registry):
    ex.append_exclusion("2026-09-16T09:08:08Z_GBP_AUD",
                        "session_context_log.csv", "2026-09-16", "r", ENTRY)
    hit = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_AUD"}
    miss = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_JPY"}
    assert ex.excluder("session_context_log.csv")(hit)
    assert not ex.excluder("session_context_log.csv")(miss)


def test_unexcluded_rows_are_untouched(registry):
    ex.append_exclusion("2026-09-16T09:08:08Z", "session_context_log.csv",
                        "2026-09-16", "r", ENTRY)
    honest = {"timestamp": "2026-09-16T09:07:52Z", "instrument": "GBP_AUD"}
    assert not ex.excluder("session_context_log.csv")(honest)


# ── THE REQUIREMENT: an excluded row cannot reach any tally ───────────────────

def test_excluded_row_cannot_reach_the_regime_accuracy_tally(
        tmp_path, monkeypatch, registry):
    import regime_classifier_logger as rcl

    ex.append_exclusion("BAD_ID", "regime_classification_log.csv",
                        "2026-09-16", "contaminated", ENTRY)

    def _rows():
        base = {k: "" for k in rcl.FIELDNAMES}
        good = dict(base, log_id="GOOD_ID", timestamp="2026-09-15T00:00:00Z",
                    instrument="GBP_AUD", composite_regime="VOLATILE",
                    outcome_filled="True", outcome_correct="True",
                    adx_d1="20", adx_h4="20", prediction_window="20")
        bad = dict(base, log_id="BAD_ID", timestamp="2026-09-16T09:08:08Z",
                   instrument="GBP_AUD", composite_regime="VOLATILE",
                   outcome_filled="True", outcome_correct="False",
                   adx_d1="20", adx_h4="20", prediction_window="20")
        return [good, bad]

    monkeypatch.setattr(rcl, "_read_all", _rows)
    acc = rcl.get_regime_accuracy(instrument="GBP_AUD", min_samples=1)
    total_n = sum(v["n"] for v in acc.values())
    assert total_n == 1, (
        f"the excluded row reached the tally (n={total_n}, expected 1)")
    # n alone cannot prove exclusion: the fixture's two rows are one
    # independent state, so dedup gives n == 1 with or without the
    # registry (exclusion_registry_fixes_spec D3). The RAW count and the
    # correct count can only be 1 if the BAD row never reached the tally.
    assert sum(v["n_raw"] for v in acc.values()) == 1, (
        "the excluded row reached the raw tally")
    assert sum(v["correct"] for v in acc.values()) == 1


def test_excluded_row_cannot_reach_the_trade_accuracy_tally(
        tmp_path, monkeypatch, registry):
    import trade_outcome_logger as tol

    ex.append_exclusion("BAD_SIG", "trade_signal_log.csv", "2026-09-16",
                        "contaminated", ENTRY)

    ledger = tmp_path / "trade_signal_log.csv"
    base = {k: "" for k in tol._FIELDS}
    rows = [
        dict(base, signal_id="GOOD_SIG", instrument="GBP_AUD",
             regime_d1="VOLATILE", direction="SHORT", conviction="50",
             outcome_filled="True", signal_correct="True"),
        dict(base, signal_id="BAD_SIG", instrument="GBP_AUD",
             regime_d1="VOLATILE", direction="SHORT", conviction="50",
             outcome_filled="True", signal_correct="False"),
    ]
    with open(ledger, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tol._FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    monkeypatch.setattr(tol, "_LOG_FILE", str(ledger))

    acc = tol.get_accuracy_by_regime(instrument="GBP_AUD", min_samples=1)
    total_n = sum(v["n"] for v in acc.values())
    assert total_n == 1, (
        f"the excluded row reached the tally (n={total_n}, expected 1)")


def test_excluded_row_cannot_reach_a_session_delta(tmp_path, monkeypatch,
                                                   registry):
    """The observed harm: a synthetic filter_allowed made the next honest
    run render 'conditions deteriorated' and fire an alert for a flip that
    never happened."""
    import session_memory as sm

    ex.append_exclusion("2026-09-16T09:08:08Z", "session_context_log.csv",
                        "2026-09-16", "contaminated", ENTRY)

    ledger = tmp_path / "session_context_log.csv"
    with open(ledger, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sm.FIELDNAMES)
        w.writeheader()
        for ts, allowed in (("2026-09-16T07:56:21Z", "False"),
                            ("2026-09-16T09:08:08Z", "True"),   # synthetic
                            ("2026-09-16T09:16:46Z", "False")):
            w.writerow({"timestamp": ts, "instrument": "GBP_AUD",
                        "adx_d1": "21.9", "adx_h4": "34.8",
                        "atr_ratio": "0.93", "regime_d1": "VOLATILE",
                        "regime_h4": "TRENDING_UP",
                        "structure_d1": "DOWNTREND",
                        "filter_allowed": allowed})
    monkeypatch.setattr(sm, "LOG_FILE", str(ledger))

    # _get_today_rows keeps only rows stamped with the CURRENT UTC date.
    # Without a frozen clock this test returned [] on every day but
    # 2026-09-16 and passed vacuously (exclusion_registry_fixes_spec D3).
    class _Frozen(sm.datetime):
        @classmethod
        def now(cls, tz=None):
            return sm.datetime(2026, 9, 16, 12, 0, tzinfo=tz)
    monkeypatch.setattr(sm, "datetime", _Frozen)

    rows = sm._get_today_rows("GBP_AUD")
    stamps = [r["timestamp"] for r in rows]
    assert stamps == ["2026-09-16T07:56:21Z", "2026-09-16T09:16:46Z"], (
        f"expected exactly the two honest rows, got {stamps}")
    assert all(r["filter_allowed"] == "False" for r in rows), (
        "no surviving row may carry the synthetic filter flip")


def test_excluded_row_cannot_reach_a_shadow_episode_count(
        tmp_path, monkeypatch, registry):
    import shadow_signals as ss

    ex.append_exclusion("2026-09-16T09:08:08Z", "shadow_signal_log.csv",
                        "2026-09-16", "contaminated", ENTRY)

    ledger = tmp_path / "shadow_signal_log.csv"
    base = {k: "" for k in ss._FIELDS}
    with open(ledger, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ss._FIELDS)
        w.writeheader()
        for ts in ("2026-08-01T00:00:00Z", "2026-09-16T09:08:08Z"):
            w.writerow(dict(base, candidate_id="THRUST_PULLBACK",
                            timestamp=ts, instrument="GBP_AUD",
                            direction="SHORT", entry="1.88", stop="1.89",
                            atr="80", adx="25", structure="DOWNTREND",
                            outcome_filled="False"))
    monkeypatch.setattr(ss, "LOG_FILE", str(ledger))

    assert ss.episode_count("THRUST_PULLBACK", "GBP_AUD") == 1, (
        "the excluded row was counted as an episode")
    assert ss.get_shadow_tally("THRUST_PULLBACK", "GBP_AUD")["logged"] == 1


# ── D1: a malformed or missing registry fails OPEN and LOUD, never silent ─────
# (docs/specs/exclusion_registry_fixes_spec.md)

REG_HEADER = "log_id,ledger,date,reason,authorizing_entry\n"
GOOD_ROW = ("KEEP_ME,regime_classification_log.csv,2026-09-16,"
            "contaminated,validation_log.md 2026-09-16\n")


@pytest.fixture(autouse=True)
def _fresh_alert_memory(monkeypatch):
    """Alerts print once per process; tests need a clean slate each."""
    monkeypatch.setattr(ex, "_warned", set(), raising=False)


def _alerts(capsys):
    return [ln for ln in capsys.readouterr().err.splitlines()
            if ln.startswith("##ALERT## EXCLUSION REGISTRY")]


def test_short_row_is_skipped_loudly_and_valid_rows_still_apply(
        registry, capsys):
    """The 2026-09-29 repro: a hand-appended short row made DictReader fill
    None and .strip() raise — and every caller swallowed it silently."""
    registry.write_text(REG_HEADER + GOOD_ROW + "JUST_AN_ID\n",
                        encoding="utf-8")
    ids = ex.excluded_ids("regime_classification_log.csv")
    assert ids == {"KEEP_ME"}, "one bad line must not disable the registry"
    alerts = _alerts(capsys)
    assert len(alerts) == 1 and "line 3" in alerts[0] and "SKIPPED" in alerts[0]


def test_non_utf8_registry_fails_open_with_an_alert(registry, capsys):
    registry.write_bytes(REG_HEADER.encode() + b"BAD\xff,x.csv,d,r,a\n")
    pred = ex.excluder("regime_classification_log.csv")
    assert pred({"log_id": "BAD"}) is False           # fail OPEN
    alerts = _alerts(capsys)
    assert len(alerts) == 1 and "UnicodeDecodeError" in alerts[0]


def test_missing_registry_fails_open_with_an_alert(registry, capsys):
    assert not registry.exists()
    assert ex.excluded_ids("regime_classification_log.csv") == set()
    alerts = _alerts(capsys)
    assert len(alerts) == 1 and "not found" in alerts[0]


def test_wrong_header_fails_open_with_an_alert(registry, capsys):
    registry.write_text("id,file\nX,regime_classification_log.csv\n",
                        encoding="utf-8")
    assert ex.excluded_ids("regime_classification_log.csv") == set()
    alerts = _alerts(capsys)
    assert len(alerts) == 1 and "header" in alerts[0]


def test_each_alert_prints_once_per_process(registry, capsys):
    """Seven call sites consult the registry in one run; one line, not seven."""
    for _ in range(7):
        ex.excluder("regime_classification_log.csv")
    assert len(_alerts(capsys)) == 1


def test_a_broken_registry_alert_reaches_a_real_tally_path(
        tmp_path, monkeypatch, registry, capsys):
    """End to end through a real caller: the grader-side tally must alert,
    not swallow. Before the fix this path printed nothing."""
    import trade_outcome_logger as tol
    registry.write_bytes(REG_HEADER.encode() + b"\xff\n")
    ledger = tmp_path / "trade_signal_log.csv"
    with open(ledger, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=tol._FIELDS).writeheader()
    monkeypatch.setattr(tol, "_LOG_FILE", str(ledger))
    tol.get_accuracy_by_regime(instrument="GBP_AUD", min_samples=1)
    assert _alerts(capsys), "a registry failure on a tally path must alert"


def test_no_call_site_swallows_a_registry_failure():
    """The seven copy-pasted `try: from exclusions import ... except
    Exception:` blocks turned every registry error into a silent empty set.
    Call sites now import exclusions at module level and use excluder() /
    filter_rows(), which alert and fail open themselves."""
    import re
    for mod in ("regime_classifier_logger.py", "trade_outcome_logger.py",
                "shadow_signals.py", "session_memory.py"):
        src = open(os.path.join(_ROOT, mod), encoding="utf-8").read()
        assert re.search(r"^from exclusions import ", src, re.M), mod
        assert not re.search(r"^[ \t]+from exclusions import", src, re.M), (
            f"{mod}: a function-local exclusions import is back")
        assert "excluded_ids(" not in src, (
            f"{mod}: call sites must use excluder(), not excluded_ids()")


# ── D2: the shadow grader and the brief's pending line honor the registry ─────

def _shadow_ledger(tmp_path, ss, stamps):
    ledger = tmp_path / "shadow_signal_log.csv"
    base = {k: "" for k in ss._FIELDS}
    with open(ledger, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ss._FIELDS)
        w.writeheader()
        for ts in stamps:
            w.writerow(dict(base, candidate_id="MOMENTUM_JOIN", timestamp=ts,
                            instrument="GBP_AUD", direction="LONG",
                            entry="1.8800", stop="1.8700", atr="80",
                            adx="35", structure="UPTREND",
                            outcome_filled="False"))
    return ledger


def test_shadow_grader_never_grades_an_excluded_row(tmp_path, monkeypatch,
                                                     registry):
    import pandas as pd
    import oanda_feed
    import shadow_signals as ss

    idx = pd.date_range("2026-09-01T01:00:00Z", periods=40, freq="4h")
    df = pd.DataFrame({"Open": 1.885, "High": 1.886, "Low": 1.884,
                       "Close": 1.885}, index=idx)
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: True)
    monkeypatch.setattr(oanda_feed, "get_h4_bars", lambda **k: df)

    good, bad = (t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in idx[:2])
    ex.append_exclusion(bad, "shadow_signal_log.csv", "2026-09-29",
                        "test contamination", ENTRY)
    ledger = _shadow_ledger(tmp_path, ss, [good, bad])
    monkeypatch.setattr(ss, "LOG_FILE", str(ledger))

    assert ss.grade_pending_shadow("GBP_AUD") == 1
    rows = {r["timestamp"]: r for r in csv.DictReader(open(ledger))}
    assert set(rows) == {good, bad}, "the excluded row must stay in the ledger"
    assert rows[good]["outcome_filled"] == "True"
    assert rows[bad]["outcome_filled"] == "False", "excluded row was graded"
    assert rows[bad]["r_multiple"] == ""


def test_brief_pending_signal_never_surfaces_an_excluded_row(
        tmp_path, monkeypatch, registry):
    import shadow_signals as ss
    older, newest = "2026-09-28T05:00:00Z", "2026-09-29T05:00:00Z"
    ex.append_exclusion(newest, "shadow_signal_log.csv", "2026-09-29",
                        "test contamination", ENTRY)
    monkeypatch.setattr(ss, "LOG_FILE",
                        str(_shadow_ledger(tmp_path, ss, [older, newest])))
    sig = ss.latest_pending_signal("GBP_AUD")
    assert sig is not None and sig["timestamp"] == older
