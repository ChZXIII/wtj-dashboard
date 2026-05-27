import os
import sys
import re
import subprocess
import html

def md_to_html(md_text):
    """Converts basic markdown tags to Apple Notes compatible HTML."""
    # Escape HTML characters first
    text = html.escape(md_text)
    
    # Unescape already escaped links to make them work in HTML
    text = text.replace("&amp;lt;", "<").replace("&amp;gt;", ">").replace("&amp;amp;", "&")
    
    # Headers
    text = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # Inline Code
    text = re.sub(r'`(.*?)`', r'<code style="background-color:#f4f4f4;padding:2px 4px;">\1</code>', text)
    
    # Links: [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Lists
    # Simple replacement for bullet points
    text = re.sub(r'^\s*[\-\*]\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # Blockquotes
    text = re.sub(r'^>\s+(.+)$', r'<blockquote style="margin: 0; padding-left: 10px; border-left: 3px solid #ccc; color: #555;">\1</blockquote>', text, flags=re.MULTILINE)
    
    # Paragraph breaks
    text = text.replace('\n', '<br>')
    
    # Wrap multiple consecutive <li> in <ul> if needed, but Apple Notes accepts loose <li> tags easily.
    return text

def compile_and_sync(topic_name):
    safe_topic = re.sub(r'[^\w\s-]', '', topic_name).strip().replace(" ", "_").lower()
    workspace_dir = os.path.join(os.path.dirname(__file__), "..", "workspace", safe_topic)
    
    script_path = os.path.join(workspace_dir, "5_youtube_script.md")
    research_path = os.path.join(workspace_dir, "3_research_doc.md")
    storyboard_path = os.path.join(workspace_dir, "7_storyboard_and_prompts.md")
    
    if not (os.path.exists(script_path) and os.path.exists(research_path) and os.path.exists(storyboard_path)):
        print("❌ Error: ไม่พบไฟล์ผลผลิตหลักในโฟลเดอร์รันไทม์ กรุณารันท่อส่งงานก่อนนะแก")
        return False
        
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
    with open(research_path, "r", encoding="utf-8") as f:
        research_content = f.read()
    with open(storyboard_path, "r", encoding="utf-8") as f:
        storyboard_content = f.read()
        
    # Build a unified note
    unified_html = f"""
    <div>
        <h1>🎬 WTJ Story: {topic_name}</h1>
        <br>
        <hr>
        <h2>🔴 1. บทพูดวิดีโอ (YouTube Script)</h2>
        <br>
        {md_to_html(script_content)}
        <br>
        <hr>
        <h2>🎥 2. สตอรี่บอร์ด & สื่อจริง / AI Prompts</h2>
        <br>
        {md_to_html(storyboard_content)}
        <br>
        <hr>
        <h2>🔬 3. ข้อมูลรีเสิร์ชอ้างอิงและตัวอย่างฟุตเทจ</h2>
        <br>
        {md_to_html(research_content)}
    </div>
    """
    
    # Clean up excess line breaks in HTML representation
    unified_html = re.sub(r'(<br>\s*){3,}', '<br><br>', unified_html)
    
    # Escape for AppleScript
    escaped_title = f"WTJ Story: {topic_name}".replace('\\', '\\\\').replace('"', '\\"')
    escaped_body = unified_html.replace('\\', '\\\\').replace('"', '\\"')
    
    applescript = f"""
    tell application "Notes"
        try
            -- Ensure root folder "WTJ" exists
            if not (exists folder "WTJ") then
                make new folder with properties {{name:"WTJ"}}
            end if
            set rootFolder to folder "WTJ"
            
            -- Ensure "WTJ_Story" subfolder exists
            if not (exists folder "WTJ_Story" of rootFolder) then
                make new folder at rootFolder with properties {{name:"WTJ_Story"}}
            end if
            set storyFolder to folder "WTJ_Story" of rootFolder
            
            -- Create the unified note
            make new note at storyFolder with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
            return "Success"
        on error err
            return "Error: " & err
        end try
    end tell
    """
    
    print(f"🚀 กำลังส่งข้อมูลตอน '{topic_name}' เข้าสู่ Apple Notes...")
    try:
        proc = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        result = proc.stdout.strip()
        if result == "Success":
            print(f"🎉 สำเร็จแล้วแก! เปิดแอป Apple Notes ดูโน้ต 'WTJ Story: {topic_name}' ได้เลย!")
            return True
        else:
            print(f"❌ ล้มเหลวผ่าน AppleScript: {result}")
            return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดทางเทคนิค: {e}")
        return False

if __name__ == "__main__":
    topic = "Game Balancer"
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    compile_and_sync(topic)
