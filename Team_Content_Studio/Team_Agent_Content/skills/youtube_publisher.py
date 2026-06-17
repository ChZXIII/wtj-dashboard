#!/usr/bin/env python3
import os
import sys
import argparse
import re
import ssl
import json
from datetime import datetime, timezone, timedelta

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

# Google API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import googleapiclient.errors

SCOPES = ['https://www.googleapis.com/auth/youtube']
TOKEN_FILENAME = os.path.join("credentials", "token_youtube.json")
CLIENT_SECRET_FILENAME = os.path.join("credentials", "client_secret.json")

def load_env():
    """Load environment variables from .env file."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

def get_youtube_client():
    """Authenticate and return the YouTube API client."""
    token_path = os.path.join(PROJECT_ROOT, TOKEN_FILENAME)
    client_secret_path = os.path.join(PROJECT_ROOT, CLIENT_SECRET_FILENAME)
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 กำลังรีเฟรช Google OAuth Token สำหรับ YouTube...")
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ รีเฟรช Token ล้มเหลว: {e} กำลังเริ่มล็อกอินใหม่...")
                creds = None
                
        if not creds:
            if not os.path.exists(client_secret_path):
                print(f"❌ Error: ไม่พบไฟล์ {CLIENT_SECRET_FILENAME} ในโปรเจกต์รูท")
                sys.exit(1)
            print("🔑 กำลังเปิดหน้าต่างเบราว์เซอร์เพื่อขอสิทธิ์เข้าถึง YouTube (OAuth)...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
            
            # บันทึก token เก็บไว้
            with open(token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())
            print(f"💾 บันทึก Token เรียบร้อยที่: {TOKEN_FILENAME}")
            
    # สร้าง Client
    return build('youtube', 'v3', credentials=creds)

def find_video_file(filename):
    """ค้นหาพาธเต็มของไฟล์วิดีโอในคลังไฟล์เครื่อง"""
    if not filename:
        return None
        
    # ล้างอักขระพิเศษหรือช่องว่างส่วนเกิน
    filename = filename.strip()
    
    # 1. เช็คถ้าเป็น Absolute path อยู่แล้ว
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
        
    # 2. เช็คถ้าอยู่ใน Directory ปัจจุบัน
    if os.path.exists(filename):
        return os.path.abspath(filename)
        
    # 3. ค้นหาแบบกว้าง (Recursive) ใต้โฟลเดอร์ทีมคอนเทนต์
    base_search = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content")
    if os.path.exists(base_search):
        for root, _, files in os.walk(base_search):
            if filename in files:
                return os.path.abspath(os.path.join(root, filename))
                
    return None

def extract_filename_from_title(title):
    """สกัดหาชื่อไฟล์วิดีโอ (MP4/MOV/etc) จากชื่อหัวข้อการ์ด Notion"""
    # เช่น: "[Reels_Under1Min Video Draft] 01   กอฟ อินพลู   30 sec_.mp4" -> "01   กอฟ อินพลู   30 sec_.mp4"
    # สนับสนุนนามสกุล .mp4, .mov, .mkv, .avi, .webm
    match = re.search(r'\]\s*(.*\.(?:mp4|mov|mkv|avi|webm))', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # ถ้าชื่อหน้าลงท้ายด้วยนามสกุลวิดีโอที่กำหนดอยู่แล้ว
    title_clean = title.strip().lower()
    if any(title_clean.endswith(ext) for ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm']):
        return title.strip()
        
    return None

def get_or_create_playlist(youtube, playlist_name):
    """ค้นหา playlist ID จากชื่อ ถ้าไม่มีให้สร้างใหม่ (หรือรีเทิร์น None)"""
    try:
        # ค้นหา playlist ที่มีอยู่แล้ว
        request = youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        response = request.execute()
        
        for item in response.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            if title.strip().lower() == playlist_name.strip().lower():
                return item.get("id")
                
        # ถ้าไม่มี ให้สร้างใหม่
        print(f"➕ ไม่พบ Playlist '{playlist_name}' ในช่อง ยูทูบ กำลังสร้างใหม่ให้แก...")
        request_create = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": f"รายการ {playlist_name} อัตโนมัติ - สร้างโดยบอท WTJ",
                    "defaultLanguage": "th"
                },
                "status": {
                    "privacyStatus": "public"
                }
            }
        )
        response_create = request_create.execute()
        playlist_id = response_create.get("id")
        print(f"✅ สร้าง Playlist '{playlist_name}' (ID: {playlist_id}) เรียบร้อยแล้วแก!")
        return playlist_id
    except Exception as e:
        print(f"⚠️ Playlist Lookup/Creation Warning: {e}")
        return None

def add_video_to_playlist(youtube, video_id, playlist_id):
    """เพิ่มวิดีโอเข้า playlist"""
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        request.execute()
        print(f"✅ เพิ่มวิดีโอ {video_id} เข้า Playlist เรียบร้อยแล้วแก!")
        return True
    except Exception as e:
        print(f"⚠️ ไม่สามารถเพิ่มวิดีโอเข้า playlist ได้: {e}")
        return False

def upload_video_to_youtube(youtube, video_path, title, description="", tags=None, privacy_status="draft", dry_run=False, thumbnail_path=None, publish_at=None, paid_promotion=False, playlist_name=None, category_id=None):
    """อัปโหลดวิดีโอขึ้น YouTube แบบ Resumable Chunked Upload"""
    if not os.path.exists(video_path):
        print(f"❌ Error: ไม่พบไฟล์วิดีโอที่: {video_path}")
        return False
        
    # ลบส่วนที่เป็น Tags: ... หรือ แท็ก: ... ออกจาก description เพื่อไม่ให้ปรากฏใต้คลิป (ป้องกัน Tag Stuffing ตามกฎ YouTube)
    if description:
        desc_lines = []
        for line in description.splitlines():
            line_strip = line.strip()
            # ตรวจสอบบรรทัดที่เป็นแท็ก
            if re.match(r'^(?:\*\*|)?(?:Tags|แท็ก)(?:\*\*|)?\s*:', line_strip, re.IGNORECASE):
                continue
            desc_lines.append(line)
        description = "\n".join(desc_lines).strip()

    # กรองความยาวของ Title ห้ามเกิน 100 ตัวอักษรตามเกณฑ์ YouTube
    if len(title) > 100:
        print(f"⚠️ Warning: ชื่อคลิปยาวเกิน 100 ตัวอักษร (ยาว {len(title)} ตัวอักษร) กำลังตัดคำท้ายออก...")
        title = title[:97] + "..."
        
    # ทำความสะอาดและกรอง Tags ให้ปลอดภัยตามเกณฑ์ของ YouTube
    if tags:
        cleaned_tags = []
        for tag in tags:
            # ลบเครื่องหมายต้องห้ามและอักขระพิเศษแปลกปลอม
            t = re.sub(r'[<>*\[\]\{\}]', '', tag).strip()
            if t and len(t) > 1:
                cleaned_tags.append(t)
        cleaned_tags = list(set(cleaned_tags))
        
        # คุมความยาวรวมไม่ให้เกิน 400 ตัวอักษร (เกณฑ์ YouTube คือ 500)
        final_tags = []
        total_len = 0
        for t in cleaned_tags:
            if total_len + len(t) + 1 <= 400:
                final_tags.append(t)
                total_len += len(t) + 1
        tags = final_tags
    else:
        tags = []
        
    print(f"\n==================================================")
    print(f"🎬 ข้อมูลที่จะอัปโหลด YouTube:")
    print(f"📁 ไฟล์วิดีโอ: {video_path}")
    if thumbnail_path:
        print(f"🖼️ ภาพหน้าปก: {thumbnail_path}")
    print(f"🏷️ ชื่อคลิป (Title): {title}")
    print(f"🔒 สถานะความเป็นส่วนตัว: {privacy_status.upper()}")
    if publish_at:
        print(f"⏰ เวลาเผยแพร่ (Scheduled UTC): {publish_at}")
    if tags:
        print(f"🔑 แท็ก: {', '.join(tags)}")
    print(f"💰 สปอนเซอร์ (Paid Promotion): {'เปิด' if paid_promotion else 'ปิด'}")
    if playlist_name:
        print(f"📁 เพลย์ลิสต์ (Playlist): {playlist_name}")
    print(f"🗂️ หมวดหมู่ (Category ID): {category_id or '27'}")
    print(f"==================================================\n")
    
    if dry_run:
        print("💡 [DRY-RUN MODE] ตรวจผ่านฉลุย สคริปต์จะไม่ส่งไฟล์ขึ้นเซิร์ฟเวอร์จริง")
        return True
        
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id or '27',  # Education (หรือ '22' สำหรับ People & Blogs)
            'defaultLanguage': 'th',
            'defaultAudioLanguage': 'th'
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
            'license': 'youtube',
            'embeddable': True,
            'publicStatsViewable': True,
            'hasPaidProductPlacement': paid_promotion
        }
    }
    
    if publish_at:
        # YouTube API requires privacyStatus to be 'private' if publishAt is specified for scheduling
        body['status']['privacyStatus'] = 'private'
        body['status']['publishAt'] = publish_at
    
    # อัปโหลดแบบ Chunk ละ 2MB (ต้องเป็นผลคูณของ 256KB)
    media = MediaFileUpload(video_path, mimetype='video/*', chunksize=2*1024*1024, resumable=True)
    
    try:
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        print("🚀 เริ่มทำการอัปโหลดไฟล์วิดีโอขึ้น YouTube...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"📊 กำลังอัปโหลด... {progress}%")
                
        video_id = response.get("id")
        print(f"✅ อัปโหลดคลิปสำเร็จเสร็จสิ้น!")
        print(f"🔗 ลิงก์คลิป YouTube: https://youtu.be/{video_id}")
        
        # อัปโหลด Thumbnail รูปหน้าปกหากระบุพาธมา
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"🖼️ กำลังอัปโหลดภาพหน้าปก (Thumbnail): {thumbnail_path} ...")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print("   ✅ ตั้งค่าภาพหน้าปกสำเร็จ!")
            except Exception as e:
                print(f"   ⚠️ เกิดข้อผิดพลาดในการตั้งหน้าปกคลิป: {e}")
                
        # เพิ่มเข้า Playlist
        if playlist_name and youtube:
            playlist_id = get_or_create_playlist(youtube, playlist_name)
            if playlist_id:
                add_video_to_playlist(youtube, video_id, playlist_id)
                
        return True
        
    except googleapiclient.errors.HttpError as e:
        print(f"❌ YouTube API HttpError: {e.resp.status} - {e.content.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิดระหว่างอัปโหลด: {e}")
        return False

def publish_from_notion(youtube, queue_name=None, dry_run=False, default_privacy="draft"):
    """ดึงข้อมูลโพสต์ที่ได้รับการอนุมัติ (Status = '5_Approved') จาก Notion และยิงขึ้น YouTube Shorts"""
    print(f"🔍 [Notion Publisher] สแกนหาการ์ดที่ผ่านการอนุมัติ (Status = '5_Approved') ใน Notion...")
    
    notion = NotionHelper()
    pages = notion.fetch_pages_by_status("5_Approved")
    
    if not pages:
        print("📭 ไม่พบโพสต์ใดที่อยู่ในสถานะ '5_Approved' ใน Notion เลยแก!")
        return
        
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    # ดึงการ์ดที่มี Platform เป็น Reels เท่านั้น (สำหรับวิดีโอสั้น)
    target_platforms = ["Reels"]
    
    posted_count = 0
    for page in pages:
        page_id_notion = page["id"]
        title = page["title"]
        platforms = page["platforms"]
        publish_date_str = page["publish_date"]
        approved_copy = page["approved_copy"]
        
        # 1. เช็คว่าเป็นคิว Reels หรือไม่
        matched = False
        for p in platforms:
            if p in target_platforms:
                matched = True
                break
                
        if not matched:
            continue
            
        print(f"\n📢 พบโพสต์อนุมัติหัวข้อ: '{title}' (Platform: Reels)")
        
        # 2. ตรวจสอบชื่อไฟล์วิดีโอจากชื่อหน้าเพจ
        video_filename = extract_filename_from_title(title)
        if not video_filename:
            print(f"⚠️ ข้าม: ไม่สามารถระบุชื่อไฟล์วิดีโอ MP4 จากชื่อหน้าเพจ '{title}' ได้แก!")
            continue
            
        # ค้นหาพาธไฟล์วิดีโอในเครื่อง
        video_path = find_video_file(video_filename)
        if not video_path:
            print(f"❌ ข้าม: ไม่พบไฟล์วิดีโอ '{video_filename}' ในเครื่องเลยแก!")
            continue
            
        # 3. ตรวจเช็ควันเวลาเผยแพร่ (Publish Date)
        if not publish_date_str:
            print(f"⚠️ แจ้งเตือน: โพสต์ '{title}' อนุมัติแล้วแต่ไม่ได้ใส่วันเวลาโพสต์ ข้ามไปก่อนนะแก...")
            continue
            
        try:
            if "T" in publish_date_str:
                publish_dt = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
                if publish_dt.tzinfo is None:
                    publish_dt = publish_dt.replace(tzinfo=tz_th)
            else:
                dt = datetime.strptime(publish_date_str, "%Y-%m-%d")
                publish_dt = datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
                
            if now_local < publish_dt:
                time_diff = publish_dt - now_local
                print(f"⏳ ยังไม่ถึงเวลาโพสต์ (ตั้งไว้: {publish_date_str} - เหลือเวลาอีก {time_diff}) ข้ามไปก่อนแก...")
                continue
                
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการคำนวณเวลาโพสต์ '{publish_date_str}': {e}")
            continue
            
        # 4. ดึงเนื้อหาข้อความที่จะใส่ใน Description
        post_content = approved_copy
        if not post_content or post_content.strip() == "":
            print(f"⚠️ Approved Copy ว่างเปล่า กำลังเข้าไปดึงข้อมูลจากเนื้อหาในหน้าเพจแทน...")
            raw_body = notion.get_page_content_text(page_id_notion)
            if "## 📝 Draft Options" in raw_body:
                raw_body = raw_body.split("## 📝 Draft Options")[0].strip()
            if "---" in raw_body:
                raw_body = raw_body.split("---")[0].strip()
            post_content = raw_body.strip()
            
        # 5. วิเคราะห์แยกย่อยข้อมูล (สกัดแฮชแท็กมาเป็น tags ของ YouTube)
        # ปรับปรุง Title และคำบรรยายตาม Format Shorts
        # ดึงบรรทัดแรกสุดของคำบรรยายมาเป็น Title ส่วนที่เหลือเก็บเป็น Description
        content_lines = [line.strip() for line in post_content.split("\n") if line.strip()]
        
        # ค้นหาแฮชแท็กในเนื้อหาทั้งหมดเพื่อจัดหมวดหมู่ tags
        tags = []
        hashtags = re.findall(r'#([^\s#]+)', post_content)
        if hashtags:
            tags = list(set(hashtags))
            
        # ลบแฮชแท็กออกจากข้อความที่จะนำมาทำชื่อคลิป
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
                    
        # ดัดแปลง Title ให้อ่านง่าย
        yt_title = f"{title.split('] ')[-1].split('.mp4')[0]} | WTJ Shorts"
        if clean_lines:
            # ดึงประโยคเด็ดแรกมาทำหัวข้อ
            candidate = clean_lines[0].replace('"', '').replace('“', '').replace('”', '')
            if len(candidate) > 10 and len(candidate) < 70:
                yt_title = f"{candidate} #Shorts"
                
        yt_description = post_content + "\n\n📲 ติดตามเพจของเราได้ที่: https://www.facebook.com/WhatTheJobs"
        
        # 6. อัปโหลดขึ้น YouTube
        success = upload_video_to_youtube(
            youtube, 
            video_path=video_path, 
            title=yt_title, 
            description=yt_description, 
            tags=tags, 
            privacy_status=default_privacy, 
            dry_run=dry_run
        )
        
        if success:
            if dry_run:
                print(f"💡 [DRY-RUN] สำเร็จเสมือนจริง จะอัปเดตสถานะ Notion '{title}' เป็น '6_Published'")
                posted_count += 1
                continue
                
            # อัปเดตสถานะใน Notion เป็น 6_Published
            notion.update_page_status(page_id_notion, "6_Published")
            print(f"✅ อัปเดตสถานะการ์ดใน Notion เป็น '6_Published' เรียบร้อยแก!")
            posted_count += 1
        else:
            print(f"❌ อัปโหลดการ์ด '{title}' ขึ้น YouTube ล้มเหลว!")
            
    print(f"\n🎉 อัปโหลดสำเร็จทั้งหมด {posted_count} คลิปสั้นจ้า!")

def main():
    parser = argparse.ArgumentParser(description="Veda Auto-Publisher for YouTube Shorts")
    parser.add_argument("-v", "--video", help="พาธไฟล์วิดีโอ MP4 ในเครื่อง")
    parser.add_argument("-t", "--title", help="ชื่อคลิปวิดีโอ (Title) ของ YouTube Shorts")
    parser.add_argument("-d", "--desc", default="", help="คำอธิบายคลิปวิดีโอ (Description)")
    parser.add_argument("--tags", help="แท็กสำหรับวิดีโอ คั่นด้วยเครื่องหมายจุลภาค (,) เช่น tag1,tag2")
    parser.add_argument("-p", "--privacy", default="draft", choices=["public", "private", "unlisted", "draft"], help="ระดับความเป็นส่วนตัว (default: draft)")
    parser.add_argument("--from-notes", action="store_true", help="ดึงข้อมูลโพสต์ที่อนุมัติแล้วจาก Notion มาอัปโหลดอัตโนมัติ")
    parser.add_argument("--dry-run", action="store_true", help="จำลองการอัปโหลดโดยไม่โพสต์จริง")
    
    args = parser.parse_args()
    
    # เริ่มดึงข้อมูล Authentication
    youtube = get_youtube_client()
    
    if args.from_notes:
        publish_from_notion(youtube, dry_run=args.dry_run, default_privacy=args.privacy)
    else:
        if not args.video or not args.title:
            print("❌ Error: กรุณาระบุไฟล์วิดีโอ (--video) และชื่อคลิป (--title) หรือระบุ --from-notes")
            sys.exit(1)
            
        video_path = find_video_file(args.video)
        if not video_path:
            print(f"❌ Error: ไม่พบไฟล์วิดีโอ: {args.video}")
            sys.exit(1)
            
        tags_list = [tag.strip() for tag in args.tags.split(",")] if args.tags else []
        
        # เพิ่ม #Shorts ใน Tag และ Title เสมอถ้าเป็น Shorts
        if "Shorts" not in tags_list:
            tags_list.append("Shorts")
        if "#Shorts" not in args.title:
            args.title = f"{args.title} #Shorts"
            
        upload_video_to_youtube(
            youtube, 
            video_path=video_path, 
            title=args.title, 
            description=args.desc, 
            tags=tags_list, 
            privacy_status=args.privacy, 
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()
