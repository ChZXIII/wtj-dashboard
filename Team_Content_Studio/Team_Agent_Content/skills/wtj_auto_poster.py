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
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Find project root dynamically
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from notion_helper import NotionHelper
from facebook_publisher import publish_to_facebook, upload_video_to_facebook_reels, upload_video_to_facebook_page
from youtube_publisher import get_youtube_client, upload_video_to_youtube, extract_filename_from_title, find_video_file
from tiktok_publisher import get_tiktok_client, upload_video_to_tiktok
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
    "FB_Videos_3-5Min": "FB_Video",
    "Reels_Under1Min": "Reels",
    "Text_Posts": "FB_Text_Quote",
    "YT_Videos_Full": "YouTube"
}

def get_sort_key(page):
    title = page.get("title", "")
    created_time = page.get("created_time") or ""
    # ดึงตัวเลขแรกสุดที่ตามหลัง ] หรืออยู่หน้าสุด เช่น "[Reels_Under1Min] 02 เก่ง..." -> 2
    match = re.search(r'(?:\]\s*|^)(\d+)', title)
    if match:
        return (0, int(match.group(1)), created_time, title)
    # สำหรับการ์ด Rerun หรือการ์ดที่ไม่มีตัวเลข ให้เรียงตามเวลาที่สร้างใน Notion (เก่าสุดไปใหม่สุด)
    return (1, created_time, title)

