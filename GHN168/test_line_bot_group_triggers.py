"""
Unit Tests for GHN168 LINE Bot Trigger & Vision OCR Upgrades.
Tests the strict separation of Group vs 1-on-1 behavior, mention filtering,
pending confirmation actions, and non-financial image rejection.
"""

import asyncio
import json
import unittest
from unittest.mock import patch, MagicMock

from line_bot_server import (
    should_reply_to_event,
    analyze_receipt_image_with_ai,
    process_line_events,
    PENDING_EXPENSE_CONFIRMATIONS,
    PENDING_INCOME_CONFIRMATIONS,
    PENDING_DOCUMENT_ORDERS,
    PENDING_NEW_CUSTOMER_SAVING,
    BOT_DIRECT_TRIGGERS
)


def create_mock_event(
    source_type: str = "group",
    text: str = "",
    msg_type: str = "text",
    mentionees: list = None,
    user_id: str = "U1234567890",
    group_id: str = "C1234567890",
    reply_token: str = "dummy_reply_token"
) -> dict:
    event = {
        "replyToken": reply_token,
        "type": "message",
        "mode": "active",
        "timestamp": 1700000000000,
        "source": {
            "type": source_type,
            "userId": user_id
        },
        "message": {
            "id": "M1234567890",
            "type": msg_type
        }
    }
    if source_type in ["group", "room"]:
        event["source"]["groupId"] = group_id

    if msg_type == "text":
        event["message"]["text"] = text
        if mentionees is not None:
            event["message"]["mention"] = {"mentionees": mentionees}

    return event


