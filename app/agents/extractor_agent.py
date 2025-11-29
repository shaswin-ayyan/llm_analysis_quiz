import logging
import os
import uuid
import re
from app.utils.browser import browser_manager
from app.agents.worker_audio import transcribe_audio

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
        # We delegate this to the Supervisor loop now, OR we can do it here.
        # The prompt says "Audio Worker transcribes only".
        # The Supervisor logic I wrote checks for audio files and calls transcribe_audio.
        # So we can skip it here to avoid double work, OR keep it here for "extraction".
        # The prompt says "Supervisor (Gemma 27B) ... Chooses tools ... Audio worker transcribes".
        # So the Supervisor should call the audio worker.
        # However, the ExtractorAgent is "Scrapes webpage, downloads files, extracts text".
        # If we remove it here, the "question text" might be missing if it's only in audio.
        # Let's keep it here but use the new worker, so the Supervisor gets the full text immediately.
        
        audio_transcript = ""
        if data["files"]["audio"]:
            for audio_path in data["files"]["audio"]:
                logger.info(f"Transcribing audio: {audio_path}")
                transcript = await transcribe_audio(audio_path)
                if transcript:
                    audio_transcript += f"\n[Audio Transcript]: {transcript}\n"
        
        # 3. Identify Question
        full_text = data["page_text"] + "\n" + audio_transcript
        
        # 4. Identify Submit URL
        submit_url = self._find_submit_url(data["html_content"], data["links"], url)
        
        return {
            "question_text": full_text.strip(),
            "page_text": data["page_text"],
            "submit_url": submit_url,
            "files": data["files"],
            "links": data["links"],
            "workspace_dir": workspace_dir
        }

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

        # 2. Check links
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "submit" in href.lower():
                submit_url = urljoin(current_url, href)
                logger.info(f"Found submit URL via anchor: {submit_url}")
                return submit_url

        # 3. Regex on HTML
        urls = re.findall(r"https?://[^\s'\"<>]+", html)
        for u in urls:
            u = u.rstrip(".,;!)]}\"'")
            if "submit" in u.lower():
                submit_url = u
                logger.info(f"Found submit URL via regex (HTML): {submit_url}")
                return submit_url

        # 4. Regex on Text
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
