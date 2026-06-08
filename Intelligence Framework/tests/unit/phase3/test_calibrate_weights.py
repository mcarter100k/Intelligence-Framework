"""
tests/unit/phase3/test_calibrate_weights.py

Unit + behavioral tests for calibrate_weights.py feedback engine.

Plain English: verify signal accuracy computation, weight blending, and
               the readiness gate — 15 labeled outcomes per regime required
               before calibration can activate. Includes Scenario L (COT
               extreme positioning) to confirm the readiness threshold holds.
"""

import json
import pytest
from datetime import date, timedelta

import calibrate_weights
from calibrate_weights import (
    MIN_OUTCOMES,
    LEARN_BLEND,
    _DEFAULT_WEIGHTS,
    _direction,
    _htf_aligned,
    _sweep_aligned,
    _strength_aligned,
    _cross_aligned,
    _value_aligned,
    _signal_accuracy,
    _compute_regime_stats,
    _build_learned_weights,
    _blend,
    load_calibrated_weights,
    run_calibration,
)
from tests.fixtures.journal_samples import (
    _base_row, write_journal_csv, YESTERDAY,
)
from tests.fixtures.market_scenarios import SCENARIO_L


# ── _direction() ──────────────────────────────────────────────────────────────

class TestDirection:

    def test_bullish_maps_to_long(self):
        assert _direction({"bias": "BULLISH"}) == "LONG"

    def test_bearish_maps_to_short(self):
        assert _direction({"bias": "BEARISH"}) == "SHORT"

    def test_missing_or_neutral_bias_maps_to_neutral(self):
        assert _direction({}) == "NEUTRAL"
        assert _direction({"bias": "NEUTRAL"}) == "NEUTRAL"


# ── Signal alignment functions ────────────────────────────────────────────────

class TestSignalAlignment:

    # HTF
    def test_htf_aligned_long_established_uptrend(self):
        assert _htf_aligned({"bias": "BULLISH", "htf_context": "ESTABLISHED_UPTREND"}) is True

    def test_htf_aligned_long_pullback_in_uptrend(self):
        assert _htf_aligned({"bias": "BULLISH", "htf_context": "PULLBACK_IN_UPTREND"}) is True

    def test_htf_aligned_short_established_downtrend(self):
        assert _htf_aligned({"bias": "BEARISH", "htf_context": "ESTABLISHED_DOWNTREND"}) is True

    def test_htf_not_aligned_direction_mismatch(self):
        assert _htf_aligned({"bias": "BULLISH", "htf_context": "ESTABLISHED_DOWNTREND"}) is False

    # Sweep
    def test_sweep_aligned_long_bullish_confirmed(self):
        assert _sweep_aligned({"bias": "BULLISH", "sweep_confirmed": "BULLISH_CONFIRMED"}) is True

    def test_sweep_aligned_short_bearish_confirmed(self):
        assert _sweep_aligned({"bias": "BEARISH", "sweep_confirmed": "BEARISH_CONFIRMED"}) is True

    def test_sweep_conflict_blocks_alignment(self):
        assert _sweep_aligned({"bias": "BULLISH", "sweep_confirmed": "CONFLICT"}) is False

    # Strength
    def test_strength_aligned_long_positive_diff(self):
        assert _strength_aligned({"bias": "BULLISH", "strength_diff": "10"}) is True

    def test_strength_aligned_short_negative_diff(self):
        assert _strength_aligned({"bias": "BEARISH", "strength_diff": "-10"}) is True

    def test_strength_not_aligned_weak_diff(self):
        # diff=3, threshold is 5
        assert _strength_aligned({"bias": "BULLISH", "strength_diff": "3"}) is False

    def test_strength_handles_empty_string(self):
        assert _strength_aligned({"bias": "BULLISH", "strength_diff": ""}) is False

    # Value
    def test_value_aligned_long_bullish_verdict(self):
        assert _value_aligned({"bias": "BULLISH", "value_verdict": "BULLISH"}) is True

    def test_value_aligned_short_bearish_verdict(self):
        assert _value_aligned({"bias": "BEARISH", "value_verdict": "BEARISH"}) is True

    def test_value_not_aligned_mismatch(self):
        assert _value_aligned({"bias": "BULLISH", "value_verdict": "BEARISH"}) is False


