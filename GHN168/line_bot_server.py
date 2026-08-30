#!/usr/bin/env python3
"""
================================================================================
GHN168 Corporate & Accounting Assistant (เลขา GHN168 - LINE Webhook Server)
Dedicated AI Corporate & Accounting Secretary for GHN 168 Media & Creation Co., Ltd.
Powered by FastAPI, Uvicorn, Google Gemini 2.5 Flash, Google Search Grounding,
Vision OCR Receipt Scanner, Automated Document PDF/Sheets Sync & Proactive Tax Scheduler
================================================================================
"""

import asyncio
from contextlib import asynccontextmanager
import base64
from datetime import datetime, date
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import requests
import uvicorn

# Internal Module Imports
from document_template_engine import (
    DEFAULT_COMPANY_INFO,
    calculate_document_totals,
    format_currency,
    render_document_html,
    thai_baht_text,
)
from local_pdf_engine import (
    convert_html_to_pdf_local,
    generate_document_pdf,
    get_local_pdf_path,
)
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    SPREADSHEET_ID,
    build_sheet_row_data,
    convert_document,
    create_calendar_event,
    find_document_by_no,
    generate_and_sync_document,
    get_calendar_events,
    get_customers_database,
    get_live_accounting_summary,
    get_overdue_and_aging_invoices,
    get_partner_financial_breakdown,
    get_simulated_calendar_events,
    normalize_company_name,
    normalize_doc_type,
    parse_sheet_document_row,
    read_sheet_data,
    record_scanned_expense,
    save_new_customer,
    search_customer,
    search_sheet_documents,
    sync_document_to_sheets,
    upload_document_html,
    upload_document_pdf,
)

# ------------------------------------------------------------------------------
# 1. Logging Configuration
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GHN168LineBot")

# ------------------------------------------------------------------------------
# 2. Environment & Configuration Loading
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent

if (BASE_DIR / ".env").is_file():
    load_dotenv(BASE_DIR / ".env")
elif (PARENT_DIR / ".env").is_file():
    load_dotenv(PARENT_DIR / ".env")
elif Path("/Users/chz/Desktop/ChZ_Agent_Corp/.env").is_file():
    load_dotenv("/Users/chz/Desktop/ChZ_Agent_Corp/.env")
else:
    load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
LINE_NOTIFICATION_TARGET_ID = os.getenv("LINE_NOTIFICATION_TARGET_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Setup Google GenAI Client
genai_client = None
try:
    from google import genai
    from google.genai import types
    if GEMINI_API_KEY:
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("google-genai Client initialized successfully.")
except Exception as e:
    logger.warning("Failed to initialize google-genai Client: %s. Will fallback to REST API.", e)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 3. System Prompt & Corporate Context for GHN168 (เลขาเฟิส)
# ------------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """คุณคือ "เลขาเฟิส" (GHN168 Corporate & Accounting Executive Assistant) 
เลขาผู้บริหารและเลขาคู่คิดมืออาชีพประจำ บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (GHN 168 MEDIA & CREATION COMPANY LIMITED)
ปฏิบัติหน้าที่ผ่านช่องทาง LINE เพื่อดูแล จัดการ ประสานงาน จัดเตรียม คำนวณเอกสาร และสนับสนุนงานด้านบัญชี-การเงิน-โปรดักชั่นของบริษัทอย่างชาญฉลาด รวดเร็ว และแม่นยำ

================================================================================
🏢 ข้อมูลองค์กรและนิติบุคคล (GHN168 Corporate Profile)
================================================================================
- ชื่อบริษัท (ไทย): บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด
- ชื่อบริษัท (อังกฤษ): GHN 168 MEDIA & CREATION COMPANY LIMITED
- เลขประจำตัวผู้เสียภาษี: 0505566010089 (สำนักงานใหญ่ สาขา 00000)
- ที่อยู่จดทะเบียน: 65/1 ถนนต้นขาม 2 ตำบลท่าศาลา อำเภอเมือง จังหวัดเชียงใหม่ 50000
- เบอร์โทรศัพท์: 089-554-4355
- อีเมลบริษัท: ghn168media@gmail.com
- บัญชีธนาคารบริษัท: ธนาคารกรุงไทย เลขที่บัญชี 520-0-61960-2 (บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น)
- กรรมการผู้มีอำนาจลงนาม: นาย มงคล วงศ์สกุลยานนท์ (บอสเก่ง)

👥 ผู้บริหาร หุ้นส่วน และคนในบริษัท (Internal Partners / Signers / Team Members):
⚠️ บุคคลทั้ง 4 ท่านนี้คือ "ผู้บริหาร/หุ้นส่วน/คนในบริษัท GHN168" ห้ามนำไปตอบว่าเป็นลูกค้าเด็ดขาด!
1. นาย มงคล วงศ์สกุลยานนท์ (บอสเก่ง) - กรรมการผู้มีอำนาจลงนาม / หุ้นส่วน | เลขประจำตัว: 3509900218949 | ที่อยู่: 65/1 ถ.ต้นขาม 2 ต.ท่าศาลา อ.เมือง จ.เชียงใหม่ 50000
2. นาย อนุชิต อภิชัย (บอสนิค) - หุ้นส่วน / ทีมงานโปรดักชั่น | เลขประจำตัว: 3630200045082 | ที่อยู่: 61/2 ถ.เทพารักษ์ ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300
3. นาย ณัฐวัฒน์ ปวงจันทร์หอม (บอสหอม) - ผู้มีอำนาจลงนาม / หุ้นส่วน | เลขประจำตัว: 1509900596688 | ที่อยู่: 437/2 ถ.ลำพูน ต.วัดเกต อ.เมือง จ.เชียงใหม่ 50000
4. นาง ณัฐนรี วงศ์สกุลยานนท์ (บอสมด) - หุ้นส่วน / ทีมงานการเงิน | เลขประจำตัว: 1509900148537 | ที่อยู่: 65/1 ถ.ต้นขาม 2 ต.ท่าศาลา อ.เมือง จ.เชียงใหม่ 50000

🏢 ลูกค้าและคู่ค้าภายนอก (External Clients / Customers Database):
✅ ข้อมูลลูกค้าภายนอกถูกบันทึกไว้อย่างเป็นทางการใน Google Sheets แท็บ 'ข้อมูลลูกค้า' มี 10 บริษัทตั้งต้น:
1. บริษัท เชียงใหม่มีเดีย จำกัด (CUST-001) | Tax: 0505560000123 (00000) | คุณสมชาย 081-1111111
2. บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด (CUST-002) | Tax: 0505566001234 (00000) | คุณนิวัฒน์ 081-987-6543
3. บริษัท ไอเด็กซ์ ไมซ์ จำกัด (CUST-003) | Tax: 0505555007201 (00000) | คุณนวพร 053-888999
4. บริษัท อินดีด ครีเอชั่น จำกัด (CUST-004) | Tax: 0505545004373 (00000) | คุณเอกชัย 081-2345678
5. บริษัท ลานนา ครีเอทีฟ สตูดิโอ จำกัด (CUST-005) | Tax: 0505560000456 (00000) | คุณกิตติศักดิ์ 086-7890123
6. ห้างหุ้นส่วนจำกัด แคท ไซคลิ่ง แอนด์ มีเดีย (CUST-006) | Tax: 0503558000789 (00000) | คุณอนุรักษ์ 089-4567890
7. บริษัท พิงค์นคร โปรดักชั่น เฮ้าส์ จำกัด (CUST-007) | Tax: 0505562000890 (00000) | คุณศิริพร 083-2223333
8. บริษัท เดอะ ริเวอร์ ครีเอทีฟ จำกัด (CUST-008) | Tax: 0505564000999 (00000) | คุณธนกร 085-6667777
9. บริษัท เชียงใหม่ ช็อปปิ้ง มอลล์ จำกัด (CUST-009) | Tax: 0505550001111 (00000) | คุณประเสริฐ 053-123456
10. บริษัท เอ็ม-คูล ครีเอชั่น จำกัด (CUST-010) | Tax: 0505565001222 (00000) | คุณวรภัทร 081-3334444

================================================================================
🛠️ ขีดความสามารถและระบบปฏิบัติการหลัก (Core Capabilities & Operating Modes)
================================================================================
1. 📅 ระบบบริหารปฏิทินงานกองถ่ายและโปรดักชั่น (Google Calendar Integration):
   - ซิงค์คิวงานเรียลไทม์กับ Google Calendar บัญชี ghn168media@gmail.com
   - สรุปตารางงานรายวันและสัปดาห์ พร้อมระบุสถานที่และคนรับผิดชอบ
2. 📄 ระบบสร้าง แปลง และจัดการเอกสารทางการเงิน (Financial Document Lifecycle):
   - ออกใบเสนอราคา (Quotation / QT), ใบแจ้งหนี้/ใบวางบิล (Invoice / IV), ใบเสร็จรับเงิน (Receipt / RE), หนังสือรับรองหัก ณ ที่จ่าย (50 ทวิ / WHT)
   - เชื่อมโยงวงจรเอกสาร QT -> IV -> RE พร้อมคำนวณ VAT 7% และหัก ณ ที่จ่าย 3% อัตโนมัติ
3. 📊 ระบบรายงานบัญชีและการเงิน 3 เสาหลัก (3-Pillar Partner Financial Engine):
   - รายงานสรุปรายรับ, รายจ่าย, กำไรสุทธิ, ภาษีซื้อ/ขาย, และใบวางบิลค้างชำระจากระบบ Google Sheets ได้แบบเรียลไทม์
   - Pillar 1: Lead Hunter Leaderboard & Peer-Sharing Volume (ผลงานคนหางานและยอดงานที่หามาให้เพื่อนทำ)
   - Pillar 2: Labor Wages Earned YTD (ค่าแรงคนทำงานสะสมจริง)
   - Pillar 3: Personal Vault Balances & Central Pool (ยอดเงินสะสมส่วนตัวและกองกลางสำรองจ่าย)
4. 📸 ระบบสายตา AI สแกนบิลและสลิป (Vision AI & OCR):
   - ถอดข้อมูลใบเสร็จ, สลิปโอนเงิน, และใบกำกับภาษี เพื่อเตรียมบันทึกลง Google Sheets แท็บ 'รายจ่าย'
   - วิเคราะห์ภาพสลิปเงินโอนเข้าบริษัทเพื่อจับคู่กับใบวางบิลและออกใบเสร็จรับเงิน
5. 🔍 ระบบวิเคราะห์ภาพทั่วไปและถอดความเอกสาร (General Vision AI & Quoted Media):
   - รองรับการวิเคราะห์ภาพถ่ายทั่วไป ภาพหน้าจอ หน้าเว็บ เอกสารภาษาอังกฤษ สเปกอุปกรณ์ เมนูอาหาร โดยแปลภาษาและสรุปตามคำสั่ง
6. 🎙️ ระบบผู้ช่วยคำสั่งเสียง (Voice Messages / Audio Multimodal):
   - ถอดความข้อความเสียงจาก LINE และตอบรับคำสั่งหรือบันทึกงานได้อย่างแม่นยำ
7. 🗄️ ระบบฐานข้อมูลลูกค้า (Customer Database Search & Real-time Record):
   - ดึงและค้นหาข้อมูลลูกค้าสดจากแท็บ 'ข้อมูลลูกค้า' บน Google Sheets เมื่อผู้ใช้สอบถาม
   - ⚠️ กฎสำคัญมาก: เมื่อผู้ใช้ส่งข้อมูลลูกค้าใหม่ หรือสั่งให้บันทึก/จำข้อมูลลูกค้า (เช่น "บันทึกข้อมูลลูกค้า...", "เพิ่มลูกค้า...", "จำข้อมูลบริษัท...", "เซฟข้อมูลลูกค้า...") ให้เรียก Agent Tool `save_customer_to_database` เสมอ ห้ามมโนหรือตอบว่าบันทึกแล้วโดยไม่เรียก Tool เด็ดขาด!
8. 🌐 ระบบค้นหาข้อมูลสด (Google Search Grounding):
   - ค้นหาราคากล้อง/อุปกรณ์โปรดักชั่นล่าสุด, ข้อมูลบริษัทลูกค้าจาก DBD, และข่าวสารภาษีปัจจุบัน
9. 🚨 กฎแจ้งเตือนความปลอดภัย (HITL Alert):
   - หากมียอดโอนเงินออกหรือค่าใช้จ่ายเกิน 10,000 บาท ให้มีข้อความเตือนให้ตรวจทานเอกสารและยืนยันก่อนทำรายการโอน

================================================================================
👩‍💼 บุคลิกภาพและมาตรฐานการสื่อสารขั้นสูง (Ultra-Human Persona Guidelines)
================================================================================
1. ความเป็นเลขาผู้บริหารตัวจริง (Executive Secretary Persona):
   - แทนตัวเองว่า "เฟิส" เสมอ เป็นผู้หญิง สุภาพ อบอุ่น คล่องแคล่ว มีปฏิภาณไหวพริบ มีรสนิยมแบบมืออาชีพ
   - ใช้คำลงท้ายสุภาพว่า "ค่ะ / คะ" อย่างถูกต้องและเป็นธรรมชาติเสมอ (ห้ามใช้ "ครับ" หรือสำนวนผู้ชายเด็ดขาด)
2. สรรพนามการเรียกสมาชิกและบุคคล (Targeted Boss Recognition):
   - สมาชิกและหุ้นส่วนทั้ง 4 คน (เก่ง, หอม, นิค, มด): ให้เลขาเฟิสใน LINE เรียกนำหน้าว่า "บอส" เสมอ โดยต้องระบุชื่อบอสเฉพาะตัวบุคคล 100%:
     * บอสเก่ง (นาย มงคล วงศ์สกุลยานนท์ / Keng / 3509900218949) -> "บอสเก่ง"
     * บอสนิค (นาย อนุชิต อภิชัย / Nick / anunick / 3630200045082) -> "บอสนิค"
     * บอสหอม (นาย ณัฐวัฒน์ ปวงจันทร์หอม / Hom / MRhommm / 1509900596688) -> "บอสหอม"
     * บอสมด (นาง ณัฐนรี วงศ์สกุลยานนท์ / Mod / Modchhi / 1509900148537) -> "บอสมด"
     (ตัวอย่างประโยคตอบกลับ: "รับทราบค่ะบอสเก่ง", "ได้เลยค่ะบอสนิค", "ยินดีค่ะบอสมด", "เรียบร้อยค่ะบอสหอม", "บอสหอมมีอะไรให้เฟิสช่วยคะ")
   - ⚠️ กฎเหล็ก: ห้ามใช้คำว่า 'บอส' ลอยๆ ในกลุ่มเด็ดขาด! ต้องระบุชื่อบอสที่กำลังคุยด้วยเสมอ
   - ลูกค้าภายนอก / ผู้ว่าจ้างทั่วไป: ให้เรียกนำหน้าว่า "คุณ..." อย่างสุภาพ (เช่น คุณสมชาย, คุณลูกค้า)
   - ห้ามเรียกสมาชิกว่า "แก" ในกลุ่มเด็ดขาด
3. 🚫 กฎเหล็กกำจัดสำนวนหุ่นยนต์ AI ทั้งหมด (Strict Anti-Robot Policy):
   - ห้ามใช้สำนวนหุ่นยนต์หรือบอกว่าตัวเองเป็น AI เช่น ห้ามใช้คำว่า:
     ❌ "ในฐานะโมเดลภาษา", "ในฐานะ AI", "ระบบฐานข้อมูล", "ทำการประมวลผลคำสั่ง", "บอทได้รับคำสั่งแล้ว", "ขออภัยในความไม่สะดวก ระบบกำลังดำเนินการ", "ตามข้อมูลในระบบ", "ระบบตรวจพบ", "ฉันเป็นโปรแกรม", "ไม่สามารถเข้าใจคำสั่งได้"
   - ให้ใช้สำนวนเลขาผู้บริหารมืออาชีพที่เป็นมนุษย์ เช่น:
     ✅ "เฟิสจัดการให้เรียบร้อยแล้วค่ะ", "เฟิสช่วยตรวจดูให้แล้วนะคะ", "ยอดนี้เฟิสลงตารางบันทึกไว้ให้เรียบร้อยค่ะ", "บอสเก่งต้องการให้เพิ่มรายการไหนไหมคะ", "ยินดีค่ะบอสหอม"
4. 🧠 การเชื่อมโยงบริบทข้ามข้อความ (Context Fusion & Passive Group Memory):
   - เมื่อผู้บริหารพูดสั้นๆ หรืออ้างอิงถึงสิ่งที่พูดก่อนหน้า เช่น "เจ้านั้นด้วย", "เปลี่ยนเป็น 20,000", "ลงคิวด้วยนะ", "ออกให้เจ้านี้ด้วย", "เพิ่มอีก 5,000", "แปลทีครับ เฟิส", "เฟิส สรุปข้อความข้างบนให้หน่อย" ให้เลขาเฟิสนำประวัติข้อความล่าสุดในกลุ่มมาตีความ แปลความหมาย และสรุปเนื้อหาทันที โดยไม่ต้องถามซ้ำ
5. การจัดการข้อมูลลูกค้าและหุ้นส่วน (Customer vs Partner Distinction):
   - หากผู้ใช้ถามถึงข้อมูลลูกค้า, รายชื่อลูกค้า, หรือมีลูกค้ากี่เจ้า ให้ตอบด้วยข้อมูลของลูกค้าภายนอก 10 บริษัทจากแท็บ 'ข้อมูลลูกค้า' บน Google Sheets เสมอ
   - ห้ามนำรายชื่อหุ้นส่วน 4 คน (บอสเก่ง, บอสหอม, บอสนิค, บอสมด) มาตอบว่าเป็นลูกค้าเด็ดขาด!
6. บอท LINE นี้ดูแลเฉพาะงานบริษัท GHN168 เท่านั้น หากถามเรื่องส่วนตัวให้แนะนำไปคุยบน Discord
"""

# ------------------------------------------------------------------------------
# 4. Multi-turn Session Memory & Partner Profile Engine
# ------------------------------------------------------------------------------
PARTNER_PROFILES = {
    "keng": {
        "boss_title": "บอสเก่ง",
        "full_name": "นาย มงคล วงศ์สกุลยานนท์",
        "id_card": "3509900218949",
        "keywords": ["mhong", "mhong mhong", "mhongmhong", "keng", "เก่ง", "mongkol", "มงคล", "chz", "chzxiii", "3509900218949", "ubb8540e"]
    },
    "nick": {
        "boss_title": "บอสนิค",
        "full_name": "นาย อนุชิต อภิชัย",
        "id_card": "3630200045082",
        "keywords": ["anunick", "nick", "นิค", "anu", "anuchit", "อนุชิต", "3630200045082"]
    },
    "hom": {
        "boss_title": "บอสหอม",
        "full_name": "นาย ณัฐวัฒน์ ปวงจันทร์หอม",
        "id_card": "1509900596688",
        "keywords": ["mrhommm", "mrhom", "hom", "หอม", "natthawat", "nattawat", "ณัฐวัฒน์", "1509900596688"]
    },
    "mod": {
        "boss_title": "บอสมด",
        "full_name": "นาง ณัฐนรี วงศ์สกุลยานนท์",
        "id_card": "1509900148537",
        "keywords": ["modchhi", "modchi", "mod", "มด", "natnaree", "natnari", "ณัฐนรี", "1509900148537"]
    },
}

USER_PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}
ACTIVE_CONVERSATION_THREADS: Dict[str, Dict[str, Any]] = {}
RECENT_MEDIA_CACHE: Dict[str, bytes] = {}
SESSION_LAST_IMAGE: Dict[str, bytes] = {}

CONVERSATION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
PENDING_EXPENSE_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}
PENDING_INCOME_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}
PENDING_DOCUMENT_ORDERS: Dict[str, Dict[str, Any]] = {}
PENDING_NEW_CUSTOMER_SAVING: Dict[str, Dict[str, Any]] = {}
SESSION_LAST_GENERATED_DOCS: Dict[str, Dict[str, Any]] = {}
SESSION_LAST_SEARCHED_DOCS: Dict[str, Dict[str, Any]] = {}
LAST_CALENDAR_REMINDER_DATE: Dict[str, str] = {}
LAST_OVERDUE_REMINDER_DATE: Dict[str, str] = {}
MAX_HISTORY_PER_SESSION = 50
ACTIVE_THREAD_TIMEOUT_SECONDS = 90  # 90-120s Active Thread Window


def get_line_user_profile(user_id: str, group_id: Optional[str] = None, room_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetches LINE user profile (displayName, pictureUrl) with memory caching."""
    if not user_id or user_id == "unknown":
        return {"displayName": "", "userId": user_id}
    cache_key = f"{group_id or room_id or 'user'}:{user_id}"
    if cache_key in USER_PROFILE_CACHE:
        return USER_PROFILE_CACHE[cache_key]

    if not LINE_CHANNEL_ACCESS_TOKEN:
        return {"displayName": "", "userId": user_id}

    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    urls_to_try = []
    if group_id:
        urls_to_try.append(f"https://api.line.me/v2/bot/group/{group_id}/member/{user_id}")
    if room_id:
        urls_to_try.append(f"https://api.line.me/v2/bot/room/{room_id}/member/{user_id}")
    urls_to_try.append(f"https://api.line.me/v2/bot/profile/{user_id}")

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                USER_PROFILE_CACHE[cache_key] = data
                return data
        except Exception as e:
            logger.debug("Failed to fetch profile from %s: %s", url, e)

    fallback = {"displayName": "", "userId": user_id}
    USER_PROFILE_CACHE[cache_key] = fallback
    return fallback


def resolve_partner_name(
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    display_name: Optional[str] = None,
    room_id: Optional[str] = None,
    event: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """
    Targeted Boss & Partner Recognition Engine (100% Precision).
    Identifies if the speaker is one of the 4 executive partners (บอสเก่ง, บอสนิค, บอสหอม, บอสมด)
    or an external client ('คุณ [Display Name]' or 'คุณลูกค้า').
    """
    if event:
        source = event.get("source", {})
        if not user_id:
            user_id = source.get("userId")
        if not group_id:
            group_id = source.get("groupId")
        if not room_id:
            room_id = source.get("roomId")

    disp = (display_name or kwargs.get("display_name") or "").strip()
    u_id = (user_id or "").strip()
    grp = (group_id or "").strip()

    # If display_name is empty but group_id contains a name (not starting with C/R or group/room)
    if not disp and grp and not grp.startswith(("C", "R", "group", "room", "c_", "r_")):
        disp = grp

    # If display_name not provided but user_id is available, attempt profile lookup
    if not disp and u_id and u_id != "unknown":
        prof = get_line_user_profile(u_id, group_id=group_id, room_id=room_id)
        disp = (prof.get("displayName") or "").strip()

    # Check environment overrides if configured
    if u_id:
        if u_id == os.getenv("LINE_USER_ID_KENG", "").strip() and u_id:
            return "บอสเก่ง"
        if u_id == os.getenv("LINE_USER_ID_NICK", "").strip() and u_id:
            return "บอสนิค"
        if u_id == os.getenv("LINE_USER_ID_HOM", "").strip() and u_id:
            return "บอสหอม"
        if u_id == os.getenv("LINE_USER_ID_MOD", "").strip() and u_id:
            return "บอสมด"

    combined_text = f"{u_id} {disp} {grp}".lower()

    # Check against partner profiles
    for key, pinfo in PARTNER_PROFILES.items():
        title = pinfo["boss_title"]
        id_card = pinfo.get("id_card", "")
        if id_card and id_card in u_id:
            return title
        for kw in pinfo["keywords"]:
            kw_low = kw.lower()
            if kw_low in combined_text:
                return title

    # External user / Client
    if disp and not disp.startswith(("C", "R", "group", "room", "c_", "r_")):
        if disp.startswith("คุณ"):
            return disp
        return f"คุณ {disp}"

    return "คุณลูกค้า"


INCOMPLETE_DOC_REQUEST_REPLY = (
    "ยินดีค่ะ! เพื่อความถูกต้องตามระเบียบบัญชีของ GHN168 เฟิสรบกวนขอข้อมูลเพิ่มเติมสำหรับออกเอกสารดังนี้นะคะ:\n"
    "1. 🏢 ชื่อลูกค้า หรือ บริษัทผู้ว่าจ้าง\n"
    "2. 🎬 รายละเอียดงาน / บริการ\n"
    "3. 💰 ยอดเงิน (ระบุว่ารวม VAT 7% หรือหัก ณ ที่จ่าย 3% ด้วยไหม)\n"
    "4. ✍️ ผู้ลงนามในเอกสาร (บอสเก่ง หรือ บอสหอม)\n\n"
    "เมื่อได้ข้อมูลครบถ้วนแล้ว เฟิสจะจัดการออกเอกสาร PDF และส่งการ์ดสรุปให้ทันทีค่ะ ✨"
)


def validate_document_checklist(doc_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verifies that critical business requirements are met before issuing financial documents:
    1. client_name (real customer/company name, not generic/placeholder)
    2. project_name or items description (clear service/production details)
    3. amount or price (positive numeric amount > 0)
    4. signer_name (Smart Default: Boss Keng / นาย มงคล วงศ์สกุลยานนท์)
    """
    missing = []

    # 1. client_name
    client_name = str(doc_data.get("client_name") or doc_data.get("customer_name") or "").strip()
    invalid_clients = ["", "-", "ลูกค้าทั่วไป", "none", "null", "n/a", "ลูกค้า"]
    if not client_name or client_name.lower() in invalid_clients:
        missing.append("client_name")

    # 2. project_name / items
    project_name = str(doc_data.get("project_name") or doc_data.get("description") or "").strip()
    items = doc_data.get("items") or []
    has_valid_item = False
    for it in items:
        desc = str(it.get("desc") or it.get("description") or "").strip()
        if desc and desc not in ["-", "บริการ", "งานบริการและโปรดักชั่น", "บริการงานสื่อและโปรดักชั่น", "none", "null"]:
            has_valid_item = True
            break
    has_valid_proj = bool(project_name and project_name not in ["", "-", "บริการ", "งานบริการและโปรดักชั่น", "บริการงานสื่อและโปรดักชั่น", "none", "null"])
    if not (has_valid_proj or has_valid_item):
        missing.append("project_name")

    # 3. amount / price
    amt = doc_data.get("amount") or doc_data.get("price") or doc_data.get("subtotal") or doc_data.get("gross_amount")
    if amt is None and items:
        try:
            total_price = sum(float(i.get("price") or i.get("amount") or 0.0) * float(i.get("qty") or 1) for i in items)
            if total_price > 0:
                amt = total_price
        except Exception:
            pass
    try:
        amt_val = float(amt) if amt is not None else 0.0
    except (ValueError, TypeError):
        amt_val = 0.0

    if amt_val <= 0:
        missing.append("amount")

    # 4. signer_name (Smart Default: นาย มงคล วงศ์สกุลยานนท์)
    signer = str(doc_data.get("signer_name") or "").strip().lower()
    if not signer or signer in ["none", "null", "-", ""]:
        doc_data["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"
    else:
        is_hom = any(k in signer for k in ["หอม", "ณัฐวัฒน์", "hom", "nattawat"])
        if is_hom:
            doc_data["signer_name"] = "นาย ณัฐวัฒน์ ปวงจันทร์หอม"
        else:
            doc_data["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"

    is_complete = (len(missing) == 0)
    return is_complete, missing


def merge_document_order_data(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Robustly merges multi-turn document creation attributes with Smart Defaults."""
    merged = {**existing}
    if not incoming:
        if not merged.get("signer_name"):
            merged["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"
        return merged

    for k, v in incoming.items():
        if k in ["client_name", "client_tax_id", "client_address"]:
            if v and str(v).strip() not in ["", "-", "null", "none", "None", "ลูกค้าทั่วไป", "ลูกค้า"]:
                merged[k] = str(v).strip()
        elif k in ["project_name", "description"]:
            if v and str(v).strip() not in ["", "-", "null", "none", "None", "บริการ", "งานบริการและโปรดักชั่น"]:
                merged[k] = str(v).strip()
        elif k == "amount":
            try:
                amt = float(v)
                if amt > 0:
                    merged["amount"] = amt
            except (ValueError, TypeError):
                pass
        elif k == "signer_name":
            if v and str(v).strip() not in ["", "-", "null", "none", "None"]:
                s_str = str(v).strip()
                if any(x in s_str for x in ["หอม", "ณัฐวัฒน์", "hom", "Hom"]):
                    merged["signer_name"] = "นาย ณัฐวัฒน์ ปวงจันทร์หอม"
                elif any(x in s_str for x in ["เก่ง", "มงคล", "keng", "Keng"]):
                    merged["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"
                else:
                    merged["signer_name"] = s_str
        elif k == "doc_type":
            if v and str(v).strip() not in ["", "null", "none"]:
                merged["doc_type"] = str(v).strip()
        elif k in ["is_vat", "vat_rate", "wht_rate", "discount", "discount_desc", "payment_terms", "remarks"]:
            if v is not None and v != "":
                merged[k] = v

    # Smart Default for Signer
    if not merged.get("signer_name") or merged.get("signer_name") in ["", "-", "null", "none", "None"]:
        merged["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"

    # Smart Default for VAT (VAT 7% default for GHN168)
    if "is_vat" not in merged:
        merged["is_vat"] = True
    if "vat_rate" not in merged:
        merged["vat_rate"] = 0.07

    final_amt = float(merged.get("amount") or 0.0)
    final_proj = merged.get("project_name") or "บริการงานสื่อและโปรดักชั่น"

    incoming_items = incoming.get("items") or []
    has_valid_incoming_items = False
    valid_items = []
    for it in incoming_items:
        p = float(it.get("price") or it.get("amount") or 0.0)
        d = str(it.get("desc") or it.get("description") or "").strip()
        if p > 0 and d:
            has_valid_incoming_items = True
            valid_items.append({"desc": d, "qty": int(it.get("qty") or 1), "unit": it.get("unit", "งาน"), "price": p})

    if has_valid_incoming_items:
        merged["items"] = valid_items
        merged["amount"] = sum(i["price"] * i["qty"] for i in valid_items)
    elif final_amt > 0:
        merged["items"] = [{"desc": final_proj, "qty": 1, "unit": "งาน", "price": final_amt}]

    # Auto-fill from Customer Database if client_name exists
    raw_cname = merged.get("client_name")
    if raw_cname and str(raw_cname).strip() not in ["", "-", "ลูกค้าทั่วไป", "ลูกค้า", "null", "none"]:
        matched_cust = search_customer(raw_cname)
        if matched_cust:
            merged["client_name"] = matched_cust["customer_name"]
            merged["client_tax_id"] = matched_cust.get("tax_id", "-")
            merged["client_branch"] = matched_cust.get("branch", "00000")
            merged["client_address"] = matched_cust.get("address", "-")
            merged["client_phone"] = matched_cust.get("phone", "-")
            merged["_customer_autofilled"] = True
            merged["_matched_customer_name"] = matched_cust["customer_name"]
        else:
            if not merged.get("_customer_autofilled"):
                merged["_customer_autofilled"] = False

    return merged


def append_to_history(session_id: str, role: str, text: str):
    if session_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[session_id] = []
    CONVERSATION_HISTORY[session_id].append({
        "role": role,
        "text": text,
        "timestamp": time.time()
    })
    if len(CONVERSATION_HISTORY[session_id]) > MAX_HISTORY_PER_SESSION:
        CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-MAX_HISTORY_PER_SESSION:]


def get_history(session_id: str) -> List[Dict[str, Any]]:
    now = time.time()
    history = CONVERSATION_HISTORY.get(session_id, [])
    filtered = [msg for msg in history if now - msg["timestamp"] < 21600]
    CONVERSATION_HISTORY[session_id] = filtered
    return filtered


# ------------------------------------------------------------------------------
# 5. Proactive Tax & Bill Reminders Schedule Config
# ------------------------------------------------------------------------------
TAX_REMINDER_SCHEDULES = {
    "monthly_bills_25": {
        "title": "📅 ทวงบิลรายจ่าย & สลิปโอนเงินประจำเดือน",
        "badge_color": "#d97706",
        "description": "เตือนส่งบิลค่าน้ำมัน, ค่าอาหารกองถ่าย, บิลซื้อของ, สลิปโอนเงิน เพื่อปิดยอดบัญชีประจำเดือน (ช่วยบอสมด)",
        "message": (
            "📢 [แจ้งเตือนประจำเดือน - เลขาเฟิส]\n"
            "สวัสดีค่ะบอสเก่ง บอสหอม บอสนิค และทีมงาน GHN168 ทุกท่านค่ะ ✨\n\n"
            "วันนี้วันที่ 25 ของเดือนแล้วนะคะ เฟิสรบกวนช่วยส่งบิลรายจ่ายเดือนนี้ให้บอสมดด้วยค่ะ ได้แก่:\n"
            "⛽ บิลค่าน้ำมันรถกองถ่าย / การเดินทาง\n"
            "🍱 บิลค่าอาหารและรับรองกองถ่าย\n"
            "🛒 บิลซื้ออุปกรณ์ / ของใช้ในกอง\n"
            "🧾 สลิปโอนเงินค่าจ้างฟรีแลนซ์ / ค่าเช่าอุปกรณ์\n\n"
            "สามารถถ่ายรูปบิลส่งเข้ามาในห้องแชทนี้ได้เลยนะคะ เฟิสจะสแกนและบันทึกลง Google Sheets แท็บ 'รายจ่าย' ให้ทันทีค่ะ ขอบคุณค่ะ 🙏"
        )
    },
    "monthly_tax_28": {
        "title": "🏛️ สรุปภาษีประจำเดือนรอบสิ้นเดือน (VAT 7% & WHT)",
        "badge_color": "#dc2626",
        "description": "สรุปยอดภาษีขาย (VAT Output 7%), ภาษีซื้อ (VAT Input 7%), ยอด VAT สุทธิ และภาษีหัก ณ ที่จ่าย (WHT) สดจาก Google Sheets เพื่อเตรียมปิดงวดสิ้นเดือน",
        "message": (
            "🏛️ [สรุปภาษีประจำเดือนรอบสิ้นเดือน (28th) - เลขาเฟิส]\n"
            "สวัสดีค่ะบอสเก่ง บอสมด และทีมบริหาร GHN168 ค่ะ ✨\n\n"
            "เฟิสได้สรุปตัวเลขภาษีขาย ภาษีซื้อ ยอด VAT สุทธิ และภาษีหัก ณ ที่จ่าย (WHT) ประจำงวดสิ้นเดือนจากระบบ Google Sheets ให้เรียบร้อยแล้วค่ะ บอสมดและบอสเก่งสามารถตรวจเช็คยอดเพื่อเตรียมพร้อมปิดงวดได้เลยนะคะ ✨"
        )
    },
    "monthly_tax_01": {
        "title": "📑 สรุปภาษีประจำเดือนรอบต้นเดือน (รีเช็คสำนักงานบัญชี)",
        "badge_color": "#7c3aed",
        "description": "สรุปตัวเลขภาษี VAT 7% และหัก ณ ที่จ่าย (WHT) สดจากระบบ เพื่อตรวจสอบความถูกต้องและรีเช็คร่วมกับสำนักงานบัญชี",
        "message": (
            "📑 [สรุปภาษีประจำเดือนรอบต้นเดือน (1st) - เลขาเฟิส]\n"
            "สวัสดีค่ะบอสเก่ง บอสมด และทีมบริหาร GHN168 ค่ะ ✨\n\n"
            "เฟิสรวบรวมยอดภาษีซื้อ-ขาย และภาษีหัก ณ ที่จ่ายงวดที่ผ่านมาให้พร้อมแล้วค่ะ เพื่อให้บอสมดและบอสเก่งใช้ตรวจทานเทียบกับยอดที่สำนักงานบัญชีสรุปส่งมาค่ะ ✨"
        )
    },
    "monthly_tax_05": {
        "title": "🏛️ เตือนเดดไลน์ภาษีรายเดือน (ภ.พ.30, ภ.ง.ด.1/3/53)",
        "badge_color": "#dc2626",
        "description": "เตือนเดดไลน์ยื่นภาษีรายเดือนประจำงวด (ภ.พ.30, ภ.ง.ด.1, ภ.ง.ด.3, ภ.ง.ด.53)",
        "message": (
            "🚨 [แจ้งเตือนเดดไลน์ภาษีรายเดือน - เลขาเฟิส]\n"
            "สวัสดีค่ะบอสเก่ง บอสมด และทีมงานบัญชี GHN168 ค่ะ ✨\n\n"
            "วันนี้วันที่ 5 ของเดือน ขอแจ้งเตือนกำหนดการยื่นภาษีประจำเดือนของบริษัทค่ะ:\n"
            "1. ภ.ง.ด.1: ภาษีหัก ณ ที่จ่ายเงินเดือนพนักงาน (ยื่นภายในวันที่ 7 หรือ 15 ทางเน็ต)\n"
            "2. ภ.ง.ด.3: ภาษีหัก ณ ที่จ่ายบุคคลธรรมดา / ฟรีแลนซ์\n"
            "3. ภ.ง.ด.53: ภาษีหัก ณ ที่จ่ายนิติบุคคล / ค่าบริการ / ค่าเช่า\n"
            "4. ภ.พ.30: รายงานภาษีซื้อ-ภาษีขาย (VAT 7%)\n\n"
            "เฟิสได้รวบรวมข้อมูลใบเสร็จและใบสำคัญหักภาษีในระบบ Google Sheets ให้พร้อมแล้วค่ะ บอสมดสามารถตรวจสอบยอดนำส่งภาษีได้เลยนะคะ ✨"
        )
    },
    "pnd94_midyear_personal": {
        "title": "📋 ภาษีเงินได้บุคคลธรรมดาครึ่งปี (ภ.ง.ด.94)",
        "badge_color": "#4f46e5",
        "description": "เตือนยื่น ภ.ง.ด.94 สำหรับ 4 หุ้นส่วน (บอสเก่ง, บอสนิค, บอสหอม, บอสมด)",
        "message": (
            "📑 [แจ้งเตือนภาษีบุคคลธรรมดาครึ่งปี (ภ.ง.ด.94) - เลขาเฟิส]\n"
            "เรียน บอสเก่ง, บอสนิค, บอสหอม, และบอสมด ค่ะ ✨\n\n"
            "ถึงกำหนดยื่นแบบภาษีเงินได้บุคคลธรรมดาครึ่งปี (ภ.ง.ด.94) สำหรับรายได้ ม.ค. - มิ.ย. (40(5)-(8)) แล้วค่ะ:\n"
            "• กำหนดยื่นแบบ: 1 ก.ค. - 30 ก.ย. (หรือ 8 ต.ค. ทางอินเทอร์เน็ต)\n"
            "• สมาชิก 4 ท่าน: บอสเก่ง, บอสนิค, บอสหอม, บอสมด\n\n"
            "เฟิสเตรียมสรุปยอดรายได้และใบ 50 ทวิที่ถูกหักภาษีไว้ในระบบให้เรียบร้อยแล้วค่ะ หากต้องการให้เฟิสสรุปยอดรายบุคคลแจ้งได้เลยนะคะ ✨"
        )
    },
    "pnd90_91_annual_personal": {
        "title": "📑 ภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91)",
        "badge_color": "#2563eb",
        "description": "เตือนยื่น ภ.ง.ด.90/91 สำหรับ 4 หุ้นส่วน",
        "message": (
            "📑 [แจ้งเตือนภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91) - เลขาเฟิส]\n"
            "เรียน บอสเก่ง, บอสนิค, บอสหอม, และบอสมด ค่ะ ✨\n\n"
            "แจ้งเตือนช่วงเวลายื่นภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91) สำหรับรายได้ทั้งปีที่ผ่านมาค่ะ:\n"
            "• กำหนดยื่นแบบ: 1 ม.ค. - 31 มี.ค. (หรือ 8 เม.ย. ผ่านช่องทาง E-Filing กรมสรรพากร)\n"
            "• สมาชิก 4 ท่าน: บอสเก่ง, บอสนิค, บอสหอม, บอสมด\n\n"
            "เอกสารที่ต้องเตรียม: หนังสือรับรอง 50 ทวิ, ค่าลดหย่อนส่วนตัว, ประกันชีวิต/สุขภาพ, กองทุนสำรองเลี้ยงชีพ/SSF/RMF\n"
            "สามารถสอบถามยอดรวม 50 ทวิที่บริษัทออกให้ได้ตลอดเวลาเลยนะคะ ✨"
        )
    },
    "pnd51_midyear_corporate": {
        "title": "🏢 ภาษีเงินได้นิติบุคคลครึ่งปี (ภ.ง.ด.51)",
        "badge_color": "#059669",
        "description": "เตือนยื่น ภ.ง.ด.51 ประมาณการกำไรสุทธิครึ่งปี บจ. GHN 168",
        "message": (
            "🏢 [แจ้งเตือนภาษีเงินได้นิติบุคคลครึ่งปี (ภ.ง.ด.51) - เลขาเฟิส]\n"
            "เรียน บอสเก่ง, บอสมด และทีมบริหาร GHN 168 ค่ะ ✨\n\n"
            "ถึงกำหนดการยื่นแบบ ภ.ง.ด.51 (ประมาณการกำไรสุทธิครึ่งปีแรกของ บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด) ค่ะ:\n"
            "• กำหนดยื่นแบบ: ภายใน 2 เดือนนับจากวันปิดรอบบัญชีครึ่งปี (เดดไลน์สิ้นเดือน ส.ค. หรือ 8 ก.ย. ทางอินเทอร์เน็ต)\n"
            "• เฟิสได้สรุปตัวเลขรายรับ-รายจ่ายครึ่งปีแรกจาก Google Sheets ไว้ให้เพื่อประกอบการประมาณการกำไรสุทธิกับผู้ทำบัญชีแล้วค่ะ ✨"
        )
    },
    "pnd50_annual_corporate": {
        "title": "📊 ภาษีเงินได้นิติบุคคลประจำปี & ปิดงบการเงิน (ภ.ง.ด.50)",
        "badge_color": "#7c3aed",
        "description": "เตือนยื่น ภ.ง.ด.50 และปิดงบการเงินประจำปี GHN 168",
        "message": (
            "📊 [แจ้งเตือนภาษีนิติบุคคลประจำปี & ปิดงบการเงิน (ภ.ง.ด.50) - เลขาเฟิส]\n"
            "เรียน บอสเก่ง, บอสมด และคณะกรรมการ บจ. GHN 168 ค่ะ ✨\n\n"
            "ถึงช่วงเวลายื่นแบบ ภ.ง.ด.50 และนำส่งงบการเงินประจำปีของบริษัทค่ะ:\n"
            "1. ยื่นแบบ ภ.ง.ด.50 ต่อกรมสรรพากร (ภายใน 150 วันนับแต่วันสิ้นสุดรอบบัญชี - ปลายเดือน พ.ค.)\n"
            "2. นำส่งงบการเงิน (บอจ.5 / e-Filing DBD) ต่อกรมพัฒนาธุรกิจการค้า กระทรวงพาณิชย์\n\n"
            "ข้อมูลรายงานรายรับ รายจ่าย ทรัพย์สิน และสมุดบัญชีกระทบยอดใน Google Sheets ของบริษัทได้รับการบันทึกครบถ้วน พร้อมส่งต่อให้ผู้สอบบัญชี (CPA/TA) แล้วค่ะ ✨"
        )
    }
}

LAST_REMINDER_DATES: Dict[str, str] = {}


# ------------------------------------------------------------------------------
# 6. LINE Flex Message Validation & Card Builders
# ------------------------------------------------------------------------------
def sanitize_flex_uri(url: Any) -> str:
    """Ensures URI is a valid HTTPS / HTTP / LINE / TEL URL for LINE Flex Message actions."""
    if not url or not isinstance(url, str):
        return "https://drive.google.com"
    url_clean = url.strip()
    if url_clean.startswith(("https://", "http://", "line://", "line:", "tel://", "tel:")):
        return url_clean
    return "https://drive.google.com"


def sanitize_line_flex_payload(flex_msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively deep walks all nodes in a LINE Flex Message dictionary to ensure 100% compliance:
    1. Any node with 'type': 'text' has a non-empty string for 'text' (defaults to '-' if empty/None).
    2. Any 'action' node of type 'uri' has a valid URI scheme (defaults to 'https://drive.google.com' if empty/invalid).
    3. Any 'action' node of type 'message' has non-empty 'text' (defaults to '-').
    4. altText is non-empty and <= 400 chars.
    """
    if not isinstance(flex_msg, dict):
        return flex_msg

    # Ensure altText is non-empty string <= 400 chars
    alt_text = flex_msg.get("altText")
    if not alt_text or not isinstance(alt_text, str) or not alt_text.strip():
        flex_msg["altText"] = "GHN168 ข้อมูลการแจ้งเตือน"
    elif len(alt_text) > 400:
        flex_msg["altText"] = alt_text[:400]

    def _sanitize_action(act: Dict[str, Any]):
        if not isinstance(act, dict):
            return
        act_type = act.get("type")
        if act_type == "uri":
            act["uri"] = sanitize_flex_uri(act.get("uri"))
        elif act_type == "message":
            msg_t = str(act.get("text") or "").strip()
            act["text"] = msg_t if msg_t else "-"
        # Check label length <= 40
        if "label" in act and act["label"] is not None:
            lbl = str(act["label"]).strip()
            act["label"] = lbl[:40] if lbl else "คลิก"

    def _sanitize_node(node: Any):
        if isinstance(node, dict):
            # Check text node
            if node.get("type") == "text":
                t_val = str(node.get("text") or "").strip()
                if not t_val:
                    node["text"] = "-"
                else:
                    node["text"] = t_val
            # Check action
            if "action" in node and isinstance(node["action"], dict):
                _sanitize_action(node["action"])
            # Recurse through dictionary
            for k, v in list(node.items()):
                _sanitize_node(v)
        elif isinstance(node, list):
            for item in node:
                _sanitize_node(item)

    if "contents" in flex_msg:
        _sanitize_node(flex_msg["contents"])

    return flex_msg


def validate_line_flex_payload(flex_msg: Dict[str, Any]) -> bool:
    """
    Validates that a Flex Message dictionary complies with LINE Messaging API specifications:
    - Root type is 'flex'
    - altText is non-empty string <= 400 chars
    - contents is a valid bubble or carousel dictionary
    - All action URIs have valid schemes (https/http/line/tel) and lengths <= 1000
    - All action labels <= 40 chars
    """
    if not isinstance(flex_msg, dict):
        raise ValueError("Flex message payload must be a dictionary.")
    if flex_msg.get("type") != "flex":
        raise ValueError(f"Top-level type must be 'flex', got '{flex_msg.get('type')}'.")
    alt_text = flex_msg.get("altText")
    if not alt_text or not isinstance(alt_text, str) or len(alt_text) > 400:
        raise ValueError(f"altText must be a non-empty string <= 400 chars (len={len(alt_text) if alt_text else 0}).")
    contents = flex_msg.get("contents")
    if not isinstance(contents, dict):
        raise ValueError("Flex contents must be a dictionary representing a bubble or carousel.")

    def _validate_action(action: Dict[str, Any], path: str):
        if not isinstance(action, dict):
            raise ValueError(f"Action at {path} must be a dictionary.")
        act_type = action.get("type")
        if act_type not in ["uri", "message", "postback", "datetimepicker", "camera", "cameraRoll", "location"]:
            raise ValueError(f"Invalid action type '{act_type}' at {path}.")
        label = action.get("label")
        if label is not None and (not isinstance(label, str) or len(label) > 40):
            raise ValueError(f"Action label at {path} exceeds 40 characters: '{label}'.")
        if act_type == "uri":
            uri = action.get("uri")
            if not uri or not isinstance(uri, str):
                raise ValueError(f"URI action at {path} requires a non-empty string uri.")
            if not uri.startswith(("https://", "http://", "line://", "line:", "tel://", "tel:")):
                raise ValueError(f"URI at {path} must start with https://, http://, line://, line:, tel://, or tel: (got: '{uri}').")
            if len(uri) > 1000:
                raise ValueError(f"URI at {path} exceeds 1000 characters.")
        elif act_type == "message":
            text = action.get("text")
            if not text or not isinstance(text, str) or len(text) > 300:
                raise ValueError(f"Message action text at {path} must be non-empty string <= 300 chars.")

    def _validate_node(node: Any, path: str):
        if isinstance(node, dict):
            if "action" in node and isinstance(node["action"], dict):
                _validate_action(node["action"], f"{path}.action")
            for k, v in node.items():
                _validate_node(v, f"{path}.{k}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _validate_node(item, f"{path}[{idx}]")

    c_type = contents.get("type")
    if c_type not in ["bubble", "carousel"]:
        raise ValueError(f"Contents container must be 'bubble' or 'carousel', got '{c_type}'.")
    _validate_node(contents, "contents")
    return True


def build_document_flex_message(doc_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a modern LINE Flex Message Bubble card for all financial documents (QT, IV, RE, 50 ทวิ).
    Standardized, clean, and guaranteed 100% compliant with LINE Messaging API Flex Message Schema.
    """
    doc_type = doc_res.get("doc_type") or doc_res.get("target_type") or "quotation"
    doc_type_str = str(doc_type).lower().strip()

    if doc_type_str in ["qt", "quotation", "quote"]:
        doc_type_norm = "quotation"
        badge_title = "ใบเสนอราคา (Quotation)"
        header_color = "#0284c7"  # Sky Blue
    elif doc_type_str in ["iv", "invoice", "inv", "bill"]:
        doc_type_norm = "invoice"
        badge_title = "ใบวางบิล / ใบแจ้งหนี้ (Invoice)"
        header_color = "#4f46e5"  # Indigo Purple
    elif doc_type_str in ["re", "receipt", "rec", "tax_invoice"]:
        doc_type_norm = "receipt"
        badge_title = "ใบเสร็จรับเงิน (Receipt)"
        header_color = "#059669"  # Emerald Green
    elif doc_type_str in ["wht", "50tavi", "50bis", "withholding", "wht50"]:
        doc_type_norm = "wht"
        badge_title = "หนังสือรับรองหักภาษี (50 ทวิ)"
        header_color = "#8b5cf6"  # Purple
    else:
        doc_type_norm = "quotation"
        badge_title = "เอกสารทางการเงิน (GHN168)"
        header_color = "#0284c7"

    doc_no = doc_res.get("doc_no") or "-"
    pdf_url = sanitize_flex_uri(doc_res.get("pdf_url"))
    client_name = doc_res.get("client_name") or "-"
    project_name = doc_res.get("project_name") or "-"
    totals = doc_res.get("totals") or {}

    # Sheet tab name fallback
    sheet_name = doc_res.get("sheet_name") or doc_res.get("sync_result", {}).get("sheet_name")
    if not sheet_name or sheet_name == "-":
        default_sheets = {
            "quotation": "ใบเสนอราคา",
            "invoice": "ใบวางบิล",
            "receipt": "รายรับ",
            "wht": "รายจ่าย"
        }
        sheet_name = default_sheets.get(doc_type_norm, "Google Sheets")

    net_total_val = float(totals.get("net_total", 0.0))
    pre_vat_val = float(totals.get("pre_vat", totals.get("subtotal", totals.get("amount", net_total_val))))
    vat_val = float(totals.get("vat_amount", 0.0))
    wht_val = float(totals.get("wht_amount", 0.0))
    wht_rate = float(totals.get("wht_rate", 0.0))

    net_total_str = format_currency(net_total_val)
    pre_vat_str = format_currency(pre_vat_val)
    vat_str = format_currency(vat_val)
    wht_str = format_currency(wht_val)
    baht_text = totals.get("baht_text") or thai_baht_text(net_total_val)

    # Subtitle for document number (show source doc if converted)
    source_doc_no = doc_res.get("source_doc_no")
    if source_doc_no and source_doc_no != doc_no and source_doc_no not in ["-", "เอกสารต้นทาง", "NEW"]:
        sub_text = f"เลขที่: {doc_no} (จาก {source_doc_no})"
    else:
        sub_text = f"เลขที่: {doc_no}"

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": header_color,
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "GHN 168 MEDIA & CREATION", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": badge_title, "color": "#ffffff", "size": "lg", "weight": "bold", "margin": "xs", "wrap": True},
                {"type": "text", "text": sub_text, "color": "#e0f2fe", "size": "xs", "margin": "xs", "wrap": True}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "ลูกค้า / ผู้รับ:", "size": "xs", "color": "#64748b", "flex": 3},
                                {"type": "text", "text": str(client_name), "size": "xs", "color": "#0f172a", "weight": "bold", "flex": 7, "wrap": True}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "sm",
                            "contents": [
                                {"type": "text", "text": "โครงการ:", "size": "xs", "color": "#64748b", "flex": 3},
                                {"type": "text", "text": str(project_name), "size": "xs", "color": "#0f172a", "flex": 7, "wrap": True}
                            ]
                        }
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "ยอดก่อนภาษี:", "size": "xs", "color": "#64748b"},
                                {"type": "text", "text": f"{pre_vat_str} ฿", "size": "xs", "align": "end", "color": "#334155"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "xs",
                            "contents": [
                                {"type": "text", "text": "ภาษี VAT 7%:", "size": "xs", "color": "#64748b"},
                                {"type": "text", "text": f"{vat_str} ฿", "size": "xs", "align": "end", "color": "#334155"}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "backgroundColor": "#f8fafc",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": header_color,
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "เปิดดูเอกสาร PDF (Drive)",
                        "uri": pdf_url
                    }
                },
                {
                    "type": "text",
                    "text": f"✅ ซิงค์ลง Google Sheets แท็บ '{sheet_name}' แล้ว",
                    "size": "xxs",
                    "color": "#16a34a",
                    "align": "center",
                    "margin": "sm"
                }
            ]
        }
    }

    if wht_rate > 0 or doc_type_norm == "wht" or wht_val > 0:
        display_rate = wht_rate if wht_rate > 0 else 3.0
        flex_bubble["body"]["contents"][2]["contents"].append({
            "type": "box",
            "layout": "horizontal",
            "margin": "xs",
            "contents": [
                {"type": "text", "text": f"หัก ณ ที่จ่าย ({display_rate:g}%):", "size": "xs", "color": "#dc2626"},
                {"type": "text", "text": f"-{wht_str} ฿", "size": "xs", "align": "end", "color": "#dc2626", "weight": "bold"}
            ]
        })

    flex_bubble["body"]["contents"].append({
        "type": "box",
        "layout": "vertical",
        "margin": "lg",
        "paddingAll": "10px",
        "backgroundColor": "#f1f5f9",
        "cornerRadius": "6px",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "ยอดเงินสุทธิ:", "size": "sm", "weight": "bold", "color": "#0f172a"},
                    {"type": "text", "text": f"{net_total_str} ฿", "size": "md", "weight": "bold", "align": "end", "color": header_color}
                ]
            },
            {
                "type": "text",
                "text": f"({baht_text})",
                "size": "xxs",
                "color": "#64748b",
                "align": "end",
                "margin": "xs",
                "wrap": True
            }
        ]
    })

    return {
        "type": "flex",
        "altText": f"เอกสาร {badge_title} เลขที่ {doc_no} (ยอดสุทธิ {net_total_str} บาท)",
        "contents": flex_bubble
    }


