#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
GHN168 - Test Suite for 4 Core Missions (น้องคิว / Q - Senior Fullstack Developer)
==============================================================================
1. Quoted Image Vision OCR in resolve_quoted_message_content
2. Multi-Item Table Support in create_financial_document & HTML/PDF rendering
3. Google Drive Folder Locking (01_Quotations_QT_ใบเสนอราคา) & Col U in Google Sheets
4. LINE Group Notification Target ID Locking (Cd7b3d3b7a0fe061f341ec031c6edac8c)
==============================================================================
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Import target modules
import line_bot_server
from line_bot_server import (
    resolve_quoted_message_content,
    extract_vision_ocr_text_from_image,
    execute_agent_tool,
    GEMINI_AGENT_TOOL_DECLARATIONS,
    RECENT_MEDIA_CACHE,
    SESSION_LAST_IMAGE,
    LINE_NOTIFICATION_TARGET_ID,
)
import ghn168_sync_service
from ghn168_sync_service import (
    DOC_TYPE_FOLDER_CANDIDATES,
    DOC_TYPE_FOLDER_PREFIX,
    COMPANY_DRIVE_FOLDER_ID,
    build_sheet_row_data,
    upload_document_pdf,
    upload_document_html,
)
import document_template_engine
from document_template_engine import (
    calculate_document_totals,
    render_document_html,
)


