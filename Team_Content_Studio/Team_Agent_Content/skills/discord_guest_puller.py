#!/usr/bin/env python3
import os
import sys
import json
import re
import urllib.request
import urllib.parse
import ssl

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from notion_helper import NotionHelper
from discord_helper import DiscordHelper
import model_router

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_NAME = "ลิสรายชื่อแขกรับเชิญ-wtjpodcast"

# SSL Context bypass to prevent local certificate errors
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def make_discord_request(url, method="GET", data=None):
    if not BOT_TOKEN:
        print("❌ Error: ไม่พบ DISCORD_BOT_TOKEN ใน .env")
        return None
        
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "User-Agent": "WTJGuestPuller/1.0"
    }
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            if response.status == 204:
                return True
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Discord API request failed: {e}")
        return None

def find_target_channel():
    """Lists bot guilds and scans for the channel named target channel name."""
    print("🔍 กำลังดึงรายชื่อเซิร์ฟเวอร์ที่บอทอาศัยอยู่...")
    guilds = make_discord_request("https://discord.com/api/v10/users/@me/guilds")
    if not guilds:
        print("❌ ไม่พบเซิร์ฟเวอร์ใดๆ หรือบอทไม่มีสิทธิ์เข้าถึง")
        return None
        
    for guild in guilds:
        guild_id = guild["id"]
        guild_name = guild["name"]
        print(f"📡 ค้นหาห้องแชทในเซิร์ฟเวอร์: {guild_name} (ID: {guild_id})...")
        
        channels = make_discord_request(f"https://discord.com/api/v10/guilds/{guild_id}/channels")
        if not channels:
            continue
            
        for channel in channels:
            # We want text channels (type 0)
            if channel.get("type") == 0 and channel.get("name") == TARGET_CHANNEL_NAME:
                print(f"🎯 พบห้องเป้าหมาย! Channel Name: {channel['name']} (ID: {channel['id']})")
                return channel["id"]
    return None

def get_channel_messages(channel_id):
    """Retrieves last 100 messages from the channel."""
    print("📖 กำลังดึงประวัติข้อความในห้องแชท...")
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"
    messages = make_discord_request(url)
    if not messages:
        return []
    
    # Filter only messages with content and reverse to chronological order
    valid_msgs = [msg for msg in messages if msg.get("content")]
    valid_msgs.reverse()
    return valid_msgs

def extract_guests_from_chat(chat_content):
    """Uses Gemini to parse chat messages and extract guest lists as JSON."""
    print("🧠 ส่งประวัติแชทให้ AI (น้ำ & เรย์) วิเคราะห์และสกัดรายชื่อแขกรับเชิญ...")
    
    system_instruction = """
คุณคือเลขาอัจฉริยะของช่อง "What the job ?" 
หน้าที่ของคุณคือ: อ่านประวัติการคุยในแชท Discord และสกัดรายชื่อ "แขกรับเชิญ" พร้อมกับ "อาชีพ" หรือ "สายงาน" ของเขาออกมา
กรุณาทำตามกฎดังนี้:
1. วิเคราะห์หาชื่อคนและอาชีพอย่างเป็นธรรมชาติ เช่น "กอล์ฟ - Sport Influencer" หรือ "น้องบิ๊ก - นักพัฒนาบอร์ดเกม"
2. คืนค่าผลลัพธ์เป็นโครงสร้าง JSON Array ของวัตถุที่มีคีย์ 'name' และ 'occupation' เท่านั้น
3. ห้ามพิมพ์อธิบาย ห้ามทักทาย หรือมีตัวหนังสืออื่นนอกเหนือจาก JSON เด็ดขาด!

ตัวอย่างผลลัพธ์ที่ถูกต้อง:
[
  {"name": "กอล์ฟ", "occupation": "Sport Influencer"},
  {"name": "บิ๊ก", "occupation": "นักพัฒนาบอร์ดเกม"}
]
"""
    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"นี่คือข้อความประวัติแชทดิสคอร์ด โปรดสกัดรายชื่อออกมาตามรูปแบบ JSON:\n\n{chat_content}"
    
    response = model.generate_content(prompt)
    response_text = response.text.strip()
    
    # Extract JSON block using regex if AI wrapped it in markdown code block
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1).strip()
        
    try:
        guests = json.loads(response_text)
        if isinstance(guests, list):
            return guests
    except Exception as e:
        print(f"❌ ล้มเหลวในการแปลง JSON จาก AI: {e}")
        print(f"Raw AI Output: {response.text}")
        
    return []

