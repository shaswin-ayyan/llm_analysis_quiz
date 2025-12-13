import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockServer")

app = FastAPI(title="Mock Quiz Server")

# Base URL for links (assuming running on localhost:8003)
BASE_URL = "http://localhost:8003"

# Mount static files
app.mount("/", StaticFiles(directory="mock_quiz_static", html=True), name="static")

@app.post("/submit")
async def submit(request: Request):
    # Handle both JSON and Form data
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        data = await request.json()
        task_id = data.get("task_id") or ("data" if "Engineering" in str(data) else "audio") # Heuristic if missing
        answer = data.get("answer")
    else:
        form = await request.form()
        task_id = form.get("task_id")
        answer = form.get("answer")

    logger.info(f"Received submission: Task={task_id}, Answer={answer}")

    if task_id == "data":
        # Engineering salaries: 60000, 70000, 80000, 62000, 90000. (120000 is outlier > 100k).
        # Sum: 362000. Count: 5. Average: 72400.
        try:
            val = float(str(answer).replace(",", "").strip())
            if 72390 <= val <= 72410: # Allow small margin
                return JSONResponse({
                    "correct": True, 
                    "message": "Correct!", 
                    "next_url": f"{BASE_URL}/audio.html"
                })
        except:
            pass
        return JSONResponse({"correct": False, "message": "Incorrect average salary."})

    elif task_id == "audio":
        if "BRAVO-77" in str(answer).upper():
             return JSONResponse({
                    "correct": True, 
                    "message": "Correct!", 
                    "next_url": f"{BASE_URL}/finish.html"
                })
        return JSONResponse({"correct": False, "message": "Incorrect code."})

    return JSONResponse({"correct": False, "message": "Unknown task."})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
