import asyncio
import os
from app.config import settings

# Force enable AIPIPE for this test BEFORE importing llm_client
settings.USE_AIPIPE = True

from app.llm_client import chat_completion, ALL_PROVIDERS

# Ensure API key is set (assuming it's in env or config)
if not settings.AIPIPE_API_KEY and not settings.OPENAI_API_KEY:
    print("WARNING: No AIPIPE_API_KEY or OPENAI_API_KEY found. Tests may fail.")

MODELS_TO_TEST = [
    "z-ai/glm-4.5-air"
]

async def test_model(model_name):
    print(f"Testing {model_name}...", end=" ", flush=True)
    messages = [{"role": "user", "content": "Say 'ok'"}]
    
    # We need to temporarily override the provider's model list or just pass the model directly
    # The current llm_client implementation iterates through a fixed list in the provider.
    # To test arbitrary models, we need to hack the provider config slightly for this script.
    
    # Find the AIPIPE provider
    from app.llm_client import ALL_PROVIDERS
    aipipe_provider = next((p for p in ALL_PROVIDERS if p["type"] == "aipipe"), None)
    
    if not aipipe_provider:
        print("FAILED: AIPIPE provider not found in ALL_PROVIDERS")
        return

    # Override the models list for this specific test
    original_models = aipipe_provider["models"]
    aipipe_provider["models"] = [model_name]
    
    try:
        response = await chat_completion(messages, provider_index=0, model_index=0, timeout=15)
        if response:
            print(f"SUCCESS")
        else:
            print(f"FAILED (Empty response)")
    except Exception as e:
        print(f"FAILED ({str(e)})")
    finally:
        # Restore models
        aipipe_provider["models"] = original_models

async def main():
    print(f"Starting connectivity test for {len(MODELS_TO_TEST)} models via AIPIPE...")
    print(f"AIPIPE_BASE_URL: {settings.AIPIPE_BASE_URL}")
    
    results = []
    for model in MODELS_TO_TEST:
        await test_model(model)
        
    print("\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(main())
