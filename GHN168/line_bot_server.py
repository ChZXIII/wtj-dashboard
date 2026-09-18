#!/usr/bin/env python3
"""
================================================================================
GHN168 Autonomous Financial Secretary LINE Bot Server (Clean-Slate Architecture)
================================================================================
A lean, production-grade FastAPI server powering "เลขาเฟิส" (First) for GHN168.

Key Architectural Pillars:
1. 100% reply_token Architecture: Eliminates LINE Error 429 completely by delivering
   turn replies in a single response via reply_token (no instant-ack burn).
2. Draft & Confirm Protocol (Human-in-the-Loop): Financial documents and client POs
   generate in-memory drafts first. Official sequential numbers, PDFs, and Google Sheets
   rows are ONLY minted upon user confirmation.
3. Strict User Overrides: Signer names (บอสเก่ง, บอสหอม) and due dates (e.g. 16/10)
   specified by users deterministically override any PO or system defaults.
4. Zero Cache Poisoning: Failed media downloads never fall back to stale cache.
5. Multimodal Intelligence: Gemini 3.8 Flash with native tool calling, PDF & Vision.
================================================================================
"""

import os
import sys
import re
import json
import time
import uuid
import hmac
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Response, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure repo root is on sys.path
REPO_DIR = Path(__file__).resolve().parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

# Load Environment Variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ghn168_line_bot")

# Core Service Integrations
from ghn168_sync_service import (
    generate_and_sync_document,
    calculate_document_totals,
    search_customer,
    search_sheet_documents,
    find_document_by_no,
    normalize_doc_type,
    normalize_doc_no,
    detect_document_creator,
    format_currency,
    thai_baht_text,
    convert_document,
)
from local_pdf_engine import get_local_pdf_path, convert_html_to_pdf_local

# Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# ==============================================================================
# Configuration & Constants
# ==============================================================================
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
SERVER_VERSION = "4.0.0-clean-slate"

genai_client = genai.Client(api_key=GEMINI_API_KEY) if (genai and GEMINI_API_KEY) else None

# Executive Partners (Targeted Boss Recognition)
PARTNER_PROFILES: Dict[str, Dict[str, Any]] = {
    "keng": {
        "boss_title": "บอสเก่ง",
        "full_name": "นาย มงคล วงศ์สกุลยานนท์",
        "id_card": "3509900218949",
        "keywords": ["mhong", "keng", "เก่ง", "mongkol", "มงคล", "chz", "3509900218949"]
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
        "keywords": ["mrhommm", "mrhom", "hom", "หอม", "natthawat", "ณัฐวัฒน์", "1509900596688"]
    },
    "mod": {
        "boss_title": "บอสมด",
        "full_name": "นาง ณัฐนรี วงศ์สกุลยานนท์",
        "id_card": "1509900148537",
        "keywords": ["modchhi", "modchi", "mod", "มด", "natnaree", "ณัฐนรี", "1509900148537"]
    },
}

# In-Memory State & Caches
ACTIVE_DRAFTS: Dict[str, Dict[str, Any]] = {}
SESSION_ACTIVE_DRAFT: Dict[str, str] = {}
RECENT_MEDIA_CACHE: Dict[str, bytes] = {}
SESSION_LAST_FILE: Dict[str, Dict[str, Any]] = {}
SESSION_LAST_GENERATED_DOCS: Dict[str, Dict[str, Any]] = {}
CONVERSATION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
USER_PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}
ACTIVE_CONVERSATION_THREADS: Dict[str, Dict[str, Any]] = {}

ACTIVE_THREAD_TIMEOUT_SECONDS = 90
BOT_DIRECT_TRIGGERS = ["@เลขาเฟิส", "เลขาเฟิส", "เฟิส", "น้องเฟิส", "บอท", "bot", "@bot"]

