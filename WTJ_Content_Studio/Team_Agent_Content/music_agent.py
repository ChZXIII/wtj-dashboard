import os
import google.generativeai as genai

import sys
# Add parent directory to path so we can import model_router
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)
import model_router

# Load the system prompt
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompts", "music_prompt.md")
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    system_instruction = f.read()

# Initialize the chat session via model_router
chat = model_router.get_chat_session("music", system_instruction=system_instruction)

print("==================================================")
print("🛹 น้องมิวสิค (Creative Marketer) มารายงานตัวแล้วค่าา! 💖")
print("พิมพ์ 'exit' หรือ 'quit' เพื่อออกจากโปรแกรม")
print("==================================================\n")

while True:
    user_input = input("คุณ (ทีมงาน): ")
    if user_input.lower() in ['exit', 'quit']:
        print("มิวสิค: บ๊ายบายค่าแก ไว้มาคิดไอเดียจึ้งๆ กันใหม่น้าา! 👋💥")
        break
    
    if not user_input.strip():
        continue
        
    try:
        response = chat.send_message(user_input)
        print(f"\nมิวสิค:\n{response.text}\n")
    except Exception as e:
        print(f"\n[เกิดข้อผิดพลาดในการเชื่อมต่อ API: {e}]\n")
