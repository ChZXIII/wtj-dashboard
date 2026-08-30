#!/usr/bin/env python3
"""
================================================================================
Test Suite: Secretary Intelligence Upgrades (GHN168 เลขาเฟิส)
================================================================================
Tests the 5 core intelligence features:
1. Targeted Boss Recognition (resolve_partner_name for Keng, Nick, Hom, Mod, External)
2. Passive Group Memory Buffer (Context accumulation and translation/summary)
3. Active Conversation Thread Window (90s continuous conversation without 'เฟิส')
4. General Vision AI & Quoted Messages (quotedMessageId, image translation & summary)
5. Voice Message Multimodal (audio input, transcription & action response)
================================================================================
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import base64
import json
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ghn168_sync_service import (
    SPREADSHEET_ID,
    create_calendar_event,
    get_calendar_events,
    get_simulated_calendar_events,
)
from line_bot_server import (
    ACTIVE_CONVERSATION_THREADS,
    ACTIVE_THREAD_TIMEOUT_SECONDS,
    CONVERSATION_HISTORY,
    PARTNER_PROFILES,
    RECENT_MEDIA_CACHE,
    SESSION_LAST_IMAGE,
    analyze_general_image_with_ai,
    append_to_history,
    build_calendar_reminder_flex_message,
    call_gemini_agent,
    download_line_audio_content,
    download_line_image_content,
    execute_agent_tool,
    get_history,
    is_calendar_query_request,
    parse_natural_calendar_date_range,
    process_line_events,
    resolve_partner_name,
    sanitize_line_flex_payload,
    should_reply_to_event,
    transcribe_and_process_audio,
    validate_line_flex_payload,
)


def create_mock_event(
    source_type: str = "group",
    msg_type: str = "text",
    text: str = "",
    user_id: str = "U_test_user_001",
    group_id: str = "C_test_group_001",
    mentionees: list = None,
    quoted_msg_id: str = None,
    msg_id: str = "msg_1001",
    reply_token: str = "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA"
):
    source = {"type": source_type, "userId": user_id}
    if source_type in ["group", "room"]:
        source["groupId"] = group_id

    message = {
        "id": msg_id,
        "type": msg_type
    }
    if msg_type == "text":
        message["text"] = text
    if mentionees:
        message["mention"] = {"mentionees": mentionees}
    if quoted_msg_id:
        message["quotedMessageId"] = quoted_msg_id

    return {
        "type": "message",
        "replyToken": reply_token,
        "source": source,
        "message": message
    }


class TestSecretaryIntelligence(unittest.TestCase):

    def setUp(self):
        # Clear state caches between tests
        ACTIVE_CONVERSATION_THREADS.clear()
        CONVERSATION_HISTORY.clear()
        RECENT_MEDIA_CACHE.clear()
        SESSION_LAST_IMAGE.clear()

    # ==========================================================================
    # 1. Targeted Boss Recognition Tests (4 Partners Comprehensive Aliases)
    # ==========================================================================
    def test_01_targeted_boss_recognition_keng(self):
        """Boss Keng (Mongkol / 3509900218949 / Keng / mhong / chz / chzxiii / ubb8540e)."""
        keng_aliases = [
            "mhong", "mhong mhong", "mhongmhong", "keng", "เก่ง",
            "mongkol", "มงคล", "chz", "chzxiii", "3509900218949", "ubb8540e"
        ]
        for alias in keng_aliases:
            self.assertEqual(
                resolve_partner_name(user_id=f"U_{alias}", display_name=alias),
                "บอสเก่ง",
                f"Failed recognition for Boss Keng alias: {alias}"
            )
        self.assertEqual(resolve_partner_name(user_id="3509900218949"), "บอสเก่ง")
        self.assertEqual(resolve_partner_name(user_id="U_keng", group_id="C123", display_name="Keng"), "บอสเก่ง")

    def test_02_targeted_boss_recognition_nick(self):
        """Boss Nick (Anuchit / 3630200045082 / Nick / anunick / anu / อนุชิต)."""
        nick_aliases = ["anunick", "nick", "นิค", "anu", "anuchit", "อนุชิต", "3630200045082"]
        for alias in nick_aliases:
            self.assertEqual(
                resolve_partner_name(user_id=f"U_{alias}", display_name=alias),
                "บอสนิค",
                f"Failed recognition for Boss Nick alias: {alias}"
            )
        self.assertEqual(resolve_partner_name(user_id="3630200045082"), "บอสนิค")

    def test_03_targeted_boss_recognition_hom(self):
        """Boss Hom (Nattawat / 1509900596688 / Hom / mrhommm / mrhom / natthawat / nattawat / ณัฐวัฒน์)."""
        hom_aliases = ["mrhommm", "mrhom", "hom", "หอม", "natthawat", "nattawat", "ณัฐวัฒน์", "1509900596688"]
        for alias in hom_aliases:
            self.assertEqual(
                resolve_partner_name(user_id=f"U_{alias}", display_name=alias),
                "บอสหอม",
                f"Failed recognition for Boss Hom alias: {alias}"
            )
        self.assertEqual(resolve_partner_name(user_id="1509900596688"), "บอสหอม")

    def test_04_targeted_boss_recognition_mod(self):
        """Boss Mod (Nattaree / 1509900148537 / Mod / modchhi / modchi / natnaree / natnari / ณัฐนรี)."""
        mod_aliases = ["modchhi", "modchi", "mod", "มด", "natnaree", "natnari", "ณัฐนรี", "1509900148537"]
        for alias in mod_aliases:
            self.assertEqual(
                resolve_partner_name(user_id=f"U_{alias}", display_name=alias),
                "บอสมด",
                f"Failed recognition for Boss Mod alias: {alias}"
            )
        self.assertEqual(resolve_partner_name(user_id="1509900148537"), "บอสมด")

    def test_05_external_client_recognition(self):
        """External clients are recognized as 'คุณ [Display Name]' or 'คุณลูกค้า'."""
        self.assertEqual(resolve_partner_name(user_id="U_ext_1", display_name="Somchai"), "คุณ Somchai")
        self.assertEqual(resolve_partner_name(user_id="U_ext_2", display_name="คุณกิตติ"), "คุณกิตติ")
        self.assertEqual(resolve_partner_name(user_id="U_ext_3"), "คุณลูกค้า")

    # ==========================================================================
    # 2. Passive Group Memory Buffer Tests
    # ==========================================================================
    def test_06_passive_group_context_buffer_recording(self):
        """Verify unprompted messages in group are recorded into CONVERSATION_HISTORY with speaker labels."""
        group_id = "C_passive_group_test"
        
        # Message 1 from Nick (passive chatter)
        event1 = create_mock_event(source_type="group", group_id=group_id, user_id="3630200045082", text="subscriptions. Only pay with crypto and wire transfer")
        # Message 2 from Hom (passive chatter)
        event2 = create_mock_event(source_type="group", group_id=group_id, user_id="1509900596688", text="กล้อง Sony FX3 พร้อมเลนส์ 24-70mm อยู่ที่สตูดิโอครับ")

        with patch("line_bot_server.send_line_reply") as mock_reply:
            asyncio.run(process_line_events({"events": [event1]}))
            asyncio.run(process_line_events({"events": [event2]}))

            # Must not reply to passive group chatter
            mock_reply.assert_not_called()

        history = get_history(group_id)
        self.assertEqual(len(history), 2)
        self.assertIn("[บอสนิค]: subscriptions. Only pay with crypto and wire transfer", history[0]["text"])
        self.assertIn("[บอสหอม]: กล้อง Sony FX3 พร้อมเลนส์ 24-70mm อยู่ที่สตูดิโอครับ", history[1]["text"])

    def test_07_context_translation_on_summon(self):
        """When summoned with 'แปลทีครับ เฟิส', secretary translates recent context from passive buffer."""
        group_id = "C_translate_summon_test"
        
        # Nick posted an English phrase
        event_nick = create_mock_event(source_type="group", group_id=group_id, user_id="3630200045082", text="subscriptions. Only pay with crypto and wire transfer")
        asyncio.run(process_line_events({"events": [event_nick]}))

        # Keng asks to translate
        event_keng = create_mock_event(source_type="group", group_id=group_id, user_id="3509900218949", text="แปลทีครับ เฟิส")
        
        with patch("line_bot_server.send_line_reply") as mock_reply:
            asyncio.run(process_line_events({"events": [event_keng]}))
            mock_reply.assert_called_once()
            reply_text = mock_reply.call_args[0][1]
            self.assertIn("บอสเก่ง", reply_text)
            self.assertTrue("สรุป" in reply_text or "แปล" in reply_text)
            self.assertTrue("subscription" in reply_text.lower() or "คริปโต" in reply_text or "crypto" in reply_text.lower() or "โอนเงิน" in reply_text)

    # ==========================================================================
    # 3. Active Conversation Thread Window (90s) Tests
    # ==========================================================================
    def test_08_active_conversation_thread_window(self):
        """After bot replies, the same user can converse continuously within 90s without repeating 'เฟิส'."""
        group_id = "C_active_thread_test"
        user_id = "3509900218949"  # Boss Keng

        # Initial triggered message
        event1 = create_mock_event(source_type="group", group_id=group_id, user_id=user_id, text="เฟิส เช็คคิวงานหน่อย")
        should_reply1, reason1 = should_reply_to_event(event1)
        self.assertTrue(should_reply1)
        self.assertEqual(reason1, "matched direct bot trigger")

        with patch("line_bot_server.send_line_reply"):
            asyncio.run(process_line_events({"events": [event1]}))

        # Check that active thread is recorded
        self.assertIn(group_id, ACTIVE_CONVERSATION_THREADS)
        thread = ACTIVE_CONVERSATION_THREADS[group_id]
        self.assertEqual(thread["user_id"], user_id)
        self.assertEqual(thread["speaker_name"], "บอสเก่ง")
        self.assertGreater(thread["expires_at"], time.time())

        # Follow-up message without 'เฟิส' keyword within 90 seconds
        event2 = create_mock_event(source_type="group", group_id=group_id, user_id=user_id, text="แล้วมะรืนนี้ล่ะ")
        should_reply2, reason2 = should_reply_to_event(event2)
        self.assertTrue(should_reply2)
        self.assertEqual(reason2, "active conversation thread")

    def test_09_active_thread_tagged_other_member_silent(self):
        """Even inside an active thread, if user explicitly tags another member, bot stays silent."""
        group_id = "C_active_thread_mention_test"
        user_id = "3509900218949"  # Boss Keng

        # Set active thread
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": user_id,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() + 90
        }

        # Keng tags Modchhi
        event_tag = create_mock_event(
            source_type="group",
            group_id=group_id,
            user_id=user_id,
            text="@Modchhi บิลนี้จ่ายหรือยัง",
            mentionees=[{"userId": "U_mod", "isSelf": False}]
        )
        should_reply, reason = should_reply_to_event(event_tag)
        self.assertFalse(should_reply)
        self.assertEqual(reason, "tagged other group member")

    def test_10_active_thread_expired_silent(self):
        """After 90s expire, messages without trigger in group are ignored."""
        group_id = "C_expired_thread_test"
        user_id = "3509900218949"

        # Set expired thread
        ACTIVE_CONVERSATION_THREADS[group_id] = {
            "user_id": user_id,
            "speaker_name": "บอสเก่ง",
            "expires_at": time.time() - 5
        }

        event = create_mock_event(source_type="group", group_id=group_id, user_id=user_id, text="แล้วยังไงต่อนะ")
        should_reply, reason = should_reply_to_event(event)
        self.assertFalse(should_reply)
        self.assertEqual(reason, "group message without bot trigger")

    # ==========================================================================
    # 4. Quoted Messages & General Vision AI Tests
    # ==========================================================================
    def test_11_quote_reply_image_analysis(self):
        """Quoting a previously sent image with 'แปล' or 'สรุป' triggers general vision AI analysis."""
        group_id = "C_quote_image_test"
        quoted_img_id = "msg_img_999"
        dummy_img_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00fake_image_content"
        
        # Pre-cache quoted image
        RECENT_MEDIA_CACHE[quoted_img_id] = dummy_img_bytes

        # User quotes image and says "แปลให้หน่อยครับ เฟิส"
        event = create_mock_event(
            source_type="group",
            group_id=group_id,
            user_id="3509900218949",
            text="แปลให้หน่อยครับ เฟิส",
            quoted_msg_id=quoted_img_id
        )

        with patch("line_bot_server.send_line_reply") as mock_reply:
            asyncio.run(process_line_events({"events": [event]}))
            mock_reply.assert_called_once()
            reply_text = mock_reply.call_args[0][1]
            self.assertIn("บอสเก่ง", reply_text)
            self.assertTrue("ตรวจดูภาพ" in reply_text or "แปล" in reply_text or "สรุป" in reply_text)

    def test_12_general_vision_ai_helper(self):
        """Verify analyze_general_image_with_ai produces tailored secretary response."""
        dummy_img_bytes = b"\xff\xd8\xff\xe0dummy_jpeg"
        result = asyncio.run(analyze_general_image_with_ai(dummy_img_bytes, prompt="สเปกกล้องนี้เป็นยังไง", speaker_name="บอสนิค"))
        self.assertIn("บอสนิค", result)
        self.assertIn("เฟิส", result)

    # ==========================================================================
    # 5. Multimodal Audio / Voice Message Tests
    # ==========================================================================
    def test_13_voice_message_processing_1on1(self):
        """Verify voice message in 1-on-1 chat downloads audio and replies in character."""
        user_id = "3630200045082"  # Boss Nick
        audio_event = create_mock_event(source_type="user", user_id=user_id, msg_type="audio", msg_id="aud_101")

        with patch("line_bot_server.download_line_audio_content", return_value=b"fake_audio_m4a_stream"), \
             patch("line_bot_server.send_line_reply") as mock_reply:

            asyncio.run(process_line_events({"events": [audio_event]}))
            mock_reply.assert_called_once()
            reply_text = mock_reply.call_args[0][1]
            self.assertIn("บอสนิค", reply_text)
            self.assertIn("ข้อความเสียง", reply_text)

    def test_14_transcribe_and_process_audio_helper(self):
        """Verify transcribe_and_process_audio formats targeted boss response."""
        dummy_audio = b"fake_m4a_audio_bytes"
        result = asyncio.run(transcribe_and_process_audio(dummy_audio, "test_session", speaker_name="บอสหอม"))
        self.assertIn("บอสหอม", result)
        self.assertIn("ข้อความเสียง", result)

    # ==========================================================================
    # 6. Master Upgrades Test Suite: Deep Sanitization, GAS Sync, NL Date Ranges
    # ==========================================================================
    def test_15_flex_message_deep_sanitization(self):
        """Verify sanitize_line_flex_payload recursively sanitizes empty text and invalid URIs."""
        raw_broken_payload = {
            "type": "flex",
            "altText": "",  # Empty altText
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": ""},  # Empty text string
                        {"type": "text", "text": None},  # None text
                        {"type": "text", "text": "   "},  # Whitespace only
                        {"type": "text", "text": "Valid Header", "weight": "bold"},
                        {
                            "type": "button",
                            "action": {
                                "type": "uri",
                                "label": "This label is way too long and definitely exceeds forty characters limit in LINE schema",
                                "uri": ""  # Empty URI
                            }
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "uri",
                                "label": "Invalid Scheme Link",
                                "uri": "ftp://invalid-site.com"
                            }
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "text": ""  # Empty message text
                            }
                        }
                    ]
                }
            }
        }

        sanitized = sanitize_line_flex_payload(raw_broken_payload)
        self.assertEqual(sanitized["type"], "flex")
        self.assertTrue(bool(sanitized["altText"]))
        body_contents = sanitized["contents"]["body"]["contents"]

        # Text nodes must be "-"
        self.assertEqual(body_contents[0]["text"], "-")
        self.assertEqual(body_contents[1]["text"], "-")
        self.assertEqual(body_contents[2]["text"], "-")
        self.assertEqual(body_contents[3]["text"], "Valid Header")

        # Action nodes must have valid URI & <=40 length label
        self.assertEqual(body_contents[4]["action"]["uri"], "https://drive.google.com")
        self.assertLessEqual(len(body_contents[4]["action"]["label"]), 40)

        # Invalid scheme fallback
        self.assertEqual(body_contents[5]["action"]["uri"], "https://drive.google.com")

        # Message action text
        self.assertEqual(body_contents[6]["action"]["text"], "-")

        # validate_line_flex_payload must pass without raising ValueError
        self.assertTrue(validate_line_flex_payload(sanitized))

    def test_16_calendar_flex_card_sanitization_empty_briefing(self):
        """Verify build_calendar_reminder_flex_message with empty briefing_text sets default snippet and passes validation."""
        mock_events = [
            {
                "id": "evt_test_01",
                "title": "",  # Empty title -> should default
                "location": "",  # Empty location -> should default
                "description": "",
                "startTime": "2026-08-27T10:00:00+07:00",
                "endTime": "2026-08-27T12:00:00+07:00",
                "isAllDay": False
            }
        ]
        flex = build_calendar_reminder_flex_message(mock_events, date_label="วันพรุ่งนี้", briefing_text="")
        self.assertEqual(flex["type"], "flex")
        self.assertTrue(validate_line_flex_payload(flex))

        # Check with empty events list
        flex_empty = build_calendar_reminder_flex_message([], date_label="สัปดาห์นี้", briefing_text="")
        self.assertEqual(flex_empty["type"], "flex")
        self.assertTrue(validate_line_flex_payload(flex_empty))

    def test_17_google_calendar_gas_sync_payload_includes_spreadsheet_id(self):
        """Verify get_calendar_events and create_calendar_event include spreadsheetId in request payload."""
        with patch("requests.post") as mock_post:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {"status": "success", "totalEvents": 0, "events": []}
            mock_post.return_value = mock_res

            # Test get_calendar_events
            get_calendar_events(target_date="2026-08-27", script_url="https://script.google.com/test")
            self.assertTrue(mock_post.called)
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs.get("json", {})
            self.assertEqual(payload.get("type"), "get_calendar_events")
            self.assertEqual(payload.get("spreadsheetId"), SPREADSHEET_ID)

            # Test create_calendar_event
            mock_post.reset_mock()
            mock_res.json.return_value = {"status": "success", "eventId": "evt_123"}
            create_calendar_event(
                title="คิวถ่ายทำ Luxury Villa",
                start_date="2026-08-28",
                location="เชียงใหม่",
                script_url="https://script.google.com/test"
            )
            self.assertTrue(mock_post.called)
            create_payload = mock_post.call_args[1].get("json", {})
            self.assertEqual(create_payload.get("type"), "create_calendar_event")
            self.assertEqual(create_payload.get("spreadsheetId"), SPREADSHEET_ID)

    def test_18_natural_language_calendar_date_range_parsing(self):
        """Verify parse_natural_calendar_date_range and execute_agent_tool calendar query ranges."""
        # 1. Next Week (สัปดาห์หน้า / อาทิตย์หน้า / next_week)
        target_d, start_d, end_d, lbl = parse_natural_calendar_date_range(target_date="next_week")
        self.assertIn("สัปดาห์หน้า", lbl)
        self.assertIsNotNone(start_d)
        self.assertIsNotNone(end_d)
        self.assertNotEqual(start_d, end_d)

        # 2. This Week (สัปดาห์นี้ / อาทิตย์นี้ / this_week)
        target_d2, start_d2, end_d2, lbl2 = parse_natural_calendar_date_range(query_text="ขอเช็คคิวงานสัปดาห์นี้หน่อยค่ะ")
        self.assertIn("สัปดาห์นี้", lbl2)
        self.assertIsNotNone(start_d2)
        self.assertIsNotNone(end_d2)

        # 3. Tomorrow (พรุ่งนี้ / tomorrow)
        target_d3, start_d3, end_d3, lbl3 = parse_natural_calendar_date_range(target_date="พรุ่งนี้")
        self.assertIn("วันพรุ่งนี้", lbl3)
        self.assertEqual(start_d3, end_d3)

        # 4. This Month (เดือนนี้ / this_month)
        target_d4, start_d4, end_d4, lbl4 = parse_natural_calendar_date_range(target_date="this_month")
        self.assertIn("เดือนนี้", lbl4)
        self.assertTrue(start_d4.endswith("-01"))

        # 5. Agent Tool Execution with next_week
        res, flex = execute_agent_tool(
            "manage_calendar_schedule",
            {"action": "query", "target_date": "next_week"},
            session_id="test_nl_session"
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("events", res)
        self.assertIn("start_date", res)
        self.assertIn("end_date", res)
        self.assertIsNotNone(flex)
        self.assertTrue(validate_line_flex_payload(flex))


if __name__ == "__main__":
    unittest.main(verbosity=2)
