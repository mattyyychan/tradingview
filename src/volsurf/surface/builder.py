import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Optional, Dict, Any

import pyarrow as pa
import pyarrow.parquet as pq

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

    def compute_iv_surface_rows(self, date: dt.date, quotes: List[Quote]) -> List[Dict[str, Any]]:
        s = self.provider.get_underlying_close(date)
        if s is None:
            return []
        rows: List[Dict[str, Any]] = []
        for q in quotes:
            tenor_days = (q.expiration - date).days
            t = max(0.0, tenor_days) / 365.25
            if t <= 0:
                continue
            is_call = q.right.upper().startswith("C")
            sigma = implied_volatility_newton(q.mark, s, q.strike, t, self.r, is_call)
            if sigma is None:
                continue
            rows.append({
                "date": date,
                "expiration": q.expiration,
                "tenor_days": int(tenor_days),
                "strike": float(q.strike),
                "moneyness": float(q.strike / s),
                "right": q.right,
                "mark": float(q.mark),
                "iv": float(sigma),
                "open_interest": None if q.open_interest is None else int(q.open_interest),
            })
        rows.sort(key=lambda r: (r["tenor_days"], r["strike"]))
        return rows

    def save_surface_rows(self, rows: List[Dict[str, Any]], out_path: str) -> None:
        if not rows:
            return
        # Define an explicit schema for stability
        schema = pa.schema([
            ("date", pa.date32()),
            ("expiration", pa.date32()),
            ("tenor_days", pa.int32()),
            ("strike", pa.float64()),
            ("moneyness", pa.float64()),
            ("right", pa.string()),
            ("mark", pa.float64()),
            ("iv", pa.float64()),
            ("open_interest", pa.int64()),
        ])
        # Convert date objects to date32 compatible by ensuring Python date
        table = pa.Table.from_pylist(rows, schema=schema)
        pq.write_table(table, out_path)