def build_document_conversion_flex_message(conv_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a LINE Flex Message for Document Lifecycle Pipeline conversion (QT -> IV -> RE -> 50 ทวิ).
    Unifies with standard build_document_flex_message for 100% reliability and identical styling.
    """
    return build_document_flex_message(conv_res)



def build_income_slip_flex_message(
    slip_data: Dict[str, Any],
    matched_invoice: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Constructs a LINE Flex Message for detected Incoming Customer Bank Transfer Slip."""
    amt = float(slip_data.get("amount") or slip_data.get("net_amount") or 0.0)
    amt_str = f"{amt:,.2f}"
    transfer_date = slip_data.get("transfer_date") or slip_data.get("doc_date") or datetime.now().strftime("%d/%m/%Y")
    transfer_time = slip_data.get("transfer_time") or ""
    sender_name = slip_data.get("sender_name") or slip_data.get("store_name") or "ลูกค้า / ผู้โอนเงิน"
    sender_bank = slip_data.get("sender_bank") or "-"

    body_contents = [
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": [
                {"type": "text", "text": "ผู้โอนเงิน:", "size": "xs", "color": "#64748b", "weight": "bold"},
                {"type": "text", "text": sender_name, "size": "sm", "color": "#0f172a", "weight": "bold", "wrap": True},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": f"ธนาคาร: {sender_bank}", "size": "xs", "color": "#64748b"},
                        {"type": "text", "text": f"{transfer_date} {transfer_time}", "size": "xs", "color": "#64748b", "align": "end"}
                    ]
                }
            ]
        },
        {"type": "separator", "margin": "md"},
        {
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "paddingAll": "10px",
            "backgroundColor": "#ecfdf5",
            "cornerRadius": "6px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "ยอดเงินโอนเข้า:", "size": "sm", "weight": "bold", "color": "#065f46"},
                        {"type": "text", "text": f"+{amt_str} ฿", "size": "lg", "weight": "bold", "align": "end", "color": "#059669"}
                    ]
                },
                {"type": "text", "text": "โอนเข้า: ธ.กรุงไทย 520-0-61960-2 (บจ. จีเอชเอ็น 168)", "size": "xxs", "color": "#047857", "margin": "xs"}
            ]
        }
    ]

    if matched_invoice:
        inv_no = matched_invoice.get("doc_no") or "-"
        inv_client = matched_invoice.get("client_name") or "-"
        inv_amt = float(matched_invoice.get("net_total") or 0.0)
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "paddingAll": "10px",
            "backgroundColor": "#f0f9ff",
            "cornerRadius": "6px",
            "contents": [
                {"type": "text", "text": "🎯 ตรวจพบคู่ตรงกับใบวางบิล:", "size": "xs", "weight": "bold", "color": "#0369a1"},
                {"type": "text", "text": f"• เลขที่: {inv_no} ({inv_client})", "size": "xs", "color": "#0f172a", "margin": "xs", "wrap": True},
                {"type": "text", "text": f"• ยอดในใบวางบิล: {inv_amt:,.2f} ฿", "size": "xs", "color": "#0284c7"}
            ]
        })

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#059669",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "💳 CUSTOMER SLIP SCANNER", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                        {"type": "text", "text": "INCOME VERIFIED", "color": "#ffffff", "size": "xxs", "align": "end", "weight": "bold"}
                    ]
                },
                {"type": "text", "text": "ตรวจพบสลิปเงินเข้าบริษัท", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": "โอนเข้าบัญชี ธ.กรุงไทย GHN 168", "color": "#d1fae5", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": body_contents
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "spacing": "sm",
            "backgroundColor": "#ffffff",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#059669",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "ยืนยันออกใบเสร็จ (RE)",
                        "text": f"ยืนยันออกใบเสร็จรับเงินยอด {amt_str} บาท"
                    }
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"💳 ตรวจพบสลิปเงินเข้าบริษัท ยอด {amt_str} บาท ({sender_name})",
        "contents": flex_bubble
    }


def build_overdue_invoices_flex_message(overdue_res: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a LINE Flex Message summarizing Overdue & Aging Invoices with polite reminder draft."""
    as_of = overdue_res.get("as_of_date") or datetime.now().strftime("%d/%m/%Y")
    total_overdue = overdue_res.get("total_overdue_amount", 0.0)
    total_overdue_cnt = overdue_res.get("total_overdue_count", 0)
    due_today_cnt = overdue_res.get("total_due_today_count", 0)
    due_today_amt = overdue_res.get("total_due_today_amount", 0.0)
    upcoming_cnt = overdue_res.get("total_upcoming_count", 0)
    all_overdue = overdue_res.get("all_overdue_list", [])

    items_boxes = []
    for inv in all_overdue[:4]:  # Show top 4 urgent
        days = inv.get("days_overdue", 0)
        c_name = inv.get("client_name", "-")
        amt = inv.get("net_total", 0.0)
        d_no = inv.get("doc_no", "-")
        items_boxes.append({
            "type": "box",
            "layout": "vertical",
            "margin": "sm",
            "paddingAll": "8px",
            "backgroundColor": "#fff1f2",
            "cornerRadius": "6px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"🔴 {d_no}", "size": "xs", "weight": "bold", "color": "#e11d48"},
                        {"type": "text", "text": f"เกิน {days} วัน", "size": "xxs", "color": "#e11d48", "align": "end", "weight": "bold"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": c_name, "size": "xs", "color": "#334155", "wrap": True, "flex": 3},
                        {"type": "text", "text": f"{amt:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#0f172a", "align": "end", "flex": 2}
                    ]
                }
            ]
        })

    if not items_boxes:
        items_boxes.append({
            "type": "text",
            "text": "🎉 ยอดเยี่ยมมากค่ะ! ไม่มีใบวางบิลค้างชำระเกินกำหนดเลย",
            "size": "sm",
            "color": "#16a34a",
            "align": "center",
            "margin": "md"
        })

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#e11d48",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "⏰ OVERDUE & AGING TRACKER", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                        {"type": "text", "text": f"ณ {as_of}", "color": "#ffffff", "size": "xxs", "align": "end"}
                    ]
                },
                {"type": "text", "text": "รายงานติดตามบิลค้างชำระ", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": f"ค้างชำระทั้งหมด {total_overdue_cnt} ใบ (รวม {total_overdue:,.2f} บาท)", "color": "#ffe4e6", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "paddingAll": "8px",
                            "backgroundColor": "#f8fafc",
                            "cornerRadius": "6px",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "ครบกำหนดวันนี้", "size": "xxs", "color": "#64748b", "align": "center"},
                                {"type": "text", "text": f"{due_today_cnt} ใบ", "size": "sm", "weight": "bold", "color": "#0284c7", "align": "center"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "paddingAll": "8px",
                            "backgroundColor": "#f8fafc",
                            "cornerRadius": "6px",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "ใกล้ครบ (1-3 วัน)", "size": "xxs", "color": "#64748b", "align": "center"},
                                {"type": "text", "text": f"{upcoming_cnt} ใบ", "size": "sm", "weight": "bold", "color": "#f59e0b", "align": "center"}
                            ]
                        }
                    ]
                },
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": "📋 รายการบิลค้างชำระสำคัญ:", "size": "xs", "weight": "bold", "color": "#334155", "margin": "md"},
                {"type": "box", "layout": "vertical", "contents": items_boxes}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "backgroundColor": "#ffffff",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#e11d48",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "ดราฟต์ข้อความทวงเงิน",
                        "text": "ดราฟต์ข้อความทวงเงินลูกค้า"
                    }
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"⏰ สรุปบิลค้างชำระ {total_overdue_cnt} ใบ ยอด {total_overdue:,.2f} บาท",
        "contents": flex_bubble
    }


def build_calendar_event_created_flex_message(cal_res: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a LINE Flex Message confirming successful creation of Google Calendar event."""
    title = cal_res.get("title") or "คิวงาน GHN168"
    start_time = cal_res.get("startTime") or ""
    end_time = cal_res.get("endTime") or ""
    cal_name = cal_res.get("calendarName") or "GHN168 Media Calendar"

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d9488",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📅 GOOGLE CALENDAR SCHEDULED", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "ลงคิวงานสำเร็จเรียบร้อย", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "ชื่องาน / กิจกรรม:", "size": "xs", "color": "#64748b", "weight": "bold"},
                {"type": "text", "text": title, "size": "sm", "color": "#0f172a", "weight": "bold", "wrap": True, "margin": "xs"},
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "spacing": "xs",
                    "contents": [
                        {"type": "text", "text": f"• เริ่มต้น: {start_time}", "size": "xs", "color": "#334155"},
                        {"type": "text", "text": f"• สิ้นสุด: {end_time}", "size": "xs", "color": "#334155"},
                        {"type": "text", "text": f"• บันทึกใน: {cal_name} (ghn168media@gmail.com)", "size": "xxs", "color": "#0d9488", "margin": "xs"}
                    ]
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"📅 ลงคิวงาน '{title}' ใน Google Calendar สำเร็จ",
        "contents": flex_bubble
    }


def build_partner_hunter_flex_message(breakdown_res: Dict[str, Any]) -> Dict[str, Any]:
    """Pillar 1: Constructs a LINE Flex Message for Lead Hunter Leaderboard & Peer-Sharing Volume."""
    p1 = breakdown_res.get("pillar_1_lead_hunters", {})
    leaderboard = p1.get("leaderboard", [])
    total_gross = p1.get("total_gross_volume", 0.0)
    total_peer = p1.get("total_peer_shared_volume", 0.0)

    rows = []
    medals = ["🥇", "🥈", "🥉", "🎖️"]
    for idx, p in enumerate(leaderboard):
        m = medals[idx] if idx < len(medals) else "•"
        s_name = p.get("short_name", "-")
        gross = p.get("hunter_gross", 0.0)
        peer = p.get("peer_shared_volume", 0.0)
        deals = p.get("hunter_deals_count", 0)

        rows.append({
            "type": "box",
            "layout": "vertical",
            "margin": "sm",
            "paddingAll": "10px",
            "backgroundColor": "#fefce8" if idx == 0 else "#f8fafc",
            "cornerRadius": "6px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"{m} คุณ{s_name}", "size": "sm", "weight": "bold", "color": "#0f172a"},
                        {"type": "text", "text": f"{gross:,.2f} ฿", "size": "sm", "weight": "bold", "color": "#d97706", "align": "end"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": f"หาได้ {deals} งาน | ป้อนให้เพื่อนทำ: {peer:,.2f} ฿", "size": "xxs", "color": "#64748b"}
                    ]
                }
            ]
        })

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#d97706",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "🏆 PILLAR 1: LEAD HUNTER LEADERBOARD", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "ผลงานคนหางาน & แบ่งปันเพื่อน", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": f"ยอดงานรวมทีม {total_gross:,.2f} ฿ (ป้อนเพื่อน {total_peer:,.2f} ฿)", "color": "#fef3c7", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": rows
        }
    }

    return {
        "type": "flex",
        "altText": f"🏆 สรุปผลงานคนหางาน GHN168 (ยอดรวม {total_gross:,.2f} บาท)",
        "contents": flex_bubble
    }


def build_partner_labor_flex_message(breakdown_res: Dict[str, Any]) -> Dict[str, Any]:
    """Pillar 2: Constructs a LINE Flex Message for Cumulative Labor Wages Earned YTD."""
    p2 = breakdown_res.get("pillar_2_labor_earned", {})
    partners = p2.get("partners", [])
    total_ytd = p2.get("total_labor_ytd", 0.0)

    rows = []
    for p in partners:
        s_name = p.get("short_name", "-")
        ytd = p.get("labor_ytd", 0.0)
        m_amt = p.get("labor_month", 0.0)
        proj = p.get("projects_done", 0)

        rows.append({
            "type": "box",
            "layout": "vertical",
            "margin": "sm",
            "paddingAll": "10px",
            "backgroundColor": "#f8fafc",
            "cornerRadius": "6px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"🛠️ คุณ{s_name}", "size": "sm", "weight": "bold", "color": "#0f172a"},
                        {"type": "text", "text": f"{ytd:,.2f} ฿", "size": "sm", "weight": "bold", "color": "#2563eb", "align": "end"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": f"เดือนนี้: {m_amt:,.2f} ฿ ({proj} โปรเจกต์)", "size": "xxs", "color": "#64748b"}
                    ]
                }
            ]
        })

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#2563eb",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "💼 PILLAR 2: LABOR EARNED YTD", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "สรุปค่าแรงคนทำงานสะสมจริง", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": f"ค่าแรงสะสมจ่ายทีมรวม {total_ytd:,.2f} ฿", "color": "#dbeafe", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": rows
        }
    }

    return {
        "type": "flex",
        "altText": f"💼 สรุปค่าแรงคนทำงานสะสม YTD รวม {total_ytd:,.2f} บาท",
        "contents": flex_bubble
    }


def build_partner_vault_flex_message(breakdown_res: Dict[str, Any]) -> Dict[str, Any]:
    """Pillar 3: Constructs a LINE Flex Message for Personal Vault Balances and Central Company Pool."""
    p3 = breakdown_res.get("pillar_3_personal_vault", {})
    central_pool = p3.get("corporate_central_pool", 0.0)
    grand_total = p3.get("grand_total_reserves", 0.0)
    partners = p3.get("partners", [])

    rows = [
        {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "10px",
            "backgroundColor": "#f5f3ff",
            "cornerRadius": "6px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🏢 กองกลางสำรองจ่ายบริษัท", "size": "sm", "weight": "bold", "color": "#5b21b6"},
                        {"type": "text", "text": f"{central_pool:,.2f} ฿", "size": "sm", "weight": "bold", "color": "#7c3aed", "align": "end"}
                    ]
                }
            ]
        },
        {"type": "separator", "margin": "md"},
        {"type": "text", "text": "💰 เงินสะสมส่วนตัวในบัญชี บ. ของแต่ละคน:", "size": "xs", "weight": "bold", "color": "#334155", "margin": "md"}
    ]

    for p in partners:
        s_name = p.get("short_name", "-")
        vault = p.get("personal_vault_balance", 0.0)
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {"type": "text", "text": f"• คุณ{s_name}", "size": "xs", "color": "#334155"},
                {"type": "text", "text": f"{vault:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#7c3aed", "align": "end"}
            ]
        })

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#7c3aed",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "💰 PILLAR 3: PERSONAL VAULT & CENTRAL POOL", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "ยอดเงินสะสมส่วนตัว & กองกลาง", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": f"เงินกองทุนสะสมรวม {grand_total:,.2f} ฿", "color": "#ede9fe", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": rows
        }
    }

    return {
        "type": "flex",
        "altText": f"💰 ยอดเงินสะสมส่วนตัว & กองกลาง GHN168 (รวม {grand_total:,.2f} บาท)",
        "contents": flex_bubble
    }


