#!/usr/bin/env python3
import argparse
import datetime as dt
import os
from typing import List

import sys

# Ensure local src is importable when running as script
sys.path.insert(0, "/workspace/src")

from volsurf.providers.polygon import PolygonOptionsProvider
from volsurf.surface.builder import SurfaceBuilder, year_to_date_dates


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build NVDA YTD volatility surface time series with OI")
    p.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD (default: Jan 1)")
    p.add_argument("--end", type=str, default=None, help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--rights", type=str, default="C", help="Option rights to include, e.g., C,P")
    p.add_argument("--expirations", type=str, default=None, help="CSV of expirations YYYY-MM-DD; default: next 6 weeklies + 3 monthlies")
    p.add_argument("--strikes", type=str, default=None, help="CSV of strikes (floats) around ATM; default: 0.5x to 1.5x in 5% steps (derived daily)")
    p.add_argument("--out", type=str, default="/workspace/data/surfaces/nvda_ytd.parquet", help="Output parquet path")
    return p.parse_args()


def derive_default_expirations(today: dt.date) -> List[dt.date]:
    # Next 6 Fridays + 3 monthly expirations approx
    exp: List[dt.date] = []
    cur = today
    # add 6 weekly Fridays
    while len(exp) < 6:
        cur += dt.timedelta(days=1)
        if cur.weekday() == 4:  # Friday
            exp.append(cur)
    # add 3 month-ends (approx options monthlies)
    cur = today
    for _ in range(3):
        month = cur.month + 1
        year = cur.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        last_day = (dt.date(year, month, 1) - dt.timedelta(days=1)).day
        month_end = dt.date(cur.year, cur.month, last_day)
        # shift to Friday of that week
        friday = month_end + dt.timedelta(days=(4 - month_end.weekday()) % 7)
        if friday > today:
            exp.append(friday)
        cur = cur.replace(day=1) + dt.timedelta(days=32)
        cur = cur.replace(day=1)
    # unique & sorted
    exp = sorted(set(exp))
    return exp


def derive_default_strikes(s_close: float) -> List[float]:
    levels = [x / 100.0 for x in range(50, 151, 5)]  # 0.50x .. 1.50x
    return [round(s_close * m, 2) for m in levels]


def main() -> None:
    args = parse_args()
    if args.start and args.end:
        dates = []
        start = dt.datetime.strptime(args.start, "%Y-%m-%d").date()
        end = dt.datetime.strptime(args.end, "%Y-%m-%d").date()
        cur = start
        while cur <= end:
            dates.append(cur)
            cur += dt.timedelta(days=1)
    else:
        dates = year_to_date_dates()

    provider = PolygonOptionsProvider("NVDA")
    builder = SurfaceBuilder(provider)

    total_rows = 0
    rights = [r.strip().upper() for r in args.rights.split(",") if r.strip()]

    for d in dates:
        s_close = provider.get_underlying_close(d)
        if s_close is None:
            continue
        if args.expirations:
            expirations = [dt.datetime.strptime(x.strip(), "%Y-%m-%d").date() for x in args.expirations.split(",") if x.strip()]
        else:
            expirations = derive_default_expirations(d)
        if args.strikes:
            strikes = [float(x.strip()) for x in args.strikes.split(",") if x.strip()]
        else:
            strikes = derive_default_strikes(s_close)
        day_quotes = []
        for right in rights:
            day_quotes.extend(builder.build_quotes_for_date(d, expirations, strikes, right))
        rows = builder.compute_iv_surface_rows(d, day_quotes)
        if rows:
            # accumulate daily and write append-style by reading existing and concatenating in memory could be heavy;
            # instead we will collect all then write once outside the loop to a single parquet
            total_rows += len(rows)
            # buffer rows on disk per-day then merge at end
            tmp_path = f"/workspace/data/surfaces/_tmp_nvda_{d.isoformat()}.parquet"
            builder.save_surface_rows(rows, tmp_path)

    if total_rows == 0:
        print("No data collected. Check API key or parameters.")
        return
    out_path = args.out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Merge temp parquet files
    import pyarrow.parquet as pq
    import pyarrow as pa
    tmp_files = sorted(f for f in os.listdir("/workspace/data/surfaces") if f.startswith("_tmp_nvda_") and f.endswith(".parquet"))
    tables = [pq.read_table(os.path.join("/workspace/data/surfaces", f)) for f in tmp_files]
    if not tables:
        print("No temp files found despite row count.")
        return
    table = pa.concat_tables(tables, promote=True)
    # sort by date, tenor, strike
    import pyarrow.compute as pc
    sort_keys = [
        ("date", "ascending"),
        ("tenor_days", "ascending"),
        ("strike", "ascending"),
    ]
    indices = pc.sort_indices(table, sort_keys=sort_keys)
    table = pc.take(table, indices)
    pq.write_table(table, out_path)
    # cleanup temp files
    for f in tmp_files:
        try:
            os.remove(os.path.join("/workspace/data/surfaces", f))
        except Exception:
            pass
    print(f"Saved {table.num_rows} rows to {out_path}")


if __name__ == "__main__":
    main()
