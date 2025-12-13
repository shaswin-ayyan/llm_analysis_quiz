import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockServer")

app = FastAPI(title="Mock Full Quiz Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL
BASE_URL = "http://localhost:8000"

# Mount static files
# We serve the 'public' directory. 
# Note: The HTML files in 'public' are named like 'project2-gh-tree' (no extension).
# We might need to handle this.
# For now, let's mount it and see if we can access /project2-gh-tree directly if it exists as a file.
# Mount static files moved to end

# Fixtures and Logic
email = "23f1000266@ds.study.iitm.ac.in" # Hardcoded for verification
fixtures = {
    "ghTreeExpected": 1,
    "logsSum": 335,
    "pdfTotal": 170.97,
    "orderLeaders": [
        {"customer_id": "B", "total": 110},
        {"customer_id": "D", "total": 100},
        {"customer_id": "A", "total": 90},
    ],
    "chartAnswer": "stacked area", # From run_real_evaluation.py
    "shardInputs": {
        "dataset": 18000,
        "max_docs_per_shard": 3200,
        "max_shards": 6,
        "min_replicas": 2,
        "max_replicas": 3,
        "memory_per_shard": 1.5,
        "memory_budget": 18,
    },
    "embeddingPair": ["s4", "s5"],
    "imageDiff": 7,
    "rateMinutes": 71,
    "ragTop": ["c1", "c2", "c3"],
    "f1": {"run_id": "runC", "macro_f1": 0.8175},
}

# Sequence
SEQUENCE = {
    "/project2-gh-tree": "/project2-logs",
    "/project2-logs": "/project2-invoice",
    "/project2-invoice": "/project2-orders",
    "/project2-orders": "/project2-chart",
    "/project2-chart": "/project2-cache",
    "/project2-cache": "/project2-shards",
    "/project2-shards": "/project2-embed",
    "/project2-embed": "/project2-tools",
    "/project2-tools": "/project2-diff",
    "/project2-diff": "/project2-rate",
    "/project2-rate": "/project2-guard",
    "/project2-guard": "/project2-rag",
    "/project2-rag": "/project2-f1",
    "/project2-f1": None # End
}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse({"correct": False, "message": "Invalid JSON"})

    url = data.get("url", "")
    answer = data.get("answer")
    
    # Extract path from URL
    # e.g. http://localhost:8000/project2-gh-tree -> /project2-gh-tree
    path = url.replace(BASE_URL, "").split("?")[0]
    
import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockServer")

app = FastAPI(title="Mock Full Quiz Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL
BASE_URL = "http://localhost:8000"

# Mount static files
# We serve the 'public' directory. 
# Note: The HTML files in 'public' are named like 'project2-gh-tree' (no extension).
# We might need to handle this.
# For now, let's mount it and see if we can access /project2-gh-tree directly if it exists as a file.
# Mount static files moved to end

# Fixtures and Logic
email = "23f1000266@ds.study.iitm.ac.in" # Hardcoded for verification
fixtures = {
    "ghTreeExpected": 1,
    "logsSum": 335,
    "pdfTotal": 170.97,
    "orderLeaders": [
        {"customer_id": "B", "total": 110},
        {"customer_id": "D", "total": 100},
        {"customer_id": "A", "total": 90},
    ],
    "chartAnswer": "stacked area", # From run_real_evaluation.py
    "shardInputs": {
        "dataset": 18000,
        "max_docs_per_shard": 3200,
        "max_shards": 6,
        "min_replicas": 2,
        "max_replicas": 3,
        "memory_per_shard": 1.5,
        "memory_budget": 18,
    },
    "embeddingPair": ["s4", "s5"],
    "imageDiff": 7,
    "rateMinutes": 71,
    "ragTop": ["c1", "c2", "c3"],
    "f1": {"run_id": "runC", "macro_f1": 0.8175},
}

# Sequence
SEQUENCE = {
    "/project2-gh-tree": "/project2-logs",
    "/project2-logs": "/project2-invoice",
    "/project2-invoice": "/project2-orders",
    "/project2-orders": "/project2-chart",
    "/project2-chart": "/project2-cache",
    "/project2-cache": "/project2-shards",
    "/project2-shards": "/project2-embed",
    "/project2-embed": "/project2-tools",
    "/project2-tools": "/project2-diff",
    "/project2-diff": "/project2-rate",
    "/project2-rate": "/project2-guard",
    "/project2-guard": "/project2-rag",
    "/project2-rag": "/project2-f1",
    "/project2-f1": None # End
}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse({"correct": False, "message": "Invalid JSON"})

    url = data.get("url", "")
    answer = data.get("answer")
    
    # Extract path from URL
    # e.g. http://localhost:8000/project2-gh-tree -> /project2-gh-tree
    path = url.replace(BASE_URL, "").split("?")[0]
    
    logger.info(f"Submission: Path={path}, Answer={answer}")
    
    correct = False
    message = "Incorrect"
    
    # Validation Logic
    if path == "/project2-gh-tree":
        expected = fixtures["ghTreeExpected"] + (len(email) % 2)
        try:
            if int(answer) == expected:
                correct = True
        except:
            pass
            
    elif path == "/project2-logs":
        expected = fixtures["logsSum"] + (len(email) % 5)
        try:
            if float(answer) == expected:
                correct = True
        except:
            pass

    elif path == "/project2-invoice":
        try:
            if float(answer) == fixtures["pdfTotal"]:
                correct = True
        except:
            pass

    elif path == "/project2-orders":
        # Check if list matches
        # Simplification: check first item
        if isinstance(answer, list) and len(answer) > 0 and answer[0]["customer_id"] == "B":
            correct = True

    elif path == "/project2-chart":
        ans_str = str(answer).lower()
        if ans_str == "stacked area" or ans_str == "b":
            correct = True

    elif path == "/project2-cache":
        if "uses: actions/cache@v4" in str(answer):
            correct = True

    elif path == "/project2-shards":
        if answer == {"shards": 6, "replicas": 2}:
            correct = True

    elif path == "/project2-embed":
        expected = ["s4", "s5"] if (len(email) % 2) == 0 else ["s2", "s3"]
        if answer == expected:
            correct = True
        elif isinstance(answer, str) and answer == ",".join(expected):
            correct = True

    elif path == "/project2-tools":
        if isinstance(answer, list) and len(answer) == 3:
            correct = True

    elif path == "/project2-diff":
        try:
            if int(answer) == fixtures["imageDiff"]:
                correct = True
        except:
            pass

    elif path == "/project2-rate":
        expected = fixtures["rateMinutes"] + (len(email) % 3)
        try:
            if int(answer) == expected:
                correct = True
        except:
            pass

    elif path == "/project2-guard":
        if "JSON only" in str(answer):
            correct = True

    elif path == "/project2-rag":
        if answer == fixtures["ragTop"]:
            correct = True

    elif path == "/project2-f1":
        if answer == fixtures["f1"]:
            correct = True

    if correct:
        next_path = SEQUENCE.get(path)
        next_url = f"{BASE_URL}{next_path}" if next_path else None
        return JSONResponse({"correct": True, "message": "Correct!", "next_url": next_url})
    else:
        return JSONResponse({"correct": False, "message": f"Incorrect. Expected something else."})

# Mount static files at the end to allow API routes to take precedence
app.mount("/", StaticFiles(directory="tds-llm-analysis-main-tests/public", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
