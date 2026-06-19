#!/usr/bin/env python3
"""
🚀 WTJ Master Auto-Poster (Sequential/Queue-based)
ดึงการ์ดที่อนุมัติแล้ว (Status = '5_Approved') ใน Notion ตามคิวงานที่ระบุ
เรียงตามตัวเลขหน้าคลิปเพื่อความต่อเนื่อง (Sequential Posting)
และทำการโพสต์ไปยังทุกแพลตฟอร์มที่ระบุในการ์ดทีละแพลตฟอร์มจนครบ
"""

import os
import sys
import argparse
import re
from datetime import datetime, timezone, timedelta

# Set up paths
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
from youtube_publisher import get_youtube_client, upload_video_to_youtube, extract_filename_from_title, find_video_file
from discord_helper import DiscordHelper

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# คิวงาน -> แพลตฟอร์มหลักใน Notion
QUEUE_PLATFORM_MAP = {
    "Reels_Under1Min": "Reels",
    "Text_Posts": "FB_Text_Quote",
    "YT_Videos_Full": "YouTube"
}

def get_sort_key(page):
    title = page.get("title", "")
    created_time = page.get("created_time") or ""
    
    # สำหรับคลิปใหม่หรือโพสต์ทั่วไป ให้จัดเรียงตามตัวเลขตอน
    # 1. ค้นหาแบบบังคับว่าต้องมีคำนำหน้าตอน เช่น ep, ep., episode
    match = re.search(r'\b(?:ep|ep\.|episode|no\.|no|episode)\s*(\d+)', title, re.IGNORECASE)
    
    # 2. หากไม่พบ ค่อยค้นหาตัวเลขแรกหลังวงเล็บเหลี่ยมปิด หรือตัวเลขทั่วไปตัวแรกสุด
    if not match:
        match = re.search(r'(?:\]\s*)(\d+)', title)
    if not match:
        match = re.search(r'\b(\d+)\b', title)
        
    if match:
        return (0, int(match.group(1)), created_time, title)
    return (1, created_time, title)

