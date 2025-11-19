import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception_type(httpx.HTTPError))
async def download_bytes(url: str) -> bytes:
    logger.info(f"Downloading: {url}")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url, timeout=30)
        r.raise_for_status()
        return r.content
