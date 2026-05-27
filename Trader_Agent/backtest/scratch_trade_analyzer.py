import pandas as pd
import numpy as np
import pandas_ta as ta
from pathlib import Path

# Load data
DATA_PATH = Path("/Users/chz/Desktop/AI Agent/Trader_Agent/backtest/data/btc_1h.csv")
df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True)

close = df["close"]
close_pct = close.pct_change().fillna(0)

# Calculate indicators
daily = close.resample("1D").last().dropna()
ema200d = daily.ewm(span=200, adjust=False).mean()
ema200_1h = ema200d.reindex(df.index, method="ffill")
is_bull = close > ema200_1h

ema_f = ta.ema(close, 25)
ema_s = ta.ema(close, 100)
rsi = ta.rsi(close, 14)

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

# Signals
long_sig = crossover(ema_f, ema_s) & (rsi < 60)
short_sig = crossunder(ema_f, ema_s) & (rsi > 35) & ~is_bull

# Build positions
pos = np.zeros(len(close), dtype=np.int8)
current = 0
for i in range(len(pos)):
    if long_sig.iloc[i]:
        current = 1
    elif short_sig.iloc[i]:
        current = -1
    pos[i] = current

pos_series = pd.Series(pos, index=close.index)

# Track trades
trades = []
current_pos = 0
entry_idx = None

for i in range(len(pos_series)):
    p = pos_series.iloc[i]
    if p != current_pos:
        if current_pos != 0:
            # Exit previous trade
            exit_price = close.iloc[i]
            exit_time = close.index[i]
            entry_price = close.iloc[entry_idx]
            entry_time = close.index[entry_idx]
            
            pnl = (exit_price - entry_price) / entry_price if current_pos == 1 else (entry_price - exit_price) / entry_price
            trades.append({
                "type": "LONG" if current_pos == 1 else "SHORT",
                "entry_time": entry_time,
                "entry_price": entry_price,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "pnl": pnl * 100
            })
        current_pos = p
        entry_idx = i

# Convert to DataFrame
df_trades = pd.DataFrame(trades)
df_trades["pnl_cum"] = (1 + df_trades["pnl"] / 100).cumprod() * 100 - 100

# Sort by worst trades
worst_trades = df_trades.sort_values("pnl").head(10)
print("=== TOP 10 WORST TRADES ===")
print(worst_trades.to_string())

print("\n=== TOTAL TRADES ===")
print(f"Total trades: {len(df_trades)}")
print(f"Average PnL per trade: {df_trades['pnl'].mean():.2f}%")
print(f"Max PnL: {df_trades['pnl'].max():.2f}%")
print(f"Min PnL: {df_trades['pnl'].min():.2f}%")