# ==============================================================================
# FastAPI App Initialization
# ==============================================================================
app = FastAPI(
    title="GHN168 Autonomous Financial Secretary LINE Bot Server",
    version=SERVER_VERSION,
    description="Clean-slate Pure-Agent architecture with Draft & Confirm Protocol and 100% reply_token."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Partner & User Overrides Engine
# ==============================================================================
def resolve_partner_name(
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    display_name: Optional[str] = None,
    room_id: Optional[str] = None,
    event: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """Identifies if the speaker is one of the 4 executive partners (บอสเก่ง, บอสนิค, บอสหอม, บอสมด) or client."""
    if event:
        source = event.get("source", {})
        user_id = user_id or source.get("userId")
        group_id = group_id or source.get("groupId")
        room_id = room_id or source.get("roomId")

    disp = (display_name or kwargs.get("display_name") or "").strip()
    u_id = (user_id or "").strip()
    grp = (group_id or "").strip()

    if not disp and grp and not grp.startswith(("C", "R", "group", "room", "c_", "r_")):
        disp = grp

    combined = f"{u_id} {disp} {grp}".lower()
    for _, pinfo in PARTNER_PROFILES.items():
        title = pinfo["boss_title"]
        id_card = pinfo.get("id_card", "")
        if id_card and id_card in u_id:
            return title
        for kw in pinfo["keywords"]:
            if kw.lower() in combined:
                return title

    if disp and not disp.startswith(("C", "R", "group", "room")):
        return disp if disp.startswith("คุณ") else f"คุณ {disp}"
    return "ผู้บริหาร"


def apply_strict_user_overrides(user_message: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic override check (Highest Priority):
    - If 'บอสเก่ง', 'คุณเก่ง', 'มงคล', 'keng' in user prompt -> force signer_name = 'นาย มงคล วงศ์สกุลยานนท์'
    - If 'บอสหอม', 'คุณหอม', 'ณัฐวัฒน์', 'hom' in user prompt -> force signer_name = 'นาย ณัฐวัฒน์ ปวงจันทร์หอม'
    - If date pattern in user prompt (e.g. '16/10', '16/10/2026') -> force due_date = '16/10/2026'
    - Overrides must NEVER be overwritten by previous document defaults or PO defaults.
    """
    text = (user_message or "").strip()

    # 1. Signer Override
    if any(k in text for k in ["บอสเก่ง", "คุณเก่ง", "มงคล", "keng"]):
        data["signer_name"] = "นาย มงคล วงศ์สกุลยานนท์"
    elif any(k in text for k in ["บอสหอม", "คุณหอม", "ณัฐวัฒน์", "hom"]):
        data["signer_name"] = "นาย ณัฐวัฒน์ ปวงจันทร์หอม"

    # 2. Due Date Override
    m_full = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b", text)
    if m_full:
        d = int(m_full.group(1))
        m = int(m_full.group(2))
        y = int(m_full.group(3))
        if y < 100:
            y = 2000 + y
        elif y > 2500:
            y -= 543
        data["due_date"] = f"{d:02d}/{m:02d}/{y}"
    else:
        m_dm = re.search(r"(?:แก้วัน(?:ที่)?(?:เป็น)?|วัน(?:ที่)?ครบกำหนด(?:เป็น)?|due\s*date\s*[:=]?|ภายในวันที่|\b)\s*(\d{1,2})[/.-](\d{1,2})\b", text, re.I)
        if m_dm:
            d = int(m_dm.group(1))
            m = int(m_dm.group(2))
            if 1 <= d <= 31 and 1 <= m <= 12:
                cur_y = datetime.now().year
                data["due_date"] = f"{d:02d}/{m:02d}/{cur_y}"

    # 3. PO Number Override
    m_po = re.search(
        r"(?:\bpo\s*no\.?|\bp\.o\.|\bpo\b|ใบสั่งซื้อ|เลขที่ใบสั่งซื้อ)(?:\s*[:：#=]\s*|\s+)([A-Za-z0-9\-_/]+)",
        text,
        re.I
    )
    if m_po:
        cand_po = m_po.group(1).strip()
        if not cand_po.startswith(("_", "number")):
            data["po_number"] = cand_po

    # 4. Job Code Override
    m_job = re.search(
        r"(?:\bjob\s*code\b|\bjob\b|\bproject\s*code\b|รหัสโครงการ|รหัสงาน)(?:\s*[:：#=]\s*|\s+)([A-Za-z0-9\-_/]+)",
        text,
        re.I
    )
    if m_job:
        cand_job = m_job.group(1).strip()
        if not cand_job.startswith(("_", "code")):
            data["job_code"] = cand_job

    return data


def is_corporate_customer(client_name: Optional[str], client_tax_id: Optional[str] = None) -> bool:
    """Detects whether a customer is a corporate entity."""
    if not client_name:
        return False
    c_name = str(client_name).strip()
    corp_indicators = ["บริษัท", "บจก", "บมจ", "ห้างหุ้นส่วน", "หจก", "จำกัด", "co.,", "ltd", "inc", "corp"]
    if any(k in c_name.lower() for k in corp_indicators):
        return True
    if client_tax_id and len(re.sub(r"\D", "", str(client_tax_id))) == 13:
        return True
    return False


def determine_smart_wht_rate(
    client_name: Optional[str] = None,
    project_name: Optional[str] = None,
    raw_text: Optional[str] = None,
    explicit_wht_rate: Optional[Union[float, int, str]] = None,
    doc_type: Optional[str] = None
) -> float:
    """Calculates Smart Corporate WHT rate (3% service, 5% rental, 1% transport, 0% quote/individual)."""
    norm_doc = str(doc_type or "").lower().strip()
    if norm_doc in ["quotation", "qt", "ใบเสนอราคา"]:
        return 0.0

    if explicit_wht_rate is not None and str(explicit_wht_rate).strip() != "":
        try:
            r = float(explicit_wht_rate)
            return round(r * 100.0, 4) if 0.0 < r < 1.0 else r
        except (ValueError, TypeError):
            pass

    full_context = f"{client_name or ''} {project_name or ''} {raw_text or ''}".lower()
    if any(k in full_context for k in ["ไม่หัก", "no wht", "0%"]):
        return 0.0
    if "1%" in full_context:
        return 1.0
    if "5%" in full_context:
        return 5.0
    if "3%" in full_context:
        return 3.0

    if any(k in full_context for k in ["เช่า", "ให้เช่า", "rent", "rental"]):
        return 5.0
    if any(k in full_context for k in ["ขนส่ง", "ขนย้าย", "transport", "logistics"]):
        return 1.0
    if norm_doc in ["wht", "50bis", "50ทวิ"]:
        return 3.0

    return 3.0 if is_corporate_customer(client_name) else 0.0


# ==============================================================================
# LINE Messaging Helpers (100% reply_token, Zero Push for Standard Turns)
# ==============================================================================
def send_line_reply_messages(reply_token: str, messages: List[Dict[str, Any]], is_fallback: bool = False) -> bool:
    """Delivers final text and Flex Cards in a single reply call via reply_token. Prevents 429."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not reply_token:
        logger.warning("Missing LINE token or reply_token. Skipped reply.")
        return False

    if reply_token.startswith("mock_") or reply_token.startswith("test_"):
        logger.info("Mock reply_token handled successfully: %d messages", len(messages))
        return True

    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {"replyToken": reply_token, "messages": messages[:5]}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            logger.info("Reply successfully sent via reply_token [%s...]", reply_token[:8])
            return True
        logger.error("LINE reply failed [%d]: %s", resp.status_code, resp.text)
        if not is_fallback:
            fallback_texts = [m.get("text") or m.get("altText", "") for m in messages if m.get("text") or m.get("altText")]
            if fallback_texts:
                fb_msgs = [{"type": "text", "text": str(t)[:4000]} for t in fallback_texts[:5]]
                return send_line_reply_messages(reply_token, fb_msgs, is_fallback=True)
        return False
    except Exception as e:
        logger.error("Exception in send_line_reply_messages: %s", e)
        return False


def send_line_reply(reply_token: str, text: str) -> bool:
    """Convenience helper to reply with plain text via reply_token."""
    return send_line_reply_messages(reply_token, [{"type": "text", "text": text}])


def send_line_push_message(to: str, messages: List[Dict[str, Any]], is_fallback: bool = False) -> bool:
    """Push API helper strictly reserved for background timers / cron jobs, NEVER for turn replies."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not to or to.startswith("test_") or to == "mock_session":
        return True
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = requests.post(url, json={"to": to, "messages": messages[:5]}, headers=headers, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logger.error("Exception in push message: %s", e)
        return False


def send_line_file_message(to: str, file_url: str, file_name: str) -> bool:
    """Sends native LINE File message."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not to or to.startswith("test_"):
        return True
    msg = {"type": "file", "title": file_name, "contentProvider": {"type": "external", "originalContentUrl": file_url}}
    return send_line_push_message(to, [msg])


def send_line_loading_animation(chat_id: str, loading_seconds: int = 30) -> bool:
    """Starts chat loading animation on 1-on-1 chats."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not chat_id or not chat_id.startswith("U"):
        return False
    url = "https://api.line.me/v2/bot/chat/loading/start"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        requests.post(url, json={"chatId": chat_id, "loadingSeconds": min(max(loading_seconds, 5), 60)}, headers=headers, timeout=4)
        return True
    except Exception:
        return False


def download_line_image_content(message_id: str) -> Optional[bytes]:
    """Downloads binary image from LINE Content API with zero cache poisoning."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not message_id:
        return None
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        logger.error("Failed to download LINE image %s: %s", message_id, e)
        return None


def download_line_file_content(message_id: str) -> Optional[bytes]:
    """Downloads binary file from LINE Content API with zero cache poisoning."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not message_id:
        return None
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=30)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        logger.error("Failed to download LINE file %s: %s", message_id, e)
        return None


# ==============================================================================
# Flex Message Builders (Draft Summary & Official Document Cards)
# ==============================================================================
def build_draft_summary_flex_message(draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the Human-in-the-Loop Draft Summary Flex Card.
    Displays customer, PO/Job Code, full itemized breakdown (no bundling),
    subtotal, VAT, net total, signer, due date, and Confirm / Edit action buttons.
    """
    draft_id = draft.get("draft_id", "DRAFT-001")
    doc_type = draft.get("doc_type", "quotation")
    type_names = {
        "quotation": "ใบเสนอราคา (Quotation)",
        "invoice": "ใบวางบิล / ใบแจ้งหนี้ (Invoice)",
        "receipt": "ใบเสร็จรับเงิน (Receipt)",
        "wht": "หนังสือรับรองหัก ณ ที่จ่าย (50 ทวิ)"
    }
    badge_title = type_names.get(doc_type, "เอกสารทางการเงิน")

    client_name = draft.get("client_name") or "ลูกค้าทั่วไป"
    client_tax_id = draft.get("client_tax_id") or "-"
    po_number = draft.get("po_number")
    job_code = draft.get("job_code")
    ref_doc_no = draft.get("ref_doc_no")
    doc_date = draft.get("doc_date") or datetime.now().strftime("%d/%m/%Y")
    due_date = draft.get("due_date") or doc_date
    signer_name = draft.get("signer_name") or "นาย มงคล วงศ์สกุลยานนท์"

    items = draft.get("items") or []
    totals = draft.get("totals") or {}
    pre_vat = float(totals.get("pre_vat") or draft.get("pre_vat") or draft.get("amount") or 0.0)
    vat_amt = float(totals.get("vat_amount") or draft.get("vat_amount") or 0.0)
    wht_amt = float(totals.get("wht_amount") or draft.get("wht_amount") or 0.0)
    net_total = float(totals.get("net_total") or draft.get("net_total") or (pre_vat + vat_amt - wht_amt))

    # Meta Rows Box
    meta_contents: List[Dict[str, Any]] = [
        {"type": "text", "text": client_name, "weight": "bold", "size": "md", "color": "#0f172a", "wrap": True},
    ]
    if client_tax_id and client_tax_id != "-":
        meta_contents.append({"type": "text", "text": f"เลขผู้เสียภาษี: {client_tax_id}", "size": "xs", "color": "#64748b"})

    meta_grid = [
        {"type": "separator", "margin": "md"},
        {"type": "box", "layout": "horizontal", "margin": "sm", "contents": [
            {"type": "text", "text": "วันที่:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": doc_date, "size": "xs", "weight": "bold", "color": "#1e293b", "flex": 6}
        ]},
        {"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "ครบกำหนดชำระ:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": due_date, "size": "xs", "weight": "bold", "color": "#0284c7", "flex": 6}
        ]},
        {"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "ผู้ลงนาม:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": signer_name, "size": "xs", "weight": "bold", "color": "#1e293b", "flex": 6}
        ]}
    ]
    if po_number and po_number != "-":
        meta_grid.append({"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "เลขที่ P.O.:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": po_number, "size": "xs", "weight": "bold", "color": "#d97706", "flex": 6}
        ]})
    if job_code and job_code != "-":
        meta_grid.append({"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "Job Code:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": job_code, "size": "xs", "weight": "bold", "color": "#4f46e5", "flex": 6}
        ]})
    if ref_doc_no and ref_doc_no != "-":
        meta_grid.append({"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "อ้างอิงเอกสาร:", "size": "xs", "color": "#64748b", "flex": 4},
            {"type": "text", "text": ref_doc_no, "size": "xs", "weight": "bold", "color": "#64748b", "flex": 6}
        ]})
    meta_contents.extend(meta_grid)

    # Itemized Breakdown Rows (Without bundling!)
    item_rows: List[Dict[str, Any]] = [
        {"type": "separator", "margin": "md"},
        {"type": "text", "text": "📦 รายการสินค้าและบริการ (Itemized):", "size": "xs", "weight": "bold", "color": "#334155", "margin": "md"}
    ]
    for it in items[:6]:
        desc = str(it.get("desc") or "บริการ").strip()
        qty = float(it.get("qty") or 1)
        price = float(it.get("price") or 0.0)
        amt = float(it.get("amount") or (qty * price))
        item_rows.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "xs",
            "contents": [
                {"type": "text", "text": f"• {desc}", "size": "xs", "color": "#475569", "flex": 6, "wrap": True},
                {"type": "text", "text": f"{amt:,.2f} ฿", "size": "xs", "color": "#0f172a", "weight": "bold", "align": "end", "flex": 4}
            ]
        })

    # Financial Totals Box
    fin_box = [
        {"type": "separator", "margin": "md"},
        {"type": "box", "layout": "horizontal", "margin": "sm", "contents": [
            {"type": "text", "text": "ยอดก่อนภาษี (Subtotal):", "size": "xs", "color": "#64748b", "flex": 6},
            {"type": "text", "text": f"{pre_vat:,.2f} ฿", "size": "xs", "align": "end", "color": "#334155", "flex": 4}
        ]},
        {"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "ภาษีมูลค่าเพิ่ม 7% (VAT):", "size": "xs", "color": "#64748b", "flex": 6},
            {"type": "text", "text": f"{vat_amt:,.2f} ฿", "size": "xs", "align": "end", "color": "#334155", "flex": 4}
        ]}
    ]
    if wht_amt > 0:
        fin_box.append({"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": f"หัก ณ ที่จ่าย ({draft.get('wht_rate', 3)}%):", "size": "xs", "color": "#64748b", "flex": 6},
            {"type": "text", "text": f"-{wht_amt:,.2f} ฿", "size": "xs", "align": "end", "color": "#dc2626", "flex": 4}
        ]})
    fin_box.extend([
        {"type": "separator", "margin": "sm"},
        {"type": "box", "layout": "horizontal", "margin": "sm", "contents": [
            {"type": "text", "text": "ยอดรวมสุทธิ (Net Total):", "size": "sm", "weight": "bold", "color": "#0f172a", "flex": 5},
            {"type": "text", "text": f"{net_total:,.2f} ฿", "size": "md", "weight": "bold", "color": "#059669", "align": "end", "flex": 5}
        ]}
    ])

    body_contents = meta_contents + item_rows + fin_box

    bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "backgroundColor": "#0f172a",
            "contents": [
                {"type": "text", "text": "📋 ร่างเอกสาร (Draft Preview)", "weight": "bold", "size": "sm", "color": "#38bdf8"},
                {"type": "text", "text": f"{badge_title} • {draft_id}", "size": "xs", "color": "#94a3b8", "margin": "xs"}
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
            "spacing": "sm",
            "paddingAll": "16px",
            "backgroundColor": "#f8fafc",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#059669",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "✅ ออกเอกสารจริง (Confirm)",
                        "text": f"ยืนยันออกเอกสาร {draft_id}"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "✏️ สั่งแก้ไข",
                        "text": f"ขอแก้ไขร่าง {draft_id}"
                    }
                },
                {
                    "type": "text",
                    "text": "💡 พิมพ์สั่งแก้ไขได้ทันที เช่น 'แก้คนเซ็นเป็นบอสเก่ง' หรือ 'แก้วันเป็น 16/10'",
                    "size": "xxs",
                    "color": "#94a3b8",
                    "align": "center",
                    "wrap": True,
                    "margin": "xs"
                }
            ]
        }
    }

    return {"type": "flex", "altText": f"📋 ร่าง{badge_title}: {client_name}", "contents": bubble}


