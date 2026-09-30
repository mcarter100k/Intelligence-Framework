"""
test_evidence_isolation.py — the test suite cannot touch real evidence or the
network (conftest.py; Phase 1 of the 2026-09-29 audit plan).

Three layers are each shown to hold:
  1. every test runs in its own tmp_path, and the absolute-path writers are
     redirected there too;
  2. unit tests cannot resolve a network host;
  3. the session guard FAILS a run that changes a real evidence file. That
     one is proven with a real pytest run in a throwaway project, because a
     guard that has never been seen to fire is not evidence that it works.
"""
import os
import shutil
import socket
import subprocess
import sys
import textwrap

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))


def test_relative_ledger_writes_land_in_tmp(tmp_path):
    import regime_classifier_logger as rcl
    import session_memory as sm
    import shadow_signals as ss
    import trade_outcome_logger as tol
    assert os.getcwd() == str(tmp_path)
    for rel in (ss.LOG_FILE, rcl.LOG_FILE, sm.LOG_FILE, tol._LOG_FILE):
        assert not os.path.isabs(rel), f"{rel} became absolute — isolate it"
        assert os.path.abspath(rel).startswith(str(tmp_path))


def test_absolute_path_writers_are_redirected(tmp_path):
    import calendar_fetch
    import setup_check
    import trade_logger
    for path in (setup_check.JOURNAL_FILE, trade_logger.TRADES_FILE,
                 calendar_fetch._CALENDAR_FILE):
        assert path.startswith(str(tmp_path)), path


def test_unit_tests_cannot_reach_the_network():
    with pytest.raises(RuntimeError, match="network"):
        socket.getaddrinfo("api-fxtrade.oanda.com", 443)
    socket.getaddrinfo("localhost", 80)              # local stays usable


_STUB_MODULES = {
    "setup_check.py":    'JOURNAL_FILE = "x"\n',
    "trade_logger.py":   'TRADES_FILE = "x"\n',
    "calendar_fetch.py": '_CALENDAR_FILE = "x"\n',
}


def _mini_project(tmp_path, test_body):
    proj = tmp_path / "proj"
    proj.mkdir()
    shutil.copy(os.path.join(_ROOT, "conftest.py"), proj / "conftest.py")
    shutil.copy(os.path.join(_ROOT, "pytest.ini"), proj / "pytest.ini")
    for name, body in _STUB_MODULES.items():
        (proj / name).write_text(body)
    (proj / "fake_ledger.csv").write_text("a,b\n1,2\n")
    (proj / "test_mini.py").write_text(textwrap.dedent(test_body))
    return proj


def _run_pytest(proj):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=proj, capture_output=True, text=True, timeout=120)


def test_session_guard_fails_a_run_that_writes_real_evidence(tmp_path):
    proj = _mini_project(tmp_path, f"""
        def test_contaminates():
            with open({str(tmp_path / 'proj' / 'fake_ledger.csv')!r}, "a") as f:
                f.write("3,4\\n")
    """)
    r = _run_pytest(proj)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    assert "TEST RUN CHANGED REAL EVIDENCE FILES: fake_ledger.csv" in out


def test_session_guard_passes_a_clean_run(tmp_path):
    proj = _mini_project(tmp_path, """
        def test_clean():
            with open("fake_ledger.csv", "a") as f:   # cwd is tmp_path
                f.write("3,4\\n")
    """)
    r = _run_pytest(proj)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (proj / "fake_ledger.csv").read_text() == "a,b\n1,2\n"
