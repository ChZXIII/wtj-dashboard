# 🏗️ GHN168 — System Architecture & Code Map (ARCHITECTURE.md)

เอกสารสถาปัตยกรรมระบบ โครงสร้างโค้ด และการเชื่อมต่อทั้งหมดของ บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด

---

## 1. 📂 แผนผังโค้ดและโมดูลสำคัญ (Code Map)

```
GHN168/
├── GEMINI.md                     # Startup Rules & Pointer Directory (Lean)
├── ARCHITECTURE.md               # [ไฟล์นี้] พิมพ์เขียวสถาปัตยกรรมระบบ & Endpoints
├── TAX_SCHEDULE.md               # ปฏิทินภาษี & ตารางทวงบิล 4 บอส
├── ROADMAP.md                    # สถานะโปรเจกต์ & Roadmap การพัฒนา
├── document_template_engine.py   # Engine สร้าง HTML เอกสาร 4 ประเภท + Thai Baht Text
├── ghn168_sync_service.py        # Service เชื่อมต่อ GAS Webhook, Drive & Google Sheets
├── line_bot_server.py            # FastAPI Webhook Server (Gemini 2.5 Flash, Vision OCR, Tax Scheduler)
├── google_sheets_sync_script.gs  # Google Apps Script กลางสำหรับรับ Webhook & Sync
├── start_line_bot.sh             # Bash Script สำหรับรันเซิร์ฟเวอร์ LINE Bot
├── index.html                    # PWA Web App ระบบบัญชี & Dashboard
├── app.js                        # สคริปต์หน้าเว็บสำหรับการคำนวณภาษีและจัดการแท็บ
├── signature_pad.html            # กระดานเซ็นชื่อดิจิทัล (Digital Signature Pad)
└── tests/
    ├── test_full_option_features.py  # ทดสอบ Tax Scheduler, Vision OCR, Search, Live Sheets
    ├── test_pdf_generation_flow.py   # ทดสอบ End-to-End PDF & Template Engine
    └── test_line_bot.py              # ทดสอบ LINE Bot Health Check & HMAC Security
```

---

## 2. 🔌 รายละเอียดระบบและ Endpoints

### A. ระบบสร้างเอกสาร & ซิงค์อัตโนมัติ (Document & Sync Engine - v2.5 Full-Option)
* `document_template_engine.py`:
  * เทมเพลต HTML/CSS เอกสาร 4 ประเภท: ใบเสนอราคา (QT), ใบวางบิล/แจ้งหนี้ (IV), ใบเสร็จ/ใบกำกับภาษี (RE), 50 ทวิ (WHT)
  * ฟังก์ชันสะกดตัวเลขภาษาไทย `thai_baht_text()` แม่นยำ 100%
  * ฝัง Base64 Assets (โลโก้, ตรายางบริษัท, ลายเซ็นคุณเก่ง) แบบ Standalone
* `ghn168_sync_service.py`:
  * `upload_document_html`: แปลง HTML เป็น PDF ผ่าน PDFShift และเซฟลง Drive แยกโฟลเดอร์ (`01_Quotation`, `02_Invoice`, `03_Receipt`, `04_WHT_Certificates`) คืนค่า `pdfUrl`
  * `sync_document_to_sheets`: ซิงค์แถวข้อมูล 22-25 คอลัมน์ลงแท็บ Google Sheets (`ใบเสนอราคา`, `ใบวางบิล`, `รายรับ`, `รายจ่าย`)
  * `read_sheet_data`: อ่านข้อมูลสดจากแท็บชีต
  * `get_live_accounting_summary`: คำนวณรายรับ, รายจ่าย, Cashflow สุทธิ, VAT ซื้อ/ขาย, ยอดค้างชำระ
  * `record_scanned_expense`: บันทึกบิล/ใบเสร็จจาก Vision AI ลงแท็บ `รายจ่าย`

### B. เลขา GHN168 LINE Bot Assistant (FastAPI Backend)
* `line_bot_server.py` (รันด้วย Gemini 2.5 Flash):
  * **📸 Vision AI OCR:** ดาวน์โหลดรูปภาพจาก LINE API -> Gemini Vision สกัดยอด/VAT/เลขผู้เสียภาษี -> ส่ง LINE Flex Message รอคำสั่งยืนยันลงแท็บ `รายจ่าย` (Endpoint: `POST /api/scan_receipt`)
  * **📅 Proactive Tax Scheduler:** ระบบทวงบิลและเตือนภาษีอัตโนมัติ (Endpoint: `POST /api/tax_reminders/trigger`, `GET /api/tax_reminders/status`)
  * **🌐 Google Search Grounding:** ค้นหาราคากล้อง/อุปกรณ์/ข้อมูล DBD ผ่าน `google_search`
  * **📊 Live Sheets Insights:** สรุปยอดบัญชีสดส่งเข้า LINE (Endpoint: `GET /api/accounting/summary`)

---

## 3. 🧪 ชุดทดสอบ & คุณภาพ (Testing Suite)
* `test_full_option_features.py`: 19 Test Cases (100% Pass)
* `test_pdf_generation_flow.py`: 21 Test Cases (100% Pass)
* `test_line_bot.py`: HMAC-SHA256 & Webhook Health Check (100% Pass)
