#!/usr/bin/env python3
"""
================================================================================
GHN168 Full-Option Features Comprehensive Test Suite (v3.0)
================================================================================
Executive Secretary & Financial Engine (v3.0) 100% Coverage Test Suite:
1. 🔄 Document Lifecycle Pipeline (QT -> IV -> RE -> 50 ทวิ)
2. 💳 Customer Slip Scanner (Income Slip vs Expense OCR & Matching)
3. ⏰ Overdue & Aging Invoice Tracker (09:30 AM Daily Scheduler & Templates)
4. 📅 Google Calendar Creation via Chat
5. 📊 3-Pillar Partner Financial Engine (Hunter, Labor, Vault)
6. 👥 Customer Database & Proactive Tax Reminders
================================================================================
"""

import base64
import json
import unittest
from datetime import datetime, date
from fastapi.testclient import TestClient

from line_bot_server import (
    app,
    TAX_REMINDER_SCHEDULES,
    trigger_scheduled_tax_reminder,
    check_and_run_daily_tax_reminders,
    check_and_run_daily_overdue_tracker,
    build_tax_reminder_flex_message,
    build_expense_ocr_flex_message,
    build_income_slip_flex_message,
    build_overdue_invoices_flex_message,
    build_calendar_event_created_flex_message,
    build_document_conversion_flex_message,
    build_partner_hunter_flex_message,
    build_partner_labor_flex_message,
    build_partner_vault_flex_message,
    build_partner_all_in_one_financial_flex_message,
    analyze_receipt_image_with_ai,
    match_incoming_slip_with_invoice,
    is_document_conversion_request,
    is_overdue_invoices_request,
    is_create_calendar_request,
    is_partner_financial_request,
    is_accounting_summary_request,
    is_customer_query_request
)
from ghn168_sync_service import (
    convert_document,
    create_calendar_event,
    find_document_by_no,
    get_overdue_and_aging_invoices,
    get_partner_financial_breakdown,
    get_live_accounting_summary,
    get_customers_database,
    search_customer,
    read_sheet_data
)

client = TestClient(app)


