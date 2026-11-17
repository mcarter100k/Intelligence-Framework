# GLS-1 result: gold lower-timeframe structure (one run, verbatim)

Spec `docs/specs/gold_ltf_structure_spec.md` v5 (commit af63c76); runner 284236c (sha256 `0f7e8873fca3f2c0506c802047040b6a361499b244f7d4f148ec3dff41d60809`); counts stage logged 823585c. Run 2026-11-17 through `reality_run.py --no-env`: exit 0, stderr empty, project unchanged by hash. Output sha256 `ad1a837ce322377d983a2fdc10f62f81e242bda9e0f582dca936118b743ef63e`, 1,427 lines. Seed 20261117, 2,000 session-cluster resamples. One blind crash check ran first with its output deleted unread (the run is deterministic, so it printed the same). Reading: `docs/reports/gold_ltf_structure_report.md`.

```
# GLS-1 full run. DESCRIPTIVE, not tradeable. 2021-2026 only, a regime-specific description. Structures counted on history; none is a signal.

data sha256: XAU_USD_M15_USED.csv ccc62418068d6f80fde399643b756638750fdd33c05a78bb9f1d882761ddc7f3; XAU_USD_M30_USED.csv 3f8636bc08cbfd6e193d21cc01147066524e8ff52975ba7ea697df1f1f18a828; XAU_USD_M5_BA_USED.csv 2c42103ba35d866ba7ba1223b7861e05bd070d5df5528ccf3bbbc6563b5ad959; XAU_USD_M5_USED.csv 92c3957aa1ba9ef50b3cb18071b3a1124ace21c5d92aa228628a513779ca684b

==============================================================================
# PART A: venue-independent (no costs)
==============================================================================

## §4 4-hour setups (G1; headline): 516 setups

### long: 286 setups; Selected on the outcome: 176 worked
- 4-hour: entered 286; missed {}
- 30-minute: entered 265; missed {'4-hour stop touched first': 21}
- 15-minute: entered 270; missed {'4-hour stop touched first': 16}
- 5-minute: entered 281; missed {'4-hour stop touched first': 5}

#### R before costs, per trade (all setups)
- +1 4-hour: n 286; mean +0.045 [-0.033, +0.129]; median +0.003; SD 0.668; mean w/o best 1% +0.020; positive 50.0%; stopped 41
- +1 30-minute: n 242; mean +0.023 [-0.127, +0.186]; median -0.249; SD 1.280; mean w/o best 1% -0.023; positive 42.6%; stopped 101
- +1 15-minute: n 269; mean -0.014 [-0.212, +0.215]; median -1.000; SD 1.767; mean w/o best 1% -0.121; positive 32.3%; stopped 157
- +1 5-minute: n 281; mean +0.185 [-0.117, +0.517]; median -1.000; SD 2.581; mean w/o best 1% +0.067; positive 24.2%; stopped 209
- +2 4-hour: n 286; mean +0.059 [-0.042, +0.160]; median -0.022; SD 0.900; mean w/o best 1% +0.015; positive 48.6%; stopped 58
- +2 30-minute: n 262; mean +0.105 [-0.118, +0.350]; median -1.000; SD 1.894; mean w/o best 1% -0.002; positive 37.0%; stopped 145
- +2 15-minute: n 270; mean +0.070 [-0.183, +0.355]; median -1.000; SD 2.328; mean w/o best 1% -0.079; positive 27.0%; stopped 186
- +2 5-minute: n 281; mean +0.215 [-0.131, +0.594]; median -1.000; SD 3.106; mean w/o best 1% +0.049; positive 19.6%; stopped 225
- +5 4-hour: n 286; mean +0.194 [+0.061, +0.345]; median -0.007; SD 1.281; mean w/o best 1% +0.137; positive 50.0%; stopped 98
- +5 30-minute: n 265; mean +0.348 [+0.000, +0.707]; median -1.000; SD 2.999; mean w/o best 1% +0.172; positive 27.9%; stopped 179
- +5 15-minute: n 270; mean +0.430 [-0.038, +0.974]; median -1.000; SD 4.216; mean w/o best 1% +0.111; positive 20.7%; stopped 210
- +5 5-minute: n 281; mean +0.180 [-0.291, +0.717]; median -1.000; SD 4.356; mean w/o best 1% -0.130; positive 11.4%; stopped 249
- +10 4-hour: n 286; mean +0.333 [+0.124, +0.561]; median -0.705; SD 1.864; mean w/o best 1% +0.243; positive 42.7%; stopped 138
- +10 30-minute: n 265; mean +0.460 [+0.034, +0.936]; median -1.000; SD 3.768; mean w/o best 1% +0.232; positive 22.3%; stopped 203
- +10 15-minute: n 270; mean +0.384 [-0.090, +0.917]; median -1.000; SD 4.218; mean w/o best 1% +0.134; positive 14.8%; stopped 230
- +10 5-minute: n 281; mean -0.067 [-0.491, +0.452]; median -1.000; SD 4.056; mean w/o best 1% -0.365; positive 7.5%; stopped 260

#### R before costs, per setup (a missed entry counts 0R), and paired difference from the 4-hour entry
- +1 4-hour: n 286; mean +0.045 [-0.032, +0.125]; median +0.003; SD 0.668; mean w/o best 1% +0.020; positive 50.0%
- +1 30-minute: n 286; mean +0.020 [-0.114, +0.165]; median +0.000; SD 1.177; mean w/o best 1% -0.038; positive 36.0% | paired vs 4-hour (both traded, n 242): -0.136 [-0.254, -0.004]
- +1 15-minute: n 286; mean -0.013 [-0.206, +0.183]; median -1.000; SD 1.714; mean w/o best 1% -0.114; positive 30.4% | paired vs 4-hour (both traded, n 269): -0.123 [-0.306, +0.067]
- +1 5-minute: n 286; mean +0.182 [-0.102, +0.497]; median -1.000; SD 2.558; mean w/o best 1% +0.065; positive 23.8% | paired vs 4-hour (both traded, n 281): +0.121 [-0.138, +0.415]
- +2 4-hour: n 286; mean +0.059 [-0.043, +0.160]; median -0.022; SD 0.900; mean w/o best 1% +0.015; positive 48.6%
- +2 30-minute: n 286; mean +0.096 [-0.101, +0.311]; median -1.000; SD 1.813; mean w/o best 1% -0.002; positive 33.9% | paired vs 4-hour (both traded, n 262): -0.041 [-0.218, +0.148]
- +2 15-minute: n 286; mean +0.066 [-0.187, +0.346]; median -1.000; SD 2.262; mean w/o best 1% -0.075; positive 25.5% | paired vs 4-hour (both traded, n 270): -0.052 [-0.279, +0.189]
- +2 5-minute: n 286; mean +0.212 [-0.126, +0.564]; median -1.000; SD 3.079; mean w/o best 1% +0.048; positive 19.2% | paired vs 4-hour (both traded, n 281): +0.137 [-0.171, +0.482]
- +5 4-hour: n 286; mean +0.194 [+0.051, +0.342]; median -0.007; SD 1.281; mean w/o best 1% +0.137; positive 50.0%
- +5 30-minute: n 286; mean +0.322 [+0.001, +0.680]; median -1.000; SD 2.888; mean w/o best 1% +0.159; positive 25.9% | paired vs 4-hour (both traded, n 265): +0.059 [-0.213, +0.386]
- +5 15-minute: n 286; mean +0.406 [-0.032, +0.927]; median -1.000; SD 4.097; mean w/o best 1% +0.104; positive 19.6% | paired vs 4-hour (both traded, n 270): +0.165 [-0.262, +0.645]
- +5 5-minute: n 286; mean +0.176 [-0.286, +0.712]; median -1.000; SD 4.318; mean w/o best 1% -0.127; positive 11.2% | paired vs 4-hour (both traded, n 281): -0.036 [-0.489, +0.449]
- +10 4-hour: n 286; mean +0.333 [+0.115, +0.548]; median -0.705; SD 1.864; mean w/o best 1% +0.243; positive 42.7%
- +10 30-minute: n 286; mean +0.426 [+0.012, +0.855]; median -1.000; SD 3.628; mean w/o best 1% +0.215; positive 20.6% | paired vs 4-hour (both traded, n 265): +0.021 [-0.335, +0.410]
- +10 15-minute: n 286; mean +0.362 [-0.089, +0.848]; median -1.000; SD 4.099; mean w/o best 1% +0.127; positive 14.0% | paired vs 4-hour (both traded, n 270): -0.029 [-0.479, +0.437]
- +10 5-minute: n 286; mean -0.066 [-0.479, +0.410]; median -1.000; SD 4.021; mean w/o best 1% -0.359; positive 7.3% | paired vs 4-hour (both traded, n 281): -0.424 [-0.860, +0.053]

#### The deciding number (Selected on the outcome): worked setups whose entry was stopped before the exit
- +1 4-hour: stopped 2/176 = 1.1% [0.3, 4.0]; after the stop the move ran (R of the stop hit) n 2; p25 0.00, median 1.28, p75 2.57, p90 2.57
- +1 30-minute: stopped 48/164 = 29.3% [22.8, 36.6]; after the stop the move ran (R of the stop hit) n 48; p25 4.70, median 6.55, p75 11.22, p90 18.81
- +1 15-minute: stopped 86/176 = 48.9% [41.6, 56.2]; after the stop the move ran (R of the stop hit) n 86; p25 6.04, median 12.37, p75 18.81, p90 31.51
- +1 5-minute: stopped 110/176 = 62.5% [55.2, 69.3]; after the stop the move ran (R of the stop hit) n 110; p25 11.29, median 20.96, p75 34.47, p90 66.51
- +2 4-hour: stopped 5/176 = 2.8% [1.2, 6.5]; after the stop the move ran (R of the stop hit) n 5; p25 0.00, median 0.17, p75 2.57, p90 7.38
- +2 30-minute: stopped 74/174 = 42.5% [35.4, 50.0]; after the stop the move ran (R of the stop hit) n 74; p25 2.85, median 5.95, p75 11.28, p90 18.81
- +2 15-minute: stopped 101/176 = 57.4% [50.0, 64.5]; after the stop the move ran (R of the stop hit) n 101; p25 4.76, median 11.55, p75 17.16, p90 29.85
- +2 5-minute: stopped 121/176 = 68.8% [61.6, 75.1]; after the stop the move ran (R of the stop hit) n 121; p25 11.09, median 19.49, p75 32.83, p90 55.09
- +5 4-hour: stopped 16/176 = 9.1% [5.7, 14.3]; after the stop the move ran (R of the stop hit) n 16; p25 0.00, median 0.24, p75 1.68, p90 2.57
- +5 30-minute: stopped 97/176 = 55.1% [47.7, 62.3]; after the stop the move ran (R of the stop hit) n 97; p25 2.47, median 5.12, p75 10.43, p90 18.42
- +5 15-minute: stopped 119/176 = 67.6% [60.4, 74.1]; after the stop the move ran (R of the stop hit) n 119; p25 3.46, median 10.44, p75 16.34, p90 26.56
- +5 5-minute: stopped 144/176 = 81.8% [75.5, 86.8]; after the stop the move ran (R of the stop hit) n 144; p25 8.69, median 17.29, p75 31.26, p90 54.70
- +10 4-hour: stopped 39/176 = 22.2% [16.7, 28.9]; after the stop the move ran (R of the stop hit) n 39; p25 0.00, median 0.00, p75 0.72, p90 2.03
- +10 30-minute: stopped 116/176 = 65.9% [58.6, 72.5]; after the stop the move ran (R of the stop hit) n 116; p25 0.93, median 4.13, p75 8.75, p90 17.92
- +10 15-minute: stopped 136/176 = 77.3% [70.5, 82.8]; after the stop the move ran (R of the stop hit) n 136; p25 2.39, median 8.75, p75 15.51, p90 21.76
- +10 5-minute: stopped 155/176 = 88.1% [82.4, 92.1]; after the stop the move ran (R of the stop hit) n 155; p25 7.74, median 15.87, p75 30.87, p90 54.14

#### Adverse excursion to the exit (Selected on the outcome, worked setups): dollars; daily ATR
- +1 4-hour: $n 176; p25 4.92, median 9.37, p75 17.27, p90 29.24 | n 176; p25 0.111, median 0.320, p75 0.562, p90 0.873
- +1 30-minute: $n 164; p25 4.26, median 9.01, p75 20.67, p90 38.41 | n 164; p25 0.160, median 0.302, p75 0.542, p90 0.908
- +1 15-minute: $n 176; p25 5.54, median 9.66, p75 20.12, p90 35.09 | n 176; p25 0.180, median 0.338, p75 0.580, p90 0.938
- +1 5-minute: $n 176; p25 4.34, median 8.88, p75 17.43, p90 28.35 | n 176; p25 0.120, median 0.280, p75 0.483, p90 0.867
- +2 4-hour: $n 176; p25 5.61, median 11.86, p75 21.13, p90 35.85 | n 176; p25 0.135, median 0.380, p75 0.733, p90 1.048
- +2 30-minute: $n 174; p25 6.30, median 13.08, p75 27.14, p90 46.21 | n 174; p25 0.222, median 0.386, p75 0.812, p90 1.163
- +2 15-minute: $n 176; p25 6.51, median 14.56, p75 26.03, p90 42.15 | n 176; p25 0.205, median 0.404, p75 0.820, p90 1.197
- +2 5-minute: $n 176; p25 5.09, median 10.79, p75 20.93, p90 37.03 | n 176; p25 0.156, median 0.370, p75 0.660, p90 1.088
- +5 4-hour: $n 176; p25 7.98, median 15.75, p75 24.50, p90 60.08 | n 176; p25 0.246, median 0.528, p75 0.885, p90 1.281
- +5 30-minute: $n 176; p25 8.88, median 18.94, p75 33.34, p90 68.46 | n 176; p25 0.315, median 0.588, p75 1.011, p90 1.592
- +5 15-minute: $n 176; p25 8.52, median 18.90, p75 33.34, p90 62.35 | n 176; p25 0.307, median 0.556, p75 1.053, p90 1.496
- +5 5-minute: $n 176; p25 8.61, median 16.16, p75 26.19, p90 59.23 | n 176; p25 0.255, median 0.481, p75 0.909, p90 1.404
- +10 4-hour: $n 176; p25 10.70, median 19.99, p75 46.49, p90 96.54 | n 176; p25 0.373, median 0.731, p75 1.266, p90 2.385
- +10 30-minute: $n 176; p25 10.91, median 25.37, p75 55.82, p90 117.39 | n 176; p25 0.375, median 0.837, p75 1.389, p90 2.977
- +10 15-minute: $n 176; p25 13.02, median 23.93, p75 55.78, p90 108.22 | n 176; p25 0.404, median 0.794, p75 1.440, p90 2.845
- +10 5-minute: $n 176; p25 10.99, median 20.38, p75 51.94, p90 101.47 | n 176; p25 0.380, median 0.671, p75 1.290, p90 2.500

#### Stop sizes (all entries taken): dollars; daily ATR; share under 0.3 daily ATR
- 4-hour: $n 286; p25 27.04, median 40.29, p75 68.45, p90 127.83 | n 286; p25 1.013, median 1.317, p75 1.802, p90 2.256 | under 0.3 ATR 0/286 = 0.0% [0.0, 1.3]
- 30-minute: $n 265; p25 8.04, median 14.11, p75 26.27, p90 48.09 | n 265; p25 0.299, median 0.427, p75 0.669, p90 1.198 | under 0.3 ATR 67/265 = 25.3% [20.4, 30.8]
- 15-minute: $n 270; p25 5.09, median 9.47, p75 17.24, p90 30.83 | n 270; p25 0.184, median 0.276, p75 0.464, p90 0.726 | under 0.3 ATR 148/270 = 54.8% [48.9, 60.6]
- 5-minute: $n 281; p25 3.02, median 4.89, p75 9.00, p90 14.18 | n 281; p25 0.111, median 0.155, p75 0.226, p90 0.371 | under 0.3 ATR 237/281 = 84.3% [79.6, 88.1]

#### Hindsight ratio (F2): share of trades with R before costs > 0, worked setups / all setups
- +1: 4-hour 73.3% / 50.0% = 1.47; 30-minute 55.5% / 42.6% = 1.30; 15-minute 43.8% / 32.3% = 1.35; 5-minute 36.9% / 24.2% = 1.53
- +2: 4-hour 73.9% / 48.6% = 1.52; 30-minute 49.4% / 37.0% = 1.33; 15-minute 39.2% / 27.0% = 1.45; 5-minute 30.7% / 19.6% = 1.57
- +5: 4-hour 78.4% / 50.0% = 1.57; 30-minute 39.8% / 27.9% = 1.42; 15-minute 30.7% / 20.7% = 1.48; 5-minute 18.2% / 11.4% = 1.60
- +10: 4-hour 67.6% / 42.7% = 1.59; 30-minute 33.0% / 22.3% = 1.48; 15-minute 22.7% / 14.8% = 1.53; 5-minute 11.9% / 7.5% = 1.60

#### By wait bucket (4-hour bars), R before costs per trade
- +1 30-minute: 1 n 29 mean -0.050; 2 n 53 mean -0.004; 3-6 n 137 mean +0.007; 7-12 n 23 mean +0.276
- +1 15-minute: 1 n 86 mean -0.050; 2 n 73 mean -0.163; 3-6 n 107 mean +0.124; 7-12 n 3 mean -0.257
- +1 5-minute: 1 n 205 mean +0.184; 2 n 63 mean +0.104; 3-6 n 13 mean +0.597
- +2 30-minute: 1 n 29 mean -0.079; 2 n 53 mean +0.249; 3-6 n 138 mean +0.007; 7-12 n 38 mean +0.409; 13+ n 4 mean +0.003
- +2 15-minute: 1 n 86 mean +0.187; 2 n 73 mean +0.066; 3-6 n 107 mean +0.003; 7-12 n 4 mean -0.579
- +2 5-minute: 1 n 205 mean +0.188; 2 n 63 mean +0.139; 3-6 n 13 mean +1.023
- +5 30-minute: 1 n 29 mean +0.124; 2 n 53 mean +0.265; 3-6 n 138 mean +0.125; 7-12 n 39 mean +0.928; 13+ n 6 mean +3.514
- +5 15-minute: 1 n 86 mean +0.336; 2 n 73 mean +0.577; 3-6 n 107 mean +0.460; 7-12 n 4 mean -1.029
- +5 5-minute: 1 n 205 mean +0.262; 2 n 63 mean +0.026; 3-6 n 13 mean -0.371
- +10 30-minute: 1 n 29 mean +0.847; 2 n 53 mean +0.318; 3-6 n 138 mean +0.363; 7-12 n 39 mean +0.248; 13+ n 6 mean +3.443
- +10 15-minute: 1 n 86 mean +0.299; 2 n 73 mean +0.072; 3-6 n 107 mean +0.717; 7-12 n 4 mean -1.029
- +10 5-minute: 1 n 205 mean -0.001; 2 n 63 mean -0.275; 3-6 n 13 mean -0.109

#### Secondary: the 1-session cut (waits of 6 bars or fewer), R before costs per setup (missed 0R)
- +1 30-minute: n 286; mean -0.002 [-0.119, +0.137]; median +0.000; SD 1.101; mean w/o best 1% -0.058; positive 32.2%
- +1 15-minute: n 286; mean -0.010 [-0.201, +0.193]; median -1.000; SD 1.713; mean w/o best 1% -0.111; positive 30.1%
- +1 5-minute: n 286; mean +0.182 [-0.111, +0.476]; median -1.000; SD 2.558; mean w/o best 1% +0.065; positive 23.8%
- +2 30-minute: n 286; mean +0.041 [-0.130, +0.237]; median +0.000; SD 1.600; mean w/o best 1% -0.053; positive 28.0%
- +2 15-minute: n 286; mean +0.074 [-0.162, +0.347]; median -1.000; SD 2.258; mean w/o best 1% -0.067; positive 25.2%
- +2 5-minute: n 286; mean +0.212 [-0.121, +0.609]; median -1.000; SD 3.079; mean w/o best 1% +0.048; positive 19.2%
- +5 30-minute: n 286; mean +0.122 [-0.115, +0.382]; median -1.000; SD 2.147; mean w/o best 1% -0.000; positive 21.0%
- +5 15-minute: n 286; mean +0.420 [-0.023, +0.924]; median -1.000; SD 4.094; mean w/o best 1% +0.119; positive 19.6%
- +5 5-minute: n 286; mean +0.176 [-0.284, +0.727]; median -1.000; SD 4.318; mean w/o best 1% -0.127; positive 11.2%
- +10 30-minute: n 286; mean +0.320 [-0.028, +0.710]; median -1.000; SD 3.188; mean w/o best 1% +0.108; positive 18.2%
- +10 15-minute: n 286; mean +0.377 [-0.060, +0.894]; median -1.000; SD 4.096; mean w/o best 1% +0.141; positive 14.0%
- +10 5-minute: n 286; mean -0.066 [-0.497, +0.452]; median -1.000; SD 4.021; mean w/o best 1% -0.359; positive 7.3%

#### Volatility split (H3; daily ATR / price at the setup): R before costs per setup (missed 0R); deciding number
- ATR / price (primary)
    low +1 4-hour: n 102; mean +0.086 [-0.052, +0.232]; median +0.032; SD 0.745; mean w/o best 1% +0.060; positive 52.0% | worked stopped 2/70 = 2.9% [0.8, 9.8]
    low +1 30-minute: n 102; mean +0.074 [-0.131, +0.298]; median +0.000; SD 1.087; mean w/o best 1% +0.033; positive 42.2% | worked stopped 16/64 = 25.0% [16.0, 36.8]
    low +1 15-minute: n 102; mean +0.037 [-0.311, +0.442]; median -1.000; SD 1.963; mean w/o best 1% -0.066; positive 28.4% | worked stopped 34/70 = 48.6% [37.2, 60.0]
    low +1 5-minute: n 102; mean -0.060 [-0.440, +0.351]; median -1.000; SD 2.058; mean w/o best 1% -0.153; positive 23.5% | worked stopped 46/70 = 65.7% [54.0, 75.8]
    low +5 4-hour: n 102; mean +0.405 [+0.124, +0.711]; median +0.258; SD 1.531; mean w/o best 1% +0.350; positive 53.9% | worked stopped 7/70 = 10.0% [4.9, 19.2]
    low +5 30-minute: n 102; mean +0.743 [+0.129, +1.411]; median -1.000; SD 3.306; mean w/o best 1% +0.615; positive 31.4% | worked stopped 37/70 = 52.9% [41.3, 64.1]
    low +5 15-minute: n 102; mean +0.583 [-0.138, +1.503]; median -1.000; SD 4.303; mean w/o best 1% +0.296; positive 20.6% | worked stopped 48/70 = 68.6% [57.0, 78.2]
    low +5 5-minute: n 102; mean -0.489 [-0.813, -0.131]; median -1.000; SD 1.835; mean w/o best 1% -0.587; positive 8.8% | worked stopped 61/70 = 87.1% [77.3, 93.1]
    mid +1 4-hour: n 96; mean -0.030 [-0.158, +0.100]; median -0.033; SD 0.644; mean w/o best 1% -0.050; positive 46.9% | worked stopped 0/54 = 0.0% [0.0, 6.6]
    mid +1 30-minute: n 96; mean -0.019 [-0.273, +0.263]; median -0.249; SD 1.369; mean w/o best 1% -0.083; positive 30.2% | worked stopped 15/52 = 28.8% [18.3, 42.3]
    mid +1 15-minute: n 96; mean -0.188 [-0.444, +0.105]; median -1.000; SD 1.419; mean w/o best 1% -0.253; positive 27.1% | worked stopped 29/54 = 53.7% [40.6, 66.3]
    mid +1 5-minute: n 96; mean +0.251 [-0.300, +0.851]; median -1.000; SD 2.901; mean w/o best 1% +0.116; positive 22.9% | worked stopped 33/54 = 61.1% [47.8, 73.0]
    mid +5 4-hour: n 96; mean +0.057 [-0.162, +0.295]; median -0.081; SD 1.083; mean w/o best 1% +0.021; positive 46.9% | worked stopped 4/54 = 7.4% [2.9, 17.6]
    mid +5 30-minute: n 96; mean -0.022 [-0.379, +0.385]; median -1.000; SD 1.880; mean w/o best 1% -0.103; positive 22.9% | worked stopped 31/54 = 57.4% [44.2, 69.7]
    mid +5 15-minute: n 96; mean +0.071 [-0.408, +0.666]; median -1.000; SD 2.649; mean w/o best 1% -0.042; positive 17.7% | worked stopped 38/54 = 70.4% [57.2, 80.9]
    mid +5 5-minute: n 96; mean +0.344 [-0.468, +1.236]; median -1.000; SD 4.419; mean w/o best 1% +0.091; positive 11.5% | worked stopped 43/54 = 79.6% [67.1, 88.2]
    high +1 4-hour: n 88; mean +0.080 [-0.046, +0.208]; median +0.012; SD 0.597; mean w/o best 1% +0.064; positive 51.1% | worked stopped 0/52 = 0.0% [0.0, 6.9]
    high +1 30-minute: n 88; mean -0.001 [-0.211, +0.231]; median +0.000; SD 1.055; mean w/o best 1% -0.045; positive 35.2% | worked stopped 17/48 = 35.4% [23.4, 49.6]
    high +1 15-minute: n 88; mean +0.121 [-0.202, +0.480]; median -0.821; SD 1.701; mean w/o best 1% +0.032; positive 36.4% | worked stopped 23/52 = 44.2% [31.6, 57.7]
    high +1 5-minute: n 88; mean +0.387 [-0.146, +0.973]; median -1.000; SD 2.686; mean w/o best 1% +0.281; positive 25.0% | worked stopped 31/52 = 59.6% [46.1, 71.8]
    high +5 4-hour: n 88; mean +0.098 [-0.132, +0.348]; median -0.079; SD 1.135; mean w/o best 1% +0.046; positive 48.9% | worked stopped 5/52 = 9.6% [4.2, 20.6]
    high +5 30-minute: n 88; mean +0.210 [-0.365, +0.981]; median -1.000; SD 3.228; mean w/o best 1% -0.032; positive 22.7% | worked stopped 29/52 = 55.8% [42.3, 68.4]
    high +5 15-minute: n 88; mean +0.566 [-0.364, +1.746]; median -1.000; SD 5.065; mean w/o best 1% +0.244; positive 20.5% | worked stopped 33/52 = 63.5% [49.9, 75.2]
    high +5 5-minute: n 88; mean +0.765 [-0.344, +2.123]; median -1.000; SD 5.911; mean w/o best 1% +0.382; positive 13.6% | worked stopped 40/52 = 76.9% [63.9, 86.3]
- ATR in dollars (secondary)
    low +1 4-hour: n 91; mean -0.000 [-0.153, +0.164]; median -0.031; SD 0.751; mean w/o best 1% -0.030; positive 45.1% | worked stopped 2/50 = 4.0% [1.1, 13.5]
    low +1 30-minute: n 91; mean -0.043 [-0.248, +0.167]; median +0.000; SD 1.001; mean w/o best 1% -0.092; positive 38.5% | worked stopped 12/47 = 25.5% [15.3, 39.5]
    low +1 15-minute: n 91; mean -0.206 [-0.518, +0.162]; median -1.000; SD 1.673; mean w/o best 1% -0.314; positive 20.9% | worked stopped 27/50 = 54.0% [40.4, 67.0]
    low +1 5-minute: n 91; mean -0.412 [-0.690, -0.101]; median -1.000; SD 1.469; mean w/o best 1% -0.505; positive 17.6% | worked stopped 35/50 = 70.0% [56.2, 80.9]
    low +5 4-hour: n 91; mean +0.140 [-0.149, +0.456]; median -0.256; SD 1.503; mean w/o best 1% +0.075; positive 42.9% | worked stopped 6/50 = 12.0% [5.6, 23.8]
    low +5 30-minute: n 91; mean +0.395 [-0.181, +1.043]; median -1.000; SD 2.983; mean w/o best 1% +0.247; positive 25.3% | worked stopped 27/50 = 54.0% [40.4, 67.0]
    low +5 15-minute: n 91; mean +0.312 [-0.442, +1.316]; median -1.000; SD 4.321; mean w/o best 1% -0.013; positive 15.4% | worked stopped 36/50 = 72.0% [58.3, 82.5]
    low +5 5-minute: n 91; mean -0.515 [-0.855, -0.087]; median -1.000; SD 1.893; mean w/o best 1% -0.625; positive 6.6% | worked stopped 44/50 = 88.0% [76.2, 94.4]
    mid +1 4-hour: n 101; mean -0.030 [-0.147, +0.091]; median -0.017; SD 0.609; mean w/o best 1% -0.051; positive 47.5% | worked stopped 0/67 = 0.0% [0.0, 5.4]
    mid +1 30-minute: n 101; mean -0.085 [-0.304, +0.167]; median -0.130; SD 1.180; mean w/o best 1% -0.147; positive 26.7% | worked stopped 18/58 = 31.0% [20.6, 43.8]
    mid +1 15-minute: n 101; mean -0.078 [-0.354, +0.261]; median -1.000; SD 1.647; mean w/o best 1% -0.182; positive 30.7% | worked stopped 32/67 = 47.8% [36.3, 59.5]
    mid +1 5-minute: n 101; mean +0.179 [-0.312, +0.737]; median -1.000; SD 2.651; mean w/o best 1% +0.050; positive 23.8% | worked stopped 42/67 = 62.7% [50.7, 73.3]
    mid +5 4-hour: n 101; mean +0.260 [+0.049, +0.469]; median +0.316; SD 1.115; mean w/o best 1% +0.228; positive 58.4% | worked stopped 3/67 = 4.5% [1.5, 12.4]
    mid +5 30-minute: n 101; mean +0.447 [-0.099, +1.098]; median -1.000; SD 3.143; mean w/o best 1% +0.239; positive 28.7% | worked stopped 35/67 = 52.2% [40.5, 63.7]
    mid +5 15-minute: n 101; mean +0.247 [-0.266, +0.806]; median -1.000; SD 2.716; mean w/o best 1% +0.135; positive 22.8% | worked stopped 44/67 = 65.7% [53.7, 75.9]
    mid +5 5-minute: n 101; mean -0.041 [-0.607, +0.666]; median -1.000; SD 3.400; mean w/o best 1% -0.285; positive 11.9% | worked stopped 55/67 = 82.1% [71.3, 89.4]
    high +1 4-hour: n 94; mean +0.170 [+0.040, +0.288]; median +0.185; SD 0.633; mean w/o best 1% +0.156; positive 57.4% | worked stopped 0/59 = 0.0% [0.0, 6.1]
    high +1 30-minute: n 94; mean +0.194 [-0.075, +0.465]; median +0.000; SD 1.316; mean w/o best 1% +0.139; positive 43.6% | worked stopped 18/59 = 30.5% [20.3, 43.1]
    high +1 15-minute: n 94; mean +0.244 [-0.112, +0.630]; median -1.000; SD 1.807; mean w/o best 1% +0.162; positive 39.4% | worked stopped 27/59 = 45.8% [33.7, 58.3]
    high +1 5-minute: n 94; mean +0.760 [+0.158, +1.434]; median -1.000; SD 3.119; mean w/o best 1% +0.653; positive 29.8% | worked stopped 33/59 = 55.9% [43.3, 67.8]
    high +5 4-hour: n 94; mean +0.175 [-0.051, +0.427]; median -0.072; SD 1.223; mean w/o best 1% +0.127; positive 47.9% | worked stopped 7/59 = 11.9% [5.9, 22.5]
    high +5 30-minute: n 94; mean +0.118 [-0.340, +0.631]; median -1.000; SD 2.502; mean w/o best 1% -0.012; positive 23.4% | worked stopped 35/59 = 59.3% [46.6, 70.9]
    high +5 15-minute: n 94; mean +0.667 [-0.205, +1.756]; median -1.000; SD 5.034; mean w/o best 1% +0.367; positive 20.2% | worked stopped 39/59 = 66.1% [53.4, 76.9]
    high +5 5-minute: n 94; mean +1.080 [-0.047, +2.481]; median -1.000; SD 6.316; mean w/o best 1% +0.725; positive 14.9% | worked stopped 45/59 = 76.3% [64.0, 85.3]

### short: 230 setups; Selected on the outcome: 102 worked
- 4-hour: entered 230; missed {}
- 30-minute: entered 200; missed {'4-hour stop touched first': 29, 'none within 10 sessions': 1}
- 15-minute: entered 215; missed {'4-hour stop touched first': 15}
- 5-minute: entered 223; missed {'4-hour stop touched first': 7}

#### R before costs, per trade (all setups)
- +1 4-hour: n 230; mean -0.053 [-0.146, +0.037]; median -0.098; SD 0.692; mean w/o best 1% -0.076; positive 42.2%; stopped 36
- +1 30-minute: n 181; mean -0.009 [-0.220, +0.216]; median -0.331; SD 1.528; mean w/o best 1% -0.116; positive 37.0%; stopped 78
- +1 15-minute: n 212; mean +0.001 [-0.322, +0.410]; median -1.000; SD 2.828; mean w/o best 1% -0.197; positive 28.3%; stopped 132
- +1 5-minute: n 223; mean +0.310 [-0.282, +1.073]; median -1.000; SD 5.394; mean w/o best 1% -0.116; positive 19.3%; stopped 175
- +2 4-hour: n 230; mean -0.077 [-0.180, +0.035]; median -0.142; SD 0.835; mean w/o best 1% -0.104; positive 41.3%; stopped 60
- +2 30-minute: n 199; mean +0.024 [-0.235, +0.303]; median -1.000; SD 1.973; mean w/o best 1% -0.076; positive 30.7%; stopped 118
- +2 15-minute: n 214; mean -0.039 [-0.380, +0.410]; median -1.000; SD 3.008; mean w/o best 1% -0.254; positive 22.4%; stopped 157
- +2 5-minute: n 223; mean +0.284 [-0.285, +1.042]; median -1.000; SD 5.307; mean w/o best 1% -0.105; positive 14.3%; stopped 185
- +5 4-hour: n 230; mean -0.096 [-0.245, +0.071]; median -0.432; SD 1.188; mean w/o best 1% -0.149; positive 37.0%; stopped 100
- +5 30-minute: n 200; mean +0.020 [-0.331, +0.478]; median -1.000; SD 2.910; mean w/o best 1% -0.180; positive 21.0%; stopped 150
- +5 15-minute: n 215; mean -0.132 [-0.433, +0.210]; median -1.000; SD 2.444; mean w/o best 1% -0.262; positive 16.3%; stopped 176
- +5 5-minute: n 223; mean +0.245 [-0.322, +0.923]; median -1.000; SD 4.857; mean w/o best 1% -0.087; positive 10.8%; stopped 198
- +10 4-hour: n 230; mean -0.186 [-0.346, -0.016]; median -1.000; SD 1.264; mean w/o best 1% -0.230; positive 31.3%; stopped 128
- +10 30-minute: n 200; mean -0.128 [-0.487, +0.257]; median -1.000; SD 2.677; mean w/o best 1% -0.287; positive 15.5%; stopped 167
- +10 15-minute: n 215; mean -0.332 [-0.621, +0.000]; median -1.000; SD 2.281; mean w/o best 1% -0.447; positive 11.6%; stopped 188
- +10 5-minute: n 223; mean -0.099 [-0.578, +0.455]; median -1.000; SD 4.047; mean w/o best 1% -0.361; positive 7.6%; stopped 205

#### R before costs, per setup (a missed entry counts 0R), and paired difference from the 4-hour entry
- +1 4-hour: n 230; mean -0.053 [-0.139, +0.043]; median -0.098; SD 0.692; mean w/o best 1% -0.076; positive 42.2%
- +1 30-minute: n 230; mean -0.007 [-0.176, +0.177]; median +0.000; SD 1.355; mean w/o best 1% -0.091; positive 29.1% | paired vs 4-hour (both traded, n 181): -0.116 [-0.273, +0.061]
- +1 15-minute: n 230; mean +0.001 [-0.296, +0.391]; median -1.000; SD 2.715; mean w/o best 1% -0.182; positive 26.1% | paired vs 4-hour (both traded, n 212): -0.020 [-0.294, +0.370]
- +1 5-minute: n 230; mean +0.301 [-0.260, +1.052]; median -1.000; SD 5.311; mean w/o best 1% -0.112; positive 18.7% | paired vs 4-hour (both traded, n 223): +0.333 [-0.216, +1.114]
- +2 4-hour: n 230; mean -0.077 [-0.180, +0.028]; median -0.142; SD 0.835; mean w/o best 1% -0.104; positive 41.3%
- +2 30-minute: n 230; mean +0.021 [-0.204, +0.267]; median -1.000; SD 1.835; mean w/o best 1% -0.065; positive 26.5% | paired vs 4-hour (both traded, n 199): -0.022 [-0.226, +0.197]
- +2 15-minute: n 230; mean -0.037 [-0.344, +0.388]; median -1.000; SD 2.901; mean w/o best 1% -0.236; positive 20.9% | paired vs 4-hour (both traded, n 214): -0.029 [-0.333, +0.380]
- +2 5-minute: n 230; mean +0.275 [-0.316, +1.028]; median -1.000; SD 5.225; mean w/o best 1% -0.102; positive 13.9% | paired vs 4-hour (both traded, n 223): +0.332 [-0.214, +1.062]
- +5 4-hour: n 230; mean -0.096 [-0.248, +0.064]; median -0.432; SD 1.188; mean w/o best 1% -0.149; positive 37.0%
- +5 30-minute: n 230; mean +0.017 [-0.299, +0.413]; median -1.000; SD 2.712; mean w/o best 1% -0.156; positive 18.3% | paired vs 4-hour (both traded, n 200): -0.018 [-0.332, +0.320]
- +5 15-minute: n 230; mean -0.123 [-0.407, +0.203]; median -1.000; SD 2.363; mean w/o best 1% -0.244; positive 15.2% | paired vs 4-hour (both traded, n 215): -0.099 [-0.340, +0.167]
- +5 5-minute: n 230; mean +0.238 [-0.310, +0.911]; median -1.000; SD 4.782; mean w/o best 1% -0.085; positive 10.4% | paired vs 4-hour (both traded, n 223): +0.312 [-0.216, +0.930]
- +10 4-hour: n 230; mean -0.186 [-0.340, -0.015]; median -1.000; SD 1.264; mean w/o best 1% -0.230; positive 31.3%
- +10 30-minute: n 230; mean -0.111 [-0.413, +0.230]; median -1.000; SD 2.496; mean w/o best 1% -0.249; positive 13.5% | paired vs 4-hour (both traded, n 200): -0.062 [-0.362, +0.264]
- +10 15-minute: n 230; mean -0.310 [-0.573, -0.004]; median -1.000; SD 2.207; mean w/o best 1% -0.418; positive 10.9% | paired vs 4-hour (both traded, n 215): -0.203 [-0.459, +0.074]
- +10 5-minute: n 230; mean -0.096 [-0.559, +0.480]; median -1.000; SD 3.984; mean w/o best 1% -0.350; positive 7.4% | paired vs 4-hour (both traded, n 223): +0.061 [-0.364, +0.590]

#### The deciding number (Selected on the outcome): worked setups whose entry was stopped before the exit
- +1 4-hour: stopped 0/102 = 0.0% [0.0, 3.6]; after the stop the move ran (R of the stop hit) n 0
- +1 30-minute: stopped 29/98 = 29.6% [21.5, 39.3]; after the stop the move ran (R of the stop hit) n 29; p25 3.97, median 6.02, p75 8.54, p90 15.60
- +1 15-minute: stopped 47/101 = 46.5% [37.1, 56.2]; after the stop the move ran (R of the stop hit) n 47; p25 4.48, median 7.23, p75 12.47, p90 14.62
- +1 5-minute: stopped 60/102 = 58.8% [49.1, 67.9]; after the stop the move ran (R of the stop hit) n 60; p25 8.93, median 15.15, p75 27.26, p90 40.25
- +2 4-hour: stopped 1/102 = 1.0% [0.2, 5.3]; after the stop the move ran (R of the stop hit) n 1; p25 0.20, median 0.20, p75 0.20, p90 0.20
- +2 30-minute: stopped 43/102 = 42.2% [33.0, 51.9]; after the stop the move ran (R of the stop hit) n 43; p25 2.83, median 5.58, p75 8.54, p90 14.04
- +2 15-minute: stopped 56/102 = 54.9% [45.2, 64.2]; after the stop the move ran (R of the stop hit) n 56; p25 4.30, median 6.85, p75 12.47, p90 14.53
- +2 5-minute: stopped 67/102 = 65.7% [56.1, 74.2]; after the stop the move ran (R of the stop hit) n 67; p25 7.66, median 12.87, p75 25.35, p90 39.57
- +5 4-hour: stopped 7/102 = 6.9% [3.4, 13.5]; after the stop the move ran (R of the stop hit) n 7; p25 0.00, median 0.00, p75 0.14, p90 0.20
- +5 30-minute: stopped 58/102 = 56.9% [47.2, 66.1]; after the stop the move ran (R of the stop hit) n 58; p25 1.62, median 3.87, p75 7.86, p90 13.35
- +5 15-minute: stopped 66/102 = 64.7% [55.1, 73.3]; after the stop the move ran (R of the stop hit) n 66; p25 3.57, median 6.21, p75 11.90, p90 14.23
- +5 5-minute: stopped 77/102 = 75.5% [66.3, 82.8]; after the stop the move ran (R of the stop hit) n 77; p25 6.50, median 11.83, p75 25.09, p90 37.64
- +10 4-hour: stopped 19/102 = 18.6% [12.3, 27.3]; after the stop the move ran (R of the stop hit) n 19; p25 0.00, median 0.00, p75 0.00, p90 0.20
- +10 30-minute: stopped 70/102 = 68.6% [59.1, 76.8]; after the stop the move ran (R of the stop hit) n 70; p25 0.41, median 3.38, p75 6.96, p90 12.77
- +10 15-minute: stopped 76/102 = 74.5% [65.3, 82.0]; after the stop the move ran (R of the stop hit) n 76; p25 2.57, median 5.38, p75 11.35, p90 14.04
- +10 5-minute: stopped 84/102 = 82.4% [73.8, 88.5]; after the stop the move ran (R of the stop hit) n 84; p25 4.62, median 10.72, p75 22.94, p90 36.08

#### Adverse excursion to the exit (Selected on the outcome, worked setups): dollars; daily ATR
- +1 4-hour: $n 102; p25 3.36, median 9.38, p75 16.45, p90 28.64 | n 102; p25 0.112, median 0.266, p75 0.516, p90 0.683
- +1 30-minute: $n 98; p25 4.38, median 7.70, p75 17.70, p90 35.85 | n 98; p25 0.136, median 0.277, p75 0.530, p90 0.885
- +1 15-minute: $n 101; p25 4.70, median 9.55, p75 17.60, p90 31.72 | n 101; p25 0.152, median 0.318, p75 0.558, p90 0.739
- +1 5-minute: $n 102; p25 3.36, median 7.62, p75 17.17, p90 32.12 | n 102; p25 0.112, median 0.279, p75 0.518, p90 0.743
- +2 4-hour: $n 102; p25 4.31, median 10.90, p75 18.09, p90 34.34 | n 102; p25 0.151, median 0.324, p75 0.591, p90 0.774
- +2 30-minute: $n 102; p25 4.85, median 11.84, p75 23.70, p90 39.93 | n 102; p25 0.162, median 0.381, p75 0.697, p90 1.029
- +2 15-minute: $n 102; p25 6.26, median 12.64, p75 19.74, p90 40.89 | n 102; p25 0.190, median 0.391, p75 0.688, p90 0.837
- +2 5-minute: $n 102; p25 4.13, median 9.75, p75 19.47, p90 36.84 | n 102; p25 0.126, median 0.347, p75 0.584, p90 0.868
- +5 4-hour: $n 102; p25 5.95, median 14.73, p75 28.64, p90 49.09 | n 102; p25 0.183, median 0.492, p75 0.746, p90 1.192
- +5 30-minute: $n 102; p25 5.98, median 14.91, p75 32.96, p90 67.01 | n 102; p25 0.203, median 0.521, p75 1.012, p90 1.582
- +5 15-minute: $n 102; p25 8.38, median 15.18, p75 34.06, p90 67.32 | n 102; p25 0.286, median 0.518, p75 0.867, p90 1.510
- +5 5-minute: $n 102; p25 6.34, median 12.55, p75 31.68, p90 57.18 | n 102; p25 0.199, median 0.469, p75 0.811, p90 1.451
- +10 4-hour: $n 102; p25 9.34, median 17.84, p75 48.08, p90 101.72 | n 102; p25 0.319, median 0.602, p75 1.205, p90 2.231
- +10 30-minute: $n 102; p25 10.88, median 22.25, p75 49.77, p90 116.89 | n 102; p25 0.326, median 0.749, p75 1.544, p90 2.781
- +10 15-minute: $n 102; p25 10.91, median 19.06, p75 49.77, p90 109.57 | n 102; p25 0.357, median 0.688, p75 1.387, p90 2.556
- +10 5-minute: $n 102; p25 7.67, median 17.09, p75 47.97, p90 104.78 | n 102; p25 0.281, median 0.579, p75 1.315, p90 2.489

#### Stop sizes (all entries taken): dollars; daily ATR; share under 0.3 daily ATR
- 4-hour: $n 230; p25 23.88, median 35.44, p75 68.68, p90 127.44 | n 230; p25 0.919, median 1.200, p75 1.633, p90 2.229 | under 0.3 ATR 1/230 = 0.4% [0.1, 2.4]
- 30-minute: $n 200; p25 7.81, median 12.50, p75 26.67, p90 48.03 | n 200; p25 0.277, median 0.405, p75 0.706, p90 1.032 | under 0.3 ATR 67/200 = 33.5% [27.3, 40.3]
- 15-minute: $n 215; p25 4.79, median 8.03, p75 18.80, p90 38.00 | n 215; p25 0.198, median 0.271, p75 0.397, p90 0.634 | under 0.3 ATR 123/215 = 57.2% [50.5, 63.6]
- 5-minute: $n 223; p25 2.62, median 4.83, p75 9.72, p90 20.44 | n 223; p25 0.101, median 0.151, p75 0.236, p90 0.320 | under 0.3 ATR 197/223 = 88.3% [83.5, 91.9]

#### Hindsight ratio (F2): share of trades with R before costs > 0, worked setups / all setups
- +1: 4-hour 74.5% / 42.2% = 1.77; 30-minute 51.0% / 37.0% = 1.38; 15-minute 44.6% / 28.3% = 1.57; 5-minute 38.2% / 19.3% = 1.98
- +2: 4-hour 80.4% / 41.3% = 1.95; 30-minute 49.0% / 30.7% = 1.60; 15-minute 40.2% / 22.4% = 1.79; 5-minute 30.4% / 14.3% = 2.12
- +5: 4-hour 76.5% / 37.0% = 2.07; 30-minute 40.2% / 21.0% = 1.91; 15-minute 33.3% / 16.3% = 2.05; 5-minute 23.5% / 10.8% = 2.19
- +10: 4-hour 65.7% / 31.3% = 2.10; 30-minute 30.4% / 15.5% = 1.96; 15-minute 24.5% / 11.6% = 2.11; 5-minute 16.7% / 7.6% = 2.19

#### By wait bucket (4-hour bars), R before costs per trade
- +1 30-minute: 1 n 27 mean -0.085; 2 n 27 mean -0.104; 3-6 n 108 mean +0.005; 7-12 n 19 mean +0.149
- +1 15-minute: 1 n 64 mean +0.391; 2 n 45 mean -0.069; 3-6 n 98 mean -0.251; 7-12 n 5 mean +0.568
- +1 5-minute: 1 n 161 mean +0.405; 2 n 44 mean +0.385; 3-6 n 18 mean -0.722
- +2 30-minute: 1 n 27 mean -0.156; 2 n 27 mean -0.124; 3-6 n 108 mean +0.090; 7-12 n 37 mean +0.072
- +2 15-minute: 1 n 64 mean +0.374; 2 n 45 mean -0.226; 3-6 n 98 mean -0.175; 7-12 n 7 mean -0.722
- +2 5-minute: 1 n 161 mean +0.401; 2 n 44 mean +0.198; 3-6 n 18 mean -0.552
- +5 30-minute: 1 n 27 mean +0.004; 2 n 27 mean -0.250; 3-6 n 108 mean -0.017; 7-12 n 37 mean +0.365; 13+ n 1 mean -1.000
- +5 15-minute: 1 n 64 mean +0.386; 2 n 45 mean -0.317; 3-6 n 98 mean -0.321; 7-12 n 8 mean -0.917
- +5 5-minute: 1 n 161 mean +0.429; 2 n 44 mean +0.082; 3-6 n 18 mean -1.000
- +10 30-minute: 1 n 27 mean -0.466; 2 n 27 mean -0.627; 3-6 n 108 mean -0.008; 7-12 n 37 mean +0.156; 13+ n 1 mean -1.000
- +10 15-minute: 1 n 64 mean +0.143; 2 n 45 mean -0.600; 3-6 n 98 mean -0.464; 7-12 n 8 mean -1.000
- +10 5-minute: 1 n 161 mean +0.082; 2 n 44 mean -0.390; 3-6 n 18 mean -1.000

#### Secondary: the 1-session cut (waits of 6 bars or fewer), R before costs per setup (missed 0R)
- +1 30-minute: n 230; mean -0.020 [-0.176, +0.165]; median +0.000; SD 1.304; mean w/o best 1% -0.104; positive 24.3%
- +1 15-minute: n 230; mean -0.012 [-0.302, +0.421]; median -1.000; SD 2.708; mean w/o best 1% -0.194; positive 24.8%
- +1 5-minute: n 230; mean +0.301 [-0.307, +1.106]; median -1.000; SD 5.311; mean w/o best 1% -0.112; positive 18.7%
- +2 30-minute: n 230; mean +0.010 [-0.182, +0.240]; median +0.000; SD 1.613; mean w/o best 1% -0.072; positive 20.9%
- +2 15-minute: n 230; mean -0.015 [-0.338, +0.387]; median -1.000; SD 2.896; mean w/o best 1% -0.214; positive 20.4%
- +2 5-minute: n 230; mean +0.275 [-0.284, +0.983]; median -1.000; SD 5.225; mean w/o best 1% -0.102; positive 13.9%
- +5 30-minute: n 230; mean -0.037 [-0.260, +0.207]; median -1.000; SD 1.794; mean w/o best 1% -0.123; positive 15.7%
- +5 15-minute: n 230; mean -0.091 [-0.373, +0.223]; median -1.000; SD 2.358; mean w/o best 1% -0.212; positive 15.2%
- +5 5-minute: n 230; mean +0.238 [-0.301, +0.897]; median -1.000; SD 4.782; mean w/o best 1% -0.085; positive 10.4%
- +10 30-minute: n 230; mean -0.132 [-0.373, +0.157]; median -1.000; SD 2.084; mean w/o best 1% -0.256; positive 11.3%
- +10 15-minute: n 230; mean -0.275 [-0.549, +0.029]; median -1.000; SD 2.203; mean w/o best 1% -0.383; positive 10.9%
- +10 5-minute: n 230; mean -0.096 [-0.561, +0.467]; median -1.000; SD 3.984; mean w/o best 1% -0.350; positive 7.4%

#### Volatility split (H3; daily ATR / price at the setup): R before costs per setup (missed 0R); deciding number
- ATR / price (primary)
    low +1 4-hour: n 71; mean -0.072 [-0.253, +0.134]; median -0.050; SD 0.772; mean w/o best 1% -0.111; positive 46.5% | worked stopped 0/31 = 0.0% [0.0, 11.0]
    low +1 30-minute: n 71; mean -0.120 [-0.391, +0.247]; median -0.277; SD 1.415; mean w/o best 1% -0.254; positive 19.7% | worked stopped 11/30 = 36.7% [21.9, 54.5]
    low +1 15-minute: n 71; mean +0.197 [-0.501, +1.375]; median -1.000; SD 4.321; mean w/o best 1% -0.293; positive 21.1% | worked stopped 16/31 = 51.6% [34.8, 68.0]
    low +1 5-minute: n 71; mean +0.614 [-0.563, +2.599]; median -1.000; SD 7.775; mean w/o best 1% -0.286; positive 18.3% | worked stopped 20/31 = 64.5% [46.9, 78.9]
    low +5 4-hour: n 71; mean -0.147 [-0.434, +0.197]; median -1.000; SD 1.368; mean w/o best 1% -0.235; positive 32.4% | worked stopped 2/31 = 6.5% [1.8, 20.7]
    low +5 30-minute: n 71; mean -0.445 [-0.746, -0.066]; median -1.000; SD 1.530; mean w/o best 1% -0.578; positive 9.9% | worked stopped 24/31 = 77.4% [60.2, 88.6]
    low +5 15-minute: n 71; mean -0.073 [-0.608, +0.624]; median -1.000; SD 2.746; mean w/o best 1% -0.307; positive 12.7% | worked stopped 22/31 = 71.0% [53.4, 83.9]
    low +5 5-minute: n 71; mean +0.032 [-0.762, +1.016]; median -1.000; SD 3.876; mean w/o best 1% -0.265; positive 8.5% | worked stopped 25/31 = 80.6% [63.7, 90.8]
    mid +1 4-hour: n 74; mean +0.014 [-0.158, +0.189]; median -0.123; SD 0.769; mean w/o best 1% -0.015; positive 41.9% | worked stopped 0/36 = 0.0% [0.0, 9.6]
    mid +1 30-minute: n 74; mean +0.182 [-0.164, +0.625]; median +0.000; SD 1.697; mean w/o best 1% +0.051; positive 35.1% | worked stopped 11/34 = 32.4% [19.1, 49.2]
    mid +1 15-minute: n 74; mean +0.037 [-0.304, +0.437]; median -1.000; SD 1.658; mean w/o best 1% -0.052; positive 29.7% | worked stopped 17/35 = 48.6% [33.0, 64.4]
    mid +1 5-minute: n 74; mean +0.715 [-0.253, +1.923]; median -1.000; SD 5.028; mean w/o best 1% +0.298; positive 18.9% | worked stopped 21/36 = 58.3% [42.2, 72.9]
    mid +5 4-hour: n 74; mean -0.093 [-0.328, +0.170]; median -0.498; SD 1.114; mean w/o best 1% -0.147; positive 40.5% | worked stopped 4/36 = 11.1% [4.4, 25.3]
    mid +5 30-minute: n 74; mean +0.136 [-0.344, +0.695]; median -1.000; SD 2.296; mean w/o best 1% -0.006; positive 23.0% | worked stopped 17/36 = 47.2% [32.0, 63.0]
    mid +5 15-minute: n 74; mean -0.215 [-0.597, +0.260]; median -1.000; SD 1.918; mean w/o best 1% -0.349; positive 14.9% | worked stopped 23/36 = 63.9% [47.6, 77.5]
    mid +5 5-minute: n 74; mean +0.767 [-0.324, +2.216]; median -1.000; SD 5.736; mean w/o best 1% +0.266; positive 13.5% | worked stopped 26/36 = 72.2% [56.0, 84.2]
    high +1 4-hour: n 85; mean -0.096 [-0.208, +0.016]; median -0.152; SD 0.536; mean w/o best 1% -0.114; positive 38.8% | worked stopped 0/35 = 0.0% [0.0, 9.9]
    high +1 30-minute: n 85; mean -0.078 [-0.258, +0.122]; median +0.000; SD 0.885; mean w/o best 1% -0.124; positive 31.8% | worked stopped 7/34 = 20.6% [10.3, 36.8]
    high +1 15-minute: n 85; mean -0.195 [-0.466, +0.126]; median -1.000; SD 1.442; mean w/o best 1% -0.281; positive 27.1% | worked stopped 14/35 = 40.0% [25.6, 56.4]
    high +1 5-minute: n 85; mean -0.321 [-0.706, +0.156]; median -1.000; SD 1.982; mean w/o best 1% -0.467; positive 18.8% | worked stopped 19/35 = 54.3% [38.2, 69.5]
    high +5 4-hour: n 85; mean -0.054 [-0.265, +0.196]; median -0.249; SD 1.099; mean w/o best 1% -0.100; positive 37.6% | worked stopped 1/35 = 2.9% [0.5, 14.5]
    high +5 30-minute: n 85; mean +0.300 [-0.316, +1.190]; median -1.000; SD 3.640; mean w/o best 1% -0.043; positive 21.2% | worked stopped 17/35 = 48.6% [33.0, 64.4]
    high +5 15-minute: n 85; mean -0.085 [-0.536, +0.474]; median -1.000; SD 2.393; mean w/o best 1% -0.217; positive 17.6% | worked stopped 21/35 = 60.0% [43.6, 74.4]
    high +5 5-minute: n 85; mean -0.052 [-0.821, +1.094]; median -1.000; SD 4.568; mean w/o best 1% -0.488; positive 9.4% | worked stopped 26/35 = 74.3% [57.9, 85.8]
- ATR in dollars (secondary)
    low +1 4-hour: n 81; mean +0.001 [-0.167, +0.168]; median -0.039; SD 0.779; mean w/o best 1% -0.033; positive 48.1% | worked stopped 0/41 = 0.0% [0.0, 8.6]
    low +1 30-minute: n 81; mean +0.038 [-0.261, +0.413]; median -0.085; SD 1.559; mean w/o best 1% -0.077; positive 25.9% | worked stopped 13/39 = 33.3% [20.6, 49.0]
    low +1 15-minute: n 81; mean +0.370 [-0.326, +1.401]; median -1.000; SD 4.187; mean w/o best 1% -0.056; positive 25.9% | worked stopped 21/41 = 51.2% [36.5, 65.7]
    low +1 5-minute: n 81; mean +0.959 [-0.355, +2.982]; median -1.000; SD 7.780; mean w/o best 1% +0.176; positive 19.8% | worked stopped 26/41 = 63.4% [48.1, 76.4]
    low +5 4-hour: n 81; mean -0.029 [-0.278, +0.247]; median -0.228; SD 1.191; mean w/o best 1% -0.104; positive 42.0% | worked stopped 1/41 = 2.4% [0.4, 12.6]
    low +5 30-minute: n 81; mean -0.008 [-0.430, +0.559]; median -1.000; SD 2.180; mean w/o best 1% -0.119; positive 17.3% | worked stopped 25/41 = 61.0% [45.7, 74.3]
    low +5 15-minute: n 81; mean +0.155 [-0.445, +0.856]; median -1.000; SD 2.901; mean w/o best 1% -0.047; positive 17.3% | worked stopped 27/41 = 65.9% [50.5, 78.4]
    low +5 5-minute: n 81; mean +0.416 [-0.414, +1.459]; median -1.000; SD 4.187; mean w/o best 1% +0.165; positive 12.3% | worked stopped 31/41 = 75.6% [60.7, 86.2]
    mid +1 4-hour: n 73; mean -0.040 [-0.205, +0.136]; median -0.152; SD 0.733; mean w/o best 1% -0.071; positive 38.4% | worked stopped 0/29 = 0.0% [0.0, 11.7]
    mid +1 30-minute: n 73; mean +0.019 [-0.287, +0.414]; median +0.000; SD 1.560; mean w/o best 1% -0.116; positive 30.1% | worked stopped 10/28 = 35.7% [20.7, 54.2]
    mid +1 15-minute: n 73; mean -0.249 [-0.506, +0.045]; median -1.000; SD 1.200; mean w/o best 1% -0.314; positive 23.3% | worked stopped 16/28 = 57.1% [39.1, 73.5]
    mid +1 5-minute: n 73; mean +0.071 [-0.644, +1.160]; median -1.000; SD 4.137; mean w/o best 1% -0.361; positive 13.7% | worked stopped 18/29 = 62.1% [44.0, 77.3]
    mid +5 4-hour: n 73; mean -0.087 [-0.366, +0.236]; median -0.612; SD 1.303; mean w/o best 1% -0.171; positive 35.6% | worked stopped 3/29 = 10.3% [3.6, 26.4]
    mid +5 30-minute: n 73; mean -0.186 [-0.583, +0.263]; median -1.000; SD 1.842; mean w/o best 1% -0.335; positive 17.8% | worked stopped 16/29 = 55.2% [37.5, 71.6]
    mid +5 15-minute: n 73; mean -0.399 [-0.731, +0.017]; median -1.000; SD 1.623; mean w/o best 1% -0.508; positive 11.0% | worked stopped 21/29 = 72.4% [54.3, 85.3]
    mid +5 5-minute: n 73; mean +0.326 [-0.669, +1.688]; median -1.000; SD 5.372; mean w/o best 1% -0.188; positive 11.0% | worked stopped 21/29 = 72.4% [54.3, 85.3]
    high +1 4-hour: n 76; mean -0.123 [-0.241, -0.008]; median -0.169; SD 0.536; mean w/o best 1% -0.143; positive 39.5% | worked stopped 0/32 = 0.0% [0.0, 10.7]
    high +1 30-minute: n 76; mean -0.082 [-0.255, +0.102]; median +0.000; SD 0.817; mean w/o best 1% -0.118; positive 31.6% | worked stopped 6/31 = 19.4% [9.2, 36.3]
    high +1 15-minute: n 76; mean -0.153 [-0.439, +0.201]; median -1.000; SD 1.481; mean w/o best 1% -0.249; positive 28.9% | worked stopped 10/32 = 31.2% [18.0, 48.6]
    high +1 5-minute: n 76; mean -0.180 [-0.613, +0.314]; median -1.000; SD 2.096; mean w/o best 1% -0.342; positive 22.4% | worked stopped 16/32 = 50.0% [33.6, 66.4]
    high +5 4-hour: n 76; mean -0.174 [-0.399, +0.082]; median -0.503; SD 1.077; mean w/o best 1% -0.227; positive 32.9% | worked stopped 3/32 = 9.4% [3.2, 24.2]
    high +5 30-minute: n 76; mean +0.240 [-0.443, +1.197]; median -1.000; SD 3.748; mean w/o best 1% -0.145; positive 19.7% | worked stopped 17/32 = 53.1% [36.4, 69.1]
    high +5 15-minute: n 76; mean -0.154 [-0.633, +0.376]; median -1.000; SD 2.319; mean w/o best 1% -0.303; positive 17.1% | worked stopped 18/32 = 56.2% [39.3, 71.8]
    high +5 5-minute: n 76; mean -0.038 [-0.891, +1.136]; median -1.000; SD 4.827; mean w/o best 1% -0.527; positive 7.9% | worked stopped 25/32 = 78.1% [61.2, 89.0]

## §4 daily setups (side result, no verdict): 67 setups

### long: 41 setups; Selected on the outcome: 29 worked
- daily: entered 41; missed {}
- 30-minute: entered 41; missed {}
- 15-minute: entered 41; missed {}
- 5-minute: entered 41; missed {}

#### R before costs, per trade (all setups)
- +1 daily: n 40; mean -0.009 [-0.074, +0.062]; median -0.046; SD 0.236; mean w/o best 1% -0.023; positive 42.5%; stopped 0
- +1 30-minute: n 36; mean -0.069 [-0.524, +0.512]; median -1.000; SD 1.535; mean w/o best 1% -0.242; positive 33.3%; stopped 19
- +1 15-minute: n 40; mean +0.122 [-0.620, +1.006]; median -1.000; SD 2.656; mean w/o best 1% -0.119; positive 25.0%; stopped 29
- +1 5-minute: n 40; mean +0.188 [-0.837, +1.592]; median -1.000; SD 3.796; mean w/o best 1% -0.218; positive 12.5%; stopped 35
- +2 daily: n 41; mean +0.055 [-0.042, +0.159]; median +0.042; SD 0.330; mean w/o best 1% +0.028; positive 51.2%; stopped 0
- +2 30-minute: n 40; mean +0.314 [-0.385, +1.185]; median -1.000; SD 2.647; mean w/o best 1% +0.021; positive 35.0%; stopped 22
- +2 15-minute: n 41; mean +0.358 [-0.675, +1.721]; median -1.000; SD 3.965; mean w/o best 1% -0.116; positive 24.4%; stopped 31
- +2 5-minute: n 41; mean +0.806 [-0.756, +2.947]; median -1.000; SD 6.410; mean w/o best 1% -0.032; positive 14.6%; stopped 35
- +5 daily: n 41; mean +0.131 [-0.026, +0.295]; median +0.046; SD 0.532; mean w/o best 1% +0.094; positive 53.7%; stopped 0
- +5 30-minute: n 41; mean +0.834 [-0.398, +2.439]; median -1.000; SD 4.782; mean w/o best 1% +0.324; positive 24.4%; stopped 30
- +5 15-minute: n 41; mean +0.799 [-0.613, +2.750]; median -1.000; SD 5.771; mean w/o best 1% +0.080; positive 17.1%; stopped 34
- +5 5-minute: n 41; mean +1.406 [-0.920, +4.372]; median -1.000; SD 8.865; mean w/o best 1% +0.382; positive 9.8%; stopped 37
- +10 daily: n 41; mean +0.195 [-0.044, +0.428]; median +0.051; SD 0.768; mean w/o best 1% +0.146; positive 53.7%; stopped 5
- +10 30-minute: n 41; mean +0.809 [-0.404, +2.324]; median -1.000; SD 4.797; mean w/o best 1% +0.260; positive 24.4%; stopped 31
- +10 15-minute: n 41; mean +0.560 [-0.593, +2.133]; median -1.000; SD 4.682; mean w/o best 1% +0.013; positive 14.6%; stopped 35
- +10 5-minute: n 41; mean +0.893 [-1.000, +3.195]; median -1.000; SD 7.074; mean w/o best 1% +0.107; positive 7.3%; stopped 38

#### R before costs, per setup (a missed entry counts 0R), and paired difference from the daily entry
- +1 daily: n 41; mean -0.009 [-0.077, +0.064]; median -0.043; SD 0.233; mean w/o best 1% -0.023; positive 41.5%
- +1 30-minute: n 41; mean -0.060 [-0.460, +0.405]; median -0.382; SD 1.436; mean w/o best 1% -0.212; positive 29.3% | paired vs daily (both traded, n 36): -0.081 [-0.477, +0.407]
- +1 15-minute: n 41; mean +0.119 [-0.588, +0.961]; median -1.000; SD 2.623; mean w/o best 1% -0.116; positive 24.4% | paired vs daily (both traded, n 40): +0.131 [-0.555, +0.965]
- +1 5-minute: n 41; mean +0.183 [-0.774, +1.472]; median -1.000; SD 3.749; mean w/o best 1% -0.213; positive 12.2% | paired vs daily (both traded, n 40): +0.197 [-0.736, +1.439]
- +2 daily: n 41; mean +0.055 [-0.043, +0.154]; median +0.042; SD 0.330; mean w/o best 1% +0.028; positive 51.2%
- +2 30-minute: n 41; mean +0.306 [-0.375, +1.137]; median -1.000; SD 2.614; mean w/o best 1% +0.020; positive 34.1% | paired vs daily (both traded, n 40): +0.250 [-0.399, +1.076]
- +2 15-minute: n 41; mean +0.358 [-0.646, +1.672]; median -1.000; SD 3.965; mean w/o best 1% -0.116; positive 24.4% | paired vs daily (both traded, n 41): +0.303 [-0.703, +1.620]
- +2 5-minute: n 41; mean +0.806 [-0.739, +3.068]; median -1.000; SD 6.410; mean w/o best 1% -0.032; positive 14.6% | paired vs daily (both traded, n 41): +0.751 [-0.763, +2.803]
- +5 daily: n 41; mean +0.131 [-0.024, +0.294]; median +0.046; SD 0.532; mean w/o best 1% +0.094; positive 53.7%
- +5 30-minute: n 41; mean +0.834 [-0.403, +2.497]; median -1.000; SD 4.782; mean w/o best 1% +0.324; positive 24.4% | paired vs daily (both traded, n 41): +0.703 [-0.488, +2.152]
- +5 15-minute: n 41; mean +0.799 [-0.637, +2.846]; median -1.000; SD 5.771; mean w/o best 1% +0.080; positive 17.1% | paired vs daily (both traded, n 41): +0.668 [-0.771, +2.551]
- +5 5-minute: n 41; mean +1.406 [-0.920, +4.291]; median -1.000; SD 8.865; mean w/o best 1% +0.382; positive 9.8% | paired vs daily (both traded, n 41): +1.276 [-1.014, +4.233]
- +10 daily: n 41; mean +0.195 [-0.031, +0.430]; median +0.051; SD 0.768; mean w/o best 1% +0.146; positive 53.7%
- +10 30-minute: n 41; mean +0.809 [-0.422, +2.477]; median -1.000; SD 4.797; mean w/o best 1% +0.260; positive 24.4% | paired vs daily (both traded, n 41): +0.614 [-0.526, +2.112]
- +10 15-minute: n 41; mean +0.560 [-0.711, +2.170]; median -1.000; SD 4.682; mean w/o best 1% +0.013; positive 14.6% | paired vs daily (both traded, n 41): +0.365 [-0.824, +1.869]
- +10 5-minute: n 41; mean +0.893 [-1.000, +3.451]; median -1.000; SD 7.074; mean w/o best 1% +0.107; positive 7.3% | paired vs daily (both traded, n 41): +0.698 [-1.135, +3.035]

#### The deciding number (Selected on the outcome): worked setups whose entry was stopped before the exit
- +1 daily: stopped 0/28 = 0.0% [0.0, 12.1]; after the stop the move ran (R of the stop hit) n 0
- +1 30-minute: stopped 11/26 = 42.3% [25.5, 61.1]; after the stop the move ran (R of the stop hit) n 11; p25 1.23, median 3.83, p75 8.58, p90 13.37
- +1 15-minute: stopped 17/28 = 60.7% [42.4, 76.4]; after the stop the move ran (R of the stop hit) n 17; p25 7.72, median 10.65, p75 14.37, p90 33.83
- +1 5-minute: stopped 23/28 = 82.1% [64.4, 92.1]; after the stop the move ran (R of the stop hit) n 23; p25 10.36, median 20.08, p75 40.57, p90 54.14
- +2 daily: stopped 0/29 = 0.0% [0.0, 11.7]; after the stop the move ran (R of the stop hit) n 0
- +2 30-minute: stopped 13/29 = 44.8% [28.4, 62.5]; after the stop the move ran (R of the stop hit) n 13; p25 1.98, median 5.06, p75 10.53, p90 13.37
- +2 15-minute: stopped 19/29 = 65.5% [47.3, 80.1]; after the stop the move ran (R of the stop hit) n 19; p25 7.72, median 10.69, p75 15.66, p90 33.83
- +2 5-minute: stopped 23/29 = 79.3% [61.6, 90.2]; after the stop the move ran (R of the stop hit) n 23; p25 10.36, median 20.08, p75 40.57, p90 54.14
- +5 daily: stopped 0/29 = 0.0% [0.0, 11.7]; after the stop the move ran (R of the stop hit) n 0
- +5 30-minute: stopped 18/29 = 62.1% [44.0, 77.3]; after the stop the move ran (R of the stop hit) n 18; p25 1.96, median 3.86, p75 8.58, p90 13.37
- +5 15-minute: stopped 22/29 = 75.9% [57.9, 87.8]; after the stop the move ran (R of the stop hit) n 22; p25 5.12, median 10.57, p75 14.37, p90 22.82
- +5 5-minute: stopped 25/29 = 86.2% [69.4, 94.5]; after the stop the move ran (R of the stop hit) n 25; p25 10.36, median 20.08, p75 40.57, p90 54.14
- +10 daily: stopped 2/29 = 6.9% [1.9, 22.0]; after the stop the move ran (R of the stop hit) n 2; p25 0.00, median 0.00, p75 0.00, p90 0.00
- +10 30-minute: stopped 19/29 = 65.5% [47.3, 80.1]; after the stop the move ran (R of the stop hit) n 19; p25 1.23, median 3.83, p75 8.58, p90 13.37
- +10 15-minute: stopped 23/29 = 79.3% [61.6, 90.2]; after the stop the move ran (R of the stop hit) n 23; p25 4.61, median 10.49, p75 14.37, p90 22.82
- +10 5-minute: stopped 26/29 = 89.7% [73.6, 96.4]; after the stop the move ran (R of the stop hit) n 26; p25 10.29, median 17.86, p75 40.57, p90 54.14

#### Adverse excursion to the exit (Selected on the outcome, worked setups): dollars; daily ATR
- +1 daily: $n 28; p25 5.68, median 11.79, p75 25.31, p90 40.53 | n 28; p25 0.225, median 0.340, p75 0.620, p90 1.567
- +1 30-minute: $n 26; p25 5.88, median 14.24, p75 33.29, p90 40.52 | n 26; p25 0.234, median 0.343, p75 0.645, p90 1.298
- +1 15-minute: $n 28; p25 6.70, median 10.89, p75 26.92, p90 34.24 | n 28; p25 0.162, median 0.343, p75 0.571, p90 1.041
- +1 5-minute: $n 28; p25 5.74, median 12.20, p75 26.54, p90 37.43 | n 28; p25 0.248, median 0.328, p75 0.597, p90 1.401
- +2 daily: $n 29; p25 4.58, median 14.32, p75 27.06, p90 45.59 | n 29; p25 0.174, median 0.311, p75 0.758, p90 1.629
- +2 30-minute: $n 29; p25 6.30, median 16.96, p75 33.29, p90 46.51 | n 29; p25 0.282, median 0.414, p75 0.806, p90 1.335
- +2 15-minute: $n 29; p25 6.70, median 14.19, p75 28.09, p90 37.79 | n 29; p25 0.162, median 0.351, p75 0.597, p90 1.103
- +2 5-minute: $n 29; p25 5.74, median 12.99, p75 26.54, p90 43.74 | n 29; p25 0.248, median 0.351, p75 0.610, p90 1.463
- +5 daily: $n 29; p25 5.68, median 14.57, p75 37.13, p90 90.50 | n 29; p25 0.246, median 0.620, p75 1.330, p90 2.006
- +5 30-minute: $n 29; p25 11.60, median 19.89, p75 36.58, p90 89.70 | n 29; p25 0.343, median 0.695, p75 1.091, p90 2.165
- +5 15-minute: $n 29; p25 10.21, median 17.15, p75 37.79, p90 84.12 | n 29; p25 0.356, median 0.597, p75 1.049, p90 2.165
- +5 5-minute: $n 29; p25 8.90, median 15.43, p75 37.43, p90 83.41 | n 29; p25 0.278, median 0.539, p75 1.211, p90 2.190
- +10 daily: $n 29; p25 11.80, median 22.06, p75 48.88, p90 128.78 | n 29; p25 0.298, median 0.658, p75 1.664, p90 3.112
- +10 30-minute: $n 29; p25 14.80, median 33.29, p75 54.82, p90 123.34 | n 29; p25 0.492, median 0.806, p75 1.643, p90 3.501
- +10 15-minute: $n 29; p25 13.91, median 28.53, p75 45.52, p90 123.34 | n 29; p25 0.408, median 0.721, p75 1.668, p90 2.977
- +10 5-minute: $n 29; p25 11.19, median 16.53, p75 49.13, p90 133.39 | n 29; p25 0.333, median 0.610, p75 1.687, p90 3.219

#### Stop sizes (all entries taken): dollars; daily ATR; share under 0.3 daily ATR
- daily: $n 41; p25 82.49, median 105.50, p75 195.56, p90 281.35 | n 41; p25 3.055, median 3.762, p75 4.829, p90 5.904 | under 0.3 ATR 0/41 = 0.0% [0.0, 8.6]
- 30-minute: $n 41; p25 9.41, median 11.93, p75 26.50, p90 35.93 | n 41; p25 0.294, median 0.398, p75 0.566, p90 1.057 | under 0.3 ATR 11/41 = 26.8% [15.7, 41.9]
- 15-minute: $n 41; p25 4.27, median 6.41, p75 8.86, p90 22.10 | n 41; p25 0.160, median 0.202, p75 0.278, p90 0.392 | under 0.3 ATR 32/41 = 78.0% [63.3, 88.0]
- 5-minute: $n 41; p25 2.14, median 2.83, p75 6.36, p90 12.48 | n 41; p25 0.088, median 0.117, p75 0.153, p90 0.225 | under 0.3 ATR 39/41 = 95.1% [83.9, 98.7]

#### Hindsight ratio (F2): share of trades with R before costs > 0, worked setups / all setups
- +1: daily 60.7% / 42.5% = 1.43; 30-minute 46.2% / 33.3% = 1.38; 15-minute 35.7% / 25.0% = 1.43; 5-minute 17.9% / 12.5% = 1.43
- +2: daily 65.5% / 51.2% = 1.28; 30-minute 48.3% / 35.0% = 1.38; 15-minute 34.5% / 24.4% = 1.41; 5-minute 20.7% / 14.6% = 1.41
- +5: daily 72.4% / 53.7% = 1.35; 30-minute 34.5% / 24.4% = 1.41; 15-minute 24.1% / 17.1% = 1.41; 5-minute 13.8% / 9.8% = 1.41
- +10: daily 72.4% / 53.7% = 1.35; 30-minute 34.5% / 24.4% = 1.41; 15-minute 20.7% / 14.6% = 1.41; 5-minute 10.3% / 7.3% = 1.41

#### By wait bucket (4-hour bars), R before costs per trade
- +1 30-minute: 1 n 5 mean -0.569; 2 n 6 mean -0.348; 3-6 n 21 mean +0.154; 7-12 n 4 mean -0.194
- +1 15-minute: 1 n 10 mean +0.367; 2 n 9 mean -0.764; 3-6 n 21 mean +0.385
- +1 5-minute: 1 n 28 mean +0.043; 2 n 10 mean +0.832; 3-6 n 2 mean -1.000
- +2 30-minute: 1 n 6 mean -0.414; 2 n 6 mean -0.252; 3-6 n 21 mean +0.464; 7-12 n 7 mean +0.973
- +2 15-minute: 1 n 11 mean +1.436; 2 n 9 mean -0.811; 3-6 n 21 mean +0.293
- +2 5-minute: 1 n 29 mean +0.737; 2 n 10 mean +1.366; 3-6 n 2 mean -1.000
- +5 30-minute: 1 n 6 mean -0.465; 2 n 6 mean -0.443; 3-6 n 21 mean +1.210; 7-12 n 7 mean +2.175; 13+ n 1 mean -1.000
- +5 15-minute: 1 n 11 mean +1.768; 2 n 9 mean -1.000; 3-6 n 21 mean +1.063
- +5 5-minute: 1 n 29 mean +0.906; 2 n 10 mean +3.339; 3-6 n 2 mean -1.000
- +10 30-minute: 1 n 6 mean -0.501; 2 n 6 mean +0.122; 3-6 n 21 mean +1.217; 7-12 n 7 mean +1.554; 13+ n 1 mean -1.000
- +10 15-minute: 1 n 11 mean +1.523; 2 n 9 mean -1.000; 3-6 n 21 mean +0.723
- +10 5-minute: 1 n 29 mean +0.527; 2 n 10 mean +2.332; 3-6 n 2 mean -1.000

#### Secondary: the 1-session cut (waits of 6 bars or fewer), R before costs per setup (missed 0R)
- +1 30-minute: n 41; mean -0.041 [-0.422, +0.450]; median -0.254; SD 1.425; mean w/o best 1% -0.193; positive 24.4%
- +1 15-minute: n 41; mean +0.119 [-0.542, +1.001]; median -1.000; SD 2.623; mean w/o best 1% -0.116; positive 24.4%
- +1 5-minute: n 41; mean +0.183 [-0.792, +1.399]; median -1.000; SD 3.749; mean w/o best 1% -0.213; positive 12.2%
- +2 30-minute: n 41; mean +0.140 [-0.418, +0.903]; median -0.015; SD 2.224; mean w/o best 1% -0.150; positive 29.3%
- +2 15-minute: n 41; mean +0.358 [-0.629, +1.625]; median -1.000; SD 3.965; mean w/o best 1% -0.116; positive 24.4%
- +2 5-minute: n 41; mean +0.806 [-0.737, +2.862]; median -1.000; SD 6.410; mean w/o best 1% -0.032; positive 14.6%
- +5 30-minute: n 41; mean +0.487 [-0.388, +1.581]; median -1.000; SD 3.449; mean w/o best 1% +0.072; positive 22.0%
- +5 15-minute: n 41; mean +0.799 [-0.653, +2.741]; median -1.000; SD 5.771; mean w/o best 1% +0.080; positive 17.1%
- +5 5-minute: n 41; mean +1.406 [-0.920, +4.358]; median -1.000; SD 8.865; mean w/o best 1% +0.382; positive 9.8%
- +10 30-minute: n 41; mean +0.568 [-0.409, +2.009]; median -1.000; SD 4.007; mean w/o best 1% +0.013; positive 22.0%
- +10 15-minute: n 41; mean +0.560 [-0.650, +2.143]; median -1.000; SD 4.682; mean w/o best 1% +0.013; positive 14.6%
- +10 5-minute: n 41; mean +0.893 [-1.000, +3.576]; median -1.000; SD 7.074; mean w/o best 1% +0.107; positive 7.3%

#### Volatility split (H3; daily ATR / price at the setup): R before costs per setup (missed 0R); deciding number
- ATR / price (primary)
    low +1 daily: n 16; mean +0.046 [-0.088, +0.184]; median +0.065; SD 0.284; mean w/o best 1% +0.011; positive 56.2% | worked stopped 0/13 = 0.0% [0.0, 22.8]
    low +1 30-minute: n 16; mean +0.675 [-0.099, +1.630]; median +0.230; SD 1.870; mean w/o best 1% +0.319; positive 62.5% | worked stopped 2/12 = 16.7% [4.7, 44.8]
    low +1 15-minute: n 16; mean +1.035 [-0.527, +2.798]; median -1.000; SD 3.516; mean w/o best 1% +0.468; positive 37.5% | worked stopped 7/13 = 53.8% [29.1, 76.8]
    low +1 5-minute: n 16; mean +1.758 [-0.455, +4.719]; median -1.000; SD 5.688; mean w/o best 1% +0.807; positive 25.0% | worked stopped 9/13 = 69.2% [42.4, 87.3]
    low +5 daily: n 16; mean +0.241 [-0.021, +0.516]; median +0.150; SD 0.571; mean w/o best 1% +0.150; positive 62.5% | worked stopped 0/13 = 0.0% [0.0, 22.8]
    low +5 30-minute: n 16; mean +1.647 [-0.556, +4.422]; median -1.000; SD 5.242; mean w/o best 1% +0.619; positive 37.5% | worked stopped 7/13 = 53.8% [29.1, 76.8]
    low +5 15-minute: n 16; mean +2.447 [-1.000, +6.885]; median -1.000; SD 8.780; mean w/o best 1% +0.638; positive 18.8% | worked stopped 10/13 = 76.9% [49.7, 91.8]
    low +5 5-minute: n 16; mean +3.851 [-1.000, +11.414]; median -1.000; SD 13.361; mean w/o best 1% +1.282; positive 12.5% | worked stopped 11/13 = 84.6% [57.8, 95.7]
    mid +1 daily: n 12; mean -0.020 [-0.119, +0.070]; median -0.051; SD 0.183; mean w/o best 1% -0.044; positive 41.7% | worked stopped 0/8 = 0.0% [0.0, 32.4]
    mid +1 30-minute: n 12; mean -0.562 [-1.000, +0.116]; median -1.000; SD 1.074; mean w/o best 1% -0.860; positive 8.3% | worked stopped 6/8 = 75.0% [40.9, 92.9]
    mid +1 15-minute: n 12; mean -0.201 [-1.000, +1.189]; median -1.000; SD 2.402; mean w/o best 1% -0.887; positive 16.7% | worked stopped 6/8 = 75.0% [40.9, 92.9]
    mid +1 5-minute: n 12; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 8/8 = 100.0% [67.6, 100.0]
    mid +5 daily: n 12; mean +0.097 [-0.133, +0.346]; median -0.003; SD 0.436; mean w/o best 1% +0.004; positive 50.0% | worked stopped 0/8 = 0.0% [0.0, 32.4]
    mid +5 30-minute: n 12; mean -0.484 [-1.000, +0.375]; median -1.000; SD 1.285; mean w/o best 1% -0.813; positive 16.7% | worked stopped 6/8 = 75.0% [40.9, 92.9]
    mid +5 15-minute: n 12; mean +0.119 [-1.000, +2.012]; median -1.000; SD 2.835; mean w/o best 1% -0.624; positive 16.7% | worked stopped 6/8 = 75.0% [40.9, 92.9]
    mid +5 5-minute: n 12; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 8/8 = 100.0% [67.6, 100.0]
    high +1 daily: n 13; mean -0.065 [-0.167, +0.042]; median -0.043; SD 0.203; mean w/o best 1% -0.102; positive 23.1% | worked stopped 0/7 = 0.0% [0.0, 35.4]
    high +1 30-minute: n 13; mean -0.502 [-0.754, -0.238]; median -0.423; SD 0.510; mean w/o best 1% -0.567; positive 7.7% | worked stopped 3/6 = 50.0% [18.8, 81.2]
    high +1 15-minute: n 13; mean -0.712 [-0.923, -0.463]; median -1.000; SD 0.467; mean w/o best 1% -0.780; positive 15.4% | worked stopped 4/7 = 57.1% [25.0, 84.2]
    high +1 5-minute: n 13; mean -0.662 [-1.000, -0.064]; median -1.000; SD 0.958; mean w/o best 1% -0.917; positive 7.7% | worked stopped 6/7 = 85.7% [48.7, 97.4]
    high +5 daily: n 13; mean +0.027 [-0.254, +0.339]; median -0.026; SD 0.576; mean w/o best 1% -0.089; positive 46.2% | worked stopped 0/8 = 0.0% [0.0, 32.4]
    high +5 30-minute: n 13; mean +1.049 [-1.000, +4.618]; median -1.000; SD 6.139; mean w/o best 1% -0.632; positive 15.4% | worked stopped 5/8 = 62.5% [30.6, 86.3]
    high +5 15-minute: n 13; mean -0.601 [-1.000, -0.064]; median -1.000; SD 1.035; mean w/o best 1% -0.855; positive 15.4% | worked stopped 6/8 = 75.0% [40.9, 92.9]
    high +5 5-minute: n 13; mean +0.619 [-1.000, +3.359]; median -1.000; SD 4.936; mean w/o best 1% -0.727; positive 15.4% | worked stopped 6/8 = 75.0% [40.9, 92.9]
- ATR in dollars (secondary)
    low +1 daily: n 12; mean -0.070 [-0.210, +0.071]; median -0.108; SD 0.258; mean w/o best 1% -0.110; positive 33.3% | worked stopped 0/9 = 0.0% [0.0, 29.9]
    low +1 30-minute: n 12; mean +0.070 [-0.655, +0.906]; median -0.638; SD 1.485; mean w/o best 1% -0.230; positive 41.7% | worked stopped 4/9 = 44.4% [18.9, 73.3]
    low +1 15-minute: n 12; mean +0.500 [-1.000, +2.411]; median -1.000; SD 3.213; mean w/o best 1% -0.321; positive 25.0% | worked stopped 6/9 = 66.7% [35.4, 87.9]
    low +1 5-minute: n 12; mean +0.265 [-1.000, +2.795]; median -1.000; SD 4.382; mean w/o best 1% -1.000; positive 8.3% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    low +5 daily: n 12; mean +0.119 [-0.140, +0.375]; median +0.055; SD 0.462; mean w/o best 1% +0.041; positive 58.3% | worked stopped 0/9 = 0.0% [0.0, 29.9]
    low +5 30-minute: n 12; mean +0.434 [-1.000, +2.910]; median -1.000; SD 3.740; mean w/o best 1% -0.573; positive 16.7% | worked stopped 7/9 = 77.8% [45.3, 93.7]
    low +5 15-minute: n 12; mean +1.548 [-1.000, +6.644]; median -1.000; SD 8.826; mean w/o best 1% -1.000; positive 8.3% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    low +5 5-minute: n 12; mean +2.616 [-1.000, +9.847]; median -1.000; SD 12.525; mean w/o best 1% -1.000; positive 8.3% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    mid +1 daily: n 15; mean +0.061 [-0.064, +0.180]; median +0.067; SD 0.250; mean w/o best 1% +0.025; positive 53.3% | worked stopped 0/10 = 0.0% [0.0, 27.8]
    mid +1 30-minute: n 15; mean +0.414 [-0.289, +1.416]; median +0.000; SD 1.819; mean w/o best 1% +0.015; positive 40.0% | worked stopped 1/8 = 12.5% [2.2, 47.1]
    mid +1 15-minute: n 15; mean +0.746 [-0.554, +2.510]; median -1.000; SD 3.147; mean w/o best 1% +0.153; positive 40.0% | worked stopped 4/10 = 40.0% [16.8, 68.7]
    mid +1 5-minute: n 15; mean +0.996 [-0.867, +3.642]; median -1.000; SD 4.765; mean w/o best 1% -0.077; positive 20.0% | worked stopped 7/10 = 70.0% [39.7, 89.2]
    mid +5 daily: n 15; mean +0.328 [+0.032, +0.652]; median +0.122; SD 0.636; mean w/o best 1% +0.236; positive 60.0% | worked stopped 0/11 = 0.0% [0.0, 25.9]
    mid +5 30-minute: n 15; mean +2.636 [-0.166, +6.328]; median -0.039; SD 6.886; mean w/o best 1% +1.308; positive 46.7% | worked stopped 3/11 = 27.3% [9.7, 56.6]
    mid +5 15-minute: n 15; mean +1.649 [-0.608, +4.551]; median -1.000; SD 5.430; mean w/o best 1% +0.432; positive 33.3% | worked stopped 6/11 = 54.5% [28.0, 78.7]
    mid +5 5-minute: n 15; mean +1.501 [-1.000, +6.283]; median -1.000; SD 8.819; mean w/o best 1% -0.766; positive 13.3% | worked stopped 9/11 = 81.8% [52.3, 94.9]
    high +1 daily: n 14; mean -0.030 [-0.124, +0.067]; median -0.039; SD 0.183; mean w/o best 1% -0.061; positive 35.7% | worked stopped 0/9 = 0.0% [0.0, 29.9]
    high +1 30-minute: n 14; mean -0.681 [-0.915, -0.428]; median -1.000; SD 0.474; mean w/o best 1% -0.754; positive 7.1% | worked stopped 6/9 = 66.7% [35.4, 87.9]
    high +1 15-minute: n 14; mean -0.879 [-1.000, -0.682]; median -1.000; SD 0.325; mean w/o best 1% -0.956; positive 7.1% | worked stopped 7/9 = 77.8% [45.3, 93.7]
    high +1 5-minute: n 14; mean -0.758 [-1.000, -0.274]; median -1.000; SD 0.906; mean w/o best 1% -1.000; positive 7.1% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    high +5 daily: n 14; mean -0.070 [-0.274, +0.119]; median -0.061; SD 0.406; mean w/o best 1% -0.115; positive 42.9% | worked stopped 0/9 = 0.0% [0.0, 29.9]
    high +5 30-minute: n 14; mean -0.754 [-1.000, -0.261]; median -1.000; SD 0.922; mean w/o best 1% -1.000; positive 7.1% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    high +5 15-minute: n 14; mean -0.754 [-1.000, -0.261]; median -1.000; SD 0.922; mean w/o best 1% -1.000; positive 7.1% | worked stopped 8/9 = 88.9% [56.5, 98.0]
    high +5 5-minute: n 14; mean +0.269 [-1.000, +2.808]; median -1.000; SD 4.749; mean w/o best 1% -1.000; positive 7.1% | worked stopped 8/9 = 88.9% [56.5, 98.0]

### short: 26 setups; Selected on the outcome: 13 worked
- daily: entered 26; missed {}
- 30-minute: entered 26; missed {}
- 15-minute: entered 26; missed {}
- 5-minute: entered 26; missed {}

#### R before costs, per trade (all setups)
- +1 daily: n 26; mean +0.048 [-0.056, +0.170]; median -0.014; SD 0.317; mean w/o best 1% +0.019; positive 42.3%; stopped 0
- +1 30-minute: n 23; mean +0.678 [-0.280, +1.919]; median -0.493; SD 2.752; mean w/o best 1% +0.237; positive 43.5%; stopped 11
- +1 15-minute: n 26; mean +0.886 [-0.353, +2.370]; median -1.000; SD 3.597; mean w/o best 1% +0.506; positive 26.9%; stopped 19
- +1 5-minute: n 26; mean +1.165 [-0.954, +4.124]; median -1.000; SD 6.706; mean w/o best 1% +0.142; positive 11.5%; stopped 22
- +2 daily: n 26; mean +0.042 [-0.092, +0.191]; median -0.018; SD 0.397; mean w/o best 1% -0.000; positive 46.2%; stopped 0
- +2 30-minute: n 24; mean +0.683 [-0.372, +1.961]; median -1.000; SD 2.966; mean w/o best 1% +0.268; positive 37.5%; stopped 13
- +2 15-minute: n 26; mean +0.892 [-0.455, +2.575]; median -1.000; SD 4.133; mean w/o best 1% +0.418; positive 23.1%; stopped 20
- +2 5-minute: n 26; mean +1.143 [-1.000, +4.348]; median -1.000; SD 7.282; mean w/o best 1% -0.154; positive 11.5%; stopped 23
- +5 daily: n 26; mean +0.037 [-0.145, +0.230]; median -0.078; SD 0.515; mean w/o best 1% -0.029; positive 46.2%; stopped 0
- +5 30-minute: n 26; mean +0.746 [-0.667, +2.709]; median -1.000; SD 4.629; mean w/o best 1% +0.020; positive 23.1%; stopped 20
- +5 15-minute: n 26; mean +1.531 [-0.513, +3.888]; median -1.000; SD 6.007; mean w/o best 1% +0.808; positive 19.2%; stopped 21
- +5 5-minute: n 26; mean +1.388 [-1.000, +4.865]; median -1.000; SD 7.890; mean w/o best 1% +0.015; positive 11.5%; stopped 23
- +10 daily: n 26; mean -0.063 [-0.250, +0.120]; median -0.126; SD 0.470; mean w/o best 1% -0.092; positive 42.3%; stopped 1
- +10 30-minute: n 26; mean +0.413 [-0.847, +2.272]; median -1.000; SD 4.222; mean w/o best 1% -0.333; positive 19.2%; stopped 21
- +10 15-minute: n 26; mean +1.069 [-0.557, +3.276]; median -1.000; SD 5.237; mean w/o best 1% +0.349; positive 19.2%; stopped 21
- +10 5-minute: n 26; mean +0.843 [-1.000, +2.885]; median -1.000; SD 5.223; mean w/o best 1% +0.223; positive 11.5%; stopped 23

#### R before costs, per setup (a missed entry counts 0R), and paired difference from the daily entry
- +1 daily: n 26; mean +0.048 [-0.067, +0.169]; median -0.014; SD 0.317; mean w/o best 1% +0.019; positive 42.3%
- +1 30-minute: n 26; mean +0.600 [-0.238, +1.662]; median -0.169; SD 2.591; mean w/o best 1% +0.209; positive 38.5% | paired vs daily (both traded, n 23): +0.606 [-0.271, +1.802]
- +1 15-minute: n 26; mean +0.886 [-0.354, +2.378]; median -1.000; SD 3.597; mean w/o best 1% +0.506; positive 26.9% | paired vs daily (both traded, n 26): +0.837 [-0.396, +2.164]
- +1 5-minute: n 26; mean +1.165 [-0.977, +4.174]; median -1.000; SD 6.706; mean w/o best 1% +0.142; positive 11.5% | paired vs daily (both traded, n 26): +1.117 [-0.950, +3.908]
- +2 daily: n 26; mean +0.042 [-0.096, +0.200]; median -0.018; SD 0.397; mean w/o best 1% -0.000; positive 46.2%
- +2 30-minute: n 26; mean +0.630 [-0.307, +1.815]; median -0.776; SD 2.851; mean w/o best 1% +0.247; positive 34.6% | paired vs daily (both traded, n 24): +0.617 [-0.325, +1.889]
- +2 15-minute: n 26; mean +0.892 [-0.470, +2.599]; median -1.000; SD 4.133; mean w/o best 1% +0.418; positive 23.1% | paired vs daily (both traded, n 26): +0.849 [-0.466, +2.463]
- +2 5-minute: n 26; mean +1.143 [-1.000, +4.348]; median -1.000; SD 7.282; mean w/o best 1% -0.154; positive 11.5% | paired vs daily (both traded, n 26): +1.101 [-0.935, +4.166]
- +5 daily: n 26; mean +0.037 [-0.141, +0.240]; median -0.078; SD 0.515; mean w/o best 1% -0.029; positive 46.2%
- +5 30-minute: n 26; mean +0.746 [-0.709, +2.756]; median -1.000; SD 4.629; mean w/o best 1% +0.020; positive 23.1% | paired vs daily (both traded, n 26): +0.708 [-0.554, +2.559]
- +5 15-minute: n 26; mean +1.531 [-0.513, +4.017]; median -1.000; SD 6.007; mean w/o best 1% +0.808; positive 19.2% | paired vs daily (both traded, n 26): +1.493 [-0.376, +3.710]
- +5 5-minute: n 26; mean +1.388 [-1.000, +4.974]; median -1.000; SD 7.890; mean w/o best 1% +0.015; positive 11.5% | paired vs daily (both traded, n 26): +1.351 [-0.931, +4.764]
- +10 daily: n 26; mean -0.063 [-0.249, +0.114]; median -0.126; SD 0.470; mean w/o best 1% -0.092; positive 42.3%
- +10 30-minute: n 26; mean +0.413 [-0.817, +2.379]; median -1.000; SD 4.222; mean w/o best 1% -0.333; positive 19.2% | paired vs daily (both traded, n 26): +0.476 [-0.665, +2.264]
- +10 15-minute: n 26; mean +1.069 [-0.684, +3.179]; median -1.000; SD 5.237; mean w/o best 1% +0.349; positive 19.2% | paired vs daily (both traded, n 26): +1.132 [-0.520, +3.235]
- +10 5-minute: n 26; mean +0.843 [-1.000, +3.039]; median -1.000; SD 5.223; mean w/o best 1% +0.223; positive 11.5% | paired vs daily (both traded, n 26): +0.906 [-0.843, +2.919]

#### The deciding number (Selected on the outcome): worked setups whose entry was stopped before the exit
- +1 daily: stopped 0/13 = 0.0% [0.0, 22.8]; after the stop the move ran (R of the stop hit) n 0
- +1 30-minute: stopped 4/13 = 30.8% [12.7, 57.6]; after the stop the move ran (R of the stop hit) n 4; p25 5.76, median 7.01, p75 9.40, p90 9.40
- +1 15-minute: stopped 7/13 = 53.8% [29.1, 76.8]; after the stop the move ran (R of the stop hit) n 7; p25 3.42, median 7.22, p75 9.40, p90 14.73
- +1 5-minute: stopped 9/13 = 69.2% [42.4, 87.3]; after the stop the move ran (R of the stop hit) n 9; p25 11.15, median 15.59, p75 27.14, p90 53.31
- +2 daily: stopped 0/13 = 0.0% [0.0, 22.8]; after the stop the move ran (R of the stop hit) n 0
- +2 30-minute: stopped 5/13 = 38.5% [17.7, 64.5]; after the stop the move ran (R of the stop hit) n 5; p25 5.76, median 6.15, p75 8.26, p90 9.40
- +2 15-minute: stopped 7/13 = 53.8% [29.1, 76.8]; after the stop the move ran (R of the stop hit) n 7; p25 3.42, median 7.22, p75 9.40, p90 14.73
- +2 5-minute: stopped 10/13 = 76.9% [49.7, 91.8]; after the stop the move ran (R of the stop hit) n 10; p25 7.53, median 14.32, p75 27.14, p90 53.31
- +5 daily: stopped 0/13 = 0.0% [0.0, 22.8]; after the stop the move ran (R of the stop hit) n 0
- +5 30-minute: stopped 7/13 = 53.8% [29.1, 76.8]; after the stop the move ran (R of the stop hit) n 7; p25 0.00, median 5.76, p75 8.26, p90 9.40
- +5 15-minute: stopped 8/13 = 61.5% [35.5, 82.3]; after the stop the move ran (R of the stop hit) n 8; p25 3.42, median 6.46, p75 9.40, p90 14.73
- +5 5-minute: stopped 10/13 = 76.9% [49.7, 91.8]; after the stop the move ran (R of the stop hit) n 10; p25 7.53, median 14.32, p75 27.14, p90 53.31
- +10 daily: stopped 0/13 = 0.0% [0.0, 22.8]; after the stop the move ran (R of the stop hit) n 0
- +10 30-minute: stopped 8/13 = 61.5% [35.5, 82.3]; after the stop the move ran (R of the stop hit) n 8; p25 0.00, median 4.25, p75 8.26, p90 9.40
- +10 15-minute: stopped 8/13 = 61.5% [35.5, 82.3]; after the stop the move ran (R of the stop hit) n 8; p25 3.42, median 6.46, p75 9.40, p90 14.73
- +10 5-minute: stopped 10/13 = 76.9% [49.7, 91.8]; after the stop the move ran (R of the stop hit) n 10; p25 7.53, median 14.32, p75 27.14, p90 53.31

#### Adverse excursion to the exit (Selected on the outcome, worked setups): dollars; daily ATR
- +1 daily: $n 13; p25 7.97, median 16.03, p75 25.56, p90 80.80 | n 13; p25 0.264, median 0.494, p75 0.707, p90 0.796
- +1 30-minute: $n 13; p25 4.80, median 8.44, p75 20.90, p90 39.55 | n 13; p25 0.115, median 0.396, p75 0.604, p90 0.891
- +1 15-minute: $n 13; p25 4.31, median 12.55, p75 19.79, p90 58.99 | n 13; p25 0.111, median 0.403, p75 0.610, p90 0.876
- +1 5-minute: $n 13; p25 3.99, median 12.34, p75 22.36, p90 49.62 | n 13; p25 0.210, median 0.302, p75 0.515, p90 0.835
- +2 daily: $n 13; p25 7.97, median 16.03, p75 35.84, p90 80.80 | n 13; p25 0.368, median 0.494, p75 0.707, p90 0.796
- +2 30-minute: $n 13; p25 4.80, median 8.44, p75 20.90, p90 56.39 | n 13; p25 0.115, median 0.396, p75 0.604, p90 0.891
- +2 15-minute: $n 13; p25 4.31, median 12.55, p75 19.79, p90 75.83 | n 13; p25 0.111, median 0.403, p75 0.752, p90 0.876
- +2 5-minute: $n 13; p25 3.99, median 12.34, p75 22.36, p90 49.62 | n 13; p25 0.210, median 0.302, p75 0.515, p90 0.835
- +5 daily: $n 13; p25 13.27, median 21.93, p75 48.81, p90 80.80 | n 13; p25 0.370, median 0.707, p75 0.941, p90 1.067
- +5 30-minute: $n 13; p25 6.02, median 23.12, p75 41.84, p90 56.39 | n 13; p25 0.158, median 0.583, p75 1.022, p90 1.280
- +5 15-minute: $n 13; p25 4.51, median 21.22, p75 41.84, p90 75.83 | n 13; p25 0.111, median 0.752, p75 0.966, p90 1.285
- +5 5-minute: $n 13; p25 3.99, median 22.36, p75 48.91, p90 49.62 | n 13; p25 0.220, median 0.506, p75 1.022, p90 1.181
- +10 daily: $n 13; p25 13.27, median 31.32, p75 54.73, p90 113.22 | n 13; p25 0.560, median 0.796, p75 1.084, p90 1.807
- +10 30-minute: $n 13; p25 8.44, median 27.47, p75 57.34, p90 119.34 | n 13; p25 0.280, median 0.778, p75 1.236, p90 2.860
- +10 15-minute: $n 13; p25 6.02, median 21.22, p75 57.34, p90 115.77 | n 13; p25 0.111, median 0.887, p75 1.128, p90 2.865
- +10 5-minute: $n 13; p25 3.99, median 26.24, p75 51.05, p90 115.09 | n 13; p25 0.238, median 0.701, p75 1.167, p90 2.758

#### Stop sizes (all entries taken): dollars; daily ATR; share under 0.3 daily ATR
- daily: $n 26; p25 83.61, median 120.30, p75 191.88, p90 338.86 | n 26; p25 3.110, median 3.758, p75 4.421, p90 4.909 | under 0.3 ATR 0/26 = 0.0% [0.0, 12.9]
- 30-minute: $n 26; p25 9.45, median 15.38, p75 30.94, p90 46.12 | n 26; p25 0.304, median 0.444, p75 0.801, p90 1.032 | under 0.3 ATR 6/26 = 23.1% [11.0, 42.1]
- 15-minute: $n 26; p25 3.95, median 9.68, p75 17.15, p90 33.27 | n 26; p25 0.135, median 0.268, p75 0.366, p90 0.500 | under 0.3 ATR 16/26 = 61.5% [42.5, 77.6]
- 5-minute: $n 26; p25 2.08, median 4.62, p75 8.97, p90 28.81 | n 26; p25 0.100, median 0.130, p75 0.203, p90 0.262 | under 0.3 ATR 24/26 = 92.3% [75.9, 97.9]

#### Hindsight ratio (F2): share of trades with R before costs > 0, worked setups / all setups
- +1: daily 76.9% / 42.3% = 1.82; 30-minute 61.5% / 43.5% = 1.42; 15-minute 46.2% / 26.9% = 1.71; 5-minute 23.1% / 11.5% = 2.00
- +2: daily 84.6% / 46.2% = 1.83; 30-minute 61.5% / 37.5% = 1.64; 15-minute 46.2% / 23.1% = 2.00; 5-minute 23.1% / 11.5% = 2.00
- +5: daily 84.6% / 46.2% = 1.83; 30-minute 46.2% / 23.1% = 2.00; 15-minute 38.5% / 19.2% = 2.00; 5-minute 23.1% / 11.5% = 2.00
- +10: daily 76.9% / 42.3% = 1.82; 30-minute 38.5% / 19.2% = 2.00; 15-minute 38.5% / 19.2% = 2.00; 5-minute 23.1% / 11.5% = 2.00

#### By wait bucket (4-hour bars), R before costs per trade
- +1 30-minute: 1 n 2 mean +0.022; 2 n 8 mean -0.024; 3-6 n 12 mean +0.448; 7-12 n 1 mean +10.375
- +1 15-minute: 1 n 4 mean -1.000; 2 n 7 mean +1.442; 3-6 n 14 mean +0.468; 7-12 n 1 mean +10.375
- +1 5-minute: 1 n 10 mean -1.000; 2 n 12 mean +3.691; 3-6 n 4 mean -1.000
- +2 30-minute: 1 n 2 mean +0.083; 2 n 8 mean +0.190; 3-6 n 12 mean +0.340; 7-12 n 1 mean +10.216; 13+ n 1 mean +0.396
- +2 15-minute: 1 n 4 mean -1.000; 2 n 7 mean +1.945; 3-6 n 14 mean +0.240; 7-12 n 1 mean +10.216
- +2 5-minute: 1 n 10 mean -1.000; 2 n 12 mean +3.643; 3-6 n 4 mean -1.000
- +5 30-minute: 1 n 2 mean -0.221; 2 n 8 mean +0.650; 3-6 n 12 mean -0.106; 7-12 n 1 mean +18.902; 13+ n 3 mean -1.000
- +5 15-minute: 1 n 4 mean -1.000; 2 n 7 mean +3.141; 3-6 n 14 mean +0.207; 7-12 n 1 mean +18.902
- +5 5-minute: 1 n 10 mean -1.000; 2 n 12 mean +4.174; 3-6 n 4 mean -1.000
- +10 30-minute: 1 n 2 mean -1.000; 2 n 8 mean -0.403; 3-6 n 12 mean -0.009; 7-12 n 1 mean +19.063; 13+ n 3 mean -1.000
- +10 15-minute: 1 n 4 mean -1.000; 2 n 7 mean +2.530; 3-6 n 14 mean -0.355; 7-12 n 1 mean +19.063
- +10 5-minute: 1 n 10 mean -1.000; 2 n 12 mean +2.993; 3-6 n 4 mean -1.000

#### Secondary: the 1-session cut (waits of 6 bars or fewer), R before costs per setup (missed 0R)
- +1 30-minute: n 26; mean +0.201 [-0.357, +0.848]; median -0.169; SD 1.655; mean w/o best 1% -0.001; positive 34.6%
- +1 15-minute: n 26; mean +0.486 [-0.517, +1.721]; median -1.000; SD 3.034; mean w/o best 1% +0.156; positive 23.1%
- +1 5-minute: n 26; mean +1.165 [-0.977, +3.885]; median -1.000; SD 6.706; mean w/o best 1% +0.142; positive 11.5%
- +2 30-minute: n 26; mean +0.222 [-0.471, +1.107]; median -0.776; SD 2.076; mean w/o best 1% -0.082; positive 26.9%
- +2 15-minute: n 26; mean +0.499 [-0.681, +2.010]; median -1.000; SD 3.670; mean w/o best 1% +0.009; positive 19.2%
- +2 5-minute: n 26; mean +1.143 [-1.000, +4.348]; median -1.000; SD 7.282; mean w/o best 1% -0.154; positive 11.5%
- +5 30-minute: n 26; mean +0.134 [-0.688, +1.332]; median -1.000; SD 2.753; mean w/o best 1% -0.349; positive 19.2%
- +5 15-minute: n 26; mean +0.804 [-0.678, +2.832]; median -1.000; SD 4.854; mean w/o best 1% +0.052; positive 15.4%
- +5 5-minute: n 26; mean +1.388 [-1.000, +4.861]; median -1.000; SD 7.890; mean w/o best 1% +0.015; positive 11.5%
- +10 30-minute: n 26; mean -0.205 [-0.769, +0.571]; median -1.000; SD 1.818; mean w/o best 1% -0.496; positive 15.4%
- +10 15-minute: n 26; mean +0.336 [-0.773, +1.912]; median -1.000; SD 3.736; mean w/o best 1% -0.301; positive 15.4%
- +10 5-minute: n 26; mean +0.843 [-1.000, +3.234]; median -1.000; SD 5.223; mean w/o best 1% +0.223; positive 11.5%

#### Volatility split (H3; daily ATR / price at the setup): R before costs per setup (missed 0R); deciding number
- ATR / price (primary)
    low +1 daily: n 7; mean +0.167 [-0.066, +0.431]; median +0.028; SD 0.370; mean w/o best 1% +0.068; positive 57.1% | worked stopped 0/3 = 0.0% [0.0, 56.2]
    low +1 30-minute: n 7; mean +0.508 [-0.614, +2.122]; median +0.000; SD 2.172; mean w/o best 1% -0.284; positive 42.9% | worked stopped 1/3 = 33.3% [6.1, 79.2]
    low +1 15-minute: n 7; mean +0.652 [-1.000, +3.440]; median -1.000; SD 3.637; mean w/o best 1% -0.698; positive 28.6% | worked stopped 1/3 = 33.3% [6.1, 79.2]
    low +1 5-minute: n 7; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 3/3 = 100.0% [43.8, 100.0]
    low +5 daily: n 7; mean +0.033 [-0.318, +0.618]; median -0.248; SD 0.750; mean w/o best 1% -0.244; positive 28.6% | worked stopped 0/3 = 0.0% [0.0, 56.2]
    low +5 30-minute: n 7; mean +0.886 [-1.000, +4.659]; median -1.000; SD 4.991; mean w/o best 1% -1.000; positive 14.3% | worked stopped 2/3 = 66.7% [20.8, 93.9]
    low +5 15-minute: n 7; mean +1.941 [-1.000, +7.823]; median -1.000; SD 7.781; mean w/o best 1% -1.000; positive 14.3% | worked stopped 2/3 = 66.7% [20.8, 93.9]
    low +5 5-minute: n 7; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 3/3 = 100.0% [43.8, 100.0]
    mid +1 daily: n 10; mean -0.059 [-0.222, +0.102]; median -0.120; SD 0.274; mean w/o best 1% -0.116; positive 30.0% | worked stopped 0/4 = 0.0% [0.0, 49.0]
    mid +1 30-minute: n 10; mean -0.167 [-0.862, +0.627]; median -1.000; SD 1.252; mean w/o best 1% -0.457; positive 30.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    mid +1 15-minute: n 10; mean +0.652 [-1.000, +2.419]; median -1.000; SD 2.777; mean w/o best 1% +0.021; positive 30.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    mid +1 5-minute: n 10; mean +1.795 [-1.000, +6.643]; median -1.000; SD 6.653; mean w/o best 1% -0.175; positive 20.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    mid +5 daily: n 10; mean -0.038 [-0.249, +0.157]; median +0.020; SD 0.353; mean w/o best 1% -0.082; positive 50.0% | worked stopped 0/4 = 0.0% [0.0, 49.0]
    mid +5 30-minute: n 10; mean -0.400 [-1.000, +0.407]; median -1.000; SD 1.341; mean w/o best 1% -0.771; positive 20.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    mid +5 15-minute: n 10; mean +0.266 [-1.000, +1.967]; median -1.000; SD 2.842; mean w/o best 1% -0.527; positive 20.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    mid +5 5-minute: n 10; mean +1.538 [-1.000, +4.926]; median -1.000; SD 5.705; mean w/o best 1% -0.056; positive 20.0% | worked stopped 2/4 = 50.0% [15.0, 85.0]
    high +1 daily: n 9; mean +0.074 [-0.097, +0.294]; median -0.008; SD 0.316; mean w/o best 1% -0.012; positive 44.4% | worked stopped 0/6 = 0.0% [0.0, 39.0]
    high +1 30-minute: n 9; mean +1.524 [-0.434, +4.112]; median +0.000; SD 3.738; mean w/o best 1% +0.417; positive 44.4% | worked stopped 1/6 = 16.7% [3.0, 56.4]
    high +1 15-minute: n 9; mean +1.326 [-1.000, +4.512]; median -1.000; SD 4.638; mean w/o best 1% +0.195; positive 22.2% | worked stopped 4/6 = 66.7% [30.0, 90.3]
    high +1 5-minute: n 9; mean +2.149 [-1.000, +8.312]; median -1.000; SD 9.222; mean w/o best 1% -0.924; positive 11.1% | worked stopped 4/6 = 66.7% [30.0, 90.3]
    high +5 daily: n 9; mean +0.124 [-0.174, +0.446]; median +0.089; SD 0.500; mean w/o best 1% +0.009; positive 55.6% | worked stopped 0/6 = 0.0% [0.0, 39.0]
    high +5 30-minute: n 9; mean +1.909 [-0.827, +6.332]; median -1.000; SD 6.564; mean w/o best 1% -0.215; positive 33.3% | worked stopped 3/6 = 50.0% [18.8, 81.2]
    high +5 15-minute: n 9; mean +2.617 [-1.000, +7.639]; median -1.000; SD 7.402; mean w/o best 1% +0.581; positive 22.2% | worked stopped 4/6 = 66.7% [30.0, 90.3]
    high +5 5-minute: n 9; mean +3.078 [-1.000, +11.235]; median -1.000; SD 12.235; mean w/o best 1% -1.000; positive 11.1% | worked stopped 5/6 = 83.3% [43.6, 97.0]
- ATR in dollars (secondary)
    low +1 daily: n 11; mean +0.143 [-0.040, +0.341]; median +0.028; SD 0.329; mean w/o best 1% +0.081; positive 54.5% | worked stopped 0/6 = 0.0% [0.0, 39.0]
    low +1 30-minute: n 11; mean +0.500 [-0.454, +1.596]; median +0.000; SD 1.939; mean w/o best 1% +0.025; positive 45.5% | worked stopped 2/6 = 33.3% [9.7, 70.0]
    low +1 15-minute: n 11; mean +1.188 [-0.671, +3.325]; median -1.000; SD 3.554; mean w/o best 1% +0.431; positive 36.4% | worked stopped 2/6 = 33.3% [9.7, 70.0]
    low +1 5-minute: n 11; mean +1.541 [-1.000, +5.948]; median -1.000; SD 6.367; mean w/o best 1% -0.257; positive 18.2% | worked stopped 4/6 = 66.7% [30.0, 90.3]
    low +5 daily: n 11; mean +0.086 [-0.188, +0.461]; median -0.096; SD 0.595; mean w/o best 1% -0.074; positive 45.5% | worked stopped 0/6 = 0.0% [0.0, 39.0]
    low +5 30-minute: n 11; mean +0.746 [-1.000, +3.318]; median -1.000; SD 4.007; mean w/o best 1% -0.400; positive 27.3% | worked stopped 3/6 = 50.0% [18.8, 81.2]
    low +5 15-minute: n 11; mean +2.022 [-1.000, +5.776]; median -1.000; SD 6.419; mean w/o best 1% +0.266; positive 27.3% | worked stopped 3/6 = 50.0% [18.8, 81.2]
    low +5 5-minute: n 11; mean +1.308 [-1.000, +4.387]; median -1.000; SD 5.466; mean w/o best 1% -0.151; positive 18.2% | worked stopped 4/6 = 66.7% [30.0, 90.3]
    mid +1 daily: n 5; mean -0.039 [-0.167, +0.086]; median -0.020; SD 0.164; mean w/o best 1% -0.079; positive 40.0% | worked stopped 0/2 = 0.0% [0.0, 65.8]
    mid +1 30-minute: n 5; mean -0.447 [-1.000, +0.105]; median -1.000; SD 0.757; mean w/o best 1% -0.655; positive 40.0% | worked stopped 1/2 = 50.0% [9.5, 90.5]
    mid +1 15-minute: n 5; mean -0.195 [-1.000, +1.414]; median -1.000; SD 1.799; mean w/o best 1% -1.000; positive 20.0% | worked stopped 2/2 = 100.0% [34.2, 100.0]
    mid +1 5-minute: n 5; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 2/2 = 100.0% [34.2, 100.0]
    mid +5 daily: n 5; mean +0.027 [-0.159, +0.202]; median +0.098; SD 0.243; mean w/o best 1% -0.042; positive 60.0% | worked stopped 0/2 = 0.0% [0.0, 65.8]
    mid +5 30-minute: n 5; mean -0.689 [-1.000, -0.066]; median -1.000; SD 0.696; mean w/o best 1% -1.000; positive 20.0% | worked stopped 1/2 = 50.0% [9.5, 90.5]
    mid +5 15-minute: n 5; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 2/2 = 100.0% [34.2, 100.0]
    mid +5 5-minute: n 5; mean -1.000 [-1.000, -1.000]; median -1.000; SD 0.000; mean w/o best 1% -1.000; positive 0.0% | worked stopped 2/2 = 100.0% [34.2, 100.0]
    high +1 daily: n 10; mean -0.013 [-0.223, +0.207]; median -0.119; SD 0.358; mean w/o best 1% -0.100; positive 30.0% | worked stopped 0/5 = 0.0% [0.0, 43.4]
    high +1 30-minute: n 10; mean +1.233 [-0.550, +3.634]; median -0.246; SD 3.626; mean w/o best 1% +0.217; positive 30.0% | worked stopped 1/5 = 20.0% [3.6, 62.4]
    high +1 15-minute: n 10; mean +1.093 [-1.000, +4.142]; median -1.000; SD 4.434; mean w/o best 1% +0.062; positive 20.0% | worked stopped 3/5 = 60.0% [23.1, 88.2]
    high +1 5-minute: n 10; mean +1.834 [-1.000, +7.381]; median -1.000; SD 8.751; mean w/o best 1% -0.933; positive 10.0% | worked stopped 3/5 = 60.0% [23.1, 88.2]
    high +5 daily: n 10; mean -0.011 [-0.307, +0.327]; median -0.221; SD 0.557; mean w/o best 1% -0.129; positive 40.0% | worked stopped 0/5 = 0.0% [0.0, 43.4]
    high +5 30-minute: n 10; mean +1.463 [-1.000, +5.443]; median -1.000; SD 6.305; mean w/o best 1% -0.475; positive 20.0% | worked stopped 3/5 = 60.0% [23.1, 88.2]
    high +5 15-minute: n 10; mean +2.255 [-1.000, +6.775]; median -1.000; SD 7.072; mean w/o best 1% +0.405; positive 20.0% | worked stopped 3/5 = 60.0% [23.1, 88.2]
    high +5 5-minute: n 10; mean +2.671 [-1.000, +10.012]; median -1.000; SD 11.608; mean w/o best 1% -1.000; positive 10.0% | worked stopped 4/5 = 80.0% [37.6, 96.4]

## §5 catalogue. DESCRIPTIVE, not tradeable. 2021-2026 only, a regime-specific description. Structures counted on history; none is a signal.
4-hour swing starts (Selected on the outcome): up 420, down 381; failed swings: up 246, down 281; base windows 8321

### M30: 63563 bars
- consolidation down: 842 (13.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 31/381 = 8.1% [5.8, 11.3]; failed (Selected on the outcome) 13/281 = 4.6% [2.7, 7.8]; base 1317/8321 = 15.8% [15.1, 16.6] -> OUTSIDE the base interval
    +1: n 830; mean -0.032 [-0.114, +0.060]; median -0.079; SD 0.965; mean w/o best 1% -0.066; positive 45.5% | drift baseline mean -0.058 (n 62234); minus baseline +0.026
    +2: n 832; mean -0.100 [-0.216, +0.022]; median -0.113; SD 1.257; mean w/o best 1% -0.139; positive 45.7% | drift baseline mean -0.108 (n 62185); minus baseline +0.008
    +5: n 828; mean -0.142 [-0.310, +0.035]; median -0.151; SD 1.884; mean w/o best 1% -0.208; positive 46.3% | drift baseline mean -0.253 (n 62229); minus baseline +0.111
    +10: n 821; mean -0.380 [-0.622, -0.147]; median -0.254; SD 2.580; mean w/o best 1% -0.450; positive 45.4% | drift baseline mean -0.507 (n 61817); minus baseline +0.127
- consolidation up: 990 (15.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 33/420 = 7.9% [5.6, 10.8]; failed (Selected on the outcome) 14/246 = 5.7% [3.4, 9.3]; base 1508/8321 = 18.1% [17.3, 19.0] -> OUTSIDE the base interval
    +1: n 971; mean +0.143 [+0.062, +0.225]; median +0.118; SD 0.957; mean w/o best 1% +0.114; positive 55.4% | drift baseline mean +0.058 (n 62234); minus baseline +0.085
    +2: n 971; mean +0.183 [+0.090, +0.281]; median +0.149; SD 1.150; mean w/o best 1% +0.144; positive 56.1% | drift baseline mean +0.108 (n 62185); minus baseline +0.075
    +5: n 971; mean +0.353 [+0.193, +0.530]; median +0.363; SD 1.883; mean w/o best 1% +0.287; positive 59.6% | drift baseline mean +0.253 (n 62229); minus baseline +0.100
    +10: n 964; mean +0.580 [+0.352, +0.805]; median +0.259; SD 2.569; mean w/o best 1% +0.497; positive 56.1% | drift baseline mean +0.507 (n 61817); minus baseline +0.073
- double bottom / top down: 709 (11.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 48/381 = 12.6% [9.6, 16.3]; failed (Selected on the outcome) 34/281 = 12.1% [8.8, 16.4]; base 1183/8321 = 14.2% [13.5, 15.0] -> OUTSIDE the base interval
    +1: n 695; mean -0.018 [-0.103, +0.066]; median -0.050; SD 0.927; mean w/o best 1% -0.046; positive 47.8% | drift baseline mean -0.058 (n 62234); minus baseline +0.040
    +2: n 699; mean -0.061 [-0.179, +0.057]; median -0.081; SD 1.252; mean w/o best 1% -0.102; positive 47.8% | drift baseline mean -0.108 (n 62185); minus baseline +0.047
    +5: n 696; mean -0.254 [-0.433, -0.076]; median -0.250; SD 1.855; mean w/o best 1% -0.316; positive 43.7% | drift baseline mean -0.253 (n 62229); minus baseline -0.001
    +10: n 692; mean -0.529 [-0.757, -0.302]; median -0.365; SD 2.477; mean w/o best 1% -0.594; positive 43.4% | drift baseline mean -0.507 (n 61817); minus baseline -0.022
- double bottom / top up: 797 (12.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 66/420 = 15.7% [12.5, 19.5]; failed (Selected on the outcome) 29/246 = 11.8% [8.3, 16.4]; base 1317/8321 = 15.8% [15.1, 16.6] -> inside the base interval
    +1: n 781; mean +0.106 [+0.031, +0.185]; median +0.071; SD 0.867; mean w/o best 1% +0.079; positive 54.4% | drift baseline mean +0.058 (n 62234); minus baseline +0.048
    +2: n 776; mean +0.152 [+0.046, +0.262]; median +0.138; SD 1.167; mean w/o best 1% +0.111; positive 56.4% | drift baseline mean +0.108 (n 62185); minus baseline +0.044
    +5: n 780; mean +0.396 [+0.236, +0.543]; median +0.353; SD 1.716; mean w/o best 1% +0.335; positive 59.1% | drift baseline mean +0.253 (n 62229); minus baseline +0.143
    +10: n 777; mean +0.643 [+0.394, +0.890]; median +0.401; SD 2.595; mean w/o best 1% +0.558; positive 58.0% | drift baseline mean +0.507 (n 61817); minus baseline +0.135
- engulfing down: 4191 (65.9 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 266/381 = 69.8% [65.0, 74.2]; failed (Selected on the outcome) 205/281 = 73.0% [67.5, 77.8]; base 5545/8321 = 66.6% [65.6, 67.6] -> OUTSIDE the base interval
    +1: n 4109; mean -0.048 [-0.101, +0.003]; median -0.058; SD 0.876; mean w/o best 1% -0.081; positive 46.8% | drift baseline mean -0.058 (n 62234); minus baseline +0.009
    +2: n 4102; mean -0.112 [-0.173, -0.048]; median -0.084; SD 1.109; mean w/o best 1% -0.151; positive 46.9% | drift baseline mean -0.108 (n 62185); minus baseline -0.003
    +5: n 4110; mean -0.232 [-0.332, -0.135]; median -0.192; SD 1.709; mean w/o best 1% -0.287; positive 45.0% | drift baseline mean -0.253 (n 62229); minus baseline +0.021
    +10: n 4083; mean -0.488 [-0.630, -0.350]; median -0.275; SD 2.395; mean w/o best 1% -0.554; positive 43.4% | drift baseline mean -0.507 (n 61817); minus baseline +0.019
- engulfing up: 4161 (65.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 275/420 = 65.5% [60.8, 69.9]; failed (Selected on the outcome) 170/246 = 69.1% [63.1, 74.5]; base 5520/8321 = 66.3% [65.3, 67.3] -> inside the base interval
    +1: n 4059; mean +0.056 [+0.001, +0.108]; median +0.056; SD 0.908; mean w/o best 1% +0.027; positive 53.0% | drift baseline mean +0.058 (n 62234); minus baseline -0.002
    +2: n 4053; mean +0.114 [+0.044, +0.186]; median +0.075; SD 1.157; mean w/o best 1% +0.076; positive 52.9% | drift baseline mean +0.108 (n 62185); minus baseline +0.006
    +5: n 4073; mean +0.272 [+0.166, +0.386]; median +0.252; SD 1.790; mean w/o best 1% +0.209; positive 55.8% | drift baseline mean +0.253 (n 62229); minus baseline +0.019
    +10: n 4037; mean +0.556 [+0.418, +0.705]; median +0.336; SD 2.507; mean w/o best 1% +0.479; positive 57.5% | drift baseline mean +0.507 (n 61817); minus baseline +0.048
- engulfing at a level down: 622 (9.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 42/381 = 11.0% [8.3, 14.6]; failed (Selected on the outcome) 36/281 = 12.8% [9.4, 17.2]; base 1125/8321 = 13.5% [12.8, 14.3] -> OUTSIDE the base interval
    +1: n 612; mean -0.034 [-0.118, +0.050]; median -0.090; SD 0.896; mean w/o best 1% -0.064; positive 46.1% | drift baseline mean -0.058 (n 62234); minus baseline +0.024
    +2: n 606; mean -0.134 [-0.236, -0.027]; median -0.104; SD 1.143; mean w/o best 1% -0.173; positive 45.2% | drift baseline mean -0.108 (n 62185); minus baseline -0.025
    +5: n 605; mean -0.298 [-0.456, -0.146]; median -0.318; SD 1.703; mean w/o best 1% -0.348; positive 42.3% | drift baseline mean -0.253 (n 62229); minus baseline -0.046
    +10: n 607; mean -0.545 [-0.777, -0.330]; median -0.420; SD 2.440; mean w/o best 1% -0.611; positive 41.0% | drift baseline mean -0.507 (n 61817); minus baseline -0.038
- engulfing at a level up: 531 (8.4 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 50/420 = 11.9% [9.1, 15.4]; failed (Selected on the outcome) 33/246 = 13.4% [9.7, 18.2]; base 957/8321 = 11.5% [10.8, 12.2] -> inside the base interval
    +1: n 521; mean +0.051 [-0.044, +0.145]; median +0.046; SD 0.928; mean w/o best 1% +0.020; positive 52.2% | drift baseline mean +0.058 (n 62234); minus baseline -0.007
    +2: n 518; mean +0.119 [-0.004, +0.241]; median +0.084; SD 1.189; mean w/o best 1% +0.076; positive 52.5% | drift baseline mean +0.108 (n 62185); minus baseline +0.010
    +5: n 522; mean +0.248 [+0.073, +0.432]; median +0.253; SD 1.815; mean w/o best 1% +0.185; positive 56.1% | drift baseline mean +0.253 (n 62229); minus baseline -0.005
    +10: n 519; mean +0.530 [+0.287, +0.779]; median +0.280; SD 2.534; mean w/o best 1% +0.451; positive 56.5% | drift baseline mean +0.507 (n 61817); minus baseline +0.023
- head and shoulders down: 102 (1.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 8/381 = 2.1% [1.1, 4.1]; failed (Selected on the outcome) 4/281 = 1.4% [0.6, 3.6]; base 197/8321 = 2.4% [2.1, 2.7] -> inside the base interval
    +1: n 100; mean -0.059 [-0.220, +0.114]; median -0.119; SD 0.840; mean w/o best 1% -0.089; positive 39.0% | drift baseline mean -0.058 (n 62234); minus baseline -0.001
    +2: n 99; mean -0.185 [-0.422, +0.069]; median -0.121; SD 1.217; mean w/o best 1% -0.227; positive 44.4% | drift baseline mean -0.108 (n 62185); minus baseline -0.076
    +5: n 99; mean -0.125 [-0.483, +0.236]; median -0.090; SD 1.708; mean w/o best 1% -0.168; positive 47.5% | drift baseline mean -0.253 (n 62229); minus baseline +0.128
    +10: n 97; mean -0.531 [-1.099, +0.009]; median -0.325; SD 2.438; mean w/o best 1% -0.581; positive 46.4% | drift baseline mean -0.507 (n 61817); minus baseline -0.024
- head and shoulders up: 117 (1.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 10/420 = 2.4% [1.3, 4.3]; failed (Selected on the outcome) 1/246 = 0.4% [0.1, 2.3]; base 221/8321 = 2.7% [2.3, 3.0] -> inside the base interval
    +1: n 115; mean +0.179 [-0.010, +0.374]; median +0.149; SD 0.990; mean w/o best 1% +0.154; positive 58.3% | drift baseline mean +0.058 (n 62234); minus baseline +0.121
    +2: n 115; mean +0.265 [+0.038, +0.486]; median +0.245; SD 1.165; mean w/o best 1% +0.234; positive 55.7% | drift baseline mean +0.108 (n 62185); minus baseline +0.156
    +5: n 116; mean +0.343 [-0.000, +0.697]; median +0.286; SD 1.853; mean w/o best 1% +0.292; positive 56.0% | drift baseline mean +0.253 (n 62229); minus baseline +0.090
    +10: n 115; mean +0.510 [+0.001, +1.006]; median +0.276; SD 2.524; mean w/o best 1% +0.445; positive 54.8% | drift baseline mean +0.507 (n 61817); minus baseline +0.002
- pin bar down: 1296 (20.4 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 124/381 = 32.5% [28.0, 37.4]; failed (Selected on the outcome) 83/281 = 29.5% [24.5, 35.1]; base 2170/8321 = 26.1% [25.1, 27.0] -> OUTSIDE the base interval
    +1: n 1267; mean -0.072 [-0.141, -0.007]; median -0.078; SD 0.904; mean w/o best 1% -0.104; positive 45.6% | drift baseline mean -0.058 (n 62234); minus baseline -0.015
    +2: n 1269; mean -0.114 [-0.200, -0.023]; median -0.113; SD 1.174; mean w/o best 1% -0.157; positive 44.4% | drift baseline mean -0.108 (n 62185); minus baseline -0.006
    +5: n 1271; mean -0.272 [-0.410, -0.135]; median -0.262; SD 1.758; mean w/o best 1% -0.330; positive 43.3% | drift baseline mean -0.253 (n 62229); minus baseline -0.019
    +10: n 1261; mean -0.536 [-0.734, -0.352]; median -0.195; SD 2.460; mean w/o best 1% -0.609; positive 45.4% | drift baseline mean -0.507 (n 61817); minus baseline -0.029
- pin bar up: 1560 (24.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 131/420 = 31.2% [26.9, 35.8]; failed (Selected on the outcome) 72/246 = 29.3% [23.9, 35.2]; base 2508/8321 = 30.1% [29.2, 31.1] -> OUTSIDE the base interval
    +1: n 1530; mean +0.023 [-0.042, +0.087]; median +0.022; SD 0.914; mean w/o best 1% -0.002; positive 51.2% | drift baseline mean +0.058 (n 62234); minus baseline -0.034
    +2: n 1528; mean +0.056 [-0.023, +0.140]; median +0.065; SD 1.164; mean w/o best 1% +0.023; positive 52.9% | drift baseline mean +0.108 (n 62185); minus baseline -0.052
    +5: n 1539; mean +0.181 [+0.056, +0.302]; median +0.179; SD 1.743; mean w/o best 1% +0.127; positive 54.1% | drift baseline mean +0.253 (n 62229); minus baseline -0.072
    +10: n 1523; mean +0.411 [+0.223, +0.600]; median +0.260; SD 2.549; mean w/o best 1% +0.336; positive 55.6% | drift baseline mean +0.507 (n 61817); minus baseline -0.096
- pin bar at a level down: 230 (3.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 19/381 = 5.0% [3.2, 7.7]; failed (Selected on the outcome) 9/281 = 3.2% [1.7, 6.0]; base 435/8321 = 5.2% [4.8, 5.7] -> inside the base interval
    +1: n 223; mean -0.067 [-0.191, +0.061]; median -0.080; SD 0.886; mean w/o best 1% -0.095; positive 44.8% | drift baseline mean -0.058 (n 62234); minus baseline -0.010
    +2: n 226; mean -0.047 [-0.206, +0.114]; median -0.098; SD 1.131; mean w/o best 1% -0.086; positive 46.0% | drift baseline mean -0.108 (n 62185); minus baseline +0.062
    +5: n 226; mean -0.215 [-0.441, -0.005]; median -0.307; SD 1.531; mean w/o best 1% -0.253; positive 41.6% | drift baseline mean -0.253 (n 62229); minus baseline +0.037
    +10: n 224; mean -0.298 [-0.603, -0.010]; median +0.118; SD 2.110; mean w/o best 1% -0.343; positive 51.8% | drift baseline mean -0.507 (n 61817); minus baseline +0.209
- pin bar at a level up: 235 (3.7 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 20/420 = 4.8% [3.1, 7.2]; failed (Selected on the outcome) 14/246 = 5.7% [3.4, 9.3]; base 447/8321 = 5.4% [4.9, 5.9] -> OUTSIDE the base interval
    +1: n 230; mean -0.009 [-0.144, +0.124]; median +0.074; SD 0.917; mean w/o best 1% -0.030; positive 52.6% | drift baseline mean +0.058 (n 62234); minus baseline -0.067
    +2: n 230; mean +0.053 [-0.103, +0.208]; median +0.036; SD 1.106; mean w/o best 1% +0.028; positive 51.7% | drift baseline mean +0.108 (n 62185); minus baseline -0.055
    +5: n 228; mean +0.183 [-0.053, +0.412]; median +0.228; SD 1.625; mean w/o best 1% +0.137; positive 54.4% | drift baseline mean +0.253 (n 62229); minus baseline -0.070
    +10: n 225; mean +0.332 [-0.011, +0.673]; median +0.203; SD 2.333; mean w/o best 1% +0.261; positive 56.9% | drift baseline mean +0.507 (n 61817); minus baseline -0.175
- retest failed down: 731 (11.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 62/381 = 16.3% [12.9, 20.3]; failed (Selected on the outcome) 46/281 = 16.4% [12.5, 21.1]; base 1382/8321 = 16.6% [15.8, 17.4] -> inside the base interval
    +1: n 716; mean -0.003 [-0.080, +0.077]; median -0.005; SD 0.928; mean w/o best 1% -0.034; positive 49.6% | drift baseline mean -0.058 (n 62234); minus baseline +0.055
    +2: n 719; mean -0.059 [-0.165, +0.045]; median -0.047; SD 1.210; mean w/o best 1% -0.099; positive 47.8% | drift baseline mean -0.108 (n 62185); minus baseline +0.049
    +5: n 717; mean -0.105 [-0.267, +0.051]; median -0.140; SD 1.824; mean w/o best 1% -0.169; positive 47.3% | drift baseline mean -0.253 (n 62229); minus baseline +0.148
    +10: n 712; mean -0.258 [-0.482, -0.044]; median -0.090; SD 2.466; mean w/o best 1% -0.338; positive 47.9% | drift baseline mean -0.507 (n 61817); minus baseline +0.249
- retest failed up: 758 (11.9 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 70/420 = 16.7% [13.4, 20.5]; failed (Selected on the outcome) 30/246 = 12.2% [8.7, 16.9]; base 1443/8321 = 17.3% [16.5, 18.2] -> inside the base interval
    +1: n 739; mean +0.080 [-0.003, +0.160]; median +0.056; SD 0.975; mean w/o best 1% +0.051; positive 53.6% | drift baseline mean +0.058 (n 62234); minus baseline +0.022
    +2: n 740; mean +0.164 [+0.071, +0.265]; median +0.088; SD 1.193; mean w/o best 1% +0.128; positive 53.2% | drift baseline mean +0.108 (n 62185); minus baseline +0.055
    +5: n 741; mean +0.329 [+0.167, +0.492]; median +0.260; SD 1.859; mean w/o best 1% +0.268; positive 57.1% | drift baseline mean +0.253 (n 62229); minus baseline +0.076
    +10: n 741; mean +0.654 [+0.425, +0.879]; median +0.347; SD 2.610; mean w/o best 1% +0.580; positive 57.5% | drift baseline mean +0.507 (n 61817); minus baseline +0.147
- retest held down: 732 (11.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 56/381 = 14.7% [11.5, 18.6]; failed (Selected on the outcome) 36/281 = 12.8% [9.4, 17.2]; base 1373/8321 = 16.5% [15.7, 17.3] -> OUTSIDE the base interval
    +1: n 716; mean -0.078 [-0.151, -0.008]; median -0.109; SD 0.840; mean w/o best 1% -0.103; positive 44.0% | drift baseline mean -0.058 (n 62234); minus baseline -0.020
    +2: n 719; mean -0.150 [-0.237, -0.060]; median -0.114; SD 1.040; mean w/o best 1% -0.178; positive 44.6% | drift baseline mean -0.108 (n 62185); minus baseline -0.042
    +5: n 718; mean -0.255 [-0.402, -0.110]; median -0.228; SD 1.681; mean w/o best 1% -0.303; positive 44.8% | drift baseline mean -0.253 (n 62229); minus baseline -0.002
    +10: n 709; mean -0.594 [-0.790, -0.393]; median -0.375; SD 2.326; mean w/o best 1% -0.656; positive 41.0% | drift baseline mean -0.507 (n 61817); minus baseline -0.087
- retest held up: 838 (13.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 63/420 = 15.0% [11.9, 18.7]; failed (Selected on the outcome) 41/246 = 16.7% [12.5, 21.8]; base 1586/8321 = 19.1% [18.2, 19.9] -> OUTSIDE the base interval
    +1: n 820; mean +0.047 [-0.022, +0.111]; median +0.029; SD 0.859; mean w/o best 1% +0.020; positive 51.3% | drift baseline mean +0.058 (n 62234); minus baseline -0.011
    +2: n 817; mean +0.103 [+0.015, +0.190]; median +0.067; SD 1.070; mean w/o best 1% +0.068; positive 52.8% | drift baseline mean +0.108 (n 62185); minus baseline -0.005
    +5: n 820; mean +0.220 [+0.097, +0.355]; median +0.182; SD 1.667; mean w/o best 1% +0.165; positive 54.9% | drift baseline mean +0.253 (n 62229); minus baseline -0.033
    +10: n 810; mean +0.451 [+0.246, +0.650]; median +0.229; SD 2.457; mean w/o best 1% +0.376; positive 55.7% | drift baseline mean +0.507 (n 61817); minus baseline -0.056

### M15: 127112 bars
- consolidation down: 1408 (11.1 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 96/381 = 25.2% [21.1, 29.8]; failed (Selected on the outcome) 60/281 = 21.4% [17.0, 26.5]; base 2184/8321 = 26.2% [25.3, 27.2] -> OUTSIDE the base interval
    +1: n 1384; mean -0.022 [-0.085, +0.040]; median -0.053; SD 0.884; mean w/o best 1% -0.055; positive 47.0% | drift baseline mean -0.057 (n 124463); minus baseline +0.035
    +2: n 1385; mean -0.079 [-0.159, -0.000]; median -0.073; SD 1.137; mean w/o best 1% -0.121; positive 46.9% | drift baseline mean -0.108 (n 124354); minus baseline +0.029
    +5: n 1378; mean -0.146 [-0.269, -0.016]; median -0.212; SD 1.685; mean w/o best 1% -0.203; positive 45.2% | drift baseline mean -0.252 (n 124449); minus baseline +0.107
    +10: n 1372; mean -0.389 [-0.562, -0.219]; median -0.265; SD 2.344; mean w/o best 1% -0.456; positive 43.9% | drift baseline mean -0.507 (n 123623); minus baseline +0.118
- consolidation up: 1676 (13.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 113/420 = 26.9% [22.9, 31.3]; failed (Selected on the outcome) 67/246 = 27.2% [22.1, 33.1]; base 2473/8321 = 29.7% [28.7, 30.7] -> OUTSIDE the base interval
    +1: n 1638; mean +0.071 [-0.001, +0.139]; median +0.076; SD 0.962; mean w/o best 1% +0.042; positive 53.5% | drift baseline mean +0.057 (n 124463); minus baseline +0.014
    +2: n 1631; mean +0.134 [+0.049, +0.219]; median +0.106; SD 1.181; mean w/o best 1% +0.098; positive 54.6% | drift baseline mean +0.108 (n 124354); minus baseline +0.026
    +5: n 1635; mean +0.318 [+0.168, +0.458]; median +0.270; SD 1.853; mean w/o best 1% +0.257; positive 57.7% | drift baseline mean +0.252 (n 124449); minus baseline +0.066
    +10: n 1628; mean +0.554 [+0.355, +0.747]; median +0.286; SD 2.556; mean w/o best 1% +0.476; positive 57.0% | drift baseline mean +0.507 (n 123623); minus baseline +0.047
- double bottom / top down: 1553 (12.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 91/381 = 23.9% [19.9, 28.4]; failed (Selected on the outcome) 59/281 = 21.0% [16.6, 26.1]; base 2339/8321 = 28.1% [27.2, 29.1] -> OUTSIDE the base interval
    +1: n 1520; mean -0.014 [-0.078, +0.053]; median -0.045; SD 0.883; mean w/o best 1% -0.044; positive 47.0% | drift baseline mean -0.057 (n 124463); minus baseline +0.043
    +2: n 1523; mean -0.050 [-0.140, +0.042]; median -0.065; SD 1.180; mean w/o best 1% -0.090; positive 47.5% | drift baseline mean -0.108 (n 124354); minus baseline +0.058
    +5: n 1524; mean -0.137 [-0.266, -0.014]; median -0.177; SD 1.697; mean w/o best 1% -0.188; positive 45.4% | drift baseline mean -0.252 (n 124449); minus baseline +0.115
    +10: n 1514; mean -0.414 [-0.595, -0.234]; median -0.240; SD 2.411; mean w/o best 1% -0.484; positive 44.6% | drift baseline mean -0.507 (n 123623); minus baseline +0.093
- double bottom / top up: 1538 (12.1 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 87/420 = 20.7% [17.1, 24.8]; failed (Selected on the outcome) 54/246 = 22.0% [17.2, 27.5]; base 2391/8321 = 28.7% [27.8, 29.7] -> OUTSIDE the base interval
    +1: n 1501; mean +0.073 [+0.011, +0.139]; median +0.069; SD 0.873; mean w/o best 1% +0.045; positive 54.6% | drift baseline mean +0.057 (n 124463); minus baseline +0.016
    +2: n 1497; mean +0.113 [+0.033, +0.190]; median +0.131; SD 1.101; mean w/o best 1% +0.078; positive 54.9% | drift baseline mean +0.108 (n 124354); minus baseline +0.005
    +5: n 1499; mean +0.307 [+0.187, +0.431]; median +0.254; SD 1.711; mean w/o best 1% +0.246; positive 56.9% | drift baseline mean +0.252 (n 124449); minus baseline +0.055
    +10: n 1495; mean +0.468 [+0.293, +0.659]; median +0.239; SD 2.476; mean w/o best 1% +0.390; positive 55.3% | drift baseline mean +0.507 (n 123623); minus baseline -0.039
- engulfing down: 8183 (64.4 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 349/381 = 91.6% [88.4, 94.0]; failed (Selected on the outcome) 247/281 = 87.9% [83.6, 91.2]; base 7355/8321 = 88.4% [87.7, 89.1] -> OUTSIDE the base interval
    +1: n 8008; mean -0.039 [-0.090, +0.008]; median -0.051; SD 0.897; mean w/o best 1% -0.074; positive 47.3% | drift baseline mean -0.057 (n 124463); minus baseline +0.018
    +2: n 8001; mean -0.096 [-0.164, -0.029]; median -0.082; SD 1.169; mean w/o best 1% -0.140; positive 46.7% | drift baseline mean -0.108 (n 124354); minus baseline +0.012
    +5: n 8020; mean -0.233 [-0.329, -0.140]; median -0.228; SD 1.743; mean w/o best 1% -0.289; positive 44.5% | drift baseline mean -0.252 (n 124449); minus baseline +0.019
    +10: n 7965; mean -0.480 [-0.612, -0.345]; median -0.270; SD 2.452; mean w/o best 1% -0.552; positive 43.7% | drift baseline mean -0.507 (n 123623); minus baseline +0.027
- engulfing up: 8480 (66.7 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 367/420 = 87.4% [83.9, 90.2]; failed (Selected on the outcome) 227/246 = 92.3% [88.3, 95.0]; base 7402/8321 = 89.0% [88.3, 89.6] -> OUTSIDE the base interval
    +1: n 8289; mean +0.069 [+0.023, +0.116]; median +0.065; SD 0.896; mean w/o best 1% +0.041; positive 53.7% | drift baseline mean +0.057 (n 124463); minus baseline +0.012
    +2: n 8287; mean +0.123 [+0.059, +0.187]; median +0.098; SD 1.146; mean w/o best 1% +0.086; positive 54.1% | drift baseline mean +0.108 (n 124354); minus baseline +0.015
    +5: n 8295; mean +0.273 [+0.171, +0.377]; median +0.229; SD 1.781; mean w/o best 1% +0.211; positive 55.9% | drift baseline mean +0.252 (n 124449); minus baseline +0.021
    +10: n 8245; mean +0.530 [+0.383, +0.672]; median +0.317; SD 2.509; mean w/o best 1% +0.452; positive 57.1% | drift baseline mean +0.507 (n 123623); minus baseline +0.023
- engulfing at a level down: 1205 (9.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 77/381 = 20.2% [16.5, 24.5]; failed (Selected on the outcome) 61/281 = 21.7% [17.3, 26.9]; base 2045/8321 = 24.6% [23.7, 25.5] -> OUTSIDE the base interval
    +1: n 1173; mean -0.050 [-0.124, +0.028]; median -0.060; SD 0.937; mean w/o best 1% -0.088; positive 46.6% | drift baseline mean -0.057 (n 124463); minus baseline +0.008
    +2: n 1176; mean -0.111 [-0.208, -0.012]; median -0.078; SD 1.221; mean w/o best 1% -0.163; positive 46.4% | drift baseline mean -0.108 (n 124354); minus baseline -0.003
    +5: n 1175; mean -0.261 [-0.401, -0.121]; median -0.216; SD 1.750; mean w/o best 1% -0.317; positive 44.9% | drift baseline mean -0.252 (n 124449); minus baseline -0.009
    +10: n 1169; mean -0.499 [-0.697, -0.307]; median -0.252; SD 2.495; mean w/o best 1% -0.570; positive 44.9% | drift baseline mean -0.507 (n 123623); minus baseline +0.008
- engulfing at a level up: 1111 (8.7 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 70/420 = 16.7% [13.4, 20.5]; failed (Selected on the outcome) 45/246 = 18.3% [14.0, 23.6]; base 1877/8321 = 22.6% [21.7, 23.5] -> OUTSIDE the base interval
    +1: n 1092; mean +0.011 [-0.062, +0.082]; median +0.031; SD 0.921; mean w/o best 1% -0.016; positive 51.6% | drift baseline mean +0.057 (n 124463); minus baseline -0.046
    +2: n 1091; mean +0.075 [-0.014, +0.169]; median +0.082; SD 1.135; mean w/o best 1% +0.038; positive 53.3% | drift baseline mean +0.108 (n 124354); minus baseline -0.033
    +5: n 1094; mean +0.257 [+0.109, +0.398]; median +0.200; SD 1.766; mean w/o best 1% +0.197; positive 54.7% | drift baseline mean +0.252 (n 124449); minus baseline +0.005
    +10: n 1081; mean +0.471 [+0.263, +0.679]; median +0.259; SD 2.530; mean w/o best 1% +0.390; positive 55.8% | drift baseline mean +0.507 (n 123623); minus baseline -0.036
- head and shoulders down: 204 (1.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 25/381 = 6.6% [4.5, 9.5]; failed (Selected on the outcome) 14/281 = 5.0% [3.0, 8.2]; base 391/8321 = 4.7% [4.3, 5.2] -> OUTSIDE the base interval
    +1: n 202; mean -0.053 [-0.169, +0.061]; median -0.071; SD 0.788; mean w/o best 1% -0.076; positive 46.5% | drift baseline mean -0.057 (n 124463); minus baseline +0.004
    +2: n 202; mean -0.137 [-0.300, +0.015]; median -0.124; SD 1.066; mean w/o best 1% -0.170; positive 44.6% | drift baseline mean -0.108 (n 124354); minus baseline -0.029
    +5: n 197; mean -0.222 [-0.485, +0.038]; median -0.219; SD 1.720; mean w/o best 1% -0.287; positive 44.2% | drift baseline mean -0.252 (n 124449); minus baseline +0.031
    +10: n 199; mean -0.560 [-0.937, -0.150]; median -0.424; SD 2.480; mean w/o best 1% -0.639; positive 39.7% | drift baseline mean -0.507 (n 123623); minus baseline -0.053
- head and shoulders up: 223 (1.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 20/420 = 4.8% [3.1, 7.2]; failed (Selected on the outcome) 7/246 = 2.8% [1.4, 5.8]; base 429/8321 = 5.2% [4.7, 5.7] -> inside the base interval
    +1: n 216; mean +0.155 [+0.018, +0.293]; median +0.043; SD 0.917; mean w/o best 1% +0.124; positive 53.2% | drift baseline mean +0.057 (n 124463); minus baseline +0.097
    +2: n 216; mean +0.208 [+0.038, +0.379]; median +0.094; SD 1.185; mean w/o best 1% +0.171; positive 51.9% | drift baseline mean +0.108 (n 124354); minus baseline +0.100
    +5: n 217; mean +0.353 [+0.086, +0.609]; median +0.365; SD 1.759; mean w/o best 1% +0.307; positive 57.6% | drift baseline mean +0.252 (n 124449); minus baseline +0.101
    +10: n 216; mean +0.665 [+0.334, +1.011]; median +0.552; SD 2.453; mean w/o best 1% +0.590; positive 59.3% | drift baseline mean +0.507 (n 123623); minus baseline +0.158
- pin bar down: 2575 (20.3 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 165/381 = 43.3% [38.4, 48.3]; failed (Selected on the outcome) 121/281 = 43.1% [37.4, 48.9]; base 3728/8321 = 44.8% [43.7, 45.9] -> OUTSIDE the base interval
    +1: n 2523; mean -0.071 [-0.125, -0.017]; median -0.052; SD 0.886; mean w/o best 1% -0.101; positive 47.0% | drift baseline mean -0.057 (n 124463); minus baseline -0.013
    +2: n 2513; mean -0.105 [-0.177, -0.031]; median -0.062; SD 1.154; mean w/o best 1% -0.144; positive 47.1% | drift baseline mean -0.108 (n 124354); minus baseline +0.004
    +5: n 2509; mean -0.275 [-0.389, -0.160]; median -0.298; SD 1.767; mean w/o best 1% -0.333; positive 42.6% | drift baseline mean -0.252 (n 124449); minus baseline -0.023
    +10: n 2496; mean -0.531 [-0.700, -0.363]; median -0.288; SD 2.518; mean w/o best 1% -0.607; positive 43.6% | drift baseline mean -0.507 (n 123623); minus baseline -0.024
- pin bar up: 3021 (23.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 207/420 = 49.3% [44.5, 54.1]; failed (Selected on the outcome) 118/246 = 48.0% [41.8, 54.2]; base 4090/8321 = 49.2% [48.1, 50.2] -> inside the base interval
    +1: n 2960; mean +0.056 [-0.002, +0.112]; median +0.055; SD 0.918; mean w/o best 1% +0.029; positive 53.1% | drift baseline mean +0.057 (n 124463); minus baseline -0.002
    +2: n 2949; mean +0.124 [+0.046, +0.199]; median +0.078; SD 1.184; mean w/o best 1% +0.088; positive 53.7% | drift baseline mean +0.108 (n 124354); minus baseline +0.016
    +5: n 2953; mean +0.302 [+0.189, +0.414]; median +0.282; SD 1.776; mean w/o best 1% +0.241; positive 57.2% | drift baseline mean +0.252 (n 124449); minus baseline +0.050
    +10: n 2935; mean +0.537 [+0.369, +0.704]; median +0.300; SD 2.520; mean w/o best 1% +0.460; positive 58.3% | drift baseline mean +0.507 (n 123623); minus baseline +0.030
- pin bar at a level down: 390 (3.1 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 29/381 = 7.6% [5.4, 10.7]; failed (Selected on the outcome) 17/281 = 6.0% [3.8, 9.5]; base 723/8321 = 8.7% [8.1, 9.3] -> OUTSIDE the base interval
    +1: n 380; mean -0.155 [-0.256, -0.053]; median -0.077; SD 0.881; mean w/o best 1% -0.184; positive 45.0% | drift baseline mean -0.057 (n 124463); minus baseline -0.098
    +2: n 376; mean -0.182 [-0.314, -0.052]; median -0.114; SD 1.141; mean w/o best 1% -0.218; positive 44.9% | drift baseline mean -0.108 (n 124354); minus baseline -0.073
    +5: n 379; mean -0.448 [-0.664, -0.233]; median -0.448; SD 1.867; mean w/o best 1% -0.507; positive 40.4% | drift baseline mean -0.252 (n 124449); minus baseline -0.195
    +10: n 377; mean -0.592 [-0.854, -0.322]; median -0.229; SD 2.454; mean w/o best 1% -0.664; positive 44.6% | drift baseline mean -0.507 (n 123623); minus baseline -0.085
- pin bar at a level up: 441 (3.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 34/420 = 8.1% [5.9, 11.1]; failed (Selected on the outcome) 21/246 = 8.5% [5.7, 12.7]; base 809/8321 = 9.7% [9.1, 10.4] -> OUTSIDE the base interval
    +1: n 435; mean +0.003 [-0.101, +0.101]; median -0.005; SD 0.927; mean w/o best 1% -0.025; positive 49.9% | drift baseline mean +0.057 (n 124463); minus baseline -0.055
    +2: n 434; mean +0.084 [-0.046, +0.213]; median +0.086; SD 1.207; mean w/o best 1% +0.046; positive 53.7% | drift baseline mean +0.108 (n 124354); minus baseline -0.024
    +5: n 433; mean +0.287 [+0.100, +0.473]; median +0.356; SD 1.772; mean w/o best 1% +0.226; positive 58.2% | drift baseline mean +0.252 (n 124449); minus baseline +0.034
    +10: n 433; mean +0.414 [+0.184, +0.673]; median +0.223; SD 2.391; mean w/o best 1% +0.345; positive 55.7% | drift baseline mean +0.507 (n 123623); minus baseline -0.093
- retest failed down: 1552 (12.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 126/381 = 33.1% [28.5, 37.9]; failed (Selected on the outcome) 94/281 = 33.5% [28.2, 39.2]; base 2719/8321 = 32.7% [31.7, 33.7] -> inside the base interval
    +1: n 1522; mean -0.036 [-0.098, +0.026]; median -0.028; SD 0.911; mean w/o best 1% -0.066; positive 48.5% | drift baseline mean -0.057 (n 124463); minus baseline +0.021
    +2: n 1533; mean -0.089 [-0.163, -0.011]; median -0.097; SD 1.150; mean w/o best 1% -0.126; positive 46.1% | drift baseline mean -0.108 (n 124354); minus baseline +0.019
    +5: n 1529; mean -0.166 [-0.295, -0.045]; median -0.203; SD 1.761; mean w/o best 1% -0.223; positive 45.8% | drift baseline mean -0.252 (n 124449); minus baseline +0.087
    +10: n 1515; mean -0.381 [-0.550, -0.217]; median -0.243; SD 2.421; mean w/o best 1% -0.454; positive 44.9% | drift baseline mean -0.507 (n 123623); minus baseline +0.126
- retest failed up: 1583 (12.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 131/420 = 31.2% [26.9, 35.8]; failed (Selected on the outcome) 81/246 = 32.9% [27.4, 39.0]; base 2719/8321 = 32.7% [31.7, 33.7] -> OUTSIDE the base interval
    +1: n 1549; mean +0.051 [-0.009, +0.110]; median +0.060; SD 0.930; mean w/o best 1% +0.023; positive 53.0% | drift baseline mean +0.057 (n 124463); minus baseline -0.006
    +2: n 1550; mean +0.098 [+0.018, +0.178]; median +0.061; SD 1.143; mean w/o best 1% +0.064; positive 52.8% | drift baseline mean +0.108 (n 124354); minus baseline -0.010
    +5: n 1557; mean +0.199 [+0.073, +0.313]; median +0.147; SD 1.731; mean w/o best 1% +0.137; positive 53.6% | drift baseline mean +0.252 (n 124449); minus baseline -0.054
    +10: n 1548; mean +0.436 [+0.256, +0.613]; median +0.243; SD 2.507; mean w/o best 1% +0.358; positive 54.8% | drift baseline mean +0.507 (n 123623); minus baseline -0.071
- retest held down: 1409 (11.1 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 121/381 = 31.8% [27.3, 36.6]; failed (Selected on the outcome) 92/281 = 32.7% [27.5, 38.4]; base 2518/8321 = 30.3% [29.3, 31.3] -> OUTSIDE the base interval
    +1: n 1383; mean -0.078 [-0.139, -0.020]; median -0.076; SD 0.873; mean w/o best 1% -0.109; positive 44.9% | drift baseline mean -0.057 (n 124463); minus baseline -0.021
    +2: n 1383; mean -0.110 [-0.188, -0.032]; median -0.066; SD 1.123; mean w/o best 1% -0.150; positive 46.7% | drift baseline mean -0.108 (n 124354); minus baseline -0.002
    +5: n 1385; mean -0.196 [-0.315, -0.073]; median -0.188; SD 1.711; mean w/o best 1% -0.254; positive 45.6% | drift baseline mean -0.252 (n 124449); minus baseline +0.056
    +10: n 1372; mean -0.463 [-0.631, -0.293]; median -0.255; SD 2.380; mean w/o best 1% -0.531; positive 44.5% | drift baseline mean -0.507 (n 123623); minus baseline +0.044
- retest held up: 1580 (12.4 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 138/420 = 32.9% [28.5, 37.5]; failed (Selected on the outcome) 67/246 = 27.2% [22.1, 33.1]; base 2772/8321 = 33.3% [32.3, 34.3] -> inside the base interval
    +1: n 1544; mean +0.076 [+0.016, +0.135]; median +0.038; SD 0.908; mean w/o best 1% +0.049; positive 52.2% | drift baseline mean +0.057 (n 124463); minus baseline +0.019
    +2: n 1538; mean +0.147 [+0.070, +0.225]; median +0.107; SD 1.150; mean w/o best 1% +0.111; positive 53.9% | drift baseline mean +0.108 (n 124354); minus baseline +0.039
    +5: n 1546; mean +0.342 [+0.219, +0.468]; median +0.323; SD 1.807; mean w/o best 1% +0.286; positive 59.1% | drift baseline mean +0.252 (n 124449); minus baseline +0.090
    +10: n 1535; mean +0.570 [+0.401, +0.753]; median +0.335; SD 2.535; mean w/o best 1% +0.497; positive 57.6% | drift baseline mean +0.507 (n 123623); minus baseline +0.063

### M5: 381285 bars
- consolidation down: 3511 (9.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 238/381 = 62.5% [57.5, 67.2]; failed (Selected on the outcome) 181/281 = 64.4% [58.7, 69.8]; base 4625/8321 = 55.6% [54.5, 56.6] -> OUTSIDE the base interval
    +1: n 3440; mean -0.035 [-0.084, +0.015]; median -0.048; SD 0.859; mean w/o best 1% -0.066; positive 47.2% | drift baseline mean -0.057 (n 373353); minus baseline +0.022
    +2: n 3447; mean -0.083 [-0.154, -0.013]; median -0.076; SD 1.115; mean w/o best 1% -0.122; positive 46.7% | drift baseline mean -0.108 (n 373008); minus baseline +0.025
    +5: n 3427; mean -0.195 [-0.306, -0.085]; median -0.205; SD 1.713; mean w/o best 1% -0.249; positive 45.6% | drift baseline mean -0.252 (n 373310); minus baseline +0.058
    +10: n 3404; mean -0.445 [-0.597, -0.292]; median -0.280; SD 2.445; mean w/o best 1% -0.518; positive 44.2% | drift baseline mean -0.507 (n 370825); minus baseline +0.062
- consolidation up: 3936 (10.3 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 277/420 = 66.0% [61.3, 70.3]; failed (Selected on the outcome) 167/246 = 67.9% [61.8, 73.4]; base 4867/8321 = 58.5% [57.4, 59.5] -> OUTSIDE the base interval
    +1: n 3850; mean +0.056 [+0.004, +0.105]; median +0.044; SD 0.873; mean w/o best 1% +0.030; positive 52.8% | drift baseline mean +0.057 (n 373353); minus baseline -0.001
    +2: n 3835; mean +0.108 [+0.042, +0.173]; median +0.061; SD 1.107; mean w/o best 1% +0.077; positive 52.6% | drift baseline mean +0.108 (n 373008); minus baseline +0.000
    +5: n 3855; mean +0.267 [+0.161, +0.372]; median +0.250; SD 1.740; mean w/o best 1% +0.208; positive 56.3% | drift baseline mean +0.252 (n 373310); minus baseline +0.015
    +10: n 3820; mean +0.537 [+0.378, +0.689]; median +0.319; SD 2.480; mean w/o best 1% +0.458; positive 56.3% | drift baseline mean +0.507 (n 370825); minus baseline +0.030
- double bottom / top down: 4923 (12.9 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 243/381 = 63.8% [58.8, 68.4]; failed (Selected on the outcome) 200/281 = 71.2% [65.6, 76.2]; base 5423/8321 = 65.2% [64.1, 66.2] -> OUTSIDE the base interval
    +1: n 4831; mean -0.048 [-0.101, +0.005]; median -0.064; SD 0.872; mean w/o best 1% -0.080; positive 46.5% | drift baseline mean -0.057 (n 373353); minus baseline +0.009
    +2: n 4831; mean -0.102 [-0.170, -0.034]; median -0.076; SD 1.124; mean w/o best 1% -0.142; positive 46.8% | drift baseline mean -0.108 (n 373008); minus baseline +0.006
    +5: n 4818; mean -0.209 [-0.313, -0.110]; median -0.192; SD 1.722; mean w/o best 1% -0.265; positive 45.5% | drift baseline mean -0.252 (n 373310); minus baseline +0.043
    +10: n 4796; mean -0.484 [-0.642, -0.334]; median -0.308; SD 2.486; mean w/o best 1% -0.554; positive 43.8% | drift baseline mean -0.507 (n 370825); minus baseline +0.023
- double bottom / top up: 5032 (13.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 263/420 = 62.6% [57.9, 67.1]; failed (Selected on the outcome) 165/246 = 67.1% [61.0, 72.6]; base 5588/8321 = 67.2% [66.1, 68.2] -> OUTSIDE the base interval
    +1: n 4929; mean +0.072 [+0.021, +0.124]; median +0.072; SD 0.893; mean w/o best 1% +0.046; positive 54.2% | drift baseline mean +0.057 (n 373353); minus baseline +0.015
    +2: n 4910; mean +0.122 [+0.058, +0.187]; median +0.088; SD 1.146; mean w/o best 1% +0.087; positive 53.6% | drift baseline mean +0.108 (n 373008); minus baseline +0.014
    +5: n 4929; mean +0.275 [+0.175, +0.382]; median +0.242; SD 1.760; mean w/o best 1% +0.216; positive 56.5% | drift baseline mean +0.252 (n 373310); minus baseline +0.022
    +10: n 4905; mean +0.516 [+0.370, +0.663]; median +0.310; SD 2.475; mean w/o best 1% +0.439; positive 56.5% | drift baseline mean +0.507 (n 370825); minus baseline +0.009
- engulfing down: 24465 (64.2 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 381/381 = 100.0% [99.0, 100.0]; failed (Selected on the outcome) 280/281 = 99.6% [98.0, 99.9]; base 8291/8321 = 99.6% [99.5, 99.7] -> OUTSIDE the base interval
    +1: n 23966; mean -0.054 [-0.099, -0.006]; median -0.056; SD 0.883; mean w/o best 1% -0.086; positive 46.7% | drift baseline mean -0.057 (n 373353); minus baseline +0.003
    +2: n 23943; mean -0.098 [-0.159, -0.036]; median -0.081; SD 1.134; mean w/o best 1% -0.138; positive 46.7% | drift baseline mean -0.108 (n 373008); minus baseline +0.011
    +5: n 23958; mean -0.225 [-0.318, -0.137]; median -0.216; SD 1.724; mean w/o best 1% -0.280; positive 44.5% | drift baseline mean -0.252 (n 373310); minus baseline +0.027
    +10: n 23828; mean -0.454 [-0.593, -0.321]; median -0.257; SD 2.457; mean w/o best 1% -0.526; positive 44.1% | drift baseline mean -0.507 (n 370825); minus baseline +0.053
- engulfing up: 25404 (66.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 420/420 = 100.0% [99.1, 100.0]; failed (Selected on the outcome) 246/246 = 100.0% [98.5, 100.0]; base 8292/8321 = 99.7% [99.5, 99.8] -> OUTSIDE the base interval
    +1: n 24862; mean +0.059 [+0.014, +0.106]; median +0.066; SD 0.879; mean w/o best 1% +0.032; positive 53.8% | drift baseline mean +0.057 (n 373353); minus baseline +0.002
    +2: n 24835; mean +0.116 [+0.056, +0.176]; median +0.099; SD 1.133; mean w/o best 1% +0.081; positive 54.0% | drift baseline mean +0.108 (n 373008); minus baseline +0.008
    +5: n 24857; mean +0.271 [+0.177, +0.366]; median +0.241; SD 1.753; mean w/o best 1% +0.212; positive 56.3% | drift baseline mean +0.252 (n 373310); minus baseline +0.019
    +10: n 24684; mean +0.525 [+0.399, +0.654]; median +0.296; SD 2.488; mean w/o best 1% +0.447; positive 56.8% | drift baseline mean +0.507 (n 370825); minus baseline +0.018
- engulfing at a level down: 3653 (9.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 203/381 = 53.3% [48.3, 58.2]; failed (Selected on the outcome) 160/281 = 56.9% [51.1, 62.6]; base 4732/8321 = 56.9% [55.8, 57.9] -> OUTSIDE the base interval
    +1: n 3569; mean -0.059 [-0.114, -0.001]; median -0.057; SD 0.890; mean w/o best 1% -0.093; positive 47.3% | drift baseline mean -0.057 (n 373353); minus baseline -0.002
    +2: n 3578; mean -0.114 [-0.186, -0.044]; median -0.068; SD 1.135; mean w/o best 1% -0.157; positive 47.0% | drift baseline mean -0.108 (n 373008); minus baseline -0.006
    +5: n 3572; mean -0.278 [-0.383, -0.170]; median -0.261; SD 1.690; mean w/o best 1% -0.332; positive 43.3% | drift baseline mean -0.252 (n 373310); minus baseline -0.025
    +10: n 3559; mean -0.510 [-0.665, -0.358]; median -0.314; SD 2.468; mean w/o best 1% -0.586; positive 43.4% | drift baseline mean -0.507 (n 370825); minus baseline -0.003
- engulfing at a level up: 3483 (9.1 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 213/420 = 50.7% [45.9, 55.5]; failed (Selected on the outcome) 124/246 = 50.4% [44.2, 56.6]; base 4536/8321 = 54.5% [53.4, 55.6] -> OUTSIDE the base interval
    +1: n 3389; mean +0.062 [+0.008, +0.113]; median +0.058; SD 0.879; mean w/o best 1% +0.034; positive 53.5% | drift baseline mean +0.057 (n 373353); minus baseline +0.005
    +2: n 3391; mean +0.150 [+0.083, +0.217]; median +0.123; SD 1.122; mean w/o best 1% +0.112; positive 54.2% | drift baseline mean +0.108 (n 373008); minus baseline +0.042
    +5: n 3384; mean +0.291 [+0.188, +0.398]; median +0.236; SD 1.728; mean w/o best 1% +0.232; positive 55.8% | drift baseline mean +0.252 (n 373310); minus baseline +0.038
    +10: n 3350; mean +0.592 [+0.428, +0.754]; median +0.343; SD 2.523; mean w/o best 1% +0.513; positive 56.9% | drift baseline mean +0.507 (n 370825); minus baseline +0.085
- head and shoulders down: 657 (1.7 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 68/381 = 17.8% [14.3, 22.0]; failed (Selected on the outcome) 45/281 = 16.0% [12.2, 20.8]; base 1227/8321 = 14.7% [14.0, 15.5] -> OUTSIDE the base interval
    +1: n 643; mean -0.052 [-0.146, +0.032]; median -0.028; SD 0.933; mean w/o best 1% -0.084; positive 47.7% | drift baseline mean -0.057 (n 373353); minus baseline +0.005
    +2: n 641; mean -0.143 [-0.258, -0.024]; median -0.140; SD 1.218; mean w/o best 1% -0.182; positive 45.6% | drift baseline mean -0.108 (n 373008); minus baseline -0.035
    +5: n 641; mean -0.297 [-0.458, -0.145]; median -0.319; SD 1.750; mean w/o best 1% -0.341; positive 42.6% | drift baseline mean -0.252 (n 373310); minus baseline -0.045
    +10: n 636; mean -0.623 [-0.848, -0.388]; median -0.360; SD 2.451; mean w/o best 1% -0.694; positive 41.7% | drift baseline mean -0.507 (n 370825); minus baseline -0.116
- head and shoulders up: 701 (1.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 74/420 = 17.6% [14.3, 21.6]; failed (Selected on the outcome) 40/246 = 16.3% [12.2, 21.4]; base 1311/8321 = 15.8% [15.0, 16.6] -> OUTSIDE the base interval
    +1: n 684; mean +0.122 [+0.045, +0.194]; median +0.110; SD 0.861; mean w/o best 1% +0.093; positive 55.3% | drift baseline mean +0.057 (n 373353); minus baseline +0.065
    +2: n 683; mean +0.132 [+0.037, +0.228]; median +0.108; SD 1.122; mean w/o best 1% +0.097; positive 53.1% | drift baseline mean +0.108 (n 373008); minus baseline +0.024
    +5: n 683; mean +0.299 [+0.156, +0.451]; median +0.265; SD 1.723; mean w/o best 1% +0.239; positive 58.1% | drift baseline mean +0.252 (n 373310); minus baseline +0.047
    +10: n 679; mean +0.524 [+0.313, +0.739]; median +0.311; SD 2.460; mean w/o best 1% +0.449; positive 57.7% | drift baseline mean +0.507 (n 370825); minus baseline +0.017
- pin bar down: 7515 (19.7 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 313/381 = 82.2% [78.0, 85.7]; failed (Selected on the outcome) 215/281 = 76.5% [71.2, 81.1]; base 6732/8321 = 80.9% [80.0, 81.7] -> OUTSIDE the base interval
    +1: n 7369; mean -0.076 [-0.126, -0.024]; median -0.078; SD 0.906; mean w/o best 1% -0.108; positive 46.0% | drift baseline mean -0.057 (n 373353); minus baseline -0.019
    +2: n 7369; mean -0.130 [-0.196, -0.066]; median -0.087; SD 1.156; mean w/o best 1% -0.171; positive 46.7% | drift baseline mean -0.108 (n 373008); minus baseline -0.022
    +5: n 7373; mean -0.277 [-0.381, -0.170]; median -0.252; SD 1.777; mean w/o best 1% -0.334; positive 44.0% | drift baseline mean -0.252 (n 373310); minus baseline -0.025
    +10: n 7333; mean -0.504 [-0.663, -0.350]; median -0.301; SD 2.510; mean w/o best 1% -0.578; positive 43.3% | drift baseline mean -0.507 (n 370825); minus baseline +0.003
- pin bar up: 8592 (22.5 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 364/420 = 86.7% [83.1, 89.6]; failed (Selected on the outcome) 190/246 = 77.2% [71.6, 82.0]; base 7102/8321 = 85.4% [84.6, 86.1] -> OUTSIDE the base interval
    +1: n 8437; mean +0.041 [-0.009, +0.095]; median +0.041; SD 0.927; mean w/o best 1% +0.012; positive 52.8% | drift baseline mean +0.057 (n 373353); minus baseline -0.016
    +2: n 8407; mean +0.084 [+0.020, +0.152]; median +0.061; SD 1.176; mean w/o best 1% +0.047; positive 52.8% | drift baseline mean +0.108 (n 373008); minus baseline -0.024
    +5: n 8434; mean +0.210 [+0.109, +0.310]; median +0.209; SD 1.762; mean w/o best 1% +0.152; positive 55.6% | drift baseline mean +0.252 (n 373310); minus baseline -0.042
    +10: n 8370; mean +0.457 [+0.309, +0.591]; median +0.254; SD 2.489; mean w/o best 1% +0.378; positive 55.7% | drift baseline mean +0.507 (n 370825); minus baseline -0.050
- pin bar at a level down: 1141 (3.0 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 76/381 = 19.9% [16.2, 24.3]; failed (Selected on the outcome) 57/281 = 20.3% [16.0, 25.4]; base 1922/8321 = 23.1% [22.2, 24.0] -> OUTSIDE the base interval
    +1: n 1119; mean -0.057 [-0.128, +0.012]; median -0.059; SD 0.928; mean w/o best 1% -0.093; positive 47.7% | drift baseline mean -0.057 (n 373353); minus baseline +0.000
    +2: n 1116; mean -0.104 [-0.197, -0.008]; median -0.031; SD 1.193; mean w/o best 1% -0.151; positive 48.7% | drift baseline mean -0.108 (n 373008); minus baseline +0.004
    +5: n 1112; mean -0.253 [-0.401, -0.117]; median -0.189; SD 1.774; mean w/o best 1% -0.313; positive 45.3% | drift baseline mean -0.252 (n 373310); minus baseline -0.001
    +10: n 1104; mean -0.415 [-0.627, -0.212]; median -0.240; SD 2.547; mean w/o best 1% -0.493; positive 45.7% | drift baseline mean -0.507 (n 370825); minus baseline +0.092
- pin bar at a level up: 1358 (3.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 104/420 = 24.8% [20.9, 29.1]; failed (Selected on the outcome) 55/246 = 22.4% [17.6, 28.0]; base 2225/8321 = 26.7% [25.8, 27.7] -> OUTSIDE the base interval
    +1: n 1330; mean +0.070 [-0.000, +0.134]; median +0.059; SD 0.901; mean w/o best 1% +0.041; positive 54.2% | drift baseline mean +0.057 (n 373353); minus baseline +0.013
    +2: n 1331; mean +0.108 [+0.026, +0.189]; median +0.074; SD 1.134; mean w/o best 1% +0.072; positive 53.3% | drift baseline mean +0.108 (n 373008); minus baseline +0.000
    +5: n 1329; mean +0.184 [+0.048, +0.322]; median +0.221; SD 1.779; mean w/o best 1% +0.124; positive 55.9% | drift baseline mean +0.252 (n 373310); minus baseline -0.069
    +10: n 1325; mean +0.417 [+0.225, +0.615]; median +0.260; SD 2.449; mean w/o best 1% +0.342; positive 55.8% | drift baseline mean +0.507 (n 370825); minus baseline -0.090
- retest failed down: 4788 (12.6 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 267/381 = 70.1% [65.3, 74.5]; failed (Selected on the outcome) 185/281 = 65.8% [60.1, 71.1]; base 5810/8321 = 69.8% [68.8, 70.8] -> inside the base interval
    +1: n 4694; mean -0.063 [-0.111, -0.013]; median -0.068; SD 0.891; mean w/o best 1% -0.097; positive 46.4% | drift baseline mean -0.057 (n 373353); minus baseline -0.006
    +2: n 4699; mean -0.133 [-0.202, -0.069]; median -0.108; SD 1.137; mean w/o best 1% -0.175; positive 45.5% | drift baseline mean -0.108 (n 373008); minus baseline -0.025
    +5: n 4690; mean -0.249 [-0.353, -0.151]; median -0.256; SD 1.739; mean w/o best 1% -0.306; positive 44.1% | drift baseline mean -0.252 (n 373310); minus baseline +0.003
    +10: n 4650; mean -0.508 [-0.658, -0.361]; median -0.284; SD 2.494; mean w/o best 1% -0.576; positive 44.1% | drift baseline mean -0.507 (n 370825); minus baseline -0.001
- retest failed up: 4899 (12.8 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 288/420 = 68.6% [64.0, 72.8]; failed (Selected on the outcome) 176/246 = 71.5% [65.6, 76.8]; base 5908/8321 = 71.0% [70.0, 72.0] -> OUTSIDE the base interval
    +1: n 4783; mean +0.046 [-0.006, +0.098]; median +0.044; SD 0.909; mean w/o best 1% +0.018; positive 52.5% | drift baseline mean +0.057 (n 373353); minus baseline -0.011
    +2: n 4766; mean +0.082 [+0.016, +0.147]; median +0.057; SD 1.146; mean w/o best 1% +0.047; positive 52.3% | drift baseline mean +0.108 (n 373008); minus baseline -0.026
    +5: n 4778; mean +0.244 [+0.143, +0.344]; median +0.220; SD 1.775; mean w/o best 1% +0.183; positive 56.0% | drift baseline mean +0.252 (n 373310); minus baseline -0.009
    +10: n 4763; mean +0.495 [+0.349, +0.633]; median +0.269; SD 2.462; mean w/o best 1% +0.417; positive 56.1% | drift baseline mean +0.507 (n 370825); minus baseline -0.012
- retest held down: 4190 (11.0 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 270/381 = 70.9% [66.1, 75.2]; failed (Selected on the outcome) 197/281 = 70.1% [64.5, 75.2]; base 5463/8321 = 65.7% [64.6, 66.7] -> OUTSIDE the base interval
    +1: n 4102; mean -0.046 [-0.098, +0.003]; median -0.058; SD 0.891; mean w/o best 1% -0.078; positive 46.7% | drift baseline mean -0.057 (n 373353); minus baseline +0.011
    +2: n 4110; mean -0.108 [-0.176, -0.044]; median -0.068; SD 1.148; mean w/o best 1% -0.147; positive 47.0% | drift baseline mean -0.108 (n 373008); minus baseline -0.000
    +5: n 4106; mean -0.237 [-0.344, -0.132]; median -0.221; SD 1.769; mean w/o best 1% -0.293; positive 44.5% | drift baseline mean -0.252 (n 373310); minus baseline +0.016
    +10: n 4067; mean -0.466 [-0.612, -0.322]; median -0.267; SD 2.473; mean w/o best 1% -0.544; positive 44.2% | drift baseline mean -0.507 (n 370825); minus baseline +0.041
- retest held up: 4584 (12.0 per 1,000 bars) | windows with one: swing starts (Selected on the outcome) 304/420 = 72.4% [67.9, 76.4]; failed (Selected on the outcome) 163/246 = 66.3% [60.1, 71.9]; base 5750/8321 = 69.1% [68.1, 70.1] -> OUTSIDE the base interval
    +1: n 4497; mean +0.069 [+0.019, +0.119]; median +0.065; SD 0.898; mean w/o best 1% +0.042; positive 53.9% | drift baseline mean +0.057 (n 373353); minus baseline +0.012
    +2: n 4493; mean +0.120 [+0.052, +0.189]; median +0.078; SD 1.156; mean w/o best 1% +0.084; positive 53.4% | drift baseline mean +0.108 (n 373008); minus baseline +0.012
    +5: n 4497; mean +0.286 [+0.177, +0.392]; median +0.266; SD 1.766; mean w/o best 1% +0.225; positive 57.1% | drift baseline mean +0.252 (n 373310); minus baseline +0.033
    +10: n 4481; mean +0.594 [+0.458, +0.744]; median +0.351; SD 2.482; mean w/o best 1% +0.516; positive 57.3% | drift baseline mean +0.507 (n 370825); minus baseline +0.088

## §6 pullback continuation versus reversal. DESCRIPTIVE, not tradeable. 2021-2026 only, a regime-specific description. Structures counted on history; none is a signal. Not a classifier.

### R48 legs
- 38.2%: legs 61 ({'continued': 34, 'reversed': 18, 'unresolved': 9}); continued among resolved 34/52 = 65.4% [51.8, 76.8]
    speed: fast (<= median 5 bars) vs slow: 19/30 = 63.3% [45.5, 78.1] vs 15/22 = 68.2% [47.3, 83.6]; difference -4.8 [-28.4, +20.7] -> does not separate
    15-minute structure: with vs against: 19/25 = 76.0% [56.6, 88.5] vs 15/27 = 55.6% [37.3, 72.4]; difference +20.4 [-5.3, +42.6] -> does not separate
- 50.0%: legs 49 ({'reversed': 22, 'continued': 20, 'unresolved': 7}); continued among resolved 20/42 = 47.6% [33.4, 62.3]
    speed: fast (<= median 6 bars) vs slow: 11/22 = 50.0% [30.7, 69.3] vs 9/20 = 45.0% [25.8, 65.8]; difference +5.0 [-23.4, +32.2] -> does not separate
    15-minute structure: with vs against: 10/17 = 58.8% [36.0, 78.4] vs 10/25 = 40.0% [23.4, 59.3] -> INSUFFICIENT (a side has fewer than 20)
- 61.8%: legs 36 ({'reversed': 22, 'continued': 11, 'unresolved': 3}); continued among resolved 11/33 = 33.3% [19.8, 50.4]
    speed: fast (<= median 8 bars) vs slow: 6/17 = 35.3% [17.3, 58.7] vs 5/16 = 31.2% [14.2, 55.6] -> INSUFFICIENT (a side has fewer than 20)
    15-minute structure: with vs against: 6/12 = 50.0% [25.4, 74.6] vs 5/21 = 23.8% [10.6, 45.1] -> INSUFFICIENT (a side has fewer than 20)

### 4-hour swing legs
- 38.2%: legs 280 ({'continued': 153, 'reversed': 119, 'unresolved': 8}); continued among resolved 153/272 = 56.2% [50.3, 62.0]
    speed: fast (<= median 3 bars) vs slow: 85/164 = 51.8% [44.2, 59.3] vs 68/108 = 63.0% [53.6, 71.5]; difference -11.1 [-22.5, +0.9] -> does not separate
    15-minute structure: with vs against: 59/113 = 52.2% [43.1, 61.2] vs 94/159 = 59.1% [51.4, 66.5]; difference -6.9 [-18.6, +5.0] -> does not separate
- 50.0%: legs 217 ({'continued': 91, 'reversed': 120, 'unresolved': 6}); continued among resolved 91/211 = 43.1% [36.6, 49.9]
    speed: fast (<= median 4 bars) vs slow: 50/119 = 42.0% [33.5, 51.0] vs 41/92 = 44.6% [34.8, 54.7]; difference -2.5 [-15.8, +10.7] -> does not separate
    15-minute structure: with vs against: 29/71 = 40.8% [30.2, 52.5] vs 62/140 = 44.3% [36.3, 52.6]; difference -3.4 [-16.9, +10.6] -> does not separate
- 61.8%: legs 179 ({'continued': 55, 'reversed': 119, 'unresolved': 5}); continued among resolved 55/174 = 31.6% [25.2, 38.9]
    speed: fast (<= median 6 bars) vs slow: 35/109 = 32.1% [24.1, 41.4] vs 20/65 = 30.8% [20.9, 42.8]; difference +1.3 [-13.1, +14.9] -> does not separate
    15-minute structure: with vs against: 16/51 = 31.4% [20.3, 45.0] vs 39/123 = 31.7% [24.1, 40.4]; difference -0.3 [-14.4, +15.3] -> does not separate

==============================================================================
# PART B: the four entries under two cost structures (§4.5)
==============================================================================

## §4.5 part B, 4-hour setups. Every cost is a labelled placeholder except the measured spread. Trades without a spread quote: 0

### long: 286 setups

#### CFD primary (both pay): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 286; mean +0.023 [-0.052, +0.101]; median -0.015; SD 0.667; mean w/o best 1% -0.003; positive 49.0%
- +1 30-minute: n 286; mean -0.016 [-0.145, +0.119]; median +0.000; SD 1.171; mean w/o best 1% -0.072; positive 35.3% | paired -0.156 [-0.283, -0.031]
- +1 15-minute: n 286; mean -0.076 [-0.266, +0.131]; median -1.020; SD 1.705; mean w/o best 1% -0.177; positive 30.1% | paired -0.168 [-0.341, +0.028]
- +1 5-minute: n 286; mean +0.044 [-0.242, +0.342]; median -1.074; SD 2.549; mean w/o best 1% -0.071; positive 23.8% | paired +0.003 [-0.257, +0.284]
- +2 4-hour: n 286; mean +0.024 [-0.078, +0.132]; median -0.055; SD 0.894; mean w/o best 1% -0.020; positive 46.9%
- +2 30-minute: n 286; mean +0.038 [-0.164, +0.241]; median -1.005; SD 1.796; mean w/o best 1% -0.059; positive 33.2% | paired -0.068 [-0.245, +0.112]
- +2 15-minute: n 286; mean -0.020 [-0.266, +0.249]; median -1.040; SD 2.223; mean w/o best 1% -0.159; positive 24.8% | paired -0.108 [-0.344, +0.141]
- +2 5-minute: n 286; mean +0.052 [-0.283, +0.421]; median -1.084; SD 3.048; mean w/o best 1% -0.111; positive 19.2% | paired +0.010 [-0.299, +0.353]
- +5 4-hour: n 286; mean +0.129 [-0.019, +0.274]; median -0.072; SD 1.260; mean w/o best 1% +0.073; positive 49.3%
- +5 30-minute: n 286; mean +0.223 [-0.090, +0.568]; median -1.031; SD 2.830; mean w/o best 1% +0.063; positive 25.5% | paired +0.020 [-0.260, +0.304]
- +5 15-minute: n 286; mean +0.277 [-0.160, +0.749]; median -1.052; SD 3.999; mean w/o best 1% -0.019; positive 19.2% | paired +0.096 [-0.303, +0.567]
- +5 5-minute: n 286; mean -0.032 [-0.480, +0.478]; median -1.100; SD 4.244; mean w/o best 1% -0.332; positive 11.2% | paired -0.183 [-0.618, +0.298]
- +10 4-hour: n 286; mean +0.228 [+0.028, +0.443]; median -0.855; SD 1.815; mean w/o best 1% +0.141; positive 42.3%
- +10 30-minute: n 286; mean +0.278 [-0.091, +0.722]; median -1.038; SD 3.485; mean w/o best 1% +0.074; positive 19.6% | paired -0.028 [-0.375, +0.340]
- +10 15-minute: n 286; mean +0.184 [-0.249, +0.653]; median -1.057; SD 3.895; mean w/o best 1% -0.040; positive 13.6% | paired -0.108 [-0.526, +0.338]
- +10 5-minute: n 286; mean -0.311 [-0.704, +0.181]; median -1.109; SD 3.871; mean w/o best 1% -0.594; positive 7.3% | paired -0.567 [-0.996, -0.086]

#### CFD stress (hour p90 spread): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 286; mean +0.018 [-0.059, +0.097]; median -0.017; SD 0.667; mean w/o best 1% -0.007; positive 48.6%
- +1 30-minute: n 286; mean -0.027 [-0.163, +0.109]; median +0.000; SD 1.170; mean w/o best 1% -0.083; positive 35.0% | paired -0.164 [-0.291, -0.040]
- +1 15-minute: n 286; mean -0.094 [-0.281, +0.111]; median -1.028; SD 1.703; mean w/o best 1% -0.194; positive 30.1% | paired -0.183 [-0.360, +0.004]
- +1 5-minute: n 286; mean +0.013 [-0.271, +0.316]; median -1.095; SD 2.547; mean w/o best 1% -0.102; positive 23.8% | paired -0.024 [-0.281, +0.263]
- +2 4-hour: n 286; mean +0.019 [-0.083, +0.123]; median -0.059; SD 0.893; mean w/o best 1% -0.024; positive 46.9%
- +2 30-minute: n 286; mean +0.027 [-0.171, +0.248]; median -1.007; SD 1.794; mean w/o best 1% -0.070; positive 33.2% | paired -0.076 [-0.252, +0.106]
- +2 15-minute: n 286; mean -0.037 [-0.286, +0.246]; median -1.051; SD 2.221; mean w/o best 1% -0.176; positive 24.8% | paired -0.121 [-0.349, +0.131]
- +2 5-minute: n 286; mean +0.021 [-0.314, +0.386]; median -1.103; SD 3.047; mean w/o best 1% -0.141; positive 19.2% | paired -0.017 [-0.327, +0.341]
- +5 4-hour: n 286; mean +0.125 [-0.020, +0.274]; median -0.076; SD 1.259; mean w/o best 1% +0.069; positive 48.6%
- +5 30-minute: n 286; mean +0.213 [-0.092, +0.565]; median -1.039; SD 2.828; mean w/o best 1% +0.052; positive 25.2% | paired +0.013 [-0.261, +0.328]
- +5 15-minute: n 286; mean +0.261 [-0.172, +0.764]; median -1.064; SD 3.996; mean w/o best 1% -0.035; positive 19.2% | paired +0.082 [-0.329, +0.519]
- +5 5-minute: n 286; mean -0.062 [-0.507, +0.467]; median -1.131; SD 4.243; mean w/o best 1% -0.362; positive 11.2% | paired -0.208 [-0.624, +0.282]
- +10 4-hour: n 286; mean +0.224 [+0.008, +0.446]; median -0.859; SD 1.814; mean w/o best 1% +0.137; positive 42.3%
- +10 30-minute: n 286; mean +0.268 [-0.118, +0.710]; median -1.050; SD 3.483; mean w/o best 1% +0.064; positive 19.6% | paired -0.035 [-0.382, +0.344]
- +10 15-minute: n 286; mean +0.168 [-0.257, +0.644]; median -1.070; SD 3.893; mean w/o best 1% -0.056; positive 13.6% | paired -0.121 [-0.520, +0.298]
- +10 5-minute: n 286; mean -0.339 [-0.737, +0.148]; median -1.140; SD 3.870; mean w/o best 1% -0.623; positive 7.3% | paired -0.593 [-1.008, -0.121]

#### CFD side: shorts receive: net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 286; mean +0.023 [-0.056, +0.104]; median -0.015; SD 0.667; mean w/o best 1% -0.003; positive 49.0%
- +1 30-minute: n 286; mean -0.016 [-0.148, +0.121]; median +0.000; SD 1.171; mean w/o best 1% -0.072; positive 35.3% | paired -0.156 [-0.284, -0.021]
- +1 15-minute: n 286; mean -0.076 [-0.263, +0.137]; median -1.020; SD 1.705; mean w/o best 1% -0.177; positive 30.1% | paired -0.168 [-0.355, +0.018]
- +1 5-minute: n 286; mean +0.044 [-0.245, +0.344]; median -1.074; SD 2.549; mean w/o best 1% -0.071; positive 23.8% | paired +0.003 [-0.253, +0.282]
- +2 4-hour: n 286; mean +0.024 [-0.081, +0.130]; median -0.055; SD 0.894; mean w/o best 1% -0.020; positive 46.9%
- +2 30-minute: n 286; mean +0.038 [-0.160, +0.263]; median -1.005; SD 1.796; mean w/o best 1% -0.059; positive 33.2% | paired -0.068 [-0.239, +0.121]
- +2 15-minute: n 286; mean -0.020 [-0.265, +0.262]; median -1.040; SD 2.223; mean w/o best 1% -0.159; positive 24.8% | paired -0.108 [-0.341, +0.137]
- +2 5-minute: n 286; mean +0.052 [-0.291, +0.422]; median -1.084; SD 3.048; mean w/o best 1% -0.111; positive 19.2% | paired +0.010 [-0.317, +0.349]
- +5 4-hour: n 286; mean +0.129 [-0.018, +0.275]; median -0.072; SD 1.260; mean w/o best 1% +0.073; positive 49.3%
- +5 30-minute: n 286; mean +0.223 [-0.078, +0.567]; median -1.031; SD 2.830; mean w/o best 1% +0.063; positive 25.5% | paired +0.020 [-0.239, +0.331]
- +5 15-minute: n 286; mean +0.277 [-0.154, +0.771]; median -1.052; SD 3.999; mean w/o best 1% -0.019; positive 19.2% | paired +0.096 [-0.303, +0.569]
- +5 5-minute: n 286; mean -0.032 [-0.486, +0.465]; median -1.100; SD 4.244; mean w/o best 1% -0.332; positive 11.2% | paired -0.183 [-0.613, +0.312]
- +10 4-hour: n 286; mean +0.228 [+0.023, +0.449]; median -0.855; SD 1.815; mean w/o best 1% +0.141; positive 42.3%
- +10 30-minute: n 286; mean +0.278 [-0.113, +0.679]; median -1.038; SD 3.485; mean w/o best 1% +0.074; positive 19.6% | paired -0.028 [-0.380, +0.353]
- +10 15-minute: n 286; mean +0.184 [-0.222, +0.665]; median -1.057; SD 3.895; mean w/o best 1% -0.040; positive 13.6% | paired -0.108 [-0.505, +0.321]
- +10 5-minute: n 286; mean -0.311 [-0.718, +0.187]; median -1.109; SD 3.871; mean w/o best 1% -0.594; positive 7.3% | paired -0.567 [-0.992, -0.094]

#### futures primary (basis carry): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 286; mean +0.028 [-0.046, +0.105]; median -0.011; SD 0.667; mean w/o best 1% +0.003; positive 49.3%
- +1 30-minute: n 286; mean -0.007 [-0.142, +0.133]; median +0.000; SD 1.174; mean w/o best 1% -0.064; positive 35.3% | paired -0.152 [-0.272, -0.017]
- +1 15-minute: n 286; mean -0.058 [-0.256, +0.151]; median -1.013; SD 1.705; mean w/o best 1% -0.158; positive 30.1% | paired -0.155 [-0.343, +0.041]
- +1 5-minute: n 286; mean +0.093 [-0.187, +0.404]; median -1.043; SD 2.545; mean w/o best 1% -0.023; positive 23.8% | paired +0.047 [-0.226, +0.338]
- +2 4-hour: n 286; mean +0.035 [-0.068, +0.139]; median -0.043; SD 0.894; mean w/o best 1% -0.008; positive 46.9%
- +2 30-minute: n 286; mean +0.057 [-0.140, +0.269]; median -1.004; SD 1.799; mean w/o best 1% -0.039; positive 33.6% | paired -0.059 [-0.229, +0.133]
- +2 15-minute: n 286; mean +0.011 [-0.230, +0.284]; median -1.024; SD 2.239; mean w/o best 1% -0.129; positive 25.5% | paired -0.087 [-0.314, +0.166]
- +2 5-minute: n 286; mean +0.110 [-0.226, +0.482]; median -1.049; SD 3.049; mean w/o best 1% -0.052; positive 19.2% | paired +0.057 [-0.251, +0.418]
- +5 4-hour: n 286; mean +0.152 [+0.007, +0.299]; median -0.039; SD 1.267; mean w/o best 1% +0.096; positive 49.3%
- +5 30-minute: n 286; mean +0.258 [-0.067, +0.581]; median -1.020; SD 2.847; mean w/o best 1% +0.098; positive 25.5% | paired +0.033 [-0.251, +0.338]
- +5 15-minute: n 286; mean +0.326 [-0.094, +0.811]; median -1.030; SD 4.037; mean w/o best 1% +0.028; positive 19.2% | paired +0.124 [-0.268, +0.580]
- +5 5-minute: n 286; mean +0.049 [-0.395, +0.557]; median -1.059; SD 4.268; mean w/o best 1% -0.252; positive 11.2% | paired -0.123 [-0.552, +0.385]
- +10 4-hour: n 286; mean +0.267 [+0.059, +0.486]; median -0.804; SD 1.831; mean w/o best 1% +0.179; positive 42.3%
- +10 30-minute: n 286; mean +0.332 [-0.053, +0.753]; median -1.026; SD 3.534; mean w/o best 1% +0.127; positive 19.6% | paired -0.011 [-0.363, +0.364]
- +10 15-minute: n 286; mean +0.252 [-0.190, +0.741]; median -1.035; SD 3.974; mean w/o best 1% +0.023; positive 13.6% | paired -0.077 [-0.501, +0.336]
- +10 5-minute: n 286; mean -0.215 [-0.629, +0.259]; median -1.063; SD 3.928; mean w/o best 1% -0.502; positive 7.3% | paired -0.509 [-0.933, -0.005]

#### futures side: no carry: net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 286; mean +0.040 [-0.041, +0.118]; median +0.001; SD 0.669; mean w/o best 1% +0.014; positive 50.0%
- +1 30-minute: n 286; mean +0.005 [-0.121, +0.140]; median +0.000; SD 1.178; mean w/o best 1% -0.052; positive 36.0% | paired -0.149 [-0.275, -0.015]
- +1 15-minute: n 286; mean -0.039 [-0.229, +0.170]; median -1.010; SD 1.716; mean w/o best 1% -0.140; positive 30.4% | paired -0.146 [-0.327, +0.048]
- +1 5-minute: n 286; mean +0.131 [-0.161, +0.436]; median -1.031; SD 2.565; mean w/o best 1% +0.015; positive 23.8% | paired +0.074 [-0.188, +0.351]
- +2 4-hour: n 286; mean +0.053 [-0.049, +0.172]; median -0.026; SD 0.900; mean w/o best 1% +0.010; positive 48.6%
- +2 30-minute: n 286; mean +0.079 [-0.112, +0.292]; median -1.003; SD 1.813; mean w/o best 1% -0.018; positive 33.9% | paired -0.054 [-0.230, +0.135]
- +2 15-minute: n 286; mean +0.039 [-0.225, +0.330]; median -1.014; SD 2.263; mean w/o best 1% -0.102; positive 25.5% | paired -0.075 [-0.315, +0.187]
- +2 5-minute: n 286; mean +0.160 [-0.166, +0.536]; median -1.033; SD 3.085; mean w/o best 1% -0.003; positive 19.2% | paired +0.090 [-0.231, +0.435]
- +5 4-hour: n 286; mean +0.188 [+0.047, +0.340]; median -0.011; SD 1.281; mean w/o best 1% +0.131; positive 50.0%
- +5 30-minute: n 286; mean +0.305 [-0.008, +0.661]; median -1.008; SD 2.886; mean w/o best 1% +0.142; positive 25.9% | paired +0.046 [-0.246, +0.347]
- +5 15-minute: n 286; mean +0.378 [-0.056, +0.873]; median -1.016; SD 4.097; mean w/o best 1% +0.077; positive 19.2% | paired +0.142 [-0.280, +0.606]
- +5 5-minute: n 286; mean +0.125 [-0.357, +0.628]; median -1.039; SD 4.323; mean w/o best 1% -0.179; positive 11.2% | paired -0.083 [-0.500, +0.414]
- +10 4-hour: n 286; mean +0.326 [+0.120, +0.553]; median -0.708; SD 1.864; mean w/o best 1% +0.237; positive 42.7%
- +10 30-minute: n 286; mean +0.408 [+0.007, +0.864]; median -1.010; SD 3.626; mean w/o best 1% +0.197; positive 20.3% | paired +0.008 [-0.364, +0.386]
- +10 15-minute: n 286; mean +0.334 [-0.145, +0.805]; median -1.018; SD 4.098; mean w/o best 1% +0.099; positive 14.0% | paired -0.052 [-0.487, +0.432]
- +10 5-minute: n 286; mean -0.118 [-0.535, +0.367]; median -1.040; SD 4.024; mean w/o best 1% -0.411; positive 7.3% | paired -0.471 [-0.895, +0.030]

#### Position-size-free: net dollars an ounce per trade (CFD primary; futures primary); net daily ATR (CFD primary)
- +1 4-hour: CFD $n 286; mean +4.846 [+0.504, +9.404]; median -0.485; SD 38.670; mean w/o best 1% +3.296; positive 49.0% | futures $n 286; mean +5.167 [+0.849, +9.440]; median -0.312; SD 38.677; mean w/o best 1% +3.606; positive 49.3% | CFD ATR n 286; mean +0.040 [-0.056, +0.141]; median -0.020; SD 0.832; mean w/o best 1% +0.014; positive 49.0%
- +1 30-minute: CFD $n 242; mean +1.931 [-1.541, +5.484]; median -4.241; SD 27.505; mean w/o best 1% +0.760; positive 41.7% | futures $n 242; mean +2.126 [-1.270, +5.701]; median -4.161; SD 27.596; mean w/o best 1% +0.946; positive 41.7% | CFD ATR n 242; mean -0.024 [-0.106, +0.058]; median -0.147; SD 0.663; mean w/o best 1% -0.039; positive 41.7%
- +1 15-minute: CFD $n 269; mean +1.507 [-1.377, +4.440]; median -4.267; SD 24.526; mean w/o best 1% +0.184; positive 32.0% | futures $n 269; mean +1.727 [-1.149, +4.755]; median -4.201; SD 24.582; mean w/o best 1% +0.399; positive 32.0% | CFD ATR n 269; mean -0.022 [-0.077, +0.034]; median -0.159; SD 0.471; mean w/o best 1% -0.041; positive 32.0%
- +1 5-minute: CFD $n 281; mean +2.599 [+0.033, +5.401]; median -3.705; SD 23.076; mean w/o best 1% +1.350; positive 24.2% | futures $n 281; mean +2.883 [+0.331, +5.699]; median -3.561; SD 23.093; mean w/o best 1% +1.633; positive 24.2% | CFD ATR n 281; mean +0.022 [-0.030, +0.076]; median -0.132; SD 0.460; mean w/o best 1% +0.000; positive 24.2%
- +2 4-hour: CFD $n 286; mean +3.550 [-1.613, +9.385]; median -2.293; SD 48.195; mean w/o best 1% +1.445; positive 46.9% | futures $n 286; mean +4.131 [-1.437, +10.093]; median -2.247; SD 48.191; mean w/o best 1% +2.011; positive 46.9% | CFD ATR n 286; mean +0.053 [-0.068, +0.174]; median -0.094; SD 1.079; mean w/o best 1% +0.010; positive 46.9%
- +2 30-minute: CFD $n 262; mean +1.012 [-3.153, +5.192]; median -6.266; SD 34.967; mean w/o best 1% -0.930; positive 36.3% | futures $n 262; mean +1.370 [-2.797, +5.495]; median -6.120; SD 35.034; mean w/o best 1% -0.590; positive 36.6% | CFD ATR n 262; mean -0.019 [-0.115, +0.088]; median -0.231; SD 0.835; mean w/o best 1% -0.054; positive 36.3%
- +2 15-minute: CFD $n 270; mean +2.112 [-1.652, +6.449]; median -5.439; SD 33.750; mean w/o best 1% +0.072; positive 26.3% | futures $n 270; mean +2.480 [-1.291, +6.636]; median -5.294; SD 33.927; mean w/o best 1% +0.424; positive 27.0% | CFD ATR n 270; mean -0.012 [-0.087, +0.072]; median -0.196; SD 0.645; mean w/o best 1% -0.040; positive 26.3%
- +2 5-minute: CFD $n 281; mean +3.318 [-0.152, +7.126]; median -3.976; SD 30.638; mean w/o best 1% +1.429; positive 19.6% | futures $n 281; mean +3.671 [+0.483, +7.357]; median -3.840; SD 30.779; mean w/o best 1% +1.764; positive 19.6% | CFD ATR n 281; mean +0.026 [-0.035, +0.090]; median -0.146; SD 0.557; mean w/o best 1% -0.005; positive 19.6%
- +5 4-hour: CFD $n 286; mean +8.358 [-0.297, +17.494]; median -3.512; SD 78.268; mean w/o best 1% +3.982; positive 49.3% | futures $n 286; mean +9.465 [+0.768, +18.347]; median -2.010; SD 78.472; mean w/o best 1% +5.075; positive 49.3% | CFD ATR n 286; mean +0.213 [+0.020, +0.416]; median -0.110; SD 1.699; mean w/o best 1% +0.150; positive 49.3%
- +5 30-minute: CFD $n 265; mean +4.259 [-1.891, +11.788]; median -8.573; SD 57.831; mean w/o best 1% +0.035; positive 27.5% | futures $n 265; mean +4.948 [-1.594, +12.734]; median -8.406; SD 58.125; mean w/o best 1% +0.706; positive 27.5% | CFD ATR n 265; mean +0.089 [-0.055, +0.242]; median -0.309; SD 1.251; mean w/o best 1% +0.035; positive 27.5%
- +5 15-minute: CFD $n 270; mean +3.402 [-2.249, +9.881]; median -6.308; SD 51.732; mean w/o best 1% -0.422; positive 20.4% | futures $n 270; mean +4.023 [-1.810, +10.869]; median -6.168; SD 52.036; mean w/o best 1% +0.179; positive 20.4% | CFD ATR n 270; mean +0.066 [-0.054, +0.196]; median -0.229; SD 1.040; mean w/o best 1% +0.012; positive 20.4%
- +5 5-minute: CFD $n 281; mean +5.537 [-0.189, +12.264]; median -4.555; SD 54.843; mean w/o best 1% +1.152; positive 11.4% | futures $n 281; mean +6.062 [+0.184, +12.870]; median -4.319; SD 55.170; mean w/o best 1% +1.655; positive 11.4% | CFD ATR n 281; mean +0.053 [-0.052, +0.172]; median -0.159; SD 0.909; mean w/o best 1% -0.008; positive 11.4%
- +10 4-hour: CFD $n 286; mean +10.939 [-0.955, +24.348]; median -19.394; SD 108.867; mean w/o best 1% +5.092; positive 42.3% | futures $n 286; mean +12.780 [+0.268, +25.216]; median -18.419; SD 109.367; mean w/o best 1% +6.907; positive 42.3% | CFD ATR n 286; mean +0.337 [+0.043, +0.616]; median -0.756; SD 2.395; mean w/o best 1% +0.253; positive 42.3%
- +10 30-minute: CFD $n 265; mean +3.818 [-3.831, +12.348]; median -10.575; SD 67.628; mean w/o best 1% -0.404; positive 21.1% | futures $n 265; mean +4.854 [-3.485, +13.123]; median -10.290; SD 68.263; mean w/o best 1% +0.590; positive 21.1% | CFD ATR n 265; mean +0.129 [-0.060, +0.335]; median -0.354; SD 1.674; mean w/o best 1% +0.045; positive 21.1%
- +10 15-minute: CFD $n 270; mean +1.863 [-4.203, +8.804]; median -7.762; SD 55.353; mean w/o best 1% -1.934; positive 14.4% | futures $n 270; mean +2.711 [-3.475, +10.066]; median -7.494; SD 55.903; mean w/o best 1% -1.124; positive 14.4% | CFD ATR n 270; mean +0.099 [-0.062, +0.273]; median -0.254; SD 1.418; mean w/o best 1% +0.021; positive 14.4%
- +10 5-minute: CFD $n 281; mean +0.403 [-4.224, +5.935]; median -4.878; SD 43.172; mean w/o best 1% -3.396; positive 7.5% | futures $n 281; mean +1.057 [-3.337, +6.521]; median -4.555; SD 43.583; mean w/o best 1% -2.778; positive 7.5% | CFD ATR n 281; mean +0.012 [-0.090, +0.126]; median -0.169; SD 0.958; mean w/o best 1% -0.057; positive 7.5%

#### Financing as a share of risk (G4; CFD, both pay), median by year
- +1 4-hour: 2021 +0.006R (n 35); 2022 +0.007R (n 53); 2023 +0.014R (n 60); 2024 +0.013R (n 55); 2025 +0.009R (n 54); 2026 +0.009R (n 29)
- +1 30-minute: 2021 +0.000R (n 27); 2022 +0.000R (n 41); 2023 +0.000R (n 52); 2024 +0.000R (n 48); 2025 +0.000R (n 49); 2026 +0.000R (n 25)
- +1 15-minute: 2021 +0.000R (n 31); 2022 +0.000R (n 49); 2023 +0.000R (n 58); 2024 +0.014R (n 51); 2025 +0.016R (n 52); 2026 +0.003R (n 28)
- +1 5-minute: 2021 +0.000R (n 34); 2022 +0.000R (n 53); 2023 +0.000R (n 59); 2024 +0.000R (n 54); 2025 +0.040R (n 53); 2026 +0.000R (n 28)
- +2 4-hour: 2021 +0.012R (n 35); 2022 +0.012R (n 53); 2023 +0.031R (n 60); 2024 +0.026R (n 55); 2025 +0.020R (n 54); 2026 +0.014R (n 29)
- +2 30-minute: 2021 +0.006R (n 29); 2022 +0.011R (n 48); 2023 +0.003R (n 56); 2024 +0.020R (n 51); 2025 +0.031R (n 51); 2026 +0.020R (n 27)
- +2 15-minute: 2021 +0.009R (n 31); 2022 +0.000R (n 50); 2023 +0.000R (n 58); 2024 +0.042R (n 51); 2025 +0.041R (n 52); 2026 +0.023R (n 28)
- +2 5-minute: 2021 +0.014R (n 34); 2022 +0.000R (n 53); 2023 +0.021R (n 59); 2024 +0.000R (n 54); 2025 +0.068R (n 53); 2026 +0.025R (n 28)
- +5 4-hour: 2021 +0.024R (n 35); 2022 +0.032R (n 53); 2023 +0.075R (n 60); 2024 +0.069R (n 55); 2025 +0.059R (n 54); 2026 +0.028R (n 29)
- +5 30-minute: 2021 +0.016R (n 29); 2022 +0.027R (n 49); 2023 +0.062R (n 57); 2024 +0.047R (n 51); 2025 +0.071R (n 52); 2026 +0.042R (n 27)
- +5 15-minute: 2021 +0.017R (n 31); 2022 +0.000R (n 50); 2023 +0.000R (n 58); 2024 +0.050R (n 51); 2025 +0.053R (n 52); 2026 +0.043R (n 28)
- +5 5-minute: 2021 +0.015R (n 34); 2022 +0.000R (n 53); 2023 +0.021R (n 59); 2024 +0.000R (n 54); 2025 +0.079R (n 53); 2026 +0.025R (n 28)
- +10 4-hour: 2021 +0.035R (n 35); 2022 +0.049R (n 53); 2023 +0.113R (n 60); 2024 +0.096R (n 55); 2025 +0.108R (n 54); 2026 +0.050R (n 29)
- +10 30-minute: 2021 +0.016R (n 29); 2022 +0.030R (n 49); 2023 +0.067R (n 57); 2024 +0.047R (n 51); 2025 +0.071R (n 52); 2026 +0.048R (n 27)
- +10 15-minute: 2021 +0.017R (n 31); 2022 +0.000R (n 50); 2023 +0.000R (n 58); 2024 +0.050R (n 51); 2025 +0.053R (n 52); 2026 +0.062R (n 28)
- +10 5-minute: 2021 +0.015R (n 34); 2022 +0.000R (n 53); 2023 +0.021R (n 59); 2024 +0.000R (n 54); 2025 +0.079R (n 53); 2026 +0.025R (n 28)

#### Volatility split (H3, required): net R per setup (missed 0R), CFD primary and futures primary
    low +1 4-hour: CFD n 102; mean +0.059 [-0.080, +0.214]; median +0.007; SD 0.741; mean w/o best 1% +0.033; positive 51.0% | futures n 102; mean +0.065 [-0.066, +0.219]; median +0.005; SD 0.740; mean w/o best 1% +0.040; positive 50.0%
    low +1 30-minute: CFD n 102; mean +0.033 [-0.169, +0.247]; median +0.000; SD 1.091; mean w/o best 1% -0.009; positive 41.2% | futures n 102; mean +0.041 [-0.155, +0.243]; median +0.000; SD 1.087; mean w/o best 1% -0.001; positive 41.2%
    low +1 15-minute: CFD n 102; mean -0.036 [-0.355, +0.404]; median -1.025; SD 1.955; mean w/o best 1% -0.138; positive 28.4% | futures n 102; mean -0.020 [-0.359, +0.409]; median -1.020; SD 1.951; mean w/o best 1% -0.122; positive 28.4%
    low +1 5-minute: CFD n 102; mean -0.214 [-0.589, +0.216]; median -1.082; SD 2.048; mean w/o best 1% -0.306; positive 23.5% | futures n 102; mean -0.163 [-0.528, +0.275]; median -1.049; SD 2.039; mean w/o best 1% -0.256; positive 23.5%
    low +2 4-hour: CFD n 102; mean +0.148 [-0.040, +0.361]; median +0.031; SD 1.075; mean w/o best 1% +0.094; positive 52.0% | futures n 102; mean +0.162 [-0.034, +0.375]; median +0.041; SD 1.075; mean w/o best 1% +0.109; positive 52.0%
    low +2 30-minute: CFD n 102; mean +0.232 [-0.124, +0.673]; median -0.371; SD 2.091; mean w/o best 1% +0.130; positive 37.3% | futures n 102; mean +0.257 [-0.121, +0.652]; median -0.369; SD 2.093; mean w/o best 1% +0.156; positive 38.2%
    low +2 15-minute: CFD n 102; mean +0.000 [-0.399, +0.506]; median -1.050; SD 2.334; mean w/o best 1% -0.134; positive 25.5% | futures n 102; mean +0.036 [-0.374, +0.525]; median -1.032; SD 2.360; mean w/o best 1% -0.098; positive 26.5%
    low +2 5-minute: CFD n 102; mean -0.410 [-0.762, -0.030]; median -1.093; SD 1.861; mean w/o best 1% -0.483; positive 17.6% | futures n 102; mean -0.344 [-0.686, +0.034]; median -1.054; SD 1.854; mean w/o best 1% -0.417; positive 17.6%
    low +5 4-hour: CFD n 102; mean +0.321 [+0.047, +0.625]; median +0.171; SD 1.503; mean w/o best 1% +0.267; positive 52.9% | futures n 102; mean +0.350 [+0.073, +0.643]; median +0.208; SD 1.511; mean w/o best 1% +0.296; positive 52.9%
    low +5 30-minute: CFD n 102; mean +0.606 [+0.008, +1.307]; median -1.036; SD 3.237; mean w/o best 1% +0.481; positive 30.4% | futures n 102; mean +0.651 [+0.053, +1.328]; median -1.022; SD 3.249; mean w/o best 1% +0.527; positive 30.4%
    low +5 15-minute: CFD n 102; mean +0.422 [-0.297, +1.286]; median -1.055; SD 4.165; mean w/o best 1% +0.143; positive 20.6% | futures n 102; mean +0.479 [-0.240, +1.372]; median -1.038; SD 4.222; mean w/o best 1% +0.196; positive 20.6%
    low +5 5-minute: CFD n 102; mean -0.715 [-1.022, -0.316]; median -1.115; SD 1.815; mean w/o best 1% -0.812; positive 8.8% | futures n 102; mean -0.630 [-0.943, -0.236]; median -1.064; SD 1.817; mean w/o best 1% -0.727; positive 8.8%
    low +10 4-hour: CFD n 102; mean +0.663 [+0.222, +1.151]; median -0.594; SD 2.304; mean w/o best 1% +0.568; positive 46.1% | futures n 102; mean +0.711 [+0.267, +1.175]; median -0.530; SD 2.323; mean w/o best 1% +0.614; positive 46.1%
    low +10 30-minute: CFD n 102; mean +1.122 [+0.272, +2.097]; median -1.045; SD 4.813; mean w/o best 1% +0.928; positive 26.5% | futures n 102; mean +1.195 [+0.301, +2.165]; median -1.026; SD 4.872; mean w/o best 1% +0.999; positive 26.5%
    low +10 15-minute: CFD n 102; mean +1.047 [+0.038, +2.142]; median -1.058; SD 5.349; mean w/o best 1% +0.820; positive 18.6% | futures n 102; mean +1.127 [+0.074, +2.219]; median -1.041; SD 5.461; mean w/o best 1% +0.897; positive 18.6%
    low +10 5-minute: CFD n 102; mean -0.636 [-1.026, -0.187]; median -1.119; SD 2.175; mean w/o best 1% -0.753; positive 7.8% | futures n 102; mean -0.542 [-0.920, -0.081]; median -1.066; SD 2.213; mean w/o best 1% -0.661; positive 7.8%
    mid +1 4-hour: CFD n 96; mean -0.052 [-0.176, +0.082]; median -0.052; SD 0.642; mean w/o best 1% -0.071; positive 46.9% | futures n 96; mean -0.046 [-0.174, +0.089]; median -0.056; SD 0.645; mean w/o best 1% -0.065; positive 46.9%
    mid +1 30-minute: CFD n 96; mean -0.059 [-0.310, +0.244]; median -0.280; SD 1.353; mean w/o best 1% -0.120; positive 30.2% | futures n 96; mean -0.047 [-0.301, +0.257]; median -0.277; SD 1.363; mean w/o best 1% -0.110; positive 30.2%
    mid +1 15-minute: CFD n 96; mean -0.249 [-0.508, +0.039]; median -1.036; SD 1.406; mean w/o best 1% -0.312; positive 26.0% | futures n 96; mean -0.229 [-0.489, +0.057]; median -1.023; SD 1.411; mean w/o best 1% -0.294; positive 26.0%
    mid +1 5-minute: CFD n 96; mean +0.125 [-0.405, +0.741]; median -1.076; SD 2.881; mean w/o best 1% -0.009; positive 22.9% | futures n 96; mean +0.168 [-0.380, +0.797]; median -1.052; SD 2.884; mean w/o best 1% +0.034; positive 22.9%
    mid +2 4-hour: CFD n 96; mean -0.087 [-0.228, +0.052]; median -0.102; SD 0.733; mean w/o best 1% -0.107; positive 38.5% | futures n 96; mean -0.077 [-0.218, +0.068]; median -0.096; SD 0.738; mean w/o best 1% -0.096; positive 38.5%
    mid +2 30-minute: CFD n 96; mean -0.095 [-0.404, +0.251]; median -1.018; SD 1.569; mean w/o best 1% -0.169; positive 28.1% | futures n 96; mean -0.077 [-0.364, +0.258]; median -1.011; SD 1.580; mean w/o best 1% -0.153; positive 28.1%
    mid +2 15-minute: CFD n 96; mean -0.221 [-0.544, +0.163]; median -1.045; SD 1.775; mean w/o best 1% -0.297; positive 20.8% | futures n 96; mean -0.194 [-0.521, +0.168]; median -1.027; SD 1.787; mean w/o best 1% -0.271; positive 20.8%
    mid +2 5-minute: CFD n 96; mean +0.110 [-0.484, +0.828]; median -1.086; SD 3.335; mean w/o best 1% -0.051; positive 17.7% | futures n 96; mean +0.158 [-0.435, +0.861]; median -1.055; SD 3.343; mean w/o best 1% -0.003; positive 17.7%
    mid +5 4-hour: CFD n 96; mean -0.001 [-0.194, +0.216]; median -0.131; SD 1.065; mean w/o best 1% -0.036; positive 46.9% | futures n 96; mean +0.021 [-0.198, +0.236]; median -0.108; SD 1.073; mean w/o best 1% -0.015; positive 46.9%
    mid +5 30-minute: CFD n 96; mean -0.109 [-0.454, +0.268]; median -1.030; SD 1.816; mean w/o best 1% -0.188; positive 22.9% | futures n 96; mean -0.076 [-0.421, +0.319]; median -1.020; SD 1.838; mean w/o best 1% -0.156; positive 22.9%
    mid +5 15-minute: CFD n 96; mean -0.037 [-0.507, +0.512]; median -1.050; SD 2.561; mean w/o best 1% -0.149; positive 16.7% | futures n 96; mean +0.007 [-0.469, +0.526]; median -1.030; SD 2.598; mean w/o best 1% -0.104; positive 16.7%
    mid +5 5-minute: CFD n 96; mean +0.153 [-0.654, +1.107]; median -1.100; SD 4.302; mean w/o best 1% -0.092; positive 11.5% | futures n 96; mean +0.226 [-0.536, +1.159]; median -1.061; SD 4.346; mean w/o best 1% -0.023; positive 11.5%
    mid +10 4-hour: CFD n 96; mean +0.149 [-0.160, +0.459]; median -1.000; SD 1.579; mean w/o best 1% +0.092; positive 44.8% | futures n 96; mean +0.185 [-0.120, +0.512]; median -0.973; SD 1.596; mean w/o best 1% +0.128; positive 44.8%
    mid +10 30-minute: CFD n 96; mean -0.003 [-0.456, +0.498]; median -1.036; SD 2.466; mean w/o best 1% -0.123; positive 18.8% | futures n 96; mean +0.045 [-0.430, +0.628]; median -1.025; SD 2.511; mean w/o best 1% -0.076; positive 18.8%
    mid +10 15-minute: CFD n 96; mean +0.038 [-0.598, +0.780]; median -1.055; SD 3.446; mean w/o best 1% -0.154; positive 11.5% | futures n 96; mean +0.101 [-0.543, +0.824]; median -1.032; SD 3.519; mean w/o best 1% -0.094; positive 11.5%
    mid +10 5-minute: CFD n 96; mean +0.529 [-0.511, +1.700]; median -1.103; SD 5.899; mean w/o best 1% +0.099; positive 10.4% | futures n 96; mean +0.624 [-0.483, +1.959]; median -1.062; SD 5.994; mean w/o best 1% +0.192; positive 10.4%
    high +1 4-hour: CFD n 88; mean +0.062 [-0.065, +0.190]; median -0.001; SD 0.600; mean w/o best 1% +0.046; positive 48.9% | futures n 88; mean +0.067 [-0.054, +0.192]; median +0.004; SD 0.599; mean w/o best 1% +0.051; positive 51.1%
    high +1 30-minute: CFD n 88; mean -0.027 [-0.250, +0.203]; median +0.000; SD 1.054; mean w/o best 1% -0.071; positive 34.1% | futures n 88; mean -0.019 [-0.234, +0.203]; median +0.000; SD 1.053; mean w/o best 1% -0.063; positive 34.1%
    high +1 15-minute: CFD n 88; mean +0.065 [-0.260, +0.403]; median -0.852; SD 1.695; mean w/o best 1% -0.023; positive 36.4% | futures n 88; mean +0.084 [-0.253, +0.446]; median -0.864; SD 1.696; mean w/o best 1% -0.005; positive 36.4%
    high +1 5-minute: CFD n 88; mean +0.256 [-0.263, +0.859]; median -1.056; SD 2.689; mean w/o best 1% +0.150; positive 25.0% | futures n 88; mean +0.308 [-0.240, +0.891]; median -1.024; SD 2.681; mean w/o best 1% +0.203; positive 25.0%
    high +2 4-hour: CFD n 88; mean +0.001 [-0.161, +0.182]; median -0.011; SD 0.810; mean w/o best 1% -0.025; positive 50.0% | futures n 88; mean +0.011 [-0.157, +0.183]; median -0.016; SD 0.807; mean w/o best 1% -0.014; positive 50.0%
    high +2 30-minute: CFD n 88; mean -0.042 [-0.356, +0.344]; median -0.824; SD 1.652; mean w/o best 1% -0.142; positive 34.1% | futures n 88; mean -0.028 [-0.321, +0.330]; median -0.811; SD 1.648; mean w/o best 1% -0.128; positive 34.1%
    high +2 15-minute: CFD n 88; mean +0.177 [-0.311, +0.742]; median -1.025; SD 2.518; mean w/o best 1% +0.025; positive 28.4% | futures n 88; mean +0.205 [-0.245, +0.757]; median -1.013; SD 2.527; mean w/o best 1% +0.052; positive 29.5%
    high +2 5-minute: CFD n 88; mean +0.523 [-0.195, +1.350]; median -1.063; SD 3.714; mean w/o best 1% +0.348; positive 22.7% | futures n 88; mean +0.584 [-0.132, +1.364]; median -1.029; SD 3.713; mean w/o best 1% +0.408; positive 22.7%
    high +5 4-hour: CFD n 88; mean +0.047 [-0.185, +0.279]; median -0.108; SD 1.128; mean w/o best 1% -0.005; positive 47.7% | futures n 88; mean +0.066 [-0.158, +0.316]; median -0.097; SD 1.129; mean w/o best 1% +0.014; positive 47.7%
    high +5 30-minute: CFD n 88; mean +0.141 [-0.434, +0.853]; median -1.027; SD 3.190; mean w/o best 1% -0.097; positive 22.7% | futures n 88; mean +0.168 [-0.405, +0.918]; median -1.018; SD 3.209; mean w/o best 1% -0.072; positive 22.7%
    high +5 15-minute: CFD n 88; mean +0.452 [-0.461, +1.598]; median -1.041; SD 4.992; mean w/o best 1% +0.135; positive 20.5% | futures n 88; mean +0.498 [-0.373, +1.690]; median -1.021; SD 5.016; mean w/o best 1% +0.179; positive 20.5%
    high +5 5-minute: CFD n 88; mean +0.556 [-0.498, +1.892]; median -1.086; SD 5.834; mean w/o best 1% +0.176; positive 13.6% | futures n 88; mean +0.644 [-0.413, +2.021]; median -1.037; SD 5.856; mean w/o best 1% +0.264; positive 13.6%
    high +10 4-hour: CFD n 88; mean -0.189 [-0.439, +0.078]; median -0.884; SD 1.224; mean w/o best 1% -0.244; positive 35.2% | futures n 88; mean -0.158 [-0.395, +0.106]; median -0.854; SD 1.229; mean w/o best 1% -0.213; positive 35.2%
    high +10 30-minute: CFD n 88; mean -0.393 [-0.768, +0.125]; median -1.037; SD 2.207; mean w/o best 1% -0.582; positive 12.5% | futures n 88; mean -0.354 [-0.731, +0.179]; median -1.025; SD 2.243; mean w/o best 1% -0.547; positive 12.5%
    high +10 15-minute: CFD n 88; mean -0.656 [-0.914, -0.368]; median -1.061; SD 1.385; mean w/o best 1% -0.736; positive 10.2% | futures n 88; mean -0.599 [-0.871, -0.295]; median -1.033; SD 1.393; mean w/o best 1% -0.680; positive 10.2%
    high +10 5-minute: CFD n 88; mean -0.849 [-1.195, -0.345]; median -1.123; SD 2.096; mean w/o best 1% -1.036; positive 3.4% | futures n 88; mean -0.751 [-1.094, -0.213]; median -1.059; SD 2.106; mean w/o best 1% -0.940; positive 3.4%

#### Ranking flip (J2): entries ranked by mean net R per setup, CFD primary vs futures primary
- +1: CFD 5-minute > 4-hour > 30-minute > 15-minute; futures 5-minute > 4-hour > 30-minute > 15-minute -> same order
- +2: CFD 5-minute > 30-minute > 4-hour > 15-minute; futures 5-minute > 30-minute > 4-hour > 15-minute -> same order
- +5: CFD 15-minute > 30-minute > 4-hour > 5-minute; futures 15-minute > 30-minute > 4-hour > 5-minute -> same order
- +10: CFD 30-minute > 4-hour > 15-minute > 5-minute; futures 30-minute > 4-hour > 15-minute > 5-minute -> same order

### short: 230 setups

#### CFD primary (both pay): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 230; mean -0.069 [-0.161, +0.021]; median -0.109; SD 0.692; mean w/o best 1% -0.093; positive 42.2%
- +1 30-minute: n 230; mean -0.035 [-0.195, +0.145]; median -0.009; SD 1.354; mean w/o best 1% -0.118; positive 28.3% | paired -0.134 [-0.289, +0.033]
- +1 15-minute: n 230; mean -0.052 [-0.349, +0.353]; median -1.027; SD 2.709; mean w/o best 1% -0.234; positive 25.7% | paired -0.061 [-0.339, +0.342]
- +1 5-minute: n 230; mean +0.191 [-0.394, +0.998]; median -1.073; SD 5.291; mean w/o best 1% -0.219; positive 18.7% | paired +0.237 [-0.329, +1.052]
- +2 4-hour: n 230; mean -0.099 [-0.200, +0.009]; median -0.153; SD 0.834; mean w/o best 1% -0.125; positive 39.6%
- +2 30-minute: n 230; mean -0.016 [-0.243, +0.230]; median -1.012; SD 1.827; mean w/o best 1% -0.103; positive 26.5% | paired -0.044 [-0.250, +0.185]
- +2 15-minute: n 230; mean -0.098 [-0.420, +0.319]; median -1.037; SD 2.888; mean w/o best 1% -0.296; positive 20.9% | paired -0.073 [-0.372, +0.327]
- +2 5-minute: n 230; mean +0.159 [-0.408, +0.907]; median -1.077; SD 5.194; mean w/o best 1% -0.215; positive 13.9% | paired +0.233 [-0.291, +0.953]
- +5 4-hour: n 230; mean -0.127 [-0.276, +0.026]; median -0.461; SD 1.182; mean w/o best 1% -0.180; positive 34.8%
- +5 30-minute: n 230; mean -0.032 [-0.349, +0.343]; median -1.027; SD 2.693; mean w/o best 1% -0.204; positive 18.3% | paired -0.041 [-0.333, +0.315]
- +5 15-minute: n 230; mean -0.197 [-0.479, +0.120]; median -1.044; SD 2.335; mean w/o best 1% -0.317; positive 15.2% | paired -0.145 [-0.393, +0.139]
- +5 5-minute: n 230; mean +0.103 [-0.442, +0.781]; median -1.086; SD 4.708; mean w/o best 1% -0.215; positive 10.4% | paired +0.205 [-0.310, +0.822]
- +10 4-hour: n 230; mean -0.231 [-0.384, -0.063]; median -1.012; SD 1.247; mean w/o best 1% -0.275; positive 30.0%
- +10 30-minute: n 230; mean -0.174 [-0.467, +0.169]; median -1.031; SD 2.442; mean w/o best 1% -0.309; positive 13.0% | paired -0.086 [-0.383, +0.234]
- +10 15-minute: n 230; mean -0.397 [-0.650, -0.103]; median -1.049; SD 2.146; mean w/o best 1% -0.503; positive 10.9% | paired -0.249 [-0.492, +0.013]
- +10 5-minute: n 230; mean -0.248 [-0.695, +0.249]; median -1.089; SD 3.895; mean w/o best 1% -0.499; positive 7.4% | paired -0.050 [-0.463, +0.453]

#### CFD stress (hour p90 spread): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 230; mean -0.074 [-0.160, +0.020]; median -0.111; SD 0.692; mean w/o best 1% -0.097; positive 42.2%
- +1 30-minute: n 230; mean -0.044 [-0.212, +0.157]; median -0.031; SD 1.353; mean w/o best 1% -0.127; positive 27.0% | paired -0.142 [-0.291, +0.043]
- +1 15-minute: n 230; mean -0.069 [-0.369, +0.322]; median -1.036; SD 2.706; mean w/o best 1% -0.251; positive 25.7% | paired -0.075 [-0.349, +0.284]
- +1 5-minute: n 230; mean +0.161 [-0.397, +0.931]; median -1.090; SD 5.283; mean w/o best 1% -0.249; positive 18.3% | paired +0.210 [-0.353, +0.957]
- +2 4-hour: n 230; mean -0.103 [-0.206, +0.013]; median -0.155; SD 0.834; mean w/o best 1% -0.129; positive 39.1%
- +2 30-minute: n 230; mean -0.026 [-0.244, +0.222]; median -1.016; SD 1.825; mean w/o best 1% -0.112; positive 26.5% | paired -0.051 [-0.261, +0.163]
- +2 15-minute: n 230; mean -0.114 [-0.438, +0.346]; median -1.048; SD 2.885; mean w/o best 1% -0.312; positive 20.9% | paired -0.087 [-0.390, +0.300]
- +2 5-minute: n 230; mean +0.128 [-0.421, +0.913]; median -1.095; SD 5.185; mean w/o best 1% -0.245; positive 13.9% | paired +0.206 [-0.336, +0.913]
- +5 4-hour: n 230; mean -0.131 [-0.274, +0.036]; median -0.465; SD 1.182; mean w/o best 1% -0.184; positive 34.8%
- +5 30-minute: n 230; mean -0.041 [-0.358, +0.350]; median -1.033; SD 2.690; mean w/o best 1% -0.214; positive 18.3% | paired -0.048 [-0.348, +0.335]
- +5 15-minute: n 230; mean -0.213 [-0.484, +0.101]; median -1.054; SD 2.335; mean w/o best 1% -0.333; positive 15.2% | paired -0.159 [-0.382, +0.113]
- +5 5-minute: n 230; mean +0.073 [-0.485, +0.716]; median -1.112; SD 4.704; mean w/o best 1% -0.245; positive 10.4% | paired +0.178 [-0.322, +0.796]
- +10 4-hour: n 230; mean -0.235 [-0.395, -0.076]; median -1.015; SD 1.247; mean w/o best 1% -0.279; positive 29.6%
- +10 30-minute: n 230; mean -0.184 [-0.470, +0.144]; median -1.038; SD 2.440; mean w/o best 1% -0.319; positive 13.0% | paired -0.093 [-0.389, +0.214]
- +10 15-minute: n 230; mean -0.413 [-0.669, -0.129]; median -1.060; SD 2.146; mean w/o best 1% -0.519; positive 10.9% | paired -0.262 [-0.511, -0.007]
- +10 5-minute: n 230; mean -0.278 [-0.753, +0.289]; median -1.117; SD 3.892; mean w/o best 1% -0.528; positive 7.4% | paired -0.077 [-0.488, +0.404]

#### CFD side: shorts receive: net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 230; mean -0.062 [-0.148, +0.032]; median -0.103; SD 0.692; mean w/o best 1% -0.085; positive 42.2%
- +1 30-minute: n 230; mean -0.031 [-0.198, +0.152]; median -0.008; SD 1.355; mean w/o best 1% -0.114; positive 28.7% | paired -0.138 [-0.294, +0.030]
- +1 15-minute: n 230; mean -0.043 [-0.330, +0.342]; median -1.021; SD 2.711; mean w/o best 1% -0.225; positive 26.1% | paired -0.060 [-0.356, +0.336]
- +1 5-minute: n 230; mean +0.219 [-0.355, +1.002]; median -1.049; SD 5.298; mean w/o best 1% -0.192; positive 18.7% | paired +0.257 [-0.303, +0.990]
- +2 4-hour: n 230; mean -0.084 [-0.185, +0.023]; median -0.143; SD 0.837; mean w/o best 1% -0.110; positive 40.9%
- +2 30-minute: n 230; mean -0.003 [-0.227, +0.244]; median -0.990; SD 1.836; mean w/o best 1% -0.089; positive 26.5% | paired -0.044 [-0.249, +0.172]
- +2 15-minute: n 230; mean -0.077 [-0.400, +0.363]; median -1.025; SD 2.897; mean w/o best 1% -0.275; positive 20.9% | paired -0.067 [-0.371, +0.336]
- +2 5-minute: n 230; mean +0.197 [-0.354, +0.913]; median -1.051; SD 5.211; mean w/o best 1% -0.179; positive 13.9% | paired +0.257 [-0.268, +1.019]
- +5 4-hour: n 230; mean -0.097 [-0.243, +0.060]; median -0.440; SD 1.192; mean w/o best 1% -0.150; positive 37.0%
- +5 30-minute: n 230; mean -0.003 [-0.312, +0.395]; median -1.008; SD 2.715; mean w/o best 1% -0.177; positive 18.3% | paired -0.041 [-0.349, +0.340]
- +5 15-minute: n 230; mean -0.161 [-0.446, +0.155]; median -1.026; SD 2.366; mean w/o best 1% -0.283; positive 15.7% | paired -0.140 [-0.385, +0.131]
- +5 5-minute: n 230; mean +0.165 [-0.396, +0.866]; median -1.053; SD 4.801; mean w/o best 1% -0.161; positive 10.4% | paired +0.238 [-0.300, +0.879]
- +10 4-hour: n 230; mean -0.181 [-0.335, -0.008]; median -0.976; SD 1.266; mean w/o best 1% -0.225; positive 31.3%
- +10 30-minute: n 230; mean -0.127 [-0.432, +0.230]; median -1.011; SD 2.506; mean w/o best 1% -0.267; positive 13.5% | paired -0.088 [-0.379, +0.250]
- +10 15-minute: n 230; mean -0.346 [-0.601, -0.037]; median -1.027; SD 2.200; mean w/o best 1% -0.453; positive 10.9% | paired -0.247 [-0.498, +0.031]
- +10 5-minute: n 230; mean -0.167 [-0.616, +0.346]; median -1.053; SD 3.943; mean w/o best 1% -0.420; positive 7.8% | paired -0.018 [-0.456, +0.519]

#### futures primary (basis carry): net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 230; mean -0.049 [-0.142, +0.040]; median -0.098; SD 0.694; mean w/o best 1% -0.073; positive 42.6%
- +1 30-minute: n 230; mean -0.014 [-0.180, +0.172]; median +0.000; SD 1.357; mean w/o best 1% -0.098; positive 29.1% | paired -0.129 [-0.293, +0.048]
- +1 15-minute: n 230; mean -0.012 [-0.304, +0.384]; median -1.002; SD 2.717; mean w/o best 1% -0.194; positive 26.1% | paired -0.038 [-0.309, +0.358]
- +1 5-minute: n 230; mean +0.274 [-0.311, +1.038]; median -1.022; SD 5.335; mean w/o best 1% -0.142; positive 18.7% | paired +0.302 [-0.259, +1.087]
- +2 4-hour: n 230; mean -0.066 [-0.173, +0.046]; median -0.122; SD 0.839; mean w/o best 1% -0.093; positive 42.2%
- +2 30-minute: n 230; mean +0.022 [-0.192, +0.285]; median -0.953; SD 1.845; mean w/o best 1% -0.065; positive 26.5% | paired -0.034 [-0.239, +0.179]
- +2 15-minute: n 230; mean -0.041 [-0.362, +0.394]; median -1.004; SD 2.909; mean w/o best 1% -0.240; positive 21.3% | paired -0.046 [-0.341, +0.378]
- +2 5-minute: n 230; mean +0.259 [-0.318, +1.023]; median -1.023; SD 5.258; mean w/o best 1% -0.123; positive 13.9% | paired +0.303 [-0.247, +1.040]
- +5 4-hour: n 230; mean -0.070 [-0.227, +0.087]; median -0.397; SD 1.200; mean w/o best 1% -0.124; positive 38.3%
- +5 30-minute: n 230; mean +0.033 [-0.274, +0.435]; median -0.990; SD 2.740; mean w/o best 1% -0.142; positive 18.3% | paired -0.028 [-0.335, +0.344]
- +5 15-minute: n 230; mean -0.112 [-0.404, +0.207]; median -1.006; SD 2.398; mean w/o best 1% -0.235; positive 15.7% | paired -0.115 [-0.380, +0.162]
- +5 5-minute: n 230; mean +0.240 [-0.343, +0.936]; median -1.023; SD 4.880; mean w/o best 1% -0.090; positive 10.4% | paired +0.288 [-0.245, +0.926]
- +10 4-hour: n 230; mean -0.142 [-0.302, +0.021]; median -0.926; SD 1.284; mean w/o best 1% -0.186; positive 33.5%
- +10 30-minute: n 230; mean -0.079 [-0.398, +0.285]; median -0.991; SD 2.562; mean w/o best 1% -0.221; positive 13.5% | paired -0.075 [-0.388, +0.261]
- +10 15-minute: n 230; mean -0.285 [-0.557, +0.033]; median -1.006; SD 2.262; mean w/o best 1% -0.394; positive 10.9% | paired -0.223 [-0.493, +0.069]
- +10 5-minute: n 230; mean -0.074 [-0.541, +0.456]; median -1.023; SD 4.039; mean w/o best 1% -0.329; positive 8.3% | paired +0.039 [-0.403, +0.595]

#### futures side: no carry: net R per setup (missed 0R); paired vs 4-hour
- +1 4-hour: n 230; mean -0.059 [-0.144, +0.034]; median -0.102; SD 0.692; mean w/o best 1% -0.083; positive 42.2%
- +1 30-minute: n 230; mean -0.022 [-0.186, +0.163]; median -0.004; SD 1.355; mean w/o best 1% -0.105; positive 28.7% | paired -0.129 [-0.286, +0.052]
- +1 15-minute: n 230; mean -0.026 [-0.310, +0.370]; median -1.010; SD 2.713; mean w/o best 1% -0.209; positive 26.1% | paired -0.043 [-0.330, +0.344]
- +1 5-minute: n 230; mean +0.247 [-0.327, +1.046]; median -1.037; SD 5.305; mean w/o best 1% -0.165; positive 18.7% | paired +0.284 [-0.288, +1.051]
- +2 4-hour: n 230; mean -0.083 [-0.189, +0.027]; median -0.147; SD 0.835; mean w/o best 1% -0.110; positive 40.4%
- +2 30-minute: n 230; mean +0.005 [-0.224, +0.250]; median -1.003; SD 1.834; mean w/o best 1% -0.082; positive 26.5% | paired -0.035 [-0.234, +0.189]
- +2 15-minute: n 230; mean -0.064 [-0.377, +0.357]; median -1.017; SD 2.899; mean w/o best 1% -0.263; positive 20.9% | paired -0.053 [-0.357, +0.360]
- +2 5-minute: n 230; mean +0.222 [-0.355, +0.965]; median -1.038; SD 5.219; mean w/o best 1% -0.155; positive 13.9% | paired +0.283 [-0.259, +0.981]
- +5 4-hour: n 230; mean -0.102 [-0.253, +0.053]; median -0.436; SD 1.189; mean w/o best 1% -0.155; positive 37.0%
- +5 30-minute: n 230; mean +0.000 [-0.324, +0.404]; median -1.008; SD 2.712; mean w/o best 1% -0.173; positive 18.3% | paired -0.031 [-0.336, +0.348]
- +5 15-minute: n 230; mean -0.151 [-0.428, +0.168]; median -1.018; SD 2.364; mean w/o best 1% -0.272; positive 15.2% | paired -0.124 [-0.385, +0.157]
- +5 5-minute: n 230; mean +0.183 [-0.377, +0.872]; median -1.039; SD 4.775; mean w/o best 1% -0.139; positive 10.4% | paired +0.262 [-0.267, +0.869]
- +10 4-hour: n 230; mean -0.192 [-0.348, -0.030]; median -1.002; SD 1.264; mean w/o best 1% -0.237; positive 31.3%
- +10 30-minute: n 230; mean -0.129 [-0.419, +0.211]; median -1.010; SD 2.493; mean w/o best 1% -0.266; positive 13.5% | paired -0.076 [-0.378, +0.249]
- +10 15-minute: n 230; mean -0.339 [-0.606, -0.050]; median -1.019; SD 2.205; mean w/o best 1% -0.446; positive 10.9% | paired -0.227 [-0.478, +0.049]
- +10 5-minute: n 230; mean -0.151 [-0.624, +0.413]; median -1.040; SD 3.982; mean w/o best 1% -0.405; positive 7.4% | paired +0.011 [-0.434, +0.516]

#### Position-size-free: net dollars an ounce per trade (CFD primary; futures primary); net daily ATR (CFD primary)
- +1 4-hour: CFD $n 230; mean -1.975 [-6.613, +3.317]; median -5.504; SD 39.559; mean w/o best 1% -3.823; positive 42.2% | futures $n 230; mean -1.089 [-6.104, +4.397]; median -4.805; SD 39.633; mean w/o best 1% -2.950; positive 42.6% | CFD ATR n 230; mean -0.055 [-0.158, +0.049]; median -0.178; SD 0.819; mean w/o best 1% -0.085; positive 42.2%
- +1 30-minute: CFD $n 181; mean -1.345 [-5.465, +2.800]; median -4.465; SD 28.469; mean w/o best 1% -3.091; positive 35.9% | futures $n 181; mean -0.856 [-5.061, +3.419]; median -4.291; SD 28.539; mean w/o best 1% -2.616; positive 37.0% | CFD ATR n 181; mean -0.015 [-0.103, +0.076]; median -0.183; SD 0.624; mean w/o best 1% -0.048; positive 35.9%
- +1 15-minute: CFD $n 212; mean -0.260 [-3.875, +3.767]; median -4.939; SD 27.417; mean w/o best 1% -2.057; positive 27.8% | futures $n 212; mean +0.264 [-3.137, +4.449]; median -4.736; SD 27.536; mean w/o best 1% -1.544; positive 28.3% | CFD ATR n 212; mean -0.007 [-0.078, +0.073]; median -0.184; SD 0.564; mean w/o best 1% -0.038; positive 27.8%
- +1 5-minute: CFD $n 223; mean +0.472 [-2.576, +4.073]; median -3.560; SD 25.943; mean w/o best 1% -1.342; positive 19.3% | futures $n 223; mean +0.986 [-1.957, +4.852]; median -3.260; SD 26.138; mean w/o best 1% -0.838; positive 19.3% | CFD ATR n 223; mean -0.007 [-0.074, +0.068]; median -0.127; SD 0.531; mean w/o best 1% -0.036; positive 19.3%
- +2 4-hour: CFD $n 230; mean -2.999 [-9.540, +4.109]; median -7.606; SD 50.745; mean w/o best 1% -5.358; positive 39.6% | futures $n 230; mean -1.605 [-8.021, +5.152]; median -6.821; SD 50.888; mean w/o best 1% -3.980; positive 42.2% | CFD ATR n 230; mean -0.093 [-0.224, +0.035]; median -0.246; SD 0.988; mean w/o best 1% -0.128; positive 39.6%
- +2 30-minute: CFD $n 199; mean -2.811 [-9.577, +4.115]; median -6.893; SD 49.144; mean w/o best 1% -5.153; positive 30.7% | futures $n 199; mean -2.040 [-8.844, +4.609]; median -6.385; SD 49.305; mean w/o best 1% -4.397; positive 30.7% | CFD ATR n 199; mean -0.059 [-0.162, +0.050]; median -0.266; SD 0.762; mean w/o best 1% -0.094; positive 30.7%
- +2 15-minute: CFD $n 214; mean -0.996 [-6.168, +4.403]; median -5.920; SD 38.851; mean w/o best 1% -3.353; positive 22.4% | futures $n 214; mean -0.265 [-5.288, +5.179]; median -5.583; SD 39.100; mean w/o best 1% -2.637; positive 22.9% | CFD ATR n 214; mean -0.014 [-0.098, +0.076]; median -0.221; SD 0.660; mean w/o best 1% -0.048; positive 22.4%
- +2 5-minute: CFD $n 223; mean -0.271 [-4.396, +5.040]; median -4.144; SD 35.120; mean w/o best 1% -2.566; positive 14.3% | futures $n 223; mean +0.363 [-3.766, +5.559]; median -3.677; SD 35.425; mean w/o best 1% -1.953; positive 14.3% | CFD ATR n 223; mean -0.013 [-0.088, +0.067]; median -0.139; SD 0.587; mean w/o best 1% -0.044; positive 14.3%
- +5 4-hour: CFD $n 230; mean -5.025 [-14.481, +4.840]; median -15.936; SD 74.041; mean w/o best 1% -9.092; positive 34.8% | futures $n 230; mean -2.474 [-11.558, +8.030]; median -14.698; SD 74.583; mean w/o best 1% -6.577; positive 38.3% | CFD ATR n 230; mean -0.175 [-0.350, -0.001]; median -0.621; SD 1.356; mean w/o best 1% -0.228; positive 34.8%
- +5 30-minute: CFD $n 200; mean -3.448 [-12.924, +6.564]; median -9.548; SD 70.681; mean w/o best 1% -8.089; positive 21.0% | futures $n 200; mean -2.137 [-11.490, +7.377]; median -8.908; SD 71.332; mean w/o best 1% -6.821; positive 21.0% | CFD ATR n 200; mean -0.130 [-0.263, +0.017]; median -0.312; SD 1.008; mean w/o best 1% -0.182; positive 21.0%
- +5 15-minute: CFD $n 215; mean +0.268 [-6.476, +8.075]; median -6.592; SD 54.626; mean w/o best 1% -3.763; positive 16.3% | futures $n 215; mean +1.390 [-5.187, +9.391]; median -6.305; SD 55.424; mean w/o best 1% -2.692; positive 16.7% | CFD ATR n 215; mean -0.016 [-0.129, +0.108]; median -0.245; SD 0.866; mean w/o best 1% -0.068; positive 16.3%
- +5 5-minute: CFD $n 223; mean +0.151 [-5.827, +7.392]; median -4.596; SD 50.802; mean w/o best 1% -3.889; positive 10.8% | futures $n 223; mean +1.025 [-5.106, +8.102]; median -4.355; SD 51.472; mean w/o best 1% -3.066; positive 10.8% | CFD ATR n 223; mean -0.015 [-0.104, +0.077]; median -0.155; SD 0.709; mean w/o best 1% -0.054; positive 10.8%
- +10 4-hour: CFD $n 230; mean -15.461 [-24.985, -5.090]; median -22.223; SD 75.596; mean w/o best 1% -19.074; positive 30.0% | futures $n 230; mean -11.410 [-21.013, -1.494]; median -19.675; SD 76.410; mean w/o best 1% -15.093; positive 33.5% | CFD ATR n 230; mean -0.328 [-0.517, -0.140]; median -0.836; SD 1.486; mean w/o best 1% -0.373; positive 30.0%
- +10 30-minute: CFD $n 200; mean -9.427 [-17.717, -0.914]; median -11.105; SD 62.205; mean w/o best 1% -13.187; positive 15.0% | futures $n 200; mean -7.513 [-16.335, +1.768]; median -10.191; SD 63.372; mean w/o best 1% -11.366; positive 15.5% | CFD ATR n 200; mean -0.232 [-0.358, -0.092]; median -0.360; SD 0.982; mean w/o best 1% -0.270; positive 15.0%
- +10 15-minute: CFD $n 215; mean -4.408 [-10.459, +3.041]; median -7.428; SD 48.911; mean w/o best 1% -7.789; positive 11.6% | futures $n 215; mean -2.821 [-8.943, +4.412]; median -6.798; SD 50.220; mean w/o best 1% -6.295; positive 11.6% | CFD ATR n 215; mean -0.116 [-0.210, -0.014]; median -0.258; SD 0.746; mean w/o best 1% -0.151; positive 11.6%
- +10 5-minute: CFD $n 223; mean -2.267 [-7.199, +4.332]; median -4.820; SD 45.434; mean w/o best 1% -5.762; positive 7.6% | futures $n 223; mean -1.136 [-6.333, +5.984]; median -4.509; SD 46.594; mean w/o best 1% -4.729; positive 8.5% | CFD ATR n 223; mean -0.063 [-0.144, +0.031]; median -0.160; SD 0.661; mean w/o best 1% -0.097; positive 7.6%

#### Financing as a share of risk (G4; CFD, both pay), median by year
- +1 4-hour: 2021 +0.005R (n 27); 2022 +0.004R (n 55); 2023 +0.006R (n 45); 2024 +0.005R (n 39); 2025 +0.004R (n 37); 2026 +0.003R (n 27)
- +1 30-minute: 2021 +0.000R (n 21); 2022 +0.000R (n 43); 2023 +0.000R (n 38); 2024 +0.000R (n 29); 2025 +0.000R (n 31); 2026 +0.000R (n 19)
- +1 15-minute: 2021 +0.000R (n 25); 2022 +0.000R (n 50); 2023 +0.000R (n 41); 2024 +0.000R (n 33); 2025 +0.000R (n 36); 2026 +0.002R (n 27)
- +1 5-minute: 2021 +0.011R (n 26); 2022 +0.002R (n 52); 2023 +0.000R (n 45); 2024 +0.000R (n 37); 2025 +0.012R (n 36); 2026 +0.009R (n 27)
- +2 4-hour: 2021 +0.011R (n 27); 2022 +0.008R (n 55); 2023 +0.012R (n 45); 2024 +0.011R (n 39); 2025 +0.006R (n 37); 2026 +0.006R (n 27)
- +2 30-minute: 2021 +0.000R (n 24); 2022 +0.008R (n 45); 2023 +0.006R (n 41); 2024 +0.009R (n 32); 2025 +0.006R (n 32); 2026 +0.001R (n 25)
- +2 15-minute: 2021 +0.000R (n 25); 2022 +0.010R (n 50); 2023 +0.014R (n 42); 2024 +0.000R (n 34); 2025 +0.000R (n 36); 2026 +0.008R (n 27)
- +2 5-minute: 2021 +0.011R (n 26); 2022 +0.003R (n 52); 2023 +0.000R (n 45); 2024 +0.000R (n 37); 2025 +0.014R (n 36); 2026 +0.010R (n 27)
- +5 4-hour: 2021 +0.023R (n 27); 2022 +0.021R (n 55); 2023 +0.028R (n 45); 2024 +0.020R (n 39); 2025 +0.017R (n 37); 2026 +0.012R (n 27)
- +5 30-minute: 2021 +0.007R (n 24); 2022 +0.015R (n 45); 2023 +0.018R (n 41); 2024 +0.012R (n 33); 2025 +0.008R (n 32); 2026 +0.010R (n 25)
- +5 15-minute: 2021 +0.000R (n 25); 2022 +0.014R (n 50); 2023 +0.019R (n 42); 2024 +0.000R (n 35); 2025 +0.000R (n 36); 2026 +0.013R (n 27)
- +5 5-minute: 2021 +0.011R (n 26); 2022 +0.005R (n 52); 2023 +0.000R (n 45); 2024 +0.000R (n 37); 2025 +0.016R (n 36); 2026 +0.010R (n 27)
- +10 4-hour: 2021 +0.028R (n 27); 2022 +0.032R (n 55); 2023 +0.044R (n 45); 2024 +0.030R (n 39); 2025 +0.020R (n 37); 2026 +0.017R (n 27)
- +10 30-minute: 2021 +0.007R (n 24); 2022 +0.015R (n 45); 2023 +0.018R (n 41); 2024 +0.012R (n 33); 2025 +0.008R (n 32); 2026 +0.013R (n 25)
- +10 15-minute: 2021 +0.000R (n 25); 2022 +0.014R (n 50); 2023 +0.019R (n 42); 2024 +0.000R (n 35); 2025 +0.000R (n 36); 2026 +0.016R (n 27)
- +10 5-minute: 2021 +0.011R (n 26); 2022 +0.005R (n 52); 2023 +0.000R (n 45); 2024 +0.000R (n 37); 2025 +0.016R (n 36); 2026 +0.010R (n 27)

#### Volatility split (H3, required): net R per setup (missed 0R), CFD primary and futures primary
    low +1 4-hour: CFD n 71; mean -0.093 [-0.256, +0.088]; median -0.063; SD 0.772; mean w/o best 1% -0.132; positive 46.5% | futures n 71; mean -0.068 [-0.240, +0.124]; median -0.044; SD 0.776; mean w/o best 1% -0.108; positive 46.5%
    low +1 30-minute: CFD n 71; mean -0.156 [-0.439, +0.237]; median -0.319; SD 1.416; mean w/o best 1% -0.290; positive 19.7% | futures n 71; mean -0.132 [-0.423, +0.237]; median -0.291; SD 1.420; mean w/o best 1% -0.266; positive 19.7%
    low +1 15-minute: CFD n 71; mean +0.130 [-0.567, +1.179]; median -1.044; SD 4.307; mean w/o best 1% -0.359; positive 19.7% | futures n 71; mean +0.177 [-0.517, +1.343]; median -1.006; SD 4.319; mean w/o best 1% -0.313; positive 21.1%
    low +1 5-minute: CFD n 71; mean +0.473 [-0.693, +2.500]; median -1.102; SD 7.749; mean w/o best 1% -0.423; positive 18.3% | futures n 71; mean +0.564 [-0.625, +2.930]; median -1.040; SD 7.774; mean w/o best 1% -0.335; positive 18.3%
    low +2 4-hour: CFD n 71; mean -0.116 [-0.314, +0.114]; median -0.211; SD 0.914; mean w/o best 1% -0.163; positive 38.0% | futures n 71; mean -0.078 [-0.283, +0.155]; median -0.176; SD 0.923; mean w/o best 1% -0.126; positive 40.8%
    low +2 30-minute: CFD n 71; mean -0.263 [-0.590, +0.127]; median -1.024; SD 1.561; mean w/o best 1% -0.400; positive 16.9% | futures n 71; mean -0.223 [-0.540, +0.190]; median -0.987; SD 1.575; mean w/o best 1% -0.360; positive 16.9%
    low +2 15-minute: CFD n 71; mean +0.152 [-0.612, +1.390]; median -1.056; SD 4.437; mean w/o best 1% -0.339; positive 16.9% | futures n 71; mean +0.216 [-0.547, +1.364]; median -1.009; SD 4.466; mean w/o best 1% -0.277; positive 16.9%
    low +2 5-minute: CFD n 71; mean +0.539 [-0.739, +2.643]; median -1.111; SD 7.918; mean w/o best 1% -0.362; positive 12.7% | futures n 71; mean +0.652 [-0.628, +2.808]; median -1.040; SD 7.969; mean w/o best 1% -0.252; positive 12.7%
    low +5 4-hour: CFD n 71; mean -0.186 [-0.483, +0.155]; median -1.012; SD 1.358; mean w/o best 1% -0.273; positive 31.0% | futures n 71; mean -0.116 [-0.390, +0.239]; median -0.919; SD 1.390; mean w/o best 1% -0.205; positive 33.8%
    low +5 30-minute: CFD n 71; mean -0.500 [-0.805, -0.105]; median -1.043; SD 1.518; mean w/o best 1% -0.632; positive 9.9% | futures n 71; mean -0.435 [-0.751, -0.002]; median -0.997; SD 1.561; mean w/o best 1% -0.571; positive 9.9%
    low +5 15-minute: CFD n 71; mean -0.163 [-0.687, +0.524]; median -1.062; SD 2.705; mean w/o best 1% -0.395; positive 12.7% | futures n 71; mean -0.061 [-0.641, +0.680]; median -1.009; SD 2.798; mean w/o best 1% -0.300; positive 12.7%
    low +5 5-minute: CFD n 71; mean -0.139 [-0.895, +0.820]; median -1.124; SD 3.791; mean w/o best 1% -0.434; positive 8.5% | futures n 71; mean +0.021 [-0.744, +1.037]; median -1.040; SD 3.950; mean w/o best 1% -0.280; positive 8.5%
    low +10 4-hour: CFD n 71; mean -0.233 [-0.500, +0.087]; median -1.019; SD 1.305; mean w/o best 1% -0.313; positive 25.4% | futures n 71; mean -0.123 [-0.423, +0.197]; median -0.929; SD 1.360; mean w/o best 1% -0.202; positive 36.6%
    low +10 30-minute: CFD n 71; mean -0.612 [-0.869, -0.284]; median -1.047; SD 1.251; mean w/o best 1% -0.699; positive 5.6% | futures n 71; mean -0.527 [-0.786, -0.182]; median -1.000; SD 1.346; mean w/o best 1% -0.620; positive 5.6%
    low +10 15-minute: CFD n 71; mean -0.581 [-0.921, -0.140]; median -1.066; SD 1.771; mean w/o best 1% -0.724; positive 5.6% | futures n 71; mean -0.450 [-0.819, +0.032]; median -1.009; SD 1.922; mean w/o best 1% -0.605; positive 5.6%
    low +10 5-minute: CFD n 71; mean -0.515 [-1.039, +0.203]; median -1.124; SD 2.729; mean w/o best 1% -0.774; positive 5.6% | futures n 71; mean -0.320 [-0.890, +0.462]; median -1.040; SD 2.957; mean w/o best 1% -0.601; positive 7.0%
    mid +1 4-hour: CFD n 74; mean -0.004 [-0.166, +0.182]; median -0.132; SD 0.770; mean w/o best 1% -0.033; positive 41.9% | futures n 74; mean +0.019 [-0.144, +0.197]; median -0.123; SD 0.770; mean w/o best 1% -0.011; positive 41.9%
    mid +1 30-minute: CFD n 74; mean +0.155 [-0.180, +0.596]; median +0.000; SD 1.693; mean w/o best 1% +0.025; positive 33.8% | futures n 74; mean +0.176 [-0.169, +0.596]; median +0.000; SD 1.698; mean w/o best 1% +0.045; positive 35.1%
    mid +1 15-minute: CFD n 74; mean -0.018 [-0.396, +0.399]; median -1.026; SD 1.661; mean w/o best 1% -0.107; positive 29.7% | futures n 74; mean +0.024 [-0.339, +0.432]; median -1.008; SD 1.668; mean w/o best 1% -0.065; positive 29.7%
    mid +1 5-minute: CFD n 74; mean +0.594 [-0.427, +1.777]; median -1.088; SD 5.006; mean w/o best 1% +0.181; positive 18.9% | futures n 74; mean +0.698 [-0.305, +2.012]; median -1.020; SD 5.105; mean w/o best 1% +0.270; positive 18.9%
    mid +2 4-hour: CFD n 74; mean -0.108 [-0.300, +0.108]; median -0.328; SD 0.897; mean w/o best 1% -0.142; positive 37.8% | futures n 74; mean -0.070 [-0.278, +0.142]; median -0.295; SD 0.900; mean w/o best 1% -0.104; positive 40.5%
    mid +2 30-minute: CFD n 74; mean +0.185 [-0.288, +0.704]; median -1.022; SD 2.197; mean w/o best 1% +0.061; positive 28.4% | futures n 74; mean +0.231 [-0.225, +0.764]; median -0.971; SD 2.224; mean w/o best 1% +0.104; positive 28.4%
    mid +2 15-minute: CFD n 74; mean -0.124 [-0.505, +0.341]; median -1.044; SD 1.859; mean w/o best 1% -0.233; positive 23.0% | futures n 74; mean -0.058 [-0.457, +0.401]; median -1.011; SD 1.890; mean w/o best 1% -0.170; positive 24.3%
    mid +2 5-minute: CFD n 74; mean +0.475 [-0.391, +1.563]; median -1.094; SD 4.380; mean w/o best 1% +0.181; positive 14.9% | futures n 74; mean +0.603 [-0.321, +1.732]; median -1.022; SD 4.508; mean w/o best 1% +0.289; positive 14.9%
    mid +5 4-hour: CFD n 74; mean -0.127 [-0.359, +0.136]; median -0.532; SD 1.109; mean w/o best 1% -0.181; positive 39.2% | futures n 74; mean -0.067 [-0.302, +0.201]; median -0.485; SD 1.122; mean w/o best 1% -0.121; positive 40.5%
    mid +5 30-minute: CFD n 74; mean +0.081 [-0.399, +0.663]; median -1.025; SD 2.259; mean w/o best 1% -0.060; positive 23.0% | futures n 74; mean +0.159 [-0.350, +0.690]; median -0.976; SD 2.331; mean w/o best 1% +0.013; positive 23.0%
    mid +5 15-minute: CFD n 74; mean -0.297 [-0.695, +0.172]; median -1.049; SD 1.886; mean w/o best 1% -0.429; positive 14.9% | futures n 74; mean -0.197 [-0.578, +0.283]; median -1.011; SD 1.960; mean w/o best 1% -0.332; positive 16.2%
    mid +5 5-minute: CFD n 74; mean +0.611 [-0.495, +2.061]; median -1.094; SD 5.616; mean w/o best 1% +0.122; positive 13.5% | futures n 74; mean +0.790 [-0.348, +2.312]; median -1.022; SD 5.910; mean w/o best 1% +0.267; positive 13.5%
    mid +10 4-hour: CFD n 74; mean -0.168 [-0.433, +0.119]; median -1.013; SD 1.248; mean w/o best 1% -0.224; positive 33.8% | futures n 74; mean -0.074 [-0.364, +0.236]; median -0.923; SD 1.283; mean w/o best 1% -0.131; positive 33.8%
    mid +10 30-minute: CFD n 74; mean +0.218 [-0.468, +0.970]; median -1.030; SD 3.151; mean w/o best 1% +0.012; positive 16.2% | futures n 74; mean +0.340 [-0.384, +1.146]; median -0.991; SD 3.311; mean w/o best 1% +0.121; positive 17.6%
    mid +10 15-minute: CFD n 74; mean -0.209 [-0.721, +0.435]; median -1.054; SD 2.575; mean w/o best 1% -0.383; positive 12.2% | futures n 74; mean -0.073 [-0.642, +0.614]; median -1.011; SD 2.726; mean w/o best 1% -0.253; positive 12.2%
    mid +10 5-minute: CFD n 74; mean +0.008 [-0.840, +1.040]; median -1.097; SD 4.154; mean w/o best 1% -0.268; positive 8.1% | futures n 74; mean +0.249 [-0.576, +1.296]; median -1.022; SD 4.300; mean w/o best 1% -0.032; positive 9.5%
    high +1 4-hour: CFD n 85; mean -0.107 [-0.221, +0.005]; median -0.161; SD 0.536; mean w/o best 1% -0.125; positive 38.8% | futures n 85; mean -0.092 [-0.205, +0.026]; median -0.155; SD 0.537; mean w/o best 1% -0.110; positive 40.0%
    high +1 30-minute: CFD n 85; mean -0.099 [-0.285, +0.092]; median +0.000; SD 0.889; mean w/o best 1% -0.144; positive 30.6% | futures n 85; mean -0.081 [-0.258, +0.109]; median +0.000; SD 0.888; mean w/o best 1% -0.127; positive 31.8%
    high +1 15-minute: CFD n 85; mean -0.235 [-0.520, +0.089]; median -1.022; SD 1.445; mean w/o best 1% -0.321; positive 27.1% | futures n 85; mean -0.201 [-0.483, +0.117]; median -0.995; SD 1.448; mean w/o best 1% -0.288; positive 27.1%
    high +1 5-minute: CFD n 85; mean -0.394 [-0.757, +0.060]; median -1.056; SD 1.988; mean w/o best 1% -0.541; positive 18.8% | futures n 85; mean -0.337 [-0.724, +0.145]; median -1.009; SD 1.998; mean w/o best 1% -0.484; positive 18.8%
    high +2 4-hour: CFD n 85; mean -0.076 [-0.218, +0.081]; median -0.067; SD 0.708; mean w/o best 1% -0.105; positive 42.4% | futures n 85; mean -0.053 [-0.197, +0.100]; median -0.051; SD 0.710; mean w/o best 1% -0.082; positive 44.7%
    high +2 30-minute: CFD n 85; mean +0.014 [-0.315, +0.381]; median -0.321; SD 1.670; mean w/o best 1% -0.108; positive 32.9% | futures n 85; mean +0.045 [-0.290, +0.448]; median -0.287; SD 1.679; mean w/o best 1% -0.079; positive 32.9%
    high +2 15-minute: CFD n 85; mean -0.283 [-0.623, +0.123]; median -1.027; SD 1.798; mean w/o best 1% -0.412; positive 22.4% | futures n 85; mean -0.242 [-0.577, +0.169]; median -0.999; SD 1.804; mean w/o best 1% -0.370; positive 22.4%
    high +2 5-minute: CFD n 85; mean -0.435 [-0.814, +0.017]; median -1.057; SD 2.013; mean w/o best 1% -0.582; positive 14.1% | futures n 85; mean -0.370 [-0.757, +0.113]; median -1.009; SD 2.034; mean w/o best 1% -0.517; positive 14.1%
    high +5 4-hour: CFD n 85; mean -0.078 [-0.300, +0.152]; median -0.266; SD 1.095; mean w/o best 1% -0.124; positive 34.1% | futures n 85; mean -0.035 [-0.260, +0.219]; median -0.246; SD 1.104; mean w/o best 1% -0.081; positive 40.0%
    high +5 30-minute: CFD n 85; mean +0.261 [-0.359, +1.101]; median -1.019; SD 3.623; mean w/o best 1% -0.080; positive 21.2% | futures n 85; mean +0.314 [-0.335, +1.235]; median -0.982; SD 3.666; mean w/o best 1% -0.030; positive 21.2%
    high +5 15-minute: CFD n 85; mean -0.138 [-0.600, +0.415]; median -1.032; SD 2.380; mean w/o best 1% -0.269; positive 17.6% | futures n 85; mean -0.081 [-0.527, +0.458]; median -0.999; SD 2.408; mean w/o best 1% -0.213; positive 17.6%
    high +5 5-minute: CFD n 85; mean -0.137 [-0.870, +1.015]; median -1.064; SD 4.552; mean w/o best 1% -0.572; positive 9.4% | futures n 85; mean -0.056 [-0.807, +1.053]; median -1.010; SD 4.602; mean w/o best 1% -0.495; positive 9.4%
    high +10 4-hour: CFD n 85; mean -0.283 [-0.526, -0.023]; median -1.010; SD 1.209; mean w/o best 1% -0.337; positive 30.6% | futures n 85; mean -0.216 [-0.469, +0.075]; median -0.942; SD 1.231; mean w/o best 1% -0.271; positive 30.6%
    high +10 30-minute: CFD n 85; mean -0.150 [-0.614, +0.405]; median -1.023; SD 2.457; mean w/o best 1% -0.333; positive 16.5% | futures n 85; mean -0.070 [-0.564, +0.489]; median -0.984; SD 2.555; mean w/o best 1% -0.260; positive 16.5%
    high +10 15-minute: CFD n 85; mean -0.407 [-0.770, +0.083]; median -1.033; SD 2.030; mean w/o best 1% -0.542; positive 14.1% | futures n 85; mean -0.331 [-0.708, +0.167]; median -1.001; SD 2.086; mean w/o best 1% -0.469; positive 14.1%
    high +10 5-minute: CFD n 85; mean -0.248 [-0.965, +0.809]; median -1.064; SD 4.476; mean w/o best 1% -0.685; positive 8.2% | futures n 85; mean -0.149 [-0.887, +0.952]; median -1.010; SD 4.579; mean w/o best 1% -0.595; positive 8.2%

#### Ranking flip (J2): entries ranked by mean net R per setup, CFD primary vs futures primary
- +1: CFD 5-minute > 30-minute > 15-minute > 4-hour; futures 5-minute > 15-minute > 30-minute > 4-hour -> FLIP (30-minute vs 15-minute: within noise)
- +2: CFD 5-minute > 30-minute > 15-minute > 4-hour; futures 5-minute > 30-minute > 15-minute > 4-hour -> same order
- +5: CFD 5-minute > 30-minute > 4-hour > 15-minute; futures 5-minute > 30-minute > 4-hour > 15-minute -> same order
- +10: CFD 30-minute > 4-hour > 5-minute > 15-minute; futures 5-minute > 30-minute > 4-hour > 15-minute -> FLIP (4-hour vs 5-minute: within noise; 30-minute vs 5-minute: within noise)

#### H2 flags: short cells positive only with a carry credit
- (no line above = no flagged cell)

## §5.3 catalogue net of costs (mean move in daily ATR minus round-trip cost in daily ATR; CFD = measured spread only, futures = tick + commissions; no financing or carry)
- M30 consolidation down: +1 CFD -0.043 futures -0.039; +2 CFD -0.112 futures -0.107; +5 CFD -0.154 futures -0.149; +10 CFD -0.392 futures -0.387
- M30 consolidation up: +1 CFD +0.131 futures +0.136; +2 CFD +0.171 futures +0.176; +5 CFD +0.341 futures +0.346; +10 CFD +0.568 futures +0.573
- M30 double bottom / top down: +1 CFD -0.029 futures -0.024; +2 CFD -0.072 futures -0.067; +5 CFD -0.265 futures -0.260; +10 CFD -0.540 futures -0.535
- M30 double bottom / top up: +1 CFD +0.095 futures +0.100; +2 CFD +0.141 futures +0.146; +5 CFD +0.385 futures +0.389; +10 CFD +0.631 futures +0.636
- M30 engulfing down: +1 CFD -0.060 futures -0.055; +2 CFD -0.123 futures -0.118; +5 CFD -0.243 futures -0.238; +10 CFD -0.499 futures -0.494
- M30 engulfing up: +1 CFD +0.044 futures +0.049; +2 CFD +0.103 futures +0.108; +5 CFD +0.260 futures +0.265; +10 CFD +0.544 futures +0.549
- M30 engulfing at a level down: +1 CFD -0.045 futures -0.040; +2 CFD -0.145 futures -0.140; +5 CFD -0.310 futures -0.305; +10 CFD -0.557 futures -0.552
- M30 engulfing at a level up: +1 CFD +0.040 futures +0.044; +2 CFD +0.107 futures +0.112; +5 CFD +0.236 futures +0.241; +10 CFD +0.518 futures +0.523
- M30 head and shoulders down: +1 CFD -0.069 futures -0.065; +2 CFD -0.195 futures -0.191; +5 CFD -0.136 futures -0.132; +10 CFD -0.542 futures -0.538
- M30 head and shoulders up: +1 CFD +0.167 futures +0.172; +2 CFD +0.253 futures +0.258; +5 CFD +0.331 futures +0.337; +10 CFD +0.498 futures +0.503
- M30 pin bar down: +1 CFD -0.084 futures -0.079; +2 CFD -0.126 futures -0.121; +5 CFD -0.283 futures -0.279; +10 CFD -0.548 futures -0.543
- M30 pin bar up: +1 CFD +0.012 futures +0.017; +2 CFD +0.045 futures +0.050; +5 CFD +0.169 futures +0.174; +10 CFD +0.400 futures +0.404
- M30 pin bar at a level down: +1 CFD -0.079 futures -0.074; +2 CFD -0.058 futures -0.054; +5 CFD -0.227 futures -0.222; +10 CFD -0.309 futures -0.305
- M30 pin bar at a level up: +1 CFD -0.019 futures -0.015; +2 CFD +0.043 futures +0.048; +5 CFD +0.173 futures +0.178; +10 CFD +0.322 futures +0.327
- M30 retest failed down: +1 CFD -0.014 futures -0.010; +2 CFD -0.070 futures -0.066; +5 CFD -0.116 futures -0.112; +10 CFD -0.270 futures -0.265
- M30 retest failed up: +1 CFD +0.068 futures +0.073; +2 CFD +0.152 futures +0.157; +5 CFD +0.317 futures +0.322; +10 CFD +0.642 futures +0.647
- M30 retest held down: +1 CFD -0.089 futures -0.084; +2 CFD -0.161 futures -0.157; +5 CFD -0.266 futures -0.261; +10 CFD -0.605 futures -0.601
- M30 retest held up: +1 CFD +0.036 futures +0.040; +2 CFD +0.092 futures +0.097; +5 CFD +0.208 futures +0.213; +10 CFD +0.440 futures +0.445
- M15 consolidation down: +1 CFD -0.033 futures -0.028; +2 CFD -0.090 futures -0.086; +5 CFD -0.157 futures -0.152; +10 CFD -0.400 futures -0.396
- M15 consolidation up: +1 CFD +0.060 futures +0.065; +2 CFD +0.122 futures +0.127; +5 CFD +0.306 futures +0.312; +10 CFD +0.543 futures +0.548
- M15 double bottom / top down: +1 CFD -0.025 futures -0.020; +2 CFD -0.061 futures -0.056; +5 CFD -0.148 futures -0.144; +10 CFD -0.425 futures -0.420
- M15 double bottom / top up: +1 CFD +0.062 futures +0.067; +2 CFD +0.102 futures +0.106; +5 CFD +0.296 futures +0.301; +10 CFD +0.457 futures +0.462
- M15 engulfing down: +1 CFD -0.051 futures -0.046; +2 CFD -0.107 futures -0.103; +5 CFD -0.244 futures -0.240; +10 CFD -0.491 futures -0.487
- M15 engulfing up: +1 CFD +0.058 futures +0.063; +2 CFD +0.112 futures +0.117; +5 CFD +0.262 futures +0.267; +10 CFD +0.518 futures +0.523
- M15 engulfing at a level down: +1 CFD -0.061 futures -0.056; +2 CFD -0.123 futures -0.118; +5 CFD -0.272 futures -0.268; +10 CFD -0.510 futures -0.506
- M15 engulfing at a level up: +1 CFD -0.000 futures +0.004; +2 CFD +0.063 futures +0.068; +5 CFD +0.245 futures +0.250; +10 CFD +0.459 futures +0.464
- M15 head and shoulders down: +1 CFD -0.064 futures -0.059; +2 CFD -0.148 futures -0.143; +5 CFD -0.233 futures -0.228; +10 CFD -0.571 futures -0.566
- M15 head and shoulders up: +1 CFD +0.144 futures +0.149; +2 CFD +0.197 futures +0.202; +5 CFD +0.342 futures +0.347; +10 CFD +0.654 futures +0.659
- M15 pin bar down: +1 CFD -0.082 futures -0.078; +2 CFD -0.116 futures -0.112; +5 CFD -0.287 futures -0.282; +10 CFD -0.542 futures -0.538
- M15 pin bar up: +1 CFD +0.044 futures +0.049; +2 CFD +0.113 futures +0.118; +5 CFD +0.291 futures +0.296; +10 CFD +0.526 futures +0.531
- M15 pin bar at a level down: +1 CFD -0.166 futures -0.162; +2 CFD -0.193 futures -0.188; +5 CFD -0.459 futures -0.454; +10 CFD -0.603 futures -0.599
- M15 pin bar at a level up: +1 CFD -0.008 futures -0.004; +2 CFD +0.073 futures +0.078; +5 CFD +0.276 futures +0.280; +10 CFD +0.403 futures +0.408
- M15 retest failed down: +1 CFD -0.047 futures -0.043; +2 CFD -0.101 futures -0.096; +5 CFD -0.177 futures -0.172; +10 CFD -0.393 futures -0.388
- M15 retest failed up: +1 CFD +0.040 futures +0.045; +2 CFD +0.087 futures +0.091; +5 CFD +0.187 futures +0.192; +10 CFD +0.425 futures +0.430
- M15 retest held down: +1 CFD -0.089 futures -0.085; +2 CFD -0.121 futures -0.116; +5 CFD -0.207 futures -0.203; +10 CFD -0.474 futures -0.470
- M15 retest held up: +1 CFD +0.065 futures +0.070; +2 CFD +0.135 futures +0.140; +5 CFD +0.331 futures +0.336; +10 CFD +0.558 futures +0.563
- M5 consolidation down: +1 CFD -0.046 futures -0.041; +2 CFD -0.094 futures -0.089; +5 CFD -0.206 futures -0.201; +10 CFD -0.456 futures -0.451
- M5 consolidation up: +1 CFD +0.045 futures +0.050; +2 CFD +0.097 futures +0.102; +5 CFD +0.256 futures +0.261; +10 CFD +0.525 futures +0.530
- M5 double bottom / top down: +1 CFD -0.059 futures -0.054; +2 CFD -0.113 futures -0.109; +5 CFD -0.220 futures -0.216; +10 CFD -0.495 futures -0.490
- M5 double bottom / top up: +1 CFD +0.061 futures +0.066; +2 CFD +0.111 futures +0.116; +5 CFD +0.263 futures +0.268; +10 CFD +0.504 futures +0.509
- M5 engulfing down: +1 CFD -0.065 futures -0.060; +2 CFD -0.109 futures -0.104; +5 CFD -0.236 futures -0.231; +10 CFD -0.465 futures -0.460
- M5 engulfing up: +1 CFD +0.048 futures +0.053; +2 CFD +0.105 futures +0.110; +5 CFD +0.260 futures +0.264; +10 CFD +0.514 futures +0.518
- M5 engulfing at a level down: +1 CFD -0.070 futures -0.066; +2 CFD -0.126 futures -0.121; +5 CFD -0.289 futures -0.284; +10 CFD -0.521 futures -0.517
- M5 engulfing at a level up: +1 CFD +0.050 futures +0.055; +2 CFD +0.138 futures +0.143; +5 CFD +0.279 futures +0.284; +10 CFD +0.580 futures +0.585
- M5 head and shoulders down: +1 CFD -0.063 futures -0.058; +2 CFD -0.154 futures -0.149; +5 CFD -0.308 futures -0.304; +10 CFD -0.634 futures -0.629
- M5 head and shoulders up: +1 CFD +0.111 futures +0.116; +2 CFD +0.120 futures +0.125; +5 CFD +0.288 futures +0.293; +10 CFD +0.512 futures +0.517
- M5 pin bar down: +1 CFD -0.087 futures -0.083; +2 CFD -0.141 futures -0.136; +5 CFD -0.289 futures -0.284; +10 CFD -0.515 futures -0.511
- M5 pin bar up: +1 CFD +0.029 futures +0.034; +2 CFD +0.073 futures +0.078; +5 CFD +0.199 futures +0.204; +10 CFD +0.445 futures +0.450
- M5 pin bar at a level down: +1 CFD -0.068 futures -0.064; +2 CFD -0.115 futures -0.110; +5 CFD -0.264 futures -0.260; +10 CFD -0.427 futures -0.422
- M5 pin bar at a level up: +1 CFD +0.058 futures +0.063; +2 CFD +0.097 futures +0.102; +5 CFD +0.172 futures +0.177; +10 CFD +0.405 futures +0.410
- M5 retest failed down: +1 CFD -0.075 futures -0.070; +2 CFD -0.145 futures -0.140; +5 CFD -0.260 futures -0.255; +10 CFD -0.519 futures -0.515
- M5 retest failed up: +1 CFD +0.035 futures +0.039; +2 CFD +0.071 futures +0.076; +5 CFD +0.232 futures +0.237; +10 CFD +0.484 futures +0.488
- M5 retest held down: +1 CFD -0.058 futures -0.053; +2 CFD -0.119 futures -0.115; +5 CFD -0.248 futures -0.243; +10 CFD -0.477 futures -0.472
- M5 retest held up: +1 CFD +0.058 futures +0.063; +2 CFD +0.109 futures +0.114; +5 CFD +0.274 futures +0.279; +10 CFD +0.583 futures +0.588
```
