"""Voice pipeline: STT → LLM → TTS, always using Imperator voice."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Any, Dict

from services.stt import BaseSTTProvider
from services.tts import BaseTTSProvider
from services.dialogue_router import DialogueRouter


class VoicePipeline:
    """Single-voice pipeline fixed to Imperator."""

    def __init__(
        self,
        stt: BaseSTTProvider,
        tts: BaseTTSProvider,
        voice_id: str = "",
    ) -> None:
        self.stt = stt
        self.tts = tts
        self.voice_id: str = voice_id or ""

    async def process(
        self,
        user_id: int,
        audio_path: Path,
        dialogue_router: DialogueRouter,
    ) -> Tuple[str, Path, str]:
        """Returns (reply_text, audio_path, teacher_name)."""
        transcribed = await self.stt.transcribe(audio_path)
        result: Dict[str, Any] = await dialogue_router.generate_reply(
            user_id=user_id, user_text=transcribed
        )
        reply_text = result["text"]
        audio_file = await self.tts.synthesize(reply_text, self.voice_id)
        return reply_text, audio_file, "imperator"
