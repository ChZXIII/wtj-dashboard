#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Monthly Tax Scheduler (28th and 1st of every month at 15:00)
Testing Real-time VAT & WHT extraction, LINE Flex message generation, and background checker deduplication.
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from line_bot_server import (
    app,
    TAX_REMINDER_SCHEDULES,
    LAST_REMINDER_DATES,
    trigger_scheduled_tax_reminder,
    check_and_run_daily_tax_reminders,
    build_tax_reminder_flex_message,
    validate_line_flex_payload,
)


class TestTaxScheduler28And01(unittest.TestCase):
    def setUp(self):
        # Clear trigger cache for clean test runs
        LAST_REMINDER_DATES.clear()
        self.client = TestClient(app)

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
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}

            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_tax_reminder_schedules_configured(self):
        """Verify that monthly_tax_28 and monthly_tax_01 are properly defined in TAX_REMINDER_SCHEDULES."""
        self.assertIn("monthly_tax_28", TAX_REMINDER_SCHEDULES)
        self.assertIn("monthly_tax_01", TAX_REMINDER_SCHEDULES)

        sched_28 = TAX_REMINDER_SCHEDULES["monthly_tax_28"]
        self.assertEqual(sched_28["badge_color"], "#dc2626")
        self.assertIn("สิ้นเดือน", sched_28["title"])

        sched_01 = TAX_REMINDER_SCHEDULES["monthly_tax_01"]
        self.assertEqual(sched_01["badge_color"], "#7c3aed")
        self.assertIn("ต้นเดือน", sched_01["title"])

    def test_trigger_monthly_tax_28(self):
        """Test trigger_scheduled_tax_reminder for 28th month-end tax summary."""
        mock_summary = {
            "status": "success",
            "month": 8,
            "year": 2026,
            "period_label": "08/2026",
            "summary": {
                "total_income_vat_output": 21000.0,
                "total_expense_vat_input": 7000.0,
                "net_vat_balance": 14000.0,
                "total_income_wht_deducted": 9000.0,
                "total_expense_wht_withheld": 3000.0
            }
        }
        with patch("line_bot_server.get_live_accounting_summary", return_value=mock_summary):
            res = trigger_scheduled_tax_reminder("monthly_tax_28")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["reminder_type"], "monthly_tax_28")

            # Check text contains required live metrics
            msg = res["message_text"]
            self.assertIn("21,000.00", msg)
            self.assertIn("7,000.00", msg)
            self.assertIn("14,000.00", msg)
            self.assertIn("9,000.00", msg)
            self.assertIn("3,000.00", msg)
            self.assertIn("ต้องนำส่งภาษีเพิ่ม", msg)

            # Check Flex Message card validity
            flex_card = res["flex_card"]
            self.assertTrue(validate_line_flex_payload(flex_card))

    def test_trigger_monthly_tax_01_with_credit_vat(self):
        """Test trigger_scheduled_tax_reminder for 1st month-start reconciliation when input VAT > output VAT."""
        mock_summary = {
            "status": "success",
            "month": 7,
            "year": 2026,
            "period_label": "07/2026",
            "summary": {
                "total_income_vat_output": 5000.0,
                "total_expense_vat_input": 12000.0,
                "net_vat_balance": -7000.0,
                "total_income_wht_deducted": 1500.0,
                "total_expense_wht_withheld": 4000.0
            }
        }
        with patch("line_bot_server.get_live_accounting_summary", return_value=mock_summary):
            res = trigger_scheduled_tax_reminder("monthly_tax_01")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["reminder_type"], "monthly_tax_01")

            msg = res["message_text"]
            self.assertIn("5,000.00", msg)
            self.assertIn("12,000.00", msg)
            self.assertIn("7,000.00", msg)
            self.assertIn("มีภาษีซื้อยกไป", msg)
            self.assertIn("สำนักงานบัญชี", msg)

            flex_card = res["flex_card"]
            self.assertTrue(validate_line_flex_payload(flex_card))

    def test_build_tax_reminder_flex_message_variants(self):
        """Test build_tax_reminder_flex_message with various net VAT conditions."""
        # 1. Zero balance VAT
        mock_zero_vat = {
            "status": "success",
            "period_label": "08/2026",
            "summary": {
                "total_income_vat_output": 10000.0,
                "total_expense_vat_input": 10000.0,
                "net_vat_balance": 0.0,
                "total_income_wht_deducted": 2000.0,
                "total_expense_wht_withheld": 2000.0
            }
        }
        card_zero = build_tax_reminder_flex_message("monthly_tax_28", acc_data=mock_zero_vat)
        self.assertTrue(validate_line_flex_payload(card_zero))

        # 2. Standard informational card (e.g. monthly_bills_25)
        card_bills = build_tax_reminder_flex_message("monthly_bills_25")
        self.assertTrue(validate_line_flex_payload(card_bills))

    def test_check_and_run_daily_tax_reminders_28th(self):
        """Test scheduler background trigger on 28th at 15:00 and deduplication."""
        # Outside trigger window on 28th (e.g. 14:59) -> Should not trigger
        dt_1459 = datetime(2026, 8, 28, 14, 59)
        triggered = check_and_run_daily_tax_reminders(now_dt=dt_1459)
        self.assertNotIn("monthly_tax_28", triggered)

        # In trigger window on 28th at 15:00 -> Should trigger
        dt_1500 = datetime(2026, 8, 28, 15, 0)
        with patch("line_bot_server.trigger_scheduled_tax_reminder") as mock_trigger:
            mock_trigger.return_value = {"status": "success"}
            triggered = check_and_run_daily_tax_reminders(now_dt=dt_1500)
            self.assertIn("monthly_tax_28", triggered)
            mock_trigger.assert_called_with("monthly_tax_28")

        # In trigger window at 15:01 on same day -> Should NOT trigger again due to deduplication
        dt_1501 = datetime(2026, 8, 28, 15, 1)
        with patch("line_bot_server.trigger_scheduled_tax_reminder") as mock_trigger:
            triggered = check_and_run_daily_tax_reminders(now_dt=dt_1501)
            self.assertNotIn("monthly_tax_28", triggered)
            mock_trigger.assert_not_called()

    def test_check_and_run_daily_tax_reminders_01st(self):
        """Test scheduler background trigger on 1st at 15:00 and deduplication."""
        # In trigger window on 1st at 15:00 -> Should trigger
        dt_1500 = datetime(2026, 9, 1, 15, 0)
        with patch("line_bot_server.trigger_scheduled_tax_reminder") as mock_trigger:
            mock_trigger.return_value = {"status": "success"}
            triggered = check_and_run_daily_tax_reminders(now_dt=dt_1500)
            self.assertIn("monthly_tax_01", triggered)
            mock_trigger.assert_any_call("monthly_tax_01")

        # In trigger window at 15:01 on same day -> Deduplicated
        dt_1501 = datetime(2026, 9, 1, 15, 1)
        with patch("line_bot_server.trigger_scheduled_tax_reminder") as mock_trigger:
            triggered = check_and_run_daily_tax_reminders(now_dt=dt_1501)
            self.assertNotIn("monthly_tax_01", triggered)
            mock_trigger.assert_not_called()

    def test_api_tax_reminders_status_and_trigger(self):
        """Test FastAPI tax reminder REST API endpoints."""
        # 1. GET /api/tax_reminders/status
        res_status = self.client.get("/api/tax_reminders/status")
        self.assertEqual(res_status.status_code, 200)
        data = res_status.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("monthly_tax_28", data["schedules"])
        self.assertIn("monthly_tax_01", data["schedules"])

        # 2. POST /api/tax_reminders/trigger
        res_trigger = self.client.post("/api/tax_reminders/trigger", json={
            "reminder_type": "monthly_tax_28"
        })
        self.assertEqual(res_trigger.status_code, 200)
        trig_data = res_trigger.json()
        self.assertEqual(trig_data["status"], "success")
        self.assertEqual(trig_data["reminder_type"], "monthly_tax_28")


if __name__ == "__main__":
    unittest.main()
