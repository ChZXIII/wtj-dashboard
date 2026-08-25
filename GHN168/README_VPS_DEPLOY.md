# 🚀 GHN168 LINE Bot (เลขาเฟิส) - คู่มือการติดตั้งบน Hostinger VPS 24/7

คู่มือนี้สำหรับติดตั้งและเปิดรันระบบ **GHN168 LINE Assistant Bot (เลขาเฟิส)** บนเซิร์ฟเวอร์ **Hostinger VPS (Ubuntu 24.04 LTS)** อัตโนมัติ 100% ภายใน 1 คำสั่ง!

---

## 📋 ข้อมูลเซิร์ฟเวอร์ & สภาพแวดล้อม (Target Server)

| รายการ | รายละเอียด |
| :--- | :--- |
| **Domain / Hostname** | `srv1913532.hstgr.cloud` |
| **Server IP** | `187.127.118.19` |
| **Operating System** | Ubuntu 24.04 LTS (Noble Numbat) |
| **Application Path** | `/opt/ghn168_bot` |
| **Python Virtualenv** | `/opt/ghn168_bot/venv` |
| **Systemd Service** | `ghn168-bot.service` (Auto-restart 24/7) |
| **Web Server & SSL** | Caddy (Automatic HTTPS SSL via Let's Encrypt) |
| **Internal Port** | `8000` (FastAPI / Uvicorn) |
| **Public LINE Webhook URL** | `https://srv1913532.hstgr.cloud/callback` |

---

## ⚡ วิธีที่ 1: รัน Single Command บน Browser Terminal

เปิด **Hostinger Browser Terminal** หรือ SSH เข้าสู่เซิร์ฟเวอร์ในฐานะ `root` แล้วคัดลอกคำสั่งด้านล่างไปวางแล้วกด **Enter**:

*(คัดลอกคำสั่ง One-liner จากไฟล์ `vps_installer_oneliner.sh` หรือรันคำสั่งด้านล่าง)*

```bash
bash /path/to/vps_installer.sh
```

---

## 🛠️ สิ่งที่สคริปต์ `vps_installer.sh` จัดการให้อัตโนมัติ:

1. **ติดตั้ง System Dependencies**: `python3`, `python3-venv`, `python3-pip`, `curl`, `tar`, `gzip`, `caddy`, `ufw`
2. **สร้างโฟลเดอร์ระบบ**: `/opt/ghn168_bot` พร้อมโฟลเดอร์ `assets`, `signatures`, `logs`
3. **แตกไฟล์โค้ด & คอนฟิก**:
   - `line_bot_server.py`
   - `ghn168_sync_service.py`
   - `document_template_engine.py`
   - `.env` (พร้อม Environment Variables ทั้งหมด)
   - Asset โลโก้บริษัท ตราประทับ และ ลายเซ็นดิจิทัลครบชุด
4. **สร้างและติดตั้ง Python venv**:
   - `fastapi`, `uvicorn`, `requests`, `google-genai`, `python-dotenv`, `certifi`
5. **สร้าง Systemd Service 24/7**: `/etc/systemd/system/ghn168-bot.service`
6. **ตั้งค่า Reverse Proxy & Automatic SSL**:
   - Caddy reverse proxy ชี้ `srv1913532.hstgr.cloud` ไปยัง `127.0.0.1:8000`
   - รองรับ HTTPS อัตโนมัติสำหรับ LINE Webhook
7. **ตั้งค่า Firewall & Health Verification**:
   - เปิดพอร์ต `80`, `443`, `8000`, `22`
   - ตรวจสอบความพร้อมของ Service ทันทีหลังติดตั้งเสร็จ

---

## 🌐 ตรวจสอบ Endpoints หลังติดตั้งเสร็จ

- **LINE Webhook URL:** `https://srv1913532.hstgr.cloud/callback`
- **LINE Alt Webhook URL:** `https://srv1913532.hstgr.cloud/webhook`
- **FastAPI Interactive Docs (Swagger):** `https://srv1913532.hstgr.cloud/docs`
- **Health Check Endpoint:** `https://srv1913532.hstgr.cloud/health`

---

## ⚙️ คำสั่งจัดการระบบประจำวัน (Operations & Monitoring)

```bash
# ตรวจสอบสถานะการทำงานของ Bot
systemctl status ghn168-bot

# ดู Log สดแบบ Real-time
journalctl -u ghn168-bot -f

# สั่ง Restart บอท
systemctl restart ghn168-bot

# ดูสถานะ Caddy Web Server & SSL
systemctl status caddy

# แก้ไข Environment Variables (.env)
nano /opt/ghn168_bot/.env && systemctl restart ghn168-bot
```
