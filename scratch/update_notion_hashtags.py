#!/usr/bin/env python3
import os
import sys
import re

# Find project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
skills_dir = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills")
if skills_dir not in sys.path:
    sys.path.append(skills_dir)

from notion_helper import NotionHelper

NEW_HASHTAGS = " #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน #เจาะลึกอาชีพ #วัยทำงาน"

def update_hashtags_in_text(text):
    lines = text.split("\n")
    updated_lines = []
    for line in lines:
        if "#WhatTheJob" in line:
            if "#รีวิวชีวิตทำงาน" not in line:
                line = line.strip() + NEW_HASHTAGS
        updated_lines.append(line)
    return "\n".join(updated_lines)

def update_notion_pages():
    print("🤖 Starting Notion Hashtags Updater...")
    notion = NotionHelper()
    
    # Query 4_Review pages
    print("🔍 Fetching pages with status '4_Review' from Notion...")
    pages = notion.fetch_pages_by_status("4_Review")
    if not pages:
        print("📭 No pages with status '4_Review' found.")
        return
        
    print(f"📌 Found {len(pages)} pages to process.")
    for idx, page in enumerate(pages, 1):
        page_id = page["id"]
        title = page["title"]
        print(f"[{idx}/{len(pages)}] Processing page: '{title}'...")
        
        # Get content
        content = notion.get_page_content_text(page_id)
        if not content:
            print("   ⚠️ No content found, skipping.")
            continue
            
        if "#WhatTheJob" not in content:
            print("   ⚠️ No #WhatTheJob hashtag found in content, skipping.")
            continue
            
        updated_content = update_hashtags_in_text(content)
        if updated_content != content:
            print("   🖊️ Updating page content in Notion...")
            notion.clear_page_content(page_id)
            notion.write_page_content_text(page_id, updated_content)
            print("   ✅ Updated page in Notion!")
        else:
            print("   ℹ️ Hashtags already present in Notion.")

def update_local_files():
    print("\n📁 Starting Local Files Hashtags Updater...")
    drafts_dir = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project", "workspace", "2_drafts")
    if not os.path.exists(drafts_dir):
        print(f"❌ Local drafts directory not found: {drafts_dir}")
        return
        
    files = [f for f in os.listdir(drafts_dir) if f.endswith(".md")]
    print(f"📌 Found {len(files)} local markdown draft files.")
    
    updated_count = 0
    for idx, f in enumerate(files, 1):
        file_path = os.path.join(drafts_dir, f)
        with open(file_path, "r", encoding="utf-8") as file_obj:
            content = file_obj.read()
            
        if "#WhatTheJob" not in content:
            continue
            
        updated_content = update_hashtags_in_text(content)
        if updated_content != content:
            with open(file_path, "w", encoding="utf-8") as file_obj:
                file_obj.write(updated_content)
            print(f"   ✅ Updated local file: {f}")
            updated_count += 1
            
    print(f"🎉 Updated {updated_count} local files.")

if __name__ == "__main__":
    update_notion_pages()
    update_local_files()
