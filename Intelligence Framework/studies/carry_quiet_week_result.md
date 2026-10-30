# Carry after a quiet week — pre-registered test result (2005–2013 STUDY data)

Spec: docs/specs/carry_quiet_week_spec.md. Run once, on the candles recorded at the counts stage (sha256 verified). Units: **typical-week ranges** (a trade's pips divided by the median weekly range of the 26 weeks before it), the primary measure; pips are secondary.

## GBP/JPY: **REFUTED**

- Side held: long GBP/JPY in 233 of 233 weeks (the higher-yielding currency bought).
- **Primary (typical-week units):** N 233; mean -0.003; one-sided 95% lower bound -0.075 (normal-approximation check -0.076); median -0.033; mean without the best week -0.012; winning weeks 48%
- Pips: N 233; mean -13.701 pips; one-sided 95% lower bound -45.077 pips (normal-approximation check -45.181); median -10.317 pips; mean without the best week -17.475 pips; winning weeks 48%
- Average trade in pips: price move -11.9, spread −5.5, financing +3.7, net -13.7
- Worst drawdown: -20.38 typical-week ranges (-8984 pips); worst week -1126 pips; longest losing run 7 weeks

**Secondary (never changes the verdict):**

- Carry in every week (no quiet filter): N 442; mean +0.014; one-sided 95% lower bound -0.047 (normal-approximation check -0.047); median +0.033; mean without the best week +0.008; winning weeks 52%
- Carry after non-quiet weeks: N 209; mean +0.033; one-sided 95% lower bound -0.069 (normal-approximation check -0.067); median +0.121; mean without the best week +0.022; winning weeks 57%
- Does 'quiet' add anything? Quiet minus non-quiet mean -0.037, 90% interval -0.162 to +0.088
- 2005-01 to 2008-06 (before the crisis): N 74, mean +0.080, winning weeks 57%
- 2008-07 to 2009-06 (the crisis): N 30, mean -0.118, winning weeks 40%
- 2009-07 to 2013-12 (after): N 129, mean -0.025, winning weeks 44%
- Net pips by year: 2005 +1406 (10), 2006 +2091 (30), 2007 -2345 (19), 2008 -2991 (25), 2009 -653 (36), 2010 -1099 (34), 2011 -1098 (28), 2012 +520 (28), 2013 +977 (23)
- Cost sensitivity, financing markup 0%: mean +0.004, lower bound -0.069
- Cost sensitivity, financing markup 2%: mean -0.011, lower bound -0.084
- Cost sensitivity, spread x1.5: mean -0.011, lower bound -0.084

## GBP/AUD: **INCONCLUSIVE**

- Side held: short GBP/AUD in 224 of 224 weeks (the higher-yielding currency bought).
- **Primary (typical-week units):** N 224; mean +0.033; one-sided 95% lower bound -0.035 (normal-approximation check -0.035); median +0.036; mean without the best week +0.025; winning weeks 51%
- Pips: N 224; mean +30.241 pips; one-sided 95% lower bound +1.083 pips (normal-approximation check +0.610); median +14.632 pips; mean without the best week +26.329 pips; winning weeks 51%
- Average trade in pips: price move +34.6, spread −8.7, financing +4.3, net +30.2
- Worst drawdown: -9.38 typical-week ranges (-3010 pips); worst week -616 pips; longest losing run 7 weeks

**Secondary (never changes the verdict):**

- Carry in every week (no quiet filter): N 442; mean -0.008; one-sided 95% lower bound -0.073 (normal-approximation check -0.073); median +0.042; mean without the best week -0.015; winning weeks 51%
- Carry after non-quiet weeks: N 218; mean -0.049; one-sided 95% lower bound -0.164 (normal-approximation check -0.162); median +0.061; mean without the best week -0.064; winning weeks 51%
- Does 'quiet' add anything? Quiet minus non-quiet mean +0.082, 90% interval -0.046 to +0.213
- 2005-01 to 2008-06 (before the crisis): N 78, mean +0.058, winning weeks 54%
- 2008-07 to 2009-06 (the crisis): N 27, mean +0.091, winning weeks 48%
- 2009-07 to 2013-12 (after): N 119, mean +0.003, winning weeks 50%
- Net pips by year: 2005 +871 (10), 2006 -309 (29), 2007 +133 (18), 2008 +2814 (26), 2009 +3246 (41), 2010 +1558 (26), 2011 +887 (25), 2012 -814 (33), 2013 -1612 (16)
- Cost sensitivity, financing markup 0%: mean +0.041, lower bound -0.027
- Cost sensitivity, financing markup 2%: mean +0.025, lower bound -0.041
- Cost sensitivity, spread x1.5: mean +0.022, lower bound -0.044

