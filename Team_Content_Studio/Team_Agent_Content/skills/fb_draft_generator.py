#!/usr/bin/env python3
import os
import sys
import re
import json
import google.generativeai as genai

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

def load_env():
    """Load env variables from the workspace .env file."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

# Add project root and current skills directory to system path
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if current_dir not in sys.path:
    sys.path.append(current_dir)

import model_router
from notion_helper import NotionHelper



def generate_social_posts(transcript_title, transcript_content):
    print("🧠 [Skill Generation] ส่งทรานสคริปต์ตอนย่อยให้เอเจนต์ (น้ำ, มิวสิค, เรย์) ร่วมกันปั้นโพสต์ระดับพรีเมียม...")
    
    # ดึงประวัติการเรียนรู้จากพี่เก่งมาเสริม
    learning_base_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "workspace", "learning_base.json")
    learning_examples_str = ""
    if os.path.exists(learning_base_path):
        try:
            with open(learning_base_path, "r", encoding="utf-8") as f:
                examples = json.load(f)
                if examples:
                    # ดึง 5 ตัวอย่างล่าสุดมาสอนบอท
                    latest_examples = examples[-5:]
                    learning_examples_str = "\n\n### 💡 ตัวอย่างสไตล์การเกลาคำและทางเลือกที่พี่เก่งเลือกแก้ล่าสุด (เรียนรู้และปรับตามด้านล่างนี้):\n"
                    for idx, ex in enumerate(latest_examples, 1):
                        learning_examples_str += f"""
---
ตัวอย่างที่ {idx}: เรื่อง "{ex.get('title')}"
[ดราฟต์ที่บอทเคยเสนอ]:
{ex.get('original_drafts')}

[เวอร์ชันที่พี่เก่งปรับปรุงและอนุมัติจริง]:
{ex.get('final_approved_copy')}
"""
                    learning_examples_str += "\n---"
                    print(f"📖 โหลดตัวอย่างประวัติการเกลาคำสำเร็จจำนวน {len(latest_examples)} รายการ ป้อนเข้าสู่สมองบอทแล้ว!")
        except Exception as e:
            print(f"⚠️ Warning: ไม่สามารถอ่าน learning_base.json มาเทรนบอทได้: {e}")

    system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น คิดคอนเซปต์สุดล้ำ), "มิวสิค" (Marketer สาววัยรุ่น ปั้นมีมและแคมเปญสุดจึ้ง) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: นำข้อความถอดเทปสัมภาษณ์ตอนย่อย (Sub-clip Transcript) หัวข้อ: "{transcript_title}" มาเขียนโพสต์ที่จึ้งและแตกต่างกัน เพื่อให้พี่เก่งได้เลือกอันที่ชอบที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์ทรานสคริปต์นี้ว่าเหมาะจะจัดเข้าคิวใดจาก 3 คิวนี้มากที่สุด:
   - `FB_Videos_3-5Min` (หากเป็นคลิปยาวปานกลาง เล่าเรื่อง มีสาระรายละเอียด)
   - `Reels_Under1Min` (หากเป็นคลิปสั้นแนว Reels/Shorts ตื่นเต้น หักมุม กระชับ มี Hook เด่นๆ)
   - `Text_Posts` (หากเป็นข้อความโควทคำคม หรือประเด็นชวนคุยที่เหมาะสำหรับโพสต์ข้อความถามแฟนเพจ)
2. เขียนระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: `[QUEUE: ชื่อคิว]` (เช่น `[QUEUE: Reels_Under1Min]`)
3. ร่างโพสต์ตามเงื่อนไขของคิวที่เลือกดังนี้:

A. หากเลือกคิว `FB_Videos_3-5Min` หรือ `Reels_Under1Min`:
   ร่างโพสต์มาทั้งหมด 3 ทางเลือก (3 Options) ตามกฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) ดังนี้:
   - แต่ละทางเลือกต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
   - โครงสร้างบังคับ (Strict 4-Line Structure):
     บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ขึ้นต้นด้วย 'เมื่อ...' เสมอ เช่น "เมื่อช่างภาพมือใหม่เจองานแรก 📸"]
     บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
     บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน ขึ้นต้นด้วย #WhatTheJob และตามด้วยแท็กที่เกี่ยวข้อง]
     บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
   - ตัวอย่าง:
     ทางเลือกที่ 1:
     เมื่อช่างภาพมือใหม่เจองานแรก 📸
     "มั่วสูตรไปเรื่อยเลยพี่เก่ง"
     #WhatTheJob #ช่างภาพ #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน
     ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก

B. หากเลือกคิว `Text_Posts` (สำหรับวันพฤหัสและวันอาทิตย์):
   ร่างโพสต์ออกมาเป็น 2 บล็อก (วันพฤหัส และวันอาทิตย์) โดยแต่ละบล็อกมี 3 ทางเลือก (3 Options) ในรูปแบบ EXACT ดังนี้:

   [THURSDAY_POSTS]
   ทางเลือกที่ 1:
   [เนื้อหาโพสต์ชวนคุย/โพลความยาว 2-5 บรรทัด ไม่ต้องขึ้นด้วย "เมื่อ..." และไม่ต้องปิดด้วยลิ้งคอมเมนต์ปักหมุด]
   [แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำถามชวนคิด]

   ทางเลือกที่ 2:
   ... (ร่างให้ครบ 3 ทางเลือก)

   [SUNDAY_POSTS]
   ทางเลือกที่ 1:
   [โควทคำคมเด่นของแขกรับเชิญ 1 ประโยค ตามด้วยคำอธิบายสรุปแง่คิดดีๆ/วิธีคิดสู้ชีวิตสั้นๆ รวมความยาว 3-6 บรรทัด ไม่ต้องขึ้นด้วย "เมื่อ..." และไม่ต้องปิดด้วยลิ้งคอมเมนต์ปักหมุด]
   [แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำคมดึงใจ]

   ทางเลือกที่ 2:
   ... (ร่างให้ครบ 3 ทางเลือก)

กฎเหล็กเพิ่มเติมสำหรับ Text_Posts:
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)
- ข้อเขียนยาวกว่า Reels ได้ปานกลางเพื่อขยายใจความหรือมีทางเลือกโพลชวนคุย แต่ห้ามยืดเยื้อหรือเวิ่นเว้อ
- จัดเว้นวรรคและจัดบรรทัดให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว{learning_examples_str}
"""
    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"โปรดอ่านข้อความถอดเทปย่อยนี้ และช่วยเลือกคิวพร้อมร่างโพสต์ให้หน่อยแก:\n\n{transcript_content}"
    response = model.generate_content(prompt)
    return response.text

