import pytest
from services.llm import MockLLMProvider

@pytest.mark.asyncio
async def test_mock_llm_returns_string():
    provider = MockLLMProvider()
    result = await provider.complete("Привет")
    assert isinstance(result, str) and result
