import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from document_template_engine import render_invoice_html, render_quotation_html, render_document_html
from ghn168_sync_service import build_sheet_row_data, convert_document
from line_bot_server import (
    GEMINI_AGENT_TOOL_DECLARATIONS,
    execute_agent_tool,
    should_reply_to_event,
    download_line_file_content,
    local_rule_based_extract_document,
    merge_document_order_data,
    SESSION_LAST_FILE,
)


class TestDocumentTemplateEnginePOAndJobCode:
    """Test PO number, Job Code, and automatic 30-day invoice due date in document templates."""

    def test_invoice_with_po_and_job_code(self):
        data = {
            "doc_no": "IV-202609-001",
            "doc_date": "10/09/2026",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ผลิตวิดีโอโปรโมทบริษัท",
            "amount": 50000.0,
            "po_number": "PO-2026-089",
            "job_code": "JB-MKT-04",
        }
        html = render_invoice_html(data)

        # Must contain PO No and Job Code in meta table
        assert "เลขที่ใบสั่งซื้อ / P.O. No.:" in html
        assert "PO-2026-089" in html
        assert "รหัสโครงการ / Job Code:" in html
        assert "JB-MKT-04" in html

        # Auto due date for invoice without explicit due_date must be doc_date + 30 days
        expected_due = (datetime.strptime("10/09/2026", "%d/%m/%Y") + timedelta(days=30)).strftime("%d/%m/%Y")
        assert expected_due in html

    def test_invoice_without_po_and_job_code(self):
        data = {
            "doc_no": "IV-202609-002",
            "doc_date": "10/09/2026",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "project_name": "งานบริการทั่วไป",
            "amount": 10000.0,
            "po_number": "",
            "job_code": "-",
        }
        html = render_invoice_html(data)

        # Must omit rows completely (0 blank lines, 0 empty dashes)
        assert "เลขที่ใบสั่งซื้อ / P.O. No.:" not in html
        assert "รหัสโครงการ / Job Code:" not in html

    def test_invoice_explicit_due_date_preserved(self):
        data = {
            "doc_no": "IV-202609-003",
            "doc_date": "10/09/2026",
            "due_date": "25/09/2026",
            "client_name": "ลูกค้าทั่วไป",
            "amount": 5000.0,
        }
        html = render_invoice_html(data)
        assert "25/09/2026" in html

    def test_quotation_due_date_default(self):
        data = {
            "doc_no": "QT-202609-001",
            "doc_date": "10/09/2026",
            "client_name": "บริษัท ทดสอบ จำกัด",
            "amount": 20000.0,
        }
        html = render_quotation_html(data)
        expected_due = (datetime.strptime("10/09/2026", "%d/%m/%Y") + timedelta(days=30)).strftime("%d/%m/%Y")
        assert expected_due in html


class TestSyncServiceSheetRowData:
    """Test sheet row building in ghn168_sync_service."""

    def test_build_sheet_row_data_for_invoice_with_po(self):
        doc_data = {
            "doc_no": "IV-202609-005",
            "doc_date": "12/09/2026",
            "client_name": "บริษัท เอ็กซิท จำกัด",
            "project_name": "ถ่ายภาพแฟชั่น",
            "amount": 30000.0,
            "po_number": "PO-9988-77",
            "job_code": "JB-PROD-01",
            "remarks": "วางบิลรอบบ่าย",
        }
        sheet_name, row = build_sheet_row_data("invoice", doc_data)

        assert sheet_name == "ใบวางบิล"
        assert len(row) == 25

        # Col 21 is due_date (+30 days)
        expected_due = (datetime.strptime("12/09/2026", "%d/%m/%Y") + timedelta(days=30)).strftime("%d/%m/%Y")
        assert row[21] == expected_due

        # Col 22 is remarks containing PO and Job Code
        remarks_col = row[22]
        assert "P.O. No.: PO-9988-77" in remarks_col
        assert "Job Code: JB-PROD-01" in remarks_col
        assert "วางบิลรอบบ่าย" in remarks_col


