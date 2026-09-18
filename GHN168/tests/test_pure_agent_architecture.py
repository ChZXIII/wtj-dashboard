# -*- coding: utf-8 -*-
"""
Tests for Pure Agentic Architecture & 3-Tier Safety Confirmation Guard in GHN168 LINE Bot.
Verifies:
1. Quoted Message / File Reply Context Enrichment (e.g. quoting RE-202608-563.pdf + "หอมหัก 10% เข้า บ. นะจากบิลนี้")
2. 3-Tier Safety Confirmation Preview Guard (Preview First before Google Sheets update)
3. Step 2 Execution upon Confirmation ("ยืนยันอัปเดต RE-202608-563" -> Google Sheets Commit -> Green Flex Card)
4. Cancellation Handling ("ยกเลิก" clears pending states)
5. 100% Direct Autonomous Agent Routing bypassing legacy deterministic traps.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from line_bot_server import (
    call_gemini_agent,
    process_line_events,
    should_reply_to_event,
    resolve_quoted_message_content,
    build_confirmation_preview_flex_message,
    build_document_update_flex_message,
    PENDING_UPDATE_CONFIRMATIONS,
    PENDING_DOCUMENT_ORDERS,
    PENDING_INCOME_CONFIRMATIONS,
    PENDING_EXPENSE_CONFIRMATIONS,
    PENDING_NEW_CUSTOMER_SAVING,
    RECENT_MEDIA_CACHE,
    CONVERSATION_HISTORY,
    ACTIVE_CONVERSATION_THREADS,
    search_sheet_documents,
    update_sheet_document_data,
    execute_agent_tool
)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset all in-memory caches and pending states before and after each test."""
    PENDING_UPDATE_CONFIRMATIONS.clear()
    PENDING_DOCUMENT_ORDERS.clear()
    PENDING_INCOME_CONFIRMATIONS.clear()
    PENDING_EXPENSE_CONFIRMATIONS.clear()
    PENDING_NEW_CUSTOMER_SAVING.clear()
    RECENT_MEDIA_CACHE.clear()
    CONVERSATION_HISTORY.clear()
    ACTIVE_CONVERSATION_THREADS.clear()
    with patch("line_bot_server.GEMINI_API_KEY", ""), \
         patch("line_bot_server.LINE_CHANNEL_ACCESS_TOKEN", ""), \
         patch("line_bot_server.GAS_SCRIPT_URL", ""), \
         patch("ghn168_sync_service.GAS_SCRIPT_URL", ""):
        yield
    PENDING_UPDATE_CONFIRMATIONS.clear()
    PENDING_DOCUMENT_ORDERS.clear()
    PENDING_INCOME_CONFIRMATIONS.clear()
    PENDING_EXPENSE_CONFIRMATIONS.clear()
    PENDING_NEW_CUSTOMER_SAVING.clear()
    RECENT_MEDIA_CACHE.clear()
    CONVERSATION_HISTORY.clear()
    ACTIVE_CONVERSATION_THREADS.clear()


def test_build_confirmation_preview_flex_message_schema():
    """Test that build_confirmation_preview_flex_message produces valid LINE Flex bubble."""
    preview_data = {
        "action_type": "update_sheet_document",
        "doc_no": "RE-202608-563",
        "title": "ยืนยันอัปเดต RE-202608-563",
        "summary": "หักเงิน หอม 10% (฿5,000.00) เข้า บ. จากยอดก่อน VAT ฿50,000.00",
        "details": {
            "เลขที่เอกสาร": "RE-202608-563",
            "ลูกค้า": "บริษัท อินดิโก้ ไอเดีย จำกัด",
            "โครงการ": "งานผลิต VTR สื่อประชาสัมพันธ์ AOT",
            "ยอดก่อน VAT": "฿50,000.00",
            "คนทำงาน": "หอม",
            "สัดส่วนหักเข้า บ.": "10% (฿5,000.00)"
        },
        "confirm_text": "ยืนยันอัปเดต RE-202608-563",
        "cancel_text": "ยกเลิก"
    }
    flex_msg = build_confirmation_preview_flex_message(preview_data)
    assert flex_msg["type"] == "flex"
    assert "RE-202608-563" in flex_msg["altText"]
    bubble = flex_msg["contents"]
    assert bubble["type"] == "bubble"
    assert "header" in bubble
    assert "body" in bubble
    assert "footer" in bubble

    # Check footer action buttons
    footer_contents = bubble["footer"]["contents"]
    assert len(footer_contents) == 2
    assert footer_contents[0]["action"]["type"] == "message"
    assert footer_contents[0]["action"]["text"] == "ยืนยันอัปเดต RE-202608-563"
    assert footer_contents[1]["action"]["text"] == "ยกเลิก"


