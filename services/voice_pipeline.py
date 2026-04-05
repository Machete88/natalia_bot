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
        voice_map: dict | None = None,
    ) -> None:
        self.stt = stt
        self.tts = tts
        # teacher-name -> ElevenLabs-Voice-ID aus .env
        self.voice_map = voice_map or {}

    async def process(
        self, user_id: int, audio_path: Path, dialogue_router: DialogueRouter
    ) -> Tuple[str, Path, str]:
        # 1) Voice → Text
        transcribed = await self.stt.transcribe(audio_path)

        # 2) Text → Antwort (LLM, mit Lehrerprofil)
        result: Dict[str, Any] = await dialogue_router.generate_reply(user_id, transcribed)
        reply_text = result["text"]
        teacher = result["teacher"]  # "vitali", "dering", "imperator"

        # 3) Lehrername auf Voice-ID mappen
        voice_id = self.voice_map.get(teacher.lower(), teacher)

        # 4) Text → Audio
        audio_file = await self.tts.synthesize(reply_text, voice_id)

        return reply_text, audio_file, teacher