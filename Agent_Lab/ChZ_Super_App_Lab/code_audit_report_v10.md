# 🔍 CODE AUDIT REPORT — UI Spec Harmonization & Multi-Page PDF Audit (v10)
ผู้ตรวจสอบ: น้องออม (Aom) | ผู้เขียนโค้ด: น้องคิว | วันที่ตรวจสอบ: 2 กรกฎาคม 2569 (2026-07-02)

---

## 📊 ประวัติการตรวจสอบ (Audit Summary)
ออมได้ทำการตรวจสอบ (Re-audit) การปรับแต่งแก้ไขโค้ดตามสไตล์ **Soft Pastels UI / Holographic Glassmorphic** ของหน้าจอแดชบอร์ดหลัก รวมถึงลอจิกการส่งออกเอกสาร A4 (Invoice/Quotation/Receipt) ผ่าน PDFShift ในไฟล์ [super_app_anime.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/super_app_anime.html) โดยใช้สกิล **scrutinize** และ **karpathy-guidelines** อย่างเคร่งครัด

จากการไล่ตรวจสอบโครงสร้างโค้ดและการไหลของข้อมูล (Data Path Tracing) ออมพบบั๊กความไม่ครบถ้วนตาม UI Spec ดีไซน์ และความเสี่ยงในการพิมพ์เอกสารหลายหน้าล้นตัดคำ ซึ่งจัดเป็นประเด็นระดับ **Must Fix (Blocker)** ออมจึงต้องตัดสินผลการตรวจสอบรอบนี้เป็น **FAIL (REJECT)** เพื่อให้พี่คิวทำการแก้ไขก่อนนำส่งมอบงานจริงนะแก

---

## 🔴 ต้องแก้ไข (Fail - Must Fix)

### 📌 จุดบกพร่องที่ต้องแก้ไขทันที (Blockers / Must Fix)

