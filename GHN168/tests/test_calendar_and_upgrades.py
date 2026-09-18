import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from line_bot_server import (
    GEMINI_MODEL,
    MAX_HISTORY_PER_SESSION,
    CONVERSATION_HISTORY,
    LAST_CALENDAR_REMINDER_DATE,
    app,
    append_to_history,
    build_calendar_reminder_flex_message,
    generate_calendar_daily_briefing,
    generate_gemini_reply,
    get_history,
    is_calendar_query_request,
    trigger_proactive_calendar_reminder,
    parse_iso_to_bangkok_time,
    format_calendar_event_time_display,
    format_calendar_rule_based_briefing,
    send_line_loading_animation,
    is_agent_action_command,
)
from ghn168_sync_service import (
    get_calendar_events,
    get_simulated_calendar_events,
)


from unittest.mock import MagicMock, patch


class TestGHN168MegaUpgrades(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_session = "test_session_upgrade_verification"
        CONVERSATION_HISTORY.clear()
        LAST_CALENDAR_REMINDER_DATE.clear()

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
            elif req_type == "get_calendar_events":
                from ghn168_sync_service import get_simulated_calendar_events
                sim_cal = get_simulated_calendar_events(target_date=payload.get("targetDate"), start_date=payload.get("startDate"), end_date=payload.get("endDate"))
                mock_res.json.return_value = {
                    "status": "success",
                    "total_events": len(sim_cal.get("events", [])),
                    "totalEvents": len(sim_cal.get("events", [])),
                    "events": sim_cal.get("events", [])
                }
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}

            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_01_configuration_and_model_version(self):
        print("\n--- [Test 1] Checking Model & Chat History Config ---")
        self.assertIn(GEMINI_MODEL, ["gemini-3.7-flash", "gemini-3.8-flash"])
        self.assertEqual(MAX_HISTORY_PER_SESSION, 20)
        print("Model: " + GEMINI_MODEL)
        print("Max History: " + str(MAX_HISTORY_PER_SESSION))

    def test_02_chat_history_expansion(self):
        print("\n--- [Test 2] Testing 20-Message History Sliding Window ---")
        for i in range(35):
            role = "user" if i % 2 == 0 else "model"
            append_to_history(self.test_session, role, "Message #" + str(i+1))

        history = get_history(self.test_session)
        self.assertEqual(len(history), 20)
        self.assertEqual(history[-1]["text"], "Message #35")
        self.assertEqual(history[0]["text"], "Message #16")
        print("20-message memory window verified.")

    def test_03_calendar_sync_service(self):
        print("\n--- [Test 3] Testing Google Calendar Sync Service ---")
        sim_res = get_simulated_calendar_events(target_date="2026-08-21")
        self.assertIn(sim_res["status"], ["success", "simulation"])
        self.assertGreater(sim_res["total_events"], 0)

        cal_res = get_calendar_events(target_date="2026-08-21")
        self.assertIn(cal_res["status"], ["success", "simulation"])
        self.assertIsInstance(cal_res["events"], list)
        self.assertGreater(len(cal_res["events"]), 0)
        ev0 = cal_res["events"][0]
        self.assertIn("title", ev0)
        self.assertIn("startTime", ev0)
        print("Retrieved calendar events: " + str(len(cal_res["events"])))

    def test_04_calendar_intent_parser(self):
        print("\n--- [Test 4] Testing On-Demand Calendar Intent Parser ---")
        test_queries = [
            ("พรุ่งนี้มีงานอะไร", True, "วันพรุ่งนี้"),
            ("คิวงานวันนี้มีอะไรบ้าง", True, "วันนี้"),
            ("มะรืนนี้มีถ่ายงานไหม", True, "วันมะรืน"),
            ("สัปดาห์นี้มีงานอะไรบ้างคะ", True, "สัปดาห์นี้"),
            ("เช็คคิวงานเดือนนี้หน่อย", True, "เดือนนี้"),
            ("ขอใบเสนอราคาให้ลูกค้าหน่อยค่ะ", False, ""),
            ("สวัสดีค่ะเฟิส", False, "")
        ]
        for query, expected_is_cal, label_contains in test_queries:
            is_cal, date_label, params = is_calendar_query_request(query)
            self.assertEqual(is_cal, expected_is_cal, "Failed for query: " + query)
            if expected_is_cal:
                self.assertIn(label_contains, date_label)
                print("Calendar Query Recognized: " + query + " -> " + date_label)

    def test_05_calendar_flex_card_builder(self):
        print("\n--- [Test 5] Testing Calendar Flex Card Builder ---")
        mock_events = [{
            "id": "evt_test_01",
            "title": "ถ่ายทำวิดีโอโฆษณา Luxury Villa",
            "location": "เชียงใหม่",
            "startTime": "2026-08-21T09:00:00+07:00",
            "endTime": "2026-08-21T16:00:00+07:00",
            "isAllDay": False
        }]
        briefing = "สวัสดีค่ะบอสเก่ง วันพรุ่งนี้มีคิวงานถ่ายทำ 1 งานนะคะ"
        flex = build_calendar_reminder_flex_message(mock_events, "วันพรุ่งนี้ (21/08/2026)", briefing)
        self.assertEqual(flex["type"], "flex")
        self.assertEqual(flex["contents"]["header"]["backgroundColor"], "#0f172a")
        print("Calendar Flex Card Schema verified.")

    def test_06_ai_briefing_and_proactive_reminder(self):
        print("\n--- [Test 6] Testing AI Briefing & Proactive Reminder ---")
        async def run_async():
            mock_events = [{
                "id": "evt_async_01",
                "title": "กองถ่ายทำ One Nimman",
                "location": "One Nimman เชียงใหม่",
                "startTime": "2026-08-21T09:30:00+07:00",
                "endTime": "2026-08-21T15:00:00+07:00",
                "isAllDay": False
            }]
            briefing = await generate_calendar_daily_briefing(mock_events, "วันพรุ่งนี้ (21/08/2026)")
            self.assertIsInstance(briefing, str)
            self.assertGreater(len(briefing), 10)
            print("AI Briefing Output length: " + str(len(briefing)))

            result = await trigger_proactive_calendar_reminder(target_date="2026-08-21", force=True)
            self.assertEqual(result["status"], "success")
            print("Proactive Reminder triggered successfully: " + str(result["target_date"]))

        asyncio.run(run_async())

    def test_07_fastapi_endpoints(self):
        print("\n--- [Test 7] Testing FastAPI Endpoints ---")
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        h = res_health.json()
        self.assertIn(h["gemini_model"], ["gemini-3.7-flash", "gemini-3.8-flash"])
        self.assertEqual(h["thinking_budget"], 512)
        self.assertEqual(h["max_history_per_session"], 20)
        self.assertTrue(h["features"]["gemini_3_7_flash_thinking"])
        self.assertTrue(h["features"]["proactive_calendar_reminder_1930"])
        self.assertTrue(h["features"]["on_demand_calendar_query"])
        print("GET /health: 200 OK")

        res_status = self.client.get("/api/calendar/status")
        self.assertEqual(res_status.status_code, 200)
        print("GET /api/calendar/status: 200 OK")

        res_events = self.client.get("/api/calendar/events?target_date=2026-08-21")
        self.assertEqual(res_events.status_code, 200)
        print("GET /api/calendar/events: 200 OK")

        res_trigger = self.client.post("/api/calendar/trigger_reminder", json={"target_date": "2026-08-21", "force": True})
        self.assertEqual(res_trigger.status_code, 200)
        print("POST /api/calendar/trigger_reminder: 200 OK")

        res_chat = self.client.post("/api/test_chat", json={"message": "พรุ่งนี้มีงานอะไรบ้างคะ", "session_id": "cal_test"})
        self.assertEqual(res_chat.status_code, 200)
        c = res_chat.json()
        self.assertTrue(c["is_calendar_query"])
        print("POST /api/test_chat: 200 OK")

    def test_08_calendar_timezone_and_allday_conversion(self):
        print("\n--- [Test 8] Testing UTC to Asia/Bangkok Timezone & AllDay Conversion ---")
        # 1. UTC to Asia/Bangkok time conversion
        self.assertEqual(parse_iso_to_bangkok_time("2026-09-12T01:00:00.000Z"), "08:00")
        self.assertEqual(parse_iso_to_bangkok_time("2026-09-12T11:00:00.000Z"), "18:00")
        self.assertEqual(parse_iso_to_bangkok_time("2026-09-12T13:30:00Z"), "20:30")

        # 2. All-Day event formatting ("ตลอดทั้งวัน")
        allday_event = {
            "title": "งานวันหยุดประจำสัปดาห์",
            "isAllDay": True,
            "startTime": "2026-09-12T17:00:00.000Z"
        }
        self.assertEqual(format_calendar_event_time_display(allday_event), "ตลอดทั้งวัน")

        # 3. Timed event formatting (range & single)
        timed_event = {
            "title": "ถ่ายงานโปรดักชั่น",
            "startTime": "2026-09-12T01:00:00.000Z",
            "endTime": "2026-09-12T05:00:00.000Z",
            "isAllDay": False
        }
        self.assertEqual(format_calendar_event_time_display(timed_event), "08:00 - 12:00 น.")

        single_time_event = {
            "title": "นัดคุยบรีฟ",
            "startTime": "2026-09-12T11:00:00.000Z"
        }
        self.assertEqual(format_calendar_event_time_display(single_time_event), "18:00 น.")

        # 4. Verify in Flex Bubble payload
        flex = build_calendar_reminder_flex_message([allday_event, timed_event])
        flex_str = json.dumps(flex, ensure_ascii=False)
        self.assertIn("ตลอดทั้งวัน", flex_str)
        self.assertIn("08:00 - 12:00 น.", flex_str)
        self.assertNotIn("17:00", flex_str)  # 17:00 raw slice must not appear

        # 5. Verify in rule-based briefing
        briefing = format_calendar_rule_based_briefing([allday_event, timed_event], "วันนี้")
        self.assertIn("ตลอดทั้งวัน", briefing)
        self.assertIn("08:00 - 12:00 น.", briefing)
        print("✅ Calendar Timezone & All-Day conversion verified successfully!")

    def test_09_loading_animation_group_guard(self):
        print("\n--- [Test 9] Testing send_line_loading_animation Group/Room Guard ---")
        with patch("line_bot_server.LINE_CHANNEL_ACCESS_TOKEN", "mock_token_abc"):
            # Group ID (starting with C) -> returns False immediately, no HTTP request made
            self.mock_post.reset_mock()
            res_group = send_line_loading_animation("Cd7b3d3b7a0fe061f341ec031c6edac8c", 30)
            self.assertFalse(res_group)
            self.mock_post.assert_not_called()

            # Room ID (starting with R) -> returns False immediately, no HTTP request made
            self.mock_post.reset_mock()
            res_room = send_line_loading_animation("R1234567890abcdef1234567890abcdef", 30)
            self.assertFalse(res_room)
            self.mock_post.assert_not_called()

            # Non-U ID -> returns False immediately, no HTTP request made
            self.mock_post.reset_mock()
            res_other = send_line_loading_animation("other_invalid_chat_id", 30)
            self.assertFalse(res_other)
            self.mock_post.assert_not_called()

            # User ID (starting with U) -> proceeds to call LINE Loading API
            self.mock_post.reset_mock()
            self.mock_post.return_value = MagicMock(status_code=200)
            res_user = send_line_loading_animation("U1234567890abcdef1234567890abcdef", 30)
            self.assertTrue(res_user)
            self.mock_post.assert_called_once()
            print("✅ Loading animation group/room guard verified successfully!")

    def test_10_is_agent_action_command_detection(self):
        print("\n--- [Test 10] Testing Action Command & Request Detection for Two-Stage UX ---")
        # Substantive queries / Inverted Exclusion Logic -> True
        self.assertTrue(is_agent_action_command("มีเอกสารอะไรค้างบ้าง"))
        self.assertTrue(is_agent_action_command("ลูกค้าจ่ายหรือยัง"))
        self.assertTrue(is_agent_action_command("ออกใบเสนอราคาให้บริษัทอบอุ่น"))
        self.assertTrue(is_agent_action_command("ช่วยคำนวณภาษี ยอด 30,000 บาท"))
        self.assertTrue(is_agent_action_command("วันนี้มีคิวงานอะไรบ้าง"))
        self.assertTrue(is_agent_action_command("GHN168 ขอเลขบัญชีธนาคารของบริษัทหน่อยครับ"))
        self.assertTrue(is_agent_action_command("บันทึก"))
        self.assertTrue(is_agent_action_command("ยืนยัน"))

        # Pure casual greetings / thank you -> False
        self.assertFalse(is_agent_action_command("สวัสดี"))
        self.assertFalse(is_agent_action_command("สวัสดีค่ะ"))
        self.assertFalse(is_agent_action_command("สวัสดีครับ"))
        self.assertFalse(is_agent_action_command("ขอบคุณครับ"))
        self.assertFalse(is_agent_action_command("ขอบคุณค่ะ"))
        self.assertFalse(is_agent_action_command("hi"))

        # Edge cases: empty / whitespace -> False
        self.assertFalse(is_agent_action_command(""))
        self.assertFalse(is_agent_action_command("   "))
        self.assertFalse(is_agent_action_command(" \t\n "))

        # Edge cases: punctuation & mixed Thai/English -> False
        self.assertFalse(is_agent_action_command("hi!"))
        self.assertFalse(is_agent_action_command("hello ครับ"))
        self.assertFalse(is_agent_action_command("thank you ค่ะ"))
        self.assertFalse(is_agent_action_command("สวัสดีครับ~"))

        # Edge cases: bot summon + pure greeting -> False
        self.assertFalse(is_agent_action_command("สวัสดีครับ เฟิส"))
        self.assertFalse(is_agent_action_command("เฟิส สวัสดีค่ะ"))
        self.assertFalse(is_agent_action_command("@เลขาเฟิส ดีจ้า"))

        # Edge cases: bot summon + substantive query -> True
        self.assertTrue(is_agent_action_command("เฟิส มีเอกสารอะไรค้างบ้าง"))
        self.assertTrue(is_agent_action_command("ออกใบเสนอราคา เฟิส"))

        print("✅ Inverted Exclusion Logic for action command detection verified successfully!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
