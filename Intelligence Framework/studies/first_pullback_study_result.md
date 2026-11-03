# First pullback after a range turn — pre-registered test result (2005–2013 STUDY data)

Spec: docs/specs/first_pullback_study_spec.md. Verdict on episode R after era spread and financing. Bonferroni one-sided lower bound at 0.9875 (4 cells), 90% upper bound for REFUTED (bar +0.15R), 20000 resamples, seed 7. Frame (data_map_spec §5): does this survive conditions it was not designed on.

## GBP_JPY

### GBP_JPY 38.2%: **INCONCLUSIVE** (developing (N 20-59))

- **Primary (episode R after era spread and financing):** N 37; mean +0.073R; median +0.095R; Bonferroni lower bound -0.250R; 90% upper bound +0.266R; without best +0.004R; max DD 2.7R; win 54%; SD 0.920
- Median winner +0.529R (N 20); median loser -0.978R (N 17); stopped 9 of 37
- Costs per episode: spread -0.017R, financing -0.010R, mean nights 6.3, mean risk 379 pips
- Power at this N (SD 1.2R assumed, α 0.0125): 7% for +0.15R; smallest edge detectable at 80% power +0.61R

**Secondary (never changes the verdict):**

- Before costs: N 37; mean +0.100R; median +0.125R
- Flat 3.0-pip spread (present-day cost) + financing: N 37; mean +0.081R; median +0.102R; Bonferroni lower bound -0.242R; 90% upper bound +0.273R; without best +0.012R; max DD 2.6R; win 54%
- Stops filled at the gap open: N 37; mean +0.073R; median +0.095R; stops that gapped: 0; fills through the stop: 0
- Financing markup 0%: N 37; mean +0.082R; median +0.104R
- Financing markup 2%: N 37; mean +0.065R; median +0.085R
- Secondary stop below the 61.8% level: N 37; mean +0.297R; median -0.949R; Bonferroni lower bound -0.328R; 90% upper bound +0.691R; without best +0.137R; max DD 6.3R; win 43%; stopped 19
- Long episodes: N 17; mean -0.103R; median +0.207R  (INSUFFICIENT: N<20)
- Short episodes: N 20; mean +0.223R; median +0.057R
- No trend filter (every first touch): N 105; mean -0.105R; median -0.137R
- 2005-01 to 2008-06 (before the crisis): N 13; mean +0.225R; median +0.345R  (INSUFFICIENT: N<20)
- 2008-07 to 2009-06 (the crisis): N 4; mean +0.069R; median -0.090R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 20; mean -0.024R; median +0.033R
- By year (N, mean R): 2005 1 +0.02; 2006 5 +0.09; 2007 6 +0.42; 2008 3 -0.25; 2009 4 +0.41; 2010 4 -0.25; 2011 4 +0.63; 2012 3 -0.66; 2013 7 -0.10
- Legs: long {'anchors': 458, 'anchors in warm-up (skipped)': 5, 'entries': 19, 'expired qualified': 10, 'expired unqualified': 3, 'first touches': 56, 'qualified impulses': 66, 'replaced by a lower low before a touch': 389, 'touches against the 13-week direction (no trade)': 37}; short {'anchors': 773, 'anchors in warm-up (skipped)': 29, 'entries': 20, 'expired qualified': 4, 'expired unqualified': 5, 'first touches': 65, 'qualified impulses': 69, 'replaced by a lower low before a touch': 698, 'touches against the 13-week direction (no trade)': 45}; ungraded at data end 0

### GBP_JPY 50.0%: **INCONCLUSIVE** (developing (N 20-59))

- **Primary (episode R after era spread and financing):** N 29; mean +0.094R; median -0.042R; Bonferroni lower bound -0.361R; 90% upper bound +0.383R; without best -0.029R; max DD 3.3R; win 48%; SD 1.183
- Median winner +1.032R (N 14); median loser -1.019R (N 15); stopped 10 of 29
- Costs per episode: spread -0.021R, financing -0.015R, mean nights 5.9, mean risk 312 pips
- Power at this N (SD 1.2R assumed, α 0.0125): 6% for +0.15R; smallest edge detectable at 80% power +0.69R

**Secondary (never changes the verdict):**