def main():
    parser = argparse.ArgumentParser(description="WTJ Master Auto-Poster (Sequential Queue)")
    parser.add_argument("-q", "--queue", required=True, choices=["FB_Videos_3-5Min", "Reels_Under1Min", "Text_Posts", "YT_Videos_Full"],
                        help="ชื่อคิวงานที่ต้องการโพสต์")
    parser.add_argument("-d", "--dry-run", action="store_true", help="จำลองการทำงานโดยไม่โพสต์จริง")
    parser.add_argument("--yt-privacy", default="public", choices=["public", "private", "unlisted", "draft"],
                        help="ระดับความเป็นส่วนตัว YouTube (default: public)")
    parser.add_argument("--tt-privacy", default="self", choices=["public", "self", "friends"],
                        help="ระดับความเป็นส่วนตัว TikTok (default: self)")
    
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
            # สำหรับคลิปยาว YouTube: ต้องมี "YouTube" แต่ห้ามมี "Reels"
            if "YouTube" in platforms and "Reels" not in platforms:
                filtered_pages.append(page)
        elif args.queue == "Reels_Under1Min":
            # สำหรับ Shorts: ต้องมี "Reels"
            if "Reels" in platforms:
                filtered_pages.append(page)
        else:
            # คิวอื่นๆ เช็คตรงตัว
            if target_platform_tag in platforms:
                filtered_pages.append(page)
            
    if not filtered_pages:
        print(f"📭 ไม่พบการ์ดสำหรับคิว '{args.queue}' ที่ได้รับการอนุมัติ")
        return
        
    # เรียงลำดับจากน้อยไปมากตามตัวเลข (Sequential)
    filtered_pages.sort(key=get_sort_key)
    
    # กรองเอาเฉพาะการ์ดที่ถึงกำหนดเวลาเผยแพร่แล้ว (หรือไม่ได้ใส่วันที่)
    ready_pages = []
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    for page in filtered_pages:
        pub_date_str = page.get("publish_date")
        if not pub_date_str:
            # ถ้าไม่ได้กำหนดวันที่ ให้ถือว่าพร้อมโพสต์เลย (คิวดั้งเดิม)
            ready_pages.append(page)
            continue
            
        try:
            if "T" in pub_date_str:
                pub_dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")).astimezone(tz_th)
            else:
                dt = datetime.strptime(pub_date_str, "%Y-%m-%d")
                pub_dt = datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
                
            if now_local >= pub_dt:
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
        
    # ดึงการ์ดแรกสุดที่ต้องการโพสต์รอบนี้
    target_page = ready_pages[0]
    page_id_notion = target_page["id"]
    title = target_page["title"]
    platforms = target_page["platforms"]
    approved_copy = target_page["approved_copy"]
    
    print(f"\n📢 เลือกการ์ดที่จะโพสต์ลำดับถัดไป: '{title}'")
    print(f"🏷️ แพลตฟอร์มทั้งหมดที่ต้องเผยแพร่: {platforms}")
    
    # เตรียมข้อมูลบท
    post_content = approved_copy
    if not post_content or post_content.strip() == "":
        print(f"⚠️ Approved Copy ว่างเปล่า กำลังเข้าไปดึงข้อมูลจากเนื้อหาในหน้าเพจแทน...")
        raw_body = notion.get_page_content_text(page_id_notion)
        if "## 📝 Draft Options" in raw_body:
            raw_body = raw_body.split("## 📝 Draft Options")[0].strip()
        if "---" in raw_body:
            raw_body = raw_body.split("---")[0].strip()
        post_content = raw_body.strip()
        
    if not post_content or post_content.strip() == "":
        print(f"❌ ไม่พบเนื้อหาใดๆ สำหรับการ์ด '{title}' ข้ามไปก่อนนะแก!")
        return
        
    # เช็คว่ามีไฟล์วิดีโอหรือไม่ (สำหรับ Reels และ FB Video)
    video_path = None
    is_video_queue = ("Reels" in platforms or "FB_Video" in platforms or "YouTube" in platforms)
    if is_video_queue:
        video_filename = extract_filename_from_title(title)
        if not video_filename:
            print(f"❌ ไม่สามารถสกัดหาชื่อไฟล์วิดีโอ .mp4 จากหัวข้อการ์ด '{title}' ได้!")
            return
        video_path = find_video_file(video_filename)
        if not video_path:
            print(f"❌ ไม่พบไฟล์วิดีโอ '{video_filename}' ในเครื่องเลยแก!")
            return
        print(f"🎬 พบไฟล์วิดีโอสำหรับโพสต์: {video_path}")
        
    success_flags = {}
    
    # ------------------ 1. Facebook Reels / Post ------------------
    # ถ้ามี Reels, FB_Video หรือ FB_Text_Quote ในแพลตฟอร์ม
    if any(p in platforms for p in ["Reels", "FB_Video", "FB_Text_Quote"]):
        print("\n🔵 [Facebook Publishing]")
        fb_page_id = os.environ.get("FACEBOOK_PAGE_ID")
        fb_access_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        
        if not args.dry_run and (not fb_page_id or not fb_access_token):
            print("❌ ไม่พบ FACEBOOK_PAGE_ID หรือ FACEBOOK_PAGE_ACCESS_TOKEN ใน .env")
            success_flags["Facebook"] = False
        else:
            # ตรวจสอบประเภทคิวงานเพื่อสวิตช์ฟังก์ชันการอัปโหลดที่ถูกต้อง
            if "Reels" in platforms and video_path:
                print("🎬 ตรวจพบประเภทคิว Reels: กำลังอัปโหลดวิดีโอเข้า Facebook Reels...")
                success = upload_video_to_facebook_reels(video_path, fb_page_id, fb_access_token, post_content, dry_run=args.dry_run)
            elif "FB_Video" in platforms and video_path:
                print("🎬 ตรวจพบประเภทคิว FB_Video: กำลังอัปโหลดวิดีโอเข้า Facebook Page Video...")
                success = upload_video_to_facebook_page(video_path, fb_page_id, fb_access_token, post_content, dry_run=args.dry_run)
            else:
                print("✍️ ตรวจพบประเภทโพสต์ข้อความ: กำลังยิงโพสต์ข้อความขึ้น Facebook...")
                success = publish_to_facebook(post_content, fb_page_id, fb_access_token, dry_run=args.dry_run)
            
            success_flags["Facebook"] = bool(success)
            
    # ------------------ 2. YouTube Publishing ------------------
    if "YouTube" in platforms or "Reels" in platforms:
        print("\n🔴 [YouTube Publishing]")
        try:
            youtube_client = get_youtube_client() if not args.dry_run else None
            
            # เตรียมแฮชแท็กและคีย์เวิร์ด
            default_tags = ["What the job", "WTJ", "เก่ง What the job", "สมัครงาน", "สัมภาษณ์งาน", "มนุษย์เงินเดือน", "รีวิวอาชีพ", "พัฒนาตัวเอง"]
            tags = default_tags.copy()
            
            # ดึงแฮชแท็กทั่วไปจากเนื้อหา
            hashtags = re.findall(r'#([^\s#]+)', post_content)
            if hashtags:
                tags.extend(hashtags)
                
            # ดึงจากส่วนเจาะจงที่น้องเรย์เขียน เช่น Tags: tag1, tag2 หรือ แท็ก: tag1, tag2
            tags_match = re.search(r'(?:Tags|แท็ก)\s*:\s*(.*)', post_content, re.IGNORECASE)
            if tags_match:
                content_tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]
                tags.extend(content_tags)
                
            # ลบตัวซ้ำ
            tags = list(set(tags))
            
            is_shorts = "Reels" in platforms
            thumbnail_path = None
            
            if is_shorts:
                # --- ยูทูบ Shorts ---
                content_lines = [line.strip() for line in post_content.split("\n") if line.strip()]
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
                        
                yt_title = f"{title.split('] ')[-1].split('.mp4')[0]} | WTJ Shorts"
                if clean_lines:
                    candidate = clean_lines[0].replace('"', '').replace('“', '').replace('”', '')
                    if len(candidate) > 10 and len(candidate) < 70:
                        yt_title = f"{candidate} #Shorts"
                        
                yt_description = post_content + "\n\n📲 ติดตามเพจของเราได้ที่: https://www.facebook.com/WhatTheJobs"
            else:
                # --- ยูทูบ คลิปยาวตัวเต็ม (Long Video) ---
                yt_title = title.split('] ')[-1].split('.mp4')[0].strip()
                yt_description = post_content
                
                # ค้นหาภาพหน้าปกที่มีชื่อเดียวกับชื่อการ์ด/วิดีโอ (แต่เป็น .png/.jpg/.jpeg)
                video_filename = extract_filename_from_title(title)
                if video_filename:
                    base_name = os.path.splitext(video_filename)[0].strip()
                    thumb_dirs = [
                        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "thumbnails"),
                        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Podcast_Project", "workspace", "1_raw_materials", "thumbnails"),
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
            
            success = upload_video_to_youtube(
                youtube_client,
                video_path=video_path,
                title=yt_title,
                description=yt_description,
                tags=tags,
                privacy_status=args.yt_privacy,
                dry_run=args.dry_run,
                thumbnail_path=thumbnail_path
            )
            success_flags["YouTube"] = success
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดกับ YouTube API: {e}")
            success_flags["YouTube"] = False
            
    # ------------------ 3. TikTok ------------------
    if "TikTok" in platforms or "Reels" in platforms:
        print("\n⚫ [TikTok Publishing]")
        try:
            tiktok_token = get_tiktok_client() if not args.dry_run else None
            
            # เตรียมแคปชันสำหรับ TikTok
            option_1_content = post_content
            for split_term in ["ทางเลือกที่ 2:", "ทางเลือก 2:", "option 2:", "Option 2:"]:
                if split_term in post_content:
                    option_1_content = post_content.split(split_term)[0].strip()
                    break
                    
            content_lines = [line.strip() for line in option_1_content.split("\n") if line.strip()]
            clean_lines = []
            for line in content_lines:
                line_lower = line.lower()
                if any(h in line_lower for h in ["ทางเลือกที่", "ทางเลือก", "option", "queue:"]):
                    continue
                if line.startswith("ดูคลิปเต็มที่"):
                    continue
                clean_lines.append(line)
                
            tiktok_caption = " ".join(clean_lines).strip()
            cta_text = " 📲 จิ้มลิงก์หน้าโปรไฟล์เพื่อดูคลิปเต็มได้เลย!"
            if len(tiktok_caption) + len(cta_text) > 150:
                tiktok_caption = tiktok_caption[:150 - len(cta_text) - 3] + "..."
            tiktok_caption = tiktok_caption + cta_text
                
            privacy_map = {
                "public": "PUBLIC_TO_EVERYONE",
                "self": "SELF_ONLY",
                "friends": "MUTUAL_FOLLOW_FRIENDS"
            }
            api_privacy = privacy_map.get(args.tt_privacy, "SELF_ONLY")
            
            success = upload_video_to_tiktok(
                tiktok_token,
                video_path=video_path,
                title=tiktok_caption,
                privacy_status=api_privacy,
                dry_run=args.dry_run
            )
            success_flags["TikTok"] = success
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดกับ TikTok API: {e}")
            success_flags["TikTok"] = False
            
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

    # ส่งแจ้งเตือน Discord เมื่อสำเร็จจริง (และไม่ใช่ dry-run)
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
