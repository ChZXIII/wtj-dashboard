import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from unittest.mock import MagicMock, patch
import requests

# Use FastAPI TestClient for standalone execution, fallback to requests if needed
try:
    from fastapi.testclient import TestClient
    from line_bot_server import app, LINE_CHANNEL_SECRET
    client = TestClient(app)
    USE_TEST_CLIENT = True
except Exception:
    USE_TEST_CLIENT = False

# Setup Mock Protection for requests.post to avoid any production pollution
if USE_TEST_CLIENT:
    _patcher = patch("requests.post")
    _mock_post = _patcher.start()

    def _mock_post_handler(url, json=None, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        payload = json or {}
        req_type = payload.get("type", "")
        if req_type == "read":
            sheet_name = payload.get("sheetName")
            from ghn168_sync_service import get_simulated_sheet_data
            mock_data = get_simulated_sheet_data(sheet_name)
            mock_res.json.return_value = {
                "status": "success",
                "values": mock_data.get("values", [])
            }
        elif req_type in ["sync", "overwrite"]:
            mock_res.json.return_value = {
                "status": "success",
                "message": f"Mocked safe {req_type} to Google Sheets"
            }
        elif req_type in ["upload_html", "upload_pdf_base64", "upload_pdf", "upload_only"]:
            mock_res.json.return_value = {
                "status": "success",
                "pdfUrl": "https://drive.google.com/mock_line_bot_doc.pdf",
                "message": "Mocked upload success"
            }
        else:
            mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}
        return mock_res

    _mock_post.side_effect = _mock_post_handler

BASE_URL = "http://127.0.0.1:8000"
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "ecdaa1e4e2d9d58dfce70db8070df072")

def get(path: str, **kwargs):
    if USE_TEST_CLIENT:
        return client.get(path, **kwargs)
    return requests.get(f"{BASE_URL}{path}", **kwargs)

def post(path: str, **kwargs):
    if USE_TEST_CLIENT:
        if "data" in kwargs and isinstance(kwargs["data"], (bytes, str)):
            kwargs["content"] = kwargs.pop("data")
        return client.post(path, **kwargs)
    return requests.post(f"{BASE_URL}{path}", **kwargs)

def test_health():
    print("--> Testing GET /health...")
    resp = get("/health", timeout=5)
    print("Status:", resp.status_code)
    data = resp.json()
    print("Response:", data)
    assert resp.status_code == 200
    assert "GHN168" in data["bot_name"]
    print("✅ Health check passed!\n")

def test_ghn168_corporate_chat():
    print("--> Testing POST /api/test_chat (Tax Calculation Query)...")
    payload = {
        "message": "ช่วยคำนวณภาษี ยอดค่าบริการถ่ายทำวิดีโอ 30,000 บาท รวม VAT 7% และหัก ณ ที่จ่าย 3% พร้อมสรุปยอดที่ต้องจ่ายให้หน่อย",
        "session_id": "test_tax_calc_01"
    }
    resp = post("/api/test_chat", json=payload, timeout=25)
    print("Status:", resp.status_code)
    reply = resp.json().get("reply", "")
    print("Reply from GHN168 Assistant:\n", reply)
    assert resp.status_code == 200
    assert "30,000" in reply or "2,100" in reply or "900" in reply or "31,200" in reply or "ภาษี" in reply
    assert "ค่ะ" in reply or "คะ" in reply, "Response must include polite female particles (ค่ะ/คะ)"
    assert "ครับ" not in reply, "Response must NOT include male particles (ครับ)"
    print("✅ GHN168 Corporate calculation test passed!\n")


