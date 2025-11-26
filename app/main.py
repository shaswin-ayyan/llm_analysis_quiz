# app/main.py
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.orchestrator import Orchestrator

load_dotenv()
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="TDS LLM Analysis Quiz Endpoint")

orchestrator = Orchestrator()


class SolvePayload(BaseModel):
    email: str
    url: str
    secret: str


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}


@app.post("/solve")
async def solve(payload: SolvePayload, request: Request):
    """
    Endpoint the TDS system calls.
    Expects JSON body: { "email": "...", "url": "...", "secret": "..." }
    """

    # basic JSON validation handled by Pydantic
    # secret check
    expected_secret = os.getenv("QUIZ_SECRET")
    if expected_secret:
        if payload.secret != expected_secret:
            logger.warning("Invalid secret provided")
            raise HTTPException(status_code=403, detail="Invalid secret")
    else:
        # If no secret configured, warn but allow (useful in local dev)
        logger.warning(
            "No QUIZ_SECRET configured in environment — skipping secret check"
        )

    # call orchestrator (note ordering: url, email, secret)
    try:
        result = await orchestrator.handle_task(
            payload.url, payload.email, payload.secret
        )
    except Exception as e:
        logger.exception("Error while handling task")
        raise HTTPException(status_code=500, detail=str(e))

    return result
