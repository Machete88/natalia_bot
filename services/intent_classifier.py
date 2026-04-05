"""Intent classification stub.

This module currently provides a trivial intent classifier that always
returns ``None``. In the future it can be extended to detect
commands or intent such as requesting help, starting exercises or
expressing frustration. Extracting this logic into its own module
allows future improvements without touching other parts of the system.
"""

from __future__ import annotations

from typing import Optional


class IntentClassifier:
    """Simple intent classifier placeholder."""

    async def classify(self, text: str) -> Optional[str]:
        """Classify the given text into an intent.

        Always returns ``None`` for now. When implemented, it should
        return strings such as ``"greeting"``, ``"exercise"`` or
        ``"frustrated"``.
        """
        # TODO: implement real intent detection
        return None
