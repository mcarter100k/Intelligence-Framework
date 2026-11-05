# Frozen shadow candidates on the 2005–2013 STUDY data — pre-registered result (FCS-1)

Spec: docs/specs/frozen_candidates_study_spec.md. Every H4 bar, live candidate code, live grading rule. Verdict on episode R after era spread and financing. Bonferroni one-sided lower bound at 0.99 (5 cells), 90% upper bound for REFUTED (bar +0.15R), 20000 resamples, seed 7. Frame (data_map_spec §5): does this survive conditions it was not designed on.

## MOMENTUM_JOIN GBP_AUD: **REFUTED**

- **Primary (episode R after era spread and financing):** N 98; mean -0.095R; median -1.060R; Bonferroni lower bound -0.445R; 90% upper bound +0.117R; without best -0.164R; max DD 12.4R; win 33%; SD 1.614
- Median winner +1.510R (N 32); median loser -1.084R (N 66); stopped 64 of 98
- Costs per episode: spread -0.079R, financing -0.012R, mean nights 3.6, mean risk 122 pips
- Power at this N (SD 1.2R assumed, α 0.010): 14% for +0.15R; smallest edge detectable at 80% power +0.38R

**Secondary (never changes the verdict):**

- Before costs (live rule only): N 98; mean -0.004R; median -1.000R
- Flat 3.0-pip spread + financing: N 98; mean -0.045R; median -1.017R
- Stops filled at the gap open: N 98; mean -0.095R; median -1.060R; stops that gapped: 0
- Financing markup 0%: N 98; mean -0.077R; median -1.050R
- Financing markup 2%: N 98; mean -0.113R; median -1.066R
- Long episodes: N 44; mean -0.047R; median -1.081R
- Short episodes: N 54; mean -0.134R; median -1.055R
- 2005-01 to 2008-06 (before the crisis): N 38; mean -0.241R; median -1.085R
- 2008-07 to 2009-06 (the crisis): N 6; mean +1.106R; median +0.357R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 54; mean -0.126R; median -1.056R
- By year (N, mean R): 2005 14 -0.23; 2006 11 -0.28; 2007 10 +0.04; 2008 6 +0.50; 2009 10 -0.16; 2010 12 +0.07; 2011 9 -0.46; 2012 12 +0.21; 2013 14 -0.28
- Fires: 416; invalid dropped 0; graded 415; ungraded at data end 1

## MOMENTUM_JOIN GBP_JPY: **INCONCLUSIVE**

- **Primary (episode R after era spread and financing):** N 96; mean -0.012R; median -1.042R; Bonferroni lower bound -0.408R; 90% upper bound +0.222R; without best -0.071R; max DD 20.6R; win 29%; SD 1.764
- Median winner +2.185R (N 28); median loser -1.052R (N 68); stopped 66 of 96
- Costs per episode: spread -0.055R, financing -0.001R, mean nights 3.5, mean risk 121 pips
- Power at this N (SD 1.2R assumed, α 0.010): 14% for +0.15R; smallest edge detectable at 80% power +0.39R

**Secondary (never changes the verdict):**

- Before costs (live rule only): N 96; mean +0.044R; median -1.000R
- Flat 3.0-pip spread + financing: N 96; mean +0.013R; median -1.020R
- Stops filled at the gap open: N 96; mean -0.012R; median -1.042R; stops that gapped: 0
- Financing markup 0%: N 96; mean +0.005R; median -1.038R
- Financing markup 2%: N 96; mean -0.028R; median -1.045R
- Long episodes: N 52; mean +0.200R; median -1.039R
- Short episodes: N 44; mean -0.262R; median -1.047R
- 2005-01 to 2008-06 (before the crisis): N 33; mean +0.440R; median -0.886R
- 2008-07 to 2009-06 (the crisis): N 14; mean -0.845R; median -1.029R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 49; mean -0.078R; median -1.055R
- By year (N, mean R): 2005 7 +0.71; 2006 13 -0.16; 2007 8 +1.82; 2008 12 -0.63; 2009 12 -0.88; 2010 10 +0.27; 2011 9 +0.10; 2012 13 +0.11; 2013 12 -0.45
- Fires: 381; invalid dropped 0; graded 381; ungraded at data end 0

## THRUST_PULLBACK GBP_AUD: **REFUTED**

- **Primary (episode R after era spread and financing):** N 51; mean -0.130R; median -0.163R; Bonferroni lower bound -0.421R; 90% upper bound +0.035R; without best -0.183R; max DD 12.3R; win 41%; SD 0.921
- Median winner +0.748R (N 21); median loser -1.033R (N 30); stopped 19 of 51
- Costs per episode: spread -0.040R, financing -0.013R, mean nights 5.5, mean risk 267 pips
- Power at this N (SD 1.2R assumed, α 0.010): 8% for +0.15R; smallest edge detectable at 80% power +0.53R

**Secondary (never changes the verdict):**

- Before costs (live rule only): N 51; mean -0.077R; median -0.136R
- Flat 3.0-pip spread + financing: N 51; mean -0.104R; median -0.138R
- Stops filled at the gap open: N 51; mean -0.130R; median -0.163R; stops that gapped: 0
- Financing markup 0%: N 51; mean -0.117R; median -0.147R
- Financing markup 2%: N 51; mean -0.144R; median -0.179R
- Long episodes: N 24; mean -0.218R; median -0.739R
- Short episodes: N 27; mean -0.052R; median -0.142R
- 2005-01 to 2008-06 (before the crisis): N 25; mean -0.239R; median -0.386R
- 2008-07 to 2009-06 (the crisis): N 5; mean -0.262R; median -0.142R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 21; mean +0.031R; median -0.042R
- By year (N, mean R): 2005 7 +0.26; 2006 5 -0.08; 2007 7 -0.88; 2008 8 -0.19; 2009 7 -0.49; 2010 2 +0.31; 2011 6 +0.65; 2012 5 -0.29; 2013 4 -0.02
- Fires: 75; invalid dropped 0; graded 75; ungraded at data end 0

