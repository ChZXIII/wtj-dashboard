#!/usr/bin/env python3
import os
import sys
import re
import json
import argparse
import time
import google.generativeai as legacy_genai

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

# Configure Google API key
legacy_genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

import model_router
from notion_helper import NotionHelper
from youtube_old_video_recycler import fetch_transcript, download_audio

LEARNING_BASE_PATH = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "learning_base.json")
DRAFTS_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")

def load_filtered_examples(day_type):
    """Loads and formats up to 5 examples matching the target day type (THU or SUN)."""
    if not os.path.exists(LEARNING_BASE_PATH):
        return ""
        
    try:
        with open(LEARNING_BASE_PATH, "r", encoding="utf-8") as f:
            examples = json.load(f)
            
        # Filter examples by day type
        filtered = []
        for ex in reversed(examples): # Start from latest
            title = ex.get("title", "").upper()
            if day_type == "THU" and ("RERUN_THU" in title or "THU_TEXT" in title):
                filtered.append(ex)
            elif day_type == "SUN" and ("RERUN_SUN" in title or "SUN_TEXT" in title):
                filtered.append(ex)
                
        # Fallback to any examples if specific ones are empty
        if not filtered:
            filtered = examples[-5:]
        else:
            filtered = filtered[:5]
            
        examples_str = "\n\n### 💡 ตัวอย่างสไตล์การเกลาคำและทางเลือกที่พี่เก่งเลือกแก้ล่าสุด (เรียนรู้และปรับตามด้านล่างนี้):\n"
        for idx, ex in enumerate(filtered, 1):
            examples_str += f"""
---
ตัวอย่างที่ {idx}: เรื่อง "{ex.get('title')}"
[ดราฟต์ที่บอทเคยเสนอ]:
{ex.get('original_drafts')}

[เวอร์ชันที่พี่เก่งปรับปรุงและอนุมัติจริง]:
{ex.get('final_approved_copy')}
"""
        examples_str += "\n---"
        print(f"📖 โหลดตัวอย่างสไตล์ {day_type} ทั้งหมด {len(filtered)} รายการ ป้อนเข้าสู่หัวบอทแล้ว!")
        return examples_str
    except Exception as e:
        print(f"⚠️ Warning: ไม่สามารถโหลดคลังเรียนรู้ได้: {e}")
        return ""

def extract_youtube_info(body):
    """Extracts YouTube URL and Video ID from page content."""
    # Look for any url matching youtube or youtu.be
    match = re.search(r'https?://[^\s\)]+', body)
    if match:
        url = match.group(0).strip()
        # Extract video ID
        id_match = re.search(r'(?:youtu\.be/|v=|youtu\.youtu\.be/|embed/|v/)([\w-]+)', url)
        if id_match:
            video_id = id_match.group(1)
            # Standardize URL
            clean_url = f"https://youtu.be/{video_id}"
            return clean_url, video_id
    return None, None

def generate_rerun_drafts_single_day(title, transcript_text, video_url, day_type, examples_str):
    """Generates 3 options using Gemini Model (Ray instructions) for a specific day."""
    print(f"🧠 [Gemini Agent] กำลังเขียนโพสต์รีรันสำหรับวัน {'พฤหัสบดี' if day_type == 'THU' else 'อาทิตย์'} จากทรานสคริปต์เรื่อง: '{title}'...")
    
    if day_type == "THU":
        system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: นำข้อมูลถอดเทปสัมภาษณ์ หัวข้อ: "{title}" มาร่างโพสต์ชวนคุยโปรโมตลง Facebook สำหรับวันพฤหัสบดี (Thursday Post)
โดยร่างมาทั้งหมด 3 ทางเลือก (3 Options) แต่ละทางเลือกเขียนให้มีระดับความเป็นมิตร เป็นกันเองสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน) แต่ไม่หยาบคาย และห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)

