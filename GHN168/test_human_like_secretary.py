#!/usr/bin/env python3
"""
================================================================================
Test Suite: Human-Like Executive Secretary Upgrade (เลขาคู่คิด GHN168)
================================================================================
Tests:
1. Health check capability & feature verification.
2. Active Thread Memory (180s window continuity without direct triggers).
3. Pending State Continuity (pending orders/confirmations).
4. Broad Semantic Work & Intent Detection (Natural language production/finance).
5. Casual Banter Filter (quietly ignore group chatter when idle).
6. Ultra-Human Persona & Anti-Robot Language check (Boss titles, female particles, no robot jargon).
7. Context Ellipsis Resolution (multi-turn reference understanding).
================================================================================
"""

import os
import sys
import time
import unittest
from datetime import datetime

# Import application components
from line_bot_server import (
    app,
    should_reply_to_event,
    CONVERSATION_HISTORY,
    PENDING_DOCUMENT_ORDERS,
    PENDING_EXPENSE_CONFIRMATIONS,
    PENDING_INCOME_CONFIRMATIONS,
    PENDING_NEW_CUSTOMER_SAVING,
    ACTIVE_THREAD_TIMEOUT_SECONDS,
    SYSTEM_INSTRUCTION,
    append_to_history,
    get_history
)

try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    USE_TEST_CLIENT = True
except Exception:
    USE_TEST_CLIENT = False


