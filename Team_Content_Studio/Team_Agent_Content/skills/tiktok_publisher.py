#!/usr/bin/env python3
import os
import sys
import argparse
import re
import ssl
import json
import urllib.request
import hashlib
import secrets
import urllib.parse
import urllib.error
import time
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
from discord_helper import DiscordHelper


TOKEN_FILENAME = os.path.join("credentials", "token_tiktok.json")
DEFAULT_REDIRECT_PORT = 5000

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

# OAuth Callback Server Handler
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard logging outputs in terminal
        return

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("<h3>ล็อกอิน TikTok สำเร็จแล้วแก! สามารถปิดหน้าต่างนี้และกลับไปดูที่หน้าต่าง Terminal ได้เลยจ้า</h3>".encode('utf-8'))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Failed to get auth code.".encode('utf-8'))

def get_tiktok_client():
    """Authenticate and return access token."""
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
    redirect_uri = os.environ.get("TIKTOK_REDIRECT_URI", f"http://localhost:{DEFAULT_REDIRECT_PORT}/callback")
    
    if not client_key or not client_secret:
        print("❌ Error: ไม่พบ TIKTOK_CLIENT_KEY หรือ TIKTOK_CLIENT_SECRET ในไฟล์ .env ของแก")
        print("กรุณาสร้างแอปพลิเคชันที่ TikTok Developer Portal และเพิ่มข้อมูลใน .env ก่อนลุยต่อแก!")
        sys.exit(1)
        
    token_path = os.path.join(PROJECT_ROOT, TOKEN_FILENAME)
    
    token_data = None
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
        except Exception:
            token_data = None
            
    now = time.time()
    
    # 1. เช็คว่ามี Token และยังมีอายุอยู่หรือไม่
    if token_data and token_data.get("access_token") and token_data.get("expires_at", 0) > now:
        return token_data["access_token"]
        
    # 2. ถ้า Token หมดอายุแต่มี Refresh Token ให้ทำการต่ออายุ
    if token_data and token_data.get("refresh_token") and token_data.get("refresh_expires_at", 0) > now:
        print("🔄 กำลังรีเฟรช TikTok Access Token ด้วย Refresh Token...")
        url = "https://open.tiktokapis.com/v2/oauth/token/"
        data = urllib.parse.urlencode({
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": token_data["refresh_token"]
        }).encode("utf-8")
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, context=ctx) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                
                # เก็บค่าใหม่
                res_json["expires_at"] = time.time() + res_json.get("expires_in", 86400) - 60
                res_json["refresh_expires_at"] = time.time() + res_json.get("refresh_expires_in", 31536000) - 60
                with open(token_path, "w", encoding="utf-8") as f:
                    json.dump(res_json, f, ensure_ascii=False, indent=2)
                    
                print("✅ รีเฟรช TikTok Token สำเร็จแล้วจ้า!")
                return res_json["access_token"]
        except Exception as e:
            print(f"⚠️ รีเฟรช Token ล้มเหลว: {e} กำลังจะเข้าสู่การล็อกอินใหม่...")
            
    # 3. ถ้าไม่มี Token หรือใช้ไม่ได้ ให้เริ่ม OAuth Flow ผ่านเบราว์เซอร์
    print("🔑 เริ่มต้นขั้นตอนการยืนยันตัวตนสำหรับ TikTok API...")
    
    # ดึง Host และ Port จาก URI
    port = DEFAULT_REDIRECT_PORT
    host = '127.0.0.1'
    
    # หาก redirect_uri เป็นเครื่องตัวเอง ให้ดึง host/port จริงมาใช้
    if 'localhost' in redirect_uri or '127.0.0.1' in redirect_uri:
        port_match = re.search(r':(\d+)', redirect_uri)
        if port_match:
            port = int(port_match.group(1))
        host_match = re.search(r'//([^:/]+)', redirect_uri)
        if host_match:
            host = host_match.group(1)
        
    # รัน Callback Server
    server = HTTPServer((host, port), OAuthCallbackHandler)
    server.auth_code = None
    
    def run_server():
        while server.auth_code is None:
            server.handle_request()
            
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    code_verifier = secrets.token_urlsafe(64)[:64]
    sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = sha256_hash.hex()

    state = str(int(time.time()))
    scope = "user.info.basic,video.publish"
    
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={client_key}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    
    print(f"🔗 ลิงก์ล็อกอิน: {auth_url}")
    print("🌐 กำลังเปิดเบราว์เซอร์เพื่อทำการล็อกอิน...")
    webbrowser.open(auth_url)
    
    # รอจนกว่าจะได้รับ Code
    while server.auth_code is None:
        time.sleep(0.5)
        
    auth_code = server.auth_code
    print("✅ ได้รับ Authorization Code เรียบร้อยแล้ว กำลังขอรับ Access Token...")
    
    # แลกเปลี่ยนโค้ดเป็น Token
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    token_data_payload = urllib.parse.urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }).encode("utf-8")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    req = urllib.request.Request(token_url, data=token_data_payload, headers=headers, method="POST")
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            
            if "access_token" not in res_json:
                print(f"❌ Error ในการรับ Token: {res_json}")
                sys.exit(1)
                
            res_json["expires_at"] = time.time() + res_json.get("expires_in", 86400) - 60
            res_json["refresh_expires_at"] = time.time() + res_json.get("refresh_expires_in", 31536000) - 60
            
            with open(token_path, "w", encoding="utf-8") as f:
                json.dump(res_json, f, ensure_ascii=False, indent=2)
                
            print(f"💾 บันทึก Token สำเร็จที่: {TOKEN_FILENAME}")
            return res_json["access_token"]
    except Exception as e:
        print(f"❌ ล้มเหลวในการขอรับ Token: {e}")
        sys.exit(1)

