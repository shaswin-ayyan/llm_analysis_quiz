import asyncio
import logging
import os
from app.agents.extractor_agent import extractor_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_extraction")

async def run_debug():
    url = "http://localhost:8004/project2"
    base_workspace = os.path.join(os.getcwd(), "workspace")
    
    logger.info(f"Extracting {url}...")
    result = await extractor_agent.extract(url, base_workspace)
    
    print("\n--- EXTRACTION RESULT ---")
    print(f"Submit URL: {result.get('submit_url')}")
    print(f"Page Text Preview: {result.get('page_text')[:500]}")
    print(f"Links: {result.get('links')}")

if __name__ == "__main__":
    asyncio.run(run_debug())