# ── _signal_accuracy() ────────────────────────────────────────────────────────

class TestSignalAccuracy:

    def test_no_win_rows_returns_0_5(self):
        rows = [{"outcome_label": "LOSS", "bias": "BEARISH", "htf_context": "ESTABLISHED_DOWNTREND"}]
        assert _signal_accuracy(rows, _htf_aligned) == 0.5

    def test_all_wins_all_aligned_returns_1(self):
        rows = [
            {"outcome_label": "WIN", "bias": "BEARISH", "htf_context": "ESTABLISHED_DOWNTREND"},
            {"outcome_label": "WIN", "bias": "BEARISH", "htf_context": "ESTABLISHED_DOWNTREND"},
        ]
        assert _signal_accuracy(rows, _htf_aligned) == 1.0

    def test_wins_aligned_losses_not_gives_perfect_score(self):
        rows = [
            {"outcome_label": "WIN",  "bias": "BEARISH", "htf_context": "ESTABLISHED_DOWNTREND"},
            {"outcome_label": "LOSS", "bias": "BEARISH", "htf_context": "ESTABLISHED_UPTREND"},
        ]
        result = _signal_accuracy(rows, _htf_aligned)
        assert result == 1.0

    def test_returns_float(self):
        rows = [{"outcome_label": "WIN", "bias": "BULLISH", "htf_context": "ESTABLISHED_UPTREND"}]
        assert isinstance(_signal_accuracy(rows, _htf_aligned), float)


# ── _compute_regime_stats() ───────────────────────────────────────────────────

class TestComputeRegimeStats:

    def test_empty_rows_returns_zero_n(self):
        result = _compute_regime_stats("TRENDING_DOWN", [])
        assert result["n"] == 0
        assert result["win_rate"] == 0

    def test_n_is_row_count(self):
        rows = [_base_row(outcome_label=l) for l in ("WIN", "LOSS", "WIN")]
        result = _compute_regime_stats("TRENDING_DOWN", rows)
        assert result["n"] == 3

    def test_win_rate_rounds_correctly(self):
        rows = [_base_row(outcome_label=l) for l in ("WIN", "WIN", "LOSS")]
        result = _compute_regime_stats("TRENDING_DOWN", rows)
        assert result["win_rate"] == 67   # 2/3 → 67%

    def test_signal_accuracy_dict_has_five_keys(self):
        result = _compute_regime_stats("TRENDING_DOWN", [_base_row(outcome_label="WIN")])
        assert set(result["signal_accuracy"].keys()) == {"htf", "liquidity", "strength", "cross", "value"}


# ── _blend() ─────────────────────────────────────────────────────────────────

class TestBlend:

    def _trending_down_learned(self) -> dict:
        return {"htf": 0.40, "strength": 0.27, "liquidity": 0.15,
                "cross": 0.10, "news": 0.05, "rates": 0.02, "cot": 0.01}

    def test_blended_weights_sum_to_one(self):
        default = _DEFAULT_WEIGHTS["TRENDING_DOWN"]
        blended = _blend(self._trending_down_learned(), default)
        assert abs(sum(blended.values()) - 1.0) < 0.01

    def test_blended_value_is_between_learned_and_default(self):
        learned = {"htf": 0.60}
        default = {"htf": 0.35}
        blended = _blend(learned, default)
        assert blended["htf"] > default["htf"]   # blend pulls toward learned

    def test_blend_ratio_applied_correctly(self):
        # learned=1.0, default=0.0 → blended = LEARN_BLEND * 1.0 + 0.30 * 0.0
        blended = _blend({"htf": 1.0}, {"htf": 0.0})
        assert abs(blended["htf"] - LEARN_BLEND) < 0.001

    def test_returns_dict(self):
        result = _blend({"a": 0.5, "b": 0.5}, {"a": 0.5, "b": 0.5})
        assert isinstance(result, dict)


