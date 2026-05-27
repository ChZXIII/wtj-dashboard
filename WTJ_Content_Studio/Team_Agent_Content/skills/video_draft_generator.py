#!/usr/bin/env python3
import os
import sys
import time
import re
import subprocess
import html
import shutil
from google import genai
from google.genai import types

# Find project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
from notion_helper import NotionHelper



PROJECT_ROOT = CURRENT_DIR
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

def load_env():
    """Load Environment Variables from .env file."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Load environment variables
load_env()
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    print("❌ Error: ไม่พบ GOOGLE_API_KEY ในไฟล์ .env ของโปรเจกต์")
    sys.exit(1)

# Initialize GenAI Client
client = genai.Client(api_key=API_KEY)

# Directory configurations
RAW_VIDEOS_DIR = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos")
DRAFTS_DIR = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "2_drafts")

# Supported media extensions
MEDIA_EXTENSIONS = ('.mp4', '.mp3', '.wav', '.m4a', '.mov', '.avi', '.mkv', '.ogg', '.aac', '.flac')

def wait_for_file_to_stabilize(file_path):
    """Wait until a file is fully copied (its size stops changing)."""
    print(f"⏳ กำลังตรวจสอบขนาดไฟล์ '{os.path.basename(file_path)}' เพื่อความมั่นใจว่าก๊อปเสร็จแล้ว...")
    last_size = -1
    while True:
        try:
            current_size = os.path.getsize(file_path)
            if current_size == last_size:
                print(f"✅ ไฟล์เสถียรแล้ว ขนาด: {current_size / (1024*1024):.2f} MB")
                break
            last_size = current_size
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ เกิดข้อผิดพลาดในการตรวจสอบขนาดไฟล์: {e}")
            time.sleep(2)

def create_apple_note(queue_folder, title, body_content):
    """Creates a note in Apple Notes in the queue-specific subfolders."""
    body_html = f"<div><b>{title}</b><br><br>" + body_content.replace("\n", "<br>") + "</div>"
    
    escaped_title = title.replace('\\', '\\\\').replace('"', '\\"')
    escaped_body = body_html.replace('\\', '\\\\').replace('"', '\\"')
    
    applescript = f"""
    tell application "Notes"
        try
            set rootFolder to folder "WTJ"
            set fbFolder to folder "Facebook" of rootFolder
            set parentQueue to folder "{queue_folder}" of fbFolder
            set draftsFolder to folder "1_Drafts" of parentQueue
            
            make new note at draftsFolder with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
            return "Success"
        on error err
            return "Error: " & err
        end try
    end tell
    """
    
    try:
        proc = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        return proc.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def generate_social_posts(file_ref, filename, queue_name):
    """Call Gemini to analyze the media and write drafts for a specific queue."""
    print(f"🧠 กำลังส่งวิเคราะห์สื่อสำหรับคิว: {queue_name}...")
    
    prompt = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น คิดคอนเซปต์สุดล้ำ), "มิวสิค" (Marketer สาววัยรุ่น ปั้นมีมและแคมเปญสุดจึ้ง) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังและถอดเทป/จับใจความจากไฟล์เสียง/วิดีโอที่แนบมานี้ มาเขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่จึ้งและแตกต่างกัน เพื่อให้พี่เก่งได้เลือกอันที่ชอบที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์และร่างโพสต์มาทั้งหมด 3 ทางเลือก (3 Options) ที่เน้นมุมมองที่แตกต่างกันอย่างสิ้นเชิง
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - เน้นความสั้นและกระชับสุดๆ (Extreme Brevity):
- บังคับความยาว: แต่ละทางเลือกต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
- บังคับไม่มีหัวข้อเขียนเล่น: ให้ระบุเพียงแค่ "ทางเลือกที่ 1:", "ทางเลือกที่ 2:", "ทางเลือกที่ 3:" แล้วตามด้วยบรรทัดเนื้อหาทันที ห้ามใส่ชื่อทางเลือกหรือคำอธิบาย เช่น ห้ามใส่ ### Option 1: ฟีลแบบ... หรือคำโปรยใดๆ เด็ดขาด!
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ไม่เกิน 10-12 คำ ขึ้นต้นด้วย 'เมื่อ...' เสมอ เช่น "เมื่อช่างภาพมือใหม่เจองานแรก 📸"]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
  บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน โดยขึ้นต้นด้วย #WhatTheJob และตามด้วยแท็กเจาะลึกอาชีพ, #รีวิวชีวิตทำงาน, #ชีวิตคนทำงาน, #มนุษย์เงินเดือน, #เจาะลึกอาชีพ, #วัยทำงาน เช่น #WhatTheJob #ช่างภาพ #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน #เจาะลึกอาชีพ]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ตัวอย่างที่ถูกต้อง:
  ทางเลือกที่ 1:
  เมื่อช่างภาพมือใหม่เจองานแรก 📸
  "มั่วสูตรไปเรื่อยเลยพี่เก่ง"
  #WhatTheJob #ช่างภาพ #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน #เจาะลึกอาชีพ
  ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามดราม่า ห้ามเวิ่นเว้อ ห้ามมีคำอธิบายเพิ่มเติมใดๆ นอกเหนือจาก 4 บรรทัดนี้เด็ดขาด
- ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นหรือคำพูดกันอย่างเป็นธรรมชาติ
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[file_ref, prompt]
    )
    return response.text

def process_single_file(file_path, queue_name):
    filename = os.path.basename(file_path)
    print(f"\n🎬 เริ่มการประมวลผลไฟล์: '{filename}' สำหรับคิว '{queue_name}'")
    
    # 1. Wait for stabilizing
    wait_for_file_to_stabilize(file_path)
    
    # 2. Workaround for UnicodeEncodeError in httpx headers (when filename contains non-ASCII/Thai characters)
    file_ext = os.path.splitext(file_path)[1]
    temp_filename = f"temp_upload_{int(time.time())}{file_ext}"
    temp_file_path = os.path.join(os.path.dirname(file_path), temp_filename)
    
    print(f"📦 คัดลอกไฟล์ชั่วคราวไปเป็น ASCII เพื่อแก้บั๊กอัปโหลดไฟล์ภาษาไทย...")
    try:
        shutil.copy2(file_path, temp_file_path)
    except Exception as e:
        print(f"❌ คัดลอกไฟล์ชั่วคราวล้มเหลว: {e}")
        return False
        
    myfile = None
    try:
        # 3. Upload temporary ASCII file to Gemini File API
        print(f"🚀 กำลังอัปโหลดไฟล์ขึ้นระบบคลาวด์ Gemini...")
        myfile = client.files.upload(file=temp_file_path)
        print(f"✅ อัปโหลดสำเร็จ (File ID: {myfile.name})")
    finally:
        # Delete temporary local file immediately
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    if not myfile:
        print("❌ ล้มเหลวในการอัปโหลดไฟล์")
        return False
    
    try:
        # 4. Poll file status until ACTIVE
        print("⏳ รอคลาวด์แปลงไฟล์และประมวลผล...")
        start_time = time.time()
        timeout = 300 # 5 minutes timeout
        
        while True:
            myfile = client.files.get(name=myfile.name)
            if myfile.state.name == "ACTIVE":
                print("⚡ ไฟล์พร้อมประมวลผล (Active) แล้ว!")
                break
            elif myfile.state.name == "FAILED":
                raise ValueError(f"การแปลงไฟล์ล้มเหลว: {myfile.error}")
            
            if time.time() - start_time > timeout:
                raise TimeoutError("หมดเวลารอแปลงไฟล์ (Timeout 5 นาที)")
                
            time.sleep(5)
            
        # 5. Generate post drafts
        generated_text = generate_social_posts(myfile, filename, queue_name)
        
        if not generated_text:
            print("❌ ล้มเหลว: ไม่สามารถผลิตเนื้อหาได้")
            return False
            
        # 6. Clean draft text
        clean_draft_text = re.sub(r'\[QUEUE:\s*[\w\-]+\]\n?', '', generated_text).strip()
            
        print(f"\n🔮 ผลลัพธ์การร่างสำหรับคิว: {queue_name}")
        print("\n--- 📝 ผลลัพธ์โซเชียลดราฟต์ ---")
        print(clean_draft_text)
        print("----------------------------\n")
        
        # 7. Save backup locally
        os.makedirs(DRAFTS_DIR, exist_ok=True)
        file_slug = re.sub(r'[^\w\s-]', '', filename).strip().replace(" ", "_").lower()
        backup_filename = f"{queue_name.lower()}_from_video_{file_slug}.md"
        backup_path = os.path.join(DRAFTS_DIR, backup_filename)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(clean_draft_text)
        print(f"💾 บันทึกไฟล์ร่างสำรองที่: {backup_path}")
        
        # 8. Push to Notion Database
        print("🚀 กำลังส่งดราฟต์วิดีโอไปสร้างหน้าการ์ดใหม่ใน Notion...")
        try:
            notion = NotionHelper()
            platform_tags = []
            if queue_name == "Reels_Under1Min":
                platform_tags = ["Reels"]
            elif queue_name == "FB_Videos_3-5Min":
                platform_tags = ["FB_Video"]
            
            title_notion = f"[{queue_name} Video Draft] {filename}"
            # Create page in Notion with Status: 4_Review
            new_page = notion.create_page(title_notion, status_name="4_Review", platform_tags=platform_tags)
            
            if new_page and "id" in new_page:
                page_id = new_page["id"]
                # Append generated drafts & transcript details
                notion.write_page_content_text(page_id, clean_draft_text)
                print(f"✅ สร้างการ์ดและบันทึกเนื้อหาลง Notion สำเร็จแล้วแก! (Page ID: {page_id})")
            else:
                print("❌ ล้มเหลว: ไม่สามารถสร้างหน้าใหม่ in Notion ได้")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Notion: {e}")
        
        # 9. Move file to processed folder inside the queue folder
        queue_folder_path = os.path.dirname(file_path)
        processed_dir = os.path.join(queue_folder_path, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        processed_path = os.path.join(processed_dir, filename)
        if os.path.exists(file_path):
            os.rename(file_path, processed_path)
            print(f"📦 ย้ายไฟล์วิดีโอไปที่ {processed_dir} เรียบร้อยจ้า!")
        else:
            print("⚠️ ไฟล์วิดีโอถูกย้ายหรือประมวลผลโดยระบบอื่นแล้วแก!")
        
        return True
        
    finally:
        # Cleanup file from Gemini Cloud storage immediately to save resources
        if myfile:
            try:
                print("🧹 ลบไฟล์ชั่วคราวออกจากคลาวด์ Gemini...")
                client.files.delete(name=myfile.name)
                print("✅ ลบเรียบร้อย!")
            except Exception as e:
                print(f"⚠️ ไม่สามารถลบไฟล์ชั่วคราวบนคลาวด์ได้ (ระบบจะลบให้อัตโนมัติใน 48 ชม.): {e}")

def main():
    print("==================================================")
    print("🎬 WTJ Video Auto-Transcriber & Drafter Pipeline")
    print("==================================================")
    
    # Define directories
    reels_dir = os.path.join(RAW_VIDEOS_DIR, "raw_vdo_short")
    fb_videos_dir = os.path.join(RAW_VIDEOS_DIR, "raw_vdo_3-5min")
    
    # Ensure they exist
    os.makedirs(reels_dir, exist_ok=True)
    os.makedirs(fb_videos_dir, exist_ok=True)
    os.makedirs(os.path.join(reels_dir, "processed"), exist_ok=True)
    os.makedirs(os.path.join(fb_videos_dir, "processed"), exist_ok=True)
    
    # Define scan targets: (directory, queue_name)
    targets = [
        (reels_dir, "Reels_Under1Min"),
        (fb_videos_dir, "FB_Videos_3-5Min")
    ]
    
    total_files = 0
    processed_count = 0
    
    for folder, queue_name in targets:
        # Sort files to process them deterministically (e.g. by name)
        files = sorted([f for f in os.listdir(folder) if f.lower().endswith(MEDIA_EXTENSIONS)])
        if files:
            print(f"\n🔍 ตรวจพบไฟล์ใหม่ใน '{os.path.basename(folder)}' (สำหรับคิว {queue_name}) จำนวน {len(files)} ไฟล์:")
            for f in files:
                print(f"   - {f}")
                total_files += 1
                file_path = os.path.join(folder, f)
                if process_single_file(file_path, queue_name):
                    processed_count += 1
                    
    if total_files == 0:
        print("📭 ไม่พบไฟล์วิดีโอหรือไฟล์เสียงใหม่ใน raw_vdo_short/ หรือ raw_vdo_3-5min/ เลยแก")
    else:
        print(f"\n🎉 ดำเนินการเสร็จสิ้น! ประมวลผลสำเร็จ {processed_count}/{total_files} ไฟล์จ้า!")

if __name__ == "__main__":
    main()
