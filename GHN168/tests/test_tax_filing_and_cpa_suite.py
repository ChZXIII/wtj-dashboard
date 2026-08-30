"""
================================================================================
GHN168 Tax Filing & CPA Annual Audit Package Comprehensive Test Suite
================================================================================
Author: น้องคิว (Q) - Senior Fullstack Developer (GHN168)
Coverage:
1. `get_tax_filing_report` in ghn168_sync_service.py (ภ.พ.30, ภ.ง.ด.3, ภ.ง.ด.53)
2. `get_cpa_audit_package` in ghn168_sync_service.py (P&L, 12-month breakdown, Document Archives)
3. LINE Flex Message Builders: `build_tax_filing_flex_message`, `build_cpa_audit_pack_flex_message`
4. Gemini Agent Tool Calling declarations and `execute_agent_tool`
5. Agentic Fallback Simulator with natural language tax/CPA queries
================================================================================
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict
import unittest
from unittest.mock import MagicMock, patch

# Ensure workspace root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ghn168_sync_service import (
    get_tax_filing_report,
    get_cpa_audit_package,
    get_simulated_sheet_data
)
from line_bot_server import (
    GEMINI_AGENT_TOOL_DECLARATIONS,
    execute_agent_tool,
    build_tax_filing_flex_message,
    build_cpa_audit_pack_flex_message,
    is_tax_filing_request,
    is_cpa_audit_request,
    agentic_fallback_simulate_turn,
    validate_line_flex_payload
)


class TestTaxFilingAndCPASuite(unittest.IsolatedAsyncioTestCase):
    """Rigorous Automated Test Suite for RD e-Filing and CPA Audit Closing Engine."""

    def test_get_tax_filing_report_structure_and_calc(self):
        """Test get_tax_filing_report computes ภ.พ.30, ภ.ง.ด.3, ภ.ง.ด.53 accurately."""
        res = get_tax_filing_report(month=8, year=2026)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("month"), 8)
        self.assertEqual(res.get("year"), 2026)
        self.assertEqual(res.get("period_label"), "08/2026")

        # 1. ภ.พ.30 Validation
        pnd30 = res.get("pnd30", {})
        self.assertIn("sales_pre_vat", pnd30)
        self.assertIn("vat_output", pnd30)
        self.assertIn("purchases_pre_vat", pnd30)
        self.assertIn("vat_input", pnd30)
        self.assertIn("vat_net_payable", pnd30)
        self.assertIn("vat_status", pnd30)

        self.assertGreaterEqual(pnd30["sales_pre_vat"], 0.0)
        self.assertGreaterEqual(pnd30["vat_output"], 0.0)
        self.assertGreaterEqual(pnd30["purchases_pre_vat"], 0.0)
        self.assertGreaterEqual(pnd30["vat_input"], 0.0)
        self.assertEqual(pnd30["vat_net_payable"], round(pnd30["vat_output"] - pnd30["vat_input"], 2))

        # 2. ภ.ง.ด.3 Validation
        pnd3 = res.get("pnd3", {})
        self.assertIn("count", pnd3)
        self.assertIn("base_total", pnd3)
        self.assertIn("wht_total", pnd3)
        self.assertIn("items", pnd3)
        self.assertIsInstance(pnd3["items"], list)

        # 3. ภ.ง.ด.53 Validation
        pnd53 = res.get("pnd53", {})
        self.assertIn("count", pnd53)
        self.assertIn("base_total", pnd53)
        self.assertIn("wht_total", pnd53)
        self.assertIn("items", pnd53)
        self.assertIsInstance(pnd53["items"], list)

        # 4. Summary & Deadlines
        summary = res.get("summary", {})
        self.assertIn("total_tax_to_pay", summary)
        self.assertIn("deadline_wht", summary)
        self.assertIn("deadline_vat", summary)
        expected_total_tax = round(max(0.0, pnd30["vat_net_payable"]) + pnd3["wht_total"] + pnd53["wht_total"], 2)
        self.assertEqual(summary["total_tax_to_pay"], expected_total_tax)

    def test_get_cpa_audit_package_full_year(self):
        """Test get_cpa_audit_package compiles complete P&L, 12 months, and document archives."""
        res = get_cpa_audit_package(year=2026)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("year"), 2026)
        self.assertEqual(res.get("company_tax_id"), "0505568016475")

        # P&L Summary
        pnl = res.get("pnl_summary", {})
        self.assertIn("total_revenue_pre_vat", pnl)
        self.assertIn("total_revenue_gross", pnl)
        self.assertIn("total_expense_pre_vat", pnl)
        self.assertIn("total_expense_gross", pnl)
        self.assertIn("estimated_net_profit", pnl)
        self.assertIn("estimated_corporate_tax", pnl)
        self.assertEqual(pnl["estimated_net_profit"], round(pnl["total_revenue_pre_vat"] - pnl["total_expense_pre_vat"], 2))

        # Monthly breakdown (12 months)
        monthly = res.get("monthly_breakdown", [])
        self.assertEqual(len(monthly), 12)
        for m_item in monthly:
            self.assertIn("month", m_item)
            self.assertIn("month_name", m_item)
            self.assertIn("revenue_pre_vat", m_item)
            self.assertIn("expense_pre_vat", m_item)
            self.assertIn("net_profit", m_item)

        # Document inventory & counts
        doc_counts = res.get("document_counts", {})
        self.assertIn("quotations", doc_counts)
        self.assertIn("invoices", doc_counts)
        self.assertIn("receipts_tax_invoices", doc_counts)
        self.assertIn("wht_certificates", doc_counts)
        self.assertIn("expenses_vouchers", doc_counts)
        self.assertIn("total_documents", doc_counts)

        # Drive folders & readiness
        drive_folders = res.get("drive_folders", {})
        self.assertIn("root", drive_folders)
        self.assertIn("quotations", drive_folders)
        self.assertIn("receipts", drive_folders)

        readiness = res.get("audit_readiness", {})
        self.assertGreaterEqual(readiness.get("score_percent", 0), 0)
        self.assertIsInstance(readiness.get("checklist"), list)
        self.assertGreater(len(readiness["checklist"]), 0)

    def test_build_tax_filing_flex_message_schema(self):
        """Test build_tax_filing_flex_message produces 100% compliant LINE Flex schemas."""
        tax_res = get_tax_filing_report(month=8, year=2026)

        # Test all modes
        flex_all = build_tax_filing_flex_message(tax_res, tax_type="all")
        self.assertTrue(validate_line_flex_payload(flex_all))
        self.assertIn("สรุปตัวเลขยื่นภาษี", flex_all["altText"])

        flex_pnd30 = build_tax_filing_flex_message(tax_res, tax_type="pnd30")
        self.assertTrue(validate_line_flex_payload(flex_pnd30))

        flex_pnd3 = build_tax_filing_flex_message(tax_res, tax_type="pnd3")
        self.assertTrue(validate_line_flex_payload(flex_pnd3))

        flex_pnd53 = build_tax_filing_flex_message(tax_res, tax_type="pnd53")
        self.assertTrue(validate_line_flex_payload(flex_pnd53))

    def test_build_cpa_audit_pack_flex_message_schema(self):
        """Test build_cpa_audit_pack_flex_message produces 100% compliant LINE Flex schemas."""
        cpa_res = get_cpa_audit_package(year=2026)
        flex_cpa = build_cpa_audit_pack_flex_message(cpa_res)
        self.assertTrue(validate_line_flex_payload(flex_cpa))
        self.assertIn("ปิดงบ CPA", flex_cpa["altText"])

    def test_tool_declarations_presence(self):
        """Verify new tax & cpa tool declarations are registered in GEMINI_AGENT_TOOL_DECLARATIONS."""
        tool_names = [d["name"] for d in GEMINI_AGENT_TOOL_DECLARATIONS]
        self.assertIn("get_tax_filing_report", tool_names)
        self.assertIn("prepare_cpa_audit_package", tool_names)

    def test_execute_agent_tool_tax_filing_and_cpa(self):
        """Verify execute_agent_tool handles get_tax_filing_report & prepare_cpa_audit_package."""
        # 1. Tax filing tool
        res_tax, flex_tax = execute_agent_tool("get_tax_filing_report", {"month": 8, "year": 2026, "tax_type": "all"}, "test_sess")
        self.assertEqual(res_tax.get("status"), "success")
        self.assertIn("tax_report", res_tax)
        self.assertIsNotNone(flex_tax)
        self.assertTrue(validate_line_flex_payload(flex_tax))

        # 2. CPA audit tool
        res_cpa, flex_cpa = execute_agent_tool("prepare_cpa_audit_package", {"year": 2026}, "test_sess")
        self.assertEqual(res_cpa.get("status"), "success")
        self.assertIn("cpa_audit_package", res_cpa)
        self.assertIsNotNone(flex_cpa)
        self.assertTrue(validate_line_flex_payload(flex_cpa))

    def test_intent_detection(self):
        """Verify regex & keyword intent detection for tax filing and CPA requests."""
        # Tax filing intent
        is_tax, m, y, t_type = is_tax_filing_request("ขอยอดภาษียื่นสรรพากรเดือนสิงหาคม 2026 หน่อยครับ ภพ30")
        self.assertTrue(is_tax)
        self.assertEqual(m, 8)
        self.assertEqual(y, 2026)
        self.assertEqual(t_type, "pnd30")

        is_tax2, _, _, t_type2 = is_tax_filing_request("สรุปยอดหัก ณ ที่จ่าย ภ.ง.ด.3 เดือนนี้")
        self.assertTrue(is_tax2)
        self.assertEqual(t_type2, "pnd3")

        # CPA Audit intent
        is_cpa, c_year = is_cpa_audit_request("ขอเอกสารปิดงบส่งผู้สอบบัญชี cpa ประจำปี 2026")
        self.assertTrue(is_cpa)
        self.assertEqual(c_year, 2026)

        is_cpa2, _ = is_cpa_audit_request("เตรียม audit package ปิดงบการเงิน")
        self.assertTrue(is_cpa2)

    async def test_agentic_fallback_tax_filing_turn(self):
        """Verify agentic fallback simulator responds naturally with Flex card for tax filing."""
        turn_res = await agentic_fallback_simulate_turn(
            "เลขาเฟิส ขอยอดสรุปยื่นภาษีเดือนนี้ ภ.พ.30, ภ.ง.ด.3, ภ.ง.ด.53 หน่อยค่ะ",
            session_id="test_tax_session",
            speaker_name="บอสเก่ง"
        )
        self.assertIn("ภ.พ.30", turn_res["reply_text"])
        self.assertIn("ภ.ง.ด.3", turn_res["reply_text"])
        self.assertIn("ภ.ง.ด.53", turn_res["reply_text"])
        self.assertIn("บอสเก่ง", turn_res["reply_text"])
        self.assertGreater(len(turn_res["flex_cards"]), 0)
        self.assertTrue(validate_line_flex_payload(turn_res["flex_cards"][0]))

    async def test_agentic_fallback_cpa_audit_turn(self):
        """Verify agentic fallback simulator responds naturally with Flex card for CPA audit."""
        turn_res = await agentic_fallback_simulate_turn(
            "เฟิส ขอแพ็กเกจเอกสารปิดงบส่งผู้สอบบัญชี CPA ปีนี้หน่อยครับ",
            session_id="test_cpa_session",
            speaker_name="บอสมด"
        )
        self.assertIn("CPA Audit Package", turn_res["reply_text"])
        self.assertIn("รายรับรวมทั้งปี", turn_res["reply_text"])
        self.assertIn("บอสมด", turn_res["reply_text"])
        self.assertGreater(len(turn_res["flex_cards"]), 0)
        self.assertTrue(validate_line_flex_payload(turn_res["flex_cards"][0]))


if __name__ == "__main__":
    unittest.main()
