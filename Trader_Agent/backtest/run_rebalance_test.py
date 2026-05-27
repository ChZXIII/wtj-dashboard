"""
run_rebalance_test.py
เปรียบเทียบ 5 วิธี Rebalance บน Strategy 3x / 50% Margin (1H 6Y)

วิธีที่ทดสอบ:
  0. Baseline   — ไม่ทำอะไรเลย Compound ปกติ
  1. HWM 25%    — New ATH ทุกครั้ง ถอน 25% ออก Stable
  2. HWM 50%    — New ATH ทุกครั้ง ถอน 50% ออก Stable
  3. Quarterly  — ทุก 3 เดือน ถอนกำไรส่วนเกิน 50% ออก Stable
  4. DD De-risk — DD>25% ลด Margin 50%→25% / DD>45% หยุด Strategy
  5. 50/50 Alloc— ทุกเดือน Rebalance Strategy:Stable = 50:50
  6. Target 10x — Compound จนถึง 10x (1000%) แล้วถอนออกทั้งหมด

Usage:
    python backtest/run_rebalance_test.py
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

DATA_PATH    = Path(__file__).parent / "data" / "btc_1H_6y.csv"
RESULTS_DIR  = Path(__file__).parent / "results"
FEE_RATE     = 0.0004
FUNDING_RATE = 0.0001
FUNDING_EVERY = 8
MAINT_MARGIN  = 0.004
LEVERAGE      = 3
MARGIN_PCT    = 0.50
LIQ_PCT       = (1 / LEVERAGE) * (1 - MAINT_MARGIN)

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#1a1d2e",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#c9d1d9",
    "ytick.color": "#c9d1d9", "text.color": "#c9d1d9",
    "grid.color": "#30363d", "legend.facecolor": "#161b22",
    "legend.edgecolor": "#30363d",
})

# ─── Signals ─────────────────────────────────────────────────────────────────

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

def compute_macro(df):
    daily   = df["close"].resample("1D").last().dropna()
    ema200d = daily.ewm(span=200, adjust=False).mean()
    return df["close"] > ema200d.reindex(df.index, method="ffill")

def build_positions(df):
    close = df["close"]
    is_bull  = compute_macro(df)
    ema_fast = ta.ema(close, 25)
    ema_slow = ta.ema(close, 100)
    rsi      = ta.rsi(close, 14)
    long_sig  = crossover(ema_fast, ema_slow) & (rsi < 60)
    short_sig = crossunder(ema_fast, ema_slow) & (rsi > 35) & ~is_bull
    pos = np.zeros(len(close), dtype=np.int8)
    ls  = long_sig.fillna(False).values.astype(bool)
    ss  = short_sig.fillna(False).values.astype(bool)
    cur = 0
    for i in range(len(pos)):
        if ls[i]:   cur = 1
        elif ss[i]: cur = -1
        pos[i] = cur
    return pos

# ─── Core Futures Simulator (1 step) ─────────────────────────────────────────

def step(portfolio, entry_price, cur_pos, i, close_arr, high_arr, low_arr, sig,
         margin_pct=MARGIN_PCT, leverage=LEVERAGE):
    """
    คำนวณ portfolio หลัง 1 candle พร้อม Liquidation + Funding
    Returns: (new_portfolio, new_entry_price, new_cur_pos, liquidated)
    """
    liquidated = False

    if cur_pos != 0:
        price_now = close_arr[i]

        # Check Liquidation
        if cur_pos == 1:
            hit_liq = low_arr[i] <= entry_price * (1 - LIQ_PCT)
        else:
            hit_liq = high_arr[i] >= entry_price * (1 + LIQ_PCT)

        if hit_liq:
            portfolio -= portfolio * margin_pct
            liquidated = True
            cur_pos = 0; entry_price = 0.0
        else:
            pct_chg  = (price_now - close_arr[i-1]) / close_arr[i-1] if i > 0 else 0
            notional = portfolio * margin_pct * leverage
            portfolio += notional * pct_chg * cur_pos
            if i % FUNDING_EVERY == 0:
                portfolio -= notional * FUNDING_RATE
            if sig != cur_pos:
                portfolio -= notional * FEE_RATE
                if sig != 0:
                    portfolio -= portfolio * margin_pct * leverage * FEE_RATE
                    entry_price = price_now; cur_pos = sig
                else:
                    cur_pos = 0; entry_price = 0.0
    else:
        if sig != 0:
            portfolio -= portfolio * margin_pct * leverage * FEE_RATE
            entry_price = close_arr[i]; cur_pos = sig

    return max(portfolio, 0), entry_price, cur_pos, liquidated

# ─── Method 0: Baseline (No Rebalance) ───────────────────────────────────────

def run_baseline(df, positions):
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    portfolio, entry_price, cur_pos = 100.0, 0.0, 0
    equity = np.zeros(n)
    stable = np.zeros(n)   # ไม่มีถอน = 0 ตลอด

    for i in range(n):
        portfolio, entry_price, cur_pos, _ = step(
            portfolio, entry_price, cur_pos, i,
            close_arr, high_arr, low_arr, positions[i])
        equity[i] = portfolio
        stable[i] = 0.0

    return pd.Series(equity, index=df.index), pd.Series(stable, index=df.index)

# ─── Method 1&2: High Watermark Harvest ──────────────────────────────────────

def run_hwm_harvest(df, positions, harvest_pct):
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    portfolio, entry_price, cur_pos = 100.0, 0.0, 0
    hwm = 100.0
    cum_stable = 0.0
    equity = np.zeros(n)
    stable_acc = np.zeros(n)

    for i in range(n):
        portfolio, entry_price, cur_pos, _ = step(
            portfolio, entry_price, cur_pos, i,
            close_arr, high_arr, low_arr, positions[i])

        # เมื่อทำ New ATH → ถอน harvest_pct ออก
        if portfolio > hwm:
            hwm = portfolio
            gain = portfolio - 100.0   # gain จาก original capital
            withdrawn = portfolio * harvest_pct
            portfolio -= withdrawn
            cum_stable += withdrawn

        equity[i] = portfolio
        stable_acc[i] = cum_stable

    return pd.Series(equity, index=df.index), pd.Series(stable_acc, index=df.index)

# ─── Method 3: Quarterly Harvest (50% of gains) ──────────────────────────────

def run_quarterly_harvest(df, positions, withdraw_ratio=0.50):
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    portfolio, entry_price, cur_pos = 100.0, 0.0, 0
    cum_stable = 0.0
    equity = np.zeros(n)
    stable_acc = np.zeros(n)
    quarter_candles = 365 * 24 // 4   # ~2,190 candles ต่อ quarter

    for i in range(n):
        portfolio, entry_price, cur_pos, _ = step(
            portfolio, entry_price, cur_pos, i,
            close_arr, high_arr, low_arr, positions[i])

        # ทุก Quarter → ถอน gain × withdraw_ratio ออก
        if i > 0 and i % quarter_candles == 0 and portfolio > 100.0:
            gain = portfolio - 100.0
            withdrawn = gain * withdraw_ratio
            portfolio -= withdrawn
            cum_stable += withdrawn

        equity[i] = portfolio
        stable_acc[i] = cum_stable

    return pd.Series(equity, index=df.index), pd.Series(stable_acc, index=df.index)

# ─── Method 4: DD-based De-risk ──────────────────────────────────────────────

def run_dd_derisk(df, positions, dd_soft=0.25, dd_hard=0.45):
    """
    DD > dd_soft → ลด Margin จาก 50% → 25%
    DD > dd_hard → หยุด Strategy (Margin = 0) จนกว่า portfolio recover 20%
    """
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    portfolio, entry_price, cur_pos = 100.0, 0.0, 0
    hwm = 100.0
    equity = np.zeros(n)
    stable_acc = np.zeros(n)

    for i in range(n):
        dd = (portfolio - hwm) / hwm if hwm > 0 else 0  # ค่าติดลบ

        if dd < -dd_hard:
            # หยุด Strategy จนกว่าจะ Recover 20%
            eff_margin = 0.0
        elif dd < -dd_soft:
            # ลด Margin ลงครึ่ง
            eff_margin = MARGIN_PCT * 0.5
        else:
            eff_margin = MARGIN_PCT

        portfolio, entry_price, cur_pos, _ = step(
            portfolio, entry_price, cur_pos, i,
            close_arr, high_arr, low_arr, positions[i],
            margin_pct=eff_margin)

        if portfolio > hwm:
            hwm = portfolio

        equity[i] = portfolio
        stable_acc[i] = 0.0   # ไม่ได้ถอน แค่ลด Risk

    return pd.Series(equity, index=df.index), pd.Series(stable_acc, index=df.index)

# ─── Method 5: 50/50 Monthly Rebalance ───────────────────────────────────────

def run_fixed_allocation(df, positions, strategy_ratio=0.50):
    """
    ทุกเดือน rebalance ให้ Strategy:Stable = strategy_ratio:(1-strategy_ratio)
    """
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    strat_portfolio = 100.0 * strategy_ratio
    stable_pool     = 100.0 * (1 - strategy_ratio)
    entry_price, cur_pos = 0.0, 0
    equity = np.zeros(n)
    stable_acc = np.zeros(n)
    monthly_candles = 365 * 24 // 12   # ~730 candles ต่อเดือน

    for i in range(n):
        strat_portfolio, entry_price, cur_pos, _ = step(
            strat_portfolio, entry_price, cur_pos, i,
            close_arr, high_arr, low_arr, positions[i])

        # ทุกเดือน rebalance กลับ 50/50
        if i > 0 and i % monthly_candles == 0:
            total = strat_portfolio + stable_pool
            strat_portfolio = total * strategy_ratio
            stable_pool     = total * (1 - strategy_ratio)

        equity[i] = strat_portfolio + stable_pool
        stable_acc[i] = stable_pool

    return pd.Series(equity, index=df.index), pd.Series(stable_acc, index=df.index)

# ─── Method 6: Target 10x then Exit ─────────────────────────────────────────

def run_target_exit(df, positions, target_mult=10.0):
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n = len(close_arr)

    portfolio, entry_price, cur_pos = 100.0, 0.0, 0
    locked = 0.0
    target_hit = False
    target_at  = None
    equity = np.zeros(n)
    stable_acc = np.zeros(n)

    for i in range(n):
        if not target_hit:
            portfolio, entry_price, cur_pos, _ = step(
                portfolio, entry_price, cur_pos, i,
                close_arr, high_arr, low_arr, positions[i])

            if portfolio >= 100.0 * target_mult:
                locked = portfolio
                portfolio = 0.0
                target_hit = True
                cur_pos = 0
                target_at = df.index[i]

        equity[i] = portfolio
        stable_acc[i] = locked

    return pd.Series(equity, index=df.index), pd.Series(stable_acc, index=df.index), target_at

# ─── Metrics ─────────────────────────────────────────────────────────────────

def compute_metrics(equity_s, stable_s, label):
    total_equity = equity_s + stable_s
    total_return = total_equity.iloc[-1] - 100
    strat_return = equity_s.iloc[-1] - 100
    years = len(equity_s) / (365 * 24)
    cagr  = ((total_equity.iloc[-1] / 100) ** (1 / years) - 1) * 100 if total_equity.iloc[-1] > 0 else -100

    # MaxDD บน Strategy portion เท่านั้น (ไม่รวม stable)
    rm    = equity_s.cummax()
    maxdd = ((equity_s - rm) / rm * 100).min()

    pr    = equity_s.pct_change().fillna(0)
    std   = pr.std()
    sharpe = (pr.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0

    return {
        "label":        label,
        "final_strat":  round(equity_s.iloc[-1], 1),
        "final_stable": round(stable_s.iloc[-1], 1),
        "final_total":  round(total_equity.iloc[-1], 1),
        "total_return": round(total_return, 1),
        "cagr":         round(cagr, 1),
        "sharpe":       round(sharpe, 3),
        "max_dd":       round(maxdd, 1),
    }

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"📥 โหลดข้อมูล 1H 6Y | Strategy: {LEVERAGE}x / {int(MARGIN_PCT*100)}% Margin")
    print("=" * 70)
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    close_pct = df["close"].pct_change().fillna(0)
    bh_equity = (1 + close_pct).cumprod() * 100
    bh_return = bh_equity.iloc[-1] - 100

    print("\n🔧 Build Signals ...")
    positions = build_positions(df)

    # ─── Run All Methods ─────────────────────────────────────────────────────
    print("\n🚀 Run ทุก Rebalance Method ...")
    print("=" * 70)

    results = []
    all_equity = {}
    all_total  = {}

    # 0. Baseline
    eq, st = run_baseline(df, positions)
    m = compute_metrics(eq, st, "0️⃣  Baseline (No Rebalance)")
    results.append(m); all_equity["Baseline"] = eq; all_total["Baseline"] = eq + st
    print(f"  0. Baseline         | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")

    # 1. HWM 25%
    eq, st = run_hwm_harvest(df, positions, 0.25)
    m = compute_metrics(eq, st, "1️⃣  HWM Harvest 25%")
    results.append(m); all_equity["HWM 25%"] = eq; all_total["HWM 25%"] = eq + st
    print(f"  1. HWM 25%          | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")
    print(f"     └ Strategy: {m['final_strat']:.0f}%  | Stable: {m['final_stable']:.0f}%")

    # 2. HWM 50%
    eq, st = run_hwm_harvest(df, positions, 0.50)
    m = compute_metrics(eq, st, "2️⃣  HWM Harvest 50%")
    results.append(m); all_equity["HWM 50%"] = eq; all_total["HWM 50%"] = eq + st
    print(f"  2. HWM 50%          | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")
    print(f"     └ Strategy: {m['final_strat']:.0f}%  | Stable: {m['final_stable']:.0f}%")

    # 3. Quarterly Harvest
    eq, st = run_quarterly_harvest(df, positions, 0.50)
    m = compute_metrics(eq, st, "3️⃣  Quarterly Harvest 50%")
    results.append(m); all_equity["Quarterly"] = eq; all_total["Quarterly"] = eq + st
    print(f"  3. Quarterly        | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")
    print(f"     └ Strategy: {m['final_strat']:.0f}%  | Stable: {m['final_stable']:.0f}%")

    # 4. DD De-risk
    eq, st = run_dd_derisk(df, positions, 0.25, 0.45)
    m = compute_metrics(eq, st, "4️⃣  DD De-risk (>25%→Half / >45%→Stop)")
    results.append(m); all_equity["DD De-risk"] = eq; all_total["DD De-risk"] = eq + st
    print(f"  4. DD De-risk       | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")

    # 5. 50/50 Allocation
    eq, st = run_fixed_allocation(df, positions, 0.50)
    m = compute_metrics(eq, st, "5️⃣  Fixed 50/50 Monthly Rebalance")
    results.append(m); all_equity["50/50"] = eq; all_total["50/50"] = eq + st
    print(f"  5. 50/50 Monthly    | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")
    print(f"     └ Strategy: {m['final_strat']:.0f}%  | Stable: {m['final_stable']:.0f}%")

    # 6. Target 10x
    eq, st, hit_at = run_target_exit(df, positions, 10.0)
    m = compute_metrics(eq, st, "6️⃣  Target 10x then Full Exit")
    results.append(m); all_equity["Target 10x"] = eq; all_total["Target 10x"] = eq + st
    hit_str = hit_at.strftime("%b %Y") if hit_at else "ไม่ถึง Target"
    print(f"  6. Target 10x       | Total: {m['final_total']:>8,.0f}% | Return: {m['total_return']:>+8,.0f}% | MaxDD: {m['max_dd']:>7.1f}% | Sharpe: {m['sharpe']:.3f}")
    print(f"     └ Target ถึง: {hit_str}")

    print(f"\n  ⭐ Buy & Hold (1x Spot): +{bh_return:.0f}%")

    # ── Summary Table ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("📊 SUMMARY — Portfolio Total (Strategy + Stable/Withdrawn)")
    print("=" * 70)
    print(f"{'Method':<35} {'Total %':>9} {'CAGR':>7} {'Sharpe':>7} {'MaxDD(S)':>9}")
    print("-" * 70)
    for r in results:
        print(f"  {r['label']:<33} {r['total_return']:>+9,.0f}% {r['cagr']:>+7.1f}% "
              f"{r['sharpe']:>7.3f} {r['max_dd']:>9.1f}%")
    print(f"\n  ⭐ Buy & Hold: +{bh_return:.0f}% | MaxDD(S) = MaxDD ของ Strategy portion เท่านั้น")

    # ── Plot ─────────────────────────────────────────────────────────────────
    print("\n📈 Plot กราฟ ...")
    colors = ["#58a6ff", "#3fb950", "#ffa657", "#d2a8ff", "#ff7b72", "#79c0ff", "#f0e68c"]

    # Equity (Total = Strategy + Stable)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(22, 11),
                                    gridspec_kw={"height_ratios": [3, 1]},
                                    facecolor="#0f1117")
    fig.suptitle(f"📊 Rebalance Strategy Comparison | 3x/50% Margin | EMA25/100 1H 6Y\n"
                 f"Total Portfolio = Strategy + Stable/Withdrawn",
                 color="#e6edf3", fontsize=11, y=0.99)

    ax1.plot(bh_equity.index, bh_equity.values, color="#6e7681",
             linewidth=1, linestyle="--", alpha=0.7, label=f"Buy & Hold | +{bh_return:.0f}%")
    ax1.axhline(100, color="#30363d", linewidth=0.7, linestyle=":")

    for (name, total_eq), color, res in zip(all_total.items(), colors, results):
        ax1.plot(total_eq.index, total_eq.values, color=color, linewidth=1.3,
                 label=f"{res['label']} | +{res['total_return']:,.0f}% | DD:{res['max_dd']:.0f}%")

    ax1.set_yscale("log")
    ax1.set_ylabel("Total Portfolio Value (%) — Log Scale", color="#c9d1d9")
    ax1.legend(loc="upper left", fontsize=7.5, framealpha=0.85)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # MaxDD ของ Baseline strategy portion
    rm = all_equity["Baseline"].cummax()
    dd = (all_equity["Baseline"] - rm) / rm * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#58a6ff", alpha=0.35, label="Baseline DD")
    rm2 = all_equity["DD De-risk"].cummax()
    dd2 = (all_equity["DD De-risk"] - rm2) / rm2 * 100
    ax2.fill_between(dd2.index, dd2.values, 0, color="#ff7b72", alpha=0.35, label="DD De-risk")
    ax2.set_ylabel("Strategy Drawdown (%)", color="#c9d1d9")
    ax2.legend(fontsize=7)

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    p = RESULTS_DIR / "rebalance_comparison.png"
    fig.savefig(p, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"✅ {p}")

    # Bar Chart
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor="#0f1117")
    fig.suptitle("📊 Rebalance Methods — ตัวเลขเปรียบเทียบ | 3x/50% 1H 6Y",
                 color="#e6edf3", fontsize=11)

    labels_short = ["Baseline", "HWM 25%", "HWM 50%", "Quarterly", "DD De-risk", "50/50", "10x Exit"]
    metrics_plot = [
        ([r["total_return"] for r in results], "Total Return (%)", colors),
        ([r["max_dd"] for r in results], "Max DD Strategy (%)", colors),
        ([r["sharpe"] for r in results], "Sharpe Ratio", colors),
    ]

    for ax, (vals, title, cols) in zip(axes, metrics_plot):
        ax.set_facecolor("#1a1d2e")
        bars = ax.bar(labels_short, vals, color=cols[:len(labels_short)])
        ax.set_title(title, color="#e6edf3", fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=7, colors="#c9d1d9")
        ax.tick_params(axis="y", colors="#c9d1d9")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f"{val:,.0f}", ha="center", va="bottom", fontsize=7, color="#e6edf3")

    plt.tight_layout()
    p2 = RESULTS_DIR / "rebalance_bars.png"
    fig.savefig(p2, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"✅ {p2}")
    print("\n🎉 Rebalance Test เสร็จ!")

if __name__ == "__main__":
    main()