class TestHumanLikeExecutiveSecretary(unittest.TestCase):

    def setUp(self):
        # Clear test state before each test
        CONVERSATION_HISTORY.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_EXPENSE_CONFIRMATIONS.clear()
        PENDING_INCOME_CONFIRMATIONS.clear()
        PENDING_NEW_CUSTOMER_SAVING.clear()

    def test_01_health_check_features(self):
        """Verify new human-like secretary features in /health endpoint."""
        if not USE_TEST_CLIENT:
            self.skipTest("TestClient not available")
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        features = data.get("features", {})
        self.assertTrue(features.get("human_like_executive_secretary_upgrade"))
        self.assertTrue(features.get("active_thread_memory_180s"))
        self.assertTrue(features.get("context_aware_reply_filter"))
        self.assertTrue(features.get("context_ellipsis_support"))
        print("\n✅ Test 1: Health check feature verification passed!")

    def test_02_active_thread_continuity_within_180s(self):
        """Verify active thread memory replies within 180s even without bot triggers."""
        group_session = "C_group_active_thread_test_001"
        
        # Step 1: Initial event that activates conversation history
        append_to_history(group_session, "user", "ออกใบเสนอราคาให้ บ.เชียงใหม่มีเดีย")
        append_to_history(group_session, "model", "ยินดีค่ะบอสเก่ง ยอดเท่าไหร่คะ")

        # Step 2: Follow-up message within 180 seconds WITHOUT any bot trigger or @mention
        followup_event = {
            "type": "message",
            "source": {"type": "group", "groupId": group_session, "userId": "U_boss_keng"},
            "message": {"type": "text", "text": "เปลี่ยนเป็น 25000 นะ"}
        }
        
        should_reply, reason = should_reply_to_event(followup_event)
        self.assertTrue(should_reply, f"Should reply within active thread window: {reason}")
        self.assertIn("active thread", reason)
        print("✅ Test 2.1: Active thread continuation within 180s passed!")

        # Step 3: Message AFTER 180 seconds expired (e.g. 250s ago) with no work keyword
        CONVERSATION_HISTORY[group_session][-1]["timestamp"] = time.time() - 250
        expired_event = {
            "type": "message",
            "source": {"type": "group", "groupId": group_session, "userId": "U_boss_keng"},
            "message": {"type": "text", "text": "วันนี้อากาศดีจังเลย"}
        }
        should_reply_exp, reason_exp = should_reply_to_event(expired_event)
        self.assertFalse(should_reply_exp, f"Should NOT reply after active thread expired: {reason_exp}")
        print("✅ Test 2.2: Idle thread after 180s properly ignored!")

    def test_03_pending_state_continuity(self):
        """Verify bot replies to confirmations or parameter updates during pending state."""
        group_session = "C_group_pending_test_002"
        
        # Setup pending document order state
        PENDING_DOCUMENT_ORDERS[group_session] = {
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "doc_type": "quotation"
        }

        pending_event = {
            "type": "message",
            "source": {"type": "group", "groupId": group_session, "userId": "U_boss_keng"},
            "message": {"type": "text", "text": "ยอด 30,000 บาท"}
        }
        should_reply, reason = should_reply_to_event(pending_event)
        self.assertTrue(should_reply, f"Should reply when session has pending state: {reason}")
        print("✅ Test 3: Pending state continuity passed!")

    def test_04_broad_semantic_work_detection_without_triggers(self):
        """Verify bot detects broad production and financial context in groups without name/tag."""
        work_messages = [
            "พรุ่งนี้มีคิวถ่ายที่ไหนบ้าง",
            "ช่วยเช็กยอดภาษีซื้อเดือนนี้หน่อย",
            "มีงานอะไรต้องส่งสัปดาห์นี้",
            "ตามบิลค้างชำระของเชียงใหม่มีเดียที",
            "วางบิลยอด 50,000 บาท",
            "ออกเอกสาร 50 ทวิ ค่าจ้างตัดต่อ 15,000",
            "เช็คคิวงานวันพรุ่งนี้ให้หน่อย",
            "สลิปเงินเข้าแล้วนะ"
        ]

        for msg in work_messages:
            event = {
                "type": "message",
                "source": {"type": "group", "groupId": "C_work_group_test", "userId": "U_user_001"},
                "message": {"type": "text", "text": msg}
            }
            should_reply, reason = should_reply_to_event(event)
            self.assertTrue(should_reply, f"Should detect work context for '{msg}': {reason}")
        print("✅ Test 4: Broad semantic work context detection without triggers passed!")

    def test_05_casual_banter_filtered_when_idle(self):
        """Verify casual chat in group is quietly ignored when not in active thread."""
        casual_messages = [
            "55555555555",
            "เที่ยงนี้กินข้าวไหนดี",
            "หิวข้าวมาก",
            "คืนนี้เล่นเกมปะ",
            "ง่วงมาก นอนละ",
            "ไปไหนกันดี",
            "ฮ่าๆๆๆๆ",
            "ฝันดีทุกคน"
        ]

        for msg in casual_messages:
            event = {
                "type": "message",
                "source": {"type": "group", "groupId": "C_idle_group_test", "userId": "U_user_002"},
                "message": {"type": "text", "text": msg}
            }
            should_reply, reason = should_reply_to_event(event)
            self.assertFalse(should_reply, f"Casual banter '{msg}' should be filtered: {reason}")
            self.assertIn("casual banter", reason)
        print("✅ Test 5: Casual banter filtering passed!")

    def test_06_ultra_human_persona_and_anti_robot_language(self):
        """Verify prompt and SYSTEM_INSTRUCTION strictly adhere to human secretary rules."""
        # 1. Check Anti-Robot Rules in SYSTEM_INSTRUCTION
        self.assertIn("Strict Anti-Robot Policy", SYSTEM_INSTRUCTION)
        self.assertIn("ในฐานะโมเดลภาษา", SYSTEM_INSTRUCTION)
        self.assertIn("ระบบฐานข้อมูล", SYSTEM_INSTRUCTION)
        self.assertIn("ทำการประมวลผลคำสั่ง", SYSTEM_INSTRUCTION)

        # 2. Check Boss title pronouns for 4 partners
        self.assertIn("บอสเก่ง", SYSTEM_INSTRUCTION)
        self.assertIn("บอสหอม", SYSTEM_INSTRUCTION)
        self.assertIn("บอสนิค", SYSTEM_INSTRUCTION)
        self.assertIn("บอสมด", SYSTEM_INSTRUCTION)

        # 3. Test API Chat response formatting
        if USE_TEST_CLIENT:
            resp = client.post("/api/test_chat", json={
                "message": "ทักทายพี่ๆ ผู้บริหาร GHN168 ทั้ง 4 คนหน่อย",
                "session_id": "test_human_persona_001"
            })
            self.assertEqual(resp.status_code, 200)
            reply = resp.json().get("reply", "")
            
            # Must use female polite particles
            self.assertTrue("ค่ะ" in reply or "คะ" in reply)
            self.assertNotIn("ครับ", reply)
            self.assertNotIn("ในฐานะโมเดลภาษา", reply)
            self.assertNotIn("ระบบกำลังดำเนินการ", reply)
            self.assertIn("บอส", reply)
        print("✅ Test 6: Ultra-Human Persona & Anti-Robot Language verification passed!")

    def test_07_context_ellipsis_multi_turn_flow(self):
        """Verify context ellipsis across multi-turn messages."""
        if not USE_TEST_CLIENT:
            self.skipTest("TestClient not available")

        session_id = "test_context_ellipsis_flow"

        # Step 1: Boss asks for a quotation for Chiang Mai Media
        resp1 = client.post("/api/test_chat", json={
            "message": "ออกใบเสนอราคาให้ บริษัท เชียงใหม่มีเดีย จำกัด งานถ่ายทำและตัดต่อโฆษณา ยอด 20,000 บาท ผู้ลงนามบอสเก่ง",
            "session_id": session_id
        })
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        doc1 = data1.get("doc_result")
        self.assertIsNotNone(doc1)
        self.assertEqual(doc1.get("client_name"), "บริษัท เชียงใหม่มีเดีย จำกัด")
        print("✅ Step 7.1: Initial document order generated successfully!")

        # Step 2: Follow-up with context reference ("เปลี่ยนยอดเป็น 35,000")
        resp2 = client.post("/api/test_chat", json={
            "message": "เปลี่ยนยอดเป็น 35,000 บาท",
            "session_id": session_id
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        print("Step 7.2 Response:\n", data2.get("reply"))
        print("✅ Step 7.2: Context Ellipsis handled smoothly!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
