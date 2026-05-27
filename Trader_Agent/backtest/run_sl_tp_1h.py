"""
run_sl_tp_1h.py
Step B — เพิ่ม Stop Loss + Take Profit บน
EMA25/100 + RSI<60/>35 + Macro Filter (1H 6Y)

Grid Search:
  SL: 2%, 3%, 5%, 8%, 10%, 15%, None
  TP: 5%, 10%, 15%, 20%, 30%, 50%, None

Usage:
    python backtest/run_sl_tp_1h.py
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

DATA_PATH   = Path(__file__).parent / "data" / "btc_1H_6y.csv"
RESULTS_DIR = Path(__file__).parent / "results"
FEE_RATE    = 0.001
EMA_FAST, EMA_SLOW, RSI_LONG, RSI_SHORT = 25, 100, 60, 35

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#1a1d2e",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#c9d1d9",
    "ytick.color": "#c9d1d9", "text.color": "#c9d1d9",
    "grid.color": "#30363d", "legend.facecolor": "#161b22",
})

SL_VALUES = [0.02, 0.03, 0.05, 0.08, 0.10, 0.15, None]   # None = ไม่มี SL
TP_VALUES = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, None]   # None = ไม่มี TP

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

def compute_macro(df):
    daily    = df["close"].resample("1D").last().dropna()
    ema200d  = daily.ewm(span=200, adjust=False).mean()
    return df["close"] > ema200d.reindex(df.index, method="ffill")

def build_positions_sltp(close_arr, long_arr, short_arr, sl_pct, tp_pct):
    """Position builder with Stop Loss and Take Profit"""
    n   = len(close_arr)
    pos = np.zeros(n, dtype=np.float32)
    current, entry_price = 0, 0.0

    for i in range(n):
        price = close_arr[i]

        # Check SL/TP for existing position
        if current == 1:   # Long
            if sl_pct is not None and price <= entry_price * (1 - sl_pct):
                current = 0   # SL hit
            elif tp_pct is not None and price >= entry_price * (1 + tp_pct):
                current = 0   # TP hit
        elif current == -1:  # Short
            if sl_pct is not None and price >= entry_price * (1 + sl_pct):
                current = 0   # SL hit
            elif tp_pct is not None and price <= entry_price * (1 - tp_pct):
                current = 0   # TP hit

        # New signal (only when flat)
        if current == 0:
            if long_arr[i]:
                current, entry_price = 1, price
            elif short_arr[i]:
                current, entry_price = -1, price

        pos[i] = current
    return pos

def run_backtest(close_pct, pos_arr, index=None):
    pos = pd.Series(pos_arr, index=index if index is not None else close_pct.index)
    pos_shifted = pos.shift(1).fillna(0)
    fee         = pos.diff().fillna(0).abs() * FEE_RATE
    net_ret     = pos_shifted * close_pct.values - fee.values
    net_ret     = pd.Series(net_ret.values if hasattr(net_ret, 'values') else net_ret, index=pos.index)
    equity      = (1 + net_ret).cumprod()
    years        = len(close_pct) / (365 * 24)
    total_return = (equity.iloc[-1] - 1) * 100
    cagr         = ((equity.iloc[-1]) ** (1 / years) - 1) * 100
    std          = net_ret.std()
    sharpe       = (net_ret.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0
    down         = net_ret[net_ret < 0]
    sortino      = (net_ret.mean() / down.std()) * np.sqrt(365 * 24) if len(down) > 0 and down.std() > 0 else 0
    rolling_max  = equity.cummax()
    max_dd       = ((equity - rolling_max) / rolling_max * 100).min()
    gp = net_ret[net_ret > 0].sum()
    gl = abs(net_ret[net_ret < 0].sum())
    pf           = gp / gl if gl > 0 else np.inf
    trades       = int(pos.diff().fillna(0).abs().gt(0).sum())
    pos_only     = net_ret[pos_shifted != 0]
    win_rate     = len(pos_only[pos_only > 0]) / len(pos_only) * 100 if len(pos_only) > 0 else 0
    return {
        "equity": equity * 100,
        "total_return": round(total_return, 2), "cagr": round(cagr, 2),
        "sharpe": round(sharpe, 4), "sortino": round(sortino, 4),
        "max_dd": round(max_dd, 2), "profit_factor": round(pf, 4),
        "trades": trades, "win_rate": round(win_rate, 1),
    }

def sl_label(v): return f"SL {v*100:.0f}%" if v else "No SL"
def tp_label(v): return f"TP {v*100:.0f}%" if v else "No TP"

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("📥 โหลดข้อมูล 1H 6Y")
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    close      = df["close"]
    close_pct  = close.pct_change().fillna(0)
    close_arr  = close.values.astype(np.float64)
    bh_return  = (1 + close_pct).cumprod().iloc[-1] * 100 - 100

    print("\n🔧 คำนวณ Signals ...")
    is_bull   = compute_macro(df)
    ema_fast  = ta.ema(close, EMA_FAST)
    ema_slow  = ta.ema(close, EMA_SLOW)
    rsi       = ta.rsi(close, 14)
    long_sig  = crossover(ema_fast, ema_slow) & (rsi < RSI_LONG)
    short_sig = crossunder(ema_fast, ema_slow) & (rsi > RSI_SHORT) & ~is_bull
    long_arr  = long_sig.fillna(False).values.astype(bool)
    short_arr = short_sig.fillna(False).values.astype(bool)

    # Baseline (no SL/TP)
    base_pos = build_positions_sltp(close_arr, long_arr, short_arr, None, None)
    base_res = run_backtest(close_pct, base_pos, df.index)
    print(f"✅ Baseline (No SL/TP): Return={base_res['total_return']:+.1f}% Sharpe={base_res['sharpe']:.3f} MaxDD={base_res['max_dd']:.1f}%")

    combos = [(sl, tp) for sl, tp in product(SL_VALUES, TP_VALUES)]
    total  = len(combos)
    print(f"\n🚀 Grid Search: {total} combinations (SL × TP)")
    print("=" * 65)

    results = []
    for idx, (sl, tp) in enumerate(combos):
        pos = build_positions_sltp(close_arr, long_arr, short_arr, sl, tp)
        res = run_backtest(close_pct, pos, df.index)
        results.append({
            "sl": sl, "tp": tp,
            "sl_label": sl_label(sl), "tp_label": tp_label(tp),
            **{k: v for k, v in res.items() if k != "equity"}
        })
        if (idx + 1) % 10 == 0 or (idx + 1) == total:
            best = max(results, key=lambda x: x["sharpe"])
            print(f"  [{idx+1:>3}/{total}] Best Sharpe: {best['sharpe']:.3f} "
                  f"| {sl_label(best['sl'])} / {tp_label(best['tp'])} "
                  f"| Return: {best['total_return']:+.1f}% MaxDD: {best['max_dd']:.1f}%")

    df_res = pd.DataFrame(results).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_res.index += 1

    # ── Summary ──
    print("\n" + "=" * 65)
    print("🏆 TOP 15 Combinations (by Sharpe)")
    print("=" * 65)
    print(f"{'Rk':<4} {'SL':>8} {'TP':>8} {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} "
          f"{'MaxDD%':>8} {'WinR%':>7} {'Trades':>7}")
    print("-" * 65)
    for i, r in df_res.head(15).iterrows():
        print(f"{i:<4} {sl_label(r['sl']):>8} {tp_label(r['tp']):>8} "
              f"{r['total_return']:>+9.1f} {r['cagr']:>+7.1f} {r['sharpe']:>7.3f} "
              f"{r['max_dd']:>8.1f} {r['win_rate']:>6.1f}% {int(r['trades']):>7,}")

    best = df_res.iloc[0]
    print(f"\n🥇 BEST: {sl_label(best['sl'])} / {tp_label(best['tp'])}")
    print(f"   Return : {best['total_return']:+.1f}%  |  Baseline: {base_res['total_return']:+.1f}%")
    print(f"   Sharpe : {best['sharpe']:.3f}      |  Baseline: {base_res['sharpe']:.3f}")
    print(f"   MaxDD  : {best['max_dd']:.1f}%     |  Baseline: {base_res['max_dd']:.1f}%")
    print(f"   Trades : {int(best['trades']):,}         |  Baseline: {base_res['trades']:,}")

    df_res.to_csv(RESULTS_DIR / "sltp_results.csv", index=False)

    # ── Heatmap ──
    print("\n📈 Plot Heatmaps ...")
    for metric, label, fmt in [("sharpe", "Sharpe Ratio", ".2f"),
                                 ("max_dd", "Max Drawdown (%)", ".0f"),
                                 ("total_return", "Total Return (%)", ".0f")]:
        sl_labels_ordered = [sl_label(v) for v in SL_VALUES]
        tp_labels_ordered = [tp_label(v) for v in TP_VALUES]
        pivot = df_res.pivot_table(index="sl_label", columns="tp_label",
                                   values=metric, aggfunc="mean")
        pivot = pivot.reindex(index=sl_labels_ordered, columns=tp_labels_ordered)

        fig, ax = plt.subplots(figsize=(12, 7), facecolor="#0f1117")
        cmap = "RdYlGn" if metric != "max_dd" else "RdYlGn_r"
        sns.heatmap(pivot, ax=ax, cmap=cmap, annot=True, fmt=fmt,
                    linewidths=0.3, linecolor="#0f1117", cbar_kws={"shrink": 0.8})
        ax.set_title(f"SL/TP Heatmap — {label} | EMA{EMA_FAST}/{EMA_SLOW} 1H 6Y",
                     color="#e6edf3", fontsize=11)
        ax.set_xlabel("Take Profit", color="#c9d1d9")
        ax.set_ylabel("Stop Loss", color="#c9d1d9")
        ax.tick_params(colors="#c9d1d9")
        plt.tight_layout()
        path = RESULTS_DIR / f"sltp_heatmap_{metric}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
        plt.close(fig)
        print(f"✅ {path.name}")

    # ── Best Equity ──
    best_sl, best_tp = best["sl"], best["tp"]
    best_pos = build_positions_sltp(close_arr, long_arr, short_arr, best_sl, best_tp)
    best_res = run_backtest(close_pct, best_pos)
    bh_eq    = (1 + close_pct).cumprod() * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                    gridspec_kw={"height_ratios": [3, 1]}, facecolor="#0f1117")
    fig.suptitle(f"Best SL/TP: {sl_label(best_sl)} / {tp_label(best_tp)} | EMA{EMA_FAST}/{EMA_SLOW} 1H 6Y",
                 color="#e6edf3", fontsize=12)
    ax1.plot(best_res["equity"].index, best_res["equity"].values, color="#3fb950", linewidth=1.5,
             label=f"Best ({sl_label(best_sl)}/{tp_label(best_tp)})")
    ax1.plot(pd.Series(base_res["equity"].values, index=df.index), color="#58a6ff", linewidth=1,
             linestyle=":", alpha=0.7, label=f"Baseline (No SL/TP)")
    ax1.plot(bh_eq.index, bh_eq.values, color="white", linewidth=1, linestyle="--", alpha=0.5, label="Buy & Hold")
    ax1.axhline(100, color="#30363d", linewidth=0.8)

    stats = (
        f"{'':=<30}\n"
        f"{'Metric':<16} {'Best':>8}  {'Baseline':>8}\n"
        f"{'':=<30}\n"
        f"{'Return':<16} {best_res['total_return']:>+7.1f}%  {base_res['total_return']:>+7.1f}%\n"
        f"{'CAGR':<16} {best_res['cagr']:>+7.1f}%  {base_res['cagr']:>+7.1f}%\n"
        f"{'Sharpe':<16} {best_res['sharpe']:>8.3f}  {base_res['sharpe']:>8.3f}\n"
        f"{'Sortino':<16} {best_res['sortino']:>8.3f}  {base_res['sortino']:>8.3f}\n"
        f"{'Max DD':<16} {best_res['max_dd']:>+7.1f}%  {base_res['max_dd']:>+7.1f}%\n"
        f"{'Trades':<16} {best_res['trades']:>8,}  {base_res['trades']:>8,}\n"
        f"{'Win Rate':<16} {best_res['win_rate']:>7.1f}%  {base_res['win_rate']:>7.1f}%"
    )
    ax1.text(0.01, 0.97, stats, transform=ax1.transAxes, fontsize=8,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(facecolor="#161b22", edgecolor="#3fb950", alpha=0.9))
    ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")
    ax1.legend(loc="upper left", fontsize=8)
    plt.setp(ax1.get_xticklabels(), visible=False)

    rolling_max = best_res["equity"].cummax()
    dd = (best_res["equity"] - rolling_max) / rolling_max * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")

    plt.tight_layout()
    path = RESULTS_DIR / "sltp_best_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"✅ {path.name}")
    print(f"\n⭐ B&H: +{bh_return:.1f}%")
    print("🎉 SL/TP Optimization เสร็จ!")

if __name__ == "__main__":
    main()
