import re

file_path = "/Users/chz/Desktop/ChZ_Agent_Corp/WTJ_Content_Studio/Team_Agent_Content/skills/fb_draft_generator.py"

# Read file with replace to avoid crash
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Replace any replacement characters (EF BF BD) that represent corrupt bytes
content = content.replace("", "")

# We want to replace the generate_social_posts function cleanly.
# Let's locate the start of generate_social_posts and the start of run_draft_pipeline.
start_idx = content.find("def generate_social_posts")
end_idx = content.find("def run_draft_pipeline")

if start_idx == -1 or end_idx == -1:
    print("❌ Error: Could not locate function boundaries.")
    exit(1)

new_function = """def generate_social_posts(transcript_title, transcript_content):
    print("🧠 [Skill Generation] ส่งทรานสคริปต์ตอนย่อยให้เอเจนต์ (น้ำ, มิวสิค, เรย์) ร่วมกันปั้นโพสต์ระดับพรีเมียม...")
    
    system_instruction = f\"\"\"
คุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น คิดคอนเซปต์สุดล้ำ), "มิวสิค" (Marketer สาววัยรุ่น ปั้นมีมและแคมเปญสุดจึ้ง) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: นำข้อความถอดเทปสัมภาษณ์ตอนย่อย (Sub-clip Transcript) หัวข้อ: "{transcript_title}" มาเขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่จึ้งและแตกต่างกัน เพื่อให้พี่เก่งได้เลือกอันที่ชอบที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์ทรานสคริปต์นี้ว่าเหมาะจะจัดเข้าคิวใดจาก 3 คิวนี้มากที่สุด:
   - `FB_Videos_3-5Min` (หากเป็นคลิปยาวปานกลาง เล่าเรื่อง มีสาระรายละเอียด)
   - `Reels_Under1Min` (หากเป็นคลิปสั้นแนว Reels/Shorts ตื่นเต้น หักมุม กระชับ มี Hook เด่นๆ)
   - `Text_Posts` (หากเป็นข้อความโควทคำคม หรือประเด็นชวนคุยที่เหมาะสำหรับโพสต์ข้อความถามแฟนเพจ)
2. เขียนระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: `[QUEUE: ชื่อคิว]` (เช่น `[QUEUE: Reels_Under1Min]`)
3. ร่างโพสต์มาทั้งหมด 3 ทางเลือก (3 Options) ที่เน้นมุมมองที่แตกต่างกันอย่างสิ้นเชิง

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):
- ห้ามมีคำเกริ่นนำหรือแนะนำตัวในนามทีมงานเด็ดขาด (ห้ามพูดว่า "วันนี้พวกเราทีมงาน..." หรือคำทักทายลักษณะนี้)
- ทุกทางเลือก (ทั้ง 3 Options) บรรทัดแรกสุดของเนื้อหาโพสต์ต้องขึ้นต้นด้วยคำว่า "เมื่อ..." เสนอเป็นสถานการณ์ขำๆ หรือประเด็นพีค (เช่น "เมื่อ...") ตามสไตล์ตลก 6 ฉาก
- รูปแบบเนื้อหา: บรรทัด "เมื่อ..." + โควทบทสนทนาจริงหรือโควทคำพูดเด็ดของแขกรับเชิญหรือพี่เก่ง 1-2 บรรทัด (เช่น บทสนทนาโต้ตอบกันธรรมชาติ)
- ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นหรือหยอดคำโต้ตอบกันธรรมชาติ
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในเนื้อหาโพสต์ปกติ (สามารถใช้ได้เฉพาะในบทสนทนาจริงของแขกรับเชิญ)
- ใช้สรรพนามสไตล์เพื่อนสนิทกึ่งทางการ วัยรุ่นเป็นกันเอง (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, โฮ่งมาก, แบบตะโกน, เกินต้าน)
- ปรับข้อความ CTA ให้สั้นกระชับที่สุด ปิดท้ายด้วยประโยคว่า: "ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก" เท่านั้น
- สำหรับ Reels (Reels_Under1Min) ให้เขียนข้อความโพสต์ Facebook ในแนวทางสั้นกระชับเช่นเดียวกัน โดยแบ่งเป็น 3 ทางเลือก

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
\"\"\"
    model = model_router.get_model("ray", system_instruction=system_instruction)
    prompt = f"โปรดอ่านข้อความถอดเทปย่อยนี้ และช่วยเลือกคิวพร้อมร่างโพสต์ 3 ทางเลือกให้หน่อยแก:\\n\\n{transcript_content}"
    response = model.generate_content(prompt)
    return response.text

"""

updated_content = content[:start_idx] + new_function + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(updated_content)

print("✅ Successfully repaired fb_draft_generator.py!")
