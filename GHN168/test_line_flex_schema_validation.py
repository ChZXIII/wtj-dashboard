"""
Unit Tests for LINE Messaging API Flex Message Schema Validation & Unified Document Cards.
Author: น้องคิว (Q) - Senior Backend Developer (GHN168)
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from line_bot_server import (
    sanitize_flex_uri,
    validate_line_flex_payload,
    build_document_flex_message,
    build_document_conversion_flex_message,
    build_income_slip_flex_message,
    build_overdue_invoices_flex_message,
    build_calendar_event_created_flex_message,
    build_calendar_reminder_flex_message,
    build_partner_hunter_flex_message,
    build_partner_labor_flex_message,
    build_partner_vault_flex_message,
    build_partner_all_in_one_financial_flex_message,
    build_tax_reminder_flex_message,
    build_expense_ocr_flex_message,
    build_accounting_summary_flex_message,
    build_customer_card_flex_message,
    build_customer_list_flex_message,
    send_line_reply_messages,
    send_line_push_message
)


class TestLineFlexSchemaValidation(unittest.TestCase):
    """Rigorous validation tests for LINE Flex Message payloads."""

    def test_sanitize_flex_uri(self):
        """Test sanitize_flex_uri handles valid, invalid, and missing URIs safely."""
        self.assertEqual(sanitize_flex_uri("https://drive.google.com/file/d/123/view"), "https://drive.google.com/file/d/123/view")
        self.assertEqual(sanitize_flex_uri("http://example.com/doc.pdf"), "http://example.com/doc.pdf")
        self.assertEqual(sanitize_flex_uri("line://app/123"), "line://app/123")
        self.assertEqual(sanitize_flex_uri("tel:0812345678"), "tel:0812345678")
        # Invalid / missing fallbacks
        self.assertEqual(sanitize_flex_uri(""), "https://drive.google.com")
        self.assertEqual(sanitize_flex_uri(None), "https://drive.google.com")
        self.assertEqual(sanitize_flex_uri("/var/data/doc.pdf"), "https://drive.google.com")
        self.assertEqual(sanitize_flex_uri("ftp://example.com/doc.pdf"), "https://drive.google.com")

    def test_validate_line_flex_payload_rules(self):
        """Test that validate_line_flex_payload detects schema violations."""
        # Valid flex message
        valid_flex = {
            "type": "flex",
            "altText": "เอกสารใบเสนอราคา",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": "ทดสอบ"}]
                }
            }
        }
        self.assertTrue(validate_line_flex_payload(valid_flex))

        # Invalid: not a dict
        with self.assertRaises(ValueError):
            validate_line_flex_payload("not a dict")

        # Invalid: missing/wrong type
        with self.assertRaises(ValueError):
            validate_line_flex_payload({"type": "text", "text": "hello"})

        # Invalid: empty altText
        with self.assertRaises(ValueError):
            validate_line_flex_payload({"type": "flex", "altText": "", "contents": {"type": "bubble"}})

        # Invalid: altText too long (> 400 chars)
        with self.assertRaises(ValueError):
            validate_line_flex_payload({"type": "flex", "altText": "A" * 401, "contents": {"type": "bubble"}})

        # Invalid: contents not bubble or carousel
        with self.assertRaises(ValueError):
            validate_line_flex_payload({"type": "flex", "altText": "Valid", "contents": {"type": "box"}})

        # Invalid: action URI without valid scheme
        bad_uri_flex = {
            "type": "flex",
            "altText": "Valid",
            "contents": {
                "type": "bubble",
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "uri",
                                "label": "Download",
                                "uri": "/tmp/local_path.pdf"
                            }
                        }
                    ]
                }
            }
        }
        with self.assertRaises(ValueError):
            validate_line_flex_payload(bad_uri_flex)

        # Invalid: action label too long (> 40 chars)
        bad_label_flex = {
            "type": "flex",
            "altText": "Valid",
            "contents": {
                "type": "bubble",
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "This label is definitely way longer than forty characters allowed by LINE!",
                                "text": "hello"
                            }
                        }
                    ]
                }
            }
        }
        with self.assertRaises(ValueError):
            validate_line_flex_payload(bad_label_flex)

    def test_quotation_flex_card_schema(self):
        """Test Quotation (QT) Flex card schema, colors, and button."""
        doc_res = {
            "doc_type": "quotation",
            "doc_no": "QT-202608-001",
            "client_name": "บริษัท สยาม มีเดีย กรุ๊ป จำกัด",
            "project_name": "ผลิตคลิป Viral Video 3 ตอน",
            "pdf_url": "https://drive.google.com/sample_qt.pdf",
            "sheet_name": "ใบเสนอราคา",
            "totals": {
                "pre_vat": 100000.0,
                "vat_amount": 7000.0,
                "wht_amount": 3000.0,
                "net_total": 104000.0,
                "wht_rate": 3.0,
                "baht_text": "หนึ่งแสนสี่พันบาทถ้วน"
            }
        }
        card = build_document_flex_message(doc_res)
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["backgroundColor"], "#0284c7")  # Sky Blue
        self.assertEqual(bubble["footer"]["contents"][0]["action"]["label"], "เปิดดูเอกสาร PDF (Drive)")
        self.assertEqual(bubble["footer"]["contents"][0]["action"]["uri"], "https://drive.google.com/sample_qt.pdf")
        self.assertIn("ใบเสนอราคา", bubble["footer"]["contents"][1]["text"])

    def test_invoice_flex_card_schema(self):
        """Test Invoice (IV) Flex card schema, colors, and button."""
        doc_res = {
            "doc_type": "invoice",
            "doc_no": "IV2608-002",
            "source_doc_no": "QT2608-001",
            "client_name": "บริษัท เชียงใหม่ โปรดักชั่น จำกัด",
            "project_name": "บันทึกเสียงและตัดต่อ Podcast",
            "pdf_url": "https://drive.google.com/sample_iv.pdf",
            "sheet_name": "ใบวางบิล",
            "totals": {
                "pre_vat": 50000.0,
                "vat_amount": 3500.0,
                "wht_amount": 1500.0,
                "net_total": 52000.0,
                "wht_rate": 3.0,
                "baht_text": "ห้าหมื่นสองพันบาทถ้วน"
            }
        }
        card = build_document_flex_message(doc_res)
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["backgroundColor"], "#4f46e5")  # Indigo Purple
        self.assertIn("QT2608-001", bubble["header"]["contents"][2]["text"])
        self.assertEqual(bubble["footer"]["contents"][0]["action"]["label"], "เปิดดูเอกสาร PDF (Drive)")
        self.assertIn("ใบวางบิล", bubble["footer"]["contents"][1]["text"])

    def test_receipt_flex_card_schema(self):
        """Test Receipt (RE) Flex card schema, colors, and button."""
        doc_res = {
            "doc_type": "receipt",
            "doc_no": "RE2608-003",
            "source_doc_no": "IV2608-002",
            "client_name": "บริษัท กรุงเทพ บิซ จำกัด",
            "project_name": "จัดงาน Event ถ่ายทอดสด",
            "pdf_url": "https://drive.google.com/sample_re.pdf",
            "sheet_name": "รายรับ",
            "totals": {
                "pre_vat": 80000.0,
                "vat_amount": 5600.0,
                "wht_amount": 0.0,
                "net_total": 85600.0,
                "wht_rate": 0.0,
                "baht_text": "แปดหมื่นห้าพันหกร้อยบาทถ้วน"
            }
        }
        card = build_document_flex_message(doc_res)
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["backgroundColor"], "#059669")  # Emerald Green
        self.assertIn("IV2608-002", bubble["header"]["contents"][2]["text"])
        self.assertIn("รายรับ", bubble["footer"]["contents"][1]["text"])

    def test_wht_flex_card_schema(self):
        """Test 50 ทวิ (WHT) Flex card schema, colors, and button."""
        doc_res = {
            "doc_type": "wht",
            "doc_no": "50BIS-202608-001",
            "source_doc_no": "IV2608-002",
            "client_name": "คุณ สมชาย งานกราฟิก",
            "project_name": "ค่าบริการออกแบบ 3D Motion",
            "pdf_url": "https://drive.google.com/sample_wht.pdf",
            "sheet_name": "รายจ่าย",
            "totals": {
                "pre_vat": 20000.0,
                "vat_amount": 0.0,
                "wht_amount": 600.0,
                "net_total": 19400.0,
                "wht_rate": 3.0,
                "baht_text": "หนึ่งหมื่นเก้าพันสี่ร้อยบาทถ้วน"
            }
        }
        card = build_document_flex_message(doc_res)
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["backgroundColor"], "#8b5cf6")  # Purple
        self.assertIn("50 ทวิ", card["altText"])
        self.assertIn("รายจ่าย", bubble["footer"]["contents"][1]["text"])

    def test_document_conversion_unified_flex_message(self):
        """Test that build_document_conversion_flex_message produces identical standard cards."""
        conv_res = {
            "status": "success",
            "source_doc_no": "QT2608-001",
            "target_type": "invoice",
            "doc_no": "IV2608-001",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ผลิตคลิปวิดีโอโปรโมทสินค้า 2 ตอน",
            "pdf_url": "https://drive.google.com/sample_iv.pdf",
            "totals": {
                "pre_vat": 50000.0,
                "vat_amount": 3500.0,
                "wht_amount": 1500.0,
                "net_total": 52000.0,
                "wht_rate": 3.0
            }
        }
        card = build_document_conversion_flex_message(conv_res)
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["backgroundColor"], "#4f46e5")
        self.assertIn("QT2608-001", bubble["header"]["contents"][2]["text"])
        self.assertEqual(bubble["footer"]["contents"][0]["action"]["label"], "เปิดดูเอกสาร PDF (Drive)")
        self.assertEqual(bubble["footer"]["contents"][0]["action"]["uri"], "https://drive.google.com/sample_iv.pdf")

    def test_all_other_flex_message_builders_schema(self):
        """Verify that all system Flex Message builders adhere 100% to LINE schema."""
        # 1. Income slip
        slip_card = build_income_slip_flex_message({"amount": 52000.0, "sender_name": "บริษัท ผู้โอนเงิน จำกัด"})
        self.assertTrue(validate_line_flex_payload(slip_card))

        # 2. Overdue invoices
        overdue_card = build_overdue_invoices_flex_message({
            "total_unpaid_amount": 120000.0,
            "overdue_count": 2,
            "due_today_count": 1,
            "upcoming_count": 1,
            "invoices": [{"doc_no": "IV2608-001", "client_name": "บจก. เอ", "net_total": 50000.0, "days_overdue": 5}]
        })
        self.assertTrue(validate_line_flex_payload(overdue_card))

        # 3. Calendar event created
        cal_created = build_calendar_event_created_flex_message({
            "title": "นัดถ่ายทำนอกสถานที่",
            "start_time": "2026-08-26 10:00",
            "end_time": "2026-08-26 16:00"
        })
        self.assertTrue(validate_line_flex_payload(cal_created))

        # 4. Calendar reminder
        cal_rem = build_calendar_reminder_flex_message([
            {"summary": "งานถ่ายโฆษณา", "start_time": "09:00", "end_time": "12:00", "location": "สตูดิโอ GHN"}
        ], date_label="พรุ่งนี้")
        self.assertTrue(validate_line_flex_payload(cal_rem))

        # 5. Partner financial breakdown cards
        sample_breakdown = {
            "month_label": "สิงหาคม 2569",
            "pillar_1_lead_hunters": {"total_gross_volume": 200000.0, "total_peer_shared_volume": 50000.0, "leaderboard": []},
            "pillar_2_labor_costs": {"total_labor_cost": 80000.0, "crew_payouts": []},
            "pillar_3_vault_and_retained": {"retained_company_fund": 50000.0, "partner_profit_pools": []},
            "summary_dashboard": {"total_gross_revenue": 200000.0, "total_labor_expenses": 80000.0, "net_operating_profit": 120000.0}
        }
        self.assertTrue(validate_line_flex_payload(build_partner_hunter_flex_message(sample_breakdown)))
        self.assertTrue(validate_line_flex_payload(build_partner_labor_flex_message(sample_breakdown)))
        self.assertTrue(validate_line_flex_payload(build_partner_vault_flex_message(sample_breakdown)))
        self.assertTrue(validate_line_flex_payload(build_partner_all_in_one_financial_flex_message(sample_breakdown)))

        # 6. Tax reminder
        self.assertTrue(validate_line_flex_payload(build_tax_reminder_flex_message("pnd53")))

        # 7. Expense OCR
        ocr_card = build_expense_ocr_flex_message({
            "store_name": "โฮมโปร",
            "net_amount": 1500.0,
            "category": "วัสดุอุปกรณ์กองถ่าย"
        })
        self.assertTrue(validate_line_flex_payload(ocr_card))

        # 8. Accounting summary
        acc_card = build_accounting_summary_flex_message({
            "month_label": "สิงหาคม 2569",
            "total_income": 350000.0,
            "total_expense": 120000.0,
            "net_profit": 230000.0,
            "pending_invoices_count": 2,
            "pending_invoices_amount": 65000.0
        })
        self.assertTrue(validate_line_flex_payload(acc_card))

        # 9. Customer card
        cust_card = build_customer_card_flex_message({
            "customer_id": "CUST-001",
            "customer_name": "บริษัท ทดสอบ จำกัด",
            "tax_id": "0105558000000"
        })
        self.assertTrue(validate_line_flex_payload(cust_card))

        # 10. Customer list (Carousel)
        cust_list_card = build_customer_list_flex_message([
            {"customer_id": "CUST-001", "customer_name": "บริษัท ก", "tax_id": "1111111111111"},
            {"customer_id": "CUST-002", "customer_name": "บริษัท ข", "tax_id": "2222222222222"}
        ])
        self.assertTrue(validate_line_flex_payload(cust_list_card))

    @patch("line_bot_server.requests.post")
    def test_send_line_reply_messages_success_and_fallback(self, mock_post):
        """Test send_line_reply_messages with simulated 200 OK and 400 Bad Request safety fallback."""
        # 1. Successful Flex Reply
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        valid_flex = build_document_flex_message({
            "doc_type": "quotation",
            "doc_no": "QT2608-001",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "project_name": "งานบริการ",
            "pdf_url": "https://drive.google.com/sample.pdf",
            "totals": {"net_total": 10000.0}
        })
        success = send_line_reply_messages("test_reply_token_1234567890", [valid_flex])
        self.assertTrue(success)

        # 2. Simulated 400 Fallback to altText
        mock_400_response = MagicMock()
        mock_400_response.status_code = 400
        mock_400_response.text = '{"message": "Invalid URI scheme"}'

        mock_200_response = MagicMock()
        mock_200_response.status_code = 200

        mock_post.side_effect = [mock_400_response, mock_200_response]
        success_fallback = send_line_reply_messages("test_reply_token_1234567890", [valid_flex])
        self.assertTrue(success_fallback)
        # Verify fallback sent text containing altText
        self.assertEqual(mock_post.call_count, 3)  # 1 from first test + 2 from fallback test

    @patch("line_bot_server.convert_document")
    def test_keng_prompt_conversion_with_partial_error(self, mock_convert):
        """
        Simulate Keng's real prompt when PDFShift fails with 'partial_error'.
        Verifies that Flex Message is 100% created and attached to flex_cards list.
        """
        from line_bot_server import agentic_fallback_simulate_turn, execute_agent_tool

        mock_convert.return_value = {
            "status": "partial_error",
            "source_doc_no": "QT-202608-155",
            "source_type": "quotation",
            "target_type": "invoice",
            "doc_no": "IV-202608-155",
            "pdf_url": "",
            "totals": {
                "subtotal": 18000.0,
                "pre_vat": 18000.0,
                "is_vat": True,
                "vat_rate": 7.0,
                "vat_amount": 1260.0,
                "gross_amount": 19260.0,
                "net_total": 19260.0
            },
            "items": [{"desc": "งานบริการ", "qty": 1, "price": 18000.0, "amount": 18000.0}],
            "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
            "project_name": "งานบริการ",
            "message": "แปลงเอกสารสำเร็จ (PDFShift credit exhausted)"
        }

        user_prompt = "มันมี ใบเสนอราคาของ บ เอ็มคูลอยู่อันนึงที่ยอด 18000 ทำ ใบวางบิลโดยอ้างอิง ใบเสนอราคานั้น"
        session_id = "test_keng_session_001"

        import asyncio
        res = asyncio.run(agentic_fallback_simulate_turn(user_prompt, session_id))

        self.assertIn("IV-202608-155", res["reply_text"])
        self.assertIn("19,260.00", res["reply_text"])
        self.assertGreaterEqual(len(res["flex_cards"]), 1)

        flex_card = res["flex_cards"][0]
        self.assertEqual(flex_card["type"], "flex")
        self.assertTrue(validate_line_flex_payload(flex_card))
        self.assertEqual(flex_card["contents"]["header"]["backgroundColor"], "#4f46e5")
        self.assertIn("IV-202608-155", flex_card["contents"]["header"]["contents"][2]["text"])


if __name__ == "__main__":
    unittest.main()

