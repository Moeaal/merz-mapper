"""PROPOSED prototype tests: parser, pipeline logic and scorer, with fake detector/OCR (no models needed)."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from merz_signs.detector import Detection, WholeImage, pad_box  # noqa: E402
from merz_signs.ocr import make_ocr, parse_paddle_result, parse_rapidocr_result  # noqa: E402
from merz_signs.pipeline import SignPipeline, Settings, load_settings  # noqa: E402
from merz_signs.room_parser import OcrLine, RoomParser, normalise, row_groups  # noqa: E402
import score_ocr  # noqa: E402

PATTERN = r'[A-Z]?\d{1,2}\.?\d{1,3}'


@pytest.fixture
def parser() -> RoomParser:
    return RoomParser([PATTERN])


def test_normalise() -> None:
    assert normalise(' m4. 13 ') == 'M4.13'
    assert normalise('M4,13') == 'M4.13'


@pytest.mark.parametrize('raw, room, repaired', [
    ('M4.13', 'M4.13', False),
    ('m4.13', 'M4.13', False),
    ('2.07', '2.07', False),
    ('M4.I3', 'M4.13', True),      # I -> 1
    ('M4.1O', 'M4.10', True),      # O -> 0
    ('M4.13.', 'M4.13', False),    # trailing OCR noise
])
def test_parse_token(parser: RoomParser, raw: str, room: str, repaired: bool) -> None:
    assert parser.parse_token(raw) == (room, repaired)


@pytest.mark.parametrize('raw', ['Seminar', 'ROOM', 'Dr', '', 'M', 'M4.13456', 'TOILETS'])
def test_rejects_words(parser: RoomParser, raw: str) -> None:
    assert parser.parse_token(raw) is None


def test_prefix_letter_not_repaired(parser: RoomParser) -> None:
    # "S4.13": S is a plausible wing prefix, so it is kept, not turned into 5.
    assert parser.parse_token('S4.13') == ('S4.13', False)


def test_candidates_from_sign_lines(parser: RoomParser) -> None:
    lines = [OcrLine('Room M4. 13', 0.95), OcrLine('Seminar Room', 0.99), OcrLine('M4.I3', 0.97)]
    best = parser.best(lines)
    assert best is not None and best.room == 'M4.13'
    assert {c.room for c in parser.candidates(lines)} == {'M4.13'}


def test_clean_read_beats_repaired(parser: RoomParser) -> None:
    lines = [OcrLine('M4.1O', 0.96), OcrLine('M4.18', 0.90)]
    assert parser.best(lines).room == 'M4.18'          # 0.96 * 0.9 < 0.90


def test_multiple_patterns() -> None:
    p = RoomParser([PATTERN, r'[A-Z]\d\.\d{2}[A-Z]'])
    assert p.parse_token('M4.13A') == ('M4.13A', False)


def test_empty_patterns_rejected() -> None:
    with pytest.raises(ValueError):
        RoomParser([])


def test_parse_paddle_3x_and_2x() -> None:
    v3 = [{'rec_texts': ['M4.13', ''], 'rec_scores': [0.9, 0.1]}]
    v2 = [[[[[0, 0], [1, 0], [1, 1], [0, 1]], ('M4.13', 0.9)]]]
    assert parse_paddle_result(v3) == [OcrLine('M4.13', 0.9)]
    assert parse_paddle_result(v2) == [OcrLine('M4.13', 0.9)]
    assert parse_paddle_result(None) == []


def test_parse_rapidocr() -> None:
    assert parse_rapidocr_result(([[[[0, 0]], 'M4.13', 0.8], [[[0, 0]], ' ', 0.1]], [0.1])) == [OcrLine('M4.13', 0.8)]
    assert parse_rapidocr_result((None, None)) == []


def test_unknown_ocr_engine() -> None:
    with pytest.raises(ValueError):
        make_ocr('tesseract')


def test_pad_box_clips() -> None:
    assert pad_box((10, 10, 110, 60), 100, 100, 0.1) == (0, 5, 100, 65)


def test_config_loads() -> None:
    settings = load_settings()
    assert settings.room_patterns and settings.detector['mode'] == 'none'


class FakeOcr:
    def __init__(self, lines: list[OcrLine]) -> None:
        self.lines = lines
        self.calls = 0

    def read(self, image_bgr: np.ndarray) -> list[OcrLine]:
        self.calls += 1
        return self.lines


class FakeDetector:
    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        return [Detection('door', 0.8, (0, 0, 50, 100)), Detection('door_sign', 0.7, (60, 10, 90, 30))]


def test_pipeline_only_reads_sign_crops() -> None:
    ocr = FakeOcr([OcrLine('M4.13', 0.9)])
    pipeline = SignPipeline(Settings(room_patterns=[PATTERN]), FakeDetector(), ocr)
    out = pipeline.process(np.zeros((100, 100, 3), np.uint8), 'x.jpg')
    assert ocr.calls == 1
    assert out['room_number'] == 'M4.13'
    assert 'room_number' not in out['detections'][0]          # the door is not OCR'd


def test_pipeline_no_raw_text_and_blur_gate() -> None:
    ocr = FakeOcr([OcrLine('M4.13', 0.9)])
    settings = Settings(room_patterns=[PATTERN], keep_raw_text=False, min_sharpness=1e9)
    out = SignPipeline(settings, WholeImage(), ocr).process(np.zeros((50, 50, 3), np.uint8))
    assert ocr.calls == 0 and out['room_number'] is None
    assert 'ocr_lines' not in out['detections'][0]


def test_score_photo_and_sign_level() -> None:
    truth = [{'image': 'a1.jpg', 'text': 'M4.13', 'sign_id': 's1'},
             {'image': 'a2.jpg', 'text': 'M4.13', 'sign_id': 's1'},
             {'image': 'a3.jpg', 'text': 'M4.13', 'sign_id': 's1'},
             {'image': 'b1.jpg', 'text': 'M4.14', 'sign_id': 's2'},
             {'image': 'c1.jpg', 'text': 'M4.15', 'sign_id': 's3'}]
    reads = {'a1.jpg': 'M4.13', 'a2.jpg': 'M4.18', 'a3.jpg': 'm4.13', 'b1.jpg': None, 'c1.jpg': 'M4.16'}
    r = score_ocr.score(truth, reads)
    assert (r['photos'], r['photos_correct'], r['photos_no_read'], r['photos_false_read']) == (5, 2, 1, 2)
    assert (r['signs'], r['signs_correct']) == (3, 1)
    assert not r['pass']


def test_score_tie_is_wrong() -> None:
    truth = [{'image': f'{i}.jpg', 'text': 'M4.13', 'sign_id': 's'} for i in range(2)]
    r = score_ocr.score(truth, {'0.jpg': 'M4.13', '1.jpg': 'M4.18'})
    assert r['signs_correct'] == 0


def test_read_truth_defaults_sign_id(tmp_path: Path) -> None:
    csv_path = tmp_path / 't.csv'
    csv_path.write_text('image,text\na.jpg,m4.13\nb.jpg,\n', encoding='utf-8')
    rows = score_ocr.read_truth(csv_path)
    assert rows == [{'image': 'a.jpg', 'text': 'M4.13', 'sign_id': 'M4.13'}]


def test_row_groups_joins_split_number_only() -> None:
    lines = [OcrLine('M1.1', 0.99, (14, 23, 218, 122)), OcrLine('14', 0.99, (180, 29, 303, 117)),
             OcrLine('Teaching Laboratory', 0.99, (25, 142, 372, 182))]
    assert row_groups(lines) == [(14, 23, 303, 122)]
    assert row_groups([OcrLine('M1.14', 0.9, (0, 0, 100, 40))]) == []


def test_fragment_dropped_across_lines(parser: RoomParser) -> None:
    lines = [OcrLine('14', 0.9999), OcrLine('M1.14', 0.996)]
    assert [c.room for c in parser.candidates(lines)] == ['M1.14']


class SplittingOcr(FakeOcr):
    """Mimics PP-OCR splitting M1.14 into two pieces; recognition of the merged row gives the full number."""

    def __init__(self) -> None:
        super().__init__([OcrLine('M1.1', 0.99, (10, 10, 60, 40)), OcrLine('14', 0.999, (50, 12, 90, 40))])
        self.recognised: list[tuple[int, ...]] = []

    def read(self, image_bgr: np.ndarray) -> list[OcrLine]:
        return list(self.lines)

    def recognise(self, image_bgr: np.ndarray) -> OcrLine:
        self.recognised.append(image_bgr.shape)
        return OcrLine('M1.14', 0.995)


def test_pipeline_rereads_split_row() -> None:
    ocr = SplittingOcr()
    out = SignPipeline(Settings(room_patterns=[PATTERN]), WholeImage(), ocr).process(np.zeros((120, 200, 3), np.uint8))
    assert len(ocr.recognised) == 1
    assert out['room_number'] == 'M1.14'


def test_split_holds_out_whole_areas() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'train'))
    import split_dataset

    images = [Path(n) for n in ['F3-east_M3.12_01.jpg', 'F3-east_M3.12_02.jpg', 'F2-west_M2.01_01.jpg']]
    train, val = split_dataset.split(images, {'F3-east'})
    assert [p.name for p in val] == ['F3-east_M3.12_01.jpg', 'F3-east_M3.12_02.jpg']
    assert [p.name for p in train] == ['F2-west_M2.01_01.jpg']
