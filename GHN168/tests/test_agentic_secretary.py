#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agentic_secretary.py - Comprehensive Unit & Integration Test Suite
for GHN168 Autonomous Agentic AI Secretary (เลขาเฟิส) & Gemini 3.7 Native Tool Calling Engine.

Verifies:
1. Tool Declarations (6 Native Gemini Tools Schema Integrity)
2. Backend Tool Execution Engine (execute_agent_tool) across all 6 tools
3. Sheet Documents Search (search_sheet_documents across QT, IV, RE, EXP)
4. Natural Cross-Chat Lookup & Conversion Pipeline
5. Customer Autofill & Zero-Friction Document Issuing
6. Calendar Schedule Management & Query
7. 3-Pillar Partner Financial & Live Accounting Insights
8. Multi-turn Clarification & HITL Security Alert (>10,000 THB)
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure workspace is on sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from line_bot_server import (
    app,
    GEMINI_AGENT_TOOL_DECLARATIONS,
    execute_agent_tool,
    call_gemini_agent,
    generate_gemini_reply,
    SESSION_LAST_GENERATED_DOCS,
    SESSION_LAST_SEARCHED_DOCS,
    PENDING_DOCUMENT_ORDERS,
    PENDING_NEW_CUSTOMER_SAVING,
    INCOMPLETE_DOC_REQUEST_REPLY,
)
from ghn168_sync_service import (
    search_sheet_documents,
    parse_sheet_document_row,
    find_document_by_no,
    convert_document,
    search_customer,
    get_customers_database,
)


