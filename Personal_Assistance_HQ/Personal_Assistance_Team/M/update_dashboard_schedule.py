#!/usr/bin/env python3
"""
🧑‍🎨 M — Dashboard Schedule Updater
รับตารางเวลาจาก posting_schedule.json แล้วอัปเดต HTML Dashboard
จากนั้น push ขึ้น GitHub อัตโนมัติ
รันโดยอัตโนมัติ: ทุกวันที่ 1 ของเดือน เวลา 12:30 น. (30 นาทีหลัง configurator)
"""

import os
import json
import re
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
DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "dashboard")
DASHBOARD_HTML = os.path.join(DASHBOARD_DIR, "index.html")

# Map ชื่อโฟลเดอร์ → id ใน HTML
DAY_ID_MAP = {
    "FB_VIDEO_MON": "opt-time-mon",
    "FB_VIDEO_TUE": "opt-time-tue",
    "FB_VIDEO_WED": "opt-time-wed",
    "TEXT_POST_THU": "opt-time-thu",
    "FB_VIDEO_FRI": "opt-time-fri",
    "FB_VIDEO_SAT": "opt-time-sat",
    "TEXT_POST_SUN": "opt-time-sun",
}

def update_dashboard_html(schedule):
    """อัปเดตเวลาโพสใน index.html ของ dashboard"""
    if not os.path.exists(DASHBOARD_HTML):
        print(f"❌ ไม่พบ: {DASHBOARD_HTML}")
        return False

    with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    updated = html
    changes = []

    for day_name, value in schedule.items():
        if day_name.startswith("_") or day_name not in DAY_ID_MAP:
            continue

        time_str = value["time"] if isinstance(value, dict) else value
        element_id = DAY_ID_MAP[day_name]
        # จับ pattern: <div class="optimal-time-badge" id="opt-time-xxx">🚀 <span>Time to Post: HH:MM</span></div>
        pattern = rf'(<div class="optimal-time-badge" id="{element_id}">🚀 <span>Time to Post: )[\d:]+(</span></div>)'
        replacement = rf'\g<1>{time_str}\g<2>'

        new_html = re.sub(pattern, replacement, updated)
        if new_html != updated:
            changes.append(f"{day_name}: {time_str}")
            updated = new_html

    if not changes:
        print("ℹ️ ข้อมูลใน HTML ตรงตามตารางเวลาของครีมอยู่แล้ว ไม่ต้องอัปเดตเพิ่มเติม")
        return True

    # เขียนกลับ
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ อัปเดต Dashboard HTML เรียบร้อย ({len(changes)} วัน):")
    for c in changes:
        print(f"   📅 {c}")
    return True

def git_push():
    """Commit และ push ขึ้น GitHub"""
    today = datetime.now().strftime("%d/%m/%Y")
    commit_msg = f"[M] อัปเดตเวลาโพส Facebook ประจำเดือน ({today})"

    cmds = [
        (["git", "add", "index.html"], "git add"),
        (["git", "commit", "-m", commit_msg], "git commit"),
        (["git", "push", "origin", "main"], "git push"),
    ]

    for cmd, label in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=DASHBOARD_DIR)
        if result.returncode == 0:
            print(f"   ✅ {label} สำเร็จ")
        else:
            # commit อาจ return 1 ถ้าไม่มีอะไรเปลี่ยน
            if label == "git commit" and "nothing to commit" in result.stdout + result.stderr:
                print(f"   ℹ️  ไม่มีการเปลี่ยนแปลงใหม่ (ข้ามการ commit)")
                return True
            print(f"   ❌ {label} ล้มเหลว: {result.stderr.strip()}")
            return False
    return True


def main():
    print("=" * 55)
    print("🧑‍🎨 M — Dashboard Schedule Updater")
    print(f"📆 วันที่รัน: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 55)

    # อ่าน schedule
    if not os.path.exists(SCHEDULE_FILE):
        print(f"❌ ไม่พบ posting_schedule.json")
        return

    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    print(f"📋 อ่านตารางจาก Cream เรียบร้อย\n")

    # อัปเดต HTML
    print("🖊️  อัปเดต Dashboard HTML...")
    success = update_dashboard_html(schedule)
    if not success:
        return

    # Push GitHub
    print("\n🚀 Push ขึ้น GitHub...")
    if git_push():
        print(f"\n🎉 Dashboard อัปเดตและ push GitHub เรียบร้อยแล้ว!")
        print(f"🔗 https://github.com/ChZXIII/wtj-dashboard")
    else:
        print("\n❌ Push ไม่สำเร็จ ตรวจสอบ git credentials นะแก")


if __name__ == "__main__":
    main()
