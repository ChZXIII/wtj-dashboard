import os
import sys
import datetime
from dotenv import load_dotenv

# Add project root to sys.path to import model_router
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

import model_router

# Setup Lab log path
LOG_DIR = os.path.abspath(os.path.join(project_root, "Agent_Lab", "logs"))
LOG_FILE = os.path.join(LOG_DIR, "test_run.log")

def log_to_lab(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [Sandbox Demo]: {message}\n"
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)
    print(log_line.strip())

def main():
    log_to_lab("เริ่มต้นรันเดโมทดสอบระบบในห้อง Sandbox Lab...")
    
    try:
        # Request a simple greeting from First (routes to Claude Opus, fallback to Gemini)
        log_to_lab("กำลังเชื่อมต่อขอคำทักทายจากเอเจนต์ First...")
        chat = model_router.get_chat_session("first", "คุณคือเฟิส คุยสั้นๆ ทักทายเพื่อนรัก")
        response = chat.send_message("โย่วแก สบายดีมั้ย")
        
        log_to_lab(f"ได้รับคำตอบ: {response.text}")
        log_to_lab("การทดสอบสำเร็จลุล่วง 100%!")
        
    except Exception as e:
        log_to_lab(f"เกิดข้อผิดพลาดในการทดสอบ: {e}")

if __name__ == "__main__":
    main()
