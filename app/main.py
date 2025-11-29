import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from app.orchestrator import Orchestrator

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="TDS LLM Analysis Quiz Endpoint")

orchestrator = Orchestrator()

class SolvePayload(BaseModel):
    email: str
    url: str
    secret: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/solve")
async def solve(payload: SolvePayload, background_tasks: BackgroundTasks):
    """
    Endpoint the TDS system calls.
    Returns 200 OK immediately and processes in background.
    """
    # Secret check
    expected_secret = os.getenv("QUIZ_SECRET")
    if expected_secret:
        if payload.secret != expected_secret:
            logger.warning("Invalid secret provided")
            raise HTTPException(status_code=403, detail="Invalid secret")
    else:
        logger.warning("No QUIZ_SECRET configured — skipping check")

    # Add to background tasks
    background_tasks.add_task(
        orchestrator.handle_task,
        payload.url,
        payload.email,
        payload.secret
    )
    
    logger.info(f"Accepted task for {payload.email}")
    return {"status": "accepted", "message": "Task started in background"}
