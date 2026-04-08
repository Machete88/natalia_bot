"""OpenAI-kompatibler LLM-Provider (OpenRouter, OpenAI, etc.).

Unterstuetzt sowohl chat() (Messages-API) als auch complete() (Legacy).
"""
from __future__ import annotations

import logging
from typing import List, Dict

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT   = 60
_MAX_TOKENS = 400


class OpenAIProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._key   = api_key
        self._base  = base_url.rstrip("/")
        self._model = model

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Messages-API — bevorzugter Aufruf."""
        payload = {
            "model":       self._model,
            "messages":    messages,
            "max_tokens":  _MAX_TOKENS,
            "temperature": 0.75,
        }
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/Machete88/natalia_bot",
            "X-Title":       "NataliaBot",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/chat/completions",
                json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def complete(self, prompt: str) -> str:
        """Legacy-Wrapper — baut eine einzelne user-Message."""
        return await self.chat([{"role": "user", "content": prompt}])
