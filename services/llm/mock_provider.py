import asyncio
from .base import BaseLLMProvider
class MockLLMProvider(BaseLLMProvider):
    async def complete(self, prompt: str) -> str:
        await asyncio.sleep(0)
        return "Привет! Я пока в режиме тестирования. 🙂"
