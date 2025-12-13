import pandas as pd
import pdfplumber
import logging
import io
import base64
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from app.agents.sandbox import code_interpreter
from app.utils.browser import render_page_with_retries
from app.utils.url_utils import extract_urls
from app.config import settings

logger = logging.getLogger(__name__)

async def analyze_image(args, df=None):
    """
    Analyzes an image using Gemini.
    args:
      - path: str
      - prompt: str
    """
    path = args.get("path")
    prompt = args.get("prompt", "Describe this image.")
    if not path:
        return {"error": "No path provided"}
    
    import httpx
    import mimetypes
    
    try:
        # 1. Read and Encode Image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
            
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "image/png" # Default fallback
            
        # 2. Prepare Request
        # We use the configured AUDIO_MODEL (or we should have a VISION_MODEL, but let's reuse AUDIO_MODEL or WORKER_MODEL if multimodal)
        # Settings.WORKER_MODEL is "alibaba/tongyi-deepresearch-30b-a3b" which might not be multimodal?
        # Settings.AUDIO_MODEL is "google/gemini-2.0-flash-lite-001" which IS multimodal.
        # Let's use AUDIO_MODEL for now as it's definitely Gemini.
        model = settings.AUDIO_MODEL
        
        # Determine Provider/URL
        if settings.USE_AIPIPE:
            url = settings.AIPIPE_BASE_URL.rstrip("/") + "/chat/completions"
            api_key = settings.AIPIPE_API_KEY or settings.OPENAI_API_KEY
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ]
            }
            
        else:
            return {"error": "Direct Gemini API not implemented for image yet. Enable AIPIPE."}

        # 3. Send Request
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            
        if resp.status_code != 200:
            return {"error": f"Image analysis failed: {resp.status_code} {resp.text}"}
            
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {"analysis": text}

    except Exception as e:
        return {"error": str(e)}

async def download_file(args, df=None):
    """
    Downloads a file from a URL to the workspace.
    args:
      - url: str
    """
    url = args.get("url")
    if not url:
        return {"error": "url argument is required."}
    
    import httpx
    import os
    from urllib.parse import urlparse
    
    try:
        # Use proxy if needed (similar to scrape_url)
        proxy_base = settings.AIPIPE_PROXY_URL.rstrip("/")
        if not url.startswith(proxy_base) and not url.startswith("http://localhost"):
             # Only proxy external URLs if needed, but for localhost test server we shouldn't proxy
             # Actually, scrape_url logic was:
             # if not url.startswith(proxy_base): target_url = f"{proxy_base}/{url}"
             # But for localhost, we must NOT proxy.
             pass
             
        # Simple download
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"error": f"Download failed: {resp.status_code}"}
            
            # Determine filename
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename:
                filename = "downloaded_file"
                
            # Save to workspace
            # We assume CWD is workspace or we use absolute path
            # Let's use a 'downloads' folder in CWD
            save_dir = os.path.join(os.getcwd(), "workspace", "downloads")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            
            with open(save_path, "wb") as f:
                f.write(resp.content)
                
            return {
                "path": save_path, 
                "filename": filename,
                "message": f"File downloaded to {save_path}. IMPORTANT: In python_execute, access this file as '{filename}' (it is in the current directory)."
            }
            
    except Exception as e:
        return {"error": str(e)}

