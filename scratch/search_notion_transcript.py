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
            
            # Print steps containing "notion" (case insensitive) or "ดูแล" or "คนไหน"
            # to see if there was a previous explanation
            lower_content = content.lower()
            if "notion" in lower_content:
                # Find occurrences of team members
                print(f"\n[{source} Step {step_index}]")
                # Print a few lines around the match
                lines = content.split('\n')
                for l in lines:
                    if "notion" in l.lower() or "ดูแล" in l or "ทีมงาน" in l or "คนไหน" in l:
                        print(f"   {l.strip()}")
        except Exception as e:
            pass