กฎเหล็กเรื่องรูปแบบการเขียน:
1. การระบุถึงผู้อ่าน/แฟนเพจ ให้ใช้คำว่า "คุณ" หรือ "ทุกคน" หรือ "แก" (แต่ห้ามใช้คำว่า "แก!" บ่อยเกินไป หรือโผล่มาทักทายทุกประโยค)
2. หลีกเลี่ยงคำสร้อยหรือฟิลเลอร์ที่ดูยัดเยียด เช่น "โคตรจริงเลยแก!", "บ้างนะแก?", "มันไม่ได้มีแค่ความปังนะแก!" ให้เน้นการเขียนที่ดูเป็นธรรมชาติ สบายๆ
3. โพสต์วันพฤหัสต้องเน้นประเด็นชวนคุย ตั้งคำถามกระตุ้นความคิด หรือตั้งโพลให้คนมาโหวต/แชร์ประสบการณ์ส่วนตัว
4. ทุกทางเลือกต้องลงท้ายด้วยประโยคปิดตัวนี้เป๊ะๆ: ดูคลิปเต็มได้ที่นี่เลย: {video_url}
5. ทุกทางเลือกต้องมีแฮชแท็กหลัก 6 อันนี้ครบถ้วนเสมอ: #WhatTheJob #WTJ #WTJTALK #WTJSTORY #WTJPODCAST #PODCAST และสามารถใส่แฮชแท็กเฉพาะที่เกี่ยวกับหัวข้อนั้นเพิ่มอีก 1-2 อันได้

รูปแบบการตอบกลับของทางเลือกต้องพิมพ์ตามแบบนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ ห้ามพิมพ์อธิบายเพิ่ม):
ทางเลือกที่ 1:
[เนื้อหาโพสต์]
[แฮชแท็ก]
ดูคลิปเต็มได้ที่นี่เลย: {video_url}

ทางเลือกที่ 2:
...

ทางเลือกที่ 3:
...

{examples_str}
"""
    else: # SUN
        system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: นำข้อมูลถอดเทปสัมภาษณ์ หัวข้อ: "{title}" มาร่างโพสต์แชร์ข้อคิดสร้างแรงบันดาลใจโปรโมตลง Facebook สำหรับวันอาทิตย์ (Sunday Post)
โดยร่างมาทั้งหมด 3 ทางเลือก (3 Options) แต่ละทางเลือกเขียนให้มีระดับความเป็นมิตร น่าเชื่อถือ และสร้างแรงบันดาลใจ (Inspiring) ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)

กฎเหล็กเรื่องรูปแบบการเขียน:
1. เริ่มต้นทางเลือกด้วยการโควทคำพูดคำคมที่เฉียบคมและน่าประทับใจของแขกรับเชิญจากการสัมภาษณ์ในรูปแบบ: "..." (โควทคำพูดจริง)
2. ตามด้วยย่อหน้าสรุปข้อคิดดีๆ หรือวิธีคิดสู้ชีวิตจากมุมมองของแขกรับเชิญ
3. หลีกเลี่ยงคำสร้อยหรือฟิลเลอร์ที่ดูยัดเยียด เช่น "โคตรจริงเลยแก!", "ปังนะแก!" ให้ใช้น้ำเสียงเป็นมิตรและสร้างแรงบันดาลใจ
4. ทุกทางเลือกต้องลงท้ายด้วยประโยคปิดตัวนี้เป๊ะๆ: ดูคลิปเต็มได้ที่นี่เลย: {video_url}
5. ทุกทางเลือกต้องมีแฮชแท็กหลัก 6 อันนี้ครบถ้วนเสมอ: #WhatTheJob #WTJ #WTJTALK #WTJSTORY #WTJPODCAST #PODCAST และสามารถใส่แฮชแท็กเฉพาะที่เกี่ยวกับหัวข้อนั้นเพิ่มอีก 1-2 อันได้

รูปแบบการตอบกลับของทางเลือกต้องพิมพ์ตามแบบนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ ห้ามพิมพ์อธิบายเพิ่ม):
ทางเลือกที่ 1:
[เนื้อหาโพสต์]
[แฮชแท็ก]
ดูคลิปเต็มได้ที่นี่เลย: {video_url}

ทางเลือกที่ 2:
...

ทางเลือกที่ 3:
...

{examples_str}
"""

    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"โปรดอ่านข้อความถอดเทปนี้ และช่วยร่างโพสต์ Facebook วัน{'พฤหัสบดี' if day_type == 'THU' else 'อาทิตย์'} 3 Options แนบลิงก์คลิป {video_url} ให้หน่อยแก:\n\n{transcript_text[:12000]}"
    response = model.generate_content(prompt)
    return response.text

