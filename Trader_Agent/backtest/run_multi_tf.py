"""
run_multi_tf.py
Backtest EMA25/100 + RSI<60/>35 + Macro Filter
บน Multiple Timeframes:
  - 15m : ย้อนหลัง 3 ปี และ 6 ปี
  - 30m : ย้อนหลัง 6 ปี
  - 1H  : ย้อนหลัง 6 ปี  (baseline จากก่อนหน้า)
  - 1D  : ย้อนหลังสูงสุดที่มี (~8.5 ปี)

Usage:
    python backtest/run_multi_tf.py
"""

import warnings
warnings.filterwarnings("ignore")

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import ccxt
import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime, timezone

DATA_DIR    = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
FEE_RATE    = 0.001

# Best Optimized Parameters
EMA_FAST    = 25
EMA_SLOW    = 100
RSI_LONG    = 60
RSI_SHORT   = 35

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

TIMEFRAME_CONFIGS = [
    # (label, ccxt_tf, years_back, macro_resample, macro_ema_span)
    ("15m_3y",  "15m",  3,  "1D",  200),
    ("15m_6y",  "15m",  6,  "1D",  200),
    ("30m_6y",  "30m",  6,  "1D",  200),
    ("1H_6y",   "1h",   6,  "1D",  200),   # Baseline
    ("1D_max",  "1d",  10,  "1W",  200),   # 10ปี หรือมากสุดที่มี
]

# ─── Data Fetching ────────────────────────────────────────────────────────────

def fetch_ohlcv(symbol: str, timeframe: str, years: int, label: str) -> pd.DataFrame:
    cache_path = DATA_DIR / f"btc_{label}.csv"
    exchange   = ccxt.binance({"enableRateLimit": True})

    if cache_path.exists():
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        print(f"  ✅ Cache hit: {label} — {len(df):,} candles ({df.index[0].date()} → {df.index[-1].date()})")
        return df

    since_ts = int(datetime.now(timezone.utc).timestamp() * 1000) - years * 365 * 24 * 3600 * 1000
    all_ohlcv, current_since, batch = [], since_ts, 0

    print(f"  ⏳ ดึง {symbol} {timeframe} ย้อนหลัง {years}ปี ...", end="", flush=True)
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        batch += 1
        if batch % 20 == 0:
            print(f" {len(all_ohlcv):,}", end="", flush=True)
        if len(ohlcv) < 1000:
            break
        current_since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.to_csv(cache_path)
    print(f" ✅ {len(df):,} candles ({df.index[0].date()} → {df.index[-1].date()})")
    return df


# ─── Strategy ────────────────────────────────────────────────────────────────

def crossover(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))

