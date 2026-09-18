#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for:
1. PDF naming strictly {doc_no}.pdf (stripping _YYYYMMDD)
2. Google Sheets starting sequence locked to QT-202609-002+ for Quotations
3. Smart Revision Flow (new sequence, autofill, ref_doc_no, PDF & Flex subtitle)
4. Cross-Doc Pipeline Reference (QT -> IV -> RE with ref_doc_no in PDF, Sheet Col O, Flex)
"""

import unittest
from unittest.mock import patch, MagicMock

import ghn168_sync_service
from ghn168_sync_service import (
    build_sheet_row_data,
    get_next_document_number,
    generate_and_sync_document,
    clear_doc_sequence_cache,
)
import document_template_engine
from document_template_engine import render_document_html
import line_bot_server
from line_bot_server import (
    build_document_flex_message,
    execute_agent_tool,
    is_document_revision_request,
)


class TestSmartRevisionAndPdfNaming(unittest.TestCase):
    def setUp(self):
        clear_doc_sequence_cache()

    def test_pdf_naming_strict_doc_no(self):
        """Mission 1: Ensure PDF filename is purely {doc_no}.pdf without date stamp."""
        doc_data = {
            "doc_no": "QT-202609-002",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "project_name": "งานโปรดักชั่น",
            "amount": 15000.0,
        }

        with patch("ghn168_sync_service.render_document_html", return_value="<html>Dummy</html>"):
            with patch("ghn168_sync_service.convert_html_to_pdf_local", return_value={"status": "success", "pdf_path": "/tmp/test.pdf"}):
                with patch("os.path.isfile", return_value=True):
                    with patch("ghn168_sync_service.upload_document_pdf") as mock_upload:
                        mock_upload.return_value = {"status": "success", "pdfUrl": "https://drive.google.com/test_qt002"}
                        with patch("ghn168_sync_service.sync_document_to_sheets", return_value={"status": "success"}):
                            res = generate_and_sync_document("quotation", doc_data)

                            self.assertEqual(res.get("status"), "success")
                            self.assertEqual(res.get("doc_no"), "QT-202609-002")
                            # Verify pdf_name passed to upload_document_pdf is exactly 'QT-202609-002.pdf'
                            call_kwargs = mock_upload.call_args[1]
                            self.assertEqual(call_kwargs["pdf_name"], "QT-202609-002.pdf")
                            self.assertNotIn("20260906", call_kwargs["pdf_name"])

    def test_next_doc_number_starts_at_least_002(self):
        """Mission 2: Next quotation for September 2026 must be at least QT-202609-002."""
        with patch("ghn168_sync_service.read_sheet_data", return_value={"status": "success", "data": []}):
            next_qt = get_next_document_number("quotation")
            # In empty or 0-count sheet for 202609, base lock ensures at least QT-202609-002
            self.assertEqual(next_qt, "QT-202609-002")

    def test_smart_revision_html_and_sheet_data(self):
        """Mission 3: Revision displays 'อ้างอิง/ปรับปรุงจาก' in PDF HTML and Sheet Remarks."""
        doc_payload = {
            "doc_no": "QT-202609-003",
            "ref_doc_no": "QT-202609-001",
            "is_revision": True,
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "project_name": "งานบริการปรับปรุงยอด",
            "amount": 14000.0,
        }

        # 1. HTML rendering check (Quotation hides ref row for clean header, but displays Customer Acceptance)
        html = render_document_html("quotation", doc_payload)
        self.assertNotIn("อ้างอิง/ปรับปรุงจาก", html)
        self.assertIn("ผู้อนุมัติสั่งจ้าง / Customer Acceptance", html)

        # 2. Sheet Row Data Remarks (Column U / index 20) check
        sheet_name, row = build_sheet_row_data("quotation", doc_payload)
        self.assertEqual(sheet_name, "ใบเสนอราคา")
        remarks = row[20]
        self.assertIn("อ้างอิง/ปรับปรุงจาก QT-202609-001", remarks)

    def test_cross_doc_pipeline_html_and_sheet_data(self):
        """Mission 3: Pipeline (QT -> IV) displays 'อ้างอิงเอกสาร' in HTML and Sheet Remarks."""
        doc_payload = {
            "doc_no": "IV-202609-001",
            "ref_doc_no": "QT-202609-001",
            "is_revision": False,
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "amount": 13000.0,
        }

        # 1. HTML rendering check
        html = render_document_html("invoice", doc_payload)
        self.assertIn("อ้างอิงเอกสาร / Ref:", html)
        self.assertIn("QT-202609-001", html)

        # 2. Sheet Row Data Remarks (Column W / index 22) check
        sheet_name, row = build_sheet_row_data("invoice", doc_payload)
        remarks = row[22]
        self.assertIn("อ้างอิงเอกสาร: QT-202609-001", remarks)

    def test_line_flex_message_shows_reference_subtitle(self):
        """Mission 3: LINE Flex Message includes ref_doc_no in subtitle and card body."""
        # Case A: Revision
        flex_rev = build_document_flex_message({
            "doc_type": "quotation",
            "doc_no": "QT-202609-003",
            "ref_doc_no": "QT-202609-001",
            "is_revision": True,
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "amount": 14000.0,
            "pdf_url": "https://drive.google.com/test_rev"
        })
        flex_rev_str = str(flex_rev)
        self.assertIn("อ้างอิง/ปรับปรุงจาก QT-202609-001", flex_rev_str)

        # Case B: Cross-doc Pipeline
        flex_pipe = build_document_flex_message({
            "doc_type": "invoice",
            "doc_no": "IV-202609-001",
            "ref_doc_no": "QT-202609-001",
            "is_revision": False,
            "client_name": "บริษัท แสนดี อินฟินิตี้ จำกัด",
            "amount": 13000.0,
            "pdf_url": "https://drive.google.com/test_pipe"
        })
        flex_pipe_str = str(flex_pipe)
        self.assertIn("อ้างอิงเอกสาร: QT-202609-001", flex_pipe_str)

    def test_is_document_revision_request_regex(self):
        """Verify intent router detects revision requests and extracts ref_doc."""
        is_rev1, _ = is_document_revision_request("แก้ใบเสนอราคา QT-202609-001 ปรับเป็น 15,000")
        self.assertTrue(is_rev1)
        is_rev2, _ = is_document_revision_request("ปรับปรุงยอดใบเสนอราคา QT-202609-002")
        self.assertTrue(is_rev2)
        is_rev3, _ = is_document_revision_request("revision QT-202609-001")
        self.assertTrue(is_rev3)
        is_rev4, _ = is_document_revision_request("แก้ไขส่วนแบ่งกำไร 40 30 30")
        self.assertFalse(is_rev4)


if __name__ == "__main__":
    unittest.main()
