# BCS-1 result: does a second hourly close confirm a breakout? (GBP/AUD, 2005-2013 STUDY)

Spec: docs/specs/breakout_confirmation_study_spec.md. Verdict on episode R after era spread and financing. Bonferroni one-sided lower bound at 0.98333 (3 cells), 90% upper bound for REFUTED (bar +0.15R), 20000 resamples, seed 7. Frame (data_map_spec §5): does this survive conditions it was not designed on.

## Verdicts (era spread + financing, episodes)

### Cell A: **REFUTED**

- N 1494 | mean -0.164R | median -1.095R | SD 1.502 | lower -0.245 | upper -0.114 | without best -0.169 | win 33.5% | max DD 274.3R
- stop-outs 869 (58.2%); mean risk 72.4 pips; mean spread -0.144R; mean financing -0.0061R; mean nights 0.85
- power at this N: +0.15R 0.997; smallest edge at 80% 0.092R
- before costs: N 1494 | mean -0.014R | median -1.000R
- flat 3.0 pips + financing: N 1494 | mean -0.072R | median -1.031R | SD 1.501 | lower -0.152 | upper -0.022 | without best -0.077 | win 34.3% | max DD 153.4R
- flat 5.1 pips + financing: N 1494 | mean -0.108R | median -1.054R | SD 1.500 | lower -0.189 | upper -0.058 | without best -0.113 | win 34.0% | max DD 196.2R
- stops at the gap open: N 1494 | mean -0.164R | median -1.095R; bars opening through the stop 1
- long: N 715 | mean -0.196R | median -1.105R; short: N 779 | mean -0.135R | median -1.081R
- 2005-01 to 2008-06 (before the crisis): N 570 | mean -0.274R | median -1.113R
- 2008-07 to 2009-06 (the crisis): N 162 | mean -0.337R | median -1.062R
- 2009-07 to 2013-12 (after): N 762 | mean -0.045R | median -1.089R
- by year: 2005 N 154 -0.394R; 2006 N 170 -0.159R; 2007 N 163 -0.315R; 2008 N 164 -0.333R; 2009 N 165 -0.192R; 2010 N 165 -0.004R; 2011 N 173 -0.031R; 2012 N 171 -0.221R; 2013 N 169 +0.142R

### Cell B: **REFUTED**

- N 1359 | mean -0.106R | median -0.819R | SD 1.371 | lower -0.183 | upper -0.058 | without best -0.115 | win 37.7% | max DD 149.0R
- stop-outs 665 (48.9%); mean risk 88.1 pips; mean spread -0.123R; mean financing -0.0065R; mean nights 1.01
- power at this N: +0.15R 0.993; smallest edge at 80% 0.097R
- before costs: N 1359 | mean +0.023R | median -0.725R
- flat 3.0 pips + financing: N 1359 | mean -0.027R | median -0.759R | SD 1.369 | lower -0.105 | upper +0.021 | without best -0.036 | win 39.4% | max DD 53.6R
- flat 5.1 pips + financing: N 1359 | mean -0.058R | median -0.786R | SD 1.369 | lower -0.135 | upper -0.010 | without best -0.067 | win 38.5% | max DD 87.2R
- stops at the gap open: N 1359 | mean -0.107R | median -0.819R; bars opening through the stop 2
- long: N 649 | mean -0.135R | median -1.038R; short: N 710 | mean -0.080R | median -0.590R
- 2005-01 to 2008-06 (before the crisis): N 504 | mean -0.163R | median -1.001R
- 2008-07 to 2009-06 (the crisis): N 144 | mean +0.012R | median -1.022R
- 2009-07 to 2013-12 (after): N 711 | mean -0.090R | median -0.680R
- by year: 2005 N 137 -0.231R; 2006 N 146 -0.011R; 2007 N 146 -0.287R; 2008 N 148 -0.002R; 2009 N 151 -0.103R; 2010 N 155 +0.097R; 2011 N 160 -0.127R; 2012 N 156 -0.271R; 2013 N 160 -0.036R

### Cell C: **REFUTED**

