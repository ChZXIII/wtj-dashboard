#!/usr/bin/env python3
import os
import sys

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

skills_dir = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills")
if skills_dir not in sys.path:
    sys.path.append(skills_dir)

from youtube_publisher import get_youtube_client

def test_youtube():
    print("🔄 กำลังดึง YouTube client...")
    try:
        youtube = get_youtube_client()
        print("🔗 ได้รับ client สำเร็จ กำลังส่งคำร้องขอทดสอบ (List Channels)...")
        # Call channels list to verify if API is enabled
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()
        print("✅ สำเร็จ! ตัวเชื่อมต่อ YouTube Data API ทำงานได้เป็นปกติแล้วแก!")
        if "items" in response:
            for item in response["items"]:
                print(f"📺 ชื่อช่อง: {item['snippet']['title']}")
                print(f"🆔 Channel ID: {item['id']}")
        else:
            print("📭 ไม่พบช่อง YouTube ของผู้ใช้ที่เข้าสู่ระบบ")
    except Exception as e:
        print(f"❌ ล้มเหลว! เกิดข้อผิดพลาด:")
        print(e)

if __name__ == "__main__":
    test_youtube()
