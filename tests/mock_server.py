from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

app = FastAPI()


@app.get("/quiz/{quiz_id}", response_class=HTMLResponse)
async def get_quiz(quiz_id: str):
    if quiz_id == "multistep1":
        return """
        <html>
            <body>
                <p>This is a multistep quiz. What is 2 + 2?</p>
                <a href="/data.csv">data.csv</a>
                <a href="/submit/multistep1">Submit Answer</a>
            </body>
        </html>
        """
    elif quiz_id == "multistep2":
        return """
        <html>
            <body>
                <p>What is 5 * 2?</p>
                <a href="/data.csv">data.csv</a>
                <a href="/submit/multistep2">Submit Answer</a>
            </body>
        </html>
        """
    else:
        return f"""
        <html>
            <body>
                <p>This is quiz {quiz_id}. What is the sum of the "value" column?</p>
                <a href="/data.csv">data.csv</a>
                <a href="/submit/123">Submit Answer</a>
            </body>
        </html>
        """


@app.get("/data.csv", response_class=PlainTextResponse)
async def get_csv():
    return "value\n2\n2"


@app.post("/submit/{quiz_id}")
async def submit(quiz_id: str, request: Request):
    data = await request.json()
    if quiz_id == "multistep1":
        if data.get("answer") == "4":
            return {"correct": True, "url": "/quiz/multistep2"}
        else:
            return {"correct": False, "message": "Incorrect answer"}
    elif quiz_id == "multistep2":
        if data.get("answer") == "10":
            return {"correct": True}
        else:
            return {"correct": False, "message": "Incorrect answer"}
    else:
        if data.get("answer") == "4":
            return {"correct": True}
        else:
            return {"correct": False, "message": "Incorrect answer"}