- N 1082 | mean -0.094R | median -1.146R | SD 1.896 | lower -0.213 | upper -0.020 | without best -0.107 | win 30.8% | max DD 141.6R
- stop-outs 707 (65.3%); mean risk 53.8 pips; mean spread -0.187R; mean financing -0.0072R; mean nights 0.77
- power at this N: +0.15R 0.976; smallest edge at 80% 0.108R
- before costs: N 1082 | mean +0.100R | median -1.000R
- flat 3.0 pips + financing: N 1082 | mean +0.026R | median -1.048R | SD 1.895 | lower -0.093 | upper +0.100 | without best +0.013 | win 31.4% | max DD 60.7R
- flat 5.1 pips + financing: N 1082 | mean -0.021R | median -1.085R | SD 1.896 | lower -0.140 | upper +0.053 | without best -0.034 | win 31.0% | max DD 90.5R
- stops at the gap open: N 1082 | mean -0.095R | median -1.146R; bars opening through the stop 2
- long: N 526 | mean -0.078R | median -1.154R; short: N 556 | mean -0.109R | median -1.136R
- 2005-01 to 2008-06 (before the crisis): N 412 | mean -0.049R | median -1.166R
- 2008-07 to 2009-06 (the crisis): N 120 | mean +0.031R | median -1.076R
- 2009-07 to 2013-12 (after): N 550 | mean -0.155R | median -1.153R
- by year: 2005 N 114 -0.123R; 2006 N 121 +0.311R; 2007 N 121 -0.249R; 2008 N 114 -0.087R; 2009 N 127 -0.137R; 2010 N 117 -0.066R; 2011 N 125 -0.276R; 2012 N 121 -0.255R; 2013 N 122 +0.042R

## Secondary (descriptive; never changes a verdict)

1. **Fake rate:** 946 of 3085 first closes were followed by a close back inside: **30.7%**. Long 493 of 1514; short 453 of 1571.
2. **What the second close filters (cell A, all trades, after era costs):** fakes N 940 | mean -0.603R | median -1.141R; confirmations N 2129 | mean +0.028R | median -0.833R.
3. **The price of waiting:** how much worse B's entry is than A's on the same event (positive = worse): mean +11.5 pips, median +7.0 pips (+0.053 daily ATR). Paired R(B) - R(A) on the same 2129 confirmed events: mean -0.167R, median -0.007R.
4. **Retest rate:** 1554 of 2129 graded B trades were retested within 12 bars (73.0%). B trades later retested: N 1554 | mean -0.400R | median -1.095R; not retested: N 575 | mean +0.568R | median +0.422R.
5. **Session of the first close** (UTC hour of the event bar's close; no DST adjustment):
   - Asia 22-07 UTC: events 930, fake rate 30.3%; B trades N 646 | mean -0.153R | median -1.063R
   - London 07-12 UTC: events 967, fake rate 30.5%; B trades N 669 | mean -0.107R | median -0.611R
   - London/New York 12-17 UTC: events 754, fake rate 28.1%; B trades N 540 | mean -0.064R | median -0.543R
   - late New York 17-22 UTC: events 434, fake rate 36.2%; B trades N 274 | mean -0.333R | median -1.073R
6. **Counts:**
   - long: A: events in ATR warm-up (no trade) 8; A: ungraded at end of data 1; B: confirmations in ATR warm-up (no trade) 4; B: ungraded at end of data 1; C: expired 276; C: fills in ATR warm-up (no trade) 4; C: retest filled 745; C: ungraded at end of data 1; levels broken (confirmed) 1021; levels replaced unbroken 2420; swings confirmed 3442
   - short: A: events in ATR warm-up (no trade) 7; B: confirmations in ATR warm-up (no trade) 5; C: expired 300; C: fills in ATR warm-up (no trade) 4; C: retest filled 818; levels broken (confirmed) 1118; levels replaced unbroken 2326; swings confirmed 3445
   - cell A: graded entries 3069, episodes 1494, same-bar ties 0
   - cell B: graded entries 2129, episodes 1359, same-bar ties 0
   - cell C: graded entries 1554, episodes 1082, same-bar ties 0
