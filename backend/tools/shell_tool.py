"""
Octopus AI — Shell Tentacle 🐚
Execute shell commands with safety checks.
"""
import asyncio
import os
import re
import shutil
import functools
import subprocess
import resource
from tools import BaseTool


@functools.lru_cache(maxsize=1)
def _unshare_available() -> bool:
    """True only if unprivileged `unshare -r -n` actually works on this host.

    Many systems disable unprivileged user namespaces; blindly prefixing every
    command with `unshare` there would make them all fail. We probe once."""
    if not shutil.which("unshare"):
        return False
    try:
        r = subprocess.run(
            ["unshare", "-r", "-n", "true"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


# Best-effort denylist for catastrophic commands. This is a guardrail, not a
# security boundary — the shell tentacle can be disabled entirely in Settings.
_DESTRUCTIVE = [
    (r"\brm\b.*\s-\S*[rf]\S*\s+(/|/\*|~)(\s|$)", "recursive force delete of root/home"),
    (r"--no-preserve-root", "rm --no-preserve-root"),
    (r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "fork bomb"),
    (r"\bmkfs(\.\w+)?\b", "mkfs (format filesystem)"),
    (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|vd|hd)", "dd to raw disk"),
    (r">\s*/dev/(sd|nvme|vd|hd)", "overwrite raw disk"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "power control"),
]


def _match_destructive(command: str):
    for pattern, name in _DESTRUCTIVE:
        if re.search(pattern, command):
            return name
    return None


def set_resource_limits_shell():
    """Set limits on shell subprocesses to prevent resource exhaustion."""
    try:
        # Limit memory to ~512MB for shell commands (they usually need more than raw code)
        mb = 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (512 * mb, 512 * mb))
        # Limit CPU time to 60 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
        # Prevent creating core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass

class ShellTool(BaseTool):
    name = "shell_execute"
    description = "Execute a shell command safely. Commands are capped at 512MB RAM and 60s CPU time to prevent system hangs."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command (optional, defaults to home)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)"
            }
        },
        "required": ["command"]
    }

    async def execute(self, command: str, cwd: str = None, timeout: int = 30, **kwargs) -> dict:
        from config import get_workspace_dir
        from pathlib import Path

        WORKSPACE_DIR = get_workspace_dir()

        # Resolve & jail the working directory to the workspace
        if cwd:
            requested_cwd = Path(cwd).expanduser()
            if not requested_cwd.is_absolute():
                requested_cwd = (WORKSPACE_DIR / cwd).resolve()
            else:
                requested_cwd = requested_cwd.resolve()
            if not requested_cwd.is_relative_to(WORKSPACE_DIR):
                return {"status": "error", "error": "CWD must be inside the restricted workspace"}
            cwd_path = str(requested_cwd)
        else:
            cwd_path = str(WORKSPACE_DIR)

        # Refuse catastrophic commands (targeted denylist).
        hit = _match_destructive(command)
        if hit:
            return {"status": "blocked", "error": f"Refused: command matches a destructive pattern ({hit})."}

        # Sever network via unshare only when it actually works on this host.
        unshare_prefix = "unshare -r -n " if _unshare_available() else ""

        try:
            process = await asyncio.create_subprocess_shell(
                f"{unshare_prefix}{command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd_path,
                env={**os.environ},
                preexec_fn=set_resource_limits_shell
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "status": "timeout",
                    "error": f"Command timed out after {timeout}s",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1
                }

            stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

            return {
                "status": "success" if process.returncode == 0 else "error",
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode,
                "command": command,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": -1
            }