class TestLineBotGroupTriggers(unittest.TestCase):

    # --------------------------------------------------------------------------
    # 1. Group Mention & Member Filtering Tests
    # --------------------------------------------------------------------------
    def test_group_tagged_other_member_silent(self):
        """If another member (e.g. @Modchhi, @MRhommm) is tagged in group, bot must stay silent."""
        event = create_mock_event(
            source_type="group",
            text="@Modchhi ตั้งเบิก 15000",
            mentionees=[{"index": 0, "length": 8, "userId": "U_other_user", "isSelf": False}]
        )
        should_reply, reason = should_reply_to_event(event)
        self.assertFalse(should_reply)
        self.assertEqual(reason, "tagged other group member")

    def test_group_tagged_bot_native_mention(self):
        """If the bot is tagged via LINE native mention (isSelf is True), bot must reply."""
        event = create_mock_event(
            source_type="group",
            text="@เลขาเฟิส เช็คคิวงานหน่อยครับ",
            mentionees=[{"index": 0, "length": 10, "userId": "U_bot_id", "isSelf": True}]
        )
        should_reply, reason = should_reply_to_event(event)
        self.assertTrue(should_reply)
        self.assertEqual(reason, "matched direct bot trigger")

    # --------------------------------------------------------------------------
    # 2. Group Work Talk & Number Banter (No Bot Trigger) -> Must be Silent
    # --------------------------------------------------------------------------
    def test_group_work_talk_without_trigger_silent(self):
        """General conversation, numbers, or work talk without bot trigger in groups must be ignored."""
        work_texts = [
            "ค่าไฟ 1500",
            "เช็คคิวงาน",
            "ยอดเงินเข้ายัง",
            "นัดถ่ายงานพรุ่งนี้",
            "โอนเงินให้ทีมงานหรือยัง",
            "สรุปบัญชีเดือนนี้",
            "ใบเสนอราคาออกยัง",
            "กินข้าวกัน",
            "55555+",
            "ไปไหนดี"
        ]
        for text in work_texts:
            with self.subTest(text=text):
                event = create_mock_event(source_type="group", text=text)
                should_reply, reason = should_reply_to_event(event)
                self.assertFalse(should_reply, f"Bot should NOT reply to '{text}' in group without trigger")
                self.assertEqual(reason, "group message without bot trigger")

    # --------------------------------------------------------------------------
    # 3. Group Direct Bot Triggers -> Must Reply
    # --------------------------------------------------------------------------
    def test_group_direct_bot_triggers_reply(self):
        """Direct bot keywords in group chats must trigger bot reply."""
        triggers = [
            "เฟิส เช็คคิวงานหน่อย",
            "@เฟิส ออกใบเสนอราคา",
            "เลขา สรุปรายรับหน่อยครับ",
            "เลขาเฟิส ขอข้อมูลลูกค้า",
            "ghn168 สรุปยอดเงินกองกลาง",
            "@ghn168 ดูคิวถ่ายวันนี้",
            "first check schedule today",
            "น้องเฟิส ช่วยดูบิลหน่อย",
            "พี่เฟิส",
            "บอท ขอสรุปภาษี"
        ]
        for text in triggers:
            with self.subTest(text=text):
                event = create_mock_event(source_type="group", text=text)
                should_reply, reason = should_reply_to_event(event)
                self.assertTrue(should_reply, f"Bot SHOULD reply to '{text}' in group with trigger")
                self.assertEqual(reason, "matched direct bot trigger")

    # --------------------------------------------------------------------------
    # 4. Group Pending Confirmation Actions
    # --------------------------------------------------------------------------
    def test_group_pending_confirmation_reply(self):
        """When a session has pending confirmation, explicit confirmation keywords must reply."""
        keywords = [
            "บันทึก", "ยืนยัน", "ออกใบเสร็จ", "ตกลง", "โอเค", "ยกเลิก",
            "confirm", "save", "cancel", "เซฟ", "บันทึกลูกค้า", "เซฟลูกค้า"
        ]
        group_id = "C_test_group_pending"
        for kw in keywords:
            with self.subTest(keyword=kw):
                event = create_mock_event(source_type="group", text=kw, group_id=group_id)
                PENDING_EXPENSE_CONFIRMATIONS[group_id] = {"store_name": "Test Store", "net_amount": 500}
                try:
                    should_reply, reason = should_reply_to_event(event)
                    self.assertTrue(should_reply, f"Bot SHOULD reply to confirmation keyword '{kw}'")
                    self.assertEqual(reason, "pending confirmation action")
                finally:
                    PENDING_EXPENSE_CONFIRMATIONS.pop(group_id, None)

    def test_group_pending_confirmation_unrelated_text_silent(self):
        """When a session has pending confirmation, but user types unrelated chatter, bot stays silent."""
        group_id = "C_test_group_pending_unrelated"
        event = create_mock_event(source_type="group", text="ไปกินข้าวเที่ยงไหนดี", group_id=group_id)

        PENDING_EXPENSE_CONFIRMATIONS[group_id] = {"store_name": "Test Store", "net_amount": 500}
        try:
            should_reply, reason = should_reply_to_event(event)
            self.assertFalse(should_reply)
            self.assertEqual(reason, "group message without bot trigger")
        finally:
            PENDING_EXPENSE_CONFIRMATIONS.pop(group_id, None)

    # --------------------------------------------------------------------------
    # 5. 1-on-1 Chat Behavior -> Always Reply
    # --------------------------------------------------------------------------
    def test_one_on_one_always_replies(self):
        """In 1-on-1 direct chat, bot replies to all user text messages."""
        messages = [
            "สวัสดีครับ",
            "เช็คคิวงาน",
            "ค่าไฟ 1500",
            "ออกใบเสนอราคาให้ บ.เอ็มคูล ยอด 30000",
            "กินข้าวหรือยัง",
            "สรุปรายรับ"
        ]
        for text in messages:
            with self.subTest(text=text):
                event = create_mock_event(source_type="user", text=text)
                should_reply, reason = should_reply_to_event(event)
                self.assertTrue(should_reply, f"Bot SHOULD reply to 1-on-1 message '{text}'")
                self.assertEqual(reason, "1-on-1 chat")

    # --------------------------------------------------------------------------
    # 6. Vision AI & Non-Financial Document Handling
    # --------------------------------------------------------------------------
    def test_vision_ai_ocr_financial_document_schema(self):
        """Verify analyze_receipt_image_with_ai includes is_financial_document flag."""
        dummy_image_bytes = b"fake_jpeg_image_data_here"
        
        mock_non_fin_response = json.dumps({
            "is_financial_document": False,
            "is_valid_receipt": False,
            "remarks": "ภาพแคปหน้าจอแดชบอร์ด ไม่ใช่เอกสารการเงิน"
        })
        
        with patch("line_bot_server.genai_client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.text = mock_non_fin_response
            mock_client.models.generate_content.return_value = mock_response_obj

            result = asyncio.run(analyze_receipt_image_with_ai(dummy_image_bytes))
            self.assertFalse(result.get("is_financial_document"))
            self.assertFalse(result.get("is_valid_receipt"))

    def test_process_line_events_group_non_financial_image_silent(self):
        """In group chat, sending a non-financial image must result in NO reply (silent)."""
        group_event = create_mock_event(source_type="group", msg_type="image", group_id="C_test_non_fin_group")
        payload = {"events": [group_event]}

        with patch("line_bot_server.download_line_image_content", return_value=b"dummy_image_bytes"), \
             patch("line_bot_server.analyze_receipt_image_with_ai", return_value={"is_financial_document": False, "is_valid_receipt": False}), \
             patch("line_bot_server.send_line_reply") as mock_reply, \
             patch("line_bot_server.send_line_reply_messages") as mock_reply_msgs:

            asyncio.run(process_line_events(payload))
            
            # Must not call any reply functions in group chat for non-financial images
            mock_reply.assert_not_called()
            mock_reply_msgs.assert_not_called()

    def test_process_line_events_1on1_non_financial_image_polite_reply(self):
        """In 1-on-1 chat, sending a non-financial image sends a polite informative response."""
        user_event = create_mock_event(source_type="user", msg_type="image", user_id="U_test_1on1")
        payload = {"events": [user_event]}

        with patch("line_bot_server.download_line_image_content", return_value=b"dummy_image_bytes"), \
             patch("line_bot_server.analyze_receipt_image_with_ai", return_value={"is_financial_document": False, "is_valid_receipt": False}), \
             patch("line_bot_server.send_line_reply") as mock_reply, \
             patch("line_bot_server.send_line_reply_messages") as mock_reply_msgs:

            asyncio.run(process_line_events(payload))
            
            # Must call send_line_reply with polite message
            mock_reply.assert_called_once()
            reply_text = mock_reply.call_args[0][1]
            self.assertIn("ไม่ใช่สลิปโอนเงิน", reply_text)
            self.assertIn("ค่ะ", reply_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
