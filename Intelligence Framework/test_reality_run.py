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


# ── a failure is detected; a document discussing one is not (2026-10-17) ─────
# The decision-channel inventory quoted the outage's error text in its report
# and the old substring match exited 3 on a run that fetched and wrote fine.

def test_a_report_quoting_the_error_text_is_not_a_failure(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        print("| RUN ERRORED | 08-01 -> 09-09 | Framework error — do not trade: "
              "OANDA not configured — set OANDA_API_KEY ×117 | 118 run(s) |")
        print("The brief printed REASON Framework error — do not trade: on 118 runs.")
        print("The grader logged GRADER EARLY EXIT — OANDA not configured; and a")
        print("crash shows Traceback (most recent call last): at the top.")
    """)
    rc = rr.reality_run(str(proj), [target], python=sys.executable)
    assert rc == 0, capsys.readouterr().out


def test_a_grader_early_exit_is_a_failure(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        print("GRADER EARLY EXIT — OANDA not configured (set OANDA_API_KEY and "
              "OANDA_ACCOUNT_ID) — nothing graded this run")
    """)
    assert rr.reality_run(str(proj), [target], python=sys.executable) == 3


def test_a_caught_traceback_on_stderr_is_a_failure_even_with_exit_0(tmp_path, capsys):
    proj = _project(tmp_path)
    target = _script(tmp_path, """
        import traceback
        try:
            1 / 0
        except ZeroDivisionError:
            traceback.print_exc()
    """)
    assert rr.reality_run(str(proj), [target], python=sys.executable) == 3


def test_the_real_brief_error_page_is_a_failure(tmp_path, capsys):
    """Rendered by the real producer, not hand-typed."""
    import decision_brief as db
    page = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=0.0, atr_pips=0.0,
        decision="STAND DOWN", reason="Framework error — do not trade: OANDA not "
        "configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID", conviction=0, grade="C",
        size_pct=0, market_state="Unavailable", invalidation="i", regime_log="l",
        stand_down=True, override_fired=False, execution_mode="X", adx_d1=0.0,
        adx_h4=0.0, weekly_context="W", error="OANDA not configured").format()
    src = tmp_path / "page.txt"
    src.write_text(page, encoding="utf-8")
    proj = _project(tmp_path)
    target = _script(tmp_path, f"""
        import sys
        sys.stdout.write(open({str(src)!r}, encoding="utf-8").read())
    """)
    assert rr.reality_run(str(proj), [target], python=sys.executable) == 3


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
