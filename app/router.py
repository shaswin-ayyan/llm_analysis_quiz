import os
from litellm import acompletion as litellm_completion
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure LiteLLM to use AIPIPE if enabled
if settings.USE_AIPIPE:
    os.environ["OPENAI_API_BASE"] = settings.AIPIPE_BASE_URL
    os.environ["OPENAI_API_KEY"] = settings.AIPIPE_API_KEY or settings.OPENAI_API_KEY
    # LiteLLM usually needs specific provider prefixes or custom configuration for generic OpenAI-compatible endpoints
    # But since we are using "openai/..." models via AIPIPE (which acts as OpenAI proxy), it should work standardly.
    # However, for models like 'z-ai/glm-4.5-air', we might need to ensure LiteLLM treats them correctly.
    # We will assume AIPIPE handles the routing if we send it to the base URL.

# Ensure OpenRouter key is available to LiteLLM
if settings.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY

async def query_llm(messages: list, model: str = None, temperature: float = 0.0):
    """
    Routes the LLM request using LiteLLM with fallback logic.
    """
    
    # Define the fallback chain
    # 1. Primary (User requested or Configured Primary)
    # 2. Fallback (Configured Fallback)
    # 3. Expensive (Configured Expensive)
    
    target_model = model or settings.MODEL_PRIMARY
    fallback_models = []
    
    if target_model == settings.MODEL_PRIMARY:
        fallback_models = [settings.MODEL_FALLBACK, settings.MODEL_EXPENSIVE]
    elif target_model == settings.MODEL_FALLBACK:
        fallback_models = [settings.MODEL_EXPENSIVE]
    
    # LiteLLM supports 'fallbacks' parameter but it's often better to control it explicitly 
    # or use their 'completion(..., fallbacks=[...])' feature.
    
    # We'll use the model list for fallbacks
    model_chain = [target_model] + fallback_models
    
    for current_model in model_chain:
        try:
            logger.info(f"Router: Trying model {current_model}...")
            
            # If using AIPIPE, we might need to prefix models with 'openai/' if they are not standard,
            # OR just rely on AIPIPE's OpenAI compatibility.
            # Litellm might try to validate model names. 
            # We use 'openai/<model_name>' to force it to use the OpenAI endpoint (which is AIPIPE).
            
            litellm_model_name = current_model
            if settings.USE_AIPIPE:
                # Force OpenAI provider for LiteLLM to use our custom OPENAI_API_BASE
                if not litellm_model_name.startswith("openai/"):
                    litellm_model_name = f"openai/{current_model}"
            
            response = await litellm_completion(
                model=litellm_model_name,
                messages=messages,
                temperature=temperature,
                base_url=settings.AIPIPE_BASE_URL if settings.USE_AIPIPE else None,
                api_key=settings.AIPIPE_API_KEY or settings.OPENAI_API_KEY if settings.USE_AIPIPE else None
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"Router: Model {current_model} failed: {e}")
            continue
            
    raise Exception("All models in the chain failed.")
