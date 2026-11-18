# CCD-1 prototype runs (verbatim output)

Spec: docs/specs/configuration_detector_spec.md, commit bcc444a plus amendment 1 (ada22bd), before any data run. Prototype: studies/ccd1_prototype.py at 219ca97. Both runs through scripts/reality_run.py; project unchanged by hash each time.

## 1. Worked example (spec §9): live OANDA gold bars, run 2026-11-17 about 21:55 PT

```
bars: hourly 500 (last Tue 11-17 20:00 PT), 4-hour 400, daily 260
Mon 11-16 15:00 PT close 3862.77 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 55 bars, from ?)
Mon 11-16 16:00 PT close 3852.73 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 56 bars, from ?)
Mon 11-16 17:00 PT close 3866.40 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 57 bars, from ?)
Mon 11-16 18:00 PT close 3870.22 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 58 bars, from ?)
Mon 11-16 19:00 PT close 3870.88 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 59 bars, from ?)
Mon 11-16 20:00 PT close 3875.12 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 60 bars, from ?)
Mon 11-16 21:00 PT close 3881.34 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 61 bars, from ?)
Mon 11-16 22:00 PT close 3871.05 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 62 bars, from ?)
Mon 11-16 23:00 PT close 3871.20 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 63 bars, from ?)
Tue 11-17 00:00 PT close 3869.68 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 64 bars, from ?)
Tue 11-17 01:00 PT close 3865.70 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 65 bars, from ?)
Tue 11-17 02:00 PT close 3854.16 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 66 bars, from ?)
Tue 11-17 03:00 PT close 3868.26 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 67 bars, from ?)
Tue 11-17 04:00 PT close 3861.42 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 68 bars, from ?)
Tue 11-17 05:00 PT close 3851.36 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 69 bars, from ?)
Tue 11-17 06:00 PT close 3859.51 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 70 bars, from ?)
Tue 11-17 07:00 PT close 3875.80 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 71 bars, from ?)
Tue 11-17 08:00 PT close 3866.40 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 72 bars, from ?)
Tue 11-17 09:00 PT close 3863.23 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 73 bars, from ?)
Tue 11-17 10:00 PT close 3855.12 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 74 bars, from ?)
Tue 11-17 11:00 PT close 3847.30 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 75 bars, from ?)
Tue 11-17 12:00 PT close 3847.55 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 76 bars, from ?)
Tue 11-17 13:00 PT close 3849.21 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 77 bars, from ?)
Tue 11-17 15:00 PT close 3848.80 | ATR 88.09 | no close beyond range 3832.46-3923.09 (1.03 ATR, 78 bars, from ?)
Tue 11-17 16:00 PT close 3814.98 | ATR 88.09 | trend not aligned (hourly None, 4-hour DOWN, break DOWN) range 3832.46-3923.09 (1.03 ATR, 79 bars, from Thu 11-12 05:00 PT)
      trend: hourly None swings highs [3886.89, 3891.07] lows [3843.68, 3836.96]; 4-hour DOWN highs [3923.09, 3888.95] lows [3852.58, 3832.46]
      tested-side touches 1: ['Thu 11-12 21:00 PT']
      broken-side touches 3: ['Sun 11-15 22:00 PT', 'Mon 11-16 10:00 PT', 'Tue 11-17 05:00 PT']
Tue 11-17 17:00 PT close 3809.86 | ATR 88.09 | no range 
Tue 11-17 18:00 PT close 3798.07 | ATR 88.09 | no range 
Tue 11-17 19:00 PT close 3788.33 | ATR 88.09 | no range 
Tue 11-17 20:00 PT close 3786.53 | ATR 88.09 | no range 

DETECTIONS: 0
```

## 2. B1 counts: gold STUDY and USED archives (research_archive_legs, pinned hashes), counts only, no outcome

```
# B1 counts: CCD-1 (spec bcc444a, unsigned) on gold; counts only, no outcome

## STUDY: hourly bars 47967 (2006-03-20 -> 2013-12-30)
- bars by outcome of the test: {'no close beyond': 27733, 'no range': 18401, 'trend not aligned': 1295, 'not enough daily bars': 354, 'tested boundary': 139, None: 44, 'not enough 4-hour bars': 1}
- detections: 44 (up 32, down 12)
- non-overlapping episodes: pooled 31; up 24; down 10
  MDE at N=31, SD 1.25: +0.558R
  MDE at N=31, SD 1.264: +0.564R
  MDE at N=31, SD 1.864: +0.832R
  MDE at N=31, SD 1.896: +0.847R
- detections by year: {2006: 3, 2007: 5, 2008: 5, 2009: 2, 2010: 14, 2011: 5, 2012: 7, 2013: 3}

## USED: hourly bars 31816 (2021-04-26 -> 2026-09-09)
- bars by outcome of the test: {'no close beyond': 17642, 'no range': 12906, 'trend not aligned': 778, 'not enough daily bars': 345, 'tested boundary': 97, None: 47, 'not enough 4-hour bars': 1}
- detections: 47 (up 23, down 24)
- non-overlapping episodes: pooled 30; up 16; down 14
  MDE at N=30, SD 1.25: +0.567R
  MDE at N=30, SD 1.264: +0.574R
  MDE at N=30, SD 1.864: +0.846R
  MDE at N=30, SD 1.896: +0.861R
- detections by year: {2021: 1, 2022: 17, 2023: 11, 2024: 6, 2025: 7, 2026: 5}

```

## 3. Spot-check of one detection against the raw archive rows (third USED detection)

```
event bar 2022-03-04 14:00:00+00:00 close 1952.025 side UP ATR 29.599
range 1922.11 1951.02 width ATR 0.977 bars 41
trend h1 UP ([1938.836, 1951.02], [1929.715, 1934.075]) h4 UP ([1950.306, 1951.02], [1890.925, 1913.75])
tested touches [datetime.datetime(2022, 3, 2, 21, 0, tzinfo=datetime.timezone.utc), datetime.datetime(2022, 3, 3, 5, 0, tzinfo=datetime.timezone.utc), datetime.datetime(2022, 3, 3, 9, 0, tzinfo=datetime.timezone.utc), datetime.datetime(2022, 3, 3, 14, 0, tzinfo=datetime.timezone.utc), datetime.datetime(2022, 3, 3, 16, 0, tzinfo=datetime.timezone.utc)]
raw check: closes in run min/max 1924.645 1947.325 inside True
raw check: event close beyond True
  touch 2022-03-02 21:00:00+00:00 extreme 1924.846 zone edge 1925.07 in zone True
  touch 2022-03-03 05:00:00+00:00 extreme 1922.11 zone edge 1925.07 in zone True
  touch 2022-03-03 09:00:00+00:00 extreme 1923.736 zone edge 1925.07 in zone True
  touch 2022-03-03 14:00:00+00:00 extreme 1924.585 zone edge 1925.07 in zone True
  touch 2022-03-03 16:00:00+00:00 extreme 1923.36 zone edge 1925.07 in zone True
```
