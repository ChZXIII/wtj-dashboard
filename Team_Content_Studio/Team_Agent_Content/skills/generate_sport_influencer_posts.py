import os
import re
import subprocess
import google.generativeai as genai

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)


def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val.replace('"', '').replace("'", "")

load_env()

# Import model router
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
import model_router

def read_transcript(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def generate_social_posts(transcript_content):
    print("🧠 กำลังเรียกใช้งานทีมเอเจนต์ (น้ำ & เรย์) เพื่อปั้นคอนเทนต์พรีเมียม...")
    
    system_instruction = """
คุณคือทีมงานเบื้องหลังของ "What the job ?" นำโดย "น้ำ" (Creative จอมปั้น Hook) และ "เรย์" (Scriptwriter ฝีมือฉกาจ) 
หน้าที่ของคุณคือ: นำข้อความถอดเทปสัมภาษณ์ (Transcript) ของ "น้องกอล์ฟ (Sport Influencer)" มาเขียนโพสต์ Facebook 3 รูปแบบที่แตกต่างกันอย่างสิ้นเชิงเพื่อทดสอบระบบ Sandbox สัปดาห์นี้

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):
1. ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาโพสต์ปกติเด็ดขาด! (สามารถใช้ได้เฉพาะในประโยคคำพูดอ้างอิงของแขกรับเชิญเท่านั้น)
2. ใช้ภาษาเป็นกันเองสไตล์เพื่อนซี้วัยรุ่น (แก/ชั้น, จ้า, นะจ๊ะ, ปัง, ตัวแม่) เพื่อความลื่นไหลและเข้าถึงง่าย
3. เกริ่นนำในนามทีมงานเสมอ เช่น "วันนี้พวกเราทีมงาน What the job ได้ชวน..." หรือ "วันนี้ทางเราทีมงาน What the job ได้นั่งเม้าท์มอยกับ..."
4. แนะนำแขกรับเชิญด้วยชื่อเล่นภาษาไทยและมีวงเล็บวงการ/แบรนด์กำกับเสมอ: "น้องกอล์ฟ (Sport Influencer / เจ้าของแบรนด์ Brom TR)"
5. สำหรับโพสต์ Teaser ให้เรียก YouTube ว่า "บ้านแดง" และบอกให้แฟนๆ ตามไปกด "ลิ้งใต้คอมเม้น" เสมอ
6. เว้นวรรคและจัดบรรทัดให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามยาวติดกันเป็นแพ็ก

กรุณาเขียนให้ครบทั้ง 3 โพสต์ดังนี้:

---

### [POST_1: WED_Teaser]
(โพสต์สำหรับห้อง WED_Teaser -> 1_Drafts)
- **ประเภท:** Teaser / Q&A (กั๊กประเด็นชวนสงสัยให้คนอยากดูคลิปวันพฤหัสบดี)
- **โครงสร้าง:**
  * Hook เปิดเรื่อง: รูปแบบ `[หัวข้อหลัก] - [คำถามชวนคิด]?` (เช่น "อาชีพ Sport Influencer - ทำงาน 7 วัน ปั่นจักรยาน วิ่งดอยสุเทพจนไวรัล แต่เบื้องหลังรันธุรกิจกาแฟสัปดาห์ละ 5 วัน? 🚴‍♀️☕️")
  * Intro ในนามทีมงาน แนะนำน้องกอล์ฟ
  * Body: เล่าสตอรี่ความพีค 2-3 จุดแบบกั๊กข้อมูล (เช่น เรื่องเปลี่ยนชื่อบ่อยตามหมอดูจนจำชื่อเก่าแทบไม่ได้, ความบังเอิญรถเสียที่เชียงใหม่จนได้วิ่งดอยสุเทพขึ้นแท่นนางฟ้านักวิ่ง, หรือเคล็ดลับฟิตหุ่นที่อาหารคุมถึง 80%)
  * Outro + CTA: สปอยล์ว่าพรุ่งนี้ห้ามพลาดคลิปเต็มที่บ้านแดง ลิ้งปักหมุดไว้ใต้คอมเม้นนะจ๊ะ!

---

### [POST_2: FRI_Quote]
(โพสต์สำหรับห้อง FRI_Quote -> 1_Drafts)
- **ประเภท:** Quote / Insight (ขยี้ประเด็นคำคมและวิธีคิดการสู้ชีวิต)
- **โครงสร้าง:**
  * Hook เปิดเรื่อง: โควทเด็ดตัวใหญ่กระแทกตา เช่น "ว่าจ้างได้ ชอบทำงานค่ะ!" หรือ "อาหาร 80% ออกกำลังกาย 20% หุ่นดีสร้างได้จากจานข้าว!"
  * Intro นำเสนอคำคมของน้องกอล์ฟ
  * Body: อธิบายแนวคิดเบื้องหลังความฟิตและความสนุกในการทำงานของเธอ การรับมือกับวิกฤตโควิดด้วยกาแฟ Cold Brew "BL FA" จนกำลังจะเปิดหน้าร้านใหม่ "Everything Blue" ที่ตึก Thai Summit
  * Outro: ชวนลูกเพจคอมเมนต์แชร์ความคิดเห็น

---

### [POST_3: SAT_Reels]
(โพสต์สำหรับห้อง SAT_Reels -> 1_Drafts)
- **ประเภท:** 1-Minute Reels / Shorts Video Script (สคริปต์สั้นสำหรับให้พี่เก่งก๊อปไปลงหรือนำไปอัดคลิปพูดเร็วๆ สะใจวัยรุ่น)
- **โครงสร้าง:**
  * เขียนแบ่งเป็นช่องชัดเจน:
    - 🎣 **HOOK (0-10s):** คำพูดกระชากใจเปิดตัว
    - 🎥 **VISUAL CUE:** แนะนำฉากประกอบที่พี่เก่งต้องทำ/แสดง
    - 🗣️ **NARRATION:** บทพูดจริงของพี่เก่ง (สไตล์เป็นกันเอง กระฉับกระเฉง รวดเร็ว สะใจ)
    - 🏁 **CTA:** ชวนดูคลิปสัมภาษณ์ตัวเต็มที่บ้านแดง ลิ้งในคอมเม้นเล้ย!

โปรดเขียนผลลัพธ์แยกตามบล็อก [POST_1], [POST_2], [POST_3] เพื่อให้สคริปต์สกัดนำไปบันทึกลง Apple Notes ได้ง่ายดาย
"""

    model = model_router.get_model("ray", system_instruction=system_instruction)
    
    prompt = f"โปรดอ่านข้อมูล Transcript ด้านล่างนี้ และเขียนโซเชียลโพสต์ทั้ง 3 วันให้จึ้งและเป๊ะตามคู่มือการทำงานของเรย์:\n\n{transcript_content}"
    response = model.generate_content(prompt)
    return response.text

def create_apple_note(day_folder, title, body_content):
    # Prepare HTML body for Apple Notes (preserves whitespace and formatting)
    body_html = f"<div><b>{title}</b><br><br>" + body_content.replace("\n", "<br>") + "</div>"
    
    # Escape for AppleScript double-quoted string
    escaped_title = title.replace('\\', '\\\\').replace('"', '\\"')
    escaped_body = body_html.replace('\\', '\\\\').replace('"', '\\"')
    
    # AppleScript execution
    applescript = f"""
    tell application "Notes"
        try
            set rootFolder to folder "WTJ"
            set fbFolder to folder "Facebook" of rootFolder
            set dayFolder to folder "{day_folder}" of fbFolder
            set draftsFolder to folder "1_Drafts" of dayFolder
            
            make new note at draftsFolder with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
            return "Success"
        on error err
            return "Error: " & err
        end try
    end tell
    """
    
    try:
        proc = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        return proc.stdout.strip()
    except Exception as e:
        return f"Error running AppleScript: {e}"

if __name__ == "__main__":
    transcript_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "1_raw_materials", "transcript_Sport_Influencer.md")
    
    if not os.path.exists(transcript_path):
        print(f"Error: ไม่พบไฟล์ Transcript ในเส้นทาง {transcript_path}")
        exit(1)
        
    transcript = read_transcript(transcript_path)
    output = generate_social_posts(transcript)
    
    # Extract individual posts using Regex or splitting
    # Splitting by [POST_X] headers
    post_blocks = re.split(r'###\s*\[POST_\d+:\s*\w+\]', output)
    
    if len(post_blocks) < 4:
        # Fallback if splitting fails due to formatting, search for POST_1, POST_2, POST_3
        post_blocks = re.split(r'\[POST_\d+[^\]]*\]', output)
        
    print("\n--- 📝 ผลลัพธ์โพสต์ที่สร้างขึ้นโดยเรย์ ---")
    print(output)
    print("----------------------------------------\n")
    
    # Clean up split blocks (removing trailing markdown markers)
    # Block 1 is introduction text before POST_1
    p1_content = post_blocks[1].strip() if len(post_blocks) > 1 else ""
    p2_content = post_blocks[2].strip() if len(post_blocks) > 2 else ""
    p3_content = post_blocks[3].strip() if len(post_blocks) > 3 else ""
    
    # Write to local drafts first
    drafts_dir = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")
    os.makedirs(drafts_dir, exist_ok=True)
    
    with open(f"{drafts_dir}/wed_teaser_draft.md", "w", encoding="utf-8") as f:
        f.write(p1_content)
    with open(f"{drafts_dir}/fri_quote_draft.md", "w", encoding="utf-8") as f:
        f.write(p2_content)
    with open(f"{drafts_dir}/sat_reels_draft.md", "w", encoding="utf-8") as f:
        f.write(p3_content)
        
    print("💾 บันทึกไฟล์ร่างลง workspace/2_drafts/ เรียบร้อยแล้ว!")
    
    # Write to Apple Notes
    print("\n🚀 กำลังยิงดราฟต์สคริปต์เข้า Apple Notes ของพี่เก่ง...")
    
    res1 = create_apple_note("WED_Teaser", "WED_Teaser: สปอยล์น้องกอล์ฟ Sport Influencer", p1_content)
    print(f"- WED_Teaser (วันพุธ): {res1}")
    
    res2 = create_apple_note("FRI_Quote", "FRI_Quote: โควทน้องกอล์ฟ Sport Influencer", p2_content)
    print(f"- FRI_Quote (วันศุกร์): {res2}")
    
    res3 = create_apple_note("SAT_Reels", "SAT_Reels: บท Reels/Shorts น้องกอล์ฟ", p3_content)
    print(f"- SAT_Reels (วันเสาร์): {res3}")
    
    print("\n🎉 จัดเตรียมสคริปต์และส่งขึ้น Apple Notes ทุกซับโฟลเดอร์เรียบร้อยแล้วแก!")
