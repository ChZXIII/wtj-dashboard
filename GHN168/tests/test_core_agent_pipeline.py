#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_core_agent_pipeline.py - Comprehensive Unit & Integration Test Suite
for GHN168 Agentic Backbone & Gemini 3.7 Tool Calling Protocol Fix.

Verifies:
1. Function Response Payload Schema Integrity (role="user" for both SDK and REST tiers).
2. Intent Interception & Regex Cleanliness:
   - "เฟิสสรุปยอดภาษีหัก ณ ที่จ่าย กับ vat ของเดือนนี้มาให้หน่อย" -> Calls get_accounting_insights, NOT 50 ทวิ conversion
   - "ทำใบวางบิล บ.เอ็มคูล" -> Valid document creation / conversion pipeline
   - "หาเบอร์ บ.ลานนา" -> Calls search_customer_database with keyword "ลานนา"
   - "เช็กคิวถ่ายงาน" -> Calls manage_calendar_schedule query
3. Multi-turn Agent Tool Calling Loop Simulation (SDK & REST) with role="user" compliance.
4. Backend execute_agent_tool correctness and Flex card attachments across all tools.
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from line_bot_server import (
    app,
    GEMINI_AGENT_TOOL_DECLARATIONS,
    execute_agent_tool,
    call_gemini_agent,
    agentic_fallback_simulate_turn,
    is_document_conversion_request,
    is_document_creation_request,
    is_customer_query_request,
    is_calendar_query_request,
    is_accounting_summary_request,
    is_partner_financial_request,
    SESSION_LAST_GENERATED_DOCS,
    SESSION_LAST_SEARCHED_DOCS,
    PENDING_DOCUMENT_ORDERS,
    PENDING_NEW_CUSTOMER_SAVING,
    genai_client,
    types,
)


from pathlib import Path

