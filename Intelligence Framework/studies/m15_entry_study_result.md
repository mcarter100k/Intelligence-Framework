# BCS-3 result: 15-minute entries on the BCS-1 and BCS-2 breakouts (GBP/AUD, 2005-2013 STUDY)

Spec: docs/specs/m15_entry_study_spec.md. Verdict on episode R after era spread and financing. Bonferroni one-sided lower bound at 0.98333 (3 cells), 90% upper bound for REFUTED (bar +0.15R), 20000 resamples, seed 7.

## Cell H1: **REFUTED**

- N 955 | mean -0.125R | median -1.106R | SD 1.646 | lower -0.236 | upper -0.056 | without best -0.138 | win 33.9% | max DD 125.0R
- for comparison, same levels with hourly entries: BCS-1 (R43): B −0.106R, C (hourly retest) −0.094R
- exits: stop 571, time 384; mean risk 68.7 pips; mean spread -0.150R; mean financing -0.0057R
- power at this N: +0.15R 0.959; smallest edge at 80% 0.115R
- before costs: N 955 | mean +0.031R | median -1.000R
- stops at the gap open: N 955 | mean -0.129R | median -1.106R
- long: N 469 | mean -0.150R | median -1.119R; short: N 486 | mean -0.101R | median -1.096R
- 2005-01 to 2008-06 (before the crisis): N 365 | mean -0.117R | median -1.123R
- 2008-07 to 2009-06 (the crisis): N 107 | mean -0.076R | median -1.055R
- 2009-07 to 2013-12 (after): N 483 | mean -0.141R | median -1.112R
- by year: 2005 N 100 -0.255R; 2006 N 115 -0.003R; 2007 N 102 -0.119R; 2008 N 100 +0.002R; 2009 N 113 -0.216R; 2010 N 100 +0.053R; 2011 N 114 -0.259R; 2012 N 107 -0.298R; 2013 N 104 -0.007R
- entry funnel: ATR warm-up or end of data 9; confirmations 2139; no entry: no retest trigger in 12 hours 592; no entry: went through the stop line first 253; triggered 1285; ungraded at end of data 1
- flat 3.0 pips + financing: N 955 | mean -0.028R | median -1.034R | SD 1.645 | lower -0.139 | upper +0.040 | without best -0.042 | win 34.7% | max DD 57.0R
- flat 5.1 pips + financing: N 955 | mean -0.066R | median -1.063R | SD 1.645 | lower -0.177 | upper +0.003 | without best -0.080 | win 34.7% | max DD 74.1R
- tight stop (lowest M15 low since the touch − 15 pips, no 0.3 ATR floor): N 955 | mean -0.255R | median -1.201R | SD 2.164 | lower -0.399 | upper -0.164 | without best -0.273 | win 24.0% | max DD 254.0R; mean risk 42.8 pips; before costs N 955 | mean -0.012R | median -1.000R

## Cell HTF-1.5: **REFUTED**

