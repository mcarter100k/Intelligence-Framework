# GMW-1 result: gold's 4-7 AM PT window (one pre-registered run)

Spec sha256 27d6738ccf8dbdda18417aebc8fc89373f5a8926bbdf1cca69f4ecc24d357326 (signed and frozen 2026-11-17). Šidák α 0.025321 (family of two), lower bound 97.47%, upper bound 90%, m = +0.05R, 20000 resamples, seed 7.

## STUDY

- Days with a complete window and ATR: 1990; skipped {'ATR warm-up': 15, 'missing window bar': 5, 'zero move': 4}
- Verdict population (floor B, d >= 0.30 ATR; cap d <= 1.0 ATR): 1723 days; floor-B skips 116; cap skips 151

### STUDY B1 (continuation); missing exit bar skipped 5
- **Primary (net of $0.50):** N 1718; mean -0.0287R; median -0.0843R; SD 0.808R; mean without best 1% -0.0654R; 97.47% lower -0.0664R; 90% upper -0.0032R -> **REFUTED**
- Without the FOMC days: N 1660; mean -0.0272R; median -0.0802R; SD 0.791R; mean without best 1% -0.0618R; 97.47% lower -0.0655R; 90% upper -0.0016R -> **REFUTED**
- Non-release days only: N 1577; mean -0.0283R; median -0.0838R; SD 0.814R; mean without best 1% -0.0648R; 97.47% lower -0.0681R; 90% upper -0.0017R
- **FINAL VERDICT B1: REFUTED**
- Block bootstrap by month: 97.47% lower -0.0666R; 90% upper -0.0027R

### STUDY B2 (fade); missing exit bar skipped 5
- **Primary (net of $0.50):** N 1718; mean -0.0685R; median -0.0602R; SD 0.759R; mean without best 1% -0.1011R; 97.47% lower -0.1046R; 90% upper -0.0454R -> **REFUTED**
- Without the FOMC days: N 1660; mean -0.0759R; median -0.0611R; SD 0.725R; mean without best 1% -0.1047R; 97.47% lower -0.1104R; 90% upper -0.0533R -> **REFUTED**
- Non-release days only: N 1577; mean -0.0703R; median -0.0610R; SD 0.762R; mean without best 1% -0.1022R; 97.47% lower -0.1080R; 90% upper -0.0454R
- **FINAL VERDICT B2: REFUTED**
- Block bootstrap by month: 97.47% lower -0.1039R; 90% upper -0.0450R

**Exam rule (§4.3):** no cell SUPPORTED: nothing goes to the sealed exam

### STUDY side results (never change a verdict)
- [1] B1 before costs: N 1718; mean +0.0271R; median -0.0333R; SD 0.807R; $1.00 spread: N 1718; mean -0.0845R; median -0.1350R; SD 0.810R; 0.012% spread: N 1718; mean +0.0130R; median -0.0478R; SD 0.807R
- [2] B1 uncapped: N 1869; mean -0.0219R; median -0.0672R; SD 0.786R; the cap removes 151 of 1869 trades (8.1%) carrying total +8.32R of the uncapped total -40.94R
- [3] B1 floor A (d >= 0.15 ATR): N 1808; mean -0.0273R; median -0.0855R; SD 0.824R; mean without best 1% -0.0656R; 97.47% lower -0.0649R; 90% upper -0.0027R -> **REFUTED**
- [4] B1 entry 8:00 AM PT: N 1716; mean -0.0357R; median -0.0694R; SD 0.678R
- [5] B1 exit 10:00 AM PT: N 1721; mean -0.0584R; median -0.0854R; SD 0.655R; exit 12:00 PM PT: N 1716; mean -0.0468R; median -0.0954R; SD 0.759R
- [6] B1 window move >= 0.5 ATR: N 139; mean -0.0666R; median -0.0648R; SD 0.522R; below: N 1579; mean -0.0253R; median -0.0850R; SD 0.829R
- [7] B1 owner's management (net $0.50): N 1718; mean -0.0366R; median -0.0646R; SD 0.700R
- [8] B1 longs: N 844; mean -0.0033R; median -0.0374R; SD 0.777R; shorts: N 874; mean -0.0531R; median -0.1277R; SD 0.837R; 6-month trend up: N 1147; mean -0.0325R; median -0.0737R; SD 0.774R; down: N 474; mean -0.0211R; median -0.0921R; SD 0.887R
  - B1 by year (N, mean R): 2006 167 -0.105; 2007 216 -0.082; 2008 227 +0.008; 2009 238 -0.011; 2010 226 -0.009; 2011 217 +0.021; 2012 218 -0.043; 2013 209 -0.030
