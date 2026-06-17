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

LEARNING_BASE_PATH = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "workspace", "learning_base.json")

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
        
        # ข้ามถ้าเรียนรู้ไปแล้ว
        if page_id in learned_ids:
            continue
            
        print(f"[{i+1}/{len(pages)}] 📝 กำลังพิจารณาเรียนรู้จากหัวข้อ: '{title}'")
        
        # 3. ดึงเนื้อหาภายในเพจ Notion
        raw_body = notion.get_page_content_text(page_id)
        if not raw_body or len(raw_body.strip()) < 10:
            print(f"⚠️ ข้าม: หน้า '{title}' ไม่มีเนื้อหาในเพจ")
            continue
            
        # สกัดชื่อไฟล์วิดีโอเพื่อหาไฟล์สำรอง
        body_lines = [l.strip() for l in raw_body.splitlines() if l.strip()]
        first_line_body = body_lines[0] if body_lines else ""
        
        video_filename = None
        if first_line_body:
            clean_first = re.sub(r'^Headline\s+', '', first_line_body, flags=re.IGNORECASE).strip()
            # สกัดหาชื่อไฟล์
            match_file = re.search(r'\]\s*(.*\.(?:mp4|mov|mkv|avi|webm))', clean_first, re.IGNORECASE)
            if match_file:
                video_filename = match_file.group(1).strip()
            elif any(clean_first.lower().endswith(ext) for ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm']):
                video_filename = clean_first
                
        if not video_filename:
            match_file = re.search(r'\]\s*(.*\.(?:mp4|mov|mkv|avi|webm))', title, re.IGNORECASE)
            if match_file:
                video_filename = match_file.group(1).strip()
            elif any(title.lower().endswith(ext) for ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm']):
                video_filename = title

        # ดึงประเภทคิวงานจากหัวข้อ (เช่น [YT_Videos_Full Video Draft] -> YT_Videos_Full)
        match_queue = re.match(r'^\[([\w\-]+)(?:\s+Video\s+Draft)?\]', title)
        queue_name = match_queue.group(1) if match_queue else "YT_Videos_Full"
        if "Spoiler" in title:
            queue_name = "Spoiler"
            
        # 4. โหลดดราฟต์แรกสุดของบอทจากไฟล์สำรองในเครื่อง (Local Backup)
        draft_options = None
        if video_filename:
            file_slug = re.sub(r'[^\w\s-]', '', video_filename).strip().replace(" ", "_").lower()
            backup_filename = f"{queue_name.lower()}_from_video_{file_slug}.md"
            
            search_dirs = [
                os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "2_drafts"),
                os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Podcast", "workspace", "2_drafts"),
                os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "workspace", "2_drafts")
            ]
            
            for d in search_dirs:
                p = os.path.join(d, backup_filename)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            draft_options = f.read().strip()
                            break
                    except Exception as e:
                        print(f"⚠️ ไม่สามารถอ่านไฟล์สำรองได้: {p} - {e}")
                        
        # 5. สกัดหาข้อความที่พี่เก่งเกลาอนุมัติ (Final Approved Copy จาก Notion Page Body)
        # โดยการลบบรรทัดแรกสุดที่เป็น Headline บอกทางออกไป
        content_lines = raw_body.splitlines()
        if content_lines and first_line_body and (first_line_body in content_lines[0] or any(ext in content_lines[0].lower() for ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm'])):
            content_lines = content_lines[1:]
        final_approved = "\n".join(content_lines).strip()
            
        # เช็คความสมบูรณ์ของข้อมูลก่อนบันทึก
        if not draft_options or len(draft_options) < 10:
            print(f"⚠️ ข้าม: หาดราฟต์ต้นฉบับสำรองในโฟลเดอร์ 2_drafts ไม่พบสำหรับ '{video_filename}'")
            continue
            
        if not final_approved or len(final_approved) < 10 or final_approved == draft_options:
            print(f"⚠️ ข้าม: ไม่มีตัวอย่างข้อความที่พี่เก่งตรวจแก้ไขเพิ่มเติม (หรือข้อความเหมือนดราฟต์แรก)")
            continue
            
        # 6. ดึงทรานสคริปต์ย่อเพื่อเป็นบริบท (Context)
        transcript_snippet = final_approved.split("\n\n")[0][:500].strip()
        
        # 7. เพิ่มเข้าคลังเรียนรู้
        learning_base.append({
            "page_id": page_id,
            "title": title,
            "transcript_snippet": transcript_snippet,
            "original_drafts": draft_options,
            "final_approved_copy": final_approved,
            "learned_at": True
        })
        
        print(f"✨ เรียนรู้สไตล์การเกลาคำสำเร็จแล้วแก! (เปรียบเทียบดราฟต์ต้นฉบับ ➔ ข้อความเกลาเสร็จของพี่เก่ง)")
        new_learnings += 1
        
    if new_learnings > 0:
        save_learning_base(learning_base)
        print(f"\n🎉 ระบบเรียนรู้ทำการสอนงานน้องๆ สำเร็จเสร็จสิ้น! เพิ่มตัวอย่างใหม่ {new_learnings} รายการ 🧠✨")
    else:
        print("\n😴 ไม่มีตัวอย่างใหม่ให้เรียนรู้เพิ่มเติมแก (บอทฉลาดอัปเดตสุดเท่าที่มีแล้ว)")

if __name__ == "__main__":
    run_learning_loop()
