import pytest
from fastapi.testclient import TestClient
import os
import multiprocessing
import uvicorn
from tests.mock_server import app as mock_app
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session")
def mock_server():
    process = multiprocessing.Process(target=uvicorn.run, args=(mock_app,), kwargs={"host": "127.0.0.1", "port": 8001})
    process.start()
    yield "http://127.0.0.1:8001"
    process.terminate()

@pytest.fixture
def client():
    os.environ["QUIZ_SECRET"] = "test_secret"
    from app.main import app

    with TestClient(app) as c:
        yield c
    del os.environ["QUIZ_SECRET"]

@patch("app.orchestrator.DataAgent.run")
def test_e2e_successful_run(mock_run, client, mock_server):
    mock_run.return_value = "4"
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": f"{mock_server}/quiz/123",
            "secret": os.environ.get("QUIZ_SECRET"),
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "completed", "answer": "4"}

@patch("app.orchestrator.DataAgent.run")
def test_e2e_incorrect_answer(mock_run, client, mock_server):
    mock_run.return_value = "5"
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": f"{mock_server}/quiz/123",
            "secret": os.environ.get("QUIZ_SECRET"),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "wrong"

@patch("app.orchestrator.render_page_with_retries")
def test_e2e_timeout(mock_render, client, mock_server):
    mock_render.side_effect = TimeoutError("Page took too long to load")
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": f"{mock_server}/quiz/123",
            "secret": os.environ.get("QUIZ_SECRET"),
        },
    )
    assert response.status_code == 500
    assert "Page took too long to load" in response.json()["detail"]

@patch("app.orchestrator.DataAgent.run")
def test_e2e_multistep_quiz(mock_run, client, mock_server):
    side_effect = ["4", "10"]
    mock_run.side_effect = lambda *args, **kwargs: side_effect.pop(0) if side_effect else "10"
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": f"{mock_server}/quiz/multistep1",
            "secret": os.environ.get("QUIZ_SECRET"),
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "completed", "answer": "10"}
