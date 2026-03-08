"""
Octopus AI — Code Tentacle 💻
Execute Python code in a sandboxed environment with strict resource limits.
"""
import asyncio
import sys
import tempfile
import os
import resource
from tools import BaseTool


def set_resource_limits():
    """Set strict limits on the subprocess to prevent fork bombs and memory leaks."""
    try:
        # Limit memory to ~256MB
        mb = 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (256 * mb, 256 * mb))
        # Limit CPU time to 10 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        # Prevent creating core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Limit number of processes (prevent fork bombs)
        resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
    except (ValueError, OSError) as e:
        # Some OSes (like certain macOS versions) might not support all limits
        pass


class CodeTool(BaseTool):
    name = "code_execute"
    description = "Execute Python code and return the output. Code runs in a strict resource-limited subprocess."
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 10, max: 30)"
            }
        },
        "required": ["code"]
    }

    async def execute(self, code: str, timeout: int = 10, **kwargs) -> dict:
        timeout = min(max(timeout, 1), 30) # Clamp timeout between 1s and 30s
        tmp_path = None
        
        try:
            # Create an isolated workspace directory inside /tmp
            workspace_dir = tempfile.mkdtemp(prefix="octopus_code_")
            
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir=workspace_dir
            ) as f:
                f.write(code)
                tmp_path = f.name

            # Run with preexec_fn to set limits BEFORE the code executes
            process = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_dir,
                preexec_fn=set_resource_limits
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except:
                    pass
                return {
                    "status": "timeout",
                    "error": f"Code execution timed out after {timeout}s",
                    "stdout": "",
                    "stderr": ""
                }

            stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:5000]
            
            # Check if terminated by signal (like SIGKILL from CPU limit)
            if process.returncode is not None and process.returncode < 0:
                stderr_str += f"\nProcess terminated by signal {-process.returncode} (Resource limit exceeded or Killed)"

            return {
                "status": "success" if process.returncode == 0 else "error",
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "stdout": "", "stderr": ""}
        finally:
            # Cleanup the workspace
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if workspace_dir and os.path.exists(workspace_dir):
                    os.rmdir(workspace_dir)
            except:
                pass
