"""
run_kraken_longterm.py
ดึงข้อมูล BTC/USD จาก Kraken (ย้อนหลังสูงสุดที่มี ~13 ปี)
แล้ว Backtest EMA25/100 + RSI<60/>35 + Macro Filter
พร้อม Baseline ที่ถูกต้อง (Futures 1x/100%)

Usage:
    python backtest/run_kraken_longterm.py
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

DATA_DIR    = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
FEE_RATE    = 0.0004    # Futures Taker 0.04%
FUNDING_RATE  = 0.0001  # 0.01% ทุก 8 ชั่วโมง
FUNDING_EVERY = 8
MAINT_MARGIN  = 0.004   # 0.4%

EMA_FAST, EMA_SLOW, RSI_LONG, RSI_SHORT = 25, 100, 60, 35

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#1a1d2e",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#c9d1d9",
    "ytick.color": "#c9d1d9", "text.color": "#c9d1d9",
    "grid.color": "#30363d", "legend.facecolor": "#161b22",
    "legend.edgecolor": "#30363d",
})

# ─── Fetch Data ───────────────────────────────────────────────────────────────

def fetch_bitfinex_max(symbol="BTC/USD", timeframe="1h"):
    cache_path = DATA_DIR / "bitfinex_btc_1h_max.csv"
    if cache_path.exists():
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        print(f"  ✅ Cache: {len(df):,} candles | {df.index[0].date()} → {df.index[-1].date()}")
        return df

    from datetime import datetime, timezone
    exchange = ccxt.bitfinex({"enableRateLimit": True})
    print(f"  ⏳ ดึง Bitfinex {symbol} {timeframe} ย้อนหลังตั้งแต่ปี 2014 ...", end="", flush=True)

    since_ts  = exchange.parse8601("2014-01-01T00:00:00Z")
    end_ts    = int(datetime.now(timezone.utc).timestamp() * 1000)
    all_ohlcv = []
    batch     = 0

    while since_ts < end_ts:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since_ts, limit=1000)
        except Exception as e:
            print(f"\n  ⚠️ Error: {e}")
            time.sleep(5)
            continue

        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        batch += 1
        if batch % 20 == 0:
            print(f" {len(all_ohlcv):,}", end="", flush=True)
        if len(ohlcv) < 1000:
            break
        since_ts = ohlcv[-1][0] + 1
        time.sleep(2)  # Bitfinex rate limit

    df = pd.DataFrame(all_ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.to_csv(cache_path)
    print(f" ✅ {len(df):,} candles ({df.index[0].date()} → {df.index[-1].date()})")    
    return df

# ─── Signals ─────────────────────────────────────────────────────────────────

def crossover(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def crossunder(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

def compute_macro(df):
    daily   = df["close"].resample("1D").last().dropna()
    ema200d = daily.ewm(span=200, adjust=False).mean()
    return df["close"] > ema200d.reindex(df.index, method="ffill")

def build_positions(df):
    close     = df["close"]
    is_bull   = compute_macro(df)
    ema_fast  = ta.ema(close, EMA_FAST)
    ema_slow  = ta.ema(close, EMA_SLOW)
    rsi       = ta.rsi(close, 14)
    long_sig  = crossover(ema_fast, ema_slow) & (rsi < RSI_LONG)
    short_sig = crossunder(ema_fast, ema_slow) & (rsi > RSI_SHORT) & ~is_bull

    pos = np.zeros(len(close), dtype=np.int8)
    ls  = long_sig.fillna(False).values.astype(bool)
    ss  = short_sig.fillna(False).values.astype(bool)
    cur = 0
    for i in range(len(pos)):
        if ls[i]:   cur = 1
        elif ss[i]: cur = -1
        pos[i] = cur
    return pos, is_bull

# ─── Simulate Futures ─────────────────────────────────────────────────────────

def simulate(df, positions, leverage, margin_pct):
    close_arr = df["close"].values.astype(np.float64)
    high_arr  = df["high"].values.astype(np.float64)
    low_arr   = df["low"].values.astype(np.float64)
    n         = len(close_arr)
    liq_pct   = (1 / leverage) * (1 - MAINT_MARGIN)

    equity, portfolio = np.zeros(n), 100.0
    entry_price, cur_pos, num_liq = 0.0, 0, 0

    for i in range(n):
        sig = positions[i]
        if cur_pos != 0:
            if cur_pos == 1:
                hit_liq = low_arr[i] <= entry_price * (1 - liq_pct)
            else:
                hit_liq = high_arr[i] >= entry_price * (1 + liq_pct)

            if hit_liq:
                portfolio -= portfolio * margin_pct
                num_liq += 1; cur_pos = 0; entry_price = 0.0
            else:
                pct_chg  = (close_arr[i] - close_arr[i-1]) / close_arr[i-1] if i > 0 else 0
                notional = portfolio * margin_pct * leverage
                portfolio += notional * pct_chg * cur_pos
                if i % FUNDING_EVERY == 0:
                    portfolio -= notional * FUNDING_RATE
                if sig != cur_pos:
                    portfolio -= notional * FEE_RATE
                    if sig != 0:
                        portfolio -= portfolio * margin_pct * leverage * FEE_RATE
                        entry_price = close_arr[i]; cur_pos = sig
                    else:
                        cur_pos = 0; entry_price = 0.0
        else:
            if sig != 0:
                portfolio -= portfolio * margin_pct * leverage * FEE_RATE
                entry_price = close_arr[i]; cur_pos = sig

        equity[i] = max(portfolio, 0)

    eq = pd.Series(equity, index=df.index)
    cp = df["close"].pct_change().fillna(0)
    bh = (1 + cp).cumprod() * 100

    years = len(df) / (365 * 24)
    ret   = eq.iloc[-1] - 100
    cagr  = ((eq.iloc[-1] / 100) ** (1 / years) - 1) * 100 if eq.iloc[-1] > 0 else -100
    pr    = eq.pct_change().fillna(0)
    std   = pr.std()
    sharpe = (pr.mean() / std) * np.sqrt(365 * 24) if std > 0 else 0
    dn    = pr[pr < 0]
    sortino = (pr.mean() / dn.std()) * np.sqrt(365 * 24) if len(dn) > 0 and dn.std() > 0 else 0
    rm    = eq.cummax()
    maxdd = ((eq - rm) / rm * 100).min()
    bh_ret = bh.iloc[-1] - 100

    return {
        "equity": eq, "bh_equity": bh,
        "total_return": round(ret, 1), "bh_return": round(bh_ret, 1),
        "cagr": round(cagr, 1), "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3), "max_dd": round(maxdd, 1),
        "num_liq": num_liq, "years": round(years, 1),
        "wiped": eq.iloc[-1] < 1,
    }

# ─── Plot ─────────────────────────────────────────────────────────────────────

def plot_results(df, results_dict, bh_eq, baseline_res):
    """
    Plot หลายๆ Combo พร้อม Baseline และ B&H
    results_dict = {label: (color, res)}
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(22, 11),
                                    gridspec_kw={"height_ratios": [3, 1]},
                                    facecolor="#0f1117")

    start_year = df.index[0].year
    end_year   = df.index[-1].year
    years      = baseline_res["years"]

    fig.suptitle(
        f"📊 BTC/USD Kraken 1H | {start_year}–{end_year} ({years:.1f}Y) | "
        f"EMA{EMA_FAST}/{EMA_SLOW} + RSI<{RSI_LONG}/>{RSI_SHORT} + Macro Filter",
        color="#e6edf3", fontsize=12, y=0.99
    )

    # Buy & Hold
    ax1.plot(bh_eq.index, bh_eq.values, color="#6e7681",
             linewidth=1.2, linestyle="--", alpha=0.7,
             label=f"Buy & Hold  | +{baseline_res['bh_return']:,.0f}%  | B&H")
    ax1.axhline(100, color="#30363d", linewidth=0.7, linestyle=":")

    # Baseline (1x / 100%)
    ax1.plot(baseline_res["equity"].index, baseline_res["equity"].values,
             color="#58a6ff", linewidth=1.8, linestyle="-.",
             label=f"📌 Baseline: 1x/100%  | +{baseline_res['total_return']:,.0f}%"
                   f"  | Sh:{baseline_res['sharpe']:.2f} | DD:{baseline_res['max_dd']:.0f}%")

    # Other combos
    for label, (color, res) in results_dict.items():
        if not res["wiped"]:
            liq_str = f" 💀{res['num_liq']}x" if res["num_liq"] > 0 else ""
            ax1.plot(res["equity"].index, res["equity"].values,
                     color=color, linewidth=1.4,
                     label=f"{label}  | +{res['total_return']:,.0f}%"
                           f"  | Sh:{res['sharpe']:.2f} | DD:{res['max_dd']:.0f}%{liq_str}")

    ax1.set_yscale("log")
    ax1.set_ylabel("Portfolio Value (%) — Log Scale", color="#c9d1d9")
    ax1.legend(loc="upper left", fontsize=8.5, framealpha=0.85)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # Drawdown ของ Baseline
    rm = baseline_res["equity"].cummax()
    dd = (baseline_res["equity"] - rm) / rm * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#58a6ff", alpha=0.4, label="Baseline DD")
    ax2.set_ylabel("Drawdown — Baseline (%)", color="#c9d1d9")
    ax2.set_xlabel("", color="#c9d1d9")

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    path = RESULTS_DIR / "kraken_longterm.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path


