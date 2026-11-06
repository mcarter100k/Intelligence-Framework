"""Research archive: one labelled, hash-pinned history of GBP_AUD and GBP_JPY
around the sealed exam (data_map_spec §11.6, team ruling 2026-11-05).

usage:
  python3 -I research_archive.py fetch-modern <modern_dir>
  python3 -I research_archive.py assemble <study_held_dir> <study_h1_dir> <modern_dir> <archive_dir>
  python3 -I research_archive.py verify <archive_dir>

  from research_archive import load
  bars = load(archive_dir, "GBP_JPY", "H1", spans={"STUDY", "USED"})

fetch-modern  OANDA D, H4 and H1 mid candles from the first USED session
              (2021-04-27) to the last complete session, for both pairs.
              Requests never start before the first USED candle, and any
              returned candle opening before it aborts the run before
              anything is written. Credentials come from the environment.
assemble      STUDY (held D/H4 and the session-study H1, converted by the
              approved weekend rule) + USED + FORWARD into <archive_dir>, one
              CSV per pair and granularity with a `span` column, and a
              manifest of sha256 values. Every source hash is checked first.
verify        re-checks the archive: hashes, span labels, no bar in the
              sealed block or an embargoed session, no weekend session,
              H1 -> H4 and H4 -> D1 consistency per span, and gaps.
load          returns bars for the spans named (required; no default).
              Refuses SEALED and unknown spans, and a file whose hash differs
              from the manifest.

Spans are assigned by session day (New York date of open + 7 h):
  STUDY    2005-01-01 -> 2013-12-30   learning
  USED     2021-04-27 -> 2026-09-09   learning only, never proof
  FORWARD  2026-09-11 -> build date   for description only: the live shadow
                                      ledger grades live claims, and an idea
                                      designed on these bars cannot be graded
                                      on them
  none     2005 and earlier, the embargo + SEALED EXAM (2013-12-31 -> 2021-04-26),
           and the 2026-09-10 boundary session (§11.6 rule 5)
If the exam is ever spent, its bars may join only with the label
SEEN_NOT_PROOF (§11.6 rule 4); that label is reserved here and unused.

Research only: never imported by the live path.
"""
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_convert as C  # noqa: E402  approved weekend rule
import history_study_gate_s3 as G  # noqa: E402  sealed block + OANDA client
import session_movement_data as D  # noqa: E402  aggregation, gaps, load

UTC = timezone.utc
PAIRS = ("GBP_AUD", "GBP_JPY")
GRANS = ("D", "H4", "H1")
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
SEALED_START, SEALED_END = G.BLOCK_START, G.BLOCK_END   # embargo + exam, candle opens
STUDY_FIRST, STUDY_LAST = date(2005, 1, 1), date(2013, 12, 30)
USED_FIRST, USED_LAST = date(2021, 4, 27), date(2026, 9, 9)
FORWARD_FIRST = date(2026, 9, 11)
BOUNDARY_EMBARGO = {date(2026, 9, 10)}
SPANS = {
    "STUDY": "learning (old convention, converted)",
    "USED": "learning only, never proof",
    "FORWARD": "description only; never a test for an idea designed on it",
}
RESERVED_LABELS = {"SEEN_NOT_PROOF"}
# A request starting one minute inside the first USED candle: OANDA returns the
# candle containing `from`, which for D, H4 and H1 opens at 2021-04-26 21:00Z.
MODERN_FROM = SEALED_END + timedelta(minutes=1)
D1_TOL_PIPS = 0.5


class Refused(RuntimeError):
    pass


# ── pure helpers (pinned by tests/test_research_archive.py) ──────────────────

def span_of(session):
    if session in BOUNDARY_EMBARGO:
        return None
    if STUDY_FIRST <= session <= STUDY_LAST:
        return "STUDY"
    if USED_FIRST <= session <= USED_LAST:
        return "USED"
    if session >= FORWARD_FIRST:
        return "FORWARD"
    return None


def in_sealed_block(t):
    return SEALED_START <= t < SEALED_END


def guard_modern_request(frm):
    if frm < MODERN_FROM:
        raise Refused(f"refused: request from {frm.isoformat()} starts before the first USED candle")


def check_modern_received(times):
    early = [t for t in times if t < SEALED_END]
    if early:
        raise Refused(f"aborting: received {len(early)} candle(s) opening before the first USED "
                      f"candle, earliest {min(early).isoformat()}; nothing written")


def label(bars):
    """{t: ohlc} -> ({t: ohlc}, {t: span}, dropped Counter) keeping labelled bars only."""
    kept, spans, dropped = {}, {}, Counter()
    for t, v in bars.items():
        sd = C.session_day(t)
        s = span_of(sd)
        if s is None:
            dropped["boundary_embargo" if sd in BOUNDARY_EMBARGO else "outside_spans"] += 1
            continue
        kept[t], spans[t] = v, s
    return kept, spans, dropped


