#!/usr/bin/env python3
"""
================================================================================
GHN168 PDF Generation & Accounting Flow Test Suite
================================================================================
Comprehensive End-to-End Tests for:
1. Thai Baht Text Conversion (thai_baht_text)
2. Document Template Engine (Quotation, Invoice, Receipt, WHT 50 Bis)
3. Total & Tax Calculations (Subtotal, Discount, VAT 7%, WHT, Net Total)
4. Google Drive & Google Sheets Sync Service (ghn168_sync_service)
5. LINE Bot Flex Message Card Generation & FastAPI Endpoints
================================================================================
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Import Modules under test
from document_template_engine import (
    DEFAULT_COMPANY_INFO,
    calculate_document_totals,
    format_currency,
    get_asset_base64,
    get_default_assets,
    render_document_html,
    render_invoice_html,
    render_quotation_html,
    render_receipt_html,
    render_wht_html,
    thai_baht_text,
)
from local_pdf_engine import (
    convert_html_to_pdf_local,
    find_chromium_binary,
    generate_document_pdf,
    get_local_pdf_path,
    get_pdf_storage_dir,
)
from ghn168_sync_service import (
    build_sheet_row_data,
    generate_and_sync_document,
    normalize_doc_type,
    sync_document_to_sheets,
    upload_document_html,
    upload_document_pdf,
)
from line_bot_server import (
    app,
    build_document_flex_message,
    is_document_creation_request,
    verify_line_signature,
)


class TestThaiBahtTextConversion(unittest.TestCase):
    """Test suite for 100% precision Thai Baht text conversion."""

    def test_zero_and_empty(self):
        self.assertEqual(thai_baht_text(0), "ศูนย์บาทถ้วน")
        self.assertEqual(thai_baht_text(0.0), "ศูนย์บาทถ้วน")
        self.assertEqual(thai_baht_text(None), "ศูนย์บาทถ้วน")
        self.assertEqual(thai_baht_text(""), "ศูนย์บาทถ้วน")

    def test_units_and_tens(self):
        self.assertEqual(thai_baht_text(1), "หนึ่งบาทถ้วน")
        self.assertEqual(thai_baht_text(5), "ห้าบาทถ้วน")
        self.assertEqual(thai_baht_text(10), "สิบบาทถ้วน")
        self.assertEqual(thai_baht_text(11), "สิบเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(20), "ยี่สิบบาทถ้วน")
        self.assertEqual(thai_baht_text(21), "ยี่สิบเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(25), "ยี่สิบห้าบาทถ้วน")
        self.assertEqual(thai_baht_text(99), "เก้าสิบเก้าบาทถ้วน")

    def test_hundreds_and_thousands(self):
        self.assertEqual(thai_baht_text(100), "หนึ่งร้อยบาทถ้วน")
        self.assertEqual(thai_baht_text(101), "หนึ่งร้อยเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(111), "หนึ่งร้อยสิบเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(1000), "หนึ่งพันบาทถ้วน")
        self.assertEqual(thai_baht_text(1001), "หนึ่งพันเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(1250), "หนึ่งพันสองร้อยห้าสิบบาทถ้วน")
        self.assertEqual(thai_baht_text(10000), "หนึ่งหมื่นบาทถ้วน")
        self.assertEqual(thai_baht_text(100000), "หนึ่งแสนบาทถ้วน")

    def test_millions_and_large_numbers(self):
        self.assertEqual(thai_baht_text(1000000), "หนึ่งล้านบาทถ้วน")
        self.assertEqual(thai_baht_text(1000001), "หนึ่งล้านเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(10000000), "สิบล้านบาทถ้วน")
        self.assertEqual(thai_baht_text(20000000), "ยี่สิบล้านบาทถ้วน")
        self.assertEqual(thai_baht_text(100000000), "หนึ่งร้อยล้านบาทถ้วน")
        self.assertEqual(thai_baht_text(1000000000), "หนึ่งพันล้านบาทถ้วน")
        self.assertEqual(thai_baht_text(1000000000000), "หนึ่งล้านล้านบาทถ้วน")

    def test_satang_decimals(self):
        self.assertEqual(thai_baht_text(0.01), "ศูนย์บาทหนึ่งสตางค์")
        self.assertEqual(thai_baht_text(0.11), "ศูนย์บาทสิบเอ็ดสตางค์")
        self.assertEqual(thai_baht_text(0.25), "ศูนย์บาทยี่สิบห้าสตางค์")
        self.assertEqual(thai_baht_text(0.50), "ศูนย์บาทห้าสิบสตางค์")
        self.assertEqual(thai_baht_text(0.75), "ศูนย์บาทเจ็ดสิบห้าสตางค์")
        self.assertEqual(thai_baht_text(1250.50), "หนึ่งพันสองร้อยห้าสิบบาทห้าสิบสตางค์")
        self.assertEqual(thai_baht_text(12345678.25), "สิบสองล้านสามแสนสี่หมื่นห้าพันหกร้อยเจ็ดสิบแปดบาทยี่สิบห้าสตางค์")


class TestDocumentTemplateEngine(unittest.TestCase):
    """Test suite for HTML document templates and calculations."""

    def setUp(self):
        self.sample_items = [
            {"desc": "ถ่ายทำวิดีโอ 1 วัน", "qty": 1, "unit": "วัน", "price": 15000},
            {"desc": "ตัดต่อและเกรดสี Master", "qty": 2, "unit": "คลิป", "price": 5000}
        ]

    def test_calculate_document_totals(self):
        # 15000 + (2*5000) = 25000
        # Pre-VAT: 25000
        # VAT 7%: 1750
        # WHT 3%: 750 (calculated on Pre-VAT 25000)
        # Net Total: 25000 + 1750 - 750 = 26000
        totals = calculate_document_totals(
            items=self.sample_items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,
            discount=0.0
        )
        self.assertEqual(totals["subtotal"], 25000.0)
        self.assertEqual(totals["pre_vat"], 25000.0)
        self.assertEqual(totals["vat_amount"], 1750.0)
        self.assertEqual(totals["wht_amount"], 750.0)
        self.assertEqual(totals["net_total"], 26000.0)
        self.assertEqual(totals["baht_text"], "สองหมื่นหกพันบาทถ้วน")

    def test_calculate_with_discount(self):
        totals = calculate_document_totals(
            items=self.sample_items,
            is_vat=True,
            vat_rate=0.07,
            wht_rate=3.0,
            discount=5000.0
        )
        # Subtotal: 25000, Discount: 5000 -> Pre-VAT: 20000
        # VAT 7%: 1400, WHT 3%: 600 -> Net: 20000 + 1400 - 600 = 20800
        self.assertEqual(totals["subtotal"], 25000.0)
        self.assertEqual(totals["discount"], 5000.0)
        self.assertEqual(totals["pre_vat"], 20000.0)
        self.assertEqual(totals["vat_amount"], 1400.0)
        self.assertEqual(totals["wht_amount"], 600.0)
        self.assertEqual(totals["net_total"], 20800.0)

    def test_calculate_document_totals_lump_sum(self):
        totals = calculate_document_totals(
            items=[
                {"desc": "งานผลิตสื่อวิดีโอ", "amount": 30000.0},
                {"desc": "งานบันทึกเสียง", "amount": 10000.0}
            ],
            is_vat=True
        )
        # Subtotal: 40000, VAT 7%: 2800 -> Net: 42800
        self.assertEqual(totals["subtotal"], 40000.0)
        self.assertEqual(totals["vat_amount"], 2800.0)
        self.assertEqual(totals["net_total"], 42800.0)
        self.assertEqual(totals["baht_text"], "สี่หมื่นสองพันแปดร้อยบาทถ้วน")

    def test_render_quotation_html(self):
        html = render_quotation_html({
            "doc_no": "QT-202608-001",
            "client_name": "บริษัท สตาร์ตอัป เชียงใหม่ จำกัด",
            "items": self.sample_items,
            "is_vat": True,
            "wht_rate": 3.0
        })
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("ใบเสนอราคา", html)
        self.assertIn("QUOTATION", html)
        self.assertIn("QT-202608-001", html)
        self.assertIn("บริษัท สตาร์ตอัป เชียงใหม่ จำกัด", html)
        self.assertIn("ภาษีมูลค่าเพิ่ม / VAT (7%)", html)
        self.assertIn("สองหมื่นหกพันบาทถ้วน", html)
        # Verify 3-column table
        self.assertIn('<th class="center" style="width: 50px;">ลำดับ</th>', html)
        self.assertIn('<th>รายการ / รายละเอียด (Description)</th>', html)
        self.assertIn('<th class="right" style="width: 140px;">จำนวนเงิน</th>', html)
        self.assertNotIn("ราคาต่อหน่วย", html)
        # Verify 3-column signature layout (left removed, seal centered, right signer)
        self.assertNotIn("ผู้สั่งซื้อ / ตกลงว่าจ้าง", html)
        self.assertNotIn("ผู้รับบริการ / ผู้จ่ายเงิน", html)
        self.assertIn("seal-watermark-center", html)
        self.assertIn("signature-card", html)
        assets = get_default_assets()
        if assets.get("logo_base64") or assets.get("seal_base64"):
            self.assertIn("data:image/png;base64,", html)  # Base64 assets embedded

    def test_render_invoice_html(self):
        html = render_invoice_html({
            "doc_no": "IV-202608-001",
            "client_name": "บริษัท มีเดีย โปรดักชั่น จำกัด",
            "items": self.sample_items,
            "payment_terms": "โอนเงินภายใน 30 วัน",
            "is_vat": True
        })
        self.assertIn("ใบวางบิล / ใบแจ้งหนี้", html)
        self.assertIn("INVOICE / BILLING NOTE", html)
        self.assertIn("IV-202608-001", html)
        self.assertIn("ภาษีมูลค่าเพิ่ม / VAT (7%)", html)
        self.assertIn("520-0-61960-2", html)  # KTB Bank Account
        # Verify 3-column table
        self.assertIn('<th class="center" style="width: 50px;">ลำดับ</th>', html)
        self.assertIn('<th>รายการ / รายละเอียด (Description)</th>', html)
        self.assertIn('<th class="right" style="width: 140px;">จำนวนเงิน</th>', html)
        self.assertNotIn("ราคาต่อหน่วย", html)
        # Verify left box removed and seal centered
        self.assertNotIn("ผู้สั่งซื้อ / ตกลงว่าจ้าง", html)
        self.assertNotIn("ผู้รับบริการ / ผู้จ่ายเงิน", html)
        self.assertIn("seal-watermark-center", html)

    def test_render_receipt_html(self):
        html = render_receipt_html({
            "doc_no": "RE-202608-001",
            "client_name": "บริษัท เชียงใหม่ ครีเอทีฟ จำกัด",
            "items": self.sample_items,
            "is_vat": True
        })
        self.assertIn("ใบเสร็จรับเงิน / ใบกำกับภาษี", html)
        self.assertIn("RECEIPT / TAX INVOICE", html)
        self.assertIn("RE-202608-001", html)
        self.assertIn("ภาษีมูลค่าเพิ่ม / VAT (7%)", html)
        # Verify 3-column table
        self.assertIn('<th class="center" style="width: 50px;">ลำดับ</th>', html)
        self.assertIn('<th>รายการ / รายละเอียด (Description)</th>', html)
        self.assertIn('<th class="right" style="width: 140px;">จำนวนเงิน</th>', html)
        self.assertNotIn("ราคาต่อหน่วย", html)
        # Verify left box removed and seal centered
        self.assertNotIn("ผู้สั่งซื้อ / ตกลงว่าจ้าง", html)
        self.assertNotIn("ผู้รับบริการ / ผู้จ่ายเงิน", html)
        self.assertIn("seal-watermark-center", html)
        # Verify Payment details box is completely removed from Receipt
        self.assertNotIn("รายละเอียดการชำระเงิน (Payment Details):", html)
        self.assertNotIn("รายละเอียดการชำระเงิน", html)
        self.assertNotIn("ในกรณีชำระด้วยเช็ค", html)

    def test_render_receipt_html_with_remarks(self):
        html = render_receipt_html({
            "doc_no": "RE-202608-002",
            "client_name": "บริษัท เชียงใหม่ ครีเอทีฟ จำกัด",
            "items": self.sample_items,
            "remarks": "ชำระเงินครบถ้วนเรียบร้อยแล้ว",
            "is_vat": True
        })
        self.assertNotIn("รายละเอียดการชำระเงิน", html)
        self.assertNotIn("Payment Details", html)
        self.assertIn("หมายเหตุ (Remarks):", html)
        self.assertIn("ชำระเงินครบถ้วนเรียบร้อยแล้ว", html)

    def test_render_wht_html(self):
        html = render_wht_html({
            "doc_no": "WHT-202608-001",
            "payee_name": "นาย ณัฐวัฒน์ ปวงจันทร์หอม (คุณหอม)",
            "payee_tax_id": "1509900596688",
            "gross_amount": 20000.0,
            "wht_rate": 3.0,
            "income_desc": "ค่าบริการตัดต่อและกราฟิกโปรเจกต์พิเศษ"
        })
        self.assertIn("หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ)", html)
        self.assertIn("WHT-202608-001", html)
        self.assertIn("นาย ณัฐวัฒน์ ปวงจันทร์หอม", html)
        self.assertIn("1509900596688", html)
        self.assertIn("600.00", html)  # 3% of 20000 = 600
        self.assertIn("หกร้อยบาทถ้วน", html)
        # Verify WHT signer is locked to ณัฐนรี วงศ์สกุลยานนท์ with title
        self.assertIn("ณัฐนรี วงศ์สกุลยานนท์", html)
        self.assertIn("ผู้มีหน้าที่หักภาษี ณ ที่จ่าย / ผู้มีอำนาจลงนาม", html)
        # Verify no company seal and no digital signature image in WHT signature container
        sig_container_html = html[html.find('class="signatures-container'):]
        self.assertNotIn("<img", sig_container_html)
        self.assertNotIn('alt="Company Seal"', html)
        self.assertNotIn('alt="Signature"', html)


class TestGhn168SyncService(unittest.TestCase):
    """Test suite for Google Apps Script Webhook synchronization and Drive upload."""

    def setUp(self):
        self.patcher = patch("requests.post")
        self.mock_post = self.patcher.start()
        def mock_post_handler(url, json=None, **kwargs):
            mock_res = MagicMock()
            mock_res.status_code = 200
            payload = json or {}
            req_type = payload.get("type", "")
            if req_type in ["upload_pdf_base64", "upload_pdf", "upload_html"]:
                mock_res.json.return_value = {
                    "status": "success",
                    "pdfUrl": "https://drive.google.com/mock_flow_test.pdf",
                    "message": "Mock upload"
                }
            else:
                mock_res.json.return_value = {
                    "status": "success",
                    "message": "Mock sync"
                }
            return mock_res
        self.mock_post.side_effect = mock_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_upload_document_pdf_bytes(self):
        dummy_bytes = b"%PDF-1.4 mock binary pdf data"
        res = upload_document_pdf(
            pdf_path_or_bytes=dummy_bytes,
            pdf_name="QT-TEST-001.pdf",
            doc_type="quotation",
            script_url="https://script.google.com/macros/s/mock/exec"
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["pdfUrl"], "https://drive.google.com/mock_flow_test.pdf")

    def test_upload_document_pdf_file(self):
        temp_pdf = Path(__file__).parent / "test_upload_temp.pdf"
        temp_pdf.write_bytes(b"%PDF-1.4 temp file test content")
        try:
            res = upload_document_pdf(
                pdf_path_or_bytes=str(temp_pdf),
                pdf_name="IV-TEST-001.pdf",
                doc_type="invoice",
                script_url="https://script.google.com/macros/s/mock/exec"
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["pdfUrl"], "https://drive.google.com/mock_flow_test.pdf")
        finally:
            if temp_pdf.exists():
                temp_pdf.unlink()

    def test_normalize_doc_type(self):
        self.assertEqual(normalize_doc_type("QT"), "quotation")
        self.assertEqual(normalize_doc_type("ใบเสนอราคา"), "quotation")
        self.assertEqual(normalize_doc_type("IV"), "invoice")
        self.assertEqual(normalize_doc_type("ใบวางบิล"), "invoice")
        self.assertEqual(normalize_doc_type("RE"), "receipt")
        self.assertEqual(normalize_doc_type("50ทวิ"), "wht")
        self.assertEqual(normalize_doc_type("wht"), "wht")

    def test_build_sheet_row_data_quotation(self):
        sheet_name, row = build_sheet_row_data("quotation", {
            "doc_no": "QT-TEST-001",
            "client_name": "ลูกค้า ก",
            "project_name": "งานโฆษณา",
            "items": [{"desc": "งานถ่ายทำ", "qty": 1, "price": 10000}],
            "is_vat": True,
            "wht_rate": 3.0
        })
        self.assertEqual(sheet_name, "ใบเสนอราคา")
        self.assertEqual(len(row), 23)
        self.assertEqual(row[2], "QT-TEST-001")  # Doc No
        self.assertEqual(row[3], "ลูกค้า ก")     # Client Name
        self.assertEqual(row[9], 10000.0)       # Pre-VAT
        self.assertEqual(row[10], 700.0)        # VAT 7%
        self.assertEqual(row[11], 300.0)        # WHT 3%
        self.assertEqual(row[12], 10400.0)      # Net Total

    def test_build_sheet_row_data_receipt(self):
        sheet_name, row = build_sheet_row_data("receipt", {
            "doc_no": "RE-TEST-001",
            "client_name": "ลูกค้า ข",
            "project_name": "งานผลิตสื่อ",
            "items": [{"desc": "โปรดักชั่น", "qty": 1, "price": 20000}],
            "is_vat": True
        }, pdf_url="https://drive.google.com/test_pdf")
        self.assertEqual(sheet_name, "รายรับ")
        self.assertEqual(len(row), 24)
        self.assertEqual(row[2], "RE-TEST-001")
        self.assertEqual(row[19], "https://drive.google.com/test_pdf")

    def test_build_sheet_row_data_wht(self):
        sheet_name, row = build_sheet_row_data("wht", {
            "doc_no": "WHT-TEST-001",
            "payee_name": "คุณเก่ง",
            "payee_tax_id": "3509900218949",
            "gross_amount": 10000.0,
            "wht_rate": 3.0
        })
        self.assertEqual(sheet_name, "รายจ่าย")
        self.assertEqual(len(row), 25)
        self.assertEqual(row[3], "คุณเก่ง")
        self.assertEqual(row[12], 3.0)
        self.assertEqual(row[13], 300.0)

    def test_generate_and_sync_document_simulation(self):
        result = generate_and_sync_document("quotation", {
            "client_name": "บริษัท ทดสอบระบบ จำกัด",
            "project_name": "ทดสอบ Flow ออกเอกสาร",
            "items": [{"desc": "ค่าบริการ", "qty": 1, "price": 5000}],
            "is_vat": True
        })
        self.assertIn(result["status"], ["success", "simulation"])
        self.assertTrue(result["doc_no"].startswith("QT-"))
        self.assertIn("pdf_url", result)
        self.assertGreater(result["html_length"], 1000)
        self.assertEqual(result["sheet_name"], "ใบเสนอราคา")


class TestLineBotServerEndpoints(unittest.TestCase):
    """Test suite for LINE Bot Server endpoints, Flex Messages, and Webhook."""

    def setUp(self):
        self.client = TestClient(app)
        self.patcher = patch("requests.post")
        self.mock_post = self.patcher.start()
        def mock_post_handler(url, json=None, **kwargs):
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {
                "status": "success",
                "pdfUrl": "https://drive.google.com/mock_flow_test.pdf",
                "message": "Mock response"
            }
            return mock_res
        self.mock_post.side_effect = mock_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("GHN168", data["bot_name"])

    def test_is_document_creation_request(self):
        self.assertTrue(is_document_creation_request("ขอออกใบเสนอราคาให้บริษัท ABC ยอด 20000"))
        self.assertTrue(is_document_creation_request("ทำใบแจ้งหนี้ให้หน่อยครับ"))
        self.assertTrue(is_document_creation_request("ออก 50 ทวิ ให้คุณหอม 15,000"))
        self.assertFalse(is_document_creation_request("สวัสดีค่ะ สอบถามข้อมูลบริษัทหน่อย"))

    def test_build_document_flex_message(self):
        sample_doc_res = {
            "doc_type": "quotation",
            "doc_no": "QT-202608-FLEX",
            "client_name": "บริษัท เฟล็กซ์ เมสเสจ จำกัด",
            "project_name": "ทดสอบ Flex Bubble",
            "pdf_url": "https://drive.google.com/test_doc_preview",
            "sheet_name": "ใบเสนอราคา",
            "totals": {
                "pre_vat": 10000.0,
                "vat_amount": 700.0,
                "wht_amount": 300.0,
                "net_total": 10400.0,
                "wht_rate": 3.0,
                "baht_text": "หนึ่งหมื่นสี่ร้อยบาทถ้วน"
            }
        }
        flex = build_document_flex_message(sample_doc_res)
        self.assertEqual(flex["type"], "flex")
        self.assertIn("QT-202608-FLEX", flex["altText"])
        self.assertEqual(flex["contents"]["type"], "bubble")
        self.assertEqual(flex["contents"]["footer"]["contents"][0]["action"]["uri"], "https://drive.google.com/test_doc_preview")

    def test_api_create_document(self):
        payload = {
            "doc_type": "quotation",
            "doc_data": {
                "client_name": "บริษัท ทดสอบ API จำกัด",
                "project_name": "ทดสอบ Endpoint",
                "items": [{"desc": "พัฒนาฟีเจอร์", "qty": 1, "price": 12000}],
                "is_vat": True,
                "wht_rate": 3.0
            }
        }
        res = self.client.post("/api/create_document", json=payload)
        self.assertIn(res.status_code, [200, 201])
        data = res.json()
        self.assertIn(data["status"], ["success", "simulation"])
        self.assertTrue(data["doc_no"].startswith("QT-"))
        self.assertEqual(data["totals"]["net_total"], 12480.0)

    def test_api_document_preview_html(self):
        res = self.client.get("/api/document_preview/quotation?client_name=PreviewCompany&amount=25000")
        self.assertEqual(res.status_code, 200)
        self.assertIn("<!DOCTYPE html>", res.text)
        self.assertIn("PreviewCompany", res.text)

    def test_api_serve_document_pdf(self):
        """Test GET /api/documents/pdf/{doc_no} serving generated PDF or live rendered PDF."""
        # Ensure a test PDF exists
        test_doc_no = "TEST-PDF-001"
        storage = get_pdf_storage_dir()
        dummy_pdf = storage / f"{test_doc_no}.pdf"
        with open(dummy_pdf, "wb") as f:
            f.write(b"%PDF-1.4 dummy valid bytes " + b"X" * 1500)
        
        try:
            res = self.client.get(f"/api/documents/pdf/{test_doc_no}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("content-type"), "application/pdf")
            self.assertIn("attachment", res.headers.get("content-disposition", "").lower() or "inline" in res.headers.get("content-disposition", "").lower() or "test-pdf-001.pdf" in res.headers.get("content-disposition", "").lower())
            self.assertGreater(len(res.content), 1000)
        finally:
            if dummy_pdf.exists():
                dummy_pdf.unlink()

    def test_end_to_end_m_cool_document_generation_with_full_details(self):
        """Verify full quotation generation for M-Cool House with Tax ID 13 digits, Boss Keng signer, and 7% VAT."""
        doc_payload = {
            "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
            "client_tax_id": "0505568016475",
            "client_branch": "00000",
            "client_address": "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
            "client_phone": "092-419-3953",
            "project_name": "ถ่าย Event 3 วัน",
            "items": [{"desc": "ถ่าย Event 3 วัน", "qty": 1, "price": 18000.0}],
            "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
            "is_vat": True,
            "vat_rate": 0.07,
            "wht_rate": 0.0
        }

        res = generate_and_sync_document("quotation", doc_payload)
        self.assertEqual(res["client_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(res["totals"]["pre_vat"], 18000.0)
        self.assertEqual(res["totals"]["vat_amount"], 1260.0)
        self.assertEqual(res["totals"]["net_total"], 19260.0)
        self.assertEqual(res["totals"]["baht_text"], "หนึ่งหมื่นเก้าพันสองร้อยหกสิบบาทถ้วน")

        # HTML verification
        html = render_document_html("quotation", doc_payload)
        self.assertIn("บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด", html)
        self.assertIn("0505568016475", html)
        self.assertIn("21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180", html)
        self.assertIn("นาย มงคล วงศ์สกุลยานนท์", html)
        self.assertIn("19,260.00", html)
        self.assertIn("หนึ่งหมื่นเก้าพันสองร้อยหกสิบบาทถ้วน", html)
        print("✅ End-to-end M-Cool House document generation & full detail rendering verified 100%.")

    def test_end_to_end_m_cool_receipt_generation_with_wht(self):
        """Verify full receipt generation for M-Cool House with 3% WHT, Boss Keng signer, and ref invoice."""
        doc_payload = {
            "doc_no": "RE-202608-586",
            "ref_invoice_no": "IV-202608-586",
            "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
            "client_tax_id": "0505568016475",
            "client_branch": "สำนักงานใหญ่ (00000)",
            "client_address": "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
            "client_phone": "092-419-3953",
            "project_name": "Thailand Food Therapy FESTIVAL",
            "items": [{"desc": "ถ่ายภาพ Event 3 วัน", "qty": 1, "price": 18000.0, "amount": 18000.0}],
            "is_vat": True,
            "vat_rate": 0.07,
            "wht_rate": 3.0,
            "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
            "receiving_bank": "KTB",
            "payment_status": "ชำระเงินแล้ว",
            "profit_share": "บริษัท (กองกลาง 100%)"
        }

        res = generate_and_sync_document("receipt", doc_payload)
        self.assertEqual(res["client_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(res["totals"]["pre_vat"], 18000.0)
        self.assertEqual(res["totals"]["vat_amount"], 1260.0)
        self.assertEqual(res["totals"]["gross_amount"], 19260.0)
        self.assertEqual(res["totals"]["wht_amount"], 540.0)
        self.assertEqual(res["totals"]["net_total"], 18720.0)
        self.assertEqual(res["totals"]["baht_text"], "หนึ่งหมื่นแปดพันเจ็ดร้อยยี่สิบบาทถ้วน")

        # HTML verification
        html = render_document_html("receipt", doc_payload)
        self.assertIn("ใบเสร็จรับเงิน / ใบกำกับภาษี", html)
        self.assertIn("RE-202608-586", html)
        self.assertIn("IV-202608-586", html)
        self.assertIn("บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด", html)
        self.assertIn("0505568016475", html)
        self.assertIn("21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180", html)
        self.assertIn("นาย มงคล วงศ์สกุลยานนท์", html)
        self.assertIn("18,720.00", html)
        self.assertIn("หนึ่งหมื่นแปดพันเจ็ดร้อยยี่สิบบาทถ้วน", html)
        print("✅ End-to-end M-Cool Receipt generation & 3% WHT rendering verified 100%.")


class TestLocalPdfEngine(unittest.TestCase):
    """Test suite for Headless Chromium local PDF engine functions."""

    def test_get_pdf_storage_dir(self):
        storage = get_pdf_storage_dir()
        self.assertTrue(storage.exists())
        self.assertTrue(os.path.isdir(storage))

    def test_find_chromium_binary(self):
        # find_chromium_binary returns string path or None
        binary = find_chromium_binary()
        if binary:
            self.assertTrue(os.path.isfile(binary) or os.path.islink(binary))

    def test_get_local_pdf_path_not_found(self):
        self.assertIsNone(get_local_pdf_path("NON-EXISTENT-DOC-999"))


if __name__ == "__main__":
    print("=" * 80)
    print("Running Full GHN168 PDF Generation & Accounting Flow Test Suite...")
    print("=" * 80)
    unittest.main(verbosity=2)
