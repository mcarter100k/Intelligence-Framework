# Currency legs and gold — Phase 1 data report (2026-11-05)

Phase 1 of the currency-leg decomposition study. **Data and verification
numbers only; no statistic of the study has been computed.**

- **Code:** `studies/leg_data.py` (fetch, assemble, verify) and
  `studies/metals_availability_probe.py`.
- **Data:** outside the repo.
  - Raw: `~/intel_study_archives/leg_data/`.
  - Assembled, span-labelled and hash-pinned:
    `~/intel_study_archives/research_archive_legs/`.
- **Partition:**
  - Same spans as the cross archive: STUDY 2005–2013, USED 2021-04-27 →
    2026-09-09, FORWARD 2026-09-11 → 2026-11-05.
  - The 2026-09-10 boundary session is embargoed.
  - **0 candles in the sealed block** were fetched or stored.

## Gold: is it available? (`metals_availability_probe.py`, read-only, via `reality_run.py`: exit 0, stderr empty, project unchanged)

- **The account's instruments endpoint** lists 68 instruments, all type
  CURRENCY. There are no METAL-type, XAU or XAG names, so **gold is not
  tradeable on this account.**
- **The candles endpoint serves gold anyway.** XAU_USD, XAG_USD and XAU_GBP
  each returned HTTP 200 with a candle dated 2026-11-05. **Price history is
  available from OANDA even though the instrument is not tradeable here.**
- **Correction to `instrument_probe_report.md` (2026-11-01):**
  - Its "NOT OFFERED" came from the account's tradeable list only. It never
    asked the candles endpoint.
  - Its conclusion that yields, equities and commodities "must come from
    free outside sources … never from OANDA" is therefore **not
    established**.
  - Recorded here; not re-probed in this task.
- **Gold's history starts 2006-03-19**, so it covers only part of STUDY
  (2,025 of 2,343 sessions).

## Validation (`leg_data.py verify`, via `reality_run.py --no-env`: exit 0 on fetch and assemble, verify exit 1 because of gold; stderr empty; project unchanged)

| Instrument | Span | H1 → H4 compared / exact | D1 vs H4: sessions / high-low within 0.5 pip / open-close exact | Gaps |
|---|---|---|---|---|
| GBP_USD | STUDY | 14,028 / 14,028 | 2,343 / 2,343 / 2,343 | holidays |
| GBP_USD | USED | 8,370 / 8,370 | 1,395 / 1,395 / 1,395 | 7 Christmas–New Year closures |
| GBP_USD | FORWARD | 240 / 240 | 40 / 40 / 40 | none |
| AUD_USD | STUDY | 14,027 / 14,027 | 2,343 / 2,343 / 2,343 | holidays |
| AUD_USD | USED | 8,370 / 8,370 | 1,395 / 1,395 / 1,395 | same 7 |
| AUD_USD | FORWARD | 240 / 240 | 40 / 40 / 40 | none |
| USD_JPY | STUDY | 14,025 / 14,025 | 2,343 / 2,343 / 2,343 | holidays |
| USD_JPY | USED | 8,370 / 8,370 | 1,395 / 1,395 / 1,395 | same 7 |
| USD_JPY | FORWARD | 240 / 240 | 40 / 40 / 40 | none |
| **XAU_USD** | **STUDY** | **12,111 / 12,110 (one $0.05 open mismatch)** | 2,025 / 2,025 / 2,025 | the daily one-hour break and US holiday closes |
| XAU_USD | USED | 8,321 / 8,321 | 1,388 / 1,388 / 1,388 | the same |
| XAU_USD | FORWARD | 240 / 240 | 40 / 40 / 40 | the daily break |

- **The three USD legs: PASS in every span.** There are zero nonzero
  differences anywhere, so there is no distribution to report.
- **Gold: FAIL**, on one bar.
  - The bar is the 4-hour bucket opening 2006-03-19 14:00 PST (session
    2006-03-20), gold's first session in OANDA's history.
  - **Raw** gold is consistent: 12,873 of 12,873 raw 4-hour bars rebuild
    exactly from raw hourly bars. There is one orphan hourly bucket
    (2006-03-19 18:00 UTC, the first hours ever served) with no 4-hour bar.
  - **The approved weekend rule** folds that Sunday-session hourly bar into
    Monday's first hourly bar, changing its open from 554.05 to 554.00.
    There is no Sunday-session 4-hour bar to fold the same way.
  - **So the failure is created by conversion at the start of history, not
    by the feed.** Whether to start gold at the 2006-03-21 session or leave
    it out is for the team. It is not trimmed here.
