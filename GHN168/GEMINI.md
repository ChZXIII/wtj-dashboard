# 🏢 GHN168 - Corporate & Workspace Context (GEMINI.md)

ยินดีต้อนรับสู่ Workspace ของ **บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด** เอกสารนี้สรุปบริบทองค์กร โครงสร้างระบบ สถาปัตยกรรมโค้ด และกฎการทำงานเพื่อให้เอเจนต์ในโปรเจกต์เข้าใจและเริ่มงานได้ทันที

---

## 1. 📌 ภาพรวมโปรเจกต์ & ข้อมูลนิติบุคคล (Corporate Profile)

### ข้อมูลบริษัท (Company Profile)
- **ชื่อบริษัท (ไทย):** บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด
- **ชื่อบริษัท (อังกฤษ):** GHN 168 MEDIA & CREATION COMPANY LIMITED
- **เลขประจำตัวผู้เสียภาษี:** `0505566010089` (สำนักงานใหญ่ สาขา 00000)
- **ที่อยู่จดทะเบียน:** 65/1 ถนนต้นขาม 2 ตำบลท่าศาลา อำเภอเมือง จังหวัดเชียงใหม่ 50000
- **เบอร์โทรศัพท์:** 089-554-4355
- **อีเมล:** `ghn168media@gmail.com`
- **บัญชีธนาคารหลัก:** ธนาคารกรุงไทย (KTB) เลขที่บัญชี **520-0-61960-2** (ชื่อบัญชี: บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น)

### สมาชิก หุ้นส่วน และผู้มีอำนาจลงนาม (Partners & Payees)
1. **บอสเก่ง (นาย มงคล วงศ์สกุลยานนท์)** - กรรมการผู้มีอำนาจลงนาม | เลขประจำตัว: `3509900218949` | อัตราหัก ณ ที่จ่าย 3%
2. **บอสหอม (นาย ณัฐวัฒน์ ปวงจันทร์หอม)** - หุ้นส่วน / ทีมงาน | เลขประจำตัว: `1509900596688` | อัตราหัก ณ ที่จ่าย 3%
3. **บอสนิค (นาย อนุชิต อภิชัย)** - หุ้นส่วน / ทีมงาน | เลขประจำตัว: `3630200045082` | อัตราหัก ณ ที่จ่าย 3%
4. **บอสมด (นาง ณัฐนรี วงศ์สกุลยานนท์)** - หุ้นส่วน / ทีมงาน | เลขประจำตัว: `1509900148537` | อัตราหัก ณ ที่จ่าย 3%

---

## 2. 📂 โครงสร้างระบบและไฟล์สำคัญ (System Architecture)

### A. ระบบสร้างเอกสาร & ซิงค์อัตโนมัติ (Document & Sync Engine - v2.5 Full-Option)
- [`document_template_engine.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/document_template_engine.py) - โมดูล HTML/CSS Template Engine สำหรับเอกสาร 4 ประเภท:
  * ใบเสนอราคา (Quotation - QT)
  * ใบวางบิล / ใบแจ้งหนี้ (Invoice / Billing Note - IV)
  * ใบเสร็จรับเงิน / ใบกำกับภาษี (Receipt / Tax Invoice - RE)
  * หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ - WHT Certificate)
  * ฟังก์ชันแปลงตัวเลขเป็นตัวสะกดภาษาไทยแม่นยำ 100% `thai_baht_text()`
  * ฝัง Base64 Assets (Logo, Company Seal, ลายเซ็นคุณเก่ง) แบบ Standalone
- [`ghn168_sync_service.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/ghn168_sync_service.py) - โมดูลเชื่อมต่อ Google Apps Script Webhook & Google Sheets:
  * `upload_document_html`: ส่ง HTML ไปแปลง PDF ผ่าน PDFShift และเซฟลง Drive แยกตามโฟลเดอร์ประเภทเอกสาร (`01_Quotation`, `02_Invoice`, `03_Receipt`, `04_WHT_Certificates`) และคืนค่า `pdfUrl`
  * `sync_document_to_sheets`: ซิงค์ข้อมูลแถว 22-25 คอลัมน์ลงแท็บชีต (`ใบเสนอราคา`, `ใบวางบิล`, `รายรับ`, `รายจ่าย`)
  * `read_sheet_data`: อ่านข้อมูลแถวทั้งหมดจากแท็บ Google Sheets แบบเรียลไทม์
  * `get_live_accounting_summary`: คำนวณยอดรายรับ, รายจ่าย, กระแสเงินสดสุทธิ, ภาษีซื้อ/ขาย (VAT Balance) และยอดค้างชำระในใบวางบิล
  * `record_scanned_expense`: บันทึกข้อมูลบิล/ใบเสร็จที่ได้จาก Vision AI ลงแท็บ `รายจ่าย`
  * `generate_and_sync_document`: Full Orchestration รวมการสร้างเอกสาร อัปโหลด Drive และซิงค์ Sheets