# ── _build_learned_weights() ──────────────────────────────────────────────────

class TestBuildLearnedWeights:

    def _aligned_win_rows(self, n: int) -> list:
        return [
            _base_row(
                outcome_label="WIN",
                regime="TRENDING_DOWN",
                bias="BEARISH",
                htf_context="ESTABLISHED_DOWNTREND",
                sweep_confirmed="BEARISH_CONFIRMED",
                strength_diff="-15",
                value_verdict="BEARISH",
                vix_regime="PANIC_FADING",
            )
            for _ in range(n)
        ]

    def test_weights_sum_approximately_one(self):
        result = _build_learned_weights("TRENDING_DOWN", self._aligned_win_rows(5))
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_all_default_keys_present(self):
        result = _build_learned_weights("TRENDING_DOWN", self._aligned_win_rows(3))
        assert set(result.keys()) == set(_DEFAULT_WEIGHTS["TRENDING_DOWN"].keys())

    def test_returns_dict_of_floats(self):
        result = _build_learned_weights("TRENDING_DOWN", self._aligned_win_rows(3))
        for v in result.values():
            assert isinstance(v, float)


# ── load_calibrated_weights() ─────────────────────────────────────────────────

class TestLoadCalibratedWeights:

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", tmp_path / "absent.json")
        assert load_calibrated_weights() is None

    def test_returns_none_when_weights_are_stale(self, tmp_path, monkeypatch):
        p = tmp_path / "weights.json"
        old_date = (date.today() - timedelta(days=31)).isoformat()
        p.write_text(json.dumps({
            "last_calibrated": old_date,
            "weights": {"TRENDING_DOWN": {"htf": 0.35}},
        }))
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", p)
        assert load_calibrated_weights() is None

    def test_returns_weights_dict_when_fresh(self, tmp_path, monkeypatch):
        p = tmp_path / "weights.json"
        weights = {"TRENDING_DOWN": {"htf": 0.40, "strength": 0.25, "liquidity": 0.15,
                                     "cross": 0.10, "news": 0.07, "rates": 0.02, "cot": 0.01}}
        p.write_text(json.dumps({"last_calibrated": date.today().isoformat(), "weights": weights}))
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", p)
        result = load_calibrated_weights()
        assert result is not None
        assert "TRENDING_DOWN" in result

    def test_returns_none_on_malformed_json(self, tmp_path, monkeypatch):
        p = tmp_path / "weights.json"
        p.write_text("{not valid json}")
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", p)
        assert load_calibrated_weights() is None


# ── run_calibration() ─────────────────────────────────────────────────────────

