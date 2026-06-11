# Skill: ส่ง Note เข้า Apple Notes (ANTIA)

---

## วิธีใช้ Skill นี้

ใช้เมื่อต้องการส่ง script หรือเนื้อหาคอร์สเข้า Apple Notes โดยจัดโครงสร้างโฟลเดอร์ตามช่อง ANTIA และแยก Subfolder ตาม Lesson

---

## โครงสร้างโฟลเดอร์ใน Apple Notes

```
📁 ANTIA
  └── 📁 Lesson 0
        └── 📝 [ชื่อ Note]
  └── 📁 Lesson 1
        └── 📝 [ชื่อ Note]
  └── 📁 Lesson N
        └── 📝 [ชื่อ Note]
```

---

## กฎการจัดหน้า (Formatting Rules)

1. **ใช้ HTML** ใส่ใน `body` ของ Note เสมอ — Apple Notes รองรับ HTML subset
2. **เว้น 1 บรรทัดก่อนหัวข้อใหญ่ทุกครั้ง** โดยใส่ `<br>` ก่อน `<h2>` เสมอ
3. **หัวข้อหลัก** ใช้ `<h1>` — มีแค่ตัวเดียวต่อ Note (ชื่อ Note)
4. **หัวข้อ Section** ใช้ `<h2>` — นำหน้าด้วย `<br>` ทุกครั้ง
5. **ย่อหน้า** ใช้ `<p>...</p>` เสมอ ห้ามใส่ข้อความลอยๆ
6. **ขึ้นบรรทัดใหม่ในย่อหน้าเดิม** ใช้ `<br>` 
7. **ตัวหนา** ใช้ `<b>...</b>` สำหรับคำสำคัญ
8. **ตัวเอียง** ใช้ `<i>...</i>` สำหรับ stage direction หรือหมายเหตุ
9. **Numbered list** ใช้ `<ol><li>...</li></ol>`
10. **Bullet list** ใช้ `<ul><li>...</li></ul>`
11. **`&amp;`** แทน `&`, **`&nbsp;`** แทน non-breaking space

---

## Template AppleScript

```applescript
set htmlContent to "[HTML ของ note ที่นี่]"
set targetFolder to "ANTIA"        -- ชื่อ folder หลัก
set targetSubFolder to "Lesson 0"  -- ชื่อ subfolder
set noteName to "ชื่อ Note"        -- ชื่อ note

tell application "Notes"
    -- หา / สร้าง folder หลัก
    set mainFolder to missing value
    repeat with f in folders
        if name of f is targetFolder then
            set mainFolder to f
            exit repeat
        end if
    end repeat
    if mainFolder is missing value then
        set mainFolder to make new folder with properties {name:targetFolder}
    end if

    -- หา / สร้าง subfolder
    set subFolder to missing value
    repeat with f in folders of mainFolder
        if name of f is targetSubFolder then
            set subFolder to f
            exit repeat
        end if
    end repeat
    if subFolder is missing value then
        set subFolder to make new folder with properties {name:targetSubFolder} at mainFolder
    end if

    -- ลบ note เก่าที่ชื่อซ้ำ แล้วสร้างใหม่
    repeat with n in notes of subFolder
        if name of n is noteName then
            delete n
        end if
    end repeat

    make new note at subFolder with properties {name:noteName, body:htmlContent}
end tell
```

---

## HTML Template สำหรับ Script คอร์ส

```html
<h1>🎬 [ชื่อ Lesson]</h1>

<p><b>คอร์ส:</b> AI ทำงานแทนคุณ ด้วย Antigravity &nbsp;|&nbsp; <b>ช่อง:</b> ANTIA &nbsp;|&nbsp; <b>ความยาว:</b> X–Y นาที</p>
<p><b>สไตล์:</b> Teleprompter &nbsp;|&nbsp; <b>โทน:</b> ตรงไปตรงมา ไม่อ้อมค้อม</p>

<br><h2>🎙 INTRO — 0:00–X:XX</h2>
<p>...</p>

<br><h2>📌 SECTION 1 — [ชื่อ] — X:XX–X:XX</h2>
<p>...</p>

<br><h2>🏁 OUTRO — X:XX–X:XX</h2>
<p>...</p>

<br><h2>📌 Director's Notes</h2>
<p><b>X:XX–X:XX</b> → ...<br>
<b>X:XX–X:XX</b> → ...</p>

<p><i>อัปเดตล่าสุด: YYYY-MM-DD | เวอร์ชัน: v1.0</i></p>
```

---

## หมายเหตุ

- ถ้าจะ **อัปเดต** note เดิม ให้ลบ note เก่าก่อนแล้วสร้างใหม่ (AppleScript ไม่มี update body โดยตรงที่เสถียร)
- Folder ใน Apple Notes จะสร้างใหม่อัตโนมัติถ้ายังไม่มี ไม่ต้องสร้างเอง
- Test ใน Notes app ว่า HTML render ถูกต้องก่อน push จริง

---
*สร้าง: 2026-05-20 | ใช้ใน: Study_Course_Agent / ANTIA channel*