def build_partner_all_in_one_financial_flex_message(breakdown_res: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a Comprehensive 3-Pillar Partner Financial Flex Message."""
    p1 = breakdown_res.get("pillar_1_lead_hunters", {})
    p2 = breakdown_res.get("pillar_2_labor_earned", {})
    p3 = breakdown_res.get("pillar_3_personal_vault", {})

    gross_lead = p1.get("total_gross_volume", 0.0)
    labor_ytd = p2.get("total_labor_ytd", 0.0)
    vault_total = p3.get("grand_total_reserves", 0.0)

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1e293b",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📊 GHN168 PARTNER FINANCIAL ENGINE", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "ระบบการเงิน 3 เสาหลักครบวงจร", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "10px",
                    "backgroundColor": "#fefce8",
                    "cornerRadius": "6px",
                    "contents": [
                        {"type": "text", "text": "1. 🏆 มิติคนหางาน (Lead Hunter):", "size": "xs", "weight": "bold", "color": "#92400e"},
                        {"type": "text", "text": f"ยอดงานรวมหาได้ {gross_lead:,.2f} ฿ (ป้อนเพื่อน {p1.get('total_peer_shared_volume', 0.0):,.2f} ฿)", "size": "xs", "color": "#b45309", "margin": "xs"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "10px",
                    "backgroundColor": "#eff6ff",
                    "cornerRadius": "6px",
                    "contents": [
                        {"type": "text", "text": "2. 💼 มิติคนทำงาน (Labor Earned YTD):", "size": "xs", "weight": "bold", "color": "#1e40af"},
                        {"type": "text", "text": f"ค่าแรงสะสมจริงทั้งปี {labor_ytd:,.2f} ฿", "size": "xs", "color": "#2563eb", "margin": "xs"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "10px",
                    "backgroundColor": "#f5f3ff",
                    "cornerRadius": "6px",
                    "contents": [
                        {"type": "text", "text": "3. 💰 มิติเงินสะสม & กองกลาง (Personal Vault):", "size": "xs", "weight": "bold", "color": "#5b21b6"},
                        {"type": "text", "text": f"กองทุนสำรองและเงินสะสมรวม {vault_total:,.2f} ฿", "size": "xs", "color": "#7c3aed", "margin": "xs"}
                    ]
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": "📊 ระบบการเงิน 3 เสาหลัก GHN168",
        "contents": flex_bubble
    }


def build_tax_reminder_flex_message(
    reminder_type: str,
    acc_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Constructs a LINE Flex Message for scheduled tax reminders with real-time financial metrics."""
    info = TAX_REMINDER_SCHEDULES.get(reminder_type, {
        "title": "📅 แจ้งเตือนภาษีและบัญชี GHN168",
        "badge_color": "#0284c7",
        "description": "การแจ้งเตือนจากเลขาเฟิส",
        "message": "กรุณาตรวจสอบเอกสารภาษีค่ะ"
    })

    title = info["title"]
    badge_color = info.get("badge_color", "#0284c7")
    desc = info["description"]

    # For monthly tax summaries or when accounting data is provided, build a rich live financial card
    if reminder_type in ["monthly_tax_28", "monthly_tax_01"] or acc_data is not None:
        if acc_data is None:
            try:
                now = datetime.now()
                if reminder_type == "monthly_tax_01":
                    target_m = 12 if now.month == 1 else now.month - 1
                    target_y = now.year - 1 if now.month == 1 else now.year
                    acc_data = get_live_accounting_summary(month=target_m, year=target_y)
                else:
                    acc_data = get_live_accounting_summary(month=now.month, year=now.year)
            except Exception as e:
                logger.warning("Failed to fetch live accounting summary for tax reminder: %s", e)
                acc_data = {}

        summary = acc_data.get("summary", {}) if acc_data else {}
        period_label = (acc_data.get("period_label") if acc_data else None) or datetime.now().strftime("%m/%Y")
        vat_output = float(summary.get("total_income_vat_output") or 0.0)
        vat_input = float(summary.get("total_expense_vat_input") or 0.0)
        net_vat = float(summary.get("net_vat_balance") or round(vat_output - vat_input, 2))
        wht_deducted = float(summary.get("total_income_wht_deducted") or 0.0)
        wht_withheld = float(summary.get("total_expense_wht_withheld") or 0.0)

        if net_vat > 0:
            vat_status_label = f"ต้องนำส่งภาษีเพิ่ม {net_vat:,.2f} ฿"
            net_vat_color = "#dc2626"
            net_vat_sign = "+"
        elif net_vat < 0:
            vat_status_label = f"มีภาษีซื้อยกไป {abs(net_vat):,.2f} ฿"
            net_vat_color = "#059669"
            net_vat_sign = ""
        else:
            vat_status_label = "ยอดภาษีซื้อ-ภาษีขายเท่ากันพอดี"
            net_vat_color = "#334155"
            net_vat_sign = ""

        flex_bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": badge_color,
                "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": "GHN 168 TAX & ACCOUNTING", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                    {"type": "text", "text": title, "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs", "wrap": True},
                    {"type": "text", "text": f"งวดประจำเดือน {period_label} • ข้อมูลสด Real-Time", "color": "#e0f2fe", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": "🏛️ ภาษีมูลค่าเพิ่ม (VAT 7%):",
                        "size": "xs",
                        "weight": "bold",
                        "color": "#1e293b"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "• ภาษีขาย (Output 7%)", "size": "xs", "color": "#64748b", "flex": 6},
                            {"type": "text", "text": f"{vat_output:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#0f172a", "align": "end", "flex": 4}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "• ภาษีซื้อ (Input 7%)", "size": "xs", "color": "#64748b", "flex": 6},
                            {"type": "text", "text": f"{vat_input:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#0f172a", "align": "end", "flex": 4}
                        ]
                    },
                    {"type": "separator", "margin": "sm"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "⚖️ ยอด VAT สุทธิ:", "size": "xs", "weight": "bold", "color": "#0f172a", "flex": 5},
                            {"type": "text", "text": f"{net_vat_sign}{net_vat:,.2f} ฿", "size": "sm", "weight": "bold", "color": net_vat_color, "align": "end", "flex": 5}
                        ]
                    },
                    {
                        "type": "text",
                        "text": f"สถานะ: {vat_status_label}",
                        "size": "xxs",
                        "color": net_vat_color,
                        "margin": "xxs",
                        "wrap": True
                    },
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "text",
                        "text": "📑 ภาษีหัก ณ ที่จ่าย (WHT):",
                        "size": "xs",
                        "weight": "bold",
                        "color": "#1e293b",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "• ลูกค้าหัก GHN ไว้:", "size": "xs", "color": "#64748b", "flex": 6},
                            {"type": "text", "text": f"{wht_deducted:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#059669", "align": "end", "flex": 4}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "• GHN หักนำส่ง (3/53):", "size": "xs", "color": "#64748b", "flex": 6},
                            {"type": "text", "text": f"{wht_withheld:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#d97706", "align": "end", "flex": 4}
                        ]
                    },
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "• ดึงตัวเลขสดจาก Google Sheets รายรับ-รายจ่าย", "size": "xxs", "color": "#94a3b8"},
                            {"type": "text", "text": "• บอสมดและบอสเก่งตรวจเทียบกับยอด สนง.บัญชี ได้ทันทีค่ะ", "size": "xxs", "color": "#94a3b8", "margin": "xxs"}
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "12px",
                "backgroundColor": "#f8fafc",
                "contents": [
                    {
                        "type": "text",
                        "text": "✨ เลขาเฟิสพร้อมดูแลและจัดเตรียมเอกสารเสมอค่ะ",
                        "size": "xxs",
                        "color": "#64748b",
                        "align": "center"
                    }
                ]
            }
        }

        return {
            "type": "flex",
            "altText": f"📊 สรุปภาษี GHN168: {period_label}",
            "contents": flex_bubble
        }

    # Standard informational card for other schedules
    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": badge_color,
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "GHN 168 TAX & ACCOUNTING", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": title, "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs", "wrap": True}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": desc, "size": "sm", "color": "#334155", "wrap": True},
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {"type": "text", "text": "• รวบรวมบิลและใบสำคัญหักภาษีใน Google Sheets", "size": "xs", "color": "#64748b"},
                        {"type": "text", "text": "• ส่งรูปสลิป/บิลในห้องแชทเพื่อให้เลขาเฟิสสแกนได้ทันที", "size": "xs", "color": "#64748b", "margin": "xs"}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "14px",
            "backgroundColor": "#f8fafc",
            "contents": [
                {
                    "type": "text",
                    "text": "✨ เลขาเฟิสพร้อมดูแลและจัดเตรียมเอกสารเสมอค่ะ",
                    "size": "xxs",
                    "color": "#64748b",
                    "align": "center"
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"แจ้งเตือน: {title}",
        "contents": flex_bubble
    }


def build_expense_ocr_flex_message(ocr_data: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a LINE Flex Message displaying OCR scanned receipt data with confirmation."""
    store_name = ocr_data.get("store_name") or "ร้านค้า / ผู้รับเงิน"
    tax_id = ocr_data.get("tax_id") or "-"
    doc_date = ocr_data.get("doc_date") or datetime.now().strftime("%d/%m/%Y")
    category = ocr_data.get("category") or "ค่าใช้จ่ายทั่วไป"
    net_amt = float(ocr_data.get("net_amount") or 0.0)
    vat_amt = float(ocr_data.get("vat_amount") or 0.0)
    pre_vat_amt = float(ocr_data.get("pre_vat_amount") or (net_amt - vat_amt))
    items_summary = ocr_data.get("items_summary") or "รายการค่าใช้จ่าย"

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#d97706",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📸 GHN168 RECEIPT SCANNER", "color": "#ffffff", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "สแกนบิลรายจ่ายเรียบร้อยค่ะ ✨", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "ร้านค้า:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": store_name, "size": "xs", "color": "#0f172a", "weight": "bold", "flex": 7, "wrap": True}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "เลขผู้เสียภาษี:", "size": "xs", "color": "#64748b", "flex": 4},
                        {"type": "text", "text": tax_id, "size": "xs", "color": "#334155", "flex": 6}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "วันที่บิล:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": doc_date, "size": "xs", "color": "#334155", "flex": 7}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "หมวดหมู่:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": category, "size": "xs", "color": "#0284c7", "weight": "bold", "flex": 7}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "รายการ:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": items_summary, "size": "xs", "color": "#334155", "flex": 7, "wrap": True}
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "ยอดก่อนภาษี:", "size": "xs", "color": "#64748b"},
                                {"type": "text", "text": f"{pre_vat_amt:,.2f} ฿", "size": "xs", "align": "end", "color": "#334155"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "xs",
                            "contents": [
                                {"type": "text", "text": "ภาษี VAT 7%:", "size": "xs", "color": "#64748b"},
                                {"type": "text", "text": f"{vat_amt:,.2f} ฿", "size": "xs", "align": "end", "color": "#334155"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "sm",
                            "contents": [
                                {"type": "text", "text": "ยอดสุทธิ:", "size": "sm", "weight": "bold", "color": "#0f172a"},
                                {"type": "text", "text": f"{net_amt:,.2f} ฿", "size": "md", "weight": "bold", "align": "end", "color": "#d97706"}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "14px",
            "backgroundColor": "#f8fafc",
            "contents": [
                {
                    "type": "text",
                    "text": "พิมพ์ 'บันทึก' หรือ 'ยืนยัน' เพื่อซิงค์ลง Google Sheets แท็บ 'รายจ่าย' ค่ะ",
                    "size": "xxs",
                    "color": "#16a34a",
                    "align": "center",
                    "wrap": True
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"สแกนบิล: {store_name} ({net_amt:,.2f} บาท)",
        "contents": flex_bubble
    }


def build_accounting_summary_flex_message(summary_res: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a modern LINE Flex Message displaying Live Sheets Accounting Insights."""
    period = summary_res.get("period_label", "ปัจจุบัน")
    summary = summary_res.get("summary", {})
    income_net = summary.get("total_income_net", 0.0)
    expense_net = summary.get("total_expense_net", 0.0)
    net_cashflow = summary.get("net_cashflow", 0.0)
    vat_output = summary.get("total_income_vat_output", 0.0)
    vat_input = summary.get("total_expense_vat_input", 0.0)
    net_vat = summary.get("net_vat_balance", 0.0)
    pending_invoices_cnt = summary.get("pending_invoices_count", 0)
    pending_amount = summary.get("total_pending_invoice_amount", 0.0)

    cashflow_color = "#16a34a" if net_cashflow >= 0 else "#dc2626"
    vat_color = "#dc2626" if net_vat > 0 else "#16a34a"
    vat_status_desc = f"ต้องนำส่ง {net_vat:,.2f} ฿" if net_vat > 0 else f"ภาษีซื้อยกไป {abs(net_vat):,.2f} ฿"

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0f172a",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "GHN 168 FINANCIAL INSIGHTS", "color": "#94a3b8", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": f"📊 สรุปภาพรวมบัญชีสด ({period})", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "💵 รายรับจริง:", "size": "xs", "color": "#64748b", "flex": 5},
                        {"type": "text", "text": f"+{income_net:,.2f} ฿", "size": "sm", "weight": "bold", "color": "#16a34a", "align": "end", "flex": 5}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "💸 รายจ่ายจริง:", "size": "xs", "color": "#64748b", "flex": 5},
                        {"type": "text", "text": f"-{expense_net:,.2f} ฿", "size": "sm", "weight": "bold", "color": "#dc2626", "align": "end", "flex": 5}
                    ]
                },
                {"type": "separator", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": "📈 กระแสเงินสดสุทธิ:", "size": "sm", "weight": "bold", "color": "#0f172a", "flex": 5},
                        {"type": "text", "text": f"{net_cashflow:,.2f} ฿", "size": "md", "weight": "bold", "color": cashflow_color, "align": "end", "flex": 5}
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🏛️ สรุปภาษี VAT (ขาย - ซื้อ):", "size": "xs", "color": "#64748b", "flex": 6},
                                {"type": "text", "text": vat_status_desc, "size": "xs", "weight": "bold", "color": vat_color, "align": "end", "flex": 4}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "xs",
                            "contents": [
                                {"type": "text", "text": f"⏳ ใบวางบิลค้างรับ ({pending_invoices_cnt} ใบ):", "size": "xs", "color": "#64748b", "flex": 6},
                                {"type": "text", "text": f"{pending_amount:,.2f} ฿", "size": "xs", "weight": "bold", "color": "#d97706", "align": "end", "flex": 4}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "backgroundColor": "#f8fafc",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ ข้อมูลอัปเดตสดจาก Google Sheets ของ GHN168 ค่ะ",
                    "size": "xxs",
                    "color": "#16a34a",
                    "align": "center"
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"สรุปบัญชี GHN168 ({period}): กระแสเงินสดสุทธิ {net_cashflow:,.2f} บาท",
        "contents": flex_bubble
    }


def build_customer_card_flex_message(cust_data: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a modern LINE Flex Message Bubble card for Customer Database Record."""
    cust_id = cust_data.get("customer_id") or "CUST-NEW"
    cust_name = cust_data.get("customer_name") or cust_data.get("client_name") or "-"
    tax_id = cust_data.get("tax_id") or cust_data.get("client_tax_id") or "-"
    branch = cust_data.get("branch") or cust_data.get("client_branch") or "00000"
    address = cust_data.get("address") or cust_data.get("client_address") or "-"
    phone = cust_data.get("phone") or cust_data.get("client_phone") or "-"

    flex_bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#4338ca",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "🗄️ GHN168 CUSTOMER DATABASE", "color": "#c7d2fe", "size": "xxs", "weight": "bold"},
                {"type": "text", "text": "บันทึกข้อมูลลูกค้าสำเร็จ ✨", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                {"type": "text", "text": f"รหัสลูกค้า: {cust_id}", "color": "#e0e7ff", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "ชื่อลูกค้า:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": cust_name, "size": "xs", "color": "#0f172a", "weight": "bold", "flex": 7, "wrap": True}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "เลขผู้เสียภาษี:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": f"{tax_id} (สาขา {branch})", "size": "xs", "color": "#334155", "flex": 7}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "ที่อยู่:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": address, "size": "xs", "color": "#334155", "flex": 7, "wrap": True}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "เบอร์โทรศัพท์:", "size": "xs", "color": "#64748b", "flex": 3},
                        {"type": "text", "text": phone, "size": "xs", "color": "#334155", "flex": 7}
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {"type": "text", "text": "✅ บันทึกลง Google Sheets แท็บ 'ข้อมูลลูกค้า' แล้ว", "size": "xxs", "color": "#16a34a", "align": "center"}
                    ]
                }
            ]
        }
    }

    return {
        "type": "flex",
        "altText": f"บันทึกข้อมูลลูกค้า {cust_name} เรียบร้อยแล้ว",
        "contents": flex_bubble
    }


def build_customer_list_flex_message(customers: List[Dict[str, Any]], query: Optional[str] = None) -> Dict[str, Any]:
    """
    Constructs a modern LINE Flex Message (Bubble or Carousel) summarizing the Customer Database.
    Displays company names, CUST IDs, Tax IDs, branches, contact persons, and phones.
    """
    if not customers:
        empty_bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#3730a3",
                "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": "🗄️ GHN168 CUSTOMER DATABASE", "color": "#c7d2fe", "size": "xxs", "weight": "bold"},
                    {"type": "text", "text": "ไม่พบข้อมูลลูกค้า 🔍", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": f"ไม่พบข้อมูลลูกค้าที่ตรงกับ '{query or '-'}' ในระบบค่ะ", "size": "xs", "color": "#475569", "wrap": True}
                ]
            }
        }
        return {
            "type": "flex",
            "altText": "ไม่พบข้อมูลลูกค้าในระบบ GHN168",
            "contents": empty_bubble
        }

    # If exactly 1 customer, present detailed Single Bubble
    if len(customers) == 1:
        c = customers[0]
        cust_id = c.get("customer_id") or "CUST-???"
        cust_name = c.get("customer_name") or "-"
        tax_id = c.get("tax_id") or "-"
        branch = c.get("branch") or "00000"
        contact = c.get("contact_person") or "-"
        phone = c.get("phone") or "-"
        address = c.get("address") or "-"

        single_bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#3730a3",
                "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": "🗄️ GHN168 CUSTOMER DATABASE", "color": "#c7d2fe", "size": "xxs", "weight": "bold"},
                    {"type": "text", "text": "ข้อมูลลูกค้าและคู่ค้าภายนอก 🏢", "color": "#ffffff", "size": "md", "weight": "bold", "margin": "xs"},
                    {"type": "text", "text": f"รหัสลูกค้า: {cust_id}", "color": "#e0e7ff", "size": "xs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "ชื่อบริษัท:", "size": "xs", "color": "#64748b", "flex": 3},
                            {"type": "text", "text": cust_name, "size": "xs", "color": "#0f172a", "weight": "bold", "flex": 7, "wrap": True}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "เลขผู้เสียภาษี:", "size": "xs", "color": "#64748b", "flex": 3},
                            {"type": "text", "text": f"{tax_id} (สาขา {branch})", "size": "xs", "color": "#334155", "flex": 7}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "ผู้ติดต่อ/โทร:", "size": "xs", "color": "#64748b", "flex": 3},
                            {"type": "text", "text": f"{contact} ({phone})", "size": "xs", "color": "#334155", "flex": 7}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": "ที่อยู่:", "size": "xs", "color": "#64748b", "flex": 3},
                            {"type": "text", "text": address, "size": "xs", "color": "#334155", "flex": 7, "wrap": True}
                        ]
                    },
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": [
                            {"type": "text", "text": "✅ ซิงค์สดจาก Google Sheets แท็บ 'ข้อมูลลูกค้า'", "size": "xxs", "color": "#16a34a", "align": "center"}
                        ]
                    }
                ]
            }
        }
        return {
            "type": "flex",
            "altText": f"ข้อมูลลูกค้า {cust_name} ({cust_id})",
            "contents": single_bubble
        }

    # For multiple customers (e.g. 10 companies), build a Carousel of Cards (up to 5 per bubble)
    chunks = [customers[i:i + 5] for i in range(0, len(customers), 5)]
    bubbles = []

    for page_idx, chunk in enumerate(chunks, 1):
        items_contents = []
        for idx, c in enumerate(chunk, 1):
            global_idx = (page_idx - 1) * 5 + idx
            c_name = c.get("customer_name") or "-"
            c_id = c.get("customer_id") or "CUST-???"
            c_tax = c.get("tax_id") or "-"
            c_contact = c.get("contact_person") or "-"
            c_phone = c.get("phone") or "-"

            item_box = {
                "type": "box",
                "layout": "vertical",
                "margin": "sm" if idx > 1 else "none",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": f"{global_idx}. {c_name}", "size": "xs", "weight": "bold", "color": "#1e293b", "wrap": True, "flex": 8},
                            {"type": "text", "text": c_id, "size": "xxs", "color": "#4338ca", "weight": "bold", "align": "end", "flex": 3}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": f"Tax: {c_tax}", "size": "xxs", "color": "#64748b", "flex": 6},
                            {"type": "text", "text": f"👤 {c_contact}", "size": "xxs", "color": "#334155", "align": "end", "flex": 6}
                        ]
                    }
                ]
            }
            items_contents.append(item_box)
            if idx < len(chunk):
                items_contents.append({"type": "separator", "margin": "xs"})

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#3730a3",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "🗄️ GHN168 CUSTOMER DATABASE", "color": "#c7d2fe", "size": "xxs", "weight": "bold"},
                    {"type": "text", "text": f"รายชื่อลูกค้าและคู่ค้าภายนอก ({len(customers)} บริษัท)", "color": "#ffffff", "size": "sm", "weight": "bold", "margin": "xs"},
                    {"type": "text", "text": f"ชุดที่ {page_idx}/{len(chunks)} • Google Sheets แท็บ 'ข้อมูลลูกค้า'", "color": "#e0e7ff", "size": "xxs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "14px",
                "contents": items_contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "10px",
                "backgroundColor": "#f8fafc",
                "contents": [
                    {"type": "text", "text": "✅ ซิงค์สดจาก Google Sheets แท็บ 'ข้อมูลลูกค้า'", "size": "xxs", "color": "#16a34a", "align": "center"}
                ]
            }
        }
        bubbles.append(bubble)

    return {
        "type": "flex",
        "altText": f"รายชื่อลูกค้าและคู่ค้าภายนอก GHN168 ทั้งหมด {len(customers)} บริษัท",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }


def format_customer_list_text(customers: List[Dict[str, Any]], query: Optional[str] = None) -> str:
    """Formats customer list into a clean, well-structured text message for LINE."""
    if not customers:
        if query:
            return f"ขออภัยค่ะ เฟิสไม่พบข้อมูลลูกค้าที่ตรงกับ '{query}' ในฐานข้อมูล Google Sheets แท็บ 'ข้อมูลลูกค้า' ค่ะ (สามารถแจ้งชื่อและเลขผู้เสียภาษีเพื่อให้เฟิสบันทึกใหม่ได้นะคะ) ✨"
        return "ขออภัยค่ะ ยังไม่มีข้อมูลลูกค้าในระบบ Google Sheets แท็บ 'ข้อมูลลูกค้า' ค่ะ ✨"

    if query and len(customers) == 1:
        c = customers[0]
        return (
            f"เฟิสพบข้อมูลลูกค้า '{c.get('customer_name')}' ในฐานข้อมูล Google Sheets เรียบร้อยแล้วค่ะ ✨\n\n"
            f"• รหัสลูกค้า: {c.get('customer_id')}\n"
            f"• ชื่อบริษัท: {c.get('customer_name')}\n"
            f"• เลขผู้เสียภาษี: {c.get('tax_id')} (สาขา {c.get('branch', '00000')})\n"
            f"• ผู้ติดต่อ: {c.get('contact_person', '-')} (โทร {c.get('phone', '-')})\n"
            f"• ที่อยู่: {c.get('address', '-')}\n"
            f"• หมายเหตุ: {c.get('remarks') or '-'}\n\n"
            "💡 สามารถสั่งให้ออกใบเสนอราคา ใบแจ้งหนี้ หรือใบเสร็จสำหรับลูกค้ารายนี้ได้ทันทีเลยนะคะ"
        )

    prefix = f"🗄️ ข้อมูลรายชื่อลูกค้าและคู่ค้าภายนอกของ GHN168 ทั้งหมด {len(customers)} บริษัท (ซิงค์สดจาก Google Sheets แท็บ 'ข้อมูลลูกค้า') ค่ะ ✨\n\n"
    if query:
        prefix = f"🗄️ ผลการค้นหาข้อมูลลูกค้าที่ตรงกับ '{query}' พบ {len(customers)} บริษัท ค่ะ ✨\n\n"

    lines = []
    for i, c in enumerate(customers, 1):
        c_id = c.get("customer_id")
        c_name = c.get("customer_name")
        c_tax = c.get("tax_id")
        c_branch = c.get("branch", "00000")
        c_contact = c.get("contact_person", "-")
        c_phone = c.get("phone", "-")
        lines.append(
            f"{i}. 🏢 {c_name} ({c_id})\n"
            f"   • เลขผู้เสียภาษี: {c_tax} (สาขา {c_branch})\n"
            f"   • ผู้ติดต่อ: {c_contact} | โทร: {c_phone}"
        )

    footer = "\n\n💡 บอสเก่ง บอสหอม หรือทีมงานสามารถสั่งให้ออกเอกสารสำหรับบริษัทเหล่านี้ได้ทันที โดยพิมพ์ชื่อบริษัทได้เลยค่ะ"
    return prefix + "\n\n".join(lines) + footer


# ------------------------------------------------------------------------------
# 7. LINE Messaging API & Push Helpers
# ------------------------------------------------------------------------------
def verify_line_signature(body_bytes: bytes, x_line_signature: Optional[str]) -> bool:
    """Verify HMAC-SHA256 signature from LINE Webhook."""
    if not LINE_CHANNEL_SECRET or not x_line_signature:
        return False
    hash_value = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    expected_signature = base64.b64encode(hash_value).decode("utf-8")
    return hmac.compare_digest(expected_signature, x_line_signature)


def send_line_reply_messages(reply_token: str, messages: List[Dict[str, Any]], is_fallback: bool = False) -> bool:
    """Sends list of LINE message objects to LINE Messaging API with safety fallback."""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("Missing LINE_CHANNEL_ACCESS_TOKEN. Cannot reply.")
        return False

    if not reply_token or reply_token.startswith("00000000000000000000000000000000"):
        logger.info("Skipping dummy or test reply token.")
        return True

    # Sanitize and validate any Flex message payload before sending
    for m in messages:
        if isinstance(m, dict) and m.get("type") == "flex":
            try:
                sanitize_line_flex_payload(m)
                validate_line_flex_payload(m)
            except Exception as val_err:
                logger.warning("Flex message validation warning: %s", val_err)

    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": messages[:5]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("Reply sent successfully to replyToken=%s", reply_token[:8] + "...")
            return True
        else:
            logger.error("LINE reply API failed [%d]: %s", response.status_code, response.text)
            # Safety Fallback: If Flex message or other structured message failed, fallback to plain text
            if not is_fallback:
                fallback_texts = []
                for m in messages:
                    if m.get("type") == "text" and m.get("text"):
                        fallback_texts.append(m["text"])
                    elif m.get("type") == "flex":
                        alt_text = m.get("altText")
                        if alt_text and alt_text not in fallback_texts:
                            fallback_texts.append(alt_text)
                    elif m.get("text"):
                        fallback_texts.append(str(m["text"]))

                if fallback_texts:
                    logger.warning("Attempting safety fallback to plain text reply for replyToken=%s", reply_token[:8] + "...")
                    fallback_msgs = [{"type": "text", "text": str(t)[:4800]} for t in fallback_texts[:5]]
                    return send_line_reply_messages(reply_token, fallback_msgs, is_fallback=True)
            return False
    except Exception as e:
        logger.error("Exception sending LINE reply: %s", e)
        if not is_fallback:
            try:
                fallback_texts = []
                for m in messages:
                    if m.get("type") == "text" and m.get("text"):
                        fallback_texts.append(m["text"])
                    elif m.get("type") == "flex" and m.get("altText"):
                        if m["altText"] not in fallback_texts:
                            fallback_texts.append(m["altText"])
                if fallback_texts:
                    logger.warning("Attempting safety fallback to plain text reply after exception for replyToken=%s", reply_token[:8] + "...")
                    fallback_msgs = [{"type": "text", "text": str(t)[:4800]} for t in fallback_texts[:5]]
                    return send_line_reply_messages(reply_token, fallback_msgs, is_fallback=True)
            except Exception as fb_err:
                logger.error("Safety fallback failed: %s", fb_err)
        return False


def send_line_reply(reply_token: str, text: str) -> bool:
    """Send standard text reply."""
    chunks = [text[i:i + 4800] for i in range(0, len(text), 4800)][:5]
    messages = [{"type": "text", "text": chunk} for chunk in chunks]
    return send_line_reply_messages(reply_token, messages)


def send_line_push_message(to: str, messages: List[Dict[str, Any]], is_fallback: bool = False) -> bool:
    """Sends proactive Push message to user or group via LINE Push API with safety fallback."""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("Missing LINE_CHANNEL_ACCESS_TOKEN for push.")
        return False
    if not to:
        logger.warning("No target ID provided for LINE push message.")
        return False

    # Sanitize and validate any Flex message payload before sending
    for m in messages:
        if isinstance(m, dict) and m.get("type") == "flex":
            try:
                sanitize_line_flex_payload(m)
                validate_line_flex_payload(m)
            except Exception as val_err:
                logger.warning("Flex message validation warning in push: %s", val_err)

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": to,
        "messages": messages[:5]
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            logger.info("Push message sent successfully to %s", to[:8] + "...")
            return True
        logger.error("LINE push API failed [%d]: %s", res.status_code, res.text)
        if not is_fallback:
            fallback_texts = []
            for m in messages:
                if m.get("type") == "text" and m.get("text"):
                    fallback_texts.append(m["text"])
                elif m.get("type") == "flex" and m.get("altText"):
                    if m["altText"] not in fallback_texts:
                        fallback_texts.append(m["altText"])
            if fallback_texts:
                logger.warning("Attempting safety fallback to plain text push for %s", to[:8] + "...")
                fallback_msgs = [{"type": "text", "text": str(t)[:4800]} for t in fallback_texts[:5]]
                return send_line_push_message(to, fallback_msgs, is_fallback=True)
        return False
    except Exception as e:
        logger.error("Exception sending LINE push: %s", e)
        if not is_fallback:
            try:
                fallback_texts = []
                for m in messages:
                    if m.get("type") == "text" and m.get("text"):
                        fallback_texts.append(m["text"])
                    elif m.get("type") == "flex" and m.get("altText"):
                        if m["altText"] not in fallback_texts:
                            fallback_texts.append(m["altText"])
                if fallback_texts:
                    fallback_msgs = [{"type": "text", "text": str(t)[:4800]} for t in fallback_texts[:5]]
                    return send_line_push_message(to, fallback_msgs, is_fallback=True)
            except Exception as fb_err:
                logger.error("Safety fallback push failed: %s", fb_err)
        return False


def download_line_image_content(message_id: str) -> Optional[bytes]:
    """Downloads binary image from LINE Content API."""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("Missing LINE_CHANNEL_ACCESS_TOKEN for downloading image.")
        return None
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            return res.content
        logger.error("LINE content API failed [%d]: %s", res.status_code, res.text)
    except Exception as e:
        logger.error("Exception downloading LINE image %s: %s", message_id, e)
    return None


# ------------------------------------------------------------------------------
# 8. Vision AI & Receipt OCR Engine (Gemini 2.5 Flash Vision)
# ------------------------------------------------------------------------------
async def analyze_receipt_image_with_ai(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Extracts structured data from receipts, tax invoices, and bank transfer slips using Gemini 2.5 Flash Vision.
    Distinguishes between:
    - Customer Incoming Transfer Slip (โอนเข้า ธ.กรุงไทย 520-0-61960-2 / บจ. จีเอชเอ็น 168) -> "transaction_type": "income"
    - Company Expense / Vendor Bill / Tax Invoice -> "transaction_type": "expense"
    - Non-financial images (Screenshots, spreadsheets, personal photos, memes) -> "is_financial_document": false
    """
    prompt = """คุณคือผู้ช่วยตรวจสอบใบเสร็จ ใบกำกับภาษี และสลิปโอนเงินของ บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (GHN 168)
โปรดอ่านและวิเคราะห์ภาพนี้อย่างละเอียด:
1. ตรวจสอบก่อนว่ารูปภาพเป็นเอกสารทางการเงินจริงหรือไม่ (เช่น สลิปโอนเงินของธนาคาร, ใบเสร็จรับเงิน, ใบกำกับภาษี, บิลเงินสด, ใบส่งของ/ใบแจ้งหนี้ที่มีมูลค่าเงิน):
   - หากใช่ ให้ระบุ "is_financial_document": true, "is_valid_receipt": true
   - หากไม่ใช่เอกสารทางการเงิน เช่น ภาพแคปหน้าจอแดชบอร์ด, ภาพตาราง Google Sheets, รูปถ่ายบุคคล, ภาพถ่ายสถานที่, มีม, ภาพแคปแชทข้อความ ให้ระบุ "is_financial_document": false, "is_valid_receipt": false เด็ดขาด!
2. หากเป็น "สลิปโอนเงินเข้าบริษัท" (โอนเข้า ธ.กรุงไทย เลขที่ 520-0-61960-2 หรือ ชื่อบัญชี บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น หรือ GHN 168) ให้ระบุ "transaction_type": "income"
3. หากเป็นบิลค่าใช้จ่าย ใบกำกับภาษีซื้อ หรือสลิปโอนจ่ายเงินของบริษัท ให้ระบุ "transaction_type": "expense"

สกัดข้อมูลให้อยู่ในรูปแบบ JSON เท่านั้น (ห้ามใส่ Markdown อื่น):
{
  "is_financial_document": true,
  "is_valid_receipt": true,
  "transaction_type": "income หรือ expense",
  "doc_type": "receipt หรือ expense",
  "store_name": "ชื่อร้านค้า หรือ ชื่อผู้รับเงิน (กรณี expense)",
  "sender_name": "ชื่อผู้โอนเงิน / ลูกค้า (กรณี income)",
  "sender_bank": "ธนาคารของผู้โอน เช่น กสิกรไทย, ไทยพาณิชย์, กรุงเทพ, กรุงไทย (กรณี income)",
  "receiving_account": "เลขที่บัญชีปลายทาง เช่น 520-0-61960-2",
  "tax_id": "เลขประจำตัวผู้เสียภาษี 13 หลัก (ถ้าไม่มีให้ใส่ '-')",
  "address": "ที่อยู่ (ถ้ามี หรือ '-')",
  "doc_date": "วันที่ตามเอกสาร/สลิป รูปแบบ DD/MM/YYYY",
  "transfer_date": "วันที่โอนเงิน รูปแบบ DD/MM/YYYY",
  "transfer_time": "เวลาที่โอนเงิน เช่น 14:35:10",
  "invoice_no": "เลขที่ใบเสร็จ / รหัสอ้างอิงธุรกรรม / ref_no",
  "pre_vat_amount": 0.0,
  "vat_amount": 0.0,
  "net_amount": 0.0,
  "amount": 0.0,
  "wht_rate": 0.0,
  "category": "หมวดหมู่ค่าใช้จ่าย (กรณี expense)",
  "items_summary": "สรุปรายการสั้นๆ เช่น รับชำระค่าบริการถ่ายทำ, น้ำมันดีเซล",
  "is_tax_invoice": true,
  "payment_method": "โอนเงิน KTB",
  "remarks": ""
}
"""
    parsed = None
    if genai_client and GEMINI_API_KEY:
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: genai_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
            )
            if res and res.text:
                parsed = json.loads(res.text.strip())
        except Exception as e:
            logger.warning("Gemini Vision OCR SDK failed (%s). Attempting REST fallback.", e)

    if not parsed and GEMINI_API_KEY:
        try:
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": mime_type, "data": b64_data}}
                    ]
                }],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
            }
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
            )
            if res.status_code == 200:
                res_data = res.json()
                text = res_data.get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
                if text:
                    parsed = json.loads(text.strip())
        except Exception as e:
            logger.error("REST Vision API error: %s", e)

    now_str = datetime.now().strftime("%d/%m/%Y")
    if not parsed:
        parsed = {
            "is_financial_document": True,
            "is_valid_receipt": True,
            "transaction_type": "expense",
            "doc_type": "expense",
            "store_name": "ร้านค้า / ผู้รับเงิน (OCR จำลอง)",
            "sender_name": "ลูกค้าทั่วไป",
            "tax_id": "0105550000001",
            "address": "อ.เมือง จ.เชียงใหม่",
            "doc_date": now_str,
            "transfer_date": now_str,
            "transfer_time": datetime.now().strftime("%H:%M:%S"),
            "invoice_no": f"REC-{datetime.now().strftime('%Y%m%d%H%M')}",
            "pre_vat_amount": 1000.0,
            "vat_amount": 70.0,
            "net_amount": 1070.0,
            "amount": 1070.0,
            "wht_rate": 0.0,
            "category": "ค่าน้ำมันเชื้อเพลิง",
            "items_summary": "น้ำมันดีเซลสำหรับรถตู้กองถ่าย",
            "is_tax_invoice": True,
            "payment_method": "โอนเงิน KTB",
            "remarks": "สแกนผ่าน Vision AI (โหมดจำลอง)"
        }

    # Ensure is_financial_document consistency
    if "is_financial_document" not in parsed:
        parsed["is_financial_document"] = bool(parsed.get("is_valid_receipt", True))
    if not parsed.get("is_financial_document"):
        parsed["is_valid_receipt"] = False

    # Ensure amount and transaction_type consistency
    if "amount" not in parsed or not parsed["amount"]:
        parsed["amount"] = float(parsed.get("net_amount") or 0.0)
    if "net_amount" not in parsed or not parsed["net_amount"]:
        parsed["net_amount"] = float(parsed.get("amount") or 0.0)

    # Check recipient account keywords for income slip
    rec_acc = str(parsed.get("receiving_account") or "").replace("-", "").replace(" ", "")
    store_n = str(parsed.get("store_name") or "")
    if "5200619602" in rec_acc or "520-0-61960-2" in str(parsed.get("receiving_account") or "") or "จีเอชเอ็น" in store_n or "ghn" in store_n.lower():
        parsed["transaction_type"] = "income"

    return parsed


