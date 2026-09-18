"""
==============================================================================
GHN168 Temporal Conversation Memory Engine (ghn_memory_engine.py)
==============================================================================
Provides high-resilience, multi-turn conversational memory for LINE Bot with:
1. Atomic File I/O (.tmp write + atomic replace + threading.RLock)
2. Structured SessionState tracking:
   - session_id (Group/Room/User ID)
   - rolling_summary (สรุปมติและประเด็นงานที่คุยค้างไว้)
   - active_projects (โปรเจกต์หรือลูกค้ารายล่าสุดที่กำลังคุย)
   - draft_documents (ดราฟต์ใบเสนอราคา/ใบแจ้งหนี้)
   - recent_turns (บทสนทนาสดล่าสุด 15 turns)
   - updated_at (timestamp)
3. State Compaction & Pruning when history accumulates (>20 turns)
4. LLM Context Generation for Gemini System Instruction
5. Singleton instance: ghn_memory
==============================================================================
"""

import os
import re
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ghn_memory_engine")

DEFAULT_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "line_conversation_state.json"
)

MAX_RECENT_TURNS = 15
COMPACTION_THRESHOLD = 20


class SessionState:
    """
    State container for a single LINE chat session (Group, Room, or 1-on-1 User).
    """
    def __init__(
        self,
        session_id: str,
        rolling_summary: str = "",
        active_projects: Optional[List[str]] = None,
        draft_documents: Optional[Dict[str, Any]] = None,
        recent_turns: Optional[List[Dict[str, Any]]] = None,
        updated_at: Optional[float] = None
    ):
        self.session_id = session_id
        self.rolling_summary = rolling_summary or ""
        self.active_projects = list(active_projects) if active_projects is not None else []
        self.draft_documents = dict(draft_documents) if draft_documents is not None else {}
        self.recent_turns = list(recent_turns) if recent_turns is not None else []
        self.updated_at = updated_at or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "rolling_summary": self.rolling_summary,
            "active_projects": self.active_projects,
            "draft_documents": self.draft_documents,
            "recent_turns": self.recent_turns,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        return cls(
            session_id=data.get("session_id", ""),
            rolling_summary=data.get("rolling_summary", ""),
            active_projects=data.get("active_projects", []),
            draft_documents=data.get("draft_documents", {}),
            recent_turns=data.get("recent_turns", []),
            updated_at=data.get("updated_at", time.time())
        )


