"""
Octopus AI — Memory Manager
Persistent conversation storage and context management.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from config import MEMORY_DIR


class MemoryManager:
    def __init__(self):
        self.conversations_dir = MEMORY_DIR / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

    def _conv_path(self, conv_id: str) -> Path:
        return self.conversations_dir / f"{conv_id}.json"

    def create_conversation(self, title: str = "New Chat") -> dict:
        conv_id = str(uuid.uuid4())[:8]
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
        for f in sorted(self.conversations_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
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

    def add_message(self, conv_id: str, role: str, content: str, tool_calls: list = None) -> dict:
        conv = self.get_conversation(conv_id)
        if not conv:
            conv = self.create_conversation()
            conv_id = conv["id"]

        message = {
            "id": str(uuid.uuid4())[:8],
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        conv["messages"].append(message)
        conv["updated_at"] = datetime.now().isoformat()

        # Auto-title from first user message
        if role == "user" and len(conv["messages"]) == 1:
            conv["title"] = content[:60] + ("..." if len(content) > 60 else "")

        self._save(conv_id, conv)
        return message

    def get_context_messages(self, conv_id: str, max_messages: int = 50) -> list:
        conv = self.get_conversation(conv_id)
        if not conv:
            return []
        messages = conv.get("messages", [])
        return messages[-max_messages:]

    def delete_conversation(self, conv_id: str) -> bool:
        path = self._conv_path(conv_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def _save(self, conv_id: str, data: dict):
        with open(self._conv_path(conv_id), "w") as f:
            json.dump(data, f, indent=2, default=str)