#### 1. ปุ่มสวิตช์ภาษา (Language Switcher) หายไปจากโครงสร้าง HTML ของ Sidebar
* **พิกัดโค้ด:** [super_app_anime.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/super_app_anime.html#L2234-L2248)
* **การแกะรอยโค้ด (Path Tracing):**
  1. ใน CSS สไตล์ชีตหลัก มีการประกาศกฎสำหรับคลาส `.lang-switch-capsule` และ `.toggle-circle` (บรรทัดที่ 306-341) พร้อม Event Listener ใน JS อย่างครบถ้วน
  2. แต่เมื่อออมตรวจสอบโครงสร้าง HTML ในส่วนของ `.sidebar-bottom` (บรรทัดที่ 2234-2247) กลับพบว่ามีเพียงกล่องผู้ใช้ `.user-profile-capsule` เท่านั้น โดยไม่มีองค์ประกอบของปุ่มสวิตช์ภาษา `.lang-switch-capsule` อยู่ในหน้าจอจริงเลย
* **ผลกระทบ:** หน้าจอแดชบอร์ดจริงจะไม่มีปุ่มสวิตช์ภาษาให้กดใช้งาน ซึ่งไม่ตรงตาม UI Spec ข้อ 2.1 และขัดต่อเกณฑ์การตรวจรับงานข้อ 1 อย่างรุนแรง
* **แนวทางแก้ไข:** ให้เพิ่มปุ่มสวิตช์ภาษากลับคืนมาใน `.sidebar-bottom` เหมือนสเปกดั้งเดิมของ v11:
  ```html
  <div class="sidebar-bottom" style="margin-top: auto; padding-bottom: 8px;">
    
    <div class="user-profile-capsule">
      <div class="user-avatar-wrap">
        <div class="user-avatar-placeholder">
          <img src="assets/keng_avatar.jpg" alt="CHZ Manager" class="user-avatar-img">
        </div>
      </div>
      <div class="user-info-text">
        <div class="user-role">CHZ MANAGER</div>
        <div class="user-version">Version 1.05</div>
      </div>
    </div>

    <!-- Restored Language Switcher Button -->
    <div class="lang-switch-capsule">
      <span class="lang-label">Eng</span>
      <div class="toggle-circle"></div>
    </div>
  </div>
  ```

#### 2. ล็อกความสูงหน้าเอกสารกระดาษชั่วคราวเป็น 295mm แบบคงที่ (Multi-Page PDF Truncation Bug)
* **พิกัดโค้ด:** [super_app_anime.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/super_app_anime.html#L6069-L6072)
* **การแกะรอยโค้ด (Path Tracing):**
  1. ในฟังก์ชันส่งออก PDF เมื่อผู้ใช้ส่งฟอร์มเพื่อสร้างไฟล์ PDF ระบบจะบังคับเปลี่ยนสไตล์ของ `#a4-preview-content` (หรือ `previewElement`) ชั่วคราว:
     ```javascript
     previewElement.style.height = '295mm';
     previewElement.style.minHeight = '295mm';
     previewElement.style.maxHeight = '295mm';
     previewElement.style.overflow = 'hidden';
     ```
  2. การตั้งค่านี้เป็นการบังคับให้ความสูงของกระดาษพรีวิวย่อขนาดเหลือเพียง 1 หน้า (295mm) เสมอ
* **ผลกระทบ:** หากผู้ใช้เพิ่มรายการธุรกรรม (Items List) ในหน้าสไลด์ 4 จำนวนหลายสิบรายการจนมีเนื้อหาล้นยาวเกิน 1 หน้ากระดาษจริง ข้อมูลของหน้าที่ 2 และหน้าถัดๆ ไปทั้งหมดจะถูกตัดทิ้งเนื่องจากคุณสมบัติ `overflow = 'hidden'` และ `maxHeight = '295mm'` ทำให้ไม่สามารถแปลงหน้าเอกสารเป็น PDF ที่มีหลายหน้าได้
* **แนวทางแก้ไข:** ให้คำนวณจำนวนหน้าจริง $N$ แบบไดนามิกโดยหารความสูงจริงของอิลิเมนต์กระดาษด้วยขนาดความสูงต่อหน้า ก่อนที่จะทำการล็อกความสูงเพื่อส่งข้อมูลไปยัง PDFShift:
  ```javascript
  const scrollHeight = previewElement.scrollHeight;
  const N = Math.ceil(scrollHeight / 1115) || 1; // 1115px คือขนาดความสูงประมาณ 295mm ของ A4
  const targetHeight = (N * 295) + 'mm';
  
  previewElement.style.height = targetHeight;
  previewElement.style.minHeight = targetHeight;
  previewElement.style.maxHeight = targetHeight;
  previewElement.style.overflow = 'hidden';
  ```

---

## 🟡 ข้อเสนอแนะ (Advisory)

### 1. ลบโค้ดขยะลอยค้าง (Dead Code) ในฟังก์ชัน `updateDashboardMetrics`
* **พิกัดโค้ด:** [super_app_anime.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/super_app_anime.html#L5260-L5264)
* **รายละเอียด:** ในฟังก์ชันคำนวณยอดเงินโลคอล มีการสแกนหาไอดี `#summary-left-title` และ `#summary-right-title` เพื่อเขียนข้อความ `'Feltz Studio'` และ `'Grab Income'` ทับลงไป แต่ไอดีทั้งสองไม่มีอยู่ในโครงสร้าง HTML จริงแล้ว (ถูกแทนที่ด้วย `slide2-stat-left-title` และ `slide2-stat-right-title` ซึ่งพี่คิวเขียนคำสั่งอัปเดตทับไว้ที่บรรทัดก่อนหน้าแล้ว) จึงกลายเป็นโค้ดขยะลอยค้างที่ไม่มีผลในการแสดงผล
* **แนวทางแก้ไข:** ลบโค้ดบล็อกส่วนเกินนี้ออกเพื่อรักษาความคลีนของไฟล์ระบบตามกฎ Karpathy Guidelines:
  ```javascript
  // ลบบล็อกนี้ออก
  const leftTitleEl = document.getElementById('summary-left-title');
  const rightTitleEl = document.getElementById('summary-right-title');
  if (leftTitleEl) leftTitleEl.textContent = 'Feltz Studio';
  if (rightTitleEl) rightTitleEl.textContent = 'Grab Income';
  ```

---

## 🟢 ผ่าน (Pass)

### 1. ลอจิกสะกดภาษาไทยค่าเงินบาท (Thai Baht Spelling - PASS)
* **รายละเอียด:** ฟังก์ชัน `thaiBahtText` ทำงานได้อย่างยอดเยี่ยมและลื่นไหลดีมาก มีการคำนวณและสะกดตัวอักษรสำหรับหลักสิบเอ็ด หลักสิบ และหลักหน่วยอื่นๆ ได้อย่างละเอียดสมบูรณ์ ปราศจากบั๊กการเกิดตัวอักษรสะกดซ้อนและค่าสตางค์แสดงผลถูกต้องตรงตามหลักบัญชี

### 2. ลอจิกการดัก Error ออฟไลน์ (Offline Error Isolation - PASS)
* **รายละเอียด:** ฟังก์ชันดักจับข้อผิดพลาดส่วนกลาง `window.onerror` ได้คัดแยกและละเว้น (Ignore) `"Script error."` และ `lineno === 0` ออกจากตัวแผงแจ้งเตือนบนหน้าจออย่างรัดกุม ทำให้เมื่อนำหน้าจอไปเปิดใช้งานแบบออฟไลน์ (`file://`) จะไม่มีการแจ้งเตือนความผิดพลาดปลอมจากส่วนขยายเบราว์เซอร์โผล่ขึ้นมารบกวนผู้ใช้

### 3. ความปลอดภัยและไม่พึ่งพาเซิร์ฟเวอร์ค้าง (Security & Port-Free Static - PASS)
* **รายละเอียด:** ตัวหน้าจอทำงานได้แบบ Static HTML (ดับเบิ้ลคลิกรันผ่านเบราว์เซอร์ได้ทันที) ไม่พบการเขียน Hardcode ค่าความลับใดๆ เช่น API Key หรือ Web App Script URL ลงในโค้ดตรงๆ โดยเก็บค่าผ่าน `localStorage` ในหน้า Settings สอดคล้องตามมาตรฐานความปลอดภัยอย่างเคร่งครัด

### 4. นโยบายห้ามใช้อีโมจิบนดีไซน์หน้าเว็บ (No Emoji in UI - PASS)
* **รายละเอียด:** ตรวจสอบส่วนประกอบ UI ทั้งหมด ไม่พบรูปสัญลักษณ์อีโมจิมาใช้งานแทนปุ่มหรือไอคอน โดยใช้ SVG เวกเตอร์และข้อความดิบสวยงามตามข้อตกลง CI

---

## 🏁 คำตัดสินสุดท้าย (Final Verdict)

- [ ] **PASS** — อนุมัติให้นำแผนงาน/โค้ดขึ้นระบบจริงได้
- [X] **REJECT (ไม่ผ่านการตรวจสอบ)** — ส่งคืนให้ **น้องคิว (Q)** ดำเนินการแก้ไขข้อผิดพลาด Blocker ทั้ง 2 ข้อ (คืนปุ่ม Language Switcher บน Sidebar และแก้ไขระบบล็อกความสูงกระดาษ PDF แบบไดนามิกเพื่อรองรับเอกสารหลายหน้า) ก่อนส่งรายงานตรวจสอบมาให้ออมตรวจทานอีกรอบนะแก

---
*รายงานโดย: น้องออม (Aom) — ผู้ตรวจสอบโค้ดประจำตึก Coder_Studio* 🕵️‍♀️💻✨
