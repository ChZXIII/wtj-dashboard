import sqlite3
import os
import re

db_path = "/Users/chz/.gemini/antigravity/conversations/14de93a9-af38-439c-8995-2a7c5ecc4a63.db"

if not os.path.exists(db_path):
    print("❌ DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT idx, step_payload FROM steps ORDER BY idx;")
rows = cursor.fetchall()

print(f"Dump of conversation 14de (ถาม-ตอบ 2 จ๊ะ) - Total steps: {len(rows)}")

for idx, payload in rows:
    if not payload:
        continue
    try:
        payload_str = payload.decode('utf-8', errors='ignore')
        
        # Clean the text to readable characters
        readable = []
        for char in payload_str:
            code = ord(char)
            if 32 <= code <= 126 or 3584 <= code <= 3711 or char in '\n\t':
                readable.append(char)
        clean_text = "".join(readable)
        
        # Find if it is a user input or model output
        # Usually, the payload contains the JSON block or the text message itself
        # Let's search for user request and model response patterns
        if "USER_REQUEST" in clean_text or "MODEL" in clean_text or "bot-" in clean_text:
            lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
            for line in lines:
                if len(line) < 300 and any(k in line for k in ["ถาม-ตอบ", "จ๊ะ", "แก", "ฉัน", "เฟิส", "ครับ", "ค่ะ"]):
                    print(f"[{idx}] {line}")
    except Exception as e:
        print(f"Error reading step {idx}: {e}")

conn.close()
