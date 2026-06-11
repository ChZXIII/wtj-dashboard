#!/usr/bin/env python3
import os
import sys
import csv
import re
import json
import argparse
from datetime import datetime
import subprocess
import time

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

def load_env():
    """Load environment variables from the .env file in project root."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if current_dir not in sys.path:
    sys.path.append(current_dir)

import model_router
from notion_helper import NotionHelper
from youtube_transcript_api import YouTubeTranscriptApi

# Constants
CSV_PATH = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "analytics", "Table data.csv")
STATE_PATH = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "rerun_state.json")
DRAFTS_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")

def get_all_existing_notion_titles(notion):
    """Retrieves all titles in the database to prevent duplicate card creation."""
    print("🔍 กำลังดึงรายชื่อหัวข้อทั้งหมดใน Notion เพื่อความแน่ใจ...")
    url = f"https://api.notion.com/v1/databases/{notion.database_id}/query"
    titles = set()
    has_more = True
    start_cursor = None
    title_prop_name = notion.get_title_property_name()
    
    while has_more:
        data = {}
        if start_cursor:
            data["start_cursor"] = start_cursor
        
        res = notion._make_request(url, method="POST", data=data)
        if res and "results" in res:
            for page in res["results"]:
                properties = page.get("properties", {})
                name_prop = properties.get(title_prop_name, {})
                if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
                    title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
                    titles.add(title.strip())
            
            has_more = res.get("has_more", False)
            start_cursor = res.get("next_cursor")
        else:
            has_more = False
            
    print(f"📊 โหลดหัวข้อจาก Notion สำเร็จ: {len(titles)} หัวข้อ")
    return titles

def load_state():
    """Load local processed video IDs list."""
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    """Save processed video IDs list."""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def parse_date(date_str):
    """Parse publish date string, e.g. 'Sep 7, 2022' or 'Aug 24, 2024'."""
    date_str = date_str.strip().strip('"')
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # Fallback to epoch if parsing fails
    return datetime.fromtimestamp(0)

def fetch_videos_from_csv():
    """Reads videos from CSV, filters, and sorts them by date ascending."""
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: ไม่พบไฟล์ CSV สถิติช่องที่: {CSV_PATH}")
        sys.exit(1)
        
    videos = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            content_id = row.get("Content", "").strip()
            # Skip Total and empty rows
            if content_id == "Total" or not content_id:
                continue
                
            title = row.get("Video title", "").strip()
            pub_time = row.get("Video publish time", "").strip()
            duration = int(row.get("Duration", 0)) if row.get("Duration") else 0
            
            # Filter teasers/shorts (shorter than 60 seconds or title contains Teaser)
            if duration < 60 or "teaser" in title.lower():
                continue
                
            parsed_date = parse_date(pub_time)
            videos.append({
                "id": content_id,
                "title": title,
                "publish_time": pub_time,
                "parsed_date": parsed_date,
                "url": f"https://youtu.be/{content_id}"
            })
            
    # Sort: oldest first (ascending)
    videos.sort(key=lambda x: x["parsed_date"])
    return videos

def fetch_transcript(video_id):
    """Fetches video transcript using YouTubeTranscriptApi."""
    print(f"🎧 กำลังเริ่มดึงทรานสคริปต์สำหรับ Video ID: {video_id}...")
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['th']).fetch()
        except Exception:
            # Try to translate English/other to Thai
            try:
                transcript = transcript_list.find_transcript(['en']).translate('th').fetch()
            except Exception:
                # If en translate fails, pick the first one and translate to Thai
                first_transcript = next(iter(transcript_list))
                transcript = first_transcript.translate('th').fetch()
                
        full_text = " ".join([entry.text for entry in transcript])
        return full_text
    except Exception as e:
        print(f"⚠️ ไม่สามารถดึงซับไตเติ้ลสำหรับ {video_id} ได้: {e}")
        return None

def download_audio(video_id, output_path):
    """Downloads audio only from YouTube using yt-dlp."""
    print(f"📥 กำลังดาวน์โหลดไฟล์เสียงสำหรับ Video ID: {video_id}...")
    # Use yt-dlp to download format 140 (AAC) or bestaudio as m4a
    cmd = [
        os.path.join(PROJECT_ROOT, "venv", "bin", "yt-dlp"),
        "-f", "140/bestaudio[ext=m4a]/bestaudio",
        "-o", output_path,
        f"https://youtu.be/{video_id}"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_path):
            print(f"✅ ดาวน์โหลดไฟล์เสียงสำเร็จ: {output_path} (ขนาด {os.path.getsize(output_path)} bytes)")
            return True
    except Exception as e:
        print(f"❌ ดาวน์โหลดไฟล์เสียงล้มเหลว: {e}")
    return False

def generate_rerun_drafts_from_audio(title, audio_path, video_url):
    """Uploads audio file to Gemini, generates Friday/Sunday drafts, and cleans up."""
    print(f"🧠 [Gemini Audio Agent] กำลังเขียนโพสต์รีรันจากการฟังเสียงเรื่อง: '{title}'...")
    
    system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังไฟล์เสียงสัมภาษณ์ฉบับเต็มของรายการ หัวข้อ: "{title}" มาร่างโพสต์รีรันโปรโมตลง Facebook 2 แบบ (วันพฤหัสบดี ชวนคุย/โพล และ วันอาทิตย์ คำคมดึงใจ)
โดยแต่ละโพสต์ต้องมี 3 ทางเลือก (3 Options) และลงท้ายด้วยการแนะนำลิงก์วิดีโอแบบปิดอย่างชัดเจน

รูปแบบและกฎเหล็กการเขียน:
1. ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)
2. ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)
3. ร่างดราฟต์ออกมาเป็นรูปแบบด้านล่างนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ หรืออธิบายเพิ่มเติมเด็ดขาด):

[THURSDAY_POSTS]
ทางเลือกที่ 1:
[เนื้อหาโพสต์แนวคำถามชวนแฟนเพจคุย หรือตั้งโพลประเด็นเด็ดที่เกี่ยวกับวิดีโอนี้ ความยาวประมาณ 2-5 บรรทัด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำถามชวนคิด]
ดูคลิปเต็มได้ที่นี่เลยแก: {video_url}

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

ทางเลือกที่ 3:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

[SUNDAY_POSTS]
ทางเลือกที่ 1:
[คำคมหรือทัศนคติเจ๋งๆ จากแขกรับเชิญในคลิป 1 ประโยค ตามด้วยบทสรุปแง่คิดสร้างแรงบันดาลใจ ความยาวประมาณ 3-6 บรรทัด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำคมดึงใจ]
ดูคลิปเต็มได้ที่นี่เลยแก: {video_url}

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

ทางเลือกที่ 3:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)
"""
    try:
        import google.generativeai as legacy_genai
        
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
        
        # Get routed model name
        _, model_name = model_router.get_routing_info("ray")
        
        # Initialize generative model
        model = legacy_genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        prompt = f"โปรดฟังไฟล์เสียงสัมภาษณ์นี้ และช่วยร่างโพสต์ Facebook (พฤหัส ชวนคุย + อาทิตย์ คำคม) แนบลิงก์คลิป {video_url} ให้หน่อยแก:"
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

