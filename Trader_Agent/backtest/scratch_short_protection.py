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

# Build positions with "Exit SHORT on Crossover" rule
pos = np.zeros(len(close), dtype=np.int8)
current = 0
for i in range(len(pos)):
    # 1. Check for entry signals
    if long_sig.iloc[i]:
        current = 1
    elif short_sig.iloc[i]:
        current = -1
    
    # 2. Check for exit rules (Whipsaw / Trend change protection)
    # If in SHORT, and a crossover happens (momentum flips up), we must exit SHORT to FLAT
    elif current == -1 and crossover(ema_f, ema_s).iloc[i]:
        current = 0
    # What if we are in LONG, and a crossunder happens? 
    # In pure reversal, we only exit on SHORT signal. 
    # Let's keep it that way for LONG to see if it protects SHORT.
    
    pos[i] = current

pos_series = pd.Series(pos, index=close.index)

# Backtest
FEE_RATE = 0.001
pos_shifted = pos_series.shift(1).fillna(0)
fee = pos_series.diff().fillna(0).abs() * FEE_RATE
net_ret = pos_shifted * close_pct - fee
equity = (1 + net_ret).cumprod()

total_return = (equity.iloc[-1] - 1) * 100
years = len(close_pct) / (365 * 24)
cagr = ((equity.iloc[-1]) ** (1 / years) - 1) * 100
std = net_ret.std()
sharpe = (net_ret.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0
rolling_max = equity.cummax()
max_dd = ((equity - rolling_max) / rolling_max * 100).min()
trades = int(pos_series.diff().fillna(0).abs().gt(0).sum())

print("=== EXIT SHORT ON CROSSOVER STRATEGY ===")
print(f"Total Return: {total_return:.2f}%")
print(f"CAGR: {cagr:.2f}%")
print(f"Sharpe: {sharpe:.4f}")
print(f"Max DD: {max_dd:.2f}%")
print(f"Trades: {trades}")

# Track trades
trades_list = []
current_pos = 0
entry_idx = None
for i in range(len(pos_series)):
    p = pos_series.iloc[i]
    if p != current_pos:
        if current_pos != 0:
            exit_price = close.iloc[i]
            exit_time = close.index[i]
            entry_price = close.iloc[entry_idx]
            entry_time = close.index[entry_idx]
            pnl = (exit_price - entry_price) / entry_price if current_pos == 1 else (entry_price - exit_price) / entry_price
            trades_list.append({
                "type": "LONG" if current_pos == 1 else "SHORT",
                "entry_time": entry_time,
                "exit_time": exit_time,
                "pnl": pnl * 100
            })
        current_pos = p
        entry_idx = i

df_trades = pd.DataFrame(trades_list)
worst_trades = df_trades.sort_values("pnl").head(5)
print("\n=== TOP 5 WORST TRADES ===")
print(worst_trades.to_string())
