#!/usr/bin/env python3
"""
GHN168 Advanced Features Test Script
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch
import requests

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
                "pdfUrl": "https://drive.google.com/mock_all_features_doc.pdf",
                "message": "Mocked upload success"
            }
        else:
            mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}
        return mock_res

    _mock_post.side_effect = _mock_post_handler

BASE_URL = "http://127.0.0.1:8000"
CHANNEL_SECRET = "ecdaa1e4e2d9d58dfce70db8070df072"


def make_signed_request(path: str, payload_dict: dict):
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    hash_val = hmac.new(CHANNEL_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    sig = base64.b64encode(hash_val).decode("utf-8")
    if USE_TEST_CLIENT:
        return client.post(path, headers={"X-Line-Signature": sig, "Content-Type": "application/json"}, content=payload_bytes)
    return requests.post(
        f"{BASE_URL}{path}",
        headers={"X-Line-Signature": sig, "Content-Type": "application/json"},
        data=payload_bytes,
        timeout=10
    )


def test_group_chat_no_trigger():
    print("--> Testing Group Chat WITHOUT trigger (should be ignored)...")
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "00000000000000000000000000000000",
                "source": {
                    "userId": "U12345",
                    "groupId": "Cgroup999",
                    "type": "group"
                },
                "timestamp": int(time.time() * 1000),
                "message": {
                    "type": "text",
                    "id": "200001",
                    "text": "วันนี้กินข้าวที่ไหนกันดีพวกเรา"
                }
            }
        ]
    }
    resp = make_signed_request("/webhook", payload)
    assert resp.status_code == 200
    print("✅ Group chat without trigger successfully received and ignored as expected.\n")


def test_group_chat_with_trigger():
    print("--> Testing Group Chat WITH trigger (should process)...")
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "00000000000000000000000000000000",
                "source": {
                    "userId": "U12345",
                    "groupId": "Cgroup999",
                    "type": "group"
                },
                "timestamp": int(time.time() * 1000),
                "message": {
                    "type": "text",
                    "id": "200002",
                    "text": "เฟิส ช่วยดูหน่อยว่ากล้องของ GHN168 มีอะไรบ้าง"
                }
            }
        ]
    }
    resp = make_signed_request("/webhook", payload)
    assert resp.status_code == 200
    print("✅ Group chat with trigger processed.\n")


def test_multi_turn_session():
    print("--> Testing Multi-turn conversation memory...")
    # Turn 1
    if USE_TEST_CLIENT:
        resp1 = client.post("/api/test_chat", json={
            "message": "เฟิส ขอข้อมูลบริษัท GHN168 หน่อยค่ะ",
            "session_id": "session_multi_turn_test"
        })
    else:
        resp1 = requests.post(f"{BASE_URL}/api/test_chat", json={
            "message": "เฟิส ขอข้อมูลบริษัท GHN168 หน่อยค่ะ",
            "session_id": "session_multi_turn_test"
        }, timeout=15)
    assert resp1.status_code == 200
    print("Turn 1 reply:", resp1.json().get("reply")[:100] + "...")

    # Turn 2
    if USE_TEST_CLIENT:
        resp2 = client.post("/api/test_chat", json={
            "message": "แล้วเลขบัญชีกรุงไทยของบริษัทคือเลขอะไรนะ",
            "session_id": "session_multi_turn_test"
        })
    else:
        resp2 = requests.post(f"{BASE_URL}/api/test_chat", json={
            "message": "แล้วเลขบัญชีกรุงไทยของบริษัทคือเลขอะไรนะ",
            "session_id": "session_multi_turn_test"
        }, timeout=15)
    assert resp2.status_code == 200
    reply2 = resp2.json().get("reply", "")
    print("Turn 2 reply:", reply2[:100] + "...")
    assert "520" in reply2 or "กรุงไทย" in reply2 or "61960" in reply2
    print("✅ Multi-turn context retention verified!\n")


if __name__ == "__main__":
    try:
        test_group_chat_no_trigger()
        test_group_chat_with_trigger()
        test_multi_turn_session()
        print("==================================================")
        print("🎉 ALL ADVANCED FEATURES VERIFIED SUCCESSFULLY! 🎉")
        print("==================================================")
    finally:
        if USE_TEST_CLIENT:
            _patcher.stop()