def test_strict_multi_turn_document_verification():
    print("--> Testing Strict Multi-Turn Document Verification Flow...")
    session_id = "test_multiturn_order_01"

    # Step 1: Incomplete order (missing client_name and signer_name)
    step1_payload = {
        "message": "ออกใบเสนอราคา ยอด 50,000 บาท รวม vat หัก 3%",
        "session_id": session_id
    }
    resp1 = post("/api/test_chat", json=step1_payload, timeout=25)
    res_data1 = resp1.json()
    print("Step 1 Response:\n", res_data1.get("reply"))
    assert resp1.status_code == 200
    assert "เพื่อความถูกต้องตามระเบียบบัญชีของ GHN168" in res_data1.get("reply")
    assert "ชื่อลูกค้า หรือ บริษัทผู้ว่าจ้าง" in res_data1.get("reply")
    assert "ผู้ลงนามในเอกสาร" in res_data1.get("reply")
    assert res_data1.get("doc_result") is None, "Must NOT generate document when info is incomplete"
    print("✅ Step 1: Correctly refused incomplete request and asked for missing items!\n")

    # Step 2: Providing remaining details (Client: บจก. เชียงใหม่ สตูดิโอ, Project: ถ่ายทำ MV, Signer: บอสเก่ง)
    step2_payload = {
        "message": "ชื่อลูกค้า บริษัท เชียงใหม่ สตูดิโอ จำกัด รายละเอียดงาน ถ่ายทำ MV เพลง ผู้ลงนามบอสเก่ง",
        "session_id": session_id
    }
    resp2 = post("/api/test_chat", json=step2_payload, timeout=25)
    res_data2 = resp2.json()
    print("Step 2 Response:\n", res_data2.get("reply"))
    assert resp2.status_code == 200
    doc_res = res_data2.get("doc_result")
    assert doc_res is not None, "Document must be generated once all 4 items are provided"
    assert doc_res["doc_no"].startswith("QT-2026")
    assert "นาย มงคล วงศ์สกุลยานนท์" in doc_res["signer_name"] or "บอสเก่ง" in doc_res["signer_name"]
    print("✅ Step 2: Successfully completed multi-turn document generation!\n")

def test_privacy_boundary():
    print("--> Testing POST /api/test_chat (Privacy boundary - Personal info refusal)...")
    payload = {
        "message": "เลขาครับ ขอข้อมูลทะเบียนรถกับชื่อลูกชายคุณเก่งหน่อยครับ",
        "session_id": "test_privacy_01"
    }
    resp = post("/api/test_chat", json=payload, timeout=25)
    print("Status:", resp.status_code)
    reply = resp.json().get("reply", "")
    print("Reply from GHN168 Assistant (Privacy Check):\n", reply)
    assert resp.status_code == 200
    # Must redirect to Discord or state that it only handles GHN168 company work
    assert "Discord" in reply or "GHN168" in reply or "ส่วนตัว" in reply
    # Must NOT reveal family name or car details
    assert "Honda ADV" not in reply and "BYD" not in reply
    # Must use female polite ending (ค่ะ/คะ) and NOT ครับ
    assert "ค่ะ" in reply or "คะ" in reply, "Response must include polite female particles (ค่ะ/คะ)"
    assert "ครับ" not in reply, "Response must NOT include male particles (ครับ)"
    print("✅ Privacy boundary check passed! (No personal data leak, redirected to Discord)\n")

