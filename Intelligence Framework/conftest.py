"""
conftest.py — pytest bootstrap for the Intelligence Framework.

1. Makes the repo root importable regardless of the directory pytest is
   invoked from, so `import regime_detection` etc. resolve without install.

2. EVIDENCE ISOLATION (Phase 1 of the 2026-09-29 audit plan). The ledgers are
   append-only evidence, and a contaminated row can never be removed (AGENTS.md
   rule 10). Isolation used to be per-test and by hand, and the opt-in
   integration tests wrote synthetic rows (including a grade-A LONG) into the
   real ledgers. Now:
   * every test runs with its working directory set to its own tmp_path, so
     the loggers' relative ledger paths land there, never in the project;
   * the absolute-path writers (pre-trade journal, trades.csv, calendar) are
     redirected into tmp_path as well;
   * the session HASHES every real evidence file before and after the run and
     FAILS the run if any changed. That backstop catches a write by any path,
     including modules loaded per-file that no fixture can patch.

3. NO NETWORK in unit tests. Only tests marked `integration` may reach the
   network. A unit test that needs data must mock it. Before this, the
   default suite made authenticated calls to live OANDA whenever the key was
   exported in the shell.
"""
import hashlib
import os
import socket
import sys

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)


# ── 2. evidence isolation ────────────────────────────────────────────────────

# Written by absolute path (not relative to the working directory), so
# chdir alone does not protect them. (module, attribute, filename)
_ABSOLUTE_WRITERS = [
    ("setup_check",    "JOURNAL_FILE",   "pre_trade_journal.csv"),
    ("trade_logger",   "TRADES_FILE",    "trades.csv"),
    ("calendar_fetch", "_CALENDAR_FILE", "calendar.csv"),
]


# Read by absolute path, so the REAL file would leak into every test that
# runs the live path. news_gate reads calendar.csv: a real HIGH-impact event
# within 2 hours changed apply_filter's answer and made tests fail by
# wall-clock (data_at_source review V4, reproduced with a planted event).
# Tests that need a calendar pass their own path or set this attribute.
_ABSOLUTE_READERS = [
    ("news_gate", "_CALENDAR_FILE", "calendar.csv"),
]


@pytest.fixture(autouse=True)
def _isolate_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for module, attr, name in _ABSOLUTE_WRITERS + _ABSOLUTE_READERS:
        mod = __import__(module)
        monkeypatch.setattr(mod, attr, str(tmp_path / name))


# Everything except regenerable caches and the environment. The first version
# watched only root-level .csv/.json plus logs/health_state.json. The
# 2026-09-29 validation proved it missed a test appending to logs/ and a
# test creating a new file at the root, so it now watches the whole tree.
_UNWATCHED_DIRS = {"venv", "__pycache__", ".pytest_cache", ".git"}


def _evidence_files():
    """Every file in the project a test must never create, change or delete."""
    files = []
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _UNWATCHED_DIRS]
        files.extend(os.path.join(dirpath, f) for f in filenames)
    return sorted(files)


def _digest():
    out = {}
    for f in _evidence_files():
        with open(f, "rb") as fh:
            out[f] = hashlib.sha256(fh.read()).hexdigest()
    return out


def pytest_sessionstart(session):
    session.config._evidence_before = _digest()


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_evidence_before", None)
    if before is None:
        return
    after = _digest()
    changed = sorted(f for f in set(before) | set(after)
                     if before.get(f) != after.get(f))
    if changed:
        names = ", ".join(os.path.relpath(f, _ROOT) for f in changed)
        sys.stderr.write(
            "\n\n##ALERT## TEST RUN CHANGED REAL EVIDENCE FILES: " + names +
            "\nA test wrote to a real ledger. Find it before anything else: "
            "a contaminated append-only row can never be removed (AGENTS.md "
            "rule 10). (If a scheduled launchd job ran during this test "
            "session, it may be the writer: check its log, then re-run.)\n")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


# ── 3. no network in unit tests ──────────────────────────────────────────────

# Installed for the WHOLE session, not per test: module- and session-scoped
# fixtures run before any function-scoped fixture, and the first version of
# this block missed exactly that case (test_regime_detection_p1's
# module-scoped `mocked_regime` still reached OANDA). Only an `integration`
# test lifts it, for its own duration.
_LOCAL = {"localhost", "127.0.0.1", "::1", None}
_real_getaddrinfo = socket.getaddrinfo
_net = {"allowed": False}


def _guarded_getaddrinfo(host, *a, **k):
    if _net["allowed"] or host in _LOCAL:
        return _real_getaddrinfo(host, *a, **k)
    raise RuntimeError(
        f"unit test tried to reach the network ({host}). Mock the data, "
        f"or mark the test @pytest.mark.integration.")


def pytest_configure(config):
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_unconfigure(config):
    socket.getaddrinfo = _real_getaddrinfo


@pytest.fixture(autouse=True)
def _network_only_for_integration(request):
    _net["allowed"] = bool(request.node.get_closest_marker("integration"))
    yield
    _net["allowed"] = False
