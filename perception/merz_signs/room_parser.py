"""Turn raw OCR lines into room numbers with a configurable regex. No ROS, no OCR library needed.

PROPOSED. The real Merz Court sign format is UNKNOWN until signs are photographed; the patterns live in
config/sign_formats.yaml so they can be changed without touching code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, Sequence

# OCR often confuses letters and digits that look alike. A repair is only tried when the plain text fails.
LOOKALIKE_DIGITS = str.maketrans({'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', '|': '1',
                                  'Z': '2', 'S': '5', 'B': '8', 'G': '6'})
# Characters kept after normalising. Dots and hyphens stay, as room numbers may use them.
_NOT_ALLOWED = re.compile(r'[^A-Z0-9.\-]')


def normalise(text: str) -> str:
    """Uppercase and strip everything except letters, digits, dots and hyphens (spaces included)."""
    return _NOT_ALLOWED.sub('', text.upper().replace(',', '.'))


Box = tuple[int, int, int, int]   # x1, y1, x2, y2 in pixels of the crop given to OCR


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float
    box: Box | None = field(default=None, compare=False)


def row_groups(lines: Sequence[OcrLine], gap_ratio: float = 0.6) -> list[Box]:
    """Union boxes of text pieces that sit side by side on one row (two or more pieces only).

    PP-OCR's text detector sometimes splits one room number into overlapping pieces ("M1.1" + "14" for M1.14, seen
    on the synthetic samples), and the pieces cannot be joined reliably as text. Re-reading the union box can.
    Pieces join when they overlap vertically by half the smaller height and the horizontal gap is under
    gap_ratio x line height (overlaps count as gap <= 0).
    """
    boxed = sorted((l.box for l in lines if l.box is not None), key=lambda b: b[0])
    groups: list[list[Box]] = []
    for box in boxed:
        for group in groups:
            last = group[-1]
            height = min(box[3] - box[1], last[3] - last[1])
            v_overlap = min(box[3], last[3]) - max(box[1], last[1])
            gap = box[0] - last[2]
            if height > 0 and v_overlap >= 0.5 * height and gap <= gap_ratio * height:
                group.append(box)
                break
        else:
            groups.append([box])
    return [(min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))
            for g in groups if len(g) > 1]


@dataclass(frozen=True)
class RoomCandidate:
    room: str
    confidence: float
    source_text: str
    repaired: bool


class RoomParser:
    """Find room numbers in OCR output.

    patterns: regexes that must match a whole token (fullmatch), tried in order.
    prefix_letters: how many leading characters may be real letters (e.g. a building or wing prefix) and so are never
    "repaired" into digits.
    """

    def __init__(self, patterns: Sequence[str], prefix_letters: int = 1) -> None:
        if not patterns:
            raise ValueError('At least one room-number pattern is needed')
        self.patterns = [re.compile(p) for p in patterns]
        self.prefix_letters = prefix_letters

    def matches(self, token: str) -> bool:
        return any(p.fullmatch(token) for p in self.patterns)

    def parse_token(self, raw: str) -> tuple[str, bool] | None:
        """Return (room, repaired) or None. A trailing dot or hyphen from OCR noise is dropped."""
        token = normalise(raw).strip('.-')
        if not token:
            return None
        if self.matches(token):
            return token, False
        head, tail = token[:self.prefix_letters], token[self.prefix_letters:]
        repaired = head + tail.translate(LOOKALIKE_DIGITS)
        if repaired != token and self.matches(repaired):
            return repaired, True
        return None

    def _tokens(self, text: str) -> Iterable[str]:
        """Each whitespace token, then neighbouring pairs joined, then the whole line without spaces.

        OCR sometimes splits one number ("M4. 13") or merges a label into it ("ROOM M4.13" stays split by space).
        """
        parts = text.split()
        yield from parts
        for a, b in zip(parts, parts[1:]):
            yield a + b
        if len(parts) > 2:
            yield ''.join(parts)

    def candidates(self, lines: Iterable[OcrLine]) -> list[RoomCandidate]:
        found: dict[str, RoomCandidate] = {}
        for line in lines:
            line_hits = [p for p in (self.parse_token(t) for t in self._tokens(line.text)) if p is not None]
            # When "M4. 13" is split, "13" alone may also match a loose pattern; keep only the longest reading.
            rooms = {room for room, _ in line_hits}
            line_hits = [(r, rep) for r, rep in line_hits if not any(r != o and r in o for o in rooms)]
            for room, repaired in line_hits:
                # A repaired read is slightly less trusted than a clean one of the same confidence.
                confidence = line.confidence * (0.9 if repaired else 1.0)
                previous = found.get(room)
                if previous is None or confidence > previous.confidence:
                    found[room] = RoomCandidate(room, confidence, line.text, repaired)
        # Across lines too: a fragment ("14") of a longer reading ("M1.14") of the same sign is dropped.
        kept = [c for c in found.values() if not any(c.room != o and c.room in o for o in found)]
        return sorted(kept, key=lambda c: c.confidence, reverse=True)

    def best(self, lines: Iterable[OcrLine]) -> RoomCandidate | None:
        found = self.candidates(lines)
        return found[0] if found else None