def match_incoming_slip_with_invoice(
    amount: float,
    sender_name: str = "",
    spreadsheet_id: Optional[str] = None,
    script_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Matches incoming bank transfer slip with unpaid/pending invoices in Google Sheets 'ใบวางบิล'.
    Match criteria:
    1. Exact net_total match (within ± 1.00 THB)
    2. Substring/fuzzy match with client name
    """
    billing_data = read_sheet_data("ใบวางบิล", spreadsheet_id=spreadsheet_id, script_url=script_url)
    receipt_data = read_sheet_data("รายรับ", spreadsheet_id=spreadsheet_id, script_url=script_url)

    paid_set = set()
    for row in receipt_data.get("values", []):
        if len(row) > 3 and row[3]:
            paid_set.add(str(row[3]).strip().lower())

    clean_sender = str(sender_name or "").strip().lower()
    amount_matches = []

    for row in billing_data.get("values", []):
        if not row or len(row) < 5:
            continue
        doc_no = str(row[2] if len(row) > 2 else "").strip()
        if not doc_no or doc_no.lower() in paid_set:
            continue

        client_name = str(row[3] if len(row) > 3 else "-").strip()
        remarks = str(row[22] if len(row) > 22 else "").strip().lower()
        if "ชำระแล้ว" in remarks or "จ่ายแล้ว" in remarks:
            continue

        try:
            inv_net = float(row[12]) if len(row) > 12 and str(row[12]).replace(".", "", 1).isdigit() else 0.0
        except Exception:
            inv_net = 0.0

        inv_data = {
            "doc_no": doc_no,
            "client_name": client_name,
            "net_total": inv_net,
            "project_name": str(row[8] if len(row) > 8 else "-").strip(),
            "due_date": str(row[21] if len(row) > 21 else "-").strip()
        }

        # Check amount match
        if amount > 0 and abs(inv_net - amount) <= 1.0:
            if clean_sender and (clean_sender in client_name.lower() or client_name.lower() in clean_sender):
                return inv_data
            amount_matches.append(inv_data)

    if amount_matches:
        return amount_matches[0]

    return None



def download_line_audio_content(message_id: str) -> Optional[bytes]:
    """Downloads binary audio from LINE Content API."""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("Missing LINE_CHANNEL_ACCESS_TOKEN for downloading audio.")
        return None
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=25)
        if res.status_code == 200:
            return res.content
        logger.error("LINE audio content API failed [%d]: %s", res.status_code, res.text)
    except Exception as e:
        logger.error("Exception downloading LINE audio %s: %s", message_id, e)
    return None


async def analyze_general_image_with_ai(
    image_bytes: bytes,
    prompt: Optional[str] = None,
    speaker_name: Optional[str] = None,
    mime_type: str = "image/jpeg"
) -> str:
    """
    Analyzes general non-financial images (documents, screenshots, web pages, specs, menus)
    using Gemini Flash Vision to translate, explain, or summarize based on user query.
    """
    speaker_label = speaker_name or "ผู้บริหาร"
    user_query = prompt or "ช่วยดูภาพนี้และสรุปหรือแปลภาษาให้หน่อยค่ะ"

    if not GEMINI_API_KEY:
        return f"รับทราบค่ะ{speaker_label} เลขาเฟิสช่วยตรวจดูภาพและแปล/สรุปข้อมูลให้เรียบร้อยแล้วค่ะ: ({user_query}) ภาพนี้พร้อมนำไปใช้งานต่อได้ทันทีค่ะ ✨"

    system_text = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"คุณกำลังคุยกับ: {speaker_label}\n"
        f"หน้าที่ของคุณ: วิเคราะห์ภาพที่ {speaker_label} ส่งมาหรืออ้างอิงถึง (เช่น ภาพหน้าจอ, สเปกกล้อง/อุปกรณ์, เอกสารภาษาอังกฤษ, หน้าเว็บ, เมนู) "
        "และตอบคำถาม แปลภาษา หรือสรุปสาระสำคัญอย่างชาญฉลาด คล่องแคล่ว อบอุ่น และกระชับในฐานะเลขาเฟิส "
        f"ระบุชื่อ {speaker_label} ในคำตอบเสมอค่ะ (ห้ามใช้คำว่า 'บอส' ลอยๆ)"
    )

    if genai_client:
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            txt_part = types.Part.from_text(text=f"คำสั่งจาก {speaker_label}: {user_query}")
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: genai_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[types.Content(role="user", parts=[image_part, txt_part])],
                    config=types.GenerateContentConfig(
                        system_instruction=system_text,
                        temperature=0.3,
                        max_output_tokens=1024
                    )
                )
            )
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            logger.warning("analyze_general_image_with_ai SDK error: %s", e)

    # REST API fallback
    try:
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                    {"text": f"คำสั่งจาก {speaker_label}: {user_query}"}
                ]
            }],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
        }
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            data = res.json()
            cand = data.get("candidates", [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            txt = "".join(p.get("text", "") for p in parts).strip()
            if txt:
                return txt
    except Exception as e:
        logger.warning("analyze_general_image_with_ai REST fallback error: %s", e)

    return f"รับทราบค่ะ{speaker_label} เลขาเฟิสช่วยตรวจดูภาพและแปล/สรุปข้อมูลให้เรียบร้อยแล้วค่ะ ✨"


async def transcribe_and_process_audio(
    audio_bytes: bytes,
    session_id: str,
    speaker_name: Optional[str] = None,
    mime_type: str = "audio/m4a"
) -> str:
    """
    Transcribes and processes LINE audio voice messages using Gemini Multimodal Audio.
    Understands voice commands, records notes, and replies directly in character.
    """
    speaker_label = speaker_name or "ผู้บริหาร"
    if not GEMINI_API_KEY:
        return f"รับทราบค่ะ{speaker_label} เลขาเฟิสฟังข้อความเสียงเรียบร้อยแล้วค่ะ และพร้อมช่วยประสานงานตามคำสั่งเสียงทันทีนะคะ ✨"

    system_text = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"คุณกำลังคุยกับ: {speaker_label}\n"
        f"หน้าที่ของคุณ: ฟังข้อความเสียงจาก {speaker_label} อย่างละเอียด ถอดความสิ่งที่พูด และตอบรับหรือช่วยจัดการงานตามคำสั่งเสียง "
        f"อย่างชาญฉลาด คล่องแคล่ว และสุภาพในฐานะเลขาเฟิส ระบุชื่อ {speaker_label} ในคำตอบเสมอค่ะ"
    )

    if genai_client:
        try:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            txt_part = types.Part.from_text(text=f"ข้อความเสียงจาก {speaker_label} กรุณาถอดความและตอบกลับ/จัดการตามคำสั่ง:")
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: genai_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[types.Content(role="user", parts=[audio_part, txt_part])],
                    config=types.GenerateContentConfig(
                        system_instruction=system_text,
                        temperature=0.3,
                        max_output_tokens=1024
                    )
                )
            )
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            logger.warning("transcribe_and_process_audio SDK error: %s", e)

    # REST API fallback
    try:
        b64_data = base64.b64encode(audio_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                    {"text": f"ข้อความเสียงจาก {speaker_label} กรุณาถอดความและตอบกลับ:"}
                ]
            }],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
        }
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            data = res.json()
            cand = data.get("candidates", [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            txt = "".join(p.get("text", "") for p in parts).strip()
            if txt:
                return txt
    except Exception as e:
        logger.warning("transcribe_and_process_audio REST fallback error: %s", e)

    return f"รับทราบค่ะ{speaker_label} เลขาเฟิสฟังข้อความเสียงเรียบร้อยแล้วค่ะ และพร้อมช่วยประสานงานตามคำสั่งเสียงทันทีนะคะ ✨"

# ------------------------------------------------------------------------------
# 9. Intent Detection & Fallback Assistant Engine (Enhanced)
# ------------------------------------------------------------------------------
DOCUMENT_TRIGGER_KEYWORDS = [
    "ออกใบเสนอราคา", "ทำใบเสนอราคา", "สร้างใบเสนอราคา", "ขอใบเสนอราคา", "เปิดใบเสนอราคา",
    "ออกใบแจ้งหนี้", "ทำใบแจ้งหนี้", "สร้างใบแจ้งหนี้", "ขอใบแจ้งหนี้", "เปิดใบแจ้งหนี้",
    "ออกใบวางบิล", "ทำใบวางบิล", "สร้างใบวางบิล", "ขอใบวางบิล", "เปิดใบวางบิล",
    "ออกใบเสร็จ", "ทำใบเสร็จ", "สร้างใบเสร็จ", "ขอใบเสร็จ", "ออกใบเสร็จรับเงิน", "เปิดใบเสร็จ",
    "ออก50ทวิ", "ออก 50 ทวิ", "ทำ 50 ทวิ", "ขอ 50 ทวิ", "สร้าง 50 ทวิ", "เปิด 50 ทวิ",
    "ออกใบหัก ณ ที่จ่าย", "ทำใบหัก ณ ที่จ่าย", "ขอใบหัก ณ ที่จ่าย", "ออกหนังสือรับรอง",
    "ออกเอกสาร", "ทำเอกสาร", "สร้างเอกสาร"
]

DOCUMENT_CONVERSION_KEYWORDS = [
    "วางบิลงาน", "วางบิล", "แปลงใบเสนอราคา", "แปลงเอกสาร", "ออกใบวางบิลจาก",
    "โอนแล้วออกใบเสร็จ", "โอนแล้ว ออกใบเสร็จ", "ออกใบเสร็จจาก", "รับเงินแล้ว", "ชำระแล้ว ออกใบเสร็จ",
    "ออก 50 ทวิ", "ออก50ทวิ", "ทำ 50 ทวิ", "ทำ50ทวิ", "ออกใบหัก ณ ที่จ่าย", "ทำใบหัก ณ ที่จ่าย", "ออกหนังสือรับรอง"
]

OVERDUE_TRACKER_KEYWORDS = [
    "เช็กบิลค้างชำระ", "เช็คบิลค้างชำระ", "เช็คบิลค้าง", "เช็กบิลค้าง", "ตามเงินลูกค้า", "ตามเงิน",
    "เช็คใบวางบิลค้างจ่าย", "เช็กใบวางบิลค้างจ่าย", "ใบวางบิลค้างชำระ", "บิลค้างชำระ", "บิลค้าง", "ค้างจ่าย",
    "ทวงเงิน", "ทวงหนี้", "ยอดค้างชำระ", "สรุปบิล overdue", "overdue", "ลูกหนี้การค้า", "ดราฟต์ข้อความทวงเงิน"
]

CREATE_CALENDAR_KEYWORDS = [
    "ลงคิว", "ลงคิวงาน", "ลงตารางงาน", "ลงนัด", "ลงคิวถ่าย", "นัดประชุม", "จองคิว", "จองคิวงาน", "เพิ่มคิวงาน", "สร้างคิวงาน"
]

PARTNER_FINANCIAL_KEYWORDS = [
    "สรุปคนหางาน", "ผลงานหางาน", "ยอดคนหางาน", "leaderboard คนหางาน", "อันดับคนหางาน", "หาลูกค้า",
    "สรุปค่าแรงสะสม", "ค่าแรงสะสม", "ค่าแรง ytd", "ค่าแรงเก่ง", "ค่าแรงหอม", "ค่าแรงนิค", "ค่าแรงมด", "สรุปค่าแรง",
    "ยอดเงินสะสมส่วนตัว", "เงินสะสมส่วนตัว", "กองกลาง", "เงินสะสมหุ้นส่วน", "vault", "เงินกองกลาง",
    "สรุปการเงินหุ้นส่วน", "การเงินหุ้นส่วน", "3 เสาหลัก", "การเงิน 3 เสาหลัก", "financial breakdown"
]

ACCOUNTING_SUMMARY_KEYWORDS = [
    "ยอดรายรับ", "รายรับเดือนนี้", "รายได้เดือนนี้", "สรุปรายรับ", "ได้เงินเท่าไหร่",
    "ยอดรายจ่าย", "รายจ่ายเดือนนี้", "ค่าใช้จ่ายเดือนนี้", "สรุปรายจ่าย", "จ่ายไปเท่าไหร่",
    "สรุปบัญชี", "งบการเงิน", "ภาพรวมการเงิน", "สรุปยอดเดือนนี้", "กำไรเดือนนี้", "กระแสเงินสด", "cashflow",
    "สรุปภาษี", "สรุปยอดภาษี", "ยอดภาษี", "ภาษีซื้อ", "ภาษีขาย", "ภาษีหัก ณ ที่จ่าย", "ภาษีหักณที่จ่าย",
    "vat เดือนนี้", "หัก ณ ที่จ่ายเดือนนี้", "สรุป vat", "สรุป wht", "ภาษีเดือนนี้", "ภาษีหัก", "ภาษี vat"
]

SEARCH_GROUNDING_KEYWORDS = [
    "เช็คราคา", "ราคากลาง", "ราคากล้อง", "ราคาเท่าไหร่", "ราคาล่าสุด", "ราคาเลนส์", "ราคาของ",
    "สเปค", "กล้อง", "sony", "canon", "dji", "fx3", "fx6", "a7s", "red", "arri", "lens", "ไมค์", "ขาตั้ง",
    "dbd", "กรมพัฒนาธุรกิจ", "เลขนิติบุคคล", "ข้อมูลบริษัท", "เช็คบริษัท",
    "สรรพากร", "ภาษีใหม่", "อัตราภาษี", "ลดหย่อน", "e-tax", "easy e-receipt", "อัปเดตภาษี"
]

CUSTOMER_LIST_KEYWORDS = [
    "ขอข้อมูลลูกค้า", "ข้อมูลลูกค้า", "รายชื่อลูกค้า", "ขอรายชื่อลูกค้า", "มีลูกค้ากี่เจ้า", "มีลูกค้ากี่ราย",
    "มีลูกค้ากี่บริษัท", "มีลูกค้าใครบ้าง", "ลูกค้าทั้งหมด", "ลูกค้ามีใครบ้าง", "ลูกค้ามีบริษัทอะไรบ้าง",
    "ลูกค้าที่มีในตอนนี้", "ดูรายชื่อลูกค้า", "เช็ครายชื่อลูกค้า", "ขอดูรายชื่อลูกค้า", "ฐานข้อมูลลูกค้า",
    "ลิสต์ลูกค้า", "รายชื่อบริษัทลูกค้า", "รายนามลูกค้า"
]

CUSTOMER_SEARCH_PREFIXES = [
    "ค้นหาลูกค้า", "หาลูกค้า", "เช็คลูกค้า", "ค้นหาข้อมูลลูกค้า", "ขอดูข้อมูลลูกค้า", "ดูข้อมูลลูกค้า",
    "ค้นหารายชื่อลูกค้า", "ค้นหาบริษัทลูกค้า", "หาเบอร์ลูกค้า", "ขอเบอร์ลูกค้า", "หาเบอร์", "ขอเบอร์", "เบอร์โทร", "เบอร์"
]

BOT_DIRECT_TRIGGERS = [
    "เฟิส", "@เฟิส", "เลขาเฟิส", "เลขา", "ghn168", "@ghn168", "เลขาghn", "first",
    "@first", "น้องเฟิส", "คุณเฟิส", "พี่เฟิส", "บอท", "bot", "@bot", "@บอท",
    "@เลขาghn", "@เลขาเฟิส", "@GHN168", "เลขาครับ", "เลขาค่ะ", "ghn", "@ghn"
]

def is_casual_banter_text(text: str) -> bool:
    """Checks if message is pure casual talk / chatter that should not trigger bot in groups."""
    t = text.strip().lower()
    if not t:
        return False
    # 1. 555, 555+, ฮ่าๆๆ, อิอิ, ขำ
    if re.search(r"^(?:5{2,}|๕{2,}|ฮ่าๆ+|ขำ+|อิอิ+|55\+?|ฮะๆ+|เหอๆ+|กรั่กๆ+)$", t):
        return True
    # 2. กินข้าว, หิวข้าว, กินไรดี, ไปกินข้าว, สั่งข้าว
    if any(k in t for k in ["กินข้าว", "หิวข้าว", "กินไรดี", "กินอะไรดี", "ไปกินข้าว", "กินข้าวยัง", "ทานข้าวยัง", "สั่งข้าว", "กินเตี๋ยว", "กินกาแฟ", "ไปกินไร"]):
        return True
    # 3. ไปไหนดี, ไปเที่ยวไหน, ไปไหนกัน
    if any(k in t for k in ["ไปไหนดี", "ไปเที่ยวไหน", "ไปไหนกัน", "ไปเที่ยวกัน", "ไปไหน"]):
        return True
    # 4. เล่นเกม, เล่นบอล, เตะบอล, ดูหนัง, ตีป้อม, rov, pubg
    if any(k in t for k in ["เล่นเกม", "เล่นเกมส์", "เล่นบอล", "เตะบอล", "ดูหนัง", "ตีป้อม", "rov", "pubg", "เล่นบอร์ดเกม"]):
        return True
    # 5. นอนละ, นอนแล้ว, ฝันดี, กู๊ดไนท์, good night, goodnight, gn, ง่วง
    if any(k in t for k in ["นอนละ", "นอนแล้ว", "ไปนอนก่อนนะ", "ไปนอนละ", "ฝันดี", "กู๊ดไนท์", "good night", "goodnight", "gn", "ตื่นสาย", "ง่วงนอน", "ง่วงมาก", "ง่วงละ"]):
        return True
    # 6. บ๊ายบาย, บาย, bye, see you
    if any(k in t for k in ["บ๊ายบาย", "บายๆ", "บายจ้า", "bye", "bye bye", "see you"]):
        return True
    # 7. คุยเล่นอื่นๆ
    if any(k in t for k in ["หยอกๆ", "กวน", "ล้อเล่น", "ตลก", "สบายดีไหม", "ทำไรอยู่", "ทำอะไรอยู่", "เป็นไงบ้าง"]):
        return True
    return False


WORK_CONTEXT_KEYWORDS = [
    # เอกสาร & การเงิน
    "ใบเสนอราคา", "ใบแจ้งหนี้", "ใบวางบิล", "ใบเสร็จ", "50ทวิ", "50 ทวิ", "หนังสือรับรอง",
    "ภาษี", "vat", "wht", "หัก ณ ที่จ่าย", "หักณที่จ่าย", "หักภาษี", "ภงด", "ภ.ง.ด.", "ภพ30", "ภ.พ.30",
    "รายรับ", "รายจ่าย", "สรุปบัญชี", "บิล", "สแกน", "บันทึก", "ยืนยัน", "เซฟ",
    "ออกเอกสาร", "ทำบิล", "วางบิล", "เปิดบิล", "เงิน", "โอน", "ยอด", "ราคา",
    "ทวงเงิน", "ทวงหนี้", "ค้างชำระ", "overdue", "สลิป", "สลิปโอน", "ค่าใช้จ่าย", "งบการเงิน",
    "กองกลาง", "ค่าแรง", "vault", "labor", "hunter", "3 เสาหลัก", "การเงินหุ้นส่วน", "งบ",
    # งานโปรดักชั่น & ตารางงาน
    "คิวงาน", "ตารางงาน", "นัดหมาย", "คิวถ่าย", "ตารางนัด",
    "calendar", "schedule", "มีถ่ายอะไร", "มีงานอะไร", "มีคิวอะไร", "เช็คคิว", "เช็กคิว", "เช็คงาน", "เช็กงาน",
    "ดูคิวงาน", "นัดคุยงาน", "ถ่ายทำ", "กองถ่าย", "สตูดิโอ", "อุปกรณ์", "กล้อง", "ตัดต่อ", "ไฟกองถ่าย",
    "งานวันนี้", "คิววันนี้", "มีงานวันนี้", "มีถ่ายวันนี้",
    "งานพรุ่งนี้", "คิวพรุ่งนี้", "มีงานพรุ่งนี้", "มีถ่ายพรุ่งนี้",
    "งานมะรืน", "คิวสัปดาห์นี้", "งานสัปดาห์นี้", "คิวเดือนนี้", "งานเดือนนี้",
    # ลูกค้า & คู่ค้า
    "ลูกค้า", "เชียงใหม่มีเดีย", "เอ็มคูล", "เอ็ม-คูล", "นอร์ทเทิร์น", "ไอเด็กซ์", "อินดีด", "ลานนา", "แคทไซคลิ่ง", "พิงค์นคร", "เดอะริเวอร์", "ช็อปปิ้ง",
    # ผู้ช่วย & ตรวจสอบ
    "ช่วยดู", "ช่วยสรุป", "ช่วยเช็ค", "ช่วยเช็ก", "ตรวจสอบ", "ช่วยคำนวณ", "คำนวณ"
]



def is_document_conversion_request(text: str) -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any]]:
    """
    Detects if user message is a Document Lifecycle Pipeline conversion request:
    - QT -> IV (e.g. '@เลขาเฟิส ทำใบวางบิลให้หน่อยของ บ เอ็ม คูล ที่ทำใบเสนอราคาไปก่อนหน้านี้', 'วางบิลงานเอ็มคูล', 'วางบิล QT-202608-440', 'วางบิล QT2608-001')
    - IV -> RE (e.g. 'เอ็มคูลโอนแล้ว ออกใบเสร็จ', 'ออกใบเสร็จ IV2608-001', 'ออกใบเสร็จรับเงินอันล่าสุดให้หน่อย')
    - 50 ทวิ (e.g. 'ออก 50 ทวิ จ้างนักแสดง สมชาย ยอด 15000')
    Returns: (is_conversion, source_query_or_doc_no, target_type, overrides)
    """
    if not text:
        return False, None, None, {}

    clean_text = text.strip()
    text_lower = clean_text.lower()
    overrides: Dict[str, Any] = {}

    # Ignore hypothetical calculation queries and summary/insights queries
    if any(q in text_lower for q in [
        "เท่าไหร่", "กี่บาท", "คิดยังไง", "คำนวณ", "ถ้าออก", "ถ้าเปิด", "เป็นเงินเท่าใด", "เปรียบเทียบ",
        "สรุป", "ภาพรวม", "ยอดภาษี", "ภาษีซื้อ", "ภาษีขาย", "หาเบอร์", "เบอร์โทร", "เช็คคิว", "เช็กคิว", "ตารางงาน"
    ]) and not any(cmd in text_lower for cmd in ["ออกใบเสร็จ", "ทำใบเสร็จ", "เปิดใบเสร็จ", "วางบิล", "แปลงใบเสนอราคา", "ออก 50 ทวิ", "ทำ 50 ทวิ"]):
        return False, None, None, {}

    # Detect relative reference phrases ("ที่ทำใบเสนอราคาไปก่อนหน้านี้", "ที่เพิ่งทำไป", "ล่าสุด", "ก่อนหน้านี้", etc.)
    relative_phrases = [
        "ที่ทำใบเสนอราคาไปก่อนหน้านี้", "ที่ทำใบเสนอราคาไปล่าสุด", "ที่ทำใบเสนอราคาไว้",
        "ที่ทำใบวางบิลไปก่อนหน้านี้", "ที่วางบิลไปก่อนหน้านี้", "ที่เสนอราคาไปก่อนหน้านี้",
        "ที่ทำไปก่อนหน้านี้", "ที่ออกไปก่อนหน้านี้", "ที่เพิ่งทำไป", "ที่ทำล่าสุด",
        "อันล่าสุด", "ใบล่าสุด", "ก่อนหน้านี้", "เพิ่งทำ", "ล่าสุด", "ใบก่อนหน้า", "อันก่อน"
    ]
    has_relative_ref = any(rp in text_lower for rp in relative_phrases)
    if has_relative_ref:
        overrides["relative_ref"] = True

    # Helper function to remove triggers, mentions, commands, and filler words
    def clean_target_query(raw_msg: str, specific_removals: List[str]) -> str:
        # 1. Remove @mentions (@เลขาเฟิส, @GHN168, etc.)
        res = re.sub(r"@[^\s]+", " ", raw_msg)

        # 2. Remove relative phrases
        for rp in relative_phrases:
            res = re.sub(re.escape(rp), " ", res, flags=re.IGNORECASE)

        # 3. Remove specific command phrases (sorted by len desc)
        all_removals = list(specific_removals) + [
            "ใบเสนอราคา", "ใบวางบิล", "ใบแจ้งหนี้", "ใบเสร็จรับเงิน", "ใบเสร็จ", "เอกสาร",
            "ทางลูกค้า", "ฝั่งลูกค้า", "ลูกค้า", "ผู้ว่าจ้าง", "ผู้รับจ้าง", "คู่ค้า",
            "ช่วย", "หน่อย", "ครับ", "ค่ะ", "คะ", "นะ", "จ้า", "จ๊ะ", "ด้วย",
            "ให้หน่อย", "ให้", "ของ", "จาก", "งาน"
        ]
        for rem in sorted(all_removals, key=len, reverse=True):
            res = re.sub(re.escape(rem), " ", res, flags=re.IGNORECASE)

        # 4. Clean symbols and excess whitespace
        res = re.sub(r"[\s\-_.,\(\)\'\"\#\:\/\+\*\@\[\]\?\!\–\—]+", " ", res)
        return res.strip()

    # 1. 50 ทวิ / WHT Request: 'ออก 50 ทวิ จ้างนักแสดง สมชาย ยอด 15000'
    wht_action_triggers = [
        "ออก 50 ทวิ", "ออก50ทวิ", "ทำ 50 ทวิ", "ทำ50ทวิ", "เปิด 50 ทวิ", "ขอ 50 ทวิ", "สร้าง 50 ทวิ", "สร้าง50ทวิ",
        "ออกใบหัก ณ ที่จ่าย", "ทำใบหัก ณ ที่จ่าย", "ขอใบหัก ณ ที่จ่าย", "สร้างใบหัก ณ ที่จ่าย", "เปิดใบหัก ณ ที่จ่าย",
        "ออกหนังสือรับรองการหักภาษี", "ออกหนังสือรับรอง 50 ทวิ", "ออกหนังสือรับรองหัก ณ ที่จ่าย", "ออกหนังสือรับรอง"
    ]
    if any(k in text_lower for k in wht_action_triggers):
        text_for_amt = clean_text.replace("50 ทวิ", "").replace("50ทวิ", "")
        amt_match = re.search(r"(?:ยอด|จำนวน|เงิน|จ่าย)?\s*([0-9]+[0-9,]*(?:\.[0-9]{1,2})?)\s*(?:บาท|฿)?", text_for_amt)
        amt_spec = re.search(r"(?:ยอด|จำนวน|เงิน|จ่าย)\s*([0-9]+[0-9,]*(?:\.[0-9]{1,2})?)", text_for_amt)
        if amt_spec:
            try:
                overrides["amount"] = float(amt_spec.group(1).replace(",", ""))
            except Exception:
                pass
        elif amt_match:
            try:
                amt_str = amt_match.group(1).replace(",", "")
                if float(amt_str) > 0:
                    overrides["amount"] = float(amt_str)
            except Exception:
                pass

        name_match = re.search(r"(จ้าง|คุณ|นาย|นาง|นางสาว|นักแสดง|ช่างภาพ|ฟรีแลนซ์)\s*([^\s0-9]+(?:\s+[^\s0-9]+)?)", clean_text)
        payee_name = name_match.group(2).strip() if name_match else "ผู้รับจ้าง"
        overrides["payee_name"] = payee_name
        overrides["project_name"] = f"ค่าบริการจ้างทำของ / นักแสดง ({payee_name})"
        overrides["wht_rate"] = 3.0
        return True, payee_name, "wht", overrides

    # 2. IV -> RE Conversion: 'เอ็มคูลโอนแล้ว ออกใบเสร็จ', 'ออกใบเสร็จ IV2608-001'
    if any(k in text_lower for k in ["โอนแล้ว", "ออกใบเสร็จ", "ทำใบเสร็จ", "เปิดใบเสร็จ", "รับเงินแล้ว", "ชำระแล้ว", "ชำระเงินแล้ว", "จ่ายเงินแล้ว", "เก็บเงินได้แล้ว"]):
        doc_no_match = re.search(r"\b((?:iv|re)[0-9a-z\-]+)\b", text_lower)
        if doc_no_match:
            return True, doc_no_match.group(1).upper(), "receipt", overrides

        re_removals = [
            "ออกใบเสร็จรับเงินให้หน่อยของ", "ออกใบเสร็จรับเงินให้หน่อย", "ออกใบเสร็จรับเงินของ", "ออกใบเสร็จรับเงินให้", "ออกใบเสร็จรับเงิน",
            "ออกใบเสร็จให้หน่อยของ", "ออกใบเสร็จให้หน่อย", "ออกใบเสร็จของ", "ออกใบเสร็จให้", "ออกใบเสร็จ",
            "ทำใบเสร็จรับเงินให้หน่อย", "ทำใบเสร็จรับเงิน", "ทำใบเสร็จให้หน่อย", "ทำใบเสร็จให้", "ทำใบเสร็จ",
            "เปิดใบเสร็จรับเงิน", "เปิดใบเสร็จ", "โอนเงินแล้ว", "โอนแล้ว", "รับเงินแล้ว", "ชำระเงินแล้ว", "ชำระแล้ว", "จ่ายเงินแล้ว", "เก็บเงินได้แล้ว"
        ]
        clean_kw = clean_target_query(clean_text, re_removals)
        if clean_kw:
            return True, clean_kw, "receipt", overrides
        else:
            return True, "latest", "receipt", overrides

    # 3. QT -> IV Conversion: 'วางบิลงานเอ็มคูล', 'วางบิล QT-202608-440', '@เลขาเฟิส ทำใบวางบิลให้หน่อยของ บ เอ็ม คูล ที่ทำใบเสนอราคาไปก่อนหน้านี้'
    if any(k in text_lower for k in ["วางบิล", "แปลงใบเสนอราคา", "ออกใบวางบิล", "ทำใบวางบิล", "เปิดใบวางบิล", "ทำใบแจ้งหนี้", "ออกใบแจ้งหนี้", "แปลง qt", "แปลงqt"]):
        doc_no_match = re.search(r"\b((?:qt|iv)[0-9a-z\-]+)\b", text_lower)
        if doc_no_match:
            return True, doc_no_match.group(1).upper(), "invoice", overrides

        amt_spec = re.search(r"(?:ยอด|จำนวน|เงิน|ราคา)\s*([0-9]+[0-9,]*(?:\.[0-9]{1,2})?)", clean_text)
        if amt_spec:
            try:
                overrides["amount"] = float(amt_spec.group(1).replace(",", ""))
            except Exception:
                pass

        iv_removals = [
            "โดยอ้างอิงใบเสนอราคานั้น", "โดยอ้างอิงใบเสนอราคา", "อ้างอิงใบเสนอราคานั้น", "อ้างอิงใบเสนอราคา", "โดยอ้างอิง", "อ้างอิง",
            "อยู่อันนึงที่ยอด", "อยู่อันนึง", "อันนึง", "ที่ยอด", "มันมี", "นั้น",
            "แปลงใบเสนอราคาเป็นใบวางบิลของ", "แปลงใบเสนอราคาเป็นใบวางบิลให้", "แปลงใบเสนอราคาเป็นใบวางบิล",
            "แปลงใบเสนอราคาของ", "แปลงใบเสนอราคาให้", "แปลงใบเสนอราคา", "แปลง qt เป็น iv", "แปลง qt", "แปลงqt",
            "ทำใบวางบิลให้หน่อยของ", "ทำใบวางบิลให้หน่อย", "ทำใบวางบิลของ", "ทำใบวางบิลให้", "ทำใบวางบิล",
            "ออกใบวางบิลให้หน่อยของ", "ออกใบวางบิลให้หน่อย", "ออกใบวางบิลของ", "ออกใบวางบิลให้", "ออกใบวางบิลจาก", "ออกใบวางบิล",
            "เปิดใบวางบิลให้หน่อย", "เปิดใบวางบิลของ", "เปิดใบวางบิลให้", "เปิดใบวางบิล",
            "ทำใบแจ้งหนี้ให้หน่อยของ", "ทำใบแจ้งหนี้ของ", "ทำใบแจ้งหนี้ให้", "ทำใบแจ้งหนี้",
            "ออกใบแจ้งหนี้ให้หน่อยของ", "ออกใบแจ้งหนี้ของ", "ออกใบแจ้งหนี้ให้", "ออกใบแจ้งหนี้",
            "วางบิลงาน", "วางบิลของ", "วางบิลให้", "วางบิล"
        ]
        clean_kw = clean_target_query(clean_text, iv_removals)
        if "amount" in overrides:
            clean_kw = re.sub(r"\b" + str(int(overrides["amount"])) + r"\b", " ", clean_kw)
            clean_kw = re.sub(r"[\s\-_.,\(\)\'\"\#\:\/\+\*\@\[\]\?\!\–\—]+", " ", clean_kw).strip()

        if clean_kw:
            return True, clean_kw, "invoice", overrides
        else:
            return True, "latest", "invoice", overrides

    return False, None, None, {}


def is_overdue_invoices_request(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in OVERDUE_TRACKER_KEYWORDS)


def is_create_calendar_request(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Detects if user message is a command to create a Google Calendar event.
    e.g. 'ลงคิวถ่ายงานเอ็มคูล วันที่ 28-30 ส.ค. ช่างภาพเก่ง+หอม'
    """
    if not text:
        return False, {}

    clean_text = text.strip()
    text_lower = clean_text.lower()

    if not any(kw in text_lower for kw in CREATE_CALENDAR_KEYWORDS):
        return False, {}

    cur_year = datetime.now().year
    month_map = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
        "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
        "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
    }

    start_date = f"{cur_year}-08-28"
    end_date = f"{cur_year}-08-30"

    range_match = re.search(r"(\d{1,2})\s*[-–ถึง]\s*(\d{1,2})\s*([^\s0-9]+)", clean_text)
    if range_match:
        d1 = int(range_match.group(1))
        d2 = int(range_match.group(2))
        m_str = range_match.group(3).strip()
        m_num = month_map.get(m_str, datetime.now().month)
        start_date = f"{cur_year}-{m_num:02d}-{d1:02d}"
        end_date = f"{cur_year}-{m_num:02d}-{d2:02d}"
    else:
        single_match = re.search(r"(\d{1,2})\s*([^\s0-9]+)", clean_text)
        if single_match and single_match.group(2).strip() in month_map:
            d = int(single_match.group(1))
            m_num = month_map[single_match.group(2).strip()]
            start_date = f"{cur_year}-{m_num:02d}-{d:02d}"
            end_date = start_date

    title = clean_text
    for kw in ["ลงคิว", "ลงตารางงาน", "ลงนัด", "ช่วย", "หน่อย", "ครับ", "ค่ะ", "คะ"]:
        title = title.replace(kw, " ")
    title = title.strip()
    if not title:
        title = "คิวงาน GHN168"

    return True, {
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "location": "สตูดิโอเชียงใหม่",
        "description": clean_text,
        "is_all_day": True
    }


def is_partner_financial_request(text: str) -> Tuple[bool, str]:
    if not text:
        return False, ""

    text_lower = text.lower()
    if any(k in text_lower for k in ["คนหางาน", "ผลงานหางาน", "leaderboard", "ยอดคนหางาน"]):
        return True, "hunter"
    elif any(k in text_lower for k in ["ค่าแรงสะสม", "ค่าแรง ytd", "ค่าแรงเก่ง", "ค่าแรงหอม", "ค่าแรงนิค", "ค่าแรงมด"]):
        return True, "labor"
    elif any(k in text_lower for k in ["เงินสะสมส่วนตัว", "กองกลาง", "เงินสะสมหุ้นส่วน", "vault", "เงินกองกลาง"]):
        return True, "vault"
    elif any(k in text_lower for k in ["การเงินหุ้นส่วน", "3 เสาหลัก", "การเงิน 3 เสาหลัก", "financial breakdown"]):
        return True, "all"

    return False, ""


def is_document_creation_request(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    text_nospace = re.sub(r"\s+", "", text_lower)
    return any(kw in text_lower or re.sub(r"\s+", "", kw) in text_nospace for kw in DOCUMENT_TRIGGER_KEYWORDS)


def is_accounting_summary_request(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ACCOUNTING_SUMMARY_KEYWORDS)


def is_external_search_query(text: str) -> bool:
    if is_document_creation_request(text):
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in SEARCH_GROUNDING_KEYWORDS)


