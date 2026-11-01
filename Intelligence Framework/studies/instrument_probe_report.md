# Instrument probe report (2026-11-01)

Owner-approved read-only probe of the live OANDA account
(`studies/instrument_probe.py`, run through `scripts/reality_run.py`:
exit 0, project files unchanged by hash, stderr empty). Verbatim output:

```
INSTRUMENT PROBE — account ****************-002 — api-fxtrade.oanda.com
Instruments offered by type: CURRENCY 68

## USD legs
  USD_JPY      offered (CURRENCY): daily history 2002-05-06 → 2026-10-29
  GBP_USD      offered (CURRENCY): daily history 2002-05-06 → 2026-10-29
  AUD_USD      offered (CURRENCY): daily history 2002-05-06 → 2026-10-29
  USD_CNH      offered (CURRENCY): daily history 2011-02-06 → 2026-10-29

## Yields
  USB02Y_USD   NOT OFFERED
  USB10Y_USD   NOT OFFERED
  UK10YB_GBP   NOT OFFERED
  DE10YB_EUR   NOT OFFERED

## Equities
  SPX500_USD   NOT OFFERED
  NAS100_USD   NOT OFFERED
  JP225_USD    NOT OFFERED
  AU200_AUD    NOT OFFERED
  UK100_GBP    NOT OFFERED

## Commodities
  XCU_USD      NOT OFFERED
  XAU_USD      NOT OFFERED
  BCO_USD      NOT OFFERED
  WTICO_USD    NOT OFFERED
  NATGAS_USD   NOT OFFERED

## Financing (as reported by the instruments endpoint)
  GBP_JPY: longRate 0.016 shortRate -0.0366
  GBP_AUD: longRate -0.0189 shortRate -0.0018

## All non-currency instruments (0)
  none
```

## What it means for the driver-coverage plan

- **The account offers currency pairs only (68 instruments, all CURRENCY).**
  No bond, index, metal or commodity CFDs. The US 10-year yield, equities,
  VIX, iron ore and copper must come from free outside sources (FRED, World
  Bank, RBA), each with its own feed validation, never from OANDA.
- **The USD legs are available with daily history from 2002-05-06**
  (USD/CNH from 2011-02-06). This covers the US-event reaction study and the
  GBP/USD vs AUD/USD leg decomposition on the same feed as the traded pairs.
- **Financing as quoted today** (annual rates, sign = paid to the holder):
  - GBP/JPY long earns 1.6% a year; short pays 3.66%.
  - GBP/AUD long pays 1.89%; short pays 0.18%.
  - This confirms from the broker itself the carry flip the reviews reported:
    a long GBP/AUD now costs carry. These are today's rates only; the
    endpoint gives no history.
