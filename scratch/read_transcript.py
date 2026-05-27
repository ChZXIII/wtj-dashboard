import json
import os

transcript_path = "/Users/chz/.gemini/antigravity/brain/82710335-6133-4102-a83e-086bcda1e0f1/.system_generated/logs/transcript.jsonl"

if not os.path.exists(transcript_path):
    print("❌ Transcript not found")
    exit(1)

print("🔍 Searching transcript for TikTok uploads...")
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            content = data.get("content", "")
            if "TikTok" in content or "tiktok" in content:
                # If content is a dict/json, print it. If it contains "Dry-run: False" or "upload"
                lines = content.split("\n")
                for l in lines:
                    if any(k in l for k in ["upload", "Upload", "สำเร็จ", "success", "โพสต์", "Privacy", "dry"]):
                        print(f"[{data.get('step_index')}] {l.strip()}")
        except Exception as e:
            pass
