#!/usr/bin/env python3
"""
⚙️ WTJ Schedule Configurator (Queue-based version)
อ่าน posting_schedule.json ที่ครีมเขียนไว้
แล้วสร้าง/อัปเดต LaunchAgents สำหรับบอทโพส Facebook ทุกวันตามประเภทคอนเทนต์
รันโดยอัตโนมัติ: ทุกวันที่ 1 ของเดือน เวลา 12:00 น.
"""

import os
import json
import plistlib
import subprocess
from datetime import datetime

# === Paths ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.env')) or os.path.exists(os.path.join(PROJECT_ROOT, '.git')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

SCHEDULE_FILE = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "posting_schedule.json")
MASTER_SCRIPT = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "skills", "wtj_auto_poster.py")
CONTENT_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project")
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")

# ใช้ Python ใน Virtual Environment ของโปรเจกต์โดยตรงเพื่อความถูกต้อง
PYTHON3_PATH = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
if not os.path.exists(PYTHON3_PATH):
    PYTHON3_PATH = "/usr/bin/python3" # Fallback

# Map ประเภทคอนเทนต์ -> โฟลเดอร์คิวใน Apple Notes
QUEUE_MAP = {
    "reels": "Reels_Under1Min",
    "fb_video": "FB_Videos_3-5Min",
    "text_post": "Text_Posts"
}

def unload_old_agents():
    """ถอด LaunchAgents บอทโพส WTJ เก่าทั้งหมดออก"""
    if not os.path.exists(LAUNCH_AGENTS_DIR):
        return
    
    count = 0
    for filename in os.listdir(LAUNCH_AGENTS_DIR):
        is_wtj_agent = (
            filename.startswith("com.wtj.fb.") or 
            filename.startswith("com.wtj.yt.") or 
            filename.startswith("com.wtj.tt.") or
            filename.startswith("com.wtj.master.")
        ) and filename.endswith(".plist")
        
        if is_wtj_agent:
            label = filename[:-6]
            plist_path = os.path.join(LAUNCH_AGENTS_DIR, filename)
            subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
            try:
                os.remove(plist_path)
                print(f"   🗑️  ถอด LaunchAgent เก่า: {label}")
                count += 1
            except Exception as e:
                print(f"   ⚠️  ลบไฟล์ LaunchAgent ล้มเหลว: {plist_path} ({e})")
    return count

def create_launch_agent_generic(platform_prefix, script_path, agent_key, args_list, weekday, hour, minute):
    """สร้าง LaunchAgent plist สำหรับสคริปต์, แพลตฟอร์ม และเวลาที่ระบุ"""
    label = f"com.wtj.{platform_prefix}.{agent_key.lower()}"
    plist_path = os.path.join(LAUNCH_AGENTS_DIR, f"{label}.plist")
    log_base = os.path.join(CONTENT_DIR, "workspace", f"{platform_prefix}_{agent_key.lower()}")

    # จัดเตรียมเวลาในการทริกเกอร์
    calendar_interval = {
        "Hour": hour,
        "Minute": minute
    }
    if weekday is not None:
        calendar_interval["Weekday"] = weekday

    plist_data = {
        "Label": label,
        "ProgramArguments": [PYTHON3_PATH, script_path] + args_list,
        "WorkingDirectory": PROJECT_ROOT,  # รันที่ root โฟลเดอร์โปรเจกต์
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        },
        "StartCalendarInterval": calendar_interval,
        "RunAtLoad": False,
        "StandardOutPath": f"{log_base}.out",
        "StandardErrorPath": f"{log_base}.err",
    }

    with open(plist_path, "wb") as f:
        plistlib.dump(plist_data, f)

    result = subprocess.run(["launchctl", "load", plist_path], capture_output=True)
    return result.returncode == 0, plist_path

def main():
    print("=" * 60)
    print("⚙️  WTJ Schedule Configurator (Queue-based)")
    print(f"📆 วันที่รัน: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)

    if not os.path.exists(SCHEDULE_FILE):
        print(f"❌ ไม่พบไฟล์ตารางการโพสต์: {SCHEDULE_FILE}")
        return

    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    last_updated = schedule.get("_last_updated", "ไม่ทราบ")
    print(f"📋 อ่านตาราง posting_schedule.json (อัปเดตล่าสุด: {last_updated})")
    print(f"🐍 ใช้ Python: {PYTHON3_PATH}")
    print()

    # ถอด LaunchAgents เก่าออกก่อน
    print("🗑️  ถอด LaunchAgents เก่าออก...")
    unloaded = unload_old_agents()
    print(f"    เสร็จสิ้น! ถอดออกทั้งหมด {unloaded} ตัว")
    print()

    # สร้าง LaunchAgents ใหม่ตามตารางเวลาใหม่
    print("✨ สร้าง LaunchAgents ใหม่...")
    success_count = 0
    total_agents = 0

    day_names_thai = {
        0: "อาทิตย์",
        1: "จันทร์",
        2: "อังคาร",
        3: "พุธ",
        4: "พฤหัสบดี",
        5: "ศุกร์",
        6: "เสาร์",
    }

    for key, value in schedule.items():
        if key.startswith("_"):  # ข้าม metadata fields
            continue
        
        total_agents += 1
        c_type = value.get("type")
        time_str = value.get("time")
        weekday = value.get("weekday") # อาจเป็น None (แปลว่าโพสต์ทุกวัน)
        
        if c_type not in QUEUE_MAP:
            print(f"   ⚠️  ไม่รู้จักประเภทคอนเทนต์ '{c_type}' สำหรับคีย์ '{key}' ข้ามไป")
            continue
            
        queue_folder = QUEUE_MAP[c_type]
        
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            print(f"   ❌ รูปแบบเวลาผิด '{time_str}' สำหรับคีย์ '{key}'")
            continue

        # สร้าง Master Auto-Poster Agent ตัวเดียวต่อตารางเวลา
        success, plist_path = create_launch_agent_generic(
            "master", MASTER_SCRIPT, key, ["-q", queue_folder], weekday, hour, minute
        )
        
        if success:
            timing_desc = f"ทุกวัน{day_names_thai[weekday]}" if weekday is not None else "ทุกวัน"
            print(f"   ✅ บอทโพส Master {key} (คิว: {queue_folder}) → {timing_desc} เวลา {time_str} น.")
            success_count += 1
        else:
            print(f"   ❌ สร้าง LaunchAgent Master สำหรับ {key} ไม่สำเร็จ")

    # 🧹 Notion Archiver Agent (Run every Sunday at 03:00 AM)
    print()
    print("🧹 ตั้งค่าระบบ Notion Archiver อัตโนมัติ...")
    archiver_script = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "skills", "notion_archiver.py")
    success_archiver, plist_archiver = create_launch_agent_generic(
        "master", archiver_script, "archiver", [], 0, 3, 0  # 0 = Sunday, 3:00 AM
    )
    if success_archiver:
        print("   ✅ Notion Archiver (notion_archiver.py) → ทุกวันอาทิตย์ เวลา 03:00 น.")
    else:
        print("   ❌ สร้าง LaunchAgent Notion Archiver ไม่สำเร็จ")

    print()
    print("=" * 60)
    print(f"🎉 เสร็จสิ้น! ตั้งบอทโพสและระบบเคลียร์บ้านสำเร็จ {success_count + (1 if success_archiver else 0)}/{total_agents + 1} รายการ")
    print("=" * 60)

if __name__ == "__main__":
    main()
