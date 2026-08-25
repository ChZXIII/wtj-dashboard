# 🤖 เลขา GHN168 LINE Bot Assistant (GHN168 Corporate & Accounting Assistant)

ระบบเซิร์ฟเวอร์ LINE Bot สำหรับเลขาบริษัท GHN168 ประจำการบน LINE เพื่อดูแลงานเอกสาร คำนวณภาษี บัญชี-การเงิน ของ บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (GHN168 Media & Creation Co., Ltd.) แบบ Full-Option (v2.5) ขับเคลื่อนด้วย FastAPI + Google Gemini 2.5 Flash, Google Search Grounding, Vision OCR และ Google Sheets Live Insights

---

## 📁 ไฟล์สำคัญในระบบ

- [`line_bot_server.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/line_bot_server.py): เซิร์ฟเวอร์หลัก (FastAPI Webhook Server + Gemini AI Generation สำหรับ GHN168)
- [`ghn168_sync_service.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/ghn168_sync_service.py): โมดูลซิงค์เอกสารและอ่านข้อมูลสรุปบัญชีสดจาก Google Sheets
- [`document_template_engine.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/document_template_engine.py): เทมเพลตเอกสาร PDF 4 ประเภท (QT, IV, RE, WHT)
- [`.env`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/.env): ไฟล์เก็บ API Keys และ LINE Tokens
- [`test_full_option_features.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_full_option_features.py): ชุดทดสอบฟังก์ชัน Full-Option 4 ด้าน
- [`test_pdf_generation_flow.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_pdf_generation_flow.py): ชุดทดสอบการออกเอกสาร PDF & Sheets
- [`test_line_bot.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_line_bot.py): ชุดทดสอบพื้นฐาน LINE Bot
- [`start_line_bot.sh`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/start_line_bot.sh): สคริปต์รันเซิร์ฟเวอร์แบบง่าย

---

## ⚡ วิธีเปิดใช้งานระบบ (Step-by-Step)

### 1. เปิดเซิร์ฟเวอร์ LINE Bot
```bash
cd /Users/chz/Desktop/ChZ_Agent_Corp/GHN168
python3 line_bot_server.py
# หรือ
./start_line_bot.sh
```
เซิร์ฟเวอร์จะรันที่ `http://0.0.0.0:8000`

### 2. เปิด Webhook Tunnel (ส่งออก Public URL)
ใช้ **ngrok** (มีติดตั้งในเครื่องแล้วที่ `/opt/homebrew/bin/ngrok`):
```bash
ngrok http 8000
```
ระบบจะให้ Forwarding URL มา เช่น:
`https://xxxx-xx-xx-xx.ngrok-free.app`

### 3. นำ Webhook URL ไปตั้งค่าใน LINE Developers Console
1. เข้าไปที่ [LINE Developers Console](https://developers.line.biz/console/)
2. เลือก Messaging API Channel ของเลขา GHN168
3. ไปที่แท็บ **Messaging API**
4. ในส่วน **Webhook settings**:
   - **Webhook URL:** ใส่ URL ของคุณต่อท้ายด้วย `/webhook` เช่น:
     `https://xxxx-xx-xx-xx.ngrok-free.app/webhook`
   - กดปุ่ม **Update**
   - กดปุ่ม **Verify** (จะส่ง Ping มาทดสอบ และเซิร์ฟเวอร์จะตอบกลับ 200 OK)
   - เปิดสวิตช์ **Use webhook** เป็น **Enabled (สีเขียว)**

---

## 🎯 4 ฟังก์ชันใหญ่ระดับ Full-Option (GHN168 v2.5)

1. **📅 ระบบปฏิทินตั้งเตือนภาษี & ทวงบิลรายจ่ายอัตโนมัติ (Proactive Tax Scheduler):**
   - ทุกวันที่ 25 ของเดือน (10:00 น.): ทวงบิลค่าน้ำมัน, ค่าอาหารกองถ่าย, บิลซื้อของ, สลิปโอนเงิน (ช่วยบอสมด)
   - ทุกวันที่ 5 ของเดือน (10:00 น.): เตือนเดดไลน์ภาษีรายเดือน (ภ.พ.30, ภ.ง.ด.1/3/53)
   - ภ.ง.ด.94 (ภาษีครึ่งปีบุคคลธรรมดา 4 ท่าน): 1 ก.ย. และ 25 ก.ย.
   - ภ.ง.ด.90/91 (ภาษีประจำปีบุคคลธรรมดา 4 ท่าน): 15 ม.ค., 15 ก.พ., 25 มี.ค.
   - ภ.ง.ด.51 (ภาษีนิติบุคคลครึ่งปี): 1 ส.ค. และ 20 ส.ค.
   - ภ.ง.ด.50 (ภาษีนิติบุคคลประจำปี & ปิดงบ): 1 เม.ย. และ 10 พ.ค.

2. **📸 ระบบสายตา AI สแกนรูปภาพบิล & สลิป (Vision AI & Receipt OCR):**
   - รองรับ Event รูปภาพใน LINE Webhook (`message.type == "image"`)
   - ดาวน์โหลดและสกัดข้อมูลด้วย Gemini 2.5 Flash Vision
   - ส่ง LINE Flex Message Card พร้อมให้ยืนยันเพื่อบันทึกลง Google Sheets แท็บ `รายจ่าย` ทันที

3. **🌐 ระบบค้นหาข้อมูลสดจาก Google แบบเรียลไทม์ (Google Search Grounding):**
   - ค้นหาราคากล้อง/อุปกรณ์โปรดักชั่นล่าสุด, ข้อมูลบริษัทลูกค้าจาก DBD, ข่าวสารสรรพากร

4. **📊 ระบบสอบถามสรุปบัญชีสดจาก Google Sheets (Live Sheets Insights):**
   - รายรับรวม, รายจ่ายรวม, กระแสเงินสดสุทธิ (Net Cashflow), ภาษีซื้อ/ขาย (VAT Output/Input), และยอดค้างชำระในใบวางบิล

---

## 🧪 ทดสอบระบบผ่านคำสั่ง
```bash
# ทดสอบ 4 ฟังก์ชันใหญ่ระดับ Full-Option
python3 test_full_option_features.py

# ทดสอบการออกเอกสาร PDF & Sheets Sync
python3 test_pdf_generation_flow.py

# ทดสอบเซิร์ฟเวอร์ LINE Bot & ความปลอดภัย Signature
python3 test_line_bot.py
```
