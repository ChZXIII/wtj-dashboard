"""
fetch_data.py
ดึงข้อมูล BTC/USDT 1H ย้อนหลัง 6 ปีจาก Binance
"""

import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "data" / "btc_1h.csv"
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
YEARS = 6


def fetch_ohlcv(symbol: str, timeframe: str, years: int) -> pd.DataFrame:
    exchange = ccxt.binance({"enableRateLimit": True})

    since_dt = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    since_ts = int(since_dt.timestamp() * 1000) - years * 365 * 24 * 3600 * 1000

    all_ohlcv = []
    current_since = since_ts
    limit = 1000

    print(f"⏳ ดึงข้อมูล {symbol} {timeframe} ย้อนหลัง {years} ปี ...")
    print(f"   จาก: {datetime.fromtimestamp(since_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')}")
    print(f"   ถึง:  {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")

    batch = 0
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        batch += 1
        last_ts = ohlcv[-1][0]
        print(f"   Batch {batch:3d} | candles: {len(all_ohlcv):6,} | last: {datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}")

        if len(ohlcv) < limit:
            break

        current_since = last_ts + 1
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df


def main():
    if OUTPUT_PATH.exists():
        existing = pd.read_csv(OUTPUT_PATH, index_col=0, parse_dates=True)
        existing.index = pd.to_datetime(existing.index, utc=True)
        print(f"✅ พบข้อมูลเก่า: {len(existing):,} candles ({existing.index[0].date()} – {existing.index[-1].date()})")
        print("🔄 อัปเดตข้อมูลล่าสุด ...")

        last_ts = int(existing.index[-1].timestamp() * 1000) + 1
        exchange = ccxt.binance({"enableRateLimit": True})
        new_data = []
        current_since = last_ts

        while True:
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=current_since, limit=1000)
            if not ohlcv:
                break
            new_data.extend(ohlcv)
            if len(ohlcv) < 1000:
                break
            current_since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)

        if new_data:
            new_df = pd.DataFrame(new_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
            new_df["timestamp"] = pd.to_datetime(new_df["timestamp"], unit="ms", utc=True)
            new_df = new_df.set_index("timestamp")
            df = pd.concat([existing, new_df])
            df = df[~df.index.duplicated(keep="last")].sort_index()
            print(f"✅ เพิ่มข้อมูลใหม่ {len(new_data):,} candles | รวม: {len(df):,} candles")
        else:
            df = existing
            print("✅ ข้อมูลเป็นปัจจุบันแล้ว")
    else:
        df = fetch_ohlcv(SYMBOL, TIMEFRAME, YEARS)

    df.to_csv(OUTPUT_PATH)
    print(f"\n✅ บันทึกข้อมูลแล้ว: {OUTPUT_PATH}")
    print(f"   Total candles : {len(df):,}")
    print(f"   Period        : {df.index[0].date()} – {df.index[-1].date()}")
    print(f"   Missing check : {df.isnull().sum().sum()} null values")
    return df


if __name__ == "__main__":
    main()
