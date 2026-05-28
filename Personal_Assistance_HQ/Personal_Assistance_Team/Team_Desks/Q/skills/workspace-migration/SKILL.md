---
name: workspace-migration
description: Guidelines and procedure for migrating agent workspaces, source files, and credentials from an old path to a new path. Includes updating LaunchAgents on macOS for cron/daemon automation and workspace cleanup.
---

# Skill: Workspace Migration & Reorganization (Mac OS)

ใช้เมื่อต้องการกู้คืน ย้าย หรือจัดสัดส่วนห้องทำงาน (Workspace) ของทีมงานเอเจนต์ทั้งหมดไปยังโฟลเดอร์/พิกัดเส้นทางใหม่โดยไม่ให้ท่อระบบหลังบ้านพัง

---

## 📋 1. การย้ายไฟล์และกุญแจความปลอดภัย (Safe Copy & Keys)
1. **คัดลอกโฟลเดอร์โครงการ:** ใช้ `cp -R` หรือ `rsync` ย้ายโค้ดต้นฉบับและ Sub-workspace ไปยังพิกัดใหม่
2. **กู้คืนคีย์ความปลอดภัย:** ตรวจสอบและดึงไฟล์ความลับ/State จากตึกเก่ามาใส่ในตึกใหม่ให้ครบถ้วน:
   - `token.json` / `token_sheets.json` (Google API Tokens)
   - `client_secret.json` (Google Client Secret)
   - `trade_sync_state.json` (บอทเทรดคริปโต)
   - `.env` (ไฟล์ Config สิทธิ์การเข้าถึงต่างๆ)

---

## ⚙️ 2. การเปลี่ยนท่อระบบเบื้องหลังของ Mac (Mac LaunchAgents Update)
หากบอทมีการตั้งค่าแบบ Scheduler ให้รันงานอัตโนมัติรายวันผ่าน macOS LaunchAgents (`launchd`) เราต้องปรับแต่งพาธการทำงานในไฟล์ `.plist` ให้ตรงกับพิกัดโฟลเดอร์ใหม่ดังนี้:

### 1. ค้นหาไฟล์ plist ของระบบ
ไฟล์จะถูกเก็บไว้ที่: `/Users/chz/Library/LaunchAgents/`
* **ตัวอย่างไฟล์ในระบบ:** `com.antigravity.jane.plist`, `com.antigravity.win.plist`, `com.wtj.m.dashboard.updater.plist`

### 2. แก้ไขพาธในไฟล์ plist
เปิดไฟล์ `.plist` และอัปเดตเส้นทางพาธ 3 จุดหลัก:
* **ProgramArguments (จุดที่ 1 - Python Path):** ชี้ไปที่ `venv` ของตึกใหม่
* **ProgramArguments (จุดที่ 2 - Script Path):** ชี้ไปที่ไฟล์สคริปต์ในตึกใหม่
* **WorkingDirectory:** เปลี่ยนเป็นเส้นทางโฟลเดอร์ใหม่
* **StandardOutPath / StandardErrorPath:** เปลี่ยนที่เก็บไฟล์ Log ให้ไปอยู่ที่ห้องทำงานใหม่

```xml
<!-- ตัวอย่างการแก้ไข -->
<key>ProgramArguments</key>
<array>
    <string>/Users/chz/Desktop/ChZ_Agent_Corp/venv/bin/python3</string>
    <string>/Users/chz/Desktop/ChZ_Agent_Corp/Team_Content_Studio/Team_Agent_Content/skills/grab_receipt_sync.py</string>
</array>
<key>WorkingDirectory</key>
<string>/Users/chz/Desktop/ChZ_Agent_Corp</string>
```

### 3. คำสั่งยกเลิกตัวเก่าและลงทะเบียนตัวใหม่ (Unload & Load)
เมื่อแก้ไขไฟล์เสร็จแล้ว ต้องสั่งรีสตาร์ทตัว Agent ใน macOS ให้รับรู้ค่าใหม่:
```bash
# ยกเลิกตารางงานเก่า
launchctl unload ~/Library/LaunchAgents/com.example.agent.plist

# ลงทะเบียนตารางงานใหม่
launchctl load ~/Library/LaunchAgents/com.example.agent.plist
```

---

## 🧪 3. การตรวจสอบความถูกต้องก่อนลบตึกเก่า (Verification Check)
1. **รันเทสสคริปต์รายคน:**
   - เจน: รันเช็ค `grab_receipt_sync.py`
   - วิน: รันเช็ค `crypto_portfolio_sync.py`
2. **เช็ค Log ของ LaunchAgents:** ตรวจสอบว่าหลังจากรันแล้ว log file ในพิกัดใหม่ถูกสร้างขึ้นมาจริงและไม่แสดง Error
3. **การลบโฟลเดอร์เก่า:** เมื่อพรูฟความพร้อมผ่านการรันเทส 100% แล้ว จึงจะทำลายล้างโฟลเดอร์นอกตึกและบน Desktop ที่ไม่ได้ใช้งานเพื่อความสะอาดคลีนของหน้าจอ
