"""
cot_data.py

Fetches CFTC Commitment of Traders (COT) data for GBP and AUD futures.

The CFTC FinFutWk.txt file has NO header row — it is pure data CSV.
We parse it positionally using the known CFTC column layout.

CFTC Financial Futures column layout (0-indexed):
  0  : Market name
  1  : As of date (YYMMDD)
  2  : Report date (YYYY-MM-DD)
  3  : CFTC contract market code
  4  : Exchange
  5  : CFTC market code
  6  : CFTC region code
  7  : Non-commercial longs
  8  : Non-commercial shorts
  9  : Non-commercial spreads
  10 : Commercial longs
  11 : Commercial shorts
  12 : Total reportable longs
  13 : Total reportable shorts
  14 : Non-reportable longs
  15 : Non-reportable shorts
  ... (change columns follow)

Contract identifiers:
  GBP : 096742  or  "BRITISH POUND"
  AUD : 232741  or  "AUSTRALIAN DOLLAR"
"""

from __future__ import annotations
import csv
import io
import zipfile
import requests
from datetime import datetime
import json
from pathlib import Path

_CACHE_FILE = Path(__file__).parent / "cot_cache.json"
from typing import Dict, List, Optional, Tuple

_CFTC_URLS = [
    "https://www.cftc.gov/dea/newcot/FinFutWk.txt",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip",
    "https://www.cftc.gov/files/dea/history/fut_fin_txt_2025.zip",
]

# Column indices in the positional CSV
_COL_NAME        = 0
_COL_DATE_YYMMDD = 1
_COL_DATE_ISO    = 2
_COL_CODE        = 3
_COL_NC_LONG     = 7
_COL_NC_SHORT    = 8


def get_cot_data() -> Dict:

    raw_text = _fetch()
    if raw_text is None:
        return _fallback("Could not download CFTC data")

    try:
        return _parse(raw_text)
    except Exception as exc:
        return _fallback(f"Parse error: {exc}")


def _fetch() -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        ),
    }
    for url in _CFTC_URLS:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                continue
            if resp.content[:2] == b'PK':
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    for name in z.namelist():
                        if name.lower().endswith(('.txt', '.csv')):
                            with z.open(name) as f:
                                text = f.read().decode('utf-8', errors='replace')
                                return text
            else:
                return resp.text
        except Exception:
            continue


def _parse(raw_text: str) -> Dict:
    lines = raw_text.strip().splitlines()

    # Parse as CSV — no header, purely positional
    reader = csv.reader(io.StringIO(raw_text))
    rows   = [row for row in reader if len(row) > 10]


    # Show first few market names and codes for verification
    sample = []
    for row in rows[:5]:
        name = row[_COL_NAME].strip() if len(row) > _COL_NAME else ""
        code = row[_COL_CODE].strip() if len(row) > _COL_CODE else ""
        sample.append(f"[{code}] {name[:50]}")

    gbp_row = _find_row(rows, ["096742", "BRITISH POUND", "BP - CHICAGO"])
    aud_row = _find_row(rows, ["232741", "AUSTRALIAN DOLLAR", "AD - CHICAGO"])

    if not gbp_row and not aud_row:
        all_names = [r[_COL_NAME].strip()[:50] for r in rows if len(r) > _COL_NAME]
        forex = [n for n in all_names if any(
            k in n.upper() for k in
            ["POUND", "DOLLAR", "EURO", "YEN", "FRANC", "PESO", "CURRENCY", "STERLING"]
        )]
        return _fallback(
            f"GBP/AUD not found. Forex markets in file: {forex[:8]}"
        )

    report_date = _extract_date(gbp_row or aud_row)
    gbp_data    = _interpret(gbp_row, "GBP") if gbp_row else _empty("GBP")
    aud_data    = _interpret(aud_row, "AUD") if aud_row else _empty("AUD")
    pair_bias   = _pair_bias(gbp_data, aud_data)
    pair_sum    = _pair_summary(gbp_data, aud_data, pair_bias)


    result = {
        "gbp_net":          gbp_data["net"],
        "gbp_pct_long":     gbp_data["pct_long"],
        "gbp_pct_short":    gbp_data["pct_short"],
        "gbp_bias":         gbp_data["bias"],
        "gbp_extreme":      gbp_data["extreme"],
        "gbp_extreme_note": gbp_data["extreme_note"],
        "gbp_summary":      gbp_data["summary"],
        "aud_net":          aud_data["net"],
        "aud_pct_long":     aud_data["pct_long"],
        "aud_pct_short":    aud_data["pct_short"],
        "aud_bias":         aud_data["bias"],
        "aud_extreme":      aud_data["extreme"],
        "aud_extreme_note": aud_data["extreme_note"],
        "aud_summary":      aud_data["summary"],
        "pair_bias":        pair_bias,
        "pair_summary":     pair_sum,
        "report_date":      report_date,
        "cached":           False,
        "error":            None,
    }
    # Save to cache for fallback
    try:
        _CACHE_FILE.write_text(json.dumps(result))
    except Exception:
        pass
    return result


def _find_row(rows: List[List[str]], identifiers: List[str]) -> Optional[List[str]]:
    for row in rows:
        row_str = " ".join(row[:6]).upper()
        for ident in identifiers:
            if ident.upper() in row_str:
                return row
    return None


