# merz_perception

**Status: IMPLEMENTED - not yet built or tested on hardware.** There is no trained Merz model, and the room number
format and sharpness threshold are placeholders.

Finds landmarks with YOLO and reads room numbers from door signs (O3).

## How it works
1. `detector_node` runs at a few Hz, once per camera. The D455 instance finds all landmark types, as it has depth. The
   C920 instance looks only for `room_sign`, as it has the detail for text. Each output keeps its image's timestamp.
2. `sign_reader_node` runs only when a sign is detected. It crops the sign and rejects blur (variance of Laplacian). It
   upscales small crops, runs OCR, then normalises and validates the text with a regex. A number is only published
   once read the same way twice within 10 s, as one misread must not create a false room.
3. `merz_semantic_map` takes these and works out positions.

Engine choice is a parameter (`ultralytics` or `tensorrt`); see `tools/export_tensorrt.md`. Training data: use
`tools/extract_frames.py` on recorded bags.

## Run without ROS
```powershell
python -m merz_perception.offline_batch --images frames --out results.csv --weights merz.pt
python -m merz_perception.offline_batch --images crops --out ocr.csv --no-detector --ocr rapid
```

## Known limitation
The robot does not stop for signs. At full speed the sharpness check may reject most crops, which would hurt O3 and
would show up in the `sharp_enough` column. If so, lower the exploration speed or add stops near signs.

## Unit tests that pass on Windows
`test/test_perception_core.py`: normaliser, validator and repair, read agreement, sharpness on sharp and blurred images,
CSV output, label filter, box clipping, rate limiter, engine selection errors, parsing of OCR result formats.
**Not covered on Windows:** real inference (needs a model and libraries), `detector_node`, `sign_reader_node`.
