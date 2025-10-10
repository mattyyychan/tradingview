import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from volsurf.utils.iv import implied_volatility_newton


@dataclass
class Quote:
    date: dt.date
    expiration: dt.date
    strike: float
    right: str  # 'C' or 'P'
    mark: float
    open_interest: Optional[int]


def year_to_date_dates(today: Optional[dt.date] = None) -> List[dt.date]:
    ref = today or dt.date.today()
    start = dt.date(ref.year, 1, 1)
    days: List[dt.date] = []
    cur = start
    while cur <= ref:
        # include all calendar days; provider will return None for non-trading days
        days.append(cur)
        cur += dt.timedelta(days=1)
    return days


class SurfaceBuilder:
    def __init__(self, provider, risk_free_rate: float = 0.05) -> None:
        self.provider = provider
        self.r = risk_free_rate

    def build_quotes_for_date(self, date: dt.date, expirations: Iterable[dt.date], strikes: Iterable[float], right: str) -> List[Quote]:
        quotes: List[Quote] = []
        for expiry in expirations:
            for strike in strikes:
                sym = self.provider.option_symbol(expiry, strike, right)
                snap = self.provider.get_daily_option_snapshot(sym, date)
                if not snap or snap.get("close") is None:
                    continue
                mark = float(snap["close"])  # using close as mark
                oi = snap.get("open_interest")
                quotes.append(Quote(date=date, expiration=expiry, strike=float(strike), right=right[0].upper(), mark=mark, open_interest=oi))
        return quotes

    def compute_iv_surface(self, date: dt.date, quotes: List[Quote]) -> pd.DataFrame:
        s = self.provider.get_underlying_close(date)
        if s is None:
            return pd.DataFrame()
        rows = []
        for q in quotes:
            t = max(0.0, (q.expiration - date).days) / 365.25
            if t <= 0:
                continue
            is_call = q.right.upper().startswith("C")
            sigma = implied_volatility_newton(q.mark, s, q.strike, t, self.r, is_call)
            if sigma is None:
                continue
            rows.append({
                "date": date,
                "expiration": q.expiration,
                "tenor_days": (q.expiration - date).days,
                "strike": q.strike,
                "moneyness": q.strike / s,
                "right": q.right,
                "mark": q.mark,
                "iv": sigma,
                "open_interest": q.open_interest,
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df.sort_values(["tenor_days", "strike"], inplace=True)
        return df

    def save_surface(self, df: pd.DataFrame, out_path: str) -> None:
        if df.empty:
            return
        # Partition by date for efficient time series access
        df.to_parquet(out_path, index=False)
