#!/usr/bin/env python3
"""
================================================================================
GHN168 - Unit Tests for Tax ID, Branch Code Formatting, Deduplication & Dual-Engine
================================================================================
Author: Q (Lead Backend Developer, ChZ Agent Corp)
"""

import unittest
from datetime import datetime

from ghn168_sync_service import (
    format_google_sheets_text,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    build_sheet_row_data,
    save_new_customer
)
from repair_sheet_tax_ids_and_duplicates import (
    format_tax_id as repair_format_tax_id,
    format_branch as repair_format_branch
)


class TestTaxIdAndBranchFormatting(unittest.TestCase):
    """Test suite for 13-digit Tax ID and 5-digit Branch formatting standards."""

    def test_tax_id_12_digits_pads_to_13_digits(self):
        # 12-digit Tax ID (e.g. Idex Mice previously missing leading 0: 505555007201)
        tax_12 = "505555007201"
        res = format_tax_id_for_sheet(tax_12)
        self.assertEqual(res, "'0505555007201")
        self.assertEqual(len(res.lstrip("'")), 13)

        repair_res = repair_format_tax_id(tax_12)
        self.assertEqual(repair_res, "'0505555007201")

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


class TestCustomerSaveFormatting(unittest.TestCase):
    """Test customer auto-save formatting."""

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


if __name__ == "__main__":
    unittest.main()
