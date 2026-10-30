"""SQLite persistence for candidate radio song observations."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class AirplayStore:
    def __init__(self, path: str | Path) -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS airplay_observations (
                id INTEGER PRIMARY KEY,
                station TEXT NOT NULL,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                segment_sequence INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'hls',
                UNIQUE(station, observed_at, segment_sequence, artist, title)
            )
        """)
        self.connection.commit()

    def add(self, station: str, label: str, observed_at: datetime | None,
            segment_sequence: int) -> bool:
        if observed_at is None or " - " not in label:
            return False
        artist, title = label.split(" - ", 1)
        if not artist.strip() or not title.strip():
            return False
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO airplay_observations
               (station, artist, title, observed_at, segment_sequence)
               VALUES (?, ?, ?, ?, ?)""",
            (station, artist.strip(), title.strip(), observed_at.isoformat(),
             segment_sequence),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> AirplayStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
