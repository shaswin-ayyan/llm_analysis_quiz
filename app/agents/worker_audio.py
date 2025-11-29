import logging
import os
import base64
import aiohttp
from app.config import settings

logger = logging.getLogger(__name__)

async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes audio using google/gemini-2.0-flash-lite-001.
    Tries OpenRouter if configured, otherwise falls back to Gemini Direct.
    """
    if not os.path.exists(file_path):
        return "Error: Audio file not found."

    # Read prompt
    with open("app/prompts/audio_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # Read audio
    with open(file_path, "rb") as f:
        audio_data = f.read()
    b64_audio = base64.b64encode(audio_data).decode("utf-8")

    # Determine mime type
    mime_type = "audio/mp3"
    if file_path.endswith(".wav"): mime_type = "audio/wav"
    elif file_path.endswith(".ogg"): mime_type = "audio/ogg"

    # 1. Try OpenRouter if key is present
    if settings.OPENROUTER_API_KEY:
        try:
            return await _transcribe_openrouter(system_prompt, b64_audio, mime_type)
        except Exception as e:
            logger.warning(f"OpenRouter audio transcription failed: {e}. Falling back to Gemini Direct.")
    
    # 2. Fallback to Gemini Direct
    if settings.GEMINI_API_KEY:
        return await _transcribe_gemini_direct(system_prompt, b64_audio, mime_type)

    return "Error: No suitable API key for audio transcription."

async def _transcribe_openrouter(system_prompt: str, b64_audio: str, mime_type: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "LLM Quiz Solver"
    }
    
    # OpenRouter / OpenAI Multimodal format
    # Note: Not all models support this via OpenRouter, but Gemini Flash Lite should.
    payload = {
        "model": settings.AUDIO_WORKER_MODEL, # e.g. google/gemini-2.0-flash-lite-001
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Transcribe this audio."},
                    {
                        "type": "image_url", # OpenRouter often uses image_url for multimodal inputs generally, or specific audio fields
                        # However, standard OpenAI is "input_audio". OpenRouter docs say for Gemini/Claude it maps automatically.
                        # Let's try the data URI format in content which is common for OpenRouter/VLM
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_audio}"
                        }
                    }
                ]
            }
        ]
    }
    
    # NOTE: "image_url" is a misnomer but often used for multimodal input in OpenAI-compatible APIs.
    # If this fails, we might need "input_audio" or specific vendor extensions.
    # Given the uncertainty, we wrap this in try/except in the main function.

    async with aiohttp.ClientSession() as session:
        async with session.post(settings.OPENROUTER_BASE_URL + "/chat/completions", headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"OpenRouter API failed: {resp.status} - {text}")
            
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

async def _transcribe_gemini_direct(system_prompt: str, b64_audio: str, mime_type: str) -> str:
    clean_model = settings.AUDIO_WORKER_MODEL.replace("google/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={settings.GEMINI_API_KEY}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{
            "parts": [
                {"text": "Transcribe this audio."},
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
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                return f"Error: Gemini API failed {resp.status}"
            data = await resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except:
                return "Error: No transcript returned."
