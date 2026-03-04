"""
Octopus AI — File Tentacle 📁
Read, write, list, and search files.
"""
import os
import glob
from pathlib import Path
from tools import BaseTool


class FileTool(BaseTool):
    name = "file_operations"
    description = "Perform file system operations: read files, write files, list directories, search for files by name or content. Use for viewing code, editing files, exploring project structure."
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "list", "search", "info", "mkdir", "delete"],
                "description": "The file operation to perform"
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write operation)"
            },
            "pattern": {
                "type": "string",
                "description": "Search pattern (for search operation, supports glob)"
            }
        },
        "required": ["operation", "path"]
    }

    async def execute(self, operation: str, path: str, content: str = None, pattern: str = None, **kwargs) -> dict:
        path = os.path.expanduser(path)

        try:
            if operation == "read":
                return self._read(path)
            elif operation == "write":
                return self._write(path, content or "")
            elif operation == "list":
                return self._list(path)
            elif operation == "search":
                return self._search(path, pattern or "*")
            elif operation == "info":
                return self._info(path)
            elif operation == "mkdir":
                return self._mkdir(path)
            elif operation == "delete":
                return self._delete(path)
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _read(self, path: str) -> dict:
        if not os.path.exists(path):
            return {"status": "error", "error": f"File not found: {path}"}

        size = os.path.getsize(path)
        if size > 500_000:
            return {"status": "error", "error": f"File too large ({size} bytes). Max 500KB."}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "status": "success",
                "content": content,
                "path": path,
                "size": size,
                "lines": content.count("\n") + 1
            }
        except UnicodeDecodeError:
            return {"status": "error", "error": "Binary file, cannot read as text"}

    def _write(self, path: str, content: str) -> dict:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "status": "success",
            "message": f"Written {len(content)} chars to {path}",
            "path": path
        }

    def _list(self, path: str) -> dict:
        if not os.path.exists(path):
            return {"status": "error", "error": f"Directory not found: {path}"}

        entries = []
        try:
            for entry in sorted(os.listdir(path)):
                full = os.path.join(path, entry)
                entry_info = {
                    "name": entry,
                    "type": "directory" if os.path.isdir(full) else "file",
                }
                if os.path.isfile(full):
                    entry_info["size"] = os.path.getsize(full)
                entries.append(entry_info)
        except PermissionError:
            return {"status": "error", "error": f"Permission denied: {path}"}

        return {"status": "success", "path": path, "entries": entries[:100]}

    def _search(self, path: str, pattern: str) -> dict:
        results = []
        search_path = os.path.join(path, "**", pattern)
        for match in glob.glob(search_path, recursive=True)[:50]:
            results.append({
                "path": match,
                "type": "directory" if os.path.isdir(match) else "file"
            })
        return {"status": "success", "matches": results, "count": len(results)}

    def _info(self, path: str) -> dict:
        if not os.path.exists(path):
            return {"status": "error", "error": f"Path not found: {path}"}
        stat = os.stat(path)
        return {
            "status": "success",
            "path": path,
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

    def _mkdir(self, path: str) -> dict:
        os.makedirs(path, exist_ok=True)
        return {"status": "success", "message": f"Created directory: {path}"}

    def _delete(self, path: str) -> dict:
        if not os.path.exists(path):
            return {"status": "error", "error": f"Path not found: {path}"}
        if os.path.isfile(path):
            os.remove(path)
            return {"status": "success", "message": f"Deleted file: {path}"}
        return {"status": "error", "error": "Use shell for directory deletion (safety measure)"}
