"""Read-only API smoke tests with a temporary SQLite fixture."""
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from musicforge.airplay.api import create_app


def test_charts_and_station_listing(tmp_path):
    db = tmp_path / "airplay.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE airplay_observations (
            station TEXT, artist TEXT, title TEXT, observed_at TEXT,
            segment_sequence INTEGER, source TEXT)""")
        conn.execute("INSERT INTO airplay_observations VALUES (?, ?, ?, ?, ?, ?)",
                     ("WRIF", "Artist", "Song", "2026-10-30T12:00:00+00:00", 1, "netplayer"))
    client = TestClient(create_app(db))
    songs = client.get("/api/v1/charts/songs", params={"day": "2026-10-30"}).json()
    assert songs["results"][0]["plays"] == 1
    assert songs["results"][0]["title"] == "Song"
    assert client.get("/api/v1/charts/artists", params={"day": "2026-10-30"}).json()["results"][0]["songs"] == 1
    assert client.get("/api/v1/stations").json()["stations"][0]["station"] == "WRIF"
    assert client.get("/api/v1/charts/songs", params={"period": "bad"}).status_code == 422


def test_missing_database(tmp_path):
    client = TestClient(create_app(tmp_path / "missing.sqlite3"))
    assert client.get("/health").json()["database_available"] is False
    assert client.get("/api/v1/stations").status_code == 503
