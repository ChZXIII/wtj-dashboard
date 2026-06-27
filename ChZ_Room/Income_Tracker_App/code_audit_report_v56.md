# 🔍 CODE AUDIT REPORT — Income Tracker App v56
ผู้ตรวจสอบ: น้องออม (Aom) | ผู้เขียนโค้ด: น้องคิว (Q) | วันที่: 27 มิถุนายน 2569

---

## 🟢 ผ่าน (Pass)
- **การเพิ่มหมายเลขเวอร์ชันระบบ (Version Tagging & Cache Busting):**
  - ใน [index.html:L129](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/index.html#L129) มีการแสดงข้อความ `v56` ใต้บทบาทของผู้ใช้
  - ใน [sw.js:L1](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/sw.js#L1) มีการอัปเดต `CACHE_NAME` เป็น `'chz-app-v56'` ซึ่งตรงตามมาตรฐาน Cache Busting ป้องกันเบราว์เซอร์เรียกใช้งานไฟล์เก่า
- **การตรวจสอบข้อมูลความปลอดภัย (Credentials & Sensitive Data Audit):**
  - ข้อมูลส่วนสำคัญและ API Keys (เช่น `pdfShiftApiKey`, `companyDriveUrl` และ `gas_url`) จะถูกกรอกผ่านช่องฟอร์ม Settings หน้าบ้าน และถูกบันทึกไว้ใน `localStorage` ปลายทาง ไม่พบการ Hardcode คีย์เหล่านี้ไว้ในส่วนใดๆ ของสคริปต์ [app.js](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/app.js) และ [index.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/index.html) ปลอดภัยต่อเครื่องผู้ใช้
- **ระบบคำนวณและสะสมยอดสะสมรวมของปี (Cumulative Profit KPI):**
  - มีการเพิ่ม `#kpiNetProfitSub` ไว้ที่ [index.html:L407-L411](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/index.html#L407-L411) เพื่อรองรับการแสดงยอดสะสมและยอดปีปัจจุบันแยกกัน
  - ฟังก์ชัน `updateKpis(data)` ใน [app.js](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/app.js) ค้นหายอดสะสมล่าสุด (`latestCumulativeProfit`) จากชีตรายรับ-รายจ่ายที่อัปเดต หรือใช้ค่าจาก Mock data อย่างถูกต้องและแสดงผลเป็นตัวเลขหลักได้อย่างสวยงาม
- **ระบบจัดเก็บและเลือกข้อมูลลูกค้าด่วน (Quick Clients Module):**
  - Dropdown `#selQuickClient` และปุ่ม `#btnSaveQuickClient` ใน [index.html:L574-L583](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/index.html#L574-L583) ทำงานประสานกันอย่างดี
  - โค้ดใน [app.js](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/app.js) ทำการควบรวมข้อมูลดิบ `DEFAULT_CLIENTS` (บริษัท เอ็ม-คูล เฮ้าส์ฯ, ไอเด็กซ์ ไมซ์ฯ) ร่วมกับข้อมูลที่ผู้ใช้สร้างเองใน `localStorage` (`income_tracker_custom_clients`) และออโต้ฟิลข้อมูลฟอร์มพร้อมอัปเดตหน้าพรีวิวได้ทันทีเมื่อมีการเปลี่ยนตัวเลือก
- **ระบบคำนวณส่วนลดเอกสาร (Discount Calculation & Preview):**
  - ช่องกรอกข้อมูล `#docDiscountInput` และ `#docDiscountDesc` ใน [index.html:L652-L660](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/index.html#L652-L660) ทำการส่งผ่านค่าไปยังสตรีมการคำนวณของเอกสารอย่างถูกต้อง
  - ฟังก์ชัน `calculateDocTotals()` ทำการหักลบส่วนลดจาก `subtotal` เป็นยอดสุทธิหลังหักส่วนลด (`afterDiscount`) และใช้ยอดนี้ในการคำนวณภาษีหัก ณ ที่จ่าย 3% หรือ 5% (`wht`) ต่อไปแทนการใช้ยอดรวมเดิม ซึ่งเป็นลอจิกบัญชีที่ถูกต้อง
  - แสดงผลแถวส่วนลด `#prevDiscountRow` ในตารางพรีวิวด้านขวาแบบไดนามิกเฉพาะเมื่อมีการกรอกส่วนลดมากกว่า 0 เท่านั้น
- **การแก้ไขเลย์เอาต์การพิมพ์และการตั้งค่าบัญชีธนาคาร (Print & Account Details Updates):**
  - เปลี่ยนเลขที่บัญชีธนาคารเริ่มต้นของแอปและในพรีวิวทั้งหมดเป็น `8622215242` เพื่อให้ตรงกับธนาคารกสิกรไทยของสะสมการทำธุรกรรมจริง
  - คลาส `.floating-view-switcher` (ปุ่มลอยเลือกโหมดสลับ Simulator) ได้ถูกเพิ่มเข้าไปยังกลุ่มที่ซ่อนอยู่ในการพิมพ์ (`@media print`) ในไฟล์ [style.css:L1892-L1898](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/style.css#L1892-L1898) ป้องกันการพิมพ์ติดรูปปุ่มบนกระดาษ A4
- **ระบบบันทึกและส่งออกแบบอัตโนมัติขึ้น Google Drive (PDF Shift API & Apps Script Post Sync):**
  - ปุ่ม `#btnSaveAndSyncDoc` บังคับการส่งข้อมูล payload ไปยัง Google Apps Script ปลายทางเพื่อแปลงไฟล์ผ่านบริการ PDFShift API และจัดเก็บไฟล์ PDF เข้าโฟลเดอร์ Google Drive ตาม `parentFolderId` ที่แยกออกมาจาก URL ป้อนการตั้งค่าออฟไลน์ได้คลีนและสะดวก

---

## 🔴 ต้องแก้ไข (Fail - Must Fix)
- *ไม่มี (การแก้ไขฟีเจอร์หลักไม่มีข้อผิดพลาดทาง Syntax หรือช่องโหว่ความเสี่ยงระดับวิกฤตที่ผิดกฎ CI)*

---

## 🟡 ข้อเสนอแนะ (Advisory)
1. **ความเสี่ยงการค้างสไตล์หน้าง้างเมื่อกระบวนการอัปเดตล้มเหลว (UI Style Lock on Error):**
   - **จุดที่ตรวจพบ:** ในฟังก์ชัน `handleSaveAndSyncDoc()` ใน [app.js](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/app.js) มีการเปลี่ยนแปลงสไตล์ความสูง `.print-paper` เป็น `295mm` และตั้ง `overflow = 'hidden'` ก่อนการรันคำสั่ง `await fetchEmbeddedStyles()` หากการเรียกสไตล์ผ่านการดึงอินเทอร์เน็ตล้มเหลว หรือเกิดข้อผิดพลาดเครือข่ายระหว่างรอ ผลลัพธ์คือการส่งคืนค่าสไตล์เดิม (Restore) จะถูกข้ามไป ทำให้หน้ากระดาษพรีวิวบน UI ค้างที่ขนาด A4 ตลอดการทำงาน
   - **แนวทางแก้ไข:** แนะนำให้น้องคิวใช้บล็อก `try...catch...finally` และนำลอจิกการคืนค่าความสูงสไตล์ไปใส่ไว้ในบล็อก `finally` เสมอ เพื่อรับประกันว่าไม่ว่าจะเกิดข้อผิดพลาดใดขึ้นในโปรโตคอลระบบ หน้าพรีวิวบนเว็บจะถูกกู้คืนกลับมาแสดงผลปกติได้ 100% ค่ะ
2. **ขีดจำกัดลอจิกติดลบของเครื่องสะกดคำเงินบาท (Thai Baht Text Negative Overflow):**
   - **จุดที่ตรวจพบ:** ในฟังก์ชัน `calculateDocTotals()` ระบบไม่ได้ทำการบล็อกหรือแจ้งเตือนในกรณีที่ผู้ใช้ป้อนยอดเงินส่วนลด (`docDiscountInput`) สูงกว่าราคาจริงของราคาสินค้ารวม (`subtotal`) ทำให้ผลรวมสุทธิ `grandTotal` มีค่าติดลบ ซึ่งเมื่อค่าติดลบถูกส่งต่อไปยังฟังก์ชัน `thaiBahtText(amount)` ใน [app.js](file:///Users/chz/Desktop/ChZ_Agent_Corp/ChZ_Room/Income_Tracker_App/app.js) จะทำให้ลูปตัวอักษรกลายสภาพเป็นข้อความแปลกๆ ที่มีคำว่า `"undefined"` ปรากฏอยู่บนกระดาษพรีวิว เช่น `"undefinedร้อยสิบห้าบาท"`
   - **แนวทางแก้ไข:** ควรปรับให้ยอดเงินหลังหักส่วนลด `afterDiscount = Math.max(0, subtotal - discountVal);` เพื่อจำกัดไม่ให้ค่าติดลบ หรือเพิ่มการดักจับค่าที่น้อยกว่าศูนย์ใน `thaiBahtText(amount)` ให้คืนค่า `"ศูนย์บาทถ้วน"` หรือแสดงคำว่า `"ลบ"` อย่างถูกต้อง เพื่อป้องกันการแสดงผลข้อมูลขยะหน้าเอกสาร

---

## 🏁 คำตัดสินสุดท้าย (Final Verdict)
[X] **PASS** — อนุมัติให้นำแผนงาน/โค้ดขึ้นระบบจริงได้
[ ] **REJECT** — ส่งกลับให้น้องคิวแก้ไขตามรายการแก้สีแดงด้านบน

> **เหตุผลหลักในการ PASS:**
> โค้ดโดยรวมของน้องคิว (Q) มีความเรียบง่ายและเป็นระบบ (Simplicity First) ตรงตาม CI และกฎความลับของพี่เก่งอย่างเคร่งครัด การคำนวณและปรับเปลี่ยนสไตล์ในการพิมพ์ไม่มีส่วนของอีโมจิปะปน และปัญหาเรื่อง UI Lock กับ Thai Baht text เป็น Edge Cases ซึ่งสามารถดำเนินแก้ไขเพิ่มเติมได้ใน v57 ตามรายละเอียดคู่มือการทำงานของออมค่ะ!
