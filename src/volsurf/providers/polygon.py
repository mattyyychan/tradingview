import os
import math
import time
import datetime as dt
from typing import Dict, List, Optional, Tuple

import requests

POLYGON_BASE = "https://api.polygon.io"


def _get_polygon_api_key() -> str:
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY environment variable is required for Polygon provider")
    return api_key


def _retry_get(url: str, params: Dict[str, str], retries: int = 3, backoff: float = 1.5) -> Dict:
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(backoff ** (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(backoff ** (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("Unknown Polygon request error")


class PolygonOptionsProvider:
    """Fetches historical option quotes and OI for a ticker from Polygon.io.

    Notes:
    - Requires POLYGON_API_KEY env var.
    - Uses aggregates and daily option data endpoints. OI coverage varies by contract/date.
    """

    def __init__(self, underlying: str = "NVDA") -> None:
        self.underlying = underlying.upper()
        self.api_key = _get_polygon_api_key()

    @staticmethod
    def _iso(date: dt.date) -> str:
        return date.strftime("%Y-%m-%d")

    def list_option_contracts(self, as_of: dt.date) -> List[Dict]:
        """List option contracts for the underlying as of a date.

        Polygon's reference options endpoint returns listed contracts; we filter by as_of.
        """
        url = f"{POLYGON_BASE}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": self.underlying,
            "expired": "false",
            "as_of": self._iso(as_of),
            "limit": "1000",
            "apiKey": self.api_key,
        }
        results: List[Dict] = []
        while True:
            data = _retry_get(url, params)
            results.extend(data.get("results", []))
            next_url = data.get("next_url")
            if not next_url:
                break
            url = next_url
            params = {"apiKey": self.api_key}
        return results

    def get_daily_option_snapshot(self, option_symbol: str, date: dt.date) -> Optional[Dict]:
        """Fetch daily open/close/IV/OI if available for a single contract/date.

        Uses v1/open-close for options; IV may not be present. Falls back to aggregates.
        """
        # v1 open-close may not support options fully; use v2 aggs (1 day) for pricing/OI
        url = f"{POLYGON_BASE}/v2/aggs/ticker/{option_symbol}/range/1/day/{self._iso(date)}/{self._iso(date)}"
        params = {"adjusted": "true", "limit": "1", "apiKey": self.api_key}
        try:
            data = _retry_get(url, params)
        except Exception:
            return None
        results = data.get("results", [])
        if not results:
            return None
        res = results[0]
        # Polygon uses field names: o,h,l,c,v,op,oib? Check docs; OI often via /snapshot for options chain
        # We'll capture available fields; OI via daily snapshot endpoint v3 if present
        snapshot_oi = self.get_daily_oi(option_symbol, date)
        return {
            "date": self._iso(date),
            "open": res.get("o"),
            "high": res.get("h"),
            "low": res.get("l"),
            "close": res.get("c"),
            "volume": res.get("v"),
            "open_interest": snapshot_oi,
        }

    def get_daily_oi(self, option_symbol: str, date: dt.date) -> Optional[int]:
        """Attempt to fetch daily OI for option using v3 endpoint."""
        url = f"{POLYGON_BASE}/v3/reference/options/oi"
        params = {
            "ticker": option_symbol,
            "date": self._iso(date),
            "apiKey": self.api_key,
            "limit": "1",
        }
        try:
            data = _retry_get(url, params)
        except Exception:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return results[0].get("oi")

    def get_underlying_close(self, date: dt.date) -> Optional[float]:
        url = f"{POLYGON_BASE}/v2/aggs/ticker/{self.underlying}/range/1/day/{self._iso(date)}/{self._iso(date)}"
        params = {"adjusted": "true", "limit": "1", "apiKey": self.api_key}
        try:
            data = _retry_get(url, params)
        except Exception:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return float(results[0].get("c"))

    def option_symbol(self, expiration: dt.date, strike: float, right: str) -> str:
        """Constructs Polygon option ticker: O:[root][YY][MM][DD][C/P][strike*1000 no dot]."""
        root = self.underlying
        yy = expiration.strftime("%y")
        mm = expiration.strftime("%m")
        dd = expiration.strftime("%d")
        cp = "C" if right.upper().startswith("C") else "P"
        strike_int = int(round(strike * 1000))
        return f"O:{root}{yy}{mm}{dd}{cp}{strike_int:08d}"
