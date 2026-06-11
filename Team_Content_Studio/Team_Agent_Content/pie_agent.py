import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env from workspace root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

import sys
# Add parent directory to path so we can import model_router
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)
import model_router

# Load the system prompt for Pie
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompts", "pie_prompt.md")
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    system_instruction = f.read()

# Load the latest data analysis report if available to give Pie local context
report_path = os.path.join(os.path.dirname(__file__), "workspace", "data_analysis_report.md")
if os.path.exists(report_path):
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        system_instruction += "\n\n---\n\nนี่คือรายงานวิเคราะห์ข้อมูลล่าสุดที่คุณ (ปาย) ได้ทำไว้ ใช้ข้อมูลในนี้ตอบคำถามที่เกี่ยวข้องได้เลย:\n\n" + report_content
    except Exception as e:
        print(f"⚠️ ไม่สามารถโหลดรายงานวิเคราะห์ข้อมูลล่าสุดได้: {e}")

# Initialize the chat session via model_router
chat = model_router.get_chat_session("pie", system_instruction=system_instruction)

print("==================================================")
print("📊 น้องปาย (Data Analyst) พร้อมวิเคราะห์ตัวเลขแล้วจ้า!")
print("พิมพ์ 'exit' หรือ 'quit' เพื่อออกจากโปรแกรม")
print("==================================================\n")

while True:
    user_input = input("คุณ (ทีมงาน): ")
    if user_input.lower() in ['exit', 'quit']:
        print("น้องปาย: บ๊ายบายแก ไว้มีตัวเลขหรือสถิติตัวไหนน่าสงสัย ค่อยเรียกปายมาดูอีกนะ!")
        break
    
    if not user_input.strip():
        continue
        
    try:
        response = chat.send_message(user_input)
        print(f"\nน้องปาย:\n{response.text}\n")
    except Exception as e:
        print(f"\n[เกิดข้อผิดพลาดในการเชื่อมต่อ API: {e}]\n")