def generate_guest_social_posts(guest_name, occupation):
    """Calls Gemini to write Thursday and Sunday drafts based only on Guest name and Occupation."""
    print(f"✍️ กำลังให้ทีมงานเขียนร่างโพสต์ชวนคุยและคำคมสำหรับแขก: **{guest_name} ({occupation})**...")
    
    system_instruction = f"""
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น), "มิวสิค" (Marketer สาววัยรุ่น) และ "เรย์" (Writer มือเจียระไน)
หน้าที่ของคุณคือ: เขียนร่างโพสต์ Facebook 2 สไตล์ (วันพฤหัสบดี ชวนคุย/โพล และวันอาทิตย์ คำคม/แง่คิดดึงใจ) สำหรับแนะนำหรือเกี่ยวกับอาชีพของแขกรับเชิญคนนี้ล่วงหน้า

ข้อมูลแขกรับเชิญ:
ชื่อ: {guest_name}
อาชีพ/สายงาน: {occupation}

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):
1. เขียนออกมาเป็น 2 บล็อก (วันพฤหัสบดี และวันอาทิตย์) โดยแต่ละบล็อกมี 3 ทางเลือก (3 Options)
2. ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ในโควทจริงของแขกได้)
3. ใช้สรรพนามสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)
4. จัดเว้นวรรคและจัดบรรทัดให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว

รูปแบบคำตอบ EXACT:

[THURSDAY_POSTS]
ทางเลือกที่ 1:
[คำถามชวนคิดหรือแบบสอบถามโพล ชวนลูกเพจคอมเมนต์คุยแลกเปลี่ยนประเด็นของอาชีพ {occupation} ความยาว 2-5 บรรทัด ไม่ต้องขึ้นด้วย "เมื่อ..." และไม่ต้องปิดด้วยคอมเมนต์ปักหมุด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #{occupation.replace(' ', '')} #คำถามชวนคิด]

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก)

[SUNDAY_POSTS]
ทางเลือกที่ 1:
[คำโควทสไตล์ข้อคิดดึงใจที่เกี่ยวกับทัศนคติ/ความจริงใจในงานของอาชีพ {occupation} (จินตนาการโควทเด็ดขึ้นมาได้เลย) ตามด้วยแง่คิดอธิบายกระตุกต่อมคิด 3-6 บรรทัด ไม่ต้องขึ้นด้วย "เมื่อ..." และไม่ต้องปิดด้วยคอมเมนต์ปักหมุด]
[แฮชแท็ก 2-4 อัน เช่น #WhatTheJob #{occupation.replace(' ', '')} #คำคมดึงใจ #ข้อคิดคนทำงาน]

ทางเลือกที่ 2:
... (ร่างให้ครบ 3 ทางเลือก)
"""
    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"เขียนโพสต์พฤหัสบดีชวนคุย และอาทิตย์คำคมสำหรับอาชีพ {occupation} หน่อยแก"
    response = model.generate_content(prompt)
    return response.text