- N 52 | mean -0.397R | median -1.096R | SD 1.022 | lower -0.688 | upper -0.215 | without best -0.430 | win 34.6% | max DD 22.6R
- for comparison, same levels with hourly entries: BCS-2 (R44): B −0.346R, C (hourly retest) −0.280R
- exits: breakeven 3, stop 34, target 7, trail 8; mean risk 87.5 pips; mean spread -0.117R; mean financing -0.0000R
- power at this N: +0.15R 0.110; smallest edge at 80% 0.494R
- before costs: N 52 | mean -0.280R | median -1.000R
- stops at the gap open: N 52 | mean -0.397R | median -1.096R
- long: N 21 | mean -0.414R | median -1.112R; short: N 31 | mean -0.386R | median -1.078R
- 2005-01 to 2008-06 (before the crisis): N 18 | mean -0.554R | median -1.131R
- 2008-07 to 2009-06 (the crisis): N 6 | mean +0.095R | median +0.100R
- 2009-07 to 2013-12 (after): N 28 | mean -0.402R | median -1.096R
- by year: 2005 N 4 -1.161R; 2006 N 4 -0.622R; 2007 N 4 +0.057R; 2008 N 9 -0.178R; 2009 N 6 -0.295R; 2010 N 4 -0.484R; 2011 N 4 -0.732R; 2012 N 10 -0.176R; 2013 N 7 -0.537R
- entry funnel: ATR warm-up or end of data 1; confirmations 317; daily trend not aligned 139; first obstacle inside the target 14; no entry: no retest trigger in 12 hours 76; no entry: went through the stop line first 28; triggered 212; ungraded at end of data 1
- flat 3.0 pips + financing: N 54 | mean -0.338R | median -1.032R | SD 1.020 | lower -0.625 | upper -0.160 | without best -0.368 | win 33.3% | max DD 20.7R
- flat 5.1 pips + financing: N 53 | mean -0.359R | median -1.062R | SD 1.023 | lower -0.646 | upper -0.181 | without best -0.391 | win 34.0% | max DD 21.3R
- tight stop (lowest M15 low since the touch − 15 pips, no 0.3 ATR floor): N 54 | mean -0.435R | median -1.119R | SD 1.018 | lower -0.725 | upper -0.259 | without best -0.468 | win 40.7% | max DD 26.7R; mean risk 49.0 pips; before costs N 54 | mean -0.201R | median -1.000R
- no partial (full size to target, breakeven at +1R): N 52 | mean -0.371R | median -1.096R
- without the trend and obstacle filters: N 154 | mean -0.243R | median -1.077R

## Cell HTF-2.5: **REFUTED**

- N 47 | mean -0.330R | median -1.092R | SD 1.086 | lower -0.652 | upper -0.128 | without best -0.376 | win 36.2% | max DD 17.5R
- for comparison, same levels with hourly entries: BCS-2 (R44): B −0.346R, C (hourly retest) −0.280R
- exits: breakeven 2, stop 30, target 1, trail 14; mean risk 89.0 pips; mean spread -0.117R; mean financing -0.0002R
- power at this N: +0.15R 0.102; smallest edge at 80% 0.520R
- before costs: N 47 | mean -0.213R | median -1.000R
- stops at the gap open: N 47 | mean -0.330R | median -1.092R
- long: N 20 | mean -0.353R | median -1.115R; short: N 27 | mean -0.314R | median -1.063R
- 2005-01 to 2008-06 (before the crisis): N 17 | mean -0.516R | median -1.130R
- 2008-07 to 2009-06 (the crisis): N 5 | mean +0.444R | median +1.108R
- 2009-07 to 2013-12 (after): N 25 | mean -0.359R | median -1.092R
- by year: 2005 N 4 -1.161R; 2006 N 3 -0.448R; 2007 N 4 +0.068R; 2008 N 9 -0.138R; 2009 N 5 -0.075R; 2010 N 4 -0.454R; 2011 N 2 -0.358R; 2012 N 9 -0.213R; 2013 N 7 -0.537R
- entry funnel: ATR warm-up or end of data 1; confirmations 317; daily trend not aligned 139; first obstacle inside the target 21; no entry: no retest trigger in 12 hours 76; no entry: went through the stop line first 28; triggered 212; ungraded at end of data 1
- flat 3.0 pips + financing: N 47 | mean -0.257R | median -1.032R | SD 1.076 | lower -0.576 | upper -0.056 | without best -0.301 | win 36.2% | max DD 14.1R
- flat 5.1 pips + financing: N 47 | mean -0.286R | median -1.056R | SD 1.080 | lower -0.606 | upper -0.085 | without best -0.331 | win 36.2% | max DD 15.5R
- tight stop (lowest M15 low since the touch − 15 pips, no 0.3 ATR floor): N 52 | mean -0.409R | median -1.131R | SD 1.041 | lower -0.706 | upper -0.226 | without best -0.452 | win 42.3% | max DD 24.3R; mean risk 45.0 pips; before costs N 52 | mean -0.164R | median -1.000R
- no partial (full size to target, breakeven at +1R): N 47 | mean -0.268R | median -1.092R
- without the trend and obstacle filters: N 154 | mean -0.233R | median -1.077R

