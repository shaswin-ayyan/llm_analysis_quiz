import io
import contextlib
import traceback
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pdfplumber
import bs4
import openpyxl
import csv
import json
import logging

logger = logging.getLogger(__name__)

# Whitelisted libraries available in the sandbox
ALLOWED_MODULES = {
    "pandas": pd,
    "numpy": np,
    "matplotlib": plt,
    "matplotlib.pyplot": plt,
    "pdfplumber": pdfplumber,
    "bs4": bs4,
    "openpyxl": openpyxl,
    "csv": csv,
    "json": json,
}

class PythonSandbox:
    def __init__(self, workspace_dir: str = "/workspace/runtime/"):
        self.workspace_dir = workspace_dir
        # Initialize global namespace with allowed modules
        self.globals = {name: mod for name, mod in ALLOWED_MODULES.items()}
        self.globals["__builtins__"] = __builtins__.copy()
        
        # Remove dangerous builtins
        dangerous = ["exec", "eval", "compile", "open", "input"]
        for d in dangerous:
            if d in self.globals["__builtins__"]:
                del self.globals["__builtins__"][d]

    def execute(self, code: str) -> dict:
        """
        Executes Python code in a sandboxed environment.
        Returns: { "stdout": "...", "result": "...", "error": "..." }
        """
        stdout_buffer = io.StringIO()
        result = None
        error = None

        try:
            # Capture stdout
            with contextlib.redirect_stdout(stdout_buffer):
                # Execute code
                # We use a shared globals dictionary to persist state between executions
                exec(code, self.globals) # nosec B102
                
                if "result" in self.globals:
                    result = self.globals["result"]

        except Exception:
            error = traceback.format_exc()

        return {
            "stdout": stdout_buffer.getvalue(),
            "result": str(result) if result is not None else None,
            "error": error
        }
