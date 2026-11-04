# merz_exploration

**Status: IMPLEMENTED - not yet built or tested on hardware.**

Drives frontier exploration from an entrance, works out what is reachable from it (O5), photographs junctions for the
website (O7), and saves everything at the end of a run.

## How it works
- **Exploration:** `explore_lite` (decisions #7, PROPOSED) sends Nav2 towards frontiers, the edges of known space.
- **Mission end:** `mission_node` ends the run when no frontier has been reported for 60 s, when the time cap passes, or on
  request (`ros2 service call /mission_node/finish std_srvs/srv/Trigger`). It then stops the explorer, saves map and
  posegraph, and asks for the access zone. explore_lite announces no finish of its own, so this rule is an assumption
  about its marker output, and must be checked on the first real run.
- **Access zones:** closed doors are walls to the LIDAR, so exploration stops at them. A flood fill from the entrance
  gives the connected free space. Landmarks within `landmark_adjacency_m` of it are in the zone. Unknown cells block the
  fill: only what was seen counts. Re-run offline with `python -m merz_exploration.compute_access_zones`.
- **Junction rule:** the scan is split into four 90-degree sectors. A sector is open if its median range exceeds
  `open_range_m`. A corridor has two open sectors, so three or more means a junction. A new junction must be at least
  `min_spacing_m` from any saved one. Edges between junctions use distance driven.

## Threats to validity (O5)
Doors open during a run make the zone too large, so record each door's state. Glass that the LIDAR sees through could
also connect zones wrongly, or leave gaps. `start_yaw` and `start_x/y` must be correct in the shared map frame.

## Unit tests that pass on Windows
`test/test_exploration_core.py`: flood fill on small synthetic grids (rooms, closed doors, diagonal gaps, unknown cells),
start cell snapping, zone membership, PGM and map YAML reading against the map_server rules, the junction rule, the
junction graph, and mission-end timing, plus a run from saved map to stored access zone.
**Not covered on Windows:** the nodes, and explore_lite's real behaviour.
