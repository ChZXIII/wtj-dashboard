"""
TradingView Webhook Server
รับ Alert จาก TradingView แล้วส่งไป Telegram ทันที
"""

from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "8842401881:AAFfoWSp2RqFte_kBrNFf-_Uzsy41ClNiiM"
CHAT_ID   = "8903809012"
PORT      = 5050

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def format_signal(data: dict) -> str:
    """Format TradingView alert payload to Telegram message"""
    signal  = data.get("signal", "UNKNOWN")
    price   = data.get("price", "N/A")
    rsi     = data.get("rsi", "N/A")
    macro   = data.get("macro", "N/A")
    tf      = data.get("timeframe", "1H")
    symbol  = data.get("symbol", "BTCUSDT")
    ts      = datetime.now().strftime("%Y-%m-%d %H:%M")

    emoji = {"BUY": "🟢", "SELL": "🔴", "EXIT": "⬜", "SHORT": "🔴"}.get(signal, "⚡")

    return (
        f"{emoji} <b>{signal} Signal</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 <b>{symbol}</b> | {tf}\n"
        f"💰 Price: <code>${price}</code>\n"
        f"📈 RSI(14): <code>{rsi}</code>\n"
        f"🌍 Macro: <b>{macro}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🕐 {ts}"
    )

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    """รับ Alert จาก TradingView"""
    try:
        # TradingView ส่งมาเป็น JSON หรือ plain text
        if request.is_json:
            data = request.get_json()
        else:
            # Plain text — parse manually
            raw = request.data.decode("utf-8")
            try:
                data = json.loads(raw)
            except:
                # ถ้า parse ไม่ได้ ส่ง raw text ตรงๆ
                send_telegram(f"⚡ TradingView Alert:\n{raw}")
                return jsonify({"status": "ok", "mode": "raw"}), 200

        message = format_signal(data)
        success = send_telegram(message)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Signal: {data.get('signal')} | Telegram: {'OK' if success else 'FAIL'}")
        return jsonify({"status": "ok", "telegram": success}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "time": str(datetime.now())}), 200

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Webhook Server running on port {PORT}")
    print(f"Webhook URL: http://localhost:{PORT}/webhook")
    app.run(host="0.0.0.0", port=PORT, debug=False)
