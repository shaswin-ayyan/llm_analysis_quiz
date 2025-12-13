import logging
import os
import pandas as pd
from app.agents.sandbox import code_interpreter
from app.router import query_llm
from app.config import settings

logger = logging.getLogger(__name__)

class DataAgent:
    def __init__(self):
        pass

    def _robust_load_csv(self, file_path: str):
        """
        Loads a CSV with robust dialect detection.
        Returns (df, separator).
        """
        import csv
        try:
            # Read the first 2KB to sniff the dialect
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(2048)
                f.seek(0)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                    sep = dialect.delimiter
                    has_header = sniffer.has_header(sample)
                    # Use detected delimiter
                    df = pd.read_csv(file_path, sep=sep, header=0 if has_header else None)
                    return df, sep
                except csv.Error:
                    # Fallback: Let Python engine guess
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    return df, None
        except Exception:
            # Final Fallback: Standard load
            df = pd.read_csv(file_path)
            return df, ","

    async def analyze_csv(self, file_path: str, query: str) -> str:
        """
        Analyzes a CSV file by generating Python code and running it in the sandbox.
        """
        try:
            # 1. Load CSV metadata (columns) with robust detection
            df, sep = self._robust_load_csv(file_path)
            columns = df.columns.tolist()
            head = df.head(3).to_string()
            
            logger.info(f"Analyzing CSV {file_path} with query: {query}")
            
            # 2. Generate Code using LLM
            sep_arg = f", sep='{sep}'" if sep and sep != ',' else ""
            
            prompt = f"""
            You are a Data Analyst. Write Python code to answer the following query about a CSV file.
            
            File: {os.path.basename(file_path)}
            Columns: {columns}
            Sample Data:
            {head}
            
            Query: {query}
            
            Requirements:
            - Use 'pandas' library.
            - Load the file using `df = pd.read_csv('{os.path.basename(file_path)}'{sep_arg})`.
            - Print the final answer to stdout.
            - Do not generate markdown formatting (no ```python). Just the code.
            """
            
            code = await query_llm([{"role": "user", "content": prompt}], model=settings.MODEL_PRIMARY)
            
            # Clean code
            code = code.replace("```python", "").replace("```", "").strip()
            
            # 3. Execute Code
            result = await code_interpreter.run_code(code, files=[file_path])
            
            return result.strip()
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return f"Error analyzing data: {str(e)}"

data_agent = DataAgent()
