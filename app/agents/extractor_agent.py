import logging
import os
import uuid
import base64
import aiohttp
import re
from app.utils.browser import browser_manager
from app.config import settings

logger = logging.getLogger(__name__)

class ExtractorAgent:
    def __init__(self):
        pass

    async def extract(self, url: str, base_workspace: str) -> dict:
        """
        Extracts all data from the page.
        Returns:
        {
          "question_text": "...",
          "page_text": "...",
          "submit_url": "...",
          "files": { ... }
        }
        """
        unique_id = str(uuid.uuid4())
        workspace_dir = os.path.join(base_workspace, "files", unique_id)
        
        logger.info(f"Starting extraction for {url} in {workspace_dir}")
        
        # 1. Page Rendering & File Download
        data = await browser_manager.extract_page_data(url, workspace_dir)
        
        # 2. Audio Transcription
        audio_transcript = ""
        if data["files"]["audio"]:
            for audio_path in data["files"]["audio"]:
                logger.info(f"Transcribing audio: {audio_path}")
                transcript = await self._transcribe_audio(audio_path)
                if transcript:
                    audio_transcript += f"\n[Audio Transcript]: {transcript}\n"
        
        # 3. Identify Question
        # The question is usually in the text or audio.
        # We combine them.
        full_text = data["page_text"] + "\n" + audio_transcript
        
        # 4. Identify Submit URL
        # We look for forms or links with "submit"
        submit_url = self._find_submit_url(data["html_content"], data["links"], url)
        
        return {
            "question_text": full_text.strip(), # The reasoning agent will parse this
            "page_text": data["page_text"],
            "submit_url": submit_url,
            "files": data["files"],
            "links": data["links"]
        }

    async def _transcribe_audio(self, file_path: str) -> str:
        """
        Transcribes audio using Gemini.
        """
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set, skipping transcription.")
            return ""

        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()
            
            b64_audio = base64.b64encode(audio_data).decode("utf-8")
            
            model = "gemini-2.0-flash"
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
            
            mime_type = "audio/mp3"
            if file_path.endswith(".wav"): mime_type = "audio/wav"
            elif file_path.endswith(".ogg"): mime_type = "audio/ogg"
            elif file_path.endswith(".opus"): mime_type = "audio/opus"

            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Transcribe this audio file exactly."},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_audio
                            }
                        }
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Gemini transcription failed: {resp.status}")
                        return ""
                    
                    result = await resp.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def _find_submit_url(self, html: str, links: list, current_url: str) -> str:
        """
        Finds the submit URL using robust heuristics.
        """
        from urllib.parse import urljoin
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        submit_url = None

        # 1. Form Action
        for form in soup.find_all("form", action=True):
            action = form["action"].strip()
            if "submit" in action.lower() or action.startswith("http"):
                submit_url = urljoin(current_url, action)
                logger.info(f"Found submit URL via form: {submit_url}")
                return submit_url

        # 2. Check links (already passed in, but let's re-verify with soup to be safe/consistent)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "submit" in href.lower():
                submit_url = urljoin(current_url, href)
                logger.info(f"Found submit URL via anchor: {submit_url}")
                return submit_url

        # 3. Regex on HTML
        # Regex to find http/https URLs, stopping at whitespace or common punctuation
        urls = re.findall(r"https?://[^\s'\"<>]+", html)
        for u in urls:
            u = u.rstrip(".,;!)]}\"'")
            if "submit" in u.lower():
                submit_url = u
                logger.info(f"Found submit URL via regex (HTML): {submit_url}")
                return submit_url

        # 4. Regex on Text (handles split tags)
        text_content = soup.get_text(separator="")
        urls = re.findall(r"https?://[^\s'\"<>]+", text_content)
        for u in urls:
            u = u.rstrip(".,;!)]}\"'")
            if "submit" in u.lower():
                submit_url = u
                logger.info(f"Found submit URL via regex (Text): {submit_url}")
                return submit_url

        return None

extractor_agent = ExtractorAgent()
