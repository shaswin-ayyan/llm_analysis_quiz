import pytest
from unittest.mock import patch
from app.orchestrator import Orchestrator


@pytest.fixture
def orchestrator():
    return Orchestrator()


def test_extract_question_and_resources(orchestrator):
    html = """
    <html>
        <body>
            <p>What is the capital of France?</p>
            <a href="data.csv">Download CSV</a>
            <a href="/submit">Submit</a>
        </body>
    </html>
    """
    (
        question,
        csv_url,
        submit_url,
    ) = orchestrator.extract_question_and_resources(html, "http://example.com")
    assert question == "What is the capital of France? Download CSV Submit"
    assert csv_url == "http://example.com/data.csv"
    assert submit_url == "http://example.com/submit"


@pytest.mark.asyncio
async def test_handle_task_successful(orchestrator):
    with (
        patch("app.orchestrator.render_page_with_retries") as mock_render,
        patch("app.orchestrator.DataAgent.run") as mock_run,
        patch("app.orchestrator.submit_answer") as mock_submit,
    ):
        mock_render.return_value = """
        <html>
            <body>
                <p>What is the capital of France?</p>
                <a href="data.csv">Download CSV</a>
                <a href="/submit">Submit</a>
            </body>
        </html>
        """
        mock_run.return_value = "Paris"
        mock_submit.return_value = {"correct": True}

        result = await orchestrator.handle_task(
            "http://example.com", "test@example.com", "secret"
        )
        assert result == {"status": "completed", "answer": "Paris"}


@pytest.mark.asyncio
async def test_handle_task_timeout(orchestrator):
    with patch("time.time") as mock_time:
        mock_time.side_effect = [0, 181, 182, 183, 184, 185]
        result = await orchestrator.handle_task(
            "http://example.com", "test@example.com", "secret"
        )
        assert result == {"error": "timeout"}


@pytest.mark.asyncio
async def test_handle_task_no_question(orchestrator):
    with patch("app.orchestrator.render_page_with_retries") as mock_render:
        mock_render.return_value = "<html></html>"
        result = await orchestrator.handle_task(
            "http://example.com", "test@example.com", "secret"
        )
        assert result == {"error": "no_question_text"}
