# Source Generated with Decompyle++
# File: video_draft_generator.cpython-312.pyc (Python 3.12)

import os
import sys
import time
import re
import shutil
import argparse
from google import genai
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
from notion_helper import NotionHelper
PROJECT_ROOT = CURRENT_DIR
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

def load_env():
    '''Load Environment Variables from .env file.'''
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding = 'utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or not '=' in line:
                        continue
                    (key, val) = line.split('=', 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
        except Exception as e:
            print(f"⚠️ Error loading env: {e}")

load_env()
API_KEY = os.environ.get('GOOGLE_API_KEY')
if not API_KEY:
    print('❌ Error: ไม่พบ GOOGLE_API_KEY ในไฟล์ .env ของโปรเจกต์')
    sys.exit(1)
client = genai.Client(api_key = API_KEY)
RAW_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Story', 'workspace', '1_raw_materials')
DRAFTS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Story', 'workspace', '2_drafts')
MEDIA_EXTENSIONS = ('.mp4', '.mp3', '.wav', '.m4a', '.mov', '.avi', '.mkv', '.ogg', '.aac', '.flac')
PROJECT_TYPE = 'story'

def wait_for_file_to_stabilize(file_path):
    '''Wait until a file is fully copied (its size stops changing).'''
    print(f'''⏳ กำลังตรวจสอบขนาดไฟล์ \'{os.path.basename(file_path)}\' เพื่อความมั่นใจว่าก๊อปเสร็จแล้ว...''')
    last_size = -1
    while True:
        try:
            current_size = os.path.getsize(file_path)
            if current_size == last_size:
                print(f'''✅ ไฟล์เสถียรแล้ว ขนาด: {current_size / 1048576:.2f} MB''')
                break
            last_size = current_size
            time.sleep(2)
        except Exception as e:
            print(f'''⚠️ เกิดข้อผิดพลาดในการตรวจสอบขนาดไฟล์: {e}''')
            time.sleep(2)



def generate_social_posts(file_ref, filename, queue_name):
    '''Call Gemini to analyze the media and write drafts for a specific queue.'''
    print(f'''🧠 กำลังส่งวิเคราะห์สื่อสำหรับคิว: {queue_name}...''')
    
    if PROJECT_TYPE == "sidekick":
        if queue_name == "YT_Videos_Full":
            prompt = f'''คุณคือทีมงานหลังบ้านของช่อง AI Sidekick ช่องที่ช่วยให้ทุกคนทำงานร่วมกับ AI ได้อย่างมืออาชีพและง่ายขึ้น โดยมีมาสคอตคือ "น้อง Kick" หุ่นยนต์ช่วยเหลือสีขาวตาดิจิทัลฟ้า
หน้าที่ของคุณคือ: ฟังและวิเคราะห์จากไฟล์เสียง/วิดีโอที่แนบมานี้ เพื่อเขียนดราฟต์ 2 ส่วนหลัก:
1. YouTube Drafts:
   - ไอเดียชื่อคลิป (Title Options) 3-5 แบบที่ดึงดูดสายตาและมีความสร้างสรรค์ (Creative Clickbait)
   - คำอธิบายคลิปสั้น (Description Draft) สรุปใจความสำคัญ
   - ไทม์สแตมป์/บทย่อย (Chapters/Timestamps) พร้อมระบุเวลาเริ่มและหัวข้อสั้นๆ
2. Facebook Posts Draft:
   - เขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่มีมุมมองและการนำเสนอที่แตกต่างกันอย่างสิ้นเชิง

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์เนื้อหาและเขียนเนื้อหาสำหรับทั้ง 2 ส่วน
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ
3. ระหว่าง YouTube Drafts และ Facebook Posts Draft ให้ใช้หัวข้อเด่นชัดคือ "🔵 FACEBOOK POSTS DRAFT" เพื่อให้ระบบใช้ตัดข้อความได้

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - สำหรับ Facebook Posts:
- บังคับความยาว: แต่ละทางเลือกของ Facebook ต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
- บังคับไม่มีหัวข้อเขียนเล่น: ให้ระบุเพียงแค่ "ทางเลือกที่ 1:", "ทางเลือกที่ 2:", "ทางเลือกที่ 3:" แล้วตามด้วยบรรทัดเนื้อหาทันที
- เรื่องการใช้คำ (Critical Rule): ห้ามใช้คำว่า "บทเรียน" หรือ "Lesson" หรือใส่ตัวเลขบทเรียนเด็ดขาด! ให้ใช้คำว่า "หัวข้อ" หรือ "Topic" แทน และเน้นการใช้ Creative Clickbait ดึงดูดสายตาคนดู
- โครงสร้างบังคับ (Strict 4-Line Structure) สำหรับแต่ละทางเลือกของ Facebook:
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ไม่เกิน 10-12 คำ ขึ้นต้นด้วย 'เมื่อ...' เสนอ เช่น "เมื่ออยากใช้ AI ทำงานแต่ไม่รู้จะเริ่มยังไง 🤖"]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
  บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน โดยขึ้นต้นด้วย #AISidekick และตามด้วยแท็กเจาะลึกหัวข้อ, #รีวิวชีวิตทำงาน, #ชีวิตคนทำงาน, #มนุษย์เงินเดือน, #เจาะลึกอาชีพ, #วัยทำงาน]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ฉัน, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
'''
        elif queue_name == "FB_Videos_3-5Min":
            prompt = f'''คุณคือทีมงานหลังบ้านของช่อง AI Sidekick ช่องที่ช่วยให้ทุกคนทำงานร่วมกับ AI ได้อย่างมืออาชีพและง่ายขึ้น โดยมีมาสคอตคือ "น้อง Kick" หุ่นยนต์ช่วยเหลือสีขาวตาดิจิทัลฟ้า
หน้าที่ของคุณคือ: ฟังและถอดเทป/จับใจความจากไฟล์เสียง/วิดีโอที่แนบมานี้ มาเขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่จึ้งและแตกต่างกัน เพื่อให้ได้เลือกอันที่ชอบที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์และร่างโพสต์มาทั้งหมด 3 ทางเลือก (3 Options) ที่เน้นมุมมองที่แตกต่างกันอย่างสิ้นเชิง
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - สำหรับ Facebook Posts:
- บังคับความยาว: แต่ละทางเลือกต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
- บังคับไม่มีหัวข้อเขียนเล่น: ให้ระบุเพียงแค่ "ทางเลือกที่ 1:", "ทางเลือกที่ 2:", "ทางเลือกที่ 3:" แล้วตามด้วยบรรทัดเนื้อหาทันที
- เรื่องการใช้คำ (Critical Rule): ห้ามใช้คำว่า "บทเรียน" หรือ "Lesson" หรือใส่ตัวเลขบทเรียนเด็ดขาด! ให้ใช้คำว่า "หัวข้อ" หรือ "Topic" แทน และเน้นการใช้ Creative Clickbait ดึงดูดสายตาคนดู
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ไม่เกิน 10-12 คำ ขึ้นต้นด้วย 'เมื่อ...' เสนอ เช่น "เมื่ออยากใช้ AI ทำงานแต่ไม่รู้จะเริ่มยังไง 🤖"]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
  บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน โดยขึ้นต้นด้วย #AISidekick และตามด้วยแท็กเจาะลึกหัวข้อ, #รีวิวชีวิตทำงาน, #ชีวิตคนทำงาน, #มนุษย์เงินเดือน, #เจาะลึกอาชีพ, #วัยทำงาน]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ฉัน, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
'''
        else: # Reels_Under1Min
            prompt = f'''คุณคือทีมงานหลังบ้านของช่อง AI Sidekick ช่องที่ช่วยให้ทุกคนทำงานร่วมกับ AI ได้อย่างมืออาชีพและง่ายขึ้น โดยมีมาสคอตคือ "น้อง Kick" หุ่นยนต์ช่วยเหลือสีขาวตาดิจิทัลฟ้า
หน้าที่ของคุณคือ: ฟังและถอดเทป/จับใจความจากไฟล์เสียง/วิดีโอที่แนบมานี้ มาเขียนแคปชั่นสำหรับ Reels/Shorts/TikTok 3 ทางเลือก (3 Options) ที่จึ้งและสั้นกระชับที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์และร่างแคปชั่นมาทั้งหมด 3 ทางเลือก (3 Options) ที่มีมุมมองและการนำเสนอที่แตกต่างกันอย่างสิ้นเชิง
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - สำหรับแคปชั่นวิดีโอสั้น:
- บังคับความยาว: แต่ละทางเลือกต้องมีความยาวไม่เกิน 3 บรรทัด (รวมแฮชแท็ก) และสั้นกระชับมากๆ
- เรื่องการใช้คำ (Critical Rule): ห้ามใช้คำว่า "บทเรียน" หรือ "Lesson" หรือใส่ตัวเลขบทเรียนเด็ดขาด! ให้ใช้คำว่า "หัวข้อ" หรือ "Topic" แทน และเน้นการใช้ Creative Clickbait ดึงดูดสายตาคนดู
- โครงสร้างบังคับ (Strict Captions):
  บรรทัดที่ 1: [หัวข้อสั้นและดึงดูดใจมากที่สุด มีอีโมจิ 1 ตัว]
  บรรทัดที่ 2: #AISidekick และแท็กที่เกี่ยวข้อง 3-4 อัน
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ฉัน, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
'''
    else: # สำหรับ WTJ หรือ อื่นๆ
        if queue_name == "YT_Videos_Full":
            prompt = f'''\nคุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น คิดคอนเซปต์สุดล้ำ), "มิวสิค" (Marketer สาววัยรุ่น ปั้นมีมและแคมเปญสุดจึ้ง) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังและวิเคราะห์จากไฟล์เสียง/วิดีโอที่แนบมานี้ เพื่อเขียนดราฟต์ 2 ส่วนหลัก:
1. YouTube Drafts:
   - ไอเดียชื่อคลิป (Title Options) 3-5 แบบที่ดึงดูดสายตาและมีความสร้างสรรค์
   - คำอธิบายคลิปสั้น (Description Draft) สรุปใจความสำคัญ
   - ไทม์สแตมป์/บทย่อย (Chapters/Timestamps) พร้อมระบุเวลาเริ่มและหัวข้อสั้นๆ
2. Facebook Posts Draft:
   - เขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่มีมุมมองและการนำเสนอที่แตกต่างกันอย่างสิ้นเชิง

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์เนื้อหาและเขียนเนื้อหาสำหรับทั้ง 2 ส่วน
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ
3. ระหว่าง YouTube Drafts และ Facebook Posts Draft ให้ใช้หัวข้อเด่นชัดคือ "🔵 FACEBOOK POSTS DRAFT" เพื่อให้ระบบใช้ตัดข้อความได้

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - สำหรับ Facebook Posts:
- บังคับความยาว: แต่ละทางเลือกของ Facebook ต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
- บังคับไม่มีหัวข้อเขียนเล่น: ให้ระบุเพียงแค่ "ทางเลือกที่ 1:", "ทางเลือกที่ 2:", "ทางเลือกที่ 3:" แล้วตามด้วยบรรทัดเนื้อหาทันที
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ไม่เกิน 10-12 คำ ขึ้นต้นด้วย \'เมื่อ...\' เสมอ เช่น "เมื่อช่างภาพมือใหม่เจองานแรก 📸"]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
  บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน โดยขึ้นต้นด้วย #WhatTheJob และตามด้วยแท็กเจาะลึกอาชีพ, #รีวิวชีวิตทำงาน, #ชีวิตคนทำงาน, #มนุษย์เงินเดือน, #เจาะลึกอาชีพ, #วัยทำงาน]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
'''
        else: # FB_Videos_3-5Min หรือ Reels_Under1Min สำหรับ WTJ
            prompt = f'''\nคุณคือทีมงานหลังบ้านของช่อง "What the job ?" นำโดย "น้ำ" (Creative สาวมั่น คิดคอนเซปต์สุดล้ำ), "มิวสิค" (Marketer สาววัยรุ่น ปั้นมีมและแคมเปญสุดจึ้ง) และ "เรย์" (Writer มือเจียระไนคำพูด)
หน้าที่ของคุณคือ: ฟังและถอดเทป/จับใจความจากไฟล์เสียง/วิดีโอที่แนบมานี้ มาเขียนโพสต์ Facebook 3 ทางเลือก (3 Options) ที่จึ้งและแตกต่างกัน เพื่อให้พี่เก่งได้เลือกอันที่ชอบที่สุด

ขั้นตอนการทำงานของคุณ:
1. วิเคราะห์และร่างโพสต์มาทั้งหมด 3 ทางเลือก (3 Options) ที่เน้นมุมมองที่แตกต่างกันอย่างสิ้นเชิง
2. พิมพ์ระบุคิวที่เลือกไว้ที่บรรทัดแรกสุดของคำตอบในรูปแบบ: [QUEUE: {queue_name}] เพื่อยืนยันระบบ

กฎเหล็กเรื่องน้ำเสียงและรูปแบบ (Tone & Guidelines) - เน้นความสั้นและกระชับสุดๆ (Extreme Brevity):
- บังคับความยาว: แต่ละทางเลือกต้องมีความยาวรวมไม่เกิน 4 บรรทัด และห้ามมีประโยคเกริ่นนำ ห้ามทักทาย ห้ามพรรณนา ห้ามอธิบาย หรือแซวใดๆ ทั้งสิ้น!
- บังคับไม่มีหัวข้อเขียนเล่น: ให้ระบุเพียงแค่ "ทางเลือกที่ 1:", "ทางเลือกที่ 2:", "ทางเลือกที่ 3:" แล้วตามด้วยบรรทัดเนื้อหาทันที ห้ามใส่ชื่อทางเลือกหรือคำอธิบาย เช่น ห้ามใส่ ### Option 1: ฟีลแบบ... หรือคำโปรยใดๆ เด็ดขาด!
- โครงสร้างบังคับ (Strict 4-Line Structure):
  บรรทัดที่ 1: เมื่อ [สถานการณ์สั้นที่สุดในบรรทัดเดียว ไม่เกิน 10-12 คำ ขึ้นต้นด้วย \'เมื่อ...\' เสมอ เช่น "เมื่อช่างภาพมือใหม่เจองานแรก 📸"]
  บรรทัดที่ 2: "[ประโยคโควทเด็ด/คำพูดจริงสั้นๆ กระชับที่สุด 1 บรรทัด ไม่เกิน 12-15 คำ]"
  บรรทัดที่ 3: [แฮชแท็ก 5-6 อัน โดยขึ้นต้นด้วย #WhatTheJob และตามด้วยแท็กเจาะลึกอาชีพ, #รีวิวชีวิตทำงาน, #ชีวิตคนทำงาน, #มนุษย์เงินเดือน, #เจาะลึกอาชีพ, #วัยทำงาน เช่น #WhatTheJob #ช่างภาพ #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน #เจาะลึกอาชีพ]
  บรรทัดที่ 4: ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ตัวอย่างที่ถูกต้อง:
  ทางเลือกที่ 1:
  เมื่อช่างภาพมือใหม่เจองานแรก 📸
  "มั่วสูตรไปเรื่อยเลยพี่เก่ง"
  #WhatTheJob #ช่างภาพ #รีวิวชีวิตทำงาน #ชีวิตคนทำงาน #มนุษย์เงินเดือน #เจาะลึกอาชีพ
  ดูคลิปเต็มที่คอมเมนต์ปักหมุดเลยแก
- ห้ามดราม่า ห้ามเวิ่นเว้อ ห้ามมีคำอธิบายเพิ่มเติมใดๆ นอกเหนือจาก 4 บรรทัดนี้เด็ดขาด
- ห้ามแนะนำตัวแขกรับเชิญแบบเป็นทางการในวงเล็บ (เช่น อาชีพ/แบรนด์) ให้เรียกชื่อเล่นหรือคำพูดกันอย่างเป็นธรรมชาติ
- ห้ามใช้คำลงท้าย "ครับ/ค่ะ" ในคำบรรยายปกติ (ใช้ได้เฉพาะในประโยคโควทจริงเท่านั้น)
- ใช้สรรพนามเป็นกันเองสไตล์เพื่อนสนิท (แก/ชั้น, จ้า, นะจ๊ะ, ตัวแม่, ปัง, เกินต้าน)

เว้นวรรคจัดย่อหน้าให้อ่านง่าย สบายตา มีอีโมจิประกอบพอดีๆ ห้ามเขียนเป็นแพยาว
'''

    response = client.models.generate_content(model = 'gemini-2.5-flash', contents = [
        file_ref,
        prompt])
    return response.text


def process_single_file(file_path, queue_name):
    filename = os.path.basename(file_path)
    print(f"\n🎬 เริ่มการประมวลผลไฟล์: '{filename}' สำหรับคิว '{queue_name}'")
    wait_for_file_to_stabilize(file_path)
    
    file_ext = os.path.splitext(file_path)[1]
    temp_filename = f"temp_upload_{int(time.time())}{file_ext}"
    temp_file_path = os.path.join(os.path.dirname(file_path), temp_filename)
    
    myfile = None
    try:
        print("📦 คัดลอกไฟล์ชั่วคราวเพื่อแก้บั๊กอัปโหลดไฟล์ภาษาไทย...")
        shutil.copy2(file_path, temp_file_path)
        
        print("🚀 กำลังอัปโหลดไฟล์ขึ้นระบบคลาวด์ Gemini...")
        myfile = client.files.upload(file=temp_file_path)
        print(f"✅ อัปโหลดสำเร็จ (File ID: {myfile.name})")
    except Exception as e:
        print(f"❌ คัดลอก/อัปโหลดไฟล์ล้มเหลว: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return False

    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

    if not myfile:
        print("❌ ล้มเหลวในการอัปโหลดไฟล์")
        return False

    try:
        print("⏳ รอคลาวด์แปลงไฟล์และประมวลผล...")
        start_time = time.time()
        timeout = 300
        while True:
            myfile = client.files.get(name=myfile.name)
            if myfile.state.name == "ACTIVE":
                print("⚡ ไฟล์พร้อมประมวลผล (Active) แล้ว!")
                break
            elif myfile.state.name == "FAILED":
                raise ValueError(f"การแปลงไฟล์ล้มเหลว: {myfile.error}")
            
            if time.time() - start_time > timeout:
                raise TimeoutError("หมดเวลารอแปลงไฟล์ (Timeout 5 นาที)")
                
            time.sleep(5)
            
        generated_text = generate_social_posts(myfile, filename, queue_name)
        if not generated_text:
            print("❌ ล้มเหลว: ไม่สามารถผลิตเนื้อหาได้")
            if myfile:
                print("🧹 ลบไฟล์ชั่วคราวออกจากคลาวด์ Gemini...")
                try:
                    client.files.delete(name=myfile.name)
                    print("✅ ลบเรียบร้อย!")
                except Exception as de:
                    print(f"⚠️ ไม่สามารถลบไฟล์ชั่วคราวบนคลาวด์ได้: {de}")
            return False
            
        clean_draft_text = re.sub(r'\[QUEUE:\s*[\w\-]+\]\n?', '', generated_text).strip()
        
        print(f"\n🔮 ผลลัพธ์การร่างสำหรับคิว: {queue_name}")
        print("\n--- 📝 ผลลัพธ์โซเชียลดราฟต์ ---")
        print(clean_draft_text)
        print("----------------------------\n")
        
        os.makedirs(DRAFTS_DIR, exist_ok=True)
        file_slug = re.sub(r'[^\w\s-]', '', filename).strip().replace(" ", "_").lower()
        backup_filename = f"{queue_name.lower()}_from_video_{file_slug}.md"
        backup_path = os.path.join(DRAFTS_DIR, backup_filename)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(clean_draft_text)
        print(f"💾 บันทึกไฟล์ร่างสำรองที่: {backup_path}")
        
        print("🚀 กำลังส่งดราฟต์วิดีโอไปสร้างหน้าการ์ดใหม่ใน Notion...")
        try:
            db_id = None
            if PROJECT_TYPE == "sidekick":
                db_id = os.environ.get("NOTION_AI_SIDEKICK_DATABASE_ID")
                print(f"ℹ️ ใช้ Database ID สำหรับ AI Sidekick: {db_id}")
            notion = NotionHelper(database_id=db_id)
            platform_tags = []
            if queue_name == "Reels_Under1Min":
                platform_tags = ["Reels"]
            elif queue_name == "FB_Videos_3-5Min":
                platform_tags = ["FB_Video"]
            elif queue_name in ["YT_Videos_Full", "FB_Videos_Full"]:
                platform_tags = ["YT_Video"] if PROJECT_TYPE == "sidekick" else ["YouTube"]
                
            title_notion = f"[{queue_name} Video Draft] {filename}"
            status_name = "3_Reviewing" if PROJECT_TYPE == "sidekick" else "4_Review"
            
            # 1. สร้างการ์ดหลัก
            new_page = notion.create_page(title_notion, status_name=status_name, platform_tags=platform_tags)
            if new_page and "id" in new_page:
                page_id = new_page["id"]
                
                # ข้อความทั้งหมด
                page_content_to_write = clean_draft_text
                
                # ลอจิกแยกสปอยเลอร์
                fb_headers = [
                    "🔵 FACEBOOK POSTS DRAFT", 
                    "# FACEBOOK POSTS DRAFT", 
                    "FACEBOOK POSTS DRAFT",
                    "# 🔵 FACEBOOK POSTS",
                    "🔵 FACEBOOK POSTS",
                    "# 🔵 FACEBOOK POST",
                    "🔵 FACEBOOK POST",
                    "# FACEBOOK POSTS",
                    "# FACEBOOK POST"
                ]
                
                fb_posts_content = ""
                has_split = False
                
                if queue_name in ["YT_Videos_Full", "FB_Videos_Full"]:
                    for header in fb_headers:
                        if header in clean_draft_text:
                            parts = clean_draft_text.split(header, 1)
                            page_content_to_write = parts[0].strip()
                            fb_posts_content = parts[1].strip()
                            has_split = True
                            break
                
                # หากเป็น Sidekick และเป็นวิดีโอเต็ม ให้ต่อท้ายด้วยเทมเพลตคำอธิบายช่อง
                if PROJECT_TYPE == "sidekick" and queue_name in ["YT_Videos_Full", "FB_Videos_Full"]:
                    template = """📲 ติดตามช่องทางอื่นๆ ของพวกเรา AI Sidekick
• Facebook Page: https://www.facebook.com/AISidekick
• ติดต่อโฆษณา/สปอนเซอร์: ghn168media@gmail.com
-----------------------------------------------------

ถ้าอยากให้พวกเรานำเสนอหัวข้อ AI อะไร หรือมีข้อสงสัยตรงไหน คอมเมนต์บอกพวกเราไว้ใต้คลิปได้เลยนะแก!

#AISidekick #NongKick #AIสำหรับทุกคน #ชีวิตทำงาน #รีวิวชีวิตทำงาน #วัยทำงาน"""
                    page_content_to_write = page_content_to_write + "\n\n" + template
                
                # บันทึกเนื้อหาลงการ์ดหลัก
                headline = f"[{queue_name} Video Draft] {filename}\n\n"
                notion.write_page_content_text(page_id, headline + page_content_to_write)
                print(f"✅ สร้างการ์ดและบันทึกเนื้อหาลง Notion สำเร็จแล้วแก! (Page ID: {page_id})")
                
                # 2. ถ้าเป็นวิดีโอตัวเต็ม และมีโพสต์ Facebook แยกออกมา ให้สร้างการ์ดสปอยเลอร์ (ยกเว้นโปรเจกต์ sidekick)
                if queue_name in ["YT_Videos_Full", "FB_Videos_Full"] and has_split and PROJECT_TYPE != "sidekick":
                    print("🚀 กำลังสร้างการ์ดสปอยล์ (Spoiler) ใน Notion...")
                    try:
                        if not fb_posts_content:
                            fb_posts_content = clean_draft_text
                        
                        if PROJECT_TYPE == "sidekick":
                            spoiler_title = f"[Spoiler_Sidekick] {filename}"
                            replacement_cta = "รอติดตามชมคลิปเต็มได้เร็วๆ นี้ น้าแก!"
                            spoiler_status = "3_Reviewing"
                            spoiler_tags = ["FB_Text_Quote"]
                        elif PROJECT_TYPE == "story":
                            spoiler_title = f"[Spoiler_SUN] {filename}"
                            replacement_cta = "รอติดตามชมคลิปเต็มได้เย็นนี้ เวลา 18:00 น. น้าแก!"
                            spoiler_status = "4_Review"
                            spoiler_tags = ["FB_Text_Quote"]
                        else:  # podcast หรืออื่นๆ
                            spoiler_title = f"[Spoiler_THU] {filename}"
                            replacement_cta = "รอติดตามชมคลิปเต็มได้คืนนี้ เวลา 20:00 น. น้าแก!"
                            spoiler_status = "4_Review"
                            spoiler_tags = ["FB_Text_Quote"]
                        
                        # เปลี่ยน CTA ท้ายโพสต์
                        fb_posts_content_modified = []
                        for line in fb_posts_content.splitlines():
                            if re.search(r"ดูคลิปเต็ม|ปักหมุดเลยแก|คลิปเต็มได้ที่|คอมเมนต์ปักหมุด", line):
                                line = replacement_cta
                            fb_posts_content_modified.append(line)
                        fb_posts_content = "\n".join(fb_posts_content_modified)
                        
                        # สร้างการ์ดสปอยเลอร์
                        spoiler_page = notion.create_page(spoiler_title, status_name=spoiler_status, platform_tags=spoiler_tags)
                        if spoiler_page and "id" in spoiler_page:
                            spoiler_page_id = spoiler_page["id"]
                            headline_spoiler = f"[{queue_name} Video Draft] {filename}\n\n"
                            notion.write_page_content_text(spoiler_page_id, headline_spoiler + fb_posts_content)
                            
                            # บันทึกไฟล์ร่างสำรองของสปอยเลอร์
                            backup_filename_spoiler = f"spoiler_from_video_{file_slug}.md"
                            backup_path_spoiler = os.path.join(DRAFTS_DIR, backup_filename_spoiler)
                            with open(backup_path_spoiler, "w", encoding="utf-8") as f:
                                f.write(fb_posts_content)
                            print(f"✅ สร้างการ์ดสปอยล์สำเร็จแล้วแก! (Page ID: {spoiler_page_id})")
                        else:
                            print("❌ ล้มเหลว: ไม่สามารถสร้างการ์ดสปอยล์ใน Notion ได้")
                    except Exception as ex:
                        print(f"⚠️ เกิดข้อผิดพลาดในการสร้างการ์ดสปอยล์: {ex}")
            else:
                print("❌ ล้มเหลว: ไม่สามารถสร้างหน้าใหม่ in Notion ได้")
        except Exception as ne:
            print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Notion: {ne}")

        # ย้ายไฟล์วิดีโอดิบไป processed
        queue_folder_path = os.path.dirname(file_path)
        processed_dir = os.path.join(queue_folder_path, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        processed_path = os.path.join(processed_dir, filename)
        if os.path.exists(file_path):
            os.rename(file_path, processed_path)
            print(f"📦 ย้ายไฟล์วิดีโอไปที่ {processed_dir} เรียบร้อยจ้า!")
        else:
            print("⚠️ ไฟล์วิดีโอถูกย้ายหรือประมวลผลโดยระบบอื่นแล้วแก!")
            
        return True
            
    finally:
        if myfile:
            print("🧹 ลบไฟล์ชั่วคราวออกจากคลาวด์ Gemini...")
            try:
                client.files.delete(name=myfile.name)
                print("✅ ลบเรียบร้อย!")
            except Exception as e:
                print(f"⚠️ ไม่สามารถลบไฟล์ชั่วคราวบนคลาวด์ได้ (ระบบจะลบให้อัตโนมัติใน 48 ชม.): {e}")


def main():
    global PROJECT_TYPE, RAW_VIDEOS_DIR, DRAFTS_DIR
    
    parser = argparse.ArgumentParser(description="WTJ Video Auto-Transcriber & Drafter Pipeline")
    parser.add_argument("--project", type=str, default="story", choices=["story", "podcast", "sidekick"], help="Project type")
    args = parser.parse_args()
    
    PROJECT_TYPE = args.project
    
    print('==================================================')
    print(f'🎬 WTJ Video Auto-Transcriber & Drafter Pipeline ({PROJECT_TYPE.upper()})')
    print('==================================================')
    
    if PROJECT_TYPE == "sidekick":
        RAW_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'AI_Sidekick_Project', 'workspace', '1_raw_materials')
        DRAFTS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'AI_Sidekick_Project', 'workspace', '2_drafts')
    elif PROJECT_TYPE == "podcast":
        RAW_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Podcast', 'workspace', '1_raw_materials')
        DRAFTS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Podcast', 'workspace', '2_drafts')
    else:
        RAW_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Story', 'workspace', '1_raw_materials')
        DRAFTS_DIR = os.path.join(PROJECT_ROOT, 'Team_Content_Studio', 'Team_Agent_Content', 'WTJ_Project', 'WTJ_Story', 'workspace', '2_drafts')
        
    reels_dir = os.path.join(RAW_VIDEOS_DIR, 'raw_vdo_short')
    fb_videos_dir = os.path.join(RAW_VIDEOS_DIR, 'raw_vdo_3-5min')
    fb_full_dir = os.path.join(RAW_VIDEOS_DIR, 'raw_vdo_full')
    
    os.makedirs(reels_dir, exist_ok = True)
    os.makedirs(fb_videos_dir, exist_ok = True)
    os.makedirs(fb_full_dir, exist_ok = True)
    os.makedirs(os.path.join(reels_dir, 'processed'), exist_ok = True)
    os.makedirs(os.path.join(fb_videos_dir, 'processed'), exist_ok = True)
    os.makedirs(os.path.join(fb_full_dir, 'processed'), exist_ok = True)
    
    targets = [
        (reels_dir, 'Reels_Under1Min'),
        (fb_videos_dir, 'FB_Videos_3-5Min'),
        (fb_full_dir, 'YT_Videos_Full')]
        
    total_files = 0
    processed_count = 0
    
    for folder, queue_name in targets:
        files = sorted([f for f in os.listdir(folder) if f.lower().endswith(MEDIA_EXTENSIONS)])
        if not files:
            continue
        print(f"\n🔍 ตรวจพบไฟล์ใหม่ใน '{os.path.basename(folder)}' (สำหรับคิว {queue_name}) จำนวน {len(files)} ไฟล์:")
        for f in files:
            print(f"   - {f}")
            total_files += 1
            file_path = os.path.join(folder, f)
            if process_single_file(file_path, queue_name):
                processed_count += 1
                
    if total_files == 0:
        print(f'📭 ไม่พบไฟล์วิดีโอหรือไฟล์เสียงใหม่ใน raw_vdo_short/, raw_vdo_3-5min/ หรือ raw_vdo_full/ ของโปรเจกต์ {PROJECT_TYPE} เลยแก')
        return None
    print(f"\n🎉 ดำเนินการเสร็จสิ้น! ประมวลผลสำเร็จ {processed_count}/{total_files} ไฟล์จ้า!")

if __name__ == '__main__':
    main()
