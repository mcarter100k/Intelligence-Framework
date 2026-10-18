"""
test_study_guards.py — studies that run the real brief must not write into
the live ledgers. historical_scenario_replay.py did, when run from the
project root (2026-10-18 review, HYG-1).
"""
import ast
import importlib.util
import os

from _paths import ROOT

_PATH = os.path.join(ROOT, "studies", "historical_scenario_replay.py")


def _study():
    spec = importlib.util.spec_from_file_location("historical_scenario_replay", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                 # import only: no replay runs
    return mod


def test_the_replay_refuses_inside_the_project_and_runs_outside(tmp_path):
    study = _study()
    for inside in (ROOT, os.path.join(ROOT, "studies"), os.path.join(ROOT, "logs")):
        msg = study._refuse_inside_project(inside)
        assert msg and "scripts/reality_run.py script" in msg
    assert study._refuse_inside_project(str(tmp_path)) is None


def test_the_refusal_runs_before_any_replay():
    tree = ast.parse(open(_PATH, encoding="utf-8").read())
    main = next(n for n in tree.body if isinstance(n, ast.If)
                and "__main__" in ast.dump(n.test))
    calls = [ast.unparse(s) for s in main.body]
    first_replay = next(i for i, c in enumerate(calls) if c.startswith("replay_scenario("))
    guard = next(i for i, c in enumerate(calls) if "_refuse_inside_project" in c)
    assert guard < first_replay
