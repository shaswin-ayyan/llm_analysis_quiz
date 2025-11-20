# app/utils/submitter.py
import logging
import httpx
from typing import Optional, Any, Dict

logger = logging.getLogger("uvicorn.error")


async def submit_answer(
    submit_url: str, payload: Dict[str, Any], timeout: int = 20
) -> Optional[Dict[str, Any]]:
    """
    Post the payload to the quiz submit endpoint.
    Expects JSON response; returns parsed JSON or None on failure.
    """
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                submit_url, json=payload, headers=headers
            )
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}

            if resp.status_code >= 400:
                logger.error(
                    f"Submit failed {resp.status_code}: {resp.text}"
                )
                data.setdefault("correct", False)
                data.setdefault("status_code", resp.status_code)
            return data
    except Exception as e:
        logger.exception(f"submit_answer raised exception: {e}")
        return None
