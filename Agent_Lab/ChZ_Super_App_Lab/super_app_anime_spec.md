# 🎨 พิมพ์เขียวการสร้าง UI: แดชบอร์ดอนิเมะซูเปอร์แอป (Anime Super App UI Specification)

เอกสารฉบับนี้กำหนดรายละเอียดและมาตรฐานการออกแบบหน้าจอแดชบอร์ดตามสไตล์ **Soft Pastels UI / Holographic Glassmorphic** โดยระบุพิกัด CSS/Class และวิธีเกลี่ยสีของพาเลตสีลงบนส่วนประกอบแดชบอร์ดเพื่อความสวยงามพรีเมียมและสมดุลที่สุด เพื่อให้นักพัฒนา (น้องคิว) และผู้ตรวจสอบโค้ด (น้องออม) นำไปปรับแต่งหน้าจอจริงใน [super_app_anime.html](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/super_app_anime.html) ได้อย่างสมบูรณ์แบบค่ะ

---

## 1. พาเลตสีหลักและตัวแปร CSS (Color Palette & Variables)

ตัวแปรสีหลักใน `:root` ที่นำมาใช้ในการออกแบบ:
*   **White (#FFFFFF):** ความสะอาด สว่าง และความเบาบาง (`--color-white`)
*   **Ice Blue (#b3ddf2):** สีฟ้าพาสเทลอ่อนสำหรับความนุ่มนวลและสถานะจองแล้ว (`--color-ice-blue`)
*   **Neon Rose (#ff4b72):** สีชมพูอมแดงสดสำหรับสถานะเลือกอยู่ (Active/Selected) และปุ่มสำคัญ (`--color-neon-rose`)
*   **Violet/Purple (#8f3dff):** สีม่วงสดสว่างสำหรับแบรนด์หลักและองค์ประกอบรองเพื่อสร้างมิติ (`--color-violet`)
*   **Pastel Green (#a2e8c4):** สีเขียวพาสเทลสำหรับงานที่ชำระเงินแล้ว ละมุนและมี Contrast สวยงาม (`--color-pastel-green`)
*   **Pastel Yellow (#fde68a):** สีเหลืองพาสเทลสำหรับงานที่จองคิว นุ่มตาไม่ฉูดฉาด (`--color-pastel-yellow`)

---

## 2. รายละเอียดการเกลี่ยสีแยกตามส่วนประกอบ (Detailed Color Distribution Specifications)

### 2.1 แถบซ้าย (Sidebar Area)
*   **ไอคอนเมนูนำทาง (Navigation Items):**
    *   **เมนูที่เลือกอยู่ (Active Menu - `.nav-item.active`):**
        *   `background-color: var(--color-neon-rose);` (ชมพูอมแดงสด)
        *   `color: var(--color-white);` (ขาวสะอาด)
        *   `box-shadow: 0 8px 20px rgba(255, 75, 114, 0.35);` (เงาเรืองแสงสีชมพูบางเบา)
    *   **เมนูที่ไม่ได้เลือก (Inactive Menu - `.nav-item`):**
        *   `color: var(--color-text-secondary);` (เทาอ่อน)
        *   **เมื่อ Hover (`.nav-item:hover`):**
            *   `background-color: var(--color-ice-blue);` (ฟ้าพาสเทลอ่อน)
            *   `color: var(--color-neon-rose);` (ไอคอนเปลี่ยนเป็นสีชมพูอมแดงสดเพื่อสร้างความตื่นตัว)
*   **สวิตช์ภาษา (Language Switcher - `.lang-switch-capsule`):**
    *   `background-color: var(--color-ice-blue);` (พื้นหลังฟ้าพาสเทลอ่อน)
    *   `border: 1px solid rgba(255, 75, 114, 0.15);` (ขอบชมพูจางพิเศษเพื่อหลีกเลี่ยงสีม่วงเข้มเด่นสะดุดตา)
    *   **ตัวหนังสือภาษา (Label - `.lang-label`):**
        *   `color: var(--color-neon-rose);` (สีชมพูอมแดงสดในโทนน่ารัก ไม่เข้มเด่นสะดุดตา)
    *   **ปุ่มวงกลมสลับ (Toggle Button - `.toggle-circle`):**
        *   `background-color: var(--color-white);` (วงกลมสีขาวสะอาด)
        *   `box-shadow: 0 2px 5px rgba(255, 75, 114, 0.15);` (เงาตกกระทบโทนชมพูบางเบา)

### 2.2 กล่องกลาง (Hero Banner Area)
*   **ปุ่ม Back/Next ในแบนเนอร์ (`.capsule-btn`):**
    *   **สถานะปกติ (Idle):**
        *   `background: rgba(255, 255, 255, 0.85);` (ขาวกึ่งโปร่งแสง)
        *   `border: 1px solid var(--color-ice-blue);` (สีกรอบฟ้าพาสเทลอ่อน)
        *   `color: var(--color-text-primary);` (ดำเข้ม)
    *   **สถานะเมื่อชี้เมาส์ (Hover):**
        *   `background: var(--color-neon-rose);` (เปลี่ยนเป็นพื้นชมพูอมแดงสด)
        *   `border-color: var(--color-neon-rose);` (กรอบชมพูอมแดงสด)
        *   `color: var(--color-white);` (ตัวหนังสือขาว)
        *   `transform: translateY(-1px);`
*   **กล่องรายละเอียดการ์ด Dungeon & Dragon (`.hero-overlay-card`):**
    *   `background: rgba(255, 255, 255, 0.8);` (พื้นหลังขาวกึ่งโปร่งแสง)
    *   `backdrop-filter: blur(20px);` (เอฟเฟกต์กระจกฝ้า)
    *   `border: 1px solid rgba(255, 255, 255, 0.5);`
    *   **ตัวหนังสือเดือน (`.date-month`):**
        *   `color: var(--color-neon-rose);` (ชมพูอมแดงสด)
    *   **ตัวหนังสือวันที่ (`.date-day`):**
        *   `color: var(--color-neon-rose);` (ชมพูอมแดงสดขนาดใหญ่)
    *   **ปุ่มไอคอนโต้ตอบ (Heart, Star, Bookmark - `.btn-icon`):**
        *   `color: var(--color-text-secondary);`
        *   **เมื่อ Hover (`.btn-icon:hover`):**
            *   `color: var(--color-neon-rose);` (เปลี่ยนเป็นสีชมพูอมแดงสด ทั้งไอคอนและข้อความตัวเลข)

### 2.3 การ์ด Promo (Promo Card)
*   **แท็กแคปซูลส่วนลดย่อย (`.tag-capsule`):**
    *   เกลี่ยสีของปุ่มย่อยทั้งสามเพื่อสร้างสมดุลเชิงดีไซน์โดยใช้พาเลตสี 4 สี:
    1.  **แท็กที่ 1 ("20% off" - เน้นความสำคัญสูงสุด):**
        *   `background-color: rgba(255, 75, 114, 0.12);` (พื้นชมพูอมแดงสดแบบจาง)
        *   `color: var(--color-neon-rose);` (ตัวหนังสือชมพูอมแดงสด)
        *   `border: 1px solid rgba(255, 75, 114, 0.25);`
    2.  **แท็กที่ 2 ("Free Popcorn" - ของรางวัลพิเศษ):**
        *   `background-color: rgba(179, 221, 242, 0.3);` (พื้นฟ้าไอซ์บลูจาง)
        *   `color: #bf8eff;` (ตัวหนังสือม่วงอ่อน/ม่วงพาสเทลเพื่อความสบายตา)
        *   `border: 1px solid rgba(179, 221, 242, 0.5);`
    3.  **แท็กที่ 3 ("5% off" - ทั่วไป):**
        *   `background-color: var(--color-white);` (พื้นสีขาวสะอาด)
        *   `color: var(--color-text-secondary);` (ตัวหนังสือสีเทาเพื่อความสะอาดตา)
        *   `border: 1px solid var(--color-ice-blue);` (กรอบสีฟ้าจางเพื่อสร้างมิติและไม่แย่งสายตา)

### 2.4 การ์ดปฏิทินแบบไดนามิก (Dynamic Calendar Slot Card - ขวาบน)
ปรับโครงสร้าง Slot Card เดิมให้เป็นระบบแสดงตารางงานและปฏิทินความคืบหน้าของ ChZ Agent Corp:
*   **Month Slider:** แถบสลับเดือนด้านบนสุด แสดงผลเป็น `Sep` | `Oct` (Active) | `Nov`
    *   เดือนที่เลือกอยู่ (`.month-btn.active`): พื้นหลังสีชมพูอมแดงสด (`--color-neon-rose`), ตัวหนังสือสีขาวสะอาด
    *   เดือนที่ไม่ได้เลือก (`.month-btn`): ตัวหนังสือสีเทาอ่อน, เมื่อ Hover จะเปลี่ยนตัวหนังสือเป็นสีชมพูอมแดงสด
*   **Mini Calendar Grid:** ตารางแสดงความหนาแน่นของงาน คล้ายแผงผังที่นั่งเดิมแต่แสดงผลแบบไม่มีตัวเลขวัน:
    *   ประกอบด้วยจุดสีกลม 30 จุด (`.cal-dot`) เรียงตัวในระบบกริด 6x5 หรือ 7x5
    *   เฉดสีคละความสำคัญและสถานะของงาน:
        *   `status-active` (งานเร่งด่วน/เลือกอยู่): สีชมพูอมแดงสด (`--color-neon-rose`) พร้อมเงาเรืองแสงสีชมพู
        *   `status-paid` (งานที่จ่ายเงินแล้ว): สีเขียวพาสเทล (`--color-pastel-green`)
        *   `status-booked` (งานที่จองคิวไว้): สีเหลืองพาสเทล (`--color-pastel-yellow`)
        *   `status-empty` (ไม่มีงาน/ว่าง): สีขาวสะอาด ขอบเส้นบางสีเทาอ่อน
    *   เมื่อชี้เมาส์ที่ตารางจะแสดงเอฟเฟกต์ยกตัวเล็กน้อย และเมื่อคลิกจะเปิด Modal ปฏิทินขนาดใหญ่ซ้อนทับขึ้นมา
*   **Job Carousel (ม้าหมุนรายการงาน):** แผงหมุนวนรายละเอียดของงานในเดือนนั้นๆ อัตโนมัติ:
    *   **การเคลื่อนไหว (Timing):** เลื่อนสไลด์จากซ้ายไปขวา (Slide Transition) โดยใช้เวลาเปลี่ยนผ่าน 0.4 วินาที และจะหยุดแสดงข้อมูลค้างไว้ 3.5 วินาทีต่อหนึ่งสไลด์งาน
    *   **รายละเอียดสไลด์งาน:** แสดงชื่องาน, ช่วงเวลา, และสถานะของงาน
*   **แผงข้อมูล Footer การ์ดปฏิทิน:**
    *   **วันที่ขนาดใหญ่ (Date Highlight):** แสดงตัวเลขวันที่ตัวหนาขนาดใหญ่ เช่น `02` (แทนที่ตัวเลขที่นั่งว่าง 158 เดิม)
    *   **เดือนและวัน (Day & Month Label):** แสดงตัวหนังสือ เช่น `Mon, Oct` ด้านล่างวันที่ (แทนที่ข้อความ seats available เดิม)
    *   ข้อมูลวันที่และข้อความนี้ต้องสลับค่าสอดคล้องตามรายการงานที่ม้าหมุนกำลังแสดงผลอยู่ในขณะนั้นด้วยแอนิเมชันเฟดเข้า-ออก (Opacity transition) ที่นุ่มนวล
*   **ปุ่มวงกลมแอคชั่นขวาล่าง:**
    *   สลับเฉดสีพื้นหลังและสีเงาเรืองแสงสอดรับตามสถานะของงานบนสไลด์ปัจจุบันโดยอัตโนมัติ:
        *   สถานะ **Paid**: พื้นหลังสีเขียวพาสเทล (`--color-pastel-green`), เงาสีเขียวเรืองแสงจาง (`0 8px 24px rgba(162, 232, 196, 0.45)`)
        *   สถานะ **Booked**: พื้นหลังสีเหลืองพาสเทล (`--color-pastel-yellow`), เงาสีเหลืองเรืองแสงจาง (`0 8px 24px rgba(253, 230, 138, 0.45)`)
        *   สถานะ **Urgent/Active**: พื้นหลังสีชมพูอมแดงสด (`--color-neon-rose`), เงาสีชมพูเรืองแสงจาง (`0 8px 24px rgba(255, 75, 114, 0.45)`)

### 2.5 ปุ่มแอคชั่นทรงกลม (Circle Action Buttons)
*   **การอัปเดตสไตล์และเงาเรืองแสงกลมกลืน (`.btn-circle-action`):**
    *   `background: linear-gradient(135deg, var(--color-neon-rose) 0%, var(--color-violet) 100%);` (การไล่เฉดสีจากชมพูอมแดงสดไปม่วงสดเพื่อความสว่างแบบโฮโลแกรม)
    *   `box-shadow: 0 8px 24px rgba(255, 75, 114, 0.45);` (เงาฟุ้งเรืองแสงนุ่มนวลสีชมพูแดง)
    *   **เอฟเฟกต์เมื่อ Hover (`.btn-circle-action:hover`):**
        *   `transform: translateY(-2px) scale(1.05);` (ยกตัวขึ้นเล็กน้อยและขยายตัวนิดๆ)
        *   `box-shadow: 0 12px 28px rgba(255, 75, 114, 0.55), 0 4px 12px rgba(143, 61, 255, 0.25);` (เรืองแสงเข้มข้นขึ้นสองชั้น)

### 2.6 แอนิเมชันขยายร่างและปฏิทินขนาดใหญ่ (Expanding Modal Transition & Big Calendar Modal)
*   **แอนิเมชันซูมขยายร่าง (Expanding Transition):**
    *   เมื่อคลิกเปิดปฏิทินมินิ โครงร่างหน้าต่างปฏิทินขนาดใหญ่ (`.calendar-modal`) จะขยายขนาดขึ้นมาจาก 0 เป็น 1 (`transform: scale(0) -> scale(1)`)
    *   **จุดกำเนิดแอนิเมชัน (Origin Target):** ตั้งค่า `transform-origin` แบบไดนามิกผ่าน JavaScript โดยอ้างอิงพิกัดจุดกึ่งกลางของการ์ดปฏิทิน Slot Card เพื่อให้ผู้ใช้รู้สึกว่า Modal นี้พุ่งขยายร่างออกมาจากตัวกล่องเดิมจริง
    *   ใช้วิธีเปลี่ยนผ่านด้วย `transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s ease;` เพื่อให้เกิดจังหวะเด้งเบาๆ (Elastic Bounce) ที่ดูพรีเมียม
*   **ปฏิทินขนาดใหญ่ด้านใน (Big Calendar Structure):**
    *   **ฉากหลังหน้าต่าง:** สไตล์กระจกฝ้าโปร่งแสง (`background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(25px); border: 1px solid rgba(255, 255, 255, 0.5);`)
    *   **หัวข้อเดือนและสัปดาห์:** แสดงชื่องานพร้อมปุ่มเปลี่ยนเดือน และหัวตารางแสดงวันจันทร์ถึงอาทิตย์ (`Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`) โดยใช้ฟอนต์ Outfit
    *   **ตารางวัน (Grid 1-31):** แสดงตัวเลขวันที่ครบถ้วน 1-31 ช่อง ในตารางสี่เหลี่ยมโค้งมนสวยงาม
    *   **การกำกับงาน (Job Labels):** ในช่องวันที่มีการจองงานไว้ ให้แสดงแถบสีข้อความ (Job Pill) ชื่องานสอดคล้องตามโทนสีสถานะของงานจริง (Paid = เขียว, Booked = เหลือง, Urgent = ชมพู)
    *   **ปุ่มปิดหน้าต่าง (Close Button):** ปุ่มกลมเล็กใช้ไอคอนกากบาทเวกเตอร์ SVG ห้ามใช้อีโมจิหรืออักษรธรรมดา x เพื่อความสวยงามสะอาดตา

---

## 3. พิกัดโค้ด CSS สำหรับหน้าเว็บจริง (CSS Stylesheet Specifications)

นี่คือบล็อกโค้ด CSS ที่ดีไซเนอร์ระบุให้คุณเก่งและคุณเฟิสตรวจสอบ และมอบหมายให้น้องคิว (Q) นำไปอัปเดตในสไตล์ชีตหลัก:

```css
/* ==========================================================================
   BLUEPRINT SPEC: COLOR HARMONIZATION RULES & DYNAMIC CALENDAR ANIMATION
   ========================================================================= */

/* 1. Sidebar Nav Items & Lang Switch */
.nav-item.active {
  background-color: var(--color-neon-rose) !important;
  color: var(--color-white) !important;
  box-shadow: 0 8px 20px rgba(255, 75, 114, 0.35) !important;
}

.nav-item:not(.active):hover {
  background-color: var(--color-ice-blue) !important;
  color: var(--color-neon-rose) !important;
}

.lang-switch-capsule {
  background-color: var(--color-ice-blue) !important;
  border: 1px solid rgba(255, 75, 114, 0.15) !important;
}

.lang-label {
  color: var(--color-neon-rose) !important;
}

.toggle-circle {
  background-color: var(--color-white) !important;
  box-shadow: 0 2px 5px rgba(255, 75, 114, 0.15) !important;
}

/* 2. Hero Banner Back/Next & Overlay Detail */
.capsule-btn {
  border: 1px solid var(--color-ice-blue) !important;
}

.capsule-btn:hover {
  background: var(--color-neon-rose) !important;
  border-color: var(--color-neon-rose) !important;
  color: var(--color-white) !important;
  transform: translateY(-1px);
}

.capsule-btn:hover .icon {
  color: var(--color-white) !important;
}

.date-month, .date-day {
  color: var(--color-neon-rose) !important;
}

.btn-icon:hover {
  color: var(--color-neon-rose) !important;
}

/* 3. Promo Tags Capsules */
.promo-tags .tag-capsule:nth-child(1) {
  background-color: rgba(255, 75, 114, 0.12) !important;
  color: var(--color-neon-rose) !important;
  border: 1px solid rgba(255, 75, 114, 0.25) !important;
}

.promo-tags .tag-capsule:nth-child(2) {
  background-color: rgba(179, 221, 242, 0.3) !important;
  color: #bf8eff !important;
  border: 1px solid rgba(179, 221, 242, 0.5) !important;
}

.promo-tags .tag-capsule:nth-child(3) {
  background-color: var(--color-white) !important;
  color: var(--color-text-secondary) !important;
  border: 1px solid var(--color-ice-blue) !important;
}

/* 4. Dynamic Calendar Slider & Mini Calendar Grid */
.month-slider {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 14px 0;
  background: var(--color-card-bg);
  padding: 4px;
  border-radius: 9999px;
  border: 1px solid var(--color-border-light);
}

.month-btn {
  flex: 1;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 9999px;
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 800;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.25s ease;
}

.month-btn.active {
  background: var(--color-neon-rose) !important;
  color: var(--color-white) !important;
  box-shadow: 0 4px 10px rgba(255, 75, 114, 0.25) !important;
}

.month-btn:not(.active):hover {
  color: var(--color-neon-rose);
}

.mini-calendar-container {
  background: var(--color-card-bg);
  padding: 14px 12px;
  border-radius: 18px;
  border: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-calendar-container:hover {
  border-color: var(--color-text-secondary);
  box-shadow: 0 6px 16px rgba(143, 61, 255, 0.06);
  transform: translateY(-1px);
}

.mini-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  flex: 1;
  justify-items: center;
}

.cal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-white);
  border: 1px solid var(--color-border-light);
  transition: all 0.2s ease;
}

.cal-dot.status-active {
  background-color: var(--color-neon-rose) !important;
  border: none !important;
  box-shadow: 0 0 6px var(--color-neon-rose) !important;
}

.cal-dot.status-paid {
  background-color: var(--color-pastel-green) !important;
  border: none !important;
  box-shadow: 0 0 6px var(--color-pastel-green) !important;
}

.cal-dot.status-booked {
  background-color: var(--color-pastel-yellow) !important;
  border: none !important;
  box-shadow: 0 0 6px var(--color-pastel-yellow) !important;
}

/* 5. Job Carousel Layout & Animations */
.job-carousel-container {
  height: 85px;
  overflow: hidden;
  position: relative;
  margin: 12px 0 6px 0;
  border-radius: 12px;
  background: rgba(24, 26, 30, 0.02);
  border: 1px dashed var(--color-border-light);
}

.job-carousel-wrapper {
  display: flex;
  height: 100%;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.job-carousel-slide {
  min-width: 100%;
  height: 100%;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
}

.job-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.job-time {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.job-status-tag {
  font-size: 9px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.job-status-tag.status-active {
  background-color: rgba(255, 75, 114, 0.12);
  color: var(--color-neon-rose);
}

.job-status-tag.status-paid {
  background-color: rgba(162, 232, 196, 0.15);
  color: #27a873;
}

.job-status-tag.status-booked {
  background-color: rgba(253, 230, 138, 0.2);
  color: #b58900;
}

/* 6. Footer Animations & Dynamic Actions */
.slot-footer-details {
  display: flex;
  flex-direction: column;
  transition: opacity 0.3s ease;
}

.slot-footer-details.fade-out {
  opacity: 0;
}

.btn-circle-action.paid {
  background: var(--color-pastel-green) !important;
  color: var(--color-text-primary) !important;
  box-shadow: 0 8px 24px rgba(162, 232, 196, 0.45) !important;
}

.btn-circle-action.booked {
  background: var(--color-pastel-yellow) !important;
  color: var(--color-text-primary) !important;
  box-shadow: 0 8px 24px rgba(253, 230, 138, 0.45) !important;
}

.btn-circle-action.urgent {
  background: var(--color-neon-rose) !important;
  color: var(--color-white) !important;
  box-shadow: 0 8px 24px rgba(255, 75, 114, 0.45) !important;
}

/* 7. Large Calendar Modal (Expanding Glassmorphic Modal) */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(24, 26, 30, 0.2);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.4s ease;
}

.modal-overlay.show {
  opacity: 1;
  pointer-events: auto;
}

.calendar-modal {
  width: 720px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 28px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.08), 0 10px 30px rgba(143, 61, 255, 0.02);
  padding: 28px;
  transform: scale(0);
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.modal-overlay.show .calendar-modal {
  transform: scale(1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title-wrap {
  display: flex;
  flex-direction: column;
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 800;
  color: var(--color-text-primary);
}

.modal-subtitle {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
  margin-top: 2px;
}

.btn-close-modal {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--color-border-light);
  background: var(--color-white);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-close-modal:hover {
  border-color: var(--color-text-primary);
  color: var(--color-text-primary);
  transform: rotate(90deg);
}

.btn-close-modal .icon {
  width: 16px;
  height: 16px;
}

/* Big Calendar Grid & Tables */
.big-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
  background: rgba(24, 26, 30, 0.01);
  padding: 8px;
  border-radius: 18px;
  border: 1px solid var(--color-border-light);
}

.weekday-header {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 800;
  color: var(--color-text-secondary);
  text-align: center;
  padding: 6px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.day-cell {
  background: var(--color-white);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  min-height: 72px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.day-cell:hover {
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
  border-color: var(--color-text-secondary);
}

.day-number {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-secondary);
  align-self: flex-end;
}

.day-cell.today {
  border-color: var(--color-neon-rose);
  background: rgba(255, 75, 114, 0.02);
}

.day-cell.today .day-number {
  color: var(--color-neon-rose);
}

.day-cell.other-month {
  opacity: 0.35;
  background: rgba(24, 26, 30, 0.01);
}

.day-job-pill {
  font-size: 9.5px;
  font-weight: 700;
  padding: 2.5px 6px;
  border-radius: 6px;
  margin-top: 4px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  box-sizing: border-box;
}

.day-job-pill.status-active {
  background-color: rgba(255, 75, 114, 0.12);
  color: var(--color-neon-rose);
  border-left: 3px solid var(--color-neon-rose);
}

.day-job-pill.status-paid {
  background-color: rgba(162, 232, 196, 0.15);
  color: #27a873;
  border-left: 3px solid var(--color-pastel-green);
}

.day-job-pill.status-booked {
  background-color: rgba(253, 230, 138, 0.2);
  color: #b58900;
  border-left: 3px solid var(--color-pastel-yellow);
}
```

---

## 4. เกณฑ์การตรวจรับงาน (Verification & Acceptance Criteria)
1.  **Sidebar:**
    *   [ ] แถบ active เป็นสีชมพูอมแดงสด (Neon Rose: #ff4b72) ส่องแสงเงาเรืองแสงสีชมพู
    *   [ ] ไอคอนเมนูที่ Hover เปลี่ยนเป็นสีชมพูอมแดงสด (Neon Rose: #ff4b72)
    *   [ ] สวิตช์ภาษา 'Eng' ใช้พื้นหลังสีฟ้าไอซ์บลู ขอบสีชมพูจาง ตัวหนังสือสีชมพูอมแดงสด (Neon Rose) และเงาปุ่มกลมเป็นโทนชมพู
2.  **Hero Banner:**
    *   [ ] ปุ่ม Back/Next เมื่อชี้เมาส์ (Hover) เปลี่ยนเป็นสีชมพูอมแดงสด (Neon Rose)
    *   [ ] ตัวหนังสือเดือน/วันที่ในกล่อง Dungeon & Dragon เปลี่ยนเป็นสีชมพูอมแดงสด (Neon Rose)
    *   [ ] ไอคอนปุ่มถูกหัวใจ/ดาว/บุ๊คมาร์ก เปลี่ยนเป็นสีชมพูอมแดงสด (Neon Rose) เมื่อ Hover
3.  **Promo Card:**
    *   [ ] แท็กส่วนลดแยกความสว่างและสีอย่างกลมกลืน: 20% off (พื้นชมพูจาง ตัวหนังสือชมพูอมแดงสด), Free Popcorn (พื้นฟ้าไอซ์บลูจาง ตัวหนังสือม่วงพาสเทลอ่อน #bf8eff), 5% off (พื้นสีขาว กรอบฟ้าจาง)
4.  **Calendar Slot Card (ขวาบน):**
    *   [ ] Month Slider แสดงตัวเลือก Sep | Oct | Nov โดยเดือนที่ถูกเลือกจะมีพื้นสีชมพูอมแดงสดและตัวหนังสือสีขาว
    *   [ ] Mini Calendar Grid แสดงจุดกลม 30 จุด คละเฉดสีที่ถูกต้อง (ชมพูอมแดงสด `--color-neon-rose`, เขียวพาสเทล `--color-pastel-green`, เหลืองพาสเทล `--color-pastel-yellow`, และขาว/ขอบเทา) ไม่มีตัวเลขวัน
    *   [ ] Job Carousel หมุนวนข้อมูลงานในเดือนตารางอัตโนมัติจากซ้ายไปขวา ใช้เวลา Transition 0.4 วินาที และมีจังหวะหยุดค้าง 3.5 วินาทีต่อหน้าสไลด์
    *   [ ] แผง Footer สลับค่ารายละเอียดวันที่ขนาดใหญ่ ('02' ตัวหนาเข้ม) และคำกำกับด้านล่าง ('Mon, Oct') ตามข้อมูลของสไลด์งานที่ปรากฏจริงในม้าหมุน ผ่านแอนิเมชัน Opacity นุ่มนวล
    *   [ ] ปุ่มวงกลมแอคชั่นขวาล่างเปลี่ยนเฉดสีพื้นหลังและสีเงาเรืองแสงตกกระทบตามประเภทของสถานะสไลด์งานขณะนั้น (เขียวพาสเทลสำหรับ Paid / เหลืองพาสเทลสำหรับ Booked / ชมพูแดงสำหรับ Urgent)
5.  **Expanding Modal & Big Calendar:**
    *   [ ] เมื่อกดยังกล่องปฏิทินมินิ จะเปิดหน้าต่างปฏิทินแบบ Modal คลุมพื้นที่จอเบื้องหน้า
    *   [ ] แอนิเมชันเปิดแบบขยายร่าง (Scale 0 -> Scale 1) โดยมีจุดอ้างอิง `transform-origin` ออกมาจากตำแหน่งกล่อง Slot Card โดยตรง และมีพฤติกรรมเด้งดึ๋งนุ่มตา
    *   [ ] ตารางปฏิทินขนาดใหญ่ แสดงชื่อวันจันทร์-อาทิตย์, วันที่ 1-31, แถบระบุงาน (Job Pill) สวยงามมีสีสันตรงตามสถานะงาน
    *   [ ] ไม่มีปุ่มสัญลักษณ์ หรือเนื้อหาใดๆ ที่ใช้ **อีโมจิ** เป็นหน้าตาไอคอนหรือตกแต่ง (ปุ่มปิด Modal ต้องใช้สัญลักษณ์ SVG กากบาทเท่านั้น)

---
*จัดเตรียมโดย: ดี (D) — ผู้อำนวยการฝ่ายศิลป์และดีไซเนอร์ UI/UX ของ ChZ Agent Corp*
