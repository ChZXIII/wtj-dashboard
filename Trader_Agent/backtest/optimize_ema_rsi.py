"""
optimize_ema_rsi.py
Grid Search Optimization สำหรับ EMA + RSI Filter Strategy
บน BTC/USDT 1H ย้อนหลัง 6 ปี + EMA200 Daily Macro Filter

Parameters ที่ Optimize:
  - EMA Fast  : 5, 8, 10, 12, 15, 20, 25
  - EMA Slow  : 20, 30, 50, 75, 100, 150, 200
  - RSI Long threshold  : 50, 55, 60, 65, 70 (Long เข้าได้ถ้า RSI < threshold)
  - RSI Short threshold : 30, 35, 40, 45, 50 (Short เข้าได้ถ้า RSI > threshold)

Constraint: EMA Fast < EMA Slow เสมอ

Usage:
    python backtest/optimize_ema_rsi.py
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product

DATA_PATH   = Path(__file__).parent / "data" / "btc_1h.csv"
RESULTS_DIR = Path(__file__).parent / "results"
FEE_RATE    = 0.001

plt.rcParams.update({
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#1a1d2e",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#c9d1d9",
    "ytick.color":      "#c9d1d9",
    "text.color":       "#c9d1d9",
    "grid.color":       "#30363d",
})

# ─── Parameter Grid ───────────────────────────────────────────────────────────

EMA_FAST_RANGE  = [5, 8, 10, 12, 15, 20, 25]
EMA_SLOW_RANGE  = [20, 30, 50, 75, 100, 150, 200]
RSI_LONG_RANGE  = [50, 55, 60, 65, 70]   # Long ถ้า RSI < value
RSI_SHORT_RANGE = [30, 35, 40, 45, 50]   # Short ถ้า RSI > value

# ─── Helpers ──────────────────────────────────────────────────────────────────

def compute_macro_filter(df: pd.DataFrame) -> pd.Series:
    daily      = df["close"].resample("1D").last().dropna()
    ema200d    = daily.ewm(span=200, adjust=False).mean()
    ema200_1h  = ema200d.reindex(df.index, method="ffill")
    return df["close"] > ema200_1h   # True = Bull


def crossover(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))

def crossunder(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def build_positions(close, ema_fast, ema_slow, rsi_long_thresh, rsi_short_thresh, is_bull):
    long_sig  = crossover(ema_fast, ema_slow) & (ta.rsi(close, 14) < rsi_long_thresh)
    short_sig = crossunder(ema_fast, ema_slow) & (ta.rsi(close, 14) > rsi_short_thresh) & ~is_bull

    pos = np.zeros(len(close), dtype=np.int8)
    current = 0
    for i in range(len(pos)):
        if long_sig.iloc[i]:
            current = 1
        elif short_sig.iloc[i]:
            current = -1
        pos[i] = current
    return pd.Series(pos, index=close.index)


def fast_backtest(close_pct: pd.Series, pos: pd.Series) -> dict:
    pos_shifted = pos.shift(1).fillna(0)
    fee         = pos.diff().fillna(0).abs() * FEE_RATE
    net_ret     = pos_shifted * close_pct - fee
    equity      = (1 + net_ret).cumprod()

    total_return = (equity.iloc[-1] - 1) * 100
    years        = len(close_pct) / (365 * 24)
    cagr         = ((equity.iloc[-1]) ** (1 / years) - 1) * 100
    std          = net_ret.std()
    sharpe       = (net_ret.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0
    down         = net_ret[net_ret < 0]
    sortino      = (net_ret.mean() / down.std()) * np.sqrt(365 * 24) if len(down) > 0 and down.std() > 0 else 0
    rolling_max  = equity.cummax()
    max_dd       = ((equity - rolling_max) / rolling_max * 100).min()
    gp = net_ret[net_ret > 0].sum()
    gl = abs(net_ret[net_ret < 0].sum())
    pf = gp / gl if gl > 0 else np.inf
    trades       = int(pos.diff().fillna(0).abs().gt(0).sum())

    return {
        "total_return": round(total_return, 2),
        "cagr":         round(cagr, 2),
        "sharpe":       round(sharpe, 4),
        "sortino":      round(sortino, 4),
        "max_dd":       round(max_dd, 2),
        "profit_factor":round(pf, 4),
        "trades":       trades,
    }


# ─── Plotting ──────────────────────────────────────────────────────────────────

def plot_heatmaps(results_df: pd.DataFrame, best: dict):
    """Heatmap: Sharpe vs EMA Fast/Slow (avg across RSI params)"""
    fig, axes = plt.subplots(1, 2, figsize=(20, 8), facecolor="#0f1117")
    fig.suptitle("🔥 EMA+RSI Filter — Grid Search Heatmap | BTC/USDT 1H 6Y",
                 color="#e6edf3", fontsize=13)

    for ax, metric, label, fmt in zip(axes,
            ["sharpe", "total_return"],
            ["Sharpe Ratio (avg)", "Total Return % (avg)"],
            [".2f", ".0f"]):
        pivot = results_df.groupby(["ema_fast", "ema_slow"])[metric].mean().unstack()
        sns.heatmap(pivot, ax=ax, cmap="RdYlGn", annot=True, fmt=fmt,
                    linewidths=0.3, linecolor="#0f1117",
                    cbar_kws={"shrink": 0.8})
        ax.set_title(label, color="#e6edf3", fontsize=10)
        ax.set_xlabel("EMA Slow", color="#c9d1d9")
        ax.set_ylabel("EMA Fast", color="#c9d1d9")
        ax.tick_params(colors="#c9d1d9")

    plt.tight_layout()
    path = RESULTS_DIR / "optimize_heatmap.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_rsi_heatmap(results_df: pd.DataFrame):
    """Heatmap: Sharpe vs RSI Long/Short thresholds"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="#0f1117")
    fig.suptitle("🔥 RSI Thresholds — Grid Search Heatmap",
                 color="#e6edf3", fontsize=12)

    for ax, metric, label, fmt in zip(axes,
            ["sharpe", "total_return"],
            ["Sharpe Ratio (avg)", "Total Return % (avg)"],
            [".2f", ".0f"]):
        pivot = results_df.groupby(["rsi_long", "rsi_short"])[metric].mean().unstack()
        sns.heatmap(pivot, ax=ax, cmap="RdYlGn", annot=True, fmt=fmt,
                    linewidths=0.3, linecolor="#0f1117",
                    cbar_kws={"shrink": 0.8})
        ax.set_title(label, color="#e6edf3", fontsize=10)
        ax.set_xlabel("RSI Short threshold", color="#c9d1d9")
        ax.set_ylabel("RSI Long threshold", color="#c9d1d9")
        ax.tick_params(colors="#c9d1d9")

    plt.tight_layout()
    path = RESULTS_DIR / "optimize_rsi_heatmap.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_top20_equity(df: pd.DataFrame, close: pd.Series, is_bull: pd.Series, bh_equity: pd.Series):
    """Equity curves ของ Top 20 Combinations"""
    fig, ax = plt.subplots(figsize=(20, 9), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")

    top20 = df.nlargest(20, "sharpe")
    colors = plt.cm.plasma(np.linspace(0.1, 0.95, 20))
    close_pct = close.pct_change().fillna(0)

    for (_, row), color in zip(top20.iterrows(), colors):
        ema_f = ta.ema(close, int(row["ema_fast"]))
        ema_s = ta.ema(close, int(row["ema_slow"]))
        pos   = build_positions(close, ema_f, ema_s,
                                int(row["rsi_long"]), int(row["rsi_short"]), is_bull)
        pos_shifted = pos.shift(1).fillna(0)
        fee     = pos.diff().fillna(0).abs() * FEE_RATE
        net_ret = pos_shifted * close_pct - fee
        equity  = (1 + net_ret).cumprod() * 100

        label = f"EMA{int(row['ema_fast'])}/{int(row['ema_slow'])} RSI<{int(row['rsi_long'])}/>>{int(row['rsi_short'])} Sh:{row['sharpe']:.2f}"
        ax.plot(equity.index, equity.values, linewidth=0.9, color=color, alpha=0.75, label=label)

    ax.plot(bh_equity.index, bh_equity.values * 100, color="white",
            linewidth=1.8, linestyle="--", alpha=0.6, label="Buy & Hold", zorder=10)
    ax.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax.set_ylabel("Portfolio Value (%) — Start = 100%", color="#c9d1d9")
    ax.set_title("🏆 Top 20 Combinations — EMA+RSI Filter | BTC/USDT 1H 6Y", color="#e6edf3", fontsize=12)
    ax.legend(loc="upper left", fontsize=5.5, ncol=2)

    plt.tight_layout()
    path = RESULTS_DIR / "optimize_top20_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_best_equity(best_row: pd.Series, close: pd.Series, is_bull: pd.Series, bh_equity: pd.Series):
    """Equity + Drawdown ของ Best Combination"""
    ema_f = ta.ema(close, int(best_row["ema_fast"]))
    ema_s = ta.ema(close, int(best_row["ema_slow"]))
    pos   = build_positions(close, ema_f, ema_s,
                            int(best_row["rsi_long"]), int(best_row["rsi_short"]), is_bull)
    close_pct   = close.pct_change().fillna(0)
    pos_shifted = pos.shift(1).fillna(0)
    fee         = pos.diff().fillna(0).abs() * FEE_RATE
    net_ret     = pos_shifted * close_pct - fee
    equity      = (1 + net_ret).cumprod() * 100
    bh          = bh_equity * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                    gridspec_kw={"height_ratios": [3, 1]},
                                    facecolor="#0f1117")
    fig.suptitle(
        f"🏆 Best Combo: EMA{int(best_row['ema_fast'])}/{int(best_row['ema_slow'])} | "
        f"RSI Long <{int(best_row['rsi_long'])} | RSI Short >{int(best_row['rsi_short'])} | "
        f"BTC/USDT 1H 6Y",
        color="#e6edf3", fontsize=12
    )

    ax1.plot(equity.index, equity.values, color="#3fb950", linewidth=1.5, label="Best EMA+RSI (Optimized)")
    ax1.plot(bh.index, bh.values, color="white", linewidth=1.2, linestyle="--", alpha=0.5, label="Buy & Hold")
    ax1.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")

    stats = (
        f"Total Return : {best_row['total_return']:+.1f}%\n"
        f"CAGR         : {best_row['cagr']:+.1f}%\n"
        f"Sharpe       : {best_row['sharpe']:.3f}\n"
        f"Sortino      : {best_row['sortino']:.3f}\n"
        f"Max DD       : {best_row['max_dd']:.1f}%\n"
        f"Profit Factor: {best_row['profit_factor']:.3f}\n"
        f"Total Trades : {int(best_row['trades']):,}"
    )
    ax1.text(0.01, 0.97, stats, transform=ax1.transAxes, fontsize=9,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(facecolor="#161b22", edgecolor="#3fb950", alpha=0.9))
    ax1.legend(loc="upper left")
    plt.setp(ax1.get_xticklabels(), visible=False)

    rolling_max = equity.cummax()
    dd = (equity - rolling_max) / rolling_max * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")
    ax2.set_xlabel("")

    plt.tight_layout()
    path = RESULTS_DIR / "optimize_best_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("📥 โหลดข้อมูล")
    print("=" * 65)
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    close = df["close"]
    close_pct = close.pct_change().fillna(0)
    bh_equity = (1 + close_pct).cumprod()

    print("\n🔍 คำนวณ Macro Filter ...")
    is_bull = compute_macro_filter(df)
    print(f"✅ Bull: {is_bull.mean()*100:.1f}% | Bear: {(~is_bull).mean()*100:.1f}%")

    print("\n🔧 Pre-computing RSI(14) ...")
    rsi_series = ta.rsi(close, 14)

    # Build all valid parameter combinations
    all_combos = [
        (ef, es, rl, rs)
        for ef, es, rl, rs in product(EMA_FAST_RANGE, EMA_SLOW_RANGE, RSI_LONG_RANGE, RSI_SHORT_RANGE)
        if ef < es   # EMA Fast ต้องน้อยกว่า EMA Slow เสมอ
    ]
    total = len(all_combos)
    print(f"\n🚀 Grid Search: {total:,} combinations")
    print("=" * 65)

    results = []
    prev_ema_fast, ema_fast_cache = None, None
    prev_ema_slow, ema_slow_cache = None, None

    for idx, (ema_f_val, ema_s_val, rsi_l, rsi_s) in enumerate(all_combos):
        # Cache EMA calculations
        if ema_f_val != prev_ema_fast:
            ema_fast_cache = ta.ema(close, ema_f_val)
            prev_ema_fast = ema_f_val
        if ema_s_val != prev_ema_slow:
            ema_slow_cache = ta.ema(close, ema_s_val)
            prev_ema_slow = ema_s_val

        long_sig  = crossover(ema_fast_cache, ema_slow_cache) & (rsi_series < rsi_l)
        short_sig = crossunder(ema_fast_cache, ema_slow_cache) & (rsi_series > rsi_s) & ~is_bull

        pos = np.zeros(len(close), dtype=np.int8)
        current = 0
        for i in range(len(pos)):
            if long_sig.iloc[i]:
                current = 1
            elif short_sig.iloc[i]:
                current = -1
            pos[i] = current
        pos_series = pd.Series(pos, index=close.index)

        metrics = fast_backtest(close_pct, pos_series)
        results.append({
            "ema_fast": ema_f_val, "ema_slow": ema_s_val,
            "rsi_long": rsi_l, "rsi_short": rsi_s,
            **metrics
        })

        if (idx + 1) % 50 == 0 or (idx + 1) == total:
            best_so_far = max(results, key=lambda x: x["sharpe"])
            print(f"  [{idx+1:>4}/{total}] Best Sharpe so far: {best_so_far['sharpe']:.3f} "
                  f"| EMA{best_so_far['ema_fast']}/{best_so_far['ema_slow']} "
                  f"RSI<{best_so_far['rsi_long']}/>>{best_so_far['rsi_short']} "
                  f"| Return: {best_so_far['total_return']:+.1f}%")

    # ─── Results ───
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_results.index += 1

    print("\n" + "=" * 65)
    print("🏆 TOP 20 Combinations (by Sharpe Ratio)")
    print("=" * 65)
    print(f"{'Rk':<4} {'EMAf':>5} {'EMAs':>5} {'RSI_L':>6} {'RSI_S':>6} "
          f"{'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'PF':>6} {'Trades':>7}")
    print("-" * 70)
    for i, row in df_results.head(20).iterrows():
        print(f"{i:<4} {int(row['ema_fast']):>5} {int(row['ema_slow']):>5} "
              f"{int(row['rsi_long']):>6} {int(row['rsi_short']):>6} "
              f"{row['total_return']:>+9.1f} {row['cagr']:>+7.1f} "
              f"{row['sharpe']:>7.3f} {row['max_dd']:>8.1f} "
              f"{row['profit_factor']:>6.3f} {int(row['trades']):>7,}")

    best = df_results.iloc[0]
    print(f"\n🥇 BEST: EMA{int(best['ema_fast'])}/{int(best['ema_slow'])} | "
          f"RSI Long <{int(best['rsi_long'])} | RSI Short >{int(best['rsi_short'])}")
    print(f"   Return  : {best['total_return']:+.1f}%")
    print(f"   CAGR    : {best['cagr']:+.1f}%")
    print(f"   Sharpe  : {best['sharpe']:.3f}")
    print(f"   Sortino : {best['sortino']:.3f}")
    print(f"   Max DD  : {best['max_dd']:.1f}%")
    print(f"   PF      : {best['profit_factor']:.3f}")
    print(f"   Trades  : {int(best['trades']):,}")
    print(f"\n⭐ Buy & Hold: +{(bh_equity.iloc[-1]-1)*100:.1f}%")

    # Save
    df_results.to_csv(RESULTS_DIR / "optimize_results.csv")
    df_results.head(50).to_csv(RESULTS_DIR / "optimize_top50.csv")
    print(f"\n✅ บันทึกผล: {RESULTS_DIR}/optimize_results.csv")

    # ─── Charts ───
    print("\n📈 Plot กราฟ ...")
    p1 = plot_heatmaps(df_results, best.to_dict())
    p2 = plot_rsi_heatmap(df_results)
    p3 = plot_top20_equity(df_results, close, is_bull, bh_equity)
    p4 = plot_best_equity(best, close, is_bull, bh_equity)
    print(f"✅ EMA Heatmap    : {p1}")
    print(f"✅ RSI Heatmap    : {p2}")
    print(f"✅ Top20 Equity   : {p3}")
    print(f"✅ Best Equity    : {p4}")
    print("\n🎉 Optimization เสร็จแล้ว!")


if __name__ == "__main__":
    main()
