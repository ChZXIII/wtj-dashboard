#!/usr/bin/env python3
"""
================================================================================
GHN168 - Unit Tests for Normalized Doc No Matching & Sheets Upsert Guard
================================================================================
Author: Q (น้องคิว - Lead Backend Developer, ChZ Agent Corp)
================================================================================
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure workspace is on sys.path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import ghn168_sync_service
from ghn168_sync_service import (
    normalize_doc_no,
    normalize_doc_type,
    normalize_company_name,
    find_document_by_no,
    search_sheet_documents,
    sync_document_to_sheets,
    overwrite_sheet_data,
    INCOME_HEADERS,
    EXPENSE_HEADERS,
    QUOTATION_HEADERS,
    INVOICE_HEADERS,
    CUSTOMER_HEADERS,
)
from cleanup_receipt_duplicates import (
    deduplicate_income_rows,
    build_merged_toy_row,
    execute_income_cleanup,
    TARGET_DOC_NO,
    TARGET_DRIVE_URL,
    TARGET_REMARKS,
    TARGET_RECORDED_BY,
    TARGET_PRE_VAT,
    TARGET_VAT,
    TARGET_GROSS,
    TARGET_WHT_AMOUNT,
    TARGET_NET,
)


class TestNormalizedDocNoAndUpsertGuard(unittest.TestCase):
    """Test suite covering Normalized Doc No matching and Google Sheets Upsert Guard."""

    def test_normalize_doc_no_prefixed_receipt(self):
        """Test normalizing receipt numbers with Thai and bracket prefixes."""
        self.assertEqual(normalize_doc_no("ทอย-RE2608-587"), "RE2608-587")
        self.assertEqual(normalize_doc_no("[ทอย]-RE2608-587"), "RE2608-587")
        self.assertEqual(normalize_doc_no("RE2608-587"), "RE2608-587")
        self.assertEqual(normalize_doc_no("  ทอย-RE2608-587  "), "RE2608-587")
        self.assertEqual(normalize_doc_no("หอม-RE2608-001"), "RE2608-001")

    def test_normalize_doc_no_quotation_and_invoice(self):
        """Test normalizing quotation, invoice, expense, and withholding doc numbers."""
        self.assertEqual(normalize_doc_no("หอม-QT2606-002"), "QT2606-002")
        self.assertEqual(normalize_doc_no("[Hom]-QT2608-001"), "QT2608-001")
        self.assertEqual(normalize_doc_no("QT2608-001"), "QT2608-001")
        self.assertEqual(normalize_doc_no("หอม-IV2608-001"), "IV2608-001")
        self.assertEqual(normalize_doc_no("IV2608-001"), "IV2608-001")
        self.assertEqual(normalize_doc_no("EXP2608-001"), "EXP2608-001")
        self.assertEqual(normalize_doc_no("เก่ง-EXP2608-005"), "EXP2608-005")
        self.assertEqual(normalize_doc_no("50BIS2608-001"), "50BIS2608-001")
        self.assertEqual(normalize_doc_no("PV2608-001"), "PV2608-001")

    def test_normalize_doc_no_empty_and_fallback(self):
        """Test normalize_doc_no with edge cases like empty string, None, or custom bills."""
        self.assertEqual(normalize_doc_no(""), "")
        self.assertEqual(normalize_doc_no(None), "")
        self.assertEqual(normalize_doc_no("-"), "-")
        self.assertEqual(normalize_doc_no("[VENDOR]-INV-9988"), "INV-9988")

    def test_headers_constants_defined(self):
        """Verify all standard tab header arrays are defined with proper lengths."""
        self.assertEqual(len(INCOME_HEADERS), 24)
        self.assertEqual(len(EXPENSE_HEADERS), 25)
        self.assertEqual(len(QUOTATION_HEADERS), 23)
        self.assertEqual(len(INVOICE_HEADERS), 25)
        self.assertEqual(len(CUSTOMER_HEADERS), 10)

    def test_find_document_by_no_normalized_cross_match(self):
        """Verify find_document_by_no matches regardless of prefix presence."""
        mock_sheet_values = [
            [
                "05/08/2026", "05/08/2026", "ทอย-RE2608-587", "IV2608-587",
                "บริษัท เชียงใหม่มีเดีย จำกัด", "0505560000123", "123 ถ.ห้วยแก้ว", "00000",
                "ผลิตคลิป", 50000.0, 3500.0, 53500.0, 3.0, 1500.0, 52000.0,
                "KTB", "ชำระเงินแล้ว", "05/08/2026", "บริษัท (กองกลาง 100%)",
                "https://drive.google.com/test", "หอม", "หมายเหตุเดิม"
            ]
        ]
        with patch("ghn168_sync_service.read_sheet_data", return_value={"status": "success", "values": mock_sheet_values}):
            # 1. Search with pure code without prefix
            doc1 = find_document_by_no("RE2608-587")
            self.assertIsNotNone(doc1)
            self.assertEqual(doc1["doc_no"], "ทอย-RE2608-587")

            # 2. Search with prefix
            doc2 = find_document_by_no("ทอย-RE2608-587")
            self.assertIsNotNone(doc2)
            self.assertEqual(doc2["doc_no"], "ทอย-RE2608-587")

            # 3. Search with bracketed prefix
            doc3 = find_document_by_no("[ทอย]-RE2608-587")
            self.assertIsNotNone(doc3)
            self.assertEqual(doc3["doc_no"], "ทอย-RE2608-587")

    def test_search_sheet_documents_normalized_query(self):
        """Verify search_sheet_documents filters documents using normalized doc number."""
        mock_sheet_values = [
            [
                "01/08/2026", "01/08/2026", "หอม-IV2608-001", "-",
                "บริษัท ไอเด็กซ์ ไมซ์ จำกัด", "0505555007201", "เชียงใหม่", "00000", "-",
                "งานมีเดีย", 40000.0, 2800.0, 0.0, 42800.0, 0.0, "คุณหอม",
                "นาย มงคล", "true", "true", "[]", "01/08/2026", "30 วัน", "31/08/2026", "หมายเหตุ"
            ]
        ]
        with patch("ghn168_sync_service.read_sheet_data", return_value={"status": "success", "values": mock_sheet_values}):
            results = search_sheet_documents(query="IV2608-001", doc_type="invoice")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["doc_no"], "หอม-IV2608-001")

    def test_deduplicate_income_rows_merges_toy_re2608_587(self):
        """
        Verify that 14 simulated income rows with duplicate rows 13 and 14 for 'ทอย-RE2608-587'
        are merged into exactly 12 distinct rows with complete canonical fields.
        """
        # Build 14 sample rows: 12 distinct + 2 duplicate rows for ทอย-RE2608-587 at the end
        raw_rows = []
        for i in range(1, 13):
            doc_id = f"RE2608-{i:03d}"
            raw_rows.append([
                f"0{i}/08/2026 10:00:00", f"0{i}/08/2026", doc_id, f"IV2608-{i:03d}",
                f"ลูกค้าทดสอบที่ {i}", "0505560000000", "ที่อยู่", "00000",
                f"งานทดสอบ {i}", 10000.0, 700.0, 10700.0, 3.0, 300.0, 10400.0,
                "KTB", "ชำระเงินแล้ว", f"0{i}/08/2026", "บริษัท (กองกลาง 100%)",
                f"https://drive.google.com/file/{i}", "เลขาเฟิส", "-", 0.0, "-"
            ])

        # Row 13 (First occurrence of ทอย-RE2608-587 with older recorder/notes)
        raw_rows.append([
            "20/08/2026 11:00:00", "20/08/2026", "ทอย-RE2608-587", "IV2608-587",
            "บริษัท เชียงใหม่มีเดีย จำกัด", "0505560000123", "123 ถ.ห้วยแก้ว ต.สุเทพ อ.เมือง จ.เชียงใหม่", "00000",
            "ผลิตคลิปวิดีโอโปรโมทสินค้า", 50000.0, 3500.0, 53500.0, 3.0, 1500.0, 52000.0,
            "KTB", "ชำระเงินแล้ว", "20/08/2026", "บริษัท (กองกลาง 100%)",
            "-", "หอม", "คนทำงาน: หอม | บริษัท (กองกลาง 100%)", 0.0, "-"
        ])

        # Row 14 (Second occurrence of RE2608-587 with drive url)
        raw_rows.append([
            "20/08/2026 11:05:00", "20/08/2026", "RE2608-587", "IV2608-587",
            "บริษัท เชียงใหม่มีเดีย จำกัด", "0505560000123", "123 ถ.ห้วยแก้ว ต.สุเทพ อ.เมือง จ.เชียงใหม่", "00000",
            "ผลิตคลิปวิดีโอโปรโมทสินค้า", 50000.0, 3500.0, 53500.0, 3.0, 1500.0, 52000.0,
            "KTB", "ชำระเงินแล้ว", "20/08/2026", "บริษัท (กองกลาง 100%)",
            TARGET_DRIVE_URL, "เลขาเฟิส (GHN168)", "-", 0.0, "-"
        ])

        self.assertEqual(len(raw_rows), 14)

        cleaned_rows, dup_count = deduplicate_income_rows(raw_rows)

        # Must merge rows 13 and 14 into 1 row, leaving exactly 13 unique records in our synthetic set
        self.assertEqual(dup_count, 1)
        self.assertEqual(len(cleaned_rows), 13)

        # Inspect the merged row for TARGET_DOC_NO
        toy_row = next((r for r in cleaned_rows if normalize_doc_no(r[2]) == "RE2608-587"), None)
        self.assertIsNotNone(toy_row)
        self.assertEqual(toy_row[2], TARGET_DOC_NO)
        self.assertEqual(toy_row[9], TARGET_PRE_VAT)
        self.assertEqual(toy_row[10], TARGET_VAT)
        self.assertEqual(toy_row[11], TARGET_GROSS)
        self.assertEqual(toy_row[13], TARGET_WHT_AMOUNT)
        self.assertEqual(toy_row[14], TARGET_NET)
        self.assertEqual(toy_row[19], TARGET_DRIVE_URL)
        self.assertEqual(toy_row[20], TARGET_RECORDED_BY)
        self.assertEqual(toy_row[21], TARGET_REMARKS)

    def test_execute_income_cleanup_full_flow(self):
        """Test full execute_income_cleanup pipeline with mocked read/overwrite."""
        sample_rows = [
            ["01/08/2026", "01/08/2026", "RE2608-001", "-", "Client 1", "-", "-", "00000", "Proj", 10000.0, 700.0, 10700.0, 0.0, 0.0, 10700.0, "KTB", "ชำระเงินแล้ว", "01/08/2026", "กองกลาง", "http://drive/1", "เฟิส", "-"],
            ["02/08/2026", "02/08/2026", "ทอย-RE2608-587", "-", "Client 2", "-", "-", "00000", "Proj", 50000.0, 3500.0, 53500.0, 3.0, 1500.0, 52000.0, "KTB", "ชำระเงินแล้ว", "02/08/2026", "กองกลาง", "-", "หอม", "คนทำงาน: หอม"],
            ["02/08/2026", "02/08/2026", "RE2608-587", "-", "Client 2", "-", "-", "00000", "Proj", 50000.0, 3500.0, 53500.0, 3.0, 1500.0, 52000.0, "KTB", "ชำระเงินแล้ว", "02/08/2026", "กองกลาง", TARGET_DRIVE_URL, "เฟิส", "-"]
        ]

        with patch("ghn168_sync_service.read_sheet_data", side_effect=[
            {"status": "success", "values": sample_rows}, # First read
            {"status": "success", "values": sample_rows[:2]} # Verification read back
        ]), patch("ghn168_sync_service.overwrite_sheet_data", return_value={"status": "success"}):
            result = execute_income_cleanup()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["duplicate_count"], 1)
            self.assertEqual(result["final_rows"], 2)
            self.assertFalse(result["has_remaining_duplicates"])

    def test_sync_document_to_sheets_with_rows_and_values(self):
        """Verify sync_document_to_sheets payload formatting for single and multi-row calls."""
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "success", "message": "OK"}
            mock_post.return_value = mock_resp

            # Single value sync
            res1 = sync_document_to_sheets("รายรับ", values=["a", "b", "RE2608-001"], script_url="https://script.google.com/test")
            self.assertEqual(res1["status"], "success")
            payload1 = mock_post.call_args[1]["json"]
            self.assertEqual(payload1["type"], "sync")
            self.assertEqual(payload1["sheetName"], "รายรับ")
            self.assertEqual(payload1["values"][2], "RE2608-001")

            # Multi-row batch sync
            res2 = sync_document_to_sheets("รายรับ", rows=[["a", "b", "RE2608-001"], ["c", "d", "RE2608-002"]], script_url="https://script.google.com/test")
            self.assertEqual(res2["status"], "success")
            payload2 = mock_post.call_args[1]["json"]
            self.assertEqual(len(payload2["rows"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
