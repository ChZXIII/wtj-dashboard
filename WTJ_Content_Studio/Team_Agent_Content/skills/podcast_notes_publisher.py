#!/usr/bin/env python3
"""
🚀 Podcast Notes Publisher Skill
หน้าที่: ส่งเนื้อหา/บทสัมภาษณ์ เข้า Apple Notes ในโฟลเดอร์ที่ต้องการ (Default: WTJ Podcast)
"""

import os
import sys
import argparse
import subprocess

def format_text_to_html(text):
    """แปลงเนื้อหาดิบ/Markdown เบื้องต้นเป็น HTML สำหรับ Apple Notes"""
    lines = text.split('\n')
    html_output = ""
    for line in lines:
        clean_line = line.strip()
        if clean_line == "":
            html_output += "<div><br></div>"
        else:
            # แปลงหัวข้อ Markdown
            if clean_line.startswith("# "):
                clean_line = "<h1><b>" + clean_line[2:] + "</b></h1>"
            elif clean_line.startswith("## "):
                clean_line = "<h2><b>" + clean_line[3:] + "</b></h2>"
            elif clean_line.startswith("### "):
                clean_line = "<h3><b>" + clean_line[4:] + "</b></h3>"
            # แปลงตัวหนา Markdown
            import re
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_line)
            # แปลงลิงก์ Markdown
            clean_line = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', clean_line)
            
            # ถ้าเป็น bullet point
            if clean_line.startswith("- ") or clean_line.startswith("* ") or clean_line.startswith("• "):
                clean_line = "• " + clean_line[2:]
                
            html_output += f"<div>{clean_line}</div>"
    return html_output

def push_to_notes(note_name, content, folder_name):
    # ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = current_dir
    while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
        if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
            break
        PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

    # แปลง content เป็น HTML
    if not (content.startswith("<div>") or content.startswith("<html>")):
        html_body = format_text_to_html(content)
    else:
        html_body = content

    # Escape double quotes and newlines for AppleScript
    html_escaped = html_body.replace('"', '\\"').replace('\n', '\\n')
    
    applescript = f'''
    tell application "Notes"
        set folderFound to false
        
        -- Try top-level folder
        if exists folder "{folder_name}" then
            set targetFolder to folder "{folder_name}"
            set folderFound to true
        end if
        
        -- Try under WTJ
        if not folderFound then
            if exists folder "WTJ" then
                set rootFolder to folder "WTJ"
                if exists folder "{folder_name}" of rootFolder then
                    set targetFolder to folder "{folder_name}" of rootFolder
                    set folderFound to true
                end if
            end if
        end if
        
        -- If still not found, create at top level
        if not folderFound then
            make new folder with properties {{name:"{folder_name}"}}
            set targetFolder to folder "{folder_name}"
        end if
        
        -- Delete old note if exists
        try
            delete (notes of targetFolder whose name contains "{note_name}")
        end try
        
        -- Create new note
        make new note with properties {{name:"{note_name}", body:"{html_escaped}"}} at targetFolder
    end tell
    '''
    
    process = subprocess.Popen(['osascript', '-e', applescript], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    
    if err and err.strip():
        print(f"❌ Error creating note: {err.decode('utf-8')}", file=sys.stderr)
        return False
    else:
        print(f"✅ Send note '{note_name}' to Apple Notes folder '{folder_name}' successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description="Skill: Publish Podcast Notes to Apple Notes")
    parser.add_argument("-t", "--title", required=True, help="ชื่อหัวข้อ/หัวโน้ต")
    parser.add_argument("-f", "--folder", default="WTJ Podcast", help="ชื่อโฟลเดอร์ปลายทางใน Apple Notes (Default: WTJ Podcast)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--content", help="เนื้อหาข้อความโดยตรง")
    group.add_argument("-i", "--input-file", help="พาธไฟล์เนื้อหาที่ต้องการอ่าน (รองรับ .txt หรือ .md)")

    args = parser.parse_args()

    content = ""
    if args.content:
        content = args.content
    elif args.input_file:
        if not os.path.exists(args.input_file):
            print(f"❌ Error: ไม่พบไฟล์อินพุตที่ {args.input_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()

    success = push_to_notes(args.title, content, args.folder)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