class TestGHN168ExecutiveV3(unittest.TestCase):
    """Complete End-to-End Test Suite for GHN168 v3.0."""

    # --------------------------------------------------------------------------
    # 1. Document Lifecycle Pipeline
    # --------------------------------------------------------------------------
    def test_document_pipeline_qt_to_iv_to_re(self):
        """Test complete pipeline from QT -> IV -> RE."""
        # Step 1: QT -> IV
        iv_res = convert_document("QT2608-001", "invoice")
        self.assertIn(iv_res["status"], ["success", "simulation"])
        self.assertEqual(iv_res["target_type"], "invoice")
        self.assertIn("IV", iv_res["doc_no"])
        self.assertEqual(iv_res["totals"]["net_total"], 53500.0)

        # Step 2: IV -> RE
        re_res = convert_document(iv_res["doc_no"], "receipt")
        self.assertIn(re_res["status"], ["success", "simulation"])
        self.assertEqual(re_res["target_type"], "receipt")
        self.assertIn("RE", re_res["doc_no"])

    def test_document_conversion_intent_recognition(self):
        """Test chat intents for document lifecycle."""
        # QT -> IV
        is_c1, src1, tgt1, _ = is_document_conversion_request("วางบิลงานเอ็มคูล")
        self.assertTrue(is_c1)
        self.assertEqual(tgt1, "invoice")

        # IV -> RE
        is_c2, src2, tgt2, _ = is_document_conversion_request("เอ็มคูลโอนแล้ว ออกใบเสร็จ")
        self.assertTrue(is_c2)
        self.assertEqual(tgt2, "receipt")

        # 50 ทวิ
        is_c3, src3, tgt3, ov3 = is_document_conversion_request("ออก 50 ทวิ จ้างนักแสดง สมชาย ยอด 15000")
        self.assertTrue(is_c3)
        self.assertEqual(tgt3, "wht")
        self.assertEqual(ov3["amount"], 15000.0)

    # --------------------------------------------------------------------------
    # 2. Customer Slip Scanner (Income vs Expense)
    # --------------------------------------------------------------------------
    def test_match_incoming_slip_with_invoice(self):
        """Test matching incoming payment slip with pending invoices."""
        # Match 52,000 THB to Chiang Mai Media invoice
        matched = match_incoming_slip_with_invoice(52000.0, "เชียงใหม่มีเดีย")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["net_total"], 52000.0)
        self.assertIn("เชียงใหม่มีเดีย", matched["client_name"])

    def test_income_slip_flex_card_builder(self):
        """Test income slip flex card generation."""
        slip_sample = {
            "transaction_type": "income",
            "amount": 52000.0,
            "sender_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "sender_bank": "ธนาคารกสิกรไทย",
            "transfer_date": "23/08/2026",
            "transfer_time": "14:20:00"
        }
        matched_sample = {
            "doc_no": "IV2608-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "net_total": 52000.0
        }
        card = build_income_slip_flex_message(slip_sample, matched_sample)
        self.assertEqual(card["type"], "flex")
        self.assertEqual(card["contents"]["header"]["backgroundColor"], "#059669")

    # --------------------------------------------------------------------------
    # 3. Overdue & Aging Invoice Tracker
    # --------------------------------------------------------------------------
    def test_overdue_and_aging_calculation(self):
        """Test overdue invoice categorization into aging buckets."""
        overdue_data = get_overdue_and_aging_invoices()
        self.assertEqual(overdue_data["status"], "success")
        self.assertIn("total_overdue_count", overdue_data)
        self.assertIn("overdue_buckets", overdue_data)
        self.assertIn("all_overdue_list", overdue_data)

        # Check polite follow-up reminder draft
        if overdue_data["all_overdue_list"]:
            sample_draft = overdue_data["all_overdue_list"][0]["draft_message"]
            self.assertIn("เรียนแจ้งทาง", sample_draft)
            self.assertIn("520-0-61960-2", sample_draft)

    def test_overdue_intent_and_api(self):
        """Test overdue intent detection and API endpoint."""
        self.assertTrue(is_overdue_invoices_request("เช็กบิลค้างชำระ"))
        self.assertTrue(is_overdue_invoices_request("ตามเงินลูกค้า"))
        self.assertTrue(is_overdue_invoices_request("ทวงเงิน"))

        resp = client.get("/api/invoices/check_overdue")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    # --------------------------------------------------------------------------
    # 4. Google Calendar Creation via Chat
    # --------------------------------------------------------------------------
    def test_create_calendar_event_intent_and_execution(self):
        """Test calendar event intent extraction and creation."""
        text = "ลงคิวถ่ายงานเอ็มคูล วันที่ 28-30 ส.ค. ช่างภาพเก่ง+หอม"
        is_cal, params = is_create_calendar_request(text)
        self.assertTrue(is_cal)
        self.assertIn("2026-08-28", params["start_date"])
        self.assertIn("2026-08-30", params["end_date"])

        cal_res = create_calendar_event(
            title=params["title"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            description=params["description"]
        )
        self.assertIn(cal_res["status"], ["success", "simulation"])
        self.assertIn("eventId", cal_res)

        card = build_calendar_event_created_flex_message(cal_res)
        self.assertEqual(card["type"], "flex")

    # --------------------------------------------------------------------------
    # 5. 3-Pillar Partner Financial Engine
    # --------------------------------------------------------------------------
    def test_3_pillar_partner_financial_engine(self):
        """Test all 3 pillars of Partner Financial Engine."""
        breakdown = get_partner_financial_breakdown()
        self.assertEqual(breakdown["status"], "success")

        # Pillar 1
        p1 = breakdown["pillar_1_lead_hunters"]
        self.assertEqual(len(p1["leaderboard"]), 4)
        self.assertGreater(p1["total_gross_volume"], 0)

        # Pillar 2
        p2 = breakdown["pillar_2_labor_earned"]
        self.assertEqual(len(p2["partners"]), 4)
        self.assertGreater(p2["total_labor_ytd"], 0)

        # Pillar 3
        p3 = breakdown["pillar_3_personal_vault"]
        self.assertEqual(p3["corporate_central_pool"], 450000.0)
        self.assertGreater(p3["total_partner_vaults"], 0)

    def test_partner_financial_endpoints(self):
        """Test REST API endpoints for partner financial breakdown."""
        endpoints = [
            "/api/partners/financial_breakdown",
            "/api/partners/hunter",
            "/api/partners/labor",
            "/api/partners/vault"
        ]
        for ep in endpoints:
            r = client.get(ep)
            self.assertEqual(r.status_code, 200, f"Endpoint {ep} must return 200 OK")
            self.assertEqual(r.json()["status"], "success")

    # --------------------------------------------------------------------------
    # 6. Customer Database & Tax Reminders
    # --------------------------------------------------------------------------
    def test_customer_database_search(self):
        """Test searching customer database."""
        custs = get_customers_database()
        self.assertGreaterEqual(len(custs), 4)

        found = search_customer("เชียงใหม่มีเดีย")
        self.assertIsNotNone(found)
        self.assertEqual(found["tax_id"], "0505560000123")

    def test_tax_reminders_scheduler(self):
        """Test tax reminder schedules."""
        self.assertEqual(len(TAX_REMINDER_SCHEDULES), 6)
        res = trigger_scheduled_tax_reminder("monthly_bills_25")
        self.assertEqual(res["status"], "success")


if __name__ == "__main__":
    unittest.main()
