#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
GHN168 - Test Suite for Document Engine, LINE Bot Append & Tax Upgrades
==============================================================================
Author: น้องคิว (Q - Senior Fullstack Developer, ChZ Agent Corp)
Target Missions:
1. Quotation Template Upgrades:
   - Customer Acceptance Signature Block on left column
   - Hidden ref_row_html and clean header on Quotation PDF
   - Automatic 30-day validity (Valid Until) calculation (doc_date + 30 days)
   - GHN Seal clean styling (background transparent, border none, filter)
2. LINE Bot "เพิ่มรายการ" (Append Mode) in Revision Flow:
   - Detect append intent and parse item desc & price
   - Retain all previous items and append new items without collapsing
   - Correctly recalculate Subtotal and VAT 7%
3. Section 86/4 Thai Baht Text for Receipt (RE):
   - Baht Text reads Gross Amount before WHT for Tax Invoice / Receipt
   - Dedicated rows for Subtotal, VAT 7%, Gross Amount, WHT, and Net Paid
4. Google Sheets & PDF Data Integrity:
   - QT-202609-001 Row 18 contains 3 specific items in Column S
   - QT-202609-002 contains 4 items with 17,120 THB Net Total
==============================================================================
"""

import os
import re
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np

import document_template_engine
from document_template_engine import (
    calculate_document_totals,
    render_document_html,
    render_receipt_html,
    BASE_DOCUMENT_CSS,
)
import line_bot_server
from line_bot_server import (
    is_document_revision_request,
    execute_agent_tool,
    GEMINI_AGENT_TOOL_DECLARATIONS,
    SESSION_LAST_GENERATED_DOCS,
)
import ghn168_sync_service
from ghn168_sync_service import (
    build_sheet_row_data,
    update_sheet_document_data,
)


class TestDocumentAndRevisionSprint(unittest.TestCase):
    def setUp(self):
        SESSION_LAST_GENERATED_DOCS.clear()

    # --------------------------------------------------------------------------
    # Mission 1: Quotation Template Upgrades
    # --------------------------------------------------------------------------
    def test_quotation_has_customer_acceptance_signature_block(self):
        """Verify Quotation HTML includes Customer Acceptance block on the left."""
        data = {
            "doc_no": "QT-202609-002",
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "items": [{"desc": "งานโปรดักชั่น", "amount": 10000.0}],
            "is_vat": True
        }
        html = render_document_html("quotation", data)
        self.assertIn("ผู้อนุมัติสั่งจ้าง / Customer Acceptance", html)
        self.assertIn("(ลงชื่อผู้ว่าจ้าง / ประทับตรา)", html)
        self.assertIn("วันที่ / Date: ....................", html)
        # Right column has Boss Keng
        self.assertIn("นาย มงคล วงศ์สกุลยานนท์", html)

    def test_quotation_pdf_hides_ref_row_for_clean_header(self):
        """Verify Quotation HTML completely suppresses 'อ้างอิง/ปรับปรุงจาก' row."""
        data = {
            "doc_no": "QT-202609-002",
            "ref_doc_no": "QT-202609-001",
            "is_revision": True,
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "items": [{"desc": "งานโปรดักชั่น", "amount": 10000.0}],
            "remarks": "อ้างอิง/ปรับปรุงจาก QT-202609-001"
        }
        html = render_document_html("quotation", data)
        self.assertNotIn("อ้างอิง/ปรับปรุงจาก / Ref:", html)
        self.assertNotIn("อ้างอิงเอกสาร / Ref:", html)
        # Verify Ref row is NOT in meta-table
        meta_table_match = re.search(r'<table class="meta-table">.*?</table>', html, re.DOTALL)
        self.assertIsNotNone(meta_table_match)
        self.assertNotIn("QT-202609-001", meta_table_match.group(0))

    def test_quotation_default_due_date_calculates_30_days(self):
        """Verify Quotation due_date defaults to doc_date + 30 days."""
        data = {
            "doc_no": "QT-202609-002",
            "doc_date": "07/09/2026",
            # No due_date passed
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "items": [{"desc": "งานโปรดักชั่น", "amount": 10000.0}]
        }
        html = render_document_html("quotation", data)
        # 07/09/2026 + 30 days = 07/10/2026
        self.assertIn("07/10/2026", html)
        self.assertIn("ยืนราคาถึงวันที่ / Valid Until", html)

    def test_company_seal_css_and_transparent_edges(self):
        """Verify seal CSS has transparent background, border none, and zero dirty edge alpha."""
        # CSS check
        self.assertIn("background: transparent !important;", BASE_DOCUMENT_CSS)
        self.assertIn("border: none !important;", BASE_DOCUMENT_CSS)
        self.assertIn("filter: contrast(105%)", BASE_DOCUMENT_CSS)

        # Image pixel check
        seal_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "GHN_company_seal.png")
        self.assertTrue(os.path.isfile(seal_path))
        img = Image.open(seal_path)
        arr = np.array(img)
        # All 4 outer borders must have 0 alpha (no rectangular box artifact)
        self.assertEqual(arr[0, :, 3].max(), 0, "Top edge has non-zero alpha")
        self.assertEqual(arr[-1, :, 3].max(), 0, "Bottom edge has non-zero alpha")
        self.assertEqual(arr[:, 0, 3].max(), 0, "Left edge has non-zero alpha")
        self.assertEqual(arr[:, -1, 3].max(), 0, "Right edge has non-zero alpha")

    # --------------------------------------------------------------------------
    # Mission 2: LINE Bot "เพิ่มรายการ" Append Logic in Revision Flow
    # --------------------------------------------------------------------------
    def test_is_document_revision_request_detects_append_intent(self):
        """Verify is_document_revision_request extracts append items when user says 'เพิ่มรายการ...'"""
        text = "แก้ไขใบเสนอราคา QT-202609-001 เพิ่มรายการ โดรน 3,000 บาท"
        is_rev, args = is_document_revision_request(text)
        self.assertTrue(is_rev)
        self.assertEqual(args.get("source_doc_no"), "QT-202609-001")
        self.assertTrue(args.get("is_append"))
        self.assertEqual(args.get("action"), "append")
        self.assertIsNotNone(args.get("append_items"))
        self.assertEqual(len(args["append_items"]), 1)
        self.assertEqual(args["append_items"][0]["desc"], "โดรน")
        self.assertEqual(args["append_items"][0]["price"], 3000.0)

    def test_execute_agent_tool_revises_with_append_without_collapsing(self):
        """Verify execute_agent_tool appends new items to prev_items and calculates totals."""
        prev_items = [
            {"desc": "ถ่ายภาพนิ่งบ้านพร้อมอยู่ 3 ห้องนอน 3 ห้องน้ำ", "qty": 1, "price": 5000.0, "amount": 5000.0},
            {"desc": "VDO", "qty": 1, "price": 5000.0, "amount": 5000.0},
            {"desc": "ตัดต่อ VDO 1 ตัว", "qty": 1, "price": 3000.0, "amount": 3000.0}
        ]
        mock_source_doc = {
            "doc_no": "QT-202609-001",
            "doc_type": "quotation",
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "client_tax_id": "0505561016828",
            "items": prev_items,
            "pre_vat": 13000.0,
            "net_total": 13910.0,
            "signer_name": "นาย มงคล วงศ์สกุลยานนท์"
        }

        rev_args = {
            "source_doc_no": "QT-202609-001",
            "action": "append",
            "is_append": True,
            "append_items": [{"desc": "โดรน", "qty": 1, "price": 3000.0, "amount": 3000.0}],
            "remarks": "เพิ่มรายการถ่ายภาพโดรน"
        }

        with patch("line_bot_server.find_document_by_no", return_value=mock_source_doc):
            with patch("line_bot_server.generate_and_sync_document") as mock_gen:
                mock_gen.return_value = {
                    "status": "success",
                    "doc_no": "QT-202609-002",
                    "pdf_url": "https://drive.google.com/test_qt_002",
                    "totals": {"subtotal": 16000.0, "pre_vat": 16000.0, "vat_amount": 1120.0, "net_total": 17120.0}
                }
                res, flex = execute_agent_tool("revise_financial_document", rev_args, session_id="test_append")

                # Verify payload passed to generate_and_sync_document has 4 items
                call_args = mock_gen.call_args[0]
                doc_type_arg = call_args[0]
                payload_arg = call_args[1]

                self.assertEqual(doc_type_arg, "quotation")
                self.assertEqual(len(payload_arg["items"]), 4)
                self.assertEqual(payload_arg["items"][0]["desc"], "ถ่ายภาพนิ่งบ้านพร้อมอยู่ 3 ห้องนอน 3 ห้องน้ำ")
                self.assertEqual(payload_arg["items"][3]["desc"], "โดรน")
                self.assertEqual(payload_arg["amount"], 16000.0)

    # --------------------------------------------------------------------------
    # Mission 3: Section 86/4 Thai Baht Text for Receipt (RE)
    # --------------------------------------------------------------------------
    def test_receipt_baht_text_reads_gross_amount_per_section_86_4(self):
        """Receipt Thai Baht Text must read Gross Amount before WHT per Revenue Code Section 86/4."""
        items = [{"desc": "บริการโปรดักชั่น", "qty": 1, "price": 10000.0}]
        # Subtotal = 10,000 | VAT 7% = 700 | Gross = 10,700 | WHT 3% = 300 | Net Paid = 10,400
        totals = calculate_document_totals(
            items=items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,
            doc_type="receipt"
        )
        self.assertEqual(totals["subtotal"], 10000.0)
        self.assertEqual(totals["vat_amount"], 700.0)
        self.assertEqual(totals["gross_amount"], 10700.0)
        self.assertEqual(totals["wht_amount"], 300.0)
        self.assertEqual(totals["net_total"], 10400.0)
        # Baht Text MUST read Gross Amount (10,700.00) = หนึ่งหมื่นเจ็ดร้อยบาทถ้วน
        self.assertEqual(totals["baht_text"], "หนึ่งหมื่นเจ็ดร้อยบาทถ้วน")

    def test_invoice_baht_text_retains_net_total(self):
        """Invoice Baht Text continues to read requested net total amount (Amount Due with 0% WHT)."""
        items = [{"desc": "บริการโปรดักชั่น", "qty": 1, "price": 10000.0}]
        totals = calculate_document_totals(
            items=items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,
            doc_type="invoice"
        )
        # Invoice Baht Text reads 10,700 = หนึ่งหมื่นเจ็ดร้อยบาทถ้วน (Amount Due)
        self.assertEqual(totals["baht_text"], "หนึ่งหมื่นเจ็ดร้อยบาทถ้วน")

    def test_receipt_html_renders_gross_total_and_net_paid_rows(self):
        """Receipt HTML renders dedicated Total Amount (Gross), WHT deduction, and Net Paid."""
        data = {
            "doc_no": "RE-202609-001",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "items": [{"desc": "งานบริการ", "qty": 1, "price": 20000.0}],
            "is_vat": True,
            "wht_rate": 3.0
        }
        html = render_receipt_html(data)
        # Subtotal: 20,000 | VAT: 1,400 | Gross: 21,400 | WHT: 600 | Net: 20,800
        self.assertIn("ยอดเงินรวมทั้งสิ้น / Total Amount", html)
        self.assertIn("21,400.00", html)
        self.assertIn("สองหมื่นหนึ่งพันสี่ร้อยบาทถ้วน", html)
        self.assertIn("หักภาษี ณ ที่จ่าย / WHT (3%)", html)
        self.assertIn("-600.00", html)
        self.assertIn("ยอดโอนสุทธิ / Net Paid", html)
        self.assertIn("20,800.00", html)


if __name__ == "__main__":
    unittest.main()
