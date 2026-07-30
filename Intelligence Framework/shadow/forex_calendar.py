"""
forex_calendar.py

Fetches GBP/AUD economic events from ForexFactory.
Falls back to calendar.csv if the site blocks the request.
"""

import time
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ForexCalendarScraper:

    def __init__(self):
        self.target_currencies = ["GBP", "AUD"]
        self.base_url = "https://www.forexfactory.com/calendar"
        self.session  = self._build_session()
        self.stale_info: dict | None = None   # set by _try_fallback when CSV is stale

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language":  "en-US,en;q=0.9",
            "Accept-Encoding":  "gzip, deflate, br",
            "Connection":       "keep-alive",
            "Cache-Control":    "max-age=0",
            "Sec-Fetch-Dest":   "document",
            "Sec-Fetch-Mode":   "navigate",
            "Sec-Fetch-Site":   "none",
            "Sec-Fetch-User":   "?1",
            "Upgrade-Insecure-Requests": "1",
        })
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(("GET",)),
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://",  adapter)
        return s

    def get_weekly_calendar(self) -> pd.DataFrame:

        today      = datetime.now()
        monday     = today - timedelta(days=today.weekday())
        week_param = monday.strftime("%Y-%m-%d")
        url        = f"{self.base_url}?week={week_param}"

        try:
            self.session.get("https://www.forexfactory.com/", timeout=15)
            time.sleep(2)
        except Exception:
            pass

        try:
            response = self.session.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"Request failed: {exc}")
            return self._try_fallback()

        if response.status_code != 200:
            return self._try_fallback()

        pass  # silent
        soup   = BeautifulSoup(response.text, "html.parser")
        events = self._parse(soup)

        if not events:
            return self._try_fallback()

        df = pd.DataFrame(events)
        df = df.sort_values("time").reset_index(drop=True)
        return df

    def _parse(self, soup: BeautifulSoup) -> List[Dict]:
        table = soup.find("table", class_="calendar__table")
        if not table:
            for t in soup.find_all("table"):
                if t.find("tr", class_=lambda c: c and "calendar__row" in " ".join(c)):
                    table = t
                    break
        if not table:
            return []

        events: List[Dict] = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = ""

        for row in table.find_all("tr"):
            classes = " ".join(row.get("class", []))

            if "day-breaker" in classes:
                date_cell = row.find("td")
                if date_cell:
                    current_date = self._parse_date(date_cell.get_text(strip=True))
                continue

            if "calendar__row" not in classes:
                continue

            event = self._parse_row(row, current_date)
            if event is None:
                continue

            if event["time"] and event["time"] != current_date:
                current_time = event["time"]
            elif not event["time"]:
                event["time"] = current_time

            if event["currency"] in self.target_currencies:
                events.append(event)

        return events

    def _parse_row(self, row, current_date: str) -> Optional[Dict]:
        try:
            currency_cell = row.find("td", class_="calendar__currency")
            if not currency_cell:
                return None
            currency = currency_cell.get_text(strip=True)
            if not currency:
                return None

            time_cell = row.find("td", class_="calendar__time")
            time_str  = time_cell.get_text(strip=True) if time_cell else ""
            full_time = f"{current_date} {time_str}".strip() if time_str else current_date

            event_name = ""
            event_cell = row.find("td", class_="calendar__event")
            if event_cell:
                span = event_cell.find("span", class_="calendar__event-title")
                event_name = (
                    span.get_text(strip=True) if span
                    else event_cell.get_text(strip=True)
                )
            if not event_name:
                return None

            impact   = self._parse_impact(row)
            actual   = self._cell(row, "calendar__actual")
            forecast = self._cell(row, "calendar__forecast")
            previous = self._cell(row, "calendar__previous")

            return {
                "time":     full_time,
                "currency": currency,
                "event":    event_name,
                "actual":   actual,
                "forecast": forecast,
                "previous": previous,
                "impact":   impact,
            }
        except Exception:
            return None

    def _cell(self, row, cls: str) -> str:
        cell = row.find("td", class_=cls)
        return cell.get_text(strip=True) if cell else ""

    def _parse_impact(self, row) -> str:
        try:
            impact_cell = row.find("td", class_="calendar__impact")
            if not impact_cell:
                return "Unknown"
            html = str(impact_cell)
            if "red" in html: return "High"
            if "ora" in html: return "Medium"
            if "yel" in html: return "Low"
            return "Unknown"
        except Exception:
            return "Unknown"

    def _parse_date(self, raw: str) -> str:
        raw = raw.strip()
        year = datetime.now().year
        for fmt in ["%a %b %d", "%A %b %d", "%a %B %d"]:
            try:
                dt = datetime.strptime(f"{raw} {year}", f"{fmt} %Y")
                if abs((dt - datetime.now()).days) > 180:
                    dt = dt.replace(year=year + 1)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")

    def _try_fallback(self) -> pd.DataFrame:
        import os
        if os.path.exists("calendar.csv"):
            try:
                df = pd.read_csv("calendar.csv")
                if df.empty:
                    return df

                # Check whether the CSV contains data for the current week.
                # If all dates are older than 7 days the file is stale and will
                # feed wrong events into the news-lockout gate — more dangerous
                # than returning nothing.
                today      = datetime.now()
                cutoff     = today - timedelta(days=7)
                time_col   = df.get("time", df.iloc[:, 0] if len(df.columns) else None)
                if time_col is not None:
                    try:
                        dates = pd.to_datetime(time_col, errors="coerce")
                        most_recent = dates.max()
                        if pd.isna(most_recent) or most_recent < pd.Timestamp(cutoff):
                            days_old = (today - most_recent.to_pydatetime()).days if not pd.isna(most_recent) else "?"
                            recent_str = str(most_recent.date()) if not pd.isna(most_recent) else "unknown"
                            self.stale_info = {
                                "days_old":    days_old,
                                "most_recent": recent_str,
                            }
                            return pd.DataFrame()   # return empty so news gate skips rather than uses bad data
                    except Exception:
                        pass  # if date parsing fails, proceed with what we have

                return df
            except Exception:
                pass  # silent

        print()
        print("time, currency, event, actual, forecast, previous, impact")
        print("Example: 2026-03-27 09:30,GBP,CPI YoY,,2.9%,3.0%,High")
        return pd.DataFrame()


def main():
    scraper = ForexCalendarScraper()
    df = scraper.get_weekly_calendar()
    if not df.empty:
        print(df[["time", "currency", "event", "impact", "forecast", "actual"]].to_string())
    else:
        print("No data returned.")


if __name__ == "__main__":
    main()
