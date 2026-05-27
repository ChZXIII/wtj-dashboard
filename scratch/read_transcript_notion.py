import json
import os

transcript_path = "/Users/chz/.gemini/antigravity/brain/ebc0c03e-7494-432e-8719-08b48bf6c245/.system_generated/logs/transcript.jsonl"

if not os.path.exists(transcript_path):
    print("❌ Transcript not found")
    exit(1)

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            step_index = data.get("step_index")
            source = data.get("source")
            msg_type = data.get("type")
            content = data.get("content", "")
            
            if msg_type == "USER_INPUT":
                print(f"\n👤 [USER] Step {step_index}:\n{content.strip()}")
            elif source == "MODEL" and msg_type == "PLANNER_RESPONSE":
                print(f"\n🦉 [MODEL] Step {step_index}:\n{content.strip()}")
        except Exception as e:
            pass
