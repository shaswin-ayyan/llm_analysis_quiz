import pytest
from unittest.mock import patch, MagicMock
from app.agents.data_agent import DataAgent
import pandas as pd

@pytest.fixture
def mock_chat_completion():
    with patch('app.agents.data_agent.chat_completion') as mock:
        yield mock

@pytest.fixture
def mock_load_csv_tool():
    with patch('app.agents.data_agent.load_csv_tool') as mock:
        yield mock

@pytest.mark.asyncio
async def test_data_agent_run_no_csv_url():
    agent = DataAgent()
    result = await agent.run(question="What is the capital of France?", csv_url=None)
    assert result == {"error": "csv_url missing"}

@pytest.mark.asyncio
async def test_data_agent_run_csv_load_failed(mock_load_csv_tool):
    agent = DataAgent()
    mock_load_csv_tool.side_effect = Exception("Failed to load CSV")
    result = await agent.run(question="What is the capital of France?", csv_url="http://example.com/data.csv")
    assert result == {"error": "csv_load_failed", "details": "Failed to load CSV"}

@pytest.mark.asyncio
async def test_data_agent_run_successful(mock_load_csv_tool, mock_chat_completion):
    agent = DataAgent()
    mock_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
    mock_load_csv_tool.return_value = mock_df
    mock_chat_completion.return_value = '[{"final_answer": "Paris"}]'
    result = await agent.run(question="What is the capital of France?", csv_url="http://example.com/data.csv")
    assert result == "Paris"
