"""
Octopus AI — Shell Tentacle 🐚
Execute shell commands with safety checks.
"""
import asyncio
import os
from tools import BaseTool


class ShellTool(BaseTool):
    name = "shell_execute"
    description = "Execute a shell command on the local system. Use for running programs, scripts, package managers, git commands, and system operations. Returns stdout, stderr, and exit code."
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

    # Commands that are blocked for safety
    DANGEROUS_PATTERNS = [
        "rm -rf /",
        "mkfs.",
        ":(){:|:&};:",
        "dd if=/dev/zero of=/dev/sd",
        "> /dev/sd",
    ]

    async def execute(self, command: str, cwd: str = None, timeout: int = 30, **kwargs) -> dict:
        # Safety check
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command:
                return {
                    "status": "blocked",
                    "error": f"Command blocked for safety: contains dangerous pattern '{pattern}'",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1
                }

        if not cwd:
            cwd = os.path.expanduser("~")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ}
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
