# Code Audit Report (v37) - View Mode Switcher Feature
**Project:** Income Tracker App (ChZ Room)  
**Auditor:** น้องออม (Aom - Code Auditor)  
**Date:** 2026-06-23  

---

## 🔍 Executive Summary
รายงานฉบับนี้เป็นการตรวจสอบความถูกต้อง ความปลอดภัย มาตรฐานการเขียนโค้ด (Karpathy Guidelines) และแนวทางปฏิบ้าน UI/UX (Neobrutalist CI & No Emoji Rule) ของฟีเจอร์ **"View Mode Switcher (จำลองหน้าจอมือถือสลับกับเว็บปกติ)"** บนแอปพลิเคชันบันทึกรายรับของพี่เก่ง (Income Tracker App) 

**ผลการตรวจสอบภาพรวม:** **PASS (SHIP)**  
โค้ดทำงานได้ถูกต้อง มีตรรกะการสลับหน้าจอและการบันทึกสถานะลง `localStorage` ที่มั่นคง แยกลอจิกและ UI ได้ดีเยี่ยม ปลอดภัย ไม่มีสิ่งผิดสังเกตหรือบั๊กตกค้าง

---

## 🛡️ 1. Scrutinize Audit (Code Path Tracing & Logic Verification)

### 1.1 Intent (วัตถุประสงค์ของฟีเจอร์)
- **เป้าหมาย:** สลับโหมดการแสดงผลของหน้าเว็บระหว่าง "Desktop View" (ปกติ) และ "Mobile Simulator View" (จำลองหน้าจอมือถือที่มี bottom nav และสกรอลล์แยกอิสระ) บนหน้าจอขนาดใหญ่ และซ่อนตัวสลับนี้โดยอัตโนมัติเมื่อเข้าใช้งานผ่านหน้าจอมือถือจริง
- **การประเมิน YAGNI:** มีความจำเป็นสูงสำหรับการพรูฟหน้าจอ Mockup และทดสอบ UX/UI ของระบบ PWA ในบริบทที่หลากหลายอย่างรวดเร็ว โดยไม่จำเป็นต้องใช้เครื่องมือ DevTools ของเบราว์เซอร์

### 1.2 Code Path Tracing (การแกะรอยการทำงาน)
1. **Initial State (เริ่มต้น):** 
   - `app.js:initViewModeSwitcher()` จะทำงานทันทีหลัง `DOMContentLoaded`
   - ทำการอ่านค่า `localStorage.getItem('income_tracker_view_mode')` (Default: `desktop`)
   - หากเป็น `mobile` จะเพิ่มคลาส `.mobile-simulator-active` ให้ `body` และกำหนดไอคอนของปุ่มสลับให้แสดงรูป Desktop (เพื่อกดสลับกลับ) ผ่านฟังก์ชัน `updateIcon()`
2. **Action Trigger (การสลับโหมด):**
   - เมื่อกดปุ่ม `#btnToggleViewMode` (หรือ `.floating-view-switcher`)
   - ฟังก์ชันจะทำ `document.body.classList.toggle('mobile-simulator-active')`
   - จัดเก็บสถานะใหม่ลงใน `localStorage` ด้วยคีย์ `income_tracker_view_mode`
   - เรียกใช้ `updateIcon()` เพื่อสลับ Path SVG ของไอคอนระหว่างมือถือและเดสก์ท็อปอย่างถูกต้อง
3. **UI Simulation (สไตล์ของ Simulator):**
   - เมื่อ `.mobile-simulator-active` ทำงานบน `body` (ในหน้าจอ Desktop @media (min-width: 769px)) ตัวแอปพลิเคชัน `.app-container` จะถูกตีกรอบความกว้างเป็น `420px` สูง `860px` มีกรอบโทรศัพท์สีเข้มหนา `12px` สไตล์ Neobrutalist
   - Sidebar จะย้ายมาอยู่ด้านล่างเป็น Bottom Navigation (สูง `65px`)
   - `.main-content` จะล้าง margin-left และจำกัดพื้นที่ด้วย `height: 100%` พร้อมเปิด `overflow-y: auto` ทำให้การสกรอลล์เนื้อหาหลักเกิดขึ้นแยกส่วนโดยไม่ล้นกรอบ simulator และไม่เบียดบังปุ่ม Bottom Navigation

