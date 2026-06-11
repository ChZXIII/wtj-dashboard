#!/usr/bin/env python3
import os
import sys
import glob

# Find project root
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
skills_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "skills")
if skills_path not in sys.path:
    sys.path.append(skills_path)

from notion_helper import NotionHelper

def process_text_hashtags(text):
    lines = text.split('\n')
    updated_lines = []
    for line in lines:
        stripped = line.strip()
        # A hashtag line has words starting with #, e.g. "#WhatTheJob #Streamer"
        words = stripped.split()
        if words and all(w.startswith('#') for w in words):
            # It's a hashtag line!
            # Required hashtags: #WhatTheJob #WTJ #WTJTALK #WTJSTORY #WTJPODCAST #PODCAST
            required = ["#whatthejob", "#wtj", "#wtjtalk", "#wtjstory", "#wtjpodcast", "#podcast"]
            
            new_words = []
            for w in words:
                if w.lower() not in required:
                    new_words.append(w)
            
            # Build list with standard capitalization
            final_words = ["#WhatTheJob"]
            for w in new_words:
                final_words.append(w)
            final_words.extend(["#WTJ", "#WTJTALK", "#WTJSTORY", "#WTJPODCAST", "#PODCAST"])
            
            # De-duplicate while preserving order
            seen = set()
            dedup_words = []
            for w in final_words:
                w_lower = w.lower()
                if w_lower not in seen:
                    seen.add(w_lower)
                    dedup_words.append(w)
            
            indent = line[:len(line) - len(line.lstrip())]
            updated_lines.append(indent + " ".join(dedup_words))
        else:
            updated_lines.append(line)
    return '\n'.join(updated_lines)

def main():
    print("==================================================")
    print("🦉 เลขาเฟิส: เริ่มดำเนินการปรับปรุงแฮชแท็กพื้นฐานในดราฟต์ทั้งหมด... 🚀")
    print("==================================================")
    
    # 1. Update Notion Pages in status "4_Review"
    notion = NotionHelper()
    pages = notion.fetch_pages_by_status("4_Review")
    print(f"พบการ์ดทั้งหมด {len(pages)} ใบในสถานะ 4_Review ที่จะทำการตรวจสอบ")
    
    updated_notion_count = 0
    for idx, p in enumerate(pages, 1):
        page_id = p["id"]
        title = p["title"]
        print(f"[{idx}/{len(pages)}] กำลังสแกนการ์ด: '{title}'...")
        
        # Get content
        content = notion.get_page_content_text(page_id)
        if not content:
            print(f"  - ไม่พบเนื้อหาในหน้า หรือไม่สามารถดึงข้อมูลได้ ข้าม...")
            continue
            
        updated_content = process_text_hashtags(content)
        
        if content != updated_content:
            print(f"  ⚡️ พบการเปลี่ยนแปลงของแฮชแท็ก กำลังเขียนข้อมูลทับใน Notion...")
            # Clear old content
            notion.clear_page_content(page_id)
            # Write new content
            notion.write_page_content_text(page_id, updated_content)
            print(f"  ✅ อัปเดต Notion สำเร็จ!")
            updated_notion_count += 1
        else:
            print(f"  - แฮชแท็กถูกต้องครบถ้วนแล้ว ไม่ต้องอัปเดต")
            
    # 2. Update Local Backup files in workspace/2_drafts/
    drafts_dir = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")
    md_files = glob.glob(os.path.join(drafts_dir, "*.md"))
    print(f"\nพบไฟล์ดราฟต์สำรองโลคอลทั้งหมด {len(md_files)} ไฟล์ใน: {drafts_dir}")
    
    updated_files_count = 0
    for idx, file_path in enumerate(md_files, 1):
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        updated_content = process_text_hashtags(content)
        
        if content != updated_content:
            print(f"[{idx}/{len(md_files)}] ⚡️ อัปเดตไฟล์โลคอล: {filename}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            updated_files_count += 1
        else:
            # Optionally log skipped
            pass
            
    print("\n==================================================")
    print(f"🎉 ดำเนินการปรับปรุงแฮชแท็กเสร็จเรียบร้อยแล้วแก!")
    print(f"  - อัปเดตการ์ด Notion สำเร็จ: {updated_notion_count} ใบ")
    print(f"  - อัปเดตไฟล์โลคอลสำเร็จ: {updated_files_count} ไฟล์")
    print("==================================================")

if __name__ == "__main__":
    main()
