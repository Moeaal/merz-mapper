"""Unit tests for the perception logic, with fake engines. No ROS, no GPU and no model needed."""
import csv
from pathlib import Path
import re

import numpy as np
import pytest
import yaml

from merz_perception.engines import Detection, RateLimiter, clip_box, keep_labels, make_engine
from merz_perception.ocr import OcrResult, parse_paddle_result, parse_rapidocr_result, prepare_crop
from merz_perception.offline_batch import CSV_COLUMNS, DEFAULT_ROOM_REGEX, process_folder, process_image
from merz_perception.room_numbers import ReadAgreement, RoomNumberValidator, normalise
from merz_perception.sharpness import is_sharp, to_gray, variance_of_laplacian

PACKAGE = Path(__file__).resolve().parents[1]
VALIDATOR = RoomNumberValidator(DEFAULT_ROOM_REGEX)


def checkerboard(size: int = 64, square: int = 8) -> np.ndarray:
    cols = np.indices((size, size)).sum(axis=0) // square % 2
    return (cols * 255).astype(np.uint8)


class FakeDetector:
    def __init__(self, detections):
        self._detections = detections

    def detect(self, image):
        return self._detections


class FakeOcr:
    def __init__(self, text='m2 14', confidence=0.9):
        self.calls = 0
        self._result = OcrResult(text, confidence)

    def read(self, image):
        self.calls += 1
        return self._result


# ---- room numbers
@pytest.mark.parametrize('raw, expected', [
    ('m2.14', 'M2.14'), (' M2 14 ', 'M214'), ('Room: 2-14!', 'ROOM2-14'), ('', ''),
])
def test_normalise(raw, expected):
    assert normalise(raw) == expected


@pytest.mark.parametrize('raw, expected', [
    ('m2.14', 'M2.14'),
    ('214', '214'),
    ('m2.1O', 'M2.10'),      # the letter O read in place of a zero
    ('M2.I4', 'M2.14'),      # the letter I read in place of a one
    ('EXIT', None),
    ('', None),
])
def test_validator_accepts_repairs_or_rejects(raw, expected):
    assert VALIDATOR.validate(raw) == expected


def test_validator_keeps_the_first_letter_during_repair():
    assert RoomNumberValidator(r'S\d{3}').validate('s1O2') == 'S102'


def test_validator_uses_the_configured_regex():
    assert RoomNumberValidator(r'\d{3}').validate('M2.14') is None


def test_one_read_is_not_agreement_but_two_are():
    agreement = ReadAgreement(min_agreement=2, window_s=10.0)
    assert agreement.add('M2.14', 0.0) is False
    assert agreement.add('M2.14', 1.0) is True


def test_different_text_does_not_count_towards_agreement():
    agreement = ReadAgreement(min_agreement=2, window_s=10.0)
    agreement.add('M2.14', 0.0)
    assert agreement.add('M2.15', 1.0) is False


def test_old_reads_expire():
    agreement = ReadAgreement(min_agreement=2, window_s=10.0)
    agreement.add('M2.14', 0.0)
    assert agreement.add('M2.14', 11.0) is False


# ---- sharpness
def test_sharp_image_scores_above_blurred_copy():
    cv2 = pytest.importorskip('cv2')
    sharp = checkerboard()
    assert variance_of_laplacian(sharp) > 10 * variance_of_laplacian(cv2.GaussianBlur(sharp, (9, 9), 3))


def test_flat_image_scores_zero_and_tiny_image_is_safe():
    assert variance_of_laplacian(np.full((32, 32), 128, np.uint8)) == 0.0
    assert variance_of_laplacian(np.zeros((2, 2), np.uint8)) == 0.0


def test_is_sharp_applies_the_threshold():
    assert is_sharp(checkerboard(), 100.0)
    assert not is_sharp(np.full((32, 32), 128, np.uint8), 100.0)


def test_laplacian_agrees_with_opencv():
    cv2 = pytest.importorskip('cv2')
    rng = np.random.default_rng(1)
    image = rng.integers(0, 255, (40, 40), dtype=np.uint8)
    opencv_value = cv2.Laplacian(image, cv2.CV_64F, ksize=1)[1:-1, 1:-1].var()
    assert variance_of_laplacian(image) == pytest.approx(opencv_value)


def test_to_gray_weights_bgr_order():
    pure_green = np.zeros((3, 3, 3), np.uint8)
    pure_green[..., 1] = 100
    assert to_gray(pure_green)[0, 0] == pytest.approx(58.7)


# ---- engine helpers
def test_keep_labels_filters_and_empty_list_keeps_all():
    door, lift = Detection('door', .9, 0, 0, 1, 1), Detection('lift', .9, 0, 0, 1, 1)
    assert keep_labels([door, lift], ['door']) == [door]
    assert keep_labels([door, lift], []) == [door, lift]