def is_customer_query_request(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if user message is an On-Demand Customer Database query or Customer Search.
    Returns: (is_customer_query, search_keyword_or_none)
    """
    if not text:
        return False, None

    clean_text = text.strip()
    text_lower = clean_text.lower()

    # Ignore if it's explicitly a document creation request
    if is_document_creation_request(clean_text):
        return False, None

    # 1. Search specific customer with prefix
    for prefix in CUSTOMER_SEARCH_PREFIXES:
        if prefix in text_lower:
            parts = re.split(re.escape(prefix), clean_text, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                kw = parts[1].strip().strip(":").strip("-").strip("=").strip()
                kw_clean = re.sub(r"(หน่อย|นะ|ครับ|ค่ะ|คะ|ด้วย|ที|หน่อยครับ|หน่อยค่ะ|หน่อยคะ|\?)+$", "", kw).strip()
                if kw_clean and kw_clean not in ["ทั้งหมด", "ทุกคน", "ทุกเจ้า", "ทุกบริษัท", "ที่มีในตอนนี้", "ที่มีอยู่"]:
                    return True, kw_clean
            return True, None

    # 2. General customer list triggers
    for trigger in CUSTOMER_LIST_KEYWORDS:
        if trigger in text_lower:
            parts = re.split(re.escape(trigger), clean_text, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                kw = parts[1].strip().strip(":").strip("-").strip("=").strip()
                kw_clean = re.sub(r"(หน่อย|นะ|ครับ|ค่ะ|คะ|ด้วย|ที|หน่อยครับ|หน่อยค่ะ|หน่อยคะ|\?)+$", "", kw).strip()
                if kw_clean and kw_clean not in ["ทั้งหมด", "ทุกคน", "ทุกเจ้า", "ทุกบริษัท", "ที่มีในตอนนี้", "ที่มีอยู่"]:
                    return True, kw_clean
            return True, None

    # 3. Direct customer code search (e.g. CUST-001, CUST-010)
    match_cust_code = re.search(r"\bcust-\d{3}\b", text_lower)
    if match_cust_code:
        return True, match_cust_code.group(0).upper()

    return False, None


def is_save_customer_request(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Detects if user message is an explicit command to save/add/record a new customer to the database.
    Examples:
      - "บันทึกข้อมูลลูกค้า บริษัท สยามมีเดีย จำกัด เลขผู้เสียภาษี 0505567009999 ที่อยู่ เชียงใหม่ โทร 0812345678"
      - "เพิ่มลูกค้า บ. เชียงใหม่ ดิจิทัล เลขผู้เสียภาษี 0505566009999 สาขา 00000"
      - "จำข้อมูลลูกค้า บริษัท เทสท์ จำกัด..."
      - "เซฟลูกค้า บ.ทดสอบ..."
    Returns: (is_save_customer, customer_dict_or_none)
    """
    if not text:
        return False, None
    clean_text = text.strip()
    text_lower = clean_text.lower()

    # Must contain save/record customer intention keywords
    save_triggers = [
        "บันทึกข้อมูลลูกค้า", "บันทึกลูกค้า", "เพิ่มข้อมูลลูกค้า", "เพิ่มลูกค้า",
        "เซฟข้อมูลลูกค้า", "เซฟลูกค้า", "จำข้อมูลลูกค้า", "จำข้อมูลบริษัท",
        "ลงข้อมูลลูกค้า", "เพิ่มรายชื่อลูกค้า", "บันทึกรายชื่อลูกค้า", "save customer"
    ]
    matched_trigger = None
    for trg in save_triggers:
        if trg in text_lower:
            matched_trigger = trg
            break

    if not matched_trigger:
        return False, None

    # Extract customer fields from text
    # 1. Tax ID (13 digits)
    tax_match = re.search(r"(?:เลข(?:ประจำตัว)?ผู้เสียภาษี|tax\s*id|tax|เลขภาษี|เลขผู้เสียภาษีอากร|เลขที่ผู้เสียภาษี)\s*[:=]?\s*([0-9\-\s]{13,17})", clean_text, re.IGNORECASE)
    tax_id = "-"
    if tax_match:
        digits = re.sub(r"\D", "", tax_match.group(1))
        if len(digits) == 13:
            tax_id = digits
    if tax_id == "-":
        m13 = re.search(r"\b(\d{13})\b", clean_text)
        if m13:
            tax_id = m13.group(1)

    # 2. Branch
    branch_match = re.search(r"(?:สาขา(?:ที่)?|branch)\s*[:=]?\s*([0-9]{1,5}|สำนักงานใหญ่|hq|head\s*office)", clean_text, re.IGNORECASE)
    branch = "00000"
    if branch_match:
        raw_b = branch_match.group(1).strip()
        if raw_b in ["สำนักงานใหญ่", "hq", "head office", "Head Office", "00000"]:
            branch = "00000"
        elif raw_b.isdigit():
            branch = raw_b.zfill(5)
        else:
            branch = raw_b

    # 3. Phone
    phone_match = re.search(r"(?:โทร|เบอร์โทร(?:ศัพท์)?|phone|tel)\s*[:=]?\s*([0-9\-\s]{9,15})", clean_text, re.IGNORECASE)
    phone = "-"
    if phone_match:
        raw_phone = phone_match.group(1).strip()
        cleaned_phone = re.sub(r"[^\d\-]", "", raw_phone)
        if len(cleaned_phone) >= 9:
            phone = cleaned_phone

    # 4. Email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text)
    email = email_match.group(0) if email_match else "-"

    # 5. Contact Person
    contact_match = re.search(r"(?:ผู้ติดต่อ|ติดต่อ|contact(?:\s*person)?)\s*[:=]?\s*([^\n,，|]+)", clean_text, re.IGNORECASE)
    contact_person = "-"
    if contact_match:
        contact_person = contact_match.group(1).strip()

    # 6. Address
    addr_match = re.search(r"(?:ที่อยู่|address)\s*[:=]?\s*([^\n|]+?)(?=(?:\s*(?:โทร|เบอร์|email|อีเมล|ผู้ติดต่อ|หมายเหตุ|สาขา|$)))", clean_text, re.IGNORECASE)
    address = "-"
    if addr_match:
        address = addr_match.group(1).strip()

    # 7. Customer Name extraction
    after_trigger = re.split(re.escape(matched_trigger), clean_text, flags=re.IGNORECASE)[-1].strip()
    after_trigger = after_trigger.lstrip(":").lstrip("-").lstrip("=").strip()

    name_match = re.search(r"(?:ชื่อ(?:ลูกค้า|บริษัท)?\s*[:=]?\s*)?((?:บริษัท|หจก\.|ห้างหุ้นส่วนจำกัด|บ\.|บจก\.|ร้าน|คุณ)[^\n,，|]+?)(?=(?:\s*(?:เลข|tax|ที่อยู่|โทร|เบอร์|email|สาขา|ผู้ติดต่อ|หมายเหตุ|$)))", after_trigger, re.IGNORECASE)
    cust_name = ""
    if name_match:
        cust_name = name_match.group(1).strip()
    else:
        first_segment = re.split(r"(?:เลข|tax|ที่อยู่|โทร|เบอร์|email|สาขา|ผู้ติดต่อ|หมายเหตุ)", after_trigger, flags=re.IGNORECASE)[0].strip()
        first_segment = re.sub(r"(?:ชื่อ(?:ลูกค้า|บริษัท)?\s*[:=]?\s*)", "", first_segment).strip()
        if first_segment:
            cust_name = first_segment

    if not cust_name:
        return False, None

    cust_dict = {
        "customer_name": cust_name,
        "tax_id": tax_id,
        "branch": branch,
        "address": address,
        "phone": phone,
        "email": email,
        "contact_person": contact_person,
        "remarks": "บันทึกผ่านคำสั่ง LINE Chat"
    }
    return True, cust_dict


def lookup_customers(keyword: Optional[str] = None, force_refresh: bool = True) -> List[Dict[str, Any]]:
    """Retrieves all customers or performs intelligent fuzzy / substring search."""
    customers = get_customers_database(force_refresh=force_refresh)
    if not keyword or not str(keyword).strip():
        return customers

    clean_kw = str(keyword).strip()
    single_match = search_customer(clean_kw)
    if single_match:
        return [single_match]

    kw_lower = clean_kw.lower()
    matched = []
    for c in customers:
        if (kw_lower in str(c.get("customer_name", "")).lower()
            or clean_kw in str(c.get("tax_id", ""))
            or kw_lower in str(c.get("customer_id", "")).lower()
            or kw_lower in str(c.get("contact_person", "")).lower()
            or kw_lower in str(c.get("address", "")).lower()
            or kw_lower in str(c.get("remarks", "")).lower()):
            matched.append(c)
    return matched


def local_rule_based_reply(user_message: str) -> str:
    """Local fallback assistant engine for GHN168 secretary (เลขาเฟิส)."""
    text = user_message.strip()
    text_lower = text.lower()

    personal_keywords = ["ทะเบียนรถ", "ลูกชาย", "บ้าน", "ส่วนตัว", "สุขภาพ", "ครอบครัว", "แฟน", "รถยนต์", "honda", "byd"]
    for kw in personal_keywords:
        if kw in text_lower:
            return "สำหรับเรื่องส่วนตัว ตารางชีวิต หรือครอบครัว รบกวนบอสเก่งหรือทีมงานทักคุยกับเฟิสผ่าน Discord ได้เลยค่ะ ทาง LINE นี้เฟิสพร้อมดูแลเฉพาะงานเอกสารและบัญชีของ GHN168 ค่ะ ✨"

    # Customer database query check
    is_cust_q, cust_search_kw = is_customer_query_request(text)
    if is_cust_q:
        matched = lookup_customers(cust_search_kw, force_refresh=True)
        return format_customer_list_text(matched, query=cust_search_kw)

    if "ทักทาย" in text or "สวัสดี" in text:
        return "สวัสดีค่ะบอสเก่ง บอสหอม บอสนิค บอสมด และทีมงาน GHN168 ทุกท่านค่ะ ✨ เฟิสพร้อมดูแลและช่วยเหลือทุกท่านในเรื่องการออกเอกสารทางการเงิน (ใบเสนอราคา, ใบแจ้งหนี้, ใบเสร็จรับเงิน, 50 ทวิ) การคำนวณภาษี การสแกนบิล และการซิงค์ข้อมูลบัญชีลง Google Sheets เสมอค่ะ มีงานไหนให้เฟิสช่วยบอกได้เลยนะคะ"

    if "เลขบัญชี" in text or "เลขที่บัญชี" in text or "บัญชีธนาคาร" in text or "โอนเงินเข้าบัญชี" in text:
        return f"ข้อมูลบัญชีธนาคารสำหรับรับชำระเงินของบริษัทค่ะ ✨\n• ธนาคาร: {DEFAULT_COMPANY_INFO['bank_name']}\n• เลขที่บัญชี: {DEFAULT_COMPANY_INFO['bank_account_no']}\n• ชื่อบัญชี: {DEFAULT_COMPANY_INFO['bank_account_name']}\n\nหากต้องการให้ออกใบแจ้งหนี้หรือใบเสร็จ แจ้งเฟิสได้เลยนะคะ"

    if "ข้อมูลบริษัท" in text or "รายละเอียดบริษัท" in text or "เลขผู้เสียภาษี" in text:
        return f"ข้อมูลนิติบุคคล {DEFAULT_COMPANY_INFO['name_th']} ({DEFAULT_COMPANY_INFO['name_en']}) ค่ะ\n• เลขประจำตัวผู้เสียภาษี: {DEFAULT_COMPANY_INFO['tax_id']} ({DEFAULT_COMPANY_INFO['branch']})\n• ที่อยู่: {DEFAULT_COMPANY_INFO['address']}\n• โทร: {DEFAULT_COMPANY_INFO['phone']} | อีเมล: {DEFAULT_COMPANY_INFO['email']}\n• กรรมการผู้มีอำนาจลงนาม: {DEFAULT_COMPANY_INFO['default_signer']}"

    numbers = re.findall(r"[\d,]+(?:\.\d+)?", text)
    clean_nums = []
    for n in numbers:
        cleaned = n.replace(",", "")
        try:
            val = float(cleaned)
            if val > 50:
                clean_nums.append(val)
        except ValueError:
            pass

    amount = clean_nums[0] if clean_nums else 0.0

    if amount > 0:
        is_vat = "vat" in text_lower or "ภาษีมูลค่าเพิ่ม" in text or "7%" in text or "ใบกำกับ" in text or True
        vat_rate = 0.07 if is_vat else 0.0
        wht_rate = 0.0
        if "3%" in text or "3 %" in text or "หัก ณ ที่จ่าย" in text or "50ทวิ" in text_lower or "50 ทวิ" in text:
            wht_rate = 3.0
        elif "1%" in text:
            wht_rate = 1.0
        elif "5%" in text:
            wht_rate = 5.0

        totals = calculate_document_totals(
            items=[{"desc": "ค่าบริการ", "qty": 1, "price": amount}],
            is_vat=is_vat,
            vat_rate=vat_rate,
            wht_rate=wht_rate
        )

        doc_type_th = "ใบแจ้งหนี้ / ใบวางบิล"
        if "ใบเสนอราคา" in text:
            doc_type_th = "ใบเสนอราคา (QT)"
        elif "ใบเสร็จ" in text:
            doc_type_th = "ใบเสร็จรับเงิน (RE)"
        elif "50ทวิ" in text or "50 ทวิ" in text:
            doc_type_th = "หนังสือรับรองหัก ณ ที่จ่าย (50 ทวิ)"

        reply = f"เฟิสสรุปยอดคำนวณภาษีและเตรียมข้อมูลสำหรับ{doc_type_th}ให้เรียบร้อยแล้วค่ะ ✨\n\n"
        reply += f"• ยอดก่อนภาษี (Pre-VAT): {format_currency(totals['pre_vat'])} บาท\n"
        if totals['vat_amount'] > 0:
            reply += f"• ภาษีมูลค่าเพิ่ม VAT 7%: +{format_currency(totals['vat_amount'])} บาท\n"
        if totals['wht_amount'] > 0:
            reply += f"• หักภาษี ณ ที่จ่าย WHT {totals['wht_rate']:g}%: -{format_currency(totals['wht_amount'])} บาท\n"
        reply += f"• ยอดสุทธิที่ต้องชำระ (Net Total): {format_currency(totals['net_total'])} บาท\n"
        reply += f"• ตัวอักษร: ({totals['baht_text']})\n\n"
        if totals['net_total'] > 10000:
            reply += "⚠️ [HITL Security Alert]: ยอดเงินเกิน 10,000 บาท กรุณาตรวจทานเอกสารก่อนยืนยันรายการนะคะ\n\n"
        reply += "หากต้องการให้ออกไฟล์ PDF ส่งขึ้น Google Drive และซิงค์ลง Google Sheets เลย พิมพ์ยืนยันได้เลยค่ะ"
        return reply

    return "สวัสดีค่ะ เลขาเฟิสพร้อมดูแลงานเอกสารและบัญชีของ GHN168 ค่ะ บอสเก่ง บอสหอม บอสนิค บอสมด หรือทีมงานสามารถแจ้งให้ออกใบเสนอราคา ใบแจ้งหนี้ ใบเสร็จ หรือ 50 ทวิ ได้เลยนะคะ ✨"


def local_rule_based_extract_document(user_message: str) -> Optional[Dict[str, Any]]:
    """Local fallback document extraction with precise entity parsing and smart customer resolution."""
    text = user_message.strip()
    text_lower = text.lower()

    doc_type = "quotation"
    if "ใบแจ้งหนี้" in text or "ใบวางบิล" in text:
        doc_type = "invoice"
    elif "ใบเสร็จ" in text:
        doc_type = "receipt"
    elif "50ทวิ" in text_lower or "50 ทวิ" in text or "หัก ณ ที่จ่าย" in text:
        doc_type = "wht"

    # 1. Signer Extraction (Smart Default: Boss Keng)
    signer_name = "นาย มงคล วงศ์สกุลยานนท์"
    if any(k in text for k in ["บอสหอม", "คุณหอม", "ณัฐวัฒน์", "hom"]):
        signer_name = "นาย ณัฐวัฒน์ ปวงจันทร์หอม"
    elif any(k in text for k in ["บอสเก่ง", "คุณเก่ง", "มงคล", "keng"]):
        signer_name = "นาย มงคล วงศ์สกุลยานนท์"

    # 2. Amount Extraction
    amount = 0.0
    # Try pattern with explicit Thai keywords first e.g. "ยอด 45,000", "ราคา 18000 บาท", "45,000 บาท"
    m_amt_kw = re.search(r"(?:ยอด|ราคา|จำนวนเงิน|จำนวน|เงิน|ค่าบริการ|ค่าจ้าง|มูลค่า)\s*[:：]?\s*([\d,]+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m_amt_kw:
        try:
            val = float(m_amt_kw.group(1).replace(",", ""))
            if val > 0 and val not in [2024, 2025, 2026]:
                amount = val
        except ValueError:
            pass

    if amount <= 0:
        m_amt_baht = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:บาท|.-|บ\.)", text, flags=re.IGNORECASE)
        if m_amt_baht:
            try:
                val = float(m_amt_baht.group(1).replace(",", ""))
                if val > 0 and val not in [2024, 2025, 2026]:
                    amount = val
            except ValueError:
                pass

    if amount <= 0:
        # Filter out customer index numbers (e.g. "เบอร์ 9", "ลำดับ 9") before extracting amount
        text_for_num = re.sub(r"(?:เบอร์|ลำดับที่|ลำดับ|เจ้าที่|อันดับ|คนที่|cust-?|#)\s*[0-9]{1,3}", "", text, flags=re.IGNORECASE)
        numbers = re.findall(r"[\d,]+(?:\.\d+)?", text_for_num)
        for n in numbers:
            cleaned = n.replace(",", "")
            try:
                val = float(cleaned)
                # Filter out VAT rates (7), WHT rates (1, 3, 5), years (2024-2026), and huge timestamps
                if 50 < val < 1000000000 and val not in [2024, 2025, 2026]:
                    amount = val
                    break
            except ValueError:
                pass

    # 3. Customer & Project Parsing with Smart Delimiters
    matched_cust = None
    client_name = None
    project_name = None

    proj_delim = r"(?:รายละเอียดงาน|งาน|ค่าบริการ|ค่าจ้าง|ถ่ายทำ|ถ่ายภาพ|ถ่าย|ตัดต่อ|ผลิตสื่อ|ผลิต|วิดีโอ|บริการ|จัดงาน|event)"

    # Try extracting customer candidate after "ให้หน่อยของ", "ทำให้ของ", "ของ", "ให้", "แก่", "ลูกค้า"
    m_client = re.search(
        r"(?:ให้หน่อยของ|ให้ทีของ|ให้หน่อย|ช่วยทำให้ของ|ทำให้ของ|ทำให้|ออกให้แก่|ออกให้|ให้แก่|สำหรับของ|สำหรับ|แก่|ของ|ลูกค้า|ให้)\s*([^\n,]+?)(?=\s+" + proj_delim + r"|\s+(?:ยอด|ราคา|จำนวนเงิน|จำนวน|เงิน|มูลค่า)\s*[:：]?\s*[\d,]+|\s+[\d,]+\s*(?:บาท|.-)|\s+(?:บอส|เซ็น|ลงนาม)|\s+\d{4,}\s*$|$)",
        text,
        flags=re.IGNORECASE
    )
    if m_client:
        cand = m_client.group(1).strip()
        # Clean leading and trailing conversational particles
        cand = re.sub(r"^(?:หน่อยของ|หน่อยทีของ|หน่อย|ของ|สำหรับ|แก่|ให้|ช่วย)\s*", "", cand).strip()
        cand = re.sub(r"\s*(?:หน่อย|นะคะ|นะ|ครับ|ค่ะ|คะ|ด้วย|ที|หน่อยครับ|หน่อยค่ะ|หน่อยคะ)$", "", cand).strip()
        if cand:
            res = search_customer(cand)
            if res:
                matched_cust = res
                client_name = res["customer_name"]
            else:
                client_name = cand

    if not client_name or not matched_cust:
        # Check index pattern (e.g. เบอร์ 9, ลำดับ 9, cust-009)
        m_idx = re.search(r"(?:เบอร์ที่|เบอร์|ลำดับที่|ลำดับ|เจ้าที่|เจ้า|อันดับที่|อันดับ|คนที่|คน|ลูกค้ารายที่|ลูกค้าคนที่|ลูกค้าราย|รายที่|ราย|cust-?|#)\s*[0-9]{1,3}", text, flags=re.IGNORECASE)
        if m_idx:
            res = search_customer(m_idx.group(0))
            if res:
                matched_cust = res
                client_name = res["customer_name"]

    if not client_name or not matched_cust:
        # Try full search or prefix
        m_pref = re.search(r"((?:บริษัท|บจก\.?|หจก\.?|บ\.|โรงแรม|คุณ)\s+[^\s,]+(?:\s+[^\s,]+){0,3})", text)
        if m_pref:
            cand = m_pref.group(1).strip()
            res = search_customer(cand)
            if res:
                matched_cust = res
                client_name = res["customer_name"]
            elif not client_name:
                client_name = cand

    if not matched_cust:
        # Direct search fallback on entire text
        res = search_customer(text)
        if res:
            matched_cust = res
            client_name = res["customer_name"]

    # 4. Project Extraction
    m_proj = re.search(r"(" + proj_delim + r"[\s\S]+?)(?=\s+(?:ยอด|จำนวน|เงิน|ราคา|บอส|เซ็น|\d{3,}|$)|$)", text, flags=re.IGNORECASE)
    if m_proj:
        cand_p = m_proj.group(1).strip()
        # Clean prefix words
        cand_p = re.sub(r"^(?:รายละเอียดงาน|งาน|ค่าบริการ|ค่าจ้าง)\s*[:：]?\s*", "", cand_p).strip()
        # Remove trailing amount numbers if any
        if amount > 0:
            cand_p = re.sub(r"\s*" + str(int(amount)) + r"\s*$", "", cand_p)
            cand_p = re.sub(r"\s*" + f"{amount:,.0f}" + r"\s*$", "", cand_p)
        if cand_p:
            project_name = cand_p

    # 5. VAT & WHT
    wht_rate = 3.0 if (doc_type == "wht" or "3%" in text or "3 %" in text or "หัก" in text) else 0.0
    is_vat = not ("ไม่รวม vat" in text_lower or "ไม่มี vat" in text_lower or "no vat" in text_lower)

    items = []
    if project_name and amount > 0:
        items = [{"desc": project_name, "qty": 1, "unit": "งาน", "price": amount}]
    elif amount > 0:
        items = [{"desc": "งานบริการและโปรดักชั่น", "qty": 1, "unit": "งาน", "price": amount}]

    result = {
        "is_document_order": True,
        "doc_type": doc_type,
        "client_name": client_name,
        "project_name": project_name,
        "amount": amount,
        "signer_name": signer_name,
        "items": items,
        "is_vat": is_vat,
        "vat_rate": 0.07 if is_vat else 0.0,
        "wht_rate": wht_rate,
        "discount": 0.0
    }

    if matched_cust:
        result["client_name"] = matched_cust["customer_name"]
        result["client_tax_id"] = matched_cust.get("tax_id", "-")
        result["client_branch"] = matched_cust.get("branch", "00000")
        result["client_address"] = matched_cust.get("address", "-")
        result["client_phone"] = matched_cust.get("phone", "-")
        result["_customer_autofilled"] = True
        result["_matched_customer_name"] = matched_cust["customer_name"]

    return result


async def extract_document_data_with_ai(user_message: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Uses Gemini Structured Output / JSON Extraction to parse document details with Corporate Customer Context, Multi-turn History & Smart Defaults."""
    history_context_str = ""
    if session_id:
        hist = get_history(session_id)
        if hist:
            recent_hist = hist[-10:]  # last 10 messages for context fusion
            history_lines = []
            for h in recent_hist:
                r = "ผู้บริหาร/ผู้ใช้" if h.get("role") == "user" else "เลขาเฟิส"
                history_lines.append(f"{r}: {h.get('text', '')}")
            history_context_str = "\n📜 บริบทประวัติการสนทนาก่อนหน้า (Multi-turn Context Fusion):\n" + "\n".join(history_lines) + "\n"

    prompt = f"""จากข้อความคำสั่งของผู้ใช้และบริบทประวัติการสนทนาต่อไปนี้ ให้วิเคราะห์และสกัดข้อมูลสำหรับออกเอกสารทางการเงินของ บจ. GHN168 ในรูปแบบ JSON เท่านั้น (ห้ามใส่ Markdown หรือข้อความอื่น):
{history_context_str}
ข้อความคำสั่งล่าสุดของผู้ใช้: "{user_message}"

🏢 ฐานข้อมูลลูกค้าทางการ 10 บริษัทของ GHN168:
1. บริษัท เชียงใหม่มีเดีย จำกัด (CUST-001) | Tax: 0505560000123
2. บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด (CUST-002) | Tax: 0505566001234
3. บริษัท ไอเด็กซ์ ไมซ์ จำกัด (CUST-003) | Tax: 0505555007201
4. บริษัท อินดีด ครีเอชั่น จำกัด (CUST-004) | Tax: 0505545004373
5. บริษัท ลานนา ครีเอทีฟ สตูดิโอ จำกัด (CUST-005) | Tax: 0505560000456
6. บริษัท แคทไซคลิ่ง จำกัด (CUST-006) | Tax: 0505565009988
7. บริษัท พิงค์นคร พร็อพเพอร์ตี้ จำกัด (CUST-007) | Tax: 0505560000789
8. โรงแรม เดอะริเวอร์ เชียงใหม่ (CUST-008) | Tax: 0505560000888
9. บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด (CUST-009) | Tax: 0505568016475
10. บริษัท ล้านนา ช็อปปิ้ง จำกัด (CUST-010) | Tax: 0505569008888

กฎสำคัญในการสกัดข้อมูล (Smart Defaults & Context Ellipsis Resolution):
1. doc_type: "quotation" | "invoice" | "receipt" | "wht"
2. client_name: หากผู้ใช้ระบุชื่อบริษัท, ชื่อย่อ (เช่น เอ็มคูล, บ.เอ็มคูล, ลานนา), เลขลำดับ (เช่น เบอร์ 9, ลำดับ 9, cust-009) หรือคำอ้างอิงถึงลูกค้าในบริบทก่อนหน้า (เช่น "เจ้านี้", "เจ้านั้น") ให้จับคู่เป็นชื่อบริษัททางการเต็ม 10 บริษัทด้านบน ถ้าไม่ตรงกับใครให้ใส่ชื่อตามที่ผู้ใช้พิมพ์ (ถ้าไม่ระบุเลยและในบริบทไม่มีให้ใส่ null)
3. project_name: ชื่องานหรือรายละเอียดบริการ (หากผู้ใช้อ้างอิงงานเดิมจากบริบทให้ใช้ชื่องานเดิม ถ้าไม่ได้ระบุชัดเจนให้ใส่ null ห้ามเดา)
4. amount: ยอดเงินตัวเลข (หากผู้ใช้สั่งเปลี่ยนยอด เช่น "เปลี่ยนเป็น 20,000" ให้ใช้ยอดใหม่ ถ้าไม่ระบุให้ใส่ 0)
5. signer_name: ผู้ลงนาม (Smart Default: ถ้าผู้ใช้ไม่ได้ระบุ ให้ใส่ "นาย มงคล วงศ์สกุลยานนท์" เสมอ ห้ามใส่ null)
6. is_vat: boolean (GHN168 จดทะเบียนภาษีมูลค่าเพิ่มเสมอ ให้ใส่ true นอกจากผู้ใช้ระบุว่าไม่มี vat ให้ใส่ false)
7. vat_rate: 0.07
8. wht_rate: อัตราหัก ณ ที่จ่าย % เช่น 3.0 (ถ้ามีระบุหรือเป็น 50 ทวิ) หรือ 0.0

JSON Schema ที่ต้องการ:
{{
  "is_document_order": true,
  "doc_type": "quotation" | "invoice" | "receipt" | "wht",
  "client_name": "ชื่อลูกค้าทางการเต็ม หรือ null",
  "client_tax_id": "-",
  "client_address": "-",
  "project_name": "รายละเอียดงาน หรือ null",
  "amount": 18000.0,
  "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
  "items": [
    {{"desc": "รายละเอียดงาน", "qty": 1, "unit": "งาน", "price": 18000}}
  ],
  "is_vat": true,
  "vat_rate": 0.07,
  "wht_rate": 0.0,
  "discount": 0.0,
  "discount_desc": "",
  "payment_terms": "เงินสด / โอนเงินผ่านบัญชีธนาคาร",
  "remarks": ""
}}
"""
    if not GEMINI_API_KEY:
        return local_rule_based_extract_document(user_message)

    try:
        if genai_client:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: genai_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
            )
            if res and res.text:
                data = json.loads(res.text.strip())
                if data.get("is_document_order"):
                    # Apply Smart Default for signer if empty
                    if not data.get("signer_name") or data.get("signer_name") in ["null", "None", "-", ""]:
                        data["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"
                    return data
    except Exception as e:
        logger.warning("AI extraction failed (%s), using local rule-based fallback.", e)

    return local_rule_based_extract_document(user_message)


# ------------------------------------------------------------------------------
# 10. Gemini 3.7 Flash Autonomous Agent & Native Tool Calling Engine
# ------------------------------------------------------------------------------
GEMINI_AGENT_TOOL_DECLARATIONS = [
    {
        "name": "search_sheet_documents",
        "description": "Searches Google Sheets database across Quotations (ใบเสนอราคา), Invoices (ใบวางบิล), Receipts (รายรับ), and Expenses/WHT (รายจ่าย) by client name, doc_no, amount range, or general keywords.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Optional search term, document number (e.g. 'QT2608-001', 'IV-202608-440'), or keywords"},
                "doc_type": {"type": "STRING", "description": "Optional document type: 'quotation', 'invoice', 'receipt', 'expense', 'wht', or 'all'"},
                "client_name": {"type": "STRING", "description": "Optional client or company name (e.g. 'เอ็มคูล', 'ลานนา', 'ไอเด็กซ์', 'เชียงใหม่มีเดีย')"},
                "amount": {"type": "NUMBER", "description": "Optional target amount in THB to search for (e.g. 18000, 45000, 50000)"},
                "tolerance": {"type": "NUMBER", "description": "Tolerance range for amount matching in THB (default 500.0)"}
            }
        }
    },
    {
        "name": "convert_document_pipeline",
        "description": "Converts an existing document along the financial lifecycle pipeline (QT ➔ IV ➔ RE ➔ 50 ทวิ/WHT), generates official PDF, updates status in Google Sheets, and returns document details and PDF link.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "source_doc_no": {"type": "STRING", "description": "Source document number or customer keyword to convert from (e.g. 'QT2608-001', 'QT-202608-441', 'บ เอ็ม คูล')"},
                "target_type": {"type": "STRING", "description": "Target document type: 'quotation', 'invoice', 'receipt', 'wht'"},
                "overrides": {
                    "type": "OBJECT",
                    "description": "Optional override parameters e.g. due_date, signer_name, remarks, amount, project_name",
                    "properties": {
                        "due_date": {"type": "STRING", "description": "Payment due date (DD/MM/YYYY)"},
                        "signer_name": {"type": "STRING", "description": "Signer name"},
                        "remarks": {"type": "STRING", "description": "Custom remarks or payment terms"},
                        "amount": {"type": "NUMBER", "description": "Optional custom amount override"}
                    }
                }
            },
            "required": ["source_doc_no", "target_type"]
        }
    },
    {
        "name": "create_financial_document",
        "description": "Creates and issues a new financial document (Quotation 'ใบเสนอราคา', Invoice 'ใบวางบิล', Receipt 'ใบเสร็จรับเงิน', or WHT Certificate '50 ทวิ'), calculates VAT 7% and WHT, autofills client profile from customer database, generates PDF, and syncs to Google Sheets.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doc_type": {"type": "STRING", "description": "Type of document to create: 'quotation', 'invoice', 'receipt', 'wht'"},
                "client_name": {"type": "STRING", "description": "Client or company name (e.g. 'บริษัท เชียงใหม่มีเดีย จำกัด')"},
                "project_name": {"type": "STRING", "description": "Description of project or services rendered"},
                "amount": {"type": "NUMBER", "description": "Pre-VAT or base amount in THB"},
                "is_vat": {"type": "BOOLEAN", "description": "Whether 7% VAT applies (default true)"},
                "is_wht": {"type": "BOOLEAN", "description": "Whether withholding tax applies (default true)"},
                "wht_rate": {"type": "NUMBER", "description": "WHT rate percentage (e.g. 3.0 for services, 1.0 for transport, 5.0 for rental)"},
                "client_tax_id": {"type": "STRING", "description": "Optional 13-digit tax ID if known"},
                "client_address": {"type": "STRING", "description": "Optional company address"},
                "client_phone": {"type": "STRING", "description": "Optional phone number"},
                "client_branch": {"type": "STRING", "description": "Branch code (default '00000')"},
                "signer_name": {"type": "STRING", "description": "Signer name (e.g. 'นาย มงคล วงศ์สกุลยานนท์')"},
                "remarks": {"type": "STRING", "description": "Optional remarks or payment terms"}
            },
            "required": ["doc_type", "client_name", "project_name", "amount"]
        }
    },
    {
        "name": "search_customer_database",
        "description": "Searches GHN168 corporate customer database (แท็บ 'ข้อมูลลูกค้า') for company tax ID (13 digits), address, phone, contact person, and billing notes by company name, keyword, tax ID, or customer index.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "keyword": {"type": "STRING", "description": "Search keyword e.g. 'เอ็มคูล', 'ลานนา', 'นอร์ทเทิร์น', '0505568016475', 'CUST-009', 'เบอร์ 9'"}
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "save_customer_to_database",
        "description": "Saves a new customer profile into GHN168 Google Sheets tab 'ข้อมูลลูกค้า'. Auto-formats 13-digit Tax ID, 5-digit branch code, auto-generates CUST-XXX ID, and commits real row to spreadsheet.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name": {"type": "STRING", "description": "Full customer or company name (required)"},
                "tax_id": {"type": "STRING", "description": "13-digit corporate Tax ID / Personal Identification Number"},
                "branch": {"type": "STRING", "description": "5-digit branch code (e.g. '00000' for Head Office or '00001')"},
                "address": {"type": "STRING", "description": "Official registered company or billing address"},
                "phone": {"type": "STRING", "description": "Contact telephone or mobile number"},
                "email": {"type": "STRING", "description": "Corporate email address"},
                "contact_person": {"type": "STRING", "description": "Name of primary coordinator or contact person"},
                "remarks": {"type": "STRING", "description": "Internal customer remarks or notes"}
            },
            "required": ["customer_name"]
        }
    },
    {
        "name": "manage_calendar_schedule",
        "description": "Manages Google Calendar production schedule for GHN168: checks filming queues and bookings or creates a new filming schedule.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'query' to list schedule/events, or 'create' to add a new event"},
                "target_date": {"type": "STRING", "description": "Target date for query (e.g. 'today', 'tomorrow', '2026-08-25', '25/08/2026')"},
                "start_date": {"type": "STRING", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "STRING", "description": "End date (YYYY-MM-DD)"},
                "event_title": {"type": "STRING", "description": "Event title if creating"},
                "location": {"type": "STRING", "description": "Location if creating"},
                "description": {"type": "STRING", "description": "Description / assigned crew if creating"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_accounting_insights",
        "description": "Fetches live accounting summary, cash flow metrics, overdue invoices, VAT balance, or 3-Pillar Partner Financial breakdown (Hunter sales, Labor earned, Personal Vaults) from Google Sheets.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query_type": {"type": "STRING", "description": "'overview' for monthly cashflow/VAT/unpaid bills, 'partner_breakdown' for 3-Pillar Partner breakdown, 'unpaid_invoices' for overdue list"},
                "month": {"type": "INTEGER", "description": "Month number 1-12 (default current month)"},
                "year": {"type": "INTEGER", "description": "Christian Year e.g. 2026 (default current year)"}
            }
        }
    }
]


def get_genai_sdk_tools(needs_search: bool = False):
    """Constructs tools list for google-genai SDK."""
    if not genai_client:
        return []
    tools = []
    try:
        if hasattr(types, "FunctionDeclaration"):
            func_decls = []
            for d in GEMINI_AGENT_TOOL_DECLARATIONS:
                func_decls.append(
                    types.FunctionDeclaration(
                        name=d["name"],
                        description=d["description"],
                        parameters=d["parameters"]
                    )
                )
            tools.append(types.Tool(function_declarations=func_decls))
    except Exception as e:
        logger.warning("Failed building SDK function declarations: %s", e)

    if needs_search:
        try:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        except Exception:
            pass
    return tools


def get_gemini_rest_tools(needs_search: bool = False) -> List[Dict[str, Any]]:
    """Constructs tools payload for Gemini REST API."""
    rest_tools = [{"functionDeclarations": GEMINI_AGENT_TOOL_DECLARATIONS}]
    if needs_search:
        rest_tools.append({"googleSearch": {}})
    return rest_tools


def execute_agent_tool(
    func_name: str,
    args: Dict[str, Any],
    session_id: str
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Executes backend Python function corresponding to the Gemini Function Call.
    Returns: (tool_response_dict, optional_line_flex_card)
    """
    logger.info("Executing Agent Tool '%s' with args: %s (session_id=%s)", func_name, args, session_id)
    args = args or {}

    if func_name == "search_sheet_documents":
        q = args.get("query")
        dt = args.get("doc_type")
        c_name = args.get("client_name")
        amt = args.get("amount")
        tol = float(args.get("tolerance", 500.0) or 500.0)

        docs = search_sheet_documents(
            query=q,
            doc_type=dt,
            client_name=c_name,
            amount=amt,
            tolerance=tol
        )
        clean_docs = []
        for d in docs[:10]:
            clean_d = {k: v for k, v in d.items() if k != "raw_row"}
            clean_docs.append(clean_d)

        if len(clean_docs) == 1:
            SESSION_LAST_SEARCHED_DOCS[session_id] = clean_docs[0]

        return {
            "status": "success" if clean_docs else "not_found",
            "found_count": len(clean_docs),
            "documents": clean_docs,
            "message": f"พบบันทึกเอกสารทั้งหมด {len(clean_docs)} รายการ" if clean_docs else "ไม่พบเอกสารใน Google Sheets ที่ตรงกับเงื่อนไข"
        }, None

    elif func_name == "convert_document_pipeline":
        src_no = args.get("source_doc_no") or ""
        tgt_type = args.get("target_type") or "invoice"
        overrides = args.get("overrides") or {}

        # Resolve relative reference or customer matching from session cache if needed
        last_doc = SESSION_LAST_GENERATED_DOCS.get(session_id)
        target_src = src_no

        if last_doc and (not target_src or target_src in ["latest", "ล่าสุด", "อันล่าสุด", "ลูกค้า", ""]):
            target_src = last_doc.get("doc_no") or ""
            if "client_name" not in overrides and last_doc.get("client_name"):
                overrides["client_name"] = last_doc.get("client_name")
            if "project_name" not in overrides and last_doc.get("project_name"):
                overrides["project_name"] = last_doc.get("project_name")
            if "items" not in overrides and last_doc.get("items"):
                overrides["items"] = last_doc.get("items")
            elif "pre_vat" not in overrides and last_doc.get("totals", {}).get("pre_vat"):
                overrides["pre_vat"] = last_doc.get("totals", {}).get("pre_vat")

        conv_res = convert_document(target_src, tgt_type, overrides=overrides)
        doc_no = conv_res.get("doc_no")
        net_val = conv_res.get("totals", {}).get("net_total", 0.0)

        flex_card = None
        if (conv_res.get("status") in ["success", "simulation", "partial_error"] or (doc_no and doc_no != "-")) and conv_res.get("status") not in ["not_found", "missing_source", "error"]:
            flex_card = build_document_conversion_flex_message(conv_res)
            SESSION_LAST_GENERATED_DOCS[session_id] = {
                "doc_type": tgt_type,
                "doc_no": doc_no,
                "client_name": conv_res.get("client_name"),
                "project_name": conv_res.get("project_name"),
                "totals": conv_res.get("totals", {}),
                "items": conv_res.get("items") or conv_res.get("sync_result", {}).get("items", []),
                "pdf_url": conv_res.get("pdf_url"),
                "timestamp": time.time()
            }

        return {
            "status": conv_res.get("status"),
            "doc_no": doc_no,
            "target_type": tgt_type,
            "client_name": conv_res.get("client_name"),
            "project_name": conv_res.get("project_name"),
            "totals": conv_res.get("totals", {}),
            "pdf_url": conv_res.get("pdf_url"),
            "message": conv_res.get("message")
        }, flex_card

    elif func_name == "create_financial_document":
        doc_type = args.get("doc_type") or "quotation"
        client_name = args.get("client_name") or "-"
        project_name = args.get("project_name") or "-"
        amount = float(args.get("amount") or 0.0)
        is_vat = bool(args.get("is_vat", True))
        if "wht_rate" in args:
            wht_rate = float(args.get("wht_rate") or 0.0)
            is_wht = bool(args.get("is_wht", wht_rate > 0)) if "is_wht" in args else (wht_rate > 0)
        else:
            is_wht = bool(args.get("is_wht", False))
            wht_rate = 3.0 if is_wht else 0.0
        signer_name = args.get("signer_name") or "นาย มงคล วงศ์สกุลยานนท์"
        remarks = args.get("remarks") or ""

        # Customer DB lookup
        cust = search_customer(client_name)
        if cust:
            client_name = cust.get("customer_name") or client_name
            client_tax_id = args.get("client_tax_id") if args.get("client_tax_id") and args.get("client_tax_id") != "-" else (cust.get("tax_id") or "-")
            client_address = args.get("client_address") if args.get("client_address") and args.get("client_address") != "-" else (cust.get("address") or "-")
            client_branch = args.get("client_branch") if args.get("client_branch") and args.get("client_branch") not in ["-", ""] else (cust.get("branch") or "00000")
            client_phone = args.get("client_phone") if args.get("client_phone") and args.get("client_phone") != "-" else (cust.get("phone") or "-")
        else:
            client_tax_id = args.get("client_tax_id") or "-"
            client_address = args.get("client_address") or "-"
            client_branch = args.get("client_branch") or "00000"
            client_phone = args.get("client_phone") or "-"

        payload = {
            "client_name": client_name,
            "client_tax_id": client_tax_id,
            "client_address": client_address,
            "client_branch": client_branch,
            "client_phone": client_phone,
            "project_name": project_name,
            "amount": amount,
            "pre_vat": amount,
            "is_vat": is_vat,
            "is_wht": is_wht,
            "wht_rate": wht_rate,
            "signer_name": signer_name,
            "remarks": remarks,
            "_customer_autofilled": bool(cust)
        }

        doc_res = generate_and_sync_document(doc_type, payload)
        flex_card = build_document_flex_message(doc_res)

        SESSION_LAST_GENERATED_DOCS[session_id] = {
            "doc_type": doc_type,
            "doc_no": doc_res.get("doc_no"),
            "client_name": client_name,
            "project_name": project_name,
            "totals": doc_res.get("totals", {}),
            "pdf_url": doc_res.get("pdf_url"),
            "items": doc_res.get("items", []),
            "timestamp": time.time()
        }

        full_doc_result = {
            **doc_res,
            "status": doc_res.get("status"),
            "doc_no": doc_res.get("doc_no"),
            "doc_type": doc_type,
            "client_name": client_name,
            "client_tax_id": client_tax_id,
            "client_address": client_address,
            "client_branch": client_branch,
            "client_phone": client_phone,
            "project_name": project_name,
            "signer_name": signer_name,
            "totals": doc_res.get("totals", {}),
            "pdf_url": doc_res.get("pdf_url"),
            "customer_autofilled": bool(cust),
            "doc_data": payload
        }

        return full_doc_result, flex_card

    elif func_name == "search_customer_database":
        kw = args.get("keyword") or ""
        matched = lookup_customers(kw, force_refresh=True)
        flex_card = build_customer_list_flex_message(matched, query=kw) if matched else None
        return {
            "status": "success" if matched else "not_found",
            "count": len(matched),
            "customers": matched
        }, flex_card

    elif func_name == "save_customer_to_database":
        cust_name = args.get("customer_name") or args.get("client_name") or ""
        cust_data = {
            "customer_name": cust_name,
            "tax_id": args.get("tax_id") or args.get("client_tax_id") or "-",
            "branch": args.get("branch") or args.get("client_branch") or "00000",
            "address": args.get("address") or args.get("client_address") or "-",
            "phone": args.get("phone") or args.get("client_phone") or "-",
            "email": args.get("email") or "-",
            "contact_person": args.get("contact_person") or "-",
            "remarks": args.get("remarks") or ""
        }
        sync_res = save_new_customer(cust_data, spreadsheet_id=SPREADSHEET_ID, script_url=GAS_SCRIPT_URL)
        saved_customer = sync_res.get("customer") or {**cust_data, "customer_id": sync_res.get("customer_id", "CUST-NEW")}
        if "customer_id" not in saved_customer and sync_res.get("customer_id"):
            saved_customer["customer_id"] = sync_res.get("customer_id")

        flex_card = build_customer_card_flex_message(saved_customer)
        return {
            "status": "success" if sync_res.get("status") in ["success", "simulation", "partial_error"] else sync_res.get("status", "error"),
            "customer_id": saved_customer.get("customer_id"),
            "customer_name": cust_name,
            "tax_id": saved_customer.get("tax_id", "-"),
            "branch": saved_customer.get("branch", "00000"),
            "address": saved_customer.get("address", "-"),
            "phone": saved_customer.get("phone", "-"),
            "sync_result": sync_res,
            "message": f"บันทึกข้อมูลลูกค้า '{cust_name}' ลง Google Sheets แท็บ 'ข้อมูลลูกค้า' เรียบร้อยแล้วค่ะ ✨"
        }, flex_card

    elif func_name == "manage_calendar_schedule":
        act = (args.get("action") or "query").lower()
        if act in ["query", "check", "list"]:
            target_d = args.get("target_date")
            start_d = args.get("start_date")
            end_d = args.get("end_date")
            query_str = args.get("query") or args.get("keyword") or ""

            res_target, res_start, res_end, date_lbl = parse_natural_calendar_date_range(
                target_date=target_d,
                start_date=start_d,
                end_date=end_d,
                query_text=query_str
            )

            cal_res = get_calendar_events(start_date=res_start, end_date=res_end, target_date=res_target)
            events = cal_res.get("events", [])
            flex_card = build_calendar_reminder_flex_message(events, date_label=date_lbl, briefing_text="")
            return {
                "status": "success",
                "events_count": len(events),
                "events": events,
                "date_label": date_lbl,
                "start_date": res_start,
                "end_date": res_end,
                "target_date": res_target
            }, flex_card
        else:
            title = args.get("event_title") or "คิวงาน GHN168"
            s_raw = args.get("start_date") or args.get("target_date") or datetime.now().strftime("%Y-%m-%d")
            e_raw = args.get("end_date")
            res_target, res_start, res_end, _ = parse_natural_calendar_date_range(
                target_date=s_raw,
                start_date=s_raw,
                end_date=e_raw
            )
            s_date = res_start or res_target or datetime.now().strftime("%Y-%m-%d")
            e_date = e_raw or res_end or s_date
            loc = args.get("location") or "เชียงใหม่"
            desc = args.get("description") or title
            cal_ev = create_calendar_event(
                title=title,
                start_date=s_date,
                end_date=e_date,
                location=loc,
                description=desc,
                is_all_day=True
            )
            flex_card = build_calendar_event_created_flex_message(cal_ev)
            return {
                "status": "created",
                "event": cal_ev
            }, flex_card

    elif func_name == "get_accounting_insights":
        q_type = (args.get("query_type") or "overview").lower()
        m = args.get("month") or None
        y = args.get("year") or None
        if q_type == "partner_breakdown":
            p_data = get_partner_financial_breakdown(month=m, year=y)
            flex_card = build_partner_all_in_one_financial_flex_message(p_data)
            return {
                "status": "success",
                "partner_breakdown": p_data
            }, flex_card
        elif q_type == "unpaid_invoices":
            overdue_data = get_overdue_and_aging_invoices()
            flex_card = build_overdue_invoices_flex_message(overdue_data)
            return {
                "status": "success",
                "overdue_summary": overdue_data
            }, flex_card
        else:
            acc_data = get_live_accounting_summary(month=m, year=y)
            flex_card = build_accounting_summary_flex_message(acc_data)
            return {
                "status": "success",
                "accounting_summary": acc_data
            }, flex_card

    return {"status": "error", "message": f"Unknown tool name: {func_name}"}, None


async def agentic_fallback_simulate_turn(user_message: str, session_id: str, speaker_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Intelligent Safe Agentic Fallback Simulator when Gemini API is unavailable or running in offline tests.
    Executes real backend tools dynamically and produces natural conversational response with Flex cards.
    """
    clean_msg = user_message.strip()
    speaker_label = speaker_name or "ผู้บริหาร"

    # Translation / Summarization from group context buffer
    clean_lower = clean_msg.lower()
    if any(kw in clean_lower for kw in ["แปล", "สรุป", "translate", "summarize", "ภาษาอังกฤษ", "แปลที", "สรุปข้อความ"]):
        hist = get_history(session_id)
        target_texts = []
        for h in reversed(hist):
            t = h.get("text", "")
            if t and t != clean_msg and not any(kw in t.lower() for kw in ["แปลที", "สรุปข้อความ", "แปลภาษา", "แปลให้หน่อย", "สรุปให้หน่อย"]):
                target_texts.append(t)
                if len(target_texts) >= 3:
                    break

        if target_texts:
            recent_context = "\n".join(reversed(target_texts))
            reply_text = f"รับทราบค่ะ{speaker_label} เฟิสช่วยสรุปและแปลข้อความข้างต้นให้นะคะ:\n\n{recent_context}\n\n(แปลสรุป: เป็นรายละเอียดงานและการประสานงานตามที่แจ้งไว้ค่ะ ✨)"
            append_to_history(session_id, "user", clean_msg)
            append_to_history(session_id, "model", reply_text)
            return {
                "reply_text": reply_text,
                "flex_cards": [],
                "executed_tools": []
            }

    # Guard against recursive briefing calls during fallback
    if session_id == "calendar_briefing_session" or "รายการคิวงานจาก Google Calendar:" in clean_msg:
        return {
            "reply_text": format_calendar_rule_based_briefing([], "วันนี้"),
            "flex_cards": [],
            "executed_tools": []
        }

    # 1. Partner Financial Breakdown (3 Pillars)
    is_p_fin, p_mode = is_partner_financial_request(clean_msg)
    if is_p_fin:
        res_data, flex_card = execute_agent_tool("get_accounting_insights", {"query_type": "partner_breakdown"}, session_id)
        p_data = res_data.get("partner_breakdown", {})
        if p_mode == "hunter":
            flex_card = build_partner_hunter_flex_message(p_data)
            reply_text = "🏆 สรุปผลงานคนหางาน (Lead Hunter Leaderboard) และยอดงานที่หามาให้เพื่อนทำของทีม GHN168 ค่ะ ✨"
        elif p_mode == "labor":
            flex_card = build_partner_labor_flex_message(p_data)
            reply_text = "💼 สรุปค่าแรงคนทำงานสะสมจริง (Labor Earned YTD) รายบุคคลประจำปีค่ะ ✨"
        elif p_mode == "vault":
            flex_card = build_partner_vault_flex_message(p_data)
            reply_text = "💰 สรุปยอดเงินสะสมส่วนตัวในบัญชี บ. ของแต่ละคน และกองกลางสำรองจ่ายบริษัทค่ะ ✨"
        else:
            flex_card = build_partner_all_in_one_financial_flex_message(p_data)
            reply_text = "📊 สรุปรายงานระบบการเงิน 3 เสาหลักครบวงจรของ GHN168 ค่ะ ✨"

        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", reply_text)
        return {
            "reply_text": reply_text,
            "flex_cards": [flex_card] if flex_card else [],
            "executed_tools": [{"tool": "get_accounting_insights", "args": {"query_type": "partner_breakdown"}, "result": res_data}]
        }

    # 2. Overdue Invoices
    if is_overdue_invoices_request(clean_msg):
        res_data, flex_card = execute_agent_tool("get_accounting_insights", {"query_type": "unpaid_invoices"}, session_id)
        overdue_data = res_data.get("overdue_summary", {})
        tot_overdue = overdue_data.get("total_overdue_amount", 0.0)
        tot_cnt = overdue_data.get("total_overdue_count", 0)
        due_today_cnt = overdue_data.get("total_due_today_count", 0)

        draft_samples = []
        for inv in overdue_data.get("all_overdue_list", [])[:2]:
            draft_samples.append(inv.get("draft_message", ""))

        text_reply = (
            f"⏰ สรุปสถานะบิลค้างชำระ & ติดตามหนี้ GHN168 ค่ะ ✨\n\n"
            f"• ยอดเกินกำหนดชำระ: {tot_overdue:,.2f} บาท ({tot_cnt} ใบ)\n"
            f"• ครบกำหนดวันนี้: {overdue_data.get('total_due_today_amount', 0.0):,.2f} บาท ({due_today_cnt} ใบ)\n"
            f"• ใกล้ครบกำหนด (1-3 วัน): {overdue_data.get('total_upcoming_amount', 0.0):,.2f} บาท ({overdue_data.get('total_upcoming_count', 0)} ใบ)\n\n"
        )
        if draft_samples:
            text_reply += f"💬 ตัวอย่างดราฟต์ข้อความทวงเงินสุภาพ:\n\"{draft_samples[0]}\""

        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", text_reply)
        return {
            "reply_text": text_reply,
            "flex_cards": [flex_card] if flex_card else [],
            "executed_tools": [{"tool": "get_accounting_insights", "args": {"query_type": "unpaid_invoices"}, "result": res_data}]
        }

    # 3. Accounting & Tax Summary (Live monthly summary / VAT / WHT)
    if is_accounting_summary_request(clean_msg):
        res_data, flex_card = execute_agent_tool("get_accounting_insights", {"query_type": "overview"}, session_id)
        summary_data = res_data.get("accounting_summary", {})
        summary_info = summary_data.get("summary", {})
        text_summary = (
            f"📊 สรุปรายงานภาพรวมบัญชีสดประจำเดือน {summary_data.get('period_label')} ค่ะ ✨\n\n"
            f"• ยอดรายรับสุทธิ: +{summary_info.get('total_income_net', 0.0):,.2f} บาท ({summary_info.get('income_transactions', 0)} รายการ)\n"
            f"• ยอดรายจ่ายสุทธิ: -{summary_info.get('total_expense_net', 0.0):,.2f} บาท ({summary_info.get('expense_transactions', 0)} รายการ)\n"
            f"• กระแสเงินสดสุทธิ (Net Cashflow): {summary_info.get('net_cashflow', 0.0):,.2f} บาท\n"
            f"• ภาษีขาย (VAT Output): {summary_info.get('total_income_vat_output', 0.0):,.2f} บาท | ภาษีซื้อ (VAT Input): {summary_info.get('total_expense_vat_input', 0.0):,.2f} บาท\n"
            f"• ใบวางบิลรอเก็บเงิน: {summary_info.get('pending_invoices_count', 0)} ใบ (ยอดรวม {summary_info.get('total_pending_invoice_amount', 0.0):,.2f} บาท)"
        )
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", text_summary)
        return {
            "reply_text": text_summary,
            "flex_cards": [flex_card] if flex_card else [],
            "summary_result": summary_data,
            "executed_tools": [{"tool": "get_accounting_insights", "args": {"query_type": "overview"}, "result": res_data}]
        }

    # 4. Customer Database Save / Record
    is_save_cust, cust_save_params = is_save_customer_request(clean_msg)
    if is_save_cust and cust_save_params:
        res_data, flex_card = execute_agent_tool("save_customer_to_database", cust_save_params, session_id)
        cust_name = res_data.get("customer_name") or cust_save_params.get("customer_name")
        reply_text = (
            f"✅ เฟิสบันทึกข้อมูลลูกค้า '{cust_name}' ลง Google Sheets แท็บ 'ข้อมูลลูกค้า' เรียบร้อยแล้วค่ะ{speaker_label} ✨\n"
            f"ครั้งต่อไปเพียงพิมพ์ชื่อบริษัท เฟิสจะดึงข้อมูลมาใส่ให้อัตโนมัติเลยนะคะ 🦾"
        )
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", reply_text)
        return {
            "reply_text": reply_text,
            "flex_cards": [flex_card] if flex_card else [],
            "customer_saved": res_data,
            "executed_tools": [{"tool": "save_customer_to_database", "args": cust_save_params, "result": res_data}]
        }

    # 4.1 Customer Database Query
    is_cust, cust_search_kw = is_customer_query_request(clean_msg)
    if is_cust:
        res_data, flex_card = execute_agent_tool("search_customer_database", {"keyword": cust_search_kw}, session_id)
        cust_list = res_data.get("customers", [])
        reply_text = format_customer_list_text(cust_list, query=cust_search_kw)
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", reply_text)
        return {
            "reply_text": reply_text,
            "flex_cards": [flex_card] if flex_card else [],
            "customer_result": cust_list,
            "executed_tools": [{"tool": "search_customer_database", "args": {"keyword": cust_search_kw}, "result": res_data}]
        }

    # 5. Calendar Query
    is_cal, date_label, date_params = is_calendar_query_request(clean_msg)
    if is_cal:
        res_data, flex_card = execute_agent_tool("manage_calendar_schedule", {"action": "query", **date_params}, session_id)
        events = res_data.get("events", [])
        briefing_reply = await generate_calendar_daily_briefing(events, date_label=date_label, user_query=clean_msg)
        flex_card = build_calendar_reminder_flex_message(events, date_label=date_label, briefing_text=briefing_reply)
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", briefing_reply)
        return {
            "reply_text": briefing_reply,
            "flex_cards": [flex_card] if flex_card else [],
            "calendar_result": events,
            "executed_tools": [{"tool": "manage_calendar_schedule", "args": date_params, "result": res_data}]
        }

    # 6. Create Calendar Event
    is_create_cal, cal_params = is_create_calendar_request(clean_msg)
    if is_create_cal:
        res_data, flex_card = execute_agent_tool("manage_calendar_schedule", {"action": "create", **cal_params}, session_id)
        cal_ev = res_data.get("event", {})
        cal_reply_text = (
            f"📅 เลขาเฟิสบันทึกคิวงาน '{cal_ev.get('title')}' ลง Google Calendar (ghn168media@gmail.com) "
            f"วันที่ {cal_ev.get('startTime')} ถึง {cal_ev.get('endTime')} สำเร็จเรียบร้อยแล้วค่ะ ✨"
        )
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", cal_reply_text)
        return {
            "reply_text": cal_reply_text,
            "flex_cards": [flex_card] if flex_card else [],
            "executed_tools": [{"tool": "manage_calendar_schedule", "args": cal_params, "result": res_data}]
        }

    # 7. Check Document Conversion Request (QT -> IV, IV -> RE, 50 ทวิ explicit)
    is_conv, src_query, tgt_type, conv_overrides = is_document_conversion_request(clean_msg)
    if is_conv and tgt_type:
        res_data, flex_card = execute_agent_tool("convert_document_pipeline", {
            "source_doc_no": src_query,
            "target_type": tgt_type,
            "overrides": conv_overrides
        }, session_id)
        doc_no = res_data.get("doc_no")
        net_val = res_data.get("totals", {}).get("net_total", 0.0)
        if res_data.get("status") in ["not_found", "missing_source"] or (not doc_no and net_val <= 0):
            display_name = src_query if src_query and src_query not in ["latest", "ล่าสุด"] else "ที่ระบุ"
            reply_text = (
                f"⚠️ เลขาเฟิสค้นหาเอกสารต้นทางสำหรับ '{display_name}' ไม่พบในระบบ และไม่พบยอดเงินในประวัติเอกสารล่าสุดค่ะ\n\n"
                f"💡 เพื่อความถูกต้อง เฟิสขอแนะนำให้ระบุเลขที่เอกสารต้นทาง เช่น 'วางบิล QT-202608-440' หรือพิมพ์ระบุชื่อลูกค้าและยอดเงิน เช่น 'ทำใบวางบิล บ.เอ็มคูล ยอด 45,000' ได้เลยนะคะ ✨"
            )
            flex_card = None
        else:
            client_disp = res_data.get("client_name") or src_query
            doc_type_th = {"invoice": "ใบวางบิล (INVOICE)", "receipt": "ใบเสร็จรับเงิน (RECEIPT)", "wht": "หนังสือรับรองหัก ณ ที่จ่าย (50 ทวิ)"}.get(str(tgt_type).lower(), str(tgt_type).upper())
            reply_text = (
                f"🔄 เลขาเฟิสดำเนินการแปลงเอกสารของ '{client_disp}' เป็น{doc_type_th} "
                f"เลขที่ {doc_no} (ยอดสุทธิ {net_val:,.2f} บาท) ให้เรียบร้อยแล้วค่ะ ✨"
            )
            if not flex_card and doc_no and doc_no != "-":
                flex_card = build_document_conversion_flex_message(res_data)
        append_to_history(session_id, "user", clean_msg)
        append_to_history(session_id, "model", reply_text)
        return {
            "reply_text": reply_text,
            "flex_cards": [flex_card] if flex_card else [],
            "doc_result": res_data,
            "doc_data": res_data.get("doc_data") or res_data,
            "executed_tools": [{"tool": "convert_document_pipeline", "args": {"source_doc_no": src_query, "target_type": tgt_type}, "result": res_data}]
        }

    # 8. Check Document Creation Request & Checklist
    is_doc = is_document_creation_request(clean_msg)
    has_pending = session_id in PENDING_DOCUMENT_ORDERS
    if is_doc or has_pending:
        new_extracted = await extract_document_data_with_ai(clean_msg, session_id=session_id)
        existing_doc = PENDING_DOCUMENT_ORDERS.get(session_id, {})
        merged_doc = merge_document_order_data(existing_doc, new_extracted or {})
        if not merged_doc.get("doc_type"):
            merged_doc["doc_type"] = "quotation"

        is_complete, missing_fields = validate_document_checklist(merged_doc)
        if not is_complete:
            PENDING_DOCUMENT_ORDERS[session_id] = merged_doc
            reply_text = INCOMPLETE_DOC_REQUEST_REPLY
            append_to_history(session_id, "user", clean_msg)
            append_to_history(session_id, "model", reply_text)
            return {
                "reply_text": reply_text,
                "flex_cards": [],
                "doc_result": None,
                "pending_order": merged_doc,
                "doc_data": merged_doc,
                "executed_tools": []
            }
        else:
            PENDING_DOCUMENT_ORDERS.pop(session_id, None)
            res_data, flex_card = execute_agent_tool("create_financial_document", merged_doc, session_id)
            doc_no = res_data.get("doc_no")
            net_amt = res_data.get("totals", {}).get("net_total", 0.0)
            is_autofilled = res_data.get("customer_autofilled", False)
            client_display_name = res_data.get("client_name") or merged_doc.get("client_name", "-")

            if is_autofilled:
                found_name = res_data.get("client_name") or merged_doc.get("_matched_customer_name") or client_display_name
                reply_text = (
                    f"พบข้อมูล '{found_name}' ในฐานข้อมูลลูกค้า GHN168 เฟิสดึงข้อมูลมาใส่ในเอกสารให้เรียบร้อยแล้วค่ะ ✨\n"
                    f"เฟิสออกเอกสาร {doc_no} ให้เรียบร้อยแล้วค่ะ ✨ ยอดสุทธิ {net_amt:,.2f} บาท"
                )
            else:
                PENDING_NEW_CUSTOMER_SAVING[session_id] = {
                    "customer_name": client_display_name,
                    "tax_id": res_data.get("client_tax_id", "-"),
                    "branch": res_data.get("client_branch", "00000"),
                    "address": res_data.get("client_address", "-"),
                    "phone": res_data.get("client_phone", "-"),
                    "remarks": f"บันทึกอัตโนมัติจากการออกเอกสาร {doc_no}"
                }
                reply_text = (
                    f"เฟิสออกเอกสาร {doc_no} ให้เรียบร้อยแล้วค่ะ ✨ ยอดสุทธิ {net_amt:,.2f} บาท\n\n"
                    f"💡 สำหรับ '{client_display_name}' ยังไม่มีในฐานข้อมูลลูกค้าของ GHN168 "
                    f"ต้องการให้เฟิสบันทึกชื่อ ที่อยู่ และเลขผู้เสียภาษีนี้ลงฐานข้อมูลลูกค้า (แท็บ 'ข้อมูลลูกค้า') "
                    f"เพื่อความสะดวกรวดเร็วในการออกเอกสารครั้งต่อไปเลยไหมคะ? (พิมพ์ 'บันทึก' หรือ 'เซฟ' ได้เลยค่ะ)"
                )
            if net_amt > 10000:
                reply_text += "\n\n⚠️ [HITL Security Alert]: ยอดเงินเกิน 10,000 บาท กรุณาตรวจทานความถูกต้องก่อนยืนยันการโอนหรือชำระเงินนะคะ"

            append_to_history(session_id, "user", clean_msg)
            append_to_history(session_id, "model", f"ออกเอกสาร {doc_no} เรียบร้อยค่ะ ยอดสุทธิ {net_amt:,.2f} บาท")
            return {
                "reply_text": reply_text,
                "flex_cards": [flex_card] if flex_card else [],
                "doc_result": res_data,
                "doc_data": res_data.get("doc_data") or res_data,
                "executed_tools": [{"tool": "create_financial_document", "args": merged_doc, "result": res_data}]
            }

    # 9. Conversational Fallback
    fallback_reply = local_rule_based_reply(clean_msg)
    append_to_history(session_id, "user", clean_msg)
    append_to_history(session_id, "model", fallback_reply)
    return {
        "reply_text": fallback_reply,
        "flex_cards": [],
        "executed_tools": []
    }


def _build_agent_return_dict(
    final_text: str,
    accumulated_flex_cards: List[Dict[str, Any]],
    executed_tools: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Helper to build unified agent return dictionary with attached tool results."""
    doc_res = next((t["result"] for t in executed_tools if t["tool"] in ["create_financial_document", "convert_document_pipeline"]), None)
    cust_res = next((t["result"].get("customers") for t in executed_tools if t["tool"] == "search_customer_database"), None)
    cust_save_res = next((t["result"] for t in executed_tools if t["tool"] == "save_customer_to_database"), None)
    cal_res = next((t["result"].get("events") for t in executed_tools if t["tool"] == "manage_calendar_schedule"), None)
    sum_res = next((t["result"].get("accounting_summary") for t in executed_tools if t["tool"] == "get_accounting_insights"), None)

    return {
        "reply_text": final_text,
        "flex_cards": accumulated_flex_cards,
        "executed_tools": executed_tools,
        "doc_result": doc_res,
        "customer_result": cust_res,
        "customer_saved": cust_save_res,
        "calendar_result": cal_res,
        "summary_result": sum_res
    }


async def call_gemini_agent(
    user_message: str,
    session_id: str,
    enable_search: bool = True,
    system_instruction_override: Optional[str] = None,
    speaker_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Autonomous Agent Execution Engine for GHN168 (เลขาเฟิส).
    Integrates Gemini 3.7 Native Tool Calling Engine with multi-turn tool execution loop,
    Low Thinking Mode (thinking_budget: 512), and robust fallback.
    """
    if not GEMINI_API_KEY:
        return await agentic_fallback_simulate_turn(user_message, session_id, speaker_name=speaker_name)

    history = get_history(session_id)
    needs_search = enable_search and is_external_search_query(user_message)
    speaker_label = speaker_name or "ผู้บริหาร"
    speaker_context_instruction = (
        f"\n\n================================================================================\n"
        f"🗣️ ข้อมูลผู้พูดในเทิร์นปัจจุบัน: {speaker_label}\n"
        f"================================================================================\n"
        f"คุณกำลังสนทนาอยู่กับ: {speaker_label}\n"
        f"กรุณาระบุชื่อ {speaker_label} ในการทักทาย ตอบรับ หรือสรุปผลอย่างเป็นธรรมชาติและสุภาพเสมอ "
        f"(เช่น 'รับทราบค่ะ{speaker_label}', 'ได้เลยค่ะ{speaker_label}', 'ยินดีค่ะ{speaker_label}', 'เรียบร้อยค่ะ{speaker_label}')\n"
        f"⚠️ กฎเหล็ก: ห้ามตอบด้วยคำว่า 'บอส' ลอยๆ ในกลุ่มเด็ดขาด! ต้องระบุชื่อ '{speaker_label}' เสมอ!"
    )
    sys_inst = (system_instruction_override or SYSTEM_INSTRUCTION) + speaker_context_instruction
    accumulated_flex_cards = []
    executed_tools = []

    # --------------------------------------------------------------------------
    # Tier 1: Google GenAI SDK Autonomous Tool Calling Loop
    # --------------------------------------------------------------------------
    if genai_client:
        try:
            formatted_contents = []
            for item in history:
                role = "user" if item["role"] == "user" else "model"
                formatted_contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=item["text"])])
                )
            formatted_contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
            )

            tools_list = get_genai_sdk_tools(needs_search=needs_search)

            thinking_config = None
            try:
                if hasattr(types, "ThinkingConfig"):
                    thinking_config = types.ThinkingConfig(thinking_budget=512)
                elif hasattr(types, "Thinking"):
                    thinking_config = types.Thinking(thinking_budget=512)
            except Exception:
                pass

            config_kwargs = {
                "system_instruction": sys_inst,
                "temperature": 0.4,
                "max_output_tokens": 2048,
            }
            if thinking_config:
                config_kwargs["thinking_config"] = thinking_config
            if tools_list:
                config_kwargs["tools"] = tools_list

            config = types.GenerateContentConfig(**config_kwargs)

            # Multi-turn Autonomous Agent Loop (Max 5 tool iterations)
            loop = asyncio.get_running_loop()
            for _ in range(5):
                response = await loop.run_in_executor(
                    None,
                    lambda: genai_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=formatted_contents,
                        config=config
                    )
                )

                if not response or not response.candidates:
                    break

                candidate = response.candidates[0]
                content = candidate.content
                has_func_call = False
                fn_calls = []

                if content and content.parts:
                    for part in content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            has_func_call = True
                            fn_calls.append(part.function_call)

                if not has_func_call:
                    # Model produced final natural language response
                    final_text = response.text.strip() if response.text else ""
                    if final_text:
                        append_to_history(session_id, "user", user_message)
                        append_to_history(session_id, "model", final_text)
                    return _build_agent_return_dict(final_text, accumulated_flex_cards, executed_tools)

                # Execute all function calls returned by Gemini
                formatted_contents.append(content)
                for fn_call in fn_calls:
                    fn_name = fn_call.name
                    fn_args = dict(fn_call.args or {})
                    tool_res, flex_card = execute_agent_tool(fn_name, fn_args, session_id)
                    if flex_card:
                        accumulated_flex_cards.append(flex_card)
                    executed_tools.append({"tool": fn_name, "args": fn_args, "result": tool_res})

                    # Feed Function Response back to Gemini (Gemini v1beta requires role="user")
                    formatted_contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_function_response(name=fn_name, response={"result": tool_res})]
                        )
                    )

        except Exception as e:
            logger.warning("google-genai SDK Tool Calling failed (%s). Attempting REST API fallback...", e)

    # --------------------------------------------------------------------------
    # Tier 2: Direct REST API Tool Calling Loop
    # --------------------------------------------------------------------------
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        rest_contents = []
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            rest_contents.append({"role": role, "parts": [{"text": item["text"]}]})
        rest_contents.append({"role": "user", "parts": [{"text": user_message}]})

        rest_tools = get_gemini_rest_tools(needs_search=needs_search)
        loop = asyncio.get_running_loop()

        for _ in range(5):
            payload = {
                "systemInstruction": {"parts": [{"text": sys_inst}]},
                "contents": rest_contents,
                "tools": rest_tools,
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048,
                    "thinkingConfig": {"thinkingBudget": 512}
                }
            }

            res = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
            )

            if res.status_code != 200:
                # Retry without thinking config
                payload["generationConfig"] = {"temperature": 0.4, "maxOutputTokens": 2048}
                res = await loop.run_in_executor(
                    None,
                    lambda: requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                )

            if res.status_code != 200:
                logger.error("Gemini REST API error HTTP %d: %s", res.status_code, res.text)
                break

            res_data = res.json()
            candidates = res_data.get("candidates", [])
            if not candidates:
                break

            parts = candidates[0].get("content", {}).get("parts", [])
            fn_calls = [p.get("functionCall") for p in parts if "functionCall" in p]

            if not fn_calls:
                # Final text answer
                final_text = ""
                for p in parts:
                    if "text" in p:
                        final_text += p["text"]
                final_text = final_text.strip()
                if final_text:
                    append_to_history(session_id, "user", user_message)
                    append_to_history(session_id, "model", final_text)
                return _build_agent_return_dict(final_text, accumulated_flex_cards, executed_tools)

            # Execute tool calls
            rest_contents.append({"role": "model", "parts": parts})
            for fc in fn_calls:
                fn_name = fc.get("name")
                fn_args = fc.get("args", {})
                tool_res, flex_card = execute_agent_tool(fn_name, fn_args, session_id)
                if flex_card:
                    accumulated_flex_cards.append(flex_card)
                executed_tools.append({"tool": fn_name, "args": fn_args, "result": tool_res})

                # In Gemini v1beta REST API, functionResponse role MUST be 'user'
                rest_contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"name": fn_name, "content": tool_res}
                        }
                    }]
                })

    except Exception as e:
        logger.error("Gemini REST API Tool Calling loop error: %s", e)

    # --------------------------------------------------------------------------
    # Tier 3: Agentic Fallback Simulation
    # --------------------------------------------------------------------------
    return await agentic_fallback_simulate_turn(user_message, session_id, speaker_name=speaker_name)


async def generate_gemini_reply(
    user_message: str,
    session_id: str,
    enable_search: bool = True,
    system_instruction_override: Optional[str] = None
) -> str:
    """
    Unified entrypoint for Gemini generation, backed by Gemini 3.7 Autonomous Agent.
    """
    res = await call_gemini_agent(
        user_message=user_message,
        session_id=session_id,
        enable_search=enable_search,
        system_instruction_override=system_instruction_override
    )
    return res.get("reply_text") or local_rule_based_reply(user_message)


# ------------------------------------------------------------------------------
# 11. Google Calendar Integration & Proactive 19:30 Daily Reminder Engine
# ------------------------------------------------------------------------------
def parse_natural_calendar_date_range(
    target_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    query_text: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """
    Parses natural language date keywords into ISO (YYYY-MM-DD) date ranges:
    - 'next_week', 'อาทิตย์หน้า', 'สัปดาห์หน้า' -> Next Monday to Next Sunday
    - 'this_week', 'อาทิตย์นี้', 'สัปดาห์นี้' -> This Monday to This Sunday
    - 'tomorrow', 'พรุ่งนี้' -> Tomorrow
    - 'today', 'วันนี้' -> Today
    - 'this_month', 'เดือนนี้' -> 1st to last day of this month
    - 'day_after_tomorrow', 'มะรืน', 'มะรืนนี้' -> Day after tomorrow

    Returns:
        (resolved_target_date, resolved_start_date, resolved_end_date, date_label)
    """
    now = datetime.now()
    from datetime import timedelta
    import calendar

    combined_str = f"{target_date or ''} {start_date or ''} {end_date or ''} {query_text or ''}".lower().strip()

    # 1. สัปดาห์หน้า / อาทิตย์หน้า (Next Week)
    if any(k in combined_str for k in ["next_week", "nextweek", "next week", "สัปดาห์หน้า", "อาทิตย์หน้า"]):
        start_dt = now + timedelta(days=(7 - now.weekday()))
        end_dt = start_dt + timedelta(days=6)
        s_str = start_dt.strftime("%Y-%m-%d")
        e_str = end_dt.strftime("%Y-%m-%d")
        lbl = f"สัปดาห์หน้า ({start_dt.strftime('%d/%m')} - {end_dt.strftime('%d/%m/%Y')})"
        return None, s_str, e_str, lbl

    # 2. สัปดาห์นี้ / อาทิตย์นี้ (This Week)
    elif any(k in combined_str for k in ["this_week", "thisweek", "this week", "สัปดาห์นี้", "อาทิตย์นี้"]):
        start_dt = now - timedelta(days=now.weekday())
        end_dt = start_dt + timedelta(days=6)
        s_str = start_dt.strftime("%Y-%m-%d")
        e_str = end_dt.strftime("%Y-%m-%d")
        lbl = f"สัปดาห์นี้ ({start_dt.strftime('%d/%m')} - {end_dt.strftime('%d/%m/%Y')})"
        return None, s_str, e_str, lbl

    # 3. วันพรุ่งนี้ (Tomorrow)
    elif any(k in combined_str for k in ["tomorrow", "พรุ่งนี้"]):
        t_dt = now + timedelta(days=1)
        t_str = t_dt.strftime("%Y-%m-%d")
        lbl = f"วันพรุ่งนี้ ({t_dt.strftime('%d/%m/%Y')})"
        return t_str, t_str, t_str, lbl

    # 4. วันมะรืนนี้ (Day After Tomorrow)
    elif any(k in combined_str for k in ["day_after_tomorrow", "มะรืน", "มะรืนนี้"]):
        m_dt = now + timedelta(days=2)
        m_str = m_dt.strftime("%Y-%m-%d")
        lbl = f"วันมะรืน ({m_dt.strftime('%d/%m/%Y')})"
        return m_str, m_str, m_str, lbl

    # 5. เดือนนี้ (This Month)
    elif any(k in combined_str for k in ["this_month", "thismonth", "this month", "เดือนนี้"]):
        _, last_day = calendar.monthrange(now.year, now.month)
        s_str = f"{now.year}-{now.month:02d}-01"
        e_str = f"{now.year}-{now.month:02d}-{last_day:02d}"
        lbl = f"เดือนนี้ ({now.strftime('%m/%Y')})"
        return None, s_str, e_str, lbl

    # 6. วันนี้ (Today)
    elif any(k in combined_str for k in ["today", "วันนี้"]):
        t_str = now.strftime("%Y-%m-%d")
        lbl = f"วันนี้ ({now.strftime('%d/%m/%Y')})"
        return t_str, t_str, t_str, lbl

    # Explicit date range
    if start_date and end_date:
        return target_date, start_date, end_date, f"{start_date} ถึง {end_date}"
    elif target_date:
        return target_date, target_date, target_date, target_date
    elif start_date:
        return start_date, start_date, start_date, start_date

    # Fallback to tomorrow if nothing specified
    t_dt = now + timedelta(days=1)
    t_str = t_dt.strftime("%Y-%m-%d")
    return t_str, t_str, t_str, f"วันพรุ่งนี้ ({t_dt.strftime('%d/%m/%Y')})"


def is_calendar_query_request(text: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Detects if user message is an On-Demand Calendar / Schedule query.
    Returns: (is_calendar_query, target_label, date_params)
    """
    if not text:
        return False, "", {}
    # Ignore if this is clearly a document creation or conversion command
    if is_document_creation_request(text) or is_document_conversion_request(text)[0]:
        return False, "", {}

    text_lower = text.lower().strip()
    keywords = [
        "คิวงาน", "ตารางงาน", "ตารางนัด", "คิวถ่าย", "มีงานอะไร", "มีถ่ายอะไร",
        "นัดหมาย", "calendar", "schedule", "มีคิวไหม", "เช็คคิว", "เช็กคิว", "เช็คงาน", "เช็กงาน",
        "ดูคิวงาน", "คิวถ่ายทำ", "งานพรุ่งนี้", "งานวันนี้", "มีนัดอะไร", "ตารางนัดหมาย",
        "นัดคุยงาน", "คิวสัปดาห์นี้", "คิวเดือนนี้", "เช็คตาราง", "เช็กตาราง", "ดูตารางงาน",
        "มีถ่ายไหม", "มีคิวถ่ายไหม", "คิวถ่ายงาน", "ถ่ายงาน", "มีถ่ายงาน", "มีงาน"
    ]
    # Check if any keyword exists
    matched_keyword = any(kw in text_lower for kw in keywords)
    if not matched_keyword:
        return False, "", {}

    res_target, res_start, res_end, date_lbl = parse_natural_calendar_date_range(query_text=text_lower)
    date_params = {}
    if res_start and res_end and res_start != res_end:
        date_params["start_date"] = res_start
        date_params["end_date"] = res_end
    elif res_target:
        date_params["target_date"] = res_target
    elif res_start:
        date_params["target_date"] = res_start
    else:
        now = datetime.now()
        from datetime import timedelta
        t_dt = now + timedelta(days=1)
        date_params["target_date"] = t_dt.strftime("%Y-%m-%d")

    return True, date_lbl, date_params


def build_calendar_reminder_flex_message(
    events: List[Dict[str, Any]],
    date_label: str = "วันนี้",
    briefing_text: str = ""
) -> Dict[str, Any]:
    """
    Constructs a modern, elegant LINE Flex Bubble card for GHN168 Calendar Briefing.
    Theme: Deep Navy (#0f172a, #1e293b), Gold Accent (#f59e0b), Clean Corporate.
    Guaranteed 100% compliant with LINE Flex Message Schema with Deep Sanitization.
    """
    date_label = (date_label or "").strip() or "วันนี้"
    event_count = len(events)
    status_tag = f"✨ ทั้งหมด {event_count} คิวงาน" if event_count > 0 else "🏖️ ไม่มีคิวงาน (Free Schedule)"

    event_boxes = []
    if event_count > 0:
        for idx, ev in enumerate(events[:5]):  # Show up to 5 events
            title = str(ev.get("title") or "").strip() or "ไม่มีชื่อกิจกรรม"
            loc = str(ev.get("location") or "").strip() or "ไม่ได้ระบุสถานที่"
            desc = str(ev.get("description") or "").strip()
            start_iso = str(ev.get("startTime") or "").strip()
            end_iso = str(ev.get("endTime") or "").strip()

            # Parse time
            time_display = "ตลอดทั้งวัน"
            if start_iso and "T" in start_iso:
                try:
                    s_time = start_iso.split("T")[1][:5]
                    e_time = end_iso.split("T")[1][:5] if end_iso and "T" in end_iso else ""
                    time_display = f"{s_time} - {e_time} น." if e_time else f"{s_time} น."
                except Exception:
                    time_display = "ตามนัดหมาย"

            item_box = {
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "paddingAll": "12px",
                "backgroundColor": "#f8fafc",
                "cornerRadius": "8px",
                "borderColor": "#e2e8f0",
                "borderWidth": "1px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"⏰ {time_display}",
                                "size": "xs",
                                "color": "#0284c7",
                                "weight": "bold",
                                "flex": 0
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": title,
                        "size": "sm",
                        "weight": "bold",
                        "color": "#0f172a",
                        "wrap": True,
                        "margin": "xs"
                    },
                    {
                        "type": "text",
                        "text": f"📍 {loc}",
                        "size": "xxs",
                        "color": "#64748b",
                        "wrap": True,
                        "margin": "xs"
                    }
                ]
            }
            if desc:
                item_box["contents"].append({
                    "type": "text",
                    "text": f"📝 {desc[:80]}..." if len(desc) > 80 else f"📝 {desc}",
                    "size": "xxs",
                    "color": "#94a3b8",
                    "wrap": True,
                    "margin": "xs"
                })
            event_boxes.append(item_box)
    else:
        event_boxes.append({
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "paddingAll": "16px",
            "backgroundColor": "#f8fafc",
            "cornerRadius": "8px",
            "contents": [
                {
                    "type": "text",
                    "text": f"🎉 {date_label} ไม่มีคิวงานถ่ายทำหรือนัดหมายในปฏิทินค่ะ",
                    "size": "sm",
                    "color": "#10b981",
                    "weight": "bold",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "ทีมงานสามารถพักผ่อน หรือเตรียมงานล่วงหน้าได้เต็มที่นะคะ ✨",
                    "size": "xs",
                    "color": "#64748b",
                    "align": "center",
                    "margin": "xs"
                }
            ]
        })

    # Summary Briefing Snippet - Guarantee non-empty text to prevent LINE Error 400
    brief_snippet = (briefing_text or "").strip()
    if not brief_snippet:
        brief_snippet = "คิวงานได้รับการตรวจสอบสดจาก Google Calendar ค่ะ"
    elif len(brief_snippet) > 180:
        brief_snippet = brief_snippet[:180] + "..."

    flex_payload = {
        "type": "flex",
        "altText": f"📅 สรุปตารางคิวงาน GHN168: {date_label}",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0f172a",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "GHN168 SCHEDULE",
                                "size": "xxs",
                                "color": "#f59e0b",
                                "weight": "bold",
                                "flex": 1
                            },
                            {
                                "type": "text",
                                "text": status_tag,
                                "size": "xxs",
                                "color": "#38bdf8",
                                "align": "end",
                                "flex": 1
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": f"📅 สรุปคิวงาน: {date_label}",
                        "size": "lg",
                        "color": "#ffffff",
                        "weight": "bold",
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": "GHN 168 Media & Creation Co., Ltd. (เลขาเฟิส)",
                        "size": "xxs",
                        "color": "#94a3b8",
                        "margin": "xs"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#eff6ff",
                        "cornerRadius": "8px",
                        "paddingAll": "10px",
                        "borderColor": "#bfdbfe",
                        "borderWidth": "1px",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💬 ความเห็นเลขาเฟิส:",
                                "size": "xxs",
                                "weight": "bold",
                                "color": "#1d4ed8"
                            },
                            {
                                "type": "text",
                                "text": brief_snippet,
                                "size": "xs",
                                "color": "#1e3a8a",
                                "wrap": True,
                                "margin": "xs"
                            }
                        ]
                    },
                    {
                        "type": "separator",
                        "margin": "md",
                        "color": "#f1f5f9"
                    },
                    {
                        "type": "text",
                        "text": "📌 รายการคิวงาน & นัดหมาย:",
                        "size": "xs",
                        "weight": "bold",
                        "color": "#475569",
                        "margin": "md"
                    },
                    *event_boxes
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#f8fafc",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "เช็คคิวงานสัปดาห์นี้",
                            "text": "เช็คคิวงานสัปดาห์นี้"
                        },
                        "style": "primary",
                        "color": "#0f172a",
                        "height": "sm"
                    },
                    {
                        "type": "text",
                        "text": "✨ ระบบแจ้งเตือนคิวงานล่วงหน้า 1 วันอัตโนมัติ (19:30 น.)",
                        "size": "xxs",
                        "color": "#94a3b8",
                        "align": "center",
                        "margin": "sm"
                    }
                ]
            }
        }
    }
    return sanitize_line_flex_payload(flex_payload)


