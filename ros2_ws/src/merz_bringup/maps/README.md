# Keep-out masks for glass

**Status: IMPLEMENTED - not yet built or tested on hardware.** Real masks need a real map, and `.pgm` files are not kept
in git, so there is none here yet.

A mask is a copy of a saved map with the forbidden areas painted black.
1. Run one entrance, then find the map (`.yaml` + `.pgm`) in `~/merz_data/maps/`.
2. Copy both to `keepout.pgm` and `keepout.yaml`, and set `image: keepout.pgm` in the YAML.
3. In an image editor, paint a black area over each glass wall or door and a safe margin in front of it, and paint
   everything else white. Save as 8-bit PGM.
4. Use it: `keepout_mask:=/path/to/keepout.yaml`.

**The mask only lines up when run in the same map frame.** A new SLAM run starts its frame where the robot starts. So run
later entrances with `posegraph:=...`, or the mask will land in the wrong place. Check it in RViz (`/keepout_filter_mask`)
against the live map before any autonomous motion.