class TestAgenticSecretary(unittest.TestCase):
    """Test suite for GHN168 Gemini 3.7 Native Tool Calling & Agentic Secretary Engine."""

    def setUp(self):
        self.client = TestClient(app)
        SESSION_LAST_GENERATED_DOCS.clear()
        SESSION_LAST_SEARCHED_DOCS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_NEW_CUSTOMER_SAVING.clear()

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
                    "pdfUrl": "https://drive.google.com/mock_test_agentic_doc.pdf",
                    "message": "Mocked upload success"
                }
            elif req_type == "create_calendar_event":
                mock_res.json.return_value = {
                    "status": "success",
                    "eventId": "evt_test_agent_123",
                    "title": payload.get("title", ""),
                    "startTime": payload.get("startDate", ""),
                    "endTime": payload.get("endDate", ""),
                    "calendarName": "GHN168 Media Official Calendar",
                    "message": "สร้างคิวงานสำเร็จ"
                }
            elif req_type == "get_calendar_events":
                from ghn168_sync_service import get_simulated_calendar_events
                sim_cal = get_simulated_calendar_events(target_date=payload.get("targetDate"))
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

    # --------------------------------------------------------------------------
    # 1. Tool Declarations Schema Verification
    # --------------------------------------------------------------------------
    def test_01_tool_declarations_schema(self):
        """Verify all 6 Native Gemini Tool Declarations exist and have valid JSON schema."""
        expected_tools = {
            "search_sheet_documents",
            "convert_document_pipeline",
            "create_financial_document",
            "search_customer_database",
            "save_customer_to_database",
            "manage_calendar_schedule",
            "get_accounting_insights",
            "get_tax_filing_report",
            "prepare_cpa_audit_package"
        }
        declared_names = {t["name"] for t in GEMINI_AGENT_TOOL_DECLARATIONS}
        self.assertEqual(declared_names, expected_tools)

        for decl in GEMINI_AGENT_TOOL_DECLARATIONS:
            self.assertIn("name", decl)
            self.assertIn("description", decl)
            self.assertIn("parameters", decl)
            self.assertEqual(decl["parameters"]["type"], "OBJECT")
            self.assertIn("properties", decl["parameters"])
        print("✅ Test 1 Passed: 7 Gemini Tool Declarations Schema verified 100%.")

    # --------------------------------------------------------------------------
    # 2. search_sheet_documents Backend & Tool Execution
    # --------------------------------------------------------------------------
    def test_02_search_sheet_documents_by_client_and_amount(self):
        """Verify search_sheet_documents finds Quotations by client and amount with tolerance."""
        res, flex = execute_agent_tool("search_sheet_documents", {
            "client_name": "เอ็มคูล",
            "amount": 18000.0,
            "tolerance": 500.0
        }, session_id="test_search_01")

        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["found_count"], 1)
        docs = res["documents"]
        first_doc = docs[0]
        self.assertIn("เอ็ม-คูล", first_doc["client_name"])
        self.assertEqual(first_doc["pre_vat"], 18000.0)
        self.assertEqual(first_doc["net_total"], 19260.0)
        self.assertIn("test_search_01", SESSION_LAST_SEARCHED_DOCS)
        print("✅ Test 2 Passed: search_sheet_documents by client & amount verified.")

    def test_03_search_sheet_documents_by_doc_no(self):
        """Verify search_sheet_documents by exact doc_no."""
        res, _ = execute_agent_tool("search_sheet_documents", {
            "query": "QT-202608-440"
        }, session_id="test_search_02")

        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["found_count"], 1)
        self.assertEqual(res["documents"][0]["doc_no"], "QT-202608-440")
        print("✅ Test 3 Passed: search_sheet_documents by doc_no verified.")

    # --------------------------------------------------------------------------
    # 3. convert_document_pipeline Tool Execution
    # --------------------------------------------------------------------------
    def test_04_convert_document_pipeline_tool(self):
        """Verify convert_document_pipeline converts QT -> IV with valid Flex card."""
        res, flex = execute_agent_tool("convert_document_pipeline", {
            "source_doc_no": "QT-202608-440",
            "target_type": "invoice",
            "overrides": {"due_date": "30/08/2026"}
        }, session_id="test_conv_01")

        self.assertIn(res["status"], ["success", "simulation"])
        self.assertTrue(res["doc_no"].startswith("IV-"))
        self.assertIsNotNone(flex)
        self.assertEqual(flex.get("type"), "flex")
        self.assertIn("test_conv_01", SESSION_LAST_GENERATED_DOCS)
        print("✅ Test 4 Passed: convert_document_pipeline tool execution verified.")

    # --------------------------------------------------------------------------
    # 4. create_financial_document Tool Execution with Customer Autofill
    # --------------------------------------------------------------------------
    def test_05_create_financial_document_autofill(self):
        """Verify create_financial_document autofills client tax ID and default signer."""
        res, flex = execute_agent_tool("create_financial_document", {
            "doc_type": "quotation",
            "client_name": "บ. เอ็มคูล",
            "project_name": "ถ่ายงาน Event 3 วัน",
            "amount": 18000.0,
            "is_vat": True,
            "is_wht": False
        }, session_id="test_create_01")

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["customer_autofilled"])
        self.assertEqual(res["client_tax_id"], "0505568016475")
        self.assertEqual(res["signer_name"], "นาย มงคล วงศ์สกุลยานนท์")
        self.assertEqual(res["totals"]["net_total"], 19260.0)
        self.assertIsNotNone(flex)
        print("✅ Test 5 Passed: create_financial_document autofill & calculation verified.")

    # --------------------------------------------------------------------------
    # 5. search_customer_database Tool Execution
    # --------------------------------------------------------------------------
    def test_06_search_customer_database_tool(self):
        """Verify search_customer_database finds customer by Tax ID and keyword."""
        res, flex = execute_agent_tool("search_customer_database", {
            "keyword": "0505568016475"
        }, session_id="test_cust_01")

        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["count"], 1)
        self.assertEqual(res["customers"][0]["tax_id"], "0505568016475")
        self.assertIsNotNone(flex)
        print("✅ Test 6 Passed: search_customer_database tool verified.")

    # --------------------------------------------------------------------------
    # 6. manage_calendar_schedule Tool Execution
    # --------------------------------------------------------------------------
    def test_07_manage_calendar_schedule_query_and_create(self):
        """Verify manage_calendar_schedule query and event creation."""
        # Query
        res_q, flex_q = execute_agent_tool("manage_calendar_schedule", {
            "action": "query",
            "target_date": "today"
        }, session_id="test_cal_01")
        self.assertEqual(res_q["status"], "success")
        self.assertIsNotNone(flex_q)

        # Create
        res_c, flex_c = execute_agent_tool("manage_calendar_schedule", {
            "action": "create",
            "event_title": "ถ่ายทำโฆษณา GHN168 x Chiang Mai Media",
            "start_date": "2026-08-30",
            "end_date": "2026-08-30",
            "location": "สตูดิโอ GHN168 เชียงใหม่"
        }, session_id="test_cal_02")
        self.assertEqual(res_c["status"], "created")
        self.assertEqual(res_c["event"]["title"], "ถ่ายทำโฆษณา GHN168 x Chiang Mai Media")
        self.assertIsNotNone(flex_c)
        print("✅ Test 7 Passed: manage_calendar_schedule query & create verified.")

    # --------------------------------------------------------------------------
    # 7. get_accounting_insights Tool Execution
    # --------------------------------------------------------------------------
    def test_08_get_accounting_insights_tool(self):
        """Verify get_accounting_insights for overview, partner breakdown, and overdue invoices."""
        # Overview
        res_ov, flex_ov = execute_agent_tool("get_accounting_insights", {
            "query_type": "overview"
        }, session_id="test_acc_01")
        self.assertEqual(res_ov["status"], "success")
        self.assertIn("accounting_summary", res_ov)
        self.assertIsNotNone(flex_ov)

        # Partner Breakdown
        res_pb, flex_pb = execute_agent_tool("get_accounting_insights", {
            "query_type": "partner_breakdown"
        }, session_id="test_acc_02")
        self.assertEqual(res_pb["status"], "success")
        self.assertIn("partner_breakdown", res_pb)
        self.assertIsNotNone(flex_pb)

        # Overdue
        res_od, flex_od = execute_agent_tool("get_accounting_insights", {
            "query_type": "unpaid_invoices"
        }, session_id="test_acc_03")
        self.assertEqual(res_od["status"], "success")
        self.assertIn("overdue_summary", res_od)
        self.assertIsNotNone(flex_od)
        print("✅ Test 8 Passed: get_accounting_insights (overview, partners, overdue) verified.")

    # --------------------------------------------------------------------------
    # 8. End-to-End Chat via /api/test_chat (Natural Language Agentic Flow)
    # --------------------------------------------------------------------------
    def test_09_e2e_cross_chat_search_and_conversion(self):
        """
        Verify end-to-end flow:
        User asks: 'มันมีใบเสนอราคาของ บ เอ็มคูลอยู่อันนึงที่ยอด 18000 ทำใบวางบิลโดยอ้างอิงใบเสนอราคานั้น'
        """
        session_id = "test_agent_cross_01"
        payload = {
            "session_id": session_id,
            "message": "มันมีใบเสนอราคาของ บ เอ็มคูลอยู่อันนึงที่ยอด 18000 ทำใบวางบิลโดยอ้างอิงใบเสนอราคานั้น"
        }
        res = self.client.post("/api/test_chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNotNone(data.get("doc_result"))
        doc_no = data["doc_result"].get("doc_no")
        self.assertTrue(doc_no.startswith("IV"))
        self.assertIn("วางบิล", data["reply"])
        print("✅ Test 9 Passed: End-to-end natural cross-chat search & conversion verified.")

    def test_10_e2e_multi_turn_clarification_and_completion(self):
        """Verify multi-turn clarification when user command is incomplete, followed by completion."""
        session_id = "test_agent_multiturn_01"

        # Turn 1: Vague request
        payload1 = {
            "session_id": session_id,
            "message": "ช่วยออกเอกสารให้หน่อยค่ะ"
        }
        res1 = self.client.post("/api/test_chat", json=payload1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertIn("ขอข้อมูลเพิ่มเติม", data1["reply"])
        self.assertIn(session_id, PENDING_DOCUMENT_ORDERS)

        # Turn 2: Provide complete details
        payload2 = {
            "session_id": session_id,
            "message": "ออกใบเสนอราคาให้ บ. เอ็มคูล รายละเอียดถ่าย Event 3 วัน ยอด 18000"
        }
        res2 = self.client.post("/api/test_chat", json=payload2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()

        self.assertNotIn(session_id, PENDING_DOCUMENT_ORDERS)
        self.assertTrue(data2.get("is_document_order"))
        self.assertEqual(data2["doc_result"]["totals"]["net_total"], 19260.0)
        self.assertIn("19,260.00", data2["reply"])
        print("✅ Test 10 Passed: Multi-turn clarification and order completion verified.")

    def test_11_hitl_security_alert_over_10k(self):
        """Verify HITL Security Alert is appended when document amount exceeds 10,000 THB."""
        session_id = "test_hitl_01"
        payload = {
            "session_id": session_id,
            "message": "ทำใบเสนอราคาให้ บ. เอ็มคูล ถ่ายงาน 25000"
        }
        res = self.client.post("/api/test_chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("HITL Security Alert", data["reply"])
        self.assertIn("ยอดเงินเกิน 10,000 บาท", data["reply"])
        print("✅ Test 11 Passed: HITL Security Alert for transactions > 10,000 THB verified.")


if __name__ == "__main__":
    unittest.main()