- Before costs: N 29; mean +0.130R; median -0.016R
- Flat 3.0-pip spread (present-day cost) + financing: N 29; mean +0.103R; median -0.034R; Bonferroni lower bound -0.351R; 90% upper bound +0.392R; without best -0.019R; max DD 3.2R; win 48%
- Stops filled at the gap open: N 29; mean +0.094R; median -0.042R; stops that gapped: 0; fills through the stop: 0
- Financing markup 0%: N 29; mean +0.103R; median -0.032R
- Financing markup 2%: N 29; mean +0.085R; median -0.052R
- Secondary stop below the 61.8% level: N 29; mean +0.829R; median -1.060R; Bonferroni lower bound -0.366R; 90% upper bound +1.633R; without best +0.434R; max DD 9.1R; win 38%; stopped 18
- Long episodes: N 14; mean -0.125R; median -0.312R  (INSUFFICIENT: N<20)
- Short episodes: N 15; mean +0.299R; median +0.025R  (INSUFFICIENT: N<20)
- No trend filter (every first touch): N 89; mean -0.096R; median -0.145R
- 2005-01 to 2008-06 (before the crisis): N 8; mean +0.358R; median -0.240R  (INSUFFICIENT: N<20)
- 2008-07 to 2009-06 (the crisis): N 4; mean +0.305R; median -0.056R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 17; mean -0.080R; median -0.042R  (INSUFFICIENT: N<20)
- By year (N, mean R): 2006 3 -0.07; 2007 4 +0.74; 2008 3 -0.21; 2009 4 +0.81; 2010 4 -0.14; 2011 2 -0.09; 2012 3 -0.72; 2013 6 +0.05
- Legs: long {'anchors': 458, 'anchors in warm-up (skipped)': 5, 'entries': 15, 'expired qualified': 21, 'expired unqualified': 3, 'first touches': 45, 'qualified impulses': 66, 'replaced by a lower low before a touch': 389, 'touches against the 13-week direction (no trade)': 30}; short {'anchors': 773, 'anchors in warm-up (skipped)': 29, 'entries': 15, 'expired qualified': 14, 'expired unqualified': 5, 'first touches': 55, 'qualified impulses': 69, 'replaced by a lower low before a touch': 698, 'touches against the 13-week direction (no trade)': 40}; ungraded at data end 0

## GBP_AUD

### GBP_AUD 38.2%: **REFUTED** (developing (N 20-59))

- **Primary (episode R after era spread and financing):** N 36; mean -0.011R; median -0.082R; Bonferroni lower bound -0.269R; 90% upper bound +0.140R; without best -0.057R; max DD 3.2R; win 44%; SD 0.706
- Median winner +0.580R (N 16); median loser -0.385R (N 20); stopped 5 of 36
- Costs per episode: spread -0.030R, financing -0.004R, mean nights 6.9, mean risk 372 pips
- Power at this N (SD 1.2R assumed, α 0.0125): 7% for +0.15R; smallest edge detectable at 80% power +0.62R

**Secondary (never changes the verdict):**

- Before costs: N 36; mean +0.022R; median -0.061R
- Flat 3.0-pip spread (present-day cost) + financing: N 36; mean +0.008R; median -0.075R; Bonferroni lower bound -0.249R; 90% upper bound +0.159R; without best -0.037R; max DD 2.9R; win 44%
- Stops filled at the gap open: N 36; mean -0.011R; median -0.082R; stops that gapped: 0; fills through the stop: 0
- Financing markup 0%: N 36; mean +0.001R; median -0.078R
- Financing markup 2%: N 36; mean -0.024R; median -0.086R
- Secondary stop below the 61.8% level: N 36; mean -0.163R; median -1.043R; Bonferroni lower bound -0.645R; 90% upper bound +0.139R; without best -0.277R; max DD 12.2R; win 31%; stopped 22
- Long episodes: N 15; mean +0.186R; median +0.186R  (INSUFFICIENT: N<20)
- Short episodes: N 21; mean -0.152R; median -0.215R
- No trend filter (every first touch): N 90; mean +0.041R; median -0.059R
- 2005-01 to 2008-06 (before the crisis): N 12; mean -0.269R; median -0.394R  (INSUFFICIENT: N<20)
- 2008-07 to 2009-06 (the crisis): N 5; mean +0.385R; median +0.297R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 19; mean +0.047R; median -0.096R  (INSUFFICIENT: N<20)
- By year (N, mean R): 2005 2 -0.97; 2006 7 +0.03; 2007 2 -0.24; 2008 4 +0.20; 2009 4 +0.31; 2010 5 +0.25; 2011 5 +0.00; 2012 3 -0.19; 2013 4 -0.23
- Legs: long {'anchors': 860, 'anchors in warm-up (skipped)': 16, 'entries': 15, 'expired qualified': 10, 'expired unqualified': 3, 'first touches': 50, 'qualified impulses': 60, 'replaced by a lower low before a touch': 797, 'touches against the 13-week direction (no trade)': 35}; short {'anchors': 616, 'anchors in warm-up (skipped)': 7, 'entries': 21, 'expired qualified': 13, 'expired unqualified': 3, 'first touches': 48, 'qualified impulses': 61, 'replaced by a lower low before a touch': 551, 'touches against the 13-week direction (no trade)': 27}; ungraded at data end 0