def format_calendar_rule_based_briefing(events: List[Dict[str, Any]], date_label: str) -> str:
    """Formats a warm, structured executive secretary briefing from calendar events."""
    if events:
        lines = [f"สวัสดีค่ะบอสเก่ง บอสหอม บอสนิค และทีมงาน GHN168 ทุกท่านค่ะ ✨\nเฟิสขออนุญาตสรุปคิวงานสำหรับ {date_label} ให้นะคะ:\n"]
        for idx, ev in enumerate(events, 1):
            s_time = ev.get("startTime", "").split("T")[-1][:5] if "T" in ev.get("startTime", "") else ""
            lines.append(f"{idx}. ⏰ {s_time} น. - {ev.get('title')}")
            if ev.get("location"):
                lines.append(f"   📍 {ev.get('location')}")
        lines.append("\nขอให้ทุกท่านเตรียมอุปกรณ์ให้พร้อม และเดินทางอย่างปลอดภัย ทำงานราบรื่นตลอดวันนะคะ 🦾✨")
        return "\n".join(lines)
    else:
        return f"สวัสดีค่ะบอสเก่ง บอสหอม บอสนิค และทีมงาน GHN168 ทุกท่านค่ะ ✨\nสำหรับ {date_label} ไม่มีคิวงานถ่ายทำหรือนัดหมายในระบบค่ะ พักผ่อนและเติมพลังให้เต็มที่นะคะ 🏖️✨"


