"""
Unit Tests for Smart Group Conversation Awareness & Peer Addressing Filter in GHN168 LINE Bot.
Tests:
1. Peer-to-peer talk with numbers ("หอม พรุ่งนี้เจอกัน 10 โมงนะ") -> Silent (False)
2. Peer-to-peer talk with work keywords ("นิค ส่งงานลูกค้าไปหรือยัง") -> Silent (False)
3. Calling bot with friend's name ("เฟิส หอมบอกว่าให้ลดราคา 10%") -> Replies (True)
4. Multi-Boss partner answers bot question ("โอเค ยืนยันเลย") -> Replies (True)
5. Peer talk resets Active Thread immediately (not keeping 90s window)
6. Tone mark & word boundary safeguards (หมด, แก้ไข, เทคนิค, กู้เงิน, ข้าวหอม)
7. Multi-Boss active thread continuation
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Ensure workspace root is in sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from line_bot_server import (
    should_reply_to_event,
    should_bot_reply_in_group,
    is_peer_to_peer_talk,
    check_if_waiting_for_answer,
    ACTIVE_CONVERSATION_THREADS,
    PENDING_DOCUMENT_ORDERS,
    PENDING_EXPENSE_CONFIRMATIONS,
    PENDING_INCOME_CONFIRMATIONS,
    BOT_DIRECT_TRIGGERS,
    PARTNER_PROFILES,
)


def create_mock_group_event(
    text: str,
    user_id: str = "U_user_keng_001",
    group_id: str = "C_ghn168_exec_group",
    mentionees: list = None,
    msg_type: str = "text"
) -> dict:
    event = {
        "replyToken": "dummy_reply_token_123",
        "type": "message",
        "mode": "active",
        "timestamp": int(time.time() * 1000),
        "source": {
            "type": "group",
            "groupId": group_id,
            "userId": user_id
        },
        "message": {
            "id": "M_msg_test_001",
            "type": msg_type
        }
    }
    if msg_type == "text":
        event["message"]["text"] = text
        if mentionees is not None:
            event["message"]["mention"] = {"mentionees": mentionees}
    return event


class TestSmartGroupAwareness(unittest.TestCase):

    def setUp(self):
        ACTIVE_CONVERSATION_THREADS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_EXPENSE_CONFIRMATIONS.clear()
        PENDING_INCOME_CONFIRMATIONS.clear()

    def tearDown(self):
        ACTIVE_CONVERSATION_THREADS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_EXPENSE_CONFIRMATIONS.clear()
        PENDING_INCOME_CONFIRMATIONS.clear()

    # --------------------------------------------------------------------------
    # Test 1: บอสคุยกันเองมีตัวเลข -> บอทต้องไม่ตอบ (False)
    # --------------------------------------------------------------------------
    def test_boss_peer_talk_with_numbers_silent(self):
        """Test 1: บอสคุยกันเองมีตัวเลข เช่น 'หอม พรุ่งนี้เจอกัน 10 โมงนะ' -> บอทต้องไม่ตอบ (False)"""
        text = "หอม พรุ่งนี้เจอกัน 10 โมงนะ"
        event = create_mock_group_event(text=text, user_id="U_keng_test")
        should_reply, reason = should_reply_to_event(event)

        self.assertFalse(should_reply, f"Bot should NOT reply to boss peer talk '{text}'")
        self.assertEqual(reason, "peer-to-peer conversation between bosses")

    # --------------------------------------------------------------------------
    # Test 2: บอสคุยกันเองมีคีย์เวิร์ดงาน -> บอทต้องไม่ตอบ (False)
    # --------------------------------------------------------------------------
    def test_boss_peer_talk_with_work_keywords_silent(self):
        """Test 2: บอสคุยกันเองมีคีย์เวิร์ดงาน เช่น 'นิค ส่งงานลูกค้าไปหรือยัง' -> บอทต้องไม่ตอบ (False)"""
        text = "นิค ส่งงานลูกค้าไปหรือยัง"
        event = create_mock_group_event(text=text, user_id="U_keng_test")
        should_reply, reason = should_reply_to_event(event)

        self.assertFalse(should_reply, f"Bot should NOT reply to boss peer talk '{text}'")
        self.assertEqual(reason, "peer-to-peer conversation between bosses")

    # --------------------------------------------------------------------------
    # Test 3: บอสเรียกบอทแม้มีชื่อเพื่อน -> บอทต้องตอบ (True)
    # --------------------------------------------------------------------------
    def test_boss_calls_bot_with_friend_name_replies(self):
        """Test 3: บอสเรียกบอทแม้มีชื่อเพื่อน เช่น 'เฟิส หอมบอกว่าให้ลดราคา 10%' -> บอทต้องตอบ (True)"""
        text = "เฟิส หอมบอกว่าให้ลดราคา 10%"
        event = create_mock_group_event(text=text, user_id="U_keng_test")
        should_reply, reason = should_reply_to_event(event)

        self.assertTrue(should_reply, f"Bot SHOULD reply to direct trigger '{text}'")
        self.assertEqual(reason, "matched direct bot trigger")

    # --------------------------------------------------------------------------
    # Test 4: บอสคนอื่นตอบคำถามบอท -> บอทต้องตอบ (True)
    # --------------------------------------------------------------------------
    def test_multi_boss_pending_confirmation_replies(self):
        """Test 4: บอสคนอื่นตอบคำถามบอท เช่น บอสเก่งถาม แล้วบอสมดพิมพ์ 'โอเค ยืนยันเลย' -> บอทต้องตอบ (True)"""
        group_id = "C_exec_group_test_04"
        keng_uid = "U_keng_mhong"
        mod_uid = "U_mod_modchhi"  # Matches PARTNER_PROFILES keywords 'modchhi'

        # Scenario A: Pending State (e.g. pending document/expense)
        PENDING_DOCUMENT_ORDERS[group_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "amount": 50000.0,
            "created_by": keng_uid
        }

        event_mod = create_mock_group_event(
            text="โอเค ยืนยันเลย",
            user_id=mod_uid,
            group_id=group_id
        )
        should_reply, reason = should_reply_to_event(event_mod)
        self.assertTrue(should_reply, "Boss Mod confirming for Boss Keng's pending document must reply")
        self.assertEqual(reason, "pending confirmation action")

        # Scenario B: Active Thread with waiting_for_answer = True
        PENDING_DOCUMENT_ORDERS.clear()
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": keng_uid,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() + 90,
            "waiting_for_answer": True
        }

        should_reply_b, reason_b = should_reply_to_event(event_mod)
        self.assertTrue(should_reply_b, "Boss Mod replying to active thread waiting_for_answer must reply")

    # --------------------------------------------------------------------------
    # Test 5: เมื่อคุยกันเอง Active Thread ต้องถูกปิดลง ไม่เปิดค้าง 90 วิ
    # --------------------------------------------------------------------------
    def test_peer_talk_resets_active_thread_immediately(self):
        """Test 5: เมื่อคุยกันเอง Active Thread ต้องถูกปิดลง ไม่เปิดค้าง 90 วิ"""
        group_id = "C_exec_group_test_05"
        keng_uid = "U_keng_mhong"

        # Initialize active thread with 90 seconds window
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": keng_uid,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() + 90,
            "waiting_for_answer": False
        }
        self.assertIn(group_id, ACTIVE_CONVERSATION_THREADS)

        # Bosses talk to each other
        event_peer = create_mock_group_event(
            text="นิค พรุ่งนี้ไปไหน",
            user_id=keng_uid,
            group_id=group_id
        )
        should_reply, reason = should_reply_to_event(event_peer)

        # 1. Bot must stay silent
        self.assertFalse(should_reply)
        self.assertEqual(reason, "peer-to-peer conversation between bosses")

        # 2. Active Thread MUST be deleted immediately (not kept for 90s)
        self.assertNotIn(group_id, ACTIVE_CONVERSATION_THREADS, "Active Thread must be popped immediately on peer talk")

    # --------------------------------------------------------------------------
    # Comprehensive Tests: Boss Names & Peer Pronouns Detection
    # --------------------------------------------------------------------------
    def test_all_boss_peer_names_detected(self):
        """Verify is_peer_to_peer_talk detects all 4 bosses' names, handles, and titles."""
        boss_peer_phrases = [
            # หอม
            "หอม กินข้าวยัง",
            "บอสหอม วันนี้เข้าออฟฟิศไหม",
            "พี่หอม ช่วยดูหน่อย",
            "นายหอม ว่าไง",
            "@mrhom สรุปยอดหรือยัง",
            "mrhom งานเป็นไงบ้าง",
            # นิค
            "นิค พรุ่งนี้มีถ่าย",
            "บอสนิค ส่งไฟล์มาหรือยัง",
            "พี่นิค เช็คตารางงานหน่อย",
            "@anunick สะดวกไหม",
            "anunick อยู่ไหน",
            # มด
            "มด เคลียร์เอกสารยัง",
            "บอสมด ยอดเงินเข้าหรือยัง",
            "พี่มด ไปกินข้าวกัน",
            "เจ้มด สั่งของยัง",
            "@modchhi ดูงบหน่อย",
            "modchhi วันนี้ว่างไหม",
            # เก่ง
            "เก่ง ถึงสตูดิโอยัง",
            "บอสเก่ง เซ็นเอกสารหรือยัง",
            "พี่เก่ง พรุ่งนี้เจอกัน",
            "@mhong ไฟล์เสร็จแล้วนะ",
            "mhong วันนี้มีประชุมไหม",
            # สรรพนามพูดคุยระหว่างกัน
            "มึง ไปไหนกัน",
            "กูว่ายอดนี้แปลกๆ",
            "แก ส่งใบเสร็จยัง",
            "เพื่อน พรุ่งนี้เจอกันกี่โมง",
            "ทุกคน วันนี้มีประชุมบ่าย 2",
            "พวกมึง กินไรกันดี",
            "พี่ว่า อันนี้สวยกว่า",
            "ผมว่า ลูกค้าน่าจะโอเคแล้ว",
        ]
        for phrase in boss_peer_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(
                    is_peer_to_peer_talk(phrase),
                    f"is_peer_to_peer_talk should be True for '{phrase}'"
                )

    # --------------------------------------------------------------------------
    # Safeguards: Ensure False Positives are Avoided
    # --------------------------------------------------------------------------
    def test_peer_talk_safeguards_no_false_positives(self):
        """Safeguards: 'หมด', 'แก้ไข', 'เทคนิค', 'กู้เงิน', 'ข้าวหอม' must NOT trigger peer talk."""
        safe_non_peer_phrases = [
            "จ่ายเงินหมดแล้ว",
            "งบหมดแล้ว",
            "แก้ไขบิลให้หน่อย",
            "ขอแก้ยอดเงิน",
            "เทคนิคการจัดไฟในสตูดิโอ",
            "มีปัญหาทางเทคนิค",
            "กู้เงินธนาคาร",
            "ข้าวหอมมะลิ 2 ถุง",
            "หัวหอม 1 โล",
            "โอเค ยืนยันเลย",
            "บันทึกข้อมูล",
            "ตรวจสอบยอดเงิน",
            # Additional 29 Real-World Thai Production / Accounting Phrases
            "เตรียมดูคิวงานวันมะรืนด้วย",
            "ซ่อมด่วน 500 บาท",
            "พร้อมด้วยอุปกรณ์กล้อง",
            "แถมด้วยไฟล์ตัดต่อ 4K",
            "ตรวจสอบความสมดุลของบัญชี",
            "ลืมดึงข้อมูลลูกค้า",
            "ห้ามดึงสายไฟในสตูดิโอ",
            "รวมด้วย 15,000",
            "ลูกค้ายอมดรอปราคาลงมา",
            "ลูกค้าคลินิคเสริมความงาม",
            "คิวถ่ายงานที่นิคมอุตสาหกรรม",
            "จัดชุดปิคนิคสำหรับกองถ่าย",
            "เช็คระบบอิเล็กทรอนิกส์ในสตูดิโอ",
            "ถ่ายงานโฆษณาน้ำหอม 50,000",
            "ซื้อต้นหอมเข้าฉากทำอาหาร",
            "กาแฟสตูดิโอมีกลิ่นหอมมาก",
            "ซื้อหอมแดงประกอบฉาก",
            "ซิงค์ข้อมูลลงกูเกิลชีท",
            "แชร์ไฟล์ในกูเกิลไดรฟ์",
            "เชิญกูรูด้านบัญชีมาบรรยาย",
            "ถ่ายงานโรงแรมแกรนด์พาเลซ",
            "งานแกรนด์โอเพนนิ่ง",
            "ค่าอาหารข้าวแกง 60 บาท",
            "ซื้อแกงเขียวหวานเลี้ยงกองถ่าย",
            "แกลเลอรีภาพถ่ายงานแต่ง",
            "ถ่ายงานให้เพื่อนคุณสมชาย",
            "งานตัดต่อหนังสั้นเพื่อนสนิท",
            "น้องคนนี้ตัดต่อเก่งมาก",
            "ทีมเราทำงานเก่งจัง",
        ]
        for phrase in safe_non_peer_phrases:
            with self.subTest(phrase=phrase):
                self.assertFalse(
                    is_peer_to_peer_talk(phrase),
                    f"is_peer_to_peer_talk should be False for '{phrase}'"
                )

    # --------------------------------------------------------------------------
    # Multi-Boss Active Thread Continuation
    # --------------------------------------------------------------------------
    def test_multi_boss_active_thread_continuation(self):
        """In an active thread, any partner boss can continue asking work queries."""
        group_id = "C_exec_group_test_continuation"
        keng_uid = "U_keng_mhong"
        hom_uid = "U_hom_mrhom"  # Matches PARTNER_PROFILES 'mrhom'

        # Keng starts an active thread
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": keng_uid,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() + 90,
            "waiting_for_answer": False
        }

        # Hom asks a follow-up work question without bot trigger
        event_hom = create_mock_group_event(
            text="เช็คคิวงานวันพรุ่งนี้",
            user_id=hom_uid,
            group_id=group_id
        )
        should_reply, reason = should_reply_to_event(event_hom)
        self.assertTrue(should_reply, "Partner Boss Hom should be able to continue the active thread")
        self.assertEqual(reason, "active conversation thread")

    # --------------------------------------------------------------------------
    # Active Thread with Thai Compound Words (Must NOT be killed by false positives)
    # --------------------------------------------------------------------------
    def test_active_thread_compound_words_not_killed(self):
        """Compound words like 'เตรียมดู' or 'คลินิค' must NOT pop active thread."""
        group_id = "C_exec_group_test_compound"
        keng_uid = "U_keng_mhong"
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": keng_uid,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() + 90,
            "waiting_for_answer": False
        }

        # 1. 'เตรียมดูคิวงานวันมะรืนด้วย' (has ม+ด and work keyword 'คิวงาน')
        event_prep = create_mock_group_event(
            text="เตรียมดูคิวงานวันมะรืนด้วย",
            user_id=keng_uid,
            group_id=group_id
        )
        should_reply_1, reason_1 = should_reply_to_event(event_prep)
        self.assertTrue(should_reply_1, "Compound word 'เตรียมดู' must not kill active thread")
        self.assertEqual(reason_1, "active conversation thread")
        self.assertIn(group_id, ACTIVE_CONVERSATION_THREADS)

        # 2. 'ลูกค้าคลินิค 30,000' (has 'คลินิค' and work keyword + number)
        event_clinic = create_mock_group_event(
            text="ลูกค้าคลินิค 30,000",
            user_id=keng_uid,
            group_id=group_id
        )
        should_reply_2, reason_2 = should_reply_to_event(event_clinic)
        self.assertTrue(should_reply_2, "'คลินิค' with amount must not kill active thread")
        self.assertEqual(reason_2, "active conversation thread")

    # --------------------------------------------------------------------------
    # Multi-Boss Confirmation with Peer Pronouns (Priority 2 precedence)
    # --------------------------------------------------------------------------
    def test_multi_boss_pending_confirmation_with_peer_pronouns(self):
        """Even if partner boss includes pronouns like 'พี่ว่า', 'ผมว่า', pending confirmation must trigger."""
        group_id = "C_exec_group_test_pronoun_confirm"
        keng_uid = "U_keng_mhong"
        mod_uid = "U_mod_modchhi"

        PENDING_DOCUMENT_ORDERS[group_id] = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "amount": 30000.0,
            "created_by": keng_uid
        }

        # Mod replies "พี่ว่า ยืนยันเลย"
        event_mod_confirm = create_mock_group_event(
            text="พี่ว่า ยืนยันเลย",
            user_id=mod_uid,
            group_id=group_id
        )
        should_reply, reason = should_reply_to_event(event_mod_confirm)
        self.assertTrue(should_reply, "Boss Mod saying 'พี่ว่า ยืนยันเลย' must trigger pending confirmation")
        self.assertEqual(reason, "pending confirmation action")

        # Nick replies "ผมว่า โอเคแล้ว บันทึกเลย"
        nick_uid = "U_nick_anunick"
        event_nick_confirm = create_mock_group_event(
            text="ผมว่า โอเคแล้ว บันทึกเลย",
            user_id=nick_uid,
            group_id=group_id
        )
        should_reply_nick, reason_nick = should_reply_to_event(event_nick_confirm)
        self.assertTrue(should_reply_nick, "Boss Nick saying 'ผมว่า โอเคแล้ว บันทึกเลย' must trigger pending confirmation")
        self.assertEqual(reason_nick, "pending confirmation action")

    # --------------------------------------------------------------------------
    # 1-on-1 Chat Unaffected by Peer Words
    # --------------------------------------------------------------------------
    def test_one_on_one_chat_unaffected_by_peer_words(self):
        """In 1-on-1 direct chat, bot ALWAYS replies even if text has peer words."""
        one_on_one_phrases = [
            "นิค ส่งงานลูกค้าไปหรือยัง",
            "หอม พรุ่งนี้เจอกัน 10 โมงนะ",
            "ซื้อแกง 50 บาท",
            "ซ่อมด่วน 500 บาท",
            "กู้เงินธนาคาร",
            "มึง ไปไหนกัน",
            "กูว่ายอดนี้แปลกๆ",
        ]
        for phrase in one_on_one_phrases:
            event_1on1 = {
                "replyToken": "dummy_1on1_reply_token",
                "type": "message",
                "source": {
                    "type": "user",
                    "userId": "U_direct_keng_001"
                },
                "message": {
                    "id": "M_1on1_001",
                    "type": "text",
                    "text": phrase
                }
            }
            with self.subTest(phrase=phrase):
                should_reply, reason = should_reply_to_event(event_1on1)
                self.assertTrue(should_reply, f"1-on-1 chat must always reply for '{phrase}'")
                self.assertEqual(reason, "1-on-1 chat")

    # --------------------------------------------------------------------------
    # Waiting for Answer Helper
    # --------------------------------------------------------------------------
    def test_check_if_waiting_for_answer(self):
        """Verify check_if_waiting_for_answer correctly detects question indicators."""
        questions = [
            "ต้องการให้ออกใบเสร็จรับเงินเลยไหมคะ?",
            "ยอดถูกต้องไหมคะ พิมพ์ 'ยืนยัน' ได้เลยค่ะ",
            "สะดวกให้ออกเอกสารเลยหรือไม่",
            "รบกวนขอข้อมูลชื่อบริษัทเพิ่มเติมนะคะ",
        ]
        for q in questions:
            self.assertTrue(check_if_waiting_for_answer(q), f"Should detect question in '{q}'")

        non_questions = [
            "เลขาเฟิสบันทึกรายจ่ายเรียบร้อยแล้วค่ะ ✨",
            "ออกใบเสนอราคา QT-202609-001 เรียบร้อยค่ะ",
        ]
        for nq in non_questions:
            self.assertFalse(check_if_waiting_for_answer(nq), f"Should NOT detect question in '{nq}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