def d1_consistency(d1, h4, pip):
    """Per D1 bar with H4 bars in its session: (open, high, low, close) |diff| pips."""
    by = defaultdict(list)
    for t in sorted(h4):
        by[C.session_day(t)].append(t)
    out = {}
    for t, v in d1.items():
        ts = by.get(C.session_day(t))
        if not ts:
            continue
        agg = (h4[ts[0]][0], max(h4[x][1] for x in ts), min(h4[x][2] for x in ts), h4[ts[-1]][3])
        out[t] = tuple(round(abs(v[i] - agg[i]) / pip, 6) for i in range(4))
    return out


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _outside_repo(path):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.abspath(path).startswith(repo + os.sep):
        raise Refused("refused: archive and data directories must be outside the repo")


def _write(path, bars, spans):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_utc", "o", "h", "l", "c", "span"])
        for t in sorted(bars):
            w.writerow([t.isoformat(), *bars[t], spans[t]])


def _read(path):
    bars, spans = {}, {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            t = datetime.fromisoformat(r["time_utc"])
            bars[t] = (float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]))
            spans[t] = r["span"]
    return bars, spans


# ── loader ───────────────────────────────────────────────────────────────────

def load(archive_dir, pair, gran, spans):
    """Bars of `pair`/`gran` in the named spans. `spans` is required."""
    spans = set(spans or ())
    if not spans:
        raise Refused("name the spans to read: there is no default")
    bad = spans - set(SPANS)
    if bad:
        raise Refused(f"refused spans {sorted(bad)}: only {sorted(SPANS)} exist in the archive")
    with open(os.path.join(archive_dir, "manifest.json")) as fh:
        man = json.load(fh)
    name = f"{pair}_{gran}.csv"
    path = os.path.join(archive_dir, name)
    if sha(path) != man["files"][name]["sha256"]:
        raise Refused(f"{name}: hash differs from the manifest")
    bars, lab = _read(path)
    sealed = [t for t in bars if in_sealed_block(t)]
    if sealed:
        raise Refused(f"{name}: {len(sealed)} bar(s) inside the sealed block")
    return {t: v for t, v in bars.items() if lab[t] in spans}


# ── fetch ────────────────────────────────────────────────────────────────────

def fetch_modern(cl, pair, gran, now):
    rows, lo = {}, MODERN_FROM
    while lo < now:
        hi = min(lo + timedelta(days=31), now)
        guard_modern_request(lo)
        st, p = cl.candles(pair, {"granularity": gran, "price": "M",
                                  "from": G.P.iso(lo), "to": G.P.iso(hi)})
        if st != 200:
            raise RuntimeError(f"{pair} {gran}: HTTP {st} {p}")
        got = [(G.P.parse(c["time"]), c) for c in p.get("candles", [])]
        check_modern_received([t for t, _ in got])
        for t, c in got:
            if c.get("complete", True):
                m = c["mid"]
                rows[t] = tuple(float(m[k]) for k in "ohlc")
        lo = hi
    return rows


def cmd_fetch_modern(modern_dir):
    _outside_repo(modern_dir)
    os.makedirs(modern_dir, exist_ok=True)
    cl = G.P.Client(dict(os.environ))
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    hashes = {}
    for pair in PAIRS:
        for gran in GRANS:
            rows = fetch_modern(cl, pair, gran, now)
            p = os.path.join(modern_dir, f"{pair}_{gran}.csv")
            G.save(p, rows)
            hashes[os.path.basename(p)] = sha(p)
            wk = Counter(C.session_day(t).weekday() for t in rows)
            print(f"{pair} {gran}: complete candles {len(rows)}; first open {D.pt(min(rows))}; "
                  f"last open {D.pt(max(rows))}; weekend-session candles {wk[5] + wk[6]}; "
                  f"opening before the first USED candle 0 (checked on receipt)")
    with open(os.path.join(modern_dir, "data_hashes.json"), "w") as fh:
        json.dump({"fetched_utc": now.isoformat(), "files": hashes}, fh, indent=1)
    print("data hashes:", json.dumps(hashes))
    print("requests:", cl.requests)


# ── assemble ─────────────────────────────────────────────────────────────────

def _check_hashes(folder, table):
    for name, want in table.items():
        if not isinstance(want, str):
            continue
        got = sha(os.path.join(folder, name))
        if got != want:
            raise Refused(f"source hash mismatch: {folder}/{name}")