def generate_rerun_drafts_single_day_from_audio(title, audio_path, video_url, day_type, examples_str):
    """Downloads audio file and uploads to Gemini cloud to analyze and generate drafts."""
    print(f"🧠 [Gemini Audio Agent] กำลังเขียนโพสต์รีรันสำหรับวัน {'พฤหัสบดี' if day_type == 'THU' else 'อาทิตย์'} จากเสียงสัมภาษณ์เรื่อง: '{title}'...")
    
    if day_type == "THU":
        system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังไฟล์เสียงสัมภาษณ์เพื่อร่างโพสต์ชวนคุยโปรโมตลง Facebook สำหรับวันพฤหัสบดี (Thursday Post)
โดยร่างมาทั้งหมด 3 ทางเลือก (3 Options) แต่ละทางเลือกเขียนให้มีระดับความเป็นมิตร เป็นกันเองสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน) แต่ไม่หยาบคาย และห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)

กฎเหล็กเรื่องรูปแบบการเขียน:
1. การระบุถึงผู้อ่าน/แฟนเพจ ให้ใช้คำว่า "คุณ" หรือ "ทุกคน" หรือ "แก" (แต่ห้ามใช้คำว่า "แก!" บ่อยเกินไป หรือโผล่มาทักทายทุกประโยค)
2. หลีกเลี่ยงคำสร้อยหรือฟิลเลอร์ที่ดูยัดเยียด เช่น "โคตรจริงเลยแก!", "บ้างนะแก?", "มันไม่ได้มีแค่ความปังนะแก!" ให้เน้นการเขียนที่ดูเป็นธรรมชาติ สบายๆ
3. โพสต์วันพฤหัสต้องเน้นประเด็นชวนคุย ตั้งคำถามกระตุ้นความคิด หรือตั้งโพลให้คนมาโหวต/แชร์ประสบการณ์ส่วนตัว
4. ทุกทางเลือกต้องลงท้ายด้วยประโยคปิดตัวนี้เป๊ะๆ: ดูคลิปเต็มได้ที่นี่เลย: {video_url}
5. ทุกทางเลือกต้องมีแฮชแท็กหลัก 6 อันนี้ครบถ้วนเสมอ: #WhatTheJob #WTJ #WTJTALK #WTJSTORY #WTJPODCAST #PODCAST และสามารถใส่แฮชแท็กเฉพาะที่เกี่ยวกับหัวข้อนั้นเพิ่มอีก 1-2 อันได้

รูปแบบการตอบกลับของทางเลือกต้องพิมพ์ตามแบบนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ ห้ามพิมพ์อธิบายเพิ่ม):
ทางเลือกที่ 1:
[เนื้อหาโพสต์]
[แฮชแท็ก]
ดูคลิปเต็มได้ที่นี่เลย: {video_url}

ทางเลือกที่ 2:
...

ทางเลือกที่ 3:
...

