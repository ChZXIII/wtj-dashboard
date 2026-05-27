import os
import json

brain_dir = "/Users/chz/.gemini/antigravity/brain"
keywords = ["แพ็คเกจ", "แพ็กเกจ", "package", "tier", "subscription", "advanced", "ultra", "premium", "free", "pay-as-you-go"]

print("Starting log search...")
if os.path.exists(brain_dir):
    for conv_id in os.listdir(brain_dir):
        conv_path = os.path.join(brain_dir, conv_id)
        if not os.path.isdir(conv_path):
            continue
        transcript_path = os.path.join(conv_path, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        content = data.get("content", "")
                        if not content and "tool_calls" in data:
                            content = str(data["tool_calls"])
                        for kw in keywords:
                            if kw.lower() in content.lower():
                                print(f"Match in {conv_id} line {line_num} (keyword: {kw}):")
                                print(content[:300])
                                print("-" * 40)
                    except Exception as e:
                        pass
else:
    print("Brain directory does not exist or cannot be accessed.")
