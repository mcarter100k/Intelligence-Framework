"""Currency legs and gold for the research archive (currency-leg study, Phase 1).

usage:
  python3 -I leg_data.py fetch <raw_dir>
  python3 -I leg_data.py assemble <raw_dir> <cross_archive_dir> <leg_archive_dir>
  python3 -I leg_data.py verify <leg_archive_dir>

fetch     GBP_USD, AUD_USD, USD_JPY (legs) and XAU_USD (secondary) at D, H4
          and H1, mid prices, through the two guarded fetches the cross archive
          used: the STUDY fetch (history_study_gate_s3.fetch: the sealed block
          is refused before sending and on receipt) and the modern fetch
          (research_archive.fetch_modern: nothing before the first USED candle).
          Writes <raw_dir>/{study,modern}/<inst>_<gran>.csv and hashes.
assemble  STUDY converted by the approved weekend rule, both parts labelled by
          span exactly as the cross archive is (research_archive.label), FORWARD
          trimmed to the cross archive's last session so all six instruments
          cover the same sessions. Writes CSVs (with `span`) and a manifest.
verify    research_archive.cmd_verify on these instruments: hashes, labels,
          sealed block, embargo, weekend sessions, H1 -> H4 and H4 -> D1.

No price statistic is computed here. Research only; never imported by the
live path. Read it with research_archive.load(<leg_archive_dir>, inst, gran, spans).
"""
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_convert as C  # noqa: E402
import history_study_gate_s3 as G  # noqa: E402
import research_archive as A  # noqa: E402
import session_movement_data as D  # noqa: E402

UTC = timezone.utc
LEGS = ("GBP_USD", "AUD_USD", "USD_JPY")
SECONDARY = ("XAU_USD",)
INSTRUMENTS = LEGS + SECONDARY
PIP = {"GBP_USD": 0.0001, "AUD_USD": 0.0001, "USD_JPY": 0.01, "XAU_USD": 0.01}
GRANS = A.GRANS


def cmd_fetch(raw_dir):
    A._outside_repo(raw_dir)
    cl = G.P.Client(dict(os.environ))
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    out = {}
    for part in ("study", "modern"):
        os.makedirs(os.path.join(raw_dir, part), exist_ok=True)
        out[part] = {}
        for inst in INSTRUMENTS:
            for gran in GRANS:
                rows = G.fetch(cl, inst, gran) if part == "study" else A.fetch_modern(cl, inst, gran, now)
                p = os.path.join(raw_dir, part, f"{inst}_{gran}.csv")
                G.save(p, rows)
                out[part][f"{inst}_{gran}.csv"] = A.sha(p)
                sealed = sum(1 for t in rows if A.in_sealed_block(t))
                wk = Counter(C.session_day(t).weekday() for t in rows)
                print(f"{part} {inst} {gran}: candles {len(rows)}"
                      + (f"; first {D.pt(min(rows))}; last {D.pt(max(rows))}" if rows else "")
                      + f"; in sealed block {sealed}; Saturday-session {wk[5]}; Sunday-session {wk[6]}")
    with open(os.path.join(raw_dir, "data_hashes.json"), "w") as fh:
        json.dump({"fetched_utc": now.isoformat(), **out}, fh, indent=1)
    print("requests:", cl.requests)


def assemble_instrument(study, modern, last_session):
    """study/modern: {gran: {t: ohlc}} -> {gran: (bars, spans, dropped)}."""
    d1c, h4c, _ = C.convert(study["D"], study["H4"])
    _, h1c, _ = C.convert(study["D"], study["H1"])
    conv = {"D": d1c, "H4": h4c, "H1": h1c}
    out = {}
    for gran in GRANS:
        wk = sum(1 for t in modern[gran] if C.session_day(t).weekday() >= 5)
        if wk:
            raise A.Refused(f"{gran}: {wk} weekend-session candles in modern data; no approved rule covers them")
        A.check_modern_received(list(modern[gran]))
        if set(conv[gran]) & set(modern[gran]):
            raise A.Refused(f"{gran}: STUDY and modern bars overlap")
        merged = {**conv[gran], **modern[gran]}
        late = [t for t in merged if C.session_day(t) > last_session]
        for t in late:
            del merged[t]
        bars, spans, dropped = A.label(merged)
        if late:
            dropped["after_last_cross_session"] = len(late)
        if any(A.in_sealed_block(t) for t in bars):
            raise A.Refused(f"{gran}: a labelled bar lies in the sealed block")
        out[gran] = (bars, spans, dropped)
    return out


def cmd_assemble(raw_dir, cross_archive_dir, out_dir):
    A._outside_repo(out_dir)
    with open(os.path.join(raw_dir, "data_hashes.json")) as fh:
        hashes = json.load(fh)
    for part in ("study", "modern"):
        A._check_hashes(os.path.join(raw_dir, part), hashes[part])
    with open(os.path.join(cross_archive_dir, "manifest.json")) as fh:
        cross = json.load(fh)
    last = date.fromisoformat(cross["spans"]["FORWARD"][1])
    os.makedirs(out_dir, exist_ok=True)
    man = {"built_utc": datetime.now(UTC).isoformat(timespec="seconds"),
           "builder_sha256": A.sha(os.path.abspath(__file__)),
           "rules": "data_map_spec §11.2, §11.6; study_weekend_candle_spec §6; spans as the cross archive",
           "spans": {**cross["spans"], "FORWARD": [cross["spans"]["FORWARD"][0], str(last)]},
           "aligned_to_cross_manifest_sha256": A.sha(os.path.join(cross_archive_dir, "manifest.json")),
           "sources": hashes, "files": {}}
    for inst in INSTRUMENTS:
        study = {g: D.load(os.path.join(raw_dir, "study", f"{inst}_{g}.csv")) for g in GRANS}
        modern = {g: D.load(os.path.join(raw_dir, "modern", f"{inst}_{g}.csv")) for g in GRANS}
        for gran, (bars, spans, dropped) in assemble_instrument(study, modern, last).items():
            name = f"{inst}_{gran}.csv"
            path = os.path.join(out_dir, name)
            A._write(path, bars, spans)
            per = {}
            for s in A.SPANS:
                ts = sorted(t for t in bars if spans[t] == s)
                per[s] = {"rows": len(ts), "first_open_utc": ts[0].isoformat() if ts else None,
                          "last_open_utc": ts[-1].isoformat() if ts else None}
            man["files"][name] = {"sha256": A.sha(path), "rows": len(bars), "per_span": per,
                                  "dropped_unlabelled": dict(dropped)}
            print(f"{name}: rows {len(bars)}; " + "; ".join(f"{s} {per[s]['rows']}" for s in A.SPANS)
                  + f"; dropped {dict(dropped)}")
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1)
    print(f"FORWARD aligned to the cross archive's last session {last}; manifest written")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["fetch"] and len(a) == 2:
        cmd_fetch(a[1])
    elif a[:1] == ["assemble"] and len(a) == 4:
        cmd_assemble(*a[1:])
    elif a[:1] == ["verify"] and len(a) == 2:
        sys.exit(0 if A.cmd_verify(a[1], pairs=INSTRUMENTS, pip_map=PIP) else 1)
    else:
        raise SystemExit(__doc__)
