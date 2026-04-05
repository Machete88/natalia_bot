from abc import ABC, abstractmethod
from pathlib import Path
class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> Path: ...
