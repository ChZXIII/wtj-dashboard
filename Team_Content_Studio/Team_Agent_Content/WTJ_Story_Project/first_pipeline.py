import os
import sys
import google.generativeai as genai
import status_logger

# Load API key
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: ไม่พบ GOOGLE_API_KEY ในระบบ")
    exit(1)

import sys
# Add parent directory of Team_Agent_Content (project root) to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)
import model_router

# Function to load prompts
def load_prompt(filename):
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# Initialize models
researcher_prompt = load_prompt("researcher_prompt.md")
director_prompt = load_prompt("director_prompt.md")

researcher_model = model_router.get_model("researcher", system_instruction=researcher_prompt)
director_model = model_router.get_model("director", system_instruction=director_prompt)

# First's own instruction for checking sources
first_checker_instruction = """คุณคือ First (เลขาผู้ประสานงานทีมคอนเทนต์) 
หน้าที่ของคุณในขั้นตอนนี้คือ: ตรวจสอบข้อมูลที่ Lead Researcher หามาให้ ว่ามีการระบุแหล่งที่มา (Sources/References) ชัดเจนและน่าเชื่อถือหรือไม่ 
- หากมีแหล่งที่มา: ให้สรุปสั้นๆ ว่า "ตรวจสอบแหล่งที่มาแล้ว: อ้างอิงจาก [ชื่อแหล่งข้อมูลหลักๆ]" 
- หากไม่มีหรือแหล่งที่มาดูไม่น่าเชื่อถือ (เช่นอ้างลอยๆ): ให้ระบุจุดสังเกต หรือเตือน Director ไว้ให้ระวังตอนนำข้อมูลไปใช้
เขียนตอบสั้นๆ ไม่เกิน 3-4 บรรทัด ด้วยน้ำเสียงของเลขาที่รอบคอบ"""

first_checker_model = model_router.get_model("first", system_instruction=first_checker_instruction)

