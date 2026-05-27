"""
run_leverage_test.py
Leverage + Position Sizing Simulator
บน EMA25/100 + RSI<60/>35 + Macro Filter (1H 6Y)

Grid Search:
  Leverage       : 1x, 2x, 3x, 5x, 10x
  Margin per trade: 10%, 20%, 30%, 50%, 100% ของพอร์ต ณ ขณะนั้น

Simulation:
  - ใช้ OHLC จริงในการตรวจ Liquidation ทุก Candle
  - หัก Funding Rate 0.01% ทุก 8 ชั่วโมง (ตอนมี Open Position)
  - หัก Fee 0.04% ตาม Binance Futures Taker (สูงกว่า Spot)
  - Liquidation เมื่อราคาขยับสวนทาง 1/Leverage × 90%

Usage:
    python backtest/run_leverage_test.py
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
FEE_RATE    = 0.0004      # Futures Taker 0.04%
FUNDING_RATE = 0.0001     # 0.01% ทุก 8 ชั่วโมง (Binance default)
FUNDING_EVERY = 8         # ทุก 8 candles (1H TF)
MAINT_MARGIN  = 0.004     # Maintenance Margin 0.4% (Binance BTC)

EMA_FAST, EMA_SLOW, RSI_LONG, RSI_SHORT = 25, 100, 60, 35

LEVERAGE_RANGE  = [1, 2, 3, 5, 10]
MARGIN_RANGE    = [0.10, 0.20, 0.30, 0.50, 1.00]  # สัดส่วน Margin ต่อ Trade

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#1a1d2e",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#c9d1d9",
    "ytick.color": "#c9d1d9", "text.color": "#c9d1d9",
    "grid.color": "#30363d", "legend.facecolor": "#161b22",
})

# ─── Signal Preparation ──────────────────────────────────────────────────────

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

def compute_macro(df):
    daily   = df["close"].resample("1D").last().dropna()
    ema200d = daily.ewm(span=200, adjust=False).mean()
    return df["close"] > ema200d.reindex(df.index, method="ffill")

def get_base_signals(df):
    close     = df["close"]
    is_bull   = compute_macro(df)
    ema_fast  = ta.ema(close, EMA_FAST)
    ema_slow  = ta.ema(close, EMA_SLOW)
    rsi       = ta.rsi(close, 14)
    long_sig  = crossover(ema_fast, ema_slow) & (rsi < RSI_LONG)
    short_sig = crossunder(ema_fast, ema_slow) & (rsi > RSI_SHORT) & ~is_bull
    return long_sig.fillna(False), short_sig.fillna(False)

def build_raw_positions(long_sig, short_sig):
    """สร้าง position array แบบ 1H baseline ไม่มี SL/TP"""
    pos = np.zeros(len(long_sig), dtype=np.int8)
    cur = 0
    ls  = long_sig.values.astype(bool)
    ss  = short_sig.values.astype(bool)
    for i in range(len(pos)):
        if ls[i]:   cur = 1
        elif ss[i]: cur = -1
        pos[i] = cur
    return pos

# ─── Leverage Backtest Engine ─────────────────────────────────────────────────

def simulate_leverage(df, positions, leverage, margin_pct, fee_rate=FEE_RATE):
    """
    Simulate Leveraged Futures บน 1H OHLC
    
    Parameters
    ----------
    df          : DataFrame ที่มี open, high, low, close
    positions   : numpy array of int8 (+1=Long, -1=Short, 0=Flat)
    leverage    : 1, 2, 3, 5, 10 ...
    margin_pct  : สัดส่วน Margin ต่อ Trade เช่น 0.2 = ใช้ 20% ของพอร์ต
    
    Returns
    -------
    dict ของ metrics + equity curve
    """
    close_arr  = df["close"].values.astype(np.float64)
    high_arr   = df["high"].values.astype(np.float64)
    low_arr    = df["low"].values.astype(np.float64)
    n          = len(close_arr)

    # Liquidation threshold: ราคาขยับสวนทาง กี่ % จาก entry
    liq_pct    = (1 / leverage) * (1 - MAINT_MARGIN)  # เผื่อ Maintenance Margin

    equity     = np.zeros(n, dtype=np.float64)
    portfolio  = 100.0   # เริ่มที่ 100%
    num_liq    = 0
    entry_price = 0.0
    cur_pos     = 0

    for i in range(n):
        sig = positions[i]

        # ── ถ้ามี Open Position ──
        if cur_pos != 0:
            price_now = close_arr[i]

            # ตรวจ Liquidation ก่อนเลย (ใช้ High/Low ของแท่งนี้)
            if cur_pos == 1:   # Long
                liq_price = entry_price * (1 - liq_pct)
                hit_liq   = low_arr[i] <= liq_price
            else:              # Short
                liq_price = entry_price * (1 + liq_pct)
                hit_liq   = high_arr[i] >= liq_price

            if hit_liq:
                # โดน Liquidate → เสีย Margin ทั้งหมด
                margin_lost = portfolio * margin_pct
                portfolio  -= margin_lost
                num_liq    += 1
                cur_pos     = 0
                entry_price = 0.0
            else:
                # คำนวณ Return ของ Candle นี้
                pct_chg = (price_now - close_arr[i-1]) / close_arr[i-1] if i > 0 else 0
                notional = portfolio * margin_pct * leverage
                pnl      = notional * pct_chg * cur_pos
                portfolio += pnl

                # Funding Rate ทุก 8 candles
                if i % FUNDING_EVERY == 0:
                    funding  = notional * FUNDING_RATE
                    portfolio -= funding

                # ตรวจว่ามี Signal เปลี่ยน Position หรือไม่
                if sig != cur_pos:
                    if sig == 0 or sig != cur_pos:
                        # Close current + Fee
                        close_fee  = notional * fee_rate
                        portfolio -= close_fee

                        if sig != 0:
                            # Open new + Fee
                            new_notional = portfolio * margin_pct * leverage
                            open_fee     = new_notional * fee_rate
                            portfolio   -= open_fee
                            entry_price  = price_now
                            cur_pos      = sig
                        else:
                            cur_pos     = 0
                            entry_price = 0.0

        else:
            # ── ไม่มี Open Position ──
            if sig != 0:
                # Open Position
                new_notional = portfolio * margin_pct * leverage
                open_fee     = new_notional * fee_rate
                portfolio   -= open_fee
                entry_price  = close_arr[i]
                cur_pos      = sig

        equity[i] = max(portfolio, 0)

    equity_s     = pd.Series(equity, index=df.index)
    total_return = equity_s.iloc[-1] - 100
    years        = n / (365 * 24)
    cagr         = ((equity_s.iloc[-1] / 100) ** (1 / years) - 1) * 100 if equity_s.iloc[-1] > 0 else -100
    pct_ret      = equity_s.pct_change().fillna(0)
    std          = pct_ret.std()
    sharpe       = (pct_ret.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0
    down         = pct_ret[pct_ret < 0]
    sortino      = (pct_ret.mean() / down.std()) * np.sqrt(365 * 24) if len(down) > 0 and down.std() > 0 else 0
    rolling_max  = equity_s.cummax()
    max_dd       = ((equity_s - rolling_max) / rolling_max * 100).min()

    return {
        "equity":        equity_s,
        "total_return":  round(total_return, 1),
        "cagr":          round(cagr, 1),
        "sharpe":        round(sharpe, 3),
        "sortino":       round(sortino, 3),
        "max_dd":        round(max_dd, 1),
        "num_liq":       num_liq,
        "final_equity":  round(equity_s.iloc[-1], 2),
        "wiped_out":     equity_s.iloc[-1] < 1,  # ถ้าเหลือน้อยกว่า 1%
    }

# ─── Plotting ─────────────────────────────────────────────────────────────────

def plot_heatmaps(df_res, metric, title, cmap, fmt):
    pivot = df_res.pivot_table(
        index="margin_label", columns="leverage_label",
        values=metric, aggfunc="mean"
    )
    margin_order  = [f"{int(m*100)}% Margin" for m in MARGIN_RANGE]
    leverage_order = [f"{l}x" for l in LEVERAGE_RANGE]
    pivot = pivot.reindex(index=margin_order, columns=leverage_order)

    fig, ax = plt.subplots(figsize=(12, 7), facecolor="#0f1117")
    sns.heatmap(pivot, ax=ax, cmap=cmap, annot=True, fmt=fmt,
                linewidths=0.3, linecolor="#0f1117", cbar_kws={"shrink": 0.8})
    ax.set_title(f"{title} | EMA{EMA_FAST}/{EMA_SLOW} 1H 6Y",
                 color="#e6edf3", fontsize=11)
    ax.set_xlabel("Leverage", color="#c9d1d9")
    ax.set_ylabel("Margin per Trade", color="#c9d1d9")
    ax.tick_params(colors="#c9d1d9")
    plt.tight_layout()
    path = RESULTS_DIR / f"leverage_heatmap_{metric}.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_equity_grid(all_results, bh_equity):
    fig, axes = plt.subplots(len(MARGIN_RANGE), len(LEVERAGE_RANGE),
                             figsize=(28, 20), facecolor="#0f1117", squeeze=False)
    fig.suptitle(f"📊 Equity Curves — Leverage × Margin | EMA{EMA_FAST}/{EMA_SLOW} 1H 6Y",
                 color="#e6edf3", fontsize=14, y=0.995)

    colors_lev = ["#58a6ff", "#3fb950", "#ffa657", "#ff7b72", "#d2a8ff"]

    for mi, margin in enumerate(MARGIN_RANGE):
        for li, lev in enumerate(LEVERAGE_RANGE):
            ax    = axes[mi][li]
            key   = (lev, margin)
            res   = all_results.get(key)
            color = colors_lev[li]
            ax.set_facecolor("#0f1117")

            ax.plot(bh_equity.index, bh_equity.values, color="white",
                    linewidth=0.7, linestyle="--", alpha=0.4, label="B&H")

            if res and not res["wiped_out"]:
                ax.plot(res["equity"].index, res["equity"].values,
                        color=color, linewidth=0.9)
                ret_str = f"{res['total_return']:+.0f}%"
                sh_str  = f"Sh:{res['sharpe']:.2f}"
                liq_str = f"💀{res['num_liq']}" if res["num_liq"] > 0 else "✅"
                dd_str  = f"DD:{res['max_dd']:.0f}%"
            else:
                ax.text(0.5, 0.5, "💀 WIPED", transform=ax.transAxes,
                        ha="center", va="center", color="#f85149", fontsize=9, fontweight="bold")
                ret_str, sh_str, liq_str, dd_str = "—", "—", "—", "—"

            ax.set_title(f"{lev}x | {int(margin*100)}% Margin\n"
                         f"{ret_str} {sh_str} {liq_str}\n{dd_str}",
                         color="#e6edf3", fontsize=6.5, pad=2)
            ax.tick_params(labelsize=5, colors="#c9d1d9")
            ax.axhline(100, color="#30363d", linewidth=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.993])
    path = RESULTS_DIR / "leverage_equity_grid.png"
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_best_detail(best_key, best_res, bh_equity):
    lev, margin = best_key
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                    gridspec_kw={"height_ratios": [3, 1]}, facecolor="#0f1117")
    fig.suptitle(f"🏆 Best Leverage Combo: {lev}x | {int(margin*100)}% Margin per Trade | EMA{EMA_FAST}/{EMA_SLOW} 1H 6Y",
                 color="#e6edf3", fontsize=12)

    ax1.plot(best_res["equity"].index, best_res["equity"].values,
             color="#ffa657", linewidth=1.5, label=f"{lev}x | {int(margin*100)}% Margin")
    ax1.plot(bh_equity.index, bh_equity.values, color="white",
             linewidth=1, linestyle="--", alpha=0.5, label="Buy & Hold (1x Spot)")
    ax1.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")

    stats = (
        f"Leverage      : {lev}x\n"
        f"Margin/Trade  : {int(margin*100)}% of portfolio\n"
        f"Exposure/Trade: {int(lev*margin*100)}% of portfolio\n"
        f"{'─'*30}\n"
        f"Total Return  : {best_res['total_return']:+.1f}%\n"
        f"CAGR          : {best_res['cagr']:+.1f}%\n"
        f"Sharpe        : {best_res['sharpe']:.3f}\n"
        f"Sortino       : {best_res['sortino']:.3f}\n"
        f"Max DD        : {best_res['max_dd']:.1f}%\n"
        f"Liquidations  : {best_res['num_liq']} ครั้ง"
    )
    ax1.text(0.01, 0.97, stats, transform=ax1.transAxes, fontsize=9,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(facecolor="#161b22", edgecolor="#ffa657", alpha=0.9))
    ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")
    ax1.legend(loc="upper left", fontsize=9)
    plt.setp(ax1.get_xticklabels(), visible=False)

    rolling_max = best_res["equity"].cummax()
    dd = (best_res["equity"] - rolling_max) / rolling_max * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")
    plt.tight_layout()
    path = RESULTS_DIR / "leverage_best_equity.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"📥 โหลดข้อมูล 1H 6Y")
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    close_pct = df["close"].pct_change().fillna(0)
    bh_equity = (1 + close_pct).cumprod() * 100
    bh_return = bh_equity.iloc[-1] - 100

    print("\n🔧 คำนวณ Signals ...")
    long_sig, short_sig = get_base_signals(df)
    positions = build_raw_positions(long_sig, short_sig)
    print(f"✅ Signals พร้อม | Open positions: {(positions != 0).sum():,} candles")

    print(f"\n🚀 Grid Search: {len(LEVERAGE_RANGE) * len(MARGIN_RANGE)} combinations")
    print(f"   Leverage: {LEVERAGE_RANGE}")
    print(f"   Margin  : {[f'{int(m*100)}%' for m in MARGIN_RANGE]}")
    print(f"   Fee     : {FEE_RATE*100:.2f}% | Funding: {FUNDING_RATE*100:.3f}%/8h | Liq Maintenance: {MAINT_MARGIN*100:.1f}%")
    print("=" * 70)

    all_results = {}
    rows        = []

    for lev in LEVERAGE_RANGE:
        for margin in MARGIN_RANGE:
            liq_pct = (1 / lev) * (1 - MAINT_MARGIN) * 100
            res = simulate_leverage(df, positions, lev, margin)
            all_results[(lev, margin)] = res

            status = "💀WIPED" if res["wiped_out"] else (
                f"💀x{res['num_liq']}" if res["num_liq"] > 0 else "✅"
            )
            print(f"  {lev:>2}x | Margin {int(margin*100):>3}% "
                  f"(Exposure {int(lev*margin*100):>4}%) "
                  f"| Return: {res['total_return']:>+8.1f}% "
                  f"| Sharpe: {res['sharpe']:>5.3f} "
                  f"| MaxDD: {res['max_dd']:>7.1f}% "
                  f"| Liq.price ±{liq_pct:.0f}% "
                  f"| {status}")

            rows.append({
                "leverage":        lev,
                "margin":          margin,
                "exposure":        lev * margin,
                "leverage_label":  f"{lev}x",
                "margin_label":    f"{int(margin*100)}% Margin",
                "total_return":    res["total_return"],
                "cagr":            res["cagr"],
                "sharpe":          res["sharpe"],
                "sortino":         res["sortino"],
                "max_dd":          res["max_dd"],
                "num_liq":         res["num_liq"],
                "wiped_out":       int(res["wiped_out"]),
            })

    df_res = pd.DataFrame(rows)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("📊 Summary — Valid Combos (ไม่โดน Wipe)")
    print("=" * 70)
    valid = df_res[df_res["wiped_out"] == 0].sort_values("sharpe", ascending=False)
    print(f"{'Lev':>5} {'Margin':>8} {'Exposure':>9} {'Return%':>9} {'CAGR%':>7} "
          f"{'Sharpe':>7} {'MaxDD%':>8} {'Liq':>5}")
    print("-" * 70)
    for _, r in valid.iterrows():
        print(f"  {r['leverage']:>2}x   {int(r['margin']*100):>5}%   "
              f"{int(r['exposure']*100):>7}%   "
              f"{r['total_return']:>+9.1f}  {r['cagr']:>+7.1f}  "
              f"{r['sharpe']:>7.3f}  {r['max_dd']:>8.1f}  {int(r['num_liq']):>4}")

    wiped = df_res[df_res["wiped_out"] == 1]
    if len(wiped) > 0:
        print(f"\n💀 Wiped Out ({len(wiped)} combos): " +
              ", ".join(f"{int(r['leverage'])}x/{int(r['margin']*100)}%" for _, r in wiped.iterrows()))

    # Best by Sharpe (valid only)
    if len(valid) > 0:
        best_row = valid.iloc[0]
        best_key = (int(best_row["leverage"]), best_row["margin"])
        print(f"\n🏆 Best (Sharpe): {int(best_row['leverage'])}x | {int(best_row['margin']*100)}% Margin")
        print(f"   Exposure  : {int(best_row['exposure']*100)}% ของพอร์ต")
        print(f"   Return    : {best_row['total_return']:+.1f}%")
        print(f"   Sharpe    : {best_row['sharpe']:.3f}")
        print(f"   MaxDD     : {best_row['max_dd']:.1f}%")
        print(f"   Liq count : {int(best_row['num_liq'])} ครั้ง ใน 6 ปี")

    print(f"\n⭐ Baseline (1x, 100% Margin): {all_results[(1, 1.00)]['total_return']:+.1f}%")
    print(f"⭐ Buy & Hold               : {bh_return:+.1f}%")

    # ── Charts ──
    print("\n📈 Plot กราฟ ...")
    df_res.to_csv(RESULTS_DIR / "leverage_results.csv", index=False)

    for metric, title, cmap, fmt in [
        ("total_return", "Total Return (%)",  "RdYlGn",   ".0f"),
        ("sharpe",       "Sharpe Ratio",       "RdYlGn",   ".2f"),
        ("max_dd",       "Max Drawdown (%)",   "RdYlGn_r", ".0f"),
        ("num_liq",      "Liquidations (ครั้ง)", "RdYlGn_r", ".0f"),
    ]:
        p = plot_heatmaps(df_res, metric, title, cmap, fmt)
        print(f"✅ {p.name}")

    p = plot_equity_grid(all_results, bh_equity)
    print(f"✅ {p.name}")

    if len(valid) > 0:
        p = plot_best_detail(best_key, all_results[best_key], bh_equity)
        print(f"✅ {p.name}")

    print("\n🎉 Leverage Test เสร็จ!")


if __name__ == "__main__":
    main()