def clean_post_content_fallback(post_content):
    """
    หากตรวจพบว่าเนื้อหาโพสต์ยังคงมีรูปแบบเทมเพลตดราฟต์ (เช่น ทางเลือกที่ 1, ทางเลือกที่ 2)
    จะทำการสกัดเอาเฉพาะข้อความของทางเลือกที่ถูกเลือก (หรือทางเลือกที่ 1 เป็นค่าเริ่มต้น)
    และทำการตัดทรานสคริปต์รวมถึงส่วนหัวออก เพื่อป้องกันการโพสต์ติดดราฟต์ดิบและถอดเทป
    """
    opt1_pat = r'(?:ทางเลือกที่\s*1|ทางเลือก\s*1|Option\s*1)\s*:\s*'
    opt2_pat = r'(?:ทางเลือกที่\s*2|ทางเลือก\s*2|Option\s*2)\s*:\s*'
    opt3_pat = r'(?:ทางเลือกที่\s*3|ทางเลือก\s*3|Option\s*3)\s*:\s*'
    
    has_opt1 = re.search(opt1_pat, post_content, re.IGNORECASE)
    has_opt2 = re.search(opt2_pat, post_content, re.IGNORECASE)
    has_opt3 = re.search(opt3_pat, post_content, re.IGNORECASE)
    
    if not (has_opt1 or has_opt2 or has_opt3):
        return post_content  # ไม่พบรูปแบบเทมเพลต ส่งข้อความเดิมคืน
        
    extracted = ""
    if has_opt1:
        match = re.search(opt1_pat + r'(.*?)(?=(?:ทางเลือกที่\s*2|ทางเลือก\s*2|Option\s*2|ทางเลือกที่\s*3|ทางเลือก\s*3|Option\s*3|$))', post_content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
    elif has_opt2:
        match = re.search(opt2_pat + r'(.*?)(?=(?:ทางเลือกที่\s*3|ทางเลือก\s*3|Option\s*3|$))', post_content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
    elif has_opt3:
        match = re.search(opt3_pat + r'(.*)', post_content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            
    if extracted:
        extracted = extracted.strip()
        if (extracted.startswith('"') and extracted.endswith('"')) or \
           (extracted.startswith('“') and extracted.endswith('”')) or \
           (extracted.startswith("'") and extracted.endswith("'")):
            extracted = extracted[1:-1].strip()
        print("✨ [Fallback Cleaner] ตรวจพบเทมเพลตดราฟต์ ทำการสกัดเฉพาะตัวเลือกที่ระบุสำเร็จ!")
        return extracted
        
    return post_content

def prepare_platform_content(post_content, platform):
    """
    ตรวจหาบรรทัดแฮชแท็กเฉพาะของแต่ละแพลตฟอร์มใน post_content
    """
    lines = post_content.splitlines()
    platform_patterns = {
        "Facebook": [r'^#FB\s*:\s*(.*)', r'^#Facebook\s*:\s*(.*)'],
        "YouTube": [r'^#YT\s*:\s*(.*)', r'^#YouTube\s*:\s*(.*)'],
        "TikTok": [r'^#TikTok\s*:\s*(.*)', r'^#TT\s*:\s*(.*)']
    }
    
    has_platform_lines = False
    for line in lines:
        stripped = line.strip()
        for plat, patterns in platform_patterns.items():
            for pat in patterns:
                if re.match(pat, stripped, re.IGNORECASE):
                    has_platform_lines = True
                    break
            if has_platform_lines:
                break
        if has_platform_lines:
            break
            
    if not has_platform_lines:
        return post_content
        
    target_hashtags = ""
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        is_platform_line = False
        
        for plat, patterns in platform_patterns.items():
            for pat in patterns:
                match = re.match(pat, stripped, re.IGNORECASE)
                if match:
                    is_platform_line = True
                    if plat == platform:
                        target_hashtags = match.group(1).strip()
                    break
            if is_platform_line:
                break
                
        if not is_platform_line:
            cleaned_lines.append(line)
            
    cleaned_body = "\n".join(cleaned_lines).strip()
    if target_hashtags:
        cleaned_body = cleaned_body + "\n" + target_hashtags
        
    return cleaned_body

def main():
    parser = argparse.ArgumentParser(description="WTJ Master Auto-Poster (Sequential Queue)")
    parser.add_argument("-q", "--queue", required=True, choices=["Reels_Under1Min", "Text_Posts", "YT_Videos_Full"],
                        help="ชื่อคิวงานที่ต้องการโพสต์")
    parser.add_argument("-d", "--dry-run", action="store_true", help="จำลองการทำงานโดยไม่โพสต์จริง")
    parser.add_argument("--yt-privacy", default="public", choices=["public", "private", "unlisted", "draft"],
                        help="ระดับความเป็นส่วนตัว YouTube (default: public)")
    
    args = parser.parse_args()
    
    load_env()
    
    print("=" * 60)
    print(f"🚀 Master Auto-Poster Running (Queue: {args.queue})")
    print(f"📅 เวลาทำงาน: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"💡 Dry-run mode: {args.dry_run}")
    print("=" * 60)
    
    notion = NotionHelper()
    print("🔍 กำลังดึงการ์ดที่มีสถานะ '5_Approved' จาก Notion...")
    pages = notion.fetch_pages_by_status("5_Approved")
    
    if not pages:
        print("📭 ไม่พบโพสต์ใดที่มีสถานะ '5_Approved' ใน Notion เลยแก!")
        return
        
    target_platform_tag = QUEUE_PLATFORM_MAP.get(args.queue)
    filtered_pages = []
    
    for page in pages:
        platforms = page.get("platforms", [])
        if args.queue == "YT_Videos_Full":
            if "YouTube" in platforms and "Reels" not in platforms:
                filtered_pages.append(page)
        elif args.queue == "Reels_Under1Min":
            if "Reels" in platforms:
                filtered_pages.append(page)
        else:
            if target_platform_tag in platforms:
                filtered_pages.append(page)
            
    if not filtered_pages:
        print(f"📭 ไม่พบการ์ดสำหรับคิว '{args.queue}' ที่ได้รับการอนุมัติ")
        return
        
    filtered_pages.sort(key=get_sort_key)
    
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    ready_pages = []
    for page in filtered_pages:
        publish_date_str = page.get("publish_date")
        if not publish_date_str:
            if args.queue in ["YT_Videos_Full", "Reels_Under1Min"]:
                ready_pages.append(page)
                continue
            print(f"⚠️ การ์ด '{page['title']}' อนุมัติแล้วแต่ไม่มี Publish Date ข้ามไปก่อนนะแก...")
            continue
            
        try:
            if "T" in publish_date_str:
                pub_dt = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00")).astimezone(tz_th)
            else:
                dt = datetime.strptime(publish_date_str, "%Y-%m-%d")
                pub_dt = datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
                
            if now_local >= pub_dt or args.queue in ["YT_Videos_Full", "Reels_Under1Min"]:
                ready_pages.append(page)
            else:
                time_diff = pub_dt - now_local
                print(f"⏳ การ์ด '{page['title']}' ตั้งเวลาไว้ในอนาคต ({pub_date_str} - อีก {time_diff}) ข้ามไปก่อนแก...")
        except Exception as e:
            print(f"⚠️ เกิดข้อผิดพลาดในการตรวจสอบเวลาของการ์ด '{page['title']}': {e}")
            continue
            
    if not ready_pages:
        print("📭 ไม่พบโพสต์ใดในคิวนี้ที่ถึงกำหนดเวลาเผยแพร่แล้วแก!")
        return
        
    print(f"📋 พบโพสต์ในคิว '{args.queue}' ที่พร้อมทำงานทั้งหมด {len(ready_pages)} ใบ")
    for target_page in ready_pages:
        page_id_notion = target_page["id"]
        title = target_page["title"]
        platforms = target_page["platforms"]
        
        print(f"\n📢 เลือกการ์ดที่จะโพสต์ลำดับถัดไป: '{title}'")
        print(f"🏷️ แพลตฟอร์มทั้งหมดที่ต้องเผยแพร่: {platforms}")
        
        print(f"📖 กำลังเข้าไปดึงข้อมูลจากเนื้อหาในหน้าเพจ...")
        raw_body = notion.get_page_content_text(page_id_notion).strip()
        
        if not raw_body or raw_body.strip() == "":
            print(f"❌ ไม่พบเนื้อหาใดๆ สำหรับการ์ด '{title}' ข้ามไปก่อนนะแก!")
            continue
            
        body_lines = [line.strip() for line in raw_body.splitlines() if line.strip()]
        first_line_body = body_lines[0] if body_lines else ""
        
        video_filename = None
        if first_line_body:
            clean_first = re.sub(r'^Headline\s+', '', first_line_body, flags=re.IGNORECASE).strip()
            video_filename = extract_filename_from_title(clean_first)
            
        if not video_filename:
            video_filename = extract_filename_from_title(title)
            
        content_lines = raw_body.splitlines()
        if content_lines and first_line_body and (first_line_body in content_lines[0] or any(ext in content_lines[0].lower() for ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm'])):
            content_lines = content_lines[1:]
        post_content = "\n".join(content_lines).strip()
        
        if args.queue != "YT_Videos_Full":
            post_content = clean_post_content_fallback(post_content)
            
        if not post_content or post_content.strip() == "":
            print(f"❌ ไม่พบเนื้อหาโพสต์ภายหลังจากข้าม Headline สำหรับการ์ด '{title}' ข้ามไปก่อนนะแก!")
            continue
            
        video_path = None
        is_video_queue = ("Reels" in platforms or "FB_Video" in platforms or "YouTube" in platforms or "Short" in platforms)
        if is_video_queue:
            if not video_filename:
                print(f"❌ ไม่สามารถสกัดหาชื่อไฟล์วิดีโอ .mp4 จากหัวข้อการ์ดหรือหน้าเพจ '{title}' ได้!")
                continue
            video_path = find_video_file(video_filename)
            if not video_path:
                print(f"❌ ไม่พบไฟล์วิดีโอ '{video_filename}' ในเครื่องเลยแก!")
                continue
            print(f"🎬 พบไฟล์วิดีโอสำหรับโพสต์: {video_path}")
            
        success_flags = {}
        
        # ------------------ 1. Facebook & TikTok -> Discord Manual Post Redirect ------------------
        manual_platforms = [p for p in platforms if p in ["Reels", "FB_Video", "FB_Text_Quote", "TikTok"]]
        if manual_platforms:
            print(f"\n💬 [Discord Manual Post Queue] Redirecting platforms {manual_platforms} to Discord...")
            manual_webhook_url = os.environ.get("DISCORD_MANUAL_POST_WEBHOOK_URL")
            if not manual_webhook_url:
                print("⚠️ ไม่พบ DISCORD_MANUAL_POST_WEBHOOK_URL ใน .env, ใช้ DISCORD_WEBHOOK_URL สำรอง")
                manual_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
                
            if not args.dry_run and not manual_webhook_url:
                print("❌ ไม่พบ Webhook URL สำหรับ Discord ใน .env")
                for plat in manual_platforms:
                    success_flags[plat] = False
            else:
                try:
                    pref_platform = "Facebook"
                    if "TikTok" in manual_platforms and len(manual_platforms) == 1:
                        pref_platform = "TikTok"
                    
                    prepared_content = prepare_platform_content(post_content, pref_platform)
                    
                    platform_names = ", ".join(manual_platforms)
                    embed_fields = [
                        {"name": "🏷️ แพลตฟอร์มที่ต้องโพสต์มือ", "value": f"**{platform_names}**", "inline": False}
                    ]
                    
                    if video_path:
                        embed_fields.append({
                            "name": "📁 พาธไฟล์วิดีโอบนเครื่อง Mac",
                            "value": f"`{video_path}`",
                            "inline": False
                        })
                    
                    embed_fields.append({
                        "name": "📝 แคปชันข้อความ (Copyable)",
                        "value": f"```\n{prepared_content}\n```",
                        "inline": False
                    })
                    
                    if args.dry_run:
                        print(f"💡 [DRY-RUN] ส่งข้อมูลโพสต์มือของ {platform_names} ไปยัง Discord...")
                        success = True
                    else:
                        discord_manual = DiscordHelper(webhook_url=manual_webhook_url)
                        success = discord_manual.send_info(
                            title=f"เตรียมโพสต์มือ: {title}",
                            description=f"กรุณาก๊อปปี้แคปชันด้านล่างและนำไฟล์วิดีโอดังกล่าวไปโพสต์ด้วยตนเองจ้าแก",
                            fields=embed_fields,
                            username="WTJ Manual Post Assistant"
                        )
                    
                    for plat in manual_platforms:
                        success_flags[plat] = bool(success)
                        
                except Exception as e:
                    print(f"❌ เกิดข้อผิดพลาดในการส่งข้อมูลเข้า Discord: {e}")
                    for plat in manual_platforms:
                        success_flags[plat] = False
                
        # ------------------ 2. YouTube Publishing ------------------
        if "YouTube" in platforms or "Reels" in platforms or "Short" in platforms:
            print("\n🔴 [YouTube Publishing]")
            try:
                # Detect project type based on title to select the right token
                title_lower = title.lower()
                if "sidekick" in title_lower or "game balancer" in title_lower or "stage engineer" in title_lower:
                    token_filename = "credentials/token_youtube_sidekick.json"
                else:
                    token_filename = "credentials/token_youtube_wtj.json"
                
                print(f"🔑 ใช้ไฟล์โทเค็น YouTube: {token_filename}")
                youtube_client = get_youtube_client(token_filename=token_filename) if not args.dry_run else None
                
                default_tags = ["What the job", "WTJ", "เก่ง What the job", "สมัครงาน", "สัมภาษณ์งาน", "มนุษย์เงินเดือน", "รีวิวอาชีพ", "พัฒนาตัวเอง"]
                tags = default_tags.copy()
                
                yt_prepared_content = prepare_platform_content(post_content, "YouTube")
                
                hashtags = re.findall(r'#([^\s#]+)', yt_prepared_content)
                if hashtags:
                    tags.extend(hashtags)
                    
                tags_match = re.search(r'(?:Tags|Tag ใน description|แท็ก|Tag)\s*[\s*:\s*]\s*([\s\S]*?)$', yt_prepared_content, re.IGNORECASE)
                if tags_match:
                    content_tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]
                    tags.extend(content_tags)
                    
                tags = list(set(tags))
                
                is_shorts = "Reels" in platforms or "Short" in platforms
                thumbnail_path = None
                
                if is_shorts:
                    content_lines = [line.strip() for line in yt_prepared_content.split("\n") if line.strip()]
                    clean_lines = []
                    for line in content_lines:
                        line_lower = line.lower()
                        if any(h in line_lower for h in ["ทางเลือกที่", "ทางเลือก", "option", "queue:"]):
                            continue
                        if line.startswith("#WhatTheJob") or line.startswith("ดูคลิปเต็มที่"):
                            continue
                        clean_line = re.sub(r'#[^\s#]+', '', line).strip()
                        if clean_line:
                            clean_lines.append(clean_line)
                            
                    yt_title = f"{os.path.splitext(video_filename)[0] if video_filename else title} | WTJ Shorts"
                    if clean_lines:
                        candidate = clean_lines[0].replace('"', '').replace('“', '').replace('”', '')
                        if len(candidate) > 10 and len(candidate) < 70:
                            yt_title = f"{candidate} #Shorts"
                            
                    yt_description = yt_prepared_content + "\n\n📲 ติดตามเพจของเราได้ที่: https://www.facebook.com/WhatTheJobs"
                else:
                    yt_section_headers = [
                        "# ✍️ YOUTUBE DRAFTS",
                        "✍️ YOUTUBE DRAFTS",
                        "# YOUTUBE DRAFTS",
                        "YOUTUBE DRAFTS"
                    ]
                    yt_section = ""
                    for header in yt_section_headers:
                        if header in post_content:
                            yt_section = post_content.split(header, 1)[1].strip()
                            break
                    if not yt_section:
                        yt_section = post_content
                        
                    boundary_pattern = r'(?:[\*\#\s]*(?:Description Draft|Description|คำอธิบายคลิปสั้น|ติดต่องานและลงโฆษณา|Timestamps|Chapters/Timestamps|Timeline|Timeline ช่วงเวลาสำคัญ|สารบัญเวลา|Timestamp|ติดตามช่องทางอื่นๆ|Tag ใน description|แท็ก|Tag|🔵 FACEBOOK POSTS DRAFT|\# FACEBOOK POSTS DRAFT|FACEBOOK POSTS DRAFT)[\*\#\s:]*|$)'
                    
                    title_options_block = ""
                    title_match = re.search(r'(?:[\*\#\s]*Title Options[\*\#\s:]*)[\s\S]*?(?=' + boundary_pattern + ')', yt_section, re.IGNORECASE)
                    if title_match:
                        title_options_block = title_match.group(0).strip()
                        
                    yt_title = ""
                    if title_options_block:
                        for line in title_options_block.splitlines():
                            line_clean = line.strip()
                            if not line_clean:
                                continue
                            if re.match(r'^\s*[\*\#\-\s]*Title Options[\*\#\s-:]*$', line_clean, re.IGNORECASE):
                                continue
                            line_lower = line_clean.lower()
                            if any(kw in line_lower for kw in ["ติดต่องานและลงโฆษณา", "line :", "email :"]) or "@ghn168" in line_lower or "charismazz" in line_lower or "ghn168media" in line_lower or "silver_nsx" in line_lower:
                                continue
                            line_clean = re.sub(r'^\s*(?:\d+[\.\)\s]+|option\s*\d+[\.\)\s:]*)\s*', '', line_clean, flags=re.IGNORECASE).strip()
                            line_clean = line_clean.strip('"').strip("'").strip('*').strip()
                            if line_clean:
                                yt_title = line_clean
                                break
                                
                    if not yt_title:
                        yt_lines = [l.strip() for l in yt_section.splitlines() if l.strip()]
                        for l in yt_lines:
                            l_lower = l.lower()
                            if l.startswith('#') or any(h in l_lower for h in ["title options", "description", "คำอธิบาย", "ติดต่องาน", "line :", "email :", "timestamp", "timeline", "tag"]):
                                continue
                            l_clean = re.sub(r'^\s*(?:\d+[\.\)\s]+|option\s*\d+[\.\)\s:]*)\s*', '', l, flags=re.IGNORECASE).strip()
                            l_clean = l_clean.strip('"').strip("'").strip('*').strip()
                            if l_clean:
                                yt_title = l_clean
                                break
                                
                    if not yt_title:
                        yt_title = os.path.splitext(video_filename)[0].strip() if video_filename else title

                    yt_section_cleaned = yt_section
                    if title_match:
                        yt_section_cleaned = yt_section.replace(title_match.group(0), "")
                        
                    desc_header_match = re.search(r'(?:[\*\#\s]*(?:ติดต่องานและลงโฆษณา|Description Draft|Description|คำอธิบายคลิปสั้น)[\*\#\s:]*)', yt_section_cleaned, re.IGNORECASE)
                    if desc_header_match:
                        matched_text = desc_header_match.group(0)
                        yt_description = matched_text + yt_section_cleaned.split(matched_text, 1)[1]
                    else:
                        yt_description = yt_section_cleaned

                    clean_desc_lines = []
                    for line in yt_description.splitlines():
                        if re.match(r'^\s*[\*\#\-\s]*(?:Description\s*Draft|Description|คำอธิบายคลิปสั้น)[\*\#\-\s:]*$', line, re.IGNORECASE):
                            continue
                        if any(ph in line for ph in ["[ใส่ชื่อแขกรับเชิญ]", "[ใส่ช่องทางติดต่อแขกรับเชิญ]", "[ใส่ช่องทางติดต่อ]", "[ใส่ชื่อ]"]):
                            continue
                        clean_desc_lines.append(line)
                    yt_description = "\n".join(clean_desc_lines).strip()

                    yt_description = re.sub(r'\s*[\*\#\-\•\s🎬🎥📝📲⏳✨]*$', '', yt_description).strip()

                    yt_description = "\n".join([
                        line for line in yt_description.splitlines()
                        if not re.match(r'^\s*(?:Tags|แท็ก)\s*:', line, re.IGNORECASE)
                    ]).strip()

                    tags_header_match = re.search(r'(?:[\*\#\s]*(?:Tag ใน description|Tags|แท็ก)[\*\#\s:]*)([\s\S]*?)$', yt_description, re.IGNORECASE)
                    if tags_header_match:
                        raw_tags_text = tags_header_match.group(1).strip()
                        parsed_keywords = [k.strip() for k in raw_tags_text.replace("#", "").split(",") if k.strip()]
                        desc_hashtags = []
                        for kw in parsed_keywords:
                            clean_kw = re.sub(r'\s+', '', kw)
                            if clean_kw:
                                desc_hashtags.append(f"#{clean_kw}")
                        for dt in default_tags:
                            clean_dt = re.sub(r'\s+', '', dt)
                            hashtag_dt = f"#{clean_dt}"
                            if hashtag_dt not in desc_hashtags:
                                desc_hashtags.append(hashtag_dt)
                        formatted_hashtags_str = " ".join(desc_hashtags)
                        prefix = yt_description.split(tags_header_match.group(0), 1)[0].strip()
                        yt_description = f"{prefix}\n\n{formatted_hashtags_str}".strip()
                        
                    if video_filename:
                        base_name = os.path.splitext(video_filename)[0].strip()
                        thumb_dirs = [
                            os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "thumbnails"),
                            os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Podcast", "workspace", "1_raw_materials", "thumbnails"),
                        ]
                        for thumb_dir in thumb_dirs:
                            if not os.path.exists(thumb_dir):
                                continue
                            for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]:
                                check_path = os.path.join(thumb_dir, base_name + ext)
                                if os.path.exists(check_path):
                                    thumbnail_path = check_path
                                    print(f"🖼️ พบไฟล์ภาพหน้าปกที่จะใช้อัปโหลด: {thumbnail_path}")
                                    break
                            if thumbnail_path:
                                break
                                
                        if not thumbnail_path:
                            print("⚠️ ไม่พบไฟล์ภาพหน้าปกในโฟลเดอร์ thumbnails/ จะอัปโหลดเฉพาะคลิปยาวโดยให้ระบบสุ่มปก")
                
                paid_promotion = False
                raw_props = target_page.get("raw_properties", {})
                paid_prop = raw_props.get("Paid Promotion", {})
                if paid_prop.get("type") == "checkbox":
                    paid_promotion = bool(paid_prop.get("checkbox", False))
                    
                playlist_name = None
                category_id = None
                if video_path:
                    if "WTJ_Podcast" in video_path or "WTJ Podcast" in video_path:
                        playlist_name = "WTJ Podcast"
                        category_id = "22"
                    elif "WTJ_Story" in video_path or "WTJ Story" in video_path:
                        playlist_name = "WTJ Story"
                        category_id = "27"
                
                publish_at_str = None
                publish_dt = target_page.get("publish_dt")
                if publish_dt and publish_dt > now_local:
                    publish_dt_utc = publish_dt.astimezone(timezone.utc)
                    publish_at_str = publish_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                success = upload_video_to_youtube(
                    youtube_client,
                    video_path=video_path,
                    title=yt_title,
                    description=yt_description,
                    tags=tags,
                    privacy_status=args.yt_privacy,
                    dry_run=args.dry_run,
                    thumbnail_path=thumbnail_path,
                    publish_at=publish_at_str,
                    paid_promotion=paid_promotion,
                    playlist_name=playlist_name,
                    category_id=category_id
                )
                success_flags["YouTube"] = success
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดกับ YouTube API: {e}")
                success_flags["YouTube"] = False
                
        # ------------------ 3. TikTok (Redirected to Discord above) ------------------
        pass
                
        # สรุปผลการทำงาน
        print("\n" + "=" * 40)
        print("📊 สรุปการประมวลผลโพสต์:")
        all_ok = True
        for platform, success in success_flags.items():
            status_str = "✅ สำเร็จ" if success else "❌ ล้มเหลว"
            print(f" - {platform}: {status_str}")
            if not success:
                all_ok = False
                
        if all_ok:
            if args.dry_run:
                print("\n💡 [DRY-RUN] โพสต์สำเร็จเสมือนจริง จะเปลี่ยนสถานะหน้าเพจ Notion เป็น '6_Published'")
            else:
                notion.update_page_status(page_id_notion, "6_Published")
                print(f"\n🎉 โพสต์สำเร็จทุกช่องทาง! อัปเดตสถานะการ์ด '{title}' ใน Notion เป็น '6_Published' เรียบร้อยแก!")
        else:
            print("\n⚠️ มีข้อผิดพลาดในบางช่องทาง การ์ดใน Notion จะยังคงอยู่ในสถานะ '5_Approved' เพื่อแก้ไขและลองใหม่")
        print("=" * 40 + "\n")
    
        if not args.dry_run and success_flags:
            try:
                discord = DiscordHelper()
                fields = []
                for platform, success in success_flags.items():
                    fields.append({
                        "name": platform,
                        "value": "🟢 สำเร็จ" if success else "🔴 ล้มเหลว",
                        "inline": True
                    })
                
                description = f"**การ์ด Notion:** {title}\n**คิวงาน:** `{args.queue}`"
                if all_ok:
                    discord.send_success(
                        title="ยิงโพสต์ขึ้นครบทุกช่องทางเรียบร้อยแล้วแก! 🚀",
                        description=description,
                        fields=fields
                    )
                else:
                    discord.send_warning(
                        title="โพสต์สำเร็จบางช่องทาง/ต้องตรวจสอบ ⚠️",
                        description=description,
                        fields=fields
                    )
            except Exception as e:
                print(f"⚠️ ไม่สามารถส่งแจ้งเตือน Discord ได้: {e}")

if __name__ == "__main__":
    main()