def test_clip_box_stays_inside_and_applies_margin():
    box = Detection('x', 1, -5, 10, 200, 60)
    assert clip_box(box, 100, 100) == (0, 10, 100, 60)
    assert clip_box(Detection('x', 1, 10, 10, 20, 20), 100, 100, margin=0.5) == (5, 5, 25, 25)


def test_rate_limiter_allows_once_per_period():
    limiter = RateLimiter(2.0)
    assert [limiter.ready(t) for t in (0.0, 0.1, 0.5, 0.6, 1.0)] == [True, False, True, False, True]


@pytest.mark.parametrize('engine, filename', [('tensorrt', 'model.pt'), ('ultralytics', 'model.engine')])
def test_make_engine_rejects_the_wrong_file_type(engine, filename):
    with pytest.raises(ValueError, match='needs a'):
        make_engine(engine, filename)


def test_make_engine_rejects_unknown_name_and_missing_file(tmp_path):
    with pytest.raises(ValueError, match='Unknown engine'):
        make_engine('magic', 'model.pt')
    with pytest.raises(FileNotFoundError):
        make_engine('ultralytics', str(tmp_path / 'absent.pt'))


# ---- OCR result parsing
def test_parse_paddle_v3_shape():
    assert parse_paddle_result([{'rec_texts': ['A', 'M2.14'], 'rec_scores': [0.5, 0.9]}]) == OcrResult('M2.14', 0.9)


def test_parse_paddle_v2_shape():
    assert parse_paddle_result([[[[0, 0], ('M2.14', 0.8)], [[0, 0], ('x', 0.1)]]]) == OcrResult('M2.14', 0.8)


@pytest.mark.parametrize('empty', [None, [], [None], [{'rec_texts': [], 'rec_scores': []}]])
def test_parse_paddle_empty(empty):
    assert parse_paddle_result(empty) is None


def test_parse_rapidocr():
    assert parse_rapidocr_result(([[[0], 'M2.14', 0.7]], [0.1])) == OcrResult('M2.14', 0.7)
    assert parse_rapidocr_result((None, None)) is None


def test_prepare_crop_upscales_only_small_crops():
    pytest.importorskip('cv2')
    assert prepare_crop(np.zeros((32, 50, 3), np.uint8)).shape[:2] == (64, 100)
    assert prepare_crop(np.zeros((100, 50, 3), np.uint8)).shape[:2] == (100, 50)


# ---- offline pipeline and CSV
def test_blurred_sign_is_never_sent_to_ocr():
    ocr = FakeOcr()
    image = np.full((100, 100, 3), 128, np.uint8)
    rows = process_image('a.png', image, FakeDetector([Detection('room_sign', .9, 10, 10, 60, 60)]), ocr, VALIDATOR, 50)
    assert ocr.calls == 0
    assert rows[0]['sharp_enough'] is False and rows[0]['room_number'] == ''


def test_only_signs_go_to_ocr():
    ocr = FakeOcr()
    image = np.stack([checkerboard(100, 4)] * 3, axis=2)
    rows = process_image('a.png', image, FakeDetector([Detection('door', .9, 0, 0, 60, 60)]), ocr, VALIDATOR, 50)
    assert ocr.calls == 0 and rows[0]['label'] == 'door'


def test_no_detector_treats_the_image_as_a_sign_and_validates_text():
    image = np.stack([checkerboard(100, 4)] * 3, axis=2)
    rows = process_image('a.png', image, None, FakeOcr('m2.14'), VALIDATOR, 50)
    assert rows[0]['raw_text'] == 'm2.14' and rows[0]['room_number'] == 'M2.14'