def plot_summary_table(all_rows, baseline_res, bh_res):
    """วาดตาราง Summary แบบสวยงาม"""
    fig, ax = plt.subplots(figsize=(16, 6), facecolor="#0f1117")
    ax.axis("off")

    headers = ["Combo", "Leverage", "Margin/Trade", "Return (%)", "CAGR (%/yr)", "Sharpe", "MaxDD (%)", "Liq (ครั้ง)"]
    rows_data = []

    # Baseline
    rows_data.append([
        "📌 Baseline (Futures 1x)",
        "1x", "100%",
        f"+{baseline_res['total_return']:,.0f}%",
        f"+{baseline_res['cagr']:.1f}%",
        f"{baseline_res['sharpe']:.3f}",
        f"{baseline_res['max_dd']:.1f}%",
        str(baseline_res["num_liq"]),
    ])

    # Buy & Hold
    rows_data.append([
        "📈 Buy & Hold",
        "—", "—",
        f"+{baseline_res['bh_return']:,.0f}%",
        f"+{bh_res:.1f}%",
        "—", "—", "—",
    ])

    for r in all_rows:
        if not r["wiped"]:
            liq = f"💀 {r['num_liq']}" if r["num_liq"] > 0 else "✅ 0"
            rows_data.append([
                r["label"],
                r["leverage_str"], r["margin_str"],
                f"+{r['total_return']:,.0f}%",
                f"+{r['cagr']:.1f}%",
                f"{r['sharpe']:.3f}",
                f"{r['max_dd']:.1f}%",
                liq,
            ])

    table = ax.table(
        cellText=rows_data,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2.0)

    for (row, col), cell in table.get_celld().items():
        cell.set_facecolor("#161b22")
        cell.set_edgecolor("#30363d")
        cell.set_text_props(color="#c9d1d9")
        if row == 0:
            cell.set_facecolor("#21262d")
            cell.set_text_props(color="#e6edf3", fontweight="bold")
        elif row == 1:  # Baseline
            cell.set_facecolor("#0d1117")
            cell.set_text_props(color="#58a6ff")
        elif row == 2:  # B&H
            cell.set_facecolor("#0d1117")
            cell.set_text_props(color="#6e7681")

    ax.set_title(
        f"📊 Summary — Kraken BTC/USD 1H | EMA{EMA_FAST}/{EMA_SLOW} Strategy",
        color="#e6edf3", fontsize=12, pad=20
    )
    plt.tight_layout()
    path = RESULTS_DIR / "kraken_summary_table.png"
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    return path