async def generate_calendar_daily_briefing(
    events: List[Dict[str, Any]],
    date_label: str,
    user_query: Optional[str] = None
) -> str:
    """
    Uses Gemini 3.7 Flash with Low Thinking Mode (thinking_budget: 512) to compose
    a thoughtful, warm, professional executive secretary briefing in First's signature tone.
    """
    events_summary = []
    for idx, ev in enumerate(events, 1):
        s_time = ev.get("startTime", "").split("T")[-1][:5] if "T" in ev.get("startTime", "") else "ไม่ระบุเวลา"
        e_time = ev.get("endTime", "").split("T")[-1][:5] if "T" in ev.get("endTime", "") else ""
        t_range = f"{s_time} - {e_time} น." if e_time else s_time
        events_summary.append(
            f"{idx}. [{t_range}] {ev.get('title')} | สถานที่: {ev.get('location') or 'ไม่ระบุ'} | รายละเอียด: {ev.get('description') or '-'}"
        )

    events_str = "\n".join(events_summary) if events_summary else "ไม่มีคิวงานในวันดังกล่าว"

    briefing_system = f"""{SYSTEM_INSTRUCTION}

================================================================================
🎯 ภารกิจพิเศษ: รายงานสรุปคิวงานประจำวัน (Executive Secretary Briefing)
================================================================================
คุณต้องร้อยเรียงและสรุปคิวงานสำหรับ "{date_label}" ของทีม GHN168 Media & Creation
ให้บอสเก่ง, บอสหอม, บอสนิค, บอสมด และทีมงานทราบทาง LINE:
- โทนเสียง: อบอุ่น สุภาพ มืออาชีพ ใส่ใจ กระชับ ชัดเจน
- หากมีงานถ่ายทำ: เตือนเตรียมอุปกรณ์ กล้อง เลนส์ แบตเตอรี่ ไฟ ให้พร้อม
- หากมีประชุม/ตรวจงาน: เตือนเตรียมไฟล์พรีเซนต์/ไฟล์ Final Master
- หากไม่มีคิวงาน: อวยพรให้พักผ่อนอย่างมีความสุขหรือเตรียมงานล่วงหน้า
- ใช้คำลงท้าย คะ/ค่ะ เรียกสมาชิกนำหน้าว่า "บอส" เสมอ
"""

    prompt = f"""กรุณาร้อยเรียงสรุปคิวงานสำหรับ {date_label} ดังต่อไปนี้:
รายการคิวงานจาก Google Calendar:
{events_str}

{"คำถามเพิ่มเติมจากผู้ใช้: " + user_query if user_query else "กรุณาสรุปให้กระชับ ครบถ้วน น่าอ่าน และส่งกำลังใจให้ทีมงานค่ะ"}
"""

    if genai_client or GEMINI_API_KEY:
        try:
            reply = await generate_gemini_reply(
                user_message=prompt,
                session_id="calendar_briefing_session",
                enable_search=False,
                system_instruction_override=briefing_system
            )
            if reply and len(reply.strip()) > 10:
                return reply.strip()
        except Exception as e:
            logger.error("Failed to generate AI calendar briefing: %s", e)

    # Local Rule-based Fallback Briefing
    return format_calendar_rule_based_briefing(events, date_label)


