"""
signal_bot.py — BTC/USDT EMA25/100 Strategy Signal Bot
════════════════════════════════════════════════════════
ดึงข้อมูล Binance ทุกชั่วโมง คำนวณ Signal แจ้งเตือนผ่าน Telegram
เมื่อ Signal เปลี่ยนเท่านั้น (ไม่ส่งซ้ำ)

วิธีใช้:
  python3 signal/signal_bot.py              # รันครั้งเดียว
  python3 signal/signal_bot.py --test       # ทดสอบส่ง Telegram
  python3 signal/signal_bot.py --status     # ดู Signal ปัจจุบัน ไม่ส่ง

Cron Job (รันทุกชั่วโมง ที่นาทีที่ 5 หลัง Candle ปิด):
  5 * * * * /usr/bin/python3 /path/to/signal/signal_bot.py >> /path/to/signal/signal_bot.log 2>&1
"""

import sys
import json
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import ccxt
import pandas as pd
import numpy as np
import pandas_ta as ta
import requests

# ── Load Config ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    EXCHANGE, SYMBOL, TIMEFRAME, FETCH_LIMIT,
    EMA_FAST, EMA_SLOW, EMA_MACRO_D,
    RSI_PERIOD, RSI_LONG_MAX, RSI_SHORT_MIN,
    STATE_FILE, LOG_FILE
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ── Fetch Data ────────────────────────────────────────────────────────────────
def fetch_data() -> pd.DataFrame:
    """ดึง OHLCV 1H จาก Binance และคำนวณ Indicators ทั้งหมด"""
    log.info(f"📥 Fetching {FETCH_LIMIT} candles of {SYMBOL} {TIMEFRAME} from {EXCHANGE}...")
    exchange = getattr(ccxt, EXCHANGE)({"enableRateLimit": True})
    ohlcv    = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=FETCH_LIMIT)

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()

    # EMA Fast/Slow (1H)
    df["ema_fast"] = ta.ema(df["close"], EMA_FAST)
    df["ema_slow"] = ta.ema(df["close"], EMA_SLOW)

    # RSI
    df["rsi"] = ta.rsi(df["close"], RSI_PERIOD)

    # Macro Filter: Daily EMA200
    daily     = df["close"].resample("1D").last().dropna()
    ema200d   = daily.ewm(span=EMA_MACRO_D, adjust=False).mean()
    df["ema200d"]  = ema200d.reindex(df.index, method="ffill")
    df["is_bull"]  = df["close"] > df["ema200d"]

    df = df.dropna()
    log.info(f"✅ Data ready: {len(df)} candles | {df.index[-1].strftime('%Y-%m-%d %H:%M')} UTC")
    return df

# ── Compute Signal ────────────────────────────────────────────────────────────
def get_current_signal(df: pd.DataFrame) -> dict:
    """คำนวณ Signal ปัจจุบัน และ Position ล่าสุด"""
    close    = df["close"]
    ema_f    = df["ema_fast"]
    ema_s    = df["ema_slow"]
    rsi      = df["rsi"]
    is_bull  = df["is_bull"]

    # Crossover / Crossunder
    long_sig  = (ema_f > ema_s) & (ema_f.shift(1) <= ema_s.shift(1)) & (rsi < RSI_LONG_MAX)
    short_sig = (ema_f < ema_s) & (ema_f.shift(1) >= ema_s.shift(1)) & (rsi > RSI_SHORT_MIN) & ~is_bull

    # ไล่หา Current Position จาก Signal ล่าสุด (Reversal ล้วน ไม่มี FLAT)
    position   = "FLAT"
    signal_bar = None
    for i in range(len(df)):
        if long_sig.iloc[i]:
            position   = "LONG"
            signal_bar = i
        elif short_sig.iloc[i]:
            position   = "SHORT"
            signal_bar = i

    # ข้อมูล Candle ล่าสุด
    last     = df.iloc[-1]
    sig_time = df.index[signal_bar].strftime("%Y-%m-%d %H:%M UTC") if signal_bar else "N/A"

    # Signal ใน Candle ล่าสุด (เพิ่งเกิด?)
    new_long  = bool(long_sig.iloc[-1])
    new_short = bool(short_sig.iloc[-1])
    new_flat  = False
    signal_changed = new_long or new_short

    return {
        "position":       position,
        "signal_changed": signal_changed,
        "new_long":       new_long,
        "new_short":      new_short,
        "new_flat":       new_flat,
        "price":          round(float(last["close"]), 2),
        "ema_fast":       round(float(last["ema_fast"]), 2),
        "ema_slow":       round(float(last["ema_slow"]), 2),
        "ema200d":        round(float(last["ema200d"]), 2),
        "rsi":            round(float(last["rsi"]), 1),
        "is_bull":        bool(last["is_bull"]),
        "last_signal_at": sig_time,
        "checked_at":     datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M (UTC+7)"),
        "candle_time":    df.index[-1].strftime("%Y-%m-%d %H:%M UTC"),
    }

# ── State Management ──────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"position": None, "last_alert_at": None}

