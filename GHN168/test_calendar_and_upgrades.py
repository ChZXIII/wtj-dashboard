import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
)
from ghn168_sync_service import (
    get_calendar_events,
    get_simulated_calendar_events,
)


class TestGHN168MegaUpgrades(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_session = "test_session_upgrade_verification"
        CONVERSATION_HISTORY.clear()
        LAST_CALENDAR_REMINDER_DATE.clear()

    def test_01_configuration_and_model_version(self):
        print("\n--- [Test 1] Checking Model & Chat History Config ---")
        self.assertEqual(GEMINI_MODEL, "gemini-3.7-flash")
        self.assertEqual(MAX_HISTORY_PER_SESSION, 50)
        print("Model: " + GEMINI_MODEL)
        print("Max History: " + str(MAX_HISTORY_PER_SESSION))

    def test_02_chat_history_expansion(self):
        print("\n--- [Test 2] Testing 50-Message History Sliding Window ---")
        for i in range(65):
            role = "user" if i % 2 == 0 else "model"
            append_to_history(self.test_session, role, "Message #" + str(i+1))

        history = get_history(self.test_session)
        self.assertEqual(len(history), 50)
        self.assertEqual(history[-1]["text"], "Message #65")
        self.assertEqual(history[0]["text"], "Message #16")
        print("50-message memory window verified.")

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
        self.assertEqual(h["gemini_model"], "gemini-3.7-flash")
        self.assertEqual(h["thinking_budget"], 512)
        self.assertEqual(h["max_history_per_session"], 50)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
