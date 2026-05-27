# 📡 BTC/USDT Signal Bot — Setup Guide

## ไฟล์ที่อยู่ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร |
|---|---|
| `ema_strategy_signal.pine` | Pine Script สำหรับ TradingView |
| `signal_bot.py` | Python bot ส่ง Telegram |
| `config.py` | ตั้งค่า Token + Parameters |
| `signal_state.json` | เก็บ Signal ล่าสุด (สร้างอัตโนมัติ) |
| `signal_bot.log` | Log การทำงาน (สร้างอัตโนมัติ) |

---

## 1️⃣ TradingView Pine Script

### วิธีใส่
1. เปิด [TradingView](https://tradingview.com) → Chart BTC/USDT 1H
2. คลิก **Pine Editor** (ด้านล่าง) → วางโค้ดจาก `ema_strategy_signal.pine`
3. กด **Add to chart**

### ตั้ง Alert
1. คลิกขวาที่ Chart → **Add Alert**
2. Condition → เลือก **EMA Signal** → เลือก Alert ที่ต้องการ
   - `🟢 BUY Signal` — เมื่อ EMA25 ตัด EMA100 ขึ้น + RSI < 60
   - `🔴 SELL Signal` — เมื่อ EMA25 ตัด EMA100 ลง + RSI > 35 + Bear
   - `⬜ EXIT Long` — เมื่อ Exit ใน Bull Market (ไม่ Short)
   - `⚡ Any Signal Change` — ทุก Signal เปลี่ยน

---

## 2️⃣ Python Telegram Bot

### ขั้นตอนที่ 1: รับ Telegram Bot Token
1. เปิด Telegram → ค้นหา **@BotFather**
2. ส่ง `/newbot` → ตั้งชื่อ Bot → ได้ Token มา
3. ใส่ Token ใน `config.py` → `TELEGRAM_BOT_TOKEN`

### ขั้นตอนที่ 2: รับ Chat ID
1. เปิด Telegram → ค้นหา **@userinfobot**
2. ส่งข้อความอะไรก็ได้ → มันตอบ Chat ID กลับมา
3. ใส่ใน `config.py` → `TELEGRAM_CHAT_ID`

### ขั้นตอนที่ 3: ทดสอบ
```bash
# ทดสอบส่ง Telegram
python3 signal/signal_bot.py --test

# ดู Signal ปัจจุบัน (ไม่ส่ง Alert)
python3 signal/signal_bot.py --status

# รันปกติ (ส่งเฉพาะเมื่อ Signal เปลี่ยน)
python3 signal/signal_bot.py

# บังคับส่งแม้ Signal ไม่เปลี่ยน
python3 signal/signal_bot.py --force
```

### ขั้นตอนที่ 4: ตั้ง Cron Job (รันอัตโนมัติทุกชั่วโมง)
```bash
# เปิด crontab
crontab -e

# เพิ่มบรรทัดนี้ (รันทุกชั่วโมง นาทีที่ 5 = หลัง Candle ปิด 5 นาที)
5 * * * * /usr/bin/python3 "/Users/chz/Desktop/AI Agent/Trader_Agent/signal/signal_bot.py" >> "/Users/chz/Desktop/AI Agent/Trader_Agent/signal/signal_bot.log" 2>&1
```

---

## 📱 ตัวอย่าง Telegram Message

```
⚡ BTC/USDT Signal Alert
━━━━━━━━━━━━━━━━━━━━
🟢 Signal: LONG
💰 Price: $95,420.00
📊 RSI(14): 52.3
📈 EMA25: $94,100
📉 EMA100: $91,500
📅 EMA200D: $85,200
🌍 Macro: 🌕 BULL (Long only)
━━━━━━━━━━━━━━━━━━━━
🕐 Candle: 2026-05-20 17:00 UTC
⏰ Alert: 2026-05-20 17:05 (UTC+7)
━━━━━━━━━━━━━━━━━━━━
⚡ EMA25/100 + RSI<60/>35 + Macro Filter
```

---

## ⚙️ Strategy Parameters (ใน config.py)

| Parameter | Value | ความหมาย |
|---|---|---|
| EMA_FAST | 25 | EMA เร็ว |
| EMA_SLOW | 100 | EMA ช้า |
| EMA_MACRO_D | 200 | EMA Daily Macro Filter |
| RSI_PERIOD | 14 | RSI period |
| RSI_LONG_MAX | 60 | Long ได้เฉพาะ RSI < 60 |
| RSI_SHORT_MIN | 35 | Short ได้เฉพาะ RSI > 35 |

---

*EMA25/100 + RSI + Macro Filter | Optimized on BTC/USDT 1H 6Y | Sharpe 1.437*
