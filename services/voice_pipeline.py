from __future__ import annotations
from pathlib import Path
from typing import Tuple, Any, Dict

from services.stt import BaseSTTProvider
from services.tts import BaseTTSProvider
from services.dialogue_router import DialogueRouter


class VoicePipeline:
    def __init__(
        self,
        stt: BaseSTTProvider,
        tts: BaseTTSProvider,
        voice_id: str | None = None,
    ) -> None:
        self.stt = stt
        self.tts = tts
        # Feste Voice-ID für Imperator
        self.voice_id = voice_id or ""

    async def process(
        self, user_id: int, audio_path: Path, dialogue_router: DialogueRouter
    ) -> Tuple[str, Path, str]:
        # 1) Voice → Text
        transcribed = await self.stt.transcribe(audio_path)

        # 2) Text → Antwort (LLM)
        result: Dict[str, Any] = await dialogue_router.generate_reply(user_id, transcribed)
        reply_text = result["text"]

        # 3) Text → Audio (immer Imperator)
        audio_file = await self.tts.synthesize(reply_text, self.voice_id)

        return reply_text, audio_file, "imperator"
