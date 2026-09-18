"""
==============================================================================
Test Suite for GHN168 Temporal Conversation Memory Engine
File: /Users/chz/Desktop/ChZ_Agent_Corp/GHN168/tests/test_ghn_temporal_memory.py
==============================================================================
Tests verify:
1. Persistence across reload (Persistence Test with Atomic File I/O)
2. State Compaction & Pruning when conversation turns exceed 20 (>20 turns)
3. LLM Context Generation format for Gemini System Instruction
4. Integration with line_bot_server.append_to_history and get_history
5. Atomic Thread Safety with concurrent writes
==============================================================================
"""

import os
import time
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

import line_bot_server as bot_server
from ghn_memory_engine import GHNMemoryEngine, SessionState, ghn_memory


class TestGHNTemporalMemory(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ghn_test_memory_")
        self.storage_path = os.path.join(self.test_dir, "test_conversation_state.json")
        self.engine = GHNMemoryEngine(storage_path=self.storage_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. Persistence Test Across Engine Reload
    # --------------------------------------------------------------------------
    def test_persistence_across_engine_reload(self):
        """Verify conversational state persists cleanly across engine reload via Atomic I/O."""
        session_id = "group_audit_session_001"

        # Append turns with speaker and document references
        self.engine.append_turn(
            session_id=session_id,
            role="user",
            text="สวัสดีครับเลขาเฟิส ช่วยดูใบเสนอราคา QT-202609-001 ของ บริษัท เชียงใหม่มีเดีย จำกัด ให้หน่อยครับ",
            speaker="บอสเก่ง"
        )
        self.engine.append_turn(
            session_id=session_id,
            role="model",
            text="สวัสดีค่ะบอสเก่ง เฟิสตรวจสอบเอกสาร QT-202609-001 ให้เรียบร้อยค่ะ ยอดสุทธิ 10,700 บาทค่ะ",
            speaker="เลขาเฟิส"
        )

        # Confirm file is written atomically and valid JSON
        self.assertTrue(os.path.exists(self.storage_path))
        with open(self.storage_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            self.assertIn("sessions", raw_data)
            self.assertIn(session_id, raw_data["sessions"])

        # Create a new, separate engine instance pointing to the same file
        reloaded_engine = GHNMemoryEngine(storage_path=self.storage_path)
        self.assertIn(session_id, reloaded_engine.sessions)

        session = reloaded_engine.sessions[session_id]
        self.assertEqual(len(session.recent_turns), 2)
        self.assertEqual(session.recent_turns[0]["speaker"], "บอสเก่ง")
        self.assertEqual(session.recent_turns[0]["role"], "user")
        self.assertIn("QT-202609-001", session.draft_documents)
        self.assertIn("เชียงใหม่มีเดีย", session.active_projects)

        # Verify get_recent_history
        history = reloaded_engine.get_recent_history(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["speaker"], "เลขาเฟิส")

    # --------------------------------------------------------------------------
    # 2. State Compaction & Pruning Test (>20 turns)
    # --------------------------------------------------------------------------
    def test_state_compaction_and_pruning_over_20_turns(self):
        """Verify older turns are pruned to 15 and condensed into rolling_summary when > 20 turns."""
        session_id = "group_discussion_marathon"

        # Append 25 conversation turns
        for i in range(1, 26):
            role = "user" if i % 2 != 0 else "model"
            speaker = "บอสเก่ง" if role == "user" else "เลขาเฟิส"
            text = f"ข้อความเทิร์นที่ {i}: อัปเดตงานโฆษณาชิ้นที่ {i}"
            self.engine.append_turn(session_id=session_id, role=role, text=text, speaker=speaker)

        session = self.engine.sessions[session_id]
        self.assertEqual(len(session.recent_turns), 25)
        self.assertEqual(session.rolling_summary, "")

        # Trigger compaction (threshold=20, keep_recent=15)
        compacted = self.engine.compact_session(session_id, threshold=20, keep_recent=15)
        self.assertTrue(compacted)

        # recent_turns must now be pruned to exactly 15 turns
        self.assertEqual(len(session.recent_turns), 15)
        self.assertEqual(session.recent_turns[0]["text"], "ข้อความเทิร์นที่ 11: อัปเดตงานโฆษณาชิ้นที่ 11")
        self.assertEqual(session.recent_turns[-1]["text"], "ข้อความเทิร์นที่ 25: อัปเดตงานโฆษณาชิ้นที่ 25")

        # Older turns (1-10) must be summarized in rolling_summary
        self.assertTrue(len(session.rolling_summary) > 0)
        self.assertIn("สรุปประเด็นก่อนหน้า", session.rolling_summary)
        self.assertIn("บอสเก่ง", session.rolling_summary)

        # Calling compact again when turns <= 20 must return False (no-op)
        compacted_again = self.engine.compact_session(session_id, threshold=20, keep_recent=15)
        self.assertFalse(compacted_again)
        self.assertEqual(len(session.recent_turns), 15)

    # --------------------------------------------------------------------------
    # 3. LLM Context Generation Format Test
    # --------------------------------------------------------------------------
    def test_get_llm_context_formatting(self):
        """Verify get_llm_context formats rolling summary, active projects, draft docs, and live turns."""
        session_id = "executive_board_chat"

        # Setup session state with project, draft doc, and rolling summary
        self.engine.append_turn(
            session_id=session_id,
            role="user",
            text="ติดตามใบแจ้งหนี้ IV-202609-005 ให้กับ บริษัท ไอเด็กซ์ ไมซ์ จำกัด ด้วยครับ",
            speaker="บอสมด"
        )
        session = self.engine.sessions[session_id]
        session.rolling_summary = "• มติที่ประชุม: อนุมัติงบกองถ่าย MV ตัวใหม่ 50,000 บาท"

        llm_ctx = self.engine.get_llm_context(session_id)

        # Assert mandatory contextual sections are present
        self.assertIn("GHN168 TEMPORAL MEMORY CONTEXT", llm_ctx)
        self.assertIn("📌 สรุปมติและประเด็นงานที่คุยค้างไว้ (Rolling Summary):", llm_ctx)
        self.assertIn("อนุมัติงบกองถ่าย MV ตัวใหม่", llm_ctx)
        self.assertIn("🏢 โปรเจกต์ / ลูกค้าล่าสุด:", llm_ctx)
        self.assertIn("ไอเด็กซ์", llm_ctx)
        self.assertIn("📑 ดราฟต์เอกสาร / เอกสารที่อ้างอิง:", llm_ctx)
        self.assertIn("IV-202609-005", llm_ctx)
        self.assertIn("💬 บทสนทนาสดล่าสุด", llm_ctx)
        self.assertIn("[บอสมด]: ติดตามใบแจ้งหนี้ IV-202609-005", llm_ctx)

    # --------------------------------------------------------------------------
    # 4. Integration with line_bot_server
    # --------------------------------------------------------------------------
    def test_line_bot_server_history_delegation(self):
        """Verify bot_server.append_to_history and bot_server.get_history work via ghn_memory."""
        test_session = f"test_delegation_{int(time.time() * 1000)}"

        bot_server.append_to_history(
            session_id=test_session,
            role="user",
            text="ช่วยเปิดบิลให้ บจก. นอร์ทเทิร์น อินโนเวชั่น แล็บ",
            speaker="บอสเก่ง"
        )
        bot_server.append_to_history(
            session_id=test_session,
            role="model",
            text="รับทราบค่ะบอสเก่ง กำลังเปิดบิลให้ บจก. นอร์ทเทิร์น อินโนเวชั่น แล็บ ค่ะ",
            speaker="เลขาเฟิส"
        )

        history = bot_server.get_history(test_session)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["text"], "ช่วยเปิดบิลให้ บจก. นอร์ทเทิร์น อินโนเวชั่น แล็บ")
        self.assertEqual(history[0]["speaker"], "บอสเก่ง")
        self.assertEqual(history[1]["role"], "model")
        self.assertEqual(history[1]["speaker"], "เลขาเฟิส")

        # Verify ghn_memory singleton also captured it
        mem_hist = ghn_memory.get_recent_history(test_session)
        self.assertEqual(len(mem_hist), 2)
        self.assertEqual(mem_hist[-1]["text"], history[1]["text"])

    # --------------------------------------------------------------------------
    # 5. Thread-safe Concurrent Writes
    # --------------------------------------------------------------------------
    def test_thread_safe_atomic_writes(self):
        """Verify concurrent multi-threaded appends maintain file and state integrity."""
        session_id = "concurrent_stress_session"
        num_threads = 8
        turns_per_thread = 5

        def worker(thread_idx: int):
            for j in range(turns_per_thread):
                self.engine.append_turn(
                    session_id=session_id,
                    role="user" if j % 2 == 0 else "model",
                    text=f"Thread-{thread_idx} Turn-{j}",
                    speaker=f"Worker-{thread_idx}"
                )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check total turns in memory
        session = self.engine.sessions[session_id]
        expected_turns = num_threads * turns_per_thread
        self.assertEqual(len(session.recent_turns), expected_turns)

        # Verify persisted JSON on disk is non-corrupt
        with open(self.storage_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
            self.assertEqual(len(disk_data["sessions"][session_id]["recent_turns"]), expected_turns)

    # --------------------------------------------------------------------------
    # 6. Corrupt JSON File Recovery & Backup
    # --------------------------------------------------------------------------
    def test_corrupt_json_recovery_and_backup(self):
        """Verify corrupt JSON file is handled gracefully without crashing, backed up, and recoverable."""
        corrupt_path = os.path.join(self.test_dir, "corrupted_state.json")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true, incomplete")

        # Loading corrupt file must not raise, and must create .corrupt.bak
        engine = GHNMemoryEngine(storage_path=corrupt_path)
        self.assertEqual(len(engine.sessions), 0)
        self.assertTrue(os.path.exists(f"{corrupt_path}.corrupt.bak"))

        # Writing after corrupt recovery must create a healthy JSON file
        engine.append_turn("recovered_session", "user", "กู้คืนระบบสำเร็จ", speaker="บอสเก่ง")
        self.assertIn("recovered_session", engine.sessions)
        with open(corrupt_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("recovered_session", data["sessions"])

    # --------------------------------------------------------------------------
    # 7. Relative Storage Path Without Directory
    # --------------------------------------------------------------------------
    def test_relative_storage_path_without_dir(self):
        """Verify initializing engine with a bare relative filename does not fail os.makedirs."""
        bare_filename = f"temp_nodir_test_{int(time.time() * 1000)}.json"
        try:
            bare_engine = GHNMemoryEngine(storage_path=bare_filename)
            bare_engine.append_turn("session_nodir", "user", "ทดสอบ relative path", speaker="บอสเก่ง")
            self.assertTrue(os.path.exists(bare_filename))
            self.assertIn("session_nodir", bare_engine.sessions)
        finally:
            if os.path.exists(bare_filename):
                os.remove(bare_filename)
            if os.path.exists(f"{bare_filename}.tmp"):
                os.remove(f"{bare_filename}.tmp")

    # --------------------------------------------------------------------------
    # 8. Partial Corruption Resilience in Sessions Dict
    # --------------------------------------------------------------------------
    def test_partial_corruption_in_sessions(self):
        """Verify a single corrupted session entry does not corrupt or drop valid sibling sessions."""
        partial_path = os.path.join(self.test_dir, "partial_corrupt.json")
        payload = {
            "version": "1.0",
            "saved_at": time.time(),
            "sessions": {
                "valid_session_01": {
                    "session_id": "valid_session_01",
                    "rolling_summary": "สรุปงานโฆษณา",
                    "active_projects": ["เชียงใหม่มีเดีย"],
                    "draft_documents": {},
                    "recent_turns": [{"role": "user", "text": "สวัสดี", "speaker": "บอสเก่ง", "timestamp": time.time()}],
                    "updated_at": time.time()
                },
                "corrupt_session_02": "MALFORMED_NON_DICT_ENTRY",
                "corrupt_session_03": None
            }
        }
        with open(partial_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        engine = GHNMemoryEngine(storage_path=partial_path)
        # Valid session must be recovered while skipping malformed items
        self.assertIn("valid_session_01", engine.sessions)
        self.assertEqual(engine.sessions["valid_session_01"].rolling_summary, "สรุปงานโฆษณา")
        self.assertNotIn("corrupt_session_02", engine.sessions)

    # --------------------------------------------------------------------------
    # 9. Multiple Documents and Empty Text Handling
    # --------------------------------------------------------------------------
    def test_multiple_documents_and_empty_text_handling(self):
        """Verify multiple doc codes are extracted cleanly and empty texts are skipped."""
        session_id = "multi_doc_session"

        # Empty / whitespace should be safely ignored
        self.engine.append_turn(session_id, "user", "   ", speaker="บอสเก่ง")
        self.assertEqual(len(self.engine.get_recent_history(session_id)), 0)

        # Multiple document codes in a single message
        multi_doc_msg = "ออกเอกสาร QT-202609-001, IV-202609-002, และ RE-202609-003 ให้หน่อยครับ"
        self.engine.append_turn(session_id, "user", multi_doc_msg, speaker="บอสเก่ง")

        session = self.engine.sessions[session_id]
        self.assertEqual(len(session.recent_turns), 1)
        self.assertIn("QT-202609-001", session.draft_documents)
        self.assertIn("IV-202609-002", session.draft_documents)
        self.assertIn("RE-202609-003", session.draft_documents)

    # --------------------------------------------------------------------------
    # 10. Clear Session and Clear All Verification
    # --------------------------------------------------------------------------
    def test_clear_session_and_clear_all(self):
        """Verify clear_session and clear_all wipe memory and persist cleanly to disk."""
        self.engine.append_turn("s1", "user", "ข้อความที่ 1")
        self.engine.append_turn("s2", "user", "ข้อความที่ 2")
        self.assertEqual(len(self.engine.sessions), 2)

        self.engine.clear_session("s1")
        self.assertNotIn("s1", self.engine.sessions)
        self.assertIn("s2", self.engine.sessions)

        # Reload to verify disk state
        reloaded = GHNMemoryEngine(storage_path=self.storage_path)
        self.assertNotIn("s1", reloaded.sessions)
        self.assertIn("s2", reloaded.sessions)

        # Clear all
        self.engine.clear_all()
        self.assertEqual(len(self.engine.sessions), 0)
        reloaded_empty = GHNMemoryEngine(storage_path=self.storage_path)
        self.assertEqual(len(reloaded_empty.sessions), 0)


if __name__ == "__main__":
    unittest.main()
