import os
from typing import Any, Dict, List
from pathlib import Path

# ── Pairs ─────────────────────────────────────────────────────────────────────
CURRENCY_PAIRS: List[str] = ["GBP/AUD"]
BASE_CURRENCIES: List[str] = ["GBP", "AUD"]

# ── Calendar ──────────────────────────────────────────────────────────────────
FOREX_FACTORY_URL: str = "https://www.forexfactory.com/calendar"
IMPACT_LEVELS: List[str] = ["High", "Medium"]

# ── Alpha Vantage (kept for optional rate fetch) ───────────────────────────────
API_CONFIG: Dict[str, Any] = {
    "key": os.getenv("ALPHA_VANTAGE_API_KEY", ""),
    "base_url": "https://www.alphavantage.co/query",
    "timeout": 30,
    "rate_limit": {
        "calls": 2,
        "period": 3600,
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_CONFIG: Dict[str, str] = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "directory": str(Path(__file__).parent / "logs"),
}
