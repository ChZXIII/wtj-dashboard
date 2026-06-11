#!/usr/bin/env python3
import os
import sys
import argparse
import urllib.request
import urllib.parse
import json
import ssl
import subprocess
import re
from datetime import datetime, timezone, timedelta

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
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
from discord_helper import DiscordHelper


def load_env(env_path=".env"):
    """โหลด Environment Variables จากไฟล์ .env แบบดั้งเดิม (ไม่ต้องลง library เพิ่ม)"""
    possible_paths = [
        env_path,
        os.path.join(os.path.dirname(os.path.dirname(__file__)), env_path),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), env_path),
        os.path.join(PROJECT_ROOT, env_path)
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        val_clean = val.strip().strip('"').strip("'")
                        os.environ[key.strip()] = val_clean

def clean_markdown_content(file_path):
    """อ่านไฟล์ Markdown และจัดระดับข้อความให้เหมาะสมสำหรับโพสต์ลง Facebook"""
    if not os.path.exists(file_path):
        print(f"❌ Error: ไม่พบไฟล์บทความที่ระบุ: {file_path}")
        sys.exit(1)
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        
    lines = content.split("\n")
    cleaned_lines = []
    
    for line in lines:
        if line.startswith("# "):
            cleaned_lines.append(line.replace("# ", "📢 ").upper() + "\n")
        elif line.startswith("## "):
            cleaned_lines.append(line.replace("## ", "✨ ") + "\n")
        elif line.startswith("- ") or line.startswith("* "):
            cleaned_lines.append("▪️ " + line[2:])
        else:
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)

def extract_and_remove_urls(message):
    """
    ค้นหา URL ในข้อความ, สกัดออกมาเก็บไว้พร้อมกับไอคอนนำหน้า (ถ้ามี), 
    และลบส่วนนั้นออกจากข้อความหลัก
    """
    url_pattern = r'(https?://[^\s]+)'
    urls = re.findall(url_pattern, message)
    
    if not urls:
        return message, []
        
    cleaned_message = message
    extracted_lines = []
    
    for url in urls:
        escaped_url = re.escape(url)
        line_pattern = r'(?m)^(.*?)(https?://[^\s]+)(.*?)$\n?'
        match = re.search(line_pattern, cleaned_message)
        if match:
            extracted_line = match.group(0).strip()
            extracted_lines.append(extracted_line)
            cleaned_message = re.sub(line_pattern, '', cleaned_message)
        else:
            extracted_lines.append(url)
            cleaned_message = cleaned_message.replace(url, "")
            
    cleaned_message = re.sub(r'\n{3,}', '\n\n', cleaned_message)
    return cleaned_message.strip(), extracted_lines

def post_facebook_comment(post_id, comment_text, access_token, dry_run=False):
    """ส่งคำสั่งเขียนคอมเมนต์ใต้โพสต์ Facebook"""
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    
    data = urllib.parse.urlencode({
        "message": comment_text,
        "access_token": access_token
    }).encode("utf-8")
    
    if dry_run:
        print("\n=== 🔍 [DRY-RUN COMMENT] ตรวจสอบคอมเมนต์ที่จะถูกแปะออโต้ ===")
        print(comment_text)
        print("==========================================================")
        return True

    req = urllib.request.Request(url, data=data, method="POST")
    
    try:
        print(f"💬 กำลังส่งลิงก์ไปแปะที่คอมเมนต์แรกของโพสต์ {post_id}...")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            comment_id = res_data.get("id")
            print(f"✅ สำเร็จ! แปะคอมเมนต์แรกให้เรียบร้อยแล้วจ้า! (Comment ID: {comment_id})")
            return True
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_msg)
            fb_error = error_json.get("error", {}).get("message", "Unknown Facebook Error")
            print(f"❌ Facebook Comment API Error: {fb_error}")
        except Exception:
            print(f"❌ HTTP Error {e.code} on Comment: {error_msg}")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดทางเทคนิคในการคอมเมนต์: {e}")
        return False