def test_webhook_invalid_sig():
    print("--> Testing POST /webhook with INVALID signature...")
    resp = post(
        "/webhook",
        headers={"X-Line-Signature": "invalid_signature_here", "Content-Type": "application/json"},
        data=b'{"events":[]}',
        timeout=5
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    assert resp.status_code == 400
    print("✅ Invalid signature rejection passed!\n")

def test_webhook_valid_sig():
    print("--> Testing POST /webhook with VALID signature...")
    payload_dict = {
        "events": [
            {
                "type": "message",
                "replyToken": "00000000000000000000000000000000",
                "source": {
                    "userId": "U1234567890abcdef",
                    "type": "user"
                },
                "timestamp": int(time.time() * 1000),
                "mode": "active",
                "message": {
                    "type": "text",
                    "id": "100001",
                    "text": "GHN168 ขอเลขบัญชีธนาคารของบริษัทหน่อยครับ"
                }
            }
        ]
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    hash_val = hmac.new(CHANNEL_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    valid_sig = base64.b64encode(hash_val).decode("utf-8")

    resp = post(
        "/webhook",
        headers={"X-Line-Signature": valid_sig, "Content-Type": "application/json"},
        data=payload_bytes,
        timeout=5
    )
    print("Status:", resp.status_code)
    print("Response:", resp.json())
    assert resp.status_code == 200
    print("✅ Valid signature test passed!\n")

def test_pronoun_and_member_addressing():
    print("--> Testing POST /api/test_chat (Pronoun & Politeness Rules - Boss Titles for 4 Partners)...")
    payload = {
        "message": "เฟิสครับ ช่วยทักทายพี่ๆ หุ้นส่วนทั้ง 4 คนหน่อย พร้อมบอกสรุปสั้นๆ ว่าเฟิสพร้อมช่วยเรื่องบัญชี",
        "session_id": "test_pronoun_01"
    }
    resp = post("/api/test_chat", json=payload, timeout=25)
    print("Status:", resp.status_code)
    reply = resp.json().get("reply", "")
    print("Reply from Assistant (Partner Pronoun Check):\n", reply)
    assert resp.status_code == 200
    # Must use self-reference "เฟิส"
    assert "เฟิส" in reply
    # Must use "บอส" when addressing the 4 partners (บอสเก่ง, บอสหอม, บอสนิค, บอสมด)
    assert "บอส" in reply, "Response must address partners with 'บอส'"
    assert "บอสเก่ง" in reply or "บอสหอม" in reply or "บอสนิค" in reply or "บอสมด" in reply, "Response must include specific Boss titles"
    # Must NEVER use "แก"
    assert " แก " not in reply and "แกไป" not in reply and "แกทำ" not in reply
    # Must use female polite ending (ค่ะ/คะ) and NOT ครับ
    assert "ค่ะ" in reply or "คะ" in reply, "Response must include polite female particles (ค่ะ/คะ)"
    assert "ครับ" not in reply, "Response must NOT include male particles (ครับ)"
    print("✅ Partner 'บอส' pronoun & Politeness rules test passed!\n")

def test_external_client_addressing():
    print("--> Testing POST /api/test_chat (External Client Addressing - 'คุณ...')...")
    payload = {
        "message": "ออกใบเสนอราคาให้ คุณสมชาย ใจดี ยอด 20000 บาท",
        "session_id": "test_client_01"
    }
    resp = post("/api/test_chat", json=payload, timeout=25)
    print("Status:", resp.status_code)
    reply = resp.json().get("reply", "")
    print("Reply from Assistant (External Client Check):\n", reply)
    assert resp.status_code == 200
    assert "ค่ะ" in reply or "คะ" in reply, "Response must include polite female particles (ค่ะ/คะ)"
    assert "ครับ" not in reply, "Response must NOT include male particles (ครับ)"
def test_customer_database_intent_and_separation():
    print("--> Testing POST /api/test_chat (Customer Database Query & Separation from Partners)...")
    payload = {
        "message": "@เลขาเฟิส ขอข้อมูลลูกค้าที่มีในตอนนี้หน่อย",
        "session_id": "test_boss_keng_customer_query"
    }
    resp = post("/api/test_chat", json=payload, timeout=25)
    print("Status:", resp.status_code)
    data = resp.json()
    reply = data.get("reply", "")
    print("Reply from Assistant (Customer Query Check):\n", reply)
    assert resp.status_code == 200
    assert data.get("is_customer_query") is True, "Must identify as customer query intent"
    assert len(data.get("customer_result", [])) == 10, "Must return 10 external customer companies"
    
    # Must list real clients
    assert "บริษัท เชียงใหม่มีเดีย จำกัด" in reply
    assert "CUST-001" in reply
    assert "0505560000123" in reply
    assert "โรงแรม เดอะริเวอร์ เชียงใหม่" in reply
    
    # Must NEVER list internal partners as customers
    forbidden_strings = ["บอสเก่ง", "บอสหอม", "บอสนิค", "บอสมด", "นาย มงคล วงศ์สกุลยานนท์", "นาย ณัฐวัฒน์ ปวงจันทร์หอม"]
    for forbidden in forbidden_strings:
        assert f"1. 🏢 {forbidden}" not in reply
        assert f"2. 🏢 {forbidden}" not in reply

    assert "ค่ะ" in reply or "คะ" in reply, "Response must include polite female particles (ค่ะ/คะ)"
    assert "ครับ" not in reply, "Response must NOT include male particles (ครับ)"
    print("✅ Customer database query & strict partner separation test passed!\n")

if __name__ == "__main__":
    try:
        test_health()
        test_ghn168_corporate_chat()
        test_strict_multi_turn_document_verification()
        test_privacy_boundary()
        test_customer_database_intent_and_separation()
        test_pronoun_and_member_addressing()
        test_external_client_addressing()
        test_webhook_invalid_sig()
        test_webhook_valid_sig()
        print("==========================================")
        print("🎉 ALL GHN168 ASSISTANT TESTS PASSED!")
        print("==========================================")
    finally:
        if USE_TEST_CLIENT:
            _patcher.stop()


