"""
test_reality_run.py — the Gate-2 tool must neutralize relative-path writes
and must CATCH any write that escapes into the project (AGENTS.md rule 10).

Runs scripts/reality_run.py against a throwaway project, never the real one.
"""
import importlib.util
import os
import sys
import textwrap

_ROOT = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "reality_run", os.path.join(_ROOT, "scripts", "reality_run.py"))
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def _project(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "regime_classification_log.csv").write_text("log_id\nA\n")
    (proj / ".env").write_text("export OANDA_API_KEY=abc\nOANDA_ACCOUNT_ID='42'\n")
    return proj


def _script(tmp_path, body):
    p = tmp_path / "target.py"
    p.write_text(textwrap.dedent(body))
    return str(p)


def test_relative_ledger_writes_land_in_the_copy_not_the_project(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        import os
        with open("regime_classification_log.csv", "a") as f:
            f.write("B\\n")
        assert os.environ["OANDA_API_KEY"] == "abc"          # .env was loaded
        assert os.environ["OANDA_ACCOUNT_ID"] == "42"
    """)
    rc = rr.reality_run(str(proj), [target], python=sys.executable)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert (proj / "regime_classification_log.csv").read_text() == "log_id\nA\n"
    assert "ledger copy changed: regime_classification_log.csv (2 -> 3 lines)" in out
    assert "UNCHANGED" in out


def test_a_write_that_escapes_into_the_project_fails_the_run(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, f"""
        with open({str(proj / 'regime_classification_log.csv')!r}, "a") as f:
            f.write("CONTAMINATED\\n")
    """)
    rc = rr.reality_run(str(proj), [target], python=sys.executable)
    out = capsys.readouterr().out
    assert rc == 2
    assert "##ALERT## REALITY RUN CHANGED THE PROJECT: regime_classification_log.csv" in out


def test_no_env_runs_without_credentials(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        import os, sys
        sys.exit(0 if "OANDA_API_KEY" not in os.environ else 1)
    """)
    assert rr.reality_run(str(proj), [target], use_env=False,
                          python=sys.executable) == 0


def test_env_file_parsing_matches_shell_export_semantics(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# comment\n\nA=1\nexport B=\"two\"\nC='3'\n")
    assert rr.load_env_file(str(p)) == {"A": "1", "B": "two", "C": "3"}


def test_an_error_page_is_not_a_reality_run(tmp_path, capsys):
    """The brief exits 0 even when it renders an error page. On 2026-09-29
    the first version of this tool certified such a run as a success."""
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        print("REASON  Framework error — do not trade: OANDA not configured")
    """)
    rc = rr.reality_run(str(proj), [target], python=sys.executable)
    out = capsys.readouterr().out
    assert rc == 3
    assert "NOT a valid REALITY GATE" in out


def test_a_missing_env_file_is_flagged(tmp_path, capsys):
    proj = _project(tmp_path)
    (proj / ".env").unlink()
    target = _script(tmp_path, "pass\n")
    rr.reality_run(str(proj), [target], python=sys.executable)
    assert "no .env" in capsys.readouterr().out


def test_options_after_the_target_are_honored(tmp_path, monkeypatch):
    """`reality_run.py brief --project X --code Y` once silently ignored both
    options, and ran the wrong project with no credentials."""
    seen = {}
    monkeypatch.setattr(rr, "reality_run",
                        lambda project, argv, code=None, use_env=True:
                        seen.update(project=project, argv=argv, code=code) or 0)
    monkeypatch.setattr(sys, "argv", ["reality_run.py", "brief",
                                      "--project", str(tmp_path / "P"),
                                      "--code", str(tmp_path / "C")])
    assert rr.main() == 0
    assert seen["project"] == str(tmp_path / "P")
    assert seen["code"] == str(tmp_path / "C")
    assert seen["argv"][0] == str(tmp_path / "C" / "decision_brief.py")
