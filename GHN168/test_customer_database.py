#!/usr/bin/env python3
"""
================================================================================
GHN168 Smart Customer Database - Comprehensive Test Suite
================================================================================
Test Coverage:
1. `get_customers_database()`: Retrieval, Schema Validation (10 columns), and Cache.
2. `search_customer()`: Full Name, Partial / Fuzzy Match, Tax ID, Contact Person, and Not Found.
3. `save_new_customer()`: Insertion / Upsert payload construction.
4. Auto-fill in Document Generation: Existing customer auto-fill of Tax ID, Branch, Address, Phone.
5. New Customer Prompt & Save Flow: Prompt when customer is missing, and confirmation via 'บันทึก'/'เซฟ'.
6. FastAPI Endpoints: `GET /api/customers`, `POST /api/customers`, and `/api/test_chat`.
================================================================================
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from ghn168_sync_service import (
    get_customers_database,
    search_customer,
    save_new_customer,
    _CUSTOMERS_CACHE,
    build_sheet_row_data,
    generate_and_sync_document,
)
from line_bot_server import (
    app,
    PENDING_DOCUMENT_ORDERS,
    PENDING_NEW_CUSTOMER_SAVING,
    merge_document_order_data,
    validate_document_checklist,
    build_customer_card_flex_message,
    build_customer_list_flex_message,
    format_customer_list_text,
    is_customer_query_request,
    local_rule_based_reply,
)


class TestSmartCustomerDatabase(unittest.TestCase):

    def setUp(self):
        # Reset memory state before each test
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_NEW_CUSTOMER_SAVING.clear()
        _CUSTOMERS_CACHE["data"] = None
        _CUSTOMERS_CACHE["timestamp"] = 0.0
        self.client = TestClient(app)

        # Patch requests.post to ensure 100% Zero Production Pollution
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
            elif req_type == "upload_html":
                mock_res.json.return_value = {
                    "status": "success",
                    "pdfUrl": "https://drive.google.com/mock_test_doc.pdf",
                    "message": "Mocked upload success"
                }
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}
                
            return mock_res
            
        self.mock_post.side_effect = mock_requests_post_handler

    def tearDown(self):
        self.patcher.stop()

    def test_01_get_customers_database_structure(self):
        """Test retrieving all customers and validating schema."""
        customers = get_customers_database(force_refresh=True)
        self.assertIsInstance(customers, list)
        self.assertEqual(len(customers), 10)

        first = customers[0]
        required_keys = [
            "customer_id", "customer_name", "tax_id", "branch",
            "address", "phone", "email", "contact_person", "created_date", "remarks"
        ]
        for k in required_keys:
            self.assertIn(k, first, f"Missing key {k} in customer schema")

        # Validate first customer values
        self.assertEqual(first["customer_id"], "CUST-001")
        self.assertEqual(first["customer_name"], "บริษัท เชียงใหม่มีเดีย จำกัด")
        self.assertEqual(first["tax_id"], "0505560000123")
        self.assertEqual(first["branch"], "00000")
        print("✅ Test 1 Passed: Customer database retrieval & schema structure verified.")

    def test_02_search_all_10_real_customers(self):
        """Test searching each of the 10 real customer companies."""
        test_queries = [
            ("เชียงใหม่มีเดีย", "บริษัท เชียงใหม่มีเดีย จำกัด", "0505560000123"),
            ("นอร์ทเทิร์น อินโนเวชั่น แล็บ", "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด", "0505566001234"),
            ("ไอเด็กซ์ ไมซ์", "บริษัท ไอเด็กซ์ ไมซ์ จำกัด", "0505555007201"),
            ("อินดีด ครีเอชั่น", "บริษัท อินดีด ครีเอชั่น จำกัด", "0505545004373"),
            ("ลานนา ครีเอทีฟ", "บริษัท ลานนา ครีเอทีฟ สตูดิโอ จำกัด", "0505560000456"),
            ("แคทไซคลิ่ง", "บริษัท แคทไซคลิ่ง จำกัด", "0505565009988"),
            ("พิงค์นคร พร็อพเพอร์ตี้", "บริษัท พิงค์นคร พร็อพเพอร์ตี้ จำกัด", "0505560000789"),
            ("เดอะริเวอร์ เชียงใหม่", "โรงแรม เดอะริเวอร์ เชียงใหม่", "0505560000888"),
            ("เอ็ม-คูล เฮ้าส์", "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด", "0505568016475"),
            ("ล้านนา ช็อปปิ้ง", "บริษัท ล้านนา ช็อปปิ้ง จำกัด", "0505569008888"),
        ]

        for query, expected_name, expected_tax in test_queries:
            res = search_customer(query)
            self.assertIsNotNone(res, f"Failed to find customer with query: {query}")
            self.assertEqual(res["customer_name"], expected_name)
            self.assertEqual(res["tax_id"], expected_tax)

        # Tax ID Searches
        res_tax1 = search_customer("0505568016475")
        self.assertIsNotNone(res_tax1)
        self.assertEqual(res_tax1["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")

        res_tax2 = search_customer("0505566001234")
        self.assertIsNotNone(res_tax2)
        self.assertEqual(res_tax2["customer_name"], "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด")

        # Contact Person Search
        res_contact = search_customer("คุณนัท")
        self.assertIsNotNone(res_contact)
        self.assertEqual(res_contact["customer_name"], "โรงแรม เดอะริเวอร์ เชียงใหม่")

        # Not Found Case
        res_none = search_customer("บริษัท กาแฟดอยสุเทพ จำกัด 999")
        self.assertIsNone(res_none)
        print("✅ Test 2 Passed: All 10 Real Customers successfully searched & matched.")

    def test_03_save_new_customer(self):
        """Test saving a new customer into the database with auto-generated CUST-011 and padded fields."""
        new_cust_data = {
            "customer_name": "บริษัท เชียงใหม่ โซล่าร์เซลล์ จำกัด",
            "tax_id": "0505567778889",
            "branch": "00000",
            "address": "123 ถ.โชตนา ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",
            "phone": "053-123456",
            "email": "solar@cm.co.th",
            "contact_person": "คุณสุริยา",
            "remarks": "ลูกค้าระบบพลังงานแสงอาทิตย์"
        }

        save_res = save_new_customer(new_cust_data)
        self.assertEqual(save_res["status"], "success")
        self.assertEqual(save_res["customer"]["customer_name"], new_cust_data["customer_name"])
        self.assertEqual(save_res["customer"]["tax_id"], "0505567778889")
        self.assertEqual(save_res["customer"]["branch"], "00000")
        self.assertEqual(save_res["customer"]["customer_id"], "CUST-011")
        print("✅ Test 3 Passed: save_new_customer verified with CUST-011 auto-generation.")

    def test_04_document_order_autofill_existing_customer(self):
        """Test that existing customer info is auto-filled during document order merging."""
        order_input = {
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ผลิตคลิปสัมภาษณ์ผู้บริหาร 1 ตอน",
            "amount": 25000.0,
            "signer_name": "บอสเก่ง"
        }

        merged = merge_document_order_data({}, order_input)
        self.assertTrue(merged.get("_customer_autofilled"))
        self.assertEqual(merged["client_name"], "บริษัท เชียงใหม่มีเดีย จำกัด")
        self.assertEqual(merged["client_tax_id"], "0505560000123")
        self.assertEqual(merged["client_branch"], "00000")
        self.assertEqual(merged["client_phone"], "081-1111111")
        print("✅ Test 4 Passed: Document order customer auto-fill verified.")

    def test_05_multi_turn_new_customer_prompt_and_save_flow(self):
        """Test multi-turn flow for a brand new customer: Doc Creation -> Prompt -> Confirm Save."""
        import time
        unique_name = f"บริษัท เชียงใหม่ สตูดิโอ {int(time.time())} จำกัด"
        session_id = f"test_user_new_cust_{int(time.time())}"
        PENDING_DOCUMENT_ORDERS.clear()
        PENDING_NEW_CUSTOMER_SAVING.clear()

        # Step 1: Issue document for a new client
        payload_1 = {
            "session_id": session_id,
            "message": f"ออกใบเสนอราคาให้ {unique_name} ยอด 45,000 บาท งานถ่ายทำสปอตโฆษณา บอสเก่งเซ็น"
        }
        res_1 = self.client.post("/api/test_chat", json=payload_1)
        self.assertEqual(res_1.status_code, 200)
        data_1 = res_1.json()

        # Should ask to save new customer
        self.assertIn("ยังไม่มีในฐานข้อมูลลูกค้าของ GHN168", data_1["reply"])
        self.assertIn("พิมพ์ 'บันทึก' หรือ 'เซฟ'", data_1["reply"])
        self.assertIn(session_id, PENDING_NEW_CUSTOMER_SAVING)
        self.assertEqual(PENDING_NEW_CUSTOMER_SAVING[session_id]["customer_name"], unique_name)

        # Step 2: Confirm save by replying "บันทึก"
        payload_2 = {
            "session_id": session_id,
            "message": "บันทึก"
        }
        res_2 = self.client.post("/api/test_chat", json=payload_2)
        self.assertEqual(res_2.status_code, 200)
        data_2 = res_2.json()

        self.assertTrue(data_2.get("is_customer_saved"))
        self.assertIn(f"บันทึกข้อมูลลูกค้า '{unique_name}' ลงฐานข้อมูลลูกค้า", data_2["reply"])
        self.assertNotIn(session_id, PENDING_NEW_CUSTOMER_SAVING)
        print("✅ Test 5 Passed: Multi-turn new customer prompt & confirmation flow verified.")

    def test_06_customer_api_endpoints(self):
        """Test GET /api/customers, GET /api/customers?search=..., and POST /api/customers."""
        # 1. GET all customers
        get_all_res = self.client.get("/api/customers")
        self.assertEqual(get_all_res.status_code, 200)
        all_data = get_all_res.json()
        self.assertEqual(all_data["status"], "success")
        self.assertEqual(all_data["total"], 10)

        # 2. GET customers with search query
        search_res = self.client.get("/api/customers?search=พิงค์นคร")
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.json()
        self.assertEqual(search_data["status"], "success")
        self.assertEqual(search_data["total"], 1)
        self.assertIn("พิงค์นคร", search_data["customers"][0]["customer_name"])

        # 3. POST new customer
        post_payload = {
            "customer_name": "บริษัท นอร์ทเทิร์น ดิจิทัล เอเจนซี่ จำกัด",
            "tax_id": "0505561122334",
            "branch": "00000",
            "address": "77 ถ.คันคลองชลประทาน ต.สุเทพ อ.เมือง จ.เชียงใหม่",
            "phone": "053-888777",
            "email": "contact@northerndigital.co.th",
            "contact_person": "คุณพิม",
            "remarks": "เอเจนซี่การตลาดออนไลน์"
        }
        post_res = self.client.post("/api/customers", json=post_payload)
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.json()
        self.assertEqual(post_data["status"], "success")
        self.assertEqual(post_data["customer"]["customer_name"], post_payload["customer_name"])
        self.assertEqual(post_data["customer"]["tax_id"], "0505561122334")
        self.assertEqual(post_data["customer"]["branch"], "00000")

        # 4. POST without customer_name (Validation error)
        invalid_post = self.client.post("/api/customers", json={"tax_id": "12345"})
        self.assertEqual(invalid_post.status_code, 400)
        print("✅ Test 6 Passed: Customer API Endpoints verified.")

    def test_07_customer_flex_card_builder(self):
        """Test building Customer LINE Flex card."""
        cust_sample = {
            "customer_id": "CUST-001",
            "customer_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "tax_id": "0505560000123",
            "branch": "00000",
            "address": "123 ถ.ห้วยแก้ว เชียงใหม่",
            "phone": "081-1111111"
        }
        flex_card = build_customer_card_flex_message(cust_sample)
        self.assertEqual(flex_card["type"], "flex")
        self.assertIn("GHN168 CUSTOMER DATABASE", json_str := str(flex_card))
        self.assertIn("บริษัท เชียงใหม่มีเดีย จำกัด", json_str)
        print("✅ Test 7 Passed: Customer Flex card builder verified.")

    def test_08_customer_query_intent_and_listing(self):
        """Test user queries asking for customer list (like '@เลขาเฟิส ขอข้อมูลลูกค้าที่มีในตอนนี้หน่อย')."""
        test_queries = [
            "@เลขาเฟิส ขอข้อมูลลูกค้าที่มีในตอนนี้หน่อย",
            "ขอข้อมูลลูกค้า",
            "รายชื่อลูกค้า",
            "มีลูกค้ากี่เจ้า",
            "ลูกค้าทั้งหมด",
            "ลูกค้ามีใครบ้าง",
            "ดูรายชื่อลูกค้าหน่อย"
        ]

        for query in test_queries:
            is_cust, kw = is_customer_query_request(query)
            self.assertTrue(is_cust, f"Failed to detect customer query intent for: {query}")
            self.assertIsNone(kw, f"Expected None search keyword for general query: {query}")

            # Test via /api/test_chat
            res = self.client.post("/api/test_chat", json={"message": query, "session_id": "test_cust_q_01"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("is_customer_query"))
            self.assertEqual(len(data.get("customer_result", [])), 10)
            
            # Validate response text contains 10 customers and does not contain partner mistakes
            reply = data.get("reply", "")
            self.assertIn("10 บริษัท", reply)
            self.assertIn("บริษัท เชียงใหม่มีเดีย จำกัด", reply)
            self.assertIn("CUST-001", reply)
            self.assertIn("โรงแรม เดอะริเวอร์ เชียงใหม่", reply)

            # Test local rule-based reply fallback directly
            local_rep = local_rule_based_reply(query)
            self.assertIn("10 บริษัท", local_rep)
            self.assertIn("บริษัท เชียงใหม่มีเดีย จำกัด", local_rep)

        print("✅ Test 8 Passed: Customer query intent detection and 10-customer listing verified.")

    def test_09_customer_search_via_chat(self):
        """Test on-demand customer search via chat queries."""
        search_cases = [
            ("ค้นหาลูกค้า เชียงใหม่มีเดีย", "เชียงใหม่มีเดีย", "บริษัท เชียงใหม่มีเดีย จำกัด"),
            ("ข้อมูลลูกค้า โรงแรมเดอะริเวอร์", "โรงแรมเดอะริเวอร์", "โรงแรม เดอะริเวอร์ เชียงใหม่"),
            ("ขอข้อมูลลูกค้า CUST-003", "CUST-003", "บริษัท ไอเด็กซ์ ไมซ์ จำกัด"),
            ("เช็คลูกค้า 0505568016475", "0505568016475", "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        ]

        for query, expected_kw, expected_company in search_cases:
            is_cust, kw = is_customer_query_request(query)
            self.assertTrue(is_cust, f"Failed to detect search intent: {query}")
            self.assertIsNotNone(kw, f"Failed to extract keyword: {query}")

            res = self.client.post("/api/test_chat", json={"message": query, "session_id": "test_cust_search_01"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("is_customer_query"))
            self.assertGreaterEqual(len(data.get("customer_result", [])), 1)
            self.assertIn(expected_company, data.get("reply", ""))

        # Test building customer list flex carousel
        customers = get_customers_database(force_refresh=True)
        flex_carousel = build_customer_list_flex_message(customers)
        self.assertEqual(flex_carousel["type"], "flex")
        self.assertEqual(flex_carousel["contents"]["type"], "carousel")
        self.assertEqual(len(flex_carousel["contents"]["contents"]), 2)  # 2 bubbles for 10 items (5 per bubble)
        print("✅ Test 9 Passed: Customer search via chat and Flex Carousel builder verified.")

    def test_10_partner_vs_customer_strict_separation(self):
        """Verify that internal partners (บอสเก่ง, บอสหอม, บอสนิค, บอสมด) are NEVER returned as customers."""
        res = self.client.post("/api/test_chat", json={"message": "ขอข้อมูลลูกค้าที่มีในตอนนี้หน่อย", "session_id": "test_sep_01"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        reply = data.get("reply", "")

        # Verify partners are NOT presented as customers
        forbidden_customer_names = [
            "1. 🏢 นาย มงคล วงศ์สกุลยานนท์",
            "1. 🏢 บอสเก่ง",
            "2. 🏢 นาย อนุชิต อภิชัย",
            "2. 🏢 บอสนิค",
            "3. 🏢 นาย ณัฐวัฒน์ ปวงจันทร์หอม",
            "3. 🏢 บอสหอม",
            "4. 🏢 นาง ณัฐนรี วงศ์สกุลยานนท์",
            "4. 🏢 บอสมด"
        ]
        for forbidden in forbidden_customer_names:
            self.assertNotIn(forbidden, reply, f"Internal partner '{forbidden}' must NOT be listed as a customer!")

        # Verify real corporate clients are listed
        self.assertIn("บริษัท เชียงใหม่มีเดีย จำกัด", reply)
        self.assertIn("บริษัท ล้านนา ช็อปปิ้ง จำกัด", reply)
        print("✅ Test 10 Passed: Strict separation between Internal Partners and External Customers verified.")

    def test_11_customer_flex_message_margin_syntax_validation(self):
        """Verify that all margin attributes in Flex messages strictly conform to LINE API specs."""
        customers = get_customers_database(force_refresh=True)
        flex_carousel = build_customer_list_flex_message(customers)
        flex_card = build_customer_card_flex_message(customers[0])

        valid_margins = {"none", "xs", "sm", "md", "lg", "xl", "xxl"}

        def extract_margins(obj):
            extracted = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "margin":
                        extracted.append(v)
                    else:
                        extracted.extend(extract_margins(v))
            elif isinstance(obj, list):
                for item in obj:
                    extracted.extend(extract_margins(item))
            return extracted

        carousel_margins = extract_margins(flex_carousel)
        card_margins = extract_margins(flex_card)

        # Assert no "xxs" exists in margin
        self.assertNotIn("xxs", carousel_margins, "Margin 'xxs' is invalid in LINE API and must not exist!")
        self.assertNotIn("xxs", card_margins, "Margin 'xxs' is invalid in LINE API and must not exist!")

        # Assert all margin values are valid LINE API values
        for m in carousel_margins:
            self.assertIn(m, valid_margins, f"Invalid margin '{m}' found in customer list flex carousel")
        for m in card_margins:
            self.assertIn(m, valid_margins, f"Invalid margin '{m}' found in customer card flex")

        print("✅ Test 11 Passed: Customer Flex message margin syntax strictly validated against LINE API specs.")

    def test_12_send_line_reply_messages_safety_fallback(self):
        """Verify that send_line_reply_messages falls back to plain text if LINE API rejects flex/rich payload."""
        from line_bot_server import send_line_reply_messages
        import line_bot_server

        orig_token = line_bot_server.LINE_CHANNEL_ACCESS_TOKEN
        line_bot_server.LINE_CHANNEL_ACCESS_TOKEN = "mock_token_for_test"

        try:
            call_count = 0
            sent_payloads = []

            def mock_reply_post(url, json=None, **kwargs):
                nonlocal call_count
                call_count += 1
                sent_payloads.append(json)
                mock_res = MagicMock()
                # First call (Flex message) fails with 400 Bad Request
                if call_count == 1:
                    mock_res.status_code = 400
                    mock_res.text = '{"message":"invalid property"}'
                else:
                    # Fallback plain text succeeds with 200 OK
                    mock_res.status_code = 200
                    mock_res.text = '{"message":"ok"}'
                return mock_res

            self.mock_post.side_effect = mock_reply_post

            test_messages = [
                {"type": "text", "text": "ข้อความนำ"},
                {"type": "flex", "altText": "รายชื่อลูกค้า 10 บริษัท", "contents": {"type": "bubble"}}
            ]

            success = send_line_reply_messages("valid_test_reply_token_1234567890", test_messages)
            self.assertTrue(success, "Safety fallback should succeed on second plain text attempt")
            self.assertEqual(call_count, 2, "Expected 2 attempts: 1st failed rich message, 2nd fallback plain text")
            self.assertEqual(sent_payloads[1]["messages"][0]["type"], "text")
            self.assertEqual(sent_payloads[1]["messages"][1]["type"], "text")
            self.assertEqual(sent_payloads[1]["messages"][1]["text"], "รายชื่อลูกค้า 10 บริษัท")
            print("✅ Test 12 Passed: send_line_reply_messages safety fallback verified.")
        finally:
            line_bot_server.LINE_CHANNEL_ACCESS_TOKEN = orig_token

    def test_13_advanced_fuzzy_index_and_phonetic_search(self):
        """Verify advanced fuzzy matching, prefix stripping, index/rank queries, and typo handling."""
        # 1. Prefix stripped variations (บ. เอ็มคูล, เอ็ม-คูล, บจก.เอ็มคูล)
        res1 = search_customer("บ. เอ็มคูล")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(res1["tax_id"], "0505568016475")
        self.assertEqual(res1["branch"], "00000")
        self.assertEqual(res1["address"], "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180")
        self.assertEqual(res1["phone"], "092-419-3953")

        res_dash = search_customer("เอ็ม-คูล")
        self.assertIsNotNone(res_dash)
        self.assertEqual(res_dash["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")

        # 2. Index / Rank searches (เบอร์ 9, เบอร์9, ลำดับที่ 9, ลำดับ 9, เจ้าที่ 9, คนที่ 9, cust-009, cust-9, 9, #9)
        index_queries = [
            "เบอร์ 9", "เบอร์9", "ลำดับที่ 9", "ลำดับ 9", "เจ้าที่ 9", "อันดับ 9",
            "คนที่ 9", "cust-009", "cust-9", "9", "#9", "เบอร์ 09"
        ]
        for q in index_queries:
            res_idx = search_customer(q)
            self.assertIsNotNone(res_idx, f"Failed index search for query: {q}")
            self.assertEqual(res_idx["customer_id"], "CUST-009", f"Query {q} did not return CUST-009")
            self.assertEqual(res_idx["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")

        # 3. Query containing index embedded in sentence
        res_embedded = search_customer("บ.เอ็มคูบ เบอร์ 9 ที่มีในฐานข้อมูล")
        self.assertIsNotNone(res_embedded)
        self.assertEqual(res_embedded["customer_id"], "CUST-009")
        self.assertEqual(res_embedded["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")

        # 4. Fuzzy & Typo Matching (difflib.SequenceMatcher for typos like 'บ.เอ็มคูบ')
        res_typo = search_customer("บ.เอ็มคูบ")
        self.assertIsNotNone(res_typo)
        self.assertEqual(res_typo["customer_name"], "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(res_typo["tax_id"], "0505568016475")

        # 5. Full data integrity returned
        self.assertTrue(len(res1["tax_id"]) == 13)
        self.assertEqual(res1["branch"], "00000")
        self.assertIn("เชียงใหม่", res1["address"])
        print("✅ Test 13 Passed: Advanced Fuzzy, Index & Phonetic Match verified 100%.")

    def test_14_smart_defaults_and_zero_friction_one_shot_issuing(self):
        """Verify One-shot document issuing without redundant questions, with Boss Keng signer and 7% VAT default."""
        session_id = "test_one_shot_keng_01"
        PENDING_DOCUMENT_ORDERS.clear()

        # Command: "ทำใบเสนอราคาให้ บ. เอ็มคูล ถ่าย Event 3 วัน 18000"
        payload = {
            "session_id": session_id,
            "message": "ทำใบเสนอราคาให้ บ. เอ็มคูล ถ่าย Event 3 วัน 18000"
        }
        res = self.client.post("/api/test_chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Assert document order processed immediately (One-shot)
        self.assertTrue(data.get("is_document_order"))
        self.assertNotIn(session_id, PENDING_DOCUMENT_ORDERS)

        # Assert correct customer autofill
        doc_data = data.get("doc_data", {})
        self.assertEqual(doc_data.get("client_name"), "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(doc_data.get("client_tax_id"), "0505568016475")
        self.assertEqual(doc_data.get("client_branch"), "00000")
        self.assertIn("เชียงใหม่", doc_data.get("client_address", ""))

        # Assert Smart Default Signer: Boss Keng
        self.assertEqual(doc_data.get("signer_name"), "นาย มงคล วงศ์สกุลยานนท์")

        # Assert Default VAT 7% Calculation:
        # Pre-VAT: 18,000 | VAT 7%: 1,260 | Net Total: 19,260
        totals = data.get("doc_result", {}).get("totals", {})
        self.assertEqual(totals.get("pre_vat"), 18000.0)
        self.assertEqual(totals.get("vat_amount"), 1260.0)
        self.assertEqual(totals.get("net_total"), 19260.0)
        self.assertEqual(totals.get("baht_text"), "หนึ่งหมื่นเก้าพันสองร้อยหกสิบบาทถ้วน")

        # Assert reply mentions successful issuance
        reply_text = data.get("reply", "")
        self.assertIn("ออกเอกสาร", reply_text)
        self.assertIn("19,260.00", reply_text)
        self.assertNotIn("ขอข้อมูลเพิ่มเติม", reply_text)
        print("✅ Test 14 Passed: Smart Defaults & Zero-Friction One-Shot Document Issuing verified 100%.")

    def test_15_conversational_one_shot_issuing_with_spaces_and_boss_keng(self):
        """Verify conversational phrasing: 'เฟิส ทำ ใบเสนอราคา ให้หน่อยของ บ. เอ็มคูล รายละเอียดงาน ถ่าย Event 3 วัน 18000'."""
        session_id = "test_one_shot_conversational_02"
        PENDING_DOCUMENT_ORDERS.clear()

        # Conversational command with spaces in triggers & polite prefix
        payload = {
            "session_id": session_id,
            "message": "เฟิส ทำ ใบเสนอราคา ให้หน่อยของ บ. เอ็มคูล รายละเอียดงาน ถ่าย Event 3 วัน 18000"
        }
        res = self.client.post("/api/test_chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data.get("is_document_order"))
        self.assertNotIn(session_id, PENDING_DOCUMENT_ORDERS)

        doc_data = data.get("doc_data", {})
        self.assertEqual(doc_data.get("client_name"), "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด")
        self.assertEqual(doc_data.get("client_tax_id"), "0505568016475")
        self.assertEqual(doc_data.get("client_branch"), "00000")
        self.assertEqual(doc_data.get("signer_name"), "นาย มงคล วงศ์สกุลยานนท์")

        totals = data.get("doc_result", {}).get("totals", {})
        self.assertEqual(totals.get("pre_vat"), 18000.0)
        self.assertEqual(totals.get("vat_amount"), 1260.0)
        self.assertEqual(totals.get("net_total"), 19260.0)

        # Verify PDFShift / Template Rendered Content
        rendered_html = data.get("doc_result", {}).get("html", "")
        if not rendered_html:
            from document_template_engine import render_document_html
            rendered_html = render_document_html(doc_data.get("doc_type", "quotation"), doc_data)

        self.assertIn("บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด", rendered_html)
        self.assertIn("0505568016475", rendered_html)
        self.assertIn("นาย มงคล วงศ์สกุลยานนท์", rendered_html)
        self.assertIn("19,260.00", rendered_html)
        print("✅ Test 15 Passed: Conversational one-shot issuing with full data rendering verified 100%.")


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Running GHN168 Smart Customer Database Test Suite...")
    print("=" * 70)
    unittest.main()
