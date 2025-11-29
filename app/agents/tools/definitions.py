import pandas as pd
import pdfplumber
import logging
import io
import base64
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from app.agents.sandbox import PythonSandbox
from app.utils.browser import render_page_with_retries
from app.utils.url_utils import extract_urls
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Sandbox
sandbox = PythonSandbox()

async def python_execute(args, df=None):
    """
    Executes Python code in the sandbox.
    args:
      - code: str
    """
    code = args.get("code")
    if not code:
        return {"error": "No code provided"}
    
    return sandbox.execute(code)

async def load_csv_metadata(args, df=None):
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
        # 1. Read first few rows with default header behavior
        df_default = pd.read_csv(path, nrows=5)
        
        # 2. Read first few rows assuming NO header
        df_no_header = pd.read_csv(path, header=None, nrows=5)
        
        # 3. Check dtypes
        # If default read has all object (string) columns, but no-header read has some non-object (numeric) columns,
        # it implies the first row was actually data (numbers) but got treated as header.
        default_is_all_obj = all(dtype == 'object' for dtype in df_default.dtypes)
        no_header_has_numeric = any(dtype != 'object' for dtype in df_no_header.dtypes)
        
        has_header = True
        if default_is_all_obj and no_header_has_numeric:
            has_header = False
            
        # Load the full dataframe based on detection
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

async def load_excel_metadata(args, df=None):
    """
    Loads an Excel file and returns metadata.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        df = pd.read_excel(path)
        sandbox.globals["df"] = df
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "message": "DataFrame loaded into sandbox as variable 'df'"
        }
    except Exception as e:
        return {"error": str(e)}

async def load_json_metadata(args, df=None):
    """
    Loads a JSON file and returns metadata.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        df = pd.read_json(path)
        sandbox.globals["df"] = df
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "message": "DataFrame loaded into sandbox as variable 'df'"
        }
    except Exception as e:
        return {"error": str(e)}

async def load_pdf(args, df=None):
    """
    Extracts text and tables from a PDF.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        text_content = []
        tables = []
        
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {i+1} ---\n{text}")
                
                page_tables = page.extract_tables()
                for tbl in page_tables:
                    tables.append(tbl)
                    
        return {
            "text": "\n".join(text_content),
            "tables": tables
        }
    except Exception as e:
        return {"error": str(e)}

async def load_html_tables(args, df=None):
    """
    Extracts tables from an HTML file.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
            
        dfs = pd.read_html(html)
        tables = []
        for i, df in enumerate(dfs):
            tables.append({
                "table_index": i,
                "columns": list(df.columns),
                "data": df.head(5).to_dict(orient="records"),
                "full_data_summary": f"{len(df)} rows"
            })
            
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}

async def plot_to_base64(args, df=None):
    """
    Executes plotting code and returns base64 image.
    args:
      - code: str
    """
    code = args.get("code")
    if not code:
        return {"error": "No code provided"}
    
    try:
        plt.clf()
        res = sandbox.execute(code)
        if res.get("error"):
            return res
            
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode("utf-8")
        plt.clf()
        
        return {
            "stdout": res.get("stdout"),
            "image_base64": img_str
        }
    except Exception as e:
        return {"error": str(e)}

async def extract_urls_tool(args, df=None):
    """
    Extracts URLs from text.
    args:
      - text: str
      - base_url: str (optional)
    """
    text = args.get("text")
    base_url = args.get("base_url")
    if not text:
        return {"error": "text argument is required."}
    
    urls = extract_urls(text, base_url)
    return {"urls": urls}

async def scrape_url_tool(args, df=None):
    """
    Visits a URL and returns the text content.
    args:
      - url: str
    """
    url = args.get("url")
    if not url:
        return {"error": "url argument is required."}
    
    try:
        # Use AI Pipe Proxy as requested
        proxy_base = settings.AIPIPE_PROXY_URL.rstrip("/")
        if not url.startswith(proxy_base):
            # Ensure we don't double proxy if already proxied
            target_url = f"{proxy_base}/{url}"
        else:
            target_url = url
            
        logger.info(f"Scraping via Proxy: {target_url}")
        html = await render_page_with_retries(target_url)
        if not html:
            return {"error": "Failed to load page (empty content)."}
        
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n").strip()
        import re
        text = re.sub(r"\n\s*\n", "\n\n", text)
        
        return {"content": text[:10000] + "..." if len(text) > 10000 else text}
    except Exception as e:
        logger.error(f"Scrape tool failed: {e}")
        return {"error": f"Error scraping URL: {str(e)}"}

async def extract_archive(args, df=None):
    """
    Extracts ZIP, TAR, TAR.GZ archives.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "path argument is required."}
    
    import zipfile
    import tarfile
    import os
    
    try:
        extract_dir = os.path.splitext(path)[0] + "_extracted"
        os.makedirs(extract_dir, exist_ok=True)
        
        extracted_files = []
        
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                extracted_files = zip_ref.namelist()
        elif tarfile.is_tarfile(path):
            with tarfile.open(path, 'r') as tar_ref:
                tar_ref.extractall(extract_dir)
                extracted_files = tar_ref.getnames()
        else:
            return {"error": "Unsupported archive format or not an archive."}
            
        # Return absolute paths of extracted files
        abs_files = [os.path.join(extract_dir, f) for f in extracted_files]
        return {
            "message": f"Extracted {len(extracted_files)} files to {extract_dir}",
            "files": abs_files
        }
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
