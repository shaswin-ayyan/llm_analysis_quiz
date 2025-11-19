import httpx
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

# ======================
# PROVIDERS CONFIG
# ======================

PRIMARY_MODELS = []
if settings.LLM_CHAT_MODEL:
    PRIMARY_MODELS.append(settings.LLM_CHAT_MODEL)
for model in settings.LLM_FALLBACK_MODELS:
    if model and model not in PRIMARY_MODELS:
        PRIMARY_MODELS.append(model)

AIPIPE_PROVIDER = {
    "name": "AIPipe",
    "type": "aipipe",
    "url": settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
    "api_key": settings.OPENAI_API_KEY,
    "models": PRIMARY_MODELS,
}

ALL_PROVIDERS = [AIPIPE_PROVIDER]


# ***************************************************************
# MAIN COMPLETION FUNCTION WITH FULL SEMANTIC FAILOVER
# ***************************************************************
async def chat_completion(messages, provider_index=0, model_index=0, timeout=20):
    """
    provider_index: which provider to use
    model_index: which model inside the provider to use (for OpenRouter)
    """

    # --------------------
    # IF ALL FAILED
    # --------------------
    if provider_index >= len(ALL_PROVIDERS):
        raise RuntimeError("All LLM providers failed semantically.")

    provider = ALL_PROVIDERS[provider_index]
    models = provider.get("models") or [provider.get("model")]
    models = [m for m in models if m]

    if not models:
        raise RuntimeError(f"No models configured for provider {provider['name']}")

    if model_index >= len(models):
        return await chat_completion(messages, provider_index+1, 0, timeout)

    model = models[model_index]

    # ======================================================
    # TRY AIPIPE PROVIDER (OpenAI-compatible endpoint)
    # ======================================================
    if provider["type"] == "aipipe":

        if not provider["api_key"]:
            print("[AIPipe] No API key — skipping")
            return await chat_completion(messages, provider_index+1, 0, timeout)

        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    provider["url"],
                    headers=headers,
                    json=payload
                )
        except Exception as e:
            print(f"[AIPipe EXCEPTION] {model} → {e}")
            return await chat_completion(messages, provider_index, model_index+1, timeout)

        if resp.status_code != 200:
            print(f"[AIPipe ERROR] {model} → {resp.status_code} {resp.text[:200]}")
            return await chat_completion(messages, provider_index, model_index+1, timeout)

        try:
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"[LLM] Using AIPipe model: {model}")
            print(f"[LLM SHORT] {content[:150]}")
            return content

        except Exception as e:
            print(f"[AIPipe PARSE ERROR] {model} → {e}")
            return await chat_completion(messages, provider_index, model_index+1, timeout)