def _interpret(row: List[str], currency: str) -> Dict:
    try:
        longs  = int(float(row[_COL_NC_LONG].strip().replace(",", "")))
        shorts = int(float(row[_COL_NC_SHORT].strip().replace(",", "")))
    except (IndexError, ValueError) as exc:
                return _empty(currency, f"Could not read position data: {exc}")

    net   = longs - shorts
    total = longs + shorts
    pct_l = round(longs  / total * 100, 1) if total > 0 else 0.0
    pct_s = round(shorts / total * 100, 1) if total > 0 else 0.0
    bias  = "BULLISH" if net > 0 else "BEARISH" if net < 0 else "NEUTRAL"

    extreme = False
    extreme_note = ""
    warn = ""

    if pct_l > 70:
        extreme = True
        extreme_note = f"CROWDED LONG ({pct_l:.0f}% long)"
        warn = (
            "Extremely crowded long — contrarian BEARISH warning. "
            "When everyone has already bought, fewer buyers remain."
        )
    elif pct_s > 70:
        extreme = True
        extreme_note = f"CROWDED SHORT ({pct_s:.0f}% short)"
        warn = (
            "Extremely crowded short — contrarian BULLISH warning. "
            "A short squeeze could push price sharply higher."
        )

    net_str   = f"+{net:,}" if net > 0 else f"{net:,}"
    direction = "more long than short" if net > 0 else "more short than long"
    summary   = (
        f"Hedge funds are {direction} on {currency}. "
        f"Net: {net_str} contracts ({pct_l:.0f}% long, {pct_s:.0f}% short)."
    )
    if warn:
        summary += f" {warn}"

    return {
        "currency": currency, "longs": longs, "shorts": shorts, "net": net,
        "pct_long": pct_l, "pct_short": pct_s, "bias": bias,
        "extreme": extreme, "extreme_note": extreme_note, "summary": summary,
    }


def _extract_date(row: Optional[List[str]]) -> str:
    if not row:
        return "Unknown"
    # Try ISO date column first (col 2)
    if len(row) > 2:
        iso = row[2].strip()
        if len(iso) == 10 and iso[4] == "-":
            return iso
    # Try YYMMDD column (col 1)
    if len(row) > 1:
        raw = row[1].strip()
        if len(raw) == 6:
            try:
                return datetime.strptime(raw, "%y%m%d").strftime("%Y-%m-%d")
            except Exception:
                pass
    return "Unknown"


def _pair_bias(gbp: Dict, aud: Dict) -> str:
    g = 1 if gbp["bias"] == "BULLISH" else -1 if gbp["bias"] == "BEARISH" else 0
    a = 1 if aud["bias"] == "BULLISH" else -1 if aud["bias"] == "BEARISH" else 0
    score = g - a
    return "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL"


def _pair_summary(gbp: Dict, aud: Dict, bias: str) -> str:
    gd = "long" if gbp["net"] >= 0 else "short"
    ad = "long" if aud["net"] >= 0 else "short"
    s  = f"Institutions net {gd} GBP and net {ad} AUD. "
    s += ("Supports GBP/AUD going UP." if bias == "BULLISH"
          else "Supports GBP/AUD going DOWN." if bias == "BEARISH"
          else "No clear directional signal from hedge fund positioning.")
    extremes = []
    if gbp["extreme"]: extremes.append(f"GBP {gbp['extreme_note']}")
    if aud["extreme"]: extremes.append(f"AUD {aud['extreme_note']}")
    if extremes:
        s += " WARNING - EXTREME: " + ", ".join(extremes) + " - reversal risk elevated."
    return s


def _empty(currency: str, note: str = "") -> Dict:
    return {
        "currency": currency, "longs": 0, "shorts": 0, "net": 0,
        "pct_long": 0.0, "pct_short": 0.0, "bias": "NEUTRAL",
        "extreme": False, "extreme_note": "",
        "summary": note or f"{currency} data not found",
    }


def _fallback(reason: str) -> Dict:
    # Try loading cached data first
    try:
        if _CACHE_FILE.exists():
            cached = json.loads(_CACHE_FILE.read_text())
            cached["cached"]       = True
            cached["error"]        = f"CACHED (live fetch failed: {reason})"
            cached["pair_summary"] += f" [CACHED data — {cached.get('report_date','?')}]"
            return cached
    except Exception:
        pass
    return {
        "gbp_net": 0, "gbp_pct_long": 0.0, "gbp_pct_short": 0.0,
        "gbp_bias": "NEUTRAL", "gbp_extreme": False,
        "gbp_extreme_note": "", "gbp_summary": reason,
        "aud_net": 0, "aud_pct_long": 0.0, "aud_pct_short": 0.0,
        "aud_bias": "NEUTRAL", "aud_extreme": False,
        "aud_extreme_note": "", "aud_summary": reason,
        "pair_bias": "NEUTRAL",
        "pair_summary": f"COT data unavailable: {reason}",
        "report_date": "", "cached": False, "error": reason,
    }


if __name__ == "__main__":
    data = get_cot_data()
    if data["error"]:
        print(f"\nError: {data['error']}")
    else:
        print(f"\nReport date : {data['report_date']}")
        print(f"GBP: {data['gbp_summary']}")
        print(f"AUD: {data['aud_summary']}")
        print(f"Pair bias   : {data['pair_bias']}")
        print(f"{data['pair_summary']}")
