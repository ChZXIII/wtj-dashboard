"""
Tests for Confirmation Gatekeeper & Deposit Logic for GHN168 Bot.
Verifies:
1. Disabling blind auto-conversion on payment triggers ('จ่ายแล้ว', 'โอนแล้ว', 'ลูกค้าจ่ายมาหมดแล้ว', etc.)
2. Confirmation Gatekeeper Flex Message builder and interactive intent flow (0%, 3%, 1%, net transfer, cancel)
3. Deposit (เงินมัดจำ) math breakdown, installment receipt generation '(งวดที่ 1 เงินมัดจำ)', and final invoice deduction
4. convert_document in ghn168_sync_service.py does not naively copy wht_rate=0 from Quotation to Receipt
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from ghn168_sync_service import (
    calculate_deposit_breakdown,
    calculate_final_invoice_with_deposit,
    convert_document,
)
from line_bot_server import (
    app,
    build_payment_gatekeeper_flex_message,
    detect_explicit_payment_confirmation,
    is_payment_trigger_message,
    validate_line_flex_payload,
    PENDING_PAYMENT_CONFIRMATIONS,
    SESSION_LAST_GENERATED_DOCS,
)


class TestConfirmationGatekeeperAndDeposit(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.gemini_patch = patch("line_bot_server.GEMINI_API_KEY", "")
        self.gemini_patch.start()
        PENDING_PAYMENT_CONFIRMATIONS.clear()
        SESSION_LAST_GENERATED_DOCS.clear()

    def tearDown(self):
        self.gemini_patch.stop()
        PENDING_PAYMENT_CONFIRMATIONS.clear()
        SESSION_LAST_GENERATED_DOCS.clear()

    # --------------------------------------------------------------------------
    # 1. Math and Calculation Helpers
    # --------------------------------------------------------------------------
    def test_calculate_deposit_breakdown(self):
        """Test deposit breakdown: 20,000 -> Pre-VAT 18,691.59, VAT 1,308.41."""
        res = calculate_deposit_breakdown(20000.0)
        self.assertEqual(res["deposit_amount"], 20000.0)
        self.assertEqual(res["pre_vat"], 18691.59)
        self.assertEqual(res["vat_amount"], 1308.41)
        self.assertEqual(res["total_amount"], 20000.0)

    def test_calculate_final_invoice_with_deposit(self):
        """Test final invoice deduction: 50,000 - 18,691.59 = 31,308.41 + VAT 2,191.59 = 33,500."""
        res = calculate_final_invoice_with_deposit(
            total_project_pre_vat=50000.0,
            deposit_pre_vat=18691.59,
            vat_rate=0.07
        )
        self.assertEqual(res["total_project_pre_vat"], 50000.0)
        self.assertEqual(res["deposit_pre_vat"], 18691.59)
        self.assertEqual(res["remaining_pre_vat"], 31308.41)
        self.assertEqual(res["vat_amount"], 2191.59)
        self.assertEqual(res["gross_amount"], 33500.00)
        self.assertEqual(res["net_total"], 33500.00)

        # Test items produced
        items = res["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["amount"], 50000.0)
        self.assertEqual(items[1]["amount"], -18691.59)

    # --------------------------------------------------------------------------
    # 2. Scope 4: convert_document does NOT copy wht_rate=0 from Quotation
    # --------------------------------------------------------------------------
    @patch("ghn168_sync_service.find_document_by_no")
    @patch("ghn168_sync_service.generate_and_sync_document")
    @patch("ghn168_sync_service.get_next_document_number")
    def test_convert_document_does_not_naively_copy_zero_wht(
        self, mock_next_no, mock_sync, mock_find
    ):
        """Quotation source has wht_rate=0.0; converting to Receipt must default to 3.0% instead of 0.0%."""
        mock_find.return_value = {
            "doc_no": "QT-202609-001",
            "doc_type": "quotation",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "project_name": "งานโฆษณา",
            "net_total": 48150.0,
            "pre_vat": 45000.0,
            "vat_amount": 3150.0,
            "wht_rate": 0.0,  # Quotation standard
            "items": [{"desc": "งานโฆษณา", "qty": 1, "price": 45000.0, "amount": 45000.0}]
        }
        mock_next_no.return_value = "RE-202609-001"
        mock_sync.side_effect = lambda doc_type, doc_data, **kwargs: {
            "status": "success",
            "doc_no": doc_data.get("doc_no"),
            "totals": {"net_total": 46800.0, "wht_rate": doc_data.get("wht_rate")},
            "wht_rate": doc_data.get("wht_rate")
        }

        # Conversion without explicit wht_rate override -> should default to 3.0% (NOT 0.0%)
        res = convert_document("QT-202609-001", "receipt")
        self.assertEqual(res["status"], "success")
        passed_payload = mock_sync.call_args[1]["doc_data"]
        self.assertEqual(passed_payload["wht_rate"], 3.0)

        # Conversion with explicit wht_rate=0 override -> should respect 0.0%
        res_zero = convert_document("QT-202609-001", "receipt", overrides={"wht_rate": 0.0})
        passed_zero_payload = mock_sync.call_args[1]["doc_data"]
        self.assertEqual(passed_zero_payload["wht_rate"], 0.0)

    # --------------------------------------------------------------------------
    # 3. Scope 3: convert_document with Deposit
    # --------------------------------------------------------------------------
    @patch("ghn168_sync_service.find_document_by_no")
    @patch("ghn168_sync_service.generate_and_sync_document")
    @patch("ghn168_sync_service.get_next_document_number")
    def test_convert_document_deposit_receipt_generation(
        self, mock_next_no, mock_sync, mock_find
    ):
        """Testing deposit receipt with '(งวดที่ 1 เงินมัดจำ)'."""
        mock_find.return_value = {
            "doc_no": "IV-202609-001",
            "doc_type": "invoice",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "project_name": "งานโฆษณา",
            "net_total": 53500.0,
            "pre_vat": 50000.0,
            "vat_amount": 3500.0,
            "wht_rate": 3.0
        }
        mock_next_no.return_value = "RE-202609-002"
        mock_sync.side_effect = lambda doc_type, doc_data, **kwargs: {
            "status": "success",
            "doc_no": doc_data.get("doc_no"),
            "totals": {"net_total": 20000.0, "pre_vat": doc_data.get("pre_vat")},
            "items": doc_data.get("items")
        }

        res = convert_document("IV-202609-001", "receipt", overrides={"deposit_amount": 20000.0})
        passed_payload = mock_sync.call_args[1]["doc_data"]
        self.assertEqual(passed_payload["pre_vat"], 18691.59)
        self.assertEqual(passed_payload["vat_amount"], 1308.41)
        self.assertEqual(len(passed_payload["items"]), 1)
        self.assertIn("(งวดที่ 1 เงินมัดจำ)", passed_payload["items"][0]["desc"])

    # --------------------------------------------------------------------------
    # 4. Scope 2: Flex Card Validation
    # --------------------------------------------------------------------------
    def test_payment_gatekeeper_flex_card_schema(self):
        """Test build_payment_gatekeeper_flex_message schema correctness."""
        card = build_payment_gatekeeper_flex_message({
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 48150.0,
            "pre_vat": 45000.0,
            "vat_amount": 3150.0
        })
        self.assertTrue(validate_line_flex_payload(card))
        bubble = card["contents"]
        self.assertEqual(bubble["header"]["contents"][1]["text"], "แจ้งยืนยันยอดเงินรับชำระ")

        # Verify 3 Action Buttons
        footer_contents = bubble["footer"]["contents"]
        buttons = [c for c in footer_contents if c.get("type") == "button"]
        self.assertEqual(len(buttons), 3)
        self.assertIn("โอนเต็ม (ไม่หักภาษี)", buttons[0]["action"]["label"])
        self.assertIn("หัก 3% บริการทั่วไป", buttons[1]["action"]["label"])
        self.assertIn("หัก 1% ราชการ/AOT", buttons[2]["action"]["label"])

        # Verify footer guidance text
        footer_text = footer_contents[3]["text"]
        self.assertIn("หรือพิมพ์ยอดเงินที่โอนเข้าจริงในแชท", footer_text)
        self.assertIn("เข้า 16,640", footer_text)
        self.assertIn("มัดจำ 20,000", footer_text)

    # --------------------------------------------------------------------------
    # 5. Detector Functions
    # --------------------------------------------------------------------------
    def test_payment_detectors(self):
        """Test is_payment_trigger_message and detect_explicit_payment_confirmation."""
        self.assertTrue(is_payment_trigger_message("จ่ายแล้ว"))
        self.assertTrue(is_payment_trigger_message("ลูกค้าจ่ายมาหมดแล้ว"))
        self.assertTrue(is_payment_trigger_message("โอนแล้ว"))
        self.assertTrue(is_payment_trigger_message("เอ็มคูลจ่ายแล้ว"))
        self.assertFalse(is_payment_trigger_message("ขอใบเสนอราคาหน่อย"))

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("จ่ายแล้ว")
        self.assertFalse(has_exp)

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("โอนเต็ม (ไม่หักภาษี)")
        self.assertTrue(has_exp)
        self.assertEqual(wht, 0.0)

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("หัก 3% บริการทั่วไป")
        self.assertTrue(has_exp)
        self.assertEqual(wht, 3.0)

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("หัก 1% ราชการ/AOT")
        self.assertTrue(has_exp)
        self.assertEqual(wht, 1.0)

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("โอนมัดจำมา 20,000")
        self.assertTrue(has_exp)
        self.assertEqual(dep, 20000.0)

        has_exp, wht, dep, trans = detect_explicit_payment_confirmation("เข้า 16,640")
        self.assertTrue(has_exp)
        self.assertEqual(trans, 16640.0)

    # --------------------------------------------------------------------------
    # 6. End-to-End Chat Flow: Turn 1 Gatekeeper -> Turn 2 Confirmations
    # --------------------------------------------------------------------------
    @patch("line_bot_server.find_document_by_no")
    def test_payment_gatekeeper_trigger_in_chat(self, mock_find):
        """Turn 1: User says payment trigger -> Gatekeeper triggers WITHOUT creating RE."""
        mock_find.return_value = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 48150.0,
            "net_total": 48150.0,
            "pre_vat": 45000.0,
            "vat_amount": 3150.0,
            "project_name": "งานโฆษณา"
        }
        session_id = "test_gatekeeper_session_001"
        resp = self.client.post("/api/test_chat", json={
            "message": "IV-202609-001 ลูกค้าจ่ายมาหมดแล้ว",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("แจ้งยืนยันยอดเงินรับชำระ", data["reply"])
        self.assertIn("48,150.00", data["reply"])
        self.assertIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        self.assertEqual(PENDING_PAYMENT_CONFIRMATIONS[session_id]["doc_no"], "IV-202609-001")

    @patch("line_bot_server.convert_document")
    def test_gatekeeper_button_options_in_chat(self, mock_convert):
        """Turn 2: Testing Button 1 (0%), Button 2 (3%), Button 3 (1%)."""
        session_id = "test_gatekeeper_turn2"
        mock_convert.return_value = {
            "status": "success",
            "doc_no": "RE-202609-001",
            "totals": {"net_total": 46800.0, "pre_vat": 45000.0}
        }

        # Sub-test 1: Button 2 (หัก 3%)
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 48150.0,
            "pre_vat": 45000.0,
            "vat_amount": 3150.0
        }
        resp = self.client.post("/api/test_chat", json={
            "message": "หัก 3% บริการทั่วไป",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        self.assertIn("RE-202609-001", resp.json()["reply"])
        mock_convert.assert_called_with("IV-202609-001", "receipt", overrides={
            "wht_rate": 3.0,
            "payment_status": "ชำระเงินแล้ว",
            "actual_payment_date": unittest.mock.ANY
        })

        # Sub-test 2: Button 1 (0% โอนเต็ม)
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 48150.0,
            "pre_vat": 45000.0
        }
        resp = self.client.post("/api/test_chat", json={
            "message": "โอนเต็ม (ไม่หักภาษี)",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        mock_convert.assert_called_with("IV-202609-001", "receipt", overrides={
            "wht_rate": 0.0,
            "payment_status": "ชำระเงินแล้ว",
            "actual_payment_date": unittest.mock.ANY
        })

        # Sub-test 3: Button 3 (1% AOT)
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 48150.0,
            "pre_vat": 45000.0
        }
        resp = self.client.post("/api/test_chat", json={
            "message": "หัก 1% ราชการ/AOT",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        mock_convert.assert_called_with("IV-202609-001", "receipt", overrides={
            "wht_rate": 1.0,
            "payment_status": "ชำระเงินแล้ว",
            "actual_payment_date": unittest.mock.ANY
        })

    @patch("line_bot_server.convert_document")
    def test_gatekeeper_deposit_turn2_in_chat(self, mock_convert):
        """Turn 2: User inputs 'มัดจำ 20,000' -> Issues (งวดที่ 1 เงินมัดจำ) receipt."""
        session_id = "test_gatekeeper_deposit"
        mock_convert.return_value = {
            "status": "success",
            "doc_no": "RE-202609-DEP",
            "totals": {"net_total": 20000.0, "pre_vat": 18691.59}
        }
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด",
            "gross_amount": 53500.0,
            "pre_vat": 50000.0,
            "project_name": "งานผลิตสื่อ"
        }
        resp = self.client.post("/api/test_chat", json={
            "message": "มัดจำ 20,000",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        self.assertIn("RE-202609-DEP", resp.json()["reply"])
        self.assertIn("งวดที่ 1 เงินมัดจำ", resp.json()["reply"])
        self.assertIn("18,691.59", resp.json()["reply"])
        self.assertIn("1,308.41", resp.json()["reply"])

    def test_gatekeeper_cancel_flow(self):
        """User can cancel pending gatekeeper safely."""
        session_id = "test_gatekeeper_cancel"
        PENDING_PAYMENT_CONFIRMATIONS[session_id] = {
            "doc_no": "IV-202609-001",
            "client_name": "บริษัท เอ็ม-คูล จำกัด"
        }
        resp = self.client.post("/api/test_chat", json={
            "message": "ยกเลิก",
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(session_id, PENDING_PAYMENT_CONFIRMATIONS)
        self.assertIn("ยกเลิกรายการ", resp.json()["reply"])


if __name__ == "__main__":
    unittest.main()