def find_video_file(filename):
    """ค้นหาพาธเต็มของไฟล์วิดีโอในคลังไฟล์เครื่อง"""
    if not filename:
        return None
        
    filename = filename.strip()
    
    search_dirs = [
        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos", "raw_vdo_short", "processed"),
        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos", "raw_vdo_3-5min", "processed"),
        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos", "raw_vdo_short"),
        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos", "raw_vdo_3-5min"),
        os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos"),
    ]
    
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
        
    if os.path.exists(filename):
        return os.path.abspath(filename)
        
    for d in search_dirs:
        full_path = os.path.join(d, filename)
        if os.path.exists(full_path):
            return os.path.abspath(full_path)
            
    base_search = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "raw_videos")
    if os.path.exists(base_search):
        for root, _, files in os.walk(base_search):
            if filename in files:
                return os.path.abspath(os.path.join(root, filename))
                
    return None

def extract_filename_from_title(title):
    """สกัดหาชื่อไฟล์วิดีโอ MP4 จากชื่อหัวข้อการ์ด Notion"""
    match = re.search(r'\]\s*(.*\.mp4)', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if title.strip().lower().endswith('.mp4'):
        return title.strip()
    return None

def upload_video_to_tiktok(access_token, video_path, title, privacy_status="SELF_ONLY", dry_run=False):
    """อัปโหลดวิดีโอขึ้น TikTok โดยใช้ Content Posting API v2"""
    if not os.path.exists(video_path):
        print(f"❌ Error: ไม่พบไฟล์วิดีโอที่: {video_path}")
        return False
        
    video_size = os.path.getsize(video_path)
    
    # ลบแฮชแท็กส่วนเกินออกจาก title เพื่อสกัดเอาเฉพาะข้อความเนื้อหา (เพราะใน TikTok แคปชันใส่แฮชแท็กทีหลังได้)
    # แต่จริงๆ TikTok Content Posting API ส่งแฮชแท็กเข้าไปเป็นส่วนหนึ่งของ Title (Caption) ได้
    # ความยาวห้ามเกิน 150 ตัวอักษร
    if len(title) > 150:
        title = title[:147] + "..."
        
    print(f"\n==================================================")
    print(f"🎬 ข้อมูลที่จะอัปโหลด TikTok:")
    print(f"📁 ไฟล์วิดีโอ: {video_path} (ขนาด {video_size} bytes)")
    print(f"🏷️ แคปชันโพสต์: {title}")
    print(f"🔒 ความเป็นส่วนตัว: {privacy_status}")
    print(f"==================================================\n")
    
    if dry_run:
        print("💡 [DRY-RUN MODE] ตรวจผ่านฉลุย สคริปต์จะไม่ส่งไฟล์ขึ้นเซิร์ฟเวอร์จริง")
        return True
        
    # คำนวณขนาด Chunk และจำนวน Chunk
    # หากขนาดไฟล์ไม่เกิน 60 MB ให้ส่งแบบชิ้นเดียว (single chunk)
    if video_size <= 60 * 1024 * 1024:
        chunk_size = video_size
        total_chunk_count = 1
    else:
        # หากเกินให้แบ่งเป็น Chunk ขนาด 20 MB
        chunk_size = 20 * 1024 * 1024
        total_chunk_count = video_size // chunk_size

    # ขั้นตอนที่ 1: Initialize Upload
    init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    init_payload = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_status,
            "disable_duet": False,
            "disable_stitch": False,
            "disable_comment": False
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunk_count
        }
    }
    
    req_init = urllib.request.Request(
        init_url, 
        data=json.dumps(init_payload).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        print("🚀 กำลังส่งคำร้องเริ่มอัปโหลด (Upload Initialization) ไปที่ TikTok...")
        with urllib.request.urlopen(req_init, context=ctx) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            error_info = res_data.get("error", {})
            if error_info.get("code") != "ok":
                print(f"❌ TikTok API Error: {error_info.get('message')}")
                return False
                
            upload_url = res_data.get("data", {}).get("upload_url")
            publish_id = res_data.get("data", {}).get("publish_id")
            
            if not upload_url:
                print("❌ ล้มเหลว: ไม่ได้ upload_url จาก TikTok")
                return False
                
        # ขั้นตอนที่ 2: Upload Binary Data (แบ่งชิ้นอัปโหลดทีละ Chunk)
        print("📊 ได้รับ Upload URL แล้ว กำลังเริ่มอัปโหลดไฟล์วิดีโอ...")
        
        with open(video_path, "rb") as video_file:
            for chunk_idx in range(total_chunk_count):
                start_byte = chunk_idx * chunk_size
                
                # ถ้าเป็น chunk สุดท้าย ให้อ่านจนสุดไฟล์
                if chunk_idx == total_chunk_count - 1:
                    chunk_data = video_file.read()
                    end_byte = video_size - 1
                else:
                    chunk_data = video_file.read(chunk_size)
                    end_byte = start_byte + len(chunk_data) - 1
                    
                chunk_len = len(chunk_data)
                print(f"📤 กำลังอัปโหลด Chunk {chunk_idx + 1}/{total_chunk_count} (bytes {start_byte}-{end_byte}/{video_size})...")
                
                put_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(chunk_len),
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{video_size}"
                }
                
                req_upload = urllib.request.Request(
                    upload_url,
                    data=chunk_data,
                    headers=put_headers,
                    method="PUT"
                )
                
                with urllib.request.urlopen(req_upload, context=ctx) as put_response:
                    put_response.read()
                    
            print(f"✅ อัปโหลดวิดีโอขึ้น TikTok สำเร็จเสร็จสิ้น! (Publish ID: {publish_id})")
            return True
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8", errors="ignore")
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(f"Details: {error_msg}")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิดในการอัปโหลด TikTok: {e}")
        return False