{examples_str}
"""
    else: # SUN
        system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังไฟล์เสียงสัมภาษณ์เพื่อร่างโพสต์แชร์ข้อคิดสร้างแรงบันดาลใจโปรโมตลง Facebook สำหรับวันอาทิตย์ (Sunday Post)
โดยร่างมาทั้งหมด 3 ทางเลือก (3 Options) แต่ละทางเลือกเขียนให้มีระดับความเป็นมิตร น่าเชื่อถือ และสร้างแรงบันดาลใจ (Inspiring) ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)

กฎเหล็กเรื่องรูปแบบการเขียน:
1. เริ่มต้นทางเลือกด้วยการโควทคำพูดคำคมที่เฉียบคมและน่าประทับใจของแขกรับเชิญจากการสัมภาษณ์ในรูปแบบ: "..." (โควทคำพูดจริง)
2. ตามด้วยย่อหน้าสรุปข้อคิดดีๆ หรือวิธีคิดสู้ชีวิตจากมุมมองของแขกรับเชิญ
3. หลีกเลี่ยงคำสร้อยหรือฟิลเลอร์ที่ดูยัดเยียด เช่น "โคตรจริงเลยแก!", "ปังนะแก!" ให้ใช้น้ำเสียงเป็นมิตรและสร้างแรงบันดาลใจ
4. ทุกทางเลือกต้องลงท้ายด้วยประโยคปิดตัวนี้เป๊ะๆ: ดูคลิปเต็มได้ที่นี่เลย: {video_url}
5. ทุกทางเลือกต้องมีแฮชแท็กหลัก 6 อันนี้ครบถ้วนเสมอ: #WhatTheJob #WTJ #WTJTALK #WTJSTORY #WTJPODCAST #PODCAST และสามารถใส่แฮชแท็กเฉพาะที่เกี่ยวกับหัวข้อนั้นเพิ่มอีก 1-2 อันได้

รูปแบบการตอบกลับของทางเลือกต้องพิมพ์ตามแบบนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ ห้ามพิมพ์อธิบายเพิ่ม):
ทางเลือกที่ 1:
[เนื้อหาโพสต์]
[แฮชแท็ก]
ดูคลิปเต็มได้ที่นี่เลย: {video_url}

ทางเลือกที่ 2:
...

ทางเลือกที่ 3:
...

{examples_str}
"""
    try:
        # Get model name from router
        _, model_name = model_router.get_routing_info("ray")
        
        print("🚀 กำลังอัปโหลดไฟล์เสียงขึ้น Gemini Files API...")
        audio_file = legacy_genai.upload_file(path=audio_path)
        print(f"   - อัปโหลดเสร็จสิ้น (File Name: {audio_file.name})")
        
        print("⏳ กำลังรอให้ Gemini ประมวลผลเสียง (Processing)...")
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = legacy_genai.get_file(audio_file.name)
            
        if audio_file.state.name == "FAILED":
            print("❌ Gemini ไม่สามารถประมวลผลไฟล์เสียงนี้ได้")
            return None
            
        print("✅ ไฟล์เสียงพร้อมใช้งานแล้ว! เริ่มทำการวิเคราะห์และร่างคอนเทนต์...")
        
        # Initialize generative model
        model = legacy_genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        prompt = f"โปรดฟังไฟล์เสียงสัมภาษณ์นี้ และช่วยร่างโพสต์ Facebook วัน{'พฤหัสบดี' if day_type == 'THU' else 'อาทิตย์'} 3 Options แนบลิงก์คลิป {video_url} ให้หน่อยแก:"
        response = model.generate_content([audio_file, prompt])
        
        # Clean up Gemini cloud storage
        print(f"🗑️ กำลังลบไฟล์เสียงจากระบบคลาวด์ Gemini ({audio_file.name})...")
        try:
            legacy_genai.delete_file(audio_file.name)
        except Exception as delete_err:
            print(f"⚠️ ไม่สามารถลบไฟล์บนคลาวด์ได้: {delete_err}")
            
        return response.text
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการรัน Gemini Audio API: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Regenerate Review Drafts in Notion")
    parser.add_argument("-l", "--limit", type=int, default=5, help="จำนวนหน้าเพจสูงสุดที่จะประมวลผล (default: 5)")
    parser.add_argument("-p", "--page-id", help="เจาะจงรันเฉพาะ Page ID ที่ระบุ")
    parser.add_argument("-d", "--dry-run", action="store_true", help="รันโหมดจำลองพิมพ์ออกหน้าจอเฉยๆ ไม่เขียนลง Notion")
    
    args = parser.parse_args()
    
    print("==================================================")
    print("🦉 เลขาเฟิส: ปฏิบัติการปรับปรุงดราฟต์ให้ตรงใจพี่เก่งขึ้น 🚀")
    print("==================================================")
    
    notion = NotionHelper()
    
    # 1. Fetch 4_Review pages
    print("🔍 กำลังดึงรายการที่มีสถานะ '4_Review' จาก Notion...")
    pages = notion.fetch_pages_by_status("4_Review")
    
    if not pages:
        print("📭 ไม่พบเพจในสถานะ '4_Review' เลยแก!")
        return
        
    print(f"📊 พบทั้งหมด {len(pages)} หัวข้อในสถานะ '4_Review'")
    
    # 2. Filter to targeted page if specified
    if args.page_id:
        target_pages = [p for p in pages if p["id"] == args.page_id]
        if not target_pages:
            print(f"❌ ไม่พบเพจ ID '{args.page_id}' ในคิว 4_Review")
            sys.exit(1)
    else:
        target_pages = pages[:args.limit]
        
    print(f"📌 จะประมวลผลทั้งหมด {len(target_pages)} หน้า:")
    for idx, p in enumerate(target_pages, 1):
        print(f"  {idx}. [{p['id']}] {p['title']}")
        
    processed = 0
    for p in target_pages:
        page_id = p["id"]
        title = p["title"]
        
        print(f"\n⚡ [{processed+1}/{len(target_pages)}] กำลังเริ่มประมวลผล: '{title}'")
        
        # Determine day type
        day_type = None
        if "RERUN_THU" in title.upper():
            day_type = "THU"
        elif "RERUN_SUN" in title.upper():
            day_type = "SUN"
        else:
            print(f"⚠️ ข้าม: ไม่ใช่โพสต์รีรัน (ชื่อไม่ขึ้นต้นด้วย [RERUN_THU] หรือ [RERUN_SUN])")
            continue
            
        # Get page content to parse URL and current source context
        body = notion.get_page_content_text(page_id)
        if not body:
            print(f"⚠️ ข้าม: ไม่สามารถอ่านเนื้อหาในเพจได้")
            continue
            
        video_url, video_id = extract_youtube_info(body)
        if not video_url:
            print(f"❌ ข้าม: หาลิงก์ YouTube ไม่พบในเนื้อหาเพจ")
            continue
            
        print(f"🔗 ลิงก์วิดีโอ: {video_url} (ID: {video_id})")
        
        # Load examples
        examples_str = load_filtered_examples(day_type)
        
        # Fetch transcript
        transcript_text = fetch_transcript(video_id)
        generated_text = None
        source_context = ""
        
        if transcript_text and len(transcript_text.strip()) >= 50:
            source_context = f"ถอดเทปข้อความย่อ:\n\n{transcript_text[:1500]}"
            generated_text = generate_rerun_drafts_single_day(title, transcript_text, video_url, day_type, examples_str)
        else:
            # Fallback to audio download
            print(f"⚠️ ไม่พบคำบรรยายแบบข้อความ กำลังดาวน์โหลดไฟล์เสียงจาก YouTube เพื่อส่งให้ Gemini...")
            temp_audio_filename = f"temp_audio_{video_id}.m4a"
            temp_audio_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", temp_audio_filename)
            
            if download_audio(video_id, temp_audio_path):
                generated_text = generate_rerun_drafts_single_day_from_audio(title, temp_audio_path, video_url, day_type, examples_str)
                source_context = "วิเคราะห์รายละเอียดจากเสียงสัมภาษณ์ในคลิปโดยตรง"
                
                # Delete local audio file
                if os.path.exists(temp_audio_path):
                    print(f"🗑️ กำลังลบไฟล์เสียงโลคอลชั่วคราว: {temp_audio_path}")
                    os.remove(temp_audio_path)
            else:
                print(f"❌ ดึงข้อมูลเสียงไม่สำเร็จ ข้ามหัวข้อนี้แก...")
                continue
                
        if not generated_text or "ทางเลือกที่ 1" not in generated_text:
            print(f"❌ ข้าม: เจนข้อความโพสต์จาก AI ไม่สำเร็จ หรือรูปแบบคำตอบไม่ถูกต้อง")
            continue
            
        # Format full page content
        full_page_content = f"วิดีโอคำบรรยายต้นฉบับสำหรับการรีรัน:\n\n{source_context}\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + generated_text
        
        if args.dry_run:
            print(f"💡 [DRY-RUN] ข้อความที่จะเขียนลง Notion:")
            print("="*40)
            print(full_page_content)
            print("="*40)
        else:
            print(f"🚀 กำลังอัปเดตเพจ Notion {page_id}...")
            # Clear old content
            notion.clear_page_content(page_id)
            # Write new content
            notion.write_page_content_text(page_id, full_page_content)
            
            # Save local backup
            clean_topic = re.sub(r'[^\w\s]', '', title).strip().replace(" ", "_").lower()
            os.makedirs(DRAFTS_DIR, exist_ok=True)
            backup_path = os.path.join(DRAFTS_DIR, f"rerun_{day_type.lower()}_regenerated_{clean_topic}.md")
            
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n**URL:** {video_url}\n\n" + generated_text)
            print(f"💾 บันทึกดราฟต์สำรองสำเร็จที่: {backup_path}")
            
        processed += 1
        # Small delay to prevent API rate limits
        if not args.dry_run and processed < len(target_pages):
            print("⏳ พักเครื่อง 2 วินาทีเพื่อหลีกเลี่ยง API Rate Limit...")
            time.sleep(2)
        
    print(f"\n🎉 ปฏิบัติการเสร็จสิ้น! อัปเดตปรับปรุงใหม่เสร็จไป {processed} หน้าแก! 🦉🤘✨")

if __name__ == "__main__":
    main()
