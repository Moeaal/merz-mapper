"""The Merz Mapper SQLite database. Standard library only. Schema documented in docs/DATABASE_SCHEMA.md.

The robot writes this file during a run, and the website reads it afterwards.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Iterable, Optional

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entrances (
    id     TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    x      REAL NOT NULL,
    y      REAL NOT NULL,
    yaw    REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS photos (
    id     INTEGER PRIMARY KEY,
    path   TEXT NOT NULL,
    x      REAL,
    y      REAL,
    yaw    REAL,
    taken_at REAL
);
CREATE TABLE IF NOT EXISTS landmarks (
    id     INTEGER PRIMARY KEY,
    class  TEXT NOT NULL,
    text   TEXT NOT NULL DEFAULT '',
    x      REAL NOT NULL,
    y      REAL NOT NULL,
    z      REAL NOT NULL,
    var_x  REAL NOT NULL DEFAULT 0,
    var_y  REAL NOT NULL DEFAULT 0,
    var_z  REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    observation_count INTEGER NOT NULL DEFAULT 1,
    first_seen REAL,
    last_seen  REAL,
    photo_id INTEGER REFERENCES photos(id)
);
CREATE TABLE IF NOT EXISTS observations (
    id          INTEGER PRIMARY KEY,
    landmark_id INTEGER NOT NULL REFERENCES landmarks(id),
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    depth_m REAL,
    confidence REAL,
    stamp REAL
);
CREATE TABLE IF NOT EXISTS access_zones (
    entrance_id TEXT NOT NULL REFERENCES entrances(id),
    landmark_id INTEGER NOT NULL REFERENCES landmarks(id),
    PRIMARY KEY (entrance_id, landmark_id)
);
CREATE TABLE IF NOT EXISTS junctions (
    id     INTEGER PRIMARY KEY,
    x      REAL NOT NULL,
    y      REAL NOT NULL,
    photo_id INTEGER REFERENCES photos(id)
);
CREATE TABLE IF NOT EXISTS junction_edges (
    a INTEGER NOT NULL REFERENCES junctions(id),
    b INTEGER NOT NULL REFERENCES junctions(id),
    length_m REAL NOT NULL,
    PRIMARY KEY (a, b),
    CHECK (a < b)
);
CREATE TABLE IF NOT EXISTS zone_junctions (
    entrance_id TEXT NOT NULL REFERENCES entrances(id),
    junction_id INTEGER NOT NULL REFERENCES junctions(id),
    PRIMARY KEY (entrance_id, junction_id)
);
"""


