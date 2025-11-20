import httpx
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

# ======================
# PROVIDERS CONFIG
# ======================

ALL_PROVIDERS = []

# ======================
# GEMINI PROVIDER
# ======================
if settings.GEMINI_API_KEY:
    GEMINI_PROVIDER = {
        "name": "Gemini",
        "type": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "api_key": settings.GEMINI_API_KEY,
        "models": [settings.GEMINI_MODEL],
    }
    ALL_PROVIDERS.append(GEMINI_PROVIDER)

# ======================
# AIPipe Provider
# ======================
PRIMARY_MODELS = []
if settings.LLM_CHAT_MODEL:
    PRIMARY_MODELS.append(settings.LLM_CHAT_MODEL)
for m in settings.LLM_FALLBACK_MODELS:
    if m not in PRIMARY_MODELS:
        PRIMARY_MODELS.append(m)

AIPIPE_PROVIDER = {
    "name": "AIPipe",
    "type": "aipipe",
    "url": settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
    "api_key": settings.OPENAI_API_KEY,
    "models": PRIMARY_MODELS,
}
ALL_PROVIDERS.append(AIPIPE_PROVIDER)

# ======================
# OpenRouter Provider
# ======================
if settings.OPENROUTER_API_KEY:
    OPENROUTER_PROVIDER = {
        "name": "OpenRouter",
        "type": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key": settings.OPENROUTER_API_KEY,
        "models": settings.OPENROUTER_MODELS,
    }
    ALL_PROVIDERS.append(OPENROUTER_PROVIDER)


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
            content = data["candidates"][0]["content"]["parts"][0]["text"]

        # OpenAI-style parsing (AIPipe, OpenRouter)
        else:
            content = data["choices"][0]["message"]["content"]

        print(f"[LLM] Using {provider['name']} → {model}")
        return content

    except Exception as e:
        print(f"[EXCEPTION] {provider['name']} {model}: {e}")
        return await chat_completion(messages, provider_index, model_index + 1, timeout)
