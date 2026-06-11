import os
import sys
import re
import dotenv
from google import genai
import google.generativeai as legacy_genai

# 1. Load Environment Variables and API Key
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = None
test_dir = current_dir
for _ in range(4):
    test_path = os.path.join(test_dir, ".env")
    if os.path.exists(test_path):
        env_path = test_path
        break
    test_dir = os.path.dirname(test_dir)

if env_path:
    dotenv.load_dotenv(env_path)

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ Error: ไม่พบ GOOGLE_API_KEY ในระบบกรุณาตั้งค่าใน .env ก่อนรันสคริปต์")
    exit(1)

# Configure legacy SDK for text generation
legacy_genai.configure(api_key=API_KEY)
# Initialize new SDK for image generation fallback
genai_client = genai.Client(api_key=API_KEY)

# 2. Helper to load prompts
def load_prompt(filename):
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
    if not os.path.exists(prompt_path):
        print(f"⚠️ Warning: ไม่พบไฟล์ prompt {filename} จะลองเช็คในโฟลเดอร์ปัจจุบัน...")
        prompt_path = os.path.join(os.path.dirname(__file__), filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# Load all agent prompts
try:
    deer_prompt = load_prompt("deer_prompt.md")
    creative_prompt = load_prompt("creative_prompt.md")
    music_prompt = load_prompt("music_prompt.md")
    researcher_prompt = load_prompt("researcher_prompt.md")
    or_prompt = load_prompt("or_prompt.md")
    ray_prompt = load_prompt("ray_prompt.md")
    cri_prompt = load_prompt("cri_prompt.md")
    director_prompt = load_prompt("director_prompt.md")
    p_prompt = load_prompt("p_prompt.md")
except Exception as e:
    print(f"❌ Error loading prompt files: {e}")
    exit(1)

# Combined Prompt for Chris (Director) & P (Visuals)
storyboard_prompt = f"""{director_prompt}

---
{p_prompt}

---
หน้าที่ร่วมกันของคุณสองคนในขั้นตอนนี้คือ: รวมพลังผู้กำกับ (Chris) และฝ่ายจัดทัศน์ภาพ (P) 
เพื่อสร้าง Storyboard รายซีนของสคริปต์ที่ได้ รับส่งข้อมูลวิจัย และระบุ B-roll 
1. แยกแยะอย่างชัดเจนว่าซีนไหนคือเคสจริง/แบรนด์จริง (เช่น Aphelios ของ LOL, Yoshi-P ของ FF14) -> ให้ระบุประเภทสื่อเป็น `[ใช้ภาพ/คลิปจริง - ลิขสิทธิ์ผ่าน]` และแนบแนวทางการสืบค้นและลิงก์จริงที่ครีมหามาให้
2. ซีนที่เป็นนามธรรม/เปรียบเปรย -> ให้ระบุประเภทสื่อเป็น `[ใช้ภาพ AI เจน]` และเขียน Prompt ภาษาอังกฤษแนวยาว 16:9 ในสไตล์ 3D Claymation / Miniature Figurine / Soft Plastic Toy style ของช่อง Sai MoneyMonster เสมอ
"""

# Import model router
# Find project root where model_router is located
test_dir = os.path.dirname(os.path.abspath(__file__))
for _ in range(4):
    test_path = os.path.join(test_dir, "model_router.py")
    if os.path.exists(test_path):
        if test_dir not in sys.path:
            sys.path.append(test_dir)
        break
    test_dir = os.path.dirname(test_dir)
import model_router

# Initialize routed models using model_router
deer_model = model_router.get_model("deer", system_instruction=deer_prompt)
creative_model = model_router.get_model("creative", system_instruction=creative_prompt)
music_model = model_router.get_model("music", system_instruction=music_prompt)
researcher_model = model_router.get_model("researcher", system_instruction=researcher_prompt)
or_model = model_router.get_model("or", system_instruction=or_prompt)
ray_model = model_router.get_model("ray", system_instruction=ray_prompt)
cri_model = model_router.get_model("cri", system_instruction=cri_prompt)
storyboard_model = model_router.get_model("storyboard", system_instruction=storyboard_prompt)

def extract_prompts(storyboard_content):
    prompts = []
    lines = storyboard_content.split('\n')
    current_scene = "Unknown Scene"
    for i, line in enumerate(lines):
        if line.startswith("### 📸 Scene") or line.startswith("### Scene"):
            current_scene = line.replace("### 📸 ", "").replace("### ", "").strip()
        if "Prompt" in line and i + 1 < len(lines):
            next_line = lines[i+1].strip()
            if next_line.startswith(">"):
                prompt_text = next_line.lstrip(">").strip()
                # Clean up Midjourney aspect ratio commands just in case
                if prompt_text and not prompt_text.startswith("["):
                    prompts.append((current_scene, prompt_text))
    return prompts

def execute_pipeline(topic):
    # Setup Output Folder
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(" ", "_").lower()
    workspace_dir = os.path.join(os.path.dirname(__file__), "..", "workspace", safe_topic)
    os.makedirs(workspace_dir, exist_ok=True)
    
    print("==================================================")
    print(f"🎬 เริ่มท่อส่งงานอัตโนมัติ WTJ Story สำหรับตอน: '{topic}'")
    print(f"📁 บันทึกข้อมูลที่: {workspace_dir}")
    print("==================================================\n")
    
    # Step 1: Deer (Idea Card)
    print("[1/9] 🦌 เดียร์ (Idea Card): กำลังร่างบอร์ดไอเดียและมุมเล่าเรื่อง...")
    try:
        deer_res = deer_model.generate_content(f"ร่าง Idea Card เจาะลึกอาชีพ: {topic}")
        idea_card_path = os.path.join(workspace_dir, "1_idea_card.md")
        with open(idea_card_path, "w", encoding="utf-8") as f:
            f.write(deer_res.text)
        print("✅ ร่าง Idea Card เสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 1 (Deer): {e}")
        return

    # Step 2: Nam (Creative Concept)
    print("[2/9] 💅 น้ำ (Creative Concept): กำลังดีไซน์โครงสร้างมุมเล่าเรื่องสร้างสรรค์...")
    try:
        creative_res = creative_model.generate_content(f"นี่คือ Idea Card จากเดียร์ รบกวนดีไซน์ Creative Concept ด้วยนะจ๊ะ:\n\n{deer_res.text}")
        creative_draft = creative_res.text
        print("✅ ร่างไอเดียสร้างสรรค์เสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 2 (Nam): {e}")
        return

    # Step 3: Music (Marketing Enhancement)
    print("[3/9] 🎸 มิวสิค (Marketing/Meme): กำลังใส่ไอเดียการตลาดและมีมประกอบ...")
    try:
        music_res = music_model.generate_content(f"นี่คือคอนเซปต์ของน้ำ ช่วยเสริมไอเดียมีมและการตลาดให้จึ้งๆ หน่อยน้าา:\n\n{creative_draft}")
        creative_concept_path = os.path.join(workspace_dir, "2_creative_concept.md")
        with open(creative_concept_path, "w", encoding="utf-8") as f:
            f.write(music_res.text)
        print("✅ เสริมคอนเซปต์การตลาดเสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 3 (Music): {e}")
        return

    # Step 4: Cream (Researcher)
    print("[4/9] 🔬 ครีม (Research): กำลังสืบค้นข้อมูลเชิงลึก ข้อเท็จจริง และแหล่งภาพประกอบจริง...")
    try:
        research_res = researcher_model.generate_content(f"นี่คือบอร์ดไอเดียและแนวทางสร้างสรรค์ รบกวนหาข้อมูลเชิงลึก ตัวเลขรายได้ และเช็คลิงก์รูปภาพ/วิดีโอจริงที่มีลิขสิทธิ์ปลอดภัยให้หน่อยนะ:\n\n{music_res.text}")
        research_draft = research_res.text
        print("✅ สืบค้นข้อมูลเชิงลึกเสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 4 (Cream): {e}")
        return

    # Step 5: Or (Auditor)
    print("[5/9] 📋 ออ (Audit): กำลังตรวจ Fact-check ความถูกต้องและลิขสิทธิ์ภาพประกอบ...")
    try:
        audit_res = or_model.generate_content(f"นี่คือข้อมูลวิจัยของน้องครีม รบกวนพี่ออช่วยตรวจเช็คความถูกต้องและลิขสิทธิ์ของภาพ/วิดีโออ้างอิงให้ทีค่ะ:\n\n{research_draft}")
        audit_report_path = os.path.join(workspace_dir, "4_audit_report.md")
        with open(audit_report_path, "w", encoding="utf-8") as f:
            f.write(audit_res.text)
            
        research_doc_path = os.path.join(workspace_dir, "3_research_doc.md")
        with open(research_doc_path, "w", encoding="utf-8") as f:
            f.write(research_draft)
        print("✅ ตรวจสอบ Fact-check และสื่อลิขสิทธิ์เสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 5 (Or): {e}")
        return

    # Step 6: Ray (Writer)
    print("[6/9] ✍️ เรย์ (Writer): กำลังประกอบร่างสคริปต์บทพูดและดราฟต์โซเชียล...")
    try:
        ray_prompt_msg = f"รบกวนปั้นสคริปต์บทพูดสำหรับพี่เก่งตามโครงสร้าง WTJ Story ด้วยนะ\n\n[ข้อมูลวิจัยที่ผ่านออดิต]:\n{research_draft}\n\n[รายงานออดิตจากออ]:\n{audit_res.text}\n\n[ครีเอทีฟคอนเซปต์]:\n{music_res.text}"
        ray_res = ray_model.generate_content(ray_prompt_msg)
        script_draft = ray_res.text
        print("✅ ร่างบทพูดสคริปต์แรกเสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 6 (Ray): {e}")
        return

    # Step 7: Music (Content Optimize)
    print("[7/9] 🎤 มิวสิค (Optimize Script): กำลังร่วมมือกับเรย์ ขยี้ Hook และพาดหัวคลิป...")
    try:
        music_opt_res = music_model.generate_content(f"นี่คือดราฟต์สคริปต์ของเรย์ ช่วยขยี้ท่อน Hook และตรวจพาดหัวโปรโมตดึงดูดใจตามสไตล์การตลาดมีมจึ้งๆ ให้หน่อยค่า:\n\n{script_draft}")
        script_path = os.path.join(workspace_dir, "5_youtube_script.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(music_opt_res.text)
        print("✅ ตกแต่งสคริปต์การตลาดเสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 7 (Music Optimize): {e}")
        return

    # Step 8: Cri (Critic)
    print("[8/9] 🎭 คริ (Critic): กำลังวิจารณ์ Pacing จังหวะเล่า และความลื่นไหลของบท...")
    try:
        cri_res = cri_model.generate_content(f"นี่คือสคริปต์รอบสุดท้าย ช่วยวิจารณ์ Pacing, Hook และตรวจความเหมาะสมด้วยครับ:\n\n{music_opt_res.text}")
        critique_path = os.path.join(workspace_dir, "6_critique_script.md")
        with open(critique_path, "w", encoding="utf-8") as f:
            f.write(cri_res.text)
        print("✅ วิเคราะห์ประเมินสคริปต์เสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 8 (Cri): {e}")
        return

    # Step 9: Chris & P (Storyboard & Prompts)
    print("[9/9] 🎬 คริส & พี (Storyboard & Prompts): กำลังวางสตอรี่บอร์ด คอนเซปต์ 3D Claymation (16:9) และระบุจุดใช้ภาพจริง...")
    try:
        storyboard_prompt_msg = f"รบกวนวางสตอรี่บอร์ดและ Prompt 16:9 สไตล์ Claymation ร่วมถึง B-roll ให้สอดคล้องกับบทด้วยครับ:\n\n[สคริปต์บทพูด]:\n{music_opt_res.text}\n\n[ข้อมูลวิจัยและแหล่งสื่อจริง]:\n{research_draft}"
        storyboard_res = storyboard_model.generate_content(storyboard_prompt_msg)
        storyboard_path = os.path.join(workspace_dir, "7_storyboard_and_prompts.md")
        with open(storyboard_path, "w", encoding="utf-8") as f:
            f.write(storyboard_res.text)
        print("✅ สตอรี่บอร์ดร่างเสร็จสิ้น")
    except Exception as e:
        print(f"❌ Error at Step 9 (Chris & P): {e}")
        return

    # --- Step 10: Automatic Image Generation Fallback Check ---
    print("\n🎨 ระบบตรวจสอบความสามารถการเจนภาพอัตโนมัติ...")
    storyboard_text = storyboard_res.text
    ai_prompts = extract_prompts(storyboard_text)
    
    if not ai_prompts:
        print("ℹ️ ไม่พบ Prompt สำหรับรูปภาพ AI ในสตอรี่บอร์ด (อาจเป็นภาพจริงทั้งหมด)")
        print("\n🎉 ท่อส่งงานอัตโนมัติ WTJ Story ผลิตคอนเทนต์ครบ 7 ขั้นตอนเรียบร้อยแล้วแก!")
        return

    print(f"🔍 ตรวจพบ {len(ai_prompts)} ภาพที่ต้องการ AI เจน... กำลังทดสอบสิทธิ์ API Key...")
    images_dir = os.path.join(workspace_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Try generating the first image to check paid vs free tier API status
    first_scene, first_prompt = ai_prompts[0]
    try:
        from google.genai import types
        # Standard Imagen 4.0 configuration
        result = genai_client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=first_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio='16:9',
                output_mime_type='image/png'
            )
        )
        # If it reaches here without throwing exception, paid plan is enabled!
        print("🚀 API Key รองรับการเจนภาพผ่านโค้ด! กำลังวาดรูปประกอบแนวนอน 16:9 ทั้งหมด...")
        
        # Save first image
        import io
        from PIL import Image
        image = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
        image_filename = f"scene_1_{first_scene.lower().replace(' ', '_')}.png"
        image.save(os.path.join(images_dir, image_filename))
        print(f"- บันทึกรูปแรก: {image_filename}")
        
        # Loop for remaining prompts
        for idx, (scene, p_text) in enumerate(ai_prompts[1:], start=2):
            result = genai_client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=p_text,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio='16:9',
                    output_mime_type='image/png'
                )
            )
            image = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
            image_filename = f"scene_{idx}_{scene.lower().replace(' ', '_')}.png"
            image.save(os.path.join(images_dir, image_filename))
            print(f"- บันทึกรูป: {image_filename}")
            
        print("\n🎉 วาดภาพประกอบครบถ้วนและเซฟลงโฟลเดอร์เรียบร้อยแล้วแก!")

    except Exception as e:
        # Fallback for Free Tier / Invalid Argument error
        error_msg = str(e)
        if "paid plans" in error_msg or "400" in error_msg or "INVALID_ARGUMENT" in error_msg:
            print("\n⚠️ [แจ้งเตือนข้อจำกัดบัญชีฟรี] API Key ของแกไม่รองรับการดึงโมเดลสร้างภาพ Imagen 4.0/3.0 ผ่านโค้ด")
            print("💡 ระบบทำการสกัดลิสต์ Prompts ทั้งหมดออกมาเพื่อความสะดวกในการเจนมือแทนนะครับ")
            
            instructions_path = os.path.join(workspace_dir, "image_prompts_instructions.txt")
            with open(instructions_path, "w", encoding="utf-8") as f:
                f.write(f"=== 🎨 IMAGE PROMPTS INSTRUCTION FOR TOPIC: {topic} ===\n\n")
                f.write("เนื่องจาก API Key เป็นแบบฟรี บล๊อกไม่ให้วาดรูปผ่าน API\n")
                f.write("แกสามารถเลือกก๊อปปี้ Prompts ภาษาอังกฤษแนวยาว 16:9 ด้านล่างนี้ส่งให้ Antigravity ในแชทช่วยวาดให้ได้เลยครับ!\n\n")
                f.write("--------------------------------------------------\n")
                for idx, (scene, p_text) in enumerate(ai_prompts, start=1):
                    f.write(f"📸 ซีน: {scene}\n")
                    f.write(f"Prompt: {p_text}\n")
                    f.write("--------------------------------------------------\n")
            print(f"💾 บันทึกคำสั่งและ Prompts เรียบร้อยที่: {instructions_path}")
        else:
            print(f"❌ เกิดข้อผิดพลาดอื่นๆ ในระบบภาพ: {e}")

    print("\n🎉 ดำเนินการผลิตเนื้อหา WTJ Story ทุกขั้นตอนสำเร็จเรียบร้อยแล้วแก!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        topic_input = " ".join(sys.argv[1:])
        execute_pipeline(topic_input)
    else:
        # Interactive mode fallback
        print("==================================================")
        print("🦉 เลขาเฟิส: เริ่มระบบผลิตอัตโนมัติ WTJ Auto-Producer Pipeline")
        print("==================================================")
        topic_input = input("ระบุหัวข้อที่ต้องการทำ (เช่น Game Balancer): ")
        if topic_input.strip():
            execute_pipeline(topic_input)
