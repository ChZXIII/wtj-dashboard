"""
run_options.py
รัน Backtest 2 Options และเปรียบเทียบกับ Original L+S
  Option A: Long-Only (flat เมื่อ Short signal)
  Option B: Long+Short + EMA200 Daily Macro Filter

Usage:
    python backtest/run_options.py
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import seaborn as sns
from strategies import STRATEGIES

# ─── Settings ───────────────────────────────────────────────────────────────
FEE_RATE    = 0.001
DATA_PATH   = Path(__file__).parent / "data" / "btc_1h.csv"
RESULTS_DIR = Path(__file__).parent / "results"
CHARTS_DIR  = RESULTS_DIR / "charts_options"

plt.rcParams.update({
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#1a1d2e",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#c9d1d9",
    "ytick.color":      "#c9d1d9",
    "text.color":       "#c9d1d9",
    "grid.color":       "#30363d",
    "grid.linewidth":   0.5,
    "legend.facecolor": "#161b22",
    "legend.edgecolor": "#30363d",
})

# ─── Position Modes ──────────────────────────────────────────────────────────

def pos_long_only(long_entry: pd.Series, short_entry: pd.Series) -> pd.Series:
    """Long-only: Long เมื่อ signal, Flat เมื่อ short signal"""
    pos = pd.Series(0, index=long_entry.index, dtype=int)
    current = 0
    for i in range(len(pos)):
        if long_entry.iloc[i]:
            current = 1
        elif short_entry.iloc[i]:
            current = 0   # flat แทน short
        pos.iloc[i] = current
    return pos


def pos_long_short(long_entry: pd.Series, short_entry: pd.Series) -> pd.Series:
    """Long+Short full flip"""
    pos = pd.Series(0, index=long_entry.index, dtype=int)
    current = 0
    for i in range(len(pos)):
        if long_entry.iloc[i]:
            current = 1
        elif short_entry.iloc[i]:
            current = -1
        pos.iloc[i] = current
    return pos


# ─── Macro Filter (EMA 200 Daily) ────────────────────────────────────────────

def compute_macro_filter(df: pd.DataFrame) -> pd.Series:
    """
    Resample 1H → Daily, คำนวณ EMA200 แล้ว forward-fill กลับมา 1H
    Macro trend = BULLISH เมื่อ Close > EMA200_Daily
    """
    daily = df["close"].resample("1D").last().dropna()
    ema200_daily = daily.ewm(span=200, adjust=False).mean()
    # Reindex กลับมา 1H แล้ว forward fill
    ema200_1h = ema200_daily.reindex(df.index, method="ffill")
    is_bull = df["close"] > ema200_1h
    return is_bull


def get_strategy_signals(df: pd.DataFrame, name: str, func) -> tuple:
    """แยก Long/Short signals จาก strategy"""
    import pandas_ta as ta

    def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
    def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    if name == "EMA Cross 9/21":
        e1, e2 = ta.ema(close, 9), ta.ema(close, 21)
        return crossover(e1, e2), crossunder(e1, e2)
    elif name == "EMA Cross 20/50":
        e1, e2 = ta.ema(close, 20), ta.ema(close, 50)
        return crossover(e1, e2), crossunder(e1, e2)
    elif name == "EMA Cross 50/200":
        e1, e2 = ta.ema(close, 50), ta.ema(close, 200)
        return crossover(e1, e2), crossunder(e1, e2)
    elif name == "Supertrend (10,3)":
        st  = ta.supertrend(high, low, close, length=10, multiplier=3)
        dcol = [c for c in st.columns if "SUPERTd" in c][0]
        d   = st[dcol]
        return (d == 1) & (d.shift(1) == -1), (d == -1) & (d.shift(1) == 1)
    elif name == "RSI (14)":
        rsi = ta.rsi(close, 14)
        return crossover(rsi, pd.Series(30, index=rsi.index)), crossunder(rsi, pd.Series(70, index=rsi.index))
    elif name == "Stochastic RSI":
        stoch = ta.stochrsi(close, 14, 14, 3, 3)
        k = stoch[[c for c in stoch.columns if "STOCHRSIk" in c][0]]
        d = stoch[[c for c in stoch.columns if "STOCHRSId" in c][0]]
        return crossover(k, d) & (k < 20), crossunder(k, d) & (k > 80)
    elif name == "MACD (12/26/9)":
        m   = ta.macd(close, 12, 26, 9)
        ml  = m[[c for c in m.columns if c.startswith("MACD_")][0]]
        sl  = m[[c for c in m.columns if c.startswith("MACDs_")][0]]
        return crossover(ml, sl), crossunder(ml, sl)
    elif name == "Bollinger Bands":
        bb  = ta.bbands(close, 20, 2)
        lo  = bb[[c for c in bb.columns if "BBL_" in c][0]]
        up  = bb[[c for c in bb.columns if "BBU_" in c][0]]
        return crossover(close, lo), crossunder(close, up)
    elif name == "Keltner Channel":
        kc  = ta.kc(high, low, close, 20, 2)
        up  = kc[[c for c in kc.columns if "KCUe_" in c][0]]
        lo  = kc[[c for c in kc.columns if "KCLe_" in c][0]]
        return crossover(close, up), crossunder(close, lo)
    elif name == "VWAP":
        df2        = df.copy()
        df2["date"] = df2.index.date
        df2["tp"]   = (df2["high"] + df2["low"] + df2["close"]) / 3
        df2["tpv"]  = df2["tp"] * df2["volume"]
        vwap       = df2.groupby("date")["tpv"].cumsum() / df2.groupby("date")["volume"].cumsum()
        surge      = df["volume"] > df["volume"].rolling(20).mean() * 1.5
        return crossover(close, vwap) & surge, crossunder(close, vwap) & surge
    elif name == "OBV Trend":
        obv    = ta.obv(close, df["volume"])
        obv_ma = obv.rolling(20).mean()
        return crossover(obv, obv_ma), crossunder(obv, obv_ma)
    elif name == "EMA + RSI Filter":
        e1, e2 = ta.ema(close, 20), ta.ema(close, 50)
        rsi = ta.rsi(close, 14)
        return crossover(e1, e2) & (rsi < 60), crossunder(e1, e2) & (rsi > 40)
    else:
        raise ValueError(f"Unknown strategy: {name}")


# ─── Backtest Engine ─────────────────────────────────────────────────────────

def backtest(df: pd.DataFrame, positions: pd.Series, fee_rate: float = FEE_RATE) -> dict:
    close       = df["close"]
    pct_returns = close.pct_change().fillna(0)
    pos_shifted = positions.shift(1).fillna(0)
    strat_ret   = pos_shifted * pct_returns
    fee_ret     = positions.diff().fillna(0).abs() * fee_rate
    net_ret     = strat_ret - fee_ret
    equity      = (1 + net_ret).cumprod() * 100
    bh_equity   = (1 + pct_returns).cumprod() * 100

    total_return = equity.iloc[-1] - 100
    years  = len(df) / (365 * 24)
    cagr   = ((equity.iloc[-1] / 100) ** (1 / years) - 1) * 100
    sharpe = (net_ret.mean() / net_ret.std()) * np.sqrt(365 * 24) if net_ret.std() != 0 else 0
    rolling_max = equity.cummax()
    max_dd = ((equity - rolling_max) / rolling_max * 100).min()
    down   = net_ret[net_ret < 0]
    sortino = (net_ret.mean() / down.std()) * np.sqrt(365 * 24) if len(down) > 0 and down.std() != 0 else 0
    gp = net_ret[net_ret > 0].sum()
    gl = abs(net_ret[net_ret < 0].sum())
    pf = gp / gl if gl != 0 else np.inf

    trades = int(positions.diff().fillna(0).abs().gt(0).sum())
    pos_only = net_ret[pos_shifted != 0]
    wins  = pos_only[pos_only > 0]
    win_rate = len(wins) / len(pos_only) * 100 if len(pos_only) > 0 else 0

    return {
        "equity": equity, "bh_equity": bh_equity,
        "total_return": round(total_return, 2),
        "cagr":         round(cagr, 2),
        "sharpe":       round(sharpe, 3),
        "sortino":      round(sortino, 3),
        "max_dd":       round(max_dd, 2),
        "profit_factor":round(pf, 3),
        "total_trades": trades,
        "win_rate":     round(win_rate, 1),
    }


# ─── Plotting ────────────────────────────────────────────────────────────────

def plot_comparison_equity(all_A: dict, all_B: dict, bh_equity: pd.Series):
    """Plot equity curve ทุก strategy ทั้ง 2 options"""
    fig, axes = plt.subplots(1, 2, figsize=(22, 9), facecolor="#0f1117")
    fig.suptitle("BTC/USDT 1H — Option A vs Option B | 6 Years", color="#e6edf3", fontsize=14)

    colors = plt.cm.tab20(np.linspace(0, 1, len(all_A)))

    for ax, (all_res, title) in zip(axes, [
        (all_A, "Option A: Long-Only"),
        (all_B, "Option B: Long+Short + EMA200D Filter"),
    ]):
        ax.set_facecolor("#0f1117")
        ax.plot(bh_equity.index, bh_equity.values, color="white",
                linewidth=2, linestyle="--", alpha=0.6, label="Buy & Hold", zorder=10)
        ax.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")

        for (name, res), color in zip(all_res.items(), colors):
            ax.plot(res["equity"].index, res["equity"].values,
                    linewidth=0.9, label=name, color=color, alpha=0.85)

        ax.set_title(title, color="#e6edf3", fontsize=11)
        ax.set_ylabel("Portfolio Value (%) — Start = 100%", color="#c9d1d9")
        ax.legend(loc="upper left", fontsize=6.5, ncol=2)

    plt.tight_layout()
    path = RESULTS_DIR / "options_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_summary_comparison(df_A: pd.DataFrame, df_B: pd.DataFrame, bh_return: float):
    """Bar chart เปรียบเทียบ Key Metrics ทั้ง 2 Options"""
    metrics = [
        ("total_return",  "Total Return (%)"),
        ("cagr",          "CAGR (%)"),
        ("sharpe",        "Sharpe Ratio"),
        ("max_dd",        "Max Drawdown (%)"),
        ("win_rate",      "Win Rate (%)"),
        ("profit_factor", "Profit Factor"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(22, 12), facecolor="#0f1117")
    fig.suptitle("📊 Option A vs Option B — Strategy Comparison | BTC/USDT 1H 6Y",
                 color="#e6edf3", fontsize=14, y=0.99)

    strategies = df_A["strategy"].tolist()
    x = np.arange(len(strategies))
    width = 0.38

    color_A = "#58a6ff"
    color_B = "#3fb950"

    for ax, (col, label) in zip(axes.flat, metrics):
        vals_A = df_A.set_index("strategy").loc[strategies, col].values.astype(float)
        vals_B = df_B.set_index("strategy").loc[strategies, col].values.astype(float)

        bars_A = ax.bar(x - width/2, vals_A, width, label="Option A (Long-Only)", color=color_A, alpha=0.85)
        bars_B = ax.bar(x + width/2, vals_B, width, label="Option B (L+S+Filter)",  color=color_B, alpha=0.85)

        # Benchmark line สำหรับ total_return
        if col == "total_return":
            ax.axhline(bh_return, color="white", linewidth=1.5, linestyle="--", alpha=0.7, label=f"B&H: +{bh_return:.0f}%")

        ax.set_title(label, color="#e6edf3", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace(" ", "\n") for s in strategies], fontsize=6.5, color="#c9d1d9")
        ax.tick_params(colors="#c9d1d9")
        if col in ("sharpe", "profit_factor", "win_rate"):
            ax.axhline(0, color="#30363d", linewidth=0.8)
        ax.legend(fontsize=7, loc="best")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = RESULTS_DIR / "options_comparison.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_winner_detail(name_A: str, res_A: dict, name_B: str, res_B: dict, bh: pd.Series):
    """Equity + Drawdown ของ Winner แต่ละ Option"""
    fig = plt.figure(figsize=(20, 10), facecolor="#0f1117")
    fig.suptitle(f"🏆 Winners — Option A: {name_A}  |  Option B: {name_B}", color="#e6edf3", fontsize=13)
    gs = gridspec.GridSpec(2, 2, height_ratios=[3, 1], hspace=0.1)

    for col, (name, res) in enumerate([(name_A, res_A), (name_B, res_B)]):
        ax1 = fig.add_subplot(gs[0, col])
        ax2 = fig.add_subplot(gs[1, col], sharex=ax1)

        color = "#58a6ff" if col == 0 else "#3fb950"
        label = f"Option {'A' if col==0 else 'B'}: {name}"

        ax1.plot(res["equity"].index, res["equity"].values, color=color, linewidth=1.5, label=label)
        ax1.plot(bh.index, bh.values, color="white", linewidth=1, linestyle="--", alpha=0.5, label="Buy & Hold")
        ax1.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")

        stats = (
            f"Total Return : {res['total_return']:+.1f}%\n"
            f"CAGR         : {res['cagr']:+.1f}%\n"
            f"Sharpe       : {res['sharpe']:.2f}\n"
            f"Sortino      : {res['sortino']:.2f}\n"
            f"Max DD       : {res['max_dd']:.1f}%\n"
            f"Win Rate     : {res['win_rate']:.1f}%\n"
            f"Profit Factor: {res['profit_factor']:.2f}\n"
            f"Total Trades : {res['total_trades']:,}"
        )
        ax1.text(0.01, 0.97, stats, transform=ax1.transAxes, fontsize=8,
                 verticalalignment="top", fontfamily="monospace",
                 bbox=dict(facecolor="#161b22", edgecolor=color, alpha=0.9))

        title_label = "Long-Only" if col == 0 else "Long+Short + EMA200D Filter"
        ax1.set_title(f"{title_label}", color="#e6edf3", fontsize=10)
        ax1.legend(loc="upper left", fontsize=8)
        ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")

        # Drawdown
        rolling_max = res["equity"].cummax()
        dd = (res["equity"] - rolling_max) / rolling_max * 100
        ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
        ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")
        plt.setp(ax1.get_xticklabels(), visible=False)

    plt.tight_layout()
    path = RESULTS_DIR / "winners_detail.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_macro_filter_visual(df: pd.DataFrame, is_bull: pd.Series):
    """แสดงช่วงเวลาที่ Macro Filter อนุญาต Short"""
    import pandas_ta as ta
    daily = df["close"].resample("1D").last().dropna()
    ema200d = daily.ewm(span=200, adjust=False).mean().reindex(df.index, method="ffill")

    # Sample รายวัน
    df_day = df["close"].resample("1D").last()
    ema200_day = ema200d.resample("1D").last()
    is_bull_day = (df_day > ema200_day).reindex(df_day.index)

    fig, ax = plt.subplots(figsize=(20, 6), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")

    ax.plot(df_day.index, df_day.values, color="#58a6ff", linewidth=0.8, label="BTC Price (Daily)", alpha=0.9)
    ax.plot(ema200_day.index, ema200_day.values, color="#ffa657", linewidth=1.5, label="EMA 200 Daily", alpha=0.9)

    # แรเงาช่วง Bearish (Short Allowed)
    bear_mask = ~is_bull_day
    prev = False
    start = None
    for idx, val in bear_mask.items():
        if val and not prev:
            start = idx
        elif not val and prev and start is not None:
            ax.axvspan(start, idx, color="#f85149", alpha=0.15)
            start = None
        prev = val
    if start is not None:
        ax.axvspan(start, bear_mask.index[-1], color="#f85149", alpha=0.15)

    ax.set_yscale("log")
    ax.set_title("Macro Filter — 🔴 Short Allowed (Below EMA200D) | 🟢 Long Only (Above EMA200D)",
                 color="#e6edf3", fontsize=11)
    ax.set_ylabel("BTC Price (log)", color="#c9d1d9")
    ax.legend(fontsize=9)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#f85149", alpha=0.3, label="Short Allowed (Bear Trend)"),
        Patch(facecolor="#3fb950", alpha=0.3, label="Long Only (Bull Trend)"),
    ]
    ax.legend(handles=legend_elements + ax.get_legend_handles_labels()[0][:2], fontsize=8)

    plt.tight_layout()
    path = RESULTS_DIR / "macro_filter_zones.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("📥 โหลดข้อมูล")
    print("=" * 65)
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    # Macro Filter
    print("\n🔍 คำนวณ Macro Filter (EMA 200 Daily) ...")
    is_bull = compute_macro_filter(df)
    bull_pct = is_bull.mean() * 100
    print(f"✅ Macro Filter: Bull {bull_pct:.1f}% | Bear {100-bull_pct:.1f}% ของ 6 ปี")

    # Plot macro zones
    print("📈 Plot Macro Filter zones ...")
    p_macro = plot_macro_filter_visual(df, is_bull)
    print(f"✅ {p_macro}")

    print("\n" + "=" * 65)
    print("🚀 รัน Backtest — Option A (Long-Only) + Option B (L+S+Filter)")
    print("=" * 65)

    results_A, results_B = {}, {}
    rows_A, rows_B = [], []

    for name, func in STRATEGIES.items():
        print(f"\n▶ {name:<22}", end=" ", flush=True)
        try:
            long_sig, short_sig = get_strategy_signals(df, name, func)

            # Option A: Long-Only
            pos_A = pos_long_only(long_sig, short_sig)
            res_A = backtest(df, pos_A)
            results_A[name] = res_A

            # Option B: L+S with Macro Filter
            # Short signal ทำงานได้เฉพาะตอน Bearish (Close < EMA200D)
            short_filtered = short_sig & ~is_bull
            pos_B = pos_long_short(long_sig, short_filtered)
            res_B = backtest(df, pos_B)
            results_B[name] = res_B

            print(f"A: {res_A['total_return']:>+7.1f}% Sh:{res_A['sharpe']:>5.2f}  |  "
                  f"B: {res_B['total_return']:>+7.1f}% Sh:{res_B['sharpe']:>5.2f}")

            rows_A.append({"strategy": name, **{k: v for k, v in res_A.items() if k not in ("equity", "bh_equity")}})
            rows_B.append({"strategy": name, **{k: v for k, v in res_B.items() if k not in ("equity", "bh_equity")}})

        except Exception as e:
            print(f"❌ {e}")
            import traceback; traceback.print_exc()

    # ─── Summary Tables ───
    df_A = pd.DataFrame(rows_A).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_B = pd.DataFrame(rows_B).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_A.index += 1
    df_B.index += 1

    bh_return = float(list(results_A.values())[0]["bh_equity"].iloc[-1] - 100)

    print("\n" + "=" * 65)
    print("📊 OPTION A — Long-Only (Ranking by Sharpe)")
    print("=" * 65)
    print(f"{'Rk':<4} {'Strategy':<22} {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'WinR%':>7} {'PF':>6} {'Trades':>7}")
    print("-" * 80)
    for i, r in df_A.iterrows():
        print(f"{i:<4} {r['strategy']:<22} {r['total_return']:>+9.1f} {r['cagr']:>+7.1f} "
              f"{r['sharpe']:>7.2f} {r['max_dd']:>8.1f} {r['win_rate']:>6.1f}% {r['profit_factor']:>6.2f} {int(r['total_trades']):>7,}")
    print(f"\n  ★ Buy & Hold: +{bh_return:.1f}%")

    print("\n" + "=" * 65)
    print("📊 OPTION B — Long+Short + EMA200D Filter (Ranking by Sharpe)")
    print("=" * 65)
    print(f"{'Rk':<4} {'Strategy':<22} {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'WinR%':>7} {'PF':>6} {'Trades':>7}")
    print("-" * 80)
    for i, r in df_B.iterrows():
        print(f"{i:<4} {r['strategy']:<22} {r['total_return']:>+9.1f} {r['cagr']:>+7.1f} "
              f"{r['sharpe']:>7.2f} {r['max_dd']:>8.1f} {r['win_rate']:>6.1f}% {r['profit_factor']:>6.2f} {int(r['total_trades']):>7,}")
    print(f"\n  ★ Buy & Hold: +{bh_return:.1f}%")

    # ─── Save CSVs ───
    df_A.to_csv(RESULTS_DIR / "summary_option_A.csv")
    df_B.to_csv(RESULTS_DIR / "summary_option_B.csv")

    # ─── Charts ───
    print("\n📈 Plot กราฟ ...")
    p1 = plot_comparison_equity(results_A, results_B, list(results_A.values())[0]["bh_equity"])
    p2 = plot_summary_comparison(df_A, df_B, bh_return)

    winner_A = df_A.iloc[0]["strategy"]
    winner_B = df_B.iloc[0]["strategy"]
    p3 = plot_winner_detail(
        winner_A, results_A[winner_A],
        winner_B, results_B[winner_B],
        list(results_A.values())[0]["bh_equity"]
    )
    print(f"✅ Equity comparison : {p1}")
    print(f"✅ Metrics comparison: {p2}")
    print(f"✅ Winners detail    : {p3}")

    # ─── Final Summary ───
    print("\n" + "=" * 65)
    print(f"🏆 WINNER Option A (Long-Only)  : {winner_A}")
    wa = df_A.iloc[0]
    print(f"   Return: {wa['total_return']:+.1f}% | Sharpe: {wa['sharpe']:.2f} | MaxDD: {wa['max_dd']:.1f}%")

    print(f"\n🏆 WINNER Option B (L+S+Filter) : {winner_B}")
    wb = df_B.iloc[0]
    print(f"   Return: {wb['total_return']:+.1f}% | Sharpe: {wb['sharpe']:.2f} | MaxDD: {wb['max_dd']:.1f}%")

    print(f"\n⭐ Buy & Hold Benchmark          : +{bh_return:.1f}%")
    print("=" * 65)


if __name__ == "__main__":
    main()
