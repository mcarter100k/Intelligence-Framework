"""
test_foundation_tools.py — the instruments that produce the honest numbers.

power_check.py and episodes.py (foundation/tools/) compute every power figure
and every independent-episode count the framework reports. Both failed
silently rather than loudly before these tests existed:
  * power_check's "avg R without best episode" removed every episode equal to
    the max and substituted 0.0 when none were left (six -1R -> +0.000);
  * episodes' to_bar_index compared strings (Z vs +00:00 off by one bar) and
    clamped out-of-range fires onto a real bar instead of raising (I5).
Assertions pin the expected VALUE, never a bound (M19).
"""
import importlib.util
import os
import subprocess
import sys

import pytest

from _paths import ROOT
TOOLS = os.path.join(ROOT, "foundation", "tools")


def _load(name):
    spec = importlib.util.spec_from_file_location(f"foundation_{name}", os.path.join(TOOLS, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = _load("power_check")
ep = _load("episodes")


def _observed(capsys, rs):
    pc._report_observed(rs)
    return capsys.readouterr().out


def _line(out, label):
    hits = [l for l in out.splitlines() if l.startswith(label)]
    assert len(hits) <= 1, out
    return hits[0].split(":", 1)[1].split()[0] if hits else None


WITHOUT_BEST = "avg R without best episode"
LOWER_BOUND = "90% one-sided lower bound"


# ── power_check: avg R without best episode ─────────────────────────────────

def test_without_best_all_equal_losses_keeps_five_losses(capsys):
    # The I15 shape: guaranteed -1R rows. Removing one of six leaves five -1R.
    out = _observed(capsys, [-1.0] * 6)
    assert _line(out, WITHOUT_BEST) == "-1.000"


def test_without_best_absent_at_n1_and_no_invented_zero(capsys):
    out = _observed(capsys, [-1.0])
    assert _line(out, WITHOUT_BEST) is None
    assert "+0.000" not in out
    assert "0.0" not in out


def test_without_best_tied_maxima_removes_exactly_one(capsys):
    out = _observed(capsys, [-1, -1, -1, 2.5, 2.5])
    assert _line(out, WITHOUT_BEST) == "-0.125"


def test_without_best_normal_case_removes_only_the_best(capsys):
    rs = [-1, -1, 2, 0.5, -0.3, 1.1, -1, 0.2, -1, 3]
    out = _observed(capsys, rs)
    assert _line(out, WITHOUT_BEST) == "-0.056"          # (2.5 - 3) / 9
    assert "<- outlier-driven" in out                    # mean +0.25 > 0 >= -0.056


# ── power_check: bootstrap gate (percentile, M3 floor of 20) ────────────────

RS20 = [-1.0] * 12 + [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, -0.5, 0.2]


def test_bootstrap_suppressed_below_20(capsys):
    out = _observed(capsys, RS20[:19])
    assert _line(out, LOWER_BOUND) is None
    assert "bootstrap" not in out


def test_bootstrap_present_at_20_and_labelled_percentile(capsys):
    out = _observed(capsys, RS20)
    assert _line(out, LOWER_BOUND) == "-0.465"
    assert "percentile bootstrap, under-covers on skewed R" in out


# ── power_check: arithmetic anchors (the coin-flip figures M10 cites) ───────

def test_n_required_anchor():
    assert pc.n_required(0.15, 1.2, 0.8) == 396


def test_power_at_n_anchor():
    assert round(pc.power_at_n(0.15, 1.2, 60), 2) == 0.25
    assert round(pc.power_at_n(0.15, 1.2, 60), 4) == 0.2493   # 2 dp alone lets small drifts through


def test_false_pass_rate_anchor():
    assert round(pc.false_pass_rate(0.15, 1.2, 60), 2) == 0.17
    assert round(pc.false_pass_rate(0.15, 1.2, 60), 4) == 0.1665


# ── episodes: bar-index mapping (instants, never defaults) ──────────────────

BARS = [f"2026-09-18T{h}:00:00Z" for h in ("01", "05", "09", "13", "17", "21")]


def test_same_instant_any_spelling_maps_to_same_bar():
    fires = ["2026-09-18T09:00:00Z",
             "2026-09-18T09:00:00+00:00",
             "2026-09-18T08:00:00-01:00",
             "2026-09-18T09:00:00.000000000Z"]   # OANDA's nanosecond form
    assert ep.to_bar_index(fires, BARS) == [2, 2, 2, 2]


def test_bar_spelling_does_not_move_the_index():
    bars = [b.replace("Z", "+00:00") for b in BARS]
    # 12:00-01:00 is 13:00Z; as a string it sorts before "13:00" and lands a bar early.
    assert ep.to_bar_index(["2026-09-18T12:00:00-01:00", "2026-09-18T13:30:00Z"], bars) == [3, 3]


def test_fire_before_first_bar_raises():
    with pytest.raises(ValueError, match="2020-01-01T00:00:00Z"):
        ep.to_bar_index(["2020-01-01T00:00:00Z"], BARS)


def test_fire_after_last_bar_raises():
    with pytest.raises(ValueError, match="2030-01-01T00:00:00Z"):
        ep.to_bar_index(["2030-01-01T00:00:00Z"], BARS)


def test_unparseable_timestamp_raises_naming_it():
    with pytest.raises(ValueError, match="not-a-time"):
        ep.to_bar_index(["not-a-time"], BARS)


def test_timezone_less_timestamp_raises_naming_it():
    with pytest.raises(ValueError, match="2026-09-18T09:00:00'"):
        ep.to_bar_index(["2026-09-18T09:00:00"], BARS)


def test_count_episodes_non_overlap():
    assert ep.count_episodes([0, 1, 2, 30, 31], 30) == [0, 30]


# ── episodes: CLI (graded filter, loud failure) ─────────────────────────────

def _write(path, header, rows):
    path.write_text("\n".join([header] + rows) + "\n")
    return str(path)


def _cli(tmp_path, fire_rows, *extra):
    bars = _write(tmp_path / "bars.csv", "time", BARS)
    fires = _write(tmp_path / "fires.csv", "fire_time,outcome", fire_rows)
    return subprocess.run(
        [sys.executable, os.path.join(TOOLS, "episodes.py"), fires, "--time-col", "fire_time",
         "--bars", bars, "--horizon", "3", *extra],
        capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def test_cli_pending_rows_dropped_and_counted(tmp_path):
    r = _cli(tmp_path, ["2026-09-18T01:00:00Z,-1.0",
                        "2026-09-18T05:00:00Z,pending",
                        "2026-09-18T09:00:00Z,PENDING",
                        "2026-09-18T13:00:00Z,n/a",
                        "2026-09-18T13:00:00Z,False",
                        "2026-09-18T17:00:00Z,",
                        "2026-09-18T17:00:00Z,0.5"],
             "--graded-col", "outcome")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [
        "dropped as ungraded (outcome): 5 of 7 rows",
        "all: 2 rows -> 2 independent episodes   INSUFFICIENT (<20)",
    ]


def test_cli_extra_ungraded_value(tmp_path):
    r = _cli(tmp_path, ["2026-09-18T01:00:00Z,-1.0", "2026-09-18T17:00:00Z,open"],
             "--graded-col", "outcome", "--ungraded-value", "OPEN")
    assert r.stdout.splitlines()[0] == "dropped as ungraded (outcome): 1 of 2 rows"


def test_cli_unknown_graded_col_errors(tmp_path):
    r = _cli(tmp_path, ["2026-09-18T01:00:00Z,-1.0"], "--graded-col", "r_multiple")
    assert r.returncode == 2
    assert "'r_multiple' is not a column" in r.stderr
    assert "independent episodes" not in r.stdout


def test_cli_unmappable_fires_fail_loudly(tmp_path):
    r = _cli(tmp_path, ["2020-01-01T00:00:00Z,-1", "2030-01-01T00:00:00Z,1"],
             "--graded-col", "outcome")
    assert r.returncode == 2
    assert "2020-01-01T00:00:00Z" in r.stderr
    assert "independent episodes" not in r.stdout


# ── power_check: multiple cells (Sidak) ─────────────────────────────────────

def _power_cli(*args):
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "power_check.py"), *args],
                       capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def test_family_wise_rate_six_cells_is_26_percent():
    # Three candidates x two pairs at one-sided alpha 0.05 per cell.
    assert round(pc.family_wise_rate(0.05, 6), 4) == 0.2649


def test_sidak_alpha_six_cells_holds_family_at_alpha():
    assert round(pc.sidak_alpha(0.05, 6), 6) == 0.008512
    assert round(pc.family_wise_rate(pc.sidak_alpha(0.05, 6), 6), 12) == 0.05


def test_cli_cells_adjusts_n_required_and_prints_family_rate():
    assert _power_cli("--edge", "0.15", "--sd", "1.2", "--power", "0.8", "--cells", "6") == [
        "Cells: 6. Family-wise false-pass at alpha 0.05 per cell: 26%; Sidak per-cell alpha 0.0085 "
        "holds it at 5%. Figures below use the Sidak alpha.",
        "N required: 667 independent episodes (edge +0.15R, SD 1.2R, power 80%, alpha 0.008512)",
    ]


def test_cli_cells_adjusts_power_and_min_edge_and_false_pass():
    out = _power_cli("--edge", "0.15", "--sd", "1.2", "--n", "60", "--threshold", "0.15", "--cells", "6")
    assert out[1:] == ["Power: 8% (edge +0.15R, SD 1.2R, N=60, alpha 0.008512)",
                       "Zero-edge false-pass rate at avg R >= +0.15: 17% per cell, "
                       "66% family-wise across 6 cells"]
    assert _power_cli("--sd", "1.2", "--n", "60", "--cells", "6")[1] == \
        "Smallest edge detectable at 80% power: +0.50R (SD 1.2R, N=60, alpha 0.008512)"


def test_cli_one_cell_is_unadjusted():
    assert _power_cli("--edge", "0.15", "--sd", "1.2", "--power", "0.8") == [
        "N required: 396 independent episodes (edge +0.15R, SD 1.2R, power 80%, alpha 0.05)"]
