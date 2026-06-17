# 🦉 AI Sidekick Course Outline - Lesson 1: Hello World with Google Antigravity SDK

## 📋 Course Information
- **Course Name:** เริ่มต้นสร้าง AI Agent อัจฉริยะด้วย Google Antigravity SDK
- **Lesson Number:** 1
- **Lesson Title:** Hello World! รู้จักกับ 3 เสาหลัก และการสร้าง Agent ตัวแรก
- **Target Audience:** Developers, Tech Enthusiasts, AI Creators ที่ต้องการสร้าง Autonomous Agents บนเครื่องคอมพิวเตอร์ตัวเอง

## 🎯 Lesson Objectives
1. เข้าใจแนวคิด 3 เสาหลักของ Google Antigravity SDK (Agent, Conversation, Connection)
2. รู้วิธีการติดตั้งและตั้งค่า Environment เบื้องต้น
3. เขียนโค้ดรัน Agent ตอบคำถามแบบพื้นฐานได้ (Hello World)
4. เข้าใจการทำงานแบบ Streaming (การสตรีมคำตอบ และการดึง Thoughts/ความคิดเบื้องหลังของ AI)

## 💡 Key Content Points to Cover
- **ติดตั้งง่าย:** ใช้ `pip install google-antigravity`
- **คีย์ API:** การตั้งค่า `GOOGLE_API_KEY` ในไฟล์ `.env`
- **3 เสาหลัก (The 3 Pillars):**
  1. **Agent:** ตัวควบคุมหลัก รับ Config
  2. **Conversation:** เซสชันแชทที่จำประวัติ (Stateful)
  3. **Connection:** ตัวขนส่งข้อมูลคุยกับโมเดลหลังบ้าน
- **ตัวอย่างโค้ด Hello World:** การใช้ `async with Agent(LocalAgentConfig()) as agent:`
- **ตัวอย่างโค้ด Streaming Thoughts:** การใช้ `async for thought in response.thoughts:` เพื่อแง้มดูหัวสมองกระบวนการคิดของ Agent ก่อนตอบจริง
