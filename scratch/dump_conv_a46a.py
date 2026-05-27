import sqlite3
import os

db_path = "/Users/chz/.gemini/antigravity/conversations/a46a20cf-82f4-423d-b272-0616cab44781.db"

if not os.path.exists(db_path):
    print("❌ DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT idx, step_payload FROM steps ORDER BY idx;")
rows = cursor.fetchall()

print(f"Dump of conversation a46a - Total steps: {len(rows)}")

# Let's search for "ถาม-ตอบ" in steps and print the steps and content
for idx, payload in rows:
    if not payload:
        continue
    try:
        payload_str = payload.decode('utf-8', errors='ignore')
        if "ถาม-ตอบ 2" in payload_str or "ถามตอบ 2" in payload_str or "ถาม-ตอบ" in payload_str:
            print(f"\n[Step {idx}]")
            # Print up to 1000 characters of readable text
            readable = []
            for char in payload_str:
                code = ord(char)
                if 32 <= code <= 126 or 3584 <= code <= 3711 or char in '\n\t':
                    readable.append(char)
            clean_text = "".join(readable)
            print(clean_text[:1000])
    except Exception as e:
        print(f"Error reading step {idx}: {e}")

conn.close()