def generate_rerun_drafts(title, transcript_text, video_url):
    """Uses Gemini (Ray/Nam/Music instructions) to draft interactive Thursday & inspiring Sunday posts."""
    print(f"🧠 [Gemini Agent] กำลังเขียนโพสต์รีรันจากทรานสคริปต์เรื่อง: '{title}'...")
    
    system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer วัยรุ่น) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: นำข้อความถอดเทปวิดีโอรายการตัวเต็ม (Transcript) หัวข้อ: "{title}" มาร่างโพสต์รีรันโปรโมตลง Facebook 2 แบบ (วันพฤหัสบดี ชวนคุย/โพล และ วันอาทิตย์ คำคมดึงใจ)
โดยแต่ละโพสต์ต้องมี 3 ทางเลือก (3 Options) และลงท้ายด้วยการแนะนำลิงก์วิดีโอแบบปิดอย่างชัดเจน

รูปแบบและกฎเหล็กการเขียน:
1. ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาคำบรรยายปกติ (ใช้ได้เฉพาะในโควทจริงของแขกรับเชิญ)
2. ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)
3. ร่างดราฟต์ออกมาเป็นรูปแบบด้านล่างนี้เป๊ะๆ (ห้ามแต่งเกริ่นนำ หรืออธิบายเพิ่มเติมเด็ดขาด):

