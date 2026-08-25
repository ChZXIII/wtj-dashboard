#!/usr/bin/env python3
"""
================================================================================
GHN168 Document Lifecycle Pipeline Comprehensive Test Suite
================================================================================
Tests end-to-end document conversion:
1. QT -> IV (Quotation to Invoice / Billing Note with 15-day due date)
2. IV -> RE (Invoice to Receipt / Tax Invoice with safe status update to 'ชำระแล้ว' & sync to 'รายรับ')
3. WHT / 50 ทวิ (Withholding Tax Certificate generation with 3% rate)
4. Chat Intent Recognition & Flex Message generation
5. REST API Endpoints (/api/documents/convert)
================================================================================
"""

import unittest
from datetime import datetime
from fastapi.testclient import TestClient

from ghn168_sync_service import (
    convert_document,
    find_document_by_no,
    read_sheet_data,
    normalize_doc_type,
    generate_and_sync_document
)
from line_bot_server import (
    app,
    is_document_conversion_request,
    build_document_conversion_flex_message
)

client = TestClient(app)


class TestDocumentLifecyclePipeline(unittest.TestCase):
    """Unit and Integration tests for Document Lifecycle conversions."""

    def test_find_document_by_no_quotation(self):
        """Test finding an existing Quotation."""
        doc = find_document_by_no("QT2608-001")
        self.assertIsNotNone(doc)
        self.assertEqual(doc["doc_no"], "QT2608-001")
        self.assertIn("เชียงใหม่มีเดีย", doc["client_name"])
        self.assertEqual(doc["pre_vat"], 50000.0)
        self.assertEqual(doc["vat_amount"], 3500.0)

    def test_find_document_by_no_invoice(self):
        """Test finding an existing Invoice."""
        doc = find_document_by_no("IV2608-001")
        self.assertIsNotNone(doc)
        self.assertEqual(doc["doc_no"], "IV2608-001")
        self.assertIn("เชียงใหม่มีเดีย", doc["client_name"])
        self.assertEqual(doc["net_total"], 52000.0)

    def test_find_document_by_customer_name_fuzzy(self):
        """Test fuzzy finding document by customer keyword."""
        doc = find_document_by_no("ลานนา")
        self.assertIsNotNone(doc)
        self.assertIn("ลานนา", doc["client_name"])

    def test_convert_qt_to_iv(self):
        """Test converting Quotation (QT) to Invoice (IV)."""
        res = convert_document("QT2608-001", "invoice")
        self.assertIn(res["status"], ["success", "simulation"])
        self.assertEqual(res["target_type"], "invoice")
        self.assertIn("IV", res["doc_no"])
        self.assertIn("เชียงใหม่มีเดีย", res["client_name"])
        self.assertTrue(len(res["pdf_url"]) > 0)
        self.assertEqual(res["totals"]["net_total"], 53500.0)
        self.assertIn("แปลงเอกสารจาก QT2608-001 เป็น INVOICE", res["message"])

    def test_convert_iv_to_re(self):
        """Test converting Invoice (IV) to Receipt (RE)."""
        res = convert_document("IV2608-001", "receipt")
        self.assertIn(res["status"], ["success", "simulation"])
        self.assertEqual(res["target_type"], "receipt")
        self.assertIn("RE", res["doc_no"])
        self.assertIn("เชียงใหม่มีเดีย", res["client_name"])
        self.assertTrue(len(res["pdf_url"]) > 0)
        self.assertEqual(res["totals"]["net_total"], 52000.0)
        self.assertIn("แปลงเอกสารจาก IV2608-001 เป็น RECEIPT", res["message"])

    def test_convert_with_overrides(self):
        """Test conversion with explicit overrides."""
        overrides = {
            "due_date": "15/09/2026",
            "remarks": "ชำระงวดที่ 1/2",
            "signer_name": "นางสาว นวพร เขียวแก้ว (คุณหอม)"
        }
        res = convert_document("QT2608-001", "invoice", overrides=overrides)
        self.assertIn(res["status"], ["success", "simulation"])
        self.assertEqual(res["target_type"], "invoice")

    def test_generate_50_tavi_wht(self):
        """Test generating Withholding Tax Certificate (50 ทวิ)."""
        wht_data = {
            "payee_name": "นาย สมชาย นักแสดงมืออาชีพ",
            "payee_tax_id": "1509900123456",
            "gross_amount": 15000.0,
            "wht_rate": 3.0,
            "category": "ค่าบริการจ้างทำของ / ค่าแสดง",
            "project_name": "งานโฆษณานอร์ทเทิร์นแล็บ"
        }
        res = convert_document("สมชาย", "wht", overrides=wht_data)
        self.assertIn(res["status"], ["success", "simulation"])
        self.assertEqual(res["target_type"], "wht")
        self.assertIn("50BIS", res["doc_no"])

    def test_intent_detection_qt_to_iv(self):
        """Test chat intent detection for QT -> IV."""
        text1 = "วางบิลงานเอ็มคูล"
        is_conv, src, tgt, ov = is_document_conversion_request(text1)
        self.assertTrue(is_conv)
        self.assertEqual(tgt, "invoice")
        self.assertIn("เอ็มคูล", src)

        text2 = "วางบิล QT-202608-440"
        is_conv2, src2, tgt2, ov2 = is_document_conversion_request(text2)
        self.assertTrue(is_conv2)
        self.assertEqual(tgt2, "invoice")
        self.assertEqual(src2, "QT-202608-440")

    def test_intent_detection_iv_to_re(self):
        """Test chat intent detection for IV -> RE."""
        text = "เอ็มคูลโอนแล้ว ออกใบเสร็จ"
        is_conv, src, tgt, ov = is_document_conversion_request(text)
        self.assertTrue(is_conv)
        self.assertEqual(tgt, "receipt")
        self.assertIn("เอ็มคูล", src)

        text2 = "ออกใบเสร็จ IV2608-001"
        is_conv2, src2, tgt2, ov2 = is_document_conversion_request(text2)
        self.assertTrue(is_conv2)
        self.assertEqual(tgt2, "receipt")
        self.assertEqual(src2, "IV2608-001")

    def test_intent_detection_50_tavi(self):
        """Test chat intent detection for 50 ทวิ."""
        text = "ออก 50 ทวิ จ้างนักแสดง สมชาย ยอด 15000"
        is_conv, src, tgt, ov = is_document_conversion_request(text)
        self.assertTrue(is_conv)
        self.assertEqual(tgt, "wht")
        self.assertEqual(ov.get("amount"), 15000.0)
        self.assertIn("สมชาย", ov.get("payee_name", ""))

    def test_document_conversion_flex_card(self):
        """Test LINE Flex Message Card builder for document conversion."""
        sample_res = {
            "source_doc_no": "QT2608-001",
            "target_type": "invoice",
            "doc_no": "IV2608-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า 2 ตอน",
            "pdf_url": "https://drive.google.com/sample_iv.pdf",
            "totals": {"net_total": 52000.0}
        }
        card = build_document_conversion_flex_message(sample_res)
        self.assertEqual(card["type"], "flex")
        self.assertIn("contents", card)
        bubble = card["contents"]
        self.assertEqual(bubble["type"], "bubble")
        self.assertEqual(bubble["header"]["backgroundColor"], "#4f46e5")

    def test_api_convert_document_endpoint(self):
        """Test REST API POST /api/documents/convert."""
        payload = {
            "source_doc_no": "QT2608-001",
            "target_type": "invoice"
        }
        resp = client.post("/api/documents/convert", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("conversion_result", data)
        self.assertIn("flex_card", data)
    def test_normalize_company_name(self):
        """Test Thai company name normalization and symbol stripping."""
        from ghn168_sync_service import normalize_company_name

        self.assertEqual(normalize_company_name("บ เอ็ม คูล"), "เอ็มคูล")
        self.assertEqual(normalize_company_name("บ. เอ็มคูล"), "เอ็มคูล")
        self.assertEqual(normalize_company_name("บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด"), "เอ็มคูลเฮ้าส์ออแกไนซ์")
        self.assertIn(normalize_company_name("บ เอ็ม คูล"), normalize_company_name("บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด"))
        self.assertEqual(normalize_company_name("บจก. แคทไซคลิ่ง จำกัด"), "แคทไซคลิ่ง")
        self.assertEqual(normalize_company_name("หจก. ลานนา ครีเอทีฟ สตูดิโอ จำกัด (มหาชน)"), "ลานนาครีเอทีฟสตูดิโอ")
        self.assertEqual(normalize_company_name("โรงแรม เดอะริเวอร์ เชียงใหม่"), "เดอะริเวอร์เชียงใหม่")

    def test_find_document_by_company_name_mcool(self):
        """Test finding Quotation by normalized company name 'บ เอ็ม คูล'."""
        doc = find_document_by_no("บ เอ็ม คูล")
        self.assertIsNotNone(doc)
        self.assertIn("เอ็ม-คูล", doc["client_name"])
        self.assertEqual(doc["pre_vat"], 45000.0)
        self.assertEqual(doc["vat_amount"], 3150.0)
        self.assertEqual(doc["net_total"], 48150.0)

    def test_convert_mcool_qt_to_iv(self):
        """Test converting M-Cool Quotation to Invoice via customer keyword."""
        res = convert_document("บ เอ็ม คูล", "invoice")
        self.assertIn(res["status"], ["success", "simulation"])
        self.assertEqual(res["target_type"], "invoice")
        self.assertIn("IV", res["doc_no"])
        self.assertIn("เอ็ม-คูล", res["client_name"])
        self.assertEqual(res["totals"]["net_total"], 48150.0)

    def test_prevent_empty_zero_baht_document(self):
        """Test that missing source document with no amount returns not_found without generating 0-baht doc."""
        res = convert_document("บริษัทไม่มีตัวตน_XYZ_999", "invoice")
        self.assertEqual(res["status"], "not_found")
        self.assertIsNone(res["doc_no"])
        self.assertIsNone(res["pdf_url"])
        self.assertEqual(res["totals"]["net_total"], 0.0)
        self.assertIn("ไม่สามารถออกเอกสารเปล่ายอด 0.00 บาทได้", res["message"])

    def test_intent_detection_real_world_user_message(self):
        """Test intent extraction for '@เลขาเฟิส ทำใบวางบิลให้หน่อยของ บ เอ็ม คูล ที่ทำใบเสนอราคาไปก่อนหน้านี้'."""
        text = "@เลขาเฟิส ทำใบวางบิลให้หน่อยของ บ เอ็ม คูล ที่ทำใบเสนอราคาไปก่อนหน้านี้"
        is_conv, src, tgt, ov = is_document_conversion_request(text)
        self.assertTrue(is_conv)
        self.assertEqual(tgt, "invoice")
        self.assertEqual(src, "บ เอ็ม คูล")
        self.assertTrue(ov.get("relative_ref"))

    def test_intent_detection_relative_latest(self):
        """Test intent extraction for relative reference 'latest' without explicit company name."""
        text = "ทำใบวางบิลจากใบเสนอราคาล่าสุดให้หน่อย"
        is_conv, src, tgt, ov = is_document_conversion_request(text)
        self.assertTrue(is_conv)
        self.assertEqual(tgt, "invoice")
        self.assertEqual(src, "latest")
        self.assertTrue(ov.get("relative_ref"))

    def test_multi_turn_session_cache_conversion_flow(self):
        """Test multi-turn session cache conversion pipeline from QT -> IV -> RE."""
        session_id = "test_pipeline_mcool_session_001"

        # Turn 1: User asks to convert M-Cool quotation to invoice
        msg_iv = "@เลขาเฟิส ทำใบวางบิลให้หน่อยของ บ เอ็ม คูล ที่ทำใบเสนอราคาไปก่อนหน้านี้"
        resp1 = client.post("/api/test_chat", json={"message": msg_iv, "session_id": session_id})
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertIn("IV", data1["reply"])
        self.assertIn("เอ็ม-คูล", data1["reply"])
        self.assertIn("48,150.00", data1["reply"])

        # Turn 2: User asks to convert to receipt using relative reference 'อันล่าสุด'
        msg_re = "ลูกค้าโอนแล้ว ออกใบเสร็จอันล่าสุดให้หน่อย"
        resp2 = client.post("/api/test_chat", json={"message": msg_re, "session_id": session_id})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertIn("RECEIPT", data2["reply"])
        self.assertIn("RE-202608-440", data2["reply"])
        self.assertTrue(any(amt in data2["reply"] for amt in ["48,150.00", "46,800.00"]))

    def test_zero_amount_chat_warning_message(self):
        """Test that attempting to convert non-existent doc in chat returns polite warning instead of 0 baht card."""
        fresh_session = "test_unfound_fresh_session_002"
        msg = "ทำใบวางบิลให้หน่อยของ บ.ไม่มีในระบบ ที่ทำใบเสนอราคาไปก่อนหน้านี้"
        resp = client.post("/api/test_chat", json={"message": msg, "session_id": fresh_session})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("⚠️", data["reply"])
        self.assertIn("ไม่พบในระบบ", data["reply"])
        self.assertNotIn("0.00 บาท) ให้เรียบร้อยแล้ว", data["reply"])


if __name__ == "__main__":
    unittest.main()
