import hashlib, wave
from pathlib import Path
from .base import BaseTTSProvider

class MockTTSProvider(BaseTTSProvider):
    def __init__(self) -> None:
        Path("media/cache").mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str, voice: str) -> Path:
        key = hashlib.sha1((voice + text).encode()).hexdigest()
        path = Path("media/cache") / f"mock_{key}.wav"
        if path.exists():
            return path
        sr, dur = 16000, 1
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(b"\x00\x00" * sr * dur)
        return path
