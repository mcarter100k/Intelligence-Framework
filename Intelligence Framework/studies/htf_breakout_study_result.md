# BCS-2 result: weekly/daily level breaks, daily trend, obstacle check, 1.5R/2.5R targets (GBP/AUD)

Spec: docs/specs/htf_breakout_study_spec.md. Verdict on STUDY (2005-2013) episode R after era spread and financing. Bonferroni one-sided lower bound at 0.9875 (4 cells), 90% upper bound for REFUTED (bar +0.15R), 20000 resamples, seed 7. USED (2021-2026) is a learning-only replication.

## Verdicts (STUDY, era spread + financing, episodes)

### Cell B-1.5: **REFUTED**

- N 64 | mean -0.346R | median -1.060R | SD 1.011 | lower -0.623 | upper -0.184 | without best -0.372 | win 37.5% | max DD 26.5R
- exits: breakeven 7, stop 40, target 10, time 2, trail 5; mean risk 101.3 pips; mean spread -0.098R; mean financing -0.0009R; mean nights 1.19
- power at this N: +0.15R 0.107; smallest edge at 80% 0.462R
- before costs: N 64 | mean -0.247R | median -1.000R
- stops at the gap open: N 64 | mean -0.352R | median -1.060R
- long: N 26 | mean -0.350R | median -1.065R; short: N 38 | mean -0.343R | median -1.047R
- level source D: N 61 | mean -0.309R | median -1.059R; W: N 3 | mean -1.093R | median -1.097R
- 2005-01 to 2008-06 (before the crisis): N 19 | mean -0.687R | median -1.109R
- 2008-07 to 2009-06 (the crisis): N 5 | mean +0.741R | median +1.256R
- 2009-07 to 2013-12 (after): N 40 | mean -0.320R | median -1.047R
- by year: 2005 N 5 -1.135R; 2006 N 4 -1.140R; 2007 N 5 +0.037R; 2008 N 8 +0.063R; 2009 N 5 +0.284R; 2010 N 6 -0.416R; 2011 N 7 -0.877R; 2012 N 15 -0.378R; 2013 N 9 +0.034R
- skips: ATR warm-up 1; daily trend not aligned 208; first obstacle inside the target 33; stop wider than 1.5 ATR 1; ungraded at end of data 1
- flat 3.0 pips + financing: N 67 | mean -0.315R | median -1.025R | SD 0.997 | lower -0.583 | upper -0.157 | without best -0.339 | win 35.8% | max DD 25.5R
- flat 5.1 pips + financing: N 66 | mean -0.332R | median -1.040R | SD 1.000 | lower -0.597 | upper -0.174 | without best -0.357 | win 36.4% | max DD 26.3R
- no partial (full size to target, breakeven at +1R): N 64 | mean -0.341R | median -1.060R
- without the trend filter: N 160 | mean -0.194R | median -1.045R
- without the obstacle check: N 74 | mean -0.138R | median -1.042R
- without either filter: N 191 | mean -0.115R | median -1.023R

### Cell B-2.5: **REFUTED**

- N 57 | mean -0.346R | median -1.058R | SD 1.025 | lower -0.635 | upper -0.171 | without best -0.384 | win 36.8% | max DD 23.8R
- exits: breakeven 6, stop 36, target 1, time 2, trail 12; mean risk 105.4 pips; mean spread -0.095R; mean financing -0.0005R; mean nights 1.25
- power at this N: +0.15R 0.097; smallest edge at 80% 0.490R
- before costs: N 57 | mean -0.250R | median -1.000R
- stops at the gap open: N 57 | mean -0.349R | median -1.058R
- long: N 25 | mean -0.358R | median -1.068R; short: N 32 | mean -0.337R | median -1.043R
- level source D: N 53 | mean -0.344R | median -1.058R; W: N 4 | mean -0.377R | median -1.074R
- 2005-01 to 2008-06 (before the crisis): N 15 | mean -0.708R | median -1.097R
- 2008-07 to 2009-06 (the crisis): N 5 | mean +0.394R | median +1.009R
- 2009-07 to 2013-12 (after): N 37 | mean -0.299R | median -1.043R
- by year: 2005 N 3 -1.136R; 2006 N 3 -1.131R; 2007 N 4 -0.270R; 2008 N 8 -0.127R; 2009 N 5 +0.266R; 2010 N 6 -0.399R; 2011 N 5 -0.785R; 2012 N 14 -0.422R; 2013 N 9 +0.009R
- skips: ATR warm-up 1; daily trend not aligned 208; first obstacle inside the target 45; stop wider than 1.5 ATR 1; ungraded at end of data 1
- flat 3.0 pips + financing: N 59 | mean -0.310R | median -1.022R | SD 1.017 | lower -0.591 | upper -0.144 | without best -0.346 | win 35.6% | max DD 22.6R
- flat 5.1 pips + financing: N 57 | mean -0.309R | median -1.031R | SD 1.028 | lower -0.599 | upper -0.134 | without best -0.346 | win 36.8% | max DD 21.8R
- no partial (full size to target, breakeven at +1R): N 57 | mean -0.331R | median -1.058R
- without the trend filter: N 132 | mean -0.196R | median -1.049R
- without the obstacle check: N 74 | mean -0.123R | median -1.042R
- without either filter: N 191 | mean -0.120R | median -1.023R

### Cell C-1.5: **REFUTED**

