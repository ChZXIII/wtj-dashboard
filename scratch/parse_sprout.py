import re

file_path = '/Users/chz/.gemini/antigravity/brain/82710335-6133-4102-a83e-086bcda1e0f1/.system_generated/steps/391/content.md'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's clean the HTML tags to make it readable
text_clean = re.sub(r'<[^>]+>', ' ', text)
text_clean = re.sub(r'\s+', ' ', text_clean)

print("--- Searching for YouTube ---")
matches = [m.start() for m in re.finditer(r'YouTube', text_clean, re.I)]
for m in matches[:10]:
    start = max(0, m - 150)
    end = min(len(text_clean), m + 150)
    print(f"[{m}] ...{text_clean[start:end]}...\n")

print("\n--- Searching for TikTok ---")
matches_tt = [m.start() for m in re.finditer(r'TikTok', text_clean, re.I)]
for m in matches_tt[:10]:
    start = max(0, m - 150)
    end = min(len(text_clean), m + 150)
    print(f"[{m}] ...{text_clean[start:end]}...\n")