def process_topic(topic):
    # เริ่มต้นลูป
    status_logger.update_pipeline_status(
        "first_agent", 
        f"เริ่มต้นประมวลผลหัวข้อ: {topic}", 
        f"รับหัวข้อใหม่ '{topic}' เริ่มรันงานทีมคอนเทนต์", 
        clear_logs=True
    )
    
    # 1. Lead Researcher
    print(f"\n[1/4] 🔍 First: กำลังส่งหัวข้อ '{topic}' ให้ Lead Researcher หา Insight พร้อมแหล่งอ้างอิง...")
    status_logger.update_pipeline_status(
        "cream", 
        f"น้องครีมกำลังหาข้อมูลเชิงลึก: {topic}", 
        f"ส่งหัวข้อให้ น้องครีม (Lead Researcher) รีเสิร์ชความถูกต้องและ Fact เชิงลึก"
    )
    try:
        research_result = researcher_model.generate_content(f"หาข้อมูลเชิงลึกของอาชีพ: {topic}")
        print("\n--- 💡 Researcher's Insight ---")
        print(research_result.text)
        print("---------------------------------\n")
    except Exception as e:
        status_logger.update_pipeline_status("cream", "น้องครีมเกิดข้อผิดพลาดในการหาข้อมูล", f"Error: {e}")
        print(f"Error calling Researcher: {e}")
        return

    # 2. Fact-checking by First/Auditor
    print("[2/4] 🕵️ First: กำลังตรวจสอบแหล่งที่มาของข้อมูล (Fact-check)...")
    status_logger.update_pipeline_status(
        "first_agent", 
        "เฟิสกำลังตรวจทานแหล่งข้อมูล...", 
        "น้องครีมส่งข้อมูลรีเสิร์ชแล้ว กำลังส่งต่อเข้าท่อตรวจสอบ Fact-checking"
    )
    try:
        check_result = first_checker_model.generate_content(f"โปรดตรวจสอบข้อมูลต่อไปนี้:\n{research_result.text}")
        print("\n--- ✅ First's Verification ---")
        print(check_result.text)
        print("------------------------------\n")
    except Exception as e:
        status_logger.update_pipeline_status("first_agent", "เฟิสเกิดข้อผิดพลาดในการตรวจสอบ", f"Error: {e}")
        print(f"Error calling Checker: {e}")
        return

    # 3. Director/Writer
    print("[3/4] 🎬 First: กำลังส่งข้อมูล Insight ให้ Director เขียนสคริปต์สไตล์ WTJ...")
    status_logger.update_pipeline_status(
        "ray", 
        "น้องเรย์กำลังแต่งสคริปต์...", 
        "ผ่านการตรวจเช็ก Fact เรียบร้อย ส่งต่อน้องเรย์เพื่อเขียนร่างสคริปต์สไตล์ WTJ Story"
    )
    try:
        director_prompt_msg = f"นี่คือข้อมูล Insight สำหรับอาชีพ {topic} พร้อมการตรวจทานจากผม รบกวนเขียนเป็นสคริปต์วิดีโอตามโครงสร้างช่อง WTJ Story ให้หน่อยครับ:\n\n[ข้อมูลดิบจากนักวิจัย]:\n{research_result.text}\n\n[คอมเมนต์การตรวจทานจาก First]:\n{check_result.text}"
        script_result = director_model.generate_content(director_prompt_msg)
        print("\n--- 📝 Director's Script (Draft) ---")
        print(script_result.text)
        print("------------------------------------\n")
    except Exception as e:
        status_logger.update_pipeline_status("ray", "น้องเรย์เกิดข้อผิดพลาดในการเขียนสคริปต์", f"Error: {e}")
        print(f"Error calling Director: {e}")
        return

    # 4. Save to repository
    print(f"[4/4] 💾 First: กำลังเซฟสคริปต์ลงโฟลเดอร์ workspace/3_final_scripts...")
    status_logger.update_pipeline_status(
        "notes", 
        "กำลังจัดเก็บผลงานลงคลัง Notes...", 
        "น้องเรย์เขียนสคริปต์เสร็จแล้ว เฟิสกำลังจัดเก็บไฟล์บันทึกลงโฟลเดอร์คลังสคริปต์"
    )
    try:
        safe_filename = topic.replace(" ", "_").replace("/", "_").lower() + "_wtj_draft.txt"
        filepath = os.path.join(os.path.dirname(__file__), "workspace", "3_final_scripts", safe_filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script_result.text)
        print(f"✅ บันทึกไฟล์เสร็จสิ้น: {filepath}")
        
        # ลงทะเบียน Artifact และเสร็จสิ้นลูป
        abs_filepath = os.path.abspath(filepath)
        status_logger.register_artifact("YouTube Script Draft", f"file://{abs_filepath}")
        status_logger.update_pipeline_status(
            "idle", 
            "งานเสร็จสมบูรณ์ - IDLE", 
            f"บันทึกไฟล์ {safe_filename} ลงคลังสำเร็จ ปิดลูปงานเรียบร้อย!"
        )
    except Exception as e:
        status_logger.update_pipeline_status("notes", "เกิดข้อผิดพลาดในการบันทึกไฟล์", f"Error: {e}")
        print(f"Error saving file: {e}")

def run_interactive():
    print("==================================================")
    print("💼 First (เลขา): ระบบ Workflow ทีมคอนเทนต์ (พร้อมระบบ Cross-check) พร้อมแล้วครับ!")
    print("พิมพ์ชื่อ 'อาชีพ' หรือ 'หัวข้อ' ที่ต้องการ (พิมพ์ 'exit' เพื่อออก)")
    print("==================================================\n")
    while True:
        topic = input("คุณผู้ใช้ (Topic): ")
        if topic.lower() in ['exit', 'quit']:
            print("First: ปิดระบบการทำงานเรียบร้อยครับ")
            break
        if not topic.strip():
            continue
        process_topic(topic)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run via command line argument silently
        topic = " ".join(sys.argv[1:])
        process_topic(topic)
    else:
        # Run interactively
        run_interactive()
