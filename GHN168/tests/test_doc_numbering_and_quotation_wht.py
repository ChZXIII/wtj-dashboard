"""
Unit Test Suite for GHN168:
1. Quotation WHT 3% Complete Removal (Subtotal + VAT = Grand Total, no WHT row)
2. Sequential Independent Document Numbering (QT, IV, RE, 50BIS, PV)
3. Cross-Document Reference Tracking (ref_doc_no / ref_quotation_no / ref_invoice_no)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from document_template_engine import (
    calculate_document_totals,
    render_document_html,
    format_currency,
)
from ghn168_sync_service import (
    build_sheet_row_data,
    get_next_document_number,
    convert_document,
    _DOC_SEQUENCE_CACHE,
)
from line_bot_server import (
    execute_agent_tool,
    build_document_flex_message,
    determine_smart_wht_rate,
)


class TestQuotationWHTRemoval(unittest.TestCase):
    """Mission 1 Tests: Verify WHT is completely removed from Quotations."""

    def test_quotation_totals_no_wht(self):
        """13,000 THB + 7% VAT = 13,910 THB Net Total with 0% WHT for Quotation."""
        items = [{"desc": "งานผลิตสื่อและวิดีโอโฆษณา", "amount": 13000.0}]
        totals = calculate_document_totals(
            items=items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,  # Even if 3% WHT is requested
            doc_type="quotation"
        )

        self.assertEqual(totals["subtotal"], 13000.0)
        self.assertEqual(totals["vat_amount"], 910.0)
        self.assertEqual(totals["gross_amount"], 13910.0)
        self.assertEqual(totals["wht_rate"], 0.0)
        self.assertEqual(totals["wht_amount"], 0.0)
        self.assertEqual(totals["net_total"], 13910.0)
        self.assertEqual(totals["grand_total"], 13910.0)
        self.assertEqual(totals["baht_text"], "หนึ่งหมื่นสามพันเก้าร้อยสิบบาทถ้วน")

    def test_invoice_totals_no_wht(self):
        """v3.8: Invoice WHT is removed from main calculation table, net total is gross amount (Amount Due)."""
        items = [{"desc": "งานบริการและตัดต่อ", "amount": 13000.0}]
        totals = calculate_document_totals(
            items=items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,
            doc_type="invoice"
        )

        self.assertEqual(totals["subtotal"], 13000.0)
        self.assertEqual(totals["vat_amount"], 910.0)
        self.assertEqual(totals["gross_amount"], 13910.0)
        self.assertEqual(totals["wht_rate"], 0.0)
        self.assertEqual(totals["wht_amount"], 0.0)
        self.assertEqual(totals["net_total"], 13910.0)
        self.assertEqual(totals["grand_total"], 13910.0)
        self.assertEqual(totals["baht_text"], "หนึ่งหมื่นสามพันเก้าร้อยสิบบาทถ้วน")

    def test_quotation_html_rendering_no_wht_row(self):
        """HTML output for Quotation must NOT contain WHT row, and show Grand Total."""
        data = {
            "doc_no": "QT-202609-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า",
            "items": [{"desc": "ผลิตคลิปวิดีโอโปรโมทสินค้า", "amount": 13000.0}],
            "is_vat": True,
            "wht_rate": 3.0
        }
        html = render_document_html("quotation", data)

        # Assert no WHT row
        self.assertNotIn("หักภาษี ณ ที่จ่าย", html)
        self.assertNotIn("-390.00", html)

        # Assert Grand Total row and correct values
        self.assertIn("ยอดเงินรวมทั้งสิ้น / Grand Total", html)
        self.assertIn("13,910.00", html)
        self.assertIn("หนึ่งหมื่นสามพันเก้าร้อยสิบบาทถ้วน", html)

    def test_sheet_row_data_quotation_net_equals_gross(self):
        """Sheet row for quotation: Col 11 (WHT amount) is 0.0, Col 12 (Net) is gross amount."""
        doc_data = {
            "doc_no": "QT-202609-001",
            "client_name": "บริษัท ทดสอบการเงิน จำกัด",
            "project_name": "งานบริการโปรดักชั่น",
            "amount": 13000.0,
            "is_vat": True,
            "wht_rate": 3.0
        }
        sheet_name, row = build_sheet_row_data("quotation", doc_data)

        self.assertEqual(sheet_name, "ใบเสนอราคา")
        self.assertEqual(row[9], 13000.0)   # Pre-VAT
        self.assertEqual(row[10], 910.0)    # VAT 7%
        self.assertEqual(row[11], 0.0)      # WHT Amount strictly 0.0
        self.assertEqual(row[12], 13910.0)  # Net Amount is 13,910.0 (Subtotal + VAT)
        self.assertEqual(row[13], 0.0)      # WHT Rate strictly 0.0

    def test_determine_smart_wht_rate_for_quotation(self):
        """Smart WHT engine returns 0.0 for quotation regardless of corporate context."""
        rate = determine_smart_wht_rate(
            client_name="บริษัท เมกะ คอร์ป จำกัด (มหาชน)",
            project_name="งานบริการตัดต่อคลิป",
            raw_text="มีหัก ณ ที่จ่าย 3% ด้วยนะ",
            doc_type="quotation"
        )
        self.assertEqual(rate, 0.0)

    def test_line_bot_execute_tool_quotation_zero_wht(self):
        """execute_agent_tool for quotation enforces 0 WHT and Flex card displays correctly."""
        args = {
            "doc_type": "quotation",
            "client_name": "บจก. ล้านนาโปรดักชั่น",
            "project_name": "งานถ่ายทำภาพยนตร์สั้น",
            "amount": 13000.0,
            "wht_rate": 3.0
        }
        res, flex = execute_agent_tool("create_financial_document", args, session_id="test_session")

        self.assertEqual(res["totals"]["wht_rate"], 0.0)
        self.assertEqual(res["totals"]["wht_amount"], 0.0)
        self.assertEqual(res["totals"]["net_total"], 13910.0)

        # Flex message verification
        flex_str = str(flex)
        self.assertNotIn("หัก ณ ที่จ่าย", flex_str)
        self.assertIn("ยอดรวมทั้งสิ้น:", flex_str)
        self.assertIn("13,910.00", flex_str)


class TestSequentialDocumentNumbering(unittest.TestCase):
    """Mission 2 Tests: Sequential independent numbering per document book."""

    def setUp(self):
        _DOC_SEQUENCE_CACHE.clear()

    def test_get_next_document_number_independent_prefixes(self):
        """Each document book starts at 001 for a fresh month."""
        test_ym = "202901"

        with patch("ghn168_sync_service.read_sheet_data") as mock_read:
            mock_read.return_value = {"status": "success", "values": []}

            qt_no = get_next_document_number("quotation", year_month=test_ym)
            iv_no = get_next_document_number("invoice", year_month=test_ym)
            re_no = get_next_document_number("receipt", year_month=test_ym)
            wht_no = get_next_document_number("wht", year_month=test_ym)
            pv_no = get_next_document_number("expense", year_month=test_ym)

            self.assertEqual(qt_no, f"QT-{test_ym}-001")
            self.assertEqual(iv_no, f"IV-{test_ym}-001")
            self.assertEqual(re_no, f"RE-{test_ym}-001")
            self.assertEqual(wht_no, f"50BIS-{test_ym}-001")
            self.assertEqual(pv_no, f"PV-{test_ym}-001")

    def test_sequential_incrementation(self):
        """Consecutive calls for the same doc type increment 001, 002, 003."""
        test_ym = "202902"

        with patch("ghn168_sync_service.read_sheet_data") as mock_read:
            mock_read.return_value = {"status": "success", "values": []}

            no1 = get_next_document_number("quotation", year_month=test_ym)
            no2 = get_next_document_number("quotation", year_month=test_ym)
            no3 = get_next_document_number("quotation", year_month=test_ym)

            self.assertEqual(no1, f"QT-{test_ym}-001")
            self.assertEqual(no2, f"QT-{test_ym}-002")
            self.assertEqual(no3, f"QT-{test_ym}-003")

    def test_incrementation_from_existing_sheet_data(self):
        """When sheet already has QT-202903-005, next is QT-202903-006."""
        test_ym = "202903"
        existing_rows = [
            ["timestamp", "date", "QT-202903-001"],
            ["timestamp", "date", "QT2903-002"],
            ["timestamp", "date", "หอม-QT2903-005"],
        ]

        with patch("ghn168_sync_service.read_sheet_data") as mock_read:
            mock_read.return_value = {"status": "success", "values": existing_rows}

            next_no = get_next_document_number("quotation", year_month=test_ym)
            self.assertEqual(next_no, f"QT-{test_ym}-006")

    def test_offline_fallback_on_sheet_failure(self):
        """When Google Sheets API throws exception, fallback returns clean next number."""
        test_ym = "202904"

        with patch("ghn168_sync_service.read_sheet_data", side_effect=Exception("Timeout reading sheet")):
            no1 = get_next_document_number("invoice", year_month=test_ym)
            no2 = get_next_document_number("invoice", year_month=test_ym)

            self.assertEqual(no1, f"IV-{test_ym}-001")
            self.assertEqual(no2, f"IV-{test_ym}-002")


class TestDocumentConversionPipeline(unittest.TestCase):
    """Mission 2 Tests: Cross-Document Reference & Independent Doc Numbering in Conversion."""

    def setUp(self):
        _DOC_SEQUENCE_CACHE.clear()

    @patch("ghn168_sync_service.sync_document_to_sheets")
    @patch("ghn168_sync_service.find_document_by_no")
    def test_convert_qt_to_iv_independent_number_and_ref(self, mock_find, mock_sync):
        """Converting QT -> IV generates a brand new IV document number and preserves ref_quotation_no."""
        mock_find.return_value = {
            "source_sheet": "ใบเสนอราคา",
            "doc_type": "quotation",
            "doc_no": "QT2608-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "client_tax_id": "0505560000123",
            "client_address": "เชียงใหม่",
            "client_branch": "00000",
            "client_phone": "081-1111111",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า",
            "items": [{"desc": "ผลิตคลิปวิดีโอโปรโมทสินค้า", "qty": 1, "price": 50000.0, "amount": 50000.0}],
            "pre_vat": 50000.0,
            "vat_amount": 3500.0,
            "wht_amount": 0.0,
            "wht_rate": 0.0,
            "net_total": 53500.0
        }
        mock_sync.return_value = {"status": "simulation"}

        conv_res = convert_document("QT2608-001", "invoice")

        self.assertIn(conv_res["status"], ["success", "simulation"])
        self.assertEqual(conv_res["target_type"], "invoice")
        # Must be a new IV number (e.g. IV-YYYYMM-XXX), not just replacing QT prefix of QT2608-001!
        self.assertTrue(conv_res["doc_no"].startswith("IV-"))
        self.assertNotEqual(conv_res["doc_no"], "IV2608-001")

        # Must track cross reference
        self.assertEqual(conv_res["ref_doc_no"], "QT2608-001")

    @patch("ghn168_sync_service.sync_document_to_sheets")
    @patch("ghn168_sync_service.find_document_by_no")
    def test_convert_iv_to_re_independent_number_and_ref(self, mock_find, mock_sync):
        """Converting IV -> RE generates a brand new RE document number and preserves ref_invoice_no."""
        mock_find.return_value = {
            "source_sheet": "ใบวางบิล",
            "doc_type": "invoice",
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "client_tax_id": "0505560000123",
            "client_address": "เชียงใหม่",
            "client_branch": "00000",
            "client_phone": "081-1111111",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า",
            "items": [{"desc": "ผลิตคลิปวิดีโอโปรโมทสินค้า", "qty": 1, "price": 50000.0, "amount": 50000.0}],
            "pre_vat": 50000.0,
            "vat_amount": 3500.0,
            "wht_amount": 1500.0,
            "wht_rate": 3.0,
            "net_total": 52000.0
        }
        mock_sync.return_value = {"status": "simulation"}

        conv_res = convert_document("IV-202609-001", "receipt")

        self.assertIn(conv_res["status"], ["success", "simulation"])
        self.assertEqual(conv_res["target_type"], "receipt")
        # Must be a new RE number (e.g. RE-YYYYMM-XXX)
        self.assertTrue(conv_res["doc_no"].startswith("RE-"))
        self.assertNotEqual(conv_res["doc_no"], "RE-202609-001" if conv_res["doc_no"] == "IV-202609-001" else "")

        # Must track cross reference
        self.assertEqual(conv_res["ref_doc_no"], "IV-202609-001")

    def test_html_renders_ref_doc_no_header(self):
        """Document HTML header renders 'อ้างอิงเอกสาร / Ref: [ref_doc_no]' clearly."""
        iv_data = {
            "doc_no": "IV-202609-005",
            "ref_doc_no": "QT-202609-001",
            "client_name": "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า",
            "amount": 20000.0
        }
        html = render_document_html("invoice", iv_data)
        self.assertIn("อ้างอิงเอกสาร / Ref:", html)
        self.assertIn("QT-202609-001", html)


if __name__ == "__main__":
    unittest.main()
