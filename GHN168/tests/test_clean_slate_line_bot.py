import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure repo root is on sys.path
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from line_bot_server import (
    app,
    ACTIVE_DRAFTS,
    SESSION_ACTIVE_DRAFT,
    create_or_update_draft,
    confirm_draft_to_official_document,
    apply_strict_user_overrides,
    build_draft_summary_flex_message,
    build_document_flex_message,
    process_line_events,
    should_reply_to_event,
    download_line_file_content,
    call_gemini_agent,
    execute_agent_tool,
    RECENT_MEDIA_CACHE,
    SESSION_LAST_FILE,
)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear memory state before each test."""
    ACTIVE_DRAFTS.clear()
    SESSION_ACTIVE_DRAFT.clear()
    RECENT_MEDIA_CACHE.clear()
    SESSION_LAST_FILE.clear()
    yield
    ACTIVE_DRAFTS.clear()
    SESSION_ACTIVE_DRAFT.clear()


class TestDraftAndConfirmProtocol:
    """Test the Human-in-the-Loop Draft & Confirm protocol."""

    def test_draft_creation_no_sheets_no_pdf(self):
        """Creating a draft must NOT call generate_and_sync_document, mint official doc number, or write sheets."""
        session_id = "test_user_session_1"
        data = {
            "doc_type": "invoice",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ถ่ายวิดีโอ 3 วัน",
            "amount": 30000.0,
            "items": [
                {"desc": "ถ่ายวิดีโอวันที่ 1", "qty": 1, "price": 10000.0, "amount": 10000.0},
                {"desc": "ถ่ายวิดีโอวันที่ 2", "qty": 1, "price": 10000.0, "amount": 10000.0},
                {"desc": "ถ่ายวิดีโอวันที่ 3", "qty": 1, "price": 10000.0, "amount": 10000.0},
            ],
            "po_number": "PO-2026-999",
            "job_code": "JB-VID-01"
        }

        with patch("line_bot_server.generate_and_sync_document") as mock_sync:
            draft = create_or_update_draft(session_id, "ออกใบวางบิล ยอด 30,000", data, speaker_name="บอสเก่ง")

            # Must NOT touch Google Sheets or render PDF
            assert not mock_sync.called

            # Draft state assertions
            assert draft["status"] == "draft"
            assert draft["draft_id"].startswith("DFT-")
            assert draft["draft_id"] in ACTIVE_DRAFTS
            assert SESSION_ACTIVE_DRAFT[session_id] == draft["draft_id"]
            assert draft["client_name"] == "บริษัท เชียงใหม่มีเดีย จำกัด"
            assert draft["po_number"] == "PO-2026-999"
            assert draft["job_code"] == "JB-VID-01"

            # Financial Totals for Invoice Billing (30,000 + 7% VAT = 32,100 gross billable)
            assert draft["totals"]["pre_vat"] == 30000.0
            assert draft["totals"]["vat_amount"] == 2100.0
            assert draft["totals"]["wht_amount"] == 0.0
            assert draft["totals"]["net_total"] == 32100.0

            # Default invoice due date (+30 days)
            expected_due = (datetime.strptime(draft["doc_date"], "%d/%m/%Y") + timedelta(days=30)).strftime("%d/%m/%Y")
            assert draft["due_date"] == expected_due

    def test_draft_summary_flex_card_structure(self):
        """Draft Flex card must show itemized breakdown (no bundling), totals, and action buttons."""
        session_id = "test_user_session_2"
        data = {
            "doc_type": "invoice",
            "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
            "project_name": "งานโปรดักชั่น",
            "amount": 20000.0,
            "items": [
                {"desc": "ถ่ายภาพนิ่ง", "qty": 1, "price": 12000.0, "amount": 12000.0},
                {"desc": "ตัดต่อรีลส์ 3 คลิป", "qty": 3, "price": 2666.67, "amount": 8000.0}
            ],
            "po_number": "PO-MCOOL-77",
            "job_code": "JB-MKT-02"
        }
        draft = create_or_update_draft(session_id, "ออกใบวางบิล", data, speaker_name="บอสเก่ง")
        flex = build_draft_summary_flex_message(draft)

        assert flex["type"] == "flex"
        bubble = flex["contents"]

        # Header contains draft ID
        header_text = bubble["header"]["contents"][0]["text"]
        assert "ร่างเอกสาร" in header_text

        # Footer must contain Confirm and Edit buttons
        footer_buttons = bubble["footer"]["contents"]
        btn_confirm = footer_buttons[0]
        btn_edit = footer_buttons[1]

        assert btn_confirm["type"] == "button"
        assert "ออกเอกสารจริง" in btn_confirm["action"]["label"]
        assert f"ยืนยันออกเอกสาร {draft['draft_id']}" in btn_confirm["action"]["text"]

        assert btn_edit["type"] == "button"
        assert "สั่งแก้ไข" in btn_edit["action"]["label"]

    def test_confirmation_flow_mints_official_doc(self):
        """When user confirms, official doc number is minted, PDF rendered, and sheets synced."""
        session_id = "test_user_session_3"
        data = {
            "doc_type": "invoice",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "amount": 15000.0,
            "items": [{"desc": "ค่าบริการ", "qty": 1, "price": 15000.0, "amount": 15000.0}]
        }
        draft = create_or_update_draft(session_id, "ออกใบวางบิล", data, speaker_name="บอสเก่ง")
        draft_id = draft["draft_id"]

        mock_doc_res = {
            "status": "success",
            "doc_no": "IV-202609-001",
            "doc_type": "invoice",
            "client_name": "บริษัท เชียงใหม่มีเดีย จำกัด",
            "project_name": "ค่าบริการ",
            "pdf_url": "https://drive.google.com/file/d/test_pdf/view",
            "totals": {"net_total": 15600.0}
        }

        with patch("line_bot_server.generate_and_sync_document") as mock_sync:
            mock_sync.return_value = mock_doc_res

            doc_res, flex_card = confirm_draft_to_official_document(draft_id, session_id)

            assert mock_sync.called
            passed_payload = mock_sync.call_args[1]["doc_data"]
            assert passed_payload["draft_id"] == draft_id

            # Active draft status updated to confirmed
            assert ACTIVE_DRAFTS[draft_id]["status"] == "confirmed"
            assert ACTIVE_DRAFTS[draft_id]["official_doc_no"] == "IV-202609-001"
            assert session_id not in SESSION_ACTIVE_DRAFT

            # Flex card returned contains official doc number
            assert flex_card is not None
            assert "IV-202609-001" in flex_card["altText"]


class TestStrictUserOverrides:
    """Test deterministic user overrides for signer names and due dates."""

    def test_override_signer_keng(self):
        data = {"signer_name": "นาย ณัฐวัฒน์ ปวงจันทร์หอม"}
        apply_strict_user_overrides("ขอคนเซ็นเป็นบอสเก่งนะ", data)
        assert data["signer_name"] == "นาย มงคล วงศ์สกุลยานนท์"

    def test_override_signer_hom(self):
        data = {"signer_name": "นาย มงคล วงศ์สกุลยานนท์"}
        apply_strict_user_overrides("ให้บอสหอมลงนามในบิลนี้", data)
        assert data["signer_name"] == "นาย ณัฐวัฒน์ ปวงจันทร์หอม"

    def test_override_due_date_day_month(self):
        data = {"due_date": "10/10/2026"}
        apply_strict_user_overrides("แก้วันเป็น 16/10", data)
        cur_year = datetime.now().year
        assert data["due_date"] == f"16/10/{cur_year}"

    def test_override_due_date_full_date(self):
        data = {"due_date": "10/10/2026"}
        apply_strict_user_overrides("กำหนดจ่าย 25/11/2026", data)
        assert data["due_date"] == "25/11/2026"

    @pytest.mark.asyncio
    async def test_revise_active_draft_in_chat(self):
        """User typing 'แก้คนเซ็นเป็นบอสเก่ง' directly updates the active draft."""
        session_id = "test_user_session_4"
        data = {
            "doc_type": "invoice",
            "client_name": "บริษัท ลานนา ครีเอทีฟ สตูดิโอ จำกัด",
            "amount": 25000.0,
            "signer_name": "นาย ณัฐวัฒน์ ปวงจันทร์หอม"
        }
        draft = create_or_update_draft(session_id, "ออกใบวางบิล", data)
        assert draft["signer_name"] == "นาย ณัฐวัฒน์ ปวงจันทร์หอม"

        res = await call_gemini_agent("แก้คนเซ็นเป็นบอสเก่ง", session_id=session_id, speaker_name="บอสเก่ง")
        assert res["draft"]["signer_name"] == "นาย มงคล วงศ์สกุลยานนท์"
        assert len(res["flex_cards"]) == 1


class Test100PercentReplyTokenZeroPush:
    """Test that turn replies use 100% reply_token and zero push API calls."""

    @pytest.mark.asyncio
    async def test_single_stage_reply_zero_push_calls(self):
        payload = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token_999",
                    "source": {"type": "user", "userId": "U12345678"},
                    "message": {"type": "text", "id": "msg_001", "text": "ออกใบวางบิลให้ บ.เชียงใหม่มีเดีย 20000 บาท"}
                }
            ]
        }

        with patch("line_bot_server.send_line_reply_messages") as mock_reply, \
             patch("line_bot_server.send_line_push_message") as mock_push:
            mock_reply.return_value = True

            await process_line_events(payload)

            # Reply token MUST be called with final text and Flex card
            assert mock_reply.called
            token_arg = mock_reply.call_args[0][0]
            msgs_arg = mock_reply.call_args[0][1]
            assert token_arg == "test_reply_token_999"
            assert len(msgs_arg) >= 1

            # Push API MUST NOT be called! Zero push calls = Zero 429 errors!
            assert not mock_push.called


class TestMultimodalPOAndCacheSafety:
    """Test incoming PO PDF handling and zero cache poisoning."""

    @pytest.mark.asyncio
    async def test_incoming_po_pdf_handling(self):
        payload = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token_pdf",
                    "source": {"type": "group", "groupId": "Cgroup_test", "userId": "Uboss_keng"},
                    "message": {
                        "type": "file",
                        "id": "file_msg_777",
                        "fileName": "PO_DoubleImage_2026.pdf"
                    }
                }
            ]
        }

        mock_pdf_bytes = b"%PDF-1.5 Mock Corporate Purchase Order PO-2026-99"

        with patch("line_bot_server.download_line_file_content") as mock_dl, \
             patch("line_bot_server.send_line_reply_messages") as mock_reply, \
             patch("line_bot_server.send_line_push_message") as mock_push:
            mock_dl.return_value = mock_pdf_bytes
            mock_reply.return_value = True

            await process_line_events(payload)

            # Assert downloaded & cached safely
            assert mock_dl.called
            assert RECENT_MEDIA_CACHE["file_msg_777"] == mock_pdf_bytes
            assert SESSION_LAST_FILE["Cgroup_test"]["file_name"] == "PO_DoubleImage_2026.pdf"

            # Reply was sent via replyToken without push
            assert mock_reply.called
            assert not mock_push.called

    def test_zero_cache_poisoning_on_failed_download(self):
        """When downloading file fails, do NOT fall back to old cached media."""
        SESSION_LAST_FILE["old_session"] = {"bytes": b"STALE_OLD_PO_DATA", "file_name": "old.pdf"}

        with patch("line_bot_server.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            result = download_line_file_content("non_existent_msg_id")
            assert result is None  # Never returns stale cache
