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
        Transcribes audio using Gemini (Direct or OpenRouter).
        """
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()
            
            b64_audio = base64.b64encode(audio_data).decode("utf-8")
            
            mime_type = "audio/mp3"
            if file_path.endswith(".wav"):
                mime_type = "audio/wav"
            elif file_path.endswith(".ogg"):
                mime_type = "audio/ogg"
            elif file_path.endswith(".opus"):
                mime_type = "audio/opus"

            # 1. Try Direct Google API if key exists
            if settings.GEMINI_API_KEY:
                # Use the configured AUDIO_MODEL (strip 'google/' prefix for direct API if needed, 
                # but usually 'models/gemini-...' works. OpenRouter uses 'google/gemini-...')
                # Google API expects 'gemini-2.0-flash' etc.
                # settings.AUDIO_MODEL is 'google/gemini-2.0-flash-lite-preview-02-05'
                # We need to extract the model ID.
                model_id = settings.AUDIO_MODEL.replace("google/", "")
                
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={settings.GEMINI_API_KEY}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Transcribe this audio file exactly. If there are numbers, write them as digits (e.g., '219' not 'two one nine')."},
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
                        if resp.status == 200:
                            result = await resp.json()
                            return result["candidates"][0]["content"]["parts"][0]["text"]
                        else:
                            logger.warning(f"Gemini Direct transcription failed: {resp.status}. Trying OpenRouter...")

            # 2. Try OpenRouter if Direct failed or key missing
            if settings.OPENROUTER_API_KEY:
                from app.llm_client import chat_completion, ALL_PROVIDERS
                
                # Find index for OpenRouter and AUDIO_MODEL
                provider_idx = -1
                model_idx = -1
                for p_i, provider in enumerate(ALL_PROVIDERS):
                    if provider["type"] == "openrouter":
                        provider_idx = p_i
                        for m_i, model in enumerate(provider["models"]):
                            if model == settings.AUDIO_MODEL:
                                model_idx = m_i
                                break
                        break
                
                if provider_idx != -1 and model_idx != -1:
                    # Construct multimodal message for OpenRouter
                    # Note: OpenRouter support for audio via 'image_url' or custom fields varies.
                    # We will try the standard OpenAI multimodal format (image_url) as a fallback mechanism,
                    # hoping the provider maps it.
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Transcribe this audio file exactly. If there are numbers, write them as digits (e.g., '219' not 'two one nine')."},
                                {
                                    "type": "image_url", 
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_audio}"
                                    }
                                }
                            ]
                        }
                    ]
                    
                    response = await chat_completion(messages, provider_index=provider_idx, model_index=model_idx)
                    return response
            
            logger.error("Transcription failed: No valid API key or provider failed.")
            return ""

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

        # 1. Priority: Form with method="POST"
        for form in soup.find_all("form"):
            method = form.get("method", "").upper()
            action = form.get("action", "").strip()
            if method == "POST" and action:
                submit_url = urljoin(current_url, action)
                logger.info(f"Found submit URL via POST form: {submit_url}")
                return submit_url

        # 2. Priority: Keywords in links/buttons
        # Expanded keywords beyond just "submit"
        keywords = ["submit", "upload", "complete", "finish", "send", "next"]
        
        for a in soup.find_all(["a", "button"], href=True):
            href = a.get("href", "").strip()
            text = a.get_text().lower()
            
            # Check href and text for keywords
            if any(k in href.lower() for k in keywords) or any(k in text for k in keywords):
                submit_url = urljoin(current_url, href)
                logger.info(f"Found submit URL via keyword match: {submit_url}")
                return submit_url

        # 3. Fallback: Regex on HTML (for JS links or weird structures)
        urls = re.findall(r"https?://[^\s'\"<>]+", html)
        for u in urls:
            u = u.rstrip(".,;!)]}\"'")
            if any(k in u.lower() for k in keywords):
                submit_url = u
                logger.info(f"Found submit URL via regex: {submit_url}")
                return submit_url

        return None

extractor_agent = ExtractorAgent()