def publish_from_notion(access_token, dry_run=False, default_privacy="SELF_ONLY"):
    """ดึงข้อมูลโพสต์ที่ได้รับการอนุมัติ (Status = '5_Approved') จาก Notion และยิงลง TikTok"""
    print(f"🔍 [Notion Publisher] สแกนหาการ์ดที่ผ่านการอนุมัติ (Status = '5_Approved') ใน Notion...")
    
    notion = NotionHelper()
    pages = notion.fetch_pages_by_status("5_Approved")
    
    if not pages:
        print("📭 ไม่พบโพสต์ใดที่อยู่ในสถานะ '5_Approved' ใน Notion เลยแก!")
        return
        
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    # รองรับการแชร์ลง Reels หรือมีคิว TikTok โดยตรง
    target_platforms = ["Reels", "TikTok"]
    
    posted_count = 0
    for page in pages:
        page_id_notion = page["id"]
        title = page["title"]
        platforms = page["platforms"]
        publish_date_str = page["publish_date"]
        approved_copy = page["approved_copy"]
        
        # 1. เช็คว่าเป็นคิวเป้าหมายหรือไม่
        matched = False
        for p in platforms:
            if p in target_platforms:
                matched = True
                break
                
        if not matched:
            continue
            
        print(f"\n📢 พบโพสต์อนุมัติหัวข้อ: '{title}' (Platforms: {platforms})")
        
        # 2. ตรวจสอบชื่อไฟล์วิดีโอจากชื่อหน้าเพจ
        video_filename = extract_filename_from_title(title)
        if not video_filename:
            print(f"⚠️ ข้าม: ไม่สามารถระบุชื่อไฟล์วิดีโอ MP4 จากชื่อหน้าเพจ '{title}' ได้แก!")
            continue
            
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
            
        # 4. ดึงเนื้อหาข้อความที่จะใส่ใน Caption
        post_content = approved_copy
        if not post_content or post_content.strip() == "":
            print(f"⚠️ Approved Copy ว่างเปล่า กำลังเข้าไปดึงข้อมูลจากเนื้อหาในหน้าเพจแทน...")
            raw_body = notion.get_page_content_text(page_id_notion)
            if "## 📝 Draft Options" in raw_body:
                raw_body = raw_body.split("## 📝 Draft Options")[0].strip()
            if "---" in raw_body:
                raw_body = raw_body.split("---")[0].strip()
            post_content = raw_body.strip()
            
        # ดึงเฉพาะข้อความของทางเลือกที่ 1 (Option 1) มาใช้
        option_1_content = post_content
        for split_term in ["ทางเลือกที่ 2:", "ทางเลือก 2:", "option 2:", "Option 2:"]:
            if split_term in post_content:
                option_1_content = post_content.split(split_term)[0].strip()
                break
            
        # 5. ฟอร์แมตแคปชัน TikTok
        content_lines = [line.strip() for line in option_1_content.split("\n") if line.strip()]
        
        clean_lines = []
        for line in content_lines:
            line_lower = line.lower()
            if any(h in line_lower for h in ["ทางเลือกที่", "ทางเลือก", "option", "queue:"]):
                continue
            if line.startswith("ดูคลิปเต็มที่"):
                continue
            clean_lines.append(line)
            
        # สร้าง Caption สั้นๆ สำหรับ TikTok
        tiktok_caption = " ".join(clean_lines).strip()
        cta_text = " 📲 จิ้มลิงก์หน้าโปรไฟล์เพื่อดูคลิปเต็มได้เลย!"
        if len(tiktok_caption) + len(cta_text) > 150:
            tiktok_caption = tiktok_caption[:150 - len(cta_text) - 3] + "..."
        tiktok_caption = tiktok_caption + cta_text
            
        success = upload_video_to_tiktok(
            access_token, 
            video_path=video_path, 
            title=tiktok_caption, 
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
            
            # ส่งแจ้งเตือน Discord เมื่อสำเร็จจริงเท่านั้น
            discord = DiscordHelper()
            discord.send_success(
                "อัปโหลดวิดีโอลง TikTok สำเร็จแล้วแก!",
                f"**หัวข้อ Notion:** {title}\n**ไฟล์วิดีโอ:** {video_filename}\n**คำบรรยาย:** {tiktok_caption}\n🔒 **ความเป็นส่วนตัว:** {default_privacy}"
            )
            posted_count += 1
        else:
            print(f"❌ อัปโหลดการ์ด '{title}' ขึ้น TikTok ล้มเหลว!")
            
    print(f"\n🎉 อัปโหลดสำเร็จทั้งหมด {posted_count} คลิปสั้นลง TikTok จ้า!")

def main():
    parser = argparse.ArgumentParser(description="Veda Auto-Publisher for TikTok")
    parser.add_argument("-v", "--video", help="พาธไฟล์วิดีโอ MP4 ในเครื่อง")
    parser.add_argument("-t", "--title", help="แคปชัน/ชื่อคลิปสำหรับโพสต์ TikTok (จำกัด 150 ตัวอักษร)")
    parser.add_argument("-p", "--privacy", default="public", choices=["public", "self", "friends"], help="ระดับความเป็นส่วนตัว: public (ทุกคน), self (ส่วนตัว), friends (เพื่อนรัก)")
    parser.add_argument("--from-notes", action="store_true", help="ดึงข้อมูลโพสต์ที่อนุมัติแล้วจาก Notion มาอัปโหลดอัตโนมัติ")
    parser.add_argument("--dry-run", action="store_true", help="จำลองการทำงานของระบบโดยไม่อัปโหลดจริง")
    
    args = parser.parse_args()
    
    # แปรรูปค่า Privacy ของ CLI ให้ตรงกับ API
    privacy_map = {
        "public": "PUBLIC_TO_EVERYONE",
        "self": "SELF_ONLY",
        "friends": "MUTUAL_FOLLOWERS_ONLY"
    }
    api_privacy = privacy_map.get(args.privacy, "SELF_ONLY")
    
    if args.dry_run:
        access_token = "dummy_token_for_dry_run"
    else:
        access_token = get_tiktok_client()
    
    if args.from_notes:
        publish_from_notion(access_token, dry_run=args.dry_run, default_privacy=api_privacy)
    else:
        if not args.video or not args.title:
            print("❌ Error: กรุณาระบุไฟล์วิดีโอ (--video) และแคปชัน (--title) หรือระบุ --from-notes")
            sys.exit(1)
            
        video_path = find_video_file(args.video)
        if not video_path:
            print(f"❌ Error: ไม่พบไฟล์วิดีโอ: {args.video}")
            sys.exit(1)
            
        upload_video_to_tiktok(
            access_token,
            video_path=video_path,
            title=args.title,
            privacy_status=api_privacy,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()
