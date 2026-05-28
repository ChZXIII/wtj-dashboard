#!/usr/bin/env python3
"""
📅 Auto-Scheduler for Approved WTJ Notion Cards
สแกนหาการ์ดในสถานะ '5_Approved' ที่ยังไม่มีวันเวลาโพสต์ (Publish Date)
คำนวณและกรอกวันเวลาโพสต์ที่ใกล้ที่สุดล่วงหน้าตามตารางเวลาทอง (ของน้องครีม)
ป้องกันไม่ให้เวลาทับซ้อนกับการ์ดที่ตั้งเวลาไว้แล้ว
"""

import sys
import os
import json
import re
import csv
from datetime import datetime, timedelta, timezone

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'Team_Content_Studio', 'Team_Agent_Content', 'skills'))

from notion_helper import NotionHelper

# โหลดวันเผยแพร่วิดีโอต้นฉบับจาก CSV สำหรับจัดเรียง Rerun จากเก่าสุดไปใหม่สุด
video_dates = {}
csv_path = os.path.join(project_root, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "1_raw_materials", "analytics", "Table data.csv")
if os.path.exists(csv_path):
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                v_title = row.get("Video title")
                publish_time_str = row.get("Video publish time")
                if v_title and publish_time_str:
                    try:
                        dt = datetime.strptime(publish_time_str.strip('"'), "%b %d, %Y")
                        video_dates[v_title.strip().lower()] = dt
                    except Exception:
                        pass
    except Exception as e:
        print(f"⚠️ เตือน: โหลดไฟล์ CSV เพื่อจัดเรียง Rerun ล้มเหลว: {e}")

# Map JSON Weekday (0=Sunday, 1=Monday, ..., 6=Saturday) -> Python Weekday (0=Monday, ..., 6=Sunday)
def json_weekday_to_python(json_w):
    return (json_w - 1) % 7

# Map Python Weekday -> JSON Weekday
def python_weekday_to_json(py_w):
    return (py_w + 1) % 7

def load_schedule_rules():
    schedule_file = os.path.join(project_root, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "posting_schedule.json")
    if not os.path.exists(schedule_file):
        print(f"❌ ไม่พบไฟล์ตารางการโพสต์: {schedule_file}")
        sys.exit(1)
        
    with open(schedule_file, "r", encoding="utf-8") as f:
        schedule = json.load(f)
        
    # จัดกลุ่มตามประเภท
    rules = {
        "Reels_Under1Min": [],
        "FB_Videos_3-5Min": [],
        "Rerun_Post_Tue": [],
        "Rerun_Post_Fri": [],
        "Spoiler_Post_Thu": [],
        "Spoiler_Post_Sun": []
    }
    
    type_map = {
        "reels": "Reels_Under1Min",
        "fb_video": "FB_Videos_3-5Min",
        "rerun_tue": "Rerun_Post_Tue",
        "rerun_fri": "Rerun_Post_Fri",
        "spoiler_thu": "Spoiler_Post_Thu",
        "spoiler_sun": "Spoiler_Post_Sun"
    }
    
    for key, val in schedule.items():
        if key.startswith("_"):
            continue
        c_type = val.get("type")
        if c_type in type_map:
            q_name = type_map[c_type]
            weekday = val.get("weekday")
            time_str = val.get("time")
            hour, minute = map(int, time_str.split(":"))
            rules[q_name].append({
                "weekday_py": json_weekday_to_python(weekday),
                "hour": hour,
                "minute": minute
            })
            
    return rules

def get_sort_key(page):
    title = page.get("title", "")
    
    # สำหรับการ์ด Rerun ให้จัดเรียงตามวันเผยแพร่วิดีโอต้นฉบับ (เก่าสุดไปใหม่สุด)
    if "[RERUN" in title.upper():
        cleaned = title
        if cleaned.startswith("[RERUN_THU]"):
            cleaned = cleaned[len("[RERUN_THU]"):].strip()
        elif cleaned.startswith("[RERUN_SUN]"):
            cleaned = cleaned[len("[RERUN_SUN]"):].strip()
        
        cleaned_lower = cleaned.strip().lower()
        
        # 1. ค้นหาแบบตรงตัวในดิกชันนารีวันเผยแพร่
        if cleaned_lower in video_dates:
            return (2, video_dates[cleaned_lower], title)
            
        # 2. ค้นหาแบบกึ่งตรง (Fuzzy Matching)
        for v_title, v_date in video_dates.items():
            if cleaned_lower in v_title or v_title in cleaned_lower:
                return (2, v_date, title)
                
        # หากไม่พบข้อมูล ให้กำหนดวันเผยแพร่ในอนาคตไกลๆ (เพื่อให้จัดไปอยู่ท้ายคิว)
        return (2, datetime(2030, 1, 1), title)

    # สำหรับคลิปใหม่หรือโพสต์ทั่วไป ให้จัดเรียงตามตัวเลขหน้าคลิป
    match = re.search(r'(?:\]\s*|^)(\d+)', title)
    if match:
        return (0, int(match.group(1)), title)
    return (1, 0, title)

