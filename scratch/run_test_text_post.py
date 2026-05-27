import sys
import os
import subprocess

# Add skills folder to sys.path
skills_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'WTJ_Content_Studio', 'Team_Agent_Content', 'skills')
sys.path.append(skills_dir)

from notion_helper import NotionHelper

def main():
    print("🧪 Running test for splitting Text_Posts...")
    notion = NotionHelper()
    
    # 1. Create a test page in Notion with Status: 1_Ideation
    test_title = "ช่างแต่งหน้าสู้ชีวิต"
    print(f"Creating a test page: '{test_title}'...")
    new_page = notion.create_page(test_title, status_name="1_Ideation")
    
    if not new_page or "id" not in new_page:
        print("❌ Failed to create test page.")
        return
        
    page_id = new_page["id"]
    print(f"✅ Created test page in Notion: {page_id}")
    
    # 2. Add a mock transcript to the test page
    mock_transcript = """
คำถามชวนคิดสำหรับช่างแต่งหน้าและคนทำงานทุกคนแก:
ระหว่างเครื่องสำอางแบรนด์เนมราคาหลักหมื่น กับฝีมือและเทคนิคการแต่งหน้าระดับโปร สิ่งไหนสำคัญกว่ากันในการมัดใจเจ้าสาวในวันสำคัญ?
"เครื่องสำอางแพงแค่ไหน ก็เทียบไม่ได้กับฝีมือและความใส่ใจที่คุณมอบให้ลูกค้าครับ" - คำโควทเด็ดของพี่เก่งจากสัมภาษณ์ตอนล่าสุด
ชวนเพื่อนๆ พี่ๆ น้องๆ ช่างแต่งหน้ามาแชร์ประสบการณ์หรือโหวตความเห็นกันหน่อยเร็วจ้า!
"""
    print("Writing mock transcript to the test page...")
    notion.write_page_content_text(page_id, mock_transcript.strip())
    print("✅ Mock transcript written.")
    
    # 3. Execute fb_draft_generator.py to process the card
    print("Running fb_draft_generator.py...")
    generator_script = os.path.join(skills_dir, "fb_draft_generator.py")
    
    # Run the generator script using the project's venv python interpreter
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python')
    
    result = subprocess.run([venv_python, generator_script], capture_output=True, text=True)
    
    print("\n--- Generator Output ---")
    print(result.stdout)
    if result.stderr:
        print("--- Generator Errors ---")
        print(result.stderr)
    print("------------------------\n")
    
    # 4. Verify in Notion (by querying database and checking for THU and SUN cards)
    print("Checking Notion database for results...")
    res = notion.query_database()
    if res and "results" in res:
        found_thu = None
        found_sun = None
        title_prop_name = notion.get_title_property_name()
        
        for page in res["results"]:
            props = page["properties"]
            name_prop = props.get(title_prop_name, {})
            title = "Untitled"
            if name_prop.get("type") == "title" and name_prop.get("title"):
                title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
            
            if "[THU_Text]" in title and "ช่างแต่งหน้าสู้ชีวิต" in title:
                found_thu = page
            elif "[SUN_Text]" in title and "ช่างแต่งหน้าสู้ชีวิต" in title:
                found_sun = page
                
        if found_thu:
            print(f"🎉 Success! Found Thursday card: '{found_thu['properties'][title_prop_name]['title'][0]['text']['content']}' (ID: {found_thu['id']})")
        else:
            print("❌ Thursday card not found.")
            
        if found_sun:
            print(f"🎉 Success! Found Sunday card: '{found_sun['properties'][title_prop_name]['title'][0]['text']['content']}' (ID: {found_sun['id']})")
        else:
            print("❌ Sunday card not found.")
            
if __name__ == "__main__":
    main()
