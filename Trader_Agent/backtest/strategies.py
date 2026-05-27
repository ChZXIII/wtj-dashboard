"""
strategies.py
12 Indicator Strategies สำหรับ Backtest BTC/USDT 1H
Long + Short mode — ผลลัพธ์เป็น % Return ทั้งหมด

Signal convention:
  +1 = Long
  -1 = Short
   0 = No position (flat)
"""

import pandas as pd
import numpy as np
import pandas_ta as ta


def _crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """True เมื่อ a ข้าม b ขึ้นในแท่งปัจจุบัน"""
    return (series_a > series_b) & (series_a.shift(1) <= series_b.shift(1))


def _crossunder(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """True เมื่อ a ข้าม b ลงในแท่งปัจจุบัน"""
    return (series_a < series_b) & (series_a.shift(1) >= series_b.shift(1))


def signals_to_position(long_entry: pd.Series, short_entry: pd.Series) -> pd.Series:
    """
    แปลง Long/Short entry signals เป็น position series (+1/-1/0)
    ถือ position จนกว่าจะมี signal ตรงข้าม (flip)
    """
    pos = pd.Series(0, index=long_entry.index, dtype=int)
    current = 0
    for i in range(len(pos)):
        if long_entry.iloc[i]:
            current = 1
        elif short_entry.iloc[i]:
            current = -1
        pos.iloc[i] = current
    return pos


# ─────────────────────────────────────────
# 1. EMA Cross 9/21
# ─────────────────────────────────────────
def strategy_ema_9_21(df: pd.DataFrame) -> pd.Series:
    ema9  = ta.ema(df["close"], length=9)
    ema21 = ta.ema(df["close"], length=21)
    long  = _crossover(ema9, ema21)
    short = _crossunder(ema9, ema21)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 2. EMA Cross 20/50
# ─────────────────────────────────────────
def strategy_ema_20_50(df: pd.DataFrame) -> pd.Series:
    ema20 = ta.ema(df["close"], length=20)
    ema50 = ta.ema(df["close"], length=50)
    long  = _crossover(ema20, ema50)
    short = _crossunder(ema20, ema50)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 3. EMA Cross 50/200
# ─────────────────────────────────────────
def strategy_ema_50_200(df: pd.DataFrame) -> pd.Series:
    ema50  = ta.ema(df["close"], length=50)
    ema200 = ta.ema(df["close"], length=200)
    long   = _crossover(ema50, ema200)
    short  = _crossunder(ema50, ema200)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 4. Supertrend (10, 3)
# ─────────────────────────────────────────
def strategy_supertrend(df: pd.DataFrame) -> pd.Series:
    st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
    direction_col = [c for c in st.columns if "SUPERTd" in c][0]
    direction = st[direction_col]  # 1 = bullish, -1 = bearish
    long  = (direction == 1) & (direction.shift(1) == -1)
    short = (direction == -1) & (direction.shift(1) == 1)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 5. RSI (14) — Oversold/Overbought
# ─────────────────────────────────────────
def strategy_rsi(df: pd.DataFrame) -> pd.Series:
    rsi  = ta.rsi(df["close"], length=14)
    long  = _crossover(rsi, pd.Series(30, index=rsi.index))
    short = _crossunder(rsi, pd.Series(70, index=rsi.index))
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 6. Stochastic RSI
# ─────────────────────────────────────────
def strategy_stoch_rsi(df: pd.DataFrame) -> pd.Series:
    stoch = ta.stochrsi(df["close"], length=14, rsi_length=14, k=3, d=3)
    k_col = [c for c in stoch.columns if "STOCHRSIk" in c][0]
    d_col = [c for c in stoch.columns if "STOCHRSId" in c][0]
    k = stoch[k_col]
    d = stoch[d_col]
    long  = _crossover(k, d) & (k < 20)
    short = _crossunder(k, d) & (k > 80)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 7. MACD (12/26/9)
# ─────────────────────────────────────────
def strategy_macd(df: pd.DataFrame) -> pd.Series:
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    macd_col   = [c for c in macd_df.columns if c.startswith("MACD_")][0]
    signal_col = [c for c in macd_df.columns if c.startswith("MACDs_")][0]
    macd_line   = macd_df[macd_col]
    signal_line = macd_df[signal_col]
    long  = _crossover(macd_line, signal_line)
    short = _crossunder(macd_line, signal_line)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 8. Bollinger Bands (20, 2σ)
# ─────────────────────────────────────────
def strategy_bbands(df: pd.DataFrame) -> pd.Series:
    bb = ta.bbands(df["close"], length=20, std=2)
    lower_col = [c for c in bb.columns if "BBL_" in c][0]
    upper_col = [c for c in bb.columns if "BBU_" in c][0]
    lower = bb[lower_col]
    upper = bb[upper_col]
    # Long: close ลงมาถึง lower แล้ว close กลับขึ้นไปเหนือ lower
    long  = _crossover(df["close"], lower)
    # Short: close ขึ้นไปถึง upper แล้ว close กลับลงมาต่ำกว่า upper
    short = _crossunder(df["close"], upper)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 9. Keltner Channel
# ─────────────────────────────────────────
def strategy_keltner(df: pd.DataFrame) -> pd.Series:
    kc = ta.kc(df["high"], df["low"], df["close"], length=20, scalar=2)
    upper_col = [c for c in kc.columns if "KCUe_" in c][0]
    lower_col = [c for c in kc.columns if "KCLe_" in c][0]
    upper = kc[upper_col]
    lower = kc[lower_col]
    # Long: breakout above upper (momentum continuation)
    long  = _crossover(df["close"], upper)
    # Short: breakdown below lower
    short = _crossunder(df["close"], lower)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 10. VWAP (Daily reset)
# ─────────────────────────────────────────
def strategy_vwap(df: pd.DataFrame) -> pd.Series:
    # คำนวณ VWAP แบบ daily reset
    df2 = df.copy()
    df2["date"] = df2.index.date
    df2["tp"]   = (df2["high"] + df2["low"] + df2["close"]) / 3
    df2["tpv"]  = df2["tp"] * df2["volume"]
    df2["cum_tpv"] = df2.groupby("date")["tpv"].cumsum()
    df2["cum_vol"] = df2.groupby("date")["volume"].cumsum()
    vwap = df2["cum_tpv"] / df2["cum_vol"]

    vol_ma = df["volume"].rolling(20).mean()
    vol_surge = df["volume"] > vol_ma * 1.5

    long  = _crossover(df["close"], vwap) & vol_surge
    short = _crossunder(df["close"], vwap) & vol_surge
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 11. OBV Trend
# ─────────────────────────────────────────
def strategy_obv(df: pd.DataFrame) -> pd.Series:
    obv    = ta.obv(df["close"], df["volume"])
    obv_ma = obv.rolling(20).mean()
    # Long: OBV ข้ามค่าเฉลี่ยขึ้น (Bullish momentum)
    long  = _crossover(obv, obv_ma)
    # Short: OBV ข้ามค่าเฉลี่ยลง (Bearish momentum)
    short = _crossunder(obv, obv_ma)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# 12. EMA Cross + RSI Filter
# ─────────────────────────────────────────
def strategy_ema_rsi_filter(df: pd.DataFrame) -> pd.Series:
    ema20 = ta.ema(df["close"], length=20)
    ema50 = ta.ema(df["close"], length=50)
    rsi   = ta.rsi(df["close"], length=14)

    long  = _crossover(ema20, ema50) & (rsi < 60)
    short = _crossunder(ema20, ema50) & (rsi > 40)
    return signals_to_position(long, short)


# ─────────────────────────────────────────
# Registry
# ─────────────────────────────────────────
STRATEGIES = {
    "EMA Cross 9/21"       : strategy_ema_9_21,
    "EMA Cross 20/50"      : strategy_ema_20_50,
    "EMA Cross 50/200"     : strategy_ema_50_200,
    "Supertrend (10,3)"    : strategy_supertrend,
    "RSI (14)"             : strategy_rsi,
    "Stochastic RSI"       : strategy_stoch_rsi,
    "MACD (12/26/9)"       : strategy_macd,
    "Bollinger Bands"      : strategy_bbands,
    "Keltner Channel"      : strategy_keltner,
    "VWAP"                 : strategy_vwap,
    "OBV Trend"            : strategy_obv,
    "EMA + RSI Filter"     : strategy_ema_rsi_filter,
}