- **Regression:** the cross archive still verifies PASS with the extended
  verifier.
- **Limit, carried:** these checks show the timeframes agree with each
  other, not that individual values are correct. No second source exists.

## Full output (verbatim)

### fetch
```
study GBP_USD D: candles 2992; first 2005-01-01 14:00 PST; last 2013-12-29 14:00 PST; in sealed block 0; Saturday-session 231; Sunday-session 418
study GBP_USD H4: candles 15172; first 2005-01-02 10:00 PST; last 2013-12-30 10:00 PST; in sealed block 0; Saturday-session 435; Sunday-session 709
study GBP_USD H1: candles 58519; first 2005-01-02 11:00 PST; last 2013-12-30 13:00 PST; in sealed block 0; Saturday-session 674; Sunday-session 1777
study AUD_USD D: candles 2960; first 2005-01-01 14:00 PST; last 2013-12-29 14:00 PST; in sealed block 0; Saturday-session 198; Sunday-session 419
study AUD_USD H4: candles 15172; first 2005-01-02 10:00 PST; last 2013-12-30 10:00 PST; in sealed block 0; Saturday-session 402; Sunday-session 743
study AUD_USD H1: candles 58564; first 2005-01-02 10:00 PST; last 2013-12-30 13:00 PST; in sealed block 0; Saturday-session 648; Sunday-session 1846
study USD_JPY D: candles 2999; first 2005-01-01 14:00 PST; last 2013-12-29 14:00 PST; in sealed block 0; Saturday-session 235; Sunday-session 421
study USD_JPY H4: candles 15202; first 2005-01-02 10:00 PST; last 2013-12-30 10:00 PST; in sealed block 0; Saturday-session 442; Sunday-session 735
study USD_JPY H1: candles 58616; first 2005-01-02 10:00 PST; last 2013-12-30 13:00 PST; in sealed block 0; Saturday-session 693; Sunday-session 1857
study XAU_USD D: candles 2366; first 2006-03-19 14:00 PST; last 2013-12-29 14:00 PST; in sealed block 0; Saturday-session 137; Sunday-session 204
study XAU_USD H4: candles 12873; first 2006-03-19 14:00 PST; last 2013-12-30 10:00 PST; in sealed block 0; Saturday-session 328; Sunday-session 434
study XAU_USD H1: candles 49322; first 2006-03-19 12:00 PST; last 2013-12-30 13:00 PST; in sealed block 0; Saturday-session 562; Sunday-session 771
modern GBP_USD D: candles 1436; first 2021-04-26 14:00 PDT; last 2026-11-04 14:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern GBP_USD H4: candles 8618; first 2021-04-26 14:00 PDT; last 2026-11-05 18:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern GBP_USD H1: candles 34470; first 2021-04-26 14:00 PDT; last 2026-11-05 22:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern AUD_USD D: candles 1436; first 2021-04-26 14:00 PDT; last 2026-11-04 14:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern AUD_USD H4: candles 8618; first 2021-04-26 14:00 PDT; last 2026-11-05 18:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern AUD_USD H1: candles 34470; first 2021-04-26 14:00 PDT; last 2026-11-05 22:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern USD_JPY D: candles 1436; first 2021-04-26 14:00 PDT; last 2026-11-04 14:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern USD_JPY H4: candles 8618; first 2021-04-26 14:00 PDT; last 2026-11-05 18:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern USD_JPY H1: candles 34470; first 2021-04-26 14:00 PDT; last 2026-11-05 22:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern XAU_USD D: candles 1429; first 2021-04-26 14:00 PDT; last 2026-11-04 14:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern XAU_USD H4: candles 8569; first 2021-04-26 14:00 PDT; last 2026-11-05 18:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
modern XAU_USD H1: candles 32767; first 2021-04-26 15:00 PDT; last 2026-11-05 22:00 PST; in sealed block 0; Saturday-session 0; Sunday-session 0
requests: 2064
```

