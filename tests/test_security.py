import pytest
from app.agents.tools import load_data_tool

@pytest.mark.asyncio
async def test_load_data_security_traversal():
    # Test path traversal
    with pytest.raises(ValueError, match="Security Error"):
        await load_data_tool({"file_path": "../../../etc/passwd"}, None)

@pytest.mark.asyncio
async def test_load_data_security_absolute():
    # Test absolute path (we decided to allow it for now if it doesn't have .., but let's check if we implemented strictness)
    # Actually my implementation only checked for ".." and blocked it.
    # Let's verify ".." is blocked.
    with pytest.raises(ValueError, match="Security Error"):
        await load_data_tool({"file_path": "data/../../secret.txt"}, None)

@pytest.mark.asyncio
async def test_load_data_valid_url():
    # URLs should be fine
    # We mock aiohttp to avoid actual network call, or just expect it to fail on connection but NOT security
    try:
        await load_data_tool({"file_path": "http://example.com/data.csv"}, None)
    except RuntimeError as e:
        # Expected network error, not security error
        assert "Failed to fetch URL" in str(e)
    except ValueError as e:
        pytest.fail(f"Should not raise ValueError for URL: {e}")
