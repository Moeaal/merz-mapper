# Evaluation tools

**Status: IMPLEMENTED - not yet used on real data.** Only tested with synthetic data. These produce no result for the
report until real runs exist. Procedures, ground truth and pass rules are in `docs/EXPERIMENTS.md`.

| Script | Objective | Input |
| --- | --- | --- |
| `map_coverage.py` | O2 coverage, >=90% | map YAML, corridor polygon CSV |
| `wall_error.py` | O2 walls, 0.15 m | map YAML, floor plan walls CSV |
| `ocr_rate.py` | O3 signs, >=85% | manual sign list, database or offline CSV |
| `landmark_error.py` | O4, mean <=0.5 m | laser-measured truth CSV, database |
| `access_zone_compare.py` | O5 | manual survey CSV, database |
| `route_timing.py` | O6 <1 s, O7 >=9/10 | running website, routes CSV |
| `fusion_compare.py` | O8 | truth CSV, database |

Each one prints a table, and scripts with `--plot` save a report-ready figure, one IEEE column wide. The database
is opened read-only, so evaluating cannot alter results.

Run on Windows or the Jetson with no ROS: `python tools/eval/map_coverage.py --help`.

## Unit tests that pass on Windows
`test_eval.py`, using synthetic data with known answers.
