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
                    
                    # Check Content-Type for potential files
                    # We check if extension matches OR if we should probe dynamic links (optional, but requested fix implies robustness)
                    # The user request specifically mentioned "url.endswith('.csv') misses dynamic links".
                    # So we should probably check content type for ALL links? No, that's too slow.
                    # We will check content type if extension matches OR if it looks like a download link?
                    # The prompt said: "Before skipping a link, perform a HEAD request." 
                    # That implies checking everything? That might be too heavy.
                    # Let's stick to the prompt: "The Problem: url.endswith('.csv') misses dynamic links... The Fix: Before skipping a link, perform a HEAD request."
                    # This phrasing is slightly ambiguous. "Before skipping" might mean "If it doesn't match extension, check HEAD".
                    # But checking HEAD for every link on a page (could be 100s) is bad.
                    # Let's implement a smarter filter: Check if extension matches OR query params exist.
                    
                    is_candidate = False
                    ext_map = {
                        ".csv": "csv", 
                        ".pdf": "pdf", 
                        ".json": "json", 
                        ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".opus": "audio"
                    }
                    
                    # 1. Extension match
                    for ext, type_key in ext_map.items():
                        if lower_href.endswith(ext):
                            is_candidate = True
                            break
                    
                    # 2. Dynamic link match (e.g. download.php?id=...)
                    if not is_candidate and ("?" in lower_href or "download" in lower_href):
                        is_candidate = True
                        
                    if is_candidate:
                        # Perform HEAD request to verify MIME type
                        mime_type = await self._check_content_type(full_url)
                        
                        if mime_type:
                            if "csv" in mime_type or "spreadsheet" in mime_type or "text/plain" in mime_type:
                                local_path = await self._download_file(full_url, download_dir)
                                if local_path: data["files"]["csv"].append(local_path)
                            elif "pdf" in mime_type:
                                local_path = await self._download_file(full_url, download_dir)
                                if local_path: data["files"]["pdf"].append(local_path)
                            elif "json" in mime_type:
                                local_path = await self._download_file(full_url, download_dir)
                                if local_path: data["files"]["json"].append(local_path)
                            elif "audio" in mime_type:
                                local_path = await self._download_file(full_url, download_dir)
                                if local_path: data["files"]["audio"].append(local_path)

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

    async def _check_content_type(self, url: str) -> str:
        """
        Performs a HEAD request to check the Content-Type of a URL.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=5) as resp:
                    if resp.status == 200:
                        return resp.headers.get("Content-Type", "").lower()
                    # If HEAD fails (some servers don't support it), try GET with stream=True
                    if resp.status == 405:
                        async with session.get(url, allow_redirects=True, timeout=5) as get_resp:
                            if get_resp.status == 200:
                                return get_resp.headers.get("Content-Type", "").lower()
            return ""
        except Exception as e:
            logger.warning(f"Failed to check content type for {url}: {e}")
            return ""

    async def find_task_image_url(self, page_url: str) -> str:
        """
        Actively hunts for the task image using Playwright locators.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            try:
                await page.goto(page_url, wait_until="networkidle", timeout=60000)
                
                # STRATEGY 1: Look for Anchors linking to Images
                # Matches <a href="/project2/heatmap.png">
                # We use regex for extensions
                image_link = await page.locator('a[href$=".png"], a[href$=".jpg"], a[href$=".jpeg"]').first.get_attribute('href')
                
                if image_link:
                    full_url = urljoin(page_url, image_link)
                    logger.info(f"Found image via anchor: {full_url}")
                    return full_url

                # STRATEGY 2: Look for Image Tags directly
                # Matches <img src="...">
                img_src = await page.locator('img[src$=".png"], img[src$=".jpg"]').first.get_attribute('src')
                
                if img_src:
                    full_url = urljoin(page_url, img_src)
                    logger.info(f"Found image via img tag: {full_url}")
                    return full_url
                    
                # STRATEGY 3 (Fallback): Screenshot
                # We return a special URI scheme "screenshot://path" or just path?
                # User said: return f"file://{screenshot_path}"
                # But we need to save it to a persistent location, not /tmp if possible.
                # We'll save to current working directory or a temp dir.
                # Let's use os.getcwd()/workspace/screenshots if possible, or just "screenshot.png" in CWD.
                screenshot_path = os.path.abspath("page_screenshot.png")
                await page.screenshot(path=screenshot_path)
                logger.info(f"No image found. Took screenshot: {screenshot_path}")
                return f"file://{screenshot_path}"
                
            except Exception as e:
                logger.error(f"Image discovery failed: {e}")
                return ""
            finally:
                await browser.close()

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