[THURSDAY_POSTS]
ทางเลือกที่ 1:
[เนื้อหาโพสต์แนวคำถามชวนแฟนเพจคุย หรือตั้งโพลประเด็นเด็ดที่เกี่ยวกับวิดีโอนี้ ความยาวประมาณ 2-5 บรรทัด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำถามชวนคิด]
ดูคลิปเต็มได้ที่นี่เลยแก: {video_url}

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

ทางเลือกที่ 3:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

[SUNDAY_POSTS]
ทางเลือกที่ 1:
[คำคมหรือทัศนคติเจ๋งๆ จากแขกรับเชิญในคลิป 1 ประโยค ตามด้วยบทสรุปแง่คิดสร้างแรงบันดาลใจ ความยาวประมาณ 3-6 บรรทัด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #คำคมดึงใจ]
ดูคลิปเต็มได้ที่นี่เลยแก: {video_url}

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)

ทางเลือกที่ 3:
... (ร่างให้ครบ 3 ทางเลือก ทุกทางเลือกต้องลงท้ายด้วย URL)
"""
    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"โปรดอ่านข้อความถอดเทปนี้ และช่วยร่างโพสต์ Facebook (พฤหัส ชวนคุย + อาทิตย์ คำคม) แนบลิงก์คลิป {video_url} ให้หน่อยแก:\n\n{transcript_text[:12000]}" # Limit context if too long
    response = model.generate_content(prompt)
    return response.text

def main():
    parser = argparse.ArgumentParser(description="WTJ Old Video Recycler Pipeline")
    parser.add_argument("-l", "--limit", type=int, default=20, help="จำนวนคลิปเก่าสูงสุดที่จะประมวลผล (default: 20)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="รันโหมดจำลองโดยไม่สร้างการ์ด Notion หรืออัปเดต state")
    parser.add_argument("-v", "--video-id", help="เจาะจงประมวลผลเฉพาะ Video ID ที่ระบุ")
    
    args = parser.parse_args()
    
    print("==================================================")
    print("🦉 เลขาเฟิส: เริ่มปฏิบัติการกู้ชีพวิดีโอเก่ามาทำโพสต์รีรัน 🚀")
    print("==================================================")
    
    notion = NotionHelper()
    existing_titles = get_all_existing_notion_titles(notion)
    state = load_state()
    
    # Get videos from CSV
    all_videos = fetch_videos_from_csv()
    print(f"🎬 คัดกรองและเรียงลำดับวิดีโอแล้ว: พบทั้งหมด {len(all_videos)} วิดีโอ")
    
    # Filter to targeted videos
    if args.video_id:
        target_videos = [v for v in all_videos if v["id"] == args.video_id]
        if not target_videos:
            print(f"❌ Error: ไม่พบวิดีโอที่มี ID '{args.video_id}' ในฐานข้อมูล CSV")
            sys.exit(1)
    else:
        # Take the oldest ones that have not been processed
        target_videos = []
        for v in all_videos:
            if v["id"] in state:
                continue
                
            # Check if Notion already has these rerun cards to avoid duplicate creation
            title_thu = f"[RERUN_THU] {v['title']}"
            title_sun = f"[RERUN_SUN] {v['title']}"
            if title_thu in existing_titles and title_sun in existing_titles:
                # Add to state so we don't scan it again
                state[v["id"]] = {
                    "title": v["title"],
                    "processed_at": datetime.now().isoformat(),
                    "notion_exists": True
                }
                continue
                
            target_videos.append(v)
            if len(target_videos) >= args.limit:
                break
                
    if not target_videos:
        print("📭 ไม่พบวิดีโอใหม่ที่ต้องทำการรีรันเลยแก! ทุกคลิปประมวลผลเสร็จหมดแล้ว")
        if not args.dry_run:
            save_state(state)
        return
        
    print(f"\n📌 รอบนี้จะประมวลผลทั้งหมด {len(target_videos)} วิดีโอ:")
    for idx, v in enumerate(target_videos, 1):
        print(f"  {idx}. {v['publish_time']} — [{v['id']}] {v['title']}")
        
    processed_count = 0
    for v in target_videos:
        video_id = v["id"]
        title = v["title"]
        url = v["url"]
        
        print(f"\n⚡ [{processed_count+1}/{len(target_videos)}] กำลังกู้ชีพตอน: '{title}' ({url})")
        
        # 1. Fetch transcript (try first)
        transcript_text = fetch_transcript(video_id)
        generated_text = None
        
        if transcript_text and len(transcript_text.strip()) >= 50:
            # 2. Generate drafts with Gemini from transcript
            generated_text = generate_rerun_drafts(title, transcript_text, url)
        else:
            # Fallback to audio download
            print(f"⚠️ ไม่พบคำบรรยายแบบข้อความสำหรับ '{title}' กำลังสลับไปดาวน์โหลดไฟล์เสียงจาก YouTube เพื่อส่งให้ Gemini ฟังตรงๆ...")
            temp_audio_filename = f"temp_audio_{video_id}.m4a"
            temp_audio_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", temp_audio_filename)
            
            if download_audio(video_id, temp_audio_path):
                generated_text = generate_rerun_drafts_from_audio(title, temp_audio_path, url)
                
                # Delete local audio file
                if os.path.exists(temp_audio_path):
                    print(f"🗑️ กำลังลบไฟล์เสียงโลคอลชั่วคราว: {temp_audio_path}")
                    os.remove(temp_audio_path)
            else:
                print(f"❌ ดาวน์โหลดเสียงไม่สำเร็จ ข้าม '{title}'")
                if not args.dry_run:
                    state[video_id] = {
                        "title": title,
                        "url": url,
                        "processed_at": datetime.now().isoformat(),
                        "status": "failed_download_audio"
                    }
                    save_state(state)
                continue
            
        if not generated_text or "[THURSDAY_POSTS]" not in generated_text:
            print(f"❌ ข้าม '{title}': เจนข้อความโพสต์จาก AI ไม่สำเร็จ")
            if not args.dry_run:
                state[video_id] = {
                    "title": title,
                    "url": url,
                    "processed_at": datetime.now().isoformat(),
                    "status": "failed_generation"
                }
                save_state(state)
            continue
            
        # Parse Thursday and Sunday posts
        thu_content = ""
        sun_content = ""
        
        thu_match = re.search(r'\[THURSDAY_POSTS\](.*?)(\[SUNDAY_POSTS\]|$)', generated_text, re.DOTALL | re.IGNORECASE)
        sun_match = re.search(r'\[SUNDAY_POSTS\](.*)', generated_text, re.DOTALL | re.IGNORECASE)
        
        if thu_match:
            thu_content = thu_match.group(1).strip()
        if sun_match:
            sun_content = sun_match.group(1).strip()
            
        if not thu_content or not sun_content:
            print(f"❌ ข้าม '{title}': แยกโพสต์วันพฤหัสหรือวันอาทิตย์ไม่ได้ (รูปแบบคำตอบไม่ตรง)")
            if not args.dry_run:
                state[video_id] = {
                    "title": title,
                    "url": url,
                    "processed_at": datetime.now().isoformat(),
                    "status": "failed_parse"
                }
                save_state(state)
            continue
            
        # Add headers for context in backups
        thu_full_draft = f"# [RERUN_THU] {title}\n**URL:** {url}\n\n" + thu_content
        sun_full_draft = f"# [RERUN_SUN] {title}\n**URL:** {url}\n\n" + sun_content
        
        # 3. Create Notion Cards
        title_thu = f"[RERUN_THU] {title}"
        title_sun = f"[RERUN_SUN] {title}"
        
        source_context = f"ถอดเทปข้อความย่อ:\n\n{transcript_text[:1500]}" if transcript_text else "วิเคราะห์รายละเอียดจากเสียงสัมภาษณ์ในคลิปโดยตรง"
        
        if args.dry_run:
            print(f"💡 [DRY-RUN] จะสร้างการ์ด Notion:")
            print(f"  - Card 1: '{title_thu}' (Status: 4_Review, Platform: FB_Text_Quote)")
            print(f"  - Card 2: '{title_sun}' (Status: 4_Review, Platform: FB_Text_Quote)")
            print(f"\n--- 📝 [DRY-RUN THURSDAY CONTENT] ---")
            print(thu_content)
            print(f"\n--- 📝 [DRY-RUN SUNDAY CONTENT] ---")
            print(sun_content)
            print("------------------------------------\n")
        else:
            # Thursday Card
            print(f"🚀 กำลังสร้างการ์ดวันพฤหัสบดี (ชวนคุย) ใน Notion...")
            new_page_thu = notion.create_page(title_thu, status_name="4_Review", platform_tags=["FB_Text_Quote"])
            if new_page_thu and "id" in new_page_thu:
                page_id_thu = new_page_thu["id"]
                # Write transcript header and the options
                full_content_thu = f"วิดีโอคำบรรยายต้นฉบับสำหรับการรีรัน:\n\n{source_context}\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + thu_content
                notion.write_page_content_text(page_id_thu, full_content_thu)
                print("✅ สร้างการ์ดวันพฤหัสสำเร็จ!")
            else:
                print("❌ ไม่สามารถสร้างการ์ดวันพฤหัสใน Notion ได้")
                
            # Sunday Card
            print(f"🚀 กำลังสร้างการ์ดวันอาทิตย์ (คำคม) ใน Notion...")
            new_page_sun = notion.create_page(title_sun, status_name="4_Review", platform_tags=["FB_Text_Quote"])
            if new_page_sun and "id" in new_page_sun:
                page_id_sun = new_page_sun["id"]
                full_content_sun = f"วิดีโอคำบรรยายต้นฉบับสำหรับการรีรัน:\n\n{source_context}\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + sun_content
                notion.write_page_content_text(page_id_sun, full_content_sun)
                print("✅ สร้างการ์ดวันอาทิตย์สำเร็จ!")
            else:
                print("❌ ไม่สามารถสร้างการ์ดวันอาทิตย์ใน Notion ได้")
                
        # 4. Save local backup drafts
        clean_topic = re.sub(r'[^\w\s]', '', title).strip().replace(" ", "_").lower()
        os.makedirs(DRAFTS_DIR, exist_ok=True)
        
        backup_path_thu = os.path.join(DRAFTS_DIR, f"rerun_thu_{clean_topic}.md")
        backup_path_sun = os.path.join(DRAFTS_DIR, f"rerun_sun_{clean_topic}.md")
        
        if args.dry_run:
            print(f"💡 [DRY-RUN] จะบันทึกไฟล์ดราฟต์สำรองที่: {backup_path_thu} และ {backup_path_sun}")
        else:
            with open(backup_path_thu, "w", encoding="utf-8") as f:
                f.write(thu_full_draft)
            with open(backup_path_sun, "w", encoding="utf-8") as f:
                f.write(sun_full_draft)
            print(f"💾 บันทึกดราฟต์สำรองสำเร็จที่: {DRAFTS_DIR}")
            
        # 5. Update state
        if not args.dry_run:
            state[video_id] = {
                "title": title,
                "url": url,
                "processed_at": datetime.now().isoformat(),
                "status": "success"
            }
            save_state(state)
            
        processed_count += 1
        
    print(f"\n🎉 ปฏิบัติการกู้ชีพเสร็จสิ้น! ประมวลผลสำเร็จไป {processed_count} ตอนจ้า 🦉🤘✨")

if __name__ == "__main__":
    main()
