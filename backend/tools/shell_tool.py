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

    async def execute(self, command: str, cwd: str = None, timeout: int = 30, **kwargs) -> dict:
        from config import get_data_dir
        from pathlib import Path
        import shutil
        
        WORKSPACE_DIR = (Path(get_data_dir()) / "workspace").resolve()
        WORKSPACE_DIR.mkdir(exist_ok=True)

        # Set or validate CWD
        if cwd:
            requested_cwd = Path(cwd).expanduser()
            if not requested_cwd.is_absolute():
                requested_cwd = (WORKSPACE_DIR / cwd).resolve()
            
            if not requested_cwd.is_relative_to(WORKSPACE_DIR):
                return {"status": "error", "error": f"CWD must be inside restricted workspace"}
            cwd_path = str(requested_cwd)
        else:
            cwd_path = str(WORKSPACE_DIR)

        # Prevent obvious absolute path escapes (heuristic security)
        if " /" in command or command.startswith("/"):
            return {"status": "blocked", "error": "Commands operating on root structural paths are blocked by sandbox policies."}

        unshare_prefix = ""
        if shutil.which("unshare"):
            unshare_prefix = "unshare -r -n "

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
