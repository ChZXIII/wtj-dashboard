#!/usr/bin/env python3
"""
================================================================================
GHN168 - Unit Tests for Tax ID, Branch Code Formatting, Deduplication & Dual-Engine
================================================================================
Author: Q (Lead Backend Developer, ChZ Agent Corp)
"""

import os
import sys
import unittest
from datetime import datetime

# Ensure workspace is on sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from ghn168_sync_service import (
    format_google_sheets_text,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    build_sheet_row_data,
    save_new_customer
)


class TestTaxIdAndBranchFormatting(unittest.TestCase):
    """Test suite for 13-digit Tax ID and 5-digit Branch formatting standards."""

    def test_tax_id_12_digits_pads_to_13_digits(self):
        # 12-digit Tax ID (e.g. Idex Mice previously missing leading 0: 505555007201)
        tax_12 = "505555007201"
        res = format_tax_id_for_sheet(tax_12)
        self.assertEqual(res, "'0505555007201")
        self.assertEqual(len(res.lstrip("'")), 13)

    def test_tax_id_13_digits_preserves_and_prefixes_quote(self):
        # Normal 13-digit Thai Tax ID
        tax_13 = "0505566010089"
        res = format_tax_id_for_sheet(tax_13)
        self.assertEqual(res, "'0505566010089")

        # Tax ID with hyphen
        tax_hyphen = "0-5055-66010-08-9"
        res_hyphen = format_tax_id_for_sheet(tax_hyphen)
        self.assertEqual(res_hyphen, "'0505566010089")

    def test_tax_id_empty_or_dash(self):
        self.assertEqual(format_tax_id_for_sheet(""), "-")
        self.assertEqual(format_tax_id_for_sheet("-"), "-")
        self.assertEqual(format_tax_id_for_sheet(None), "-")

    def test_branch_code_zero_padding_5_digits(self):
        # Branch '0' or '00000'
        self.assertEqual(format_branch_for_sheet("0"), "'00000")
        self.assertEqual(format_branch_for_sheet("00000"), "'00000")
        self.assertEqual(format_branch_for_sheet("1"), "'00001")
        self.assertEqual(format_branch_for_sheet("12"), "'00012")
        self.assertEqual(format_branch_for_sheet(""), "'00000")
        self.assertEqual(format_branch_for_sheet(None), "'00000")

    def test_google_sheets_text_prefix(self):
        self.assertEqual(format_google_sheets_text("081-111-1111"), "'081-111-1111")
        self.assertEqual(format_google_sheets_text("'081-111-1111"), "'081-111-1111")
        self.assertEqual(format_google_sheets_text(""), "-")


