"""
Octopus AI — Memory Manager
Persistent conversation storage and context management.
"""
import json
import uuid
import os
from datetime import datetime
from typing import List, Dict, Optional
from config import get_data_dir
from vector_memory import VectorMemory


class MemoryManager:
    """Manages short-term conversation context and long-term vector embeddings."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.conv_dir = os.path.join(self.data_dir, "conversations")
        os.makedirs(self.conv_dir, exist_ok=True)
        
        # Initialize Vector Memory for cross-session RAG
        self.vector_db = VectorMemory(persist_directory=os.path.join(self.data_dir, "vector_db"))

    def _conv_path(self, conv_id: str) -> str:
        return os.path.join(self.conv_dir, f"{conv_id}.json")

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

        msg_id = str(uuid.uuid4())[:8] # Defined msg_id
        msg = {
            "id": msg_id,
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
            
        conv["messages"].append(msg)
        conv["updated_at"] = msg["timestamp"]
        
        # Auto-generate title for first user message
        if role == "user" and len([m for m in conv["messages"] if m["role"] == "user"]) == 1:
            conv["title"] = content[:30] + "..." if len(content) > 30 else content
            
        self._save(conv_id, conv) # Changed _save_conversation to _save
        
        # Store in Vector Memory in the background
        if role in ("user", "assistant"):
             try:
                 # Don't embed massive text dumps (like full file reads)
                 if len(content) < 4000:
                     import asyncio # Kept as per instruction, though not used for sync call
                     # In a real app we'd dispatch this to a background task runner,
                     # here we just run it synchronously for simplicity in the prototype
                     self.vector_db.add_conversation_message(conv_id, msg_id, role, content)
             except Exception as e:
                 print(f"Vector embedding failed: {e}")
                 
        return msg # Fixed typo: msgessage to msg

    def get_context_messages(self, conv_id: str, max_messages: int = 50) -> list:
        conv = self.get_conversation(conv_id)
        if not conv:
            return []
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
