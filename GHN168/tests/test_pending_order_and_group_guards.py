#!/usr/bin/env python3
"""
================================================================================
Test Suite: LINE Bot Group Chat & Pending Order Guards (Task 3 Verification)
================================================================================
Tests:
1. Pending Document Order Pause Guard ('แป๊บ', 'แปบนึง', 'รอก่อน', 'เดี๋ยว', 'อย่าเพิ่ง')
2. Pending Document Order Cancel Guard ('ยกเลิก', 'cancel')
3. Pending Document Order Correction Guard ('ยอดผิด', 'ไม่ใช่')
4. Explicit Confirmation Enforcement ('ยืนยัน', 'ออกบิล', 'สร้างบิล', 'บันทึก')
5. Group Chat Silent Filter for Member-to-Member chatter & Active Thread Guard
================================================================================
"""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure workspace root is in sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from fastapi.testclient import TestClient
from line_bot_server import (
    app,
    should_reply_to_event,
    should_bot_reply_in_group,
    PENDING_DOCUMENT_ORDERS,
    PENDING_EXPENSE_CONFIRMATIONS,
    ACTIVE_CONVERSATION_THREADS,
    CONVERSATION_HISTORY,
)
from ghn168_sync_service import _CUSTOMERS_CACHE


class TestPendingOrderAndGroupGuards(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_EXPENSE_CONFIRMATIONS.clear()
        ACTIVE_CONVERSATION_THREADS.clear()
        CONVERSATION_HISTORY.clear()
        _CUSTOMERS_CACHE["data"] = None
        _CUSTOMERS_CACHE["timestamp"] = 0.0

        # Patch requests.post to ensure 100% Zero Production Pollution
        self.patcher = patch("requests.post")
        self.mock_post = self.patcher.start()

        def mock_requests_post_handler(url, json=None, **kwargs):
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
                    "pdfUrl": "https://drive.google.com/mock_guard_test_doc.pdf",
                    "message": "Mocked upload success"
                }
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}
            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.patcher.stop()
        _CUSTOMERS_CACHE["data"] = None

    # --------------------------------------------------------------------------
    # 1. Pending Document Order Pause Guard ('แป๊บ', 'แปบนึง', 'รอก่อน', 'เดี๋ยว')
    # --------------------------------------------------------------------------
    def test_pending_order_pause_guard(self):
        """When in pending document flow, pause words must NOT create document."""
        session_id = "test_pending_pause_01"
        PENDING_DOCUMENT_ORDERS[session_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งาน VTR",
            "amount": 50000.0
        }

        pause_words = ["แป๊บ", "แปบนึง", "แป๊บนึง", "รอก่อน", "เดี๋ยว", "อย่าเพิ่ง"]
        for word in pause_words:
            with self.subTest(word=word):
                resp = self.client.post("/api/test_chat", json={
                    "session_id": session_id,
                    "message": word
                })
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertFalse(data.get("is_document_order", False), f"Must NOT create doc on '{word}'")
                self.assertIsNone(data.get("doc_result"), f"doc_result must be None on '{word}'")
                self.assertIn(session_id, PENDING_DOCUMENT_ORDERS, "Pending order must be preserved")
                self.assertIn("พักไว้ก่อน", data["reply"])
                print(f"✅ Pause word '{word}' correctly guarded and acknowledged.")

    # --------------------------------------------------------------------------
    # 2. Pending Document Order Cancel Guard ('ยกเลิก', 'cancel')
    # --------------------------------------------------------------------------
    def test_pending_order_cancel_guard(self):
        """When in pending document flow, cancel words must clear order and NOT create document."""
        session_id = "test_pending_cancel_01"
        PENDING_DOCUMENT_ORDERS[session_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งาน VTR",
            "amount": 50000.0
        }

        resp = self.client.post("/api/test_chat", json={
            "session_id": session_id,
            "message": "ยกเลิก"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("is_document_order", False))
        self.assertIsNone(data.get("doc_result"))
        self.assertNotIn(session_id, PENDING_DOCUMENT_ORDERS, "Pending order must be cleared")
        self.assertIn("ยกเลิก", data["reply"])
        print("✅ Cancel guard correctly cleared pending order without doc creation.")

    # --------------------------------------------------------------------------
    # 3. Pending Document Order Correction Guard ('ยอดผิด', 'ไม่ใช่')
    # --------------------------------------------------------------------------
    def test_pending_order_correction_guard(self):
        """When user says 'ยอดผิด' or 'ไม่ใช่', bot asks for details without creating doc."""
        session_id = "test_pending_correction_01"
        PENDING_DOCUMENT_ORDERS[session_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งาน VTR",
            "amount": 50000.0
        }

        resp = self.client.post("/api/test_chat", json={
            "session_id": session_id,
            "message": "ยอดผิด"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("is_document_order", False))
        self.assertIsNone(data.get("doc_result"))
        self.assertIn("แก้ไข", data["reply"])
        print("✅ Correction word correctly prompted for updated details.")

    # --------------------------------------------------------------------------
    # 4. Explicit Confirmation Requirement ('ยืนยัน', 'ออกบิล', 'สร้างบิล', 'บันทึก')
    # --------------------------------------------------------------------------
    def test_pending_order_explicit_confirmation(self):
        """Pending complete draft requires explicit confirmation keyword to generate document."""
        session_id = "test_pending_confirm_01"
        PENDING_DOCUMENT_ORDERS[session_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งานถ่ายคลิปโปรโมท",
            "amount": 30000.0
        }

        # Step 1: User says 'ยืนยัน'
        resp = self.client.post("/api/test_chat", json={
            "session_id": session_id,
            "message": "ยืนยัน"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_document_order"))
        self.assertIsNotNone(data.get("doc_result"))
        self.assertEqual(data["doc_result"]["client_name"], "บริษัท เชียงใหม่มีเดีย จำกัด")
        self.assertNotIn(session_id, PENDING_DOCUMENT_ORDERS)
        print("✅ Explicit confirmation 'ยืนยัน' correctly finalized and generated document.")

    # --------------------------------------------------------------------------
    # 5. Group Chat Silent Filter for Member-to-Member chatter & Active Thread Guard
    # --------------------------------------------------------------------------
    def test_group_chat_chatter_silent_filter(self):
        """Bot must stay completely silent on member-to-member chatter in groups."""
        group_id = "C_group_test_guard"
        chatter_texts = [
            "55555+",
            "กินข้าวไหนดี",
            "ไปกินเตี๋ยวกัน",
            "คืนนี้ตี้ rov ปะ",
            "นอนละนะ ฝันดี",
            "ไปไหนกันดี",
            "บายๆ"
        ]
        for txt in chatter_texts:
            with self.subTest(text=txt):
                event = {
                    "replyToken": "dummy_token",
                    "type": "message",
                    "source": {"type": "group", "groupId": group_id, "userId": "U_user_001"},
                    "message": {"type": "text", "text": txt}
                }
                should_reply, reason = should_bot_reply_in_group(event)
                self.assertFalse(should_reply, f"Bot should be SILENT for '{txt}' in group")

    def test_group_chat_active_thread_guard(self):
        """During active thread in group, casual chatter must NOT trigger bot, only work commands."""
        group_id = "C_group_active_thread"
        user_id = "U_user_active_01"

        # Set active thread
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": user_id,
            "expires_at": time.time() + 90
        }

        # 1. Casual banter in active thread -> SILENT
        event_banter = {
            "replyToken": "dummy_token",
            "type": "message",
            "source": {"type": "group", "groupId": group_id, "userId": user_id},
            "message": {"type": "text", "text": "กินข้าวเที่ยงยัง"}
        }
        should_reply1, _ = should_bot_reply_in_group(event_banter)
        self.assertFalse(should_reply1, "Casual banter in active thread must be SILENT")

        # 2. Work context in active thread -> REPLIES
        event_work = {
            "replyToken": "dummy_token",
            "type": "message",
            "source": {"type": "group", "groupId": group_id, "userId": user_id},
            "message": {"type": "text", "text": "เช็คคิวงานวันพรุ่งนี้"}
        }
        should_reply2, reason2 = should_bot_reply_in_group(event_work)
        self.assertTrue(should_reply2, f"Work context in active thread should reply: {reason2}")
        print("✅ Group chat active thread guard correctly separated chatter from work commands.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
