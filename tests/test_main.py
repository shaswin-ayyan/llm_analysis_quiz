import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os


@pytest.fixture
def client():
    os.environ["QUIZ_SECRET"] = "test_secret"
    from app.main import app

    with TestClient(app) as c:
        yield c
    del os.environ["QUIZ_SECRET"]


def test_solve_invalid_secret(client):
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": "http://example.com",
            "secret": "invalid",
        },
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid secret"}


@patch("app.main.orchestrator.handle_task", new_callable=AsyncMock)
def test_solve_valid_secret(mock_handle_task, client):
    mock_handle_task.return_value = {"status": "completed", "answer": "Paris"}
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "url": "http://example.com",
            "secret": os.environ.get("QUIZ_SECRET"),
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "message": "Task started in background"}