def test_process_folder_writes_a_readable_csv_in_name_order(tmp_path):
    cv2 = pytest.importorskip('cv2')
    image = np.stack([checkerboard(100, 4)] * 3, axis=2)
    for name in ('b.png', 'a.png'):
        cv2.imwrite(str(tmp_path / name), image)
    (tmp_path / 'notes.txt').write_text('not an image')
    out = tmp_path / 'out.csv'
    detector = FakeDetector([Detection('room_sign', .9, 10, 10, 60, 60), Detection('door', .8, 1, 1, 9, 9)])

    assert process_folder(tmp_path, out, detector, FakeOcr('m2.14'), VALIDATOR, 50) == 4

    with open(out, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == CSV_COLUMNS
    assert [r['image'] for r in rows] == ['a.png', 'a.png', 'b.png', 'b.png']
    assert rows[0]['room_number'] == 'M2.14' and rows[1]['room_number'] == ''


# ---- config
def test_config_regex_matches_the_default_and_compiles():
    params = yaml.safe_load((PACKAGE / 'config' / 'perception.yaml').read_text())
    regex = params['sign_reader']['ros__parameters']['room_regex']
    assert regex == DEFAULT_ROOM_REGEX
    re.compile(regex)


def test_c920_detector_only_looks_for_signs():
    params = yaml.safe_load((PACKAGE / 'config' / 'perception.yaml').read_text())
    assert params['detector_c920']['ros__parameters']['allowed_labels'] == ['room_sign']


# ---- split-row fix (decisions #24): "M1.14" detected as overlapping pieces "M1.1" + "14"
from merz_perception.ocr import parse_paddle_lines, parse_rapidocr_lines, read_room_number, row_groups  # noqa: E402


class SplitRowOcr:
    """Fake engine that reproduces the PP-OCR split seen on synthetic signs in perception/."""

    def __init__(self, merged='M1.14'):
        self._merged = merged
        self.recognised = []

    def read_lines(self, image):
        return [OcrResult('M1.1', 0.80, (10, 10, 60, 40)), OcrResult('14', 0.95, (55, 10, 85, 40))]

    def recognise(self, image):
        self.recognised.append(image.shape[:2])
        return OcrResult(self._merged, 0.90) if self._merged else None


def test_row_groups_joins_overlapping_pieces_on_one_row_only():
    lines = [OcrResult('M1.1', .8, (10, 10, 60, 40)), OcrResult('14', .9, (55, 10, 85, 40)),
             OcrResult('OFFICE', .9, (10, 80, 90, 100))]
    assert row_groups(lines) == [(10, 10, 85, 40)]
    assert row_groups([OcrResult('a', .9, (0, 0, 10, 10)), OcrResult('b', .9, (200, 0, 210, 10))]) == []
    assert row_groups([OcrResult('a', .9)]) == []


def test_split_row_is_re_read_and_the_fragment_is_not_a_room():
    ocr = SplitRowOcr()
    line, room = read_room_number(ocr, np.zeros((60, 100, 3), np.uint8), VALIDATOR)
    assert room == 'M1.14' and line.text == 'M1.14'
    assert len(ocr.recognised) == 1


def test_without_a_re_read_the_old_behaviour_is_kept():
    # No merged reading: the most confident valid line still wins (the known weakness; see decisions #24).
    line, room = read_room_number(SplitRowOcr(merged=None), np.zeros((60, 100, 3), np.uint8), VALIDATOR)
    assert room == '14'


def test_fragment_of_a_longer_reading_on_another_line_is_dropped():
    class TwoLines:
        def read_lines(self, image):
            return [OcrResult('14', 0.99), OcrResult('M1.14', 0.70)]
    assert read_room_number(TwoLines(), np.zeros((10, 10, 3), np.uint8), VALIDATOR)[1] == 'M1.14'


def test_a_label_word_next_to_the_number_is_ignored():
    class Labelled:
        def read_lines(self, image):
            return [OcrResult('Room M2.14', 0.9)]
    assert read_room_number(Labelled(), np.zeros((10, 10, 3), np.uint8), VALIDATOR)[1] == 'M2.14'


def test_engines_with_only_read_still_work_and_rejections_return_the_raw_line():
    assert read_room_number(FakeOcr('m2.14'), np.zeros((10, 10, 3), np.uint8), VALIDATOR)[1] == 'M2.14'
    line, room = read_room_number(FakeOcr('EXIT'), np.zeros((10, 10, 3), np.uint8), VALIDATOR)
    assert room is None and line.text == 'EXIT'

    class Empty:
        def read(self, image):
            return None
    assert read_room_number(Empty(), np.zeros((10, 10, 3), np.uint8), VALIDATOR) == (None, None)


def test_line_parsers_keep_boxes():
    v3 = [{'rec_texts': ['M1.1', '14'], 'rec_scores': [0.8, 0.9],
           'rec_polys': [[[10, 10], [60, 10], [60, 40], [10, 40]], [[55, 10], [85, 10], [85, 40], [55, 40]]]}]
    assert [l.box for l in parse_paddle_lines(v3)] == [(10, 10, 60, 40), (55, 10, 85, 40)]
    v2 = [[[[[0, 0], [5, 0], [5, 5], [0, 5]], ('M2.14', 0.8)]]]
    assert parse_paddle_lines(v2)[0].box == (0, 0, 5, 5)
    rapid = ([[[[1, 2], [9, 2], [9, 8], [1, 8]], 'M2.14', 0.7]], [0.1])
    assert parse_rapidocr_lines(rapid)[0].box == (1, 2, 9, 8)
