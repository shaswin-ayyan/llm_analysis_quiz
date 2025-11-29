import pandas as pd
import logging
from app.sandbox.python_execute import PythonSandbox

logger = logging.getLogger(__name__)

# Shared sandbox instance
sandbox = PythonSandbox()

async def load_csv_metadata(args):
    """
    Loads a CSV and returns metadata with robust header detection.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        # Heuristic to detect if header is missing
        df_default = pd.read_csv(path, nrows=5)
        df_no_header = pd.read_csv(path, header=None, nrows=5)
        
        default_is_all_obj = all(dtype == 'object' for dtype in df_default.dtypes)
        no_header_has_numeric = any(dtype != 'object' for dtype in df_no_header.dtypes)
        
        has_header = True
        if default_is_all_obj and no_header_has_numeric:
            has_header = False
            
        if has_header:
            df = pd.read_csv(path)
        else:
            df = pd.read_csv(path, header=None)
            
        sandbox.globals["df"] = df
        
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "has_header": has_header,
            "message": "DataFrame loaded into sandbox as variable 'df'. Check 'has_header' field!"
        }
    except Exception as e:
        return {"error": str(e)}