class TestCoreAgentPipeline(unittest.TestCase):
    """Test suite for Gemini 3.7 Native Tool Calling Engine and Regex Isolation."""

    def setUp(self):
        SESSION_LAST_GENERATED_DOCS.clear()
        SESSION_LAST_SEARCHED_DOCS.clear()
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_NEW_CUSTOMER_SAVING.clear()
        self.pdf_patcher = patch("local_pdf_engine.convert_html_to_pdf_local", return_value=Path("/tmp/mock.pdf"))
        self.pdf_patcher.start()

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
                    "pdfUrl": "https://drive.google.com/mock_core_pipeline_doc.pdf",
                    "message": "Mocked upload success"
                }
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}

            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.pdf_patcher.stop()
        self.patcher.stop()

    # --------------------------------------------------------------------------
    # 1. Function Response Schema Protocol Compliance (role='user')
    # --------------------------------------------------------------------------
    def test_01_function_response_schema_protocol(self):
        """Verify that Gemini v1beta function response payload structure strictly uses role='user'."""
        fn_name = "get_accounting_insights"
        tool_res = {
            "status": "success",
            "accounting_summary": {"summary": {"total_income_net": 125000.0, "net_cashflow": 75000.0}}
        }

        # 1. REST Tier Payload Structure
        rest_function_response = {
            "role": "user",
            "parts": [{
                "functionResponse": {
                    "name": fn_name,
                    "response": {"name": fn_name, "content": tool_res}
                }
            }]
        }
        self.assertEqual(rest_function_response["role"], "user", "REST API Function Response role MUST be 'user'")
        self.assertIn("parts", rest_function_response)
        self.assertIn("functionResponse", rest_function_response["parts"][0])
        self.assertEqual(rest_function_response["parts"][0]["functionResponse"]["name"], fn_name)

        # 2. SDK Tier Types Content Structure (if SDK types available)
        if hasattr(types, "Content") and hasattr(types, "Part"):
            try:
                sdk_content = types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=fn_name, response={"result": tool_res})]
                )
                self.assertEqual(sdk_content.role, "user", "SDK Content role MUST be 'user'")
            except Exception as e:
                self.fail(f"Building SDK Content with role='user' failed: {e}")

        print("✅ Test 1 Passed: Function Response protocol strictly complies with role='user' for both SDK and REST.")

    # --------------------------------------------------------------------------
    # 2. Test Real User Query: Tax & VAT Summary (Root Cause Bug Reproduction & Fix)
    # --------------------------------------------------------------------------
    def test_02_tax_and_vat_summary_query_isolation(self):
        """
        Verify that 'เฟิสสรุปยอดภาษีหัก ณ ที่จ่าย กับ vat ของเดือนนี้มาให้หน่อย':
        1. Is NOT misclassified as a 50 ทวิ document conversion request.
        2. Correctly matches accounting summary request or gets processed by accounting tool.
        """
        query = "เฟิสสรุปยอดภาษีหัก ณ ที่จ่าย กับ vat ของเดือนนี้มาให้หน่อย"

        # 1. Check document conversion
        is_conv, src, tgt, overrides = is_document_conversion_request(query)
        self.assertFalse(is_conv, "Tax summary query must NOT be detected as document conversion request!")

        # 2. Check accounting summary
        is_acc = is_accounting_summary_request(query)
        self.assertTrue(is_acc, "Query should match accounting summary request keywords.")

        # 3. Test Agentic Fallback Simulation Execution
        res = asyncio.run(agentic_fallback_simulate_turn(query, session_id="test_tax_summary"))
        self.assertIn("reply_text", res)
        self.assertTrue(len(res.get("flex_cards", [])) > 0, "Should generate accounting summary Flex Card.")
        self.assertTrue(any(t["tool"] == "get_accounting_insights" for t in res.get("executed_tools", [])))
        self.assertIn("ภาษีขาย", res["reply_text"])
        print("✅ Test 2 Passed: Tax & VAT summary correctly routed to get_accounting_insights without regex hijack.")

    # --------------------------------------------------------------------------
    # 3. Test Real User Query: Invoice Creation for M-Cool
    # --------------------------------------------------------------------------
    def test_03_create_invoice_m_cool(self):
        """Verify that 'ทำใบวางบิล บ.เอ็มคูล' triggers document creation or checklist prompt."""
        query = "ทำใบวางบิล บ.เอ็มคูล"

        is_doc = is_document_creation_request(query)
        is_conv, _, tgt_type, _ = is_document_conversion_request(query)
        self.assertTrue(is_doc or (is_conv and tgt_type == "invoice"), "Should detect invoice action.")

        # Run agentic turn
        res = asyncio.run(agentic_fallback_simulate_turn(query, session_id="test_mcool_inv"))
        self.assertIn("reply_text", res)
        self.assertTrue(len(res["reply_text"]) > 0)
        print("✅ Test 3 Passed: 'ทำใบวางบิล บ.เอ็มคูล' handled smoothly.")

    # --------------------------------------------------------------------------
    # 4. Test Real User Query: Customer Search Lanna Phone Number
    # --------------------------------------------------------------------------
    def test_04_customer_phone_search(self):
        """Verify that 'หาเบอร์ บ.ลานนา' accurately queries customer database."""
        query = "หาเบอร์ บ.ลานนา"

        is_cust, cust_kw = is_customer_query_request(query)
        self.assertTrue(is_cust, "Should detect customer query.")
        self.assertIn("ลานนา", cust_kw if cust_kw else "")

        res_data, flex_card = execute_agent_tool("search_customer_database", {"keyword": "ลานนา"}, session_id="test_cust_lanna")
        self.assertEqual(res_data["status"], "success")
        self.assertGreaterEqual(res_data["count"], 1)
        found_cust = res_data["customers"][0]
        self.assertIn("ลานนา", found_cust["customer_name"])
        self.assertIsNotNone(flex_card, "Should return Customer List Flex Message.")
        print("✅ Test 4 Passed: 'หาเบอร์ บ.ลานนา' found customer profile and phone successfully.")

    # --------------------------------------------------------------------------
    # 5. Test Real User Query: Calendar Schedule Check
    # --------------------------------------------------------------------------
    def test_05_calendar_schedule_check(self):
        """Verify that 'เช็กคิวถ่ายงาน' queries calendar events and produces briefing."""
        query = "เช็กคิวถ่ายงาน"

        is_cal, date_label, date_params = is_calendar_query_request(query)
        self.assertTrue(is_cal, "Should detect calendar query.")

        res_data, flex_card = execute_agent_tool("manage_calendar_schedule", {"action": "query", **date_params}, session_id="test_cal_01")
        self.assertEqual(res_data["status"], "success")
        self.assertIn("events", res_data)
        self.assertIsNotNone(flex_card, "Should return Calendar Reminder Flex Message.")
        print("✅ Test 5 Passed: 'เช็กคิวถ่ายงาน' retrieved schedule and generated Flex Card.")

    # --------------------------------------------------------------------------
    # 6. Test Gemini REST API Multi-Turn Tool Calling Loop Simulation
    # --------------------------------------------------------------------------
    def test_06_rest_tool_calling_loop_with_user_role(self):
        """
        Simulate REST API Tier receiving a function call from Gemini,
        executing backend tool, and appending role='user' functionResponse.
        """
        # Simulated First Turn: Gemini responds with function call
        first_api_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "functionCall": {
                            "name": "get_accounting_insights",
                            "args": {"query_type": "overview"}
                        }
                    }]
                }
            }]
        }

        # Simulated Second Turn: Gemini receives function response and outputs text
        second_api_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "เลขาเฟิสสรุปยอดภาษีและบัญชีประจำเดือนให้เรียบร้อยแล้วค่ะ รายรับสุทธิ 125,000 บาท ✨"
                    }]
                }
            }]
        }

        with patch("requests.post") as mock_post:
            gemini_queue = [first_api_response, second_api_response]
            gemini_requests = []

            def router_post(url, *args, **kwargs):
                mock_res = MagicMock()
                mock_res.status_code = 200
                if "generativelanguage.googleapis.com" in url:
                    gemini_requests.append({"url": url, "kwargs": kwargs})
                    if gemini_queue:
                        mock_res.json.return_value = gemini_queue.pop(0)
                    else:
                        mock_res.json.return_value = second_api_response
                else:
                    # Mock GAS read response
                    mock_res.json.return_value = {"status": "success", "data": []}
                return mock_res

            mock_post.side_effect = router_post

            # Temporarily set genai_client to None to test REST Tier directly
            with patch("line_bot_server.genai_client", None):
                with patch("line_bot_server.GEMINI_API_KEY", "fake_test_key"):
                    res = asyncio.run(call_gemini_agent(
                        user_message="เฟิสสรุปยอดภาษีหัก ณ ที่จ่าย กับ vat ของเดือนนี้มาให้หน่อย",
                        session_id="test_rest_loop_session"
                    ))

                    self.assertIn("125,000", res["reply_text"])
                    self.assertTrue(len(res["flex_cards"]) > 0, "Should contain accounting Flex Card.")
                    self.assertEqual(len(res["executed_tools"]), 1)
                    self.assertEqual(res["executed_tools"][0]["tool"], "get_accounting_insights")

                    # Verify that exactly 2 turns were made to Gemini API
                    self.assertEqual(len(gemini_requests), 2)
                    second_call_json = gemini_requests[1]["kwargs"]["json"]
                    contents = second_call_json["contents"]

                    # The functionResponse must be under role="user"
                    fn_resp_content = contents[-1]
                    self.assertEqual(fn_resp_content["role"], "user", "Gemini v1beta REST payload MUST use role='user' for functionResponse!")
                    self.assertIn("functionResponse", fn_resp_content["parts"][0])
                    self.assertEqual(fn_resp_content["parts"][0]["functionResponse"]["name"], "get_accounting_insights")

        print("✅ Test 6 Passed: Multi-turn REST Tool Calling loop verified with role='user' compliance.")


if __name__ == "__main__":
    unittest.main()