class GHNMemoryEngine:
    """
    High-resilience Temporal Conversation Memory Engine for GHN168 LINE Bot.
    Guarantees thread-safe atomic persistence to disk.
    """
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._lock = threading.RLock()
        self.sessions: Dict[str, SessionState] = {}
        self.load()

    def load(self) -> None:
        """Loads state from line_conversation_state.json with RLock."""
        with self._lock:
            if not os.path.exists(self.storage_path):
                self.sessions = {}
                return

            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions_raw = data.get("sessions", {}) if isinstance(data, dict) else {}
                self.sessions = {}
                if isinstance(sessions_raw, dict):
                    for sid, sdata in sessions_raw.items():
                        if isinstance(sdata, dict):
                            self.sessions[str(sid)] = SessionState.from_dict(sdata)
                logger.info(f"[GHNMemoryEngine] Loaded {len(self.sessions)} sessions from {self.storage_path}")
            except Exception as e:
                logger.error(f"[GHNMemoryEngine] Error loading memory state from {self.storage_path}: {e}")
                try:
                    if os.path.exists(self.storage_path) and os.path.getsize(self.storage_path) > 0:
                        bak_path = f"{self.storage_path}.corrupt.bak"
                        import shutil
                        shutil.copy2(self.storage_path, bak_path)
                        logger.warning(f"[GHNMemoryEngine] Backed up corrupted state to {bak_path}")
                except Exception as bak_err:
                    logger.error(f"[GHNMemoryEngine] Failed to backup corrupt file: {bak_err}")
                self.sessions = {}

    def save(self) -> None:
        """Saves state atomically using a temporary file and atomic replace."""
        with self._lock:
            try:
                target_dir = os.path.dirname(self.storage_path)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)

                tmp_path = f"{self.storage_path}.tmp"
                payload = {
                    "version": "1.0",
                    "saved_at": time.time(),
                    "sessions": {
                        sid: state.to_dict()
                        for sid, state in self.sessions.items()
                    }
                }

                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(tmp_path, self.storage_path)
            except Exception as e:
                logger.error(f"[GHNMemoryEngine] Error saving memory state to {self.storage_path}: {e}")

    def get_or_create_session(self, session_id: str) -> SessionState:
        """Gets existing session or initializes a new SessionState."""
        with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = SessionState(session_id=session_id)
            return self.sessions[session_id]

    def append_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        speaker: Optional[str] = None
    ) -> None:
        """
        Appends a conversational turn to recent_turns and persists state atomically.
        Also automatically extracts project references, customer names, or doc numbers.
        """
        if not session_id or not text:
            return

        text_str = str(text).strip()
        if not text_str:
            return

        with self._lock:
            session = self.get_or_create_session(session_id)
            turn = {
                "role": role,
                "text": text_str,
                "speaker": speaker,
                "timestamp": time.time()
            }
            session.recent_turns.append(turn)
            session.updated_at = time.time()

            # Heuristic detection for draft documents
            doc_matches = re.findall(r"\b(?:QT|IV|RE|BL)[-–—]?\d{4,6}[-–—]?\d{3,4}\b", text_str, re.IGNORECASE)
            for full_doc in doc_matches:
                clean_doc = full_doc.upper().replace("–", "-").replace("—", "-")
                session.draft_documents[clean_doc] = {
                    "doc_no": clean_doc,
                    "last_mentioned": time.time()
                }

            # Heuristic detection for active project/client keywords
            client_keywords = [
                "เชียงใหม่มีเดีย", "นอร์ทเทิร์น อินโนเวชั่น", "ไอเด็กซ์", "อินดีด",
                "ลานนา ครีเอทีฟ", "แคทไซคลิ่ง", "พิงค์นคร", "โรงแรม เดอะริเวอร์",
                "ซีพีออลล์", "เชอิล", "samsung", "aot", "ทอท", "ช้างเผือก"
            ]
            for kw in client_keywords:
                if kw.lower() in text_str.lower():
                    if kw not in session.active_projects:
                        session.active_projects.append(kw)
                        if len(session.active_projects) > 5:
                            session.active_projects = session.active_projects[-5:]

            self.save()

    def get_recent_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns recent conversation turns for the session.
        If limit is None, returns recent_turns (up to MAX_RECENT_TURNS or all if fewer).
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return []
            if limit is not None:
                return list(session.recent_turns[-limit:])
            return list(session.recent_turns)

    def compact_session(
        self,
        session_id: str,
        threshold: int = COMPACTION_THRESHOLD,
        keep_recent: int = MAX_RECENT_TURNS
    ) -> bool:
        """
        Prunes and condenses older messages when recent_turns > threshold (>20 turns).
        Retains the most recent `keep_recent` (15) turns in recent_turns,
        and condenses the older turns into `rolling_summary`.
        Returns True if compaction took place, False otherwise.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or len(session.recent_turns) <= threshold:
                return False

            # Extract turns that exceed keep_recent
            turns_to_compact = session.recent_turns[:-keep_recent]
            session.recent_turns = session.recent_turns[-keep_recent:]

            summary_bullet_points = []
            for t in turns_to_compact:
                role = t.get("role", "user")
                speaker = t.get("speaker")
                text = t.get("text", "").strip()
                if not text:
                    continue

                spk_name = speaker or ("ผู้บริหาร" if role == "user" else "เลขาเฟิส")
                # Truncate overly long text snippets
                clean_snippet = text if len(text) <= 60 else text[:57] + "..."
                summary_bullet_points.append(f"{spk_name}: {clean_snippet}")

            if summary_bullet_points:
                # Merge into rolling_summary
                compacted_chunk = " | ".join(summary_bullet_points[:10])
                if session.rolling_summary:
                    session.rolling_summary = f"{session.rolling_summary}\n• ข้อความก่อนหน้า: {compacted_chunk}"
                else:
                    session.rolling_summary = f"• สรุปประเด็นก่อนหน้า: {compacted_chunk}"

                # Keep rolling_summary within reasonable bounds (last 1000 characters)
                if len(session.rolling_summary) > 1000:
                    session.rolling_summary = session.rolling_summary[-1000:]

            session.updated_at = time.time()
            self.save()
            logger.info(f"[GHNMemoryEngine] Compacted session {session_id}: retained {len(session.recent_turns)} turns.")
            return True

    def get_llm_context(self, session_id: str) -> str:
        """
        Generates a structured context string summarizing work status + recent live conversation
        for insertion into Gemini System Instruction or prompt.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return ""

            parts = [
                "================================================================================",
                "🧠 GHN168 TEMPORAL MEMORY CONTEXT (บริบทความจำต่อเนื่องของห้องสนทนานี้)",
                "================================================================================"
            ]

            # 1. Rolling Summary
            if session.rolling_summary.strip():
                parts.append(f"📌 สรุปมติและประเด็นงานที่คุยค้างไว้ (Rolling Summary):\n{session.rolling_summary.strip()}")
            else:
                parts.append("📌 สรุปมติและประเด็นงานที่คุยค้างไว้: ยังไม่มีประเด็นงานค้าง")

            # 2. Active Projects / Clients
            if session.active_projects:
                proj_str = ", ".join(session.active_projects)
                parts.append(f"🏢 โปรเจกต์ / ลูกค้าล่าสุด: {proj_str}")
            else:
                parts.append("🏢 โปรเจกต์ / ลูกค้าล่าสุด: -")

            # 3. Draft Documents
            if session.draft_documents:
                docs = list(session.draft_documents.keys())
                parts.append(f"📑 ดราฟต์เอกสาร / เอกสารที่อ้างอิง: {', '.join(docs)}")
            else:
                parts.append("📑 ดราฟต์เอกสาร / เอกสารที่อ้างอิง: -")

            # 4. Recent Conversation Turns
            recent = session.recent_turns[-MAX_RECENT_TURNS:]
            if recent:
                parts.append(f"\n💬 บทสนทนาสดล่าสุด ({len(recent)} turns):")
                for item in recent:
                    role = item.get("role", "user")
                    speaker = item.get("speaker")
                    spk_label = speaker or ("ผู้บริหาร" if role == "user" else "เลขาเฟิส")
                    txt = item.get("text", "").strip()
                    parts.append(f"- [{spk_label}]: {txt}")

            parts.append("================================================================================")
            return "\n".join(parts)

    def clear_session(self, session_id: str) -> None:
        """Clears memory for a specific session."""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.save()

    def clear_all(self) -> None:
        """Clears all sessions from memory and persists state."""
        with self._lock:
            self.sessions.clear()
            self.save()


# Singleton Instance
ghn_memory = GHNMemoryEngine()