## THRUST_PULLBACK GBP_JPY: **INCONCLUSIVE**

- **Primary (episode R after era spread and financing):** N 39; mean +0.056R; median -0.256R; Bonferroni lower bound -0.369R; 90% upper bound +0.312R; without best -0.064R; max DD 5.6R; win 46%; SD 1.253
- Median winner +0.909R (N 18); median loser -1.033R (N 21); stopped 15 of 39
- Costs per episode: spread -0.028R, financing -0.029R, mean nights 5.4, mean risk 230 pips
- Power at this N (SD 1.2R assumed, α 0.010): 6% for +0.15R; smallest edge detectable at 80% power +0.61R

**Secondary (never changes the verdict):**

- Before costs (live rule only): N 39; mean +0.113R; median -0.231R
- Flat 3.0-pip spread + financing: N 39; mean +0.069R; median -0.250R
- Stops filled at the gap open: N 39; mean +0.056R; median -0.256R; stops that gapped: 0
- Financing markup 0%: N 39; mean +0.068R; median -0.248R
- Financing markup 2%: N 39; mean +0.044R; median -0.264R
- Long episodes: N 15; mean -0.163R; median -1.012R  (INSUFFICIENT: N<20)
- Short episodes: N 24; mean +0.193R; median -0.009R
- 2005-01 to 2008-06 (before the crisis): N 17; mean +0.126R; median -0.357R  (INSUFFICIENT: N<20)
- 2008-07 to 2009-06 (the crisis): N 5; mean -0.045R; median +0.168R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 17; mean +0.016R; median -0.256R  (INSUFFICIENT: N<20)
- By year (N, mean R): 2005 6 -0.72; 2006 4 +0.68; 2007 5 +0.70; 2008 5 +0.12; 2009 3 -0.54; 2010 4 +0.05; 2011 6 -0.40; 2012 2 +0.43; 2013 4 +0.66
- Fires: 53; invalid dropped 0; graded 53; ungraded at data end 0

## EARLY_MOMENTUM_v2 GBP_JPY: **REFUTED**

- **Primary (episode R after era spread and financing):** N 246; mean -0.099R; median -1.019R; Bonferroni lower bound -0.340R; 90% upper bound +0.042R; without best -0.139R; max DD 39.9R; win 31%; SD 1.718
- Median winner +1.202R (N 77); median loser -1.045R (N 169); stopped 139 of 246
- Costs per episode: spread -0.080R, financing -0.007R, mean nights 4.1, mean risk 172 pips
- Power at this N (SD 1.2R assumed, α 0.010): 36% for +0.15R; smallest edge detectable at 80% power +0.24R

**Secondary (never changes the verdict):**

- Before costs (live rule only): N 246; mean -0.012R; median -1.000R
- Flat 3.0-pip spread + financing: N 246; mean -0.063R; median -1.004R
- Stops filled at the gap open: N 246; mean -0.099R; median -1.019R; stops that gapped: 0
- Financing markup 0%: N 246; mean -0.084R; median -1.014R
- Financing markup 2%: N 246; mean -0.113R; median -1.022R
- Long episodes: N 147; mean -0.167R; median -1.012R
- Short episodes: N 99; mean +0.003R; median -1.029R
- 2005-01 to 2008-06 (before the crisis): N 92; mean -0.084R; median -1.004R
- 2008-07 to 2009-06 (the crisis): N 28; mean -0.237R; median -1.012R
- 2009-07 to 2013-12 (after): N 126; mean -0.078R; median -1.034R
- By year (N, mean R): 2005 21 -0.22; 2006 25 -0.01; 2007 27 +0.07; 2008 32 -0.24; 2009 27 +0.07; 2010 30 -0.24; 2011 28 -0.60; 2012 30 -0.12; 2013 26 +0.47
- Fires: 1955; invalid dropped 0; graded 1955; ungraded at data end 0

## Summary

| Cell | N | Mean R | Median R | Lower bound | Upper 90% | Without best | Max DD | Verdict |
|---|---|---|---|---|---|---|---|---|
| MOMENTUM_JOIN GBP_AUD | 98 | -0.095 | -1.060 | -0.445 | +0.117 | -0.164 | 12.4 | REFUTED |
| MOMENTUM_JOIN GBP_JPY | 96 | -0.012 | -1.042 | -0.408 | +0.222 | -0.071 | 20.6 | INCONCLUSIVE |
| THRUST_PULLBACK GBP_AUD | 51 | -0.130 | -0.163 | -0.421 | +0.035 | -0.183 | 12.3 | REFUTED |
| THRUST_PULLBACK GBP_JPY | 39 | +0.056 | -0.256 | -0.369 | +0.312 | -0.064 | 5.6 | INCONCLUSIVE |
| EARLY_MOMENTUM_v2 GBP_JPY | 246 | -0.099 | -1.019 | -0.340 | +0.042 | -0.139 | 39.9 | REFUTED |

- N required for +0.15R at 80% power (SD 1.2, α 0.010): 643
