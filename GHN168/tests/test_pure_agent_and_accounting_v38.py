"""
==============================================================================
Test Suite for GHN168 Pure Agent Architecture & Accounting Suite (v3.8)
==============================================================================
Tests verify:
1. Invoice (IV) Calculation: Zero WHT, Amount Due lock.
2. Invoice Template: "ผู้รับวางบิล / Received By" signature card & "วันที่ / Date: ....................".
3. Strict Reference rules: IV references QT only, RE references IV only, revision refs suppressed.
4. LINE Instant UX: send_line_loading_animation, send_line_file_message.
5. Universal Thai Date Parsing: parse_thai_date_str.
6. Document Date Forwarding in create_financial_document and revise_financial_document.
7. Vision OCR Customer Onboarding: extract_customer_profile_from_image_ocr.
8. Memory & State: MAX_HISTORY_PER_SESSION = 20.
9. Customer Alias mapping in search_customer.
==============================================================================
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

import document_template_engine as dte
import ghn168_sync_service as sync_svc
import line_bot_server as bot_server


class TestPureAgentAndAccountingSuiteV38(unittest.TestCase):

    def setUp(self):
        sync_svc._CUSTOMERS_CACHE["data"] = []
        sync_svc._CUSTOMERS_CACHE["timestamp"] = 0
        bot_server.CONVERSATION_HISTORY.clear()

    # --------------------------------------------------------------------------
    # 1. Invoice (IV) WHT = 0% and Amount Due Lock
    # --------------------------------------------------------------------------
    def test_invoice_calculation_no_wht_amount_due(self):
        """Invoice must have 0% WHT, net_total == gross_amount, Amount Due."""
        items = [
            {"desc": "บริการผลิตสื่อโฆษณา", "qty": 1, "price": 10000.0}
        ]
        totals = dte.calculate_document_totals(
            items=items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,  # Explicitly pass 3%, template engine must zero it out for invoice
            doc_type="invoice"
        )
        self.assertEqual(totals["subtotal"], 10000.0)
        self.assertEqual(totals["vat_amount"], 700.0)
        self.assertEqual(totals["gross_amount"], 10700.0)
        self.assertEqual(totals["wht_amount"], 0.0)
        self.assertEqual(totals["wht_rate"], 0.0)
        self.assertEqual(totals["net_total"], 10700.0)

    # --------------------------------------------------------------------------
    # 2. Invoice Template HTML: Signature Card & No WHT Row & Amount Due
    # --------------------------------------------------------------------------
    def test_invoice_html_template_elements(self):
        """Invoice HTML must render 'ผู้รับวางบิล / Received By' and 'Amount Due'."""
        doc_data = {
            "doc_no": "IV-202609-001",
            "doc_date": "10/09/2026",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "client_tax_id": "0105550000001",
            "client_address": "เชียงใหม่",
            "project_name": "งานโฆษณา",
            "items": [{"desc": "งานถ่ายทำ", "qty": 1, "price": 20000.0}],
            "is_vat": True,
            "ref_doc_no": "QT-202609-001"
        }
        html = dte.render_document_html("invoice", doc_data)

        # 1. Check Amount Due label
        self.assertIn("Amount Due", html)
        self.assertNotIn("หักภาษี ณ ที่จ่าย", html)

        # 2. Check left signature card: 'ผู้รับวางบิล / Received By'
        self.assertIn("ผู้รับวางบิล / Received By", html)
        self.assertIn("วันที่ / Date: ....................", html)

        # 3. Check reference line: IV must display QT reference
        self.assertIn("QT-202609-001", html)

    # --------------------------------------------------------------------------
    # 3. Strict Reference Rules
    # --------------------------------------------------------------------------
    def test_strict_reference_rules_filtering(self):
        """
        - IV only references QT*
        - RE only references IV*
        - Revision refs (e.g. IV referencing IV) suppressed from document face
        """
        # Scenario A: IV referencing IV (revision) -> suppressed on PDF
        doc_iv_rev = {
            "doc_no": "IV-202609-002",
            "client_name": "ลูกค้า A",
            "project_name": "งานบริการ",
            "items": [{"desc": "บริการ", "qty": 1, "price": 1000.0}],
            "ref_doc_no": "IV-202609-001"
        }
        html_iv_rev = dte.render_document_html("invoice", doc_iv_rev)
        self.assertNotIn("อ้างอิงเอกสาร / Ref:", html_iv_rev)

        # Scenario B: RE referencing QT -> suppressed (RE only references IV)
        doc_re_qt = {
            "doc_no": "RE-202609-001",
            "client_name": "ลูกค้า A",
            "project_name": "งานบริการ",
            "items": [{"desc": "บริการ", "qty": 1, "price": 1000.0}],
            "ref_doc_no": "QT-202609-001"
        }
        html_re_qt = dte.render_document_html("receipt", doc_re_qt)
        self.assertNotIn("QT-202609-001", html_re_qt)

        # Scenario C: RE referencing IV -> displayed!
        doc_re_iv = {
            "doc_no": "RE-202609-001",
            "client_name": "ลูกค้า A",
            "project_name": "งานบริการ",
            "items": [{"desc": "บริการ", "qty": 1, "price": 1000.0}],
            "ref_doc_no": "IV-202609-001"
        }
        html_re_iv = dte.render_document_html("receipt", doc_re_iv)
        self.assertIn("IV-202609-001", html_re_iv)

    # --------------------------------------------------------------------------
    # 4. Universal Thai Date Parsing
    # --------------------------------------------------------------------------
    def test_parse_thai_date_str(self):
        """Verifies parsing of Thai months and Buddhist years."""
        # Thai textual month + BE year
        self.assertEqual(bot_server.parse_thai_date_str("10 กันยายน 2569"), "10/09/2026")
        self.assertEqual(bot_server.parse_thai_date_str("5 ม.ค. 2569"), "05/01/2026")
        self.assertEqual(bot_server.parse_thai_date_str("1 กุมภาพันธ์ 2026"), "01/02/2026")

        # Slash format BE
        self.assertEqual(bot_server.parse_thai_date_str("15/09/2569"), "15/09/2026")
        # Slash format CE
        self.assertEqual(bot_server.parse_thai_date_str("15/09/2026"), "15/09/2026")
        # Dash format YYYY-MM-DD
        self.assertEqual(bot_server.parse_thai_date_str("2026-09-10"), "10/09/2026")

    # --------------------------------------------------------------------------
    # 5. LINE Instant UX Functions
    # --------------------------------------------------------------------------
    def test_send_line_loading_animation(self):
        """Test send_line_loading_animation with mock response."""
        with patch("line_bot_server.LINE_CHANNEL_ACCESS_TOKEN", "mock_token"):
            with patch("requests.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200)
                res = bot_server.send_line_loading_animation("U1234567890abcdef", 30)
                self.assertTrue(res)
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(kwargs["json"]["chatId"], "U1234567890abcdef")
                self.assertEqual(kwargs["json"]["loadingSeconds"], 30)

    def test_send_line_file_message(self):
        """Test send_line_file_message sends native file message payload."""
        with patch("line_bot_server.send_line_push_message") as mock_push:
            mock_push.return_value = True
            with patch("line_bot_server.LINE_CHANNEL_ACCESS_TOKEN", "mock_token"):
                res = bot_server.send_line_file_message("U123", "https://example.com/doc.pdf", "QT-202609-001.pdf")
                self.assertTrue(res)
                mock_push.assert_called_once()
                target, msgs = mock_push.call_args[0]
                self.assertEqual(target, "U123")
                self.assertEqual(msgs[0]["type"], "file")
                self.assertEqual(msgs[0]["fileName"], "QT-202609-001.pdf")

    # --------------------------------------------------------------------------
    # 6. Document Date Forwarding in create & revise
    # --------------------------------------------------------------------------
    def test_doc_date_forwarding_in_create_financial_document(self):
        """Test doc_date is parsed and forwarded to generate_and_sync_document."""
        args = {
            "doc_type": "quotation",
            "client_name": "บจก. ทดสอบ",
            "project_name": "โปรเจกต์พิเศษ",
            "amount": 10000.0,
            "doc_date": "10 กันยายน 2569"
        }
        with patch("line_bot_server.generate_and_sync_document") as mock_gen:
            mock_gen.return_value = {
                "status": "success",
                "doc_no": "QT-202609-001",
                "totals": {"net_total": 10700.0},
                "pdf_url": "https://example.com/QT-202609-001.pdf"
            }
            res_data, flex_card = bot_server.execute_agent_tool("create_financial_document", args, "test_session")
            mock_gen.assert_called_once()
            passed_payload = mock_gen.call_args[0][1]
            self.assertEqual(passed_payload.get("doc_date"), "10/09/2026")

    def test_doc_date_forwarding_in_revise_financial_document(self):
        """Test doc_date is parsed and forwarded to revise_financial_document."""
        args = {
            "source_doc_no": "QT-202609-001",
            "new_amount": 15000.0,
            "doc_date": "15 กันยายน 2569"
        }
        with patch("line_bot_server.find_document_by_no") as mock_find:
            mock_find.return_value = {
                "doc_no": "QT-202609-001",
                "client_name": "ลูกค้าเก่า",
                "project_name": "โปรเจกต์เดิม",
                "items": [{"desc": "เดิม", "qty": 1, "price": 10000.0}]
            }
            with patch("line_bot_server.generate_and_sync_document") as mock_gen:
                mock_gen.return_value = {
                    "status": "success",
                    "doc_no": "QT-202609-002",
                    "totals": {"net_total": 16050.0},
                    "pdf_url": "https://example.com/QT-202609-002.pdf"
                }
                res_data, flex_card = bot_server.execute_agent_tool("revise_financial_document", args, "test_session")
                mock_gen.assert_called_once()
                passed_payload = mock_gen.call_args[0][1]
                self.assertEqual(passed_payload.get("doc_date"), "15/09/2026")

    # --------------------------------------------------------------------------
    # 7. Vision OCR Customer Onboarding
    # --------------------------------------------------------------------------
    def test_extract_customer_profile_from_image_ocr(self):
        """Test customer extraction fallback format and validation."""
        import asyncio
        parsed = asyncio.run(bot_server.extract_customer_profile_from_image_ocr(b"dummy_image_data"))
        self.assertIn("customer_name", parsed)
        self.assertIn("tax_id", parsed)
        self.assertIn("branch", parsed)

    # --------------------------------------------------------------------------
    # 8. Memory Sliding Window Cap at 20
    # --------------------------------------------------------------------------
    def test_memory_sliding_window_cap(self):
        """Test conversation history trims at MAX_HISTORY_PER_SESSION = 20."""
        self.assertEqual(bot_server.MAX_HISTORY_PER_SESSION, 20)
        session_id = "test_memory_cap"
        for i in range(35):
            bot_server.append_to_history(session_id, "user", f"message {i}")
        hist = bot_server.get_history(session_id)
        self.assertLessEqual(len(hist), 20)
        self.assertEqual(hist[-1]["text"], "message 34")

    # --------------------------------------------------------------------------
    # 9. Customer Alias Mapping
    # --------------------------------------------------------------------------
    def test_customer_alias_cheil_samsung(self):
        """Searching for 'เชอิล', 'cheil', or 'samsung' maps to CUST-014."""
        mock_sheet = {
            "status": "success",
            "values": [
                ["CUST-014", "บริษัท เชอิล (ประเทศไทย) จำกัด", "0105534087968", "00000", "กรุงเทพฯ", "02-1234567"]
            ]
        }
        with patch("ghn168_sync_service.read_sheet_data", return_value=mock_sheet):
            cust1 = sync_svc.search_customer("เชอิล")
            self.assertIsNotNone(cust1)
            self.assertEqual(cust1.get("customer_id"), "CUST-014")

            cust2 = sync_svc.search_customer("Cheil")
            self.assertIsNotNone(cust2)
            self.assertEqual(cust2.get("customer_id"), "CUST-014")

            cust3 = sync_svc.search_customer("ซัมซุง")
            self.assertIsNotNone(cust3)
            self.assertEqual(cust3.get("customer_id"), "CUST-014")


if __name__ == "__main__":
    unittest.main()
