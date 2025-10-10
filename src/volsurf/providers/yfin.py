import datetime as dt
from typing import Dict, Optional

import yfinance as yf


class YFinanceProvider:
    """Lightweight snapshot provider using yfinance as a fallback."""

    def __init__(self, underlying: str = "NVDA") -> None:
        self.underlying = underlying.upper()

    def get_underlying_close(self, date: dt.date) -> Optional[float]:
        try:
            data = yf.download(self.underlying, start=date, end=date + dt.timedelta(days=1), progress=False, interval="1d")
            if data is None or data.empty:
                return None
            return float(data["Close"].iloc[0])
        except Exception:
            return None

    def get_chain_snapshot(self) -> Optional[Dict]:
        try:
            tk = yf.Ticker(self.underlying)
            exps = tk.options
            if not exps:
                return None
            exp = exps[0]
            calls = tk.option_chain(exp).calls
            puts = tk.option_chain(exp).puts
            return {"expiration": exp, "calls": calls, "puts": puts}
        except Exception:
            return None