def run_draft_pipeline():
    print("==================================================")
    print("🦉 เลขาเฟิส: เริ่มระบบสกัดทรานสคริปต์จาก Notion เข้าคิวโพสต์อัจฉริยะ 🚀")
    print("==================================================\n")
    
    notion = NotionHelper()
    
    # 1. ดึงข้อมูลหน้าที่มีสถานะ 1_Ideation ทั้งหมด
    print("🔍 กำลังดึงรายการที่มีสถานะ '1_Ideation' จาก Notion...")
    pages = notion.fetch_pages_by_status("1_Ideation")
    
    if not pages:
        print("📭 ไม่พบการ์ดหัวข้อใหม่ที่อยู่ในสถานะ '1_Ideation' เลยแก! (ไม่มีงานใหม่เข้ามา)")
        return
        
    print(f"📌 ตรวจพบทั้งหมด {len(pages)} หัวข้อใหม่ที่จะเอามาปั้นดราฟต์\n")
    
    for i, page in enumerate(pages):
        page_id = page["id"]
        title = page["title"]
        
        print(f"[{i+1}/{len(pages)}] 📝 เริ่มประมวลผลหัวข้อ: '{title}'")
        
        # 2. ดึงเนื้อหาทรานสคริปต์จากข้างในเพจ Notion
        transcript_content = notion.get_page_content_text(page_id)
        
        if not transcript_content or len(transcript_content.strip()) < 10:
            print(f"⚠️ คำเตือน: หน้า '{title}' ไม่มีข้อมูลทรานสคริปต์ในเนื้อหาเพจ! ข้ามหัวข้อนี้แก...")
            continue
            
        print(f"📖 ดึงข้อมูลทรานสคริปต์สำเร็จ (ความยาว {len(transcript_content)} ตัวอักษร)")
        
        # 3. ให้บอท Nam, Music, Ray เจียระไนโพสต์ 3 Options
        generated_text = generate_social_posts(title, transcript_content)
        if not generated_text:
            print("❌ ล้มเหลว: ไม่สามารถผลิตดราฟต์จากบอท AI ได้แก!")
            continue
            
        # 4. วิเคราะห์และคัดแยกคิวจากบอท
        queue_name = "FB_Videos_3-5Min" # Default fallback
        queue_match = re.search(r'\[QUEUE:\s*([\w\-]+)\]', generated_text)
        clean_draft_text = generated_text
        
        if queue_match:
            queue_name = queue_match.group(1).strip()
            # ตัดแท็ก QUEUE ออกเพื่อความสะอาด
            clean_draft_text = re.sub(r'\[QUEUE:\s*[\w\-]+\]\n?', '', generated_text).strip()
            
        print(f"🔮 บอทวิเคราะห์แล้ว คิวที่เหมาะสม: {queue_name}")
        
        # Mapping queue name to Notion Select Tag Platform
        platform_tags = []
        if queue_name == "FB_Videos_3-5Min":
            platform_tags = ["FB_Video"]
        elif queue_name == "Reels_Under1Min":
            platform_tags = ["Reels"]
        elif queue_name == "Text_Posts":
            platform_tags = ["FB_Text_Quote"]
        else:
            platform_tags = ["FB_Video"]
            
        # 5. จัดการเขียนและสร้างเพจใน Notion
        if queue_name == "Text_Posts":
            # Parsing Thursday & Sunday posts
            thu_content = ""
            sun_content = ""
            
            thu_match = re.search(r'\[THURSDAY_POSTS\](.*?)(\[SUNDAY_POSTS\]|$)', clean_draft_text, re.DOTALL | re.IGNORECASE)
            sun_match = re.search(r'\[SUNDAY_POSTS\](.*)', clean_draft_text, re.DOTALL | re.IGNORECASE)
            
            if thu_match:
                thu_content = thu_match.group(1).strip()
            if sun_match:
                sun_content = sun_match.group(1).strip()
                
            if not thu_content:
                thu_content = clean_draft_text
            if not sun_content:
                sun_content = clean_draft_text
                
            # Card 1 (Thursday): Rename original card and update status/platform
            print(f"🚀 กำลังตั้งค่าการ์ดวันพฤหัสบดี (ชวนคุย/โพล) บนการ์ดใบเดิม...")
            title_prop_name = notion.get_title_property_name()
            url_thu = f"https://api.notion.com/v1/pages/{page_id}"
            data_thu = {
                "properties": {
                    title_prop_name: {
                        "title": [{"text": {"content": f"[THU_Text] {title}"}}]
                    },
                    "Platform": {
                        "multi_select": [{"name": "FB_Text_Quote"}]
                    }
                }
            }
            notion._make_request(url_thu, method="PATCH", data=data_thu)
            
            # Write new options to Thursday card
            notion.write_page_content_text(page_id, f"\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + thu_content)
            notion.update_page_status(page_id, "4_Review")
            
            # Card 2 (Sunday): Create a new card in Notion
            print(f"🚀 กำลังสร้างการ์ดวันอาทิตย์ (คำคมดึงใจ) ใบใหม่...")
            sun_title = f"[SUN_Text] {title}"
            new_page = notion.create_page(sun_title, status_name="4_Review", platform_tags=["FB_Text_Quote"])
            
            if new_page and "id" in new_page:
                new_page_id = new_page["id"]
                # Append transcript + Sunday options
                sunday_full_content = transcript_content + f"\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + sun_content
                notion.write_page_content_text(new_page_id, sunday_full_content)
                print(f"✅ สร้างการ์ดวันอาทิตย์สำเร็จ! (Page ID: {new_page_id})")
            else:
                print("❌ ล้มเหลว: ไม่สามารถสร้างการ์ดวันอาทิตย์ใน Notion ได้")
                
            
            # Local Backup for Text_Posts
            clean_topic = re.sub(r'[^\w\s]', '', title).strip().replace(" ", "_").lower()
            drafts_dir = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")
            os.makedirs(drafts_dir, exist_ok=True)
            
            backup_path_thu = os.path.join(drafts_dir, f"text_posts_thu_{clean_topic}.md")
            with open(backup_path_thu, "w", encoding="utf-8") as f:
                f.write(thu_content)
                
            backup_path_sun = os.path.join(drafts_dir, f"text_posts_sun_{clean_topic}.md")
            with open(backup_path_sun, "w", encoding="utf-8") as f:
                f.write(sun_content)
            print(f"💾 บันทึกไฟล์ร่างสำรอง THU และ SUN ลง {drafts_dir} เรียบร้อยแก!")
            
        else:
            # Normal flows for FB_Videos_3-5Min and Reels_Under1Min
            print(f"🚀 กำลังเขียนดราฟต์ 3 Options แปะต่อท้ายลงในหน้าเพจ Notion...")
            append_content = f"\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + clean_draft_text
            notion.write_page_content_text(page_id, append_content)
            
            print(f"🔄 อัปเดตแท็ก Platform ➔ {platform_tags} และย้ายสถานะไปที่ '4_Review'")
            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {
                "properties": {
                    "Platform": {
                        "multi_select": [{"name": p} for p in platform_tags]
                    }
                }
            }
            notion._make_request(url, method="PATCH", data=data)
            notion.update_page_status(page_id, "4_Review")
            
            
            # Local Backup
            clean_topic = re.sub(r'[^\w\s]', '', title).strip().replace(" ", "_").lower()
            drafts_dir = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")
            os.makedirs(drafts_dir, exist_ok=True)
            backup_filename = f"{queue_name.lower()}_{clean_topic}.md"
            backup_path = os.path.join(drafts_dir, backup_filename)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(clean_draft_text)
            print(f"💾 บันทึกไฟล์ร่างสำรองลง {backup_path} เรียบร้อยแก!")
            
        print(f"🎉 ประมวลผลหัวข้อ '{title}' เสร็จเรียบร้อย!\n")
        
    print("🎉 ปฏิบัติการเสร็จสิ้น! ดราฟต์ทั้งหมดจอดรอแกตรวจและอนุมัติที่หน้าตาราง Notion เรียบร้อยแล้วจ้า! 🦉🤘✨")

if __name__ == "__main__":
    run_draft_pipeline()
