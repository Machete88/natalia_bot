"""Utilities for handling audio files in the bot."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


async def download_telegram_file(file: Any, destination: Path) -> Path:
    """Download a Telegram File object to the given destination path.

    The ``file`` argument is expected to be an instance of
    ``telegram.File``. The destination path's parent directories will be
    created if necessary. Returns the path to the downloaded file.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    await file.download_to_drive(custom_path=str(destination))  # type: ignore[call-arg]
    logging.debug("Downloaded Telegram file to %s", destination)
    return destination
