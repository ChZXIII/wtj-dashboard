import os
import sys
import re
import dotenv

# Determine project root and add to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# Add WTJ Story Project to sys.path to import status_logger
wtj_path = os.path.join(project_root, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project")
if wtj_path not in sys.path:
    sys.path.append(wtj_path)

import model_router
import status_logger

# Load environment variables
dotenv.load_dotenv(os.path.join(project_root, ".env"))

# Prompts Directory
PROMPTS_DIR = os.path.join(project_root, "WTJ_Content_Studio", "Team_Agent_Content", "prompts")

def load_prompt(filename):
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# Load agent prompts
deer_prompt = load_prompt("deer_prompt.md")
creative_prompt = load_prompt("creative_prompt.md")
music_prompt = load_prompt("music_prompt.md")
researcher_prompt = load_prompt("researcher_prompt.md")
or_prompt = load_prompt("or_prompt.md")
ray_prompt = load_prompt("ray_prompt.md")
cri_prompt = load_prompt("cri_prompt.md")
director_prompt = load_prompt("director_prompt.md")

# Load Antigravity Documentation for researcher context
sdk_doc_path = os.path.join(project_root, ".gemini", "antigravity", "brain", "a46a20cf-82f4-423d-b272-0616cab44781", "implementation_plan.md") # Fallback or main docs
# Let's locate the SKILL.md for google-antigravity-sdk
skill_doc_path = "/Users/chz/.gemini/config/plugins/google-antigravity-sdk/skills/google-antigravity-sdk/SKILL.md"
sdk_content = ""
if os.path.exists(skill_doc_path):
    with open(skill_doc_path, "r", encoding="utf-8") as f:
        sdk_content = f.read()
        
# Add architectural reference to research prompt
researcher_instruction = f"""{researcher_prompt}

---
นี่คือข้อมูลทางเทคนิคของ Google Antigravity SDK ที่คุณสามารถใช้อ้างอิงเพื่อตรวจสอบความถูกต้องของโค้ดและการทำงาน:
{sdk_content}
"""

# Initialize models
deer_model = model_router.get_model("deer", system_instruction=deer_prompt)
creative_model = model_router.get_model("creative", system_instruction=creative_prompt)
music_model = model_router.get_model("music", system_instruction=music_prompt)
researcher_model = model_router.get_model("researcher", system_instruction=researcher_instruction)
or_model = model_router.get_model("or", system_instruction=or_prompt)
ray_model = model_router.get_model("ray", system_instruction=ray_prompt)
cri_model = model_router.get_model("cri", system_instruction=cri_prompt)

def process_course_outline(outline_file):
    if not os.path.exists(outline_file):
        print(f"Error: ไม่พบไฟล์โครงร่างคอร์สที่ {outline_file}")
        return
        
    with open(outline_file, "r", encoding="utf-8") as f:
        outline_content = f.read()
        
    # Extract lesson title
    title_match = re.search(r'Lesson Title:\s*(.*)', outline_content)
    lesson_title = title_match.group(1).strip() if title_match else "lesson_draft"
    safe_title = re.sub(r'[^\w\s-]', '', lesson_title).strip().replace(" ", "_").lower()
    
    # 1. Deer (Idea Card)
    print("\n[1/6] 🦌 เดียร์ (Idea Card): กำลังวิเคราะห์โครงสร้างหลักสูตรและจัดลำดับเนื้อหา...")
    status_logger.update_pipeline_status(
        "deer",
        "เดียร์กำลังร่างโครงสร้างบทเรียน...",
        f"รับบทเรียน '{lesson_title}' ส่งต่อให้ น้องเดียร์ เพื่อทำ Idea Card",
        clear_logs=True
    )
    
    try:
        deer_prompt_msg = f"โปรดสร้าง Idea Card และรูปแบบการสอนสำหรับบทเรียนนี้:\n\n{outline_content}"
        deer_res = deer_model.generate_content(deer_prompt_msg)
        idea_card = deer_res.text
        
        # Save draft
        with open(os.path.join(current_dir, "workspace", "2_drafts", f"1_idea_card_{safe_title}.md"), "w", encoding="utf-8") as f:
            f.write(idea_card)
        print("✅ ร่าง Idea Card สำเร็จ")
    except Exception as e:
        status_logger.update_pipeline_status("deer", "เดียร์เกิดข้อผิดพลาด", f"Error: {e}")
        print(f"Error in Deer: {e}")
        return

    # 2. Nam (Creative Concept) & Music (Marketing/Hooks)
    print("[2/6] 💅 คอนเทนต์ & การตลาด (น้ำ & มิวสิค): กำลังปรับแต่งสำนวน เพิ่มตัวอย่างเปรียบเทียบ และลูกเล่นให้สนุกสนาน...")
    status_logger.update_pipeline_status(
        "creative",
        "น้ำและมิวสิคกำลังแต่งเติมสีสันและความสนุก...",
        "Idea Card พร้อมแล้ว ส่งต่อน้องน้ำและน้องมิวสิคเพื่อดีไซน์ Concept และท่อน Hook ประดับคอร์สเรียน"
    )
    
    try:
        nam_prompt_msg = f"นี่คือรายละเอียดบทเรียนจากเดียร์ ช่วยดีไซน์การสอนให้ตื่นเต้นและเห็นภาพง่ายสไตล์เป็นกันเอง:\n\n{idea_card}"
        nam_res = creative_model.generate_content(nam_prompt_msg)
        nam_draft = nam_res.text
        
        music_prompt_msg = f"นี่คือแนวคิดการสอนของน้ำ ช่วยเขียนท่อนเปิดหัว (Hook) ของคลิปวิชาการตัวนี้ และใส่ Meme ประกอบการเขียนโค้ดให้นักพัฒนาเข้าใจง่ายหน่อย:\n\n{nam_draft}"
        music_res = music_model.generate_content(music_prompt_msg)
        creative_concept = music_res.text
        
        # Save draft
        with open(os.path.join(current_dir, "workspace", "2_drafts", f"2_creative_concept_{safe_title}.md"), "w", encoding="utf-8") as f:
            f.write(creative_concept)
        print("✅ ปรับแต่งไอเดียสร้างสรรค์และการตลาดสำเร็จ")
    except Exception as e:
        status_logger.update_pipeline_status("creative", "น้ำ/มิวสิคเกิดข้อผิดพลาด", f"Error: {e}")
        print(f"Error in Nam/Music: {e}")
        return

    # 3. Cream (Researcher) & Or (Auditor)
    print("[3/6] 🔬 ตรวจสอบโค้ดและเทคนิค (ครีม & ออ): กำลังตรวจสอบโค้ด SDK และความถูกต้องเชิงวิชาการ...")
    status_logger.update_pipeline_status(
        "researcher",
        "ครีมและออตรวจสอบความถูกต้องทางเทคนิค...",
        "ส่งต่อข้อมูลบทเรียนให้น้องครีมเพื่อตรวจสอบโค้ดตัวอย่างกับคู่มือทางการของ SDK"
    )
    
    try:
        cream_prompt_msg = f"โปรดค้นคว้าโค้ดตัวอย่างอย่างง่ายและการทำงานของเสาหลักทั้ง 3 ในคู่มือ Antigravity และตรวจความถูกต้องของโค้ดในแนวคิดนี้:\n\n{creative_concept}"
        cream_res = researcher_model.generate_content(cream_prompt_msg)
        cream_draft = cream_res.text
        
        or_prompt_msg = f"นี่คือรายงานเทคนิคและการสาธิตโค้ดของครีม ช่วยทำ Fact-check และยืนยันความถูกต้องเชิงลึกว่าสอดคล้องกับ SDK อย่างสมบูรณ์แบบ:\n\n{cream_draft}"
        or_res = or_model.generate_content(or_prompt_msg)
        audit_report = or_res.text
        
        # Save draft
        with open(os.path.join(current_dir, "workspace", "2_drafts", f"3_technical_verification_{safe_title}.md"), "w", encoding="utf-8") as f:
            f.write(f"=== RESEARCH DRAFT ===\n\n{cream_draft}\n\n=== AUDIT REPORT ===\n\n{audit_report}")
        print("✅ ตรวจสอบเทคนิคและโค้ดตัวอย่างสำเร็จ")
    except Exception as e:
        status_logger.update_pipeline_status("researcher", "ครีม/ออเกิดข้อผิดพลาด", f"Error: {e}")
        print(f"Error in Cream/Or: {e}")
        return

    # 4. Ray (Writer) & Cri (Critic)
    print("[4/6] ✍️ ประกอบร่างสคริปต์ (เรย์ & คริ): กำลังเขียนบทพูดคำต่อคำ และ Pacing ฉากสาธิต...")
    status_logger.update_pipeline_status(
        "ray",
        "เรย์กำลังแต่งเขียนสคริปต์ฉบับสมบูรณ์...",
        "ผ่านการรับรองทางเทคนิคแล้ว ส่งต่อน้องเรย์เพื่อเขียนบทพูดตัวเต็มสไตล์ผู้สอนคู่หูเป็นกันเอง"
    )
    
    try:
        ray_prompt_msg = f"ช่วยปั้นสคริปต์วิดีโอสอนการเขียนโค้ดฉบับเต็มทีครับ โดยมีบทพูดคำต่อคำ (ภาษาไทยเป็นกันเอง วัยรุ่นคุยกัน) และระบุ Visual Cues / โค้ดที่แสดงบนหน้าจอ:\n\n[แนวคิดการนำเสนอ]:\n{creative_concept}\n\n[โค้ดและวิจัยที่ถูกต้อง]:\n{cream_draft}\n\n[ข้อเสนอแนะออดิต]:\n{audit_report}"
        ray_res = ray_model.generate_content(ray_prompt_msg)
        script_draft = ray_res.text
        
        cri_prompt_msg = f"ช่วยวิจารณ์ความลื่นไหล Pacing และความสนุกในการอธิบายเรื่องยากๆ ของสคริปต์การสอนตัวนี้ให้ทีครับ:\n\n{script_draft}"
        cri_res = cri_model.generate_content(cri_prompt_msg)
        critique = cri_res.text
        
        # Combine script and critique into final delivery
        final_delivery = f"""# บทเรียน: {lesson_title}

{script_draft}

---

## 🎭 บทวิจารณ์ Pacing และความลื่นไหลจากคริ (Critic)
{critique}
"""
        
        # Save to final_scripts
        final_path = os.path.join(current_dir, "workspace", "3_final_scripts", f"lesson_{safe_title}.md")
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(final_delivery)
            
        print(f"✅ บันทึกไฟล์บทเรียนเสร็จสิ้นที่: {final_path}")
        
        # Register artifact to M's dashboard
        abs_final_path = os.path.abspath(final_path)
        status_logger.register_artifact(f"ANTIA Lesson: {lesson_title}", f"file://{abs_final_path}")
        status_logger.update_pipeline_status(
            "idle",
            "ผลิตคอร์สเรียน ANTIA สำเร็จ - IDLE",
            f"บันทึกไฟล์บทเรียน {lesson_title} เสร็จสมบูรณ์แล้วแก!"
        )
        
    except Exception as e:
        status_logger.update_pipeline_status("ray", "เรย์/คริเกิดข้อผิดพลาด", f"Error: {e}")
        print(f"Error in Ray/Cri: {e}")
        return

if __name__ == "__main__":
    outline_path = os.path.join(current_dir, "workspace", "1_raw_materials", "course_outline_antigravity.md")
    process_course_outline(outline_path)