### 1.3 Verification Results (ผลตรวจสอบการทำงาน)
- [x] **การสลับคลาสบน body:** ถูกต้องและสอดคล้องกับพฤติกรรมของ CSS
- [x] **การสลับไอคอน SVG:** ถูกต้อง (เมื่อจำลองโมบายล์แสดงไอคอนเดสก์ท็อป / เมื่อเป็นเดสก์ท็อปแสดงไอคอนโมบายล์) 
- [x] **Data Persistence:** จัดเก็บลง `localStorage` ได้อย่างถูกต้อง รีเฟรชแล้วไม่หลุดโหมดเดิม
- [x] **Bottom Nav Layout:** จัดกลุ่มปุ่มเมนูสอดคล้องตามลำดับและการทำงานของ mobile layout
- [x] **Scroll & Spacing:** ตัวเนื้อหาใน simulator สกรอลล์ได้อย่างลื่นไหล ไม่ถูกบดบัง และไม่มีการรั่วไหลออกนอกกรอบ

---

## 🧠 2. Karpathy Guidelines & Design Audit

### 2.1 Code Cleanliness & Surgical Edits
- โค้ดมีความกระชับสูง แก้ไขอย่างจำกัดเฉพาะจุดที่เกี่ยวข้อง (Surgical Change)
- ไม่พบตัวแปรหรือฟังก์ชันที่ไม่ได้ถูกใช้งาน (Dead Code/Unused Variables)
- ปฏิบัติตามมาตรฐานการจัดระเบียบไฟล์ของระบบ (ซอฟต์แวร์ทำงานกับไฟล์อย่างสะอาด)

### 2.2 UI/UX & Neobrutalist Brand CI compliance
- **ปุ่ม Floating View Switcher:** 
  - ใช้สีกรอบและเงาจากตัวแปรสีกระดาษและหมึกสะท้อนกับระบบธีม (`var(--ink-dark)`)
  - ขอบปุ่มมีขนาดเส้นขอบ `2px` และเงาหนา `4px` ปรับระดับเงาเมื่อ hover (`6px` / `translate(-2px, -2px)`) และ active (`2px` / `translate(2px, 2px)`) ครบถ้วนตามดีไซน์ Neobrutalist 3D Solid Shadow ของบริษัท
- **ซ่อนปุ่มสลับบนหน้าจอจริง:** ในไฟล์ `style.css` มีการใช้ `@media (max-width: 768px) { .floating-view-switcher { display: none !important; } }` เพื่อปิดการทำงานของปุ่มสลับบนหน้าจอมือถือจริงอย่างเรียบร้อย เพื่อความคลีนและไม่รบกวนผู้ใช้

### 2.3 Emoji Verification (กฎเหล็กห้ามใช้อีโมจิเด็ดขาด)
- รันสคริปต์ตรวจสอบอย่างละเอียดบนไฟล์โค้ดทั้งหมดของโปรเจกต์ (`index.html`, `style.css`, `app.js`, `sw.js`)
- **ผลลัพธ์:** **PASS 100%** ไม่พบสัญลักษณ์อีโมจิหลุดรอดไปแสดงผลบนหน้าจอ UI ระบบใช้ไอคอน SVG ของแท้และตัวอักษรปกติเท่านั้น

### 2.4 Service Worker Verification
- ไฟล์ `sw.js` ได้ปรับเปลี่ยนค่า `CACHE_NAME` เป็น `'chz-app-v41'` 
- มั่นใจได้ว่ามีการทำ Cache Busting สำหรับเบราว์เซอร์ของพี่เก่งอย่างถูกต้องเมื่อนำขึ้นระบบจริง

---

## 🏆 Final Verdict
**Verdict: SHIP 🚀 (อนุมัติผ่านการตรวจสอบ)**  
**เหตุผลสนับสนุน:** โค้ดมีคุณภาพสูง เป็นระเบียบ สะอาด ปฏิบัติตามมาตรฐาน Neobrutalist CI, มาตรฐานฟอนต์, และกฎเหล็กไร้อีโมจิอย่างครบถ้วน สามารถประสานงานปล่อยงานต่อไปได้ทันที
