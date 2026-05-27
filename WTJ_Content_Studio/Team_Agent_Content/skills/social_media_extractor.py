import os
import sys

def extract_social_highlights(script_path):
    """
    Skill: Social Media Extractor
    Purpose: Extracts highlights from a YouTube script for Nam to create hooks and Ray to write posts.
    """
    topic = os.path.basename(script_path).replace('.md', '').replace('research_', '').replace('_', ' ')
    
    print(f"🔄 กำลังสกัดข้อมูลไฮไลต์จากสคริปต์เรื่อง: {topic}...")
    
    # Mockup extraction logic
    # In reality, this would use an LLM to read the script and extract highlights
    
    highlights = f"""
## 🎯 ไฮไลต์สำหรับทีม Social Media (ส่งให้ น้ำ คิด Hook -> เรย์ เขียนโพสต์)

### 📌 1. The Shocking Fact (สำหรับ TikTok/Reels)
- **ข้อมูลเด็ด:** "คนปรับสมดุลเกม (Game Balancer) คือคนที่แก้โค้ดแทบตาย แต่คนเล่นกลับบอกว่าเกมสนุกขึ้นแค่เพราะ... เราเปลี่ยนเสียงปืนให้ดังขึ้น!"
- **ความเจ็บปวด:** ไม่ได้สู้กับคณิตศาสตร์ แต่สู้กับ 'ความรู้สึก' ของคนเล่น

### 📌 2. Top 3 Insights (สำหรับ Facebook Bullet Points)
1. **รายได้สูงปรี๊ดแต่แลกด้วยน้ำตา:** เงินเดือนระดับซีเนียร์พุ่งถึง 140,000+ บาท/เดือน แต่ต้องรับมือกับคอมเมนต์ด่าทอจากแฟนเกมทั่วโลกทุกครั้งที่ตัวละครโปรดถูกเนิร์ฟ
2. **อาชีพที่มี Live Ops ไม่มีวันจบ:** ต่างจากโปรแกรมเมอร์ทั่วไปที่เกมเสร็จคือจบ แต่ Balancer ต้องตามแก้เกมไปเรื่อยๆ ตราบใดที่เซิร์ฟเวอร์ยังเปิด
3. **50% Trap:** การทำให้ทุกตัวละครเก่งเท่ากันเป๊ะๆ (50% Win rate) กลับทำให้เกมน่าเบื่อที่สุด ความท้าทายคือทำยังไงให้เกม 'ดูเหมือน' ไม่สมดุล แต่มันสนุก!

---
💡 **ส่งไม้ต่อ:** 
- **@น้ำ (Nam):** ช่วยคิด Hook เปิดคลิป TikTok ภายใน 1.5 วินาทีแรกจาก "The Shocking Fact" และโยนไอเดียหัวข้อเฟสบุ๊ก 1 บรรทัด
- **@เรย์ (Ray):** รอรับ Hook จากน้ำ แล้วไปเขียนสคริปต์ TikTok เต็มๆ 1 นาที และโพสต์เฟสบุ๊กแบบเล่าเรื่องพร้อมใส่ Hashtag
"""
    
    output_path = f"workspace/2_drafts/social_highlights_{topic.replace(' ', '_')}.md"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(highlights)
        
    print(f"✅ สกัดไฮไลต์เสร็จสิ้น! บันทึกไว้ที่: {output_path}")
    print(highlights)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        extract_social_highlights(sys.argv[1])
    else:
        print("💡 กรุณาระบุไฟล์สคริปต์ที่ต้องการสกัดข้อมูล เช่น: python skills/social_media_extractor.py 'workspace/3_final_scripts/script_game_balancer.md'")
