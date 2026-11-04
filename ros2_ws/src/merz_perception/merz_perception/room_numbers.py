"""Turn raw OCR text into a validated room number. No ROS imports.

The regex is a parameter because the real Merz Court sign format is not yet known (TODO: measure on rover).
"""
from __future__ import annotations

from collections import deque
import re

# OCR often swaps letters and digits that look alike. Only used when the plain text fails validation.
_LOOKALIKE_DIGITS = str.maketrans({'O': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8'})


def normalise(raw_text: str) -> str:
    """Uppercase, and remove spaces and anything unusual. Dots and hyphens stay, as room numbers may use them."""
    return re.sub(r'[^A-Z0-9.\-]', '', raw_text.upper())


class RoomNumberValidator:
    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(pattern)

    def is_valid(self, text: str) -> bool:
        return self._pattern.fullmatch(text) is not None

    def validate(self, raw_text: str) -> str | None:
        """Return the room number, or None if it cannot be made to fit the format.

        If the text fails, a repair is tried that swaps lookalike letters for digits, leaving the first character
        alone since it may be a real letter (a building prefix, say).
        """
        text = normalise(raw_text)
        if not text:
            return None
        if self.is_valid(text):
            return text
        repaired = text[0] + text[1:].translate(_LOOKALIKE_DIGITS)
        return repaired if self.is_valid(repaired) else None


class ReadAgreement:
    """Accept a room number once it has been read the same way at least min_agreement times within the window.

    One misread must not create a false room in the database, and the camera gets several looks at each sign.
    """

    def __init__(self, min_agreement: int = 2, window_s: float = 10.0) -> None:
        self._min_agreement = min_agreement
        self._window_s = window_s
        self._reads: deque[tuple[float, str]] = deque()

    def add(self, text: str, now_s: float) -> bool:
        """Record a read and return True if this text is now agreed."""
        self._reads.append((now_s, text))
        while self._reads and now_s - self._reads[0][0] > self._window_s:
            self._reads.popleft()
        return sum(1 for _, seen in self._reads if seen == text) >= self._min_agreement