def main():
    tz_th = timezone(timedelta(hours=7))
    now_local = datetime.now(tz_th)
    
    print("=" * 60)
    print("📅 WTJ Auto-Scheduler (Hybrid Mode)")
    print(f"⏱️  เวลาปัจจุบัน: {now_local.strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)
    
    # 1. โหลดตารางเวลา
    rules = load_schedule_rules()
    
    # 2. ดึงการ์ดทั้งหมดจาก Notion
    helper = NotionHelper()
    print("🔍 กำลังดึงข้อมูลการ์ดทั้งหมดจาก Notion เพื่อวิเคราะห์ช่วงเวลาที่ถูกจองแล้ว...")
    
    # ดึงการ์ดทุกสถานะเพื่อหาวันที่ที่ตั้งไว้แล้ว (ป้องกันการทับซ้อน)
    # Query database ทั้งหมด
    res = helper.query_database()
    if not res or "results" not in res:
        print("❌ ไม่สามารถดึงข้อมูลจาก Notion ได้แก!")
        return
        
    pages = res["results"]
    
    # แยกประเภทคิวงานและเก็บวันที่จองแล้ว
    # คิว -> รายการของวันเวลาที่จองแล้ว (datetime)
    booked_dates = {
        "Reels_Under1Min": [],
        "FB_Videos_3-5Min": [],
        "Rerun_Post_Tue": [],
        "Rerun_Post_Fri": [],
        "Spoiler_Post_Thu": [],
        "Spoiler_Post_Sun": []
    }
    
    approved_cards = {
        "Reels_Under1Min": [],
        "FB_Videos_3-5Min": [],
        "Rerun_Post_Tue": [],
        "Rerun_Post_Fri": [],
        "Spoiler_Post_Thu": [],
        "Spoiler_Post_Sun": []
    }
    
    title_prop_name = helper.get_title_property_name()
    
    for page in pages:
        props = page["properties"]
        page_id = page["id"]
        
        # ดึงสถานะ
        status = "None"
        status_prop = props.get("Status", {})
        if status_prop.get("type") == "select" and status_prop.get("select"):
            status = status_prop["select"]["name"]
            
        # ดึงแท็กแพลตฟอร์ม
        platforms = []
        platform_prop = props.get("Platform", {})
        if platform_prop.get("type") == "multi_select" and platform_prop.get("multi_select"):
            platforms = [item["name"] for item in platform_prop["multi_select"]]
            
        # ดึงวันเผยแพร่
        publish_date_str = None
        date_prop = props.get("Publish Date", {})
        if date_prop.get("type") == "date" and date_prop.get("date"):
            publish_date_str = date_prop["date"].get("start")
            
        # ดึงชื่อหัวข้อ
        title = "Untitled"
        name_prop = props.get(title_prop_name, {})
        if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
            title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
            
        # จัดกลุ่มเข้าคิว
        q_name = None
        if "Reels" in platforms:
            q_name = "Reels_Under1Min"
        elif "FB_Video" in platforms:
            q_name = "FB_Videos_3-5Min"
        elif "FB_Text_Quote" in platforms:
            if "[RERUN_THU]" in title:
                q_name = "Rerun_Post_Tue"   # Rerun วันพฤหัสบดี ย้ายไปลงอังคาร
            elif "[RERUN_SUN]" in title:
                q_name = "Rerun_Post_Fri"   # Rerun วันอาทิตย์ ย้ายไปลงศุกร์
            elif "[THU_สปอย" in title or ("สปอย" in title and ("พฤหัส" in title or "THU" in title)):
                q_name = "Spoiler_Post_Thu" # สปอย Podcast ลงพฤหัสบดีเช้า
            elif "[SUN_สปอย" in title or ("สปอย" in title and ("อาทิตย์" in title or "SUN" in title)):
                q_name = "Spoiler_Post_Sun" # สปอย Story ลงอาทิตย์เช้า
            else:
                # Fallback: ถ้าเป็น FB_Text_Quote ทั่วไปที่ไม่มี prefix
                if "RERUN" in title.upper():
                    if "THU" in title.upper():
                        q_name = "Rerun_Post_Tue"
                    else:
                        q_name = "Rerun_Post_Fri"
                else:
                    if "THU" in title.upper() or "PODCAST" in title.upper() or "TALK" in title.upper():
                        q_name = "Spoiler_Post_Thu"
                    else:
                        q_name = "Spoiler_Post_Sun"
            
        if not q_name:
            continue
            
        # ถ้าการ์ดนี้มีสถานะอนุมัติและยังไม่มีวันเวลาโพสต์ ให้เก็บไว้ลงตาราง
        if status == "5_Approved" and not publish_date_str:
            approved_cards[q_name].append({
                "id": page_id,
                "title": title,
                "platforms": platforms
            })
            
        # ถ้าการ์ดมีวันเวลาโพสต์แล้ว (ทั้งที่โพสต์แล้ว 6_Published หรือตั้งจองไว้) ให้เก็บไว้ในรายการจอง
        if publish_date_str:
            try:
                if "T" in publish_date_str:
                    p_dt = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00")).astimezone(tz_th)
                else:
                    dt = datetime.strptime(publish_date_str, "%Y-%m-%d")
                    # แฟลตเวลาตามประเภทคิวเพื่อความง่าย
                    # หาสลอตเวลาของคิวนี้
                    p_dt = datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
                booked_dates[q_name].append(p_dt)
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดในการอ่านวันที่ '{publish_date_str}' ของการ์ด '{title}': {e}")
                
    # 3. เริ่มประมวลผลคำนวณและหยอดเวลาในแต่ละคิว
    total_scheduled = 0
    
    for q_name, cards in approved_cards.items():
        if not cards:
            continue
            
        print(f"\n📂 จัดการคิว: {q_name} (พบการ์ดรอตั้งเวลา {len(cards)} ใบ)")
        
        # เรียงลำดับตัวเลขคลิปเพื่อเรียงคิวโพสต์อย่างถูกต้อง
        cards.sort(key=get_sort_key)
        
        # หาจุดเริ่มต้นคำนวณของคิวนี้
        # ถ้ามีวันจองล่าสุด ให้เริ่มหาสลอตถัดไปนับจากวันนั้น
        # ถ้าไม่มี ให้เริ่มหาสลอตถัดไปนับจากวันนี้ (now_local)
        start_dt = now_local
        if booked_dates[q_name]:
            max_booked = max(booked_dates[q_name])
            if max_booked > now_local:
                start_dt = max_booked
                print(f"   ℹ️ พบวันที่จองไว้ล่าสุดของคิวนี้คือ: {start_dt.strftime('%d/%m/%Y %H:%M')}")
                
        # ฟังก์ชันช่วยหาสลอตเวลาถัดไป
        q_rules = rules[q_name]
        if not q_rules:
            print(f"   ⚠️ ไม่พบกฎการโพสต์ของคิว {q_name} ข้ามการประมวลผล")
            continue
            
        current_ref = start_dt
        
        for card in cards:
            # หาสลอตเวลาถัดไปที่เข้าเงื่อนไข
            next_slot = None
            days_offset = 0
            
            while not next_slot:
                # ตรวจดูวันถัดๆ ไปทีละวัน
                days_offset += 1
                check_day = current_ref + timedelta(days=days_offset)
                check_w = check_day.weekday()
                
                # ตรวจว่าตรงกับกฎข้อไหนไหม
                matching_rules = [r for r in q_rules if r["weekday_py"] == check_w]
                if matching_rules:
                    # ตรง! หยิบสล็อตแรก
                    rule = matching_rules[0]
                    candidate_dt = check_day.replace(hour=rule["hour"], minute=rule["minute"], second=0, microsecond=0)
                    
                    # เช็คว่าทับซ้อนกับวันที่จองไปแล้วหรือไม่
                    # (ทับกันหมายถึงตรงกันห่างกันไม่เกิน 1 ชั่วโมง)
                    is_booked = False
                    for b_date in booked_dates[q_name]:
                        if abs((candidate_dt - b_date).total_seconds()) < 3600:
                            is_booked = True
                            break
                            
                    if not is_booked:
                        next_slot = candidate_dt
                        
            # อัปเดตลง Notion
            publish_date_iso = next_slot.isoformat()
            print(f"   ➔ 📅 ตั้งเวลาให้: '{card['title']}'")
            print(f"      📍 ลงวันที่: {next_slot.strftime('%d/%m/%Y เวลา %H:%M น.')}")
            
            # อัปเดตผ่าน API
            url = f"https://api.notion.com/v1/pages/{card['id']}"
            data = {
                "properties": {
                    "Publish Date": {
                        "date": {
                            "start": publish_date_iso
                        }
                    }
                }
            }
            res_update = helper._make_request(url, method="PATCH", data=data)
            if res_update:
                booked_dates[q_name].append(next_slot)
                current_ref = next_slot
                total_scheduled += 1
            else:
                print(f"      ❌ อัปเดตลง Notion ไม่สำเร็จ!")
                
    print("\n" + "=" * 60)
    print(f"🎉 ดำเนินการออโต้ตั้งเวลาสำเร็จทั้งหมด {total_scheduled} รายการ!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