def publish_to_facebook(message, page_id, access_token, dry_run=False):
    """ส่งคำสั่งโพสต์ไปยัง Facebook Graph API พร้อมระบบคัดแยกลิงก์ไปคอมเมนต์แรกเพื่อหลีกเลี่ยงการกั้นสายตา"""
    cleaned_message, extracted_lines = extract_and_remove_urls(message)
    
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    
    data = urllib.parse.urlencode({
        "message": cleaned_message,
        "access_token": access_token
    }).encode("utf-8")
    
    if dry_run:
        print("\n=== 🔍 [DRY-RUN MODE] ตรวจสอบข้อความหลักที่จะทำการโพสต์ ===")
        print(cleaned_message)
        print("====================================================")
        if extracted_lines:
            print("\n=== 🔍 [DRY-RUN MODE] ตรวจสอบข้อความในคอมเมนต์แรก ===")
            print("\n".join(extracted_lines))
            print("====================================================")
        print("💡 สถานะ: โหมดทดสอบเสมือนจริง โค้ดทำงานผ่านฉลุย (ไม่มีการส่งขึ้นเพจจริง)")
        return "dry_run_success"

    req = urllib.request.Request(url, data=data, method="POST")
    
    try:
        print("🚀 กำลังติดต่อระบบ Veda Space Pipeline ➡️ Facebook Page...")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        post_id = None
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            post_id = res_data.get("id")
            print(f"✅ โพสต์หลักสำเร็จ! อัปโหลดข้อมูลขึ้นเพจเรียบร้อยแล้วจ้า!")
            print(f"🔗 Link โพสต์ของแก: https://facebook.com/{post_id}")
            
        if post_id and extracted_lines:
            comment_text = "\n".join(extracted_lines)
            post_facebook_comment(post_id, comment_text, access_token, dry_run=False)
            
        return post_id
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_msg)
            fb_error = error_json.get("error", {}).get("message", "Unknown Facebook Error")
            print(f"❌ Facebook API Error: {fb_error}")
        except Exception:
            print(f"❌ HTTP Error {e.code}: {error_msg}")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดทางเทคนิค: {e}")
        return False

def upload_video_to_facebook_reels(video_path, page_id, access_token, description, dry_run=False):
    """อัปโหลดวิดีโอขึ้น Facebook Reels โดยใช้ 3-step Reels Publishing API"""
    if not os.path.exists(video_path):
        print(f"❌ Error: ไม่พบไฟล์วิดีโอที่: {video_path}")
        return False

    video_size = os.path.getsize(video_path)
    print(f"\n==================================================")
    print(f"🎬 ข้อมูลที่จะอัปโหลด Facebook Reels:")
    print(f"📁 ไฟล์วิดีโอ: {video_path} (ขนาด {video_size} bytes)")
    print(f"📝 คำบรรยาย: {description}")
    print(f"==================================================\n")

    if dry_run:
        print("💡 [DRY-RUN MODE] ตรวจสอบสิทธิ์ผ่านฉลุย สคริปต์จะไม่ส่งไฟล์ขึ้น Facebook จริง")
        return "dry_run_reels_success"

    try:
        import requests
        
        # Step 1: Initialize Upload Session
        init_url = f"https://graph.facebook.com/v19.0/{page_id}/video_reels"
        params = {
            'upload_phase': 'start',
            'access_token': access_token
        }
        print("🚀 [Step 1/3] กำลังเริ่มต้น Session สำหรับ Reels...")
        response = requests.post(init_url, params=params)
        response.raise_for_status()
        init_data = response.json()
        
        video_id = init_data.get("video_id")
        upload_url = init_data.get("upload_url")
        
        if not video_id or not upload_url:
            print("❌ Error: ไม่ได้รับ video_id หรือ upload_url จาก Facebook")
            return False
            
        print(f"✅ สร้าง Session สำเร็จ (Video ID: {video_id})")

        # Step 2: Upload Video File
        print("🚀 [Step 2/3] กำลังอัปโหลดข้อมูลไฟล์วิดีโอ...")
        headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(video_size),
            'Content-Type': 'application/octet-stream'
        }
        
        with open(video_path, 'rb') as f:
            upload_response = requests.post(upload_url, data=f, headers=headers)
            upload_response.raise_for_status()
            
        print("✅ อัปโหลดไฟล์วิดีโอไปยังเซิร์ฟเวอร์ Facebook เรียบร้อย!")

        # Step 3: Publish the Reel
        print("🚀 [Step 3/3] กำลังส่งคำร้องให้เผยแพร่ Reels บนเพจ...")
        publish_params = {
            'upload_phase': 'finish',
            'video_id': video_id,
            'access_token': access_token,
            'video_state': 'PUBLISHED',
            'description': description
        }
        
        publish_response = requests.post(init_url, params=publish_params)
        publish_response.raise_for_status()
        publish_data = publish_response.json()
        
        if publish_data.get("success") or "video_id" in publish_data:
            print(f"🎉 เผยแพร่ Facebook Reels สำเร็จเสร็จสิ้น!")
            return video_id
        else:
            print(f"❌ เผยแพร่ล้มเหลว: {publish_data}")
            return False
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการโพสต์ Reels: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Response detail: {response.text}")
        if 'upload_response' in locals() and hasattr(upload_response, 'text'):
            print(f"Upload Response detail: {upload_response.text}")
        if 'publish_response' in locals() and hasattr(publish_response, 'text'):
            print(f"Publish Response detail: {publish_response.text}")
        return False

