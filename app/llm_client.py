import httpx
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

# ======================
# PROVIDERS CONFIG
# ======================

ALL_PROVIDERS = []

# ======================
# GEMINI PROVIDER (Direct)
# ======================
if settings.GEMINI_API_KEY:
    GEMINI_PROVIDER = {
        "name": "Gemini (Direct)",
        "type": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "api_key": settings.GEMINI_API_KEY,
        "models": settings.GEMINI_MODELS,
    }
    ALL_PROVIDERS.append(GEMINI_PROVIDER)

# ======================
# OpenRouter Provider
# ======================
# Explicitly define the list of models to ensure correct order for fallback logic.
# Order: 
# 1. Orchestrator Primary (Gemma 3)
# 2. Orchestrator Fallback (Tongyi)
# 3. Worker Primary (Gemini 2.5 Flash Lite)
# 4. Worker Fallback 1 (Gemini 2.0 Flash)
# 5. Worker Fallback 2 (Llama 3.3 70B)

OPENROUTER_MODELS = [
    settings.ORCHESTRATOR_MODEL,           # google/gemma-3-27b-it
    "google/gemini-2.0-flash-lite-preview-02-05", # Fallback for Orchestrator (Multimodal)
    settings.WORKER_MODEL,                 # alibaba/tongyi-deepresearch-30b-a3b
    settings.AUDIO_MODEL,                  # Audio Transcription
    "google/gemini-2.0-flash-001",         # Fallback for Worker
    "meta-llama/llama-3.3-70b-instruct",   # Deep fallback
]

OPENROUTER_PROVIDER = {
    "name": "OpenRouter",
    "type": "openrouter",
    "url": settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
    "api_key": settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
    "models": OPENROUTER_MODELS,
}
ALL_PROVIDERS.append(OPENROUTER_PROVIDER)

# ======================
# AIPipe Provider (Conditional)
# ======================
if settings.USE_AIPIPE:
    # When using AIPIPE, we want to route ALL requests through it.
    # We can reuse the OpenRouter model list or define a specific one.
    # For now, we'll use the same models but route via AIPIPE.
    
    AIPIPE_PROVIDER = {
        "name": "AIPipe",
        "type": "aipipe",
        "url": settings.AIPIPE_BASE_URL.rstrip("/") + "/chat/completions",
        "api_key": settings.AIPIPE_API_KEY or settings.OPENAI_API_KEY,
        "models": OPENROUTER_MODELS, # Reuse the same model list
    }
    # Insert AIPIPE as the FIRST provider if enabled
    ALL_PROVIDERS.insert(0, AIPIPE_PROVIDER)


# ***************************************************************
# MAIN COMPLETION FUNCTION WITH FULL SEMANTIC FAILOVER
# ***************************************************************
def convert_openai_messages_to_gemini(messages):
    converted = []

    system_prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            # Collect system messages and merge later
            system_prompt += msg["content"] + "\n"
        else:
            converted.append({
                "role": msg["role"],
                "parts": [{"text": msg["content"]}]
            })

    # Prepend system prompt into first user message
    if system_prompt:
        if len(converted) > 0:
            converted[0]["parts"][0]["text"] = system_prompt + "\n" + converted[0]["parts"][0]["text"]
        else:
            converted.append({
                "role": "user",
                "parts": [{"text": system_prompt}]
            })

    return converted

async def chat_completion(messages, provider_index=0, model_index=0, timeout=20):
    if provider_index >= len(ALL_PROVIDERS):
        raise RuntimeError("All providers failed.")

    provider = ALL_PROVIDERS[provider_index]
    models = provider.get("models") or []
    if model_index >= len(models):
        # move to next provider
        return await chat_completion(messages, provider_index + 1, 0, timeout)

    model = models[model_index]

    headers = {"Content-Type": "application/json"}
    payload = {}

    try:
        # ==============================
        # GEMINI
        # ==============================
        if provider["type"] == "gemini":
            # AI Pipe requires Authorization header for native keys
            if "aipipe.org" in provider["url"]:
                headers["Authorization"] = f"Bearer {provider['api_key']}"
            else:
                headers["x-goog-api-key"] = provider["api_key"]
                
            url = f"{provider['url']}/{model}:generateContent"
            gemini_messages = convert_openai_messages_to_gemini(messages)
            payload = {
                "contents": gemini_messages
            }

        # ==============================
        # AIPIPE (OpenAI-compatible)
        # ==============================
        elif provider["type"] == "aipipe":
            headers["Authorization"] = f"Bearer {provider['api_key']}"
            url = provider["url"]
            payload = {"model": model, "messages": messages}

        # ==============================
        # OPENROUTER
        # ==============================
        elif provider["type"] == "openrouter":
            headers["Authorization"] = f"Bearer {provider['api_key']}"
            url = provider["url"]
            payload = {"model": model, "messages": messages}

        # ==============================
        # MAKE THE REQUEST
        # ==============================
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            print(f"[ERROR {provider['name']}] {model}: {resp.status_code}")
            return await chat_completion(messages, provider_index, model_index + 1, timeout)

        data = resp.json()

        # Gemini parsing
        if provider["type"] == "gemini":
            if not data.get("candidates") or not data["candidates"][0].get("content") or not data["candidates"][0]["content"].get("parts"):
                print(f"[ERROR {provider['name']}] {model}: Empty/Invalid response: {data}")
                return await chat_completion(messages, provider_index, model_index + 1, timeout)
            content = data["candidates"][0]["content"]["parts"][0]["text"]

        # OpenAI-style parsing (AIPipe, OpenRouter)
        else:
            content = data["choices"][0]["message"]["content"]

        print(f"[LLM] Using {provider['name']} → {model}")
        return content

    except Exception as e:
        print(f"[EXCEPTION] {provider['name']} {model}: {e}")
        return await chat_completion(messages, provider_index, model_index + 1, timeout)
