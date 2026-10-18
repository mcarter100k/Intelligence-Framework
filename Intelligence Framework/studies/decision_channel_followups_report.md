# Decision-channel follow-ups (B3, B4)

## B3. Open-market directional decisions (16)

| # | UTC | Pacific | pair | direction | printed price | price basis |
|---|---|---|---|---|---|---|
| 1 | 2026-09-11T01:04:14Z | Thu 2026-09-10 18:04 PDT | GBP_AUD | SHORT | 1.8879 | previous daily close (before 6471072) |
| 2 | 2026-09-11T09:38:41Z | Fri 2026-09-11 02:38 PDT | GBP_AUD | SHORT | 1.8879 | previous daily close (before 6471072) |
| 3 | 2026-09-11T14:32:04Z | Fri 2026-09-11 07:32 PDT | GBP_AUD | SHORT | 1.8879 | previous daily close (before 6471072) |
| 4 | 2026-09-14T16:16:50Z | Mon 2026-09-14 09:16 PDT | GBP_JPY | SHORT | 207.675 | previous daily close (before 6471072) |
| 5 | 2026-09-25T01:01:55Z | Thu 2026-09-24 18:01 PDT | GBP_JPY | SHORT | 209.984 | previous daily close (before 6471072) |
| 6 | 2026-09-25T09:36:44Z | Fri 2026-09-25 02:36 PDT | GBP_JPY | SHORT | 209.984 | previous daily close (before 6471072) |
| 7 | 2026-09-25T14:41:40Z | Fri 2026-09-25 07:41 PDT | GBP_JPY | SHORT | 209.984 | previous daily close (before 6471072) |
| 8 | 2026-10-09T01:00:11Z | Thu 2026-10-08 18:00 PDT | GBP_JPY | SHORT | 209.176 | live (after 6471072, no not-live flag) |
| 9 | 2026-10-09T09:30:10Z | Fri 2026-10-09 02:30 PDT | GBP_JPY | SHORT | 209.458 | live (after 6471072, no not-live flag) |
| 10 | 2026-10-09T14:30:06Z | Fri 2026-10-09 07:30 PDT | GBP_JPY | SHORT | 209.46 | live (after 6471072, no not-live flag) |
| 11 | 2026-10-12T01:00:10Z | Sun 2026-10-11 18:00 PDT | GBP_JPY | SHORT | 209.49 | live (after 6471072, no not-live flag) |
| 12 | 2026-10-12T09:44:32Z | Mon 2026-10-12 02:44 PDT | GBP_JPY | SHORT | 209.948 | live (after 6471072, no not-live flag) |
| 13 | 2026-10-12T14:38:40Z | Mon 2026-10-12 07:38 PDT | GBP_JPY | SHORT | 209.845 | live (after 6471072, no not-live flag) |
| 14 | 2026-10-13T01:05:33Z | Mon 2026-10-12 18:05 PDT | GBP_JPY | SHORT | 209.399 | live (after 6471072, no not-live flag) |
| 15 | 2026-10-13T09:33:36Z | Tue 2026-10-13 02:33 PDT | GBP_JPY | SHORT | 209.212 | live (after 6471072, no not-live flag) |
| 16 | 2026-10-13T14:30:08Z | Tue 2026-10-13 07:30 PDT | GBP_JPY | SHORT | 209.751 | live (after 6471072, no not-live flag) |

## B4. Concurrent-run handling: episodes and gradeable bound

| handling | GBP_AUD episodes | GBP_JPY episodes | total | gradeable (at most) | statuses |
|---|---|---|---|---|---|
| merged if every copy agrees (as reported) | 2 | 3 | 5 | 3 | {'AWAITING OPEN': 1, 'ELIGIBLE': 3, 'ONSET-CENSORED': 1} |
|  | GBP_AUD 2026-09-10 18:04:14 PDT SHORT | | | | ELIGIBLE (structure and leg-minimum not yet checked) |
|  | GBP_AUD 2026-10-16 18:12:44 PDT LONG | | | | AWAITING OPEN |
|  | GBP_JPY 2026-09-11 18:02:16 PDT SHORT | | | | ELIGIBLE (structure and leg-minimum not yet checked) |
|  | GBP_JPY 2026-09-24 18:01:55 PDT SHORT | | | | ELIGIBLE (structure and leg-minimum not yet checked) |
|  | GBP_JPY 2026-10-08 18:00:11 PDT SHORT | | | | ONSET-CENSORED |
| every concurrent group counted as RUN ERRORED | 2 | 3 | 5 | 2 | {'AWAITING OPEN': 1, 'ELIGIBLE': 2, 'NEVER ACTIONABLE': 1, 'ONSET-CENSORED': 1} |
|  | GBP_AUD 2026-09-10 18:04:14 PDT SHORT | | | | ELIGIBLE (structure and leg-minimum not yet checked) |
|  | GBP_AUD 2026-10-16 18:12:44 PDT LONG | | | | AWAITING OPEN |
|  | GBP_JPY 2026-09-11 18:02:16 PDT SHORT | | | | NEVER ACTIONABLE |
|  | GBP_JPY 2026-09-24 18:01:55 PDT SHORT | | | | ELIGIBLE (structure and leg-minimum not yet checked) |
|  | GBP_JPY 2026-10-08 18:00:11 PDT SHORT | | | | ONSET-CENSORED |
