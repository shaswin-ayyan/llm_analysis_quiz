import pytest
from unittest.mock import AsyncMock, patch
from app.llm_client import chat_completion, ALL_PROVIDERS

@pytest.mark.asyncio
async def test_chat_completion_fallback():
    # Mock httpx.AsyncClient to simulate failure on first model, success on second
    
    # We need to patch the actual network call inside chat_completion
    # Since chat_completion uses httpx.AsyncClient as context manager
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        from unittest.mock import Mock

        # Setup responses
        # First call: 500 error
        mock_resp_fail = Mock()
        mock_resp_fail.status_code = 500
        
        # Second call: 200 OK
        mock_resp_success = Mock()
        mock_resp_success.status_code = 200
        mock_resp_success.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success"}]}}]
        }
        
        # The client.post is async, so it must return an awaitable that resolves to the response
        # We can use AsyncMock for client.post
        
        async def side_effect(*args, **kwargs):
            # We need to return different responses based on call count or just iterate
            if mock_client.post.call_count == 1:
                return mock_resp_fail
            return mock_resp_success

        mock_client.post.side_effect = side_effect
        
        # We need at least 2 models configured to trigger fallback
        # Let's temporarily modify ALL_PROVIDERS for this test
        original_providers = list(ALL_PROVIDERS)
        ALL_PROVIDERS.clear()
        ALL_PROVIDERS.append({
            "name": "TestProvider",
            "type": "gemini",
            "url": "http://test",
            "api_key": "key",
            "models": ["model1", "model2"]
        })
        
        try:
            result = await chat_completion([{"role": "user", "content": "hi"}])
            assert result == "Success"
            # Verify post was called twice
            assert mock_client.post.call_count == 2
        finally:
            # Restore
            ALL_PROVIDERS.clear()
            ALL_PROVIDERS.extend(original_providers)
