#!/usr/bin/env python3
"""
================================================================================
GHN168 - Unit Tests for Receipt RE2608-001 Sync to Google Sheets
================================================================================
Author: Q (น้องคิว - Lead Backend Developer, ChZ Agent Corp)
================================================================================
"""

import unittest
from unittest.mock import patch, MagicMock

from sync_receipt_re2608_001 import (
    RECEIPT_RE2608_001_DATA,
    build_receipt_row,
    sync_receipt_re2608_001,
)


class TestSyncReceiptRE2608_001(unittest.TestCase):
    """Test suite for Receipt RE2608-001 row builder and sync functionality."""

    def setUp(self):
        self.doc_data = dict(RECEIPT_RE2608_001_DATA)
        self.fixed_record_date = "25/08/2026 20:30:00"

    def test_row_builder_column_count_is_24(self):
        """Verify that the generated row contains exactly 24 columns."""
        row = build_receipt_row(self.doc_data, record_date=self.fixed_record_date)
        self.assertEqual(len(row), 24, f"Expected 24 columns, got {len(row)}")

    def test_tax_id_and_branch_formatting(self):
        """Verify Tax ID is 13 digits and Branch is 5 digits with leading single quote."""
        row = build_receipt_row(self.doc_data, record_date=self.fixed_record_date)
        tax_id = row[5]
        branch = row[7]

        # Check single quote prefix for Google Sheets text formatting
        self.assertTrue(tax_id.startswith("'"), f"Tax ID must start with single quote, got {tax_id}")
        self.assertTrue(branch.startswith("'"), f"Branch must start with single quote, got {branch}")

        # Check digits
        self.assertEqual(tax_id, "'0505555007201")
        self.assertEqual(len(tax_id.lstrip("'")), 13)

        self.assertEqual(branch, "'00000")
        self.assertEqual(len(branch.lstrip("'")), 5)

    def test_all_24_columns_values_match_spec(self):
        """Verify each of the 24 columns against user specification."""
        row = build_receipt_row(self.doc_data, record_date=self.fixed_record_date)

        expected_row = [
            "25/08/2026 20:30:00",                                                                          # 0: record_date
            "04/08/2026",                                                                                   # 1: doc_date
            "RE2608-001",                                                                                   # 2: doc_no
            "-",                                                                                            # 3: ref_invoice_no
            "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",                                                                   # 4: client_name
            "'0505555007201",                                                                               # 5: client_tax_id
            "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",                     # 6: client_address
            "'00000",                                                                                       # 7: client_branch
            "Tasty singapore (ถ่ายทำวิดีโอ 3 คิว, ตัดต่อ 1 คลิป, เช่า GoPro 2 คิว, ชุดไฟ+ไมค์ไวเลส)",       # 8: project_name
            41000.0,                                                                                        # 9: pre_vat
            2870.0,                                                                                         # 10: vat_amount
            43870.0,                                                                                        # 11: gross_amount
            3.0,                                                                                            # 12: wht_rate
            1230.0,                                                                                         # 13: wht_amount
            42640.0,                                                                                        # 14: net_total
            "KTB",                                                                                          # 15: receiving_bank
            "ชำระเงินแล้ว",                                                                                 # 16: payment_status
            "04/08/2026",                                                                                   # 17: actual_payment_date
            "บริษัท (กองกลาง 100%)",                                                                        # 18: profit_share
            "https://drive.google.com/file/d/ghn168_receipt_re2608_001_idex/view",                          # 19: pdf_url
            "เลขาเฟิส (GHN168)",                                                                            # 20: recorded_by
            "-",                                                                                            # 21: remarks
            0.0,                                                                                            # 22: discount
            "-"                                                                                             # 23: discount_desc
        ]

        self.assertEqual(row, expected_row)

    def test_financial_calculations(self):
        """Verify mathematical integrity of the financial calculations."""
        pre_vat = self.doc_data["pre_vat"]
        vat = self.doc_data["vat_amount"]
        gross = self.doc_data["gross_amount"]
        wht_rate = self.doc_data["wht_rate"]
        wht_amt = self.doc_data["wht_amount"]
        net = self.doc_data["net_total"]

        # VAT 7% check
        expected_vat = round(pre_vat * 0.07, 2)
        self.assertEqual(vat, expected_vat)

        # Gross amount check
        expected_gross = round(pre_vat + vat, 2)
        self.assertEqual(gross, expected_gross)

        # WHT 3% check
        expected_wht = round(pre_vat * (wht_rate / 100.0), 2)
        self.assertEqual(wht_amt, expected_wht)

        # Net total check
        expected_net = round(gross - wht_amt, 2)
        self.assertEqual(net, expected_net)

    @patch("sync_receipt_re2608_001.sync_document_to_sheets")
    def test_sync_receipt_function_calls_sheets_service(self, mock_sync):
        """Verify sync_receipt_re2608_001 correctly calls sync_document_to_sheets with 'รายรับ'."""
        mock_sync.return_value = {"status": "success", "message": "Record synced successfully"}

        res = sync_receipt_re2608_001()

        self.assertIn("row_data", res)
        self.assertIn("sync_result", res)
        self.assertEqual(res["sync_result"]["status"], "success")

        # Verify arguments passed to sync_document_to_sheets
        mock_sync.assert_called_once()
        args, kwargs = mock_sync.call_args
        self.assertEqual(args[0], "รายรับ")
        self.assertIn("values", kwargs)
        self.assertEqual(len(kwargs["values"]), 24)
        self.assertEqual(kwargs["values"][2], "RE2608-001")


if __name__ == "__main__":
    unittest.main()