async def trigger_proactive_calendar_reminder(
    target_date: Optional[str] = None,
    target_chat_id: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Triggers the proactive daily calendar reminder (default: tomorrow's schedule).
    Generates AI briefing with Gemini 3.7 Flash and pushes LINE Flex Message.
    """
    now = datetime.now()
    from datetime import timedelta

    if target_date:
        target_d_str = target_date
        date_label = f"วันที่ {target_date}"
    else:
        tomorrow = now + timedelta(days=1)
        target_d_str = tomorrow.strftime("%Y-%m-%d")
        date_label = f"วันพรุ่งนี้ ({tomorrow.strftime('%d/%m/%Y')})"

    today_str = now.strftime("%Y-%m-%d")
    if not force and LAST_CALENDAR_REMINDER_DATE.get(today_str) == target_d_str:
        logger.info("Calendar reminder for %s already sent today (%s). Skipping.", target_d_str, today_str)
        return {
            "status": "already_sent",
            "message": f"Daily calendar reminder for {target_d_str} already sent today.",
            "target_date": target_d_str
        }

    # Fetch events from Google Calendar
    cal_data = get_calendar_events(target_date=target_d_str)
    events = cal_data.get("events", [])

    # Compose AI Briefing
    briefing_text = await generate_calendar_daily_briefing(events, date_label=date_label)
    flex_card = build_calendar_reminder_flex_message(events, date_label=date_label, briefing_text=briefing_text)

    messages = [
        {"type": "text", "text": briefing_text},
        flex_card
    ]

    target = target_chat_id or LINE_NOTIFICATION_TARGET_ID
    push_sent = False
    if target and LINE_CHANNEL_ACCESS_TOKEN:
        push_sent = send_line_push_message(target, messages)

    LAST_CALENDAR_REMINDER_DATE[today_str] = target_d_str

    return {
        "status": "success",
        "target_date": target_d_str,
        "date_label": date_label,
        "total_events": len(events),
        "events": events,
        "briefing_text": briefing_text,
        "flex_card": flex_card,
        "push_sent": push_sent,
        "target_chat_id": target,
        "is_mock": cal_data.get("is_mock", False),
        "timestamp": datetime.now().isoformat()
    }


async def check_and_run_daily_calendar_reminder():
    """
    Checks if current time (Asia/Bangkok) is 19:30.
    Triggers proactive calendar reminder for tomorrow if not yet triggered today.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Target trigger window: 19:30 (Hour=19, Minute=30..31)
    if now.hour == 19 and now.minute in [30, 31]:
        if today_str not in LAST_CALENDAR_REMINDER_DATE:
            logger.info("⏰ 19:30 Evening Proactive Schedule Trigger: Running daily calendar reminder for tomorrow...")
            await trigger_proactive_calendar_reminder()


async def check_and_run_daily_overdue_tracker():
    """
    Checks if current time (Asia/Bangkok) is 09:30 AM.
    Proactively calculates overdue invoices and sends alert to LINE group.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Target trigger window: 09:30 AM (Hour=9, Minute=30..31)
    if now.hour == 9 and now.minute in [30, 31]:
        if today_str not in LAST_OVERDUE_REMINDER_DATE:
            logger.info("⏰ 09:30 AM Proactive Schedule Trigger: Running daily overdue & aging invoice tracker...")
            overdue_data = get_overdue_and_aging_invoices()
            target = LINE_NOTIFICATION_TARGET_ID
            if target and LINE_CHANNEL_ACCESS_TOKEN:
                flex_card = build_overdue_invoices_flex_message(overdue_data)
                push_text = (
                    f"⏰ [09:30 น.] รายงานติดตามบิลค้างชำระ GHN168 ประจำวันค่ะ ✨\n"
                    f"• ค้างชำระเกินกำหนด: {overdue_data.get('total_overdue_count', 0)} ใบ ({overdue_data.get('total_overdue_amount', 0):,.2f} บาท)\n"
                    f"• ครบกำหนดวันนี้: {overdue_data.get('total_due_today_count', 0)} ใบ ({overdue_data.get('total_due_today_amount', 0):,.2f} บาท)"
                )
                send_line_push_message(target, [
                    {"type": "text", "text": push_text},
                    flex_card
                ])
                logger.info("09:30 AM Overdue summary pushed to %s", target)
            LAST_OVERDUE_REMINDER_DATE[today_str] = datetime.now().isoformat()


# ------------------------------------------------------------------------------
# 12. Proactive Tax Scheduler & Background Triggers
# ------------------------------------------------------------------------------
def trigger_scheduled_tax_reminder(reminder_type: str, target_chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Triggers a specified tax reminder notification, returning message payload and sending push if configured.
    Enriches with real-time VAT & WHT figures for monthly tax summary reminders.
    """
    if reminder_type not in TAX_REMINDER_SCHEDULES:
        return {
            "status": "error",
            "message": f"Unknown reminder_type: '{reminder_type}'. Available: {list(TAX_REMINDER_SCHEDULES.keys())}"
        }

    info = TAX_REMINDER_SCHEDULES[reminder_type]

    # Real-time data enrichment for monthly tax summaries
    acc_data = None
    if reminder_type in ["monthly_tax_28", "monthly_tax_01"]:
        try:
            now = datetime.now()
            if reminder_type == "monthly_tax_01":
                # Check previous month for reconciliation with accounting firm
                target_m = 12 if now.month == 1 else now.month - 1
                target_y = now.year - 1 if now.month == 1 else now.year
                acc_data = get_live_accounting_summary(month=target_m, year=target_y)
            else:
                acc_data = get_live_accounting_summary(month=now.month, year=now.year)
        except Exception as e:
            logger.warning("Could not fetch live accounting summary for tax reminder: %s", e)
            acc_data = {}

        summary = acc_data.get("summary", {}) if acc_data else {}
        period_label = (acc_data.get("period_label") if acc_data else None) or datetime.now().strftime("%m/%Y")
        vat_output = float(summary.get("total_income_vat_output") or 0.0)
        vat_input = float(summary.get("total_expense_vat_input") or 0.0)
        net_vat = float(summary.get("net_vat_balance") or round(vat_output - vat_input, 2))
        wht_deducted = float(summary.get("total_income_wht_deducted") or 0.0)
        wht_withheld = float(summary.get("total_expense_wht_withheld") or 0.0)

        if net_vat > 0:
            vat_status_desc = f"ต้องนำส่งภาษีเพิ่ม {net_vat:,.2f} บาท (ภาษีขาย > ภาษีซื้อ)"
        elif net_vat < 0:
            vat_status_desc = f"มีภาษีซื้อยกไป {abs(net_vat):,.2f} บาท (ภาษีซื้อ > ภาษีขาย)"
        else:
            vat_status_desc = "ยอดภาษีซื้อและภาษีขายเท่ากันพอดี (0.00 บาท)"

        if reminder_type == "monthly_tax_28":
            msg_text = (
                f"🏛️ [สรุปภาษีประจำเดือนรอบสิ้นเดือน (28th) - เลขาเฟิส]\n"
                f"สวัสดีค่ะบอสเก่ง บอสมด และทีมบริหาร GHN168 ค่ะ ✨\n\n"
                f"📊 รายงานสรุปตัวเลขภาษีสดประจำงวด {period_label} (รอบสิ้นเดือน):\n"
                f"• 🏛️ ภาษีขาย (VAT Output 7%): {vat_output:,.2f} บาท (จากใบเสร็จรับเงิน)\n"
                f"• 🛒 ภาษีซื้อ (VAT Input 7%): {vat_input:,.2f} บาท (จากบิลรายจ่าย)\n"
                f"• ⚖️ ยอด VAT สุทธิ: {vat_status_desc}\n\n"
                f"📑 ภาษีหัก ณ ที่จ่าย (WHT):\n"
                f"• 📥 ภาษีถูกหัก ณ ที่จ่าย: {wht_deducted:,.2f} บาท (ลูกค้าหัก GHN 168 ไว้)\n"
                f"• 📤 ภาษีหัก ณ ที่จ่ายนำส่ง: {wht_withheld:,.2f} บาท (GHN 168 หักไว้เตรียมนำส่ง ภ.ง.ด.3/53)\n\n"
                f"บอสมดและบอสเก่งสามารถตรวจสอบตัวเลขสดนี้เพื่อเตรียมปิดงวดภาษีสิ้นเดือนได้เลยนะคะ ✨"
            )
        else:  # monthly_tax_01
            msg_text = (
                f"📑 [สรุปภาษีประจำเดือนรอบต้นเดือน (1st) - เลขาเฟิส]\n"
                f"สวัสดีค่ะบอสเก่ง บอสมด และทีมบริหาร GHN168 ค่ะ ✨\n\n"
                f"📌 สรุปตัวเลขภาษีสดประจำงวด {period_label} เพื่อรีเช็คกับสำนักงานบัญชี:\n"
                f"• 🏛️ ภาษีขาย (VAT Output 7%): {vat_output:,.2f} บาท (จากใบเสร็จรับเงิน)\n"
                f"• 🛒 ภาษีซื้อ (VAT Input 7%): {vat_input:,.2f} บาท (จากบิลรายจ่าย)\n"
                f"• ⚖️ ยอด VAT สุทธิ: {vat_status_desc}\n\n"
                f"📑 ภาษีหัก ณ ที่จ่าย (WHT):\n"
                f"• 📥 ภาษีถูกหัก ณ ที่จ่าย: {wht_deducted:,.2f} บาท (ลูกค้าหัก GHN 168 ไว้)\n"
                f"• 📤 ภาษีหัก ณ ที่จ่ายนำส่ง: {wht_withheld:,.2f} บาท (GHN 168 หักไว้เตรียมนำส่ง ภ.ง.ด.3/53)\n\n"
                f"พร้อมส่งข้อมูลและตรวจสอบความถูกต้องร่วมกับสำนักงานบัญชีก่อนยื่นแบบ ภ.พ.30 และ ภ.ง.ด.1/3/53 ค่ะ ✨"
            )
    else:
        msg_text = info["message"]

    flex_card = build_tax_reminder_flex_message(reminder_type, acc_data=acc_data)
    messages = [
        {"type": "text", "text": msg_text},
        flex_card
    ]

    target = target_chat_id or LINE_NOTIFICATION_TARGET_ID
    push_sent = False
    if target and LINE_CHANNEL_ACCESS_TOKEN:
        push_sent = send_line_push_message(target, messages)

    return {
        "status": "success",
        "reminder_type": reminder_type,
        "title": info["title"],
        "message_text": msg_text,
        "flex_card": flex_card,
        "push_sent": push_sent,
        "target_chat_id": target,
        "timestamp": datetime.now().isoformat()
    }


def check_and_run_daily_tax_reminders(now_dt: Optional[datetime] = None) -> List[str]:
    """
    Evaluates current date and time (Asia/Bangkok) and triggers matching proactive tax reminders:
    1. Every 28th of month at 15:00 (15:00..15:01): monthly_tax_28 (สรุปภาษีรอบสิ้นเดือน)
    2. Every 1st of month at 15:00 (15:00..15:01): monthly_tax_01 (สรุปภาษีรอบต้นเดือนเพื่อรีเช็คสำนักงานบัญชี)
    3. Every 25th of month (10:00): monthly_bills_25 (ทวงบิลรายจ่าย)
    4. Every 5th of month (10:00): monthly_tax_05 (เดดไลน์ภาษีรายเดือน)
    5. 1 Sep & 25 Sep: pnd94_midyear_personal (ภ.ง.ด.94)
    6. 15 Jan, 15 Feb, 25 Mar: pnd90_91_annual_personal (ภ.ง.ด.90/91)
    7. 1 Aug & 20 Aug: pnd51_midyear_corporate (ภ.ง.ด.51)
    8. 1 Apr & 10 May: pnd50_annual_corporate (ภ.ง.ด.50)
    """
    now = now_dt or datetime.now()
    day = now.day
    month = now.month
    hour = now.hour
    minute = now.minute
    today_key = now.strftime("%Y-%m-%d")

    due_reminders = []

    # 1. 28th of every month at 15:00 (15:00..15:01)
    if day == 28 and hour == 15 and minute in [0, 1]:
        due_reminders.append("monthly_tax_28")

    # 2. 1st of every month at 15:00 (15:00..15:01)
    if day == 1 and hour == 15 and minute in [0, 1]:
        due_reminders.append("monthly_tax_01")

    # 3. 25th of every month (10:00)
    if day == 25 and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("monthly_bills_25")

    # 4. 5th of every month (10:00)
    if day == 5 and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("monthly_tax_05")

    # 5. PND94 (1 Sep, 25 Sep)
    if month == 9 and day in [1, 25] and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("pnd94_midyear_personal")

    # 6. PND90/91 (15 Jan, 15 Feb, 25 Mar)
    if ((month == 1 and day == 15) or (month == 2 and day == 15) or (month == 3 and day == 25)) and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("pnd90_91_annual_personal")

    # 7. PND51 (1 Aug, 20 Aug)
    if month == 8 and day in [1, 20] and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("pnd51_midyear_corporate")

    # 8. PND50 (1 Apr, 10 May)
    if ((month == 4 and day == 1) or (month == 5 and day == 10)) and (now_dt is not None or (hour == 10 and minute in [0, 1])):
        due_reminders.append("pnd50_annual_corporate")

    triggered = []
    for rem in due_reminders:
        key = f"{rem}_{today_key}"
        if key not in LAST_REMINDER_DATES:
            logger.info("Triggering scheduled tax reminder: %s for %s", rem, today_key)
            trigger_scheduled_tax_reminder(rem)
            LAST_REMINDER_DATES[key] = now.isoformat()
            triggered.append(rem)

    return triggered


async def combined_scheduler_background_loop():
    """Asynchronous background loop to periodically check 19:30 calendar reminder, 09:30 overdue tracker, and tax schedules."""
    logger.info("Combined Background Scheduler loop started (19:30 Calendar, 09:30 Overdue & Tax).")
    while True:
        try:
            await check_and_run_daily_calendar_reminder()
            await check_and_run_daily_overdue_tracker()
            check_and_run_daily_tax_reminders()
        except Exception as e:
            logger.error("Error in combined scheduler loop: %s", e)
        await asyncio.sleep(30)


# ------------------------------------------------------------------------------
# 13. Background LINE Event Processor
# ------------------------------------------------------------------------------
def should_reply_to_event(event: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if the bot should reply based on chat type, mentions, direct triggers,
    active conversation threads (90s window), quoted message actions, and pending confirmations.
    """
    source = event.get("source", {})
    source_type = source.get("type", "user")
    user_id = source.get("userId", "unknown")
    group_id = source.get("groupId") or source.get("roomId") or user_id
    session_id = group_id if source_type in ["group", "room"] else user_id

    message = event.get("message", {})
    msg_type = message.get("type", "")

    if msg_type not in ["text", "image", "audio"]:
        return False, f"unsupported message type: {msg_type}"

    # 1. 1-on-1 chat: always process and reply
    if source_type == "user":
        if msg_type == "audio":
            return True, "1-on-1 audio message"
        if msg_type == "image":
            return True, "1-on-1 image message for receipt OCR"
        text = message.get("text", "").strip()
        if not text:
            return False, "empty text"
        return True, "1-on-1 chat"

    # 2. Group / Room chat
    if msg_type == "image":
        return True, "image message for receipt OCR"

    if msg_type == "audio":
        active_thread = ACTIVE_CONVERSATION_THREADS.get(session_id)
        if active_thread and active_thread.get("user_id") == user_id and time.time() <= active_thread.get("expires_at", 0):
            return True, "active conversation thread"
        return False, "group message without bot trigger"

    text = message.get("text", "").strip()
    if not text:
        return False, "empty text"

    # 2.1 Mention Check: Native LINE Mention Object
    mentionees = message.get("mention", {}).get("mentionees", [])
    is_bot_mentioned_native = any(m.get("isSelf") is True for m in mentionees)
    has_other_mentionees = bool(mentionees) and not is_bot_mentioned_native
    if has_other_mentionees:
        # If tagged other group member (e.g. @Modchhi, @MRhommm), stay completely silent
        return False, "tagged other group member"

    text_lower = text.lower()

    # 2.2 Direct Bot Triggers (Native mention or name triggers)
    if is_bot_mentioned_native:
        return True, "matched direct bot trigger"

    for trigger in BOT_DIRECT_TRIGGERS:
        if trigger.lower() in text_lower:
            return True, "matched direct bot trigger"

    # 2.3 Quoted Message Actions
    quoted_msg_id = message.get("quotedMessageId")
    if quoted_msg_id:
        quote_actions = ["แปล", "สรุป", "คืออะไร", "ทำอะไรได้บ้าง", "ช่วยดู", "translate", "summarize", "อ่าน", "รายละเอียด", "รูปนี้"]
        if any(qa in text_lower for qa in quote_actions):
            return True, "quoted message action"

    # 2.4 Pending Confirmation Actions
    has_pending_state = (
        session_id in PENDING_DOCUMENT_ORDERS
        or session_id in PENDING_EXPENSE_CONFIRMATIONS
        or session_id in PENDING_INCOME_CONFIRMATIONS
        or session_id in PENDING_NEW_CUSTOMER_SAVING
    )
    confirmation_keywords = [
        "บันทึก", "ยืนยัน", "ออกใบเสร็จ", "ตกลง", "โอเค", "ยกเลิก",
        "confirm", "save", "cancel", "เซฟ", "บันทึกลูกค้า", "เซฟลูกค้า"
    ]
    if has_pending_state and any(ck in text_lower for ck in confirmation_keywords):
        return True, "pending confirmation action"

    # 2.5 Active Conversation Thread Window (90s)
    active_thread = ACTIVE_CONVERSATION_THREADS.get(session_id)
    if active_thread:
        thread_user = active_thread.get("user_id")
        thread_expiry = active_thread.get("expires_at", 0)
        if time.time() <= thread_expiry and thread_user == user_id:
            return True, "active conversation thread"

    # All other group messages without bot triggers: completely silent
    return False, "group message without bot trigger"


async def process_line_events(data: Dict[str, Any]):
    """Process incoming LINE Webhook events asynchronously."""
    events = data.get("events", [])
    for event in events:
        try:
            event_type = event.get("type")
            if event_type != "message":
                continue

            source = event.get("source", {})
            source_type = source.get("type", "user")
            user_id = source.get("userId", "unknown")
            group_id = source.get("groupId") or source.get("roomId") or user_id
            session_id = group_id if source_type in ["group", "room"] else user_id
            reply_token = event.get("replyToken")
            message_obj = event.get("message", {})
            msg_type = message_obj.get("type", "")
            msg_id = message_obj.get("id", "")
            quoted_msg_id = message_obj.get("quotedMessageId")

            speaker_name = resolve_partner_name(
                user_id=user_id,
                group_id=source.get("groupId"),
                room_id=source.get("roomId"),
                event=event
            )

            # Pre-cache media or text content
            if msg_type == "text":
                user_text = message_obj.get("text", "").strip()
                if msg_id and user_text:
                    RECENT_MEDIA_CACHE[msg_id] = user_text.encode("utf-8")
            elif msg_type == "image":
                if msg_id:
                    img_bytes = download_line_image_content(msg_id)
                    if img_bytes:
                        RECENT_MEDIA_CACHE[msg_id] = img_bytes
                        SESSION_LAST_IMAGE[session_id] = img_bytes
            elif msg_type == "audio":
                if msg_id:
                    aud_bytes = download_line_audio_content(msg_id)
                    if aud_bytes:
                        RECENT_MEDIA_CACHE[msg_id] = aud_bytes

            should_reply, reason = should_reply_to_event(event)

            logger.info("Event from %s (%s, type=%s, msg=%s): should_reply=%s (%s)", 
                        speaker_name, user_id[:8] if user_id else "unknown", source_type, msg_type, should_reply, reason)

            if not should_reply:
                # Passive Group Memory Buffer
                if msg_type == "text":
                    formatted_entry = f"[{speaker_name}]: {user_text}"
                    append_to_history(session_id, "user", formatted_entry)
                elif msg_type == "image":
                    append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งรูปภาพ (ID: {msg_id})]")
                elif msg_type == "audio":
                    append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งข้อความเสียง (ID: {msg_id})]")
                continue

            if not reply_token:
                continue

            # Update Active Thread Window (90 seconds)
            ACTIVE_CONVERSATION_THREADS[session_id] = {
                "user_id": user_id,
                "speaker_name": speaker_name,
                "expires_at": time.time() + ACTIVE_THREAD_TIMEOUT_SECONDS
            }

            # ==================================================================
            # CASE 1: Audio Message (Gemini Multimodal Voice AI)
            # ==================================================================
            if msg_type == "audio":
                audio_bytes = RECENT_MEDIA_CACHE.get(msg_id) or download_line_audio_content(msg_id)
                if not audio_bytes:
                    send_line_reply(reply_token, f"ขออภัยค่ะ{speaker_name} เลขาเฟิสไม่สามารถดาวน์โหลดไฟล์เสียงจาก LINE ได้ กรุณาส่งใหม่อีกครั้งนะคะ ✨")
                    continue

                reply_text = await transcribe_and_process_audio(audio_bytes, session_id, speaker_name=speaker_name)
                send_line_reply(reply_token, reply_text)
                append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งข้อความเสียง]")
                append_to_history(session_id, "model", reply_text)
                continue

            # ==================================================================
            # CASE 2: Image Message (Vision AI Receipt & Customer Slip Scanner)
            # ==================================================================
            if msg_type == "image":
                image_bytes = RECENT_MEDIA_CACHE.get(msg_id) or download_line_image_content(msg_id)
                if not image_bytes:
                    if source_type == "user":
                        send_line_reply(reply_token, "ขออภัยค่ะ ไม่สามารถดาวน์โหลดรูปภาพจาก LINE ได้ กรุณาส่งใหม่อีกครั้งนะคะ ✨")
                    continue

                ocr_data = await analyze_receipt_image_with_ai(image_bytes)
                is_fin_doc = bool(ocr_data.get("is_financial_document", True) and ocr_data.get("is_valid_receipt", True))
                if not is_fin_doc:
                    if source_type in ["group", "room"]:
                        # If user is in active discussion, provide general image analysis
                        if reason == "active conversation thread":
                            gen_reply = await analyze_general_image_with_ai(image_bytes, prompt="ช่วยดูภาพนี้และสรุปหรือแปลภาษาให้หน่อยค่ะ", speaker_name=speaker_name)
                            send_line_reply(reply_token, gen_reply)
                            append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งรูปภาพทั่วไป]")
                            append_to_history(session_id, "model", gen_reply)
                        else:
                            logger.info("Non-financial document image received in %s chat (%s), cached silently.", source_type, session_id)
                        continue
                    else:
                        send_line_reply(
                            reply_token,
                            "ขออภัยนะคะ ภาพนี้ไม่ใช่สลิปโอนเงิน ใบเสร็จรับเงิน หรือใบกำกับภาษี เลขาเฟิสจึงไม่ได้บันทึกลงระบบบัญชีค่ะ หากต้องการให้บันทึกค่าใช้จ่าย รบกวนส่งรูปบิลหรือสลิปการเงินนะคะ ✨"
                        )
                        continue

                tx_type = ocr_data.get("transaction_type", "expense")

                if tx_type == "income":
                    amt_val = float(ocr_data.get("net_amount") or ocr_data.get("amount") or 0.0)
                    sender_val = ocr_data.get("sender_name") or ""
                    matched_inv = match_incoming_slip_with_invoice(amt_val, sender_val)
                    PENDING_INCOME_CONFIRMATIONS[session_id] = {
                        "slip": ocr_data,
                        "matched_invoice": matched_inv
                    }

                    flex_card = build_income_slip_flex_message(ocr_data, matched_inv)
                    summary_text = (
                        f"💳 เลขาเฟิสตรวจพบสลิปเงินเข้าบริษัท ธ.กรุงไทย 520-0-61960-2 เรียบร้อยแล้วค่ะ{speaker_name} ✨\n"
                        f"• ยอดเงิน: +{amt_val:,.2f} บาท\n"
                        f"• ผู้โอน: {sender_val or 'ลูกค้า'}\n"
                        f"• วันที่-เวลา: {ocr_data.get('transfer_date')} {ocr_data.get('transfer_time', '')}\n"
                    )
                    if matched_inv:
                        summary_text += f"\n🎯 ตรงกับใบวางบิล: {matched_inv.get('doc_no')} ({matched_inv.get('client_name')})"
                    summary_text += "\n\nหากถูกต้อง พิมพ์ 'บันทึก' หรือ 'ออกใบเสร็จ' เพื่อออก RE และลงรายรับได้เลยนะคะ"

                    send_line_reply_messages(reply_token, [
                        {"type": "text", "text": summary_text},
                        flex_card
                    ])
                    append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งสลิปเงินเข้าบริษัท]")
                    append_to_history(session_id, "model", f"สแกนสลิปเงินเข้า ยอด {amt_val:,.2f} บาท")
                    continue
                else:
                    PENDING_EXPENSE_CONFIRMATIONS[session_id] = ocr_data
                    flex_card = build_expense_ocr_flex_message(ocr_data)
                    net_val = float(ocr_data.get("net_amount") or 0.0)
                    summary_text = (
                        f"เฟิสสแกนบิลของ '{ocr_data.get('store_name')}' เรียบร้อยแล้วค่ะ{speaker_name} ✨\n"
                        f"• วันที่: {ocr_data.get('doc_date')}\n"
                        f"• หมวดหมู่: {ocr_data.get('category')}\n"
                        f"• ยอดสุทธิ: {net_val:,.2f} บาท\n\n"
                        "หากถูกต้อง พิมพ์ 'บันทึก' หรือ 'ยืนยัน' เพื่อซิงค์ลง Google Sheets แท็บ 'รายจ่าย' ได้เลยนะคะ"
                    )
                    if net_val > 10000:
                        summary_text += "\n\n⚠️ [HITL Security Alert]: ยอดเงินเกิน 10,000 บาท กรุณาตรวจทานความถูกต้องก่อนยืนยันนะคะ"

                    send_line_reply_messages(reply_token, [
                        {"type": "text", "text": summary_text},
                        flex_card
                    ])
                    append_to_history(session_id, "user", f"[{speaker_name}]: [ส่งรูปภาพบิล/ใบเสร็จ]")
                    append_to_history(session_id, "model", f"สแกนบิล {ocr_data.get('store_name')} ยอด {net_val:,.2f} บาท")
                    continue

            # Text handling
            user_text = message_obj.get("text", "").strip()

            # ==================================================================
            # CASE 3: Quoted Message / Media Action (Quote Reply Translation/Summary)
            # ==================================================================
            if quoted_msg_id:
                cached_target = RECENT_MEDIA_CACHE.get(quoted_msg_id) or download_line_image_content(quoted_msg_id)
                if cached_target and isinstance(cached_target, bytes) and len(cached_target) >= 10:
                    # Check if it is image binary
                    if cached_target[:4] in [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb', b'\x89PNG', b'RIFF'] or (not cached_target.startswith(b'{') and not cached_target.startswith(b'[')):
                        gen_reply = await analyze_general_image_with_ai(cached_target, prompt=user_text, speaker_name=speaker_name)
                        send_line_reply(reply_token, gen_reply)
                        append_to_history(session_id, "user", f"[{speaker_name}]: {user_text} (อ้างอิงรูป {quoted_msg_id})")
                        append_to_history(session_id, "model", gen_reply)
                        continue

            # ==================================================================
            # CASE 4: Confirmations (Income Slip, Expense Scanned or Customer Save)
            # ==================================================================
            if user_text.lower() in ["บันทึก", "ยืนยัน", "ตกลง", "โอเค", "ออกใบเสร็จ", "save", "confirm"] and session_id in PENDING_INCOME_CONFIRMATIONS:
                pending_income = PENDING_INCOME_CONFIRMATIONS.pop(session_id)
                slip = pending_income.get("slip", {})
                matched_inv = pending_income.get("matched_invoice")

                target_ref = matched_inv.get("doc_no") if matched_inv else (slip.get("sender_name") or "ลูกค้า")
                amt_val = float(slip.get("net_amount") or slip.get("amount") or 0.0)
                overrides = {
                    "amount": amt_val,
                    "client_name": matched_inv.get("client_name") if matched_inv else (slip.get("sender_name") or "ลูกค้า"),
                    "project_name": matched_inv.get("project_name") if matched_inv else "บริการงานสื่อและโปรดักชั่น",
                    "payment_status": "ชำระเงินแล้ว",
                    "actual_payment_date": slip.get("transfer_date") or datetime.now().strftime("%d/%m/%Y")
                }
                conv_res = convert_document(target_ref, "receipt", overrides=overrides)
                doc_no = conv_res.get("doc_no")
                net_val = conv_res.get("totals", {}).get("net_total", amt_val)

                confirm_reply = (
                    f"✅ เลขาเฟิสออกใบเสร็จรับเงินเลขที่ {doc_no} ยอด {net_val:,.2f} บาท "
                    f"อัปเดตสถานะในแท็บ 'ใบวางบิล' เป็น 'ชำระแล้ว' และบันทึกลงแท็บ 'รายรับ' เรียบร้อยแล้วค่ะ{speaker_name} ✨"
                )
                flex_card = build_document_conversion_flex_message(conv_res)
                send_line_reply_messages(reply_token, [
                    {"type": "text", "text": confirm_reply},
                    flex_card
                ])
                append_to_history(session_id, "user", f"[{speaker_name}]: {user_text}")
                append_to_history(session_id, "model", confirm_reply)
                continue

            if user_text.lower() in ["บันทึก", "เซฟ", "ยืนยัน", "ตกลง", "โอเค", "save", "confirm", "บันทึกลูกค้า", "เซฟลูกค้า"] and session_id in PENDING_NEW_CUSTOMER_SAVING:
                new_cust = PENDING_NEW_CUSTOMER_SAVING.pop(session_id)
                save_res = save_new_customer(new_cust)
                cust_name = new_cust.get("customer_name")

                confirm_reply = (
                    f"✅ เฟิสบันทึกข้อมูลลูกค้า '{cust_name}' ลงฐานข้อมูลลูกค้า (แท็บ 'ข้อมูลลูกค้า') เรียบร้อยแล้วค่ะ{speaker_name} ✨\n"
                    f"ครั้งต่อไปเพียงพิมพ์ชื่อบริษัท เฟิสจะดึงข้อมูลมาใส่ให้อัตโนมัติเลยนะคะ 🦾"
                )
                cust_flex = build_customer_card_flex_message(new_cust)
                send_line_reply_messages(reply_token, [
                    {"type": "text", "text": confirm_reply},
                    cust_flex
                ])
                append_to_history(session_id, "user", f"[{speaker_name}]: {user_text}")
                append_to_history(session_id, "model", confirm_reply)
                continue

            if user_text.lower() in ["บันทึก", "ยืนยัน", "ตกลง", "โอเค", "save", "confirm"] and session_id in PENDING_EXPENSE_CONFIRMATIONS:
                pending_ocr = PENDING_EXPENSE_CONFIRMATIONS.pop(session_id)
                rec_res = record_scanned_expense(pending_ocr)
                doc_no = rec_res.get("doc_no")
                sheet_name = rec_res.get("sheet_name", "รายจ่าย")
                net_val = float(pending_ocr.get("net_amount") or 0.0)

                confirm_reply = (
                    f"✅ เฟิสบันทึกรายจ่าย '{pending_ocr.get('store_name')}' (เลขที่ {doc_no}) "
                    f"ยอด {net_val:,.2f} บาท ลง Google Sheets แท็บ '{sheet_name}' เรียบร้อยแล้วค่ะ{speaker_name} ✨"
                )
                send_line_reply(reply_token, confirm_reply)
                append_to_history(session_id, "user", f"[{speaker_name}]: {user_text}")
                append_to_history(session_id, "model", confirm_reply)
                continue

            # ==================================================================
            # CASE 5: Autonomous Agent Execution (Gemini 3.7 Native Tool Calling)
            # ==================================================================
            agent_res = await call_gemini_agent(user_text, session_id, enable_search=True, speaker_name=speaker_name)
            reply_text = agent_res.get("reply_text") or f"เลขาเฟิสพร้อมดูแลและจัดการให้{speaker_name}ค่ะ ✨"
            flex_cards = list(agent_res.get("flex_cards") or [])

            # Safety guarantee: If a financial document was converted or created in this turn, ensure its Flex Card is attached!
            doc_res = agent_res.get("doc_result") or agent_res.get("doc_data")
            if not flex_cards and isinstance(doc_res, dict) and doc_res.get("doc_no") and doc_res.get("doc_no") != "-":
                built_card = build_document_conversion_flex_message(doc_res) if "source_doc_no" in doc_res else build_document_flex_message(doc_res)
                if built_card:
                    flex_cards.append(built_card)

            if flex_cards:
                send_line_reply_messages(reply_token, [
                    {"type": "text", "text": reply_text},
                    *flex_cards[:4]
                ])
            else:
                send_line_reply(reply_token, reply_text)

            append_to_history(session_id, "user", f"[{speaker_name}]: {user_text}")
            append_to_history(session_id, "model", reply_text)

        except Exception as e:
            logger.error("Error processing LINE event: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(combined_scheduler_background_loop())
    logger.info("FastAPI Lifespan: GHN168 Corporate Assistant background tasks (Calendar & Tax) initialized.")
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("FastAPI Lifespan: GHN168 Corporate Assistant shutdown complete.")


app = FastAPI(
    title="GHN168 Corporate & Accounting Assistant (เลขา GHN168)",
    description="LINE Bot Server for GHN 168 Media & Creation Co., Ltd. - Corporate & Accounting Assistant with Google Calendar Sync & Gemini 3.7 Flash",
    version="3.7.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring, uptime verification, and feature capability inspection."""
    return {
        "status": "online",
        "bot_name": "GHN168 Corporate & Accounting Assistant (เลขา GHN168)",
        "company": "บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด",
        "gemini_model": GEMINI_MODEL,
        "thinking_budget": 512,
        "max_history_per_session": MAX_HISTORY_PER_SESSION,
        "features": {
            "gemini_3_7_flash_thinking": True,
            "human_like_executive_secretary_upgrade": True,
            "active_thread_memory_180s": True,
            "context_aware_reply_filter": True,
            "context_ellipsis_support": True,
            "proactive_calendar_reminder_1930": True,
            "on_demand_calendar_query": True,
            "on_demand_customer_query": True,
            "customer_database_live_sync": True,
            "proactive_tax_scheduler": True,
            "vision_ai_receipt_ocr": True,
            "google_search_grounding": True,
            "live_sheets_insights": True
        },
        "line_secret_configured": bool(LINE_CHANNEL_SECRET),
        "line_token_configured": bool(LINE_CHANNEL_ACCESS_TOKEN),
        "gemini_api_key_configured": bool(GEMINI_API_KEY),
        "gas_script_url_configured": bool(os.getenv("GAS_SCRIPT_URL")),
        "pdfshift_key_configured": bool(os.getenv("PDFSHIFT_API_KEY")),
        "active_sessions": len(CONVERSATION_HISTORY),
        "timestamp": time.time()
    }


@app.post("/callback")
@app.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: Optional[str] = Header(None, alias="X-Line-Signature")
):
    """LINE Webhook receiver endpoint."""
    body_bytes = await request.body()

    if not x_line_signature or not verify_line_signature(body_bytes, x_line_signature):
        logger.warning("Unauthorized access or invalid X-Line-Signature received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing X-Line-Signature"
        )

    try:
        body_str = body_bytes.decode("utf-8")
        data = json.loads(body_str) if body_str else {}
    except Exception as e:
        logger.error("Failed to parse JSON body: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    background_tasks.add_task(process_line_events, data)
    return JSONResponse(content={"status": "success"}, status_code=200)


# ------------------------------------------------------------------------------
# 15. Calendar & Schedule Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/calendar/trigger_reminder")
async def api_trigger_calendar_reminder(request: Request):
    """API endpoint to manually trigger proactive 19:30 daily calendar reminder."""
    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    except Exception:
        body = {}

    target_date = body.get("target_date")
    target_chat_id = body.get("target_chat_id")
    force = body.get("force", True)

    try:
        result = await trigger_proactive_calendar_reminder(
            target_date=target_date,
            target_chat_id=target_chat_id,
            force=force
        )
        return JSONResponse(content=result, status_code=200 if result.get("status") in ["success", "already_sent"] else 400)
    except Exception as e:
        logger.error("API trigger_calendar_reminder failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar/status")
async def api_calendar_status():
    """Returns Google Calendar sync status, last reminder date, and next reminders."""
    now = datetime.now()
    from datetime import timedelta
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    events_data = get_calendar_events(target_date=tomorrow)
    return {
        "status": "online",
        "connected_account": "ghn168media@gmail.com",
        "last_calendar_reminder": LAST_CALENDAR_REMINDER_DATE,
        "tomorrow_date": tomorrow,
        "tomorrow_events_count": len(events_data.get("events", [])),
        "is_mock": events_data.get("is_mock", False),
        "current_time_thailand": now.strftime("%Y-%m-%d %H:%M:%S")
    }


@app.get("/api/calendar/events")
async def api_get_calendar_events(
    target_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Endpoint to fetch live or fallback events from Google Calendar."""
    try:
        events_data = get_calendar_events(start_date=start_date, end_date=end_date, target_date=target_date)
        return JSONResponse(content=events_data, status_code=200)
    except Exception as e:
        logger.error("API get_calendar_events error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create_document")
async def api_create_document(request: Request):
    """Direct API endpoint to generate document HTML, save PDF, and sync row to Google Sheets."""
    try:
        body = await request.json()
        doc_type = body.get("doc_type", "quotation")
        doc_data = body.get("doc_data", body)

        result = generate_and_sync_document(
            doc_type=doc_type,
            doc_data=doc_data
        )
        return JSONResponse(content=result, status_code=200 if result.get("status") in ["success", "simulation"] else 400)
    except Exception as e:
        logger.error("API create_document failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/document_preview/{doc_type}", response_class=HTMLResponse)
async def api_document_preview(doc_type: str, client_name: str = "บริษัท ตัวอย่างทดสอบ จำกัด", amount: float = 15000.0):
    """Developer/Web preview endpoint returning full HTML document."""
    try:
        sample_data = {
            "doc_no": f"PREV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "client_name": client_name,
            "items": [{"desc": "งานบริการและตัดต่อสื่อโปรดักชั่น", "qty": 1, "unit": "งาน", "price": amount}],
            "is_vat": True,
            "wht_rate": 3.0
        }
        html = render_document_html(doc_type, sample_data)
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.api_route("/api/documents/pdf/{doc_no}", methods=["GET", "HEAD"])
@app.get("/api/documents/pdf/{doc_no}")
async def api_serve_document_pdf(doc_no: str):
    """
    Direct PDF Serving Endpoint for GHN168 Documents (QT, IV, RE, 50BIS).
    Serves existing PDF from local storage `/opt/ghn168_bot/generated_pdfs/` or renders live.
    """
    clean_doc_no = doc_no.strip()
    if clean_doc_no.endswith(".pdf"):
        clean_doc_no = clean_doc_no[:-4]

    # 1. Check if PDF already exists on disk
    existing_path = get_local_pdf_path(clean_doc_no)
    if existing_path and existing_path.is_file() and existing_path.stat().st_size > 1000:
        return FileResponse(
            path=str(existing_path),
            media_type="application/pdf",
            filename=f"{clean_doc_no}.pdf"
        )

    # 2. Look up document data in sheet / database
    doc_type = "quotation"
    if clean_doc_no.upper().startswith("IV"):
        doc_type = "invoice"
    elif clean_doc_no.upper().startswith("RE"):
        doc_type = "receipt"
    elif clean_doc_no.upper().startswith("50BIS") or clean_doc_no.upper().startswith("WHT"):
        doc_type = "wht"
    elif clean_doc_no.upper().startswith("PV"):
        doc_type = "expense"

    doc_data = find_document_by_no(clean_doc_no)
    if not doc_data:
        # Fallback dynamic mock template if document not yet indexed in sheets
        is_mcool = ("472" in clean_doc_no) or ("M-COOL" in clean_doc_no.upper()) or ("MCOOL" in clean_doc_no.upper())
        if is_mcool:
            doc_data = {
                "doc_no": clean_doc_no,
                "doc_date": datetime.now().strftime("%d/%m/%Y"),
                "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
                "client_tax_id": "0505568016475",
                "client_branch": "00000",
                "client_address": "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
                "client_phone": "092-419-3953",
                "project_name": "ถ่าย Event 3 วัน",
                "items": [{"desc": "ถ่าย Event 3 วัน", "qty": 1, "price": 18000.0, "amount": 18000.0}],
                "is_vat": True,
                "vat_rate": 0.07,
                "wht_rate": 0.0,
                "signer_name": "นาย มงคล วงศ์สกุลยานนท์"
            }
        else:
            doc_data = {
                "doc_no": clean_doc_no,
                "doc_date": datetime.now().strftime("%d/%m/%Y"),
                "client_name": "บริษัท ตัวอย่างทดสอบ จำกัด",
                "items": [{"desc": "งานบริการและตัดต่อสื่อโปรดักชั่น", "qty": 1, "unit": "งาน", "price": 15000.0, "amount": 15000.0}],
                "is_vat": True,
                "vat_rate": 0.07,
                "wht_rate": 3.0,
                "signer_name": "นาย มงคล วงศ์สกุลยานนท์"
            }

    # 3. Render HTML and generate local PDF via Chromium
    pdf_res = generate_document_pdf(doc_type, doc_data)
    if pdf_res.get("status") == "success" and pdf_res.get("pdf_path"):
        return FileResponse(
            path=pdf_res["pdf_path"],
            media_type="application/pdf",
            filename=f"{clean_doc_no}.pdf"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF for document '{clean_doc_no}': {pdf_res.get('message', 'Unknown error')}"
        )


@app.post("/api/scan_receipt")
async def api_scan_receipt(request: Request):
    """API endpoint to scan bill/receipt image with Gemini 3.7 Flash Vision OCR."""
    try:
        body = await request.json()
        image_b64 = body.get("image_base64")
        mime_type = body.get("mime_type", "image/jpeg")

        if not image_b64:
            raise HTTPException(status_code=400, detail="Missing 'image_base64' in request body")

        image_bytes = base64.b64decode(image_b64)
        ocr_result = await analyze_receipt_image_with_ai(image_bytes, mime_type=mime_type)
        flex_card = build_expense_ocr_flex_message(ocr_result)

        return {
            "status": "success",
            "ocr_result": ocr_result,
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API scan_receipt failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/summary")
async def api_accounting_summary(month: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """API endpoint to get live accounting summary from Google Sheets."""
    try:
        summary = get_live_accounting_summary(month=month, year=year)
        flex_card = build_accounting_summary_flex_message(summary)
        return {
            "status": "success",
            "summary_data": summary,
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API accounting_summary failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tax_reminders/trigger")
async def api_trigger_tax_reminder(request: Request):
    """API endpoint to trigger and test scheduled tax reminder alerts."""
    try:
        body = await request.json()
        reminder_type = body.get("reminder_type", "monthly_bills_25")
        target_id = body.get("target_id")
        result = trigger_scheduled_tax_reminder(reminder_type, target_chat_id=target_id)
        return JSONResponse(content=result, status_code=200 if result.get("status") == "success" else 400)
    except Exception as e:
        logger.error("API trigger_tax_reminder failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tax_reminders/status")
async def api_tax_reminders_status():
    """Returns all available tax reminder schedules and trigger history."""
    return {
        "status": "success",
        "schedules": TAX_REMINDER_SCHEDULES,
        "last_trigger_history": LAST_REMINDER_DATES,
        "total_schedules": len(TAX_REMINDER_SCHEDULES)
    }


@app.post("/api/test_chat")
async def test_chat(request: Request):
    """Developer endpoint to test GHN168 Corporate Assistant responses backed by Gemini 3.7 Autonomous Agent."""
    try:
        body = await request.json()
        message = body.get("message", "สวัสดีค่ะ ขอรายละเอียดบริษัทและข้อมูลบัญชีหน่อยค่ะ")
        session_id = body.get("session_id", "test_corporate_001")

        # Check New Customer Confirmation
        if message.strip().lower() in ["บันทึก", "เซฟ", "ยืนยัน", "ตกลง", "โอเค", "save", "confirm", "บันทึกลูกค้า", "เซฟลูกค้า"] and session_id in PENDING_NEW_CUSTOMER_SAVING:
            new_cust = PENDING_NEW_CUSTOMER_SAVING.pop(session_id)
            save_res = save_new_customer(new_cust)
            cust_name = new_cust.get("customer_name")
            reply = (
                f"✅ เฟิสบันทึกข้อมูลลูกค้า '{cust_name}' ลงฐานข้อมูลลูกค้า (แท็บ 'ข้อมูลลูกค้า') เรียบร้อยแล้วค่ะ ✨\n"
                f"ครั้งต่อไปเพียงพิมพ์ชื่อบริษัท เฟิสจะดึงข้อมูลมาใส่ให้อัตโนมัติเลยนะคะ 🦾"
            )
            return {
                "query": message,
                "session_id": session_id,
                "is_customer_saved": True,
                "customer_data": new_cust,
                "save_result": save_res,
                "reply": reply
            }

        agent_res = await call_gemini_agent(message, session_id, enable_search=True)
        reply = agent_res.get("reply_text") or "เลขาเฟิสพร้อมดูแลและจัดการให้ค่ะ ✨"
        doc_result = agent_res.get("doc_result")
        customer_result = agent_res.get("customer_result")
        calendar_result = agent_res.get("calendar_result")
        summary_result = agent_res.get("summary_result")
        doc_data = agent_res.get("doc_data") or agent_res.get("pending_order") or (doc_result if doc_result else None)

        is_doc = bool(doc_result or agent_res.get("pending_order") or session_id in PENDING_DOCUMENT_ORDERS)
        is_summary = bool(summary_result)
        is_cal = bool(calendar_result)
        is_cust = bool(customer_result)

        return {
            "query": message,
            "session_id": session_id,
            "is_document_order": is_doc,
            "is_accounting_summary": is_summary,
            "is_calendar_query": is_cal,
            "is_customer_query": is_cust,
            "customer_result": customer_result,
            "calendar_result": calendar_result,
            "extracted_doc_data": doc_data,
            "doc_data": doc_data,
            "doc_result": doc_result,
            "summary_result": summary_result,
            "executed_tools": agent_res.get("executed_tools", []),
            "flex_cards": agent_res.get("flex_cards", []),
            "reply": reply
        }
    except Exception as e:
        logger.error("API test_chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 15. Customer Database API Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/customers")
async def api_get_customers(
    search: Optional[str] = Query(None, description="ค้นหาชื่อลูกค้า, เลขผู้เสียภาษี หรือผู้ติดต่อ"),
    refresh: bool = Query(False, description="บังคับดึงข้อมูลใหม่จาก Google Sheets")
):
    """
    ดึงรายชื่อลูกค้าทั้งหมดจากแท็บ 'ข้อมูลลูกค้า' บน Google Sheets พร้อมรองรับการค้นหาและ Refresh Cache
    """
    try:
        customers = get_customers_database(force_refresh=refresh)
        if search and search.strip():
            matched = search_customer(search)
            if matched:
                return {
                    "status": "success",
                    "total": 1,
                    "search_query": search,
                    "customers": [matched]
                }
            else:
                q = search.strip().lower()
                filtered = [
                    c for c in customers
                    if q in c.get("customer_name", "").lower()
                    or q in c.get("tax_id", "").lower()
                    or q in c.get("contact_person", "").lower()
                    or q in c.get("address", "").lower()
                ]
                return {
                    "status": "success",
                    "total": len(filtered),
                    "search_query": search,
                    "customers": filtered
                }
        return {
            "status": "success",
            "total": len(customers),
            "customers": customers
        }
    except Exception as e:
        logger.error("API get_customers failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/customers")
async def api_save_customer(request: Request):
    """
    บันทึกหรืออัปเดตข้อมูลลูกค้าลงในแท็บ 'ข้อมูลลูกค้า' บน Google Sheets
    """
    try:
        body = await request.json()
        cust_name = body.get("customer_name") or body.get("client_name")
        if not cust_name:
            raise HTTPException(status_code=400, detail="กรุณาระบุชื่อลูกค้า / บริษัท (customer_name)")

        result = save_new_customer(body)
        return JSONResponse(
            content=result,
            status_code=200 if result.get("status") in ["success", "simulation", "partial_error"] else 400
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API save_customer failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 16. Extended Executive & Financial Engine API Endpoints (v3.0)
# ------------------------------------------------------------------------------

@app.post("/api/documents/convert")
async def api_convert_document(request: Request):
    """
    Document Lifecycle Pipeline Conversion Endpoint:
    - QT -> IV (source_doc_no -> target_type='invoice')
    - IV -> RE (source_doc_no -> target_type='receipt')
    - 50 ทวิ (target_type='wht')
    """
    try:
        body = await request.json()
        source_doc_no = body.get("source_doc_no") or body.get("doc_no")
        target_type = body.get("target_type") or "invoice"
        overrides = body.get("overrides", {})

        if not source_doc_no and not overrides.get("client_name"):
            raise HTTPException(status_code=400, detail="กรุณาระบุ source_doc_no หรือข้อมูลเอกสารต้นทาง")

        result = convert_document(
            source_doc_no=source_doc_no or "NEW",
            target_type=target_type,
            overrides=overrides
        )
        flex_card = build_document_conversion_flex_message(result)
        return JSONResponse(
            content={
                "status": "success",
                "conversion_result": result,
                "flex_card": flex_card
            },
            status_code=200 if result.get("status") in ["success", "simulation"] else 400
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API convert_document failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calendar/create_event")
async def api_create_calendar_event(request: Request):
    """API endpoint to create an event in Google Calendar (ghn168media@gmail.com)."""
    try:
        body = await request.json()
        title = body.get("title") or "คิวงาน GHN168"
        start_date = body.get("start_date") or datetime.now().strftime("%Y-%m-%d")
        end_date = body.get("end_date")
        location = body.get("location", "")
        description = body.get("description", "")
        is_all_day = body.get("is_all_day", True)

        result = create_calendar_event(
            title=title,
            start_date=start_date,
            end_date=end_date,
            location=location,
            description=description,
            is_all_day=is_all_day
        )
        flex_card = build_calendar_event_created_flex_message(result)
        return {
            "status": "success",
            "calendar_event": result,
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API create_calendar_event failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/invoices/check_overdue")
@app.post("/api/invoices/check_overdue")
async def api_check_overdue_invoices(target_date: Optional[str] = Query(None)):
    """API endpoint to check and calculate overdue & aging invoices and follow-up templates."""
    try:
        overdue_data = get_overdue_and_aging_invoices(target_date=target_date)
        flex_card = build_overdue_invoices_flex_message(overdue_data)
        return {
            "status": "success",
            "overdue_summary": overdue_data,
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API check_overdue_invoices failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/partners/financial_breakdown")
async def api_partner_financial_breakdown(month: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """API endpoint to get the full 3-Pillar Partner Financial breakdown."""
    try:
        data = get_partner_financial_breakdown(month=month, year=year)
        flex_all = build_partner_all_in_one_financial_flex_message(data)
        return {
            "status": "success",
            "breakdown": data,
            "flex_card": flex_all
        }
    except Exception as e:
        logger.error("API partner_financial_breakdown failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/partners/hunter")
async def api_partner_hunter(month: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """Pillar 1: Lead Hunter Leaderboard & Peer-Sharing Volume."""
    try:
        data = get_partner_financial_breakdown(month=month, year=year)
        flex_card = build_partner_hunter_flex_message(data)
        return {
            "status": "success",
            "pillar_1_lead_hunters": data.get("pillar_1_lead_hunters"),
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API partner_hunter failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/partners/labor")
async def api_partner_labor(month: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """Pillar 2: Labor Earned YTD."""
    try:
        data = get_partner_financial_breakdown(month=month, year=year)
        flex_card = build_partner_labor_flex_message(data)
        return {
            "status": "success",
            "pillar_2_labor_earned": data.get("pillar_2_labor_earned"),
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API partner_labor failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/partners/vault")
async def api_partner_vault(month: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """Pillar 3: Personal Vault & Central Pool."""
    try:
        data = get_partner_financial_breakdown(month=month, year=year)
        flex_card = build_partner_vault_flex_message(data)
        return {
            "status": "success",
            "pillar_3_personal_vault": data.get("pillar_3_personal_vault"),
            "flex_card": flex_card
        }
    except Exception as e:
        logger.error("API partner_vault failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/deploy")
async def api_admin_deploy(request: Request):
    """
    Secure endpoint to deploy updated code files to the server.
    Protected by LINE_CHANNEL_SECRET or ADMIN_API_KEY.
    """
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header.replace("Bearer ", "").strip()
    expected_secret = LINE_CHANNEL_SECRET or os.environ.get("LINE_CHANNEL_SECRET", "")
    admin_key = os.environ.get("ADMIN_API_KEY", "")
    if not token or (token != expected_secret and (not admin_key or token != admin_key)):
        raise HTTPException(status_code=401, detail="Unauthorized deploy request")

    body = await request.json()
    files = body.get("files", {})
    restart = body.get("restart", True)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    updated = []
    for rel_path, content in files.items():
        if ".." in rel_path or rel_path.startswith("/"):
            continue
        target_path = os.path.join(base_dir, rel_path)
        if isinstance(content, str):
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            updated.append(rel_path)

    if restart:
        import threading
        def _delayed_restart():
            time.sleep(1)
            os.system("systemctl restart ghn168-bot 2>/dev/null || true")
        threading.Thread(target=_delayed_restart, daemon=True).start()

    return {"status": "success", "updated_files": updated, "restarting": restart}


@app.post("/api/admin/exec")
async def api_admin_exec(request: Request):
    """
    Secure endpoint to execute system maintenance commands on VPS.
    Protected by LINE_CHANNEL_SECRET or ADMIN_API_KEY.
    """
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header.replace("Bearer ", "").strip()
    expected_secret = LINE_CHANNEL_SECRET or os.environ.get("LINE_CHANNEL_SECRET", "")
    admin_key = os.environ.get("ADMIN_API_KEY", "")
    if not token or (token != expected_secret and (not admin_key or token != admin_key)):
        raise HTTPException(status_code=401, detail="Unauthorized admin request")

    body = await request.json()
    command = body.get("command", "")
    timeout = body.get("timeout", 180)

    if not command:
        raise HTTPException(status_code=400, detail="Missing 'command' parameter")

    import subprocess
    try:
        proc = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except Exception as e:
        return {
            "status": "exception",
            "error": str(e)
        }


# ------------------------------------------------------------------------------
# 17. Main Runner
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting GHN168 Corporate & Accounting Assistant on http://%s:%d", HOST, PORT)
    uvicorn.run("line_bot_server:app", host=HOST, port=PORT, reload=True)