class TestBuildSheetRowData(unittest.TestCase):
    """Test suite for row building in all document types."""

    def test_quotation_row_formatting(self):
        doc_data = {
            "doc_no": "QT2608-099",
            "doc_date": "25/08/2026",
            "client_name": "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
            "client_tax_id": "505555007201",  # 12 digits input
            "client_branch": "0",             # single 0 input
            "client_phone": "053-888999",
            "project_name": "งานผลิตสื่อวิดีโอ",
            "amount": 35000.0,
            "is_vat": True,
            "wht_rate": 3.0
        }
        sheet_name, row = build_sheet_row_data("quotation", doc_data)
        self.assertEqual(sheet_name, "ใบเสนอราคา")
        self.assertEqual(row[4], "'0505555007201")  # Tax ID formatted to 13 digits with '
        self.assertEqual(row[6], "'00000")          # Branch formatted to 5 digits with '
        self.assertEqual(row[7], "'053-888999")     # Phone formatted with '

    def test_invoice_row_formatting(self):
        doc_data = {
            "doc_no": "IV2608-099",
            "doc_date": "25/08/2026",
            "client_name": "บริษัท พิงค์นคร พร็อพเพอร์ตี้ จำกัด",
            "client_tax_id": "0505560000789",
            "client_branch": "00000",
            "client_phone": "083-3333333",
            "project_name": "งาน Virtual Tour",
            "amount": 50000.0
        }
        sheet_name, row = build_sheet_row_data("invoice", doc_data)
        self.assertEqual(sheet_name, "ใบวางบิล")
        self.assertEqual(row[4], "'0505560000789")
        self.assertEqual(row[6], "'00000")
        self.assertEqual(row[7], "'083-3333333")

    def test_receipt_row_formatting(self):
        doc_data = {
            "doc_no": "RE2608-099",
            "doc_date": "25/08/2026",
            "invoice_no": "IV2608-099",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "client_tax_id": "505560000123",  # 12 digits
            "client_branch": "0",
            "project_name": "งานถ่ายคลิป",
            "amount": 40000.0
        }
        sheet_name, row = build_sheet_row_data("receipt", doc_data)
        self.assertEqual(sheet_name, "รายรับ")
        self.assertEqual(row[5], "'0505560000123")  # Tax ID at Col 5
        self.assertEqual(row[7], "'00000")          # Branch at Col 7

    def test_expense_wht_row_formatting(self):
        doc_data = {
            "doc_no": "PV2608-099",
            "doc_date": "25/08/2026",
            "payee_name": "นาย ช่างภาพ อิสระ",
            "payee_tax_id": "1509900112233",  # 13 digits
            "payee_branch": "0",
            "category": "ค่าจ้างตากล้อง",
            "amount": 5000.0,
            "wht_rate": 3.0
        }
        sheet_name, row = build_sheet_row_data("wht", doc_data)
        self.assertEqual(sheet_name, "รายจ่าย")
        self.assertEqual(row[4], "'1509900112233")  # Payee Tax ID
        self.assertEqual(row[6], "'00000")          # Payee Branch


from unittest.mock import MagicMock, patch


class TestCustomerSaveFormatting(unittest.TestCase):
    """Test customer auto-save formatting."""

    def setUp(self):
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
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}

            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_save_new_customer_tax_and_branch(self):
        new_cust = {
            "customer_name": "บริษัท ทดสอบ ซิงค์ จำกัด",
            "tax_id": "505577889901",  # 12 digits
            "branch": "0",
            "address": "เชียงใหม่",
            "phone": "089-999-9999"
        }
        res = save_new_customer(new_cust)
        self.assertEqual(res["status"], "success")
        self.assertIn("customer", res)
        self.assertEqual(res["customer"]["customer_id"], "CUST-011")
        self.assertEqual(res["customer"]["tax_id"], "0505577889901")
        self.assertEqual(res["customer"]["branch"], "00000")


class TestSmartCorporateWHT(unittest.TestCase):
    """Test suite for Smart Corporate WHT determination and decimal normalization."""

    def test_smart_wht_corporate_defaults(self):
        from line_bot_server import determine_smart_wht_rate, is_corporate_customer
        
        # 1. Corporate Customer -> 3% WHT for services
        self.assertTrue(is_corporate_customer("บริษัท เชียงใหม่มีเดีย จำกัด"))
        self.assertTrue(is_corporate_customer("หจก. ลานนา โปรดักชั่น"))
        self.assertTrue(is_corporate_customer("บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด"))
        self.assertFalse(is_corporate_customer("คุณสมชาย ใจดี"))

        rate_corp = determine_smart_wht_rate(
            client_name="บริษัท เชียงใหม่มีเดีย จำกัด",
            project_name="ถ่ายทำวิดีโอโฆษณา"
        )
        self.assertEqual(rate_corp, 3.0)

        # 2. Rental Equipment / Studio -> 5% WHT
        rate_rent = determine_smart_wht_rate(
            client_name="บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด",
            project_name="เช่าอุปกรณ์กล้องและไฟสตูดิโอ"
        )
        self.assertEqual(rate_rent, 5.0)

        # 3. Transport / Logistics -> 1% WHT
        rate_trans = determine_smart_wht_rate(
            client_name="บริษัท แคทไซคลิ่ง จำกัด",
            project_name="ค่าขนส่งและโลจิสติกส์กองถ่าย"
        )
        self.assertEqual(rate_trans, 1.0)

        # 4. Individual Customer with no WHT -> 0%
        rate_indiv = determine_smart_wht_rate(
            client_name="คุณสมชาย ใจดี",
            project_name="ถ่ายภาพโปรไฟล์"
        )
        self.assertEqual(rate_indiv, 0.0)

        # 5. Decimal rate normalization in determine_smart_wht_rate
        self.assertEqual(determine_smart_wht_rate(explicit_wht_rate=0.03), 3.0)
        self.assertEqual(determine_smart_wht_rate(explicit_wht_rate=0.01), 1.0)
        self.assertEqual(determine_smart_wht_rate(explicit_wht_rate=0.05), 5.0)
        self.assertEqual(determine_smart_wht_rate(explicit_wht_rate=3.0), 3.0)

        # 6. Explicit override "ไม่หัก"
        self.assertEqual(determine_smart_wht_rate(client_name="บริษัท เชียงใหม่มีเดีย จำกัด", raw_text="ไม่หัก wht"), 0.0)