def main():
    print("==================================================")
    print("🦉 เลขาเฟิส: ระบบเชื่อมท่อดูดรายชื่อแขก Discord ➡️ Notion 🚀")
    print("==================================================\n")
    
    if not BOT_TOKEN:
        print("❌ Error: กรุณาใส่ DISCORD_BOT_TOKEN ในไฟล์ .env ของคุณเก่งก่อนนะแก")
        return
        
    # 1. ค้นหาไอดีห้อง
    channel_id = find_target_channel()
    if not channel_id:
        print(f"❌ ล้มเหลว: ไม่พบห้องแชทชื่อ '{TARGET_CHANNEL_NAME}' ในทุกกิลด์ของบอทเลยแก!")
        return
        
    # 2. ดึงข้อความแชท
    messages = get_channel_messages(channel_id)
    if not messages:
        print("📭 ไม่พบข้อความในแชทเลยแก!")
        return
        
    print(f"📖 ดึงสำเร็จทั้งหมด {len(messages)} ข้อความแชท")
    
    # ประกอบข้อความเพื่อส่งให้ AI วิเคราะห์
    chat_lines = []
    for msg in messages:
        user = msg.get("author", {}).get("username", "Unknown")
        content = msg.get("content", "").strip()
        chat_lines.append(f"{user}: {content}")
    chat_content = "\n".join(chat_lines)
    
    # 3. ให้ AI แกะรายชื่อ
    guests = extract_guests_from_chat(chat_content)
    if not guests:
        print("📭 ไม่สามารถแกะรายชื่อคนสัมภาษณ์ที่มีประโยชน์ได้เลยแก!")
        return
        
    print(f"📌 สกัดรายชื่อแขกที่ได้ยินในแชทสำเร็จ: {len(guests)} รายการ")
    for g in guests:
        print(f"   - {g.get('name')} | อาชีพ: {g.get('occupation')}")
        
    # 4. ดึงหัวข้อที่มีใน Notion แล้วเพื่อทำการกรองข้าม (Cross-reference)
    notion = NotionHelper()
    print("\n🔍 โหลดหัวข้อที่มีใน Notion เพื่อสแกนหาตัวซ้ำ...")
    existing_pages = notion.query_database()
    existing_titles = []
    title_prop_name = notion.get_title_property_name()
    
    if existing_pages and "results" in existing_pages:
        for page in existing_pages["results"]:
            props = page["properties"]
            name_prop = props.get(title_prop_name, {})
            if name_prop.get("type") == "title" and name_prop.get("title"):
                title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
                existing_titles.append(title.lower())
                
    # 5. รันลูปดราฟต์และบันทึกโพสต์สำหรับคนใหม่
    new_guests_drafted = 0
    
    for guest in guests:
        name = guest.get("name", "").strip()
        occupation = guest.get("occupation", "").strip()
        
        if not name or not occupation:
            continue
            
        # ตรวจสอบว่าเคยเขียนโพสต์หรือทำการ์ดของแขกคนนี้ไว้แล้วหรือยัง
        # เช็คว่ามีชื่อของแขกคนนี้อยู่ใน Title การ์ดที่มีอยู่แล้วใน Notion หรือไม่
        name_lower = name.lower()
        already_exists = False
        for ext_title in existing_titles:
            if name_lower in ext_title:
                already_exists = True
                break
                
        if already_exists:
            print(f"⏭️ ข้าม: แขกชื่อ '{name}' อาชีพ '{occupation}' มีการ์ดใน Notion อยู่แล้วแก!")
            continue
            
        print(f"\n🌟 เริ่มปั้นดราฟต์สำหรับแขกใหม่: '{name}' ({occupation})")
        
        # 6. ร่างโพสต์พฤหัส (ชวนคุย) และ อาทิตย์ (คำคม)
        generated_text = generate_guest_social_posts(name, occupation)
        if not generated_text:
            print("❌ ล้มเหลวในการผลิตเนื้อหาดราฟต์")
            continue
            
        thu_content = ""
        sun_content = ""
        
        thu_match = re.search(r'\[THURSDAY_POSTS\](.*?)(\[SUNDAY_POSTS\]|$)', generated_text, re.DOTALL | re.IGNORECASE)
        sun_match = re.search(r'\[SUNDAY_POSTS\](.*)', generated_text, re.DOTALL | re.IGNORECASE)
        
        if thu_match:
            thu_content = thu_match.group(1).strip()
        if sun_match:
            sun_content = sun_match.group(1).strip()
            
        if not thu_content:
            thu_content = generated_text
        if not sun_content:
            sun_content = generated_text
            
        # 7. สร้างการ์ดพฤหัส (THU) ใน Notion
        thu_title = f"[THU_Text] {name} - {occupation}"
        print(f"🚀 สร้างการ์ดวันพฤหัสบดี: '{thu_title}'...")
        new_page_thu = notion.create_page(thu_title, status_name="4_Review", platform_tags=["FB_Text_Quote"])
        if new_page_thu and "id" in new_page_thu:
            page_id_thu = new_page_thu["id"]
            # เขียน 3 options ลงการ์ดพฤหัส
            mock_transcript_info = f"ดราฟต์ข้อความชวนคุยล่วงหน้าเกี่ยวกับอาชีพ: {occupation} ของแขกรับเชิญ '{name}'\n(ดึงข้อมูลมาจาก Discord แชทหลัก)"
            notion.write_page_content_text(page_id_thu, mock_transcript_info + "\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + thu_content)
            print("✅ สร้างการ์ดพฤหัสบดีใน Notion สำเร็จ!")
        else:
            print("❌ ไม่สามารถสร้างการ์ดพฤหัสบดีได้")
            
        # 8. สร้างการ์ดอาทิตย์ (SUN) ใน Notion
        sun_title = f"[SUN_Text] {name} - {occupation}"
        print(f"🚀 สร้างการ์ดวันอาทิตย์: '{sun_title}'...")
        new_page_sun = notion.create_page(sun_title, status_name="4_Review", platform_tags=["FB_Text_Quote"])
        if new_page_sun and "id" in new_page_sun:
            page_id_sun = new_page_sun["id"]
            # เขียน 3 options ลงการ์ดอาทิตย์
            mock_transcript_info = f"ดราฟต์คำคมดีๆ ล่วงหน้าเกี่ยวกับอาชีพ: {occupation} ของแขกรับเชิญ '{name}'\n(ดึงข้อมูลมาจาก Discord แชทหลัก)"
            notion.write_page_content_text(page_id_sun, mock_transcript_info + "\n\n---\n\n## 📝 Draft Options (โดย ทีม Content Agent)\n\n" + sun_content)
            print("✅ สร้างการ์ดวันอาทิตย์ใน Notion สำเร็จ!")
        else:
            print("❌ ไม่สามารถสร้างการ์ดวันอาทิตย์ได้")
            
        # Local Backups
        clean_name = re.sub(r'[^\w\s]', '', name).strip().replace(" ", "_").lower()
        drafts_dir = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "workspace", "2_drafts")
        os.makedirs(drafts_dir, exist_ok=True)
        
        backup_path_thu = os.path.join(drafts_dir, f"text_posts_thu_discord_{clean_name}.md")
        with open(backup_path_thu, "w", encoding="utf-8") as f:
            f.write(thu_content)
            
        backup_path_sun = os.path.join(drafts_dir, f"text_posts_sun_discord_{clean_name}.md")
        with open(backup_path_sun, "w", encoding="utf-8") as f:
            f.write(sun_content)
        print(f"💾 บันทึกไฟล์ร่างสำรอง THU และ SUN ในเครื่องเรียบร้อย!")
        
        # ส่งแจ้งเตือน Discord Webhook แจ้งความคืบหน้า
        discord = DiscordHelper()
        discord.send_success(
            "ดูดแชทปั้นโพสต์ล่วงหน้าสำเร็จ!",
            f"**พบแขกสัมภาษณ์ใหม่ใน Discord:** {name} ({occupation})\n🔄 *ได้สร้างการ์ด `[THU_Text]` และ `[SUN_Text]` ใน Notion รอแกตรวจให้เรียบร้อยจ้า!*"
        )
        
        new_guests_drafted += 1
        
    print("\n" + "=" * 50)
    print(f"🎉 เสร็จสิ้น! ปั้นดราฟต์สำหรับแขกสัมภาษณ์ใหม่สำเร็จทั้งหมด {new_guests_drafted} คนจ้า! 🦉🤘✨")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