- N 59 | mean -0.280R | median -1.102R | SD 1.019 | lower -0.569 | upper -0.113 | without best -0.307 | win 44.1% | max DD 18.9R
- exits: breakeven 10, stop 33, target 8, trail 8; mean risk 71.0 pips; mean spread -0.136R; mean financing +0.0006R; mean nights 0.46
- power at this N: +0.15R 0.100; smallest edge at 80% 0.482R
- before costs: N 59 | mean -0.144R | median -1.000R
- stops at the gap open: N 59 | mean -0.284R | median -1.102R
- long: N 23 | mean -0.310R | median -1.102R; short: N 36 | mean -0.261R | median -1.097R
- level source D: N 55 | mean -0.333R | median -1.107R; W: N 4 | mean +0.442R | median +0.822R
- 2005-01 to 2008-06 (before the crisis): N 20 | mean -0.436R | median -1.144R
- 2008-07 to 2009-06 (the crisis): N 6 | mean +0.682R | median +1.114R
- 2009-07 to 2013-12 (after): N 33 | mean -0.361R | median -1.102R
- by year: 2005 N 5 -1.180R; 2006 N 5 -0.382R; 2007 N 4 -0.046R; 2008 N 9 +0.341R; 2009 N 6 +0.141R; 2010 N 4 -0.572R; 2011 N 7 -0.696R; 2012 N 12 -0.348R; 2013 N 7 -0.159R
- skips: daily trend not aligned 162; first obstacle inside the target 14; no retest (expired) 74; ungraded at end of data 1
- flat 3.0 pips + financing: N 60 | mean -0.205R | median -1.030R | SD 1.007 | lower -0.490 | upper -0.041 | without best -0.230 | win 43.3% | max DD 14.9R
- flat 5.1 pips + financing: N 60 | mean -0.243R | median -1.057R | SD 1.008 | lower -0.528 | upper -0.078 | without best -0.269 | win 43.3% | max DD 17.1R
- no partial (full size to target, breakeven at +1R): N 59 | mean -0.306R | median -1.102R
- without the trend filter: N 151 | mean -0.190R | median -1.059R
- without the obstacle check: N 64 | mean -0.185R | median -0.383R
- without either filter: N 169 | mean -0.154R | median +0.296R

### Cell C-2.5: **REFUTED**

- N 55 | mean -0.280R | median -1.107R | SD 1.069 | lower -0.592 | upper -0.096 | without best -0.318 | win 41.8% | max DD 17.9R
- exits: breakeven 7, stop 32, target 1, trail 15; mean risk 71.5 pips; mean spread -0.135R; mean financing +0.0005R; mean nights 0.45
- power at this N: +0.15R 0.094; smallest edge at 80% 0.499R
- before costs: N 55 | mean -0.146R | median -1.000R
- stops at the gap open: N 55 | mean -0.280R | median -1.107R
- long: N 23 | mean -0.287R | median -1.102R; short: N 32 | mean -0.275R | median -1.115R
- level source D: N 51 | mean -0.344R | median -1.110R; W: N 4 | mean +0.532R | median +0.748R
- 2005-01 to 2008-06 (before the crisis): N 18 | mean -0.449R | median -1.144R
- 2008-07 to 2009-06 (the crisis): N 5 | mean +0.867R | median +1.293R
- 2009-07 to 2013-12 (after): N 32 | mean -0.364R | median -1.104R
- by year: 2005 N 5 -1.180R; 2006 N 3 -0.401R; 2007 N 4 -0.012R; 2008 N 9 +0.390R; 2009 N 5 +0.113R; 2010 N 4 -0.572R; 2011 N 7 -0.696R; 2012 N 11 -0.384R; 2013 N 7 -0.135R
- skips: daily trend not aligned 162; first obstacle inside the target 20; no retest (expired) 74; ungraded at end of data 1
- flat 3.0 pips + financing: N 57 | mean -0.174R | median -1.031R | SD 1.044 | lower -0.474 | upper +0.005 | without best -0.208 | win 43.9% | max DD 13.4R
- flat 5.1 pips + financing: N 57 | mean -0.209R | median -1.064R | SD 1.049 | lower -0.510 | upper -0.029 | without best -0.244 | win 43.9% | max DD 14.6R
- no partial (full size to target, breakeven at +1R): N 55 | mean -0.262R | median -1.107R
- without the trend filter: N 138 | mean -0.139R | median -1.046R
- without the obstacle check: N 64 | mean -0.165R | median -0.383R
- without either filter: N 169 | mean -0.142R | median +0.296R

## Secondary: level-break fake rate (STUDY)

- 149 of 466 first closes beyond a weekly/daily level were fakes (32.0%); D levels 137 of 432, W levels 12 of 34.

## Replication on USED 2021-04-27 -> 2026-09-09 (learning only, never proof; no financing)

- B-1.5, spread 3.0: N 38 | mean -0.096R | median -1.026R
- B-1.5, spread 5.1: N 38 | mean -0.141R | median -1.044R
- B-2.5, spread 3.0: N 35 | mean -0.137R | median -1.027R
- B-2.5, spread 5.1: N 34 | mean -0.141R | median -1.045R
- C-1.5, spread 3.0: N 28 | mean -0.016R | median +0.421R
- C-1.5, spread 5.1: N 28 | mean -0.049R | median +0.366R
- C-2.5, spread 3.0: N 28 | mean -0.030R | median -0.318R
- C-2.5, spread 5.1: N 27 | mean -0.099R | median -1.093R
