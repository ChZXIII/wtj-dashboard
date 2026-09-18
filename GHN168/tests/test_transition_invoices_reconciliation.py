"""
Tests for Reconciling and Clearing 6 Overdue Transition Invoices in Google Sheets.
Verifies:
1. get_overdue_and_aging_invoices returns total_overdue_invoices = 0 and total_overdue_amount = 0.00 ฿
2. 'ใบวางบิล' tab marks the transition invoices as 'ชำระแล้ว'
3. 'รายรับ' tab links ref_invoice_no to matching invoices
"""

import unittest
from unittest.mock import patch
from ghn168_sync_service import (
    get_overdue_and_aging_invoices,
    read_sheet_data,
    normalize_doc_no,
)


class TestTransitionInvoicesReconciliation(unittest.TestCase):
    def test_overdue_invoices_zero_cleared(self):
        """Verify that get_overdue_and_aging_invoices returns 0 overdue invoices and 0.00 amount."""
        res = get_overdue_and_aging_invoices()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res.get("total_overdue_invoices"), 0)
        self.assertEqual(res.get("total_overdue_count"), 0)
        self.assertEqual(res.get("total_overdue_amount"), 0.0)
        self.assertEqual(len(res.get("all_overdue_list", [])), 0)

    def test_reconciled_transition_invoices_in_billing_tab(self):
        """Verify that the 6 transition invoices in 'ใบวางบิล' indicate 'ชำระแล้ว' in remarks."""
        billing_res = read_sheet_data("ใบวางบิล")
        rows = billing_res.get("values", [])
        
        target_invoices = [
            "IV2608-001",
            "IV2607-002",
            "IV2607-002-LANNA",
            "IV2608-001-NORTH",
            "IV2608-003",
            "IV2608-004",
        ]
        
        found_docs = {}
        for r in rows:
            if len(r) > 2:
                doc_no = str(r[2]).strip()
                remarks = str(r[22]).strip() if len(r) > 22 else ""
                for target in target_invoices:
                    if doc_no == target or normalize_doc_no(doc_no) == normalize_doc_no(target):
                        found_docs[target] = remarks
        
        for target in target_invoices:
            self.assertIn(target, found_docs, f"Missing invoice {target} in 'ใบวางบิล'")
            self.assertIn("ชำระแล้ว", found_docs[target], f"Invoice {target} remarks not marked as 'ชำระแล้ว'")

    def test_receipt_tab_ref_invoice_cross_references(self):
        """Verify that 'รายรับ' tab links receipt rows to matching invoices."""
        receipt_res = read_sheet_data("รายรับ")
        rows = receipt_res.get("values", [])

        # Check ref links
        refs_present = set()
        for r in rows:
            if len(r) > 3 and r[3]:
                refs_present.add(str(r[3]).strip())

        self.assertIn("IV2607-002", refs_present)
        self.assertIn("IV2608-003", refs_present)
