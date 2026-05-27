#!/usr/bin/env python3
import os
import sys
import json
import re

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from notion_helper import NotionHelper

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

LEARNING_BASE_PATH = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "workspace", "learning_base.json")

def load_learning_base():
    if os.path.exists(LEARNING_BASE_PATH):
        try:
            with open(LEARNING_BASE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: ไม่สามารถอ่าน learning_base.json ได้: {e}")
            return []
    return []

def save_learning_base(data):
    # Keep only the last 30 entries to prevent memory/prompt bloat
    trimmed_data = data[-30:]
    try:
        os.makedirs(os.path.dirname(LEARNING_BASE_PATH), exist_ok=True)
        with open(LEARNING_BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(trimmed_data, f, ensure_ascii=False, indent=2)
        print(f"💾 บันทึกคลังการเรียนรู้สำเร็จ มีทั้งหมด {len(trimmed_data)} ตัวอย่างที่: {LEARNING_BASE_PATH}")
        return True
    except Exception as e:
        print(f"❌ Error: ไม่สามารถเขียนไฟล์ learning_base.json ได้: {e}")
        return False

def run_learning_loop():
    print("==================================================")
    print("🦉 เลขาเฟิส: เริ่มระบบวิเคราะห์ประวัติการเกลาคำของพี่เก่งจาก Notion 🧠")
    print("==================================================\n")
    
    notion = NotionHelper()
    
    # 1. โหลดประวัติการเรียนรู้ที่มีอยู่
    learning_base = load_learning_base()
    learned_ids = {item.get("page_id") for item in learning_base if item.get("page_id")}
    
    # 2. ดึงหน้าเพจทั้งหมดในสถานะ 6_Published และ 5_Approved
    print("🔍 กำลังดึงรายการที่มีสถานะ '6_Published' และ '5_Approved' จาก Notion...")
    pages_pub = notion.fetch_pages_by_status("6_Published") or []
    pages_app = notion.fetch_pages_by_status("5_Approved") or []
    pages = pages_pub + pages_app
    
    if not pages:
        print("📭 ไม่พบโพสต์ในสถานะ '6_Published' หรือ '5_Approved' เลยแก!")
        return
        
    print(f"📌 ตรวจพบทรานแซกชันที่อนุมัติ/เผยแพร่แล้วทั้งหมด {len(pages)} หัวข้อ\n")
    
    new_learnings = 0
    
    for i, page in enumerate(pages):
        page_id = page["id"]
        title = page["title"]
        approved_copy = page["approved_copy"]
        
        # ข้ามถ้าเรียนรู้ไปแล้ว
        if page_id in learned_ids:
            continue
            
        print(f"[{i+1}/{len(pages)}] 📝 กำลังเรียนรู้จากหัวข้อ: '{title}'")
        
        # 3. ดึงเนื้อหาภายในเพจ Notion
        raw_body = notion.get_page_content_text(page_id)
        if not raw_body or len(raw_body.strip()) < 10:
            print(f"⚠️ ข้าม: หน้า '{title}' ไม่มีเนื้อหาในเพจ")
            continue
            
        # 4. สกัดหาดราฟต์ตั้งต้น (Draft Options) ที่บอทเขียน
        draft_options = ""
        draft_headers = [
            "## 📝 Draft Options",
            "## 📝 Draft Options (โดย ทีม Content Agent)",
            "Draft Options"
        ]
        
        for header in draft_headers:
            if header in raw_body:
                parts = raw_body.split(header, 1)
                draft_options = parts[1].strip()
                break
                
        # หากหาจากหัวข้อตรงๆ ไม่เจอ ให้ลองใช้ regex หรือเช็คคำว่า "ทางเลือก"
        if not draft_options:
            match = re.search(r'(##?\s*.*?Draft.*?)\n(.*)', raw_body, re.DOTALL | re.IGNORECASE)
            if match:
                draft_options = match.group(2).strip()
            elif "ทางเลือกที่ 1" in raw_body or "Option 1" in raw_body or "ทางเลือก" in raw_body:
                draft_options = raw_body.strip()
                
        # 5. สกัดหาข้อความที่พี่เก่งอนุมัติ (Final Approved Copy)
        final_approved = approved_copy.strip() if approved_copy else ""
        
        # หาก approved_copy ว่าง ให้ดึงจากเนื้อหาก่อนแบ่ง Draft Options
        if not final_approved:
            # ใช้เนื้อหาครึ่งแรกก่อนถึงสัญลักษณ์แยก
            first_part = raw_body
            if "## 📝 Draft Options" in first_part:
                first_part = first_part.split("## 📝 Draft Options")[0].strip()
            if "---" in first_part:
                first_part = first_part.split("---")[0].strip()
            
            final_approved = first_part.strip()
            
        # เช็คความสมบูรณ์ของข้อมูลก่อนบันทึก
        if not draft_options or len(draft_options) < 10:
            print(f"⚠️ ข้าม: หาดราฟต์ต้นฉบับในเพจไม่พบ")
            continue
            
        if not final_approved or len(final_approved) < 10 or final_approved == raw_body.strip():
            # ถ้าสุดท้ายดันได้ตัวเดิมหรือไม่มีการแก้ไขเลย อาจจะข้าม
            print(f"⚠️ ข้าม: ไม่มีตัวอย่างข้อความที่พี่เก่งตรวจ/อนุมัติที่เป็นชิ้นเป็นอัน")
            continue
            
        # 6. ดึงทรานสคริปต์ย่อ เพื่อเป็นคอนเทกต์สั้นๆ
        # เอาเนื้อหาตอนบนสุดของเพจ หรือ 500 ตัวแรกมาเป็นไกด์
        transcript_snippet = raw_body.split("\n\n")[0][:500].strip()
        
        # 7. เพิ่มเข้าคลังเรียนรู้
        learning_base.append({
            "page_id": page_id,
            "title": title,
            "transcript_snippet": transcript_snippet,
            "original_drafts": draft_options,
            "final_approved_copy": final_approved,
            "learned_at": True
        })
        
        print(f"✨ เรียนรู้สไตล์สำเร็จ! จับคู่ (ดราฟต์เดิม ➔ ข้อความสุดท้ายหลังเกลา)")
        new_learnings += 1
        
    if new_learnings > 0:
        save_learning_base(learning_base)
        print(f"\n🎉 ระบบเรียนรู้ทำการสอนงานน้องๆ สำเร็จเสร็จสิ้น! เพิ่มตัวอย่างใหม่ {new_learnings} รายการ 🧠✨")
    else:
        print("\n😴 ไม่มีตัวอย่างใหม่ให้เรียนรู้เพิ่มเติมแก (บอทฉลาดอัปเดตสุดเท่าที่มีแล้ว)")

if __name__ == "__main__":
    run_learning_loop()
