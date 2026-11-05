# Tools

Plain-Python tools that run on the laptop without ROS 2. Tests: `python -m pytest tools` from the repository root.

| Path | What it does |
| --- | --- |
| [`eval/`](eval/) | One script per objective (O2-O8) that scores a run; optional `--json` and `--plot` output |
| [`extract_frames.py`](extract_frames.py) | Pulls camera frames out of a rosbag for labelling a YOLO dataset |
| [`export_tensorrt.md`](export_tensorrt.md) | How to turn the trained YOLO model into a TensorRT engine on the Jetson |
| [`web_import.py`](web_import.py) | Turns one rover run (map, database, photos, bags, eval results) into the website's data bundle |
| [`web_export.py`](web_export.py) | Exports the website as static files for GitHub Pages |
| [`synthetic_run/`](synthetic_run/) | Makes a clearly labelled SYNTHETIC run in the rover's formats, for the website until real data exists |
| [`yolo_practice/`](yolo_practice/) | Dr Wright's webcam YOLO practice script (learning only, not robot code) |
| [`test_static_refs.py`](test_static_refs.py) | Static checks across `ros2_ws`: launch files, entry points, YAML sections, messages |
| [`test_md_links.py`](test_md_links.py) | Checks that every relative link in every Markdown file resolves |
