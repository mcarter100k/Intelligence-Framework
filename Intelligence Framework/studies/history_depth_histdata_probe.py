"""HistData endpoint probe. Lists offered years, reads the form token, and
attempts ONE study-span download into a caller-supplied empty directory.
Reports bytes, zip validity, member names and first/last row timestamps only.

usage: python3 -I history_depth_histdata_probe.py <pair_lower> <year> <download_dir> <json_out>
"""
import io
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
import zipfile

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

BASE = "https://www.histdata.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
SEALED_YEARS = set(range(2014, 2022))


def get(url, data=None, referer=None):
    h = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    if data is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        return r.status, dict(r.headers), r.read()


def main():
    pair, year, dl_dir, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    if year in SEALED_YEARS:
        raise SystemExit("refused: sealed-exam year")
    if os.listdir(dl_dir):
        raise SystemExit("download dir must be empty")
    res = {"pair": pair, "year": year}
    pair_url = f"{BASE}/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}"
    st, _, body = get(pair_url)
    html = body.decode("utf-8", "replace")
    years = sorted({int(y) for y in re.findall(rf"1-minute-bar-quotes/{pair}/(\d{{4}})", html, re.I)})
    res["pair_page_http"] = st
    res["years_offered"] = years
    res["study_years_offered"] = [y for y in years if 2005 <= y <= 2013]

    year_url = f"{pair_url}/{year}"
    st, _, body = get(year_url)
    html = body.decode("utf-8", "replace")
    form = {}
    for name in ("tk", "date", "datemonth", "platform", "timeframe", "fxpair"):
        m = re.search(rf'id="{name}"[^>]*value="([^"]*)"', html) or \
            re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
        form[name] = m.group(1) if m else None
    res["year_page_http"] = st
    res["form_fields_present"] = {k: v is not None for k, v in form.items()}
    res["tk_length"] = len(form["tk"] or "")
    res["form_date"] = form["date"]
    if not form["tk"]:
        res["download"] = "not attempted: empty or missing form token"
    else:
        st, hdr, body = get(f"{BASE}/get.php", data=form, referer=year_url)
        res["get_php_http"] = st
        res["get_php_bytes"] = len(body)
        res["get_php_content_type"] = hdr.get("Content-Type")
        fn = os.path.join(dl_dir, f"histdata_{pair}_{year}.zip")
        with open(fn, "wb") as fh:
            fh.write(body)
        try:
            z = zipfile.ZipFile(io.BytesIO(body))
            res["zip_members"] = [(i.filename, i.file_size) for i in z.infolist()]
            csvs = [i for i in z.namelist() if i.lower().endswith(".csv")]
            if csvs:
                lines = z.read(csvs[0]).decode("utf-8", "replace").splitlines()
                stamp = lambda ln: ln.split(";")[0] if ";" in ln else ln.split(",")[0]
                res["csv_rows"] = len(lines)
                res["csv_first_timestamp"] = stamp(lines[0])
                res["csv_last_timestamp"] = stamp(lines[-1])
        except zipfile.BadZipFile:
            res["zip_members"] = "NOT A ZIP"
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