class TestLineBotServerPOIntegration:
    """Test tool schemas, execution, and event handling for PO in line_bot_server."""

    def test_tool_schemas_contain_po_fields(self):
        create_tool = next(t for t in GEMINI_AGENT_TOOL_DECLARATIONS if t["name"] == "create_financial_document")
        create_props = create_tool["parameters"]["properties"]
        assert "po_number" in create_props
        assert "job_code" in create_props
        assert "po_date" in create_props
        assert "due_date" in create_props

        conv_tool = next(t for t in GEMINI_AGENT_TOOL_DECLARATIONS if t["name"] == "convert_document_pipeline")
        conv_overrides_props = conv_tool["parameters"]["properties"]["overrides"]["properties"]
        assert "po_number" in conv_overrides_props
        assert "job_code" in conv_overrides_props
        assert "po_date" in conv_overrides_props

    def test_should_reply_to_event_accepts_file_in_group(self):
        event = {
            "source": {"type": "group", "groupId": "Cgroup123", "userId": "Uuser123"},
            "message": {"type": "file", "id": "msg_file_001", "fileName": "PO_DoubleImage.pdf"}
        }
        should_reply, reason = should_reply_to_event(event)
        assert should_reply is True
        assert "file message" in reason

    def test_local_rule_based_extract_document_po(self):
        msg = "ออกใบวางบิลให้ บริษัท เชียงใหม่มีเดีย จำกัด ยอด 45000 PO: PO-2026-888 Job Code: JB-MKT-01"
        extracted = local_rule_based_extract_document(msg)
        assert extracted is not None
        assert extracted["doc_type"] == "invoice"
        assert extracted["po_number"] == "PO-2026-888"
        assert extracted["job_code"] == "JB-MKT-01"
        assert extracted["amount"] == 45000.0

    def test_merge_document_order_data_preserves_po(self):
        existing = {"client_name": "บริษัท ทดสอบ จำกัด", "amount": 10000.0}
        incoming = {"po_number": "PO-1234", "job_code": "JB-99", "doc_type": "invoice"}
        merged = merge_document_order_data(existing, incoming)
        assert merged["po_number"] == "PO-1234"
        assert merged["job_code"] == "JB-99"
        assert merged["doc_type"] == "invoice"

    def test_execute_agent_tool_create_financial_document_with_po(self):
        args = {
            "doc_type": "invoice",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "งานโฆษณา",
            "amount": 25000.0,
            "po_number": "PO-TEST-001",
            "job_code": "JB-TEST-01",
        }
        with patch("line_bot_server.generate_and_sync_document") as mock_gen:
            mock_gen.return_value = {
                "status": "simulation",
                "doc_no": "IV-202609-888",
                "pdf_url": "https://example.com/test.pdf",
                "totals": {"net_total": 26750.0}
            }
            # Step 1: Draft Creation (Draft & Confirm Protocol)
            res, flex = execute_agent_tool("create_financial_document", args, session_id="test_session")
            assert res["status"] == "draft_created"
            assert not mock_sync_called if "mock_sync_called" in locals() else not mock_gen.called

            # Step 2: Confirm Draft -> Calls generate_and_sync_document
            conf_res, conf_flex = execute_agent_tool("confirm_issue_document", {"draft_id": res["draft_id"]}, session_id="test_session")
            assert mock_gen.called
            passed_payload = mock_gen.call_args[1]["doc_data"]
            assert passed_payload["po_number"] == "PO-TEST-001"
            assert passed_payload["job_code"] == "JB-TEST-01"

    def test_download_line_file_content_mock(self):
        with patch("line_bot_server.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"%PDF-1.4 Mock PDF Content"
            mock_get.return_value = mock_resp

            data = download_line_file_content("msg_file_999")
            assert data == b"%PDF-1.4 Mock PDF Content"

    def test_execute_agent_tool_convert_document_pipeline_with_po(self):
        args = {
            "source_doc_no": "QT-202609-001",
            "target_type": "invoice",
            "po_number": "PO-CONV-999",
            "job_code": "JB-CONV-88",
            "overrides": {"remarks": "ด่วนพิเศษ"}
        }
        with patch("line_bot_server.convert_document") as mock_conv:
            mock_conv.return_value = {
                "status": "simulation",
                "doc_no": "IV-202609-999",
                "pdf_url": "https://example.com/test.pdf",
                "totals": {"net_total": 50000.0}
            }
            res, flex = execute_agent_tool("convert_document_pipeline", args, session_id="test_session")
            assert mock_conv.called
            passed_overrides = mock_conv.call_args[1]["overrides"]
            assert passed_overrides["po_number"] == "PO-CONV-999"
            assert passed_overrides["job_code"] == "JB-CONV-88"
            assert passed_overrides["remarks"] == "ด่วนพิเศษ"