- [9] B1 counts: trades 1718; stopped 288 (gap fills 2); timed exits 1430; trades with a missing hold bar 4
- [10] B1 cost per trade: median 0.0494R, mean 0.0558R; share above 0.2R 0.2%
- [11] B1 release days (NFP/CPI; no verdict, outside GNC-1's family): N 141; mean -0.0332R; median -0.0964R; SD 0.746R; other days: N 1577; mean -0.0283R; median -0.0838R; SD 0.814R
- [12] B1 FOMC days: N 58; mean -0.0699R; median -0.3671R; SD 1.202R; with/without verdicts in the primary block above
- [1] B2 before costs: N 1718; mean -0.0127R; median -0.0050R; SD 0.758R; $1.00 spread: N 1718; mean -0.1243R; median -0.1137R; SD 0.760R; 0.012% spread: N 1718; mean -0.0268R; median -0.0172R; SD 0.758R
- [2] B2 uncapped: N 1869; mean -0.0703R; median -0.0629R; SD 0.735R; the cap removes 151 of 1869 trades (8.1%) carrying total -13.76R of the uncapped total -131.39R
- [3] B2 floor A (d >= 0.15 ATR): N 1808; mean -0.0747R; median -0.0676R; SD 0.759R; mean without best 1% -0.1074R; 97.47% lower -0.1088R; 90% upper -0.0521R -> **REFUTED**
- [4] B2 entry 8:00 AM PT: N 1716; mean -0.0487R; median -0.0585R; SD 0.658R
- [5] B2 exit 10:00 AM PT: N 1721; mean -0.0523R; median -0.0358R; SD 0.645R; exit 12:00 PM PT: N 1716; mean -0.0583R; median -0.0391R; SD 0.731R
- [6] B2 window move >= 0.5 ATR: N 139; mean -0.0048R; median +0.0217R; SD 0.560R; below: N 1579; mean -0.0741R; median -0.0672R; SD 0.774R
- [7] B2 owner's management (net $0.50): N 1718; mean -0.0736R; median -0.0422R; SD 0.681R
- [8] B2 longs: N 874; mean -0.0428R; median -0.0208R; SD 0.806R; shorts: N 844; mean -0.0950R; median -0.1135R; SD 0.706R; 6-month trend up: N 1147; mean -0.0683R; median -0.0675R; SD 0.767R; down: N 474; mean -0.0651R; median -0.0349R; SD 0.721R
  - B2 by year (N, mean R): 2006 167 -0.031; 2007 216 -0.125; 2008 227 -0.088; 2009 238 -0.088; 2010 226 -0.063; 2011 217 -0.080; 2012 218 -0.028; 2013 209 -0.033
- [9] B2 counts: trades 1718; stopped 329 (gap fills 0); timed exits 1389; trades with a missing hold bar 4
- [10] B2 cost per trade: median 0.0494R, mean 0.0558R; share above 0.2R 0.2%
- [11] B2 release days (NFP/CPI; no verdict, outside GNC-1's family): N 141; mean -0.0485R; median -0.0494R; SD 0.723R; other days: N 1577; mean -0.0703R; median -0.0610R; SD 0.762R
- [12] B2 FOMC days: N 58; mean +0.1431R; median -0.0142R; SD 1.414R; with/without verdicts in the primary block above
- Days with a missing bar inside the hold (stop checked on bars present): 4: 2007-12-24, 2010-04-02, 2010-11-26, 2012-04-06

## USED

- Days with a complete window and ATR: 1372; skipped {'ATR warm-up': 15, 'zero move': 1}
- Verdict population (floor B, d >= 0.30 ATR; cap d <= 1.0 ATR): 1171 days; floor-B skips 96; cap skips 105

### USED B1 (continuation); missing exit bar skipped 13
- **Learning check only (no event data for this span; conditions not applicable):** N 1158; mean -0.0377R; median -0.0718R; SD 0.705R; mean without best 1% -0.0652R; 97.47% lower -0.0779R; 90% upper -0.0110R -> **REFUTED**
- Block bootstrap by month: 97.47% lower -0.0745R; 90% upper -0.0125R

### USED B2 (fade); missing exit bar skipped 13
- **Learning check only (no event data for this span; conditions not applicable):** N 1158; mean -0.0084R; median -0.0061R; SD 0.705R; mean without best 1% -0.0356R; 97.47% lower -0.0485R; 90% upper +0.0185R -> **REFUTED**
- Block bootstrap by month: 97.47% lower -0.0511R; 90% upper +0.0191R

### USED side results (never change a verdict)
- [1] B1 before costs: N 1158; mean -0.0061R; median -0.0406R; SD 0.705R; $1.00 spread: N 1158; mean -0.0693R; median -0.1018R; SD 0.705R; 0.012% spread: N 1158; mean -0.0230R; median -0.0583R; SD 0.705R
- [2] B1 uncapped: N 1263; mean -0.0311R; median -0.0579R; SD 0.684R; the cap removes 105 of 1263 trades (8.3%) carrying total +4.44R of the uncapped total -39.23R
- [3] B1 floor A (d >= 0.15 ATR): N 1223; mean -0.0285R; median -0.0697R; SD 0.725R; mean without best 1% -0.0580R; 97.47% lower -0.0691R; 90% upper -0.0014R -> **REFUTED**
- [4] B1 entry 8:00 AM PT: N 1158; mean -0.0396R; median -0.0540R; SD 0.553R
- [5] B1 exit 10:00 AM PT: N 1171; mean -0.0263R; median -0.0421R; SD 0.583R; exit 12:00 PM PT: N 1166; mean -0.0410R; median -0.0764R; SD 0.674R
- [6] B1 window move >= 0.5 ATR: N 93; mean +0.0075R; median -0.0781R; SD 0.511R; below: N 1065; mean -0.0417R; median -0.0715R; SD 0.719R
- [7] B1 owner's management (net $0.50): N 1158; mean -0.0408R; median -0.0636R; SD 0.658R
- [8] B1 longs: N 592; mean -0.0271R; median -0.0454R; SD 0.751R; shorts: N 566; mean -0.0488R; median -0.1071R; SD 0.654R; 6-month trend up: N 821; mean -0.0140R; median -0.0413R; SD 0.709R; down: N 242; mean -0.1222R; median -0.1435R; SD 0.703R
  - B1 by year (N, mean R): 2021 138 -0.044; 2022 223 -0.060; 2023 217 -0.050; 2024 223 -0.033; 2025 221 +0.015; 2026 136 -0.068
- [9] B1 counts: trades 1158; stopped 174 (gap fills 0); timed exits 984; trades with a missing hold bar 0
- [10] B1 cost per trade: median 0.0308R, mean 0.0316R; share above 0.2R 0.0%
- [1] B2 before costs: N 1158; mean +0.0232R; median +0.0212R; SD 0.706R; $1.00 spread: N 1158; mean -0.0400R; median -0.0401R; SD 0.705R; 0.012% spread: N 1158; mean +0.0063R; median +0.0068R; SD 0.705R
- [2] B2 uncapped: N 1263; mean -0.0138R; median -0.0169R; SD 0.685R; the cap removes 105 of 1263 trades (8.3%) carrying total -7.68R of the uncapped total -17.39R
- [3] B2 floor A (d >= 0.15 ATR): N 1223; mean -0.0107R; median -0.0186R; SD 0.737R; mean without best 1% -0.0428R; 97.47% lower -0.0521R; 90% upper +0.0163R -> **REFUTED**
- [4] B2 entry 8:00 AM PT: N 1158; mean -0.0109R; median -0.0196R; SD 0.574R
- [5] B2 exit 10:00 AM PT: N 1171; mean -0.0298R; median -0.0263R; SD 0.583R; exit 12:00 PM PT: N 1166; mean -0.0109R; median -0.0009R; SD 0.666R
- [6] B2 window move >= 0.5 ATR: N 93; mean -0.0717R; median +0.0220R; SD 0.509R; below: N 1065; mean -0.0029R; median -0.0076R; SD 0.720R
- [7] B2 owner's management (net $0.50): N 1158; mean -0.0173R; median -0.0010R; SD 0.649R
- [8] B2 longs: N 566; mean -0.0148R; median +0.0045R; SD 0.684R; shorts: N 592; mean -0.0022R; median -0.0234R; SD 0.725R; 6-month trend up: N 821; mean -0.0362R; median -0.0337R; SD 0.686R; down: N 242; mean +0.0920R; median +0.0612R; SD 0.732R
  - B2 by year (N, mean R): 2021 138 -0.022; 2022 223 -0.009; 2023 217 +0.029; 2024 223 -0.029; 2025 221 -0.059; 2026 136 +0.062
- [9] B2 counts: trades 1158; stopped 168 (gap fills 0); timed exits 990; trades with a missing hold bar 0
- [10] B2 cost per trade: median 0.0308R, mean 0.0316R; share above 0.2R 0.0%
- Days with a missing bar inside the hold (stop checked on bars present): 0

