# Database schema

SQLite file, default `~/merz_data/merz.sqlite`. Written by the robot, read by the website. Definition in code:
`ros2_ws/src/merz_semantic_map/merz_semantic_map/database.py`. **Status: IMPLEMENTED - not yet used on real data.**

Positions are metres in the `map` frame. Times are ROS time in seconds. All entrances must share one map frame:
see "One map frame" below.

## Tables
| Table | One row per | Key columns | Written by |
| --- | --- | --- | --- |
| `meta` | Setting | `key`, `value`; holds `schema_version` | database.py |
| `entrances` | Building entrance | `id` (used in the QR URL), `name`, `x`, `y`, `yaw` (start pose) | access zone code |
| `landmarks` | Physical landmark | `class`, `text` (room number), `x y z`, `var_x var_y var_z` (m^2), `confidence`, `observation_count`, `first_seen`, `last_seen`, `photo_id` | `landmark_node` |
| `observations` | One sighting of a landmark | `landmark_id`, `x y z`, `depth_m`, `confidence`, `stamp` | `landmark_node` |
| `access_zones` | (entrance, landmark) reachable | `entrance_id`, `landmark_id` | access zone code |
| `junctions` | Corridor junction | `x`, `y`, `photo_id` | `junction_photo_node` |
| `junction_edges` | Corridor between junctions | `a`, `b` (always `a < b`), `length_m` | `junction_photo_node` |
| `zone_junctions` | (entrance, junction) reachable | `entrance_id`, `junction_id` | access zone code |
| `photos` | Saved image | `path`, `x`, `y`, `yaw`, `taken_at` | `junction_photo_node` |

## Rooms
A "room" is not a table of its own. It is a `landmarks` row with non-empty `text`, reachable from an entrance when
listed in `access_zones`. This keeps one source of truth for sign positions.

## Why keep every observation?
O8 compares fused and single-sensor estimates. With raw observations stored, both can be calculated from one run,
without repeating it in another mode, and the spread of each landmark's sightings can be plotted (O4).

## One map frame
Routes and landmarks only make sense across entrances if all runs share a map frame. A new SLAM run normally starts
its own frame at wherever the robot is. So the first entrance creates the map, and each later entrance continues from
its posegraph (`posegraph:=...`, with the start pose in that frame). See `docs/BUILD_GUIDE.md` section 6.

Threat to validity: a door open in an earlier run leaves free space in the continued map. Flood fill then treats it as
open unless the later run sees the door closed. Record door states for every run (O5).

## Example queries
```sql
-- Rooms reachable from one entrance
SELECT l.text FROM landmarks l JOIN access_zones z ON z.landmark_id = l.id
WHERE z.entrance_id = 'east' AND l.text <> '' ORDER BY l.text;

-- How often each landmark was seen, and how much the sightings spread
SELECT id, class, text, observation_count, sqrt(var_x + var_y) AS spread_m FROM landmarks;
```
