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
# AIPipe Provider (OpenAI Compatible)
# ======================
PRIMARY_MODELS = []
if settings.LLM_CHAT_MODEL:
    PRIMARY_MODELS.append(settings.LLM_CHAT_MODEL)
# Add Orchestrator Model
PRIMARY_MODELS.append(settings.ORCHESTRATOR_MODEL)

AIPIPE_PROVIDER = {
    "name": "AIPipe",
    "type": "aipipe",
    "url": settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
    "api_key": settings.OPENAI_API_KEY,
    "models": PRIMARY_MODELS,
}
ALL_PROVIDERS.append(AIPIPE_PROVIDER)

# ======================
# AIPipe Gemini Provider
# ======================
# The user specified: https://aipipe.org/geminiv1beta/models/gemini-2.5-flash-lite:generateContent
# This is a Google AI Studio compatible endpoint.
# We will treat it as a "gemini" type provider but with a custom URL.

if settings.GEMINI_API_KEY:
    AIPIPE_GEMINI_PROVIDER = {
        "name": "AIPipe Gemini",
        "type": "gemini",
        # The client code appends ":generateContent", so we provide the base up to the model?
        # Standard gemini url is: https://generativelanguage.googleapis.com/v1beta/models
        # AI Pipe url is: https://aipipe.org/geminiv1beta/models
        # So we set the url to the base.
        "url": "https://aipipe.org/geminiv1beta/models", 
        "api_key": settings.GEMINI_API_KEY,
        "models": [settings.WORKER_MODEL],
    }
    ALL_PROVIDERS.append(AIPIPE_GEMINI_PROVIDER)


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
