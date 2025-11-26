import pandas as pd
import aiohttp
import pdfplumber
import logging
from io import StringIO, BytesIO
from urllib.parse import urlparse
from app.utils.parse_table import html_table_to_df, normalize_dataframe

logger = logging.getLogger(__name__)

# ============================================================
# PDF TOOL (NEW)
# ============================================================
async def read_pdf_tool(args, df=None):
    """
    Extracts text from a PDF.
    args:
      - path: str (URL or local path)
    """
    path = args.get("path") or args.get("url")
    if not path:
        raise ValueError("read_pdf_tool requires 'path'")

    parsed = urlparse(path)
    is_url = parsed.scheme in ("http", "https")

    pdf_file = None
    try:
        if is_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(path) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Failed to download PDF: {resp.status}")
                    data = await resp.read()
                    pdf_file = BytesIO(data)
        else:
            # Local file (mostly for testing)
            with open(path, "rb") as f:
                pdf_file = BytesIO(f.read())

        text_content = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        
        full_text = "\n".join(text_content)
        return {"text": full_text[:5000] + "..." if len(full_text) > 5000 else full_text}

    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return {"error": str(e)}

# ============================================================
# LOAD CSV TOOL (Updated)
# ============================================================
async def load_csv_tool(args, df):
    """
    Accepted keys: file_path, url, path, dataset, file, csv_path
    """
    file_path = (
        args.get("file_path")
        or args.get("url")
        or args.get("path")
        or args.get("dataset")
        or args.get("file")
        or args.get("csv_path")
    )

    if not file_path:
        raise ValueError("load_csv requires file_path")

    # If it looks like a PDF, redirect to PDF tool
    if file_path.lower().endswith(".pdf"):
        return await read_pdf_tool({"path": file_path})

    parsed = urlparse(file_path)
    is_url = parsed.scheme in ("http", "https")

    if is_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_path) as resp:
                raw = await resp.text()

        if "<html" in raw.lower():
            html_df = html_table_to_df(raw)
            html_df = normalize_dataframe(html_df)
            if not html_df.empty:
                return html_df
            raise RuntimeError(
                f"Expected CSV but got HTML. URL: {file_path}\nPreview: {raw[:200]!r}"
            )

        try:
            return pd.read_csv(StringIO(raw))
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse CSV from URL: {file_path}\nReason: {e}"
            )

    # Local
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                raw = handle.read()
            if "<html" in raw.lower():
                html_df = html_table_to_df(raw)
                html_df = normalize_dataframe(html_df)
                if not html_df.empty:
                    return html_df
        except Exception as e:
            logger.warning(f"Failed to read local file as HTML: {e}")
        raise RuntimeError(f"Failed to read local CSV '{file_path}': {e}")

# ============================================================
# CORRELATION TOOL
# ============================================================
async def correlation_tool(args, df):
    if df is None:
        return "Error: No dataframe loaded."
    x = args.get("column_x")
    y = args.get("column_y")
    if not x or not y:
        return "Error: Missing columns."
    return float(df[x].corr(df[y]))

# ============================================================
# SUMMARY STATS TOOL
# ============================================================
async def summary_stats_tool(args, df):
    if df is None:
        return "Error: No dataframe loaded."
    col = args.get("column")
    if col:
        return df[col].describe().to_dict()
    return df.describe().to_dict()

# ============================================================
# TOP GROUP BY TOOL
# ============================================================
async def top_group_by_tool(args, df):
    if df is None:
        return "Error: No dataframe loaded."
    by = args.get("group_by")
    col = args.get("value_col")
    n = args.get("n", 5)
    return df.groupby(by)[col].sum().sort_values(ascending=False).head(int(n)).to_dict()

# ============================================================
# FILTER TOOL
# ============================================================
async def filter_tool(args, df):
    if df is None: return "Error: No dataframe loaded."
    column = args.get("column")
    op = args.get("op")
    value = args.get("value")
    
    operators = {
        ">": df[column] > value,
        "<": df[column] < value,
        ">=": df[column] >= value,
        "<=": df[column] <= value,
        "==": df[column] == value,
        "!=": df[column] != value,
    }
    return df[operators[op]]