def upload_video_to_facebook_page(video_path, page_id, access_token, description, dry_run=False):
    """อัปโหลดวิดีโอขึ้น Facebook Page (คลิปวิดีโอยาว) โดยใช้ multipart/form-data request"""
    if not os.path.exists(video_path):
        print(f"❌ Error: ไม่พบไฟล์วิดีโอที่: {video_path}")
        return False

    video_size = os.path.getsize(video_path)
    print(f"\n==================================================")
    print(f"🎬 ข้อมูลที่จะอัปโหลด Facebook Video:")
    print(f"📁 ไฟล์วิดีโอ: {video_path} (ขนาด {video_size} bytes)")
    print(f"📝 คำบรรยาย: {description}")
    print(f"==================================================\n")

    if dry_run:
        print("💡 [DRY-RUN MODE] ตรวจสอบสิทธิ์ผ่านฉลุย สคริปต์จะไม่ส่งไฟล์ขึ้น Facebook จริง")
        return "dry_run_video_success"

    try:
        import requests
        
        # Meta Video uploads use graph-video.facebook.com instead of graph.facebook.com
        url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
        
        data = {
            'access_token': access_token,
            'description': description
        }
        
        print("🚀 กำลังอัปโหลดวิดีโอไปยังหน้าเพจ Facebook...")
        with open(video_path, 'rb') as video_file:
            files = {
                'source': video_file
            }
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            
        res_data = response.json()
        video_id = res_data.get("id")
        
        if video_id:
            print(f"🎉 อัปโหลดและโพสต์วิดีโอยาวสำเร็จเรียบร้อย! (ID: {video_id})")
            return video_id
        else:
            print(f"❌ อัปโหลดล้มเหลว: {res_data}")
            return False
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการอัปโหลดวิดีโอยาว: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Response detail: {response.text}")
        return False

