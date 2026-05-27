import os
import sys

# Find project root
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Add Team_Agent_Content/skills to path
skills_dir = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills")
if skills_dir not in sys.path:
    sys.path.append(skills_dir)

try:
    from youtube_publisher import get_youtube_client
    print("🔄 กำลังตรวจสอบการเชื่อมต่อ YouTube API...")
    youtube = get_youtube_client()
    print("✅ โหลด YouTube API client สำเร็จ!")
    
    # ดึงข้อมูลช่องผู้ใช้เพื่อทดสอบ API
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        mine=True
    )
    response = request.execute()
    
    if "items" in response and len(response["items"]) > 0:
        channel = response["items"][0]
        title = channel["snippet"]["title"]
        channel_id = channel["id"]
        subscribers = channel["statistics"].get("subscriberCount", "0")
        print(f"🎉 ตรวจพบช่อง YouTube: {title} (ID: {channel_id})")
        print(f"📊 ผู้ติดตาม: {subscribers} คน")
    else:
        print("⚠️ ไม่พบข้อมูลช่อง (กรุณาเช็คสิทธิ์หรือบัญชี)")
        
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