### GBP_AUD 50.0%: **INCONCLUSIVE** (developing (N 20-59))

- **Primary (episode R after era spread and financing):** N 30; mean +0.017R; median -0.220R; Bonferroni lower bound -0.384R; 90% upper bound +0.276R; without best -0.088R; max DD 4.6R; win 40%; SD 1.084
- Median winner +1.146R (N 12); median loser -0.776R (N 18); stopped 8 of 30
- Costs per episode: spread -0.037R, financing -0.005R, mean nights 6.1, mean risk 281 pips
- Power at this N (SD 1.2R assumed, α 0.0125): 6% for +0.15R; smallest edge detectable at 80% power +0.68R

**Secondary (never changes the verdict):**

- Before costs: N 30; mean +0.060R; median -0.206R
- Flat 3.0-pip spread (present-day cost) + financing: N 30; mean +0.041R; median -0.211R; Bonferroni lower bound -0.358R; 90% upper bound +0.300R; without best -0.064R; max DD 4.4R; win 40%
- Stops filled at the gap open: N 30; mean +0.017R; median -0.220R; stops that gapped: 0; fills through the stop: 0
- Financing markup 0%: N 30; mean +0.031R; median -0.214R
- Financing markup 2%: N 30; mean +0.004R; median -0.226R
- Secondary stop below the 61.8% level: N 30; mean +0.115R; median -1.117R; Bonferroni lower bound -0.928R; 90% upper bound +0.845R; without best -0.238R; max DD 13.7R; win 17%; stopped 24
- Long episodes: N 12; mean +0.426R; median +0.141R  (INSUFFICIENT: N<20)
- Short episodes: N 18; mean -0.255R; median -0.536R  (INSUFFICIENT: N<20)
- No trend filter (every first touch): N 73; mean +0.010R; median -0.222R
- 2005-01 to 2008-06 (before the crisis): N 11; mean -0.230R; median -0.666R  (INSUFFICIENT: N<20)
- 2008-07 to 2009-06 (the crisis): N 5; mean +0.491R; median -0.186R  (INSUFFICIENT: N<20)
- 2009-07 to 2013-12 (after): N 14; mean +0.043R; median -0.047R  (INSUFFICIENT: N<20)
- By year (N, mean R): 2005 2 -0.97; 2006 6 +0.32; 2007 2 -0.74; 2008 4 +0.53; 2009 3 +0.30; 2010 3 +0.45; 2011 4 +0.23; 2012 3 -0.50; 2013 3 -0.60
- Legs: long {'anchors': 860, 'anchors in warm-up (skipped)': 16, 'entries': 12, 'expired qualified': 18, 'expired unqualified': 3, 'first touches': 42, 'qualified impulses': 60, 'replaced by a lower low before a touch': 797, 'touches against the 13-week direction (no trade)': 30}; short {'anchors': 616, 'anchors in warm-up (skipped)': 7, 'entries': 19, 'expired qualified': 23, 'expired unqualified': 3, 'first touches': 38, 'qualified impulses': 61, 'replaced by a lower low before a touch': 551, 'touches against the 13-week direction (no trade)': 19}; ungraded at data end 0

## Summary

| Cell | N | Mean R | Median R | Lower bound | Upper 90% | Without best | Max DD | Verdict |
|---|---|---|---|---|---|---|---|---|
| GBP_JPY 38.2% | 37 | +0.073 | +0.095 | -0.250 | +0.266 | +0.004 | 2.7 | INCONCLUSIVE |
| GBP_JPY 50.0% | 29 | +0.094 | -0.042 | -0.361 | +0.383 | -0.029 | 3.3 | INCONCLUSIVE |
| GBP_AUD 38.2% | 36 | -0.011 | -0.082 | -0.269 | +0.140 | -0.057 | 3.2 | REFUTED |
| GBP_AUD 50.0% | 30 | +0.017 | -0.220 | -0.384 | +0.276 | -0.088 | 4.6 | INCONCLUSIVE |

- Descriptive only: both pairs pooled at 38.2%: N 73; mean +0.032R; median -0.029R; N required for +0.15R at 80% power (SD 1.2, α 0.0125): 609