async def transcribe_audio(args, df=None):
    """
    Transcribes audio using Gemini.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    import httpx
    import mimetypes
    
    try:
        # 1. Read and Encode Audio
        with open(path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")
            
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "audio/mpeg" # Default fallback
            
        # 2. Prepare Request
        # We use the configured AUDIO_MODEL
        model = settings.AUDIO_MODEL
        
        # Determine Provider/URL
        if settings.USE_AIPIPE:
            url = settings.AIPIPE_BASE_URL.rstrip("/") + "/chat/completions"
            api_key = settings.AIPIPE_API_KEY or settings.OPENAI_API_KEY
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # OpenAI-compatible Multimodal Payload (for AIPipe/OpenRouter)
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe this audio file exactly. If there are numbers, write them as digits (e.g., '219' not 'two one nine')."},
                            {
                                "type": "input_audio", 
                                "input_audio": {
                                    "data": audio_data,
                                    "format": "mp3" if "mp3" in mime_type else "wav" # Simplified mapping
                                }
                            }
                        ]
                    }
                ]
            }
            # Note: OpenRouter/AIPipe audio format might differ. 
            # Standard OpenAI is "input_audio": {"data": ..., "format": ...}
            # But Gemini via OpenRouter might accept image_url style or specific gemini format?
            # Let's try the standard OpenAI audio format first.
            # If that fails, we might need to use "image_url" style with data URI for some providers, 
            # but audio is specific.
            # Actually, for Gemini via OpenAI compat, it's often:
            # content: [{"type": "text", ...}, {"type": "image_url", "image_url": {"url": "data:audio/mp3;base64,..."}}]
            # Let's try the data URI approach which is more common for "multimodal" adapters.
            
            payload["messages"][0]["content"][1] = {
                "type": "image_url", # Often used for generic file inputs in adapters
                "image_url": {
                    "url": f"data:{mime_type};base64,{audio_data}"
                }
            }
            
        else:
            # Direct Gemini API
            # url = ...
            return {"error": "Direct Gemini API not implemented for audio yet. Enable AIPIPE."}

        # 3. Send Request
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            
        if resp.status_code != 200:
            return {"error": f"Transcription failed: {resp.status_code} {resp.text}"}
            
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {"transcription": text}

    except Exception as e:
        return {"error": str(e)}


async def python_execute(args, df=None):
    """
    Executes Python code in the sandbox.
    args:
      - code: str
    """
    code = args.get("code")
    if not code:
        return {"error": "No code provided"}
    
    # Use code_interpreter
    # Auto-Sync: Scan workspace/downloads and upload all files to sandbox
    import os
    files_to_sync = []
    downloads_dir = os.path.join(os.getcwd(), "workspace", "downloads")
    if os.path.exists(downloads_dir):
        for root, _, files in os.walk(downloads_dir):
            for file in files:
                files_to_sync.append(os.path.join(root, file))
                
    result = await code_interpreter.run_code(code, files=files_to_sync)
    return {"stdout": result}

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
            
        # sandbox.globals["df"] = df # Cannot set globals in remote sandbox easily this way
        # For now, we just return metadata. The worker should load the CSV in its own code.
        
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "has_header": has_header,
            "message": "CSV metadata loaded. To analyze, write Python code that reads this CSV."
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
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "message": "Excel metadata loaded. To analyze, write Python code that reads this Excel file."
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
        return {
            "columns": list(df.columns),
            "num_rows": len(df),
            "first_5_rows": df.head().to_dict(orient="records"),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "message": "JSON metadata loaded. To analyze, write Python code that reads this JSON file."
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
        # We can't easily get the plot from remote sandbox or local exec without saving to file
        # For now, let's just run the code and hope it saves a file we can read?
        # Or just return stdout.
        res = await code_interpreter.run_code(code)
        return {"stdout": res, "message": "Plotting not fully supported in current sandbox mode. Ensure code saves image to disk."}
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
                # Security fix: Prevent Zip Slip
                for member in zip_ref.namelist():
                    member_path = os.path.join(extract_dir, member)
                    if not os.path.abspath(member_path).startswith(os.path.abspath(extract_dir)):
                        raise Exception(f"Zip Slip attempt detected: {member}")
                zip_ref.extractall(extract_dir) # nosec B202
                extracted_files = zip_ref.namelist()
        elif tarfile.is_tarfile(path):
            with tarfile.open(path, 'r') as tar_ref:
                # Security fix: use filter='data' to prevent Zip Slip (Python 3.11+)
                tar_ref.extractall(extract_dir, filter='data')
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
