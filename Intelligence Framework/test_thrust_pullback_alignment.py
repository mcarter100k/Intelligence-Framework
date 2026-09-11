"""
test_thrust_pullback_alignment.py — thrust_pullback_alignment fix (pinned).

The fourth silent failure: `compute_atr_series` returns n - 14 values while
the bar arrays hold n, so `check_thrust_pullback`'s `atr[b]` (bar index into
the shorter ATR list) raised IndexError on EVERY live call from go-live —
and `check_shadow_signals` swallowed it into "no signal". The existing
Gate-1 fixtures built `atr` the same length as the bars (a shape the live
feed never produces), which is why the suite stayed green.

Pins here:
  * the live shape contract itself (len(atr) == n - 14)
  * THRUST_PULLBACK evaluates and fires at the LIVE shape (would raise
    pre-fix), and still behaves identically at the legacy equal-length
    fixture shape (off = 0)
  * a raising candidate is LOUD (##ALERT## stderr marker) and never
    silences the other candidates
"""
from datetime import datetime, timezone

import shadow_signals as ss
from regime_detection import compute_atr_series, _ATR_PERIOD


def _ctx(O, H, L, C, atr, struct="TRANSITIONAL"):
    n = len(C)
    return {
        "O": O, "H": H, "L": L, "C": C,
        "T": [datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)] * n,
        "atr": atr, "pip": 0.0001, "adx": 20.0, "adx_slope": 0.0,
        "struct": struct, "sd": {},
    }


def _flat(n, base=1.9000):
    # H-L = 0.0010 each bar => the REAL smoothed ATR sits near 0.0010, so
    # the same geometry works at both the live shape (computed ATR) and the
    # legacy fixture shape (atr = [0.0010] * n).
    O = [base] * n
    H = [base + 0.0005] * n
    L = [base - 0.0005] * n
    C = [base] * n
    return O, H, L, C


def _embed_thrust(O, H, L, C):
    """Firing geometry (box -> thrust -> pullback -> fresh close-back),
    placed at the END of an arbitrary-length series. Box = [1.8995, 1.9005]."""
    n = len(C)
    b = n - 11                      # break bar inside the candidate window
    O[b], C[b], H[b], L[b] = 1.9015, 1.9030, 1.9032, 1.9014
    L[b + 4], C[b + 4], H[b + 4] = 1.9006, 1.9010, 1.9012   # pullback to edge
    C[n - 2], H[n - 2], L[n - 2] = 1.9004, 1.9006, 1.9002
    O[n - 1], C[n - 1], H[n - 1], L[n - 1] = 1.9005, 1.9020, 1.9022, 1.9003


def test_live_shape_contract_pinned():
    n = 300
    O, H, L, C = _flat(n)
    assert len(compute_atr_series(H, L, C)) == n - _ATR_PERIOD == 286


def test_thrust_pullback_no_longer_raises_at_live_shape():
    """Pre-fix: IndexError on every call at this shape. Now: clean None."""
    n = 300
    O, H, L, C = _flat(n)
    atr = compute_atr_series(H, L, C)
    assert ss.check_thrust_pullback("GBP_AUD", _ctx(O, H, L, C, atr)) is None


def test_thrust_pullback_fires_at_live_shape():
    n = 300
    O, H, L, C = _flat(n)
    _embed_thrust(O, H, L, C)
    atr = compute_atr_series(H, L, C)
    assert len(atr) == n - _ATR_PERIOD          # genuinely the live shape
    s = ss.check_thrust_pullback("GBP_AUD", _ctx(O, H, L, C, atr))
    assert s is not None and s["direction"] == "LONG"
    assert s["entry"] == 1.9020                 # the close-back bar
    assert s["stop"] == 1.8995                  # opposite box edge


def test_thrust_pullback_unchanged_at_legacy_fixture_shape():
    """off = 0 (equal lengths) must behave exactly as the frozen pins do —
    the alignment fix changes indexing, never the trigger."""
    n = 300
    O, H, L, C = _flat(n)
    _embed_thrust(O, H, L, C)
    s = ss.check_thrust_pullback("GBP_AUD", _ctx(O, H, L, C, [0.0010] * n))
    assert s is not None and s["direction"] == "LONG"
    assert s["entry"] == 1.9020 and s["stop"] == 1.8995


def test_candidate_error_is_loud_and_never_silences_the_rest(monkeypatch, capsys):
    def _boom(instrument, ctx):
        raise IndexError("list index out of range")

    def _fires(instrument, ctx):
        return {"candidate_id": "STUB", "timestamp": "t", "instrument": instrument,
                "direction": "LONG", "entry": 1.9, "stop": 1.89, "atr": 0.001,
                "adx": 20.0, "adx_slope": 0.0, "structure": "UPTREND", "extra": ""}

    monkeypatch.setattr(ss, "_CANDIDATES", [_boom, _fires])
    n = 40
    O, H, L, C = _flat(n)
    out = ss.check_shadow_signals("GBP_AUD", _ctx(O, H, L, C, [0.0010] * n))

    assert [s["candidate_id"] for s in out] == ["STUB"]   # the rest still ran
    err = capsys.readouterr().err
    assert "##ALERT## SHADOW CANDIDATE ERROR" in err
    assert "_boom" in err and "GBP_AUD" in err
    assert "IndexError" in err


def test_healthy_candidates_emit_no_error_marker(capsys):
    n = 300
    O, H, L, C = _flat(n)
    atr = compute_atr_series(H, L, C)
    ss.check_shadow_signals("GBP_AUD", _ctx(O, H, L, C, atr))
    assert "SHADOW CANDIDATE ERROR" not in capsys.readouterr().err