### assemble
```
GBP_USD_D.csv: rows 3778; STUDY 2343; USED 1395; FORWARD 40; dropped {'boundary_embargo': 1}
GBP_USD_H4.csv: rows 22638; STUDY 14028; USED 8370; FORWARD 240; dropped {'boundary_embargo': 6, 'after_last_cross_session': 2}
GBP_USD_H1.csv: rows 90505; STUDY 56068; USED 33477; FORWARD 960; dropped {'boundary_embargo': 24, 'after_last_cross_session': 9}
AUD_USD_D.csv: rows 3778; STUDY 2343; USED 1395; FORWARD 40; dropped {'boundary_embargo': 1}
AUD_USD_H4.csv: rows 22637; STUDY 14027; USED 8370; FORWARD 240; dropped {'boundary_embargo': 6, 'after_last_cross_session': 2}
AUD_USD_H1.csv: rows 90507; STUDY 56070; USED 33477; FORWARD 960; dropped {'boundary_embargo': 24, 'after_last_cross_session': 9}
USD_JPY_D.csv: rows 3778; STUDY 2343; USED 1395; FORWARD 40; dropped {'boundary_embargo': 1}
USD_JPY_H4.csv: rows 22635; STUDY 14025; USED 8370; FORWARD 240; dropped {'boundary_embargo': 6, 'after_last_cross_session': 2}
USD_JPY_H1.csv: rows 90503; STUDY 56066; USED 33477; FORWARD 960; dropped {'boundary_embargo': 24, 'after_last_cross_session': 9}
XAU_USD_D.csv: rows 3453; STUDY 2025; USED 1388; FORWARD 40; dropped {'boundary_embargo': 1}
XAU_USD_H4.csv: rows 20672; STUDY 12111; USED 8321; FORWARD 240; dropped {'boundary_embargo': 6, 'after_last_cross_session': 2}
XAU_USD_H1.csv: rows 80725; STUDY 47989; USED 31816; FORWARD 920; dropped {'boundary_embargo': 23, 'after_last_cross_session': 8}
FORWARD aligned to the cross archive's last session 2026-11-05; manifest written
```

