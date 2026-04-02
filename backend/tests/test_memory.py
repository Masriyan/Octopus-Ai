"""
Tests for MemoryManager — verifies all the fixed bugs and new features.
"""
import os
import json
import time
import pytest
from pathlib import Path
from memory import MemoryManager


@pytest.fixture
def memory_manager(tmp_path, monkeypatch):
    """Create a MemoryManager that uses a temp directory."""
    monkeypatch.setattr("memory.get_data_dir", lambda: str(tmp_path))
    return MemoryManager()


# ─── Create Conversation ──────────────────────────────────────────────

def test_create_conversation(memory_manager):
    conv = memory_manager.create_conversation("Test Chat")
    assert conv["id"]
    assert conv["title"] == "Test Chat"
    assert conv["messages"] == []
    assert "created_at" in conv


def test_create_conversation_persisted(memory_manager):
    conv = memory_manager.create_conversation("Persisted")
    path = memory_manager._conv_path(conv["id"])
    assert path.exists()
    with open(path) as f:
        data = json.load(f)
    assert data["title"] == "Persisted"


# ─── Add Message ──────────────────────────────────────────────────────

def test_add_message(memory_manager):
    conv = memory_manager.create_conversation()
    msg = memory_manager.add_message(conv["id"], "user", "Hello!")
    assert msg["role"] == "user"
    assert msg["content"] == "Hello!"
    assert "timestamp" in msg
    assert isinstance(msg["timestamp"], float)


def test_add_message_auto_title(memory_manager):
    conv = memory_manager.create_conversation()
    memory_manager.add_message(conv["id"], "user", "What is the meaning of life?")
    updated = memory_manager.get_conversation(conv["id"])
    assert updated["title"] == "What is the meaning of life?"


def test_add_message_auto_title_truncation(memory_manager):
    conv = memory_manager.create_conversation()
    long_msg = "A" * 50
    memory_manager.add_message(conv["id"], "user", long_msg)
    updated = memory_manager.get_conversation(conv["id"])
    assert updated["title"].endswith("...")
    assert len(updated["title"]) == 33  # 30 chars + "..."


def test_add_message_with_tool_calls(memory_manager):
    conv = memory_manager.create_conversation()
    tool_calls = [{"name": "shell_execute", "args": {"command": "ls"}}]
    msg = memory_manager.add_message(conv["id"], "assistant", "result", tool_calls=tool_calls)
    assert msg["tool_calls"] == tool_calls


# ─── Get Context Messages ────────────────────────────────────────────

def test_get_context_messages(memory_manager):
    conv = memory_manager.create_conversation()
    for i in range(10):
        memory_manager.add_message(conv["id"], "user", f"Message {i}")
    
    messages = memory_manager.get_context_messages(conv["id"], max_messages=5)
    assert len(messages) == 5
    assert messages[0]["content"] == "Message 5"
    assert messages[-1]["content"] == "Message 9"


def test_get_context_messages_empty(memory_manager):
    conv = memory_manager.create_conversation()
    messages = memory_manager.get_context_messages(conv["id"])
    assert messages == []


def test_get_context_messages_nonexistent(memory_manager):
    messages = memory_manager.get_context_messages("nonexistent")
    assert messages == []


# ─── List Conversations ──────────────────────────────────────────────

def test_list_conversations(memory_manager):
    memory_manager.create_conversation("Chat A")
    time.sleep(0.05)
    memory_manager.create_conversation("Chat B")
    
    convs = memory_manager.list_conversations()
    assert len(convs) == 2
    # Most recent first
    assert convs[0]["title"] == "Chat B"
    assert convs[1]["title"] == "Chat A"


def test_list_conversations_empty(memory_manager):
    convs = memory_manager.list_conversations()
    assert convs == []


# ─── Rename Conversation ─────────────────────────────────────────────

def test_rename_conversation(memory_manager):
    conv = memory_manager.create_conversation("Old Title")
    result = memory_manager.rename_conversation(conv["id"], "New Title")
    assert result is True
    updated = memory_manager.get_conversation(conv["id"])
    assert updated["title"] == "New Title"


def test_rename_nonexistent(memory_manager):
    result = memory_manager.rename_conversation("nonexistent", "Title")
    assert result is False


# ─── Export Conversation ──────────────────────────────────────────────

def test_export_json(memory_manager):
    conv = memory_manager.create_conversation("Export Test")
    memory_manager.add_message(conv["id"], "user", "Hello")
    memory_manager.add_message(conv["id"], "assistant", "Hi there!")
    
    exported = memory_manager.export_conversation(conv["id"], "json")
    data = json.loads(exported)
    assert data["title"] == "Hello"  # Auto-titled
    assert len(data["messages"]) == 2


def test_export_markdown(memory_manager):
    conv = memory_manager.create_conversation("MD Export")
    memory_manager.add_message(conv["id"], "user", "Hello")
    memory_manager.add_message(conv["id"], "assistant", "Hi!")
    
    exported = memory_manager.export_conversation(conv["id"], "markdown")
    assert "👤 User" in exported
    assert "🐙 Assistant" in exported
    assert "Hello" in exported


def test_export_nonexistent(memory_manager):
    result = memory_manager.export_conversation("nonexistent")
    assert result is None


# ─── Delete Conversation ─────────────────────────────────────────────

def test_delete_conversation(memory_manager):
    conv = memory_manager.create_conversation("To Delete")
    path = memory_manager._conv_path(conv["id"])
    assert path.exists()
    
    result = memory_manager.delete_conversation(conv["id"])
    assert result is True
    assert not path.exists()


def test_delete_nonexistent(memory_manager):
    result = memory_manager.delete_conversation("nonexistent")
    assert result is False


# ─── Path Handling (Bug Regression) ──────────────────────────────────

def test_conv_path_returns_path_object(memory_manager):
    """Regression: _conv_path must return Path, not str."""
    path = memory_manager._conv_path("test")
    assert isinstance(path, Path)


def test_conv_dir_is_path(memory_manager):
    """Regression: conv_dir must be a Path object."""
    assert isinstance(memory_manager.conv_dir, Path)