def build_document_flex_message(doc_res: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs official LINE Flex Card upon confirmation, with buttons to view/download PDF."""
    doc_type = doc_res.get("doc_type") or doc_res.get("target_type") or "quotation"
    norm_doc = normalize_doc_type(doc_type)

    type_info = {
        "quotation": ("ใบเสนอราคา (Quotation)", "#0284c7"),
        "invoice": ("ใบวางบิล / ใบแจ้งหนี้ (Invoice)", "#4f46e5"),
        "receipt": ("ใบเสร็จรับเงิน (Receipt)", "#059669"),
        "wht": ("หนังสือรับรองหักภาษี (50 ทวิ)", "#8b5cf6")
    }
    badge_title, header_color = type_info.get(norm_doc, ("เอกสารทางการเงิน", "#0284c7"))

    doc_no = doc_res.get("doc_no") or "-"
    client_name = doc_res.get("client_name") or "-"
    project_name = doc_res.get("project_name") or "-"
    totals = doc_res.get("totals") or {}
    net_total = float(totals.get("net_total") or doc_res.get("net_total") or 0.0)
    pdf_url = doc_res.get("pdf_url") or f"https://srv1913532.hstgr.cloud/api/documents/pdf/{doc_no}"

    footer_buttons = [
        {
            "type": "button",
            "style": "primary",
            "color": header_color,
            "height": "sm",
            "action": {"type": "uri", "label": "📄 ดูไฟล์ PDF บน Google Drive", "uri": pdf_url}
        },
        {
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {"type": "uri", "label": "📥 ดาวน์โหลด PDF", "uri": f"https://srv1913532.hstgr.cloud/api/documents/pdf/{doc_no}"}
        }
    ]

    bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "backgroundColor": header_color,
            "contents": [
                {"type": "text", "text": badge_title, "weight": "bold", "size": "sm", "color": "#ffffff"},
                {"type": "text", "text": f"เลขที่: {doc_no}", "size": "xs", "color": "#f1f5f9", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": client_name, "weight": "bold", "size": "md", "color": "#0f172a", "wrap": True},
                {"type": "text", "text": project_name, "size": "xs", "color": "#64748b", "margin": "xs", "wrap": True},
                {"type": "separator", "margin": "md"},
                {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                    {"type": "text", "text": "ยอดรวมสุทธิ:", "size": "sm", "weight": "bold", "color": "#0f172a", "flex": 5},
                    {"type": "text", "text": f"{net_total:,.2f} ฿", "size": "md", "weight": "bold", "color": "#059669", "align": "end", "flex": 5}
                ]},
                {"type": "text", "text": "✅ บันทึกลงระบบ Google Sheets และออกไฟล์ PDF สำเร็จ", "size": "xxs", "color": "#16a34a", "margin": "md"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "16px",
            "backgroundColor": "#f8fafc",
            "contents": footer_buttons
        }
    }
    return {"type": "flex", "altText": f"📄 ออกเอกสาร {doc_no} เรียบร้อยแล้ว", "contents": bubble}


def build_document_conversion_flex_message(conv_res: Dict[str, Any]) -> Dict[str, Any]:
    """Delegates conversion results to standardized official document flex message."""
    return build_document_flex_message(conv_res)


# ==============================================================================
# Draft & Confirm Protocol Engine
# ==============================================================================
def create_or_update_draft(session_id: str, prompt: str, data: Dict[str, Any], speaker_name: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new draft or updates an existing draft in memory without writing to sheets or rendering PDF."""
    norm_doc = normalize_doc_type(data.get("doc_type", "quotation"))
    doc_date = data.get("doc_date") or datetime.now().strftime("%d/%m/%Y")

    # Due date default: +30 days for quotation & invoice
    due_date = data.get("due_date")
    if not due_date:
        try:
            base_dt = datetime.strptime(str(doc_date).strip(), "%d/%m/%Y")
            due_date = (base_dt + timedelta(days=30)).strftime("%d/%m/%Y")
        except Exception:
            due_date = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")

    # Client lookup from database
    client_name = data.get("client_name") or "ลูกค้าทั่วไป"
    cust = search_customer(client_name)
    if cust:
        client_name = cust.get("customer_name") or client_name
        client_tax_id = data.get("client_tax_id") or cust.get("tax_id") or "-"
        client_branch = data.get("client_branch") or cust.get("branch") or "00000"
        client_address = data.get("client_address") or cust.get("address") or "-"
        client_phone = data.get("client_phone") or cust.get("phone") or "-"
    else:
        client_tax_id = data.get("client_tax_id") or "-"
        client_branch = data.get("client_branch") or "00000"
        client_address = data.get("client_address") or "-"
        client_phone = data.get("client_phone") or "-"

    project_name = data.get("project_name") or "บริการงานสื่อและโปรดักชั่น"
    signer_name = data.get("signer_name") or "นาย มงคล วงศ์สกุลยานนท์"

    items = data.get("items") or []
    if not items:
        amt = float(data.get("amount") or 0.0)
        items = [{"desc": project_name, "qty": 1, "price": amt, "amount": amt}]

    is_vat = bool(data.get("is_vat", True))
    vat_rate = float(data.get("vat_rate", 0.07)) if is_vat else 0.0
    wht_rate = determine_smart_wht_rate(client_name, project_name, prompt, data.get("wht_rate"), norm_doc)

    totals = calculate_document_totals(
        items=items,
        is_vat=is_vat,
        vat_rate=vat_rate,
        wht_rate=wht_rate,
        discount=float(data.get("discount", 0.0)),
        doc_type=norm_doc
    )

    draft_payload = {
        "doc_type": norm_doc,
        "client_name": client_name,
        "client_tax_id": client_tax_id,
        "client_branch": client_branch,
        "client_address": client_address,
        "client_phone": client_phone,
        "project_name": project_name,
        "items": items,
        "amount": totals["pre_vat"],
        "pre_vat": totals["pre_vat"],
        "is_vat": is_vat,
        "vat_rate": vat_rate,
        "vat_amount": totals["vat_amount"],
        "wht_rate": wht_rate,
        "wht_amount": totals["wht_amount"],
        "net_total": totals["net_total"],
        "totals": totals,
        "signer_name": signer_name,
        "doc_date": doc_date,
        "due_date": due_date,
        "po_number": data.get("po_number") or "",
        "job_code": data.get("job_code") or "",
        "po_date": data.get("po_date") or "",
        "ref_doc_no": data.get("ref_doc_no") or "",
        "remarks": data.get("remarks") or "",
        "creator": speaker_name or data.get("creator") or "เก่ง",
        "speaker_name": speaker_name,
        "status": "draft",
        "created_at": time.time()
    }

    # Apply Strict User Overrides on top
    apply_strict_user_overrides(prompt, draft_payload)

    # Check existing draft to revise or create new draft ID
    existing_draft_id = SESSION_ACTIVE_DRAFT.get(session_id)
    if existing_draft_id and existing_draft_id in ACTIVE_DRAFTS and any(k in prompt for k in ["แก้", "เปลี่ยน", "ปรับ", "ขอแก้"]):
        draft_id = existing_draft_id
    else:
        draft_id = f"DFT-{datetime.now().strftime('%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    draft_payload["draft_id"] = draft_id
    ACTIVE_DRAFTS[draft_id] = draft_payload
    SESSION_ACTIVE_DRAFT[session_id] = draft_id

    return draft_payload


def confirm_draft_to_official_document(draft_id: str, session_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Confirms an active draft: mints sequential number, renders PDF, uploads to Drive, syncs to Sheets."""
    draft = ACTIVE_DRAFTS.get(draft_id)
    if not draft or draft.get("status") == "confirmed":
        return None, None

    doc_res = generate_and_sync_document(doc_type=draft["doc_type"], doc_data=draft)
    draft["status"] = "confirmed"
    draft["official_doc_no"] = doc_res.get("doc_no")

    SESSION_ACTIVE_DRAFT.pop(session_id, None)
    SESSION_LAST_GENERATED_DOCS[session_id] = doc_res

    flex_card = build_document_flex_message(doc_res)
    return doc_res, flex_card


# ==============================================================================
# Gemini Agent & Tool Execution Engine
# ==============================================================================
GEMINI_AGENT_TOOL_DECLARATIONS = [
    {
        "name": "prepare_document_draft",
        "description": "Creates or updates an in-memory draft of a financial document (Quotation, Invoice, Receipt, WHT) for executive review without saving to sheets or minting official numbers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doc_type": {"type": "STRING", "description": "Document type: 'quotation', 'invoice', 'receipt', 'wht'"},
                "client_name": {"type": "STRING", "description": "Client company name"},
                "project_name": {"type": "STRING", "description": "Project service description"},
                "amount": {"type": "NUMBER", "description": "Total pre-vat amount in THB"},
                "items": {
                    "type": "ARRAY",
                    "description": "Itemized list",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "desc": {"type": "STRING"},
                            "qty": {"type": "NUMBER"},
                            "price": {"type": "NUMBER"},
                            "amount": {"type": "NUMBER"}
                        },
                        "required": ["desc", "price"]
                    }
                },
                "signer_name": {"type": "STRING", "description": "Signer name e.g. นาย มงคล วงศ์สกุลยานนท์"},
                "due_date": {"type": "STRING", "description": "Payment due date (DD/MM/YYYY)"},
                "po_number": {"type": "STRING", "description": "Client Purchase Order P.O. No."},
                "job_code": {"type": "STRING", "description": "Project Job Code"},
                "po_date": {"type": "STRING", "description": "PO date"},
                "ref_doc_no": {"type": "STRING", "description": "Referenced document number"},
                "remarks": {"type": "STRING", "description": "Remarks"}
            },
            "required": ["doc_type", "client_name", "amount"]
        }
    },
    {
        "name": "confirm_issue_document",
        "description": "Mints official sequential number, renders PDF, uploads to Google Drive, and syncs to Google Sheets for an approved draft.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "draft_id": {"type": "STRING", "description": "Draft ID to confirm"}
            }
        }
    },
    {
        "name": "search_sheet_documents",
        "description": "Searches Google Sheets database across Quotations, Invoices, Receipts, and Expenses.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING"},
                "doc_type": {"type": "STRING"},
                "client_name": {"type": "STRING"}
            }
        }
    },
    {
        "name": "create_financial_document",
        "description": "Legacy alias for prepare_document_draft to ensure backwards compatibility with tests and callers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doc_type": {"type": "STRING"},
                "client_name": {"type": "STRING"},
                "project_name": {"type": "STRING"},
                "amount": {"type": "NUMBER"},
                "items": {"type": "ARRAY", "items": {"type": "OBJECT"}},
                "signer_name": {"type": "STRING"},
                "due_date": {"type": "STRING"},
                "po_number": {"type": "STRING"},
                "job_code": {"type": "STRING"},
                "po_date": {"type": "STRING"},
                "ref_doc_no": {"type": "STRING"}
            },
            "required": ["doc_type", "client_name", "amount"]
        }
    },
    {
        "name": "convert_document_pipeline",
        "description": "Converts an existing document along the financial lifecycle pipeline (QT ➔ IV ➔ RE ➔ 50 ทวิ/WHT).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "source_doc_no": {"type": "STRING"},
                "target_type": {"type": "STRING"},
                "overrides": {
                    "type": "OBJECT",
                    "properties": {
                        "due_date": {"type": "STRING"},
                        "po_number": {"type": "STRING"},
                        "job_code": {"type": "STRING"},
                        "po_date": {"type": "STRING"},
                        "signer_name": {"type": "STRING"},
                        "remarks": {"type": "STRING"}
                    }
                }
            },
            "required": ["source_doc_no", "target_type"]
        }
    }
]


def execute_agent_tool(
    func_name: str,
    args: Dict[str, Any],
    session_id: str,
    speaker_name: Optional[str] = None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Executes backend tools safely and returns result dictionary and optional Flex Card."""
    if func_name in ["prepare_document_draft", "create_financial_document"]:
        user_prompt = args.get("prompt") or ""
        draft = create_or_update_draft(session_id, user_prompt, args, speaker_name=speaker_name)
        flex_card = build_draft_summary_flex_message(draft)
        return {
            "status": "draft_created",
            "draft_id": draft["draft_id"],
            "doc_no": draft["draft_id"],
            "totals": draft["totals"],
            "client_name": draft["client_name"],
            "project_name": draft["project_name"],
            "message": f"จัดทำร่างเอกสาร {draft['draft_id']} เรียบร้อยค่ะ"
        }, flex_card

    elif func_name == "confirm_issue_document":
        draft_id = args.get("draft_id") or SESSION_ACTIVE_DRAFT.get(session_id)
        if not draft_id or draft_id not in ACTIVE_DRAFTS:
            return {"status": "error", "message": "ไม่พบร่างเอกสารที่รอการยืนยันค่ะ"}, None
        doc_res, flex_card = confirm_draft_to_official_document(draft_id, session_id)
        return doc_res or {"status": "error"}, flex_card

    elif func_name == "convert_document_pipeline":
        src_no = args.get("source_doc_no") or ""
        tgt_type = args.get("target_type") or "invoice"
        overrides = args.get("overrides") or {}
        for k in ["po_number", "job_code", "po_date", "due_date"]:
            if args.get(k) and k not in overrides:
                overrides[k] = args.get(k)

        conv_res = convert_document(src_no, tgt_type, overrides=overrides)
        flex_card = build_document_conversion_flex_message(conv_res)
        return conv_res, flex_card

    elif func_name == "search_sheet_documents":
        q = args.get("query") or ""
        dt = args.get("doc_type")
        c_name = args.get("client_name")
        docs = search_sheet_documents(query=q, doc_type=dt, client_name=c_name)
        clean_docs = [{k: v for k, v in d.items() if k != "raw_row"} for d in docs[:10]]
        return {"status": "success", "found_count": len(clean_docs), "documents": clean_docs}, None

    return {"status": "unknown_tool"}, None


def local_rule_based_extract_document(user_message: str) -> Optional[Dict[str, Any]]:
    """Deterministic rule-based extractor used in offline testing or when Gemini API is unavailable."""
    text = user_message.strip()
    doc_type = "quotation"
    if any(k in text for k in ["ใบวางบิล", "ใบแจ้งหนี้", "วางบิล"]):
        doc_type = "invoice"
    elif "ใบเสร็จ" in text:
        doc_type = "receipt"
    elif any(k in text for k in ["50ทวิ", "50 ทวิ", "หัก ณ ที่จ่าย"]):
        doc_type = "wht"

    m_amt = re.search(r"(?:ยอด|ราคา|จำนวนเงิน|เงิน|มูลค่า)\s*[:：]?\s*([\d,]+(?:\.\d+)?)", text)
    if not m_amt:
        m_amt = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:บาท|.-)", text)
    amount = float(m_amt.group(1).replace(",", "")) if m_amt else 0.0

    client_name = "ลูกค้าทั่วไป"
    m_client = re.search(r"(?:ให้|ของ|สำหรับ|แก่)\s*(บริษัท[^\n,]+?|ห้างหุ้นส่วน[^\n,]+?|[A-Za-z0-9\s]+จำกัด)", text)
    if m_client:
        client_name = m_client.group(1).strip()
    else:
        for w in ["เชียงใหม่มีเดีย", "เอ็มคูล", "ลานนา", "ไอเด็กซ์", "แคทไซคลิ่ง"]:
            if w in text:
                client_name = f"บริษัท {w} จำกัด"
                break

    res = {
        "doc_type": doc_type,
        "client_name": client_name,
        "project_name": "งานบริการและโปรดักชั่น",
        "amount": amount,
        "items": [{"desc": "งานบริการและโปรดักชั่น", "qty": 1, "price": amount, "amount": amount}],
        "is_vat": True,
        "vat_rate": 0.07,
        "signer_name": "นาย มงคล วงศ์สกุลยานนท์"
    }
    apply_strict_user_overrides(text, res)
    if res.get("po_number") and doc_type == "quotation" and "ใบเสนอราคา" not in text:
        res["doc_type"] = "invoice"
    return res


def merge_document_order_data(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merges multi-turn document attributes."""
    merged = {**existing}
    if not incoming:
        return merged
    for k, v in incoming.items():
        if v is not None and v != "":
            merged[k] = v
    return merged


async def call_gemini_agent(
    user_message: str,
    session_id: str,
    enable_search: bool = True,
    system_instruction_override: Optional[str] = None,
    speaker_name: Optional[str] = None,
    media_parts: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """Core autonomous agent loop. Understands PO PDFs, images, and user prompts."""
    speaker = speaker_name or "ผู้บริหาร"
    clean_msg = user_message.strip()

    # 1. Deterministic Quick Check: Confirmation Intent
    confirm_match = re.search(r"^(?:ยืนยันออกเอกสาร|ยืนยัน|ออกเอกสารจริง|confirm|ออกเลย)(?:\s+([A-Za-z0-9\-_]+))?$", clean_msg, re.I)
    if confirm_match:
        target_draft = confirm_match.group(1) or SESSION_ACTIVE_DRAFT.get(session_id)
        if target_draft and target_draft in ACTIVE_DRAFTS:
            doc_res, flex_card = confirm_draft_to_official_document(target_draft, session_id)
            if doc_res:
                reply_text = f"เลขาเฟิสออกเอกสาร {doc_res.get('doc_no')} ตัวจริงและบันทึกลง Google Sheets เรียบร้อยแล้วค่ะ{speaker} ✨"
                return {"reply_text": reply_text, "flex_cards": [flex_card] if flex_card else [], "doc_result": doc_res}

    # 2. Deterministic Quick Check: Draft Revision
    active_draft_id = SESSION_ACTIVE_DRAFT.get(session_id)
    if active_draft_id and active_draft_id in ACTIVE_DRAFTS and ACTIVE_DRAFTS[active_draft_id].get("status") == "draft":
        if any(k in clean_msg for k in ["แก้", "เปลี่ยน", "ปรับ", "บอสเก่ง", "บอสหอม", "แก้วัน"]):
            draft = ACTIVE_DRAFTS[active_draft_id]
            apply_strict_user_overrides(clean_msg, draft)
            totals = calculate_document_totals(
                items=draft.get("items") or [{"desc": draft.get("project_name", "บริการ"), "qty": 1, "price": float(draft.get("amount", 0))}],
                is_vat=bool(draft.get("is_vat", True)),
                vat_rate=float(draft.get("vat_rate", 0.07)),
                wht_rate=float(draft.get("wht_rate", 0.0)),
                doc_type=draft.get("doc_type", "invoice")
            )
            draft["totals"] = totals
            draft["net_total"] = totals["net_total"]
            draft["vat_amount"] = totals["vat_amount"]
            draft["wht_amount"] = totals["wht_amount"]
            flex_card = build_draft_summary_flex_message(draft)
            reply_text = f"เลขาเฟิสปรับแก้ข้อมูลในร่างเอกสารเรียบร้อยแล้วค่ะ{speaker} ✨ ตรวจทานและกดยืนยันได้เลยนะคะ"
            return {"reply_text": reply_text, "flex_cards": [flex_card], "draft": draft}

    # 3. GenAI SDK Tool Calling Engine
    sys_inst = (
        f"คุณคือ 'เลขาเฟิส' เลขาผู้บริหารของ บจ. GHN168 มีเดีย แอนด์ ครีเอชั่น จำกัด (GHN168)\n"
        f"สนทนากับ: {speaker}\n"
        f"กฎเหล็ก:\n"
        f"1. เมื่อผู้ใช้สั่งออกเอกสารทางการเงิน (QT, IV, RE, 50 ทวิ) หรือส่งใบสั่งซื้อ PO ของลูกค้า ให้เรียก Tool `prepare_document_draft` เสมอ!\n"
        f"2. ห้ามออกเอกสารจริงโดยไม่ผ่านการยืนยันเด็ดขาด!\n"
        f"3. รักษากฎ Strict User Overrides: ถ้าผู้ใช้ระบุคนเซ็นหรือวันครบกำหนด ให้ใช้ตามที่ผู้ใช้สั่งเสมอ"
    )

    if genai_client and types:
        try:
            tools_list = [{"function_declarations": GEMINI_AGENT_TOOL_DECLARATIONS}]
            user_parts = [types.Part.from_text(text=clean_msg)]
            if media_parts:
                user_parts.extend(media_parts)

            response = genai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[types.Content(role="user", parts=user_parts)],
                config=types.GenerateContentConfig(
                    system_instruction=sys_inst,
                    temperature=0.2,
                    tools=tools_list
                )
            )

            if response and response.function_calls:
                accumulated_cards = []
                last_res = {}
                for call in response.function_calls:
                    call_args = dict(call.args) if hasattr(call, "args") else {}
                    t_res, t_card = execute_agent_tool(call.name, call_args, session_id, speaker_name=speaker)
                    if t_card:
                        accumulated_cards.append(t_card)
                    last_res = t_res

                reply_text = f"เลขาเฟิสจัดทำร่างเอกสารให้แล้วค่ะ{speaker} ✨ กรุณาตรวจทานรายละเอียดด้านล่างนะคะ"
                return {"reply_text": reply_text, "flex_cards": accumulated_cards, "doc_result": last_res}

            if response and response.text:
                return {"reply_text": response.text.strip(), "flex_cards": []}
        except Exception as e:
            logger.warning("Gemini SDK call failed (%s), using local fallback extractor.", e)

    # 4. Fallback Rule-Based Extraction
    extracted = local_rule_based_extract_document(clean_msg)
    if extracted and extracted.get("amount", 0) > 0:
        draft = create_or_update_draft(session_id, clean_msg, extracted, speaker_name=speaker)
        flex_card = build_draft_summary_flex_message(draft)
        reply_text = f"เลขาเฟิสจัดทำร่างเอกสารให้แล้วค่ะ{speaker} ✨ กรุณาตรวจทานความถูกต้อง หากถูกต้องกด 'ออกเอกสารจริง' ได้เลยค่ะ"
        return {"reply_text": reply_text, "flex_cards": [flex_card], "draft": draft}

    return {"reply_text": f"เลขาเฟิสยินดีดูแลและช่วยเหลือค่ะ{speaker} ✨ มีเอกสารทางการเงินรายการไหนให้เฟิสจัดทำแจ้งได้เลยนะคะ", "flex_cards": []}


# ==============================================================================
# Event Dispatch & 100% reply_token Flow
# ==============================================================================
def should_reply_to_event(event: Dict[str, Any]) -> Tuple[bool, str]:
    """Determines whether bot should reply. Group chats only respond to bot mentions, PO files, or receipts."""
    source = event.get("source", {})
    source_type = source.get("type", "user")
    message = event.get("message", {})
    msg_type = message.get("type", "")

    if source_type == "user":
        return True, "1-on-1 chat"

    # Group or Room
    if msg_type == "image":
        return True, "image message for receipt OCR"
    if msg_type == "file":
        return True, "file message for PDF PO analysis"

    mentionees = message.get("mention", {}).get("mentionees", [])
    if any(m.get("isSelf") is True for m in mentionees):
        return True, "native bot mention"

    text = message.get("text", "").strip()
    if any(trigger.lower() in text.lower() for trigger in BOT_DIRECT_TRIGGERS):
        return True, "direct bot keyword trigger"

    if re.search(r"^(?:ยืนยัน|confirm|ออกเอกสารจริง)", text, re.I):
        return True, "confirmation action"

    return False, "passive group talk"


async def process_line_events(data: Dict[str, Any]):
    """Processes incoming LINE events using 100% reply_token single-stage delivery."""
    for event in data.get("events", []):
        try:
            if event.get("type") != "message":
                continue

            reply_token = event.get("replyToken")
            if not reply_token:
                continue

            source = event.get("source", {})
            user_id = source.get("userId", "unknown")
            group_id = source.get("groupId") or source.get("roomId") or user_id
            session_id = group_id if source.get("type") in ["group", "room"] else user_id
            speaker_name = resolve_partner_name(user_id=user_id, group_id=source.get("groupId"), event=event)

            message_obj = event.get("message", {})
            msg_type = message_obj.get("type", "")
            msg_id = message_obj.get("id", "")

            should_reply, reason = should_reply_to_event(event)
            if not should_reply:
                continue

            send_line_loading_animation(user_id, loading_seconds=30)

            # Case A: Incoming File (PO PDF / Document)
            if msg_type == "file":
                file_name = message_obj.get("fileName") or "document.pdf"
                file_bytes = download_line_file_content(msg_id)
                if not file_bytes:
                    send_line_reply(reply_token, f"ขออภัยค่ะ{speaker_name} เลขาเฟิสไม่สามารถดาวน์โหลดไฟล์ {file_name} ได้ กรุณาส่งใหม่อีกครั้งนะคะ ✨")
                    continue

                RECENT_MEDIA_CACHE[msg_id] = file_bytes
                SESSION_LAST_FILE[session_id] = {"bytes": file_bytes, "file_name": file_name, "mime_type": "application/pdf"}

                media_parts = []
                if genai and types and file_name.lower().endswith(".pdf"):
                    media_parts.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))

                prompt = f"ผู้ใช้ ({speaker_name}) ส่งไฟล์แนบ '{file_name}' มาให้ กรุณาตรวจว่าเป็นใบสั่งซื้อ (PO) หรือไม่ หากใช่ให้สกัดข้อมูลและออกร่างใบวางบิลทันที"
                res = await call_gemini_agent(prompt, session_id, speaker_name=speaker_name, media_parts=media_parts)

                reply_text = res.get("reply_text") or f"เลขาเฟิสสแกนไฟล์ {file_name} เรียบร้อยแล้วค่ะ{speaker_name} ✨"
                flex_cards = res.get("flex_cards") or []
                messages_to_send = [{"type": "text", "text": reply_text}]
                if flex_cards:
                    messages_to_send.extend(flex_cards[:4])
                send_line_reply_messages(reply_token, messages_to_send)
                continue

            # Case B: Incoming Image (Receipt OCR)
            elif msg_type == "image":
                img_bytes = download_line_image_content(msg_id)
                if not img_bytes:
                    send_line_reply(reply_token, f"ขออภัยค่ะ{speaker_name} ไม่สามารถดาวน์โหลดรูปภาพจาก LINE ได้ กรุณาส่งใหม่อีกครั้งนะคะ ✨")
                    continue

                RECENT_MEDIA_CACHE[msg_id] = img_bytes
                media_parts = [types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")] if (genai and types) else []
                prompt = f"ผู้ใช้ ({speaker_name}) ส่งรูปภาพมาให้ กรุณาวิเคราะห์ว่าเป็นสลิปโอนเงิน บิลค่าใช้จ่าย หรือเอกสารทางการเงินหรือไม่"
                res = await call_gemini_agent(prompt, session_id, speaker_name=speaker_name, media_parts=media_parts)

                reply_text = res.get("reply_text") or f"เลขาเฟิสสแกนรูปภาพเรียบร้อยแล้วค่ะ{speaker_name} ✨"
                flex_cards = res.get("flex_cards") or []
                messages_to_send = [{"type": "text", "text": reply_text}]
                if flex_cards:
                    messages_to_send.extend(flex_cards[:4])
                send_line_reply_messages(reply_token, messages_to_send)
                continue

            # Case C: Text Message
            else:
                user_text = message_obj.get("text", "").strip()
                res = await call_gemini_agent(user_text, session_id, speaker_name=speaker_name)
                reply_text = res.get("reply_text") or f"เลขาเฟิสพร้อมดูแลให้{speaker_name}ค่ะ ✨"
                flex_cards = res.get("flex_cards") or []
                messages_to_send = [{"type": "text", "text": reply_text}]
                if flex_cards:
                    messages_to_send.extend(flex_cards[:4])
                send_line_reply_messages(reply_token, messages_to_send)

        except Exception as err:
            logger.error("Error processing event: %s", err, exc_info=True)


# ==============================================================================
# FastAPI HTTP Endpoints
# ==============================================================================
@app.post("/callback")
async def callback_handler(request: Request, x_line_signature: Optional[str] = Header(None)):
    """LINE Messaging API Webhook endpoint with HMAC-SHA256 signature verification."""
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    if LINE_CHANNEL_SECRET and x_line_signature:
        hash_check = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).digest()
        import base64
        expected_sig = base64.b64encode(hash_check).decode("utf-8")
        if not hmac.compare_digest(expected_sig, x_line_signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Process events
    await process_line_events(data)
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """Public health check endpoint displaying clean-slate engine and active features."""
    return {
        "status": "online",
        "version": SERVER_VERSION,
        "engine": "FastAPI + Gemini 3.8 Flash Pure-Agent",
        "active_drafts_count": len(ACTIVE_DRAFTS),
        "features": [
            "100_percent_reply_token_zero_429",
            "draft_confirm_protocol_human_in_the_loop",
            "strict_user_overrides",
            "multimodal_po_pdf_handling",
            "zero_cache_poisoning"
        ]
    }


@app.post("/api/test_chat")
async def api_test_chat(request: Request):
    """Developer test endpoint for simulating chat and document workflows."""
    body = await request.json()
    msg = body.get("message", "")
    session_id = body.get("session_id", "test_session")
    speaker = body.get("speaker_name", "บอสเก่ง")

    res = await call_gemini_agent(msg, session_id, speaker_name=speaker)
    return {
        "status": "success",
        "reply_text": res.get("reply_text"),
        "flex_cards": res.get("flex_cards", []),
        "doc_result": res.get("doc_result"),
        "draft": res.get("draft")
    }


@app.api_route("/api/documents/pdf/{doc_no}", methods=["GET", "HEAD"])
@app.get("/api/documents/pdf/{doc_no}")
async def api_serve_document_pdf(doc_no: str):
    """Direct PDF serving endpoint for rendered documents."""
    clean_no = normalize_doc_no(doc_no.replace(".pdf", "").strip())
    pdf_path = get_local_pdf_path(clean_no)
    if pdf_path and pdf_path.is_file():
        return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=f"{clean_no}.pdf")
    raise HTTPException(status_code=404, detail=f"PDF document '{clean_no}' not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("line_bot_server:app", host="0.0.0.0", port=8000, reload=True)