class TestRunCalibration:

    def _write_journal(self, tmp_path, rows):
        p = tmp_path / "run_journal.csv"
        write_journal_csv(p, rows)
        return p

    def test_empty_journal_returns_empty_dict(self, tmp_path, monkeypatch, capsys):
        p = tmp_path / "run_journal.csv"
        write_journal_csv(p, [])
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        assert run_calibration() == {}

    def test_no_labeled_rows_returns_empty_dict(self, tmp_path, monkeypatch, capsys):
        p = self._write_journal(tmp_path, [_base_row(outcome_label="")])
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", tmp_path / "w.json")
        assert run_calibration() == {}

    def test_below_min_outcomes_does_not_write_file(self, tmp_path, monkeypatch, capsys):
        rows = [_base_row(outcome_label="WIN", regime="TRENDING_DOWN") for _ in range(5)]
        p = self._write_journal(tmp_path, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration()
        assert not weights_p.exists()

    def test_at_min_outcomes_writes_weights_file(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(outcome_label="WIN", regime="TRENDING_DOWN", bias="BEARISH",
                      htf_context="ESTABLISHED_DOWNTREND")
            for _ in range(MIN_OUTCOMES)
        ]
        p = self._write_journal(tmp_path, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration()
        assert weights_p.exists()

    def test_written_file_has_required_keys(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(outcome_label="WIN", regime="TRENDING_DOWN", bias="BEARISH")
            for _ in range(MIN_OUTCOMES)
        ]
        p = self._write_journal(tmp_path, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration()
        data = json.loads(weights_p.read_text())
        assert "last_calibrated" in data
        assert "weights" in data
        assert "min_outcomes_required" in data

    def test_report_only_does_not_write_file(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(outcome_label="WIN", regime="TRENDING_DOWN", bias="BEARISH")
            for _ in range(MIN_OUTCOMES)
        ]
        p = self._write_journal(tmp_path, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration(report_only=True)
        assert not weights_p.exists()

    def test_returns_stats_for_all_four_regimes(self, tmp_path, monkeypatch, capsys):
        rows = [_base_row(outcome_label="WIN", regime="TRENDING_DOWN") for _ in range(5)]
        p = self._write_journal(tmp_path, rows)
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", tmp_path / "w.json")
        result = run_calibration()
        assert len(result) == 4
        assert set(result.keys()) == set(_DEFAULT_WEIGHTS.keys())


# ── Behavioral: Scenario L — readiness check ─────────────────────────────────

class TestScenarioL_CalibrationReadiness:
    """
    Scenario L — GBP 85th percentile COT extreme.
    The calibration readiness gate requires MIN_OUTCOMES=15 labeled runs per
    regime before it can learn from that regime. Until that threshold is met,
    the system uses default weights — no overfitting on sparse data.

    Plain English: COT extreme positions flip the framework's bias. To learn
                   from those flips, the calibration engine needs 15+ labeled
                   outcomes. Before that, it keeps the safety defaults.
    """

    def test_min_outcomes_constant_is_15(self):
        assert MIN_OUTCOMES == 15

    def test_learn_blend_constant_is_70_percent(self):
        assert LEARN_BLEND == 0.70

    def test_below_min_outcomes_keeps_default_weights(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(
                outcome_label="WIN" if i % 2 == 0 else "LOSS",
                regime="TRENDING_DOWN",
                cot_extreme="YES",
                bias="BEARISH",
            )
            for i in range(10)   # 10 < MIN_OUTCOMES
        ]
        p = tmp_path / "run_journal.csv"
        write_journal_csv(p, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration()
        assert not weights_p.exists(), "Should not calibrate with fewer than 15 outcomes"

    def test_exactly_15_cot_outcomes_triggers_calibration(self, tmp_path, monkeypatch, capsys):
        rows = [
            _base_row(
                outcome_label="WIN",
                regime="TRENDING_DOWN",
                cot_extreme="YES",
                bias="BEARISH",
                htf_context="ESTABLISHED_DOWNTREND",
            )
            for _ in range(15)
        ]
        p = tmp_path / "run_journal.csv"
        write_journal_csv(p, rows)
        weights_p = tmp_path / "weights.json"
        monkeypatch.setattr(calibrate_weights, "JOURNAL_PATH", p)
        monkeypatch.setattr(calibrate_weights, "WEIGHTS_PATH", weights_p)
        run_calibration()
        assert weights_p.exists(), "Should calibrate when exactly 15 outcomes are present"

    def test_scenario_l_gbp_net_is_extreme_long(self):
        assert SCENARIO_L["cot_data"]["gbp_net"] == 45_000

    def test_scenario_l_gbp_extreme_flag_set(self):
        assert SCENARIO_L["cot_data"]["gbp_extreme"] is True

    def test_scenario_l_expected_bias_is_bearish_contrarian(self):
        """At 85th percentile long, GBP is exhausted — contrarian goes SHORT."""
        assert SCENARIO_L["expected_bias"] == "BEARISH"

    def test_scenario_l_score_flips_negative(self):
        """COT extreme inverts the raw score: +50 flipped to -50."""
        assert SCENARIO_L["expected_raw_score"] == -50
