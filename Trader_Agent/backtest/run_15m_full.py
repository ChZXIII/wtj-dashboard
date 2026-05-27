"""
run_15m_full.py
Step 1: Backtest 12 Indicators บน 15m 6Y + Option B (Macro Filter)
Step 2: Auto-detect Winner แล้ว Grid Search Optimize เลย

Usage:
    python backtest/run_15m_full.py
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

DATA_PATH   = Path(__file__).parent / "data" / "btc_15m_6y.csv"
RESULTS_DIR = Path(__file__).parent / "results" / "15m"
FEE_RATE    = 0.001

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#1a1d2e",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#c9d1d9",
    "ytick.color": "#c9d1d9", "text.color": "#c9d1d9",
    "grid.color": "#30363d", "legend.facecolor": "#161b22",
})

CANDLES_PER_YEAR = 365 * 24 * 4   # 15min = 4 candles/hour

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

def compute_macro(df):
    daily    = df["close"].resample("1D").last().dropna()
    ema200d  = daily.ewm(span=200, adjust=False).mean()
    return df["close"] > ema200d.reindex(df.index, method="ffill")

def get_signals(df, name):
    close, high, low = df["close"], df["high"], df["low"]
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
        st   = ta.supertrend(high, low, close, length=10, multiplier=3)
        dcol = [c for c in st.columns if "SUPERTd" in c][0]
        d    = st[dcol]
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
        m  = ta.macd(close, 12, 26, 9)
        ml = m[[c for c in m.columns if c.startswith("MACD_")][0]]
        sl = m[[c for c in m.columns if c.startswith("MACDs_")][0]]
        return crossover(ml, sl), crossunder(ml, sl)
    elif name == "Bollinger Bands":
        bb = ta.bbands(close, 20, 2)
        lo = bb[[c for c in bb.columns if "BBL_" in c][0]]
        up = bb[[c for c in bb.columns if "BBU_" in c][0]]
        return crossover(close, lo), crossunder(close, up)
    elif name == "Keltner Channel":
        kc = ta.kc(high, low, close, 20, 2)
        up = kc[[c for c in kc.columns if "KCUe_" in c][0]]
        lo = kc[[c for c in kc.columns if "KCLe_" in c][0]]
        return crossover(close, up), crossunder(close, lo)
    elif name == "VWAP":
        df2 = df.copy(); df2["date"] = df2.index.date
        df2["tp"] = (df2["high"] + df2["low"] + df2["close"]) / 3
        df2["tpv"] = df2["tp"] * df2["volume"]
        vwap = df2.groupby("date")["tpv"].cumsum() / df2.groupby("date")["volume"].cumsum()
        surge = df["volume"] > df["volume"].rolling(20).mean() * 1.5
        return crossover(close, vwap) & surge, crossunder(close, vwap) & surge
    elif name == "OBV Trend":
        obv    = ta.obv(close, df["volume"])
        obv_ma = obv.rolling(20).mean()
        return crossover(obv, obv_ma), crossunder(obv, obv_ma)
    elif name == "EMA + RSI Filter":
        e1, e2 = ta.ema(close, 20), ta.ema(close, 50)
        rsi    = ta.rsi(close, 14)
        return crossover(e1, e2) & (rsi < 60), crossunder(e1, e2) & (rsi > 40)

def build_pos_ls_filter(long_sig, short_sig, is_bull):
    long_arr  = long_sig.fillna(False).values.astype(bool)
    short_arr = (short_sig.fillna(False) & ~is_bull).values.astype(bool)
    pos = np.zeros(len(long_arr), dtype=np.int8)
    cur = 0
    for i in range(len(pos)):
        if long_arr[i]:   cur = 1
        elif short_arr[i]: cur = -1
        pos[i] = cur
    return pd.Series(pos, index=long_sig.index)

def fast_backtest(close_pct, pos):
    pos_s   = pos.shift(1).fillna(0)
    fee     = pos.diff().fillna(0).abs() * FEE_RATE
    net_ret = pos_s * close_pct - fee
    equity  = (1 + net_ret).cumprod()
    total_return = (equity.iloc[-1] - 1) * 100
    cagr         = ((equity.iloc[-1]) ** (1 / (len(close_pct) / CANDLES_PER_YEAR)) - 1) * 100
    std          = net_ret.std()
    sharpe       = (net_ret.mean() / std) * np.sqrt(CANDLES_PER_YEAR) if std > 0 else 0
    down         = net_ret[net_ret < 0]
    sortino      = (net_ret.mean() / down.std()) * np.sqrt(CANDLES_PER_YEAR) if len(down) > 0 and down.std() > 0 else 0
    rolling_max  = equity.cummax()
    max_dd       = ((equity - rolling_max) / rolling_max * 100).min()
    gp, gl       = net_ret[net_ret > 0].sum(), abs(net_ret[net_ret < 0].sum())
    pf           = gp / gl if gl > 0 else np.inf
    trades       = int(pos.diff().fillna(0).abs().gt(0).sum())
    pos_only     = net_ret[pos_s != 0]
    win_rate     = len(pos_only[pos_only > 0]) / len(pos_only) * 100 if len(pos_only) > 0 else 0
    return {
        "equity": equity * 100, "total_return": round(total_return, 1),
        "cagr": round(cagr, 1), "sharpe": round(sharpe, 4), "sortino": round(sortino, 4),
        "max_dd": round(max_dd, 1), "profit_factor": round(pf, 4),
        "trades": trades, "win_rate": round(win_rate, 1),
    }

STRATEGIES = [
    "EMA Cross 9/21", "EMA Cross 20/50", "EMA Cross 50/200",
    "Supertrend (10,3)", "RSI (14)", "Stochastic RSI",
    "MACD (12/26/9)", "Bollinger Bands", "Keltner Channel",
    "VWAP", "OBV Trend", "EMA + RSI Filter",
]

# ── PART 1: 12 Indicators ────────────────────────────────────────────────────

def run_indicator_comparison(df, is_bull, close_pct, bh_return):
    print("\n" + "=" * 65)
    print("📊 PART 1 — 12 Indicators | Option B (L+S + Macro Filter) | 15m 6Y")
    print("=" * 65)
    results, rows = {}, []
    for name in STRATEGIES:
        print(f"  ▶ {name:<22}", end=" ", flush=True)
        try:
            long_sig, short_sig = get_signals(df, name)
            pos = build_pos_ls_filter(long_sig, short_sig, is_bull)
            res = fast_backtest(close_pct, pos)
            results[name] = res
            rows.append({"strategy": name, **{k: v for k, v in res.items() if k != "equity"}})
            print(f"Return: {res['total_return']:>+7.1f}% | Sharpe: {res['sharpe']:>5.3f} | Trades: {res['trades']:>5,}")
        except Exception as e:
            print(f"❌ {e}")

    df_res = pd.DataFrame(rows).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_res.index += 1

    print("\n" + "=" * 65)
    print(f"{'Rk':<4} {'Strategy':<22} {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'WinR%':>7} {'PF':>6} {'Trades':>7}")
    print("-" * 80)
    for i, r in df_res.iterrows():
        print(f"{i:<4} {r['strategy']:<22} {r['total_return']:>+9.1f} {r['cagr']:>+7.1f} "
              f"{r['sharpe']:>7.3f} {r['max_dd']:>8.1f} {r['win_rate']:>6.1f}% "
              f"{r['profit_factor']:>6.3f} {int(r['trades']):>7,}")
    print(f"\n  ★ Buy & Hold: +{bh_return:.1f}%")

    # Plot
    bh_eq = (1 + close_pct).cumprod() * 100
    colors = plt.cm.tab20(np.linspace(0, 1, len(results)))
    fig, ax = plt.subplots(figsize=(20, 9), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")
    ax.plot(bh_eq.index, bh_eq.values, color="white", linewidth=2, linestyle="--",
            alpha=0.6, label="Buy & Hold", zorder=10)
    for (name, res), color in zip(results.items(), colors):
        ax.plot(res["equity"].index, res["equity"].values, linewidth=0.8, label=name, color=color, alpha=0.85)
    ax.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")
    ax.set_title("📊 BTC/USDT 15m — 12 Indicators | Option B (L+S + Macro Filter) | 6Y",
                 color="#e6edf3", fontsize=12)
    ax.set_ylabel("Portfolio Value (%) — Start = 100%", color="#c9d1d9")
    ax.legend(loc="upper left", fontsize=6.5, ncol=2)
    plt.tight_layout()
    p = RESULTS_DIR / "15m_equity_all.png"
    fig.savefig(p, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"\n✅ Chart: {p}")

    df_res.to_csv(RESULTS_DIR / "15m_indicators.csv")
    winner = df_res.iloc[0]["strategy"]
    print(f"\n🏆 Winner: {winner} | Sharpe: {df_res.iloc[0]['sharpe']:.3f} | Return: {df_res.iloc[0]['total_return']:+.1f}%")
    return winner, df_res

# ── PART 2: Optimize Winner ──────────────────────────────────────────────────

def optimize_strategy(df, is_bull, close_pct, winner_name):
    """Optimize winner บน 15m — adapt parameter grid ตาม strategy"""
    print("\n" + "=" * 65)
    print(f"🔧 PART 2 — Optimize '{winner_name}' | 15m 6Y")
    print("=" * 65)

    close = df["close"]
    # Pre-compute RSI once
    rsi_series = ta.rsi(close, 14)

    # Strategy-specific grids
    if "EMA + RSI Filter" in winner_name:
        EMA_FAST_RANGE  = [5, 8, 10, 12, 15, 20, 25]
        EMA_SLOW_RANGE  = [20, 30, 50, 75, 100, 150, 200]
        RSI_LONG_RANGE  = [50, 55, 60, 65, 70]
        RSI_SHORT_RANGE = [30, 35, 40, 45, 50]
        combos = [(ef, es, rl, rs) for ef, es, rl, rs
                  in product(EMA_FAST_RANGE, EMA_SLOW_RANGE, RSI_LONG_RANGE, RSI_SHORT_RANGE)
                  if ef < es]
        def build_combo(ef, es, rl, rs, ema_f_cache, ema_s_cache):
            long_sig  = crossover(ema_f_cache, ema_s_cache) & (rsi_series < rl)
            short_sig = crossunder(ema_f_cache, ema_s_cache) & (rsi_series > rs) & ~is_bull
            return build_pos_ls_filter(long_sig, short_sig, is_bull)
        param_names = ["ema_fast", "ema_slow", "rsi_long", "rsi_short"]

    elif "EMA Cross" in winner_name:
        FAST_RANGE = [5, 8, 10, 12, 15, 20, 25, 30]
        SLOW_RANGE = [20, 30, 50, 75, 100, 150, 200]
        combos = [(f, s) for f, s in product(FAST_RANGE, SLOW_RANGE) if f < s]
        def build_combo(f, s, ema_f_cache, ema_s_cache):
            long_sig  = crossover(ema_f_cache, ema_s_cache)
            short_sig = crossunder(ema_f_cache, ema_s_cache) & ~is_bull
            return build_pos_ls_filter(long_sig, short_sig, is_bull)
        param_names = ["ema_fast", "ema_slow"]

    elif "Bollinger" in winner_name:
        LENGTH_RANGE = [10, 14, 20, 25, 30]
        STD_RANGE    = [1.5, 2.0, 2.5, 3.0]
        combos = list(product(LENGTH_RANGE, STD_RANGE))
        def build_combo(length, std, *_):
            bb  = ta.bbands(close, length, std)
            lo  = bb[[c for c in bb.columns if "BBL_" in c][0]]
            up  = bb[[c for c in bb.columns if "BBU_" in c][0]]
            ls  = crossover(close, lo)
            ss  = crossunder(close, up) & ~is_bull
            return build_pos_ls_filter(ls, ss, is_bull)
        param_names = ["length", "std_mult"]

    elif "Keltner" in winner_name:
        LENGTH_RANGE = [10, 14, 20, 25]
        MULT_RANGE   = [1.5, 2.0, 2.5, 3.0]
        combos = list(product(LENGTH_RANGE, MULT_RANGE))
        def build_combo(length, mult, *_):
            kc = ta.kc(df["high"], df["low"], close, length, mult)
            up = kc[[c for c in kc.columns if "KCUe_" in c][0]]
            lo = kc[[c for c in kc.columns if "KCLe_" in c][0]]
            ls = crossover(close, up)
            ss = crossunder(close, lo) & ~is_bull
            return build_pos_ls_filter(ls, ss, is_bull)
        param_names = ["length", "mult"]

    elif "Supertrend" in winner_name:
        LEN_RANGE  = [7, 10, 14, 20]
        MULT_RANGE = [2.0, 3.0, 4.0, 5.0]
        combos = list(product(LEN_RANGE, MULT_RANGE))
        def build_combo(length, mult, *_):
            st   = ta.supertrend(df["high"], df["low"], close, length=length, multiplier=mult)
            dcol = [c for c in st.columns if "SUPERTd" in c][0]
            d    = st[dcol]
            ls   = (d == 1) & (d.shift(1) == -1)
            ss   = ((d == -1) & (d.shift(1) == 1)) & ~is_bull
            return build_pos_ls_filter(ls, ss, is_bull)
        param_names = ["length", "mult"]

    elif "RSI" in winner_name and "Stochastic" not in winner_name:
        OB_RANGE = [65, 70, 75, 80]
        OS_RANGE = [20, 25, 30, 35]
        combos = list(product(OB_RANGE, OS_RANGE))
        def build_combo(ob, os, *_):
            rsi = ta.rsi(close, 14)
            ls  = crossover(rsi, pd.Series(os, index=rsi.index))
            ss  = crossunder(rsi, pd.Series(ob, index=rsi.index)) & ~is_bull
            return build_pos_ls_filter(ls, ss, is_bull)
        param_names = ["overbought", "oversold"]

    else:
        # Generic EMA fast/slow
        FAST_RANGE = [5, 8, 10, 15, 20, 25]
        SLOW_RANGE = [20, 30, 50, 75, 100]
        combos = [(f, s) for f, s in product(FAST_RANGE, SLOW_RANGE) if f < s]
        def build_combo(f, s, *_):
            ef, es = ta.ema(close, f), ta.ema(close, s)
            ls = crossover(ef, es); ss = crossunder(ef, es) & ~is_bull
            return build_pos_ls_filter(ls, ss, is_bull)
        param_names = ["param1", "param2"]

    total = len(combos)
    print(f"  Grid: {total:,} combinations")

    # Cache EMA calculations for EMA-based strategies
    prev_ef, prev_es = None, None
    ema_f_cache = ema_s_cache = None

    results = []
    for idx, combo in enumerate(combos):
        try:
            if "EMA" in winner_name:
                ef_val = combo[0]; es_val = combo[1]
                if ef_val != prev_ef:
                    ema_f_cache = ta.ema(close, ef_val); prev_ef = ef_val
                if es_val != prev_es:
                    ema_s_cache = ta.ema(close, es_val); prev_es = es_val
                pos = build_combo(*combo, ema_f_cache, ema_s_cache)
            else:
                pos = build_combo(*combo)
            res = fast_backtest(close_pct, pos)
            row = {p: v for p, v in zip(param_names, combo)}
            row.update({k: v for k, v in res.items() if k != "equity"})
            results.append(row)
        except Exception as e:
            pass

        if (idx + 1) % 50 == 0 or (idx + 1) == total:
            if results:
                best = max(results, key=lambda x: x["sharpe"])
                print(f"  [{idx+1:>4}/{total}] Best Sharpe: {best['sharpe']:.3f} "
                      f"| {dict(zip(param_names, combo))} "
                      f"| Return: {best.get('total_return', 0):+.1f}%")

    if not results:
        print("❌ ไม่มีผล optimization")
        return None

    df_opt = pd.DataFrame(results).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df_opt.index += 1

    print("\n" + "=" * 65)
    print(f"🏆 TOP 10 — {winner_name} (15m)")
    print("=" * 65)
    header = f"{'Rk':<4} " + " ".join(f"{p:>8}" for p in param_names) + \
             f" {'Return%':>9} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'Trades':>7}"
    print(header)
    print("-" * (len(header) + 5))
    for i, r in df_opt.head(10).iterrows():
        param_str = " ".join(f"{r[p]:>8}" for p in param_names)
        print(f"{i:<4} {param_str} {r['total_return']:>+9.1f} {r['cagr']:>+7.1f} "
              f"{r['sharpe']:>7.3f} {r['max_dd']:>8.1f} {int(r['trades']):>7,}")

    best = df_opt.iloc[0]
    print(f"\n🥇 BEST: " + ", ".join(f"{p}={best[p]}" for p in param_names))
    print(f"   Return: {best['total_return']:+.1f}% | CAGR: {best['cagr']:+.1f}% | Sharpe: {best['sharpe']:.3f} | MaxDD: {best['max_dd']:.1f}%")

    df_opt.to_csv(RESULTS_DIR / f"15m_optimize_{winner_name.replace('/', '_').replace(' ', '_')}.csv")

    # Best Equity Chart
    if "EMA" in winner_name:
        ef_val = int(best[param_names[0]]); es_val = int(best[param_names[1]])
        ema_f  = ta.ema(close, ef_val); ema_s = ta.ema(close, es_val)
        if len(param_names) == 4:
            rl, rs = int(best[param_names[2]]), int(best[param_names[3]])
            ls = crossover(ema_f, ema_s) & (rsi_series < rl)
            ss = crossunder(ema_f, ema_s) & (rsi_series > rs) & ~is_bull
        else:
            ls = crossover(ema_f, ema_s); ss = crossunder(ema_f, ema_s) & ~is_bull
        best_pos = build_pos_ls_filter(ls, ss, is_bull)
    else:
        best_pos = build_combo(*[best[p] for p in param_names])

    best_res = fast_backtest(close_pct, best_pos)
    bh_eq    = (1 + close_pct).cumprod() * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                    gridspec_kw={"height_ratios": [3, 1]}, facecolor="#0f1117")
    best_params_str = ", ".join(f"{p}={best[p]}" for p in param_names)
    fig.suptitle(f"🏆 15m Best: {winner_name} | {best_params_str}", color="#e6edf3", fontsize=11)

    ax1.plot(best_res["equity"].index, best_res["equity"].values, color="#3fb950", linewidth=1.5,
             label=f"Optimized Strategy")
    ax1.plot(bh_eq.index, bh_eq.values, color="white", linewidth=1.2, linestyle="--",
             alpha=0.5, label="Buy & Hold")
    ax1.axhline(100, color="#30363d", linewidth=0.8, linestyle=":")

    stats = (f"Total Return : {best_res['total_return']:+.1f}%\n"
             f"CAGR         : {best_res['cagr']:+.1f}%\n"
             f"Sharpe       : {best_res['sharpe']:.3f}\n"
             f"Sortino      : {best_res['sortino']:.3f}\n"
             f"Max DD       : {best_res['max_dd']:.1f}%\n"
             f"Win Rate     : {best_res['win_rate']:.1f}%\n"
             f"Trades       : {best_res['trades']:,}")
    ax1.text(0.01, 0.97, stats, transform=ax1.transAxes, fontsize=9,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(facecolor="#161b22", edgecolor="#3fb950", alpha=0.9))
    ax1.set_ylabel("Portfolio Value (%)", color="#c9d1d9")
    ax1.legend(loc="upper left")
    plt.setp(ax1.get_xticklabels(), visible=False)

    rolling_max = best_res["equity"].cummax()
    dd = (best_res["equity"] - rolling_max) / rolling_max * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#f85149", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#c9d1d9")

    plt.tight_layout()
    p = RESULTS_DIR / f"15m_best_equity.png"
    fig.savefig(p, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"\n✅ Best Equity Chart: {p}")
    return df_opt

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("📥 โหลดข้อมูล 15m 6Y")
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    print(f"✅ {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")

    close_pct  = df["close"].pct_change().fillna(0)
    bh_return  = (1 + close_pct).cumprod().iloc[-1] * 100 - 100
    is_bull    = compute_macro(df)
    bull_pct   = is_bull.mean() * 100
    print(f"🔍 Macro Filter: Bull {bull_pct:.1f}% | Bear {100-bull_pct:.1f}%")
    print(f"⭐ Buy & Hold (6Y): +{bh_return:.1f}%")

    winner, df_indicators = run_indicator_comparison(df, is_bull, close_pct, bh_return)
    df_opt = optimize_strategy(df, is_bull, close_pct, winner)

    print("\n" + "=" * 65)
    print("🎉 15m Full Backtest + Optimization เสร็จแล้ว!")
    print("=" * 65)

if __name__ == "__main__":
    main()
