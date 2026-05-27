# ── config.py ──────────────────────────────────────────────────────────────────
# แก้ไขค่าต่อไปนี้ก่อนใช้งาน
# วิธีรับ Token: https://t.me/BotFather → /newbot
# วิธีรับ Chat ID: https://t.me/userinfobot

from pathlib import Path

# ─── Telegram ───────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8842401881:AAFfoWSp2RqFte_kBrNFf-_Uzsy41ClNiiM"
TELEGRAM_CHAT_ID   = "8903809012"

# ─── Exchange / Symbol ───────────────────────────────────────────────────────
EXCHANGE   = "binance"
SYMBOL     = "BTC/USDT"
TIMEFRAME  = "1h"
FETCH_LIMIT = 500   # จำนวน candles ที่ดึงมาคำนวณ (ต้องมากพอสำหรับ EMA200D)

# ─── Strategy Parameters ─────────────────────────────────────────────────────
EMA_FAST      = 25
EMA_SLOW      = 100
EMA_MACRO_D   = 200   # EMA บน Daily TF
RSI_PERIOD    = 14
RSI_LONG_MAX  = 60    # Long ได้เฉพาะ RSI < 60
RSI_SHORT_MIN = 35    # Short ได้เฉพาะ RSI > 35

# ─── File Paths ───────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATE_FILE = BASE_DIR / "signal_state.json"   # เก็บ Signal ล่าสุดไว้ไม่ให้ส่งซ้ำ
LOG_FILE   = BASE_DIR / "signal_bot.log"
