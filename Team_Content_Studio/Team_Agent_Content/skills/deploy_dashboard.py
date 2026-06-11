#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

# Add current dir to path to allow importing skills siblings
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import config

def deploy():
    print("==================================================")
    print("🚀 เริ่มระบบอัปเดตและเผยแพร่แดชบอร์ดขึ้น GitHub Pages...")
    print("==================================================")

    # 1. นิยามไฟล์สำคัญที่ต้องซิงค์ไปรีโป
    files_to_sync = [
        "wtj_calendar_dashboard.html",
        "notion_calendar_data.js"
    ]

    # 2. คัดลอกไฟล์จากหน้าบ้าน (Local development) ไปยัง โฟลเดอร์ Git Repo
    print(f"📦 กำลังคัดลอกไฟล์แดชบอร์ด...")
    for filename in files_to_sync:
        src = os.path.join(config.LOCAL_DASHBOARD_DIR, filename)
        dst = os.path.join(config.GITHUB_DASHBOARD_DIR, filename)
        
        if not os.path.exists(src):
            print(f"⚠️ ข้าม: ไม่พบไฟล์ต้นทางที่ {src}")
            continue
            
        shutil.copy2(src, dst)
        print(f"   -> คัดลอก {filename} สำเร็จ!")

    # 3. สั่งคอมมิตและพุชขึ้น GitHub
    print(f"\n🖥️ กำลังรันคำสั่ง Git ในโฟลเดอร์ {config.GITHUB_DASHBOARD_DIR}...")
    try:
        # git add
        subprocess.run(
            ["git", "add"] + files_to_sync,
            cwd=config.GITHUB_DASHBOARD_DIR,
            check=True
        )
        
        # git status check
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=config.GITHUB_DASHBOARD_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not status_res.stdout.strip():
            print("✨ ไม่พบการเปลี่ยนแปลงใดๆ บนแดชบอร์ด ระบบไม่จำเป็นต้อง Push ขึ้น GitHub จ้า!")
            return True

        # git commit
        commit_msg = f"chore: auto-sync dashboard updates on {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=config.GITHUB_DASHBOARD_DIR,
            check=True
        )
        
        # git push
        print("📤 กำลังส่งข้อมูล (Git Push) ไปที่ GitHub รีโป...")
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=config.GITHUB_DASHBOARD_DIR,
            check=True
        )
        print("\n✅ อัปเดตและเผยแพร่แดชบอร์ดขึ้น GitHub Pages สำเร็จเรียบร้อยแล้วแก! 🎉")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ เกิดข้อผิดพลาดในการสั่งรัน Git: {e}")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
        return False

if __name__ == "__main__":
    deploy()