### verify
```
AUD_USD_D.csv: hash OK; rows 3778 (manifest 3778); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
AUD_USD_H1.csv: hash OK; rows 90507 (manifest 90507); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
AUD_USD_H4.csv: hash OK; rows 22637 (manifest 22637); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_USD_D.csv: hash OK; rows 3778 (manifest 3778); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_USD_H1.csv: hash OK; rows 90505 (manifest 90505); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
GBP_USD_H4.csv: hash OK; rows 22638 (manifest 22638); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
USD_JPY_D.csv: hash OK; rows 3778 (manifest 3778); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
USD_JPY_H1.csv: hash OK; rows 90503 (manifest 90503); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
USD_JPY_H4.csv: hash OK; rows 22635 (manifest 22635); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
XAU_USD_D.csv: hash OK; rows 3453 (manifest 3453); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
XAU_USD_H1.csv: hash OK; rows 80725 (manifest 80725); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0
XAU_USD_H4.csv: hash OK; rows 20672 (manifest 20672); span label mismatches 0; in sealed block 0; in boundary embargo 0; weekend-session 0; reserved labels 0

## GBP_USD
STUDY: H1->H4 compared 14028, exact 14028, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2343 sessions, high/low within 0.5 pip 2343, open+close exact 2343, D1 with no H4 0 | H1 gap runs 16 (236 h), runs of 3 h or more 12
USED: H1->H4 compared 8370, exact 8370, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1395 sessions, high/low within 0.5 pip 1395, open+close exact 1395, D1 with no H4 0 | H1 gap runs 9 (171 h), runs of 3 h or more 7
    gap 2022-12-25 14:00 PST -> 2022-12-26 14:00 PST  24 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 14:00 PST  24 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 14:00 PST  24 h
    gap 2024-12-24 14:00 PST -> 2024-12-25 14:00 PST  24 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 14:00 PST  24 h
    gap 2025-12-24 14:00 PST -> 2025-12-25 14:00 PST  24 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 14:00 PST  24 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 0 (0 h), runs of 3 h or more 0

## AUD_USD
STUDY: H1->H4 compared 14027, exact 14027, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2343 sessions, high/low within 0.5 pip 2343, open+close exact 2343, D1 with no H4 0 | H1 gap runs 19 (234 h), runs of 3 h or more 14
USED: H1->H4 compared 8370, exact 8370, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1395 sessions, high/low within 0.5 pip 1395, open+close exact 1395, D1 with no H4 0 | H1 gap runs 9 (171 h), runs of 3 h or more 7
    gap 2022-12-25 14:00 PST -> 2022-12-26 14:00 PST  24 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 14:00 PST  24 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 14:00 PST  24 h
    gap 2024-12-24 14:00 PST -> 2024-12-25 14:00 PST  24 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 14:00 PST  24 h
    gap 2025-12-24 14:00 PST -> 2025-12-25 14:00 PST  24 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 14:00 PST  24 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 0 (0 h), runs of 3 h or more 0

## USD_JPY
STUDY: H1->H4 compared 14025, exact 14025, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2343 sessions, high/low within 0.5 pip 2343, open+close exact 2343, D1 with no H4 0 | H1 gap runs 13 (238 h), runs of 3 h or more 11
USED: H1->H4 compared 8370, exact 8370, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1395 sessions, high/low within 0.5 pip 1395, open+close exact 1395, D1 with no H4 0 | H1 gap runs 9 (171 h), runs of 3 h or more 7
    gap 2022-12-25 14:00 PST -> 2022-12-26 14:00 PST  24 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 14:00 PST  24 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 14:00 PST  24 h
    gap 2024-12-24 14:00 PST -> 2024-12-25 14:00 PST  24 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 14:00 PST  24 h
    gap 2025-12-24 14:00 PST -> 2025-12-25 14:00 PST  24 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 14:00 PST  24 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 0 (0 h), runs of 3 h or more 0

## XAU_USD
STUDY: H1->H4 compared 12111, exact 12110, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 2025 sessions, high/low within 0.5 pip 2025, open+close exact 2025, D1 with no H4 0 | H1 gap runs 331 (753 h), runs of 3 h or more 43
    nonzero |diff| pips: H1->H4 1 values, max 5.000; D1 vs H4 0 values, max 0.000
  FAIL XAU_USD STUDY: consistency
USED: H1->H4 compared 8321, exact 8321, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 1388 sessions, high/low within 0.5 pip 1388, open+close exact 1388, D1 with no H4 0 | H1 gap runs 1387 (1831 h), runs of 3 h or more 56
    gap 2021-05-31 10:00 PDT -> 2021-05-31 15:00 PDT  5 h
    gap 2021-07-05 10:00 PDT -> 2021-07-05 15:00 PDT  5 h
    gap 2021-09-06 10:00 PDT -> 2021-09-06 15:00 PDT  5 h
    gap 2021-11-25 10:00 PST -> 2021-11-25 15:00 PST  5 h
    gap 2021-11-26 11:00 PST -> 2021-11-26 15:00 PST  4 h
    gap 2021-12-23 14:00 PST -> 2021-12-24 15:00 PST  25 h
    gap 2022-01-17 12:00 PST -> 2022-01-17 15:00 PST  3 h
    gap 2022-02-21 12:00 PST -> 2022-02-21 15:00 PST  3 h
    gap 2022-04-14 14:00 PDT -> 2022-04-15 15:00 PDT  25 h
    gap 2022-05-30 12:00 PDT -> 2022-05-30 15:00 PDT  3 h
    gap 2022-06-20 12:00 PDT -> 2022-06-20 15:00 PDT  3 h
    gap 2022-07-04 12:00 PDT -> 2022-07-04 15:00 PDT  3 h
    gap 2022-09-05 12:00 PDT -> 2022-09-05 15:00 PDT  3 h
    gap 2022-11-24 12:00 PST -> 2022-11-24 15:00 PST  3 h
    gap 2022-11-25 11:00 PST -> 2022-11-25 15:00 PST  4 h
    gap 2022-12-25 14:00 PST -> 2022-12-26 15:00 PST  25 h
    gap 2023-01-01 14:00 PST -> 2023-01-02 15:00 PST  25 h
    gap 2023-01-16 12:00 PST -> 2023-01-16 15:00 PST  3 h
    gap 2023-02-20 12:00 PST -> 2023-02-20 15:00 PST  3 h
    gap 2023-04-06 14:00 PDT -> 2023-04-07 15:00 PDT  25 h
    gap 2023-05-29 12:00 PDT -> 2023-05-29 15:00 PDT  3 h
    gap 2023-06-19 12:00 PDT -> 2023-06-19 15:00 PDT  3 h
    gap 2023-07-04 12:00 PDT -> 2023-07-04 15:00 PDT  3 h
    gap 2023-09-04 12:00 PDT -> 2023-09-04 15:00 PDT  3 h
    gap 2023-11-23 12:00 PST -> 2023-11-23 15:00 PST  3 h
    gap 2023-11-24 11:00 PST -> 2023-11-24 15:00 PST  4 h
    gap 2023-12-24 14:00 PST -> 2023-12-25 15:00 PST  25 h
    gap 2023-12-31 14:00 PST -> 2024-01-01 15:00 PST  25 h
    gap 2024-01-15 12:00 PST -> 2024-01-15 15:00 PST  3 h
    gap 2024-02-19 12:00 PST -> 2024-02-19 15:00 PST  3 h
    gap 2024-03-28 14:00 PDT -> 2024-03-29 15:00 PDT  25 h
    gap 2024-05-27 12:00 PDT -> 2024-05-27 15:00 PDT  3 h
    gap 2024-06-19 12:00 PDT -> 2024-06-19 15:00 PDT  3 h
    gap 2024-07-04 12:00 PDT -> 2024-07-04 15:00 PDT  3 h
    gap 2024-09-02 12:00 PDT -> 2024-09-02 15:00 PDT  3 h
    gap 2024-11-28 12:00 PST -> 2024-11-28 15:00 PST  3 h
    gap 2024-11-29 12:00 PST -> 2024-11-29 15:00 PST  3 h
    gap 2024-12-24 11:00 PST -> 2024-12-25 15:00 PST  28 h
    gap 2024-12-31 14:00 PST -> 2025-01-01 15:00 PST  25 h
    gap 2025-01-20 12:00 PST -> 2025-01-20 15:00 PST  3 h
    gap 2025-02-17 12:00 PST -> 2025-02-17 15:00 PST  3 h
    gap 2025-04-17 14:00 PDT -> 2025-04-18 15:00 PDT  25 h
    gap 2025-05-26 12:00 PDT -> 2025-05-26 15:00 PDT  3 h
    gap 2025-06-19 12:00 PDT -> 2025-06-19 15:00 PDT  3 h
    gap 2025-07-04 10:00 PDT -> 2025-07-04 15:00 PDT  5 h
    gap 2025-09-01 12:00 PDT -> 2025-09-01 15:00 PDT  3 h
    gap 2025-11-28 12:00 PST -> 2025-11-28 15:00 PST  3 h
    gap 2025-12-24 11:00 PST -> 2025-12-25 15:00 PST  28 h
    gap 2025-12-31 14:00 PST -> 2026-01-01 15:00 PST  25 h
    gap 2026-01-19 12:00 PST -> 2026-01-19 15:00 PST  3 h
    gap 2026-02-16 12:00 PST -> 2026-02-16 15:00 PST  3 h
    gap 2026-04-02 14:00 PDT -> 2026-04-03 15:00 PDT  25 h
    gap 2026-05-25 12:00 PDT -> 2026-05-25 15:00 PDT  3 h
    gap 2026-06-19 10:00 PDT -> 2026-06-19 15:00 PDT  5 h
    gap 2026-07-03 10:00 PDT -> 2026-07-03 15:00 PDT  5 h
    gap 2026-09-07 12:00 PDT -> 2026-09-07 15:00 PDT  3 h
FORWARD: H1->H4 compared 240, exact 240, H1-only buckets 0, H4 with no H1 0 | D1 vs its H4: 40 sessions, high/low within 0.5 pip 40, open+close exact 40, D1 with no H4 0 | H1 gap runs 39 (39 h), runs of 3 h or more 0

VERIFY: FAIL
```

### metals probe
```
account instruments endpoint: HTTP 200; 68 instruments; types {'CURRENCY': 68}
  METAL-type or XAU/XAG names on the account: none
candles endpoint XAU_USD: HTTP 200; candles returned 1; latest candle time 2026-11-05T22:00:00.000000000Z
candles endpoint XAG_USD: HTTP 200; candles returned 1; latest candle time 2026-11-05T22:00:00.000000000Z
candles endpoint XAU_GBP: HTTP 200; candles returned 1; latest candle time 2026-11-05T22:00:00.000000000Z
```
