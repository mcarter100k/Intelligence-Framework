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
import csv
import os

import pytest

import exclusions as ex

_ROOT = os.path.dirname(os.path.abspath(__file__))

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
    assert ex.is_excluded(row, "regime_classification_log.csv")


def test_idless_ledger_matches_on_bare_timestamp(registry):
    """session_context_log.csv has no id column. A bare timestamp is the
    conservative reading: it excludes every instrument logged at that
    instant."""
    ex.append_exclusion("2026-09-16T09:08:08Z", "session_context_log.csv",
                        "2026-09-16", "r", ENTRY)
    row = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_AUD"}
    assert ex.is_excluded(row, "session_context_log.csv")


def test_idless_ledger_also_matches_timestamp_instrument(registry):
    ex.append_exclusion("2026-09-16T09:08:08Z_GBP_AUD",
                        "session_context_log.csv", "2026-09-16", "r", ENTRY)
    hit = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_AUD"}
    miss = {"timestamp": "2026-09-16T09:08:08Z", "instrument": "GBP_JPY"}
    assert ex.is_excluded(hit, "session_context_log.csv")
    assert not ex.is_excluded(miss, "session_context_log.csv")


def test_unexcluded_rows_are_untouched(registry):
    ex.append_exclusion("2026-09-16T09:08:08Z", "session_context_log.csv",
                        "2026-09-16", "r", ENTRY)
    honest = {"timestamp": "2026-09-16T09:07:52Z", "instrument": "GBP_AUD"}
    assert not ex.is_excluded(honest, "session_context_log.csv")


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
    monkeypatch.setattr(sm, "datetime", sm.datetime)

    rows = sm._get_today_rows("GBP_AUD")
    stamps = [r["timestamp"] for r in rows]
    assert "2026-09-16T09:08:08Z" not in stamps, (
        "the contaminated row reached the delta comparison")
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
