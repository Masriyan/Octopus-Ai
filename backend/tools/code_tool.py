"""
Octopus AI — Code Tentacle 💻
Execute Python code in a sandboxed environment.
"""
import asyncio
import sys
import tempfile
import os
from tools import BaseTool


class CodeTool(BaseTool):
    name = "code_execute"
    description = "Execute Python code and return the output. Useful for calculations, data processing, generating outputs, or running quick scripts. Code runs in a subprocess for isolation."
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 15)"
            }
        },
        "required": ["code"]
    }

    async def execute(self, code: str, timeout: int = 15, **kwargs) -> dict:
        # Write code to a temporary file
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir="/tmp"
            ) as f:
                f.write(code)
                tmp_path = f.name

            process = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/tmp"
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "status": "timeout",
                    "error": f"Code execution timed out after {timeout}s",
                    "stdout": "",
                    "stderr": ""
                }

            stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

            return {
                "status": "success" if process.returncode == 0 else "error",
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "stdout": "", "stderr": ""}
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
