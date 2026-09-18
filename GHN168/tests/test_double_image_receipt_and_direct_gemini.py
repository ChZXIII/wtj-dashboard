#!/usr/bin/env python3
"""
================================================================================
Test Suite: Pre-Gemini Interceptor Elimination & Double Image Receipt Generation
================================================================================
Target:
1. line_bot_server.py:
   - Section 2.6 Payment Confirmation Gatekeeper Guard removed.
   - Clean messages route directly into Gemini 3.8 Flash without pre-LLM interception.
2. Boss Hom's request for 'บริษัท ดับเบิล อิมเมจ 2005 จำกัด':
   - Issues official Receipt (RE) directly.
   - Accurately captures customer details, 10,000 THB, VAT 7%, WHT 3%.
   - No Gatekeeper block ("ยังไม่พบเอกสารอ้างอิง").
================================================================================
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
WORKSPACE_DIR = str(Path(__file__).resolve().parent.parent)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import time
import line_bot_server as bot_server
from line_bot_server import (
    call_gemini_agent,
    ghn_memory,
    process_line_events,
    execute_agent_tool,
    PENDING_PAYMENT_CONFIRMATIONS,
    PENDING_DOCUMENT_ORDERS,
    SESSION_LAST_GENERATED_DOCS,
    ACTIVE_CONVERSATION_THREADS,
)


class TestDoubleImageReceiptAndDirectGemini(unittest.TestCase):

    def setUp(self):
        ghn_memory.sessions.clear()
        bot_server.CONVERSATION_HISTORY.clear()
        PENDING_PAYMENT_CONFIRMATIONS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        SESSION_LAST_GENERATED_DOCS.clear()
        ACTIVE_CONVERSATION_THREADS.clear()

    def tearDown(self):
        ghn_memory.sessions.clear()
        bot_server.CONVERSATION_HISTORY.clear()
        PENDING_PAYMENT_CONFIRMATIONS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        SESSION_LAST_GENERATED_DOCS.clear()
        ACTIVE_CONVERSATION_THREADS.clear()

    def test_01_boss_hom_double_image_receipt_generation(self):
        """Verify Boss Hom's message creates a Receipt without Gatekeeper interceptor."""
        user_msg = (
            "@เลขาเฟิส ทำ ใบเสร็จรับเงิน\n"
            "ลงวันที่ 17 กันยายน 2569\n"
            "เสนอ\n"
            "บริษัท ดับเบิล อิมเมจ 2005 จำกัดเลขที่ 58/46 หมู่ 6 ถนนกาญจนาภิเษก ตำบลเสาธงหิน อำเภอบางใหญ่ จังหวัดนนทบุรี 11140\n"
            "เลขที่ผู้เสียภาษี 0-1055-48143-35-1 (สำนักงานใหญ่)\n"
            "โทร.02-9267815-6\n"
            "ชื่องาน แชงกีล่า 12 กันยายน 2569\n"
            "รายละเอียด\n"
            "ถ่าย-ตัด Reel 2 ตัว\n"
            "ยอดรวม 10,000 บาท"
        )
        session_id = "test_boss_hom_double_image_unit"

        # Execute call_gemini_agent
        res = asyncio.run(call_gemini_agent(
            user_message=user_msg,
            session_id=session_id,
            speaker_name="บอสหอม"
        ))

        reply_text = res.get("reply_text", "")
        doc_result = res.get("doc_result")
        executed_tools = [t.get("tool") for t in res.get("executed_tools", [])]

        # 1. Must NOT be blocked by Gatekeeper
        self.assertNotIn("ยังไม่พบเอกสารอ้างอิง", reply_text, "Should NOT blurt 'ยังไม่พบเอกสารอ้างอิง'")
        self.assertNotIn("แจ้งยืนยันยอดเงินรับชำระ", reply_text, "Should NOT trigger Gatekeeper prompt")

        # 2. Must call create_financial_document tool
        self.assertIn("create_financial_document", executed_tools, f"Expected create_financial_document, got {executed_tools}")

        # 3. Must return valid receipt doc_result
        self.assertIsNotNone(doc_result, "doc_result should be populated")
        self.assertEqual(doc_result.get("doc_type"), "receipt")
        self.assertIn("ดับเบิล อิมเมจ", doc_result.get("client_name", ""))
        self.assertEqual(doc_result.get("client_tax_id"), "0105548143351")

        # 4. Totals verification
        totals = doc_result.get("totals", {})
        self.assertIn(float(totals.get("pre_vat", 0)), [10000.0, 9345.79])
        if float(totals.get("pre_vat", 0)) == 10000.0:
            self.assertEqual(float(totals.get("vat_amount", 0)), 700.0)
            self.assertEqual(float(totals.get("gross_amount", 0)), 10700.0)
            self.assertEqual(float(totals.get("wht_amount", 0)), 300.0)
            self.assertEqual(float(totals.get("net_total", 0)), 10400.0)
        else:
            self.assertAlmostEqual(float(totals.get("gross_amount", 0)), 10000.0, places=1)

        # 5. Session state: no pending gatekeeper stuck
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        print("\n✅ Test 1: Boss Hom's Double Image Receipt generated directly via Gemini 3.8 Flash!")

    def test_02_no_pre_gemini_interceptor_on_clean_messages(self):
        """Verify new messages without pending state never get caught by Gatekeeper in call_gemini_agent."""
        session_id = "test_clean_interceptor_check"
        msg = "ทำใบเสร็จรับเงิน ค่าบริการถ่ายทำ 15,000 บาท"

        # Mock Gemini to return a basic response rather than calling external network
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="รับทราบค่ะบอสเก่ง เลขาเฟิสช่วยดูแลให้อย่างดีนะคะ ✨", function_call=None)]
        mock_response.text = "รับทราบค่ะบอสเก่ง เลขาเฟิสช่วยดูแลให้อย่างดีนะคะ ✨"

        with patch.object(bot_server.genai_client.models, "generate_content", return_value=mock_response) as mock_gen:
            res = asyncio.run(call_gemini_agent(
                user_message=msg,
                session_id=session_id,
                speaker_name="บอสเก่ง"
            ))

            # Must have reached generate_content directly without being intercepted
            self.assertTrue(mock_gen.called, "clean message must route directly into genai_client.models.generate_content")
            self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        print("✅ Test 2: Clean messages route directly into generate_content without interceptor!")

    def test_03_webhook_event_processing_for_boss_hom(self):
        """Verify full process_line_events flow handles Boss Hom's receipt without errors."""
        session_id = "test_webhook_double_image_group"
        user_msg = (
            "@เลขาเฟิส ทำ ใบเสร็จรับเงิน\n"
            "ลงวันที่ 17 กันยายน 2569\n"
            "เสนอ\n"
            "บริษัท ดับเบิล อิมเมจ 2005 จำกัดเลขที่ 58/46 หมู่ 6 ถนนกาญจนาภิเษก ตำบลเสาธงหิน อำเภอบางใหญ่ จังหวัดนนทบุรี 11140\n"
            "เลขที่ผู้เสียภาษี 0-1055-48143-35-1 (สำนักงานใหญ่)\n"
            "โทร.02-9267815-6\n"
            "ชื่องาน แชงกีล่า 12 กันยายน 2569\n"
            "รายละเอียด\n"
            "ถ่าย-ตัด Reel 2 ตัว\n"
            "ยอดรวม 10,000 บาท"
        )
        event = {
            "replyToken": "dummy_reply_token_double_img",
            "type": "message",
            "source": {
                "type": "group",
                "groupId": session_id,
                "userId": "1509900596688"  # Boss Hom UID
            },
            "message": {
                "id": "msg_double_img_001",
                "type": "text",
                "text": user_msg
            }
        }

        with patch("line_bot_server.send_line_reply") as mock_reply, \
             patch("line_bot_server.send_line_push_message") as mock_push, \
             patch("line_bot_server.send_line_loading_animation"):
            asyncio.run(process_line_events({"events": [event]}))

            # Either reply or push was called
            has_replied = mock_reply.called or mock_push.called
            self.assertTrue(has_replied, "Bot must respond to Boss Hom's explicit trigger message")
        print("✅ Test 3: Webhook process_line_events handles Boss Hom's message cleanly!")

    @patch("line_bot_server.find_document_by_no")
    def test_04_double_image_convert_invoice_prompts_gatekeeper(self, mock_find):
        """Converting existing Double Image bill to receipt without WHT/transfer prompts Gatekeeper."""
        session_id = "test_double_img_gatekeeper_turn1"
        mock_find.return_value = {
            "doc_no": "IV-202609-088",
            "doc_type": "invoice",
            "client_name": "บริษัท ดับเบิล อิมเมจ 2005 จำกัด",
            "project_name": "ถ่าย-ตัด Reel 2 ตัว",
            "gross_amount": 10700.0,
            "pre_vat": 10000.0,
            "vat_amount": 700.0,
            "net_total": 10700.0,
            "items": [{"desc": "ถ่าย-ตัด Reel 2 ตัว", "qty": 1, "price": 10000.0, "amount": 10000.0}]
        }
        SESSION_LAST_GENERATED_DOCS[session_id] = mock_find.return_value

        # 1. Execute convert_document_pipeline directly through execute_agent_tool
        res_data, flex_card = execute_agent_tool(
            "convert_document_pipeline",
            {"source_doc_no": "บ ดับเบิล อิมเมจ", "target_type": "receipt"},
            session_id=session_id,
            speaker_name="บอสเก่ง"
        )

        self.assertEqual(res_data.get("status"), "pending_gatekeeper")
        self.assertIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        self.assertEqual(PENDING_PAYMENT_CONFIRMATIONS[session_id]["doc_no"], "IV-202609-088")
        self.assertEqual(PENDING_PAYMENT_CONFIRMATIONS[session_id]["gross_amount"], 10700.0)
        self.assertIsNotNone(flex_card, "Flex card must be returned")
        self.assertIn("ยอดตามใบวางบิลคือ 10,700.00 บาท ลูกค้าโอนเข้ามากี่บาทคะ?", res_data.get("message", ""))

        # 2. Also verify through call_gemini_agent with mock Gemini returning tool call
        mock_call = MagicMock()
        mock_call.name = "convert_document_pipeline"
        mock_call.args = {"source_doc_no": "บ ดับเบิล อิมเมจ", "target_type": "receipt"}

        part_call = MagicMock(function_call=mock_call, text=None)
        part_text = MagicMock(function_call=None, text="บอสเก่งคะ ยอดตามใบวางบิลคือ 10,700.00 บาท ลูกค้าโอนเข้ามากี่บาทคะ? (โอนเต็ม 0% / หัก 3% / หัก 1% / พิมพ์ยอดจริง)")

        resp_turn1 = MagicMock()
        resp_turn1.candidates = [MagicMock()]
        resp_turn1.candidates[0].content.parts = [part_call]
        resp_turn1.text = None

        resp_turn2 = MagicMock()
        resp_turn2.candidates = [MagicMock()]
        resp_turn2.candidates[0].content.parts = [part_text]
        resp_turn2.text = "บอสเก่งคะ ยอดตามใบวางบิลคือ 10,700.00 บาท ลูกค้าโอนเข้ามากี่บาทคะ? (โอนเต็ม 0% / หัก 3% / หัก 1% / พิมพ์ยอดจริง)"

        with patch.object(bot_server.genai_client.models, "generate_content", side_effect=[resp_turn1, resp_turn2]):
            agent_res = asyncio.run(call_gemini_agent(
                user_message="ทำใบเสร็จรับเงินบิลของ บ ดับเบิล อิมเมจให้ที",
                session_id=session_id,
                speaker_name="บอสเก่ง"
            ))

            self.assertIsNotNone(agent_res.get("gatekeeper_pending"))
            self.assertIsNone(agent_res.get("doc_result"), "No receipt should be issued yet")
            self.assertTrue(len(agent_res.get("flex_cards", [])) > 0)
            self.assertIn("10,700.00", agent_res.get("reply_text", ""))
            self.assertIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        print("✅ Test 4: 'ทำใบเสร็จรับเงินบิลของ บ ดับเบิล อิมเมจให้ที' prompts Gatekeeper without auto-issuing!")

    @patch("line_bot_server.convert_document")
    def test_05_gatekeeper_turn2_choices_issue_receipt_accurately(self, mock_convert):
        """Turn 2 response of 'โอนเต็ม' or 'หัก 3%' accurately issues receipt matching choice."""
        session_id = "test_turn2_choice"

        # Setup pending confirmation for Double Image
        pending_data = {
            "doc_no": "IV-202609-088",
            "client_name": "บริษัท ดับเบิล อิมเมจ 2005 จำกัด",
            "project_name": "ถ่าย-ตัด Reel 2 ตัว",
            "gross_amount": 10700.0,
            "pre_vat": 10000.0,
            "vat_amount": 700.0,
            "target_doc": {
                "doc_no": "IV-202609-088",
                "client_name": "บริษัท ดับเบิล อิมเมจ 2005 จำกัด",
                "gross_amount": 10700.0,
                "pre_vat": 10000.0,
                "vat_amount": 700.0,
            }
        }

        # Sub-test A: User replies "โอนเต็ม" -> 0% WHT, net 10,700
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = dict(pending_data)
        mock_convert.return_value = {
            "status": "success",
            "doc_no": "RE-202609-001",
            "client_name": "บริษัท ดับเบิล อิมเมจ 2005 จำกัด",
            "totals": {"pre_vat": 10000.0, "vat_amount": 700.0, "wht_rate": 0.0, "net_total": 10700.0}
        }

        res_a = asyncio.run(call_gemini_agent("โอนเต็ม", session_id=session_id, speaker_name="บอสเก่ง"))
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS, "Pending state must be cleared")
        self.assertIn("RE-202609-001", res_a.get("reply_text", ""))
        self.assertIn("10,700.00", res_a.get("reply_text", ""))
        self.assertIn("โอนเต็ม", res_a.get("reply_text", ""))
        self.assertEqual(mock_convert.call_args[1]["overrides"]["wht_rate"], 0.0)

        # Sub-test B: User replies "หัก 3%" -> 3% WHT, net 10,400
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = dict(pending_data)
        mock_convert.return_value = {
            "status": "success",
            "doc_no": "RE-202609-002",
            "client_name": "บริษัท ดับเบิล อิมเมจ 2005 จำกัด",
            "totals": {"pre_vat": 10000.0, "vat_amount": 700.0, "wht_rate": 3.0, "net_total": 10400.0}
        }

        res_b = asyncio.run(call_gemini_agent("หัก 3%", session_id=session_id, speaker_name="บอสเก่ง"))
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS, "Pending state must be cleared")
        self.assertIn("RE-202609-002", res_b.get("reply_text", ""))
        self.assertIn("10,400.00", res_b.get("reply_text", ""))
        self.assertIn("3%", res_b.get("reply_text", ""))
        self.assertEqual(mock_convert.call_args[1]["overrides"]["wht_rate"], 3.0)
        print("✅ Test 5: Turn 2 'โอนเต็ม' and 'หัก 3%' accurately issue receipts matching choice!")

    def test_06_continuous_chat_in_active_thread_no_name_error(self):
        """Continuous chat in active conversation thread without explicit mention does NOT crash with NameError."""
        group_session_id = "test_active_thread_group_001"
        bot_user_id = "1509900596688"  # Boss Hom

        # Set active thread
        bot_server.ACTIVE_CONVERSATION_THREADS[group_session_id] = {
            "user_id": bot_user_id,
            "speaker_name": "บอสหอม",
            "expires_at": time.time() + 60,
            "waiting_for_answer": True
        }

        event = {
            "replyToken": "dummy_reply_token_active_thread",
            "type": "message",
            "source": {
                "type": "group",
                "groupId": group_session_id,
                "userId": bot_user_id
            },
            "message": {
                "id": "msg_active_thread_001",
                "type": "text",
                "text": "ตามที่ตกลงกันเลยนะ"  # No bot mention, but in active thread
            }
        }

        with patch("line_bot_server.send_line_reply") as mock_reply, \
             patch("line_bot_server.send_line_push_message") as mock_push, \
             patch("line_bot_server.send_line_loading_animation"):
            # This must NOT raise NameError: name 'is_bot_mentioned_native' is not defined
            try:
                asyncio.run(process_line_events({"events": [event]}))
            except NameError as ne:
                self.fail(f"process_line_events raised NameError in active thread: {ne}")
        print("✅ Test 6: Continuous chat in active conversation thread executes without NameError!")


if __name__ == "__main__":
    unittest.main()