# ─── Main ─────────────────────────────────────────────────────────────────────

COMBOS = [
    # (label, leverage, margin_pct, color)
    ("📌 Baseline 1x/100%", 1, 1.00, "#58a6ff"),
    ("2x / 30% Margin",     2, 0.30, "#3fb950"),
    ("2x / 50% Margin",     2, 0.50, "#ffa657"),
    ("3x / 30% Margin",     3, 0.30, "#d2a8ff"),
    ("3x / 50% Margin",     3, 0.50, "#ff7b72"),
    ("2x / 100% Margin",    2, 1.00, "#f0e68c"),
]

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("📥 ดึงข้อมูล BTC/USD จาก Bitfinex (ย้อนหลังสูงสุด ~11 ปี ตั้งแต่ 2014)")
    print("=" * 65)
    df = fetch_bitfinex_max()

    years = len(df) / (365 * 24)
    print(f"\n📊 ข้อมูลที่ได้: {len(df):,} candles | {years:.1f} ปี")
    print(f"   ช่วงเวลา: {df.index[0].strftime('%b %Y')} → {df.index[-1].strftime('%b %Y')}")

    close_pct = df["close"].pct_change().fillna(0)
    bh_equity = (1 + close_pct).cumprod() * 100
    bh_return_total = bh_equity.iloc[-1] - 100
    bh_cagr = ((bh_equity.iloc[-1] / 100) ** (1 / years) - 1) * 100
    print(f"\n⭐ Buy & Hold: +{bh_return_total:,.0f}% | CAGR: +{bh_cagr:.1f}%/ปี")

    print("\n🔧 คำนวณ Signals ...")
    positions, is_bull = build_positions(df)
    bull_pct = is_bull.mean() * 100
    print(f"   Macro Filter: Bull {bull_pct:.1f}% | Bear {100-bull_pct:.1f}%")

    print("\n🚀 Backtest ทุก Combo ...")
    print("=" * 65)

    baseline_res = None
    results_dict = {}
    all_rows     = []

    for label, lev, margin, color in COMBOS:
        res = simulate(df, positions, lev, margin)
        liq_str = f"💀x{res['num_liq']}" if res["num_liq"] > 0 else "✅ 0 Liq"
        status  = "💀WIPED" if res["wiped"] else liq_str

        print(f"  {label:<22} | Exposure {int(lev*margin*100):>4}% "
              f"| Return: {res['total_return']:>+8,.0f}% "
              f"| Sharpe: {res['sharpe']:>5.3f} "
              f"| MaxDD: {res['max_dd']:>7.1f}% "
              f"| {status}")

        if lev == 1 and margin == 1.00:
            baseline_res = res

        results_dict[label] = (color, res)
        all_rows.append({
            "label": label,
            "leverage_str": f"{lev}x",
            "margin_str": f"{int(margin*100)}%",
            **{k: v for k, v in res.items() if k not in ("equity", "bh_equity")},
        })

    print("\n" + "=" * 65)
    print("📌 BASELINE (Futures 1x / 100% Margin — ถูกต้อง):")
    print(f"   Return  : +{baseline_res['total_return']:,.0f}%")
    print(f"   CAGR    : +{baseline_res['cagr']:.1f}%/ปี")
    print(f"   Sharpe  : {baseline_res['sharpe']:.3f}")
    print(f"   Max DD  : {baseline_res['max_dd']:.1f}%")
    print(f"   B&H     : +{baseline_res['bh_return']:,.0f}%")
    print(f"   Period  : {baseline_res['years']:.1f} ปี")

    print("\n📈 Plot กราฟ ...")
    p1 = plot_results(df, {k: v for k, v in results_dict.items() if k != "📌 Baseline 1x/100%"},
                      bh_equity, baseline_res)
    p2 = plot_summary_table(
        [r for r in all_rows if "Baseline" not in r["label"]],
        baseline_res, bh_cagr
    )
    print(f"✅ Equity Chart   : {p1}")
    print(f"✅ Summary Table  : {p2}")
    print("\n🎉 Kraken Long-term Backtest เสร็จ!")

if __name__ == "__main__":
    main()
