"""OpenAI-compatible LLM provider (works with OpenRouter)."""
from __future__ import annotations
import httpx
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model

    async def complete(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.85,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