class MerzDatabase:
    """A thin wrapper so that no other code has to write SQL for the robot's side of the database."""

    def __init__(self, path: str | Path) -> None:
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.connection.executescript(SCHEMA)
        self.connection.execute('INSERT OR IGNORE INTO meta VALUES (?, ?)', ('schema_version', str(SCHEMA_VERSION)))
        self.connection.commit()

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def __enter__(self) -> 'MerzDatabase':
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def set_meta(self, key: str, value: str) -> None:
        self.connection.execute('INSERT OR REPLACE INTO meta VALUES (?, ?)', (key, value))
        self.connection.commit()

    def upsert_entrance(self, entrance_id: str, name: str, x: float, y: float, yaw: float = 0.0) -> None:
        # An upsert, not INSERT OR REPLACE: replacing deletes the row first, which foreign keys in access_zones forbid.
        self.connection.execute(
            """INSERT INTO entrances (id, name, x, y, yaw) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, x=excluded.x, y=excluded.y, yaw=excluded.yaw""",
            (entrance_id, name, x, y, yaw))
        self.connection.commit()

    def add_photo(self, path: str, x: Optional[float] = None, y: Optional[float] = None, yaw: Optional[float] = None,
                  taken_at: Optional[float] = None) -> int:
        cursor = self.connection.execute('INSERT INTO photos (path, x, y, yaw, taken_at) VALUES (?, ?, ?, ?, ?)',
                                         (path, x, y, yaw, taken_at))
        self.connection.commit()
        return int(cursor.lastrowid)

    def next_landmark_id(self) -> int:
        """The first free landmark id, so that a later run adds to the database rather than overwriting it."""
        row = self.connection.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM landmarks').fetchone()
        return int(row[0])

    def upsert_landmark(self, landmark_id: int, landmark_class: str, text: str, position: Iterable[float],
                        variances: Iterable[float] = (0.0, 0.0, 0.0), confidence: float = 0.0,
                        observation_count: int = 1, first_seen: Optional[float] = None,
                        last_seen: Optional[float] = None, photo_id: Optional[int] = None) -> None:
        x, y, z = position
        var_x, var_y, var_z = variances
        self.connection.execute(
            """INSERT INTO landmarks (id, class, text, x, y, z, var_x, var_y, var_z, confidence, observation_count,
                                      first_seen, last_seen, photo_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 class=excluded.class, text=excluded.text, x=excluded.x, y=excluded.y, z=excluded.z,
                 var_x=excluded.var_x, var_y=excluded.var_y, var_z=excluded.var_z, confidence=excluded.confidence,
                 observation_count=excluded.observation_count, first_seen=excluded.first_seen,
                 last_seen=excluded.last_seen, photo_id=COALESCE(excluded.photo_id, landmarks.photo_id)""",
            (landmark_id, landmark_class, text, float(x), float(y), float(z), float(var_x), float(var_y), float(var_z),
             float(confidence), int(observation_count), first_seen, last_seen, photo_id))
        self.connection.commit()

    def add_observation(self, landmark_id: int, position: Iterable[float], depth_m: Optional[float] = None,
                        confidence: Optional[float] = None, stamp: Optional[float] = None) -> None:
        x, y, z = position
        self.connection.execute(
            'INSERT INTO observations (landmark_id, x, y, z, depth_m, confidence, stamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (landmark_id, float(x), float(y), float(z), depth_m, confidence, stamp))
        self.connection.commit()

    def landmarks(self) -> list[dict]:
        previous = self.connection.row_factory
        self.connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in self.connection.execute('SELECT * FROM landmarks ORDER BY id')]
        self.connection.row_factory = previous
        return rows

    def set_access_zone(self, entrance_id: str, landmark_ids: Iterable[int], junction_ids: Iterable[int] = ()) -> None:
        """Replace what is recorded as reachable from this entrance."""
        self.connection.execute('DELETE FROM access_zones WHERE entrance_id = ?', (entrance_id,))
        self.connection.execute('DELETE FROM zone_junctions WHERE entrance_id = ?', (entrance_id,))
        self.connection.executemany('INSERT INTO access_zones VALUES (?, ?)',
                                    [(entrance_id, int(i)) for i in landmark_ids])
        self.connection.executemany('INSERT INTO zone_junctions VALUES (?, ?)',
                                    [(entrance_id, int(i)) for i in junction_ids])
        self.connection.commit()

    def add_junction(self, x: float, y: float, photo_id: Optional[int] = None) -> int:
        cursor = self.connection.execute('INSERT INTO junctions (x, y, photo_id) VALUES (?, ?, ?)', (x, y, photo_id))
        self.connection.commit()
        return int(cursor.lastrowid)

    def add_junction_edge(self, junction_a: int, junction_b: int, length_m: float) -> None:
        """Connect two junctions. The ids are sorted, so each pair can only be stored once."""
        if junction_a == junction_b:
            return
        a, b = sorted((junction_a, junction_b))
        self.connection.execute('INSERT OR REPLACE INTO junction_edges VALUES (?, ?, ?)', (a, b, length_m))
        self.connection.commit()

    def junctions(self) -> list[dict]:
        previous = self.connection.row_factory
        self.connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in self.connection.execute('SELECT * FROM junctions ORDER BY id')]
        self.connection.row_factory = previous
        return rows
