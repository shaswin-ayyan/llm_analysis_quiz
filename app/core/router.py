import logging
import aiohttp
import json
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

async def call_llm(messages: list, model: str, temperature: float = 0.0) -> str:
    """
    Routes LLM calls to appropriate provider.
    Prioritizes OpenRouter if OPENROUTER_API_KEY is set.
    """
    # If OpenRouter key is set, try to use it for everything unless explicitly forced otherwise
    if settings.OPENROUTER_API_KEY:
        try:
            return await _call_openrouter(messages, model, temperature)
        except Exception as e:
            logger.warning(f"OpenRouter call failed for {model}: {e}. Falling back if possible.")
            if "gemini" in model and settings.GEMINI_API_KEY:
                return await _call_gemini(messages, model, temperature)
            raise e
            
    # Fallback to Gemini direct if no OpenRouter key
    if "gemini" in model and settings.GEMINI_API_KEY:
        return await _call_gemini(messages, model, temperature)
    
    raise ValueError("No suitable API key found for model execution.")

async def _call_openrouter(messages: list, model: str, temperature: float) -> str:
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "LLM Quiz Solver"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096
    }

    logger.info(f"Calling OpenRouter model: {model}")
    
    timeout = aiohttp.ClientTimeout(total=60) # 60s timeout for LLM call
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(settings.OPENROUTER_BASE_URL + "/chat/completions", headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"OpenRouter Error: {resp.status} - {text}")
                raise RuntimeError(f"OpenRouter API failed: {text}")
            
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

async def _call_gemini(messages: list, model: str, temperature: float) -> str:
    if not settings.GEMINI_API_KEY:
         raise ValueError("GEMINI_API_KEY is not set.")
    
    contents = []
    system_instruction = None
    
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = {"parts": [{"text": msg["content"]}]}
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    # Strip "google/" prefix if present for direct API
    clean_model = model.replace("google/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={settings.GEMINI_API_KEY}"
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    logger.info(f"Calling Gemini Direct: {clean_model}")

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Gemini Error: {resp.status} - {text}")
                raise RuntimeError(f"Gemini API failed: {text}")
            
            data = await resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                logger.error(f"Gemini unexpected response: {data}")
                return ""
