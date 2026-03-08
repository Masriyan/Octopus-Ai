"""
Octopus AI — Shell Tentacle 🐚
Execute shell commands with safety checks.
"""
import asyncio
import os
import resource
from tools import BaseTool


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
