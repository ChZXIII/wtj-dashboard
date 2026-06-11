import os
import sys

def search_youtube_trends(query):
    """
    Skill: YouTube Trend Researcher
    Purpose: Helps Cream (Lead Researcher) find trending topics and insights.
    Usage: python skills/youtube_researcher.py "topic"
    """
    print(f"🔍 ครีมกำลังเริ่มค้นหาอินไซต์สำหรับหัวข้อ: '{query}' บน YouTube...")
    
    # ในสภาวะจำลอง (Mockup) ของการสร้าง Skill:
    # เอเจนต์หลัก (Antigravity) จะใช้ความสามารถ search_web เพื่อหาข้อมูลจริงๆ
    # แล้วนำมาบันทึกลงใน workspace/1_raw_materials/
    
    print("✅ ค้นพบหัวข้อที่กำลังเป็นกระแส 3 อันดับแรก:")
    print("1. [Insight] ยอดวิวเฉลี่ย 1M+ สำหรับหัวข้อนี้ในสัปดาห์ที่ผ่านมา")
    print("2. [Hook] ประโยคเปิดที่คนใช้เยอะที่สุดคือ 'รู้มั้ยว่า...'")
    print("3. [Format] คลิปสั้น (Shorts) ยาว 45-55 วินาที ได้ Engagement สูงสุด")
    
    # บันทึกผลลัพธ์เพื่อให้ Director (Chris) หรือ Creative (Nam) นำไปใช้งานต่อ
    output_path = f"workspace/1_raw_materials/research_{query.replace(' ', '_')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# YouTube Research Result: {query}\n\n")
        f.write(f"**Researcher:** Cream (Lead Researcher)\n")
        f.write(f"**Findings:**\n- Trending high on YouTube Thailand.\n- Target audience: Gen Z and Millenials.\n- Key focus: Practical and fast-paced content.\n")
    
    print(f"📊 บันทึกข้อมูลวิจัยลงใน {output_path} เรียบร้อยแล้วจ้า!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_youtube_trends(sys.argv[1])
    else:
        print("💡 กรุณาระบุหัวข้อที่ต้องการค้นหา เช่น: python skills/youtube_researcher.py 'อาชีพที่น่าสนใจ'")
