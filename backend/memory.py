"""
Octopus AI — Memory Manager
Persistent conversation storage and context management.
"""
import json
import uuid
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from config import get_data_dir
from vector_memory import VectorMemory

logger = logging.getLogger("octopus.memory")


class MemoryManager:
    """Manages short-term conversation context and long-term vector embeddings."""

    def __init__(self):
        self.data_dir = Path(get_data_dir())
        self.conv_dir = self.data_dir / "conversations"
        self.conv_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Vector Memory for cross-session RAG
        self.vector_db = VectorMemory(
            persist_directory=str(self.data_dir / "vector_db")
        )

    def _conv_path(self, conv_id: str) -> Path:
        return self.conv_dir / f"{conv_id}.json"

    def create_conversation(self, title: str = "New Chat") -> dict:
        conv_id = uuid.uuid4().hex
        conv = {
            "id": conv_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        self._save(conv_id, conv)
        return conv

    def list_conversations(self) -> list:
        conversations = []
        for f in sorted(
            self.conv_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                    conversations.append({
                        "id": data["id"],
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(data.get("messages", [])),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
        return conversations

    def get_conversation(self, conv_id: str) -> dict | None:
        path = self._conv_path(conv_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def add_message(
        self, conv_id: str, role: str, content: str, tool_calls: list = None
    ) -> dict:
        conv = self.get_conversation(conv_id)
        if not conv:
            conv = self.create_conversation()
            conv_id = conv["id"]

        msg_id = uuid.uuid4().hex
        msg = {
            "id": msg_id,
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }

        if tool_calls:
            msg["tool_calls"] = tool_calls

        conv["messages"].append(msg)
        conv["updated_at"] = datetime.now().isoformat()

        # Auto-generate title for first user message
        if role == "user" and len(
            [m for m in conv["messages"] if m["role"] == "user"]
        ) == 1:
            conv["title"] = (
                content[:30] + "..." if len(content) > 30 else content
            )

        self._save(conv_id, conv)

        # Store in Vector Memory in the background
        if role in ("user", "assistant"):
            try:
                # Don't embed massive text dumps (like full file reads)
                if len(content) < 4000:
                    self.vector_db.add_conversation_message(
                        conv_id, msg_id, role, content
                    )
            except Exception as e:
                logger.warning(f"Vector embedding failed: {e}")

        return msg

    def get_context_messages(
        self, conv_id: str, max_messages: int = 50
    ) -> list:
        conv = self.get_conversation(conv_id)
        if not conv:
            return []
        return conv.get("messages", [])[-max_messages:]

    def rename_conversation(self, conv_id: str, title: str) -> bool:
        conv = self.get_conversation(conv_id)
        if not conv:
            return False
        conv["title"] = title
        conv["updated_at"] = datetime.now().isoformat()
        self._save(conv_id, conv)
        return True

    def export_conversation(self, conv_id: str, fmt: str = "json") -> str | None:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None

        if fmt == "markdown":
            lines = [f"# {conv.get('title', 'Conversation')}\n"]
            lines.append(f"*Created: {conv.get('created_at', 'Unknown')}*\n\n---\n")
            for msg in conv.get("messages", []):
                role = msg["role"].capitalize()
                if role == "Tool":
                    lines.append(f"**🔧 Tool Result:**\n```json\n{msg['content']}\n```\n\n")
                else:
                    avatar = "👤" if role == "User" else "🐙"
                    lines.append(f"**{avatar} {role}:**\n{msg['content']}\n\n")
            return "\n".join(lines)
        else:
            return json.dumps(conv, indent=2, default=str)

    def delete_conversation(self, conv_id: str) -> bool:
        path = self._conv_path(conv_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def _save(self, conv_id: str, data: dict):
        with open(self._conv_path(conv_id), "w") as f:
            json.dump(data, f, indent=2, default=str)