def publish_from_notes(page_id, access_token, queue_name=None, dry_run=False):
    """ดึงโพสต์ที่ได้รับการอนุมัติ (Status = '5_Approved') จาก Notion และยิงโพสต์ขึ้น Facebook ตามคิวและเวลาที่กำหนด"""
    print(f"🔍 [Notion Publisher] เริ่มสแกนหาโพสต์ที่ได้รับการอนุมัติใน Notion...")
    
    notion = NotionHelper()
    pages = notion.fetch_pages_by_status("5_Approved")
    
    if not pages:
        print("📭 ไม่พบโพสต์ที่อยู่ในสถานะ '5_Approved' ใน Notion เลยแก!")
        return
        
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    # กำหนด Platform tags ตามคิวงานที่ระบุ
    platform_map = {
        "FB_Videos_3-5Min": "FB_Video",
        "Reels_Under1Min": "Reels",
        "Text_Posts": "FB_Text_Quote"
    }
    
    target_platforms = []
    if queue_name:
        if queue_name in platform_map:
            target_platforms = [platform_map[queue_name]]
        else:
            # Fallback
            target_platforms = [queue_name]
    else:
        target_platforms = list(platform_map.values())
        
    print(f"📋 คอนเทนต์เป้าหมายสำหรับรอบนี้ (ประเภทคิว: {target_platforms})")
    
    posted_count = 0
    for page in pages:
        page_id_notion = page["id"]
        title = page["title"]
        platforms = page["platforms"]
        publish_date_str = page["publish_date"]
        approved_copy = page["approved_copy"]
        
        # 1. เช็คว่าเป็นคิวที่เหมาะสมสำหรับรันรอบนี้หรือไม่
        matched_platform = None
        for p in platforms:
            if p in target_platforms:
                matched_platform = p
                break
                
        if not matched_platform:
            continue
            
        print(f"\n📢 พบโพสต์อนุมัติหัวข้อ: '{title}' (Platform: {matched_platform})")
        
        # 2. ตรวจเช็คเวลาเผยแพร่ (Publish Date)
        if not publish_date_str:
            print(f"⚠️ แจ้งเตือน: โพสต์ '{title}' เป็นสถานะอนุมัติ แต่ยังไม่ได้ตั้งวันเวลาโพสต์ (Publish Date) ข้ามไปก่อนนะแก...")
            continue
            
        try:
            if "T" in publish_date_str:
                publish_dt = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
                if publish_dt.tzinfo is None:
                    publish_dt = publish_dt.replace(tzinfo=tz_th)
            else:
                # date only
                dt = datetime.strptime(publish_date_str, "%Y-%m-%d")
                publish_dt = datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
                
            if now_local < publish_dt:
                time_diff = publish_dt - now_local
                print(f"⏳ ยังไม่ถึงเวลาเผยแพร่ (ตั้งไว้: {publish_date_str} - เหลือเวลาอีก {time_diff}) ข้ามไปก่อนแก...")
                continue
                
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการคำนวณวันเวลาโพสต์ '{publish_date_str}': {e}")
            continue
            
        # 3. เตรียมเนื้อหาที่จะโพสต์ (ดึงจาก Approved Copy, ถ้าว่างให้ดึงจาก Page Content และลบเศษ Draft Options ออก)
        post_content = approved_copy
        if not post_content or post_content.strip() == "":
            print(f"⚠️ Approved Copy ว่างเปล่า กำลังเข้าไปดึงข้อมูลจากเนื้อหาในหน้าเพจแทน...")
            raw_body = notion.get_page_content_text(page_id_notion)
            
            # ตัดพวก Draft Options ที่บอทแปะด้านล่างออก
            if "## 📝 Draft Options" in raw_body:
                raw_body = raw_body.split("## 📝 Draft Options")[0].strip()
            if "---" in raw_body:
                raw_body = raw_body.split("---")[0].strip()
                
            post_content = raw_body.strip()
            
        if not post_content or post_content.strip() == "":
            print(f"❌ ไม่พบเนื้อหาสำหรับโพสต์ของเรื่อง '{title}' กรุณากรอกรายละเอียดบทก่อน!")
            continue
            
        # 4. ทำการยิงโพสต์ขึ้น Facebook
        print(f"🚀 กำลังส่งโพสต์ขึ้นเพจจริง...")
        success = publish_to_facebook(post_content, page_id, access_token, dry_run=dry_run)
        
        if success:
            if dry_run:
                print(f"💡 [DRY-RUN] โพสต์สำเร็จเสมือนจริง จะเปลี่ยนสถานะหน้าเพจ '{title}' เป็น '6_Published'")
                posted_count += 1
                continue
                
            # อัปเดตสถานะใน Notion เป็น 6_Published
            notion.update_page_status(page_id_notion, "6_Published")
            print(f"✅ อัปเดตสถานะหน้าเพจ '{title}' ใน Notion เป็น '6_Published' เรียบร้อยแก!")
            
            # ส่งแจ้งเตือน Discord เมื่อสำเร็จจริงเท่านั้น
            discord = DiscordHelper()
            post_link = f"https://facebook.com/{success}"
            discord.send_success(
                "โพสต์ใหม่ขึ้นเพจ Facebook แล้วจ้า!",
                f"**หัวข้อ:** {title}\n**คิว:** {matched_platform}\n🔗 [ลิงก์โพสต์ของแก]({post_link})"
            )
            posted_count += 1
        else:
            print(f"❌ โพสต์ '{title}' ขึ้น Facebook ล้มเหลว!")
            
    print(f"\n🎉 เสร็จสิ้นภารกิจ! ดำเนินการสำเร็จทั้งหมด {posted_count} โพสต์จ้า!")

def main():
    parser = argparse.ArgumentParser(description="Veda Auto-Publisher for Facebook Page")
    parser.add_argument("-m", "--message", help="ข้อความสั้นที่ต้องการโพสต์สดๆ")
    parser.add_argument("-f", "--file", help="พาธไฟล์ Markdown (.md) ที่ต้องการดึงเนื้อหามาโพสต์")
    parser.add_argument("--from-notes", action="store_true", help="ดึงโพสต์อนุมัติจาก Notion มาโพสต์อัตโนมัติ")
    parser.add_argument("-q", "--queue", help="ชื่อโฟลเดอร์คิวงานที่ต้องการเจาะจง (เช่น FB_Videos_3-5Min, Reels_Under1Min, Text_Posts)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="รันโหมดทดสอบความถูกต้องโดยไม่โพสต์จริง")
    
    args = parser.parse_args()
    
    load_env()
    
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    access_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    if not args.dry_run:
        if not page_id or not access_token:
            print("❌ Error: ไม่พบ FACEBOOK_PAGE_ID หรือ FACEBOOK_PAGE_ACCESS_TOKEN ในระบบ")
            print("กรุณาตั้งค่าในไฟล์ .env ในโฟลเดอร์หลักของโปรเจกต์")
            sys.exit(1)
            
    message_content = ""
    if args.from_notes:
        publish_from_notes(page_id, access_token, queue_name=args.queue, dry_run=args.dry_run)
        return
    elif args.file:
        message_content = clean_markdown_content(args.file)
    elif args.message:
        message_content = args.message
    else:
        print("❌ Error: กรุณาระบุข้อความที่ต้องการโพสต์ หรือระบุ --from-notes")
        sys.exit(1)
        
    publish_to_facebook(message_content, page_id, access_token, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
