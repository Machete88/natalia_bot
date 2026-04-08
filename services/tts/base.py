"""Abstrakte Basisklasse fuer alle TTS-Provider."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSProvider(ABC):
    """Alle TTS-Provider muessen synthesize() implementieren."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> Path:
        """Synthetisiert Text und gibt Pfad zur Audio-Datei zurueck."""
        ...
