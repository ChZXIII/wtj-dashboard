# 📖 คู่มืออย่างเป็นทางการ: Google Antigravity
*(Source: NotebookLM ของแก — อัปเดต 2026-05-20)*

---

### 1. การใช้งาน Antigravity 2.0 (Desktop Application)

**การเริ่มต้นโปรเจกต์และการตั้งค่า**
- สร้างโปรเจกต์: เพิ่มโฟลเดอร์หรือ Git Repositories เป็นพื้นที่ทำงานให้ Agent
- ติดตั้งปลั๊กอิน: Skills และปลั๊กอินสำหรับ Google products (Chrome Dev Tools ฯลฯ)
- ความปลอดภัย: ตั้งค่า Accept / Reject / Whitelist คำสั่ง + Sandboxing + Network permission

**ฟีเจอร์หลัก**
- **สั่งงานด้วยเสียง:** มีปุ่มไมโครโฟน
- **Artifacts & Implementation Plan:** AI สร้างแผนงาน → คอมเมนต์ได้ก่อนเริ่ม
- **Sub-agents:** ทำงานแบบขนาน (Frontend + Backend + QA พร้อมกัน) มี Overview window
- **New Work Tree:** ทดลองไอเดียใหม่โดยไม่กวนงานหลัก (copy โค้ดไปทำในโฟลเดอร์ใหม่)
- **Browser Testing:** `/browser` → AI เข้าเบราว์เซอร์ทดสอบโปรเจกต์เอง
- **Scheduled Tasks:** ตั้งเวลารัน prompt ล่วงหน้า (เช่น ตี 5 ทุกวัน) ทำงาน background ได้แม้ปิดแอป

---

### 2. การใช้งาน Antigravity CLI (Terminal)

**เบื้องต้น**
- `-p` flag: เริ่ม prompt ได้ทันทีตอนเปิด CLI (ใช้ใน pipeline / cron job)
- `agy -c`: กลับเข้าเซสชันเดิมที่ค้างไว้
- Export to GUI: ส่งจาก CLI → Antigravity 2.0 ได้ในคำสั่งเดียว

**Slash Commands สำคัญ**
- `/BTW`: ถามแทรกขณะ Agent ทำงานอยู่ โดยไม่ interrupt งาน
- `/fork`: แยก branch การสนทนาเพื่อลองแนวทางใหม่
- `/diff`: ดูการเปลี่ยนแปลงโค้ดที่ Agent แก้ไข
- `/artifacts`: ดู walkthrough และแผนงานที่ Agent สร้าง
- `/agents`: ดูสถานะ / สร้าง Sub-agents
- `/config`: ตั้งค่า (สี, render mode, permission แบบ strict)

---

### 3. Antigravity SDK (Python)

- สร้าง Custom Agent ในโปรเจกต์ Python
- Policy Engine: กำหนดว่า Agent รัน tool ใดได้บ้าง (รวมถึง YOLO mode)
- Trigger system: AI จับตาเหตุการณ์ background แล้วแจ้งเตือนเมื่อต้องการ

---

### 4. Agent Skills

**ทำไมต้องมี Skills?**
แก้ปัญหา **Context Bloat** — การป้อนข้อมูลมากเกินไปจนเสีย Token และทำให้โมเดลสับสน
Skills จะโหลดบริบทเฉพาะทางให้ Agent **เฉพาะเมื่อจำเป็น**

**โครงสร้างไฟล์**
```
.agent/
  skills/
    [ชื่อ-skill]/
      skill.md       ← ไฟล์หลัก
      (ไฟล์อื่นๆ ที่เกี่ยวข้อง)
```

**วิธีเขียน skill.md**
```markdown
---
name: ชื่อ Skill
description: อธิบายว่า Skill นี้ทำอะไร (AI ใช้ส่วนนี้ตัดสินใจว่าจะโหลด Skill ไหม)
---

เนื้อหา SOP / คำสั่ง / ขั้นตอนการทำงาน...
```

**แหล่งหา Skills**
- สร้างเอง: บอก AI ให้ช่วยสร้าง `skill.md` ที่เหมาะกับโปรเจกต์
- แชร์ทีม: ส่งผ่าน Git Repo ได้เลย
- Marketplace: ดาวน์โหลดจาก `agentskills.io` → ติดตั้งผ่าน `skills.sh`