def cmd_assemble(study_held_dir, study_h1_dir, modern_dir, archive_dir):
    for p in (archive_dir,):
        _outside_repo(p)
    with open(os.path.join(study_held_dir, "data_hashes.json")) as fh:
        held_h = json.load(fh)
    with open(os.path.join(study_h1_dir, "data_hashes.json")) as fh:
        h1_h = json.load(fh)
    with open(os.path.join(modern_dir, "data_hashes.json")) as fh:
        mod = json.load(fh)
    _check_hashes(study_held_dir, {k: v for k, v in held_h.items() if k.endswith(("_H4.csv", "_D.csv"))})
    _check_hashes(study_h1_dir, h1_h)
    _check_hashes(modern_dir, mod["files"])
    os.makedirs(archive_dir, exist_ok=True)

    manifest = {"built_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "builder_sha256": sha(os.path.abspath(__file__)),
                "rules": "data_map_spec §11.2, §11.6; study_weekend_candle_spec §6",
                "spans": {"STUDY": [str(STUDY_FIRST), str(STUDY_LAST)],
                          "USED": [str(USED_FIRST), str(USED_LAST)],
                          "FORWARD": [str(FORWARD_FIRST), None]},
                "no_span": ["<= 2004", "2013-12-31 -> 2021-04-26 (embargo + SEALED EXAM)",
                            *[str(d) for d in sorted(BOUNDARY_EMBARGO)]],
                "reserved_labels": sorted(RESERVED_LABELS),
                "sources": {"study_held": {k: v for k, v in held_h.items() if isinstance(v, str)},
                            "study_h1": h1_h, "modern": mod},
                "files": {}}
    for pair in PAIRS:
        raw_d1 = D.load(os.path.join(study_held_dir, f"{pair}_D.csv"))
        raw_h4 = D.load(os.path.join(study_held_dir, f"{pair}_H4.csv"))
        raw_h1 = D.load(os.path.join(study_h1_dir, f"{pair}_H1.csv"))
        d1c, h4c, _ = C.convert(raw_d1, raw_h4)
        _, h1c, _ = C.convert(raw_d1, raw_h1)
        study = {"D": d1c, "H4": h4c, "H1": h1c}
        for gran in GRANS:
            modern = D.load(os.path.join(modern_dir, f"{pair}_{gran}.csv"))
            wk = sum(1 for t in modern if C.session_day(t).weekday() >= 5)
            if wk:
                raise Refused(f"{pair} {gran}: {wk} weekend-session candles in modern data; "
                              "no approved rule covers them")
            check_modern_received(list(modern))
            merged = dict(study[gran])
            overlap = set(merged) & set(modern)
            if overlap:
                raise Refused(f"{pair} {gran}: STUDY and modern bars overlap ({len(overlap)})")
            merged.update(modern)
            bars, spans, dropped = label(merged)
            if any(in_sealed_block(t) for t in bars):
                raise Refused(f"{pair} {gran}: a labelled bar lies in the sealed block")
            name = f"{pair}_{gran}.csv"
            path = os.path.join(archive_dir, name)
            _write(path, bars, spans)
            per = {}
            for s in SPANS:
                ts = sorted(t for t in bars if spans[t] == s)
                per[s] = {"rows": len(ts), "first_open_utc": ts[0].isoformat() if ts else None,
                          "last_open_utc": ts[-1].isoformat() if ts else None}
            manifest["files"][name] = {"sha256": sha(path), "rows": len(bars), "per_span": per,
                                       "dropped_unlabelled": dict(dropped)}
            print(f"{name}: rows {len(bars)}; " + "; ".join(
                f"{s} {per[s]['rows']}" for s in SPANS) + f"; dropped {dict(dropped)}")
    # FORWARD trimmed to the last session with a complete D1 bar in both pairs
    last = min(max(C.session_day(t) for t in _read(os.path.join(archive_dir, f"{p}_D.csv"))[0])
               for p in PAIRS)
    for pair in PAIRS:
        for gran in GRANS:
            name = f"{pair}_{gran}.csv"
            path = os.path.join(archive_dir, name)
            bars, spans = _read(path)
            late = [t for t in bars if C.session_day(t) > last]
            if late:
                for t in late:
                    del bars[t], spans[t]
                _write(path, bars, spans)
                f = manifest["files"][name]
                f["sha256"], f["rows"] = sha(path), len(bars)
                fts = sorted(t for t in bars if spans[t] == "FORWARD")
                f["per_span"]["FORWARD"] = {"rows": len(fts), "first_open_utc": fts[0].isoformat(),
                                            "last_open_utc": fts[-1].isoformat()}
                f["dropped_unlabelled"]["after_last_complete_session"] = len(late)
                print(f"{name}: trimmed {len(late)} bar(s) after the last complete session {last}")
    manifest["spans"]["FORWARD"][1] = str(last)
    with open(os.path.join(archive_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"FORWARD last session {last}; manifest written")


# ── verify ───────────────────────────────────────────────────────────────────

def cmd_verify(archive_dir, pairs=PAIRS, pip_map=PIP):
    with open(os.path.join(archive_dir, "manifest.json")) as fh:
        man = json.load(fh)
    ok = True

    def fail(msg):
        nonlocal ok
        ok = False
        print("  FAIL", msg)

    data = {}
    for name, meta in sorted(man["files"].items()):
        path = os.path.join(archive_dir, name)
        if sha(path) != meta["sha256"]:
            fail(f"{name}: hash differs from manifest")
            continue
        bars, spans = _read(path)
        data[name] = (bars, spans)
        mis = sum(1 for t in bars if spans[t] != span_of(C.session_day(t)))
        sealed = sum(1 for t in bars if in_sealed_block(t))
        emb = sum(1 for t in bars if C.session_day(t) in BOUNDARY_EMBARGO)
        wk = sum(1 for t in bars if C.session_day(t).weekday() >= 5)
        rsv = sum(1 for t in bars if spans[t] in RESERVED_LABELS)
        print(f"{name}: hash OK; rows {len(bars)} (manifest {meta['rows']}); span label mismatches {mis}; "
              f"in sealed block {sealed}; in boundary embargo {emb}; weekend-session {wk}; reserved labels {rsv}")
        if len(bars) != meta["rows"] or mis or sealed or emb or wk or rsv:
            fail(f"{name}: integrity check")

    for pair in pairs:
        if not all(f"{pair}_{g}.csv" in data for g in GRANS):
            fail(f"{pair}: a timeframe is missing or failed its hash check")
            continue
        pip = pip_map[pair]
        (d1, sd1), (h4, sh4), (h1, sh1) = (data[f"{pair}_{g}.csv"] for g in GRANS)
        print(f"\n## {pair}")
        for s in SPANS:
            h1s = {t: v for t, v in h1.items() if sh1[t] == s}
            h4s = {t: v for t, v in h4.items() if sh4[t] == s}
            d1s = {t: v for t, v in d1.items() if sd1[t] == s}
            agg = D.aggregate(h1s)
            cmp_ = D.compare(agg, h4s, pip)
            exact = sum(1 for d in cmp_.values() if max(d) == 0)
            only_a, only_h = len(set(agg) - set(h4s)), len(set(h4s) - set(agg))
            dc = d1_consistency(d1s, h4s, pip)
            hl_ok = sum(1 for d in dc.values() if d[1] <= D1_TOL_PIPS and d[2] <= D1_TOL_PIPS)
            oc_ok = sum(1 for d in dc.values() if d[0] == 0 and d[3] == 0)
            gl = D.gaps(list(h1s), min(h1s).replace(minute=0), max(h1s) + timedelta(hours=1)) if h1s else []
            long_ = [(t, n) for t, n in gl if n >= 3]
            print(f"{s}: H1->H4 compared {len(cmp_)}, exact {exact}, H1-only buckets {only_a}, "
                  f"H4 with no H1 {only_h} | D1 vs its H4: {len(dc)} sessions, high/low within "
                  f"{D1_TOL_PIPS} pip {hl_ok}, open+close exact {oc_ok}, D1 with no H4 "
                  f"{len(d1s) - len(dc)} | H1 gap runs {len(gl)} ({sum(n for _, n in gl)} h), "
                  f"runs of 3 h or more {len(long_)}")
            nz = sorted(x for d in cmp_.values() for x in d if x > 0)
            nzd = sorted(x for d in dc.values() for x in d if x > 0)
            if nz or nzd:
                print(f"    nonzero |diff| pips: H1->H4 {len(nz)} values, max {max(nz) if nz else 0:.3f}; "
                      f"D1 vs H4 {len(nzd)} values, max {max(nzd) if nzd else 0:.3f}")
            for t, n in long_:
                if s != "STUDY":
                    print(f"    gap {D.pt(t)} -> {D.pt(t + timedelta(hours=n))}  {n} h")
            if exact != len(cmp_) or only_a or only_h or hl_ok != len(dc):
                fail(f"{pair} {s}: consistency")
    print("\nVERIFY:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["fetch-modern"] and len(a) == 2:
        cmd_fetch_modern(a[1])
    elif a[:1] == ["assemble"] and len(a) == 5:
        cmd_assemble(*a[1:])
    elif a[:1] == ["verify"] and len(a) == 2:
        sys.exit(0 if cmd_verify(a[1]) else 1)
    else:
        raise SystemExit(__doc__)