def test_resolve_quoted_message_content():
    """Test resolving quoted message content from RECENT_MEDIA_CACHE and history."""
    # 1. Text message
    RECENT_MEDIA_CACHE["msg_text_01"] = "ขอใบเสนอราคา เอ็มคูล 50,000".encode("utf-8")
    assert resolve_quoted_message_content("msg_text_01") == "ขอใบเสนอราคา เอ็มคูล 50,000"

    # 2. File message
    RECENT_MEDIA_CACHE["msg_file_01"] = "RE-202608-563.pdf".encode("utf-8")
    assert resolve_quoted_message_content("msg_file_01") == "RE-202608-563.pdf"

    # 3. Unknown message
    assert resolve_quoted_message_content("msg_unknown_99") == "ไฟล์/ข้อความ (ID: msg_unknown_99)"


def test_should_reply_to_event_with_quoted_work_action():
    """Test should_reply_to_event recognizes work actions on quoted messages in groups."""
    event = {
        "type": "message",
        "source": {
            "type": "group",
            "groupId": "Cgroup_test_001",
            "userId": "Uuser_keng"
        },
        "message": {
            "id": "msg_reply_01",
            "type": "text",
            "text": "หอมหัก 10% เข้า บ. นะจากบิลนี้",
            "quotedMessageId": "msg_file_01"
        }
    }
    should_reply, reason = should_reply_to_event(event)
    assert should_reply is True
    assert reason == "quoted message action"


