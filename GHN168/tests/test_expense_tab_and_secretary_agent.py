#!/usr/bin/env python3
"""
================================================================================
Test Suite: Expense Tab 14 Canonical Rows & Elite Executive Secretary Agent
================================================================================
Target:
1. Google Sheets Tab 'รายจ่าย' (14 canonical rows, PV-202609-470 & PV-202609-471).
2. ghn168_sync_service.build_sheet_row_data:
   - Store name -> supplier name, tax_id -> supplier_tax_id, address -> supplier_address.
   - WHT 0% bug fix (does NOT bounce back to 3%).
   - Actual VAT calculation (not hardcoded 0.0).
   - Composite bill decomposition (bookkeeping fee + PP30 advance payment).
3. line_bot_server:
   - Elite Executive Secretary Persona & 4 Bosses Roles.
   - Standby & [SILENT] protocol.
================================================================================
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ghn168_sync_service import (
    EXPENSE_HEADERS,
    read_sheet_data,
    build_sheet_row_data,
    decompose_composite_expense,
    record_scanned_expense
)
from line_bot_server import (
    SYSTEM_INSTRUCTION,
    should_reply_to_event,
    _build_agent_return_dict
)


class TestExpenseTabAndSecretaryAgent(unittest.TestCase):

    def test_01_expense_tab_14_canonical_rows(self):
        """Verify tab 'รายจ่าย' has 14 rows and split rows match 10,890.00 THB."""
        res = read_sheet_data("รายจ่าย")
        self.assertEqual(res.get("status"), "success")
        rows = res.get("values", [])
        self.assertEqual(len(rows), 14, f"Expected 14 rows in 'รายจ่าย', got {len(rows)}")

        # Row 13: Green Account Monthly Bookkeeping
        row13 = rows[12]
        self.assertEqual(row13[2], "PV-202609-470")
        self.assertIn("กรีนแอคเคาน์", row13[3])
        self.assertEqual(float(row13[9]), 2000.0)    # Pre-VAT
        self.assertEqual(float(row13[10]), 140.0)    # VAT
        self.assertEqual(float(row13[11]), 2140.0)   # Gross
        self.assertEqual(float(row13[12]), 0.0)      # WHT %
        self.assertEqual(float(row13[15]), 2140.0)   # Net

        # Row 14: Revenue Department PP30 Advance Payment
        row14 = rows[13]
        self.assertEqual(row14[2], "PV-202609-471")
        self.assertIn("กรมสรรพากร", row14[3])
        self.assertEqual(float(row14[9]), 8750.0)    # Pre-VAT
        self.assertEqual(float(row14[10]), 0.0)      # VAT
        self.assertEqual(float(row14[11]), 8750.0)   # Gross
        self.assertEqual(float(row14[12]), 0.0)      # WHT %
        self.assertEqual(float(row14[15]), 8750.0)   # Net

        # Total matching transfer slip: 2,140 + 8,750 = 10,890.00 THB
        total_transfer = float(row13[15]) + float(row14[15])
        self.assertEqual(total_transfer, 10890.0)
        print("\n✅ Test 1: Expense tab 14 canonical rows verified live (10,890.00 THB match)!")

    def test_02_build_sheet_row_data_store_name_tax_id_mapping(self):
        """Verify build_sheet_row_data maps store_name, tax_id, address correctly."""
        doc_data = {
            "store_name": "ร้านอุปกรณ์ถ่ายทำ เชียงใหม่",
            "tax_id": "0505560009999",
            "address": "ถ.สุเทพ อ.เมือง จ.เชียงใหม่",
            "branch": "00001",
            "category": "ค่าเช่าอุปกรณ์",
            "gross_amount": 5350.0,
            "pre_vat": 5000.0,
            "vat_amount": 350.0,
            "wht_rate": 0.0
        }
        sheet_name, row = build_sheet_row_data("expense", doc_data)
        self.assertEqual(sheet_name, "รายจ่าย")
        self.assertEqual(row[3], "ร้านอุปกรณ์ถ่ายทำ เชียงใหม่")
        self.assertEqual(row[4], "'0505560009999")
        self.assertEqual(row[5], "ถ.สุเทพ อ.เมือง จ.เชียงใหม่")
        self.assertEqual(row[6], "'00001")
        self.assertEqual(row[9], 5000.0)   # Pre-VAT
        self.assertEqual(row[10], 350.0)   # VAT
        self.assertEqual(row[11], 5350.0)  # Gross
        self.assertEqual(row[12], 0.0)     # WHT Rate %
        self.assertEqual(row[13], 0.0)     # WHT Amount
        self.assertEqual(row[15], 5350.0)  # Net Paid
        print("✅ Test 2: Field mapping and VAT calculation verified!")

    def test_03_wht_rate_zero_not_defaulted_to_three(self):
        """Verify wht_rate == 0 does NOT bounce back to 3%."""
        doc_data = {
            "supplier_name": "หจก. กรีนแอคเคาน์",
            "gross_amount": 2140.0,
            "vat_amount": 140.0,
            "pre_vat": 2000.0,
            "wht_rate": 0
        }
        sheet_name, row = build_sheet_row_data("expense", doc_data)
        self.assertEqual(row[12], 0.0)
        self.assertEqual(row[13], 0.0)
        self.assertEqual(row[15], 2140.0)
        print("✅ Test 3: WHT 0% bug fix verified (does NOT bounce to 3%)!")

    def test_04_composite_bill_decomposition(self):
        """Verify decompose_composite_expense breaks down service fee + PP30 advance."""
        composite_data = {
            "doc_no": "PV-202609-470",
            "store_name": "ห้างหุ้นส่วนจำกัด กรีนแอคเคาน์",
            "service_amount": 2000.0,
            "advance_amount": 8750.0,
            "remarks": "เงินทดรองจ่ายภาษี ภ.พ.30 ไม่คิด VAT ซ้ำซ้อน"
        }
        sub_records = decompose_composite_expense(composite_data)
        self.assertEqual(len(sub_records), 2)
        
        # Sub 1: Service fee
        self.assertEqual(sub_records[0]["doc_no"], "PV-202609-470")
        self.assertEqual(sub_records[0]["category"], "ค่าบริการทำบัญชี")
        self.assertEqual(sub_records[0]["pre_vat"], 2000.0)
        self.assertTrue(sub_records[0]["is_vat"])

        # Sub 2: PP30 advance
        self.assertEqual(sub_records[1]["doc_no"], "PV-202609-471")
        self.assertEqual(sub_records[1]["category"], "ภาษีมูลค่าเพิ่มนำส่งสรรพากร (ภ.พ.30)")
        self.assertEqual(sub_records[1]["pre_vat"], 8750.0)
        self.assertFalse(sub_records[1]["is_vat"])
        self.assertEqual(sub_records[1]["gross_amount"], 8750.0)
        print("✅ Test 4: Composite bill decomposition verified!")

    def test_05_elite_secretary_persona_and_silent_protocol(self):
        """Verify Elite Executive Secretary persona and [SILENT] return dict."""
        # 1. Persona checks
        self.assertIn("Elite Executive Secretary", SYSTEM_INSTRUCTION)
        self.assertIn("เลขาราคาแพง", SYSTEM_INSTRUCTION)
        self.assertIn("ยืน standby ในห้อง 4 บอส", SYSTEM_INSTRUCTION)
        self.assertIn("บอสเก่ง", SYSTEM_INSTRUCTION)
        self.assertIn("บอสหอม", SYSTEM_INSTRUCTION)
        self.assertIn("บอสมด", SYSTEM_INSTRUCTION)
        self.assertIn("บอสนิค", SYSTEM_INSTRUCTION)
        self.assertIn("[SILENT]", SYSTEM_INSTRUCTION)
        self.assertIn("ผู้อนุมัติโอนเงิน", SYSTEM_INSTRUCTION)
        self.assertIn("ตั้งเบิกค่าใช้จ่าย", SYSTEM_INSTRUCTION)

        # 2. _build_agent_return_dict [SILENT] behavior
        silent_res = _build_agent_return_dict("[SILENT]", [], [])
        self.assertTrue(silent_res.get("is_silent"))
        self.assertEqual(silent_res.get("reply_text"), "[SILENT]")
        self.assertEqual(silent_res.get("flex_cards"), [])
        print("✅ Test 5: Elite Executive Secretary Persona & [SILENT] verified!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
