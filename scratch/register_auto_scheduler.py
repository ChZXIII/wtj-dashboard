#!/usr/bin/env python3
import os
import plistlib
import subprocess

PROJECT_ROOT = "/Users/chz/Desktop/ChZ_Agent_Corp"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PYTHON3_PATH = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scratch", "auto_schedule_approved.py")
LABEL = "com.wtj.auto_scheduler"
PLIST_PATH = os.path.join(LAUNCH_AGENTS_DIR, f"{LABEL}.plist")
LOG_BASE = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "auto_scheduler")

def register_agent():
    print(f"⚙️  กำลังลงทะเบียน macOS LaunchAgent: {LABEL}")
    
    # 1. Unload old if exists
    if os.path.exists(PLIST_PATH):
        subprocess.run(["launchctl", "unload", PLIST_PATH], capture_output=True)
        try:
            os.remove(PLIST_PATH)
            print("   🗑️  ลบไฟล์คอนฟิกเดิม")
        except Exception as e:
            print(f"   ⚠️  ลบไฟล์คอนฟิกเดิมล้มเหลว: {e}")

    # 2. สร้าง plist ข้อมูลสำหรับรันทุกวันเวลา 04:00 น.
    plist_data = {
        "Label": LABEL,
        "ProgramArguments": [PYTHON3_PATH, SCRIPT_PATH],
        "WorkingDirectory": PROJECT_ROOT,
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        },
        "StartCalendarInterval": {
            "Hour": 4,
            "Minute": 0
        },
        "RunAtLoad": False,
        "StandardOutPath": f"{LOG_BASE}.out",
        "StandardErrorPath": f"{LOG_BASE}.err",
    }

    try:
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist_data, f)
        print(f"   💾 เขียนไฟล์ plist สำเร็จที่: {PLIST_PATH}")
    except Exception as e:
        print(f"   ❌ เขียนไฟล์ plist ล้มเหลว: {e}")
        return

    # 3. Load agent เข้าสู่ launchctl
    result = subprocess.run(["launchctl", "load", PLIST_PATH], capture_output=True)
    if result.returncode == 0:
        print(f"   ✅ ลงทะเบียนสำเร็จ! บอทจะตื่นขึ้นมารันคำนวณปฏิทินทุกวันเวลา 04:00 น. ⏰")
    else:
        print(f"   ❌ โหลด LaunchAgent ล้มเหลว (code: {result.returncode})")
        print(f"   Error: {result.stderr.decode().strip()}")

if __name__ == "__main__":
    register_agent()