class TestSanitizeRowForSheetAndBatchFix(unittest.TestCase):
    """Test suite for pre-flight row sanitization and batch tax ID recovery."""

    def test_sanitize_row_for_all_tabs(self):
        from ghn168_sync_service import sanitize_row_for_sheet

        # 1. ใบเสนอราคา (Tax ID at idx 4, Branch at idx 6)
        qt_row = ["2026-08-31", "31/08/2026", "QT2608-001", "บจก. เทส", "505555007201", "เชียงใหม่", "0", "081-1111111"]
        clean_qt = sanitize_row_for_sheet("ใบเสนอราคา", qt_row)
        self.assertEqual(clean_qt[4], "'0505555007201")
        self.assertEqual(clean_qt[6], "'00000")

        # 2. ใบวางบิล (Tax ID at idx 4, Branch at idx 6)
        iv_row = ["2026-08-31", "31/08/2026", "IV2608-001", "บจก. เทส", "505561010315", "เชียงใหม่", "0", "081-1111111"]
        clean_iv = sanitize_row_for_sheet("ใบวางบิล", iv_row)
        self.assertEqual(clean_iv[4], "'0505561010315")
        self.assertEqual(clean_iv[6], "'00000")

        # 3. รายรับ (Tax ID at idx 5, Branch at idx 7)
        re_row = ["2026-08-31", "31/08/2026", "RE2608-001", "IV2608-001", "บจก. เทส", "505545004373", "เชียงใหม่", "0"]
        clean_re = sanitize_row_for_sheet("รายรับ", re_row)
        self.assertEqual(clean_re[5], "'0505545004373")
        self.assertEqual(clean_re[7], "'00000")

        # 4. รายจ่าย (Tax ID at idx 4, Branch at idx 6)
        exp_row = ["2026-08-31", "31/08/2026", "PV2608-001", "บจก. เทส", "505568016475", "เชียงใหม่", "0"]
        clean_exp = sanitize_row_for_sheet("รายจ่าย", exp_row)
        self.assertEqual(clean_exp[4], "'0505568016475")
        self.assertEqual(clean_exp[6], "'00000")

        # 5. ข้อมูลลูกค้า (Tax ID at idx 2, Branch at idx 3)
        cust_row = ["CUST-001", "บจก. เทส", "505560000888", "0", "เชียงใหม่", "081-1111111"]
        clean_cust = sanitize_row_for_sheet("ข้อมูลลูกค้า", cust_row)
        self.assertEqual(clean_cust[2], "'0505560000888")
        self.assertEqual(clean_cust[3], "'00000")

    def test_canonical_12_digit_tax_ids_from_spec(self):
        # Specific 12-digit tax IDs mentioned in user request
        tax_ids_12 = [
            "505555007201",
            "505561010315",
            "505545004373",
            "505568016475",
            "505560000888",
            "505566001234"
        ]
        for tid in tax_ids_12:
            formatted = format_tax_id_for_sheet(tid)
            self.assertTrue(formatted.startswith("'0"), f"Failed for {tid}")
            self.assertEqual(len(formatted.lstrip("'")), 13, f"Failed len for {tid}")


if __name__ == "__main__":
    unittest.main()