def crossunder(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def compute_macro_filter(df: pd.DataFrame, resample_rule: str, ema_span: int) -> pd.Series:
    """EMA macro filter — resample แล้ว reindex กลับ"""
    daily    = df["close"].resample(resample_rule).last().dropna()
    ema_macro = daily.ewm(span=ema_span, adjust=False).mean()
    ema_1tf  = ema_macro.reindex(df.index, method="ffill")
    return df["close"] > ema_1tf   # True = Bull


def build_positions(df: pd.DataFrame, is_bull: pd.Series) -> pd.Series:
    close    = df["close"]
    ema_fast = ta.ema(close, EMA_FAST)
    ema_slow = ta.ema(close, EMA_SLOW)
    rsi      = ta.rsi(close, 14)

    long_sig  = crossover(ema_fast, ema_slow) & (rsi < RSI_LONG)
    short_sig = crossunder(ema_fast, ema_slow) & (rsi > RSI_SHORT) & ~is_bull

    pos = np.zeros(len(close), dtype=np.int8)
    current = 0
    for i in range(len(pos)):
        if long_sig.iloc[i]:
            current = 1
        elif short_sig.iloc[i]:
            current = -1
        pos[i] = current
    return pd.Series(pos, index=close.index)


def run_backtest(df: pd.DataFrame, positions: pd.Series) -> dict:
    close_pct   = df["close"].pct_change().fillna(0)
    pos_shifted = positions.shift(1).fillna(0)
    fee         = positions.diff().fillna(0).abs() * FEE_RATE
    net_ret     = pos_shifted * close_pct - fee
    equity      = (1 + net_ret).cumprod() * 100
    bh_equity   = (1 + close_pct).cumprod() * 100

    years        = len(df) / _candles_per_year(df)
    total_return = equity.iloc[-1] - 100
    cagr         = ((equity.iloc[-1] / 100) ** (1 / years) - 1) * 100
    std          = net_ret.std()
    sharpe       = (net_ret.mean() / std) * np.sqrt(_candles_per_year(df)) if std > 0 else 0
    down         = net_ret[net_ret < 0]
    sortino      = (net_ret.mean() / down.std()) * np.sqrt(_candles_per_year(df)) if len(down) > 0 and down.std() > 0 else 0
    rolling_max  = equity.cummax()
    max_dd       = ((equity - rolling_max) / rolling_max * 100).min()
    gp = net_ret[net_ret > 0].sum()
    gl = abs(net_ret[net_ret < 0].sum())
    pf = round(gp / gl, 3) if gl > 0 else np.inf
    trades       = int(positions.diff().fillna(0).abs().gt(0).sum())
    bh_total     = bh_equity.iloc[-1] - 100

    # Win rate
    pos_only = net_ret[pos_shifted != 0]
    wins     = pos_only[pos_only > 0]
    win_rate = len(wins) / len(pos_only) * 100 if len(pos_only) > 0 else 0

    return {
        "equity":        equity,
        "bh_equity":     bh_equity,
        "total_return":  round(total_return, 1),
        "bh_return":     round(bh_total, 1),
        "cagr":          round(cagr, 1),
        "sharpe":        round(sharpe, 3),
        "sortino":       round(sortino, 3),
        "max_dd":        round(max_dd, 1),
        "profit_factor": pf,
        "trades":        trades,
        "win_rate":      round(win_rate, 1),
        "years":         round(years, 1),
    }


def _candles_per_year(df: pd.DataFrame) -> float:
    """Estimate candles per year จาก median gap"""
    gaps  = df.index.to_series().diff().dropna()
    med_s = gaps.median().total_seconds()
    return 365 * 24 * 3600 / med_s


# ─── Plotting ─────────────────────────────────────────────────────────────────

TF_COLORS = {
    "15m_3y": "#ffa657",
    "15m_6y": "#ff7b72",
    "30m_6y": "#d2a8ff",
    "1H_6y":  "#3fb950",
    "1D_max": "#58a6ff",
}

TF_DISPLAY = {
    "15m_3y": "15m (3Y)",
    "15m_6y": "15m (6Y)",
    "30m_6y": "30m (6Y)",
    "1H_6y":  "1H  (6Y) ★",
    "1D_max": "1D  (Max)",
}


def plot_equity_all(all_results: dict):
    fig, axes = plt.subplots(2, 3, figsize=(22, 12), facecolor="#0f1117")
    fig.suptitle(
        f"📊 EMA{EMA_FAST}/{EMA_SLOW} + RSI<{RSI_LONG}/>{RSI_SHORT} + Macro Filter — Multi-Timeframe",
        color="#e6edf3", fontsize=13, y=0.99
    )

    axes_flat = axes.flat
    for (label, res), ax in zip(all_results.items(), axes_flat):
        ax.set_facecolor("#0f1117")
        color = TF_COLORS.get(label, "#58a6ff")
        eq    = res["equity"]
        bh    = res["bh_equity"]

        ax.plot(eq.index, eq.values,  color=color, linewidth=1.2, label=f"Strategy")
        ax.plot(bh.index, bh.values, color="white", linewidth=0.9, linestyle="--", alpha=0.5, label="Buy & Hold")
        ax.axhline(100, color="#30363d", linewidth=0.7, linestyle=":")

        stats = (
            f"Return  : {res['total_return']:+.0f}%\n"
            f"B&H     : {res['bh_return']:+.0f}%\n"
            f"CAGR    : {res['cagr']:+.0f}%/yr\n"
            f"Sharpe  : {res['sharpe']:.2f}\n"
            f"MaxDD   : {res['max_dd']:.0f}%\n"
            f"Trades  : {res['trades']:,}\n"
            f"Win Rate: {res['win_rate']:.0f}%"
        )
        ax.text(0.01, 0.97, stats, transform=ax.transAxes, fontsize=8,
                verticalalignment="top", fontfamily="monospace",
                bbox=dict(facecolor="#161b22", edgecolor=color, alpha=0.9))

        ax.set_title(f"{TF_DISPLAY[label]}", color="#e6edf3", fontsize=10)
        ax.set_ylabel("Portfolio Value (%)", color="#c9d1d9")
        ax.legend(loc="upper left", fontsize=7)

    # Hide unused subplot
    for ax in list(axes_flat)[len(all_results):]:
        ax.set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = RESULTS_DIR / "multi_tf_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_comparison_bar(summary_df: pd.DataFrame):
    metrics = [
        ("total_return",  "Total Return (%)",   True),
        ("cagr",          "CAGR (%/year)",       True),
        ("sharpe",        "Sharpe Ratio",        True),
        ("max_dd",        "Max Drawdown (%)",    False),
        ("trades",        "Total Trades",        False),
        ("win_rate",      "Win Rate (%)",        True),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(22, 10), facecolor="#0f1117")
    fig.suptitle("📊 Multi-Timeframe Comparison — Strategy vs Buy & Hold",
                 color="#e6edf3", fontsize=13, y=0.99)

    labels = summary_df["label"].tolist()
    colors = [TF_COLORS.get(l, "#58a6ff") for l in labels]
    x = np.arange(len(labels))

    for ax, (col, title, higher_better) in zip(axes.flat, metrics):
        vals = summary_df[col].values.astype(float)
        bars = ax.bar(x, vals, color=colors, alpha=0.85, width=0.6)

        # BH reference line สำหรับ return/cagr
        if col == "total_return":
            for i, (bar, bh_val) in enumerate(zip(bars, summary_df["bh_return"])):
                ax.plot([bar.get_x(), bar.get_x() + bar.get_width()],
                        [bh_val, bh_val], color="white", linewidth=2, alpha=0.7)

        ax.set_title(title, color="#e6edf3", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels([TF_DISPLAY[l] for l in labels], fontsize=7.5, color="#c9d1d9")
        ax.tick_params(colors="#c9d1d9")
        ax.axhline(0, color="#30363d", linewidth=0.8)

        for bar, val in zip(bars, vals):
            ypos = val + abs(ax.get_ylim()[1]) * 0.01 if val >= 0 else val - abs(ax.get_ylim()[1]) * 0.03
            ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                    f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color="#e6edf3")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = RESULTS_DIR / "multi_tf_comparison.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_all_on_one(all_results: dict):
    """Equity ทุก TF ในกราฟเดียว — normalize ให้เริ่มที่ 100%"""
    fig, ax = plt.subplots(figsize=(20, 9), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")

    for label, res in all_results.items():
        color = TF_COLORS.get(label, "#58a6ff")
        eq    = res["equity"]
        ax.plot(eq.index, eq.values, color=color, linewidth=1.2,
                label=f"{TF_DISPLAY[label]} — {res['total_return']:+.0f}% | Sh:{res['sharpe']:.2f}",
                alpha=0.85)

    ax.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax.set_ylabel("Portfolio Value (%) — Start = 100%", color="#c9d1d9")
    ax.set_title(
        f"📊 All Timeframes — EMA{EMA_FAST}/{EMA_SLOW} + RSI<{RSI_LONG}/>{RSI_SHORT} + Macro Filter",
        color="#e6edf3", fontsize=12
    )
    ax.legend(loc="upper left", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("Portfolio Value (%) — Log Scale", color="#c9d1d9")

    plt.tight_layout()
    path = RESULTS_DIR / "multi_tf_all_on_one.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(f"🚀 Multi-Timeframe Backtest")
    print(f"   Strategy: EMA{EMA_FAST}/{EMA_SLOW} + RSI<{RSI_LONG}/>{RSI_SHORT} + Macro Filter")
    print("=" * 65)

    # ── 1. Fetch all data ──
    print("\n📥 ดึงข้อมูลทุก Timeframe ...")
    dfs = {}
    for label, tf, years, macro_rs, macro_span in TIMEFRAME_CONFIGS:
        dfs[label] = (fetch_ohlcv("BTC/USDT", tf, years, label), macro_rs, macro_span)

    # ── 2. Backtest ──
    print("\n" + "=" * 65)
    print("⚙️  Backtest ...")
    print("=" * 65)

    all_results = {}
    summary_rows = []

    for label, (df, macro_rs, macro_span) in dfs.items():
        print(f"\n▶ {label:<12} | {len(df):>7,} candles | {df.index[0].date()} → {df.index[-1].date()}")

        is_bull  = compute_macro_filter(df, macro_rs, macro_span)
        bull_pct = is_bull.mean() * 100
        print(f"   Macro Filter: Bull {bull_pct:.1f}% | Bear {100-bull_pct:.1f}%")

        positions = build_positions(df, is_bull)
        result    = run_backtest(df, positions)
        all_results[label] = result

        print(f"   Return: {result['total_return']:+.1f}% | B&H: {result['bh_return']:+.1f}% | "
              f"Sharpe: {result['sharpe']:.3f} | MaxDD: {result['max_dd']:.1f}% | "
              f"Trades: {result['trades']:,} | Years: {result['years']:.1f}")

        summary_rows.append({
            "label":        label,
            "timeframe":    label.split("_")[0],
            "period":       f"{result['years']:.1f}Y",
            "candles":      len(df),
            "total_return": result["total_return"],
            "bh_return":    result["bh_return"],
            "cagr":         result["cagr"],
            "sharpe":       result["sharpe"],
            "sortino":      result["sortino"],
            "max_dd":       result["max_dd"],
            "profit_factor":result["profit_factor"],
            "trades":       result["trades"],
            "win_rate":     result["win_rate"],
        })

    # ── 3. Summary Table ──
    print("\n" + "=" * 65)
    print("📊 SUMMARY TABLE")
    print("=" * 65)
    print(f"{'Label':<12} {'Period':>7} {'Return%':>9} {'B&H%':>7} {'CAGR%':>7} "
          f"{'Sharpe':>7} {'MaxDD%':>8} {'WinR%':>7} {'Trades':>7}")
    print("-" * 75)
    for r in summary_rows:
        print(f"{r['label']:<12} {r['period']:>7} {r['total_return']:>+9.1f} {r['bh_return']:>+7.1f} "
              f"{r['cagr']:>+7.1f} {r['sharpe']:>7.3f} {r['max_dd']:>8.1f} "
              f"{r['win_rate']:>6.1f}% {r['trades']:>7,}")

    # Best by Sharpe
    best = max(summary_rows, key=lambda x: x["sharpe"])
    print(f"\n🏆 Best Timeframe (Sharpe): {best['label']} — Sharpe {best['sharpe']:.3f} | Return {best['total_return']:+.1f}%")

    # Save CSV
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(RESULTS_DIR / "multi_tf_summary.csv", index=False)

    # ── 4. Charts ──
    print("\n📈 Plot กราฟ ...")
    p1 = plot_equity_all(all_results)
    p2 = plot_comparison_bar(df_summary)
    p3 = plot_all_on_one(all_results)
    print(f"✅ Individual equity  : {p1}")
    print(f"✅ Bar comparison     : {p2}")
    print(f"✅ All-on-one (log)   : {p3}")
    print("\n🎉 Multi-TF Backtest เสร็จ!")


if __name__ == "__main__":
    main()
