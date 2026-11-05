# Merz Court photo checklist (phone) - PROPOSED

Purpose: training photos for the landmark model and a ground-truth list of door signs for O3. Plan:
`docs/research/perception_plan.md`. Round 1 takes about 2 hours, for 400-600 photos.

## Before going
- [ ] Permission: tell the supervisor, or ask building management, that you are photographing corridors and signs.
      Carry student ID.
- [ ] Choose areas and give each a short tag, e.g. `F2-west`, `F3-east`. **Pick one corridor as the O3 TEST
      corridor.** Photograph it only for the truth list and testing, never for training.
- [ ] Phone: clean the lens, use the normal 1x camera (not ultra-wide or portrait), HDR on auto, flash **off**,
      grid lines on. Keep location tagging on only if you want it; it is not needed.
- [ ] Bring a printed copy of the sign truth sheet (`image,text,sign_id`) or a notes app.
- [ ] Best times: quiet periods (early morning, evenings, out of term) to avoid people.

## Privacy: what NOT to photograph
- [ ] **No faces.** If someone walks into the frame, wait or retake. Delete any photo with a recognisable person
      before copying the photos off the phone.
- [ ] Do not photograph into offices, labs or meeting rooms through open doors or glass panels. Close the frame on
      the corridor side.
- [ ] Do not photograph screens, whiteboards, noticeboards with personal details, or papers on doors.
- [ ] Name plates on doors (staff names): photograph the sign as it is, but **do not publish** these photos. Keep them
      out of git (`data/` is gitignored) and out of the website. Use `run.py --no-raw-text` when sharing results.
- [ ] Avoid security features: keypads while in use, access-control panels close up, CCTV cameras.
- [ ] If asked to stop, stop and explain. Note it for the supervisor.

## For every door sign (the O3 class)
- [ ] Write its text **exactly as printed** on the truth sheet, plus a `sign_id`, before photographing.
- [ ] Note the **format** (letters, dots, digits, suffixes). This sets the regex in `config/sign_formats.yaml`.
- [ ] Take 3-4 photos:
  - [ ] **1 m, straight on**, sign filling about a third of the frame.
  - [ ] **2 m, about 30 degrees to the side**, the angle a robot driving past will see.
  - [ ] **3-4 m, down the corridor**: the hard case.
  - [ ] Optional: **lower height**, phone at about 0.5-1.0 m (roughly the C920 mast height once known; TODO: measure on
        rover), looking up at the sign.
- [ ] Include some door frame or wall around the sign, not a tight crop: the detector learns context.

## Doors, lifts, stairs, exit signs
- [ ] **Doors:** 30-50 without signs (fire doors, double doors, glass doors, open and shut). The rest come free with
      sign photos.
- [ ] **Lifts:** every lift on each floor you visit, doors open and shut, from 1, 2 and 4 m, straight on and at about
      45 degrees. 30-50 in total.
- [ ] **Stairs:** every stairwell, from the bottom looking up and the top looking down, plus the stairwell door.
      30-50 in total.
- [ ] **Exit signs:** over doors and hanging from ceilings, near and far, lit and unlit if possible. 50-100 in total.
- [ ] **Background:** about 10% of the total: corridors, corners and walls with none of the above.

## Variety (spread across the session, do not do everything in one style)
- [ ] Distances: 1, 2, 3 and 4 m.
- [ ] Angles: straight, about 30 degrees and about 60 degrees to each side.
- [ ] Heights: chest height and low (about 0.5-1 m).
- [ ] Lighting: bright corridors, dim ends, against windows (backlit), under strip lights (glare on glossy signs).
- [ ] A few slightly blurred, walking-pace photos (the robot does not stop for signs; OPEN_ISSUES #18). No more than
      about 10%.
- [ ] Portrait and landscape: mostly **landscape**, which matches the robot cameras.

## File naming (needed for the area-based split)
`<area>_<what>_<nn>.jpg`, e.g. `F3-east_M3.12_02.jpg`, `F2-west_lift_01.jpg`, `F2-west_stairs_03.jpg`,
`F2-west_bg_01.jpg`. Rename after the walk with a batch renamer; set the area tag per folder.

## After the walk
- [ ] Delete anything with a face or private detail (privacy list above).
- [ ] Copy to the laptop/SSD under `data/merz_photos/<date>/` (gitignored). **Do not commit photos.**
- [ ] Type the truth sheet into `data/merz_photos/<date>/signs.csv` with columns `image,text,sign_id`.
- [ ] Logbook entry: date, areas, count per class, lighting, the sign formats seen, any issues.
- [ ] First check, before any labelling: crop 20 signs by hand and run
      `python perception/run.py --source crops/ --out results.json` then
      `python perception/score_ocr.py --truth crops.csv --results results.json`.
      This measures the OCR alone on real signs.