- [`google_sheets_sync_script.gs`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/google_sheets_sync_script.gs) - Google Apps Script กลางสำหรับรับ Webhook

### B. เลขา GHN168 LINE Bot Assistant (AI Backend - Full-Option v2.5)
- [`line_bot_server.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/line_bot_server.py) - FastAPI Webhook Server ขับเคลื่อนด้วย Google Gemini 2.5 Flash:
  * **📅 ระบบปฏิทินตั้งเตือนภาษี & ทวงบิลอัตโนมัติ (Proactive Tax Scheduler):**
    - ทุกวันที่ 25 ของเดือน (10:00 น.): ทวงบิลค่าน้ำมัน, ค่าอาหารกองถ่าย, บิลซื้อของ, สลิปโอนเงิน เพื่อปิดยอดบัญชีประจำเดือน (ช่วยบอสมด)
    - ทุกวันที่ 5 ของเดือน (10:00 น.): เตือนเดดไลน์ภาษีรายเดือน (ภ.พ.30, ภ.ง.ด.1, ภ.ง.ด.3, ภ.ง.ด.53)
    - 1 ก.ย. และ 25 ก.ย.: เตือนภาษีบุคคลธรรมดาครึ่งปี ภ.ง.ด.94 (4 หุ้นส่วน)
    - 15 ม.ค., 15 ก.พ., และ 25 มี.ค.: เตือนภาษีบุคคลธรรมดาประจำปี ภ.ง.ด.90/91 (4 หุ้นส่วน)
    - 1 ส.ค. และ 20 ส.ค.: เตือนภาษีนิติบุคคลครึ่งปี ภ.ง.ด.51 (บจ. GHN 168)
    - 1 เม.ย. และ 10 พ.ค.: เตือนภาษีนิติบุคคลประจำปี & ปิดงบการเงิน ภ.ง.ด.50 (บจ. GHN 168)
    - Endpoint: `POST /api/tax_reminders/trigger` และ `GET /api/tax_reminders/status`
  * **📸 ระบบสายตา AI สแกนบิลและสลิป (Vision AI & OCR):**
    - ดาวน์โหลด Binary ภาพจาก LINE Content API (`https://api-data.line.me/v2/bot/message/{message_id}/content`)
    - ส่งเข้า Gemini 2.5 Flash Vision สกัดชื่อร้าน, เลขผู้เสียภาษี, วันที่, ยอดก่อน VAT, VAT 7%, ยอดสุทธิ และหมวดหมู่
    - ส่งการ์ด LINE Flex Message และรอคำสั่ง "บันทึก" หรือ "ยืนยัน" เพื่อลงแท็บ `รายจ่าย` ใน Google Sheets
    - Endpoint: `POST /api/scan_receipt`
  * **🌐 ระบบค้นหาข้อมูลสดจาก Google (Google Search Grounding):**
    - เปิดใช้งาน `tools=[types.Tool(google_search=types.GoogleSearch())]` ใน google-genai Client สำหรับคำถามราคากล้อง, ข้อมูล DBD ลูกค้า, ข่าวสารภาษีอัปเดต
  * **📊 ระบบสอบถามสรุปบัญชีสดจาก Google Sheets (Live Sheets Insights):**
    - ดึงข้อมูลสดจาก Google Sheets วิเคราะห์รายรับ, รายจ่าย, กระแสเงินสดสุทธิ, VAT ขาย/ซื้อ, และใบวางบิลที่รอเก็บเงิน
    - ตอบกลับด้วย LINE Flex Message Card กราฟิกการเงินสวยงาม
    - Endpoint: `GET /api/accounting/summary`
- [`start_line_bot.sh`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/start_line_bot.sh) - สคริปต์ Bash สำหรับรันเซิร์ฟเวอร์ LINE Bot
- [`.env.example`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/.env.example) - เทมเพลต Environment Variables (`LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_NOTIFICATION_TARGET_ID`, `GEMINI_API_KEY`, `GAS_SCRIPT_URL`, `GHN168_SHEET_ID`, `COMPANY_DRIVE_FOLDER_ID`, `PDFSHIFT_API_KEY`)

### C. PWA Web App ระบบบัญชี (Static Web App)
- [`index.html`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/index.html) - หน้าแผงควบคุม Dashboard และฟอร์มสร้างเอกสารทางการเงิน
- [`app.js`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/app.js) - สคริปต์หน้าเว็บสำหรับการคำนวณภาษี บันทึกประวัติ และจัดการแท็บ
- [`signature_pad.html`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/signature_pad.html) - โมดูลรับและประมวลผลลายเซ็นดิจิทัล

### D. ชุดทดสอบและการประกันคุณภาพ (Testing & QA Suite)
- [`test_full_option_features.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_full_option_features.py) - ชุดทดสอบครอบคลุม 4 ฟังก์ชันใหญ่: Tax Scheduler, Vision AI OCR, Google Search Grounding, และ Live Sheets Insights (19 Test Cases, 100% Pass)
- [`test_pdf_generation_flow.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_pdf_generation_flow.py) - ชุดทดสอบ End-to-End ครอบคลุม Thai Baht Text, Template Engine 4 แบบ, Sync Service, LINE Flex Message และ FastAPI Endpoints (21 Test Cases, 100% Pass)
- [`test_line_bot.py`](file:///Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_line_bot.py) - ชุดทดสอบระบบ LINE Bot: Health Check, HMAC-SHA256, และการคำนวณ (100% Pass)

---

## 3. 🎯 กฎการทำงาน, Persona และความปลอดภัย (Operating Rules)

### Persona & Communication Tone (LINE Bot: เลขาเฟิส)
1. **สรรพนามและคำลงท้าย:**
   - แทนตัวเองว่า **"เฟิส"**
   - **เพศและคำลงท้าย:** เลขาเฟิสเป็นผู้หญิง ให้ใช้คำลงท้ายสุภาพว่า **"ค่ะ / คะ"** เสมอ (ห้ามใช้ "ครับ" เด็ดขาด)
   - **สมาชิกและหุ้นส่วนทั้ง 4 คน (เก่ง, หอม, นิค, มด):** ให้เลขาเฟิสใน LINE เรียกนำหน้าว่า **"บอส"** เสมอ เช่น:
     * บอสเก่ง
     * บอสหอม
     * บอสนิค
     * บอสมด
     *(ตัวอย่างประโยคตอบกลับ: "บอสหอมมีอะไรให้เฟิสช่วยคะ", "รับทราบค่ะบอสเก่ง", "เอกสารเรียบร้อยแล้วค่ะบอสนิค", "ยินดีค่ะบอสมด")*
   - **ลูกค้าภายนอก / ผู้ว่าจ้างทั่วไป:** ให้ยังคงเรียกนำหน้าว่า **"คุณ..."** อย่างสุภาพเช่นเดิม (เช่น คุณสมชาย, คุณลูกค้า)
   - **ข้อห้ามเด็ดขาด:** ห้ามเรียกสมาชิกว่า "แก" ในกลุ่มหรือในระบบ LINE Bot เพื่อรักษาภาพลักษณ์มืออาชีพของบริษัท
2. **ความแม่นยำทางบัญชีและภาษี 100%:**
   - ใบเสนอราคา (QT), ใบแจ้งหนี้/วางบิล (IV), ใบเสร็จรับเงิน (RE), หนังสือรับรองหัก ณ ที่จ่าย (50 ทวิ)
   - อัตราภาษี: VAT 7%, WHT บริการ/ฟรีแลนซ์ 3%, ค่าเช่า 5%, ค่าขนส่ง 1%, โฆษณา 2%
   - แปลงจำนวนเงินเป็นตัวอักษรภาษาไทยกำกับเสมอ (`thai_baht_text`)
3. **ระบบความปลอดภัยของเงินบริษัท (HITL Alert):**
   - หากมีการแจ้งหรือทำรายการเบิกจ่าย/โอนเงินออกเกิน **10,000 บาท** ต้องมีคำเตือนแจ้งเตือนให้ตรวจทานและยืนยันรายการเสมอ

### การแยกขอบเขตความเป็นส่วนตัว (Privacy Isolation & Boundary)
- ระบบและบอทในโปรเจกต์นี้ดูแล **เฉพาะงานและธุรกิจของ บจ. GHN168 เท่านั้น**
- **ไม่มีและไม่เก็บข้อมูลส่วนตัว** ครอบครัว หรือทรัพย์สินส่วนบุคคลในระบบนี้
- หากมีการสอบถามเรื่องส่วนตัวหรือเรื่องที่ไม่เกี่ยวกับงาน GHN168 ให้ปฏิเสธอย่างสุภาพ และแนะนำให้ย้ายไปพูดคุยบน Discord

### แนวทางการพัฒนาโค้ด (Engineering Guidelines)
- ยึดหลัก **Karpathy Guidelines**: เรียบง่าย ตรงไปตรงมา ไม่เขียนโค้ดซับซ้อนเกินจำเป็น (Simplicity & Directness)
- ทุกโมดูลทำงานแบบ Standalone และมี Mock/Fallback ที่ปลอดภัย
- รักษาความถูกต้องของความปลอดภัย: ตรวจสอบ HMAC Signature ทุก Webhook Request
