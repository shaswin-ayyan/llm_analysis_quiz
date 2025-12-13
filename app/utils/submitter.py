import logging
import os
from typing import Any
import httpx
from urllib.parse import urlparse

logger = logging.getLogger("uvicorn.error")

async def submit_answer(question_url: str, email: str, secret: str, answer: Any) -> dict:
    """
    Submit answer to the quiz server.
    
    Returns:
        dict with keys: correct, message, url (next URL), delay
    """
    logger.info("Submitting...")
    
    # Extract base URL
    parsed = urlparse(question_url)
    submit_base = f"{parsed.scheme}://{parsed.netloc}"
    submit_url = os.getenv("SUBMIT_URL")
    
    if not submit_url:
        submit_url = f"{submit_base}/submit"
        logger.info(f"Submit URL missing, guessing: {submit_url}")
    
    payload = {
        "url": question_url,
        "email": email,
        "secret": secret,
        "answer": answer
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(submit_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Return full response for intelligent retry logic
            return data
            
    except Exception as e:
        logger.error(f"Submission error: {e}")
        return {"correct": False, "message": str(e), "url": None}