def save_state(signal: dict):
    state = {
        "position":      signal["position"],
        "last_alert_at": signal["checked_at"],
        "price_at_signal": signal["price"],
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ── Format Message ────────────────────────────────────────────────────────────
def format_message(signal: dict) -> str:
    pos = signal["position"]

    if pos == "LONG":
        header = "🚀 BUY Signal — LONG"
        emoji  = "🟢"
    elif pos == "SHORT":
        header = "⬇️ SELL Signal — SHORT"
        emoji  = "🔴"
    else:
        header = "✕ EXIT — FLAT (No Position)"
        emoji  = "⬜"

    macro_str = "🌕 BULL (Long only)" if signal["is_bull"] else "🐻 BEAR (Long + Short)"
    sep = "━" * 20

    msg = f"""⚡ *BTC/USDT Signal Alert*
{sep}
{emoji} *Signal: {pos}*
💰 Price: `${signal['price']:,.2f}`
📊 RSI(14): `{signal['rsi']}`
📈 EMA25: `${signal['ema_fast']:,.0f}`
📉 EMA100: `${signal['ema_slow']:,.0f}`
📅 EMA200D: `${signal['ema200d']:,.0f}`
🌍 Macro: {macro_str}
{sep}
🕐 Candle: `{signal['candle_time']}`
⏰ Alert: `{signal['checked_at']}`
{sep}
⚡ _EMA{EMA_FAST}/{EMA_SLOW} + RSI<{RSI_LONG_MAX}/>{RSI_SHORT_MIN} + Macro Filter_"""

    return msg

def format_status_message(signal: dict, state: dict) -> str:
    """Status message เมื่อไม่มี Signal เปลี่ยน"""
    pos       = signal["position"]
    prev_pos  = state.get("position", "Unknown")
    pos_emoji = "🟢" if pos == "LONG" else "🔴" if pos == "SHORT" else "⬜"
    macro_str = "🌕 BULL" if signal["is_bull"] else "🐻 BEAR"

    return f"""📊 *BTC/USDT Status Check*
━━━━━━━━━━━━━━━━━━━━
{pos_emoji} Position: *{pos}* (ไม่มีการเปลี่ยนแปลง)
💰 Price: `${signal['price']:,.2f}`
📊 RSI(14): `{signal['rsi']}`
🌍 Macro: {macro_str}
📌 Signal since: `{signal['last_signal_at']}`
⏰ Checked: `{signal['checked_at']}`"""

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """ส่ง Message ผ่าน Telegram Bot"""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.warning("⚠️  Telegram ยังไม่ได้ตั้งค่า — ดู config.py")
        print(f"\n{'='*50}\n{message}\n{'='*50}")
        return False

    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": parse_mode,
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            log.info("✅ Telegram sent successfully")
            return True
        else:
            log.error(f"❌ Telegram error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log.error(f"❌ Telegram exception: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BTC Signal Bot")
    parser.add_argument("--test",   action="store_true", help="ทดสอบส่ง Telegram")
    parser.add_argument("--status", action="store_true", help="ดู Status ไม่ส่ง Alert")
    parser.add_argument("--force",  action="store_true", help="ส่ง Alert แม้ Signal ไม่เปลี่ยน")
    args = parser.parse_args()

    log.info("=" * 55)
    log.info("🤖 BTC/USDT Signal Bot Starting...")
    log.info("=" * 55)

    # Fetch & Compute
    df     = fetch_data()
    signal = get_current_signal(df)
    state  = load_state()

    prev_pos = state.get("position")
    curr_pos = signal["position"]

    log.info(f"📍 Current: {curr_pos} | Previous: {prev_pos} | Signal Changed: {signal['signal_changed']}")
    log.info(f"   Price: ${signal['price']:,.2f} | RSI: {signal['rsi']} | Macro: {'BULL' if signal['is_bull'] else 'BEAR'}")

    # ─── Test Mode ───────────────────────────────────────────────────────────
    if args.test:
        log.info("🧪 TEST MODE — ส่ง Test Message")
        msg = f"✅ *Signal Bot ทำงานปกติ!*\n\nCurrent: *{curr_pos}*\nPrice: `${signal['price']:,.2f}`\n\n_{signal['checked_at']}_"
        send_telegram(msg)
        return

    # ─── Status Mode ─────────────────────────────────────────────────────────
    if args.status:
        log.info("📊 STATUS MODE — แสดงสถานะปัจจุบัน")
        msg = format_status_message(signal, state)
        print(f"\n{msg}\n")
        return

    # ─── Alert Logic ─────────────────────────────────────────────────────────
    should_alert = (
        args.force or
        signal["signal_changed"] or     # Signal เกิดใน Candle นี้
        (curr_pos != prev_pos)           # Position เปลี่ยนจากครั้งที่แล้ว
    )

    if should_alert:
        log.info(f"🚨 Signal {'CHANGED' if curr_pos != prev_pos else 'DETECTED'}: {prev_pos} → {curr_pos}")
        msg = format_message(signal)
        sent = send_telegram(msg)
        if sent:
            save_state(signal)
    else:
        log.info(f"ℹ️  No signal change. Current position: {curr_pos}")

    log.info("✅ Bot finished.")

if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════════
# SETUP GUIDE
# ══════════════════════════════════════════════════════════════════════════════
#
# 1. แก้ไข config.py:
#    TELEGRAM_BOT_TOKEN = "token จาก @BotFather"
#    TELEGRAM_CHAT_ID   = "chat_id จาก @userinfobot"
#
# 2. ทดสอบ:
#    python3 signal/signal_bot.py --test
#
# 3. ดู Status:
#    python3 signal/signal_bot.py --status
#
# 4. ตั้ง Cron Job (Mac/Linux):
#    crontab -e
#    เพิ่มบรรทัด:
#    5 * * * * /usr/bin/python3 /Users/chz/Desktop/AI\ Agent/Trader_Agent/signal/signal_bot.py
#
#    (รันทุกชั่วโมง ที่นาทีที่ 5 หลัง Candle 1H ปิด)
#
# ══════════════════════════════════════════════════════════════════════════════
