#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for GHN168:
1. Font Upgrade to IBM Plex Sans Thai
2. Company Seal Enlargement (220px - 240px)
3. Branch & Tax ID Formatting (Branch appended to name, Tax ID is raw 13 digits)
4. PDFShift Removal & Local / Browser PDF Generation
"""

import os
import re
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from document_template_engine import (
    format_company_name_with_branch,
    render_document_html,
    render_wht_html,
    DEFAULT_COMPANY_INFO,
    BASE_DOCUMENT_CSS
)
from local_pdf_engine import convert_html_to_pdf_local, find_chromium_binary


class TestDocumentStylingAndFormatting(unittest.TestCase):
    """Test suite for document typography, seal sizing, and branch/tax formatting."""

    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.index_html_path = self.base_dir / "index.html"
        self.app_js_path = self.base_dir / "app.js"
        self.doc_engine_path = self.base_dir / "document_template_engine.py"

        with open(self.index_html_path, "r", encoding="utf-8") as f:
            self.index_html_content = f.read()

        with open(self.app_js_path, "r", encoding="utf-8") as f:
            self.app_js_content = f.read()

        with open(self.doc_engine_path, "r", encoding="utf-8") as f:
            self.doc_engine_content = f.read()

    # -------------------------------------------------------------------------
    # TASK 1: FONT UPGRADE
    # -------------------------------------------------------------------------
    def test_font_family_in_document_template_engine(self):
        """Verify IBM Plex Sans Thai is configured in BASE_DOCUMENT_CSS and Google Fonts."""
        self.assertIn("IBM Plex Sans Thai", BASE_DOCUMENT_CSS)
        self.assertIn("family=IBM+Plex+Sans+Thai", BASE_DOCUMENT_CSS)
        self.assertIn("'IBM Plex Sans Thai', 'Outfit', 'Inter', 'Sukhumvit Set', sans-serif", BASE_DOCUMENT_CSS)

    def test_font_family_in_index_html(self):
        """Verify index.html uses IBM Plex Sans Thai for .doc-paper and .wht-card-paper."""
        self.assertIn("family=IBM+Plex+Sans+Thai", self.index_html_content)
        self.assertIn(".doc-paper", self.index_html_content)
        # Check that doc-paper font-family contains IBM Plex Sans Thai
        doc_paper_match = re.search(r'\.doc-paper\s*\{[^}]*font-family:\s*([^;]+);', self.index_html_content)
        self.assertIsNotNone(doc_paper_match, ".doc-paper CSS rule not found")
        self.assertIn("IBM Plex Sans Thai", doc_paper_match.group(1))

        # Check wht-card-paper
        wht_paper_match = re.search(r'\.wht-card-paper\s*\{[^}]*font-family:\s*([^;]+);', self.index_html_content)
        self.assertIsNotNone(wht_paper_match, ".wht-card-paper CSS rule not found")
        self.assertIn("IBM Plex Sans Thai", wht_paper_match.group(1))

    # -------------------------------------------------------------------------
    # TASK 2: COMPANY SEAL ENLARGEMENT
    # -------------------------------------------------------------------------
    def test_seal_size_in_document_template_engine(self):
        """Verify seal watermark width is expanded to >= 220px in document_template_engine.py."""
        # Find .seal-watermark width
        seal_match = re.search(r'\.seal-watermark\s*\{[^}]*width:\s*(\d+)px;', BASE_DOCUMENT_CSS)
        self.assertIsNotNone(seal_match, ".seal-watermark width not found in BASE_DOCUMENT_CSS")
        seal_width = int(seal_match.group(1))
        self.assertGreaterEqual(seal_width, 220, f"Seal width {seal_width}px is less than 220px")
        self.assertLessEqual(seal_width, 250, f"Seal width {seal_width}px is greater than 250px")

    def test_seal_size_in_index_html(self):
        """Verify .company-seal-img in index.html is enlarged to >= 220px."""
        seal_img_match = re.search(r'\.company-seal-img\s*\{[^}]*width:\s*(\d+)px;', self.index_html_content)
        self.assertIsNotNone(seal_img_match, ".company-seal-img width rule not found in index.html")
        seal_width = int(seal_img_match.group(1))
        self.assertGreaterEqual(seal_width, 220, f"Company seal width {seal_width}px in index.html is less than 220px")
        self.assertLessEqual(seal_width, 250, f"Company seal width {seal_width}px in index.html is greater than 250px")

    # -------------------------------------------------------------------------
    # TASK 3: BRANCH & TAX ID FORMATTING
    # -------------------------------------------------------------------------
    def test_format_company_name_with_branch_helper(self):
        """Verify format_company_name_with_branch handles 00000, 00001, text branches, and prevents duplication."""
        # Head office cases
        self.assertEqual(
            format_company_name_with_branch("บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด", "00000"),
            "บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)"
        )
        self.assertEqual(
            format_company_name_with_branch("บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด", "สำนักงานใหญ่"),
            "บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)"
        )
        self.assertEqual(
            format_company_name_with_branch("บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)", "00000"),
            "บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)"
        )

        # Other branch cases
        self.assertEqual(
            format_company_name_with_branch("บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด", "00001"),
            "บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด (สาขาที่ 00001)"
        )
        self.assertEqual(
            format_company_name_with_branch("บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด", "1"),
            "บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด (สาขาที่ 00001)"
        )
        self.assertEqual(
            format_company_name_with_branch("บริษัท เอบีซี จำกัด", "สาขาเชียงใหม่"),
            "บริษัท เอบีซี จำกัด (สาขาเชียงใหม่)"
        )

    def test_rendered_standard_document_branch_and_tax_id(self):
        """Verify rendered quotation HTML has branch in company name and clean 13-digit tax ID."""
        doc_data = {
            "doc_no": "QT-202608-001",
            "doc_date": "2026-08-26",
            "client_name": "บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด",
            "client_tax_id": "0505561008771",
            "client_branch": "00000",
            "client_address": "123 ถ.นิมมานเหมินท์ ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200",
            "items": [
                {"desc": "บริการวางระบบ AI Agent สำหรับคลินิก", "qty": 1, "price": 45000, "amount": 45000}
            ],
            "vat_type": "none",
            "wht_rate": 0
        }

        html = render_document_html("quotation", doc_data)

        # 1. GHN168 seller name contains (สำนักงานใหญ่)
        self.assertIn("บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)", html)
        # 2. GHN168 Tax ID line has ONLY 13 digits without branch suffix
        self.assertIn("0505566010089", html)
        self.assertNotIn("0505566010089 (สำนักงานใหญ่)", html)
        self.assertNotIn("0505566010089(สำนักงานใหญ่)", html)

        # 3. Client name contains (สำนักงานใหญ่)
        self.assertIn("บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด (สำนักงานใหญ่)", html)
        # 4. Client Tax ID line has ONLY 13 digits without branch suffix
        self.assertIn("0505561008771", html)
        self.assertNotIn("0505561008771 (สำนักงานใหญ่)", html)

    def test_rendered_wht_document_branch_and_tax_id(self):
        """Verify rendered 50 Tawi WHT HTML has branch in name and clean 13-digit tax ID."""
        wht_data = {
            "doc_no": "WHT-202608-001",
            "doc_date": "2026-08-26",
            "payee_name": "บริษัท เชียงใหม่ ครีเอทีฟ ดีไซน์ จำกัด",
            "payee_tax_id": "0505562009912",
            "payee_branch": "00002",
            "payee_address": "88 หมู่ 5 ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",
            "description": "ค่าจ้างงานออกแบบกราฟิก",
            "amount": 20000,
            "wht_rate": 3
        }

        html = render_wht_html(wht_data)

        # 1. Payer (GHN168) has (สำนักงานใหญ่)
        self.assertIn("บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด (สำนักงานใหญ่)", html)
        # 2. Payer Tax ID is 13 digits without branch suffix
        self.assertIn("0505566010089", html)
        self.assertNotIn("0505566010089 (สำนักงานใหญ่)", html)

        # 3. Payee name has (สาขาที่ 00002)
        self.assertIn("บริษัท เชียงใหม่ ครีเอทีฟ ดีไซน์ จำกัด (สาขาที่ 00002)", html)
        # 4. Payee Tax ID is 13 digits without branch suffix
        self.assertIn("0505562009912", html)
        self.assertNotIn("0505562009912 (สาขาที่ 00002)", html)

    def test_app_js_branch_and_tax_id_logic(self):
        """Verify app.js implements formatCompanyNameWithBranch and does not append branch to tax ID."""
        self.assertIn("formatCompanyNameWithBranch", self.app_js_content)
        # Verify prevClientTaxId receives raw taxIdVal without branchText
        self.assertIn("prevClientTaxIdEl.textContent = taxIdVal;", self.app_js_content)
        self.assertNotIn("prevClientTaxId.textContent = taxIdVal + branchText", self.app_js_content)

    # -------------------------------------------------------------------------
    # TASK 4: REMOVE PDFSHIFT 100%
    # -------------------------------------------------------------------------
    def test_pdfshift_removed_from_index_html_and_app_js(self):
        """Verify PDFShift input field and API key are removed from index.html and app.js."""
        self.assertNotIn("settingPdfShiftApiKey", self.index_html_content)
        self.assertNotIn("ghn168_pdfshift_api_key", self.app_js_content)
        self.assertNotIn("pdfShiftApiKey", self.app_js_content)

    # -------------------------------------------------------------------------
    # TASK 5: VECTOR PDF GENERATION (VPS / CHROMIUM)
    # -------------------------------------------------------------------------
    def test_local_pdf_generation_without_pdfshift(self):
        """Verify local vector PDF generator works without PDFShift."""
        if sys.platform != 'linux' or not find_chromium_binary():
            self.skipTest("Chromium headless PDF engine is configured for Linux production VPS environment (srv1913532.hstgr.cloud).")

        doc_data = {
            "doc_no": "QT-TEST-VECTOR-01",
            "doc_date": "2026-08-26",
            "client_name": "บริษัท นอร์ทเทิร์น แล็บ คลินิกแล็บ จำกัด",
            "client_tax_id": "0505561008771",
            "client_branch": "00000",
            "client_address": "123 ถ.นิมมานเหมินท์ ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200",
            "items": [
                {"desc": "Vector PDF Generation Test Item", "qty": 1, "price": 1000, "amount": 1000}
            ],
            "vat_type": "none",
            "wht_rate": 0
        }

        html = render_document_html("quotation", doc_data)
        out_pdf = self.base_dir / "test_vector_output.pdf"

        try:
            res = convert_html_to_pdf_local(html_content=html, output_pdf_path=out_pdf, doc_no="QT-TEST-VECTOR-01")
            self.assertEqual(res.get("status"), "success", f"PDF render failed: {res}")
            self.assertTrue(out_pdf.exists(), "Output PDF was not created")
            self.assertGreater(out_pdf.stat().st_size, 1000, "Output PDF size is too small")

            with open(out_pdf, "rb") as f:
                header = f.read(5)
                self.assertEqual(header, b"%PDF-", "Generated file is not a valid PDF")
        finally:
            if out_pdf.exists():
                out_pdf.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
