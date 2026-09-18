#!/usr/bin/env python3
"""
================================================================================
Test Suite: Unified Google Sheets Document Updater & Gemini Agent Tool
================================================================================
Covers:
1. Tool Schema & Parameter Validation in GEMINI_AGENT_TOOL_DECLARATIONS
2. Backend update_sheet_document_data execution & offline simulation
3. Profit Share calculation: 10% of Pre-VAT 50,000 = 5,000 THB (and fixed/zero deductions)
4. Updates across document types (Receipts, Invoices, Quotations, Expenses)
5. Not found error handling for non-existent documents
6. LINE Flex Message Card validation (Schema compliance & styling)
7. End-to-end Chat Assistant API (/api/test_chat & agentic fallback)
================================================================================
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from unittest.mock import patch

from ghn168_sync_service import (
    update_sheet_document_data,
    read_sheet_data,
    search_sheet_documents,
    normalize_doc_no,
)
from line_bot_server import (
    app,
    GEMINI_AGENT_TOOL_DECLARATIONS,
    execute_agent_tool,
    build_document_update_flex_message,
    validate_line_flex_payload,
    is_update_document_request,
    PENDING_UPDATE_CONFIRMATIONS,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_env():
    PENDING_UPDATE_CONFIRMATIONS.clear()
    with patch("ghn168_sync_service.GAS_SCRIPT_URL", ""), \
         patch("line_bot_server.GAS_SCRIPT_URL", ""), \
         patch("line_bot_server.GEMINI_API_KEY", ""):
        yield
    PENDING_UPDATE_CONFIRMATIONS.clear()


def test_tool_declaration_schema():
    """Validates that update_sheet_document is properly declared in GEMINI_AGENT_TOOL_DECLARATIONS."""
    tool_names = [t["name"] for t in GEMINI_AGENT_TOOL_DECLARATIONS]
    assert "update_sheet_document" in tool_names, "update_sheet_document must be in GEMINI_AGENT_TOOL_DECLARATIONS"

    tool_decl = next(t for t in GEMINI_AGENT_TOOL_DECLARATIONS if t["name"] == "update_sheet_document")
    assert "description" in tool_decl and len(tool_decl["description"]) > 10
    
    params = tool_decl.get("parameters", {})
    assert params.get("type") == "OBJECT"
    props = params.get("properties", {})
    
    assert "doc_no" in props, "doc_no must be a defined property"
    assert props["doc_no"]["type"] == "STRING"
    assert "profit_share_info" in props, "profit_share_info must be a defined property"
    assert props["profit_share_info"]["type"] == "OBJECT"
    assert "payment_status" in props
    assert "actual_payment_date" in props
    assert "remarks" in props
    assert "receiving_bank" in props
    assert "doc_no" in params.get("required", []), "doc_no must be required"


def test_profit_share_10_percent_calculation():
    """
    Tests calculating 10% profit share on 50,000 THB Pre-VAT base amount (RE2608-587).
    10% of 50,000 = 5,000.00 THB.
    """
    res = update_sheet_document_data(
        doc_no="RE2608-587",
        updates={
            "profit_share_info": {
                "worker_name": "หอม",
                "deduction_type": "percent",
                "deduction_value": 10
            },
            "payment_status": "ชำระเงินแล้ว",
            "actual_payment_date": "28/08/2026",
            "receiving_bank": "KTB",
            "remarks": "ผลิต VTR AOT เรียบร้อย"
        }
    )

    assert res.get("status") in ["success", "simulation"]
    assert normalize_doc_no(res.get("doc_no")) in ["RE2608-587", "RE-202608-563"]
    assert res.get("pre_vat") == 50000.0
    
    updated_fields = res.get("updated_fields", {})
    assert "คนทำงาน: หอม" in updated_fields.get("profit_share", "")
    assert "10%" in updated_fields.get("profit_share", "")
    assert "฿5,000.00" in updated_fields.get("profit_share", "")
    assert updated_fields.get("profit_share_amount") == 5000.0
    assert updated_fields.get("payment_status") == "ชำระเงินแล้ว"
    assert updated_fields.get("actual_payment_date") == "28/08/2026"
    assert updated_fields.get("receiving_bank") == "KTB"
    assert updated_fields.get("remarks") == "ผลิต VTR AOT เรียบร้อย"


def test_profit_share_fixed_and_zero_deductions():
    """Tests fixed amount deduction (1,000 THB) and zero deduction."""
    # 1. Fixed amount deduction
    res_fixed = update_sheet_document_data(
        doc_no="หอม-RE2608-587",
        updates={
            "profit_share_info": {
                "worker_name": "หอม",
                "deduction_type": "fixed",
                "deduction_value": 1000
            }
        }
    )
    assert res_fixed.get("status") in ["success", "simulation"]
    ps_fixed = res_fixed.get("updated_fields", {}).get("profit_share", "")
    assert "คนทำงาน: หอม | หัก บ.: หอม ฿1,000.00" in ps_fixed
    assert res_fixed.get("updated_fields", {}).get("profit_share_amount") == 1000.0

    # 2. Zero deduction
    res_zero = update_sheet_document_data(
        doc_no="RE2608-587",
        updates={
            "profit_share_info": {
                "worker_name": "หอม",
                "deduction_type": "percent",
                "deduction_value": 0
            }
        }
    )
    assert res_zero.get("status") in ["success", "simulation"]
    ps_zero = res_zero.get("updated_fields", {}).get("profit_share", "")
    assert "ไม่มีการหักเข้า บ." in ps_zero


def test_update_invoice_document():
    """Tests updating an Invoice in 'ใบวางบิล' tab."""
    res = update_sheet_document_data(
        doc_no="IV2608-004",
        updates={
            "payment_terms": "เครดิต 30 วัน",
            "due_date": "15/09/2026",
            "remarks": "ลูกค้ารับวางบิลแล้ว ส่งแมสเซนเจอร์รับเช็ค"
        }
    )
    assert res.get("status") in ["success", "simulation"]
    assert res.get("sheet_name") == "ใบวางบิล"
    assert res.get("pre_vat") == 80000.0
    assert res.get("updated_fields", {}).get("payment_terms") == "เครดิต 30 วัน"
    assert res.get("updated_fields", {}).get("due_date") == "15/09/2026"
    assert res.get("updated_fields", {}).get("remarks") == "ลูกค้ารับวางบิลแล้ว ส่งแมสเซนเจอร์รับเช็ค"


def test_update_quotation_document():
    """Tests updating a Quotation in 'ใบเสนอราคา' tab."""
    res = update_sheet_document_data(
        doc_no="QT2608-001",
        updates={
            "remarks": "ลูกค้ายืนยันราคาแล้ว รอออกใบวางบิล"
        }
    )
    assert res.get("status") in ["success", "simulation"]
    assert res.get("sheet_name") == "ใบเสนอราคา"
    assert res.get("pre_vat") == 50000.0
    assert res.get("updated_fields", {}).get("remarks") == "ลูกค้ายืนยันราคาแล้ว รอออกใบวางบิล"


def test_not_found_error_handling():
    """Tests safe error handling when updating a non-existent document."""
    res = update_sheet_document_data(
        doc_no="RE9999-999",
        updates={"remarks": "ทดสอบ"}
    )
    assert res.get("status") == "not_found"
    assert "ไม่พบเอกสาร" in res.get("message", "")


def test_execute_agent_tool_update_sheet_document():
    """Tests execute_agent_tool for 'update_sheet_document' with Flex card generation."""
    tool_args = {
        "doc_no": "RE2608-587",
        "profit_share_info": {
            "worker_name": "หอม",
            "deduction_type": "percent",
            "deduction_value": 10
        },
        "payment_status": "ชำระเงินแล้ว",
        "actual_payment_date": "28/08/2026",
        "receiving_bank": "KTB",
        "remarks": "งาน VTR AOT สำเร็จ"
    }

    result, flex_card = execute_agent_tool("update_sheet_document", tool_args, session_id="test_update_session")
    assert result.get("status") in ["success", "simulation"]
    assert result.get("pre_vat") == 50000.0
    assert result.get("updated_fields", {}).get("profit_share_amount") == 5000.0
    
    # Validate Flex Message Card
    assert flex_card is not None
    assert flex_card.get("type") == "flex"
    assert validate_line_flex_payload(flex_card) is True
    
    # Check Flex content properties
    bubble = flex_card.get("contents", {})
    assert bubble.get("header", {}).get("backgroundColor") == "#059669"
    header_texts = [c.get("text", "") for c in bubble.get("header", {}).get("contents", [])]
    assert any("อัปเดตข้อมูลเอกสารสำเร็จ" in t for t in header_texts)
    assert any("RE2608-587" in t for t in header_texts)


def test_execute_agent_tool_not_found():
    """Tests execute_agent_tool when document is not found."""
    result, flex_card = execute_agent_tool("update_sheet_document", {"doc_no": "NONEXISTENT-999"}, session_id="test_update_session")
    assert result.get("status") == "not_found"
    assert flex_card is None
    assert "ไม่พบเอกสาร" in result.get("message", "")


def test_is_update_document_request_detector():
    """Tests the natural language detector for document update requests."""
    text1 = "@เลขาเฟิส ช่วยอัปเดต profit share บิล RE2608-587 หักหอม 10% ให้หน่อย"
    is_upd1, args1 = is_update_document_request(text1)
    assert is_upd1 is True
    assert args1.get("doc_no") == "RE2608-587"
    assert args1.get("profit_share_info", {}).get("worker_name") == "หอม"
    assert args1.get("profit_share_info", {}).get("deduction_value") == 10.0

    text2 = "อัปเดตสถานะบิล IV2608-004 เป็นชำระเงินแล้ว ธนาคาร KTB วันที่ 28/08/2026 หมายเหตุ: จ่ายงวด 1 แล้ว"
    is_upd2, args2 = is_update_document_request(text2)
    assert is_upd2 is True
    assert args2.get("doc_no") == "IV2608-004"
    assert args2.get("payment_status") == "ชำระเงินแล้ว"
    assert args2.get("receiving_bank") == "KTB"
    assert args2.get("actual_payment_date") == "28/08/2026"
    assert args2.get("remarks") == "จ่ายงวด 1 แล้ว"


def test_api_test_chat_update_sheet_document():
    """Tests API endpoint /api/test_chat executing update_sheet_document via agentic flow."""
    payload = {
        "message": "@เลขาเฟิส ช่วยอัปเดตสัดส่วน profit share บิล RE2608-587 หักหอม 10% ให้หน่อยค่ะ",
        "session_id": "test_agentic_update_session"
    }
    resp = client.post("/api/test_chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data.get("is_update_document") is True
    upd = data.get("update_result", {})
    assert upd.get("status") in ["success", "simulation", "pending_confirmation"]
    assert normalize_doc_no(upd.get("doc_no")) == "RE2608-587"
    assert upd.get("updated_fields", {}).get("profit_share_amount") == 5000.0
    
    # Must return Flex cards (Safety Confirmation Preview card)
    flex_cards = data.get("flex_cards", [])
    assert len(flex_cards) > 0
    assert validate_line_flex_payload(flex_cards[0]) is True

    # Step 2: Confirm Update
    confirm_payload = {
        "message": "ยืนยันอัปเดต RE2608-587",
        "session_id": "test_agentic_update_session"
    }
    confirm_resp = client.post("/api/test_chat", json=confirm_payload)
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data.get("is_update_document") is True
    assert confirm_data.get("update_result", {}).get("status") in ["success", "simulation"]