@pytest.mark.asyncio
async def test_full_quoted_file_profit_share_preview_and_confirm_flow():
    """
    Simulates full end-to-end Pure Agentic flow:
    Turn 1: User replies to RE-202608-563.pdf with "หอมหัก 10% เข้า บ. นะจากบิลนี้"
            -> Context prefix attached -> Agent triggers Safety Preview Card (Tier 1 & 2)
    Turn 2: User confirms -> Agent executes Google Sheets sync -> Green Success Card (Tier 3)
    """
    session_id = "Cgroup_test_profit_share"
    user_id = "Uuser_hom"

    # Seed file cache
    file_msg_id = "msg_file_re563"
    RECENT_MEDIA_CACHE[file_msg_id] = "RE-202608-563.pdf".encode("utf-8")

    # Mock send_line_reply_messages, send_line_reply, and send_line_push_message
    replied_messages = []

    def mock_send_reply(token, text):
        replied_messages.append({"type": "text", "text": text})

    def mock_send_reply_msgs(token, msgs):
        replied_messages.extend(msgs)

    def mock_send_push(to, msgs):
        if isinstance(msgs, list):
            replied_messages.extend(msgs)
        else:
            replied_messages.append({"type": "text", "text": str(msgs)})
        return True

    with patch("line_bot_server.send_line_reply", side_effect=mock_send_reply), \
         patch("line_bot_server.send_line_reply_messages", side_effect=mock_send_reply_msgs), \
         patch("line_bot_server.send_line_push_message", side_effect=mock_send_push):

        # ----------------------------------------------------------------------
        # Turn 1: Quoted File Reply
        # ----------------------------------------------------------------------
        webhook_event_1 = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply_token_turn1",
                    "source": {
                        "type": "group",
                        "groupId": session_id,
                        "userId": user_id
                    },
                    "message": {
                        "id": "msg_reply_turn1",
                        "type": "text",
                        "text": "หอมหัก 10% เข้า บ. นะจากบิลนี้",
                        "quotedMessageId": file_msg_id
                    }
                }
            ]
        }

        await process_line_events(webhook_event_1)

        # Verify bot replied with Safety Confirmation Preview Card
        assert len(replied_messages) >= 1
        has_preview_flex = any(
            m.get("type") == "flex" and "RE-202608-563" in m.get("altText", "")
            for m in replied_messages
        )
        assert has_preview_flex is True, "Expected Safety Confirmation Preview Flex Card in Turn 1"

        # Verify staged in PENDING_UPDATE_CONFIRMATIONS
        assert session_id in PENDING_UPDATE_CONFIRMATIONS
        pending_data = PENDING_UPDATE_CONFIRMATIONS[session_id]
        assert pending_data["doc_no"] == "RE-202608-563"
        updates = pending_data["updates"]
        assert updates["profit_share_amount"] == 5000.0  # 10% of 50,000 THB base
        assert updates["deduction_percent"] == 10.0
        assert "หอม 10%" in updates["profit_share"]

        replied_messages.clear()

        # ----------------------------------------------------------------------
        # Turn 2: User Confirms Update
        # ----------------------------------------------------------------------
        webhook_event_2 = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply_token_turn2",
                    "source": {
                        "type": "group",
                        "groupId": session_id,
                        "userId": user_id
                    },
                    "message": {
                        "id": "msg_confirm_turn2",
                        "type": "text",
                        "text": "ยืนยันอัปเดต RE-202608-563"
                    }
                }
            ]
        }

        await process_line_events(webhook_event_2)

        # Verify state is popped and Google Sheets update succeeded
        assert session_id not in PENDING_UPDATE_CONFIRMATIONS
        assert len(replied_messages) >= 1

        # Check success Flex Card
        has_success_flex = any(
            m.get("type") == "flex" and ("อัปเดต" in m.get("altText", "") or "RE-202608-563" in m.get("altText", ""))
            for m in replied_messages
        )
        assert has_success_flex is True, "Expected Document Update Success Flex Card in Turn 2"


@pytest.mark.asyncio
async def test_profit_share_preview_cancellation_flow():
    """Test that user can cancel a pending update preview card cleanly with 'ยกเลิก'."""
    session_id = "Uuser_cancel_test"

    # Step 1: Call update request
    res1 = await call_gemini_agent("หอมหัก 10% เข้า บ. จากบิล RE-202608-563", session_id=session_id)
    assert session_id in PENDING_UPDATE_CONFIRMATIONS
    assert len(res1.get("flex_cards", [])) == 1

    # Step 2: Cancel
    res2 = await call_gemini_agent("ยกเลิก", session_id=session_id)
    assert session_id not in PENDING_UPDATE_CONFIRMATIONS
    assert "ยกเลิก" in res2["reply_text"]


@pytest.mark.asyncio
async def test_pure_agent_tool_execution_request_confirmation_preview():
    """Test execute_agent_tool directly for request_confirmation_preview tool."""
    tool_args = {
        "action_type": "update_sheet_document",
        "doc_no": "RE-202608-563",
        "summary": "หักเงิน หอม 10% (฿5,000.00) เข้า บ. จากยอดก่อน VAT ฿50,000.00",
        "details": {
            "เลขที่เอกสาร": "RE-202608-563",
            "ยอดก่อน VAT": "50,000.00 บาท",
            "หักเข้า บ.": "5,000.00 บาท"
        }
    }
    result_data, flex_card = execute_agent_tool("request_confirmation_preview", tool_args, "session_test")
    assert result_data["status"] == "preview_requested"
    assert flex_card is not None
    assert flex_card["type"] == "flex"
    assert "RE-202608-563" in flex_card["altText"]
