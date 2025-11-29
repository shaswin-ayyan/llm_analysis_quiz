import logging
import os
import aiohttp
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger("uvicorn.error")

class BrowserManager:
    def __init__(self):
        pass

    async def extract_page_data(self, url: str, download_dir: str) -> dict:
        """
        Renders the page, extracts text/links, and downloads relevant files.
        Returns structured data.
        """
        os.makedirs(download_dir, exist_ok=True)
        
        data = {
            "page_text": "",
            "html_content": "",
            "files": {
                "csv": [],
                "pdf": [],
                "html": [], # For tables
                "audio": [],
                "json": []
            },
            "links": []
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            
            try:
                logger.info(f"Navigating to {url}...")
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(2000) # Wait for JS
                
                content = await page.content()
                data["html_content"] = content
                
                # Extract text
                # We use BS4 for better text extraction than page.inner_text() sometimes
                soup = BeautifulSoup(content, "html.parser")
                data["page_text"] = soup.get_text(separator="\n").strip()
                
                # Extract Links & Audio
                # 1. Audio tags
                for audio in soup.find_all("audio"):
                    src = audio.get("src")
                    if src:
                        full_url = urljoin(url, src)
                        local_path = await self._download_file(full_url, download_dir)
                        if local_path:
                            data["files"]["audio"].append(local_path)
                    
                    # Sources inside audio
                    for source in audio.find_all("source"):
                        src = source.get("src")
                        if src:
                            full_url = urljoin(url, src)
                            local_path = await self._download_file(full_url, download_dir)
                            if local_path:
                                data["files"]["audio"].append(local_path)

                # 2. Links (A tags)
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    data["links"].append(full_url)
                    
                    lower_href = href.lower()
                    if lower_href.endswith(".csv"):
                        local_path = await self._download_file(full_url, download_dir)
                        if local_path:
                            data["files"]["csv"].append(local_path)
                    elif lower_href.endswith(".pdf"):
                        local_path = await self._download_file(full_url, download_dir)
                        if local_path:
                            data["files"]["pdf"].append(local_path)
                    elif lower_href.endswith(".json"):
                        local_path = await self._download_file(full_url, download_dir)
                        if local_path:
                            data["files"]["json"].append(local_path)
                    elif lower_href.endswith((".mp3", ".wav", ".ogg", ".opus")):
                        local_path = await self._download_file(full_url, download_dir)
                        if local_path:
                            data["files"]["audio"].append(local_path)

                # 3. Check for HTML tables? 
                # If there are tables, maybe save the HTML itself as a "file" for load_html_tables?
                if soup.find("table"):
                    table_file = os.path.join(download_dir, "tables.html")
                    with open(table_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    data["files"]["html"].append(table_file)

            except Exception as e:
                logger.error(f"Browser extraction failed: {e}")
            finally:
                await browser.close()
                
        return data

    async def _download_file(self, url: str, download_dir: str) -> str:
        """
        Downloads a file and returns the local path.
        """
        try:
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "downloaded_file"
            
            # Handle Google Drive or other weird URLs? 
            # For now assume direct links as per prompt "Preserve original filenames"
            
            local_path = os.path.join(download_dir, filename)
            
            # If already exists, maybe skip or overwrite? Overwrite for safety.
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(local_path, "wb") as f:
                            f.write(content)
                        return local_path
                    else:
                        logger.warning(f"Failed to download {url}: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return None

# Global instance
browser_manager = BrowserManager()

async def render_page_with_retries(url: str, retries: int = 3) -> str:
    """
    Renders a page using Playwright and returns the HTML content.
    If the URL points to a file (CSV, JSON, etc.), it downloads and returns the text content directly.
    Retries on failure.
    """
    # 1. Try fast fetch with aiohttp first to check Content-Type
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    # If it's not HTML, return text directly
                    if "text/html" not in content_type:
                        logger.info(f"Direct fetch for {url} (Content-Type: {content_type})")
                        # Try to decode as text
                        try:
                            text = await resp.text()
                            return text
                        except UnicodeDecodeError:
                            # Binary file? Return repr or empty? 
                            # For now, if we can't decode, maybe it's not useful text.
                            return f"[Binary Content: {content_type}]"
    except Exception as e:
        logger.warning(f"Direct fetch failed for {url}: {e}")
        # Fallback to Playwright if direct fetch fails (maybe JS needed for auth/redirects?)

    # 2. Fallback to Playwright
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                page = await browser.new_page()
                try:
                    logger.info(f"Rendering {url} (Attempt {attempt+1})")
                    
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=60000)
                    except Exception as e:
                        if "Download is starting" in str(e):
                            logger.info(f"Playwright triggered download for {url}. Assuming file content.")
                            return "Error: URL triggered a download. Please use load_csv_metadata or similar if this is a file."
                        raise e

                    await page.wait_for_timeout(2000)
                    content = await page.content()
                    return content
                finally:
                    await browser.close()
        except Exception as e:
             logger.warning(f"Browser launch failed: {e}")
             await asyncio.sleep(2)
            
    return ""
