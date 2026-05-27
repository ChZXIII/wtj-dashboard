"""
run_backtest.py
รัน Backtest 12 Indicators บน BTC/USDT 1H ย้อนหลัง 6 ปี
Long + Short mode — ผลลัพธ์เป็น % Return

Usage:
    python backtest/run_backtest.py
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
import seaborn as sns
from fetch_data import main as fetch_data
from strategies import STRATEGIES

# ─── Settings ───────────────────────────────────────────────────────────────
FEE_RATE       = 0.001   # 0.1% per trade (Binance Taker)
RESULTS_DIR    = Path(__file__).parent / "results"
CHARTS_DIR     = RESULTS_DIR / "charts"
DATA_PATH      = Path(__file__).parent / "data" / "btc_1h.csv"

sns.set_theme(style="darkgrid", palette="muted")
plt.rcParams.update({
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#1a1d2e",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#c9d1d9",
    "ytick.color":      "#c9d1d9",
    "text.color":       "#c9d1d9",
    "grid.color":       "#30363d",
    "grid.linewidth":   0.5,
})

# ─── Backtest Engine ─────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, positions: pd.Series, fee_rate: float = FEE_RATE) -> dict:
    """
    Vectorized backtest engine
    positions: +1 (Long), -1 (Short), 0 (Flat)
    ผลลัพธ์ทั้งหมดเป็น % ของ Portfolio เริ่มต้น = 100%
    """
    close = df["close"]

    # % return ของแต่ละแท่ง
    pct_returns = close.pct_change().fillna(0)

    # Position shifted 1 แท่ง (ซื้อที่ Open ของแท่งถัดไปจริงๆ)
    pos_shifted = positions.shift(1).fillna(0)

    # Raw strategy returns
    strategy_returns = pos_shifted * pct_returns

    # คำนวณ Trade Fees
    pos_change = positions.diff().fillna(0).abs()
    # แต่ละครั้งที่เปลี่ยน position หักค่า fee
    fee_returns = pos_change * fee_rate

    # Net returns
    net_returns = strategy_returns - fee_returns

    # Equity curve (เริ่มที่ 100%)
    equity = (1 + net_returns).cumprod() * 100

    # Buy & Hold สำหรับเปรียบเทียบ
    bh_equity = (1 + pct_returns).cumprod() * 100

    # ─── Metrics ───
    total_return = equity.iloc[-1] - 100

    # Annual return
    years = len(df) / (365 * 24)
    cagr = ((equity.iloc[-1] / 100) ** (1 / years) - 1) * 100

    # Sharpe Ratio (annualized, risk-free = 0)
    sharpe = 0.0
    if net_returns.std() != 0:
        sharpe = (net_returns.mean() / net_returns.std()) * np.sqrt(365 * 24)

    # Max Drawdown
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()

    # Trade statistics
    trades = _count_trades(positions, close, net_returns, pos_shifted, fee_rate)

    # Sortino Ratio
    downside = net_returns[net_returns < 0]
    sortino = 0.0
    if len(downside) > 0 and downside.std() != 0:
        sortino = (net_returns.mean() / downside.std()) * np.sqrt(365 * 24)

    # Profit Factor
    gross_profit = net_returns[net_returns > 0].sum()
    gross_loss   = abs(net_returns[net_returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.inf

    return {
        "equity"       : equity,
        "bh_equity"    : bh_equity,
        "drawdown"     : drawdown,
        "net_returns"  : net_returns,
        "total_return" : round(total_return, 2),
        "cagr"         : round(cagr, 2),
        "sharpe"       : round(sharpe, 3),
        "sortino"      : round(sortino, 3),
        "max_dd"       : round(max_dd, 2),
        "profit_factor": round(profit_factor, 3),
        **trades,
    }


def _count_trades(positions, close, net_returns, pos_shifted, fee_rate):
    """นับสถิติ Trade"""
    # หา trade boundaries
    pos_change = positions.diff().fillna(0)
    trade_opens  = pos_change[pos_change != 0].index
    total_trades = len(trade_opens)

    if total_trades == 0:
        return {
            "total_trades": 0, "win_rate": 0,
            "avg_trade_pct": 0, "avg_duration_hrs": 0,
        }

    # คำนวณผลแต่ละ Trade
    trade_results = []
    trade_durations = []

    prev_idx = None
    prev_pos = 0
    for i, idx in enumerate(positions.index):
        cur_pos = positions.loc[idx]
        if prev_pos != cur_pos:
            if prev_pos != 0 and prev_idx is not None:
                # Trade จบ
                segment = net_returns.loc[prev_idx:idx]
                trade_ret = (1 + segment).prod() - 1
                trade_results.append(trade_ret * 100)
                duration = len(segment)
                trade_durations.append(duration)
            prev_idx = idx
            prev_pos = cur_pos

    if not trade_results:
        return {
            "total_trades": total_trades, "win_rate": 0,
            "avg_trade_pct": 0, "avg_duration_hrs": 0,
        }

    wins = [t for t in trade_results if t > 0]
    win_rate = len(wins) / len(trade_results) * 100
    avg_trade = np.mean(trade_results)
    avg_dur   = np.mean(trade_durations) if trade_durations else 0

    return {
        "total_trades"    : total_trades,
        "win_rate"        : round(win_rate, 1),
        "avg_trade_pct"   : round(avg_trade, 3),
        "avg_duration_hrs": round(avg_dur, 1),
    }


# ─── Plotting ────────────────────────────────────────────────────────────────

def plot_individual(name: str, result: dict, df: pd.DataFrame):
    """Plot Equity Curve + Drawdown สำหรับแต่ละ Strategy"""
    fig = plt.figure(figsize=(16, 9), facecolor="#0f1117")
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    equity = result["equity"]
    bh     = result["bh_equity"]
    dd     = result["drawdown"]

    ax1.plot(equity.index, equity.values,  color="#58a6ff", linewidth=1.2, label=name)
    ax1.plot(bh.index,     bh.values,      color="#8b949e", linewidth=0.8, linestyle="--", alpha=0.7, label="Buy & Hold")
    ax1.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")
    ax1.legend(loc="upper left", facecolor="#1a1d2e", edgecolor="#30363d")

    # Stats box
    stats_text = (
        f"Total Return : {result['total_return']:+.1f}%\n"
        f"CAGR         : {result['cagr']:+.1f}%\n"
        f"Sharpe       : {result['sharpe']:.2f}\n"
        f"Sortino      : {result['sortino']:.2f}\n"
        f"Max DD       : {result['max_dd']:.1f}%\n"
        f"Win Rate     : {result['win_rate']:.1f}%\n"
        f"Profit Factor: {result['profit_factor']:.2f}\n"
        f"Total Trades : {result['total_trades']:,}"
    )
    ax1.text(0.01, 0.97, stats_text, transform=ax1.transAxes,
             fontsize=8, verticalalignment="top", fontfamily="monospace",
             bbox=dict(facecolor="#161b22", edgecolor="#30363d", alpha=0.9))

    ax1.set_title(f"📊 {name} | BTC/USDT 1H | Long + Short", color="#e6edf3", fontsize=13, pad=10)

    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")
    ax2.set_xlabel("")

    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.tight_layout()

    safe_name = name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
    path = CHARTS_DIR / f"{safe_name}.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_summary(results_df: pd.DataFrame):
    """Summary chart — Ranking ทุก Strategy"""
    fig, axes = plt.subplots(2, 3, figsize=(20, 11), facecolor="#0f1117")
    fig.suptitle("📊 BTC/USDT 1H — Indicator Backtest Summary (6Y, Long+Short)",
                 color="#e6edf3", fontsize=15, y=0.98)

    metrics = [
        ("total_return",  "Total Return (%)",   "#58a6ff"),
        ("cagr",          "CAGR (%)",            "#3fb950"),
        ("sharpe",        "Sharpe Ratio",        "#d2a8ff"),
        ("max_dd",        "Max Drawdown (%)",    "#f85149"),
        ("win_rate",      "Win Rate (%)",        "#ffa657"),
        ("profit_factor", "Profit Factor",       "#79c0ff"),
    ]

    for ax, (col, label, color) in zip(axes.flat, metrics):
        df_sorted = results_df.sort_values(col, ascending=(col == "max_dd"))
        bars = ax.barh(df_sorted["strategy"], df_sorted[col], color=color, alpha=0.85)
        ax.set_title(label, color="#e6edf3", fontsize=10)
        ax.set_xlabel(label, color="#8b949e", fontsize=8)
        ax.tick_params(colors="#c9d1d9", labelsize=7)
        # value labels
        for bar, val in zip(bars, df_sorted[col]):
            ax.text(val + (ax.get_xlim()[1] * 0.01), bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", color="#e6edf3", fontsize=7)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = RESULTS_DIR / "summary_chart.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_equity_all(all_results: dict):
    """Plot Equity Curve ทุก Strategy ในกราฟเดียว"""
    fig, ax = plt.subplots(figsize=(18, 9), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")

    colors = plt.cm.tab20(np.linspace(0, 1, len(all_results)))
    bh_plotted = False
    for (name, result), color in zip(all_results.items(), colors):
        eq = result["equity"]
        ax.plot(eq.index, eq.values, linewidth=1.0, label=name, color=color, alpha=0.85)
        if not bh_plotted:
            ax.plot(result["bh_equity"].index, result["bh_equity"].values,
                    color="white", linewidth=1.5, linestyle="--", alpha=0.5, label="Buy & Hold")
            bh_plotted = True

    ax.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax.set_ylabel("Portfolio Value (%) — Start = 100%", color="#c9d1d9")
    ax.set_title("📊 All Strategies — Equity Curves | BTC/USDT 1H | 6 Years", color="#e6edf3", fontsize=13)
    ax.legend(loc="upper left", facecolor="#1a1d2e", edgecolor="#30363d", fontsize=7, ncol=2)

    plt.tight_layout()
    path = RESULTS_DIR / "equity_all.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. โหลดข้อมูล
    print("=" * 60)
    print("📥 โหลดข้อมูล BTC/USDT 1H")
    print("=" * 60)
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        print(f"✅ โหลดข้อมูล cache: {len(df):,} candles ({df.index[0].date()} – {df.index[-1].date()})")
    else:
        df = fetch_data()

    # Validate
    assert len(df) > 10000, "ข้อมูลน้อยเกินไป!"
    print(f"✅ Data OK — {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    # 2. รัน Backtest ทุก Strategy
    print("\n" + "=" * 60)
    print("🚀 เริ่ม Backtest 12 Indicators")
    print("=" * 60)

    all_results = {}
    summary_rows = []

    for name, func in STRATEGIES.items():
        print(f"\n▶ {name} ...", end=" ", flush=True)
        try:
            positions = func(df)
            result    = run_backtest(df, positions)
            all_results[name] = result

            row = {
                "strategy"        : name,
                "total_return"    : result["total_return"],
                "cagr"            : result["cagr"],
                "sharpe"          : result["sharpe"],
                "sortino"         : result["sortino"],
                "max_dd"          : result["max_dd"],
                "win_rate"        : result["win_rate"],
                "profit_factor"   : result["profit_factor"],
                "total_trades"    : result["total_trades"],
                "avg_trade_pct"   : result["avg_trade_pct"],
                "avg_duration_hrs": result["avg_duration_hrs"],
            }
            summary_rows.append(row)

            print(f"✅ Return: {result['total_return']:+.1f}% | Sharpe: {result['sharpe']:.2f} | MaxDD: {result['max_dd']:.1f}%")

            # Plot individual
            plot_individual(name, result, df)

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback; traceback.print_exc()

    # 3. Summary Table
    print("\n" + "=" * 60)
    print("📊 สรุปผล — Ranking by Sharpe Ratio")
    print("=" * 60)

    summary_df = pd.DataFrame(summary_rows)

    # Buy & Hold benchmark
    bh_return = float(all_results[list(all_results.keys())[0]]["bh_equity"].iloc[-1] - 100)
    bh_row = {
        "strategy": "★ Buy & Hold (Benchmark)",
        "total_return": round(bh_return, 2),
        "cagr": round(((bh_return / 100 + 1) ** (1 / (len(df) / (365 * 24))) - 1) * 100, 2),
        "sharpe": "—", "sortino": "—", "max_dd": "—",
        "win_rate": "—", "profit_factor": "—",
        "total_trades": "—", "avg_trade_pct": "—", "avg_duration_hrs": "—",
    }

    summary_df = summary_df.sort_values("sharpe", ascending=False).reset_index(drop=True)
    summary_df.index += 1

    # Print table
    print(f"\n{'Rank':<5} {'Strategy':<22} {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'WinRate':>8} {'PF':>6} {'Trades':>7}")
    print("-" * 85)
    for idx, row in summary_df.iterrows():
        print(f"{idx:<5} {row['strategy']:<22} {row['total_return']:>+9.1f} {row['cagr']:>+7.1f} "
              f"{row['sharpe']:>7.2f} {row['max_dd']:>8.1f} {row['win_rate']:>7.1f}% {row['profit_factor']:>6.2f} {int(row['total_trades']):>7,}")
    print("-" * 85)
    print(f"{'BH':^5} {'★ Buy & Hold':^22} {bh_return:>+9.1f}%  (Benchmark)")

    # Save CSV
    csv_path = RESULTS_DIR / "summary.csv"
    summary_df.to_csv(csv_path)
    print(f"\n✅ บันทึก CSV: {csv_path}")

    # 4. Plots
    print("\n📈 กำลัง Plot กราฟ ...")
    p1 = plot_summary(summary_df)
    p2 = plot_equity_all(all_results)
    print(f"✅ Summary chart : {p1}")
    print(f"✅ Equity all    : {p2}")
    print(f"✅ Individual    : {CHARTS_DIR}/")

    # 5. Winner
    winner = summary_df.iloc[0]
    print("\n" + "=" * 60)
    print(f"🏆 WINNER (Sharpe): {winner['strategy']}")
    print(f"   Total Return : {winner['total_return']:+.1f}%")
    print(f"   CAGR         : {winner['cagr']:+.1f}%")
    print(f"   Sharpe Ratio : {winner['sharpe']:.3f}")
    print(f"   Max Drawdown : {winner['max_dd']:.1f}%")
    print(f"   Win Rate     : {winner['win_rate']:.1f}%")
    print(f"   Profit Factor: {winner['profit_factor']:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
