#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime

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
import config

def sync():
    print("==================================================")
    print("🤖 บอท: เริ่มระบบดึงข้อมูลจาก Notion ไปอัปเดต Dashboard...")
    print("==================================================")
    
    notion = NotionHelper()
    
    # 1. ดึงหน้าทั้งหมดใน Database
    # Query database without filtering to get all pages
    res = notion.query_database()
    if not res or "results" not in res:
        print("❌ ล้มเหลว: ไม่สามารถดึงข้อมูลจาก Notion ได้")
        return
        
    pages = res["results"]
    print(f"📊 ตรวจพบรายการทั้งหมดใน Notion: {len(pages)} หน้า")
    
    calendar_data = {}
    
    for page in pages:
        page_id = page["id"]
        properties = page["properties"]
        
        # Extract title
        title = "Untitled"
        title_prop_name = notion.get_title_property_name()
        name_prop = properties.get(title_prop_name, {})
        if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
            title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
            
        # Extract Status name
        status_name = "1_Ideation"
        status_prop = properties.get("Status", {})
        if status_prop.get("type") == "select" and status_prop.get("select"):
            status_name = status_prop["select"]["name"]
            
        # Extract Publish Date
        publish_date_str = None
        date_prop = properties.get("Publish Date", {})
        if date_prop.get("type") == "date" and date_prop.get("date"):
            publish_date_str = date_prop["date"].get("start")
            
        if not publish_date_str:
            # Skip if no publish date
            continue
            
        # Parse publish date to dateKey (YYYY-MM-DD) and timeKey (HH:MM)
        # Notion format can be: "2026-06-05" or "2026-06-05T19:30:00.000+07:00"
        date_key = ""
        time_key = "19:30" # Default slot time
        
        if "T" in publish_date_str:
            # "2026-06-05T19:30:00.000+07:00" -> split T
            date_part, time_part = publish_date_str.split("T")
            date_key = date_part
            # extract HH:MM
            time_key = time_part[:5]
        else:
            date_key = publish_date_str
            
        # Define slot key matching dashboard: "YYYY-MM-DD-HH:MM"
        slot_key = f"{date_key}-{time_key}"
        
        # Map Status to ready/missing
        # ready if Approved (5_Approved) or Published (6_Published)
        is_ready = status_name in ["5_Approved", "6_Published"]
        
        calendar_data[slot_key] = {
            "title": title,
            "status": "ready" if is_ready else "missing",
            "notion_status": status_name
        }
        
    # 2. เขียนไฟล์ JS ดาต้าสำหรับ Dashboard ทั้งสองโฟลเดอร์
    js_content = f"// Generated automatically by WTJ Sync Agent\nconst NOTION_CALENDAR_DATA = {json.dumps(calendar_data, indent=4, ensure_ascii=False)};\n"
    
    paths_to_save = [
        os.path.join(config.LOCAL_DASHBOARD_DIR, "notion_calendar_data.js"),
        os.path.join(config.GITHUB_DASHBOARD_DIR, "notion_calendar_data.js")
    ]
    
    for path in paths_to_save:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"✅ บันทึกไฟล์ข้อมูลแดชบอร์ดลง {path} สำเร็จ!")
        
    print(f"📊 ซิงก์ข้อมูลไปทั้งหมด {len(calendar_data)} สล็อตเรียบร้อยแก!\n")

if __name__ == "__main__":
    sync()
