#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for GHN168 Live Preview 50 Tawi (WHT) & V1.52 Cache Bumping:
1. WHT Modern Vector CSS Classes (.wht-header-badge, .wht-box-table, .wht-box-label)
2. #previewWhtDoc DOM Structure matching render_wht_html
3. app.js syncWhtPreview() Logic (Net tax words, Net paid amount, Boss Mod signer)
4. Cache Versioning v152 across sw.js and index.html
"""

import re
import unittest
from pathlib import Path


class TestWhtLivePreviewAndVersioning(unittest.TestCase):
    """Test suite for 50 Tawi live preview layout, sync logic, and cache bump."""

    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.index_html_path = self.base_dir / "index.html"
        self.app_js_path = self.base_dir / "app.js"
        self.sw_js_path = self.base_dir / "sw.js"

        with open(self.index_html_path, "r", encoding="utf-8") as f:
            self.index_html = f.read()

        with open(self.app_js_path, "r", encoding="utf-8") as f:
            self.app_js = f.read()

        with open(self.sw_js_path, "r", encoding="utf-8") as f:
            self.sw_js = f.read()

    def test_wht_css_classes_in_index_html(self):
        """Verify .wht-header-badge, .wht-box-table, and .wht-box-label styles exist in index.html."""
        self.assertIn(".wht-header-badge", self.index_html)
        self.assertIn(".wht-header-title", self.index_html)
        self.assertIn(".wht-header-subtitle", self.index_html)
        self.assertIn(".wht-box-table", self.index_html)
        self.assertIn(".wht-box-label", self.index_html)

        # Check background and border colors in .wht-header-badge
        self.assertIn("border: 2px solid #0f172a;", self.index_html)
        self.assertIn("background: #f8fafc;", self.index_html)
        self.assertIn("border-right: 1px solid #94a3b8 !important;", self.index_html)

    def test_wht_preview_dom_structure(self):
        """Verify #previewWhtDoc has modern vector PDF layout matching render_wht_html."""
        # Find previewWhtDoc container
        self.assertIn('<div id="previewWhtDoc" class="wht-card-paper"', self.index_html)

        # Header Badge
        self.assertIn('class="wht-header-badge"', self.index_html)
        self.assertIn('หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ)', self.index_html)
        self.assertIn('ตามมาตรา 50 ทวิ แห่งประมวลรัษฎากร (ฉบับสำหรับผู้ถูกหักภาษี ณ ที่จ่าย)', self.index_html)

        # Box Table (Payer, Payee, Doc)
        self.assertIn('class="wht-box-table"', self.index_html)
        self.assertIn('ผู้มีหน้าที่หักภาษี ณ ที่จ่าย (Payer):', self.index_html)
        self.assertIn('id="prevWhtSellerName"', self.index_html)
        self.assertIn('id="prevWhtSellerTaxId"', self.index_html)
        self.assertIn('id="prevWhtSellerAddress"', self.index_html)

        self.assertIn('ผู้ถูกหักภาษี ณ ที่จ่าย (Payee):', self.index_html)
        self.assertIn('id="prevWhtPayeeName"', self.index_html)
        self.assertIn('id="prevWhtPayeeTaxId"', self.index_html)
        self.assertIn('id="prevWhtPayeeAddress"', self.index_html)

        self.assertIn('ข้อมูลเอกสาร (Document):', self.index_html)
        self.assertIn('id="prevWhtDocNo"', self.index_html)
        self.assertIn('id="prevWhtDate"', self.index_html)

        # Money items table
        self.assertIn('class="items-table paper-table"', self.index_html)
        self.assertIn('id="prevWhtDescription"', self.index_html)
        self.assertIn('id="prevWhtRate"', self.index_html)
        self.assertIn('id="prevWhtGross"', self.index_html)
        self.assertIn('id="prevWhtTax"', self.index_html)
        self.assertIn('id="prevWhtTotalGross"', self.index_html)
        self.assertIn('id="prevWhtTotalTax"', self.index_html)

        # Baht text box & net paid box
        self.assertIn('id="prevWhtNetText"', self.index_html)
        self.assertIn('id="prevWhtNetPaid"', self.index_html)

        # Signatures
        self.assertIn('id="prevWhtSigner"', self.index_html)
        self.assertIn('ณัฐนรี วงศ์สกุลยานนท์', self.index_html)

    def test_sync_wht_preview_in_app_js(self):
        """Verify syncWhtPreview function calculates net tax words, net paid, and sets Boss Mod."""
        self.assertIn("function syncWhtPreview()", self.app_js)
        self.assertIn("prevNetTextEl.textContent = tax > 0 ? thaiBahtText(tax) : 'ศูนย์บาทถ้วน';", self.app_js)
        self.assertIn("prevNetPaidEl.textContent = gross > 0 ? `${netPaid.toLocaleString('th-TH'", self.app_js)
        self.assertIn("prevSignerEl.textContent = 'ณัฐนรี วงศ์สกุลยานนท์';", self.app_js)

    def test_cache_versioning_v152(self):
        """Verify sw.js and index.html are bumped to v152."""
        # sw.js
        self.assertIn("ghn168-cache-v152", self.sw_js)
        self.assertIn("'index.html?v=152'", self.sw_js)
        self.assertIn("'app.js?v=152'", self.sw_js)
        self.assertIn("'manifest.json?v=152'", self.sw_js)

        # index.html
        self.assertIn('href="manifest.json?v=152"', self.index_html)
        self.assertIn('src="app.js?v=152"', self.index_html)
        self.assertIn("register('sw.js?v=152')", self.index_html)
        self.assertIn("Version V1.52", self.index_html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
