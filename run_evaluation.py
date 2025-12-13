import asyncio
import logging
import os
from app.orchestrator import Orchestrator
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evaluation")

async def run_evaluation():
    # Configuration
    start_url = "http://localhost:8019/project2"
    email = "test@example.com"
    secret = "s3cret"
    
    logger.info(f"Starting evaluation against {start_url}")
    
    orchestrator = Orchestrator()
    
    # Run the task
    # The orchestrator handles the loop internally if next_url is returned
    result = await orchestrator.handle_task(start_url, email, secret, max_tasks=8)
    
    logger.info("Evaluation Complete")
    logger.info(f"Final Result: {result}")

if __name__ == "__main__":
    # Ensure we are in the right directory or set pythonpath if needed
    # Assuming run from root
    asyncio.run(run_evaluation())
