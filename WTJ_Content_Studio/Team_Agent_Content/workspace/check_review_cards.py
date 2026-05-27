#!/usr/bin/env python3
import os
import sys

# Find project root
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
skills_path = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills")
if skills_path not in sys.path:
    sys.path.append(skills_path)

from notion_helper import NotionHelper

def main():
    notion = NotionHelper()
    pages = notion.fetch_pages_by_status("4_Review")
    print(f"Total pages in 4_Review: {len(pages)}")
    for p in pages:
        print(f"- ID: {p['id']}, Title: {p['title']}")

if __name__ == "__main__":
    main()
