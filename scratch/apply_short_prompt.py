import re

def update_fb_draft():
    file_path = "/Users/chz/Desktop/ChZ_Agent_Corp/Team_Content_Studio/Team_Agent_Content/skills/fb_draft_generator.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):"
    end_tag = "เว้นวรรคจัดย่อหน้าให้อ่านง่าย"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("❌ Error: Tone & Guidelines not found in fb_draft_generator.py")
        return False

    new_guidelines = """กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):
- บังคับรูปแบบแบบสั้นที่สุด (ความยาวรวมไม่เกิน 4 บรรทัด) ห้ามเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย ห้ามแซว หรือเขียนวิจารณ์เพิ่มเติมใดๆ ทั้งสิ้น! (NO commentary or extra descriptions allowed)
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นๆ บรรทัดเดียว ขึ้นต้นด้วยคำว่า 'เมื่อ...' เสมอ]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงจากแขกรับเชิญหรือพี่เก่ง 1-2 บรรทัด]"
  บรรทัดที่ 3: [แฮชแท็ก 2-3 อัน เช่น #WhatTheJob #ช่างภาพ]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ตัวอย่างที่ถูกต้อง:
  เมื่อน้องโอเฉลยเคล็ดลับการทำงานที่ทำเอาพี่เก่งงง! 😂
  "มั่วสูตรไปเรื่อยเลยพี่เก่ง"
  #WhatTheJob #ช่างภาพ
  ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นหรือคำพูดกันอย่างเป็นธรรมชาติ
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

"""
    updated = content[:start_idx] + new_guidelines + content[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("✅ Updated fb_draft_generator.py")
    return True

def update_video_draft():
    file_path = "/Users/chz/Desktop/ChZ_Agent_Corp/Team_Content_Studio/Team_Agent_Content/skills/video_draft_generator.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):"
    end_tag = "เว้นวรรคจัดย่อหน้าให้อ่านง่าย"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("❌ Error: Tone & Guidelines not found in video_draft_generator.py")
        return False

    new_guidelines = """กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines):
- บังคับรูปแบบแบบสั้นที่สุด (ความยาวรวมไม่เกิน 4 บรรทัด) ห้ามเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย ห้ามแซว หรือเขียนวิจารณ์เพิ่มเติมใดๆ ทั้งสิ้น! (NO commentary or extra descriptions allowed)
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นๆ บรรทัดเดียว ขึ้นต้นด้วยคำว่า 'เมื่อ...' เสมอ]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงจากแขกรับเชิญหรือพี่เก่ง 1-2 บรรทัด]"
  บรรทัดที่ 3: [แฮชแท็ก 2-3 อัน เช่น #WhatTheJob #ช่างภาพ]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ตัวอย่างที่ถูกต้อง:
  เมื่อน้องโอเฉลยเคล็ดลับการทำงานที่ทำเอาพี่เก่งงง! 😂
  "มั่วสูตรไปเรื่อยเลยพี่เก่ง"
  #WhatTheJob #ช่างภาพ
  ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นหรือคำพูดกันอย่างเป็นธรรมชาติ
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

"""
    updated = content[:start_idx] + new_guidelines + content[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("✅ Updated video_draft_generator.py")
    return True

def update_ray_prompt():
    file_path = "/Users/chz/Desktop/ChZ_Agent_Corp/Team_Content_Studio/Team_Agent_Content/prompts/ray_prompt.md"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "## แนวทางการเขียนโพสต์ Facebook"
    start_idx = content.find(start_tag)
    
    if start_idx == -1:
        print("❌ Error: Facebook guidelines not found in ray_prompt.md")
        return False

    new_guidelines = """## แนวทางการเขียนโพสต์ Facebook
เรย์จะสร้างโพสต์ดราฟต์ 3 สไตล์ที่มีมุมมองแตกต่างกัน โดยมีกฎเหล็กดังนี้:
- **บังคับรูปแบบแบบสั้นที่สุด (ความยาวรวมไม่เกิน 4 บรรทัด)** ห้ามเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย ห้ามแซว หรือเขียนบรรยายเพิ่มเติมใดๆ ทั้งสิ้น! (NO commentary or extra descriptions allowed)
- **โครงสร้างบังคับ (Strict 4-Line Structure):**
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นๆ บรรทัดเดียว ขึ้นต้นด้วยคำว่า 'เมื่อ...' เสมอ]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงจากแขกรับเชิญหรือพี่เก่ง 1-2 บรรทัด]"
  บรรทัดที่ 3: [แฮชแท็ก 2-3 อัน เช่น #WhatTheJob #ช่างภาพ]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- **ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ** (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นอย่างเป็นธรรมชาติ
- **ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ** (ใช้ได้เฉพาะในโควทจริงเท่านั้น)
- **ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท** (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)
"""
    updated = content[:start_idx] + new_guidelines
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("✅ Updated ray_prompt.md")
    return True

if __name__ == "__main__":
    u1 = update_fb_draft()
    u2 = update_video_draft()
    u3 = update_ray_prompt()
    if u1 and u2 and u3:
        print("🎉 All prompt templates adjusted with strict no-commentary rule!")