class TestFourCoreMissions(unittest.TestCase):
    def setUp(self):
        RECENT_MEDIA_CACHE.clear()
        SESSION_LAST_IMAGE.clear()

    def tearDown(self):
        ghn168_sync_service._CUSTOMERS_CACHE["data"] = None
        ghn168_sync_service._CUSTOMERS_CACHE["timestamp"] = 0.0

    # --------------------------------------------------------------------------
    # Mission 1: Quoted Image Vision OCR
    # --------------------------------------------------------------------------
    def test_quoted_image_vision_ocr_from_recent_media_cache(self):
        """Verify resolve_quoted_message_content runs Vision OCR when quoted message is image bytes."""
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        msg_id = "quote_img_001"
        RECENT_MEDIA_CACHE[msg_id] = dummy_png

        # Mock extract_vision_ocr_text_from_image to return structured customer text
        mock_ocr = (
            "ชื่อบริษัท: บริษัท เชียงใหม่มีเดีย จำกัด (สำนักงานใหญ่)\n"
            "เลขประจำตัวผู้เสียภาษี: 0505560000123\n"
            "ที่อยู่: 123 ถ.ห้วยแก้ว ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300\n"
            "เบอร์โทร: 053-241999"
        )
        with patch("line_bot_server.extract_vision_ocr_text_from_image", return_value=mock_ocr):
            result = resolve_quoted_message_content(msg_id, session_id="test_session")

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("[ข้อมูลที่สแกนได้จากรูปภาพที่ผู้ใช้อ้างอิง]:"))
        self.assertIn("บริษัท เชียงใหม่มีเดีย จำกัด", result)
        self.assertIn("0505560000123", result)

    def test_quoted_image_vision_ocr_session_fallback(self):
        """Verify resolve_quoted_message_content falls back to SESSION_LAST_IMAGE if not in cache."""
        dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        session_id = "session_fallback_test"
        SESSION_LAST_IMAGE[session_id] = dummy_jpeg

        mock_ocr = "สแกนภาพเอกสาร: บริษัท ทดสอบ จำกัด เลขประจำตัวผู้เสียภาษี 0105559000111"
        with patch("line_bot_server.download_line_image_content", return_value=None):
            with patch("line_bot_server.extract_vision_ocr_text_from_image", return_value=mock_ocr):
                result = resolve_quoted_message_content("unknown_id", session_id=session_id)

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("[ข้อมูลที่สแกนได้จากรูปภาพที่ผู้ใช้อ้างอิง]:"))
        self.assertIn("0105559000111", result)

    # --------------------------------------------------------------------------
    # Mission 2: Multi-Item Table Support in create_financial_document
    # --------------------------------------------------------------------------
    def test_create_financial_document_tool_declaration_schema(self):
        """Verify GEMINI_AGENT_TOOL_DECLARATIONS has 'items' array parameter in create_financial_document."""
        create_doc_tool = next((t for t in GEMINI_AGENT_TOOL_DECLARATIONS if t["name"] == "create_financial_document"), None)
        self.assertIsNotNone(create_doc_tool)
        props = create_doc_tool["parameters"]["properties"]
        self.assertIn("items", props)
        self.assertEqual(props["items"]["type"], "ARRAY")
        item_props = props["items"]["items"]["properties"]
        self.assertIn("desc", item_props)
        self.assertIn("qty", item_props)
        self.assertIn("price", item_props)

    def test_execute_agent_tool_multi_item_support(self):
        """Verify execute_agent_tool synchronizes amount from items and passes items to document engine."""
        multi_items = [
            {"desc": "ถ่ายภาพนิ่งบ้านพร้อมอยู่ 3 ห้องนอน 3 ห้องน้ำ", "qty": 1, "price": 10000.0, "amount": 10000.0},
            {"desc": "บันทึกวิดีโอ 4K และตัดต่อ Reels 3 คลิป", "qty": 2, "price": 5000.0, "amount": 10000.0}
        ]
        args = {
            "doc_type": "quotation",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งานบริการถ่ายภาพและสื่อ",
            "amount": 0.0,  # Should be auto-calculated to 20,000.0
            "items": multi_items,
            "is_vat": True,
            "wht_rate": 3.0
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success", "pdfUrl": "https://drive.google.com/mock_qt"}
            res_data, flex_card = execute_agent_tool("create_financial_document", args, session_id="test_multi_item")

        self.assertEqual(res_data["doc_type"], "quotation")
        self.assertIsNotNone(res_data.get("doc_no"))
        totals = res_data.get("totals", {})
        self.assertEqual(totals.get("subtotal"), 20000.0)
        self.assertEqual(totals.get("pre_vat"), 20000.0)
        self.assertEqual(totals.get("vat_amount"), 1400.0)
        self.assertEqual(totals.get("wht_amount"), 0.0)  # Quotation strictly 0% WHT
        self.assertEqual(totals.get("net_total"), 21400.0)  # Grand Total = 20,000 + 1,400

    def test_multi_item_html_table_rendering(self):
        """Verify render_document_html generates distinct table rows (ลำดับ 1, 2, 3) for multi items."""
        multi_items = [
            {"desc": "ถ่ายภาพนิ่งบ้านพร้อมอยู่", "qty": 1, "price": 12000.0, "amount": 12000.0},
            {"desc": "ตัดต่อวิดีโอ Cinematic Walkthrough", "qty": 1, "price": 8000.0, "amount": 8000.0},
            {"desc": "ถ่ายภาพมุมสูงด้วยโดรน 4K", "qty": 1, "price": 5000.0, "amount": 5000.0}
        ]
        doc_payload = {
            "doc_no": "QT2609-TEST",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "items": multi_items,
            "is_vat": True,
            "wht_rate": 3.0
        }

        html = render_document_html("quotation", doc_payload)
        self.assertIn("ถ่ายภาพนิ่งบ้านพร้อมอยู่", html)
        self.assertIn("ตัดต่อวิดีโอ Cinematic Walkthrough", html)
        self.assertIn("ถ่ายภาพมุมสูงด้วยโดรน 4K", html)
        # Check table row indexes
        self.assertIn('>1<', html)
        self.assertIn('>2<', html)
        self.assertIn('>3<', html)
        self.assertIn("25,000.00", html)  # Subtotal 12k + 8k + 5k

    # --------------------------------------------------------------------------
    # Mission 3: Google Drive Folder Locking & Col U in Google Sheets
    # --------------------------------------------------------------------------
    def test_drive_folder_candidates_quotation_and_types(self):
        """Verify DOC_TYPE_FOLDER_CANDIDATES includes full names for quotation, invoice, receipt, wht."""
        self.assertIn("01_Quotations_QT_ใบเสนอราคา", DOC_TYPE_FOLDER_CANDIDATES["quotation"])
        self.assertIn("01_Quotation", DOC_TYPE_FOLDER_CANDIDATES["quotation"])
        self.assertIn("02_Invoices_IV_ใบวางบิล", DOC_TYPE_FOLDER_CANDIDATES["invoice"])
        self.assertIn("03_Receipts_RE_สำหรับเรียกเก็บเงิน", DOC_TYPE_FOLDER_CANDIDATES["receipt"])
        self.assertIn("04_WHT_Certificates_หนังสือรับรองหักณที่จ่าย", DOC_TYPE_FOLDER_CANDIDATES["wht"])
        self.assertEqual(COMPANY_DRIVE_FOLDER_ID, "162o80GF4BPGGt-DlltxRvMFvAXxRWYOY")

    def test_quotation_row_col_u_has_pdf_url(self):
        """Verify build_sheet_row_data sets Column U (index 20) with Google Drive PDF URL."""
        test_pdf_url = "https://drive.google.com/file/d/162o80GF4BPGGt-DlltxRvMFvAXxRWYOY/view"
        doc_data = {
            "doc_no": "QT2609-COLU",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ทดสอบ Col U",
            "amount": 10000.0
        }
        sheet_name, row = build_sheet_row_data("quotation", doc_data, pdf_url=test_pdf_url)
        self.assertEqual(sheet_name, "ใบเสนอราคา")
        # Column U is index 20 (0-indexed: A=0, B=1, ..., U=20)
        self.assertEqual(row[20], test_pdf_url)

    def test_upload_document_pdf_targets_correct_folder_and_doc_no(self):
        """Verify upload_document_pdf defaults to GHN168 Drive folder ID and passes docNo."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "status": "success",
                "pdfUrl": "https://drive.google.com/file/d/mock_qt/view"
            }
            res = upload_document_pdf(
                pdf_path_or_bytes=b"%PDF-1.4 dummy",
                pdf_name="QT2609-001_20260906.pdf",
                doc_type="quotation",
                doc_no="QT2609-001"
            )
            self.assertEqual(res.get("status"), "success")
            self.assertIn("pdfUrl", res)
            call_payload = mock_post.call_args[1]["json"]
            self.assertEqual(call_payload["parentFolderId"], "162o80GF4BPGGt-DlltxRvMFvAXxRWYOY")
            self.assertEqual(call_payload["docNo"], "QT2609-001")

    # --------------------------------------------------------------------------
    # Mission 4: LINE Notification Target ID Locking
    # --------------------------------------------------------------------------
    def test_line_notification_target_id_fallback(self):
        """Verify LINE_NOTIFICATION_TARGET_ID is locked to Cd7b3d3b7a0fe061f341ec031c6edac8c."""
        self.assertEqual(LINE_NOTIFICATION_TARGET_ID, "Cd7b3d3b7a0fe061f341ec031c6edac8c")


    def test_google_sheets_sync_script_has_folder_and_col_u_logic(self):
        """Verify google_sheets_sync_script.gs includes getDriveSubFolder, candidate names, and Col U update."""
        gs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_sheets_sync_script.gs")
        with open(gs_path, "r", encoding="utf-8") as f:
            gs_content = f.read()

        self.assertIn("01_Quotations_QT_ใบเสนอราคา", gs_content)
        self.assertIn("02_Invoices_IV_ใบวางบิล", gs_content)
        self.assertIn("03_Receipts_RE_สำหรับเรียกเก็บเงิน", gs_content)
        self.assertIn("04_WHT_Certificates_หนังสือรับรองหักณที่จ่าย", gs_content)
        self.assertIn("function getDriveSubFolder", gs_content)
        self.assertIn("function updateQuotationPdfUrl", gs_content)
        self.assertIn("qSheet.getRange(qi + 2, 21).setValue(pdfUrl)", gs_content)


if __name__ == "__main__":
    unittest.main()
