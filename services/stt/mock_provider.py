from pathlib import Path
from .base import BaseSTTProvider
class MockSTTProvider(BaseSTTProvider):
    async def transcribe(self, audio_path: Path) -> str:
        return "[голосовое сообщение получено — STT в режиме mock]"
