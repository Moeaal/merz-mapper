from pathlib import Path

from setuptools import find_packages, setup

package_name = "merz_semantic_map"


def data_files_for(*folders: str) -> list[tuple[str, list[str]]]:
    """Install each data folder into share/, keeping its directory layout."""
    entries = []
    for folder in folders:
        for path in sorted(Path(folder).rglob("*")):
            if path.is_file():
                target = Path("share") / package_name / path.parent
                entries.append((target.as_posix(), [path.as_posix()]))
    return entries


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        *data_files_for("launch", "config"),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Mohammed Abdulaal",
    maintainer_email="mohdbdulaal@gmail.com",
    description="Landmark localisation from detections, depth and TF, and the SQLite database writer.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "landmark_node = merz_semantic_map.landmark_node:main",
        ],
    },
)
