---
name: facebook-draft-generator
description: Scans interview transcripts in Apple Notes, generates 3 distinct social media post options (using Ray, Nam, and Music's personas), routes them to correct target queues, and saves drafts back to Apple Notes.
---

# Skill: Facebook Draft Generator (Ray's Skill)

ใช้เมื่อพี่เก่งวางข้อความถอดเทปสัมภาษณ์ (Transcript) ของคลิปย่อยหรือตอนเด่นๆ ไว้ใน Apple Notes และต้องการแปลงเป็นโพสต์โปรโมตบน Facebook ทันที

---

## 🔍 1. การสแกนวัตถุดิบ (Scan & Extract)
1. **ค้นหาโน้ตต้นฉบับ:** ระบบจะมองหาโน้ตในแอป Apple Notes ที่ชื่อโน้ตขึ้นต้นด้วยคำว่า **`Transcript:`** หรือ **`Transcript`** (เช่น `Transcript: สัมภาษณ์น้องกอล์ฟ`)
2. **ดึงข้อความดิบ:** ดึงเนื้อหา HTML จาก Apple Notes และทำการเคลียร์ HTML tags ต่างๆ ออก เพื่อเตรียมส่งให้ AI นำไปแต่งบทความ

---

## 🧠 2. กระบวนการปั้นบทความร่วมกัน (Personas & Styles)
สคริปต์จะใช้โมเดลของ Ray (Writer), Nam (Creative), และ Music (Marketer) ร่วมกันร่างโพสต์ออกมา **3 ตัวเลือก (Options)** ที่แตกต่างสไตล์กันอย่างสิ้นเชิง โดยมีรายละเอียดดังนี้:

### การจัดเข้าคิวโพสต์อัจฉริยะ (Queue Routing)
บอทจะคัดเลือกว่าข้อความ Transcript นี้เหมาะกับคิวใดจาก 3 คิวนี้มากที่สุด:
- **`FB_Videos_3-5Min`**: สำหรับคลิปวิดีโอยาวปานกลาง เล่าเรื่องมีสาระรายละเอียด
- **`Reels_Under1Min`**: สำหรับคลิปสั้นแนว Reels/Shorts เปิดเรื่องสะดุดตา จบหักมุมรวดเร็ว
- **`Text_Posts`**: สำหรับคำคม โควทเด่น หรือหัวข้อชวนคุยสร้างปฏิสัมพันธ์กับผู้ติดตาม

### กฎการใช้ภาษาและโครงสร้างบทความ (Formatting Guidelines)
- **ห้ามใส่คำลงท้าย "ครับ/ค่ะ"** ในเนื้อหาโพสต์ปกติ (เว้นแต่เป็นคำพูดจริงของแขกรับเชิญ)
- เกริ่นนำในนามทีมงานเสมอ เช่น *"วันนี้พวกเราทีมงาน What the job..."*
- วิดีโอขนาดปกติและคลิปสั้น: สั่งให้คนดูตามไปกดดูลิงก์เต็มที่ **"บ้านแดง" (ปักหมุดใต้คอมเม้น)**
- **โครงสร้างโพสต์ Reels (Reels_Under1Min):** จะแบ่งเป็น 3 ส่วนย่อยชัดเจนในแต่ละตัวเลือก:
  1. 🎣 **HOOK (0-10s):** คำเปิดใจสะกดสายตา
  2. 🎥 **VISUAL CUE:** ท่าทางที่ผู้แสดงต้องทำในคลิป
  3. 🗣️ **NARRATION:** คำพูดจริงที่ต้องพูด
  4. 🏁 **CTA:** ชวนตามไปดูต่อที่บ้านแดง

---

## 💾 3. ผลลัพธ์และการจัดส่งเอกสาร (Backup & Apple Notes Deploy)
1. **บันทึกสำรองหลังบ้าน (Markdown):** บันทึกเป็นไฟล์ `.md` ยอดนิยมไว้ที่ `Team_Content_Studio/Team_Agent_Content/workspace/2_drafts/` เพื่อเป็นสำรองข้อมูลหลังบ้าน
2. **ส่งเข้า Apple Notes (Deploy):** ยิง AppleScript ไปสร้างโน้ตใหม่ใน Apple Notes ตามพิกัดโฟลเดอร์ของคิวนั้นๆ:
   - เส้นทาง: `WTJ` ➡️ `Facebook` ➡️ `{ชื่อคิว}` ➡️ `1_Drafts` ➡️ `[ชื่อโน้ตดราฟต์]`
   - โน้ตที่บันทึกแล้วจะพร้อมให้พี่เก่งตรวจ ปรับแต่ง และโพสต์ลงเพจได้ทันที

---

## 🧪 4. วิธีเรียกใช้งาน (Execution Command)
รันคำสั่งภายใต้โฟลเดอร์หลักของโปรเจกต์:
```bash
cd /Users/chz/Desktop/ChZ_Agent_Corp
./venv/bin/python3 Team_Content_Studio/Team_Agent_Content/skills/fb_draft_generator.py
```
> [!TIP]
> - ล็อกการรันระบบและตัวเลือกที่ปั้นเสร็จจะแสดงผลลัพธ์ผ่าน Terminal พร้อมทั้งส่งข้อความไปยัง Apple Notes เรียบร้อยใน 1 คลิก!
