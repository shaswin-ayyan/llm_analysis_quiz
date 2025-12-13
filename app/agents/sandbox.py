import os
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

class CodeInterpreter:
    def __init__(self):
        self.api_key = settings.E2B_API_KEY
        if not self.api_key:
            logger.warning("E2B_API_KEY not set. Using local fallback (unsafe).")

    async def run_code(self, code: str, language: str = "python", files: list = None):
        """
        Executes code in a secure E2B sandbox or local fallback.
        files: List of paths to upload to the sandbox.
        """
        files = files or []
        
        if self.api_key:
            return await self._run_e2b(code, files)
        else:
            return await self._run_local(code, files)

    async def _run_e2b(self, code: str, files: list):
        from e2b_code_interpreter import Sandbox
        
        logger.info("Executing code in E2B Sandbox...")
        try:
            # Create sandbox
            sb = Sandbox.create()
            
            # Upload files
            for file_path in files:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        sb.files.write(os.path.basename(file_path), f)
            
            # Run code
            execution = sb.run_code(code)
            
            # Get output
            output = ""
            if execution.logs.stdout:
                output += "\n".join(execution.logs.stdout)
            if execution.logs.stderr:
                output += "\nErrors:\n" + "\n".join(execution.logs.stderr)
            if execution.error:
                output += f"\nException: {execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
                
            sb.kill()
            return output
            
        except Exception as e:
            logger.error(f"E2B Execution failed: {e}")
            logger.info("Falling back to local execution...")
            return await self._run_local(code, files)

    async def _run_local(self, code: str, files: list):
        """
        Fallback for local execution. WARNING: Unsafe.
        """
        logger.warning("Executing code LOCALLY. This is unsafe.")
        
        # Simple capture of stdout
        import sys
        from io import StringIO
        import pandas as pd # Ensure pandas is available for the code
        
        # We need to make sure the files are accessible. 
        # In local mode, they are already on disk.
        # But the code might expect them in the current directory.
        # We might need to change CWD or adjust paths in code?
        # For simplicity, we assume code uses absolute paths or we run in the workspace.
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = sys.stdout = StringIO()
        redirected_error = sys.stderr = StringIO()
        
        try:
            # Create a safe-ish globals dict
            local_scope = {
                "pd": pd,
                "print": print,
                "__builtins__": __builtins__
            }
            
            exec(code, local_scope)
            stdout = redirected_output.getvalue()
            stderr = redirected_error.getvalue()
            return stdout + ("\nSTDERR:\n" + stderr if stderr else "")
        except Exception as e:
            stdout = redirected_output.getvalue()
            stderr = redirected_error.getvalue()
            return f"{stdout}\nLocal Execution Error: {type(e).__name__}: {e}\nSTDERR:\n{stderr}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

code_interpreter = CodeInterpreter()
