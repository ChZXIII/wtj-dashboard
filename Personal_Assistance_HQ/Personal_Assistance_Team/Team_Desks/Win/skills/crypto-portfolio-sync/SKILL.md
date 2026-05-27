---
name: crypto-portfolio-sync
description: Syncs cryptocurrency trading orders from Bitkub and Binance TH APIs to Google Sheets, calculates live PnL percentages, exports history charts, and updates the HTML portfolio dashboard.
---

# Skill: Crypto Portfolio Sync (Win's Skill)

ใช้เมื่อมีรายการซื้อขายคริปโตใหม่ที่ต้องการดึงผ่าน API จาก Bitkub และ Binance TH ลงไปกรอกใน Google Sheets พร้อมอัปเดตเปอร์เซ็นต์กำไรขาดทุน (PnL) และพอร์ตแดชบอร์ดให้เป็นปัจจุบัน

---

## 📋 1. โครงสร้างและการคัดแยกเหรียญ (Routing Rules)
สคริปต์จะดึงรายการซื้อ (BUY Orders) ที่ผ่านการตกลงซื้อขายสำเร็จ (FILLED) มาคัดแยกแท็บใน Google Sheets ดังนี้:
1. **เหรียญ KUB (จาก Bitkub):** ส่งไปจดที่แท็บ **`Thyme`** เสมอ (ไม่ซิงค์เหรียญอื่นจาก Bitkub เพราะพี่เก่งไม่ได้สั่ง)
2. **เหรียญ BTC (จาก Binance TH):** ทำการแยกรายไม้ตามจำนวนเงินซื้อ:
   - ยอดเงินซื้อ **น้อยกว่าหรือเท่ากับ 300 บาท** ➡️ ส่งไปแท็บ **`Mod`**
   - ยอดเงินซื้อ **มากกว่า 300 บาท** ➡️ ส่งไปแท็บ **`BTC`**
3. **เหรียญอื่นๆ (เช่น ETH, SOL, BNB, XRP):** ส่งไปแท็บของเหรียญนั้นๆ ตามลำดับ

---

## ⚙️ 2. การจัดการหน้าตาและฟอร์แมตข้อมูล (Formatting Rules)
- **แถวหัวข้อและ Offset (แท็บ BTC):** เนื่องจากแท็บ `BTC` มีหัวตาราง 2 แถว แถวเป้าหมายสำหรับเขียนข้อมูลของวันที่ N ในเดือนนั้น จะต้องลงที่ **`แถวที่ N + 2`** เสมอ ห้ามแทรกแถวใหม่
- **การแทรกแถวใหม่ (แท็บ Thyme & Mod):**
  - ค้นหาแถวที่มีคำว่า "ราคาเฉลี่ย" หรือ "ยอดเงินที่..." แล้วทำการแทรกแถวใหม่ขึ้นมาข้างบน
  - คำนวณเลขสัปดาห์แบบไดนามิก: `last_week + 1`
  - สั่งดีไซน์จัดสี **ACCENT_BG & ROW_BG** รวมถึงขอบเข้มสีเขียวพรีเมียมให้เข้าธีมตารางทันที (ห้ามเว้นช่องขาว)
- **การลงข้อมูลย้อนหลัง (Timeframe Rules):** บอทจะเช็คยอดซื้อขายย้อนหลัง **48 ชั่วโมง** เสมอเพื่อกันออเดอร์ตกหล่น และจัดกลุ่มตาม "วันที่ซื้อจริง" ห้ามลงแค่วันที่ปัจจุบัน

---

## 📊 3. กระบวนการอัปเดตหน้า Dashboard
1. **บันทึกประวัติรายเดือน (Portfolio History):**
   - คำนวณยอดเงินลงทุนจริง (`totalInvest`) และมูลค่าพอร์ตสดๆ ทุกวัน
   - บันทึกยอด Snapshot ลงชีต `Portfolio_History` **เฉพาะวันที่ 1 ของเดือน** เท่านั้นเพื่อความคลีนของกราฟ
2. **ส่งออกข้อมูลกราฟ:** แปลงประวัติยอดเงิน PnL ย้อนหลังเป็นไฟล์ JavaScript `history_data.js` เพื่อให้หน้าเว็บอ่านข้อมูลได้ทันที
3. **อัปเดตไฟล์ HTML แดชบอร์ด:** เข้าไปแก้ไขตัวแปร `bC` (ยอด Binance TH), `bkC` (ยอด Bitkub) และ `tC_v` (ทุนรวมจริง) ในไฟล์ `portfolio_dashboard.html` อัตโนมัติ

---

## 🧪 4. คำสั่งรันการซิงค์ข้อมูล (Execution Command)
รันสคริปต์หลักผ่านทาง Terminal ภายใต้ Virtual Environment ของโปรเจกต์:
```bash
cd /Users/chz/Desktop/ChZ_Agent_Corp
./venv/bin/python3 WTJ_Content_Studio/Team_Agent_Content/skills/crypto_portfolio_sync.py
```
> [!IMPORTANT]
> - ต้องมั่นใจว่าในไฟล์ `.env` ที่ root ของโปรเจกต์มี API Key และ Secret ของ Bitkub / Binance TH ที่ถูกต้องเรียบร้อยแล้ว
> - เพื่อแก้บั๊ก Clock Drift (ปัญหา Signature ไม่ตรง) สคริปต์จะดึงเวลาจากเซิร์ฟเวอร์โดยตรงผ่าน `/api/v3/servertime` มาสร้าง Signature เสมอ
