import asyncio
import logging
from app.router import query_llm
from app.config import settings

# Configure logging to see router output
logging.basicConfig(level=logging.INFO)

async def main():
    print(f"Testing AIPIPE Connection: {settings.USE_AIPIPE}")
    print(f"Base URL: {settings.AIPIPE_BASE_URL}")
    print(f"Model: {settings.MODEL_PRIMARY}")
    
    try:
        response = await query_llm(
            messages=[{"role": "user", "content": "Hello, are you working via AIPIPE?"}]
        )
        print("\n--- Success! ---")
        print(response)
    except Exception as e:
        print("\n--- Failed! ---")
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
